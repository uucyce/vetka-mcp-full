#!/usr/bin/env python3
"""Batch-build MYCO motion assets from source MP4 files.

W9.A responsibilities:
- normalize one asset family with a fixed preset,
- assemble architect multi-part source into one master clip,
- convert all planned assets to APNG via mp4_to_apng_alpha.py,
- write one batch manifest for later MCC/UI integration.
"""

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")
DEFAULT_SOURCE_DIR = Path("/Users/danilagulin/Documents/VETKA_Project/icons/myco_logos/team_A_mp4")
DEFAULT_OUTPUT_ROOT = ROOT / "artifacts" / "myco_motion" / "team_A"
CONVERTER = ROOT / "scripts" / "media" / "mp4_to_apng_alpha.py"

DEFAULT_PRESET = {
    "mode": "luma",
    "fps": 8.0,
    "luma_threshold": 52.0,
    "alpha_blur": 0.8,
}

ARCHITECT_ROLE = "architect"


@dataclass(frozen=True)
class AssetSpec:
    role: str
    variant: str
    source_mp4: str
    assembled: bool = False
    source_parts: tuple[str, ...] = ()


def default_specs(source_dir: Path) -> list[AssetSpec]:
    return [
        AssetSpec(role=ARCHITECT_ROLE, variant="primary", source_mp4=str(source_dir / "architect_master.mp4"), assembled=True, source_parts=("arch1.mp4", "arch1-2.mp4")),
        AssetSpec(role="coder", variant="coder1", source_mp4=str(source_dir / "coder1.mp4")),
        AssetSpec(role="coder", variant="coder2", source_mp4=str(source_dir / "coder2.mp4")),
        AssetSpec(role="researcher", variant="primary", source_mp4=str(source_dir / "researcher1.mp4")),
        AssetSpec(role="scout", variant="scout1", source_mp4=str(source_dir / "scout.mp4")),
        AssetSpec(role="scout", variant="scout2", source_mp4=str(source_dir / "scout2.mp4")),
        AssetSpec(role="scout", variant="scout3", source_mp4=str(source_dir / "scout3.mp4")),
        AssetSpec(role="verifier", variant="primary", source_mp4=str(source_dir / "verif1.mp4")),
    ]


def run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed ({proc.returncode}): {' '.join(cmd)}\n"
            f"stdout: {proc.stdout}\n"
            f"stderr: {proc.stderr}"
        )
    return proc


def ensure_dependencies() -> None:
    if not CONVERTER.exists():
        raise FileNotFoundError(f"Converter not found: {CONVERTER}")
    for binary in ("ffmpeg", "ffprobe"):
        if shutil.which(binary) is None:
            raise RuntimeError(f"{binary} not found in PATH")


def ffprobe_summary(path: Path) -> dict[str, Any]:
    proc = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate,avg_frame_rate,nb_frames,duration",
            "-of",
            "json",
            str(path),
        ]
    )
    payload = json.loads(proc.stdout)
    stream = (payload.get("streams") or [{}])[0]
    return {
        "width": stream.get("width"),
        "height": stream.get("height"),
        "r_frame_rate": stream.get("r_frame_rate"),
        "avg_frame_rate": stream.get("avg_frame_rate"),
        "nb_frames": stream.get("nb_frames"),
        "duration": stream.get("duration"),
    }


def assemble_architect(source_dir: Path, output_mp4: Path) -> dict[str, Any]:
    part_a = source_dir / "arch1.mp4"
    part_b = source_dir / "arch1-2.mp4"
    for part in (part_a, part_b):
        if not part.exists():
            raise FileNotFoundError(f"Architect source part not found: {part}")

    concat_file = output_mp4.parent / "architect_concat.txt"
    concat_file.write_text(
        f"file '{part_a}'\nfile '{part_b}'\n",
        encoding="utf-8",
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-vf",
            "fps=24",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(output_mp4),
        ]
    )
    return {
        "output_mp4": str(output_mp4),
        "source_parts": [str(part_a), str(part_b)],
        "ffprobe": ffprobe_summary(output_mp4),
    }


def convert_asset(spec: AssetSpec, output_root: Path, preset: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    source_mp4 = Path(spec.source_mp4)
    if not dry_run and not source_mp4.exists():
        raise FileNotFoundError(f"Source MP4 not found: {source_mp4}")

    role_dir = output_root / spec.role / spec.variant
    build_dir = role_dir / "build"
    apng_path = role_dir / f"{spec.role}_{spec.variant}.apng"
    build_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "role": spec.role,
        "variant": spec.variant,
        "assembled": spec.assembled,
        "source_mp4": str(source_mp4),
        "output_apng": str(apng_path),
        "build_dir": str(build_dir),
        "preset": preset,
    }
    if spec.source_parts:
        result["source_parts"] = list(spec.source_parts)

    if dry_run:
        result["status"] = "planned"
        if source_mp4.exists():
            result["ffprobe"] = ffprobe_summary(source_mp4)
        return result

    result["ffprobe"] = ffprobe_summary(source_mp4)

    run(
        [
            sys.executable,
            str(CONVERTER),
            str(source_mp4),
            "--output-dir",
            str(build_dir),
            "--output-apng",
            str(apng_path),
            "--fps",
            str(preset["fps"]),
            "--mode",
            str(preset["mode"]),
            "--luma-threshold",
            str(preset["luma_threshold"]),
            "--alpha-blur",
            str(preset["alpha_blur"]),
        ]
    )
    manifest_path = build_dir / "manifest.json"
    result["status"] = "built"
    result["conversion_manifest"] = str(manifest_path)
    if manifest_path.exists():
        result["conversion"] = json.loads(manifest_path.read_text(encoding="utf-8"))
    return result


def build_manifest(source_dir: Path, output_root: Path, preset: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    specs = default_specs(source_dir)
    architect_master = output_root / ARCHITECT_ROLE / "primary" / "architect_master.mp4"
    architect_master.parent.mkdir(parents=True, exist_ok=True)

    architect_step = {
        "role": ARCHITECT_ROLE,
        "variant": "primary",
        "status": "planned" if dry_run else "assembled",
        "source_parts": [str(source_dir / "arch1.mp4"), str(source_dir / "arch1-2.mp4")],
        "output_mp4": str(architect_master),
    }
    if not dry_run:
        architect_step = assemble_architect(source_dir, architect_master)
        architect_step["role"] = ARCHITECT_ROLE
        architect_step["variant"] = "primary"
        architect_step["status"] = "assembled"

    converted_assets: list[dict[str, Any]] = []
    for spec in specs:
        actual_spec = spec
        if spec.role == ARCHITECT_ROLE:
            actual_spec = AssetSpec(
                role=spec.role,
                variant=spec.variant,
                source_mp4=str(architect_master),
                assembled=True,
                source_parts=spec.source_parts,
            )
        converted_assets.append(convert_asset(actual_spec, output_root, preset, dry_run=dry_run))

    return {
        "marker": "MARKER_168.MYCO.MOTION.BATCH_BUILD.V1",
        "source_dir": str(source_dir),
        "output_root": str(output_root),
        "preset": preset,
        "dry_run": dry_run,
        "architect_assembly": architect_step,
        "assets": converted_assets,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch-build MYCO motion APNG assets")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--manifest-path", type=Path, default=None)
    parser.add_argument("--fps", type=float, default=DEFAULT_PRESET["fps"])
    parser.add_argument("--luma-threshold", type=float, default=DEFAULT_PRESET["luma_threshold"])
    parser.add_argument("--alpha-blur", type=float, default=DEFAULT_PRESET["alpha_blur"])
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        ensure_dependencies()
        preset = {
            "mode": "luma",
            "fps": args.fps,
            "luma_threshold": args.luma_threshold,
            "alpha_blur": args.alpha_blur,
        }
        manifest = build_manifest(args.source_dir, args.output_root, preset, dry_run=args.dry_run)
        manifest_path = args.manifest_path or (args.output_root / "batch_manifest.json")
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"manifest_path": str(manifest_path), "asset_count": len(manifest["assets"]), "dry_run": args.dry_run}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
