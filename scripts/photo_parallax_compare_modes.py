#!/usr/bin/env python3
"""Build side-by-side comparison artifacts for parallax render modes."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from photo_parallax_subject_plate_bakeoff import save_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build compare sheets/videos for 2-layer, safe, and 3-layer modes.")
    parser.add_argument(
        "--sample-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/public/samples",
        help="Directory with original sample images.",
    )
    parser.add_argument(
        "--mode-routing-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mode_routing_review",
        help="Root directory with mode routing summary.",
    )
    parser.add_argument(
        "--outdir",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mode_compare_review",
        help="Output directory for compare artifacts.",
    )
    return parser.parse_args()


def load_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def extract_mid_frame(video_path: Path, out_path: Path) -> None:
    ensure_parent(out_path)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-ss",
            "2.0",
            "-frames:v",
            "1",
            str(out_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def expected_gain_score(entry: dict[str, Any]) -> tuple[float, str]:
    metrics = entry["metrics"]
    cluster_gap = float(metrics.get("cluster_gap") or 0.0)
    midground_ratio = float(metrics.get("midground_area_ratio") or 0.0)
    review_score = float(metrics.get("review_score") or 0.0)
    edge_margin = float(metrics.get("edge_margin_px") or 0.0)
    edge_pressure = max(0.0, -edge_margin) / 100.0
    score = cluster_gap * 4.2 + midground_ratio * 3.3 + review_score * 0.18 + edge_pressure * 0.9
    if score >= 2.2:
        bucket = "high"
    elif score >= 1.2:
        bucket = "medium"
    else:
        bucket = "low"
    return round(score, 4), bucket


def tile_from_image(path: Path | None, label: str, size: tuple[int, int]) -> Image.Image:
    tile = Image.new("RGB", size, "#202020")
    draw = ImageDraw.Draw(tile)
    font = ImageFont.load_default()
    if path and path.exists():
        image = Image.open(path).convert("RGB")
        image.thumbnail((size[0], size[1] - 18))
        tile.paste(image, ((size[0] - image.width) // 2, (size[1] - 18 - image.height) // 2))
    else:
        draw.text((12, size[1] // 2 - 6), "n/a", fill="#989188", font=font)
    draw.text((10, size[1] - 15), label, fill="#f6f1e7", font=font)
    return tile


def build_sheet(
    source_path: Path,
    two_frame: Path,
    safe_frame: Path | None,
    three_frame: Path | None,
    title: str,
    subtitle: str,
) -> Image.Image:
    tile_w = 300
    tile_h = 190
    margin = 16
    canvas = Image.new("RGB", (margin * 5 + tile_w * 4, 72 + margin * 2 + tile_h), "#101011")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    draw.text((margin, 12), title, fill="#f6f1e7", font=font)
    draw.text((margin, 30), subtitle, fill="#b6b0a3", font=font)
    tiles = [
        tile_from_image(source_path, "source", (tile_w, tile_h)),
        tile_from_image(two_frame, "2-layer", (tile_w, tile_h)),
        tile_from_image(safe_frame, "safe 2-layer", (tile_w, tile_h)),
        tile_from_image(three_frame, "3-layer", (tile_w, tile_h)),
    ]
    for idx, tile in enumerate(tiles):
        x = margin + idx * (tile_w + margin)
        canvas.paste(tile, (x, 72))
    return canvas


def build_compare_video(
    source_path: Path,
    two_layer_path: Path,
    safe_path: Path | None,
    three_layer_path: Path | None,
    out_path: Path,
) -> None:
    ensure_parent(out_path)
    inputs = [
        "-loop", "1", "-t", "4.0", "-i", str(source_path),
        "-i", str(two_layer_path),
    ]
    if safe_path and safe_path.exists():
        inputs.extend(["-i", str(safe_path)])
    else:
        inputs.extend(["-loop", "1", "-t", "4.0", "-i", str(source_path)])
    if three_layer_path and three_layer_path.exists():
        inputs.extend(["-i", str(three_layer_path)])
    else:
        inputs.extend(["-loop", "1", "-t", "4.0", "-i", str(source_path)])

    filter_complex = (
        "[0:v]scale=-2:540,setsar=1[a];"
        "[1:v]scale=-2:540,setsar=1[b];"
        "[2:v]scale=-2:540,setsar=1[c];"
        "[3:v]scale=-2:540,setsar=1[d];"
        "[a][b]hstack=inputs=2[top];"
        "[c][d]hstack=inputs=2[bottom];"
        "[top][bottom]vstack=inputs=2,format=yuv420p[v]"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-r",
            "24",
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


def main() -> int:
    args = parse_args()
    sample_root = Path(args.sample_root).expanduser().resolve()
    mode_routing_root = Path(args.mode_routing_root).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()

    routing_summary = load_summary(mode_routing_root / "mode_routing_summary.json")
    compare_entries: list[dict[str, Any]] = []
    batch_tiles: list[Image.Image] = []
    gain_counts = {"high": 0, "medium": 0, "low": 0}

    for entry in routing_summary["entries"]:
        source_path = sample_root / entry["sample"]
        case_out = outdir / entry["backend"] / Path(entry["sample"]).stem
        case_out.mkdir(parents=True, exist_ok=True)

        two_mid = case_out / "two_layer_mid.png"
        safe_mid = case_out / "safe_mid.png"
        three_mid = case_out / "three_layer_mid.png"
        extract_mid_frame(Path(entry["source_two_layer_preview_path"]), two_mid)
        if entry["source_safe_preview_path"]:
            extract_mid_frame(Path(entry["source_safe_preview_path"]), safe_mid)
        if entry["source_three_layer_preview_path"]:
            extract_mid_frame(Path(entry["source_three_layer_preview_path"]), three_mid)

        gain_score, gain_bucket = expected_gain_score(entry)
        gain_counts[gain_bucket] += 1
        subtitle = (
            f"{entry['source_status']} -> {entry['recommended_mode']} | "
            f"gain={gain_score} ({gain_bucket}) | {entry['reason']}"
        )
        sheet = build_sheet(
            source_path=source_path,
            two_frame=two_mid,
            safe_frame=safe_mid if safe_mid.exists() else None,
            three_frame=three_mid if three_mid.exists() else None,
            title=f"{entry['backend']} / {entry['sample']}",
            subtitle=subtitle,
        )
        sheet_path = case_out / "mode_compare_sheet.png"
        sheet.save(sheet_path)
        batch_tiles.append(sheet.resize((420, int(sheet.height * 420 / sheet.width))))

        compare_video = case_out / "mode_compare_grid.mp4"
        build_compare_video(
            source_path=source_path,
            two_layer_path=Path(entry["source_two_layer_preview_path"]),
            safe_path=Path(entry["source_safe_preview_path"]) if entry["source_safe_preview_path"] else None,
            three_layer_path=Path(entry["source_three_layer_preview_path"]) if entry["source_three_layer_preview_path"] else None,
            out_path=compare_video,
        )

        payload = {
            **entry,
            "expected_gain_score": gain_score,
            "expected_gain_bucket": gain_bucket,
            "compare_sheet_path": str(sheet_path),
            "compare_video_path": str(compare_video),
            "mid_frames": {
                "two_layer": str(two_mid),
                "safe_two_layer": str(safe_mid) if safe_mid.exists() else None,
                "three_layer": str(three_mid) if three_mid.exists() else None,
            },
        }
        save_json(case_out / "mode_compare_review.json", payload)
        compare_entries.append(payload)

    if batch_tiles:
        width = max(tile.width for tile in batch_tiles)
        height = sum(tile.height for tile in batch_tiles) + 16 * (len(batch_tiles) + 1)
        batch = Image.new("RGB", (width + 32, height), "#0f1011")
        y = 16
        for tile in batch_tiles:
            batch.paste(tile, (16, y))
            y += tile.height + 16
        batch_path = outdir / "mode_compare_batch_sheet.png"
        batch.save(batch_path)
    else:
        batch_path = outdir / "mode_compare_batch_sheet.png"

    summary = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "outdir": str(outdir),
        "gain_counts": gain_counts,
        "batch_sheet_path": str(batch_path),
        "entries": compare_entries,
    }
    save_json(outdir / "mode_compare_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
