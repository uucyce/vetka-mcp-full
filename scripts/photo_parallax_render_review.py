#!/usr/bin/env python3
"""Build review artifacts and heuristic decisions for preview renders."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from photo_parallax_subject_plate_bakeoff import checkerboard, save_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review preview.mp4 outputs and produce visual/debug artifacts.")
    parser.add_argument(
        "--render-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview",
        help="Root directory with preview render outputs.",
    )
    parser.add_argument(
        "--lama-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/lama_plate_bakeoff",
        help="Root directory with LaMa stage outputs.",
    )
    parser.add_argument(
        "--sample-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/public/samples",
        help="Directory with original sample images.",
    )
    parser.add_argument(
        "--outdir",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_review",
        help="Output directory for review artifacts.",
    )
    parser.add_argument(
        "--backend",
        action="append",
        dest="backends",
        help="Limit run to one or more depth backends.",
    )
    parser.add_argument(
        "--sample",
        action="append",
        dest="samples",
        help="Limit run to one or more sample file names or stems.",
    )
    return parser.parse_args()


def normalize_sample_filters(values: list[str] | None) -> set[str]:
    if not values:
        return set()
    out = set()
    for value in values:
        out.add(value)
        out.add(Path(value).stem)
    return out


def load_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def map_lama_entries(summary: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(entry["backend"], entry["sample"]): entry for entry in summary["entries"]}


def composite_rgba_preview(path: Path) -> Image.Image:
    rgba = Image.open(path).convert("RGBA")
    width, height = rgba.size
    board = Image.fromarray(checkerboard(width, height), mode="RGB").convert("RGBA")
    return Image.alpha_composite(board, rgba).convert("RGB")


def extract_frame(video_path: Path, out_path: Path, timestamp_sec: float) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{timestamp_sec:.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            str(out_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def build_debug_side_by_side(source_path: Path, preview_path: Path, out_path: Path, duration_sec: float, fps: int) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(fps),
            "-loop",
            "1",
            "-t",
            f"{duration_sec:.3f}",
            "-i",
            str(source_path),
            "-i",
            str(preview_path),
            "-filter_complex",
            "[0:v]scale=-2:540,setsar=1[left];[1:v]scale=-2:540,setsar=1[right];[left][right]hstack=inputs=2,format=yuv420p[v]",
            "-map",
            "[v]",
            "-r",
            str(fps),
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-shortest",
            str(out_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def evaluate_foreground_transform(layout: dict[str, Any], progress: float) -> tuple[float, float, float]:
    source = layout["source"]
    camera = layout["camera"]
    motion_type = camera["motion_type"]
    travel_x_px = float(source["width"]) * float(camera["travel_x_pct"]) / 100.0
    travel_y_px = float(source["height"]) * float(camera["travel_y_pct"]) / 100.0
    eased = (1.0 - math.cos(progress * math.pi)) / 2.0
    wave = math.sin((eased - 0.5) * math.pi)
    cosine = math.cos(eased * math.pi)
    zoom = float(camera["zoom"])

    if motion_type == "orbit":
        return travel_x_px * 0.92 * wave, travel_y_px * 0.78 * cosine, 1.0
    if motion_type == "dolly-out + zoom-in":
        return travel_x_px * 0.55 * wave, travel_y_px * 0.43 * wave, 1.0 + (zoom - 1.0) * eased
    if motion_type == "dolly-in + zoom-out":
        return travel_x_px * 0.55 * wave, travel_y_px * 0.43 * wave, 1.0 + (zoom - 1.0) * (1.0 - eased)
    return travel_x_px * 0.92 * wave, travel_y_px * 0.78 * wave, 1.0


def alpha_bbox(rgba_path: Path) -> tuple[int, int, int, int]:
    import numpy as np

    alpha = np.asarray(Image.open(rgba_path).convert("RGBA"))[:, :, 3]
    ys, xs = np.where(alpha > 0)
    if ys.size == 0 or xs.size == 0:
        return (0, 0, 0, 0)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def foreground_edge_margin(layout: dict[str, Any], rgba_path: Path) -> float:
    bbox = alpha_bbox(rgba_path)
    src_w = int(layout["source"]["width"])
    src_h = int(layout["source"]["height"])
    min_margin = float("inf")

    for progress in (0.0, 0.25, 0.5, 0.75, 1.0):
        motion_x, motion_y, scale = evaluate_foreground_transform(layout, progress)
        scaled_canvas_w = src_w * scale
        scaled_canvas_h = src_h * scale
        canvas_left = (src_w - scaled_canvas_w) / 2.0 - motion_x
        canvas_top = (src_h - scaled_canvas_h) / 2.0 - motion_y
        bbox_left = canvas_left + bbox[0] * scale
        bbox_top = canvas_top + bbox[1] * scale
        bbox_right = canvas_left + bbox[2] * scale
        bbox_bottom = canvas_top + bbox[3] * scale
        edge_margin = min(
            bbox_left,
            bbox_top,
            src_w - bbox_right,
            src_h - bbox_bottom,
        )
        min_margin = min(min_margin, edge_margin)
    return round(float(min_margin), 3)


def classify_case(layout: dict[str, Any], lama_entry: dict[str, Any], edge_margin_px: float) -> tuple[str, int, list[str]]:
    subject_area_ratio = float(lama_entry["subject_area_ratio"])
    border_touch_ratio = float(lama_entry["best"]["border_touch_ratio"])
    camera = layout["camera"]
    motion_magnitude = math.sqrt(float(camera["travel_x_pct"]) ** 2 + float(camera["travel_y_pct"]) ** 2)
    motion_type = camera["motion_type"]
    zoom = float(camera["zoom"])

    score = 0
    notes: list[str] = []

    if subject_area_ratio >= 0.5:
        score += 2
        notes.append("large foreground coverage")
    elif subject_area_ratio >= 0.35:
        score += 1
        notes.append("mid-large foreground coverage")

    if motion_magnitude >= 4.0:
        score += 1
        notes.append("strong motion amplitude")

    if edge_margin_px < 24:
        score += 2
        notes.append("foreground edge pressure")
    elif edge_margin_px < 72:
        score += 1
        notes.append("tight foreground margins")

    if border_touch_ratio >= 0.15:
        score += 1
        notes.append("mask touches frame border")

    if motion_type in {"pan", "orbit"} and subject_area_ratio >= 0.4:
        score += 1
        notes.append("2-layer planar stress")

    if motion_type.startswith("dolly") and zoom >= 1.045:
        score += 1
        notes.append("zoom pressure on 2-layer comp")

    if score >= 4:
        return "needs_3_layer", score, notes
    if score >= 2:
        return "caution", score, notes
    return "two_layer_ok", score, notes or ["no strong review warnings"]


def draw_labeled_tile(image: Image.Image, label: str, size: tuple[int, int]) -> Image.Image:
    tile = image.convert("RGB").resize(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (size[0], size[1] + 34), "#0b0d11")
    canvas.paste(tile, (0, 34))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    draw.text((12, 10), label, fill="#e7e8ea", font=font)
    return canvas


def make_review_sheet(
    source_path: Path,
    subject_rgba_path: Path,
    poster_path: Path,
    frames: dict[str, Path],
    out_path: Path,
) -> None:
    tile_size = (520, 292)
    tiles = [
        draw_labeled_tile(Image.open(source_path).convert("RGB"), "source", tile_size),
        draw_labeled_tile(composite_rgba_preview(subject_rgba_path), "subject rgba", tile_size),
        draw_labeled_tile(Image.open(poster_path).convert("RGB"), "poster", tile_size),
        draw_labeled_tile(Image.open(frames["start"]).convert("RGB"), "preview start", tile_size),
        draw_labeled_tile(Image.open(frames["mid"]).convert("RGB"), "preview mid", tile_size),
        draw_labeled_tile(Image.open(frames["end"]).convert("RGB"), "preview end", tile_size),
    ]
    width = tile_size[0] * 3
    height = (tile_size[1] + 34) * 2
    sheet = Image.new("RGB", (width, height), "#050608")
    for index, tile in enumerate(tiles):
        x = (index % 3) * tile.width
        y = (index // 3) * tile.height
        sheet.paste(tile, (x, y))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def make_batch_sheet(items: list[dict[str, Any]], out_path: Path) -> None:
    font = ImageFont.load_default()
    tile_size = (420, 236)
    header = 62
    rows = math.ceil(len(items) / 2)
    sheet = Image.new("RGB", (tile_size[0] * 2, rows * (tile_size[1] + header)), "#050608")
    draw = ImageDraw.Draw(sheet)

    for index, item in enumerate(items):
        x = (index % 2) * tile_size[0]
        y = (index // 2) * (tile_size[1] + header)
        poster = Image.open(item["poster_path"]).convert("RGB").resize(tile_size, Image.Resampling.LANCZOS)
        sheet.paste(poster, (x, y + header))
        label = f"{item['backend']} / {item['sample_stem']}"
        status = item["status"]
        draw.text((x + 12, y + 10), label, fill="#e7e8ea", font=font)
        draw.text((x + 12, y + 30), status, fill="#8fd18e" if status == "two_layer_ok" else "#f3c86b" if status == "caution" else "#f38b7a", font=font)
        draw.text((x + 12, y + 46), f"score={item['review_score']} margin={item['edge_margin_px']}px", fill="#c8cbd0", font=font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def review_entry(
    entry: dict[str, Any],
    lama_entry: dict[str, Any],
    sample_root: Path,
    out_dir: Path,
) -> dict[str, Any]:
    sample_name = entry["sample"]
    sample_path = sample_root / sample_name
    if not sample_path.exists():
        matches = list(sample_root.glob(f"{Path(sample_name).stem}.*"))
        if not matches:
            raise FileNotFoundError(f"Missing sample source for {sample_name}")
        sample_path = matches[0]

    layout = entry["layout"]
    preview_path = Path(entry["preview_path"])
    poster_path = Path(entry["poster_path"])
    subject_rgba_path = Path(entry["source_subject_rgba_path"])
    review_dir = out_dir / entry["backend"] / Path(sample_name).stem
    frames_dir = review_dir / "frames"
    duration_sec = float(entry["probe"]["duration"])
    fps = max(1, int(layout["camera"]["fps"]))
    start_t = 0.0
    mid_t = duration_sec / 2.0
    end_t = max(0.0, duration_sec - 1.0 / fps)
    frames = {
        "start": frames_dir / "start.png",
        "mid": frames_dir / "mid.png",
        "end": frames_dir / "end.png",
    }
    extract_frame(preview_path, frames["start"], start_t)
    extract_frame(preview_path, frames["mid"], mid_t)
    extract_frame(preview_path, frames["end"], end_t)

    side_by_side_path = review_dir / "debug_side_by_side.mp4"
    build_debug_side_by_side(sample_path, preview_path, side_by_side_path, duration_sec, fps)

    review_sheet_path = review_dir / "render_review_sheet.png"
    make_review_sheet(sample_path, subject_rgba_path, poster_path, frames, review_sheet_path)

    edge_margin_px = foreground_edge_margin(layout, subject_rgba_path)
    status, review_score, notes = classify_case(layout, lama_entry, edge_margin_px)

    review = {
        "backend": entry["backend"],
        "sample": sample_name,
        "sample_stem": Path(sample_name).stem,
        "status": status,
        "review_score": review_score,
        "notes": notes,
        "edge_margin_px": edge_margin_px,
        "subject_area_ratio": lama_entry["subject_area_ratio"],
        "border_touch_ratio": lama_entry["best"]["border_touch_ratio"],
        "motion_type": layout["camera"]["motion_type"],
        "travel_x_pct": layout["camera"]["travel_x_pct"],
        "travel_y_pct": layout["camera"]["travel_y_pct"],
        "zoom": layout["camera"]["zoom"],
        "preview_path": str(preview_path),
        "poster_path": str(poster_path),
        "debug_side_by_side_path": str(side_by_side_path),
        "render_review_sheet_path": str(review_sheet_path),
        "frames": {key: str(path) for key, path in frames.items()},
    }
    save_json(review_dir / "render_review.json", review)
    return review


def aggregate(items: list[dict[str, Any]]) -> dict[str, Any]:
    by_backend: dict[str, dict[str, Any]] = {}
    status_counts: dict[str, int] = {"two_layer_ok": 0, "caution": 0, "needs_3_layer": 0}
    for item in items:
        status_counts[item["status"]] += 1
        bucket = by_backend.setdefault(
            item["backend"],
            {
                "entries": 0,
                "status_counts": {"two_layer_ok": 0, "caution": 0, "needs_3_layer": 0},
                "avg_review_score": 0.0,
                "avg_edge_margin_px": 0.0,
            },
        )
        bucket["entries"] += 1
        bucket["status_counts"][item["status"]] += 1
        bucket["avg_review_score"] += float(item["review_score"])
        bucket["avg_edge_margin_px"] += float(item["edge_margin_px"])

    for backend, bucket in by_backend.items():
        bucket["avg_review_score"] = round(bucket["avg_review_score"] / bucket["entries"], 5)
        bucket["avg_edge_margin_px"] = round(bucket["avg_edge_margin_px"] / bucket["entries"], 5)

    return {
        "status_counts": status_counts,
        "by_backend": by_backend,
    }


def main() -> int:
    args = parse_args()
    render_root = Path(args.render_root).expanduser().resolve()
    lama_root = Path(args.lama_root).expanduser().resolve()
    sample_root = Path(args.sample_root).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    requested_backends = set(args.backends or [])
    requested_samples = normalize_sample_filters(args.samples)

    render_summary = load_summary(render_root / "render_preview_summary.json")
    lama_summary = load_summary(lama_root / "lama_plate_bakeoff_summary.json")
    lama_entries = map_lama_entries(lama_summary)

    reviews: list[dict[str, Any]] = []
    for entry in render_summary["entries"]:
        if requested_backends and entry["backend"] not in requested_backends:
            continue
        sample_stem = Path(entry["sample"]).stem
        if requested_samples and entry["sample"] not in requested_samples and sample_stem not in requested_samples:
            continue
        lama_entry = lama_entries[(entry["backend"], entry["sample"])]
        reviews.append(review_entry(entry, lama_entry, sample_root, outdir))

    batch_sheet_path = outdir / "render_review_batch_sheet.png"
    make_batch_sheet(reviews, batch_sheet_path)

    summary = {
        "generated_at": json.dumps(None),  # placeholder updated below
        "render_root": str(render_root),
        "lama_root": str(lama_root),
        "sample_root": str(sample_root),
        "outdir": str(outdir),
        "aggregate": aggregate(reviews),
        "batch_sheet_path": str(batch_sheet_path),
        "entries": reviews,
    }
    import datetime as dt

    summary["generated_at"] = dt.datetime.now(dt.UTC).isoformat()
    save_json(outdir / "render_review_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
