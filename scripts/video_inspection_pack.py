#!/usr/bin/env python3
"""Video Inspection Pack — Video-to-AI bridge.

Transforms mp4 into lightweight artifacts (<800KB) readable by both
AI vision models and humans. Two layers: RGB (instant, ffmpeg+Pillow)
and Depth (heavy, depth model).

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
import time
from fractions import Fraction
from pathlib import Path

DEPTH_VENV_ENV = "VIDEO_INSPECTION_DEPTH_VENV_ACTIVE"


def _preflight_depth_runtime() -> None:
    """Switch to the shared depth venv before optional third-party imports."""
    if "--depth" not in sys.argv[1:]:
        return
    if os.environ.get(DEPTH_VENV_ENV) == "1":
        return

    script_path = Path(__file__).resolve()
    root_dir = script_path.parent.parent
    venv_python = root_dir / "photo_parallax_playground" / ".depth-venv" / "bin" / "python3"
    if not venv_python.exists():
        sys.exit(
            "ERROR: --depth requested but .depth-venv is missing. "
            "Run scripts/photo_parallax_depth_bootstrap.sh first."
        )

    current_python = Path(sys.executable).resolve()
    if current_python == venv_python.resolve():
        os.environ[DEPTH_VENV_ENV] = "1"
        return

    next_env = os.environ.copy()
    next_env[DEPTH_VENV_ENV] = "1"
    os.execve(str(venv_python), [str(venv_python), str(script_path), *sys.argv[1:]], next_env)


_preflight_depth_runtime()

# Layer 1 deps (minimal)
from PIL import Image, ImageChops, ImageDraw, ImageFont

# JPEG quality for weight control — 72 keeps detail, much lighter than 85
_JPEG_QUALITY = 72


# ---------------------------------------------------------------------------
# ffprobe metadata
# ---------------------------------------------------------------------------

def get_video_metadata(input_path: str) -> dict:
    """Extract video metadata via ffprobe."""
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

    video_stream = None
    for s in data.get("streams", []):
        if s.get("codec_type") == "video":
            video_stream = s
            break
    if video_stream is None:
        sys.exit(f"ERROR: no video stream found in {input_path}")

    fps_str = video_stream.get("r_frame_rate", "30/1")
    fps = float(Fraction(fps_str))
    duration = float(data.get("format", {}).get("duration", 0))

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
# Frame extraction
# ---------------------------------------------------------------------------

def extract_frames(input_path: str, frame_dir: Path, meta: dict,
                   n_frames: int, width: int, crop: str | None) -> list[Path]:
    """Extract N uniformly-spaced frames via ffmpeg."""
    step = max(1, meta["frame_count"] // n_frames)

    vf_parts = []
    if crop:
        x, y, w, h = (int(v) for v in crop.split(","))
        vf_parts.append(f"crop={w}:{h}:{x}:{y}")
    vf_parts.append(f"select=not(mod(n\\,{step}))")
    vf_parts.append(f"scale={width}:-1")
    vf = ",".join(vf_parts)

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", vf, "-vsync", "vfr",
        str(frame_dir / "frame_%04d.png"),
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    frames = sorted(frame_dir.glob("frame_*.png"))
    return frames[:n_frames]


def extract_depth_frames(input_path: str, frame_dir: Path, meta: dict,
                         sample_rate: int, width: int, crop: str | None) -> list[Path]:
    """Extract frames for depth at --sample-rate density (every Nth source frame)."""
    vf_parts = []
    if crop:
        x, y, w, h = (int(v) for v in crop.split(","))
        vf_parts.append(f"crop={w}:{h}:{x}:{y}")
    vf_parts.append(f"select=not(mod(n\\,{sample_rate}))")
    vf_parts.append(f"scale={width}:-1")
    vf = ",".join(vf_parts)

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", vf, "-vsync", "vfr",
        str(frame_dir / "dframe_%04d.png"),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return sorted(frame_dir.glob("dframe_*.png"))


def compute_timestamps(meta: dict, n_frames: int) -> list[float]:
    """Compute real timestamps for N uniformly-sampled frames."""
    step = max(1, meta["frame_count"] // n_frames)
    return [
        round((i * step) / meta["fps"], 3) if meta["fps"] > 0 else 0.0
        for i in range(n_frames)
    ]


def compute_depth_timestamps(meta: dict, sample_rate: int, n_extracted: int) -> list[float]:
    """Compute real timestamps for depth frames at sample_rate density."""
    return [
        round((i * sample_rate) / meta["fps"], 3) if meta["fps"] > 0 else 0.0
        for i in range(n_extracted)
    ]


# ---------------------------------------------------------------------------
# Font helper
# ---------------------------------------------------------------------------

def _get_font(size: int = 18):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
    except (OSError, IOError):
        return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Contact sheet
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
    font = _get_font(18)

    step = max(1, meta["frame_count"] // len(frames))
    for i, img in enumerate(imgs):
        px = (i % cols) * thumb_w
        py = (i // cols) * thumb_h
        sheet.paste(img, (px, py))
        frame_idx = i * step
        ts_sec = frame_idx / meta["fps"] if meta["fps"] > 0 else 0
        draw.text((px + 8, py + 6), f"#{frame_idx} ({ts_sec:.1f}s)",
                  fill="white", font=font)

    out_path = outdir / "contact_sheet.jpg"
    sheet.save(out_path, "JPEG", quality=_JPEG_QUALITY)
    return out_path


# ---------------------------------------------------------------------------
# Motion diff grid
# ---------------------------------------------------------------------------

def build_motion_diff(frames: list[Path], columns: int,
                      outdir: Path) -> tuple[Path | None, dict]:
    """Compute absdiff, p98-amplify, assemble grid. Returns (path, stats)."""
    import numpy as np

    if len(frames) < 2:
        return None, {}

    diffs = []
    for i in range(len(frames) - 1):
        im1 = Image.open(frames[i]).convert("RGB")
        im2 = Image.open(frames[i + 1]).convert("RGB")
        diffs.append(ImageChops.difference(im1, im2))

    all_pixels = np.concatenate([np.array(d).ravel() for d in diffs])
    nonzero = all_pixels[all_pixels > 0]
    p98 = float(np.percentile(nonzero, 98)) if len(nonzero) > 0 else 1.0
    p98 = max(p98, 1.0)
    mean_motion = float(nonzero.mean()) if len(nonzero) > 0 else 0.0

    # Spatial concentration: fraction of pixels above median motion
    total_px = all_pixels.size
    active_px = int((all_pixels > p98 * 0.3).sum())
    motion_concentration = round(active_px / max(total_px, 1), 4)

    print(f"  diff: max={all_pixels.max()}, p98={p98:.1f}, "
          f"concentration={motion_concentration:.3f}")

    amplified = []
    for d in diffs:
        arr = (np.array(d, dtype=np.float32) * (255.0 / p98)).clip(0, 255).astype(np.uint8)
        amplified.append(Image.fromarray(arr))

    thumb_w, thumb_h = amplified[0].size
    cols = min(columns, len(amplified))
    rows = (len(amplified) + cols - 1) // cols

    grid = Image.new("RGB", (cols * thumb_w, rows * thumb_h), (0, 0, 0))
    for i, d in enumerate(amplified):
        grid.paste(d, ((i % cols) * thumb_w, (i // cols) * thumb_h))

    out_path = outdir / "motion_diff.jpg"
    grid.save(out_path, "JPEG", quality=_JPEG_QUALITY)

    stats = {
        "p98": round(p98, 2),
        "mean_motion": round(mean_motion, 2),
        "motion_concentration": motion_concentration,
    }
    return out_path, stats


# ---------------------------------------------------------------------------
# Depth contact sheet
# ---------------------------------------------------------------------------

def build_depth_contact_sheet(depth_frames: list[Path], meta: dict,
                              columns: int, model_key: str, sample_rate: int,
                              outdir: Path) -> tuple[Path, dict, list]:
    """Run depth estimation on frames and assemble depth contact sheet."""
    from video_inspection_depth import estimate_depth_batch, get_inference_stats

    imgs = [Image.open(f).convert("RGB") for f in depth_frames]

    t0 = time.time()
    depth_maps = estimate_depth_batch(imgs, model_key=model_key, progress=True)
    elapsed = time.time() - t0
    stats = get_inference_stats(len(imgs), model_key, elapsed)

    thumb_w, thumb_h = depth_maps[0].size
    cols = min(columns, len(depth_maps))
    rows = (len(depth_maps) + cols - 1) // cols

    # Grayscale sheet — much lighter than RGB
    sheet = Image.new("L", (cols * thumb_w, rows * thumb_h), 0)
    for i, dm in enumerate(depth_maps):
        sheet.paste(dm.convert("L"),
                    ((i % cols) * thumb_w, (i // cols) * thumb_h))

    # Convert to RGB for labels
    sheet_rgb = sheet.convert("RGB")
    draw = ImageDraw.Draw(sheet_rgb)
    font = _get_font(18)
    for i in range(len(depth_maps)):
        px = (i % cols) * thumb_w
        py = (i // cols) * thumb_h
        frame_idx = i * sample_rate
        ts_sec = frame_idx / meta["fps"] if meta["fps"] > 0 else 0
        draw.text((px + 8, py + 6), f"#{frame_idx} ({ts_sec:.1f}s)",
                  fill="yellow", font=font)

    # Save as JPEG — grayscale content compresses well
    out_path = outdir / "depth_contact_sheet.jpg"
    sheet_rgb.save(out_path, "JPEG", quality=_JPEG_QUALITY)
    return out_path, stats, depth_maps


# ---------------------------------------------------------------------------
# Depth diff grid
# ---------------------------------------------------------------------------

def build_depth_diff(depth_maps: list[Image.Image], columns: int,
                     outdir: Path) -> tuple[Path | None, dict]:
    """Compute absdiff between consecutive depth maps, assemble grid."""
    import numpy as np

    if len(depth_maps) < 2:
        return None, {}

    diffs = []
    for i in range(len(depth_maps) - 1):
        arr1 = np.array(depth_maps[i].convert("L"), dtype=np.float32)
        arr2 = np.array(depth_maps[i + 1].convert("L"), dtype=np.float32)
        diffs.append(np.abs(arr1 - arr2))

    all_vals = np.concatenate([d.ravel() for d in diffs])
    nonzero = all_vals[all_vals > 0]
    p98 = float(np.percentile(nonzero, 98)) if len(nonzero) > 0 else 1.0
    p98 = max(p98, 1.0)
    mean_depth_motion = float(nonzero.mean()) if len(nonzero) > 0 else 0.0
    total_px = all_vals.size
    active_px = int((all_vals > p98 * 0.3).sum())
    depth_motion_concentration = round(active_px / max(total_px, 1), 4)

    print(f"  depth diff: p98={p98:.1f}, concentration={depth_motion_concentration:.3f}")

    amplified = []
    for d in diffs:
        arr = (d * (255.0 / p98)).clip(0, 255).astype(np.uint8)
        amplified.append(Image.fromarray(arr, "L"))

    thumb_w, thumb_h = amplified[0].size
    cols = min(columns, len(amplified))
    rows = (len(amplified) + cols - 1) // cols

    grid = Image.new("L", (cols * thumb_w, rows * thumb_h), 0)
    for i, d in enumerate(amplified):
        grid.paste(d, ((i % cols) * thumb_w, (i // cols) * thumb_h))

    out_path = outdir / "depth_diff.png"
    grid.save(out_path, "PNG")

    stats = {
        "p98": round(p98, 2),
        "mean_depth_motion": round(mean_depth_motion, 2),
        "depth_motion_concentration": depth_motion_concentration,
    }
    return out_path, stats


# ---------------------------------------------------------------------------
# Motion energy heatmap
# ---------------------------------------------------------------------------

def build_motion_energy(depth_maps: list[Image.Image],
                        outdir: Path) -> Path | None:
    """Mean absdiff across all depth frames -> single heatmap PNG."""
    import numpy as np

    if len(depth_maps) < 2:
        return None

    diffs = []
    for i in range(len(depth_maps) - 1):
        arr1 = np.array(depth_maps[i].convert("L"), dtype=np.float32)
        arr2 = np.array(depth_maps[i + 1].convert("L"), dtype=np.float32)
        diffs.append(np.abs(arr1 - arr2))

    mean_diff = np.mean(diffs, axis=0)
    peak = mean_diff.max()
    if peak > 0:
        mean_diff = (mean_diff / peak * 255.0).astype(np.uint8)
    else:
        mean_diff = mean_diff.astype(np.uint8)

    # Hot colormap: black -> red -> yellow -> white
    h, w = mean_diff.shape
    heatmap = np.zeros((h, w, 3), dtype=np.uint8)
    norm = mean_diff.astype(np.float32) / 255.0
    heatmap[:, :, 0] = (np.clip(norm * 3.0, 0, 1) * 255).astype(np.uint8)
    heatmap[:, :, 1] = (np.clip(norm * 3.0 - 1.0, 0, 1) * 255).astype(np.uint8)
    heatmap[:, :, 2] = (np.clip(norm * 3.0 - 2.0, 0, 1) * 255).astype(np.uint8)

    out_path = outdir / "motion_energy.png"
    Image.fromarray(heatmap).save(out_path, "PNG")
    return out_path


# ---------------------------------------------------------------------------
# Forensic analysis (deterministic heuristics, no LLM)
# ---------------------------------------------------------------------------

def compute_forensic_analysis(meta: dict, rgb_stats: dict,
                              depth_maps: list | None,
                              depth_diff_stats: dict) -> dict:
    """Machine-readable forensic summary for inspection.json."""
    import numpy as np

    analysis = {
        "rgb_motion": {
            "p98_intensity": rgb_stats.get("p98", 0),
            "mean_intensity": rgb_stats.get("mean_motion", 0),
            "spatial_concentration": rgb_stats.get("motion_concentration", 0),
        },
    }

    if depth_maps and len(depth_maps) >= 2:
        # Rigid-slab risk: if depth variance across frames is very low,
        # the scene looks like a flat cutout being translated (cardboard)
        depth_arrays = [np.array(dm.convert("L"), dtype=np.float32) for dm in depth_maps]
        per_frame_std = [float(a.std()) for a in depth_arrays]
        mean_depth_std = round(float(np.mean(per_frame_std)), 2)

        # Cross-frame depth variance: how much does the depth structure change?
        stacked = np.stack(depth_arrays, axis=0)
        temporal_var = float(stacked.var(axis=0).mean())

        # Rigid slab: low temporal variance + high per-frame std = flat plate moving
        # Weak bg separation: low per-frame std = everything at similar depth
        rigid_slab_risk = "high" if temporal_var < 2.0 and mean_depth_std > 40 else \
                          "medium" if temporal_var < 5.0 else "low"
        weak_bg_separation = "high" if mean_depth_std < 20 else \
                             "medium" if mean_depth_std < 35 else "low"

        analysis["depth_motion"] = {
            "p98_intensity": depth_diff_stats.get("p98", 0),
            "mean_intensity": depth_diff_stats.get("mean_depth_motion", 0),
            "spatial_concentration": depth_diff_stats.get("depth_motion_concentration", 0),
        }
        analysis["depth_quality"] = {
            "mean_per_frame_std": mean_depth_std,
            "temporal_variance": round(temporal_var, 2),
            "rigid_slab_risk": rigid_slab_risk,
            "weak_background_separation_risk": weak_bg_separation,
        }

    return analysis


# ---------------------------------------------------------------------------
# inspection.json
# ---------------------------------------------------------------------------

def write_inspection_json(meta: dict, args, outdir: Path,
                          contact_path: Path | None,
                          diff_path: Path | None,
                          depth_contact_path: Path | None,
                          depth_diff_path: Path | None,
                          energy_path: Path | None,
                          timestamps: list[float],
                          depth_timestamps: list[float] | None,
                          depth_stats: dict | None,
                          analysis: dict | None,
                          file_sizes: dict | None) -> Path:
    """Write inspection summary JSON."""
    summary = {
        "version": "1.1",
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
            "depth_sample_rate": args.sample_rate if args.depth else None,
        },
        "outputs": {
            "contact_sheet": "contact_sheet.jpg" if contact_path else None,
            "motion_diff": "motion_diff.jpg" if diff_path else None,
            "depth_contact_sheet": "depth_contact_sheet.jpg" if depth_contact_path else None,
            "depth_diff": "depth_diff.png" if depth_diff_path else None,
            "motion_energy": "motion_energy.png" if energy_path else None,
        },
        "timestamps_sampled": timestamps,
    }
    if depth_timestamps:
        summary["depth_timestamps_sampled"] = depth_timestamps
    if depth_stats:
        summary["depth_stats"] = depth_stats
    if analysis:
        summary["analysis"] = analysis
    if file_sizes:
        summary["file_sizes_kb"] = file_sizes

    out_path = outdir / "inspection.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    return out_path


# ---------------------------------------------------------------------------
# File size helper
# ---------------------------------------------------------------------------

def collect_file_sizes(outdir: Path) -> dict:
    """Collect sizes of all output files in KB."""
    sizes = {}
    total = 0
    for f in sorted(outdir.iterdir()):
        if f.is_file() and f.name != "inspection.json":
            kb = round(f.stat().st_size / 1024, 1)
            sizes[f.name] = kb
            total += kb
    sizes["_total_kb"] = round(total, 1)
    return sizes


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Video Inspection Pack — Video-to-AI bridge",
    )
    p.add_argument("--input", required=True, help="Input MP4 path")
    p.add_argument("--outdir", required=True, help="Output directory")

    # Layer 1
    p.add_argument("--frames", type=int, default=8,
                   help="Frames for RGB contact sheet (default: 8)")
    p.add_argument("--columns", type=int, default=4,
                   help="Columns in grid (default: 4)")
    p.add_argument("--width", type=int, default=640,
                   help="Output width in px (default: 640)")
    p.add_argument("--crop", type=str, default=None, help="ROI crop: x,y,w,h")

    # Layer 2
    p.add_argument("--depth", action="store_true",
                   help="Enable depth analysis (Layer 2)")
    p.add_argument("--depth-model", default="depth-anything-v2",
                   help="Depth model (default: depth-anything-v2)")
    p.add_argument("--sample-rate", type=int, default=5,
                   help="Depth: every Nth source frame (default: 5)")

    # Advanced
    p.add_argument("--keyframes", action="store_true",
                   help="Scene-change detection instead of uniform [M3]")

    return p


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = build_cli()
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        sys.exit(f"ERROR: input file not found: {args.input}")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"[probe] {args.input}")
    meta = get_video_metadata(args.input)
    print(f"  {meta['width']}x{meta['height']}, {meta['fps']}fps, "
          f"{meta['duration']:.1f}s, {meta['frame_count']} frames, {meta['codec']}")

    _tmpdir = tempfile.mkdtemp()
    frame_dir = Path(_tmpdir) / "frames"
    frame_dir.mkdir()

    try:
        # --- Layer 1: RGB ---
        print(f"[extract] {args.frames} RGB frames (uniform, width={args.width})")
        frames = extract_frames(args.input, frame_dir, meta,
                                args.frames, args.width, args.crop)
        print(f"  extracted {len(frames)} frames")
        if not frames:
            sys.exit("ERROR: no frames extracted")

        timestamps = compute_timestamps(meta, len(frames))

        print("[build] contact_sheet.jpg")
        contact_path = build_contact_sheet(frames, meta, args.columns,
                                           args.width, outdir)

        print("[build] motion_diff.png")
        diff_path, rgb_stats = build_motion_diff(frames, args.columns, outdir)

        # --- Layer 2: Depth ---
        depth_contact_path = None
        depth_diff_path = None
        energy_path = None
        depth_stats = None
        depth_maps = None
        depth_diff_stats = {}
        depth_timestamps = None
        analysis = None

        if args.depth:
            scripts_dir = str(Path(__file__).parent)
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)

            # Extract separate depth frames at --sample-rate density
            depth_frame_dir = Path(_tmpdir) / "depth_frames"
            depth_frame_dir.mkdir()

            print(f"[extract] depth frames (every {args.sample_rate}th, width={args.width})")
            depth_frames = extract_depth_frames(
                args.input, depth_frame_dir, meta,
                args.sample_rate, args.width, args.crop)
            print(f"  extracted {len(depth_frames)} depth frames")

            if depth_frames:
                depth_timestamps = compute_depth_timestamps(
                    meta, args.sample_rate, len(depth_frames))

                print(f"[depth] Loading model: {args.depth_model}")
                depth_contact_path, depth_stats, depth_maps = build_depth_contact_sheet(
                    depth_frames, meta, args.columns, args.depth_model,
                    args.sample_rate, outdir)
                print(f"  depth_contact_sheet.jpg ({depth_stats['fps']:.1f} fps)")

                print("[build] depth_diff.png")
                depth_diff_path, depth_diff_stats = build_depth_diff(
                    depth_maps, args.columns, outdir)

                print("[build] motion_energy.png")
                energy_path = build_motion_energy(depth_maps, outdir)

        # --- Forensic analysis ---
        print("[analyze] forensic heuristics")
        analysis = compute_forensic_analysis(
            meta, rgb_stats, depth_maps, depth_diff_stats)

        if args.keyframes:
            print("[skip] --keyframes not yet implemented (Phase M3)")

        # --- Collect sizes and write JSON ---
        file_sizes = collect_file_sizes(outdir)

        print("[write] inspection.json")
        write_inspection_json(meta, args, outdir, contact_path, diff_path,
                              depth_contact_path, depth_diff_path, energy_path,
                              timestamps, depth_timestamps, depth_stats,
                              analysis, file_sizes)

        # --- Summary ---
        print(f"\nInspection pack ready: {outdir}/")
        for name, kb in sorted(file_sizes.items()):
            if name.startswith("_"):
                continue
            print(f"  {name:<30s} {kb:>7.1f} KB")
        print(f"  {'TOTAL':<30s} {file_sizes['_total_kb']:>7.1f} KB")

        if analysis and "depth_quality" in analysis:
            dq = analysis["depth_quality"]
            print(f"\n  forensic: rigid_slab={dq['rigid_slab_risk']}, "
                  f"weak_bg={dq['weak_background_separation_risk']}, "
                  f"depth_std={dq['mean_per_frame_std']}")

    finally:
        import shutil
        shutil.rmtree(_tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
