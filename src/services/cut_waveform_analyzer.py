"""
MARKER_B15 — Audio Waveform Analysis Service.

Generate normalized waveform peaks from audio files for timeline visualization.
Supports any audio format via FFmpeg extraction, analyzes with numpy.

@status: active
@phase: B15
@task: tb_1775176256_34682_1
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Literal

import numpy as np


@dataclass
class WaveformData:
    """Waveform analysis result."""
    peaks: list[float]  # Normalized peak values per pixel [0, 1]
    duration_sec: float
    channels: int
    sample_rate: int
    norm_type: Literal["rms", "peak"]


# Simple in-memory cache: (audio_path, width_px, norm_type) → WaveformData
_waveform_cache: dict[tuple[str, int, str], WaveformData] = {}


def compile_waveform_peaks(
    audio_path: str,
    width_px: int = 800,
    norm_type: Literal["rms", "peak"] = "rms",
    use_cache: bool = True,
) -> WaveformData:
    """
    Generate normalized waveform peaks from audio file.

    MARKER_B15: Extract audio, bin into width_px segments, compute peak/RMS per bin,
    normalize to [0, 1].

    Args:
        audio_path: Path to audio file (any format FFmpeg supports)
        width_px: Number of pixels (bins) for waveform
        norm_type: "rms" (energy-based, smooth) or "peak" (maximum amplitude)
        use_cache: Cache results by (path, width, norm_type)

    Returns:
        WaveformData with peaks list and metadata

    Raises:
        FileNotFoundError: If audio_path doesn't exist
        RuntimeError: If FFmpeg extraction fails
    """
    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Check cache
    cache_key = (audio_path, width_px, norm_type)
    if use_cache and cache_key in _waveform_cache:
        return _waveform_cache[cache_key]

    try:
        # Step 1: Extract audio via FFmpeg as PCM WAV (mono, 16-bit, 44.1kHz)
        # Using mono to simplify analysis (average channels if multi-channel)
        samples, sr, channels = _extract_audio_samples(audio_path)

        # Step 2: Bin samples into width_px segments
        bin_size = max(1, len(samples) // width_px)
        peaks: list[float] = []

        for i in range(width_px):
            start = i * bin_size
            end = min((i + 1) * bin_size, len(samples))
            bin_samples = samples[start:end]

            if len(bin_samples) == 0:
                peaks.append(0.0)
                continue

            # Compute peak or RMS
            if norm_type == "rms":
                value = float(np.sqrt(np.mean(bin_samples**2)))
            else:  # peak
                value = float(np.max(np.abs(bin_samples)))

            peaks.append(value)

        # Step 3: Normalize to [0, 1]
        max_peak = max(peaks) if peaks else 1.0
        if max_peak > 0:
            peaks = [p / max_peak for p in peaks]
        else:
            peaks = [0.0] * width_px

        # Duration calculation
        duration_sec = len(samples) / sr

        result = WaveformData(
            peaks=peaks,
            duration_sec=duration_sec,
            channels=channels,
            sample_rate=sr,
            norm_type=norm_type,
        )

        if use_cache:
            _waveform_cache[cache_key] = result

        return result

    except Exception as e:
        raise RuntimeError(f"Waveform analysis failed: {e}") from e


def _extract_audio_samples(audio_path: str, target_sr: int = 44100) -> tuple[np.ndarray, int, int]:
    """
    Extract audio samples from file using FFmpeg.

    Converts any audio format to mono PCM WAV at 16-bit, target_sr Hz.

    Args:
        audio_path: Path to audio file
        target_sr: Target sample rate (default 44100 Hz)

    Returns:
        Tuple of (samples_array, sample_rate, num_channels_original)

    Raises:
        RuntimeError: If FFmpeg extraction fails
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Get original channel info first
        probe_cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=channels",
            "-of", "default=noprint_wrappers=1:nokey=1:noinvert_units=1",
            audio_path,
        ]
        try:
            channels_output = subprocess.check_output(probe_cmd, text=True).strip()
            original_channels = int(channels_output) if channels_output else 1
        except Exception:
            original_channels = 1

        # Extract audio as mono PCM WAV
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", audio_path,
            "-ac", "1",  # Convert to mono
            "-acodec", "pcm_s16le",  # 16-bit PCM
            "-ar", str(target_sr),  # Target sample rate
            "-y",  # Overwrite
            tmp_path,
        ]

        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")

        # Read WAV file
        # WAV format: RIFF header (12 bytes) + fmt chunk + data chunk
        with open(tmp_path, "rb") as f:
            data = f.read()

        # Parse WAV: simplified (assumes standard format)
        # RIFF header at offset 0-11
        # fmt chunk: audio format (16-bit PCM = 1), channels, sample rate
        # data chunk contains samples

        # Skip RIFF/fmt parsing, use numpy's fromfile + reshape
        # 16-bit = 2 bytes per sample
        samples = np.frombuffer(data[44:], dtype=np.int16)  # Skip WAV header (44 bytes typical)
        samples = samples.astype(np.float32) / 32768.0  # Normalize to [-1, 1]

        return samples, target_sr, original_channels

    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def clear_waveform_cache() -> None:
    """Clear in-memory waveform cache."""
    global _waveform_cache
    _waveform_cache.clear()


def get_waveform_cache_stats() -> dict[str, int]:
    """Get cache statistics."""
    return {
        "cached_clips": len(_waveform_cache),
        "total_peaks": sum(len(w.peaks) for w in _waveform_cache.values()),
    }
