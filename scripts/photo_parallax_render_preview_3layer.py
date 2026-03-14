#!/usr/bin/env python3
"""Render first 3-layer preview videos for flagged parallax scenes."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import time
from pathlib import Path
from typing import Any

from photo_parallax_subject_plate_bakeoff import save_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render 3-layer preview.mp4 from planned layer PNGs.")
    parser.add_argument(
        "--three-layer-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/three_layer_plan",
        help="Root directory with three-layer plans.",
    )
    parser.add_argument(
        "--render-preview-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview",
        help="Root directory with original 2-layer preview summary.",
    )
    parser.add_argument(
        "--outdir",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_3layer",
        help="Output directory for 3-layer preview renders.",
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
    parser.add_argument(
        "--codec",
        default="libx264",
        help="Video codec for preview render.",
    )
    parser.add_argument(
        "--crf",
        type=int,
        default=18,
        help="CRF for preview render.",
    )
    parser.add_argument(
        "--supersample",
        type=float,
        default=2.0,
        help="Internal render supersampling factor before downscale.",
    )
    parser.add_argument(
        "--internal-fps",
        type=int,
        default=50,
        help="Internal render fps before final downsample. 0 keeps camera fps.",
    )
    parser.add_argument(
        "--tmix-frames",
        type=int,
        default=3,
        help="Temporal mix frame count applied before final output fps. 0 disables tmix.",
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


def map_render_entries(summary: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(entry["backend"], entry["sample"]): entry for entry in summary["entries"]}


def layer_map(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {layer["id"]: layer for layer in plan["layers"]}


def build_layer_profile(layout: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    camera = layout["camera"]
    source = layout["source"]
    motion_type = camera["motion_type"]
    curve = str(camera.get("curve", "ease")).lower()
    duration = float(camera["duration_sec"])
    speed = float(camera.get("speed", 1.0))
    progress = f"min(1,max(0,(t/{duration})*{speed}))"
    if curve == "linear":
        eased_progress = progress
        signed_progress = f"((2*({progress}))-1)"
        cosine = f"cos(({progress})*PI)"
    elif curve == "soft":
        eased_progress = f"((1-cos(({progress})*PI*0.5)))"
        signed_progress = f"sin((({eased_progress})-0.5)*PI)"
        cosine = f"cos(({eased_progress})*PI)"
    else:
        eased_progress = f"((1-cos(({progress})*PI))/2)"
        signed_progress = f"sin((({eased_progress})-0.5)*PI)"
        cosine = f"cos(({eased_progress})*PI)"
    zoom = float(camera["zoom"])
    zoom_delta = zoom - 1.0
    layers = layer_map(plan)

    def motion_expr(layer_id: str, axis: str) -> str:
        factor = float(layers[layer_id][f"motion_factor_{axis}"])
        travel_pct = float(camera[f"travel_{axis}_pct"])
        pixels = float(source["width"] if axis == "x" else source["height"]) * travel_pct / 100.0 * factor
        if motion_type == "orbit":
            orbit_x = {"background_far": 1.12, "midground": 0.56, "foreground": 0.24}
            orbit_y = {"background_far": 0.48, "midground": 0.28, "foreground": 0.16}
            pixels *= orbit_x[layer_id] if axis == "x" else orbit_y[layer_id]
        if motion_type == "orbit" and axis == "y":
            return f"{pixels:.4f}*{cosine}"
        if motion_type.startswith("dolly"):
            pixels *= 0.58 if layer_id != "foreground" else 0.72
        return f"{pixels:.4f}*{signed_progress}"

    def zoom_expr(layer_id: str) -> str:
        factor = {"background_far": 0.22, "midground": 0.58, "foreground": 1.0}[layer_id]
        if motion_type == "orbit":
            orbit_factor = {"background_far": 0.34, "midground": 0.16, "foreground": 0.08}[layer_id]
            return f"(1+({zoom_delta:.6f})*{orbit_factor:.2f}*(1-({cosine}*{cosine})))"
        if motion_type == "dolly-out + zoom-in":
            return f"(1+({zoom_delta:.6f})*{eased_progress}*{factor:.2f})"
        if motion_type == "dolly-in + zoom-out":
            return f"(1+({zoom_delta:.6f})*(1-{eased_progress})*{factor:.2f})"
        return "1.0"

    return {
        "duration": duration,
        "fps": int(camera["fps"]),
        "motion_type": motion_type,
        "curve": curve,
        "progress_expr": progress,
        "eased_progress_expr": eased_progress,
        "source_width": int(source["width"]),
        "source_height": int(source["height"]),
        "bg_x_motion": motion_expr("background_far", "x"),
        "bg_y_motion": motion_expr("background_far", "y"),
        "mid_x_motion": motion_expr("midground", "x"),
        "mid_y_motion": motion_expr("midground", "y"),
        "fg_x_motion": motion_expr("foreground", "x"),
        "fg_y_motion": motion_expr("foreground", "y"),
        "bg_zoom_expr": zoom_expr("background_far"),
        "mid_zoom_expr": zoom_expr("midground"),
        "fg_zoom_expr": zoom_expr("foreground"),
    }


def build_filter_complex(profile: dict[str, Any], supersample: float, internal_fps: int, tmix_frames: int) -> str:
    source_w = profile["source_width"]
    source_h = profile["source_height"]
    internal_w = max(2, int(round(source_w * supersample / 2) * 2))
    internal_h = max(2, int(round(source_h * supersample / 2) * 2))
    motion_scale = internal_w / source_w
    bg_x_motion = f"({profile['bg_x_motion']})*{motion_scale:.6f}"
    bg_y_motion = f"({profile['bg_y_motion']})*{motion_scale:.6f}"
    mid_x_motion = f"({profile['mid_x_motion']})*{motion_scale:.6f}"
    mid_y_motion = f"({profile['mid_y_motion']})*{motion_scale:.6f}"
    fg_x_motion = f"({profile['fg_x_motion']})*{motion_scale:.6f}"
    fg_y_motion = f"({profile['fg_y_motion']})*{motion_scale:.6f}"
    working_fps = internal_fps if internal_fps > 0 else profile["fps"]
    bg_base = f"color=c=black@0.0:s={internal_w}x{internal_h}:r={working_fps}:d={profile['duration']}[bgbase]"
    bg_scale = (
        "[0:v]"
        "format=rgba,"
        f"scale=w='iw*{supersample:.3f}*{profile['bg_zoom_expr']}':h='ih*{supersample:.3f}*{profile['bg_zoom_expr']}':flags=lanczos:eval=frame,"
        "setsar=1[bgrender]"
    )
    bg_overlay = (
        "[bgbase][bgrender]"
        f"overlay=x='(W-w)/2-({bg_x_motion})':"
        f"y='(H-h)/2-({bg_y_motion})':eval=frame:format=auto[bg]"
    )
    mid_scale = (
        "[1:v]"
        "format=rgba,"
        f"scale=w='iw*{supersample:.3f}*{profile['mid_zoom_expr']}':h='ih*{supersample:.3f}*{profile['mid_zoom_expr']}':flags=lanczos:eval=frame,"
        "setsar=1[mid]"
    )
    fg_scale = (
        "[2:v]"
        "format=rgba,"
        f"scale=w='iw*{supersample:.3f}*{profile['fg_zoom_expr']}':h='ih*{supersample:.3f}*{profile['fg_zoom_expr']}':flags=lanczos:eval=frame,"
        "setsar=1[fg]"
    )
    bg_mid = (
        "[bg][mid]"
        f"overlay=x='(W-w)/2-({mid_x_motion})':"
        f"y='(H-h)/2-({mid_y_motion})':eval=frame:format=auto[bm]"
    )
    composite = (
        "[bm][fg]"
        f"overlay=x='(W-w)/2-({fg_x_motion})':"
        f"y='(H-h)/2-({fg_y_motion})':eval=frame:format=auto,"
        f"fps={working_fps},"
        f"scale=w={source_w}:h={source_h}:flags=lanczos,"
        "format=yuv420p[composite]"
    )
    chain = [bg_base, bg_scale, bg_overlay, mid_scale, fg_scale, bg_mid, composite]
    if tmix_frames and tmix_frames > 1:
        weights = " ".join(["1"] * tmix_frames)
        chain.append(f"[composite]tmix=frames={tmix_frames}:weights='{weights}',fps={profile['fps']}[v]")
    else:
        chain.append(f"[composite]fps={profile['fps']}[v]")
    return ";".join(chain)


def ffprobe_stream(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate,duration,nb_frames",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    stream = payload["streams"][0]
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "r_frame_rate": stream.get("r_frame_rate"),
        "duration": float(stream.get("duration", 0.0)),
        "nb_frames": stream.get("nb_frames"),
    }


def build_compare_video(original_preview: Path, preview_3layer: Path, out_path: Path, fps: int) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(original_preview),
            "-i",
            str(preview_3layer),
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
            str(out_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def render_case(
    plan: dict[str, Any],
    render_entry: dict[str, Any],
    out_dir: Path,
    codec: str,
    crf: int,
    supersample: float,
    internal_fps: int,
    tmix_frames: int,
) -> dict[str, Any]:
    layout = render_entry["layout"]
    profile = build_layer_profile(layout, plan)
    duration = profile["duration"]
    fps = profile["fps"]
    filter_complex = build_filter_complex(profile, supersample, internal_fps, tmix_frames)

    foreground_path = Path(plan["paths"]["foreground_rgba"])
    midground_path = Path(plan["paths"]["midground_rgba"])
    background_path = Path(plan["paths"]["background_far_rgba"])
    preview_path = out_dir / "preview_3layer.mp4"
    poster_path = out_dir / "preview_3layer_poster.png"
    compare_path = out_dir / "compare_2layer_vs_3layer.mp4"
    report_path = out_dir / "render_report_3layer.json"
    out_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps),
        "-loop",
        "1",
        "-t",
        str(duration),
        "-i",
        str(background_path),
        "-framerate",
        str(fps),
        "-loop",
        "1",
        "-t",
        str(duration),
        "-i",
        str(midground_path),
        "-framerate",
        str(fps),
        "-loop",
        "1",
        "-t",
        str(duration),
        "-i",
        str(foreground_path),
        "-filter_complex",
        filter_complex,
        "-map",
        "[v]",
        "-r",
        str(fps),
        "-c:v",
        codec,
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(preview_path),
    ]

    started = time.perf_counter()
    subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
    runtime_sec = time.perf_counter() - started

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(preview_path),
            "-ss",
            f"{duration / 2:.3f}",
            "-frames:v",
            "1",
            str(poster_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    build_compare_video(Path(render_entry["preview_path"]), preview_path, compare_path, fps)
    probe = ffprobe_stream(preview_path)
    report = {
        "backend": plan["backend"],
        "sample": plan["sample"],
        "source_review_status": plan["source_review_status"],
        "preview_path": str(preview_path),
        "poster_path": str(poster_path),
        "compare_path": str(compare_path),
        "runtime_sec": round(runtime_sec, 5),
        "supersample": supersample,
        "internal_fps": internal_fps if internal_fps > 0 else fps,
        "tmix_frames": tmix_frames,
        "codec": codec,
        "crf": crf,
        "probe": probe,
        "layout": layout,
        "three_layer_plan_path": plan["paths"]["three_layer_plan"],
        "source_two_layer_preview_path": render_entry["preview_path"],
        "motion_profile": profile,
        "ffmpeg": {
            "filter_complex": filter_complex,
            "command": ffmpeg_cmd,
        },
    }
    save_json(report_path, report)
    return report


def main() -> int:
    args = parse_args()
    three_layer_root = Path(args.three_layer_root).expanduser().resolve()
    render_preview_root = Path(args.render_preview_root).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    requested_backends = set(args.backends or [])
    requested_samples = normalize_sample_filters(args.samples)

    plan_summary = load_summary(three_layer_root / "three_layer_plan_summary.json")
    render_entries = map_render_entries(load_summary(render_preview_root / "render_preview_summary.json"))

    reports: list[dict[str, Any]] = []
    for plan in plan_summary["entries"]:
        if requested_backends and plan["backend"] not in requested_backends:
            continue
        if requested_samples and plan["sample"] not in requested_samples and Path(plan["sample"]).stem not in requested_samples:
            continue
        render_entry = render_entries[(plan["backend"], plan["sample"])]
        sample_stem = Path(plan["sample"]).stem
        report = render_case(
            plan=plan,
            render_entry=render_entry,
            out_dir=outdir / plan["backend"] / sample_stem,
            codec=args.codec,
            crf=args.crf,
            supersample=args.supersample,
            internal_fps=args.internal_fps,
            tmix_frames=args.tmix_frames,
        )
        reports.append(report)

    summary = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "three_layer_root": str(three_layer_root),
        "render_preview_root": str(render_preview_root),
        "outdir": str(outdir),
        "entries": reports,
    }
    save_json(outdir / "render_preview_3layer_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
