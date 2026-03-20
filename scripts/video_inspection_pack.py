#!/usr/bin/env python3
"""Video Inspection Pack — Video-to-AI bridge.

Transforms mp4 into lightweight artifacts (~800KB) readable by both
AI vision models and humans. Two layers: RGB (instant, ffmpeg+Pillow)
and Depth (heavy, depth model — Phase M2).

Usage:
    python3 scripts/video_inspection_pack.py \
        --input /path/to/video.mp4 \
        --outdir /path/to/inspection

Architecture: docs/197ph_tool_analize_video_forAI/ARCHITECTURE_VIDEO_INSPECTION_TOOL.md
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

# Layer 1 deps (minimal)
from PIL import Image, ImageChops, ImageDraw, ImageFont


# ---------------------------------------------------------------------------
# ffprobe metadata
# ---------------------------------------------------------------------------

def get_video_metadata(input_path: str) -> dict:
    """Extract video metadata via ffprobe. Returns dict with duration, fps, etc."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", input_path,
    ]
    try:
        raw = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except FileNotFoundError:
        sys.exit("ERROR: ffprobe not found. Install ffmpeg: brew install ffmpeg")
    except subprocess.CalledProcessError as exc:
        sys.exit(f"ERROR: ffprobe failed on {input_path}: {exc.stdout.decode()}")

    data = json.loads(raw)

    # Find video stream
    video_stream = None
    for s in data.get("streams", []):
        if s.get("codec_type") == "video":
            video_stream = s
            break
    if video_stream is None:
        sys.exit(f"ERROR: no video stream found in {input_path}")

    # Parse fps safely via Fraction (never eval)
    fps_str = video_stream.get("r_frame_rate", "30/1")
    fps = float(Fraction(fps_str))

    duration = float(data.get("format", {}).get("duration", 0))

    # Frame count: prefer nb_frames, fallback to duration * fps
    nb_frames = video_stream.get("nb_frames")
    if nb_frames and nb_frames != "N/A":
        frame_count = int(nb_frames)
    else:
        frame_count = max(1, int(duration * fps))

    return {
        "duration": duration,
        "fps": round(fps, 3),
        "frame_count": frame_count,
        "width": int(video_stream["width"]),
        "height": int(video_stream["height"]),
        "codec": video_stream.get("codec_name", "unknown"),
    }


# ---------------------------------------------------------------------------
# Frame extraction (ffmpeg)
# ---------------------------------------------------------------------------

def extract_frames(input_path: str, frame_dir: Path, meta: dict,
                   n_frames: int, width: int, crop: str | None) -> list[Path]:
    """Extract N uniformly-spaced frames via ffmpeg. Returns sorted list of paths."""
    step = max(1, meta["frame_count"] // n_frames)

    # Build video filter chain
    vf_parts = []
    if crop:
        x, y, w, h = (int(v) for v in crop.split(","))
        vf_parts.append(f"crop={w}:{h}:{x}:{y}")
    vf_parts.append(f"select=not(mod(n\\,{step}))")
    vf_parts.append(f"scale={width}:-1")
    vf = ",".join(vf_parts)

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", vf,
        "-vsync", "vfr",
        str(frame_dir / "frame_%04d.png"),
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    frames = sorted(frame_dir.glob("frame_*.png"))
    # Limit to requested count (ffmpeg may extract more)
    return frames[:n_frames]


# ---------------------------------------------------------------------------
# Contact sheet (197.4)
# ---------------------------------------------------------------------------

def build_contact_sheet(frames: list[Path], meta: dict,
                        columns: int, width: int, outdir: Path) -> Path:
    """Assemble frames into a grid with timestamp overlay."""
    if not frames:
        return outdir / "contact_sheet.jpg"

    imgs = [Image.open(f) for f in frames]
    thumb_w, thumb_h = imgs[0].size

    cols = min(columns, len(imgs))
    rows = (len(imgs) + cols - 1) // cols

    sheet = Image.new("RGB", (cols * thumb_w, rows * thumb_h), (20, 20, 20))
    draw = ImageDraw.Draw(sheet)

    # Font: try system font, fallback to default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except (OSError, IOError):
        font = ImageFont.load_default()

    step = max(1, meta["frame_count"] // len(frames))
    for i, img in enumerate(imgs):
        col = i % cols
        row = i // cols
        px = col * thumb_w
        py = row * thumb_h
        sheet.paste(img, (px, py))

        # Timestamp label
        frame_idx = i * step
        ts_sec = frame_idx / meta["fps"] if meta["fps"] > 0 else 0
        label = f"#{frame_idx} ({ts_sec:.1f}s)"
        draw.text((px + 8, py + 6), label, fill="white", font=font)

    out_path = outdir / "contact_sheet.jpg"
    sheet.save(out_path, "JPEG", quality=85)
    return out_path


# ---------------------------------------------------------------------------
# Motion diff strip (197.5)
# ---------------------------------------------------------------------------

def _auto_amplify(diff_img: Image.Image) -> Image.Image:
    """Auto-amplify diff image so subtle motion becomes visible.

    Finds the max pixel value and scales so it maps to 255.
    Subtle parallax diffs (max ~5-15) become clearly visible.
    """
    import numpy as np
    arr = np.array(diff_img, dtype=np.float32)
    peak = arr.max()
    if peak < 1:
        return diff_img
    # Scale to fill full dynamic range — subtle motion must be visible
    factor = 255.0 / peak
    amplified = (arr * factor).clip(0, 255).astype(np.uint8)
    return Image.fromarray(amplified)


def build_motion_diff(frames: list[Path], columns: int,
                      outdir: Path) -> Path | None:
    """Compute absdiff between consecutive frames, auto-amplify, assemble grid."""
    if len(frames) < 2:
        return None

    import numpy as np

    diffs = []
    for i in range(len(frames) - 1):
        im1 = Image.open(frames[i]).convert("RGB")
        im2 = Image.open(frames[i + 1]).convert("RGB")
        raw_diff = ImageChops.difference(im1, im2)
        diffs.append(raw_diff)

    # Normalize by p98 (not max) so subtle motion fills the range.
    # Max is often a single hot pixel; p98 represents real motion edges.
    all_pixels = np.concatenate([np.array(d).ravel() for d in diffs])
    p98 = float(np.percentile(all_pixels[all_pixels > 0], 98)) if (all_pixels > 0).any() else 1.0
    p98 = max(p98, 1.0)
    print(f"  diff stats: max={all_pixels.max()}, p98={p98:.1f} (amplify: {255.0 / p98:.1f}x)")

    amplified = []
    for d in diffs:
        arr = (np.array(d, dtype=np.float32) * (255.0 / p98)).clip(0, 255).astype(np.uint8)
        amplified.append(Image.fromarray(arr))

    # Grid layout (same as contact sheet)
    thumb_w, thumb_h = amplified[0].size
    cols = min(columns, len(amplified))
    rows = (len(amplified) + cols - 1) // cols

    grid = Image.new("RGB", (cols * thumb_w, rows * thumb_h), (0, 0, 0))
    for i, d in enumerate(amplified):
        px = (i % cols) * thumb_w
        py = (i // cols) * thumb_h
        grid.paste(d, (px, py))

    # PNG to preserve subtle values (JPEG kills dark detail)
    out_path = outdir / "motion_diff.png"
    grid.save(out_path, "PNG")
    return out_path


# ---------------------------------------------------------------------------
# inspection.json (197.6)
# ---------------------------------------------------------------------------

def write_inspection_json(meta: dict, args, outdir: Path,
                          contact_path: Path | None,
                          diff_path: Path | None,
                          timestamps: list[float]) -> Path:
    """Write inspection summary JSON."""
    summary = {
        "version": "1.0",
        "tool": "video_inspection_pack",
        "input": {
            "path": str(Path(args.input).resolve()),
            "duration_sec": round(meta["duration"], 2),
            "fps": meta["fps"],
            "frame_count": meta["frame_count"],
            "resolution": f"{meta['width']}x{meta['height']}",
            "codec": meta["codec"],
        },
        "settings": {
            "frames_sampled": args.frames,
            "columns": args.columns,
            "output_width": args.width,
            "crop": args.crop or "none",
            "depth_enabled": False,  # M2
        },
        "outputs": {
            "contact_sheet": "contact_sheet.jpg" if contact_path else None,
            "motion_diff": "motion_diff.png" if diff_path else None,
        },
        "timestamps_sampled": [round(t, 3) for t in timestamps],
    }

    out_path = outdir / "inspection.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    return out_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Video Inspection Pack — Video-to-AI bridge",
    )
    # Required
    p.add_argument("--input", required=True, help="Input MP4 path")
    p.add_argument("--outdir", required=True, help="Output directory")

    # Layer 1 params
    p.add_argument("--frames", type=int, default=8, help="Frames for contact sheet (default: 8)")
    p.add_argument("--columns", type=int, default=4, help="Columns in contact sheet (default: 4)")
    p.add_argument("--width", type=int, default=960, help="Output width in px (default: 960)")
    p.add_argument("--crop", type=str, default=None, help="ROI crop: x,y,w,h")

    # Layer 2 params (M2 — not yet implemented)
    p.add_argument("--depth", action="store_true", help="Enable depth analysis (Layer 2) [M2]")
    p.add_argument("--depth-model", default="depth-anything-v2",
                    help="Depth model: depth-anything-v2, depth-pro [M2]")
    p.add_argument("--sample-rate", type=int, default=5,
                    help="Depth: every Nth frame (default: 5) [M2]")

    # Advanced (M3 — not yet implemented)
    p.add_argument("--keyframes", action="store_true",
                    help="Scene-change detection instead of uniform [M3]")

    return p


def main():
    parser = build_cli()
    args = parser.parse_args()

    # Validate input
    if not os.path.isfile(args.input):
        sys.exit(f"ERROR: input file not found: {args.input}")

    # Create outdir
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Metadata
    print(f"[probe] {args.input}")
    meta = get_video_metadata(args.input)
    print(f"  {meta['width']}x{meta['height']}, {meta['fps']}fps, "
          f"{meta['duration']:.1f}s, {meta['frame_count']} frames, {meta['codec']}")

    # Extract frames to temp dir
    with tempfile.TemporaryDirectory() as tmp:
        frame_dir = Path(tmp) / "frames"
        frame_dir.mkdir()

        print(f"[extract] {args.frames} frames (uniform, width={args.width})")
        frames = extract_frames(args.input, frame_dir, meta,
                                args.frames, args.width, args.crop)
        print(f"  extracted {len(frames)} frames")

        if not frames:
            sys.exit("ERROR: no frames extracted")

        # Compute timestamps
        step = max(1, meta["frame_count"] // args.frames)
        timestamps = [
            (i * step) / meta["fps"] if meta["fps"] > 0 else 0.0
            for i in range(len(frames))
        ]

        # Contact sheet
        print("[build] contact_sheet.jpg")
        contact_path = build_contact_sheet(frames, meta, args.columns, args.width, outdir)

        # Motion diff
        print("[build] motion_diff.png")
        diff_path = build_motion_diff(frames, args.columns, outdir)

    # Depth (M2 placeholder)
    if args.depth:
        print("[skip] --depth not yet implemented (Phase M2)")

    # Keyframes (M3 placeholder)
    if args.keyframes:
        print("[skip] --keyframes not yet implemented (Phase M3)")

    # JSON manifest
    print("[write] inspection.json")
    write_inspection_json(meta, args, outdir, contact_path, diff_path, timestamps)

    print(f"\nInspection pack ready: {outdir}/")
    print(f"  contact_sheet.jpg  — {args.frames} frames, {args.columns} columns")
    if diff_path:
        print(f"  motion_diff.png    — {len(timestamps) - 1} diffs (amplified)")
    print(f"  inspection.json    — metadata + paths")


if __name__ == "__main__":
    main()
