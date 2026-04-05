"""
MARKER_B19 — CUT Video Scope Renderer.

Computes waveform (luma), parade (RGB), vectorscope (YCbCr) from numpy frames.
Pure numpy — no cv2 dependency. FFmpeg subprocess for frame extraction.

Performance targets (1080p → 256px scope):
  Waveform: ~2-4ms | Parade: ~5-10ms | Vectorscope: ~8-15ms | All: ~15-30ms
  (MARKER_B95: vectorized — eliminated per-column Python loops)

@status: active
@phase: B19, B95
@task: tb_1773995025_4, tb_1774410419_1
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
    """Luma waveform — Y-axis=luma level, X-axis=pixel column.

    MARKER_B95: Vectorized — single np.bincount on flat 2D indices
    replaces per-column Python loop. ~3-5× faster (256 bincount calls → 1).
    """
    luma = np.dot(frame_rgb[..., :3].astype(np.float32), [0.2126, 0.7152, 0.0722]).astype(np.uint8)
    h, w = luma.shape
    if w > scope_w:
        indices = np.linspace(0, w - 1, scope_w, dtype=int)
        luma_ds = luma[:, indices]
    else:
        luma_ds = luma
        scope_w = w

    # Map all pixels to scope Y-coordinates at once
    mapped = (luma_ds.astype(np.float32) * (scope_h - 1) / 255.0).astype(np.intp)
    # Column index for each pixel (broadcast across rows)
    col_idx = np.broadcast_to(np.arange(scope_w, dtype=np.intp), luma_ds.shape)
    # Single bincount on flattened (row, col) → flat index
    flat_idx = mapped.ravel() * scope_w + col_idx.ravel()
    scope = np.bincount(flat_idx, minlength=scope_h * scope_w)[:scope_h * scope_w]
    scope = scope.reshape(scope_h, scope_w)

    scope = scope[::-1]
    mx = scope.max()
    if mx > 0:
        scope = np.clip(scope * 200 // mx, 0, 255)
    return scope.astype(np.uint8).tolist()


def compute_parade(frame_rgb: "np.ndarray", scope_w: int = 256, scope_h: int = 256) -> dict[str, list[list[int]]]:
    """RGB Parade — separate waveform per R/G/B channel.

    MARKER_B95: Vectorized — same flat-bincount approach as compute_waveform.
    768 bincount calls → 3. ~3-5× faster.

    Returns: { "r": [[scope_h][scope_w]], "g": ..., "b": ... }
    """
    h, w, _ = frame_rgb.shape

    if w > scope_w:
        indices = np.linspace(0, w - 1, scope_w, dtype=int)
    else:
        indices = np.arange(w)
        scope_w = w

    # Pre-compute column indices (shared across channels)
    col_idx = np.broadcast_to(np.arange(scope_w, dtype=np.intp), (h, scope_w))
    col_flat = col_idx.ravel()
    total_bins = scope_h * scope_w

    result = {}
    for ch_idx, ch_name in enumerate(["r", "g", "b"]):
        channel = frame_rgb[:, indices, ch_idx]
        mapped = (channel.astype(np.float32) * (scope_h - 1) / 255.0).astype(np.intp)
        flat_idx = mapped.ravel() * scope_w + col_flat
        scope = np.bincount(flat_idx, minlength=total_bins)[:total_bins]
        scope = scope.reshape(scope_h, scope_w)
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
# MARKER_B26: Broadcast Safe filter + zebra detection
# ---------------------------------------------------------------------------

# Rec.709 broadcast legal range (8-bit):
#   Luma Y: 16-235 (studio swing)
#   Chroma Cb/Cr: 16-240 (centered at 128)
BROADCAST_LUMA_MIN = 16
BROADCAST_LUMA_MAX = 235
BROADCAST_CHROMA_MIN = 16
BROADCAST_CHROMA_MAX = 240


def broadcast_safe_clamp(frame_rgb: "np.ndarray") -> "np.ndarray":
    """Clamp RGB frame to broadcast-safe Rec.709 levels.

    Converts to YCbCr, clamps Y to 16-235 and Cb/Cr to 16-240,
    converts back to RGB. Input/output: uint8 (0-255).
    """
    r = frame_rgb[:, :, 0].astype(np.float32)
    g = frame_rgb[:, :, 1].astype(np.float32)
    b = frame_rgb[:, :, 2].astype(np.float32)

    # RGB → YCbCr (Rec.601/709 studio swing)
    y = 16 + 65.481 * r / 255 + 128.553 * g / 255 + 24.966 * b / 255
    cb = 128 - 37.797 * r / 255 - 74.203 * g / 255 + 112.0 * b / 255
    cr = 128 + 112.0 * r / 255 - 93.786 * g / 255 - 18.214 * b / 255

    # Clamp to legal range
    y = np.clip(y, BROADCAST_LUMA_MIN, BROADCAST_LUMA_MAX)
    cb = np.clip(cb, BROADCAST_CHROMA_MIN, BROADCAST_CHROMA_MAX)
    cr = np.clip(cr, BROADCAST_CHROMA_MIN, BROADCAST_CHROMA_MAX)

    # YCbCr → RGB
    r_out = 1.164 * (y - 16) + 1.596 * (cr - 128)
    g_out = 1.164 * (y - 16) - 0.392 * (cb - 128) - 0.813 * (cr - 128)
    b_out = 1.164 * (y - 16) + 2.017 * (cb - 128)

    result = np.stack([r_out, g_out, b_out], axis=-1)
    return np.clip(result, 0, 255).astype(np.uint8)


def detect_out_of_range(frame_rgb: "np.ndarray") -> dict[str, Any]:
    """Detect pixels that exceed broadcast-safe levels.

    Returns:
        {
            "over_white_pct": float,   # % pixels with Y > 235
            "under_black_pct": float,  # % pixels with Y < 16
            "chroma_illegal_pct": float, # % pixels with Cb/Cr outside 16-240
            "total_illegal_pct": float,
            "zebra_mask": list[list[int]]  # 2D mask: 1=over, 2=under, 3=chroma, 0=safe
        }
    """
    r = frame_rgb[:, :, 0].astype(np.float32)
    g = frame_rgb[:, :, 1].astype(np.float32)
    b = frame_rgb[:, :, 2].astype(np.float32)

    y = 16 + 65.481 * r / 255 + 128.553 * g / 255 + 24.966 * b / 255
    cb = 128 - 37.797 * r / 255 - 74.203 * g / 255 + 112.0 * b / 255
    cr = 128 + 112.0 * r / 255 - 93.786 * g / 255 - 18.214 * b / 255

    total_px = float(y.size)
    over_white = y > BROADCAST_LUMA_MAX
    under_black = y < BROADCAST_LUMA_MIN
    chroma_illegal = (cb < BROADCAST_CHROMA_MIN) | (cb > BROADCAST_CHROMA_MAX) | \
                     (cr < BROADCAST_CHROMA_MIN) | (cr > BROADCAST_CHROMA_MAX)

    # Build zebra mask (downsampled for JSON transport)
    h, w = y.shape
    ds = max(1, max(h, w) // 128)  # downsample to ~128px max
    mask = np.zeros((h, w), dtype=np.uint8)
    mask[over_white] = 1
    mask[under_black] = 2
    mask[chroma_illegal & (mask == 0)] = 3

    # Downsample mask
    if ds > 1:
        mask_ds = mask[::ds, ::ds]
    else:
        mask_ds = mask

    return {
        "over_white_pct": round(float(over_white.sum()) / total_px * 100, 2),
        "under_black_pct": round(float(under_black.sum()) / total_px * 100, 2),
        "chroma_illegal_pct": round(float(chroma_illegal.sum()) / total_px * 100, 2),
        "total_illegal_pct": round(float((over_white | under_black | chroma_illegal).sum()) / total_px * 100, 2),
        "zebra_mask": mask_ds.tolist(),
    }


# ---------------------------------------------------------------------------
# High-level API
# ---------------------------------------------------------------------------

_scope_cache: dict[tuple, dict[str, Any]] = {}
_CACHE_MAX = 32


def _cache_key(source_path: str, time_sec: float) -> tuple[str, float]:
    return (source_path, round(time_sec * 12.5) / 12.5)


def analyze_frame_scopes(
    source_path: str,
    time_sec: float = 0.0,
    scopes: list[str] | None = None,
    scope_size: int = 256,
    log_profile: str | None = None,
    lut_path: str | None = None,
) -> dict[str, Any]:
    """Extract frame and compute requested scopes.

    Valid scopes: "histogram", "waveform", "vectorscope", "parade", "broadcast_safe"

    If log_profile or lut_path provided, applies color pipeline BEFORE
    scope computation (post-grade scopes).
    """
    if not HAS_NUMPY:
        return {"success": False, "error": "numpy_not_available"}

    if scopes is None:
        scopes = ["histogram", "waveform", "vectorscope"]

    # MARKER_B25: Include grading params in cache key
    graded = bool(log_profile or lut_path)
    cache_key_base = _cache_key(source_path, time_sec)
    cache_key = (cache_key_base[0], cache_key_base[1], log_profile or "", lut_path or "")
    cached = _scope_cache.get(cache_key)
    if cached and all(s in cached for s in scopes):
        return cached

    frame = extract_frame_rgb(source_path, time_sec, max_width=scope_size * 2)
    if frame is None:
        return {"success": False, "error": "frame_extraction_failed",
                "source_path": source_path, "time_sec": time_sec}

    # MARKER_B25: Apply color pipeline for post-grade scopes
    if graded:
        try:
            from src.services.cut_color_pipeline import apply_color_pipeline
            frame = apply_color_pipeline(frame, log_profile=log_profile, lut_path=lut_path)
        except ImportError:
            pass  # color pipeline not available, use raw frame

    result: dict[str, Any] = {
        "success": True, "source_path": source_path, "time_sec": time_sec,
        "frame_w": frame.shape[1], "frame_h": frame.shape[0],
        "graded": graded,
    }

    if "histogram" in scopes:
        result["histogram"] = compute_histogram(frame)
    if "waveform" in scopes:
        result["waveform"] = compute_waveform(frame, scope_w=scope_size, scope_h=scope_size)
    if "vectorscope" in scopes:
        result["vectorscope"] = compute_vectorscope(frame, scope_size=scope_size)
    if "parade" in scopes:
        result["parade"] = compute_parade(frame, scope_w=scope_size, scope_h=scope_size)
    if "broadcast_safe" in scopes:
        result["broadcast_safe"] = detect_out_of_range(frame)

    if len(_scope_cache) >= _CACHE_MAX:
        del _scope_cache[next(iter(_scope_cache))]
    _scope_cache[cache_key] = result
    return result
