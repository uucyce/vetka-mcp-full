#!/usr/bin/env python3
"""MP4 -> RGBA PNG sequence -> APNG.

Alpha generation modes:
- chroma: remove background by key color (fast, no ML)
- luma: derive alpha from luminance
- depth: derive alpha from monocular depth using transformers pipeline

Requires:
- ffmpeg in PATH
- Python deps: pillow, numpy
Optional for depth mode:
- torch, transformers
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np
from PIL import Image, ImageFilter


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found in PATH")


def run(cmd: List[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed ({proc.returncode}): {' '.join(cmd)}\n"
            f"stdout: {proc.stdout}\n"
            f"stderr: {proc.stderr}"
        )


def extract_frames(input_mp4: Path, rgb_dir: Path, fps: float) -> List[Path]:
    rgb_dir.mkdir(parents=True, exist_ok=True)
    pattern = rgb_dir / "rgb_%06d.png"
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(input_mp4),
            "-vf",
            f"fps={fps}",
            str(pattern),
        ]
    )
    return sorted(rgb_dir.glob("rgb_*.png"))


def parse_hex_color(value: str) -> Tuple[int, int, int]:
    v = value.strip().lstrip("#")
    if len(v) != 6:
        raise ValueError("--chroma-color must be like 00ff00")
    return tuple(int(v[i : i + 2], 16) for i in (0, 2, 4))


def alpha_from_chroma(rgb: np.ndarray, chroma_rgb: Tuple[int, int, int], threshold: float, soft: float) -> np.ndarray:
    key = np.array(chroma_rgb, dtype=np.float32)
    diff = rgb.astype(np.float32) - key
    dist = np.sqrt(np.sum(diff * diff, axis=2))

    # soft edge around threshold
    low = max(0.0, threshold - soft)
    high = threshold + soft
    alpha = (dist - low) / max(1e-6, (high - low))
    alpha = np.clip(alpha, 0.0, 1.0)
    return (alpha * 255.0).astype(np.uint8)


def alpha_from_luma(rgb: np.ndarray, threshold: float, invert: bool) -> np.ndarray:
    luma = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]).astype(np.float32)
    if invert:
        luma = 255.0 - luma
    alpha = np.where(luma >= threshold, 255.0, 0.0)
    return alpha.astype(np.uint8)


class DepthAlpha:
    def __init__(self, model: str, invert: bool, threshold: float):
        try:
            from transformers import pipeline
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Depth mode requires transformers/torch. Install: pip install torch transformers"
            ) from exc

        self._pipe = pipeline(task="depth-estimation", model=model)
        self.invert = invert
        self.threshold = threshold

    def alpha(self, img: Image.Image) -> np.ndarray:
        out = self._pipe(img)
        depth_img = out["depth"]
        depth = np.array(depth_img).astype(np.float32)
        dmin = float(depth.min())
        dmax = float(depth.max())
        norm = (depth - dmin) / max(1e-6, (dmax - dmin))
        if self.invert:
            norm = 1.0 - norm
        depth_u8 = (norm * 255.0).astype(np.uint8)
        return np.where(depth_u8 >= self.threshold, 255, 0).astype(np.uint8)


def compose_rgba(rgb_path: Path, out_path: Path, mode: str, *, chroma_rgb: Tuple[int, int, int], chroma_threshold: float,
                 chroma_softness: float, luma_threshold: float, luma_invert: bool, depth_alpha: DepthAlpha | None,
                 blur: float) -> None:
    img = Image.open(rgb_path).convert("RGB")
    rgb = np.array(img)

    if mode == "chroma":
        alpha = alpha_from_chroma(rgb, chroma_rgb, chroma_threshold, chroma_softness)
    elif mode == "luma":
        alpha = alpha_from_luma(rgb, luma_threshold, luma_invert)
    elif mode == "depth":
        if depth_alpha is None:
            raise RuntimeError("depth mode requested but depth pipeline is not initialized")
        alpha = depth_alpha.alpha(img)
    else:  # pragma: no cover
        raise ValueError(f"Unknown mode: {mode}")

    rgba = np.dstack((rgb, alpha))
    out_img = Image.fromarray(rgba, mode="RGBA")
    if blur > 0:
        a = out_img.getchannel("A").filter(ImageFilter.GaussianBlur(radius=blur))
        out_img.putalpha(a)
    out_img.save(out_path)


def build_apng(rgba_dir: Path, output_apng: Path, fps: float) -> None:
    output_apng.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(rgba_dir / "rgba_%06d.png"),
            "-plays",
            "0",
            "-f",
            "apng",
            str(output_apng),
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert MP4 to RGBA PNG sequence and APNG")
    parser.add_argument("input_mp4", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True, help="Folder for extracted and RGBA frames")
    parser.add_argument("--output-apng", type=Path, required=True, help="Output APNG path")
    parser.add_argument("--fps", type=float, default=8.0)
    parser.add_argument("--max-frames", type=int, default=0, help="0 means all")
    parser.add_argument("--mode", choices=["chroma", "luma", "depth"], default="chroma")

    parser.add_argument("--chroma-color", type=str, default="00ff00")
    parser.add_argument("--chroma-threshold", type=float, default=60.0)
    parser.add_argument("--chroma-softness", type=float, default=20.0)

    parser.add_argument("--luma-threshold", type=float, default=128.0)
    parser.add_argument("--luma-invert", action="store_true")

    parser.add_argument("--depth-model", type=str, default="depth-anything/Depth-Anything-V2-Small-hf")
    parser.add_argument("--depth-threshold", type=float, default=128.0)
    parser.add_argument("--depth-invert", action="store_true")

    parser.add_argument("--alpha-blur", type=float, default=0.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        ensure_ffmpeg()
        if not args.input_mp4.exists():
            raise FileNotFoundError(f"Input MP4 not found: {args.input_mp4}")

        work_dir = args.output_dir
        rgb_dir = work_dir / "frames_rgb"
        rgba_dir = work_dir / "frames_rgba"
        rgba_dir.mkdir(parents=True, exist_ok=True)

        rgb_frames = extract_frames(args.input_mp4, rgb_dir, args.fps)
        if args.max_frames > 0:
            rgb_frames = rgb_frames[: args.max_frames]
        if not rgb_frames:
            raise RuntimeError("No frames extracted from input MP4")

        depth_alpha = None
        if args.mode == "depth":
            depth_alpha = DepthAlpha(model=args.depth_model, invert=args.depth_invert, threshold=args.depth_threshold)

        chroma_rgb = parse_hex_color(args.chroma_color)

        for idx, frame_path in enumerate(rgb_frames):
            out_path = rgba_dir / f"rgba_{idx:06d}.png"
            compose_rgba(
                frame_path,
                out_path,
                args.mode,
                chroma_rgb=chroma_rgb,
                chroma_threshold=args.chroma_threshold,
                chroma_softness=args.chroma_softness,
                luma_threshold=args.luma_threshold,
                luma_invert=args.luma_invert,
                depth_alpha=depth_alpha,
                blur=args.alpha_blur,
            )

        build_apng(rgba_dir, args.output_apng, args.fps)

        manifest = {
            "input_mp4": str(args.input_mp4),
            "mode": args.mode,
            "fps": args.fps,
            "processed_frames": len(rgb_frames),
            "output_apng": str(args.output_apng),
            "rgba_dir": str(rgba_dir),
        }
        (work_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
