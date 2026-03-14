"""
MARKER_172.14 — FFmpeg-based audio sync: full-file PCM correlation.
Replaces 8KB byte-scanning proxy with real audio extraction + cross-correlation.
Two-pass: coarse (downsampled) → fine (full-rate) for speed + accuracy.
"""
from __future__ import annotations

import struct
import math
from typing import Any

from src.services.cut_audio_intel_eval import SyncResult
from src.services.cut_ffmpeg_waveform import (
    HAS_FFMPEG,
    extract_pcm_mono_16bit,
)


def extract_signal_ffmpeg(
    media_path: str,
    *,
    sample_rate: int = 16000,
    max_duration_sec: float = 120.0,
) -> tuple[list[float], bool, str]:
    """Extract normalized audio signal from media file via FFmpeg.

    Returns: (signal_floats, degraded_mode, degraded_reason)
    Signal is normalized to [-1.0, 1.0] range.
    """
    pcm = extract_pcm_mono_16bit(
        media_path,
        sample_rate=sample_rate,
        max_duration_sec=max_duration_sec,
    )
    if pcm is None:
        return ([], True, "ffmpeg_unavailable" if not HAS_FFMPEG else "ffmpeg_extraction_failed")
    if len(pcm) < 4:
        return ([], True, "no_audio_data")

    num_samples = len(pcm) // 2
    samples = struct.unpack(f"<{num_samples}h", pcm[:num_samples * 2])
    signal = [s / 32768.0 for s in samples]
    return (signal, False, "")


def _downsample(signal: list[float], factor: int) -> list[float]:
    """Simple decimation by averaging blocks."""
    if factor <= 1:
        return signal
    result = []
    for i in range(0, len(signal), factor):
        chunk = signal[i:i + factor]
        result.append(sum(chunk) / len(chunk))
    return result


def _cross_correlate_at_lag(a: list[float], b: list[float], lag: int) -> float:
    """Compute normalized cross-correlation at specific lag."""
    score = 0.0
    count = 0
    for i in range(len(a)):
        j = i + lag
        if 0 <= j < len(b):
            score += a[i] * b[j]
            count += 1
    return score / max(1, count)


def _find_best_lag(
    signal_a: list[float],
    signal_b: list[float],
    max_lag: int,
    step: int = 1,
) -> tuple[int, float]:
    """Find lag with highest cross-correlation score."""
    best_lag = 0
    best_score = float("-inf")
    for lag in range(-max_lag, max_lag + 1, step):
        score = _cross_correlate_at_lag(signal_a, signal_b, lag)
        if score > best_score:
            best_score = score
            best_lag = lag
    return best_lag, best_score


def sync_two_files_ffmpeg(
    reference_path: str,
    candidate_path: str,
    *,
    coarse_rate: int = 2000,
    fine_rate: int = 16000,
    max_lag_sec: float = 10.0,
    max_duration_sec: float = 120.0,
) -> SyncResult:
    """Two-pass audio sync between two media files.

    Pass 1 (coarse): Downsample to coarse_rate, scan full lag range
    Pass 2 (fine): Full rate around coarse estimate, ±0.5 sec window

    Returns SyncResult with detected offset, confidence, method.
    """
    # Extract at fine rate
    ref_signal, ref_deg, ref_reason = extract_signal_ffmpeg(
        reference_path, sample_rate=fine_rate, max_duration_sec=max_duration_sec,
    )
    cand_signal, cand_deg, cand_reason = extract_signal_ffmpeg(
        candidate_path, sample_rate=fine_rate, max_duration_sec=max_duration_sec,
    )

    if ref_deg or cand_deg:
        return SyncResult(
            detected_offset_sec=0.0,
            confidence=0.0,
            method="ffmpeg_sync_v1",
            peak_value=0.0,
        )

    # ─── Pass 1: Coarse scan ───
    downsample_factor = max(1, fine_rate // coarse_rate)
    coarse_a = _downsample(ref_signal, downsample_factor)
    coarse_b = _downsample(cand_signal, downsample_factor)
    coarse_max_lag = int(coarse_rate * max_lag_sec)

    # Limit coarse scan to avoid excessive computation
    coarse_max_lag = min(coarse_max_lag, len(coarse_a), len(coarse_b))

    coarse_lag, coarse_score = _find_best_lag(coarse_a, coarse_b, coarse_max_lag)
    coarse_offset_sec = coarse_lag / coarse_rate

    # ─── Pass 2: Fine refinement ───
    # Search ±0.5 sec around coarse estimate at full rate
    fine_center_lag = int(coarse_offset_sec * fine_rate)
    fine_window = int(fine_rate * 0.5)  # ±0.5 sec
    fine_max_lag = min(fine_center_lag + fine_window, len(ref_signal), len(cand_signal))
    fine_min_lag = max(fine_center_lag - fine_window, -len(ref_signal), -len(cand_signal))

    best_lag = fine_center_lag
    best_score = float("-inf")
    for lag in range(fine_min_lag, fine_max_lag + 1):
        score = _cross_correlate_at_lag(ref_signal, cand_signal, lag)
        if score > best_score:
            best_score = score
            best_lag = lag

    offset_sec = round(best_lag / fine_rate, 4)
    confidence = round(max(0.0, min(1.0, (best_score + 1.0) / 2.0)), 4)
    peak_value = round(best_score if best_score != float("-inf") else 0.0, 4)

    return SyncResult(
        detected_offset_sec=offset_sec,
        confidence=confidence,
        method="ffmpeg_sync_v1",
        peak_value=peak_value,
    )


def extract_signal_with_fallback(
    media_path: str,
    sample_bytes: int = 8192,
    *,
    sample_rate: int = 16000,
    max_duration_sec: float = 120.0,
) -> tuple[list[float], int, bool, str]:
    """Extract audio signal via FFmpeg, fallback to byte-scan.

    Returns: (signal, effective_sample_rate, degraded_mode, reason)
    """
    if HAS_FFMPEG:
        signal, degraded, reason = extract_signal_ffmpeg(
            media_path, sample_rate=sample_rate, max_duration_sec=max_duration_sec,
        )
        if not degraded and signal:
            return (signal, sample_rate, False, "")

    # Byte-scan fallback (original behavior)
    return _byte_scan_signal(media_path, sample_bytes)


def _byte_scan_signal(
    path: str, sample_bytes: int,
) -> tuple[list[float], int, bool, str]:
    """Original 8KB byte-scanning — returns (signal, fake_rate=1000, True, reason)."""
    try:
        with open(path, "rb") as f:
            data = f.read(sample_bytes)
    except Exception as exc:
        return ([], 1000, True, f"read_failed:{str(exc)[:48]}")
    if not data:
        return ([], 1000, True, "empty_file")
    signal = [round((byte - 128) / 128.0, 6) for byte in data]
    return (signal, 1000, True, "byte_scan_fallback")
