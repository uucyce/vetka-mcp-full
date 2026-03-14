#!/usr/bin/env python3
"""Render plate-aware preview videos from exported multi-plate assets."""

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
    parser = argparse.ArgumentParser(description="Render preview_multiplate.mp4 from exported plate assets.")
    parser.add_argument(
        "--plate-export-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports",
        help="Root directory with exported plate asset packs.",
    )
    parser.add_argument(
        "--outdir",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate",
        help="Output directory for multi-plate renders.",
    )
    parser.add_argument(
        "--sample",
        action="append",
        dest="samples",
        help="Limit run to one or more sample ids.",
    )
    parser.add_argument("--codec", default="libx264", help="Video codec for preview render.")
    parser.add_argument("--crf", type=int, default=18, help="CRF for preview render.")
    parser.add_argument("--supersample", type=float, default=2.0, help="Internal render supersampling factor.")
    parser.add_argument("--internal-fps", type=int, default=50, help="Internal render fps before final downsample.")
    parser.add_argument("--tmix-frames", type=int, default=3, help="Temporal mix frame count.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ffprobe_stream(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
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
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    stream = payload["streams"][0]
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "r_frame_rate": stream.get("r_frame_rate"),
        "duration": float(stream.get("duration", 0.0)),
        "nb_frames": stream.get("nb_frames"),
    }


def motion_profile(layout: dict[str, Any]) -> dict[str, Any]:
    camera = layout["camera"]
    source = layout["source"]
    duration = float(camera["durationSec"])
    fps = int(camera["fps"])
    motion_type = str(camera["motionType"])
    progress = f"min(1,max(0,t/{duration}))"
    signed = f"sin((({progress})-0.5)*PI)"
    cosine = f"cos(({progress})*PI)"
    zoom = float(camera["zoom"])
    travel_x_px = float(source["width"]) * float(camera["travelXPct"]) / 100.0
    travel_y_px = float(source["height"]) * float(camera["travelYPct"]) / 100.0
    return {
        "duration": duration,
        "fps": fps,
        "motion_type": motion_type,
        "progress": progress,
        "signed": signed,
        "cosine": cosine,
        "zoom": zoom,
        "travel_x_px": travel_x_px,
        "travel_y_px": travel_y_px,
        "source_width": int(source["width"]),
        "source_height": int(source["height"]),
    }


def plate_zoom_expr(profile: dict[str, Any], strength: float) -> str:
    motion_type = profile["motion_type"]
    zoom_delta = profile["zoom"] - 1.0
    progress = profile["progress"]
    cosine = profile["cosine"]
    if motion_type == "orbit":
      return f"(1+({zoom_delta:.6f})*{strength:.4f}*0.14*(1-({cosine}*{cosine})))"
    if motion_type == "dolly-out + zoom-in":
      return f"(1+({zoom_delta:.6f})*{progress}*{strength:.4f})"
    if motion_type == "dolly-in + zoom-out":
      return f"(1+({zoom_delta:.6f})*(1-{progress})*{strength:.4f})"
    return f"(1+({zoom_delta:.6f})*{strength:.4f}*0.32)"


def plate_motion_expr(profile: dict[str, Any], plate: dict[str, Any], axis: str) -> str:
    base = profile["travel_x_px"] if axis == "x" else profile["travel_y_px"]
    signed = profile["signed"]
    cosine = profile["cosine"]
    strength = float(plate["parallaxStrength"])
    damping = float(plate["motionDamping"])
    pixels = base * strength * damping
    if profile["motion_type"] == "orbit":
        if axis == "x":
            return f"{pixels:.4f}*{signed}"
        return f"{(pixels * 0.52):.4f}*{cosine}"
    if profile["motion_type"].startswith("dolly"):
        return f"{(pixels * 0.72):.4f}*{signed}"
    return f"{pixels:.4f}*{signed}"


def build_filter_complex(
    layout: dict[str, Any],
    manifest: dict[str, Any],
    supersample: float,
    internal_fps: int,
    tmix_frames: int,
    asset_scale: float,
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    profile = motion_profile(layout)
    source_w = profile["source_width"]
    source_h = profile["source_height"]
    internal_w = max(2, int(round(source_w * supersample / 2) * 2))
    internal_h = max(2, int(round(source_h * supersample / 2) * 2))
    motion_scale = internal_w / source_w
    working_fps = internal_fps if internal_fps > 0 else profile["fps"]

    visible_rgba = [plate for plate in manifest["exportedPlates"] if plate.get("visible") and "rgba" in plate.get("files", {})]
    special_clean = [plate for plate in manifest["exportedPlates"] if "clean" in plate.get("files", {})]
    layout_by_id = {plate["id"]: plate for plate in layout["plates"]}
    ordered = sorted(visible_rgba, key=lambda plate: layout_by_id.get(plate["id"], {}).get("order", 999))
    ordered_clean = sorted(special_clean, key=lambda plate: layout_by_id.get(plate["id"], {}).get("order", 999))

    clean_by_variant = {
        plate.get("cleanVariant"): plate for plate in ordered_clean if plate.get("cleanVariant")
    }

    chain: list[str] = []
    chain.append(f"color=c=black@0.0:s={internal_w}x{internal_h}:r={working_fps}:d={profile['duration']}[base]")
    clean_inputs = len(ordered_clean)
    background_index = clean_inputs
    for clean_index, _clean in enumerate(ordered_clean):
        chain.append(
            f"[{clean_index}:v]"
            "format=rgba,"
            f"scale=w='iw*{asset_scale:.6f}*{supersample:.3f}':h='ih*{asset_scale:.6f}*{supersample:.3f}':flags=lanczos:eval=frame,"
            "setsar=1"
            f"[clean{clean_index}]"
        )
    chain.append(
        f"[{background_index}:v]"
        "format=rgba,"
        f"scale=w='iw*{asset_scale:.6f}*{supersample:.3f}':h='ih*{asset_scale:.6f}*{supersample:.3f}':flags=lanczos:eval=frame,"
        "setsar=1[bg]"
    )
    chain.append("[base][bg]overlay=x='(W-w)/2':y='(H-h)/2':eval=frame:format=auto[layer0]")

    for index, plate in enumerate(ordered, start=background_index + 1):
        layout_plate = layout_by_id[plate["id"]]
        strength = float(layout_plate["parallaxStrength"])
        x_motion = f"({plate_motion_expr(profile, layout_plate, 'x')})*{motion_scale:.6f}"
        y_motion = f"({plate_motion_expr(profile, layout_plate, 'y')})*{motion_scale:.6f}"
        zoom_expr = plate_zoom_expr(profile, strength)
        layer_input = f"layer{index-background_index-1}"
        clean_variant = layout_plate.get("cleanVariant")
        clean_plate = clean_by_variant.get(clean_variant) if clean_variant else None
        if clean_plate:
            clean_input_index = ordered_clean.index(clean_plate)
            chain.append(
                f"[{layer_input}][clean{clean_input_index}]overlay=x='(W-w)/2':y='(H-h)/2':eval=frame:format=auto"
                f"[cleanunderlay{index-background_index}]"
            )
            layer_input = f"cleanunderlay{index-background_index}"
        chain.append(
            f"[{index}:v]"
            "format=rgba,"
            f"scale=w='iw*{asset_scale:.6f}*{supersample:.3f}*{zoom_expr}':h='ih*{asset_scale:.6f}*{supersample:.3f}*{zoom_expr}':flags=lanczos:eval=frame,"
            "setsar=1"
            f"[plate{index}]"
        )
        chain.append(
            f"[{layer_input}][plate{index}]"
            f"overlay=x='(W-w)/2-({x_motion})':"
            f"y='(H-h)/2-({y_motion})':eval=frame:format=auto"
            f"[layer{index-background_index}]"
        )

    last = f"[layer{len(ordered)}]"
    chain.append(
        f"{last}fps={working_fps},scale=w={source_w}:h={source_h}:flags=lanczos,format=yuv420p[composite]"
    )
    if tmix_frames and tmix_frames > 1:
        weights = " ".join(["1"] * tmix_frames)
        chain.append(f"[composite]tmix=frames={tmix_frames}:weights='{weights}',fps={profile['fps']}[v]")
    else:
        chain.append(f"[composite]fps={profile['fps']}[v]")
    return ";".join(chain), ordered_clean, ordered


def render_case(sample_dir: Path, out_dir: Path, codec: str, crf: int, supersample: float, internal_fps: int, tmix_frames: int) -> dict[str, Any]:
    manifest = load_json(sample_dir / "plate_export_manifest.json")
    layout = load_json(sample_dir / "plate_layout.json")
    output_path = out_dir / "preview_multiplate.mp4"
    poster_path = out_dir / "preview_multiplate_poster.png"
    report_path = out_dir / "preview_multiplate_report.json"
    out_dir.mkdir(parents=True, exist_ok=True)

    clean_inputs = [sample_dir / plate["files"]["clean"] for plate in manifest["exportedPlates"] if "clean" in plate.get("files", {})]
    inputs = [*clean_inputs, sample_dir / manifest["files"]["backgroundRgba"]]
    background_meta = ffprobe_stream(inputs[-1])
    asset_scale = float(layout["source"]["width"]) / max(1.0, float(background_meta["width"]))
    filter_complex, ordered_clean, ordered = build_filter_complex(layout, manifest, supersample, internal_fps, tmix_frames, asset_scale)
    routed_clean_count = sum(
        1
        for plate in layout["plates"]
        if plate.get("visible")
        and plate.get("role") != "special-clean"
        and plate.get("cleanVariant")
        and any(clean.get("cleanVariant") == plate.get("cleanVariant") for clean in manifest["exportedPlates"])
    )
    for plate in ordered:
        inputs.append(sample_dir / plate["files"]["rgba"])

    command = ["ffmpeg", "-y"]
    for path in inputs:
        command.extend(["-loop", "1", "-i", str(path)])
    command.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-t",
            str(layout["camera"]["durationSec"]),
            "-c:v",
            codec,
            "-crf",
            str(crf),
            "-preset",
            "slower",
            "-pix_fmt",
            "yuv420p",
            str(output_path),
        ]
    )

    started = time.perf_counter()
    subprocess.run(command, check=True, capture_output=True, text=True)
    runtime = time.perf_counter() - started

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(output_path), "-vf", "select=eq(n\\,0)", "-vframes", "1", str(poster_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    video = ffprobe_stream(output_path)
    report = {
        "sample": manifest["sampleId"],
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "runtime_sec": round(runtime, 4),
        "preview_path": str(output_path),
        "poster_path": str(poster_path),
        "plate_layout_path": str(sample_dir / "plate_layout.json"),
        "plate_manifest_path": str(sample_dir / "plate_export_manifest.json"),
        "video": video,
        "rendered_plate_count": len(ordered),
        "special_clean_count": len(ordered_clean),
        "routed_clean_count": routed_clean_count,
        "camera_safe": layout.get("cameraSafe", {}),
        "routing": layout.get("routing", {}),
        "transition_count": len(layout.get("transitions", [])),
        "internal_fps": internal_fps,
        "tmix_frames": tmix_frames,
        "supersample": supersample,
    }
    save_json(report_path, report)
    return report


def main() -> None:
    args = parse_args()
    export_root = Path(args.plate_export_root)
    outdir = Path(args.outdir)
    allowed = set(args.samples or [])
    sample_dirs = [path for path in sorted(export_root.iterdir()) if path.is_dir() and (not allowed or path.name in allowed)]
    if not sample_dirs:
        raise SystemExit("No plate export directories found for requested samples.")

    entries: list[dict[str, Any]] = []
    for sample_dir in sample_dirs:
        report = render_case(sample_dir, outdir / sample_dir.name, args.codec, args.crf, args.supersample, args.internal_fps, args.tmix_frames)
        entries.append(report)

    summary = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "plate_export_root": str(export_root),
        "outdir": str(outdir),
        "entries": entries,
        "count": len(entries),
    }
    save_json(outdir / "render_preview_multiplate_summary.json", summary)
    print(f"MARKER_180.PARALLAX.MULTIPLATE_RENDER.SUMMARY={outdir / 'render_preview_multiplate_summary.json'}")


if __name__ == "__main__":
    main()
