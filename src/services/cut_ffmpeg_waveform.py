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


# ---------------------------------------------------------------------------
# MARKER_B29: Stereo waveform extraction
# ---------------------------------------------------------------------------

def extract_pcm_stereo_16bit(
    media_path: str,
    *,
    sample_rate: int = 16000,
    max_duration_sec: float = 0.0,
    timeout_sec: float = 30.0,
) -> bytes | None:
    """Extract stereo 16-bit PCM from any media file via FFmpeg.

    Returns raw PCM bytes (signed 16-bit LE, 2 channels interleaved: L R L R ...)
    or None on failure.
    """
    if not HAS_FFMPEG:
        return None
    if not os.path.isfile(media_path):
        return None

    cmd = [
        FFMPEG,  # type: ignore[list-item]
        "-i", media_path,
        "-vn",                      # skip video
        "-ac", "2",                 # stereo
        "-ar", str(sample_rate),    # resample
        "-f", "s16le",              # raw signed 16-bit LE
        "-acodec", "pcm_s16le",
    ]
    if max_duration_sec > 0:
        cmd.extend(["-t", str(max_duration_sec)])
    cmd.append("pipe:1")

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


def pcm_stereo_to_rms_bins(
    pcm_data: bytes,
    *,
    bins: int = 64,
) -> tuple[list[float], list[float]]:
    """Compute per-channel RMS bins from interleaved stereo 16-bit PCM.

    Stereo PCM layout: L0 R0 L1 R1 L2 R2 ... (each sample = 2 bytes)
    Returns (left_bins, right_bins), each list of floats in [0.0, 1.0].
    """
    # Each stereo frame = 4 bytes (2 bytes L + 2 bytes R)
    num_frames = len(pcm_data) // 4
    if num_frames == 0:
        return ([0.0] * bins, [0.0] * bins)

    frames_per_bin = max(1, num_frames // bins)
    left_bins: list[float] = []
    right_bins: list[float] = []

    for i in range(bins):
        start = i * frames_per_bin
        end = min(start + frames_per_bin, num_frames)
        if start >= num_frames:
            left_bins.append(0.0)
            right_bins.append(0.0)
            continue

        # Extract interleaved stereo samples for this bin
        chunk = pcm_data[start * 4 : end * 4]
        n = len(chunk) // 4  # number of stereo frames
        if n == 0:
            left_bins.append(0.0)
            right_bins.append(0.0)
            continue

        # Unpack all samples (interleaved L R L R)
        all_samples = struct.unpack(f"<{n * 2}h", chunk)
        left_samples = all_samples[0::2]
        right_samples = all_samples[1::2]

        # RMS per channel
        l_rms = math.sqrt(sum(s * s for s in left_samples) / n) / 32768.0
        r_rms = math.sqrt(sum(s * s for s in right_samples) / n) / 32768.0
        left_bins.append(round(min(1.0, l_rms), 4))
        right_bins.append(round(min(1.0, r_rms), 4))

    return (left_bins, right_bins)


def build_stereo_waveform(
    media_path: str,
    bins: int = 64,
    *,
    sample_rate: int = 16000,
    max_duration_sec: float = 600.0,
) -> tuple[list[float], list[float], bool, str]:
    """Build stereo waveform bins (L/R channels separately).

    Returns: (left_bins, right_bins, degraded, reason)
    """
    pcm = extract_pcm_stereo_16bit(
        media_path,
        sample_rate=sample_rate,
        max_duration_sec=max_duration_sec,
    )
    if pcm is None:
        empty = [0.0] * bins
        reason = "ffmpeg_unavailable" if not HAS_FFMPEG else "ffmpeg_extraction_failed"
        return (empty, empty, True, reason)

    if len(pcm) < 8:  # need at least 2 stereo frames
        empty = [0.0] * bins
        return (empty, empty, True, "no_audio_data")

    left, right = pcm_stereo_to_rms_bins(pcm, bins=bins)
    return (left, right, False, "")


# ---------------------------------------------------------------------------
# MARKER_B5.1: Audio segment extraction for Web Audio playback
# ---------------------------------------------------------------------------

def extract_audio_wav_segment(
    media_path: str,
    *,
    start_sec: float = 0.0,
    duration_sec: float = 30.0,
    sample_rate: int = 44100,
    channels: int = 2,
    timeout_sec: float = 60.0,
) -> bytes | None:
    """Extract audio segment as WAV bytes for Web Audio API playback.

    Returns complete WAV file bytes (header + PCM data) or None on failure.
    Max duration clamped to 30 seconds to prevent memory issues.

    Args:
        media_path: Path to media file.
        start_sec: Start offset in source media (for trimmed clips).
        duration_sec: Duration to extract (max 30s).
        sample_rate: Output sample rate (44100 for Web Audio).
        channels: 1=mono, 2=stereo.
        timeout_sec: FFmpeg timeout.

    Returns:
        WAV file bytes or None.
    """
    if not HAS_FFMPEG:
        return None
    if not os.path.isfile(media_path):
        return None

    # Clamp duration to 30s
    duration_sec = min(30.0, max(0.01, duration_sec))

    cmd = [
        FFMPEG,  # type: ignore[list-item]
        "-ss", str(start_sec),       # seek before input (fast)
        "-i", media_path,
        "-t", str(duration_sec),     # duration
        "-vn",                        # skip video
        "-ac", str(channels),
        "-ar", str(sample_rate),
        "-f", "wav",                  # output WAV format (includes header)
        "-acodec", "pcm_s16le",
        "pipe:1",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout_sec,
        )
        if result.returncode != 0:
            return None
        if not result.stdout or len(result.stdout) < 44:  # WAV header is 44 bytes
            return None
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


# ---------------------------------------------------------------------------
# MARKER_B40: Real-time audio level computation for WebSocket scopes
# ---------------------------------------------------------------------------


def compute_audio_levels(
    media_path: str,
    time_sec: float,
    *,
    window_ms: float = 100.0,
    sample_rate: int = 16000,
    waveform_bins: int = 0,
    timeout_sec: float = 5.0,
) -> dict:
    """Compute audio RMS levels and optional waveform at a specific time position.

    Extracts a short PCM window around time_sec, computes per-channel RMS and peak.
    Designed for real-time WebSocket audio scopes (~2-5ms per call).

    Args:
        media_path: Path to media file.
        time_sec: Playhead position in seconds.
        window_ms: Analysis window in milliseconds (default 100ms).
        sample_rate: Sample rate for extraction (lower = faster, 16kHz sufficient for meters).
        waveform_bins: If > 0, also compute waveform bins for minimap display.
        timeout_sec: FFmpeg timeout (short for real-time use).

    Returns:
        dict with: success, rms_left, rms_right, peak_left, peak_right,
                   waveform_left?, waveform_right?, time_sec, source_path
    """
    result: dict = {
        "success": False,
        "source_path": media_path,
        "time_sec": time_sec,
        "rms_left": 0.0,
        "rms_right": 0.0,
        "peak_left": 0.0,
        "peak_right": 0.0,
    }

    if not HAS_FFMPEG or not os.path.isfile(media_path):
        return result

    duration_sec = window_ms / 1000.0
    start = max(0.0, time_sec - duration_sec / 2)

    cmd = [
        FFMPEG,  # type: ignore[list-item]
        "-ss", f"{start:.3f}",
        "-i", media_path,
        "-t", f"{duration_sec:.3f}",
        "-vn",
        "-ac", "2",  # stereo for L/R analysis
        "-ar", str(sample_rate),
        "-f", "s16le",
        "-acodec", "pcm_s16le",
        "pipe:1",
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout_sec)
        if proc.returncode != 0 or not proc.stdout:
            return result
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return result

    pcm = proc.stdout
    num_frames = len(pcm) // 4  # stereo 16-bit = 4 bytes per frame
    if num_frames == 0:
        return result

    # Unpack all stereo samples
    all_samples = struct.unpack(f"<{num_frames * 2}h", pcm[:num_frames * 4])
    left_samples = all_samples[0::2]
    right_samples = all_samples[1::2]

    # RMS per channel
    n = len(left_samples)
    l_sum_sq = sum(s * s for s in left_samples)
    r_sum_sq = sum(s * s for s in right_samples)
    rms_l = math.sqrt(l_sum_sq / n) / 32768.0
    rms_r = math.sqrt(r_sum_sq / n) / 32768.0

    # Peak per channel (absolute max / 32768)
    peak_l = max(abs(s) for s in left_samples) / 32768.0 if left_samples else 0.0
    peak_r = max(abs(s) for s in right_samples) / 32768.0 if right_samples else 0.0

    result.update({
        "success": True,
        "rms_left": round(min(1.0, rms_l), 4),
        "rms_right": round(min(1.0, rms_r), 4),
        "peak_left": round(min(1.0, peak_l), 4),
        "peak_right": round(min(1.0, peak_r), 4),
    })

    # Optional waveform bins for minimap
    if waveform_bins > 0:
        left_bins, right_bins = pcm_stereo_to_rms_bins(pcm, bins=waveform_bins)
        result["waveform_left"] = left_bins
        result["waveform_right"] = right_bins

    return result


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
