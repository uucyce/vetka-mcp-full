"""Depth estimation wrapper for Video Inspection Pack.

Uses Depth Anything V2 Small via HuggingFace Transformers pipeline.
Reuses the same venv as photo_to_parallax: photo_parallax_playground/.depth-venv

Polarity: white = close, black = far (standard for VETKA project).

Usage (standalone test):
    .depth-venv/bin/python3 scripts/video_inspection_depth.py test.png

Architecture: docs/197ph_tool_analize_video_forAI/ARCHITECTURE_VIDEO_INSPECTION_TOOL.md
"""

import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

# Model registry — only Depth Anything V2 Small for now
DEPTH_MODELS = {
    "depth-anything-v2": "depth-anything/Depth-Anything-V2-Small-hf",
}

_pipe = None
_loaded_model = None


def _load_model(model_key: str = "depth-anything-v2"):
    """Lazy-load depth pipeline. Only called when --depth is used."""
    global _pipe, _loaded_model

    if _pipe is not None and _loaded_model == model_key:
        return _pipe

    model_id = DEPTH_MODELS.get(model_key)
    if not model_id:
        raise ValueError(f"Unknown depth model: {model_key}. "
                         f"Available: {list(DEPTH_MODELS.keys())}")

    from transformers import pipeline
    _pipe = pipeline(task="depth-estimation", model=model_id)
    _loaded_model = model_key
    return _pipe


def estimate_depth(img: Image.Image,
                   model_key: str = "depth-anything-v2") -> Image.Image:
    """Run depth estimation on a single PIL Image.

    Returns: grayscale PIL Image (white=close, black=far), same size as input.
    """
    pipe = _load_model(model_key)
    result = pipe(img.convert("RGB"))
    depth_img = result["depth"]  # PIL Image, grayscale

    # Ensure same size as input
    if depth_img.size != img.size:
        depth_img = depth_img.resize(img.size, Image.LANCZOS)

    return depth_img


def estimate_depth_batch(images: list[Image.Image],
                         model_key: str = "depth-anything-v2",
                         progress: bool = True) -> list[Image.Image]:
    """Run depth estimation on a batch of PIL Images with progress.

    Returns: list of grayscale PIL Images (white=close, black=far).
    """
    results = []
    total = len(images)
    t0 = time.time()

    for i, img in enumerate(images):
        depth = estimate_depth(img, model_key)
        results.append(depth)

        if progress:
            elapsed = time.time() - t0
            fps = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (total - i - 1) / fps if fps > 0 else 0
            print(f"\r  [depth] {i + 1}/{total} "
                  f"({elapsed:.1f}s, {fps:.1f} fps, ETA {eta:.0f}s)", end="")

    if progress:
        print()  # newline after progress

    return results


def get_inference_stats(n_frames: int, model_key: str,
                        elapsed: float) -> dict:
    """Build depth_stats dict for inspection.json."""
    return {
        "model": DEPTH_MODELS.get(model_key, model_key),
        "inference_time_sec": round(elapsed, 2),
        "frames_processed": n_frames,
        "fps": round(n_frames / elapsed, 2) if elapsed > 0 else 0,
    }


# Standalone test
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python video_inspection_depth.py <image_path>")
        sys.exit(1)

    img_path = sys.argv[1]
    img = Image.open(img_path)
    print(f"Input: {img_path} ({img.size[0]}x{img.size[1]})")

    t0 = time.time()
    depth = estimate_depth(img)
    elapsed = time.time() - t0
    print(f"Depth estimation: {elapsed:.2f}s")

    out_path = Path(img_path).stem + "_depth.png"
    depth.save(out_path)
    print(f"Saved: {out_path}")
