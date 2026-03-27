"""
MARKER_B20 — CUT Preview Decoder.

Real-time preview pipeline: decode video frame → downscale → color pipeline → JPEG.
Two decode backends:
  1. PyAV (preferred): av.open() → container.decode() → numpy frame
  2. FFmpeg subprocess (fallback): ffmpeg → rawvideo pipe → numpy

Preview frames are sent to frontend via SocketIO or returned as base64 JPEG.

Per Beta-1 feedback: "FFmpeg CLI for render, PyAV for preview/scopes/LUT. Don't mix layers."
This module is the PyAV preview layer — or FFmpeg subprocess when PyAV is unavailable.

Architecture:
  decode_preview_frame(source, time, opts) → graded uint8 RGB
  PreviewSession: stateful seek + decode for scrubbing (PyAV container reuse)

Performance targets:
  540p proxy decode + LUT: ~30fps on M-series Mac
  1080p decode + LUT: ~15fps

@status: active
@phase: B20
@task: tb_1773995026_5
@depends: cut_color_pipeline (B18), cut_scope_renderer (frame extraction)
"""
from __future__ import annotations

import base64
import logging
import subprocess
import time as time_module
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Try importing PyAV
try:
    import av
    HAS_PYAV = True
except ImportError:
    av = None  # type: ignore[assignment]
    HAS_PYAV = False

from src.services.cut_color_pipeline import apply_color_pipeline


# ---------------------------------------------------------------------------
# Frame decode — dual backend (PyAV / FFmpeg subprocess)
# ---------------------------------------------------------------------------

def _probe_dimensions(source_path: str) -> tuple[int, int] | None:
    """Get video dimensions via ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0:s=x",
            str(source_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return None
        parts = result.stdout.strip().split("x")
        if len(parts) >= 2:
            return int(parts[0]), int(parts[1])
    except Exception:
        pass
    return None


def _compute_proxy_dims(
    orig_w: int, orig_h: int, max_height: int = 540
) -> tuple[int, int]:
    """Compute proxy dimensions maintaining aspect ratio."""
    if orig_h <= max_height:
        return orig_w, orig_h
    scale = max_height / orig_h
    w = int(orig_w * scale)
    # Ensure even dimensions
    w = w + (w % 2)
    h = max_height + (max_height % 2)
    return w, h


def decode_frame_pyav(
    source_path: str,
    time_sec: float,
    proxy_height: int = 540,
) -> np.ndarray | None:
    """Decode a single frame using PyAV. Returns uint8 RGB numpy array."""
    if not HAS_PYAV:
        return None

    try:
        container = av.open(source_path)
        stream = container.streams.video[0]

        # Seek to nearest keyframe
        pts = int(time_sec / stream.time_base)
        container.seek(pts, stream=stream)

        # Decode first frame after seek
        for frame in container.decode(video=0):
            # Convert to RGB numpy
            rgb_frame = frame.to_ndarray(format="rgb24")

            # Downscale if needed
            orig_h, orig_w = rgb_frame.shape[:2]
            if orig_h > proxy_height:
                pw, ph = _compute_proxy_dims(orig_w, orig_h, proxy_height)
                # Use PyAV's built-in reformatter for fast resize
                reformatted = frame.reformat(width=pw, height=ph, format="rgb24")
                rgb_frame = reformatted.to_ndarray(format="rgb24")

            container.close()
            return rgb_frame

        container.close()
    except Exception as e:
        logger.warning("PyAV decode failed for %s @ %.2fs: %s", source_path, time_sec, e)

    return None


def decode_frame_ffmpeg(
    source_path: str,
    time_sec: float,
    proxy_height: int = 540,
) -> np.ndarray | None:
    """Decode a single frame using FFmpeg subprocess. Returns uint8 RGB numpy array."""
    dims = _probe_dimensions(source_path)
    if dims is None:
        return None

    orig_w, orig_h = dims
    pw, ph = _compute_proxy_dims(orig_w, orig_h, proxy_height)

    try:
        cmd = [
            "ffmpeg", "-v", "error",
            "-ss", str(max(0.0, time_sec)),
            "-i", str(source_path),
            "-vframes", "1",
            "-vf", f"scale={pw}:{ph}",
            "-f", "rawvideo",
            "-pix_fmt", "rgb24",
            "pipe:1",
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        if result.returncode != 0 or len(result.stdout) == 0:
            return None

        expected = pw * ph * 3
        raw = result.stdout[:expected]
        if len(raw) < expected:
            return None

        return np.frombuffer(raw, dtype=np.uint8).reshape(ph, pw, 3).copy()
    except Exception as e:
        logger.warning("FFmpeg decode failed: %s", e)
        return None


def decode_frame(
    source_path: str,
    time_sec: float = 0.0,
    proxy_height: int = 540,
) -> np.ndarray | None:
    """Decode a single preview frame. Tries PyAV first, falls back to FFmpeg."""
    if not Path(source_path).exists():
        return None

    # Try PyAV first (faster for sequential access)
    if HAS_PYAV:
        frame = decode_frame_pyav(source_path, time_sec, proxy_height)
        if frame is not None:
            return frame

    # Fallback to FFmpeg subprocess
    return decode_frame_ffmpeg(source_path, time_sec, proxy_height)


# ---------------------------------------------------------------------------
# Preview frame with full color pipeline
# ---------------------------------------------------------------------------

def decode_preview_frame(
    source_path: str,
    time_sec: float = 0.0,
    proxy_height: int = 540,
    log_profile: str | None = None,
    lut_path: str | None = None,
) -> np.ndarray | None:
    """Decode + apply color pipeline. Returns graded uint8 RGB frame."""
    frame = decode_frame(source_path, time_sec, proxy_height)
    if frame is None:
        return None

    # Apply color pipeline (log decode + LUT)
    if log_profile or lut_path:
        frame = apply_color_pipeline(frame, log_profile=log_profile, lut_path=lut_path)

    return frame


def encode_preview_jpeg(frame_rgb: np.ndarray, quality: int = 80) -> bytes | None:
    """Encode RGB frame to JPEG bytes using FFmpeg."""
    h, w, _ = frame_rgb.shape
    try:
        cmd = [
            "ffmpeg", "-v", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{w}x{h}",
            "-i", "pipe:0",
            "-vframes", "1",
            "-f", "image2", "-vcodec", "mjpeg",
            "-q:v", str(max(1, min(31, 31 - int(quality * 31 / 100)))),
            "pipe:1",
        ]
        proc = subprocess.run(cmd, input=frame_rgb.tobytes(), capture_output=True, timeout=5)
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout
    except Exception as e:
        logger.warning("JPEG encode failed: %s", e)
    return None


def preview_frame_as_b64(
    source_path: str,
    time_sec: float = 0.0,
    proxy_height: int = 540,
    log_profile: str | None = None,
    lut_path: str | None = None,
    jpeg_quality: int = 80,
) -> dict[str, Any]:
    """Full preview pipeline: decode → color → JPEG → base64.

    Returns dict with success, data (base64), width, height, timing_ms.
    """
    t0 = time_module.monotonic()

    frame = decode_preview_frame(source_path, time_sec, proxy_height, log_profile, lut_path)
    if frame is None:
        return {"success": False, "error": "decode_failed"}

    jpeg = encode_preview_jpeg(frame, jpeg_quality)
    if jpeg is None:
        return {"success": False, "error": "encode_failed"}

    elapsed_ms = (time_module.monotonic() - t0) * 1000

    return {
        "success": True,
        "width": frame.shape[1],
        "height": frame.shape[0],
        "format": "jpeg",
        "data": base64.b64encode(jpeg).decode("ascii"),
        "timing_ms": round(elapsed_ms, 1),
        "decoder": "pyav" if HAS_PYAV else "ffmpeg",
        "log_profile": log_profile,
        "lut_path": lut_path,
    }


# ---------------------------------------------------------------------------
# PyAV-based PreviewSession — stateful, for scrubbing (container reuse)
# ---------------------------------------------------------------------------

class PreviewSession:
    """Stateful preview session with container reuse for fast scrubbing.

    Keeps the PyAV container open between seeks, avoiding re-open overhead.
    Falls back to per-frame FFmpeg subprocess if PyAV unavailable.
    """

    def __init__(
        self,
        source_path: str,
        proxy_height: int = 540,
        log_profile: str | None = None,
        lut_path: str | None = None,
    ):
        self.source_path = source_path
        self.proxy_height = proxy_height
        self.log_profile = log_profile
        self.lut_path = lut_path
        self._container = None
        self._stream = None
        self._last_time: float = -1.0

        if HAS_PYAV and Path(source_path).exists():
            try:
                self._container = av.open(source_path)
                self._stream = self._container.streams.video[0]
            except Exception as e:
                logger.warning("Failed to open PyAV container: %s", e)

    def seek_and_decode(self, time_sec: float) -> np.ndarray | None:
        """Decode frame at time_sec, reusing container."""
        if self._container and self._stream:
            try:
                pts = int(time_sec / self._stream.time_base)
                self._container.seek(pts, stream=self._stream)

                for frame in self._container.decode(video=0):
                    rgb = frame.to_ndarray(format="rgb24")
                    h, w = rgb.shape[:2]
                    if h > self.proxy_height:
                        pw, ph = _compute_proxy_dims(w, h, self.proxy_height)
                        ref = frame.reformat(width=pw, height=ph, format="rgb24")
                        rgb = ref.to_ndarray(format="rgb24")

                    if self.log_profile or self.lut_path:
                        rgb = apply_color_pipeline(rgb, self.log_profile, self.lut_path)

                    self._last_time = time_sec
                    return rgb
            except Exception as e:
                logger.debug("PyAV scrub failed, falling back: %s", e)

        # Fallback
        return decode_preview_frame(
            self.source_path, time_sec, self.proxy_height,
            self.log_profile, self.lut_path,
        )

    def get_preview_b64(self, time_sec: float, jpeg_quality: int = 80) -> dict[str, Any]:
        """Decode + encode to base64 JPEG."""
        t0 = time_module.monotonic()
        frame = self.seek_and_decode(time_sec)
        if frame is None:
            return {"success": False, "error": "decode_failed"}

        jpeg = encode_preview_jpeg(frame, jpeg_quality)
        if jpeg is None:
            return {"success": False, "error": "encode_failed"}

        elapsed_ms = (time_module.monotonic() - t0) * 1000
        return {
            "success": True,
            "width": frame.shape[1],
            "height": frame.shape[0],
            "data": base64.b64encode(jpeg).decode("ascii"),
            "timing_ms": round(elapsed_ms, 1),
            "time_sec": time_sec,
        }

    @property
    def info(self) -> dict[str, Any]:
        """Session metadata."""
        duration = 0.0
        fps = 25.0
        if self._stream:
            if self._stream.duration and self._stream.time_base:
                duration = float(self._stream.duration * self._stream.time_base)
            fps = float(self._stream.average_rate) if self._stream.average_rate else 25.0

        return {
            "source_path": self.source_path,
            "proxy_height": self.proxy_height,
            "decoder": "pyav" if self._container else "ffmpeg",
            "duration": duration,
            "fps": fps,
            "log_profile": self.log_profile,
            "lut_path": self.lut_path,
        }

    def close(self):
        if self._container:
            try:
                self._container.close()
            except Exception:
                pass
            self._container = None
            self._stream = None

    def __del__(self):
        self.close()


# ---------------------------------------------------------------------------
# Numpy-based effects application (pixel-level, for preview)
# ---------------------------------------------------------------------------

def apply_numpy_effects(
    frame_float32: np.ndarray,
    effects: list[dict[str, Any]],
) -> np.ndarray:
    """Apply video effects at pixel level using numpy.

    This is the preview-path equivalent of compile_video_filters() in cut_effects_engine.
    Only handles effects that can be done efficiently in numpy.

    Args:
        frame_float32: float32 [0, 1], shape (H, W, 3)
        effects: list of effect dicts with "type" and "params"

    Returns:
        Processed float32 frame [0, 1]
    """
    for e in effects:
        if not e.get("enabled", True):
            continue

        t = e.get("type", "")
        p = e.get("params", {})

        if t == "brightness":
            val = float(p.get("value", 0))
            if val != 0:
                frame_float32 = frame_float32 + val

        elif t == "contrast":
            val = float(p.get("value", 1))
            if val != 1.0:
                frame_float32 = (frame_float32 - 0.5) * val + 0.5

        elif t == "saturation":
            val = float(p.get("value", 1))
            if val != 1.0:
                luma = np.dot(frame_float32, [0.2126, 0.7152, 0.0722])
                luma3 = luma[:, :, np.newaxis]
                frame_float32 = luma3 + (frame_float32 - luma3) * val

        elif t == "gamma":
            val = float(p.get("value", 1))
            if val != 1.0:
                frame_float32 = np.power(np.clip(frame_float32, 0, 1), 1.0 / val)

        elif t == "exposure":
            stops = float(p.get("stops", 0))
            if stops != 0:
                frame_float32 = frame_float32 * (2.0 ** stops)

        elif t == "hue":
            deg = float(p.get("degrees", 0))
            if deg != 0:
                # Simple hue rotation via matrix
                rad = deg * np.pi / 180.0
                cos_a, sin_a = np.cos(rad), np.sin(rad)
                # Simplified hue rotation matrix
                mat = np.array([
                    [0.213 + cos_a * 0.787 - sin_a * 0.213,
                     0.715 - cos_a * 0.715 - sin_a * 0.715,
                     0.072 - cos_a * 0.072 + sin_a * 0.928],
                    [0.213 - cos_a * 0.213 + sin_a * 0.143,
                     0.715 + cos_a * 0.285 + sin_a * 0.140,
                     0.072 - cos_a * 0.072 - sin_a * 0.283],
                    [0.213 - cos_a * 0.213 - sin_a * 0.787,
                     0.715 - cos_a * 0.715 + sin_a * 0.715,
                     0.072 + cos_a * 0.928 + sin_a * 0.072],
                ], dtype=np.float32)
                frame_float32 = np.dot(frame_float32, mat.T)

        elif t == "opacity":
            val = float(p.get("value", 1))
            if val < 1.0:
                frame_float32 = frame_float32 * val

        elif t == "broadcast_safe":
            # MARKER_B26: Clamp to broadcast-safe range (16-235 → 0.0627-0.9216)
            frame_float32 = np.clip(frame_float32, 16.0 / 255.0, 235.0 / 255.0)

        # === MARKER_B9.5: Blur / Sharpen / Denoise / Vignette ===

        elif t == "blur":
            sigma = float(p.get("sigma", 0))
            if sigma > 0:
                # Approximated gaussian blur via repeated box blur (3 passes)
                k = max(1, int(sigma * 1.5))
                for _pass in range(3):
                    # Horizontal
                    padded = np.pad(frame_float32, ((0, 0), (k, k), (0, 0)), mode='edge')
                    cs = np.cumsum(padded, axis=1)
                    frame_float32 = (cs[:, 2*k:, :] - cs[:, :padded.shape[1]-2*k, :]) / (2*k+1)
                    # Vertical
                    padded = np.pad(frame_float32, ((k, k), (0, 0), (0, 0)), mode='edge')
                    cs = np.cumsum(padded, axis=0)
                    frame_float32 = (cs[2*k:, :, :] - cs[:padded.shape[0]-2*k, :, :]) / (2*k+1)

        elif t == "sharpen":
            amount = float(p.get("amount", 0))
            if amount > 0:
                k = max(1, int(p.get("size", 5)) // 2)
                h, w = frame_float32.shape[:2]
                # Unsharp mask: sharp = original + amount * (original - blurred)
                blurred = frame_float32.copy()
                # Horizontal box blur
                padded = np.pad(blurred, ((0, 0), (k, k), (0, 0)), mode='edge')
                cs = np.cumsum(padded, axis=1)
                blurred = (cs[:, 2*k:, :] - cs[:, :padded.shape[1]-2*k, :]) / (2*k+1)
                # Vertical box blur
                padded = np.pad(blurred, ((k, k), (0, 0), (0, 0)), mode='edge')
                cs = np.cumsum(padded, axis=0)
                blurred = (cs[2*k:, :, :] - cs[:padded.shape[0]-2*k, :, :]) / (2*k+1)
                # Trim to original size (cumsum can be off by 1)
                blurred = blurred[:h, :w, :]
                frame_float32 = frame_float32 + amount * (frame_float32 - blurred)

        elif t == "denoise":
            strength = float(p.get("strength", 0))
            if strength > 0:
                h, w = frame_float32.shape[:2]
                # Simple averaging blur as denoise approximation
                k = max(1, int(strength / 3))
                # Horizontal
                padded = np.pad(frame_float32, ((0, 0), (k, k), (0, 0)), mode='edge')
                cs = np.cumsum(padded, axis=1)
                smoothed = (cs[:, 2*k:, :] - cs[:, :padded.shape[1]-2*k, :]) / (2*k+1)
                # Vertical
                padded = np.pad(smoothed, ((k, k), (0, 0), (0, 0)), mode='edge')
                cs = np.cumsum(padded, axis=0)
                smoothed = (cs[2*k:, :, :] - cs[:padded.shape[0]-2*k, :, :]) / (2*k+1)
                smoothed = smoothed[:h, :w, :]  # trim to original size
                # Blend: mix smoothed with original (preserve edges somewhat)
                blend = min(1.0, strength / 10.0)
                frame_float32 = frame_float32 * (1 - blend) + smoothed * blend

        elif t == "vignette":
            angle = float(p.get("angle", 0.4))
            if angle > 0:
                h, w = frame_float32.shape[:2]
                cy, cx = h / 2.0, w / 2.0
                y_coords, x_coords = np.mgrid[0:h, 0:w].astype(np.float32)
                # Normalized distance from center (0 at center, 1 at corners)
                dist = np.sqrt(((x_coords - cx) / cx) ** 2 + ((y_coords - cy) / cy) ** 2)
                # Vignette falloff: stronger angle = more darkening
                vignette_mask = np.clip(1.0 - dist * angle, 0, 1)[:, :, np.newaxis]
                frame_float32 = frame_float32 * vignette_mask

        # === MARKER_B9: Color grading effects (FCP7 Ch.79-83) ===

        elif t == "lift":
            # 3-way: Shadows (lift) — add RGB offset to dark regions
            r_off = float(p.get("r", 0))
            g_off = float(p.get("g", 0))
            b_off = float(p.get("b", 0))
            if r_off != 0 or g_off != 0 or b_off != 0:
                # Lift affects shadows: weight by (1 - luma)
                luma = np.dot(frame_float32, [0.2126, 0.7152, 0.0722])[:, :, np.newaxis]
                shadow_weight = np.clip(1.0 - luma * 2.0, 0, 1)  # strongest in darks
                offsets = np.array([r_off, g_off, b_off], dtype=np.float32)
                frame_float32 = frame_float32 + offsets * shadow_weight

        elif t == "midtone":
            # 3-way: Midtones (gamma) — shift RGB in midtone range
            r_off = float(p.get("r", 0))
            g_off = float(p.get("g", 0))
            b_off = float(p.get("b", 0))
            if r_off != 0 or g_off != 0 or b_off != 0:
                luma = np.dot(frame_float32, [0.2126, 0.7152, 0.0722])[:, :, np.newaxis]
                # Bell curve peaking at 0.5 luma
                mid_weight = np.clip(1.0 - np.abs(luma - 0.5) * 4.0, 0, 1)
                offsets = np.array([r_off, g_off, b_off], dtype=np.float32)
                frame_float32 = frame_float32 + offsets * mid_weight

        elif t == "gain":
            # 3-way: Highlights (gain) — shift RGB in bright regions
            r_off = float(p.get("r", 0))
            g_off = float(p.get("g", 0))
            b_off = float(p.get("b", 0))
            if r_off != 0 or g_off != 0 or b_off != 0:
                luma = np.dot(frame_float32, [0.2126, 0.7152, 0.0722])[:, :, np.newaxis]
                highlight_weight = np.clip(luma * 2.0 - 1.0, 0, 1)  # strongest in brights
                offsets = np.array([r_off, g_off, b_off], dtype=np.float32)
                frame_float32 = frame_float32 + offsets * highlight_weight

        elif t == "white_balance":
            # MARKER_B76: Tanner Helland Kelvin→RGB for accurate preview
            temp = float(p.get("temperature", 6500))
            if abs(temp - 6500) > 50:
                from src.services.cut_effects_engine import _kelvin_to_rgb_adjustment
                r_adj, g_adj, b_adj = _kelvin_to_rgb_adjustment(temp)
                frame_float32[:, :, 0] += r_adj * 0.6   # Red (scaled for preview visibility)
                frame_float32[:, :, 1] += g_adj * 0.6   # Green
                frame_float32[:, :, 2] += b_adj * 0.6   # Blue
            tint = float(p.get("tint", 0))
            if abs(tint) > 1:
                tint_adj = tint / 200.0
                frame_float32[:, :, 0] += tint_adj * 0.15   # Red: slight boost for magenta
                frame_float32[:, :, 1] -= tint_adj * 0.5     # Green: main axis
                frame_float32[:, :, 2] += tint_adj * 0.15   # Blue: slight boost for magenta

        elif t == "curves":
            # Curve presets applied as LUT transforms
            preset = str(p.get("preset", "none"))
            if preset != "none" and preset:
                # Predefined curve adjustments (matches FFmpeg curves filter presets)
                if preset == "lighter":
                    frame_float32 = np.power(np.clip(frame_float32, 0, 1), 0.8)
                elif preset == "darker":
                    frame_float32 = np.power(np.clip(frame_float32, 0, 1), 1.3)
                elif preset == "increase_contrast":
                    frame_float32 = (frame_float32 - 0.5) * 1.3 + 0.5
                elif preset == "decrease_contrast":
                    frame_float32 = (frame_float32 - 0.5) * 0.7 + 0.5
                elif preset == "strong_contrast":
                    frame_float32 = (frame_float32 - 0.5) * 1.6 + 0.5
                elif preset == "negative":
                    frame_float32 = 1.0 - frame_float32
                elif preset == "vintage":
                    # Desaturate slightly + warm shift + lifted blacks
                    luma = np.dot(frame_float32, [0.2126, 0.7152, 0.0722])[:, :, np.newaxis]
                    frame_float32 = luma + (frame_float32 - luma) * 0.7  # desaturate
                    frame_float32[:, :, 0] += 0.03  # warm
                    frame_float32[:, :, 2] -= 0.02
                    frame_float32 = np.maximum(frame_float32, 0.05)  # lift blacks
                elif preset == "cross_process":
                    # Push green shadows, magenta highlights
                    frame_float32[:, :, 1] += (1.0 - frame_float32[:, :, 1]) * 0.08
                    frame_float32[:, :, 0] += frame_float32[:, :, 0] * 0.05
                    frame_float32[:, :, 2] += frame_float32[:, :, 2] * 0.03

        elif t == "color_balance":
            # Unified 9-parameter color balance: shadows (rs/gs/bs), mids (rm/gm/bm), highlights (rh/gh/bh)
            rs = float(p.get("rs", 0)); gs = float(p.get("gs", 0)); bs = float(p.get("bs", 0))
            rm = float(p.get("rm", 0)); gm = float(p.get("gm", 0)); bm = float(p.get("bm", 0))
            rh = float(p.get("rh", 0)); gh = float(p.get("gh", 0)); bh = float(p.get("bh", 0))
            has_any = any(v != 0 for v in [rs, gs, bs, rm, gm, bm, rh, gh, bh])
            if has_any:
                luma = np.dot(frame_float32, [0.2126, 0.7152, 0.0722])[:, :, np.newaxis]
                shadow_w = np.clip(1.0 - luma * 2.0, 0, 1)
                mid_w = np.clip(1.0 - np.abs(luma - 0.5) * 4.0, 0, 1)
                high_w = np.clip(luma * 2.0 - 1.0, 0, 1)
                s_off = np.array([rs, gs, bs], dtype=np.float32)
                m_off = np.array([rm, gm, bm], dtype=np.float32)
                h_off = np.array([rh, gh, bh], dtype=np.float32)
                frame_float32 = frame_float32 + s_off * shadow_w + m_off * mid_w + h_off * high_w

        # === MARKER_B28: Motion effects (FCP7 Ch.66) ===

        elif t == "drop_shadow":
            # Drop shadow: create dark shifted copy, blur, composite behind
            offset = float(p.get("offset", 10))
            angle_deg = float(p.get("angle", 135))
            softness = float(p.get("softness", 5))
            shadow_opacity = float(p.get("opacity", 0.5))
            if offset > 0 and shadow_opacity > 0:
                h, w = frame_float32.shape[:2]
                rad = angle_deg * np.pi / 180.0
                dx = int(round(offset * np.cos(rad)))
                dy = int(round(-offset * np.sin(rad)))  # screen Y is inverted
                # Shadow = solid dark, shifted by (dx, dy)
                shadow = np.zeros_like(frame_float32)
                # Compute source and dest slices for the shift
                src_y0 = max(0, -dy)
                src_y1 = min(h, h - dy)
                src_x0 = max(0, -dx)
                src_x1 = min(w, w - dx)
                dst_y0 = max(0, dy)
                dst_y1 = min(h, h + dy)
                dst_x0 = max(0, dx)
                dst_x1 = min(w, w + dx)
                if dst_y1 > dst_y0 and dst_x1 > dst_x0:
                    shadow[dst_y0:dst_y1, dst_x0:dst_x1] = shadow_opacity
                # Blur the shadow mask (box blur approximation)
                if softness > 0:
                    k = max(1, int(softness))
                    # Separable box blur: horizontal then vertical
                    kernel = np.ones(2 * k + 1, dtype=np.float32) / (2 * k + 1)
                    for ch in range(3):
                        col = shadow[:, :, ch]
                        # Horizontal pass
                        padded = np.pad(col, ((0, 0), (k, k)), mode='edge')
                        conv_h = np.cumsum(padded, axis=1)
                        col_h = (conv_h[:, 2*k:] - conv_h[:, :padded.shape[1]-2*k]) / (2*k+1)
                        # Vertical pass
                        padded_v = np.pad(col_h, ((k, k), (0, 0)), mode='edge')
                        conv_v = np.cumsum(padded_v, axis=0)
                        shadow[:, :, ch] = (conv_v[2*k:, :] - conv_v[:padded_v.shape[0]-2*k, :]) / (2*k+1)
                # Composite: shadow behind frame (where frame is transparent = dark areas)
                # For opaque frames: blend shadow under, then frame on top
                frame_float32 = shadow * (1.0 - frame_float32) + frame_float32 * (1.0 - shadow * 0.3) + shadow * 0.3 * frame_float32
                # Simplified: darken areas where shadow falls, keep frame pixels
                frame_float32 = np.clip(frame_float32, 0, 1)

        elif t == "distort":
            # 4-corner perspective warp (corner pin)
            tl_x = float(p.get("tl_x", 0.0))
            tl_y = float(p.get("tl_y", 0.0))
            tr_x = float(p.get("tr_x", 1.0))
            tr_y = float(p.get("tr_y", 0.0))
            bl_x = float(p.get("bl_x", 0.0))
            bl_y = float(p.get("bl_y", 1.0))
            br_x = float(p.get("br_x", 1.0))
            br_y = float(p.get("br_y", 1.0))
            # Skip if all corners are at default positions
            is_default = (
                abs(tl_x) < 0.001 and abs(tl_y) < 0.001 and
                abs(tr_x - 1.0) < 0.001 and abs(tr_y) < 0.001 and
                abs(bl_x) < 0.001 and abs(bl_y - 1.0) < 0.001 and
                abs(br_x - 1.0) < 0.001 and abs(br_y - 1.0) < 0.001
            )
            if not is_default:
                h, w = frame_float32.shape[:2]
                # Build inverse perspective mapping using bilinear interpolation
                # For each output pixel, find the source pixel via inverse bilinear
                oy, ox = np.mgrid[0:h, 0:w].astype(np.float32)
                ny = oy / max(h - 1, 1)  # normalized 0-1
                nx = ox / max(w - 1, 1)
                # Bilinear interpolation of corner positions
                src_x = (
                    tl_x * (1 - nx) * (1 - ny) +
                    tr_x * nx * (1 - ny) +
                    bl_x * (1 - nx) * ny +
                    br_x * nx * ny
                )
                src_y = (
                    tl_y * (1 - nx) * (1 - ny) +
                    tr_y * nx * (1 - ny) +
                    bl_y * (1 - nx) * ny +
                    br_y * nx * ny
                )
                # Convert back to pixel coordinates
                map_x = (src_x * (w - 1)).astype(np.int32)
                map_y = (src_y * (h - 1)).astype(np.int32)
                # Clamp to valid range
                map_x = np.clip(map_x, 0, w - 1)
                map_y = np.clip(map_y, 0, h - 1)
                # Apply remapping
                frame_float32 = frame_float32[map_y, map_x]

        elif t == "motion_blur":
            # Directional motion blur via box kernel convolution
            amount = float(p.get("amount", 0))
            if amount > 0:
                k = max(1, int(amount / 2))  # half-kernel size
                # Horizontal motion blur (separable, fast)
                # Use cumsum trick for O(1) per-pixel box blur
                padded = np.pad(frame_float32, ((0, 0), (k, k), (0, 0)), mode='edge')
                cumsum = np.cumsum(padded, axis=1)
                frame_float32 = (cumsum[:, 2*k:, :] - cumsum[:, :padded.shape[1]-2*k, :]) / (2*k + 1)

    return np.clip(frame_float32, 0, 1).astype(np.float32)
