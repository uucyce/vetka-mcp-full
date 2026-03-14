"""
MARKER_172.10 — FFmpeg-based waveform extraction.
Extracts PCM via FFmpeg subprocess → computes RMS bins for accurate waveform display.
Falls back to byte-scanning stub when FFmpeg is unavailable.
"""
from __future__ import annotations

import math
import os
import shutil
import struct
import subprocess
import tempfile
from typing import Any

# ─── FFmpeg detection ───

FFMPEG = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
HAS_FFMPEG = FFMPEG is not None


def extract_pcm_mono_16bit(
    media_path: str,
    *,
    sample_rate: int = 16000,
    max_duration_sec: float = 0.0,
    timeout_sec: float = 30.0,
) -> bytes | None:
    """Extract mono 16-bit PCM from any media file via FFmpeg.

    Returns raw PCM bytes (signed 16-bit little-endian, mono) or None on failure.
    """
    if not HAS_FFMPEG:
        return None
    if not os.path.isfile(media_path):
        return None

    cmd = [
        FFMPEG,  # type: ignore[list-item]
        "-i", media_path,
        "-vn",                      # skip video
        "-ac", "1",                 # mono
        "-ar", str(sample_rate),    # resample
        "-f", "s16le",              # raw signed 16-bit LE
        "-acodec", "pcm_s16le",
    ]
    if max_duration_sec > 0:
        cmd.extend(["-t", str(max_duration_sec)])
    cmd.append("pipe:1")  # output to stdout

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout_sec,
        )
        if result.returncode != 0:
            return None
        return result.stdout if result.stdout else None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def pcm_to_rms_bins(
    pcm_data: bytes,
    *,
    sample_rate: int = 16000,
    bins: int = 64,
) -> list[float]:
    """Compute RMS energy bins from raw 16-bit PCM data.

    Returns list of `bins` float values in [0.0, 1.0] range.
    """
    num_samples = len(pcm_data) // 2  # 16-bit = 2 bytes per sample
    if num_samples == 0:
        return [0.0] * bins

    samples_per_bin = max(1, num_samples // bins)
    result: list[float] = []

    for i in range(bins):
        start = i * samples_per_bin
        end = min(start + samples_per_bin, num_samples)
        if start >= num_samples:
            result.append(0.0)
            continue

        # Unpack 16-bit signed samples
        chunk = pcm_data[start * 2 : end * 2]
        n = len(chunk) // 2
        if n == 0:
            result.append(0.0)
            continue

        samples = struct.unpack(f"<{n}h", chunk)
        # RMS normalized to [0, 1] (32768 = max 16-bit amplitude)
        sum_sq = sum(s * s for s in samples)
        rms = math.sqrt(sum_sq / n) / 32768.0
        result.append(round(min(1.0, rms), 4))

    return result


def build_waveform_ffmpeg(
    media_path: str,
    bins: int = 64,
    *,
    sample_rate: int = 16000,
    max_duration_sec: float = 600.0,
) -> tuple[list[float], bool, str]:
    """Build waveform bins using FFmpeg PCM extraction + RMS computation.

    Returns: (bins_list, degraded_mode, degraded_reason)
    - degraded_mode=False means FFmpeg succeeded with real audio data
    - degraded_mode=True means fallback or error
    """
    pcm = extract_pcm_mono_16bit(
        media_path,
        sample_rate=sample_rate,
        max_duration_sec=max_duration_sec,
    )
    if pcm is None:
        return ([0.0] * bins, True, "ffmpeg_unavailable" if not HAS_FFMPEG else "ffmpeg_extraction_failed")

    if len(pcm) < 4:
        return ([0.0] * bins, True, "no_audio_data")

    rms_bins = pcm_to_rms_bins(pcm, sample_rate=sample_rate, bins=bins)
    return (rms_bins, False, "")


def build_waveform_with_fallback(
    media_path: str,
    bins: int = 64,
    *,
    sample_rate: int = 16000,
    max_duration_sec: float = 600.0,
) -> tuple[list[float], bool, str]:
    """Try FFmpeg first, fall back to byte-scanning proxy.

    This is the main entry point for waveform generation.
    """
    if HAS_FFMPEG:
        result_bins, degraded, reason = build_waveform_ffmpeg(
            media_path, bins,
            sample_rate=sample_rate,
            max_duration_sec=max_duration_sec,
        )
        if not degraded:
            return (result_bins, False, "")
        # FFmpeg failed on this file — fall through to byte-scan

    return _byte_scan_fallback(media_path, bins)


def _byte_scan_fallback(path: str, bins: int) -> tuple[list[float], bool, str]:
    """Original byte-scanning stub — used when FFmpeg unavailable."""
    try:
        with open(path, "rb") as f:
            data = f.read(8192)
    except Exception as exc:
        return ([0.0] * bins, True, f"read_failed:{str(exc)[:48]}")
    if not data:
        return ([0.0] * bins, True, "empty_file")
    chunk_size = max(1, len(data) // bins)
    values: list[float] = []
    for index in range(bins):
        chunk = data[index * chunk_size : (index + 1) * chunk_size]
        if not chunk:
            values.append(0.0)
            continue
        avg = sum(abs(byte - 128) for byte in chunk) / (len(chunk) * 128.0)
        values.append(round(max(0.0, min(1.0, avg)), 4))
    return (values, True, "byte_scan_fallback")
