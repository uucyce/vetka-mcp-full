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


RENDER_PRESETS: dict[str, dict[str, Any]] = {
    "web": {
        "out_width": 1280,
        "out_height": 720,
        "output_fps": 25,
        "codec": "libx264",
        "crf": 24,
        "supersample": 1.25,
        "internal_fps": 25,
        "tmix_frames": 1,
    },
    "social": {
        "out_width": 1920,
        "out_height": 1080,
        "output_fps": 30,
        "codec": "libx264",
        "crf": 20,
        "supersample": 1.5,
        "internal_fps": 50,
        "tmix_frames": 3,
    },
    "quality": {
        "out_width": 2560,
        "out_height": 1440,
        "output_fps": 25,
        "codec": "libx264",
        "crf": 18,
        "supersample": 2.0,
        "internal_fps": 50,
        "tmix_frames": 3,
    },
}

DEPTH_BANDS: list[dict[str, Any]] = [
    {"name": "near", "min": 170, "max": 255, "motion_scale": 1.18, "zoom_scale": 1.08},
    {"name": "mid", "min": 96, "max": 169, "motion_scale": 1.0, "zoom_scale": 1.0},
    {"name": "far", "min": 1, "max": 95, "motion_scale": 0.72, "zoom_scale": 0.94},
]


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
    parser.add_argument("--preset", choices=sorted(RENDER_PRESETS.keys()), default="quality", help="Named output preset.")
    parser.add_argument("--out-width", type=int, help="Optional override for output width.")
    parser.add_argument("--out-height", type=int, help="Optional override for output height.")
    parser.add_argument("--output-fps", type=int, help="Optional override for final output fps.")
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
            "stream=codec_name,width,height,r_frame_rate,duration,nb_frames,bit_rate",
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
        "codec_name": stream.get("codec_name"),
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "r_frame_rate": stream.get("r_frame_rate"),
        "duration": float(stream.get("duration", 0.0)),
        "nb_frames": stream.get("nb_frames"),
        "bit_rate": stream.get("bit_rate"),
    }


def resolve_render_settings(args: argparse.Namespace) -> dict[str, Any]:
    preset = dict(RENDER_PRESETS[args.preset])
    return {
        "name": args.preset,
        "out_width": args.out_width or preset["out_width"],
        "out_height": args.out_height or preset["out_height"],
        "output_fps": args.output_fps or preset["output_fps"],
        "codec": args.codec if args.codec != "libx264" or args.preset == "quality" else preset["codec"],
        "crf": args.crf if args.crf != 18 or args.preset == "quality" else preset["crf"],
        "supersample": args.supersample if args.supersample != 2.0 or args.preset == "quality" else preset["supersample"],
        "internal_fps": args.internal_fps if args.internal_fps != 50 or args.preset == "quality" else preset["internal_fps"],
        "tmix_frames": args.tmix_frames if args.tmix_frames != 3 or args.preset == "quality" else preset["tmix_frames"],
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


def plate_zoom_expr(profile: dict[str, Any], strength: float, zoom_scale: float = 1.0) -> str:
    motion_type = profile["motion_type"]
    zoom_delta = profile["zoom"] - 1.0
    progress = profile["progress"]
    cosine = profile["cosine"]
    scaled_strength = strength * zoom_scale
    if motion_type == "orbit":
      return f"(1+({zoom_delta:.6f})*{scaled_strength:.4f}*0.14*(1-({cosine}*{cosine})))"
    if motion_type == "dolly-out + zoom-in":
      return f"(1+({zoom_delta:.6f})*{progress}*{scaled_strength:.4f})"
    if motion_type == "dolly-in + zoom-out":
      return f"(1+({zoom_delta:.6f})*(1-{progress})*{scaled_strength:.4f})"
    return f"(1+({zoom_delta:.6f})*{scaled_strength:.4f}*0.32)"


def plate_motion_expr(profile: dict[str, Any], plate: dict[str, Any], axis: str, strength_scale: float = 1.0) -> str:
    base = profile["travel_x_px"] if axis == "x" else profile["travel_y_px"]
    signed = profile["signed"]
    cosine = profile["cosine"]
    strength = float(plate["parallaxStrength"])
    damping = float(plate["motionDamping"])
    pixels = base * strength * strength_scale * damping
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
    output_width: int,
    output_height: int,
    output_fps: int,
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

    current_layer = "layer0"
    for plate_offset, plate in enumerate(ordered):
        rgba_input_index = background_index + 1 + plate_offset * 2
        depth_input_index = rgba_input_index + 1
        layout_plate = layout_by_id[plate["id"]]
        strength = float(layout_plate["parallaxStrength"])
        layer_input = current_layer
        clean_variant = layout_plate.get("cleanVariant")
        clean_plate = clean_by_variant.get(clean_variant) if clean_variant else None
        if clean_plate:
            clean_input_index = ordered_clean.index(clean_plate)
            chain.append(
                f"[{layer_input}][clean{clean_input_index}]overlay=x='(W-w)/2':y='(H-h)/2':eval=frame:format=auto"
                f"[cleanunderlay{plate_offset + 1}]"
            )
            layer_input = f"cleanunderlay{plate_offset + 1}"

        rgba_split_labels = [f"plate{plate_offset}_rgba_{band['name']}" for band in DEPTH_BANDS]
        depth_split_labels = [f"plate{plate_offset}_depth_{band['name']}" for band in DEPTH_BANDS]
        chain.append(
            f"[{rgba_input_index}:v]format=rgba,split={len(DEPTH_BANDS)}" + "".join(f"[{label}]" for label in rgba_split_labels)
        )
        chain.append(
            f"[{depth_input_index}:v]format=gray,split={len(DEPTH_BANDS)}" + "".join(f"[{label}]" for label in depth_split_labels)
        )

        for band_index, band in enumerate(DEPTH_BANDS):
            zoom_expr = plate_zoom_expr(profile, strength, float(band["zoom_scale"]))
            x_motion = f"({plate_motion_expr(profile, layout_plate, 'x', float(band['motion_scale']))})*{motion_scale:.6f}"
            y_motion = f"({plate_motion_expr(profile, layout_plate, 'y', float(band['motion_scale']))})*{motion_scale:.6f}"
            rgba_label = rgba_split_labels[band_index]
            depth_label = depth_split_labels[band_index]
            alpha_label = f"plate{plate_offset}_alpha_{band['name']}"
            mask_label = f"plate{plate_offset}_mask_{band['name']}"
            band_alpha_label = f"plate{plate_offset}_bandalpha_{band['name']}"
            rgb_label = f"plate{plate_offset}_rgb_{band['name']}"
            band_plate_label = f"plate{plate_offset}_band_{band['name']}"
            next_layer_label = f"layer{plate_offset + 1}_{band['name']}"

            chain.append(f"[{rgba_label}]alphaextract[{alpha_label}]")
            chain.append(
                f"[{depth_label}]lut=y='if(between(val,{band['min']},{band['max']}),255,0)',gblur=sigma=0.8[{mask_label}]"
            )
            chain.append(f"[{alpha_label}][{mask_label}]blend=all_mode=multiply[{band_alpha_label}]")
            chain.append(f"[{rgba_label}]format=rgb24[{rgb_label}]")
            chain.append(f"[{rgb_label}][{band_alpha_label}]alphamerge[{band_plate_label}]")
            chain.append(
                f"[{band_plate_label}]"
                f"scale=w='iw*{asset_scale:.6f}*{supersample:.3f}*{zoom_expr}':h='ih*{asset_scale:.6f}*{supersample:.3f}*{zoom_expr}':flags=lanczos:eval=frame,"
                "setsar=1"
                f"[{band_plate_label}_scaled]"
            )
            chain.append(
                f"[{layer_input}][{band_plate_label}_scaled]"
                f"overlay=x='(W-w)/2-({x_motion})':"
                f"y='(H-h)/2-({y_motion})':eval=frame:format=auto"
                f"[{next_layer_label}]"
            )
            layer_input = next_layer_label
        current_layer = layer_input

    last = f"[{current_layer}]" if ordered else "[layer0]"
    chain.append(
        f"{last}fps={working_fps},"
        f"scale=w={source_w}:h={source_h}:flags=lanczos,"
        f"scale=w={output_width}:h={output_height}:force_original_aspect_ratio=decrease:flags=lanczos,"
        f"pad={output_width}:{output_height}:(ow-iw)/2:(oh-ih)/2:color=black,"
        "format=yuv420p[composite]"
    )
    if tmix_frames and tmix_frames > 1:
        weights = " ".join(["1"] * tmix_frames)
        chain.append(f"[composite]tmix=frames={tmix_frames}:weights='{weights}',fps={output_fps}[v]")
    else:
        chain.append(f"[composite]fps={output_fps}[v]")
    return ";".join(chain), ordered_clean, ordered


def render_case(sample_dir: Path, out_dir: Path, settings: dict[str, Any]) -> dict[str, Any]:
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
    filter_complex, ordered_clean, ordered = build_filter_complex(
        layout,
        manifest,
        settings["out_width"],
        settings["out_height"],
        settings["output_fps"],
        settings["supersample"],
        settings["internal_fps"],
        settings["tmix_frames"],
        asset_scale,
    )
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
        inputs.append(sample_dir / plate["files"]["depth"])

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
            settings["codec"],
            "-crf",
            str(settings["crf"]),
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
    file_size_bytes = output_path.stat().st_size
    validation_reasons: list[str] = []
    validation_status = "pass"
    if not layout.get("cameraSafe", {}).get("ok", False):
        validation_status = "caution"
        validation_reasons.append("camera-safe gate is not fully satisfied")
    if video["duration"] <= 0:
        validation_status = "fail"
        validation_reasons.append("render duration is invalid")
    report = {
        "sample": manifest["sampleId"],
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "runtime_sec": round(runtime, 4),
        "preview_path": str(output_path),
        "poster_path": str(poster_path),
        "plate_layout_path": str(sample_dir / "plate_layout.json"),
        "plate_manifest_path": str(sample_dir / "plate_export_manifest.json"),
        "video": video,
        "file_size_bytes": file_size_bytes,
        "preset": settings["name"],
        "render_settings": settings,
        "rendered_plate_count": len(ordered),
        "rendered_depth_band_count": len(ordered) * len(DEPTH_BANDS),
        "special_clean_count": len(ordered_clean),
        "routed_clean_count": routed_clean_count,
        "camera_safe": layout.get("cameraSafe", {}),
        "routing": layout.get("routing", {}),
        "transition_count": len(layout.get("transitions", [])),
        "internal_fps": settings["internal_fps"],
        "tmix_frames": settings["tmix_frames"],
        "supersample": settings["supersample"],
        "validation": {
            "status": validation_status,
            "reasons": validation_reasons,
        },
    }
    save_json(report_path, report)
    return report


def main() -> None:
    args = parse_args()
    export_root = Path(args.plate_export_root)
    settings = resolve_render_settings(args)
    outdir = Path(args.outdir)
    if args.preset != "quality" and Path(args.outdir).name == "render_preview_multiplate":
        outdir = outdir / settings["name"]
    if args.preset != "quality" and Path(args.outdir).name == "render_preview_multiplate_qwen_gated":
        outdir = outdir / settings["name"]
    allowed = set(args.samples or [])
    sample_dirs = [path for path in sorted(export_root.iterdir()) if path.is_dir() and (not allowed or path.name in allowed)]
    if not sample_dirs:
        raise SystemExit("No plate export directories found for requested samples.")

    entries: list[dict[str, Any]] = []
    for sample_dir in sample_dirs:
        report = render_case(sample_dir, outdir / sample_dir.name, settings)
        entries.append(report)

    validation_counts = {"pass": 0, "caution": 0, "fail": 0}
    for entry in entries:
        status = entry.get("validation", {}).get("status", "fail")
        validation_counts[status] = validation_counts.get(status, 0) + 1

    summary = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "plate_export_root": str(export_root),
        "outdir": str(outdir),
        "preset": settings["name"],
        "render_settings": settings,
        "overall_status": "fail" if validation_counts["fail"] else ("caution" if validation_counts["caution"] else "pass"),
        "validation_counts": validation_counts,
        "entries": entries,
        "count": len(entries),
    }
    save_json(outdir / "render_preview_multiplate_summary.json", summary)
    print(f"MARKER_180.PARALLAX.MULTIPLATE_RENDER.SUMMARY={outdir / 'render_preview_multiplate_summary.json'}")


if __name__ == "__main__":
    main()
