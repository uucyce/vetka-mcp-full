#!/usr/bin/env python3
"""Build side-by-side comparison artifacts for manual multi-plate vs Qwen-planned multi-plate renders."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from photo_parallax_subject_plate_bakeoff import save_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build compare sheets/videos for manual vs Qwen multiplate renders.")
    parser.add_argument(
        "--sample-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/public/samples",
    )
    parser.add_argument(
        "--manual-render-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate",
    )
    parser.add_argument(
        "--qwen-render-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate_qwen",
    )
    parser.add_argument(
        "--outdir",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_multiplate",
    )
    parser.add_argument("--sample", action="append", dest="samples")
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


def build_sheet(source_path: Path, manual_frame: Path, qwen_frame: Path, out_path: Path) -> None:
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
            str(manual_frame),
            "-i",
            str(qwen_frame),
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
    if len(sheet_paths) == 1:
        shutil.copy2(sheet_paths[0], out_path)
        return
    command = ["ffmpeg", "-y"]
    for path in sheet_paths:
        command.extend(["-i", str(path)])
    filter_complex = "".join(f"[{idx}:v]" for idx in range(len(sheet_paths))) + f"vstack=inputs={len(sheet_paths)}[v]"
    command.extend(["-filter_complex", filter_complex, "-map", "[v]", str(out_path)])
    subprocess.run(command, check=True, capture_output=True, text=True)


def build_compare_video(source_path: Path, manual_video: Path, qwen_video: Path, out_path: Path) -> None:
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
            str(manual_video),
            "-i",
            str(qwen_video),
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
    manual_root = Path(args.manual_render_root).expanduser().resolve()
    qwen_root = Path(args.qwen_render_root).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    allowed = set(args.samples or [])

    manual_summary = load_json(manual_root / "render_preview_multiplate_summary.json")
    qwen_summary = load_json(qwen_root / "render_preview_multiplate_summary.json")
    qwen_by_sample = {item["sample"]: item for item in qwen_summary["entries"]}

    entries: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    batch_sheet_paths: list[Path] = []

    for item in manual_summary["entries"]:
      sample_id = item["sample"]
      if allowed and sample_id not in allowed:
          continue
      qwen_item = qwen_by_sample.get(sample_id)
      source_candidates = list(sample_root.glob(f"{sample_id}.*"))
      if not source_candidates:
          skipped.append({"sample": sample_id, "reason": "missing-source"})
          continue
      if not qwen_item:
          skipped.append({"sample": sample_id, "reason": "missing-qwen-render"})
          continue
      source_path = source_candidates[0]
      manual_video = Path(item["preview_path"])
      qwen_video = Path(qwen_item["preview_path"])
      if not manual_video.exists() or not qwen_video.exists():
          skipped.append(
              {
                  "sample": sample_id,
                  "reason": "missing-render-input",
                  "manual_exists": manual_video.exists(),
                  "qwen_exists": qwen_video.exists(),
              }
          )
          continue

      case_out = outdir / sample_id
      case_out.mkdir(parents=True, exist_ok=True)
      manual_mid = case_out / "manual_mid.png"
      qwen_mid = case_out / "qwen_mid.png"
      extract_mid_frame(manual_video, manual_mid)
      extract_mid_frame(qwen_video, qwen_mid)

      sheet_path = case_out / "compare_sheet.png"
      build_sheet(source_path, manual_mid, qwen_mid, sheet_path)
      batch_sheet_paths.append(sheet_path)

      compare_video = case_out / "compare_grid.mp4"
      build_compare_video(source_path, manual_video, qwen_video, compare_video)

      payload = {
          "sample": sample_id,
          "source_path": str(source_path),
          "manual_preview_path": str(manual_video),
          "qwen_preview_path": str(qwen_video),
          "sheet_path": str(sheet_path),
          "compare_video_path": str(compare_video),
          "manual_mid_path": str(manual_mid),
          "qwen_mid_path": str(qwen_mid),
          "manual_rendered_plate_count": item["rendered_plate_count"],
          "qwen_rendered_plate_count": qwen_item["rendered_plate_count"],
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
    save_json(outdir / "render_compare_qwen_multiplate_summary.json", payload)
    print(f"MARKER_180.PARALLAX.QWEN_MULTIPLATE_COMPARE.SUMMARY={outdir / 'render_compare_qwen_multiplate_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
