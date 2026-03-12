#!/usr/bin/env python3
"""Analyze still images for photo-to-parallax suitability.

Uses ffprobe/ffmpeg so it runs in the default macOS shell environment
without extra Python image packages.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def run_json(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def run_signalstats(path: Path, vf: str) -> dict[str, float]:
    completed = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-vf",
            f"{vf},signalstats,metadata=print:file=-",
            "-frames:v",
            "1",
            "-f",
            "null",
            "-",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    metrics: dict[str, float] = {}
    for line in completed.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        short = key.rsplit(".", 1)[-1]
        try:
            metrics[short] = float(value)
        except ValueError:
            continue
    return metrics


def get_dimensions(path: Path) -> tuple[int, int]:
    payload = run_json(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "json",
            str(path),
        ]
    )
    stream = payload["streams"][0]
    return int(stream["width"]), int(stream["height"])


def analyze_image(path: Path) -> dict[str, Any]:
    width, height = get_dimensions(path)
    full_stats = run_signalstats(path, "format=yuv444p")
    edge_stats = run_signalstats(path, "format=gray,edgedetect=low=0.08:high=0.22")
    center_stats = run_signalstats(path, "crop=w=iw*0.5:h=ih*0.5:x=iw*0.25:y=ih*0.25,format=gray,edgedetect=low=0.08:high=0.22")

    brightness = float(full_stats.get("YAVG", 0.0) / 255.0)
    contrast = float((full_stats.get("YHIGH", 0.0) - full_stats.get("YLOW", 0.0)) / 255.0)
    saturation = float(full_stats.get("SATAVG", 0.0) / 255.0)
    edge_mean = float(edge_stats.get("YAVG", 0.0) / 255.0)
    center_edge_mean = float(center_stats.get("YAVG", 0.0) / 255.0)
    center_focus_bias = float(center_edge_mean / max(edge_mean, 1e-6))
    aspect_ratio = width / max(height, 1)

    motion_budget = clamp(5.2 - edge_mean * 11.0 - contrast * 3.5, 1.4, 5.2)
    overscan_pct = clamp(8.0 + motion_budget * 1.9 + center_focus_bias * 1.7, 10.0, 22.0)
    portrait_bonus = 4.0 if 0.85 <= aspect_ratio <= 1.15 else 0.0
    parallax_score = clamp(
        68.0
        + (center_focus_bias - 1.0) * 10.0
        + contrast * 20.0
        - edge_mean * 220.0
        - saturation * 30.0
        + portrait_bonus,
        30.0,
        95.0,
    )

    if aspect_ratio < 0.85:
        scene_type = "portrait"
    elif aspect_ratio > 1.2:
        scene_type = "landscape"
    else:
        scene_type = "square-ish"

    return {
        "path": str(path),
        "file_name": path.name,
        "width": width,
        "height": height,
        "aspect_ratio": round(aspect_ratio, 4),
        "scene_type": scene_type,
        "mean_brightness": round(brightness, 4),
        "contrast_std": round(contrast, 4),
        "mean_saturation": round(saturation, 4),
        "edge_density": round(edge_mean, 4),
        "center_focus_bias": round(center_focus_bias, 4),
        "recommended_motion_x_pct": round(motion_budget, 2),
        "recommended_motion_y_pct": round(motion_budget * 0.55, 2),
        "recommended_zoom": round(clamp(1.02 + motion_budget * 0.008, 1.03, 1.08), 3),
        "recommended_overscan_pct": round(overscan_pct, 2),
        "parallax_readiness_score": round(parallax_score, 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze image suitability for photo-to-parallax.")
    parser.add_argument("images", nargs="+", help="Image paths to analyze")
    parser.add_argument("--json-out", dest="json_out", help="Write full JSON report to file")
    args = parser.parse_args()

    report = [analyze_image(Path(image).expanduser().resolve()) for image in args.images]
    payload = {"generated_at": dt.datetime.now(dt.UTC).isoformat(), "images": report}

    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if args.json_out:
        out_path = Path(args.json_out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
