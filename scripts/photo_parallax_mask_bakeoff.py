#!/usr/bin/env python3
"""Generate and score coarse foreground masks from depth bake-off outputs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from collections import deque
from pathlib import Path
from typing import Any


SAMPLE_PRIORS: dict[str, dict[str, float]] = {
    "cassette-closeup": {"x": 0.50, "y": 0.51, "w": 0.48, "h": 0.56, "feather": 0.16},
    "keyboard-hands": {"x": 0.51, "y": 0.58, "w": 0.60, "h": 0.52, "feather": 0.18},
    "drone-portrait": {"x": 0.50, "y": 0.44, "w": 0.42, "h": 0.72, "feather": 0.18},
    "hover-politsia": {"x": 0.53, "y": 0.46, "w": 0.46, "h": 0.48, "feather": 0.14},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build coarse mask bake-off from depth outputs.")
    parser.add_argument(
        "--depth-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/depth_bakeoff",
        help="Root directory of depth bake-off outputs.",
    )
    parser.add_argument(
        "--sample-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/public/samples",
        help="Directory with original sample images.",
    )
    parser.add_argument(
        "--outdir",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mask_bakeoff",
        help="Output directory for generated masks and reports.",
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


def load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_depth(path: Path) -> "np.ndarray":
    import numpy as np
    from PIL import Image

    return np.asarray(Image.open(path), dtype=np.float32) / 65535.0


def build_box_mask(height: int, width: int, prior: dict[str, float], scale: float) -> "np.ndarray":
    import numpy as np

    x0 = max(0, int((prior["x"] - prior["w"] * scale / 2) * width))
    x1 = min(width, int((prior["x"] + prior["w"] * scale / 2) * width))
    y0 = max(0, int((prior["y"] - prior["h"] * scale / 2) * height))
    y1 = min(height, int((prior["y"] + prior["h"] * scale / 2) * height))
    mask = np.zeros((height, width), dtype=bool)
    mask[y0:y1, x0:x1] = True
    return mask


def build_focus_masks(height: int, width: int, prior: dict[str, float]) -> tuple["np.ndarray", "np.ndarray", "np.ndarray"]:
    focus = build_box_mask(height, width, prior, 1.0)
    expanded = build_box_mask(height, width, prior, 1.32)
    context = build_box_mask(height, width, prior, 1.72)
    return focus, expanded, context


def otsu_threshold(values: "np.ndarray") -> float:
    import numpy as np

    clipped = values.clip(0, 1)
    hist, bin_edges = np.histogram(clipped, bins=256, range=(0.0, 1.0))
    total = hist.sum()
    if total <= 0:
        return 0.5
    cumulative = np.cumsum(hist)
    cumulative_mean = np.cumsum(hist * np.arange(256))
    global_mean = cumulative_mean[-1]
    numerator = (global_mean * cumulative - cumulative_mean) ** 2
    denominator = cumulative * (total - cumulative)
    denominator[denominator == 0] = 1
    score = numerator / denominator
    best_index = int(np.argmax(score))
    return float(bin_edges[min(best_index + 1, len(bin_edges) - 1)])


def kmeans_thresholds(values: "np.ndarray", clusters: int = 3) -> list[float]:
    import numpy as np

    x = values.reshape(-1).clip(0, 1)
    quantiles = np.linspace(0.18, 0.82, clusters)
    centers = np.quantile(x, quantiles).astype(np.float32)
    for _ in range(12):
        distances = np.abs(x[:, None] - centers[None, :])
        labels = distances.argmin(axis=1)
        new_centers = []
        for index in range(clusters):
            selected = x[labels == index]
            new_centers.append(float(selected.mean()) if selected.size else float(centers[index]))
        new_centers = np.asarray(new_centers, dtype=np.float32)
        if np.allclose(new_centers, centers):
            break
        centers = new_centers
    return sorted(float(value) for value in centers)


def filter_components(mask: "np.ndarray", anchor_mask: "np.ndarray") -> tuple["np.ndarray", int]:
    import numpy as np
    from PIL import Image

    height, width = mask.shape
    scale = max(1, int(max(height, width) / 640))
    small_h = max(1, height // scale)
    small_w = max(1, width // scale)
    small_mask = np.asarray(
        Image.fromarray((mask.astype("uint8") * 255), mode="L").resize((small_w, small_h), Image.Resampling.NEAREST),
        dtype=np.uint8,
    ) > 0
    small_focus = np.asarray(
        Image.fromarray((anchor_mask.astype("uint8") * 255), mode="L").resize((small_w, small_h), Image.Resampling.NEAREST),
        dtype=np.uint8,
    ) > 0

    visited = np.zeros_like(small_mask, dtype=bool)
    keep = np.zeros_like(small_mask, dtype=bool)
    components: list[tuple[int, bool, list[tuple[int, int]]]] = []
    neighbors = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    for y in range(small_h):
        for x in range(small_w):
            if visited[y, x] or not small_mask[y, x]:
                continue
            queue: deque[tuple[int, int]] = deque([(y, x)])
            visited[y, x] = True
            pixels: list[tuple[int, int]] = []
            touches_focus = False
            while queue:
                cy, cx = queue.popleft()
                pixels.append((cy, cx))
                if small_focus[cy, cx]:
                    touches_focus = True
                for dy, dx in neighbors:
                    ny = cy + dy
                    nx = cx + dx
                    if ny < 0 or ny >= small_h or nx < 0 or nx >= small_w:
                        continue
                    if visited[ny, nx] or not small_mask[ny, nx]:
                        continue
                    visited[ny, nx] = True
                    queue.append((ny, nx))
            components.append((len(pixels), touches_focus, pixels))

    if not components:
        return mask, 0

    kept_components = 0
    focus_components = [component for component in components if component[1]]
    selected = focus_components if focus_components else [max(components, key=lambda item: item[0])]
    area_limit = max(component[0] for component in components) * 0.18

    for area, _, pixels in selected:
        if area < area_limit:
            continue
        kept_components += 1
        for py, px in pixels:
            keep[py, px] = True

    if kept_components == 0:
        area, _, pixels = max(components, key=lambda item: item[0])
        kept_components = 1
        for py, px in pixels:
            keep[py, px] = True

    full = np.asarray(
        Image.fromarray((keep.astype("uint8") * 255), mode="L").resize((width, height), Image.Resampling.NEAREST),
        dtype=np.uint8,
    ) > 0
    return full, kept_components


def connected_from_seed(seed_mask: "np.ndarray", support_mask: "np.ndarray") -> tuple["np.ndarray", int]:
    return filter_components(support_mask, seed_mask)


def cleanup_mask(mask: "np.ndarray", anchor_mask: "np.ndarray") -> tuple["np.ndarray", int]:
    import numpy as np
    from PIL import Image, ImageFilter

    image = Image.fromarray((mask.astype("uint8") * 255), mode="L")
    image = image.filter(ImageFilter.MaxFilter(5))
    image = image.filter(ImageFilter.MinFilter(5))
    image = image.filter(ImageFilter.MinFilter(3))
    image = image.filter(ImageFilter.MaxFilter(3))
    cleaned = np.asarray(image, dtype=np.uint8) > 127
    return filter_components(cleaned, anchor_mask)


def mask_bbox(mask: "np.ndarray") -> tuple[int, int, int, int] | None:
    import numpy as np

    ys, xs = np.where(mask)
    if ys.size == 0 or xs.size == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def bbox_iou(a: tuple[int, int, int, int] | None, b: tuple[int, int, int, int] | None) -> float:
    if a is None or b is None:
        return 0.0
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0 = max(ax0, bx0)
    iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)
    if ix1 < ix0 or iy1 < iy0:
        return 0.0
    intersection = (ix1 - ix0 + 1) * (iy1 - iy0 + 1)
    area_a = (ax1 - ax0 + 1) * (ay1 - ay0 + 1)
    area_b = (bx1 - bx0 + 1) * (by1 - by0 + 1)
    union = max(1, area_a + area_b - intersection)
    return float(intersection / union)


def mask_centroid(mask: "np.ndarray") -> tuple[float, float] | None:
    import numpy as np

    ys, xs = np.where(mask)
    if ys.size == 0 or xs.size == 0:
        return None
    return float(xs.mean()), float(ys.mean())


def score_mask(
    mask: "np.ndarray",
    oriented_depth: "np.ndarray",
    orientation_contrast: float,
    focus: "np.ndarray",
    expanded_focus: "np.ndarray",
    context_focus: "np.ndarray",
    prior: dict[str, float],
    kept_components: int,
) -> dict[str, float]:
    import numpy as np

    area_ratio = float(mask.mean())
    focus_overlap = float(mask[focus].mean()) if focus.any() else 0.0
    expanded_overlap = float(mask[expanded_focus].mean()) if expanded_focus.any() else 0.0
    context_overlap = float(mask[context_focus].mean()) if context_focus.any() else 0.0
    outside_context = ~context_focus
    outside_context_ratio = float(mask[outside_context].mean()) if outside_context.any() else 0.0
    border = np.concatenate([mask[0, :], mask[-1, :], mask[:, 0], mask[:, -1]])
    border_ratio = float(border.mean())

    bbox = mask_bbox(mask)
    if bbox is None:
        bbox_density = 0.0
    else:
        x0, y0, x1, y1 = bbox
        bbox_area = max(1, (x1 - x0 + 1) * (y1 - y0 + 1))
        bbox_density = float(mask[y0 : y1 + 1, x0 : x1 + 1].sum() / bbox_area)

    focus_bbox = mask_bbox(focus)
    expanded_bbox = mask_bbox(expanded_focus)
    focus_bbox_iou = bbox_iou(bbox, expanded_bbox)

    centroid = mask_centroid(mask)
    if centroid is None:
        center_distance = 1.0
    else:
        cx, cy = centroid
        px = prior["x"] * mask.shape[1]
        py = prior["y"] * mask.shape[0]
        diagonal = max(1.0, float((mask.shape[0] ** 2 + mask.shape[1] ** 2) ** 0.5))
        center_distance = (((cx - px) ** 2 + (cy - py) ** 2) ** 0.5) / diagonal

    outer_ring = context_focus & ~mask
    if mask.any() and outer_ring.any():
        depth_separation = float(np.median(oriented_depth[mask]) - np.median(oriented_depth[outer_ring]))
    else:
        depth_separation = 0.0

    area_target = max(0.10, float(focus.mean()) * 1.15)
    min_area = max(0.06, area_target * 0.55)
    max_area = min(0.58, float(context_focus.mean()) * 0.88)
    if area_ratio < min_area:
        area_penalty = min_area - area_ratio
    elif area_ratio > max_area:
        area_penalty = area_ratio - max_area
    else:
        area_penalty = abs(area_ratio - area_target) * 0.35

    border_penalty = border_ratio ** 1.35
    outside_context_penalty = outside_context_ratio ** 1.12
    component_penalty = max(0, kept_components - 2) * 0.08
    score = (
        focus_overlap * 3.7
        + expanded_overlap * 1.2
        + context_overlap * 0.8
        + bbox_density * 1.1
        + focus_bbox_iou * 2.2
        + max(0.0, depth_separation) * 2.2
        + max(0.0, orientation_contrast) * 2.4
        - border_penalty * 2.7
        - area_penalty * 3.8
        - outside_context_penalty * 4.2
        - center_distance * 1.4
        - max(0.0, -orientation_contrast) * 2.8
        - component_penalty
    )

    return {
        "score": round(float(score), 5),
        "area_ratio": round(area_ratio, 5),
        "focus_overlap": round(focus_overlap, 5),
        "expanded_overlap": round(expanded_overlap, 5),
        "context_overlap": round(context_overlap, 5),
        "outside_context_ratio": round(outside_context_ratio, 5),
        "border_ratio": round(border_ratio, 5),
        "bbox_density": round(bbox_density, 5),
        "focus_bbox_iou": round(focus_bbox_iou, 5),
        "depth_separation": round(depth_separation, 5),
        "orientation_contrast": round(orientation_contrast, 5),
        "center_distance": round(center_distance, 5),
        "area_penalty": round(area_penalty, 5),
        "kept_components": kept_components,
    }


def build_overlay(source_path: Path, mask: "np.ndarray") -> tuple["Image.Image", "Image.Image"]:
    from PIL import Image

    source = Image.open(source_path).convert("RGB")
    mask_image = Image.fromarray((mask.astype("uint8") * 255), mode="L")
    rgba = source.convert("RGBA")
    red = Image.new("RGBA", source.size, (255, 74, 74, 0))
    red.putalpha(mask_image.point(lambda value: int(value * 0.42)))
    overlay = Image.alpha_composite(rgba, red).convert("RGB")
    return source, overlay


def make_sheet(source, depth_preview_path: Path, best_mask, best_overlay, out_path: Path) -> None:
    from PIL import Image, ImageOps

    depth_preview = Image.open(depth_preview_path).convert("RGB")
    mask_rgb = ImageOps.colorize(best_mask, black="#050505", white="#f4efe7")
    tiles = [source, depth_preview, mask_rgb, best_overlay]
    width = max(tile.width for tile in tiles)
    height = max(tile.height for tile in tiles)
    sheet = Image.new("RGB", (width * 2, height * 2), "#060709")
    for index, tile in enumerate(tiles):
        x = (index % 2) * width
        y = (index // 2) * height
        if tile.size != (width, height):
            tile = tile.resize((width, height), Image.Resampling.LANCZOS)
        sheet.paste(tile, (x, y))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def generate_candidates(
    depth: "np.ndarray",
    focus: "np.ndarray",
    expanded_focus: "np.ndarray",
    context_focus: "np.ndarray",
) -> list[dict[str, Any]]:
    import numpy as np

    candidates: list[dict[str, Any]] = []
    for polarity_name, oriented in [("direct", depth), ("inverted", 1.0 - depth)]:
        focus_values = oriented[focus]
        ring_mask = context_focus & ~expanded_focus
        if ring_mask.any():
            orientation_contrast = float(np.median(oriented[focus]) - np.median(oriented[ring_mask]))
        else:
            orientation_contrast = 0.0
        threshold = otsu_threshold(oriented)
        candidates.append(
            {
                "method": "otsu",
                "variant": polarity_name,
                "threshold": round(threshold, 6),
                "mask": oriented >= threshold,
                "anchor_mask": expanded_focus,
                "oriented_depth": oriented,
                "orientation_contrast": orientation_contrast,
            }
        )
        for quantile in [0.65, 0.72, 0.80]:
            threshold = float(np.quantile(oriented, quantile))
            candidates.append(
                {
                    "method": "percentile",
                    "variant": f"{polarity_name}-q{int(quantile * 100)}",
                    "threshold": round(threshold, 6),
                    "mask": oriented >= threshold,
                    "anchor_mask": expanded_focus,
                    "oriented_depth": oriented,
                    "orientation_contrast": orientation_contrast,
                }
            )

        centers = kmeans_thresholds(oriented, clusters=3)
        for keep_from in [0, 1]:
            threshold = centers[keep_from]
            candidates.append(
                {
                    "method": "kmeans",
                    "variant": f"{polarity_name}-c{keep_from + 1}",
                    "threshold": round(threshold, 6),
                    "mask": oriented >= threshold,
                    "anchor_mask": expanded_focus,
                    "oriented_depth": oriented,
                    "orientation_contrast": orientation_contrast,
                }
            )

        for quantile in [0.50, 0.58, 0.66]:
            threshold = float(np.quantile(focus_values, quantile))
            candidates.append(
                {
                    "method": "focus-percentile",
                    "variant": f"{polarity_name}-q{int(quantile * 100)}",
                    "threshold": round(threshold, 6),
                    "mask": context_focus & (oriented >= threshold),
                    "anchor_mask": focus,
                    "oriented_depth": oriented,
                    "orientation_contrast": orientation_contrast,
                }
            )

        for support_q, seed_q in [(0.48, 0.72), (0.54, 0.80), (0.60, 0.86)]:
            support_threshold = float(np.quantile(focus_values, support_q))
            seed_threshold = float(np.quantile(focus_values, seed_q))
            seed = focus & (oriented >= seed_threshold)
            if not seed.any():
                continue
            support = context_focus & (oriented >= support_threshold)
            connected, _ = connected_from_seed(seed, support)
            candidates.append(
                {
                    "method": "seed-grow",
                    "variant": f"{polarity_name}-s{int(seed_q * 100)}-g{int(support_q * 100)}",
                    "threshold": round(support_threshold, 6),
                    "seed_threshold": round(seed_threshold, 6),
                    "mask": connected,
                    "anchor_mask": seed,
                    "oriented_depth": oriented,
                    "orientation_contrast": orientation_contrast,
                }
            )
    return candidates


def run_for_backend_sample(
    source_path: Path,
    sample_dir: Path,
    out_dir: Path,
    prior: dict[str, float],
) -> dict[str, Any]:
    import numpy as np
    from PIL import Image

    depth_path = sample_dir / "depth_master_16.png"
    depth_preview_path = sample_dir / "depth_preview.png"
    report = load_report(sample_dir / "report.json")
    depth = load_depth(depth_path)
    focus, expanded_focus, context_focus = build_focus_masks(depth.shape[0], depth.shape[1], prior)

    best: dict[str, Any] | None = None
    candidates_report: list[dict[str, Any]] = []
    candidate_dir = out_dir / "candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)

    for candidate in generate_candidates(depth, focus, expanded_focus, context_focus):
        cleaned_mask, kept_components = cleanup_mask(candidate["mask"], candidate["anchor_mask"])
        metrics = score_mask(
            cleaned_mask,
            candidate["oriented_depth"],
            candidate["orientation_contrast"],
            focus,
            expanded_focus,
            context_focus,
            prior,
            kept_components,
        )
        key = f"{candidate['method']}__{candidate['variant']}"
        mask_path = candidate_dir / f"{key}.png"
        Image.fromarray((cleaned_mask.astype("uint8") * 255), mode="L").save(mask_path)

        record = {
            "key": key,
            "method": candidate["method"],
            "variant": candidate["variant"],
            "threshold": candidate["threshold"],
            "seed_threshold": candidate.get("seed_threshold"),
            "mask_path": str(mask_path),
            **metrics,
        }
        candidates_report.append(record)
        if best is None or record["score"] > best["score"]:
            best = {**record, "mask_array": cleaned_mask}

    assert best is not None
    source, overlay = build_overlay(source_path, best["mask_array"])
    best_mask = Image.fromarray((best["mask_array"].astype("uint8") * 255), mode="L")
    best_mask_path = out_dir / "best_mask.png"
    best_overlay_path = out_dir / "best_overlay.png"
    best_mask.save(best_mask_path)
    overlay.save(best_overlay_path)
    make_sheet(source, depth_preview_path, best_mask, overlay, out_dir / "mask_debug_sheet.png")

    candidates_report.sort(key=lambda item: item["score"], reverse=True)
    summary = {
        "sample": report["sample"],
        "backend": report["backend"],
        "model_id": report["model_id"],
        "source_width": report["source_width"],
        "source_height": report["source_height"],
        "depth_preview_path": str(depth_preview_path),
        "best": {
            "key": best["key"],
            "method": best["method"],
            "variant": best["variant"],
            "threshold": best["threshold"],
            "score": best["score"],
            "mask_path": str(best_mask_path),
            "overlay_path": str(best_overlay_path),
            "debug_sheet_path": str(out_dir / "mask_debug_sheet.png"),
            "area_ratio": best["area_ratio"],
            "focus_overlap": best["focus_overlap"],
            "expanded_overlap": best["expanded_overlap"],
            "context_overlap": best["context_overlap"],
            "outside_context_ratio": best["outside_context_ratio"],
            "border_ratio": best["border_ratio"],
            "bbox_density": best["bbox_density"],
            "focus_bbox_iou": best["focus_bbox_iou"],
            "depth_separation": best["depth_separation"],
            "orientation_contrast": best["orientation_contrast"],
            "center_distance": best["center_distance"],
            "kept_components": best["kept_components"],
        },
        "candidates": candidates_report,
    }
    save_json(out_dir / "mask_summary.json", summary)
    return summary


def main() -> int:
    args = parse_args()
    depth_root = Path(args.depth_root).expanduser().resolve()
    sample_root = Path(args.sample_root).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    requested_backends = set(args.backends or [])

    summaries: list[dict[str, Any]] = []
    for backend_dir in sorted(path for path in depth_root.iterdir() if path.is_dir()):
        if requested_backends and backend_dir.name not in requested_backends:
            continue
        for sample_dir in sorted(path for path in backend_dir.iterdir() if path.is_dir()):
            sample_name = sample_dir.name
            source_path = next(sample_root.glob(f"{sample_name}.*"), None)
            if source_path is None:
                continue
            prior = SAMPLE_PRIORS.get(sample_name)
            if prior is None:
                continue
            summaries.append(
                run_for_backend_sample(
                    source_path=source_path,
                    sample_dir=sample_dir,
                    out_dir=outdir / backend_dir.name / sample_name,
                    prior=prior,
                )
            )

    summary = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "depth_root": str(depth_root),
        "sample_root": str(sample_root),
        "outdir": str(outdir),
        "entries": summaries,
    }
    save_json(outdir / "mask_bakeoff_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
