"""
MARKER_B19 — CUT Video Scope Renderer.

Computes waveform (luma), parade (RGB), vectorscope (YCbCr) from numpy frames.
Pure numpy — no cv2 dependency. FFmpeg subprocess for frame extraction.

Performance targets (1080p → 256px scope):
  Waveform: ~5-10ms | Parade: ~15-25ms | Vectorscope: ~8-15ms | All: ~30-50ms

@status: active
@phase: B19
@task: tb_1773995025_4
"""
from __future__ import annotations

import logging
import subprocess
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
    """Extract single frame as uint8 RGB numpy array, downscaled to max_width."""
    if not HAS_NUMPY:
        return None

    p = Path(source_path)
    if not p.exists():
        return None

    try:
        probe_cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(p),
        ]
        probe = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=5)
        if probe.returncode != 0:
            return None
        dims = probe.stdout.strip().split("x")
        orig_w, orig_h = int(dims[0]), int(dims[1])
    except Exception:
        return None

    if orig_w > max_width:
        scale_w = max_width
        scale_h = int(orig_h * max_width / orig_w)
        scale_h += scale_h % 2
        scale_filter = f",scale={scale_w}:{scale_h}"
    else:
        scale_w, scale_h = orig_w, orig_h
        scale_filter = ""

    try:
        cmd = [
            "ffmpeg", "-v", "error", "-ss", str(max(0.0, time_sec)),
            "-i", str(p), "-vframes", "1",
            "-vf", f"format=rgb24{scale_filter}",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        if result.returncode != 0 or not result.stdout:
            return None
        expected = scale_w * scale_h * 3
        raw = result.stdout[:expected]
        if len(raw) < expected:
            return None
        return np.frombuffer(raw, dtype=np.uint8).reshape(scale_h, scale_w, 3).copy()
    except Exception as e:
        logger.warning("Frame extraction failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Scope computations — pure numpy
# ---------------------------------------------------------------------------

def compute_histogram(frame_rgb: "np.ndarray") -> dict[str, list[int]]:
    """RGB histogram — 256 bins per channel."""
    return {
        "r": np.bincount(frame_rgb[:, :, 0].ravel(), minlength=256)[:256].tolist(),
        "g": np.bincount(frame_rgb[:, :, 1].ravel(), minlength=256)[:256].tolist(),
        "b": np.bincount(frame_rgb[:, :, 2].ravel(), minlength=256)[:256].tolist(),
    }


def compute_waveform(frame_rgb: "np.ndarray", scope_w: int = 256, scope_h: int = 256) -> list[list[int]]:
    """Luma waveform — Y-axis=luma level, X-axis=pixel column."""
    luma = np.dot(frame_rgb[..., :3].astype(np.float32), [0.2126, 0.7152, 0.0722]).astype(np.uint8)
    h, w = luma.shape
    if w > scope_w:
        indices = np.linspace(0, w - 1, scope_w, dtype=int)
        luma_ds = luma[:, indices]
    else:
        luma_ds = luma
        scope_w = w

    scope = np.zeros((scope_h, scope_w), dtype=np.int32)
    for x in range(scope_w):
        mapped = (luma_ds[:, x].astype(np.float32) * (scope_h - 1) / 255.0).astype(int)
        hist = np.bincount(mapped, minlength=scope_h)[:scope_h]
        scope[:, x] = hist

    scope = scope[::-1]
    mx = scope.max()
    if mx > 0:
        scope = np.clip(scope * 200 // mx, 0, 255)
    return scope.astype(np.uint8).tolist()


def compute_parade(frame_rgb: "np.ndarray", scope_w: int = 256, scope_h: int = 256) -> dict[str, list[list[int]]]:
    """RGB Parade — separate waveform per R/G/B channel.

    Returns: { "r": [[scope_h][scope_w]], "g": ..., "b": ... }
    Each channel is a waveform showing that channel's distribution per column.
    """
    h, w, _ = frame_rgb.shape

    # Downsample width
    if w > scope_w:
        indices = np.linspace(0, w - 1, scope_w, dtype=int)
    else:
        indices = np.arange(w)
        scope_w = w

    result = {}
    for ch_idx, ch_name in enumerate(["r", "g", "b"]):
        channel = frame_rgb[:, indices, ch_idx]
        scope = np.zeros((scope_h, scope_w), dtype=np.int32)
        for x in range(scope_w):
            mapped = (channel[:, x].astype(np.float32) * (scope_h - 1) / 255.0).astype(int)
            hist = np.bincount(mapped, minlength=scope_h)[:scope_h]
            scope[:, x] = hist
        scope = scope[::-1]
        mx = scope.max()
        if mx > 0:
            scope = np.clip(scope * 200 // mx, 0, 255)
        result[ch_name] = scope.astype(np.uint8).tolist()

    return result


def compute_vectorscope(frame_rgb: "np.ndarray", scope_size: int = 256) -> list[list[int]]:
    """Vectorscope — YCbCr CbCr plot (Rec.601). Log-scale for visibility."""
    r = frame_rgb[:, :, 0].astype(np.float32)
    g = frame_rgb[:, :, 1].astype(np.float32)
    b = frame_rgb[:, :, 2].astype(np.float32)

    cb = (-0.168736 * r - 0.331264 * g + 0.5 * b).ravel()
    cr = (0.5 * r - 0.418688 * g - 0.081312 * b).ravel()

    half = scope_size / 2
    scale = half / 128.0
    cx = np.clip((cb * scale + half).astype(int), 0, scope_size - 1)
    cy = np.clip((-cr * scale + half).astype(int), 0, scope_size - 1)

    scope = np.zeros((scope_size, scope_size), dtype=np.int32)
    np.add.at(scope, (cy, cx), 1)

    scope_log = np.log1p(scope.astype(np.float32))
    mx = scope_log.max()
    if mx > 0:
        scope_out = (scope_log * 255.0 / mx).astype(np.uint8)
    else:
        scope_out = np.zeros((scope_size, scope_size), dtype=np.uint8)
    return scope_out.tolist()


# ---------------------------------------------------------------------------
# High-level API
# ---------------------------------------------------------------------------

_scope_cache: dict[tuple[str, float], dict[str, Any]] = {}
_CACHE_MAX = 32


def _cache_key(source_path: str, time_sec: float) -> tuple[str, float]:
    return (source_path, round(time_sec * 12.5) / 12.5)


def analyze_frame_scopes(
    source_path: str,
    time_sec: float = 0.0,
    scopes: list[str] | None = None,
    scope_size: int = 256,
) -> dict[str, Any]:
    """Extract frame and compute requested scopes.

    Valid scopes: "histogram", "waveform", "vectorscope", "parade"
    """
    if not HAS_NUMPY:
        return {"success": False, "error": "numpy_not_available"}

    if scopes is None:
        scopes = ["histogram", "waveform", "vectorscope"]

    cache_key = _cache_key(source_path, time_sec)
    cached = _scope_cache.get(cache_key)
    if cached and all(s in cached for s in scopes):
        return cached

    frame = extract_frame_rgb(source_path, time_sec, max_width=scope_size * 2)
    if frame is None:
        return {"success": False, "error": "frame_extraction_failed",
                "source_path": source_path, "time_sec": time_sec}

    result: dict[str, Any] = {
        "success": True, "source_path": source_path, "time_sec": time_sec,
        "frame_w": frame.shape[1], "frame_h": frame.shape[0],
    }

    if "histogram" in scopes:
        result["histogram"] = compute_histogram(frame)
    if "waveform" in scopes:
        result["waveform"] = compute_waveform(frame, scope_w=scope_size, scope_h=scope_size)
    if "vectorscope" in scopes:
        result["vectorscope"] = compute_vectorscope(frame, scope_size=scope_size)
    if "parade" in scopes:
        result["parade"] = compute_parade(frame, scope_w=scope_size, scope_h=scope_size)

    if len(_scope_cache) >= _CACHE_MAX:
        del _scope_cache[next(iter(_scope_cache))]
    _scope_cache[cache_key] = result
    return result
