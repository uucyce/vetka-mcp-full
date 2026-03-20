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

def build_depth_contact_sheet(frames: list[Path], meta: dict,
                              columns: int, model_key: str,
                              outdir: Path) -> tuple[Path, dict]:
    """Run depth estimation on frames and assemble depth contact sheet."""
    from video_inspection_depth import estimate_depth_batch, get_inference_stats

    imgs = [Image.open(f).convert("RGB") for f in frames]

    t0 = __import__("time").time()
    depth_maps = estimate_depth_batch(imgs, model_key=model_key, progress=True)
    elapsed = __import__("time").time() - t0
    stats = get_inference_stats(len(imgs), model_key, elapsed)

    # Build grid (same layout as RGB contact sheet)
    thumb_w, thumb_h = depth_maps[0].size
    cols = min(columns, len(depth_maps))
    rows = (len(depth_maps) + cols - 1) // cols

    sheet = Image.new("L", (cols * thumb_w, rows * thumb_h), 0)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except (OSError, IOError):
        font = ImageFont.load_default()

    step = max(1, meta["frame_count"] // len(frames))
    for i, dm in enumerate(depth_maps):
        col = i % cols
        row = i // cols
        px = col * thumb_w
        py = row * thumb_h
        sheet.paste(dm.convert("L"), (px, py))

    # Convert to RGB for timestamp overlay
    sheet_rgb = sheet.convert("RGB")
    draw = ImageDraw.Draw(sheet_rgb)
    for i in range(len(depth_maps)):
        col = i % cols
        row = i // cols
        px = col * thumb_w
        py = row * thumb_h
        frame_idx = i * step
        ts_sec = frame_idx / meta["fps"] if meta["fps"] > 0 else 0
        label = f"#{frame_idx} ({ts_sec:.1f}s)"
        draw.text((px + 8, py + 6), label, fill="yellow", font=font)

    out_path = outdir / "depth_contact_sheet.png"
    sheet_rgb.save(out_path, "PNG")
    return out_path, stats, depth_maps


def build_depth_diff(depth_maps: list[Image.Image], columns: int,
                     outdir: Path) -> Path | None:
    """Compute absdiff between consecutive depth maps, assemble grid."""
    if len(depth_maps) < 2:
        return None

    import numpy as np

    diffs = []
    for i in range(len(depth_maps) - 1):
        arr1 = np.array(depth_maps[i].convert("L"), dtype=np.float32)
        arr2 = np.array(depth_maps[i + 1].convert("L"), dtype=np.float32)
        diffs.append(np.abs(arr1 - arr2))

    # Normalize by p98 (same approach as RGB diff)
    all_vals = np.concatenate([d.ravel() for d in diffs])
    nonzero = all_vals[all_vals > 0]
    p98 = float(np.percentile(nonzero, 98)) if len(nonzero) > 0 else 1.0
    p98 = max(p98, 1.0)
    print(f"  depth diff p98={p98:.1f} (amplify: {255.0 / p98:.1f}x)")

    amplified = []
    for d in diffs:
        arr = (d * (255.0 / p98)).clip(0, 255).astype(np.uint8)
        amplified.append(Image.fromarray(arr, "L"))

    # Grid layout
    thumb_w, thumb_h = amplified[0].size
    cols = min(columns, len(amplified))
    rows = (len(amplified) + cols - 1) // cols

    grid = Image.new("L", (cols * thumb_w, rows * thumb_h), 0)
    for i, d in enumerate(amplified):
        px = (i % cols) * thumb_w
        py = (i // cols) * thumb_h
        grid.paste(d, (px, py))

    out_path = outdir / "depth_diff.png"
    grid.save(out_path, "PNG")
    return out_path


def build_motion_energy(depth_maps: list[Image.Image],
                        outdir: Path) -> Path | None:
    """Mean absdiff across all depth frames → single heatmap PNG."""
    if len(depth_maps) < 2:
        return None

    import numpy as np

    diffs = []
    for i in range(len(depth_maps) - 1):
        arr1 = np.array(depth_maps[i].convert("L"), dtype=np.float32)
        arr2 = np.array(depth_maps[i + 1].convert("L"), dtype=np.float32)
        diffs.append(np.abs(arr1 - arr2))

    # Mean across all diffs
    mean_diff = np.mean(diffs, axis=0)

    # Normalize to 0-255
    peak = mean_diff.max()
    if peak > 0:
        mean_diff = (mean_diff / peak * 255.0).astype(np.uint8)
    else:
        mean_diff = mean_diff.astype(np.uint8)

    # Apply colormap (hot): grayscale → RGB heatmap
    # Simple hot colormap: black → red → yellow → white
    h, w = mean_diff.shape
    heatmap = np.zeros((h, w, 3), dtype=np.uint8)
    norm = mean_diff.astype(np.float32) / 255.0
    # R channel: ramps up first
    heatmap[:, :, 0] = (np.clip(norm * 3.0, 0, 1) * 255).astype(np.uint8)
    # G channel: ramps up second
    heatmap[:, :, 1] = (np.clip(norm * 3.0 - 1.0, 0, 1) * 255).astype(np.uint8)
    # B channel: ramps up last
    heatmap[:, :, 2] = (np.clip(norm * 3.0 - 2.0, 0, 1) * 255).astype(np.uint8)

    out_path = outdir / "motion_energy.png"
    Image.fromarray(heatmap).save(out_path, "PNG")
    return out_path


# ---------------------------------------------------------------------------
# inspection.json (197.6)
# ---------------------------------------------------------------------------

def write_inspection_json(meta: dict, args, outdir: Path,
                          contact_path: Path | None,
                          diff_path: Path | None,
                          depth_contact_path: Path | None,
                          depth_diff_path: Path | None,
                          energy_path: Path | None,
                          timestamps: list[float],
                          depth_stats: dict | None = None) -> Path:
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
            "depth_enabled": args.depth,
            "depth_model": args.depth_model if args.depth else None,
        },
        "outputs": {
            "contact_sheet": "contact_sheet.jpg" if contact_path else None,
            "motion_diff": "motion_diff.png" if diff_path else None,
            "depth_contact_sheet": "depth_contact_sheet.png" if depth_contact_path else None,
            "depth_diff": "depth_diff.png" if depth_diff_path else None,
            "motion_energy": "motion_energy.png" if energy_path else None,
        },
        "timestamps_sampled": [round(t, 3) for t in timestamps],
    }
    if depth_stats:
        summary["depth_stats"] = depth_stats

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

    # Layer 2 params
    p.add_argument("--depth", action="store_true", help="Enable depth analysis (Layer 2)")
    p.add_argument("--depth-model", default="depth-anything-v2",
                    help="Depth model: depth-anything-v2 (default)")
    p.add_argument("--sample-rate", type=int, default=5,
                    help="Depth: every Nth frame (default: 5)")

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

    # Extract frames to temp dir (keep alive for depth processing)
    _tmpdir = tempfile.mkdtemp()
    frame_dir = Path(_tmpdir) / "frames"
    frame_dir.mkdir()

    try:
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

        # Layer 2: Depth
        depth_contact_path = None
        depth_diff_path = None
        energy_path = None
        depth_stats = None

        if args.depth:
            # Add scripts/ to path so video_inspection_depth can be imported
            scripts_dir = str(Path(__file__).parent)
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)

            print(f"[depth] Loading model: {args.depth_model}")
            depth_contact_path, depth_stats, depth_maps = build_depth_contact_sheet(
                frames, meta, args.columns, args.depth_model, outdir)
            print(f"  depth_contact_sheet.png ready ({depth_stats['fps']:.1f} fps)")

            print("[build] depth_diff.png")
            depth_diff_path = build_depth_diff(depth_maps, args.columns, outdir)

            print("[build] motion_energy.png")
            energy_path = build_motion_energy(depth_maps, outdir)

        # Keyframes (M3 placeholder)
        if args.keyframes:
            print("[skip] --keyframes not yet implemented (Phase M3)")

        # JSON manifest
        print("[write] inspection.json")
        write_inspection_json(meta, args, outdir, contact_path, diff_path,
                              depth_contact_path, depth_diff_path, energy_path,
                              timestamps, depth_stats)

        print(f"\nInspection pack ready: {outdir}/")
        print(f"  contact_sheet.jpg      — {args.frames} frames, {args.columns} columns")
        if diff_path:
            print(f"  motion_diff.png        — {len(timestamps) - 1} diffs (amplified)")
        if depth_contact_path:
            print(f"  depth_contact_sheet.png — depth maps")
        if depth_diff_path:
            print(f"  depth_diff.png         — depth change between frames")
        if energy_path:
            print(f"  motion_energy.png      — heatmap of total motion")
        print(f"  inspection.json        — metadata + paths")

    finally:
        import shutil
        shutil.rmtree(_tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
