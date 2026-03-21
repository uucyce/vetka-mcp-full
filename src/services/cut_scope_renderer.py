"""
MARKER_SCOPES — Video Scope Renderer for CUT.

Computes waveform (luma), vectorscope (CbCr), and histogram (RGB)
from a video frame extracted via FFmpeg subprocess.

Architecture: FFmpeg CLI → frame → numpy → scope data → JSON to frontend.
Per Beta-1 feedback: FFmpeg CLI for frame extraction, not PyAV (that's for preview pipeline).

Performance targets (1080p → 256px scope):
  Waveform: ~5-10ms
  Histogram: ~2-5ms
  Vectorscope: ~8-15ms

@status: active
@phase: SCOPES
@task: tb_1773997178_1
@depends: cut_routes (endpoint), FFmpeg (frame extraction)
"""
from __future__ import annotations

import base64
import logging
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Frame extraction via FFmpeg CLI
# ---------------------------------------------------------------------------

def extract_frame_rgb(source_path: str, time_sec: float = 0.0, max_width: int = 512) -> "np.ndarray | None":
    """Extract a single frame from video at given time, return as uint8 RGB numpy array.

    Uses FFmpeg rawvideo output → numpy reshape.
    Downscales to max_width for scope analysis performance.
    """
    if not HAS_NUMPY:
        logger.warning("numpy not available, cannot compute scopes")
        return None

    p = Path(source_path)
    if not p.exists():
        return None

    # Get video dimensions first via ffprobe
    try:
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0:s=x",
            str(p),
        ]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=5)
        if probe_result.returncode != 0:
            return None
        dims = probe_result.stdout.strip().split("x")
        if len(dims) < 2:
            return None
        orig_w, orig_h = int(dims[0]), int(dims[1])
    except (subprocess.TimeoutExpired, ValueError):
        return None

    # Compute downscale dimensions
    if orig_w > max_width:
        scale_w = max_width
        scale_h = int(orig_h * max_width / orig_w)
        # Ensure even dimensions for FFmpeg
        scale_h = scale_h + (scale_h % 2)
        scale_filter = f",scale={scale_w}:{scale_h}"
    else:
        scale_w, scale_h = orig_w, orig_h
        scale_filter = ""

    # Extract single frame as raw RGB
    try:
        cmd = [
            "ffmpeg", "-v", "error",
            "-ss", str(max(0.0, time_sec)),
            "-i", str(p),
            "-vframes", "1",
            "-vf", f"format=rgb24{scale_filter}",
            "-f", "rawvideo",
            "-pix_fmt", "rgb24",
            "pipe:1",
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        if result.returncode != 0 or len(result.stdout) == 0:
            return None

        expected_bytes = scale_w * scale_h * 3
        raw = result.stdout[:expected_bytes]
        if len(raw) < expected_bytes:
            return None

        frame = np.frombuffer(raw, dtype=np.uint8).reshape(scale_h, scale_w, 3)
        return frame
    except (subprocess.TimeoutExpired, ValueError) as e:
        logger.warning("Frame extraction failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Scope computations — pure numpy, no cv2 dependency
# ---------------------------------------------------------------------------

def compute_histogram(frame_rgb: "np.ndarray") -> dict[str, list[int]]:
    """RGB histogram — 256 bins per channel.

    Returns: { "r": [256 ints], "g": [256 ints], "b": [256 ints] }
    """
    r_hist = np.bincount(frame_rgb[:, :, 0].ravel(), minlength=256)[:256]
    g_hist = np.bincount(frame_rgb[:, :, 1].ravel(), minlength=256)[:256]
    b_hist = np.bincount(frame_rgb[:, :, 2].ravel(), minlength=256)[:256]
    return {
        "r": r_hist.tolist(),
        "g": g_hist.tolist(),
        "b": b_hist.tolist(),
    }


def compute_waveform(frame_rgb: "np.ndarray", scope_w: int = 256, scope_h: int = 256) -> list[list[int]]:
    """Luma waveform scope — returns 2D array [scope_h][scope_w] of intensity values.

    Y-axis = luma level (0 at bottom, 255 at top).
    X-axis = pixel column (downsampled to scope_w).
    Value = hit count (clamped to 0-255 for direct canvas rendering).
    """
    # Compute luma (Rec.709)
    luma = np.dot(frame_rgb[..., :3].astype(np.float32), [0.2126, 0.7152, 0.0722]).astype(np.uint8)

    h, w = luma.shape
    # Downsample columns to scope_w
    if w > scope_w:
        # Simple column sampling — fast enough for scopes
        indices = np.linspace(0, w - 1, scope_w, dtype=int)
        luma_ds = luma[:, indices]
    else:
        luma_ds = luma
        scope_w = w

    # Build waveform: for each column, count pixel values
    scope = np.zeros((scope_h, scope_w), dtype=np.int32)

    for x in range(scope_w):
        col = luma_ds[:, x]
        # Map 0-255 to scope_h bins
        mapped = (col.astype(np.float32) * (scope_h - 1) / 255.0).astype(int)
        hist = np.bincount(mapped, minlength=scope_h)[:scope_h]
        scope[:, x] = hist

    # Flip vertically so 0 = bottom, 255 = top
    scope = scope[::-1]

    # Normalize to 0-255 for display
    max_val = scope.max()
    if max_val > 0:
        scope = np.clip(scope * 200 // max_val, 0, 255)

    return scope.astype(np.uint8).tolist()


def compute_vectorscope(frame_rgb: "np.ndarray", scope_size: int = 256) -> list[list[int]]:
    """Vectorscope — CbCr plot (Rec.601).

    Returns 2D array [scope_size][scope_size] of intensity values.
    Center = neutral grey, distance from center = saturation, angle = hue.
    """
    # RGB → YCbCr (Rec.601)
    r = frame_rgb[:, :, 0].astype(np.float32)
    g = frame_rgb[:, :, 1].astype(np.float32)
    b = frame_rgb[:, :, 2].astype(np.float32)

    # Cb and Cr (range roughly -128..127 mapped to 0..255)
    cb = (-0.168736 * r - 0.331264 * g + 0.5 * b).ravel()
    cr = (0.5 * r - 0.418688 * g - 0.081312 * b).ravel()

    # Map to scope coordinates (center = scope_size/2)
    half = scope_size / 2
    # Scale factor: Cb/Cr range is ±128, map to ±half
    scale = half / 128.0
    cx = (cb * scale + half).astype(int)
    cy = (-cr * scale + half).astype(int)  # Invert Y for display convention

    # Clamp to bounds
    cx = np.clip(cx, 0, scope_size - 1)
    cy = np.clip(cy, 0, scope_size - 1)

    # Accumulate hits
    scope = np.zeros((scope_size, scope_size), dtype=np.int32)
    np.add.at(scope, (cy, cx), 1)

    # Normalize with log scale for visibility
    scope_log = np.log1p(scope.astype(np.float32))
    max_val = scope_log.max()
    if max_val > 0:
        scope_out = (scope_log * 255.0 / max_val).astype(np.uint8)
    else:
        scope_out = np.zeros((scope_size, scope_size), dtype=np.uint8)

    return scope_out.tolist()


# ---------------------------------------------------------------------------
# High-level API — single call for all scopes
# ---------------------------------------------------------------------------

# LRU cache keyed on (source_path, time_sec rounded to ±2 frames at 25fps)
def _cache_key(source_path: str, time_sec: float) -> tuple[str, float]:
    """Round time to nearest 0.08s (±2 frames at 25fps) for cache hits."""
    return (source_path, round(time_sec * 12.5) / 12.5)


_scope_cache: dict[tuple[str, float], dict[str, Any]] = {}
_CACHE_MAX = 32


def analyze_frame_scopes(
    source_path: str,
    time_sec: float = 0.0,
    scopes: list[str] | None = None,
    scope_size: int = 256,
) -> dict[str, Any]:
    """Extract frame and compute requested scopes.

    Args:
        source_path: path to video file
        time_sec: timestamp to extract frame from
        scopes: list of scope types to compute (default: all)
                 Valid: "histogram", "waveform", "vectorscope"
        scope_size: output resolution for waveform/vectorscope

    Returns:
        {
            "success": True,
            "source_path": str,
            "time_sec": float,
            "histogram": { "r": [...], "g": [...], "b": [...] },
            "waveform": [[...], ...],
            "vectorscope": [[...], ...],
            "frame_w": int,
            "frame_h": int,
        }
    """
    if not HAS_NUMPY:
        return {"success": False, "error": "numpy_not_available"}

    if scopes is None:
        scopes = ["histogram", "waveform", "vectorscope"]

    # Check cache
    cache_key = _cache_key(source_path, time_sec)
    cached = _scope_cache.get(cache_key)
    if cached is not None:
        # Return cached if all requested scopes are present
        if all(s in cached for s in scopes):
            return cached

    # Extract frame
    frame = extract_frame_rgb(source_path, time_sec, max_width=scope_size * 2)
    if frame is None:
        return {
            "success": False,
            "error": "frame_extraction_failed",
            "source_path": source_path,
            "time_sec": time_sec,
        }

    result: dict[str, Any] = {
        "success": True,
        "source_path": source_path,
        "time_sec": time_sec,
        "frame_w": frame.shape[1],
        "frame_h": frame.shape[0],
    }

    if "histogram" in scopes:
        result["histogram"] = compute_histogram(frame)

    if "waveform" in scopes:
        result["waveform"] = compute_waveform(frame, scope_w=scope_size, scope_h=scope_size)

    if "vectorscope" in scopes:
        result["vectorscope"] = compute_vectorscope(frame, scope_size=scope_size)

    # Update cache (evict oldest if full)
    if len(_scope_cache) >= _CACHE_MAX:
        oldest = next(iter(_scope_cache))
        del _scope_cache[oldest]
    _scope_cache[cache_key] = result

    return result
