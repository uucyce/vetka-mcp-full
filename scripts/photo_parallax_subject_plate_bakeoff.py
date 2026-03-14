#!/usr/bin/env python3
"""Export subject RGBA and build a baseline clean plate bake-off."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build subject RGBA and clean plate baseline outputs.")
    parser.add_argument(
        "--sample-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/public/samples",
        help="Directory with original sample images.",
    )
    parser.add_argument(
        "--mask-refine-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mask_refine_bakeoff",
        help="Root directory of refine outputs.",
    )
    parser.add_argument(
        "--mask-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mask_bakeoff",
        help="Root directory of coarse mask outputs.",
    )
    parser.add_argument(
        "--outdir",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/subject_plate_bakeoff",
        help="Output directory for subject/plate artifacts.",
    )
    parser.add_argument(
        "--backend",
        action="append",
        dest="backends",
        help="Limit run to one or more depth backends.",
    )
    return parser.parse_args()


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_rgb(path: Path) -> "np.ndarray":
    import numpy as np
    from PIL import Image

    return np.asarray(Image.open(path).convert("RGB"))


def load_mask(path: Path) -> "np.ndarray":
    import numpy as np
    from PIL import Image

    return np.asarray(Image.open(path).convert("L"), dtype=np.uint8) > 127


def dilate_mask(mask: "np.ndarray", size: int) -> "np.ndarray":
    import numpy as np
    from PIL import Image, ImageFilter

    image = Image.fromarray((mask.astype("uint8") * 255), mode="L")
    return np.asarray(image.filter(ImageFilter.MaxFilter(size)), dtype=np.uint8) > 127


def erode_mask(mask: "np.ndarray", size: int) -> "np.ndarray":
    import numpy as np
    from PIL import Image, ImageFilter

    image = Image.fromarray((mask.astype("uint8") * 255), mode="L")
    eroded = np.asarray(image.filter(ImageFilter.MinFilter(size)), dtype=np.uint8) > 127
    return eroded if eroded.any() else mask


def checkerboard(width: int, height: int, block: int = 24) -> "np.ndarray":
    import numpy as np

    ys, xs = np.indices((height, width))
    tiles = ((xs // block) + (ys // block)) % 2
    board = np.zeros((height, width, 3), dtype=np.uint8)
    board[tiles == 0] = (239, 235, 228)
    board[tiles == 1] = (206, 200, 191)
    return board


def alpha_composite(rgb: "np.ndarray", alpha_mask: "np.ndarray") -> "np.ndarray":
    import numpy as np

    background = checkerboard(rgb.shape[1], rgb.shape[0])
    alpha = alpha_mask.astype(np.float32)[..., None]
    out = rgb.astype(np.float32) * alpha + background.astype(np.float32) * (1.0 - alpha)
    return out.clip(0, 255).astype("uint8")


def build_subject_rgba(rgb: "np.ndarray", mask: "np.ndarray") -> "np.ndarray":
    import numpy as np

    alpha = (mask.astype(np.uint8) * 255)[..., None]
    return np.concatenate([rgb, alpha], axis=2)


def build_background_rgba(rgb: "np.ndarray", mask: "np.ndarray") -> "np.ndarray":
    import numpy as np

    alpha = ((~mask).astype(np.uint8) * 255)[..., None]
    return np.concatenate([rgb, alpha], axis=2)


def build_trimap(mask: "np.ndarray", ring_size: int = 21) -> "np.ndarray":
    import numpy as np

    if ring_size % 2 == 0:
        ring_size += 1
    sure_fg = erode_mask(mask, ring_size)
    sure_bg = ~dilate_mask(mask, ring_size)
    trimap = np.full(mask.shape, 128, dtype=np.uint8)
    trimap[sure_bg] = 0
    trimap[sure_fg] = 255
    return trimap


def color_distance(inner_rgb: "np.ndarray", outer_rgb: "np.ndarray") -> float:
    import numpy as np

    if inner_rgb.size == 0 or outer_rgb.size == 0:
        return 1e3
    inner = inner_rgb.reshape(-1, 3).astype(np.float32)
    outer = outer_rgb.reshape(-1, 3).astype(np.float32)
    return float(np.abs(inner.mean(axis=0) - outer.mean(axis=0)).mean())


def gradient_map(gray: "np.ndarray") -> "np.ndarray":
    import cv2

    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    return cv2.magnitude(grad_x, grad_y)


def ring_metrics(image: "np.ndarray", filled_mask: "np.ndarray") -> tuple[float, float, float]:
    import numpy as np

    inner_ring = filled_mask & ~erode_mask(filled_mask, 11)
    outer_ring = dilate_mask(filled_mask, 11) & ~filled_mask
    if not inner_ring.any() or not outer_ring.any():
        return 1e3, 1e3, 1e3

    color_gap = color_distance(image[inner_ring], image[outer_ring])

    gray = image.astype(np.float32).mean(axis=2) / 255.0
    grad = gradient_map(gray)
    inner_grad = float(grad[inner_ring].mean()) if inner_ring.any() else 0.0
    outer_grad = float(grad[outer_ring].mean()) if outer_ring.any() else 0.0
    grad_gap = abs(inner_grad - outer_grad)

    inner_std = float(image[inner_ring].astype(np.float32).std()) if inner_ring.any() else 0.0
    outer_std = float(image[outer_ring].astype(np.float32).std()) if outer_ring.any() else 1.0
    texture_gap = abs(inner_std - outer_std)
    return color_gap, grad_gap, texture_gap


def build_hole_mask(mask: "np.ndarray", dilation_size: int) -> "np.ndarray":
    grown = dilate_mask(mask, dilation_size)
    return grown


def inpaint_candidate(rgb: "np.ndarray", hole_mask: "np.ndarray", method_name: str, radius: int) -> "np.ndarray":
    import cv2

    method = cv2.INPAINT_TELEA if method_name == "telea" else cv2.INPAINT_NS
    image_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    mask_u8 = (hole_mask.astype("uint8") * 255)
    filled = cv2.inpaint(image_bgr, mask_u8, radius, method)
    return cv2.cvtColor(filled, cv2.COLOR_BGR2RGB)


def mask_bbox(mask: "np.ndarray") -> tuple[int, int, int, int] | None:
    import numpy as np

    ys, xs = np.where(mask)
    if ys.size == 0 or xs.size == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def export_images(
    source_rgb: "np.ndarray",
    final_mask: "np.ndarray",
    clean_plate: "np.ndarray",
    hole_mask: "np.ndarray",
    out_dir: Path,
) -> dict[str, str]:
    import numpy as np
    from PIL import Image

    out_dir.mkdir(parents=True, exist_ok=True)
    subject_rgba = build_subject_rgba(source_rgb, final_mask)
    foreground_rgba = subject_rgba
    background_rgba = build_background_rgba(clean_plate, final_mask)
    subject_trimap = build_trimap(final_mask)
    subject_preview = alpha_composite(source_rgb, final_mask)
    hole_overlay = source_rgb.copy()
    accent = np.asarray([238, 88, 76], dtype=np.float32)
    hole_overlay[hole_mask] = (0.7 * hole_overlay[hole_mask].astype(np.float32) + 0.3 * accent).astype("uint8")
    source_cut = source_rgb.copy()
    source_cut[final_mask] = 0

    paths = {
        "subject_rgba": str(out_dir / "subject_rgba.png"),
        "foreground_rgba": str(out_dir / "foreground_rgba.png"),
        "background_rgba": str(out_dir / "background_rgba.png"),
        "subject_trimap": str(out_dir / "subject_trimap.png"),
        "subject_preview": str(out_dir / "subject_preview.png"),
        "subject_mask": str(out_dir / "subject_mask.png"),
        "clean_plate": str(out_dir / "clean_plate.png"),
        "hole_mask": str(out_dir / "hole_mask.png"),
        "hole_overlay": str(out_dir / "hole_overlay.png"),
        "source_cutout_debug": str(out_dir / "source_cutout_debug.png"),
    }

    Image.fromarray(subject_rgba, mode="RGBA").save(paths["subject_rgba"])
    Image.fromarray(foreground_rgba, mode="RGBA").save(paths["foreground_rgba"])
    Image.fromarray(background_rgba, mode="RGBA").save(paths["background_rgba"])
    Image.fromarray(subject_trimap, mode="L").save(paths["subject_trimap"])
    Image.fromarray(subject_preview, mode="RGB").save(paths["subject_preview"])
    Image.fromarray((final_mask.astype("uint8") * 255), mode="L").save(paths["subject_mask"])
    Image.fromarray(clean_plate, mode="RGB").save(paths["clean_plate"])
    Image.fromarray((hole_mask.astype("uint8") * 255), mode="L").save(paths["hole_mask"])
    Image.fromarray(hole_overlay, mode="RGB").save(paths["hole_overlay"])
    Image.fromarray(source_cut, mode="RGB").save(paths["source_cutout_debug"])
    return paths


def make_sheet(
    source_rgb: "np.ndarray",
    subject_preview: Path,
    clean_plate: Path,
    hole_overlay: Path,
    subject_mask: Path,
    hole_mask: Path,
    out_path: Path,
) -> None:
    from PIL import Image

    tiles = [
        Image.fromarray(source_rgb, mode="RGB"),
        Image.open(subject_preview).convert("RGB"),
        Image.open(clean_plate).convert("RGB"),
        Image.open(hole_overlay).convert("RGB"),
        Image.open(subject_mask).convert("RGB"),
        Image.open(hole_mask).convert("RGB"),
    ]
    width = max(tile.width for tile in tiles)
    height = max(tile.height for tile in tiles)
    sheet = Image.new("RGB", (width * 3, height * 2), "#07080b")
    for index, tile in enumerate(tiles):
        x = (index % 3) * width
        y = (index // 3) * height
        if tile.size != (width, height):
            tile = tile.resize((width, height), Image.Resampling.LANCZOS)
        sheet.paste(tile, (x, y))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def load_selected_mask(mask_refine_root: Path, mask_root: Path, backend: str, sample: str) -> tuple[Path, str]:
    refine_summary_path = mask_refine_root / backend / sample / "refine_summary.json"
    if refine_summary_path.exists():
        refine_summary = json.loads(refine_summary_path.read_text(encoding="utf-8"))
        return Path(refine_summary["best"]["mask_path"]), refine_summary["best"]["family"]

    coarse_summary_path = mask_root / backend / sample / "mask_summary.json"
    coarse_summary = json.loads(coarse_summary_path.read_text(encoding="utf-8"))
    return Path(coarse_summary["best"]["mask_path"]), "coarse_passthrough"


def candidate_score(
    plate_rgb: "np.ndarray",
    hole_mask: "np.ndarray",
    source_rgb: "np.ndarray",
) -> dict[str, float]:
    import numpy as np

    color_gap, grad_gap, texture_gap = ring_metrics(plate_rgb, hole_mask)
    hole_area = float(hole_mask.mean())
    border_touch = np.concatenate([hole_mask[0, :], hole_mask[-1, :], hole_mask[:, 0], hole_mask[:, -1]])
    border_touch_ratio = float(border_touch.mean())
    residual_delta = float(np.abs(plate_rgb.astype(np.float32) - source_rgb.astype(np.float32))[hole_mask].mean()) if hole_mask.any() else 0.0

    score = (
        12.0
        - color_gap * 0.055
        - grad_gap * 7.5
        - texture_gap * 0.035
        - residual_delta * 0.04
        - hole_area * 8.0
        - border_touch_ratio * 1.6
    )
    return {
        "score": round(float(score), 5),
        "color_gap": round(float(color_gap), 5),
        "grad_gap": round(float(grad_gap), 5),
        "texture_gap": round(float(texture_gap), 5),
        "residual_delta": round(float(residual_delta), 5),
        "hole_area_ratio": round(hole_area, 5),
        "border_touch_ratio": round(border_touch_ratio, 5),
    }


def run_for_sample(
    sample_path: Path,
    selected_mask_path: Path,
    selected_mask_family: str,
    out_dir: Path,
) -> dict[str, Any]:
    source_rgb = load_rgb(sample_path)
    final_mask = load_mask(selected_mask_path)

    candidate_records: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    candidate_dir = out_dir / "candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)

    for method_name in ("telea", "ns"):
        for dilation_size in (11, 21, 31):
            hole_mask = build_hole_mask(final_mask, dilation_size)
            radius = max(3, dilation_size // 4)
            plate_rgb = inpaint_candidate(source_rgb, hole_mask, method_name, radius)
            metrics = candidate_score(plate_rgb, hole_mask, source_rgb)

            candidate_key = f"{method_name}_d{dilation_size}"
            plate_path = candidate_dir / f"{candidate_key}.png"
            hole_path = candidate_dir / f"{candidate_key}_hole.png"

            from PIL import Image

            Image.fromarray(plate_rgb, mode="RGB").save(plate_path)
            Image.fromarray((hole_mask.astype("uint8") * 255), mode="L").save(hole_path)

            record = {
                "key": candidate_key,
                "method": method_name,
                "dilation_size": dilation_size,
                "radius": radius,
                "plate_path": str(plate_path),
                "hole_mask_path": str(hole_path),
                **metrics,
            }
            candidate_records.append(record)
            if best is None or record["score"] > best["score"]:
                best = {**record, "plate_rgb": plate_rgb, "hole_mask": hole_mask}

    assert best is not None
    export_paths = export_images(source_rgb, final_mask, best["plate_rgb"], best["hole_mask"], out_dir)
    make_sheet(
        source_rgb,
        Path(export_paths["subject_preview"]),
        Path(export_paths["clean_plate"]),
        Path(export_paths["hole_overlay"]),
        Path(export_paths["subject_mask"]),
        Path(export_paths["hole_mask"]),
        out_dir / "subject_plate_debug_sheet.png",
    )

    bbox = mask_bbox(final_mask)
    if bbox is None:
        bbox_values = None
    else:
        bbox_values = list(bbox)

    candidate_records.sort(key=lambda item: item["score"], reverse=True)
    summary = {
        "sample": sample_path.name,
        "selected_mask_path": str(selected_mask_path),
        "selected_mask_family": selected_mask_family,
        "source_width": int(source_rgb.shape[1]),
        "source_height": int(source_rgb.shape[0]),
        "subject_bbox": bbox_values,
        "subject_area_ratio": round(float(final_mask.mean()), 5),
        "best": {
            "key": best["key"],
            "method": best["method"],
            "dilation_size": best["dilation_size"],
            "radius": best["radius"],
            "score": best["score"],
            "subject_rgba_path": export_paths["subject_rgba"],
            "foreground_rgba_path": export_paths["foreground_rgba"],
            "background_rgba_path": export_paths["background_rgba"],
            "subject_trimap_path": export_paths["subject_trimap"],
            "subject_preview_path": export_paths["subject_preview"],
            "subject_mask_path": export_paths["subject_mask"],
            "clean_plate_path": export_paths["clean_plate"],
            "hole_mask_path": export_paths["hole_mask"],
            "hole_overlay_path": export_paths["hole_overlay"],
            "source_cutout_debug_path": export_paths["source_cutout_debug"],
            "debug_sheet_path": str(out_dir / "subject_plate_debug_sheet.png"),
            "color_gap": best["color_gap"],
            "grad_gap": best["grad_gap"],
            "texture_gap": best["texture_gap"],
            "residual_delta": best["residual_delta"],
            "hole_area_ratio": best["hole_area_ratio"],
            "border_touch_ratio": best["border_touch_ratio"],
        },
        "candidates": candidate_records,
    }
    save_json(out_dir / "subject_plate_summary.json", summary)
    return summary


def main() -> int:
    args = parse_args()
    sample_root = Path(args.sample_root).expanduser().resolve()
    mask_refine_root = Path(args.mask_refine_root).expanduser().resolve()
    mask_root = Path(args.mask_root).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    requested_backends = set(args.backends or [])

    summaries: list[dict[str, Any]] = []
    for backend_dir in sorted(path for path in mask_root.iterdir() if path.is_dir()):
        if requested_backends and backend_dir.name not in requested_backends:
            continue
        for sample_dir in sorted(path for path in backend_dir.iterdir() if path.is_dir()):
            sample_name = sample_dir.name
            sample_path = next(sample_root.glob(f"{sample_name}.*"), None)
            if sample_path is None:
                continue
            selected_mask_path, selected_mask_family = load_selected_mask(mask_refine_root, mask_root, backend_dir.name, sample_name)
            summaries.append(
                {
                    "backend": backend_dir.name,
                    **run_for_sample(
                        sample_path=sample_path,
                        selected_mask_path=selected_mask_path,
                        selected_mask_family=selected_mask_family,
                        out_dir=outdir / backend_dir.name / sample_name,
                    ),
                }
            )

    summary = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "sample_root": str(sample_root),
        "mask_refine_root": str(mask_refine_root),
        "mask_root": str(mask_root),
        "outdir": str(outdir),
        "entries": summaries,
    }
    save_json(outdir / "subject_plate_bakeoff_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
