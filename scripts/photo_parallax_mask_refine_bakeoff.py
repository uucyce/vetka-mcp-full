#!/usr/bin/env python3
"""Refine coarse masks with SAM 2 and compare candidates."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import time
from pathlib import Path
from typing import Any


SAMPLE_PRIORS: dict[str, dict[str, float]] = {
    "cassette-closeup": {"x": 0.50, "y": 0.51, "w": 0.48, "h": 0.56},
    "keyboard-hands": {"x": 0.51, "y": 0.58, "w": 0.60, "h": 0.52},
    "drone-portrait": {"x": 0.50, "y": 0.44, "w": 0.42, "h": 0.72},
    "hover-politsia": {"x": 0.53, "y": 0.46, "w": 0.46, "h": 0.48},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refine coarse masks with SAM 2.")
    parser.add_argument(
        "--sample-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/public/samples",
        help="Directory with original sample images.",
    )
    parser.add_argument(
        "--mask-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mask_bakeoff",
        help="Root directory of coarse mask outputs.",
    )
    parser.add_argument(
        "--outdir",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mask_refine_bakeoff",
        help="Output directory for refined masks and reports.",
    )
    parser.add_argument(
        "--hint-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/public/sample_hints",
        help="Optional directory with mask_hint PNGs.",
    )
    parser.add_argument(
        "--backend",
        action="append",
        dest="backends",
        help="Limit run to one or more depth backends.",
    )
    parser.add_argument(
        "--model-id",
        default="facebook/sam2-hiera-large",
        help="SAM 2 model checkpoint id.",
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cpu", "mps"],
        help="Inference device.",
    )
    return parser.parse_args()


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_mask(path: Path) -> "np.ndarray":
    import numpy as np
    from PIL import Image

    return np.asarray(Image.open(path).convert("L"), dtype=np.uint8) > 127


def load_rgb(path: Path) -> "np.ndarray":
    import numpy as np
    from PIL import Image

    return np.asarray(Image.open(path).convert("RGB"))


def load_rgba(path: Path) -> "np.ndarray":
    import numpy as np
    from PIL import Image

    return np.asarray(Image.open(path).convert("RGBA"))


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


def cleanup_mask(mask: "np.ndarray", anchor_mask: "np.ndarray") -> tuple["np.ndarray", int]:
    import numpy as np
    from collections import deque
    from PIL import Image, ImageFilter

    image = Image.fromarray((mask.astype("uint8") * 255), mode="L")
    image = image.filter(ImageFilter.MaxFilter(3))
    image = image.filter(ImageFilter.MinFilter(3))
    cleaned = np.asarray(image, dtype=np.uint8) > 127

    height, width = cleaned.shape
    scale = max(1, int(max(height, width) / 640))
    small_h = max(1, height // scale)
    small_w = max(1, width // scale)
    small_mask = np.asarray(
        Image.fromarray((cleaned.astype("uint8") * 255), mode="L").resize((small_w, small_h), Image.Resampling.NEAREST),
        dtype=np.uint8,
    ) > 0
    small_anchor = np.asarray(
        Image.fromarray((anchor_mask.astype("uint8") * 255), mode="L").resize((small_w, small_h), Image.Resampling.NEAREST),
        dtype=np.uint8,
    ) > 0

    visited = np.zeros_like(small_mask, dtype=bool)
    keep = np.zeros_like(small_mask, dtype=bool)
    neighbors = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    components: list[tuple[int, bool, list[tuple[int, int]]]] = []

    for y in range(small_h):
        for x in range(small_w):
            if visited[y, x] or not small_mask[y, x]:
                continue
            queue: deque[tuple[int, int]] = deque([(y, x)])
            visited[y, x] = True
            pixels: list[tuple[int, int]] = []
            touches_anchor = False
            while queue:
                cy, cx = queue.popleft()
                pixels.append((cy, cx))
                if small_anchor[cy, cx]:
                    touches_anchor = True
                for dy, dx in neighbors:
                    ny = cy + dy
                    nx = cx + dx
                    if ny < 0 or ny >= small_h or nx < 0 or nx >= small_w:
                        continue
                    if visited[ny, nx] or not small_mask[ny, nx]:
                        continue
                    visited[ny, nx] = True
                    queue.append((ny, nx))
            components.append((len(pixels), touches_anchor, pixels))

    if not components:
        return cleaned, 0

    selected = [component for component in components if component[1]]
    if not selected:
        selected = [max(components, key=lambda item: item[0])]
    area_limit = max(component[0] for component in components) * 0.14
    kept_components = 0
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


def erode_mask(mask: "np.ndarray", size: int) -> "np.ndarray":
    import numpy as np
    from PIL import Image, ImageFilter

    image = Image.fromarray((mask.astype("uint8") * 255), mode="L")
    eroded = np.asarray(image.filter(ImageFilter.MinFilter(size)), dtype=np.uint8) > 127
    return eroded if eroded.any() else mask


def dilate_mask(mask: "np.ndarray", size: int) -> "np.ndarray":
    import numpy as np
    from PIL import Image, ImageFilter

    image = Image.fromarray((mask.astype("uint8") * 255), mode="L")
    return np.asarray(image.filter(ImageFilter.MaxFilter(size)), dtype=np.uint8) > 127


def sample_points(region: "np.ndarray", count: int) -> list[list[float]]:
    import numpy as np

    ys, xs = np.where(region)
    if ys.size == 0:
        return []
    order = np.argsort(ys * region.shape[1] + xs)
    ys = ys[order]
    xs = xs[order]
    indices = np.linspace(0, xs.size - 1, num=min(count, xs.size), dtype=int)
    coords = []
    seen: set[tuple[int, int]] = set()
    for index in indices:
        point = (int(xs[index]), int(ys[index]))
        if point in seen:
            continue
        seen.add(point)
        coords.append([float(point[0]), float(point[1])])
    return coords


def resolve_hint_path(hint_root: Path, sample_name: str) -> Path | None:
    for suffix in ("png", "webp", "jpg", "jpeg"):
        candidate = hint_root / f"{sample_name}.{suffix}"
        if candidate.exists():
            return candidate
    return None


def build_hint_regions(hint_path: Path | None, coarse_mask: "np.ndarray") -> dict[str, "np.ndarray"] | None:
    import numpy as np

    if hint_path is None or not hint_path.exists():
        return None

    hint_rgba = load_rgba(hint_path)
    alpha = hint_rgba[..., 3] > 20
    rgb = hint_rgba[..., :3].astype(np.int16)
    red = alpha & (rgb[..., 0] > 170) & (rgb[..., 1] < 120) & (rgb[..., 2] < 120)
    blue = alpha & (rgb[..., 2] > 170) & (rgb[..., 0] < 120) & (rgb[..., 1] < 150)
    green = alpha & (rgb[..., 1] > 145) & (rgb[..., 0] < 160) & (rgb[..., 2] < 160)

    positive = red | (green & dilate_mask(coarse_mask, 25))
    negative = blue & ~dilate_mask(coarse_mask, 7)
    protect = green

    if not positive.any() and not negative.any() and not protect.any():
        return None

    return {
        "positive": positive,
        "negative": negative,
        "protect": protect,
        "hint_alpha": alpha,
    }


def expand_bbox(bbox: tuple[int, int, int, int], width: int, height: int, scale: float) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = bbox
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    bw = (x1 - x0 + 1) * scale
    bh = (y1 - y0 + 1) * scale
    ex0 = max(0, int(cx - bw / 2))
    ey0 = max(0, int(cy - bh / 2))
    ex1 = min(width - 1, int(cx + bw / 2))
    ey1 = min(height - 1, int(cy + bh / 2))
    return ex0, ey0, ex1, ey1


def bbox_to_mask(bbox: tuple[int, int, int, int], width: int, height: int) -> "np.ndarray":
    import numpy as np

    x0, y0, x1, y1 = bbox
    mask = np.zeros((height, width), dtype=bool)
    mask[y0 : y1 + 1, x0 : x1 + 1] = True
    return mask


def boundary_gradient(gray: "np.ndarray", mask: "np.ndarray") -> float:
    import numpy as np

    if not mask.any():
        return 0.0
    boundary = mask ^ erode_mask(mask, 5)
    if not boundary.any():
        return 0.0
    gx = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
    gy = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
    grad = gx + gy
    norm = max(1e-6, float(np.quantile(grad, 0.95)))
    return float(grad[boundary].mean() / norm)


def build_prompts(
    coarse_mask: "np.ndarray",
    hint_regions: dict[str, "np.ndarray"] | None = None,
) -> dict[str, "np.ndarray"]:
    import numpy as np

    bbox = mask_bbox(coarse_mask)
    if bbox is None:
        raise ValueError("Empty coarse mask.")
    height, width = coarse_mask.shape
    box = np.asarray([bbox[0], bbox[1], bbox[2], bbox[3]], dtype=np.float32)[None, :]

    positive_region = erode_mask(coarse_mask, 21)
    positive_points = sample_points(positive_region, 5)

    expanded_bbox = expand_bbox(bbox, width, height, 1.22)
    expanded_bbox_mask = bbox_to_mask(expanded_bbox, width, height)
    negative_region = expanded_bbox_mask & ~dilate_mask(coarse_mask, 35)
    negative_points = sample_points(negative_region, 6)

    point_coords = np.asarray(positive_points + negative_points, dtype=np.float32)
    point_labels = np.asarray([1] * len(positive_points) + [0] * len(negative_points), dtype=np.int32)

    hinted_positive_points: list[list[float]] = []
    hinted_negative_points: list[list[float]] = []
    if hint_regions is not None:
        hinted_positive_points = sample_points(hint_regions["positive"], 8)
        hinted_negative_points = sample_points(hint_regions["negative"], 8)

    hinted_coords = np.asarray(positive_points + hinted_positive_points + negative_points + hinted_negative_points, dtype=np.float32)
    hinted_labels = np.asarray(
        [1] * (len(positive_points) + len(hinted_positive_points))
        + [0] * (len(negative_points) + len(hinted_negative_points)),
        dtype=np.int32,
    )
    hint_bbox_mask = expanded_bbox_mask
    if hint_regions is not None and (hint_regions["positive"].any() or hint_regions["protect"].any()):
        hint_seed_mask = hint_regions["positive"] | hint_regions["protect"] | coarse_mask
        hint_bbox = mask_bbox(hint_seed_mask)
        if hint_bbox is not None:
            hint_bbox_mask = bbox_to_mask(expand_bbox(hint_bbox, width, height, 1.12), width, height)
            hint_box = np.asarray([hint_bbox[0], hint_bbox[1], hint_bbox[2], hint_bbox[3]], dtype=np.float32)[None, :]
        else:
            hint_box = box
    else:
        hint_box = box

    return {
        "box": box,
        "base_point_coords": point_coords,
        "base_point_labels": point_labels,
        "hinted_point_coords": hinted_coords,
        "hinted_point_labels": hinted_labels,
        "expanded_bbox_mask": expanded_bbox_mask,
        "hint_bbox_mask": hint_bbox_mask,
        "hint_box": hint_box,
    }


def candidate_metrics(
    mask: "np.ndarray",
    coarse_mask: "np.ndarray",
    gray: "np.ndarray",
    focus: "np.ndarray",
    expanded_focus: "np.ndarray",
    context_focus: "np.ndarray",
    expanded_bbox_mask: "np.ndarray",
    sam_score: float,
    kept_components: int,
    hint_regions: dict[str, "np.ndarray"] | None = None,
) -> dict[str, float]:
    import numpy as np

    area_ratio = float(mask.mean())
    coarse_iou = float((mask & coarse_mask).sum() / max(1, (mask | coarse_mask).sum()))
    coarse_recall = float((mask & coarse_mask).sum() / max(1, coarse_mask.sum()))
    coarse_precision = float((mask & coarse_mask).sum() / max(1, mask.sum()))
    focus_overlap = float(mask[focus].mean()) if focus.any() else 0.0
    expanded_overlap = float(mask[expanded_focus].mean()) if expanded_focus.any() else 0.0
    context_overlap = float(mask[context_focus].mean()) if context_focus.any() else 0.0
    outside_context = ~context_focus
    outside_context_ratio = float(mask[outside_context].mean()) if outside_context.any() else 0.0
    bbox_spill_ratio = float((mask & ~expanded_bbox_mask).mean())
    coarse_area_ratio = float(coarse_mask.mean())
    area_drift = abs(area_ratio - coarse_area_ratio)
    edge_score = boundary_gradient(gray, mask)

    bbox = mask_bbox(mask)
    anchor_bbox = mask_bbox(coarse_mask)
    bbox_alignment = bbox_iou(bbox, anchor_bbox)

    border = np.concatenate([mask[0, :], mask[-1, :], mask[:, 0], mask[:, -1]])
    border_ratio = float(border.mean())
    border_penalty = border_ratio**1.3
    spill_penalty = outside_context_ratio**1.1
    positive_hint_coverage = 0.0
    negative_hint_reject = 0.0
    protect_hint_coverage = 0.0
    hint_gain = 0.0
    if hint_regions is not None:
        if hint_regions["positive"].any():
            positive_hint_coverage = float(mask[hint_regions["positive"]].mean())
        if hint_regions["negative"].any():
            negative_hint_reject = float(1.0 - mask[hint_regions["negative"]].mean())
        if hint_regions["protect"].any():
            protect_hint_coverage = float(mask[hint_regions["protect"]].mean())
        hint_gain = positive_hint_coverage * 0.9 + negative_hint_reject * 0.9 + protect_hint_coverage * 0.55

    score = (
        sam_score * 3.4
        + coarse_iou * 2.5
        + coarse_precision * 1.2
        + coarse_recall * 0.8
        + focus_overlap * 1.1
        + expanded_overlap * 0.9
        + bbox_alignment * 1.2
        + edge_score * 1.4
        - area_drift * 2.2
        - spill_penalty * 3.0
        - bbox_spill_ratio * 3.0
        - border_penalty * 1.7
        - max(0, kept_components - 2) * 0.08
        + hint_gain * 1.4
    )

    return {
        "score": round(float(score), 5),
        "sam_score": round(float(sam_score), 5),
        "area_ratio": round(area_ratio, 5),
        "coarse_iou": round(coarse_iou, 5),
        "coarse_recall": round(coarse_recall, 5),
        "coarse_precision": round(coarse_precision, 5),
        "focus_overlap": round(focus_overlap, 5),
        "expanded_overlap": round(expanded_overlap, 5),
        "context_overlap": round(context_overlap, 5),
        "outside_context_ratio": round(outside_context_ratio, 5),
        "bbox_spill_ratio": round(bbox_spill_ratio, 5),
        "bbox_alignment": round(bbox_alignment, 5),
        "edge_score": round(edge_score, 5),
        "area_drift": round(area_drift, 5),
        "border_ratio": round(border_ratio, 5),
        "positive_hint_coverage": round(positive_hint_coverage, 5),
        "negative_hint_reject": round(negative_hint_reject, 5),
        "protect_hint_coverage": round(protect_hint_coverage, 5),
        "hint_gain": round(hint_gain, 5),
        "kept_components": kept_components,
    }


def build_overlay(source_path: Path, mask: "np.ndarray", color: tuple[int, int, int]) -> tuple["Image.Image", "Image.Image"]:
    from PIL import Image

    source = Image.open(source_path).convert("RGB")
    mask_image = Image.fromarray((mask.astype("uint8") * 255), mode="L")
    rgba = source.convert("RGBA")
    layer = Image.new("RGBA", source.size, (*color, 0))
    layer.putalpha(mask_image.point(lambda value: int(value * 0.40)))
    overlay = Image.alpha_composite(rgba, layer).convert("RGB")
    return source, overlay


def build_hint_overlay(source_path: Path, hint_regions: dict[str, "np.ndarray"] | None) -> "Image.Image" | None:
    from PIL import Image

    if hint_regions is None:
        return None
    source = Image.open(source_path).convert("RGBA")
    positive = Image.fromarray((hint_regions["positive"].astype("uint8") * 255), mode="L")
    negative = Image.fromarray((hint_regions["negative"].astype("uint8") * 255), mode="L")
    protect = Image.fromarray((hint_regions["protect"].astype("uint8") * 255), mode="L")
    for mask_image, color, alpha_scale in (
        (positive, (233, 78, 64), 0.55),
        (negative, (61, 121, 247), 0.55),
        (protect, (78, 194, 103), 0.45),
    ):
        layer = Image.new("RGBA", source.size, (*color, 0))
        layer.putalpha(mask_image.point(lambda value: int(value * alpha_scale)))
        source = Image.alpha_composite(source, layer)
    return source.convert("RGB")


def build_delta_mask(coarse_mask: "np.ndarray", refined_mask: "np.ndarray") -> "Image.Image":
    from PIL import Image
    import numpy as np

    canvas = np.zeros((*coarse_mask.shape, 3), dtype=np.uint8)
    removed = coarse_mask & ~refined_mask
    added = refined_mask & ~coarse_mask
    stable = coarse_mask & refined_mask
    canvas[stable] = (240, 236, 228)
    canvas[removed] = (233, 85, 79)
    canvas[added] = (64, 199, 173)
    return Image.fromarray(canvas, mode="RGB")


def make_sheet(tiles, out_path: Path, columns: int = 3) -> None:
    from PIL import Image

    width = max(tile.width for tile in tiles)
    height = max(tile.height for tile in tiles)
    rows = (len(tiles) + columns - 1) // columns
    sheet = Image.new("RGB", (width * columns, height * rows), "#060709")
    for index, tile in enumerate(tiles):
        x = (index % columns) * width
        y = (index // columns) * height
        if tile.size != (width, height):
            tile = tile.resize((width, height), Image.Resampling.LANCZOS)
        sheet.paste(tile, (x, y))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def resolve_device(requested: str) -> str:
    import torch

    if requested == "cpu":
        return "cpu"
    if requested == "mps":
        return "mps"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def run_for_sample(
    predictor,
    source_path: Path,
    sample_dir: Path,
    out_dir: Path,
    prior: dict[str, float],
    hint_root: Path,
) -> dict[str, Any]:
    import numpy as np
    from PIL import Image

    source_rgb = load_rgb(source_path).copy()
    gray = source_rgb.astype(np.float32).mean(axis=2) / 255.0
    coarse_mask = load_mask(sample_dir / "best_mask.png")
    hint_path = resolve_hint_path(hint_root, sample_dir.name)
    hint_regions = build_hint_regions(hint_path, coarse_mask)
    prompts = build_prompts(coarse_mask, hint_regions=hint_regions)
    box = prompts["box"]
    point_coords = prompts["base_point_coords"]
    point_labels = prompts["base_point_labels"]
    hinted_point_coords = prompts["hinted_point_coords"]
    hinted_point_labels = prompts["hinted_point_labels"]
    expanded_bbox_mask = prompts["expanded_bbox_mask"]
    hint_bbox_mask = prompts["hint_bbox_mask"]
    hint_box = prompts["hint_box"]
    focus, expanded_focus, context_focus = build_focus_masks(coarse_mask.shape[0], coarse_mask.shape[1], prior)

    positive_points = point_coords[point_labels == 1]
    positive_labels = point_labels[point_labels == 1]
    hinted_positive_points = hinted_point_coords[hinted_point_labels == 1]
    hinted_positive_labels = hinted_point_labels[hinted_point_labels == 1]

    start = time.perf_counter()
    predictor.set_image(source_rgb)
    masks_box_multi, scores_box_multi, logits_box_multi = predictor.predict(
        box=box[0],
        multimask_output=True,
        return_logits=True,
    )
    masks_box_pos, scores_box_pos, logits_box_pos = predictor.predict(
        box=box[0],
        point_coords=positive_points,
        point_labels=positive_labels,
        multimask_output=False,
        return_logits=True,
    )
    masks_box_posneg, scores_box_posneg, logits_box_posneg = predictor.predict(
        box=box[0],
        point_coords=point_coords,
        point_labels=point_labels,
        multimask_output=False,
        return_logits=True,
    )
    masks_box_posneg_refine, scores_box_posneg_refine, logits_box_posneg_refine = predictor.predict(
        box=box[0],
        point_coords=point_coords,
        point_labels=point_labels,
        mask_input=logits_box_posneg[:1],
        multimask_output=False,
        return_logits=True,
    )
    hinted_masks_box_posneg = hinted_scores_box_posneg = hinted_logits_box_posneg = None
    hinted_masks_box_posneg_refine = hinted_scores_box_posneg_refine = None
    if hint_regions is not None and hinted_point_coords.size > 0:
        hinted_masks_box_posneg, hinted_scores_box_posneg, hinted_logits_box_posneg = predictor.predict(
            box=hint_box[0],
            point_coords=hinted_point_coords,
            point_labels=hinted_point_labels,
            multimask_output=False,
            return_logits=True,
        )
        hinted_masks_box_posneg_refine, hinted_scores_box_posneg_refine, _ = predictor.predict(
            box=hint_box[0],
            point_coords=hinted_point_coords,
            point_labels=hinted_point_labels,
            mask_input=hinted_logits_box_posneg[:1],
            multimask_output=False,
            return_logits=True,
        )
    runtime_ms = (time.perf_counter() - start) * 1000

    candidate_dir = out_dir / "candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    candidates_report: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None

    candidate_specs: list[tuple[str, "np.ndarray", "np.ndarray"]] = [
        ("coarse_passthrough", np.asarray([coarse_mask], dtype=np.float32), np.asarray([0.0], dtype=np.float32)),
        ("sam_box_multi", masks_box_multi, scores_box_multi),
        ("sam_box_pos", masks_box_pos, scores_box_pos),
        ("sam_box_posneg", masks_box_posneg, scores_box_posneg),
        ("sam_box_posneg_refine", masks_box_posneg_refine, scores_box_posneg_refine),
    ]
    if hinted_masks_box_posneg is not None and hinted_scores_box_posneg is not None:
        candidate_specs.extend(
            [
                ("sam_hint_posneg", hinted_masks_box_posneg, hinted_scores_box_posneg),
                ("sam_hint_posneg_refine", hinted_masks_box_posneg_refine, hinted_scores_box_posneg_refine),
            ]
        )

    for family, masks, scores in candidate_specs:
        for index in range(masks.shape[0]):
            raw_mask = masks[index] > 0
            cleaned_mask, kept_components = cleanup_mask(raw_mask, coarse_mask)
            candidate_anchor = hint_bbox_mask if family.startswith("sam_hint_") else expanded_bbox_mask
            metrics = candidate_metrics(
                cleaned_mask,
                coarse_mask,
                gray,
                focus,
                expanded_focus,
                context_focus,
                candidate_anchor,
                float(scores[index]),
                kept_components,
                hint_regions=hint_regions,
            )
            key = f"{family}__m{index + 1}"
            mask_path = candidate_dir / f"{key}.png"
            Image.fromarray((cleaned_mask.astype("uint8") * 255), mode="L").save(mask_path)
            record = {
                "key": key,
                "family": family,
                "mask_path": str(mask_path),
                **metrics,
            }
            candidates_report.append(record)
            if best is None or record["score"] > best["score"]:
                best = {**record, "mask_array": cleaned_mask}

    assert best is not None

    source, coarse_overlay = build_overlay(source_path, coarse_mask, (255, 174, 45))
    _, refined_overlay = build_overlay(source_path, best["mask_array"], (64, 199, 173))
    hint_overlay = build_hint_overlay(source_path, hint_regions)
    coarse_mask_img = Image.fromarray((coarse_mask.astype("uint8") * 255), mode="L")
    refined_mask_img = Image.fromarray((best["mask_array"].astype("uint8") * 255), mode="L")
    delta_img = build_delta_mask(coarse_mask, best["mask_array"])

    coarse_mask_path = out_dir / "coarse_mask.png"
    refined_mask_path = out_dir / "refined_mask.png"
    coarse_overlay_path = out_dir / "coarse_overlay.png"
    refined_overlay_path = out_dir / "refined_overlay.png"
    delta_path = out_dir / "mask_delta.png"
    debug_sheet_path = out_dir / "refine_debug_sheet.png"
    hint_overlay_path = out_dir / "hint_overlay.png"
    guided_debug_sheet_path = out_dir / "guided_refine_debug_sheet.png"

    coarse_mask_img.save(coarse_mask_path)
    refined_mask_img.save(refined_mask_path)
    coarse_overlay.save(coarse_overlay_path)
    refined_overlay.save(refined_overlay_path)
    delta_img.save(delta_path)
    make_sheet(
        [source, coarse_overlay, refined_overlay, coarse_mask_img.convert("RGB"), refined_mask_img.convert("RGB"), delta_img],
        debug_sheet_path,
    )
    if hint_overlay is not None:
        hint_overlay.save(hint_overlay_path)
        make_sheet(
            [source, hint_overlay, coarse_overlay, refined_overlay, coarse_mask_img.convert("RGB"), refined_mask_img.convert("RGB"), delta_img],
            guided_debug_sheet_path,
        )

    candidates_report.sort(key=lambda item: item["score"], reverse=True)
    summary = {
        "sample": source_path.name,
        "backend": sample_dir.parent.name,
        "coarse_mask_root": str(sample_dir),
        "refine_model_id": getattr(predictor, "_hf_model_id", None),
        "runtime_ms": round(runtime_ms, 2),
        "prompt": {
            "box": box.tolist()[0],
            "positive_points": positive_points.tolist(),
            "negative_points": point_coords[point_labels == 0].tolist(),
            "hint_box": hint_box.tolist()[0],
            "hint_positive_points": hinted_positive_points.tolist(),
            "hint_negative_points": hinted_point_coords[hinted_point_labels == 0].tolist(),
        },
        "hint": {
            "path": str(hint_path) if hint_path is not None else None,
            "used": hint_regions is not None,
        },
        "best": {
            "key": best["key"],
            "family": best["family"],
            "score": best["score"],
            "mask_path": str(refined_mask_path),
            "coarse_mask_path": str(coarse_mask_path),
            "coarse_overlay_path": str(coarse_overlay_path),
            "refined_overlay_path": str(refined_overlay_path),
            "delta_path": str(delta_path),
            "debug_sheet_path": str(debug_sheet_path),
            "hint_overlay_path": str(hint_overlay_path) if hint_overlay is not None else None,
            "guided_debug_sheet_path": str(guided_debug_sheet_path) if hint_overlay is not None else None,
            "sam_score": best["sam_score"],
            "area_ratio": best["area_ratio"],
            "coarse_iou": best["coarse_iou"],
            "coarse_recall": best["coarse_recall"],
            "coarse_precision": best["coarse_precision"],
            "focus_overlap": best["focus_overlap"],
            "expanded_overlap": best["expanded_overlap"],
            "context_overlap": best["context_overlap"],
            "outside_context_ratio": best["outside_context_ratio"],
            "bbox_spill_ratio": best["bbox_spill_ratio"],
            "bbox_alignment": best["bbox_alignment"],
            "edge_score": best["edge_score"],
            "area_drift": best["area_drift"],
        },
        "candidates": candidates_report,
    }
    save_json(out_dir / "refine_summary.json", summary)
    return summary


def main() -> int:
    args = parse_args()
    sample_root = Path(args.sample_root).expanduser().resolve()
    mask_root = Path(args.mask_root).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    hint_root = Path(args.hint_root).expanduser().resolve()
    requested_backends = set(args.backends or [])

    device = resolve_device(args.device)

    from sam2.sam2_image_predictor import SAM2ImagePredictor

    predictor = SAM2ImagePredictor.from_pretrained(args.model_id, device=device)
    predictor._hf_model_id = args.model_id

    summaries: list[dict[str, Any]] = []
    for backend_dir in sorted(path for path in mask_root.iterdir() if path.is_dir()):
        if requested_backends and backend_dir.name not in requested_backends:
            continue
        for sample_dir in sorted(path for path in backend_dir.iterdir() if path.is_dir()):
            sample_name = sample_dir.name
            source_path = next(sample_root.glob(f"{sample_name}.*"), None)
            prior = SAMPLE_PRIORS.get(sample_name)
            if source_path is None or prior is None:
                continue
            summaries.append(
                run_for_sample(
                    predictor=predictor,
                    source_path=source_path,
                    sample_dir=sample_dir,
                    out_dir=outdir / backend_dir.name / sample_name,
                    prior=prior,
                    hint_root=hint_root,
                )
            )

    summary = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "sample_root": str(sample_root),
        "mask_root": str(mask_root),
        "hint_root": str(hint_root),
        "outdir": str(outdir),
        "refine_model_id": args.model_id,
        "device": device,
        "entries": summaries,
    }
    save_json(outdir / "mask_refine_bakeoff_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
