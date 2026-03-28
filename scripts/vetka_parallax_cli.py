#!/usr/bin/env python3
"""
VETKA Parallax CLI — photo-to-video with depth-driven camera motion.

Usage:
  python3 scripts/vetka_parallax_cli.py input.jpg -o output.mp4
  python3 scripts/vetka_parallax_cli.py input.jpg --motion orbit --quality social -o output.mp4
  python3 scripts/vetka_parallax_cli.py --manifest layer_space.json -o output.mp4

Modes:
  1. Single image → auto depth → parallax video
  2. Layer manifest (layer_space.json) → per-layer parallax video

No browser, no server, no CUT runtime. File in → video out.

MARKER_CLI_MVP
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from src.services.cut_depth_engine import (
    CameraGeometry,
    build_parallax_ffmpeg_cmd,
    build_parallax_filter,
    normalize_motion_type,
)
from src.services.cut_depth_service import (
    generate_depth,
    get_depth_paths,
)


# ---------------------------------------------------------------------------
# Presets — reuse CUT's proven vocabulary
# ---------------------------------------------------------------------------

MOTION_PRESETS: dict[str, dict[str, Any]] = {
    "orbit": {
        "motion_type": "orbit",
        "travel_x": 5.0,
        "travel_y": 0.0,
        "zoom": 1.0,
        "description": "Smooth orbital pan (default, most natural)",
    },
    "orbit_zoom": {
        "motion_type": "orbit",
        "travel_x": 5.0,
        "travel_y": 0.0,
        "zoom": 1.05,
        "description": "Orbit with subtle push-in",
    },
    "dolly_zoom_in": {
        "motion_type": "dolly_zoom_in",
        "travel_x": 3.0,
        "travel_y": 0.0,
        "zoom": 1.1,
        "description": "Dolly out + zoom in (Vertigo effect)",
    },
    "dolly_zoom_out": {
        "motion_type": "dolly_zoom_out",
        "travel_x": 3.0,
        "travel_y": 0.0,
        "zoom": 1.1,
        "description": "Dolly in + zoom out (reverse Vertigo)",
    },
    "linear": {
        "motion_type": "linear",
        "travel_x": 8.0,
        "travel_y": 0.0,
        "zoom": 1.0,
        "description": "Linear slide left-to-right",
    },
    "gentle": {
        "motion_type": "orbit",
        "travel_x": 2.0,
        "travel_y": 0.5,
        "zoom": 1.02,
        "description": "Subtle, gentle motion (portraits)",
    },
    "dramatic": {
        "motion_type": "orbit",
        "travel_x": 12.0,
        "travel_y": 2.0,
        "zoom": 1.08,
        "description": "Wide dramatic sweep (landscapes)",
    },
}

QUALITY_PRESETS: dict[str, dict[str, Any]] = {
    "web": {
        "width": 1280, "height": 720, "crf": 24,
        "description": "Web preview (720p, fast)",
    },
    "social": {
        "width": 1920, "height": 1080, "crf": 20,
        "description": "Social media (1080p, balanced)",
    },
    "quality": {
        "width": 2560, "height": 1440, "crf": 18,
        "description": "High quality (1440p, slow)",
    },
}


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

def probe_image_dimensions(path: str) -> tuple[int, int]:
    """Get image/video dimensions via ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0:s=x",
            str(path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        parts = result.stdout.strip().split("x")
        if len(parts) >= 2:
            return int(parts[0]), int(parts[1])
    except Exception:
        pass
    return 1920, 1080  # fallback


def run_parallax(
    input_path: str,
    output_path: str,
    depth_path: str | None = None,
    motion_preset: str = "orbit",
    quality_preset: str = "social",
    duration: float = 4.0,
    focal_length: float = 50.0,
    depth_backend: str = "auto",
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Full parallax pipeline: image → depth → camera → FFmpeg → video.

    Returns result dict with success, timing, paths.
    """
    t0 = time.monotonic()
    src = Path(input_path)
    if not src.exists():
        return {"success": False, "error": f"Input not found: {input_path}"}

    # 1. Probe dimensions
    source_width, source_height = probe_image_dimensions(input_path)
    if verbose:
        print(f"  Source: {source_width}x{source_height}")

    # 2. Generate or use existing depth map
    if depth_path and Path(depth_path).exists():
        if verbose:
            print(f"  Depth: using provided {depth_path}")
    else:
        if verbose:
            print(f"  Depth: generating ({depth_backend})...")
        depth_result = generate_depth(input_path, backend=depth_backend)
        if not depth_result.success:
            return {"success": False, "error": f"Depth generation failed: {depth_result.error}"}
        depth_path = depth_result.depth_path
        if verbose:
            print(f"  Depth: {depth_result.backend} → {depth_path} ({depth_result.elapsed_ms:.0f}ms)")

    # 3. Build camera from presets
    motion = MOTION_PRESETS.get(motion_preset, MOTION_PRESETS["orbit"])
    quality = QUALITY_PRESETS.get(quality_preset, QUALITY_PRESETS["social"])

    camera = CameraGeometry(
        focal_length_mm=focal_length,
        travel_x=float(motion["travel_x"]),
        travel_y=float(motion["travel_y"]),
        zoom=float(motion["zoom"]),
        motion_type=str(motion["motion_type"]),
        duration_sec=duration,
        overscan_pct=20.0,
    )

    if verbose:
        print(f"  Camera: {motion_preset} ({motion['description']})")
        print(f"  Quality: {quality_preset} ({quality['description']})")
        print(f"  Duration: {duration}s, focal: {focal_length}mm")

    # 4. Build FFmpeg command
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = build_parallax_ffmpeg_cmd(
        source_path=input_path,
        depth_path=depth_path,
        output_path=output_path,
        camera=camera,
        source_width=int(quality["width"]),
        source_height=int(quality["height"]),
        crf=int(quality["crf"]),
    )

    if verbose:
        print(f"  Rendering...")

    # 5. Run FFmpeg
    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=300,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode()[:500]
            return {"success": False, "error": f"FFmpeg failed: {stderr}"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "FFmpeg timed out (300s)"}

    elapsed = time.monotonic() - t0

    if not out.exists():
        return {"success": False, "error": "Output file not created"}

    file_size = out.stat().st_size
    result_dict = {
        "success": True,
        "input": input_path,
        "output": output_path,
        "depth": depth_path,
        "motion_preset": motion_preset,
        "quality_preset": quality_preset,
        "duration_sec": duration,
        "file_size_mb": round(file_size / (1024 * 1024), 2),
        "elapsed_sec": round(elapsed, 1),
    }

    if verbose:
        print(f"  Done: {output_path} ({result_dict['file_size_mb']}MB, {result_dict['elapsed_sec']}s)")

    return result_dict


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vetka-parallax",
        description="VETKA Parallax — photo-to-video with depth-driven camera motion",
        epilog="Examples:\n"
               "  %(prog)s photo.jpg -o parallax.mp4\n"
               "  %(prog)s photo.jpg --motion dramatic --quality quality -o cinematic.mp4\n"
               "  %(prog)s photo.jpg --depth depth.png --duration 6 -o custom.mp4\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("input", nargs="?", help="Input image (JPG, PNG, TIFF)")
    parser.add_argument("-o", "--output", help="Output video path (MP4)")

    # Motion
    motion_group = parser.add_argument_group("motion")
    motion_choices = list(MOTION_PRESETS.keys())
    motion_group.add_argument(
        "--motion", choices=motion_choices, default="orbit",
        help=f"Motion preset (default: orbit). Options: {', '.join(motion_choices)}",
    )
    motion_group.add_argument("--duration", type=float, default=4.0, help="Duration in seconds (default: 4)")
    motion_group.add_argument("--focal-length", type=float, default=50.0, help="Focal length in mm (default: 50)")

    # Quality
    quality_group = parser.add_argument_group("quality")
    quality_choices = list(QUALITY_PRESETS.keys())
    quality_group.add_argument(
        "--quality", choices=quality_choices, default="social",
        help=f"Quality preset (default: social). Options: {', '.join(quality_choices)}",
    )

    # Depth
    depth_group = parser.add_argument_group("depth")
    depth_group.add_argument("--depth", help="Pre-computed depth map PNG (skip auto-generation)")
    depth_group.add_argument(
        "--depth-backend", choices=["auto", "depth-pro", "depth-anything-v2-small", "ffmpeg-luma"],
        default="auto", help="Depth generation backend (default: auto)",
    )

    # Output
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    parser.add_argument("--list-presets", action="store_true", help="List all available presets")

    return parser


def list_presets() -> None:
    print("\nMotion presets:")
    for name, preset in MOTION_PRESETS.items():
        print(f"  {name:20s} — {preset['description']}")
    print("\nQuality presets:")
    for name, preset in QUALITY_PRESETS.items():
        print(f"  {name:20s} — {preset['description']}")
    print()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_presets:
        list_presets()
        return 0

    if not args.input:
        parser.error("input is required (unless --list-presets)")
    if not args.output:
        parser.error("-o/--output is required")

    if not Path(args.input).exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        return 1

    if args.verbose:
        print(f"VETKA Parallax — {args.input} → {args.output}")

    result = run_parallax(
        input_path=args.input,
        output_path=args.output,
        depth_path=args.depth,
        motion_preset=args.motion,
        quality_preset=args.quality,
        duration=args.duration,
        focal_length=args.focal_length,
        depth_backend=args.depth_backend,
        verbose=args.verbose,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    elif not result["success"]:
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1
    elif not args.verbose:
        print(result["output"])

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
