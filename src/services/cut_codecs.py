"""
MARKER_SPLIT_CODECS — CUT Codec Registry + Log Decode Filters.

Extracted from cut_render_engine.py (MARKER_B5 split).
Codec map for FFmpeg encode, camera log profile decode filters.

@status: active
@phase: B5
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Codec map — FFmpeg encoder configs keyed by preset name
# ---------------------------------------------------------------------------

CODEC_MAP: dict[str, dict[str, str]] = {
    # === Apple ProRes family ===
    "prores_proxy": {"vcodec": "prores_ks", "profile": "0", "ext": ".mov", "pix_fmt": "yuv422p10le"},
    "prores_lt":    {"vcodec": "prores_ks", "profile": "1", "ext": ".mov", "pix_fmt": "yuv422p10le"},
    "prores_422":   {"vcodec": "prores_ks", "profile": "2", "ext": ".mov", "pix_fmt": "yuv422p10le"},
    "prores_422hq": {"vcodec": "prores_ks", "profile": "3", "ext": ".mov", "pix_fmt": "yuv422p10le"},
    "prores_4444":  {"vcodec": "prores_ks", "profile": "4", "ext": ".mov", "pix_fmt": "yuva444p10le"},
    "prores_4444xq": {"vcodec": "prores_ks", "profile": "5", "ext": ".mov", "pix_fmt": "yuva444p10le"},
    # === Avid DNxHR family ===
    "dnxhr_lb":  {"vcodec": "dnxhd", "profile": "dnxhr_lb",  "ext": ".mxf", "pix_fmt": "yuv422p"},
    "dnxhr_sq":  {"vcodec": "dnxhd", "profile": "dnxhr_sq",  "ext": ".mxf", "pix_fmt": "yuv422p"},
    "dnxhr_hq":  {"vcodec": "dnxhd", "profile": "dnxhr_hq",  "ext": ".mxf", "pix_fmt": "yuv422p"},
    "dnxhr_hqx": {"vcodec": "dnxhd", "profile": "dnxhr_hqx", "ext": ".mxf", "pix_fmt": "yuv422p10le"},
    "dnxhr_444": {"vcodec": "dnxhd", "profile": "dnxhr_444", "ext": ".mxf", "pix_fmt": "yuv444p10le"},
    "dnxhd":     {"vcodec": "dnxhd", "profile": "",           "ext": ".mxf", "pix_fmt": "yuv422p"},
    # === H.264 / AVC ===
    "h264":        {"vcodec": "libx264",    "profile": "",     "ext": ".mp4", "pix_fmt": "yuv420p"},
    "h264_10bit":  {"vcodec": "libx264",    "profile": "high10", "ext": ".mp4", "pix_fmt": "yuv420p10le"},
    # === H.265 / HEVC ===
    "h265":        {"vcodec": "libx265",    "profile": "",     "ext": ".mp4", "pix_fmt": "yuv420p"},
    "h265_10bit":  {"vcodec": "libx265",    "profile": "main10", "ext": ".mp4", "pix_fmt": "yuv420p10le"},
    # === Web / Modern codecs ===
    "vp9":    {"vcodec": "libvpx-vp9", "profile": "", "ext": ".webm", "pix_fmt": "yuv420p"},
    "av1":    {"vcodec": "libsvtav1",  "profile": "", "ext": ".mp4",  "pix_fmt": "yuv420p10le"},
    "av1_8":  {"vcodec": "libsvtav1",  "profile": "", "ext": ".mp4",  "pix_fmt": "yuv420p"},
    # === Lossless / Intermediate ===
    "ffv1":     {"vcodec": "ffv1",     "profile": "", "ext": ".mkv",  "pix_fmt": "yuv422p10le"},
    "huffyuv":  {"vcodec": "huffyuv",  "profile": "", "ext": ".avi",  "pix_fmt": "yuv422p"},
    "ut_video": {"vcodec": "utvideo",  "profile": "", "ext": ".avi",  "pix_fmt": "yuv422p"},
    # === Legacy / Broadcast ===
    "mpeg2":  {"vcodec": "mpeg2video", "profile": "", "ext": ".mxf", "pix_fmt": "yuv422p"},
    "mjpeg":  {"vcodec": "mjpeg",      "profile": "", "ext": ".avi", "pix_fmt": "yuvj420p"},
    # === Image sequence ===
    "png_seq":  {"vcodec": "png",      "profile": "", "ext": ".png", "pix_fmt": "rgb24"},
    "tiff_seq": {"vcodec": "tiff",     "profile": "", "ext": ".tiff", "pix_fmt": "rgb48le"},
    "dpx_seq":  {"vcodec": "dpx",      "profile": "", "ext": ".dpx", "pix_fmt": "gbrp10le"},
    "exr_seq":  {"vcodec": "exr",      "profile": "", "ext": ".exr", "pix_fmt": "gbrpf32le"},
}


# ---------------------------------------------------------------------------
# MARKER_B16: Camera log profile → FFmpeg decode filters
# ---------------------------------------------------------------------------

_LOG_DECODE_FILTERS: dict[str, str] = {
    # V-Log (Panasonic) → approximate Rec.709 via curves
    "V-Log": "curves=master='0/0 0.09/0 0.13/0.05 0.25/0.15 0.42/0.35 0.52/0.50 0.65/0.70 0.78/0.85 0.90/0.95 1/1'",
    # S-Log3 (Sony) → approximate Rec.709
    "S-Log3": "curves=master='0/0 0.10/0 0.15/0.04 0.25/0.12 0.40/0.30 0.50/0.47 0.63/0.68 0.75/0.82 0.88/0.94 1/1'",
    # ARRI LogC3 → approximate Rec.709
    "LogC3": "curves=master='0/0 0.09/0 0.12/0.03 0.22/0.12 0.38/0.32 0.48/0.48 0.60/0.67 0.73/0.82 0.86/0.93 1/1'",
    "ARRI LogC3": "curves=master='0/0 0.09/0 0.12/0.03 0.22/0.12 0.38/0.32 0.48/0.48 0.60/0.67 0.73/0.82 0.86/0.93 1/1'",
    # Canon Log 3
    "Canon Log 3": "curves=master='0/0 0.08/0 0.12/0.04 0.24/0.14 0.40/0.33 0.50/0.48 0.62/0.66 0.74/0.80 0.88/0.94 1/1'",
    # sRGB → no decode needed (already Rec.709 gamma)
    "sRGB": "",
    # HLG (Hybrid Log-Gamma) → FFmpeg has native support
    "HLG": "zscale=transfer=bt709:transferin=arib-std-b67",
    # PQ (Perceptual Quantizer / HDR10) → tone-map to SDR
    "PQ": "zscale=transfer=bt709:transferin=smpte2084:tonemap=hable",
}


def compile_log_decode_filter(profile: str) -> str:
    """
    Get FFmpeg filter for decoding camera log profile to Rec.709.

    Returns empty string if profile is unknown or no decode needed.
    The curves approximation is serviceable for editing preview;
    for final delivery, use a proper 3D LUT from the camera manufacturer.
    """
    return _LOG_DECODE_FILTERS.get(profile, "")


# Backward compat alias (was private, now public)
_compile_log_decode_filter = compile_log_decode_filter
