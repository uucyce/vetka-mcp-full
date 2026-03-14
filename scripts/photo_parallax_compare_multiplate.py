#!/usr/bin/env python3
"""Build side-by-side comparison artifacts for 2-layer base vs multi-plate final renders."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any

from photo_parallax_subject_plate_bakeoff import save_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build compare sheets/videos for base vs multi-plate renders.")
    parser.add_argument(
        "--sample-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/public/samples",
        help="Directory with source sample images.",
    )
    parser.add_argument(
        "--base-render-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview/depth-anything-v2-small",
        help="Root directory with base 2-layer preview renders.",
    )
    parser.add_argument(
        "--multiplate-render-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate",
        help="Root directory with multi-plate final renders.",
    )
    parser.add_argument(
        "--outdir",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_multiplate",
        help="Output directory for compare artifacts.",
    )
    parser.add_argument(
        "--sample",
        action="append",
        dest="samples",
        help="Limit run to one or more sample ids.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def extract_mid_frame(video_path: Path, out_path: Path) -> None:
    ensure_parent(out_path)
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video_path), "-ss", "2.0", "-frames:v", "1", str(out_path)],
        check=True,
        capture_output=True,
        text=True,
    )


def build_sheet(source_path: Path, base_frame: Path, multiplate_frame: Path, out_path: Path) -> None:
    ensure_parent(out_path)
    filter_complex = (
        "[0:v]scale=-2:360,setsar=1[a];"
        "[1:v]scale=-2:360,setsar=1[b];"
        "[2:v]scale=-2:360,setsar=1[c];"
        "[a][b][c]hstack=inputs=3[v]"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source_path),
            "-i",
            str(base_frame),
            "-i",
            str(multiplate_frame),
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            str(out_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def build_batch_sheet(sheet_paths: list[Path], out_path: Path) -> None:
    if not sheet_paths:
        return
    ensure_parent(out_path)
    command = ["ffmpeg", "-y"]
    for path in sheet_paths:
        command.extend(["-i", str(path)])
    stack_inputs = "".join(f"[{index}:v]" for index in range(len(sheet_paths)))
    filter_complex = f"{stack_inputs}vstack=inputs={len(sheet_paths)}[v]"
    command.extend(["-filter_complex", filter_complex, "-map", "[v]", str(out_path)])
    subprocess.run(command, check=True, capture_output=True, text=True)


def build_compare_video(source_path: Path, base_video: Path, multiplate_video: Path, out_path: Path) -> None:
    ensure_parent(out_path)
    filter_complex = (
        "[0:v]scale=-2:540,setsar=1[a];"
        "[1:v]scale=-2:540,setsar=1[b];"
        "[2:v]scale=-2:540,setsar=1[c];"
        "[a][b][c]hstack=inputs=3,format=yuv420p[v]"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-t",
            "4.0",
            "-i",
            str(source_path),
            "-i",
            str(base_video),
            "-i",
            str(multiplate_video),
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-r",
            "25",
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
    base_root = Path(args.base_render_root).expanduser().resolve()
    multiplate_root = Path(args.multiplate_render_root).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    allowed = set(args.samples or [])

    summary = load_json(multiplate_root / "render_preview_multiplate_summary.json")
    entries: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    batch_sheet_paths: list[Path] = []

    for item in summary["entries"]:
        sample_id = item["sample"]
        if allowed and sample_id not in allowed:
            continue
        source_candidates = list(sample_root.glob(f"{sample_id}.*"))
        if not source_candidates:
            skipped.append({"sample": sample_id, "reason": "missing-source"})
            continue
        source_path = source_candidates[0]
        base_video = base_root / sample_id / "preview.mp4"
        multiplate_video = Path(item["preview_path"])
        if not base_video.exists() or not multiplate_video.exists():
            skipped.append(
                {
                    "sample": sample_id,
                    "reason": "missing-render-input",
                    "base_exists": base_video.exists(),
                    "multiplate_exists": multiplate_video.exists(),
                    "base_preview_path": str(base_video),
                    "multiplate_preview_path": str(multiplate_video),
                }
            )
            continue

        case_out = outdir / sample_id
        case_out.mkdir(parents=True, exist_ok=True)
        base_mid = case_out / "base_mid.png"
        multiplate_mid = case_out / "multiplate_mid.png"
        extract_mid_frame(base_video, base_mid)
        extract_mid_frame(multiplate_video, multiplate_mid)

        sheet_path = case_out / "compare_sheet.png"
        build_sheet(source_path, base_mid, multiplate_mid, sheet_path)
        batch_sheet_paths.append(sheet_path)

        compare_video = case_out / "compare_grid.mp4"
        build_compare_video(source_path, base_video, multiplate_video, compare_video)

        payload = {
            "sample": sample_id,
            "source_path": str(source_path),
            "base_preview_path": str(base_video),
            "multiplate_preview_path": str(multiplate_video),
            "sheet_path": str(sheet_path),
            "compare_video_path": str(compare_video),
            "base_mid_path": str(base_mid),
            "multiplate_mid_path": str(multiplate_mid),
            "rendered_plate_count": item["rendered_plate_count"],
        }
        save_json(case_out / "compare_review.json", payload)
        entries.append(payload)

    batch_path = outdir / "compare_batch_sheet.png"
    if batch_sheet_paths:
        build_batch_sheet(batch_sheet_paths, batch_path)

    payload = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "entries": entries,
        "count": len(entries),
        "skipped": skipped,
        "skipped_count": len(skipped),
        "batch_sheet_path": str(batch_path),
    }
    save_json(outdir / "render_compare_multiplate_summary.json", payload)
    print(f"MARKER_180.PARALLAX.MULTIPLATE_COMPARE.SUMMARY={outdir / 'render_compare_multiplate_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
