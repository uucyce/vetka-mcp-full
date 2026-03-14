#!/usr/bin/env python3
"""Plan three-layer parallax assets from depth, subject matte, and clean plate."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from photo_parallax_subject_plate_bakeoff import checkerboard, save_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build 3-layer planning assets for flagged parallax scenes.")
    parser.add_argument(
        "--render-review-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_review",
        help="Root directory with render review summary.",
    )
    parser.add_argument(
        "--lama-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/lama_plate_bakeoff",
        help="Root directory with LaMa plate summary.",
    )
    parser.add_argument(
        "--depth-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/depth_bakeoff",
        help="Root directory with depth bake-off summary.",
    )
    parser.add_argument(
        "--outdir",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/three_layer_plan",
        help="Output directory for 3-layer planning artifacts.",
    )
    parser.add_argument(
        "--status",
        action="append",
        dest="statuses",
        choices=("caution", "needs_3_layer"),
        help="Only plan selected review statuses.",
    )
    parser.add_argument(
        "--backend",
        action="append",
        dest="backends",
        help="Limit run to one or more depth backends.",
    )
    return parser.parse_args()


def load_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_rgb(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"))


def load_rgba(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA"))


def load_mask(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("L"), dtype=np.uint8) > 127


def load_depth_u16(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path), dtype=np.uint16)


def map_lama_entries(summary: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(entry["backend"], entry["sample"]): entry for entry in summary["entries"]}


def map_depth_samples(summary: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    mapped: dict[tuple[str, str], dict[str, Any]] = {}
    for report in summary["reports"]:
        backend = report["backend"]
        for sample in report["samples"]:
            mapped[(backend, sample["sample"])] = sample
    return mapped


def normalize_depth(depth_u16: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
    depth = depth_u16.astype(np.float32)
    p2 = float(np.percentile(depth, 2))
    p98 = float(np.percentile(depth, 98))
    if p98 <= p2:
        p98 = p2 + 1.0
    normalized = np.clip((depth - p2) / (p98 - p2), 0.0, 1.0)
    return normalized, {"p2": round(p2, 3), "p98": round(p98, 3)}


def infer_near_map(depth_norm: np.ndarray, subject_mask: np.ndarray) -> tuple[np.ndarray, str, dict[str, float]]:
    outside = ~subject_mask
    subject_mean = float(depth_norm[subject_mask].mean()) if subject_mask.any() else 0.5
    outside_mean = float(depth_norm[outside].mean()) if outside.any() else 0.5
    if subject_mean >= outside_mean:
        near_map = depth_norm
        polarity = "bright_near"
    else:
        near_map = 1.0 - depth_norm
        polarity = "dark_near"
    return near_map, polarity, {
        "subject_mean": round(subject_mean, 5),
        "outside_mean": round(outside_mean, 5),
    }


def two_means_threshold(values: np.ndarray) -> tuple[float, float, float]:
    flat = values.reshape(-1).astype(np.float32)
    if flat.size == 0:
        return 0.5, 0.0, 1.0
    c1 = float(np.percentile(flat, 35))
    c2 = float(np.percentile(flat, 75))
    for _ in range(8):
        split = (c1 + c2) / 2.0
        lower = flat[flat < split]
        upper = flat[flat >= split]
        if lower.size:
            c1 = float(lower.mean())
        if upper.size:
            c2 = float(upper.mean())
    return float((c1 + c2) / 2.0), float(c1), float(c2)


def clean_binary(mask: np.ndarray, kernel_size: int = 9) -> np.ndarray:
    import cv2

    kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
    cleaned = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
    return cleaned.astype(bool)


def keep_large_components(mask: np.ndarray, min_area: int) -> np.ndarray:
    import cv2

    if not mask.any():
        return mask
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    out = np.zeros_like(mask, dtype=bool)
    for label in range(1, num_labels):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area >= min_area:
            out |= labels == label
    return out if out.any() else mask


def layer_rgba(rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    alpha = (mask.astype(np.uint8) * 255)[..., None]
    return np.concatenate([rgb, alpha], axis=2)


def composite_preview(rgba: np.ndarray) -> np.ndarray:
    alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
    board = checkerboard(rgba.shape[1], rgba.shape[0]).astype(np.float32)
    out = rgba[:, :, :3].astype(np.float32) * alpha + board * (1.0 - alpha)
    return out.clip(0, 255).astype(np.uint8)


def tinted_overlay(base_rgb: np.ndarray, masks: list[tuple[np.ndarray, tuple[int, int, int]]]) -> np.ndarray:
    canvas = base_rgb.astype(np.float32).copy()
    for mask, color in masks:
        if not mask.any():
            continue
        accent = np.asarray(color, dtype=np.float32)
        canvas[mask] = canvas[mask] * 0.45 + accent * 0.55
    return canvas.clip(0, 255).astype(np.uint8)


def depth_to_preview(depth_norm: np.ndarray, near_map: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    depth_bw = (depth_norm * 255.0).clip(0, 255).astype(np.uint8)
    near_bw = (near_map * 255.0).clip(0, 255).astype(np.uint8)
    return depth_bw, near_bw


def make_sheet(
    source_rgb: np.ndarray,
    depth_bw: np.ndarray,
    near_bw: np.ndarray,
    overlay_rgb: np.ndarray,
    mid_preview: np.ndarray,
    far_preview: np.ndarray,
    title: str,
    subtitle: str,
) -> Image.Image:
    font = ImageFont.load_default()
    tile_w = 420
    tile_h = 260
    margin = 20
    canvas = Image.new("RGB", (margin * 4 + tile_w * 3, margin * 4 + 40 + tile_h * 2), "#111111")
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, margin), title, fill="#f7f3ea", font=font)
    draw.text((margin, margin + 16), subtitle, fill="#b0aa9b", font=font)

    tiles = [
        (Image.fromarray(source_rgb, mode="RGB"), "source"),
        (Image.fromarray(depth_bw, mode="L").convert("RGB"), "depth bw"),
        (Image.fromarray(near_bw, mode="L").convert("RGB"), "near map"),
        (Image.fromarray(overlay_rgb, mode="RGB"), "layer overlay"),
        (Image.fromarray(mid_preview, mode="RGB"), "midground rgba"),
        (Image.fromarray(far_preview, mode="RGB"), "background far rgba"),
    ]
    for index, (image, label) in enumerate(tiles):
        row = index // 3
        col = index % 3
        x = margin + col * (tile_w + margin)
        y = margin * 2 + 30 + row * (tile_h + margin)
        fit = image.copy()
        fit.thumbnail((tile_w, tile_h))
        tile = Image.new("RGB", (tile_w, tile_h), "#202020")
        paste_x = (tile_w - fit.width) // 2
        paste_y = (tile_h - fit.height) // 2
        tile.paste(fit, (paste_x, paste_y))
        canvas.paste(tile, (x, y))
        draw.text((x, y + tile_h + 4), label, fill="#f7f3ea", font=font)
    return canvas


def area_ratio(mask: np.ndarray) -> float:
    return round(float(mask.mean()), 5)


def build_layer_masks(near_map: np.ndarray, subject_mask: np.ndarray, status: str) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    outside = ~subject_mask
    values = near_map[outside]
    threshold, c1, c2 = two_means_threshold(values)

    if status == "needs_3_layer":
        threshold = min(0.82, threshold + 0.03)
    else:
        threshold = min(0.84, threshold + 0.06)

    raw_midground = outside & (near_map >= threshold)
    cleaned_midground = clean_binary(raw_midground, kernel_size=9)
    cleaned_midground = keep_large_components(cleaned_midground, min_area=max(1024, int(subject_mask.size * 0.006)))

    if cleaned_midground.mean() < 0.05:
        fallback_threshold = float(np.percentile(values, 72))
        cleaned_midground = outside & (near_map >= fallback_threshold)
        cleaned_midground = clean_binary(cleaned_midground, kernel_size=7)
        cleaned_midground = keep_large_components(cleaned_midground, min_area=max(900, int(subject_mask.size * 0.004)))
        threshold = fallback_threshold

    background_far = outside & ~cleaned_midground
    stats = {
        "threshold": round(float(threshold), 5),
        "cluster_low": round(float(c1), 5),
        "cluster_high": round(float(c2), 5),
        "cluster_gap": round(float(c2 - c1), 5),
    }
    return cleaned_midground, background_far, stats


def build_plan(
    review_entry: dict[str, Any],
    lama_entry: dict[str, Any],
    depth_entry: dict[str, Any],
    out_dir: Path,
) -> dict[str, Any]:
    source_path = Path(lama_entry["best"]["clean_plate_path"])
    clean_plate = load_rgb(source_path)
    subject_mask = load_mask(Path(lama_entry["best"]["subject_mask_path"]))
    subject_rgba = load_rgba(Path(lama_entry["best"]["subject_rgba_path"]))
    depth_u16 = load_depth_u16(Path(depth_entry["depth_master_path"]))

    depth_norm, depth_stats = normalize_depth(depth_u16)
    near_map, polarity, polarity_stats = infer_near_map(depth_norm, subject_mask)
    midground_mask, background_far_mask, cluster_stats = build_layer_masks(near_map, subject_mask, review_entry["status"])

    foreground_rgba = subject_rgba
    midground_rgba = layer_rgba(clean_plate, midground_mask)
    background_far_rgba = layer_rgba(clean_plate, background_far_mask)
    depth_bw, near_bw = depth_to_preview(depth_norm, near_map)
    overlay_rgb = tinted_overlay(
        clean_plate,
        [
            (background_far_mask, (79, 117, 255)),
            (midground_mask, (255, 192, 77)),
            (subject_mask, (247, 99, 88)),
        ],
    )
    mid_preview = composite_preview(midground_rgba)
    far_preview = composite_preview(background_far_rgba)

    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "foreground_rgba": out_dir / "foreground_rgba.png",
        "midground_rgba": out_dir / "midground_rgba.png",
        "background_far_rgba": out_dir / "background_far_rgba.png",
        "foreground_mask": out_dir / "foreground_mask.png",
        "midground_mask": out_dir / "midground_mask.png",
        "background_far_mask": out_dir / "background_far_mask.png",
        "depth_bw_preview": out_dir / "depth_bw_preview.png",
        "near_bw_preview": out_dir / "near_bw_preview.png",
        "layer_overlay": out_dir / "layer_overlay.png",
        "three_layer_debug_sheet": out_dir / "three_layer_debug_sheet.png",
        "three_layer_plan": out_dir / "three_layer_plan.json",
    }

    Image.fromarray(foreground_rgba, mode="RGBA").save(paths["foreground_rgba"])
    Image.fromarray(midground_rgba, mode="RGBA").save(paths["midground_rgba"])
    Image.fromarray(background_far_rgba, mode="RGBA").save(paths["background_far_rgba"])
    Image.fromarray((subject_mask.astype(np.uint8) * 255), mode="L").save(paths["foreground_mask"])
    Image.fromarray((midground_mask.astype(np.uint8) * 255), mode="L").save(paths["midground_mask"])
    Image.fromarray((background_far_mask.astype(np.uint8) * 255), mode="L").save(paths["background_far_mask"])
    Image.fromarray(depth_bw, mode="L").save(paths["depth_bw_preview"])
    Image.fromarray(near_bw, mode="L").save(paths["near_bw_preview"])
    Image.fromarray(overlay_rgb, mode="RGB").save(paths["layer_overlay"])

    sheet = make_sheet(
        source_rgb=clean_plate,
        depth_bw=depth_bw,
        near_bw=near_bw,
        overlay_rgb=overlay_rgb,
        mid_preview=mid_preview,
        far_preview=far_preview,
        title=f"{review_entry['backend']} / {review_entry['sample']}",
        subtitle=f"status={review_entry['status']} | polarity={polarity} | cluster_gap={cluster_stats['cluster_gap']}",
    )
    sheet.save(paths["three_layer_debug_sheet"])

    metrics = {
        "foreground_area_ratio": area_ratio(subject_mask),
        "midground_area_ratio": area_ratio(midground_mask),
        "background_far_area_ratio": area_ratio(background_far_mask),
        "midground_depth_mean": round(float(near_map[midground_mask].mean()), 5) if midground_mask.any() else 0.0,
        "background_far_depth_mean": round(float(near_map[background_far_mask].mean()), 5) if background_far_mask.any() else 0.0,
    }
    plan = {
        "backend": review_entry["backend"],
        "sample": review_entry["sample"],
        "source_review_status": review_entry["status"],
        "recommended_mode": "three_layer",
        "recommended_renderer": "foreground + midground + background_far",
        "paths": {key: str(value) for key, value in paths.items()},
        "depth": {
            "source_depth_master_path": depth_entry["depth_master_path"],
            "polarity": polarity,
            **depth_stats,
            **polarity_stats,
            **cluster_stats,
        },
        "metrics": metrics,
        "layers": [
            {"id": "background_far", "z": -26, "motion_factor_x": 0.18, "motion_factor_y": 0.14},
            {"id": "midground", "z": -8, "motion_factor_x": 0.52, "motion_factor_y": 0.44},
            {"id": "foreground", "z": 12, "motion_factor_x": 0.92, "motion_factor_y": 0.78},
        ],
        "notes": [
            "Three-layer plan derived from clean_plate and selected depth backend.",
            "Midground uses non-subject pixels closer than adaptive threshold in inferred near-map.",
            "Background far is the remainder of clean_plate after excluding subject and midground.",
        ],
    }
    save_json(paths["three_layer_plan"], plan)
    return plan


def main() -> int:
    args = parse_args()
    render_review_root = Path(args.render_review_root).expanduser().resolve()
    lama_root = Path(args.lama_root).expanduser().resolve()
    depth_root = Path(args.depth_root).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    requested_statuses = set(args.statuses or ["caution", "needs_3_layer"])
    requested_backends = set(args.backends or [])

    review_summary = load_summary(render_review_root / "render_review_summary.json")
    lama_entries = map_lama_entries(load_summary(lama_root / "lama_plate_bakeoff_summary.json"))
    depth_entries = map_depth_samples(load_summary(depth_root / "bakeoff_summary.json"))

    plans: list[dict[str, Any]] = []
    aggregate = {"caution": 0, "needs_3_layer": 0}
    by_backend: dict[str, dict[str, Any]] = {}

    for review_entry in review_summary["entries"]:
        if review_entry["status"] not in requested_statuses:
            continue
        if requested_backends and review_entry["backend"] not in requested_backends:
            continue

        key = (review_entry["backend"], review_entry["sample"])
        lama_entry = lama_entries[key]
        depth_entry = depth_entries[key]
        sample_stem = Path(review_entry["sample"]).stem
        plan = build_plan(
            review_entry=review_entry,
            lama_entry=lama_entry,
            depth_entry=depth_entry,
            out_dir=outdir / review_entry["backend"] / sample_stem,
        )
        plans.append(plan)
        aggregate[review_entry["status"]] += 1

        bucket = by_backend.setdefault(
            review_entry["backend"],
            {"entries": 0, "avg_midground_area_ratio": 0.0, "avg_cluster_gap": 0.0},
        )
        bucket["entries"] += 1
        bucket["avg_midground_area_ratio"] += float(plan["metrics"]["midground_area_ratio"])
        bucket["avg_cluster_gap"] += float(plan["depth"]["cluster_gap"])

    for bucket in by_backend.values():
        if bucket["entries"]:
            bucket["avg_midground_area_ratio"] = round(bucket["avg_midground_area_ratio"] / bucket["entries"], 5)
            bucket["avg_cluster_gap"] = round(bucket["avg_cluster_gap"] / bucket["entries"], 5)

    summary = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "render_review_root": str(render_review_root),
        "lama_root": str(lama_root),
        "depth_root": str(depth_root),
        "outdir": str(outdir),
        "aggregate": {"by_source_status": aggregate, "by_backend": by_backend},
        "entries": plans,
    }
    save_json(outdir / "three_layer_plan_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
