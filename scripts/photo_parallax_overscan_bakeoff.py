#!/usr/bin/env python3
"""Build motion-aware overscan plates on top of LaMa clean-plate outputs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import time
from pathlib import Path
from typing import Any

from photo_parallax_subject_plate_bakeoff import (
    color_distance,
    dilate_mask,
    erode_mask,
    gradient_map,
    load_rgb,
    save_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build overscan plates from LaMa clean-plate outputs.")
    parser.add_argument(
        "--sample-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/public/samples",
        help="Directory with original sample images.",
    )
    parser.add_argument(
        "--lama-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/lama_plate_bakeoff",
        help="Root directory of LaMa clean-plate outputs.",
    )
    parser.add_argument(
        "--sample-analysis-json",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/sample_analysis_2026-03-10.json",
        help="JSON report with recommended motion and overscan values.",
    )
    parser.add_argument(
        "--outdir",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/overscan_bakeoff",
        help="Output directory for overscan artifacts.",
    )
    parser.add_argument(
        "--model-path",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/checkpoints/lama/big-lama.pt",
        help="Local path to the LaMa torchscript model.",
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=("auto", "mps", "cpu"),
        help="Torch device for LaMa inference.",
    )
    parser.add_argument(
        "--backend",
        action="append",
        dest="backends",
        help="Limit run to one or more depth backends.",
    )
    parser.add_argument(
        "--padding-mode",
        action="append",
        dest="padding_modes",
        choices=("reflect", "edge"),
        help="Limit candidate seeding modes.",
    )
    return parser.parse_args()


def choose_device(value: str) -> str:
    import torch

    if value == "cpu":
        return "cpu"
    if value == "mps":
        return "mps"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_analysis_by_name(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {entry["file_name"]: entry for entry in payload["images"]}


def infer_motion_type(sample_name: str, analysis: dict[str, Any]) -> str:
    scene_type = analysis.get("scene_type", "")
    center_focus_bias = float(analysis.get("center_focus_bias", 1.0))
    lower_name = sample_name.lower()

    if "portrait" in lower_name or scene_type == "square-ish":
        return "dolly-out + zoom-in"
    if "hover" in lower_name or "street" in lower_name:
        return "pan"
    if center_focus_bias >= 2.2 or "closeup" in lower_name:
        return "orbit"
    return "pan"


def build_layout_payload(
    sample_name: str,
    source_width: int,
    source_height: int,
    overscan_width: int,
    overscan_height: int,
    overscan_pct: float,
    analysis: dict[str, Any],
) -> dict[str, Any]:
    motion_type = infer_motion_type(sample_name, analysis)
    return {
        "sample": sample_name,
        "source": {
            "width": source_width,
            "height": source_height,
        },
        "overscan": {
            "width": overscan_width,
            "height": overscan_height,
            "overscan_pct": round(float(overscan_pct), 2),
        },
        "layers": [
            {"id": "background", "z": -24},
            {"id": "foreground", "z": 12},
        ],
        "camera": {
            "motion_type": motion_type,
            "travel_x_pct": round(float(analysis["recommended_motion_x_pct"]), 2),
            "travel_y_pct": round(float(analysis["recommended_motion_y_pct"]), 2),
            "zoom": round(float(analysis["recommended_zoom"]), 3),
            "speed": 1.0,
            "duration_sec": 4.0,
            "fps": 25,
        },
    }


def pad_canvas(rgb: "np.ndarray", pad_x: int, pad_y: int, mode: str) -> "np.ndarray":
    import numpy as np

    if mode == "reflect":
        return np.pad(rgb, ((pad_y, pad_y), (pad_x, pad_x), (0, 0)), mode="reflect")
    return np.pad(rgb, ((pad_y, pad_y), (pad_x, pad_x), (0, 0)), mode="edge")


def build_overscan_mask(height: int, width: int, pad_x: int, pad_y: int) -> "np.ndarray":
    import numpy as np

    mask = np.ones((height + pad_y * 2, width + pad_x * 2), dtype=bool)
    mask[pad_y:pad_y + height, pad_x:pad_x + width] = False
    return mask


def run_lama(lama: Any, rgb: "np.ndarray", mask: "np.ndarray") -> "np.ndarray":
    import numpy as np
    from PIL import Image

    image = Image.fromarray(rgb, mode="RGB")
    mask_img = Image.fromarray((mask.astype("uint8") * 255), mode="L")
    result = np.asarray(lama(image, mask_img).convert("RGB"))
    target_height, target_width = rgb.shape[:2]
    return result[:target_height, :target_width]


def seam_metrics(
    overscan_rgb: "np.ndarray",
    source_width: int,
    source_height: int,
    pad_x: int,
    pad_y: int,
    overscan_mask: "np.ndarray",
) -> dict[str, float]:
    import numpy as np

    content_box = np.zeros(overscan_mask.shape, dtype=bool)
    content_box[pad_y:pad_y + source_height, pad_x:pad_x + source_width] = True
    inner_ring = content_box & ~erode_mask(content_box, 11)
    outer_ring = (dilate_mask(content_box, 11) & ~content_box) & overscan_mask

    if not inner_ring.any() or not outer_ring.any():
        return {
            "seam_color_gap": 1e3,
            "seam_grad_gap": 1e3,
            "seam_texture_gap": 1e3,
            "border_grad": 1e3,
            "score": -1e3,
        }

    seam_color_gap = color_distance(overscan_rgb[inner_ring], overscan_rgb[outer_ring])
    gray = overscan_rgb.astype("float32").mean(axis=2) / 255.0
    grad = gradient_map(gray)
    inner_grad = float(grad[inner_ring].mean())
    outer_grad = float(grad[outer_ring].mean())
    seam_grad_gap = abs(inner_grad - outer_grad)

    inner_std = float(overscan_rgb[inner_ring].astype("float32").std())
    outer_std = float(overscan_rgb[outer_ring].astype("float32").std())
    seam_texture_gap = abs(inner_std - outer_std)

    border_band = np.concatenate(
        [
            grad[0, :],
            grad[-1, :],
            grad[:, 0],
            grad[:, -1],
        ]
    )
    border_grad = float(border_band.mean())

    score = (
        12.0
        - seam_color_gap * 0.045
        - seam_grad_gap * 9.0
        - seam_texture_gap * 0.03
        - border_grad * 4.5
    )
    return {
        "seam_color_gap": round(float(seam_color_gap), 5),
        "seam_grad_gap": round(float(seam_grad_gap), 5),
        "seam_texture_gap": round(float(seam_texture_gap), 5),
        "border_grad": round(float(border_grad), 5),
        "score": round(float(score), 5),
    }


def make_debug_sheet(
    source_rgb: "np.ndarray",
    clean_plate_rgb: "np.ndarray",
    seeded_rgb: "np.ndarray",
    overscan_rgb: "np.ndarray",
    overscan_mask: "np.ndarray",
    out_path: Path,
) -> None:
    import numpy as np
    from PIL import Image

    accent = np.asarray([238, 88, 76], dtype=np.float32)
    overlay = seeded_rgb.copy()
    overlay[overscan_mask] = (0.7 * overlay[overscan_mask].astype(np.float32) + 0.3 * accent).astype("uint8")

    mask_rgb = np.repeat((overscan_mask.astype("uint8") * 255)[..., None], 3, axis=2)
    tiles = [
        Image.fromarray(source_rgb, mode="RGB"),
        Image.fromarray(clean_plate_rgb, mode="RGB"),
        Image.fromarray(seeded_rgb, mode="RGB"),
        Image.fromarray(overlay, mode="RGB"),
        Image.fromarray(overscan_rgb, mode="RGB"),
        Image.fromarray(mask_rgb, mode="RGB"),
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


def export_candidate(
    source_rgb: "np.ndarray",
    clean_plate_rgb: "np.ndarray",
    overscan_rgb: "np.ndarray",
    seeded_rgb: "np.ndarray",
    overscan_mask: "np.ndarray",
    out_dir: Path,
    key: str,
) -> dict[str, str]:
    from PIL import Image

    out_dir.mkdir(parents=True, exist_ok=True)
    candidate_dir = out_dir / "candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "candidate_path": str(candidate_dir / f"{key}.png"),
        "seeded_path": str(candidate_dir / f"{key}_seeded.png"),
        "mask_path": str(candidate_dir / f"{key}_mask.png"),
    }
    Image.fromarray(overscan_rgb, mode="RGB").save(paths["candidate_path"])
    Image.fromarray(seeded_rgb, mode="RGB").save(paths["seeded_path"])
    Image.fromarray((overscan_mask.astype("uint8") * 255), mode="L").save(paths["mask_path"])
    return paths


def build_overscan_candidate(
    lama: Any,
    clean_plate_rgb: "np.ndarray",
    overscan_pct: float,
    padding_mode: str,
) -> tuple["np.ndarray", "np.ndarray", "np.ndarray", int, int]:
    import numpy as np

    height, width = clean_plate_rgb.shape[:2]
    pad_x = max(48, int(math.ceil(width * overscan_pct / 200.0)))
    pad_y = max(48, int(math.ceil(height * overscan_pct / 200.0)))
    seeded_rgb = pad_canvas(clean_plate_rgb, pad_x, pad_y, padding_mode)
    overscan_mask = build_overscan_mask(height, width, pad_x, pad_y)
    overscan_rgb = run_lama(lama, seeded_rgb, overscan_mask)
    return overscan_rgb, seeded_rgb, overscan_mask, pad_x, pad_y


def run_for_sample(
    entry: dict[str, Any],
    sample_path: Path,
    analysis: dict[str, Any],
    out_dir: Path,
    lama: Any,
    padding_modes: list[str],
) -> dict[str, Any]:
    from PIL import Image

    source_rgb = load_rgb(sample_path)
    clean_plate_rgb = load_rgb(Path(entry["best"]["clean_plate_path"]))
    overscan_pct = float(analysis["recommended_overscan_pct"])

    best: dict[str, Any] | None = None
    candidate_records: list[dict[str, Any]] = []

    for padding_mode in padding_modes:
        started = time.perf_counter()
        overscan_rgb, seeded_rgb, overscan_mask, pad_x, pad_y = build_overscan_candidate(
            lama=lama,
            clean_plate_rgb=clean_plate_rgb,
            overscan_pct=overscan_pct,
            padding_mode=padding_mode,
        )
        runtime_sec = time.perf_counter() - started
        metrics = seam_metrics(
            overscan_rgb=overscan_rgb,
            source_width=clean_plate_rgb.shape[1],
            source_height=clean_plate_rgb.shape[0],
            pad_x=pad_x,
            pad_y=pad_y,
            overscan_mask=overscan_mask,
        )
        key = f"{padding_mode}_o{int(round(overscan_pct * 10))}"
        export_paths = export_candidate(
            source_rgb=source_rgb,
            clean_plate_rgb=clean_plate_rgb,
            overscan_rgb=overscan_rgb,
            seeded_rgb=seeded_rgb,
            overscan_mask=overscan_mask,
            out_dir=out_dir,
            key=key,
        )
        record = {
            "key": key,
            "padding_mode": padding_mode,
            "overscan_pct": round(float(overscan_pct), 2),
            "pad_x": pad_x,
            "pad_y": pad_y,
            "runtime_sec": round(float(runtime_sec), 5),
            "overscan_width": clean_plate_rgb.shape[1] + pad_x * 2,
            "overscan_height": clean_plate_rgb.shape[0] + pad_y * 2,
            **metrics,
            **export_paths,
        }
        candidate_records.append(record)
        if best is None or record["score"] > best["score"]:
            best = {**record, "overscan_rgb": overscan_rgb, "seeded_rgb": seeded_rgb, "overscan_mask": overscan_mask}

    assert best is not None
    out_dir.mkdir(parents=True, exist_ok=True)
    overscan_path = out_dir / "overscan_plate.png"
    overscan_mask_path = out_dir / "overscan_mask.png"
    seeded_path = out_dir / "overscan_seeded.png"
    debug_sheet_path = out_dir / "overscan_debug_sheet.png"
    layout_path = out_dir / "layout.json"

    Image.fromarray(best["overscan_rgb"], mode="RGB").save(overscan_path)
    Image.fromarray((best["overscan_mask"].astype("uint8") * 255), mode="L").save(overscan_mask_path)
    Image.fromarray(best["seeded_rgb"], mode="RGB").save(seeded_path)
    make_debug_sheet(
        source_rgb=source_rgb,
        clean_plate_rgb=clean_plate_rgb,
        seeded_rgb=best["seeded_rgb"],
        overscan_rgb=best["overscan_rgb"],
        overscan_mask=best["overscan_mask"],
        out_path=debug_sheet_path,
    )

    layout = build_layout_payload(
        sample_name=entry["sample"],
        source_width=clean_plate_rgb.shape[1],
        source_height=clean_plate_rgb.shape[0],
        overscan_width=best["overscan_width"],
        overscan_height=best["overscan_height"],
        overscan_pct=overscan_pct,
        analysis=analysis,
    )
    save_json(layout_path, layout)

    summary = {
        "sample": entry["sample"],
        "backend": entry["backend"],
        "clean_plate_path": entry["best"]["clean_plate_path"],
        "subject_rgba_path": entry["best"]["subject_rgba_path"],
        "recommended_motion": {
            "motion_type": layout["camera"]["motion_type"],
            "travel_x_pct": layout["camera"]["travel_x_pct"],
            "travel_y_pct": layout["camera"]["travel_y_pct"],
            "zoom": layout["camera"]["zoom"],
            "duration_sec": layout["camera"]["duration_sec"],
            "fps": layout["camera"]["fps"],
        },
        "best": {
            "key": best["key"],
            "padding_mode": best["padding_mode"],
            "overscan_pct": best["overscan_pct"],
            "pad_x": best["pad_x"],
            "pad_y": best["pad_y"],
            "overscan_width": best["overscan_width"],
            "overscan_height": best["overscan_height"],
            "runtime_sec": best["runtime_sec"],
            "overscan_plate_path": str(overscan_path),
            "overscan_mask_path": str(overscan_mask_path),
            "seeded_canvas_path": str(seeded_path),
            "debug_sheet_path": str(debug_sheet_path),
            "layout_path": str(layout_path),
            "score": best["score"],
            "seam_color_gap": best["seam_color_gap"],
            "seam_grad_gap": best["seam_grad_gap"],
            "seam_texture_gap": best["seam_texture_gap"],
            "border_grad": best["border_grad"],
        },
        "candidates": sorted(candidate_records, key=lambda item: item["score"], reverse=True),
    }
    save_json(out_dir / "overscan_summary.json", summary)
    return summary


def aggregate(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        grouped.setdefault(entry["backend"], []).append(entry)

    aggregate_payload: dict[str, dict[str, Any]] = {}
    for backend, rows in grouped.items():
        scores = [float(row["best"]["score"]) for row in rows]
        runtimes = [float(row["best"]["runtime_sec"]) for row in rows]
        aggregate_payload[backend] = {
            "entries": len(rows),
            "avg_score": round(sum(scores) / len(scores), 5),
            "avg_runtime_sec": round(sum(runtimes) / len(runtimes), 5),
            "padding_modes": sorted({row["best"]["padding_mode"] for row in rows}),
            "motion_types": sorted({row["recommended_motion"]["motion_type"] for row in rows}),
        }
    return aggregate_payload


def main() -> int:
    args = parse_args()
    sample_root = Path(args.sample_root).expanduser().resolve()
    lama_root = Path(args.lama_root).expanduser().resolve()
    sample_analysis_json = Path(args.sample_analysis_json).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    model_path = Path(args.model_path).expanduser().resolve()
    requested_backends = set(args.backends or [])
    padding_modes = args.padding_modes or ["reflect", "edge"]

    if not model_path.exists():
        raise FileNotFoundError(f"LaMa model not found: {model_path}")

    import os
    import torch
    from simple_lama_inpainting import SimpleLama

    device_name = choose_device(args.device)
    os.environ["LAMA_MODEL"] = str(model_path)
    lama = SimpleLama(device=torch.device(device_name))
    analysis_by_name = load_analysis_by_name(sample_analysis_json)
    lama_summary_path = lama_root / "lama_plate_bakeoff_summary.json"
    lama_summary = json.loads(lama_summary_path.read_text(encoding="utf-8"))

    summaries: list[dict[str, Any]] = []
    for entry in lama_summary["entries"]:
        if requested_backends and entry["backend"] not in requested_backends:
            continue
        sample_name = entry["sample"]
        sample_path = sample_root / sample_name
        if not sample_path.exists():
            matches = list(sample_root.glob(f"{Path(sample_name).stem}.*"))
            if not matches:
                continue
            sample_path = matches[0]
            sample_name = sample_path.name
        analysis = analysis_by_name.get(sample_name)
        if analysis is None:
            continue
        summaries.append(
            run_for_sample(
                entry=entry,
                sample_path=sample_path,
                analysis=analysis,
                out_dir=outdir / entry["backend"] / Path(sample_name).stem,
                lama=lama,
                padding_modes=padding_modes,
            )
        )

    summary = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "sample_root": str(sample_root),
        "lama_root": str(lama_root),
        "sample_analysis_json": str(sample_analysis_json),
        "outdir": str(outdir),
        "model_path": str(model_path),
        "device": device_name,
        "padding_modes": padding_modes,
        "aggregate_by_backend": aggregate(summaries),
        "entries": summaries,
    }
    save_json(outdir / "overscan_bakeoff_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
