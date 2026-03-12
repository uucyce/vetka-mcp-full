#!/usr/bin/env python3
"""Render first deterministic parallax preview videos via ffmpeg."""

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
    parser = argparse.ArgumentParser(description="Render preview.mp4 from subject RGBA, overscan plate, and layout.json.")
    parser.add_argument(
        "--overscan-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/overscan_bakeoff",
        help="Root directory with overscan stage outputs.",
    )
    parser.add_argument(
        "--outdir",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview",
        help="Output directory for preview renders.",
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


def load_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_sample_filters(values: list[str] | None) -> set[str]:
    if not values:
        return set()
    out = set()
    for value in values:
        out.add(value)
        out.add(Path(value).stem)
    return out


def motion_profile(layout: dict[str, Any]) -> dict[str, Any]:
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
        vertical_orbit = f"cos(({progress})*PI)"
    elif curve == "soft":
        eased_progress = f"((1-cos(({progress})*PI*0.5)))"
        signed_progress = f"sin((({eased_progress})-0.5)*PI)"
        vertical_orbit = f"cos(({eased_progress})*PI)"
    else:
        eased_progress = f"((1-cos(({progress})*PI))/2)"
        signed_progress = f"sin((({eased_progress})-0.5)*PI)"
        vertical_orbit = f"cos(({eased_progress})*PI)"

    travel_x_px = float(source["width"]) * float(camera["travel_x_pct"]) / 100.0
    travel_y_px = float(source["height"]) * float(camera["travel_y_pct"]) / 100.0
    bg_factor_x = 0.28
    bg_factor_y = 0.22
    fg_factor_x = 0.92
    fg_factor_y = 0.78
    zoom = float(camera["zoom"])

    bg_zoom_expr = "1.0"
    fg_zoom_expr = "1.0"

    if motion_type == "orbit":
        bg_factor_x = 1.08
        bg_factor_y = 0.44
        fg_factor_x = 0.26
        fg_factor_y = 0.18
        bg_x_motion = f"{travel_x_px * bg_factor_x:.4f}*{signed_progress}"
        bg_y_motion = f"{travel_y_px * bg_factor_y:.4f}*{vertical_orbit}"
        fg_x_motion = f"{travel_x_px * fg_factor_x:.4f}*{signed_progress}"
        fg_y_motion = f"{travel_y_px * fg_factor_y:.4f}*{vertical_orbit}"
        bg_zoom_expr = f"(1+({zoom - 1.0:.6f})*(0.18+0.22*(1-({vertical_orbit}*{vertical_orbit}))))"
        fg_zoom_expr = f"(1+({zoom - 1.0:.6f})*0.08*(1-({vertical_orbit}*{vertical_orbit})))"
    elif motion_type == "dolly-in + zoom-out":
        bg_x_motion = f"{travel_x_px * bg_factor_x * 0.35:.4f}*{signed_progress}"
        bg_y_motion = f"{travel_y_px * bg_factor_y * 0.35:.4f}*{signed_progress}"
        fg_x_motion = f"{travel_x_px * fg_factor_x * 0.55:.4f}*{signed_progress}"
        fg_y_motion = f"{travel_y_px * fg_factor_y * 0.55:.4f}*{signed_progress}"
        bg_zoom_expr = f"(1+({zoom - 1.0:.6f})*(1-{eased_progress})*0.35)"
        fg_zoom_expr = f"(1+({zoom - 1.0:.6f})*(1-{eased_progress}))"
    elif motion_type == "dolly-out + zoom-in":
        bg_x_motion = f"{travel_x_px * bg_factor_x * 0.35:.4f}*{signed_progress}"
        bg_y_motion = f"{travel_y_px * bg_factor_y * 0.35:.4f}*{signed_progress}"
        fg_x_motion = f"{travel_x_px * fg_factor_x * 0.55:.4f}*{signed_progress}"
        fg_y_motion = f"{travel_y_px * fg_factor_y * 0.55:.4f}*{signed_progress}"
        bg_zoom_expr = f"(1+({zoom - 1.0:.6f})*{eased_progress}*0.35)"
        fg_zoom_expr = f"(1+({zoom - 1.0:.6f})*{eased_progress})"
    else:
        bg_x_motion = f"{travel_x_px * bg_factor_x:.4f}*{signed_progress}"
        bg_y_motion = f"{travel_y_px * bg_factor_y:.4f}*{signed_progress}"
        fg_x_motion = f"{travel_x_px * fg_factor_x:.4f}*{signed_progress}"
        fg_y_motion = f"{travel_y_px * fg_factor_y:.4f}*{signed_progress}"

    return {
        "duration": duration,
        "fps": int(camera["fps"]),
        "motion_type": motion_type,
        "curve": curve,
        "progress_expr": progress,
        "eased_progress_expr": eased_progress,
        "bg_x_motion": bg_x_motion,
        "bg_y_motion": bg_y_motion,
        "fg_x_motion": fg_x_motion,
        "fg_y_motion": fg_y_motion,
        "bg_zoom_expr": bg_zoom_expr,
        "fg_zoom_expr": fg_zoom_expr,
        "travel_x_px": round(travel_x_px, 4),
        "travel_y_px": round(travel_y_px, 4),
    }


def build_filter_complex(
    layout: dict[str, Any],
    profile: dict[str, Any],
    supersample: float,
    internal_fps: int,
    tmix_frames: int,
) -> str:
    source_w = int(layout["source"]["width"])
    source_h = int(layout["source"]["height"])
    internal_w = max(2, int(round(source_w * supersample / 2) * 2))
    internal_h = max(2, int(round(source_h * supersample / 2) * 2))
    motion_scale = internal_w / source_w
    bg_zoom = profile["bg_zoom_expr"]
    fg_zoom = profile["fg_zoom_expr"]
    bg_x_motion = f"({profile['bg_x_motion']})*{motion_scale:.6f}"
    bg_y_motion = f"({profile['bg_y_motion']})*{motion_scale:.6f}"
    fg_x_motion = f"({profile['fg_x_motion']})*{motion_scale:.6f}"
    fg_y_motion = f"({profile['fg_y_motion']})*{motion_scale:.6f}"

    working_fps = internal_fps if internal_fps > 0 else profile["fps"]
    bg_base = f"color=c=black@0.0:s={internal_w}x{internal_h}:r={working_fps}:d={profile['duration']}[bgbase]"
    bg_scale = (
        "[0:v]"
        "format=rgba,"
        f"scale=w='iw*{supersample:.3f}*{bg_zoom}':h='ih*{supersample:.3f}*{bg_zoom}':flags=lanczos:eval=frame,"
        "setsar=1[bgrender]"
    )
    bg_overlay = (
        "[bgbase][bgrender]"
        f"overlay=x='(W-w)/2-({bg_x_motion})':"
        f"y='(H-h)/2-({bg_y_motion})':eval=frame:format=auto[bg]"
    )
    fg_scale = (
        "[1:v]"
        "format=rgba,"
        f"scale=w='iw*{supersample:.3f}*{fg_zoom}':h='ih*{supersample:.3f}*{fg_zoom}':flags=lanczos:eval=frame,"
        "setsar=1[fg]"
    )
    composite = (
        "[bg][fg]"
        f"overlay=x='(W-w)/2-({fg_x_motion})':"
        f"y='(H-h)/2-({fg_y_motion})':eval=frame:format=auto,"
        f"fps={working_fps},"
        f"scale=w={source_w}:h={source_h}:flags=lanczos,"
        "format=yuv420p[composite]"
    )
    chain = [bg_base, bg_scale, bg_overlay, fg_scale, composite]
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


def render_case(
    entry: dict[str, Any],
    out_dir: Path,
    codec: str,
    crf: int,
    supersample: float,
    internal_fps: int,
    tmix_frames: int,
) -> dict[str, Any]:
    layout = load_summary(Path(entry["best"]["layout_path"]))
    profile = motion_profile(layout)
    filter_complex = build_filter_complex(layout, profile, supersample, internal_fps, tmix_frames)
    duration = profile["duration"]
    fps = profile["fps"]
    subject_path = Path(entry["subject_rgba_path"])
    overscan_path = Path(entry["best"]["overscan_plate_path"])

    out_dir.mkdir(parents=True, exist_ok=True)
    preview_path = out_dir / "preview.mp4"
    poster_path = out_dir / "preview_poster.png"
    report_path = out_dir / "render_report.json"

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
        str(overscan_path),
        "-framerate",
        str(fps),
        "-loop",
        "1",
        "-t",
        str(duration),
        "-i",
        str(subject_path),
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

    probed = ffprobe_stream(preview_path)
    report = {
        "backend": entry["backend"],
        "sample": entry["sample"],
        "source_subject_rgba_path": str(subject_path),
        "source_overscan_plate_path": str(overscan_path),
        "layout_path": entry["best"]["layout_path"],
        "preview_path": str(preview_path),
        "poster_path": str(poster_path),
        "codec": codec,
        "crf": crf,
        "supersample": supersample,
        "internal_fps": internal_fps if internal_fps > 0 else fps,
        "tmix_frames": tmix_frames,
        "runtime_sec": round(float(runtime_sec), 5),
        "layout": layout,
        "motion_profile": profile,
        "ffmpeg": {
            "filter_complex": filter_complex,
            "command": ffmpeg_cmd,
        },
        "probe": probed,
    }
    save_json(report_path, report)
    return report


def aggregate_reports(reports: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for report in reports:
        grouped.setdefault(report["backend"], []).append(report)

    aggregate: dict[str, dict[str, Any]] = {}
    for backend, rows in grouped.items():
        runtimes = [float(row["runtime_sec"]) for row in rows]
        aggregate[backend] = {
            "entries": len(rows),
            "avg_runtime_sec": round(sum(runtimes) / len(runtimes), 5),
            "motion_types": sorted({row["layout"]["camera"]["motion_type"] for row in rows}),
            "preview_paths": [row["preview_path"] for row in rows],
        }
    return aggregate


def main() -> int:
    args = parse_args()
    overscan_root = Path(args.overscan_root).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    requested_backends = set(args.backends or [])
    requested_samples = normalize_sample_filters(args.samples)

    summary = load_summary(overscan_root / "overscan_bakeoff_summary.json")
    reports: list[dict[str, Any]] = []

    for entry in summary["entries"]:
        if requested_backends and entry["backend"] not in requested_backends:
            continue
        sample_stem = Path(entry["sample"]).stem
        if requested_samples and entry["sample"] not in requested_samples and sample_stem not in requested_samples:
            continue
        reports.append(
            render_case(
                entry=entry,
                out_dir=outdir / entry["backend"] / sample_stem,
                codec=args.codec,
                crf=args.crf,
                supersample=args.supersample,
                internal_fps=args.internal_fps,
                tmix_frames=args.tmix_frames,
            )
        )

    output = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "overscan_root": str(overscan_root),
        "outdir": str(outdir),
        "aggregate_by_backend": aggregate_reports(reports),
        "entries": reports,
    }
    save_json(outdir / "render_preview_summary.json", output)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
