"""
MARKER_172.10.FFMPEG_WAVEFORM_TESTS
Tests for FFmpeg-based waveform extraction: PCM extraction, RMS bins,
fallback to byte-scanning when FFmpeg unavailable.
"""
import math
import struct
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.services.cut_ffmpeg_waveform import (
    HAS_FFMPEG,
    build_waveform_ffmpeg,
    build_waveform_with_fallback,
    build_stereo_waveform,
    compute_audio_levels,
    extract_pcm_mono_16bit,
    extract_pcm_stereo_16bit,
    extract_audio_wav_segment,
    pcm_to_rms_bins,
    pcm_stereo_to_rms_bins,
    _byte_scan_fallback,
)


# ─── PCM → RMS conversion (no FFmpeg needed) ───


def test_rms_bins_silence():
    """Silent audio (all zeros) should produce all-zero bins."""
    pcm = b"\x00\x00" * 1600  # 1600 silent samples
    bins = pcm_to_rms_bins(pcm, sample_rate=16000, bins=10)
    assert len(bins) == 10
    assert all(b == 0.0 for b in bins)


def test_rms_bins_full_amplitude():
    """Max amplitude signal should produce bins near 1.0."""
    # Max positive 16-bit sample = 32767
    pcm = struct.pack("<h", 32767) * 1600
    bins = pcm_to_rms_bins(pcm, sample_rate=16000, bins=10)
    assert len(bins) == 10
    assert all(b > 0.99 for b in bins)


def test_rms_bins_half_amplitude():
    """Half amplitude should produce bins near 0.5."""
    pcm = struct.pack("<h", 16384) * 1600
    bins = pcm_to_rms_bins(pcm, sample_rate=16000, bins=10)
    assert len(bins) == 10
    assert all(0.45 < b < 0.55 for b in bins)


def test_rms_bins_varying_signal():
    """First half loud, second half silent → bins should reflect this."""
    loud = struct.pack("<h", 32000) * 800
    silent = b"\x00\x00" * 800
    pcm = loud + silent
    bins = pcm_to_rms_bins(pcm, sample_rate=16000, bins=4)
    assert len(bins) == 4
    # First two bins should be loud
    assert bins[0] > 0.9
    assert bins[1] > 0.9
    # Last two bins should be silent
    assert bins[2] < 0.01
    assert bins[3] < 0.01


def test_rms_bins_empty():
    """Empty PCM data should produce zero bins."""
    bins = pcm_to_rms_bins(b"", sample_rate=16000, bins=8)
    assert len(bins) == 8
    assert all(b == 0.0 for b in bins)


def test_rms_bins_single_sample():
    """Very short PCM should still produce bins."""
    pcm = struct.pack("<h", 16000)  # 1 sample
    bins = pcm_to_rms_bins(pcm, sample_rate=16000, bins=4)
    assert len(bins) == 4
    # First bin should have data, rest zero
    assert bins[0] > 0.0


# ─── Byte-scan fallback ───


def test_byte_scan_fallback_produces_bins(tmp_path: Path):
    """Byte-scan fallback should produce bins from raw file bytes."""
    media = tmp_path / "test.mp4"
    media.write_bytes(bytes(range(256)) * 40)
    bins, degraded, reason = _byte_scan_fallback(str(media), 16)
    assert len(bins) == 16
    assert degraded is True
    assert reason == "byte_scan_fallback"


def test_byte_scan_missing_file():
    """Missing file should return zero bins with degraded."""
    bins, degraded, reason = _byte_scan_fallback("/nonexistent/file.mp4", 8)
    assert len(bins) == 8
    assert degraded is True
    assert "read_failed" in reason


def test_byte_scan_empty_file(tmp_path: Path):
    media = tmp_path / "empty.wav"
    media.write_bytes(b"")
    bins, degraded, reason = _byte_scan_fallback(str(media), 8)
    assert degraded is True
    assert reason == "empty_file"


# ─── FFmpeg integration (skipped if FFmpeg unavailable) ───


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_ffmpeg_extract_pcm_from_wav(tmp_path: Path):
    """Generate a real WAV file and extract PCM via FFmpeg."""
    wav_path = tmp_path / "tone.wav"
    _write_sine_wav(wav_path, freq=440, duration_sec=0.5, sample_rate=16000)

    pcm = extract_pcm_mono_16bit(str(wav_path), sample_rate=16000)
    assert pcm is not None
    assert len(pcm) > 0
    # 0.5 sec × 16000 Hz × 2 bytes = 16000 bytes
    assert len(pcm) == 16000


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_ffmpeg_waveform_from_wav(tmp_path: Path):
    """Full FFmpeg waveform pipeline from WAV file."""
    wav_path = tmp_path / "tone.wav"
    _write_sine_wav(wav_path, freq=440, duration_sec=1.0, sample_rate=16000)

    bins, degraded, reason = build_waveform_ffmpeg(str(wav_path), bins=16)
    assert len(bins) == 16
    assert degraded is False
    assert reason == ""
    # Sine wave should produce non-zero bins
    assert all(b > 0.0 for b in bins)


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_ffmpeg_waveform_with_fallback_uses_ffmpeg(tmp_path: Path):
    """build_waveform_with_fallback should use FFmpeg when available."""
    wav_path = tmp_path / "tone.wav"
    _write_sine_wav(wav_path, freq=440, duration_sec=0.5, sample_rate=16000)

    bins, degraded, reason = build_waveform_with_fallback(str(wav_path), bins=8)
    assert len(bins) == 8
    assert degraded is False
    assert reason == ""


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_ffmpeg_max_duration_limits_output(tmp_path: Path):
    """max_duration_sec should limit extracted PCM."""
    wav_path = tmp_path / "long.wav"
    _write_sine_wav(wav_path, freq=440, duration_sec=2.0, sample_rate=16000)

    pcm = extract_pcm_mono_16bit(str(wav_path), sample_rate=16000, max_duration_sec=1.0)
    assert pcm is not None
    # Should be ~1 sec × 16000 Hz × 2 bytes = 32000 bytes (±some tolerance)
    assert len(pcm) <= 32100


def test_ffmpeg_unavailable_fallback(tmp_path: Path):
    """When FFmpeg is not available, should fall back to byte-scan."""
    media = tmp_path / "test.mp4"
    media.write_bytes(bytes(range(256)) * 40)

    with patch("src.services.cut_ffmpeg_waveform.HAS_FFMPEG", False):
        bins, degraded, reason = build_waveform_with_fallback(str(media), bins=8)
    assert len(bins) == 8
    assert degraded is True
    assert reason == "byte_scan_fallback"


def test_ffmpeg_nonexistent_file():
    """FFmpeg on nonexistent file should return degraded."""
    bins, degraded, reason = build_waveform_ffmpeg("/nonexistent/file.mp4", bins=8)
    assert degraded is True
    assert len(bins) == 8


# ─── MARKER_B29: Stereo waveform tests ───


def test_stereo_rms_silence():
    """Silent stereo PCM should produce all-zero L/R bins."""
    # Stereo: 4 bytes per frame (2 bytes L + 2 bytes R)
    pcm = b"\x00\x00\x00\x00" * 1600
    left, right = pcm_stereo_to_rms_bins(pcm, bins=8)
    assert len(left) == 8
    assert len(right) == 8
    assert all(b == 0.0 for b in left)
    assert all(b == 0.0 for b in right)


def test_stereo_rms_left_only():
    """Left channel loud, right silent → left bins high, right bins zero."""
    frames = []
    for _ in range(1600):
        frames.append(struct.pack("<hh", 32000, 0))  # L=loud, R=silent
    pcm = b"".join(frames)
    left, right = pcm_stereo_to_rms_bins(pcm, bins=4)
    assert all(b > 0.9 for b in left)
    assert all(b == 0.0 for b in right)


def test_stereo_rms_right_only():
    """Right channel loud, left silent."""
    frames = []
    for _ in range(1600):
        frames.append(struct.pack("<hh", 0, 32000))
    pcm = b"".join(frames)
    left, right = pcm_stereo_to_rms_bins(pcm, bins=4)
    assert all(b == 0.0 for b in left)
    assert all(b > 0.9 for b in right)


def test_stereo_rms_both_channels():
    """Both channels loud."""
    frames = []
    for _ in range(1600):
        frames.append(struct.pack("<hh", 16384, 32000))
    pcm = b"".join(frames)
    left, right = pcm_stereo_to_rms_bins(pcm, bins=4)
    assert all(0.45 < b < 0.55 for b in left)   # ~0.5
    assert all(b > 0.9 for b in right)            # ~1.0


def test_stereo_rms_empty():
    """Empty stereo PCM → zero bins."""
    left, right = pcm_stereo_to_rms_bins(b"", bins=4)
    assert len(left) == 4
    assert len(right) == 4
    assert all(b == 0.0 for b in left)


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_stereo_extract_from_wav(tmp_path: Path):
    """Extract stereo PCM from a stereo WAV."""
    wav_path = tmp_path / "stereo.wav"
    _write_stereo_sine_wav(wav_path, freq_l=440, freq_r=880, duration_sec=0.5, sample_rate=16000)
    pcm = extract_pcm_stereo_16bit(str(wav_path), sample_rate=16000)
    assert pcm is not None
    # 0.5 sec × 16000 Hz × 4 bytes/frame = 32000 bytes
    assert len(pcm) == 32000


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_build_stereo_waveform(tmp_path: Path):
    """Full stereo waveform pipeline."""
    wav_path = tmp_path / "stereo.wav"
    _write_stereo_sine_wav(wav_path, freq_l=440, freq_r=880, duration_sec=1.0, sample_rate=16000)
    left, right, degraded, reason = build_stereo_waveform(str(wav_path), bins=16)
    assert len(left) == 16
    assert len(right) == 16
    assert degraded is False
    assert all(b > 0.0 for b in left)
    assert all(b > 0.0 for b in right)


def test_build_stereo_nonexistent():
    """Nonexistent file → degraded."""
    left, right, degraded, reason = build_stereo_waveform("/nonexistent/file.mp4", bins=8)
    assert degraded is True
    assert len(left) == 8
    assert len(right) == 8


# ─── MARKER_B5.1: Audio segment extraction tests ───


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_wav_segment_from_stereo(tmp_path: Path):
    """Extract WAV segment from stereo file."""
    wav_path = tmp_path / "stereo.wav"
    _write_stereo_sine_wav(wav_path, freq_l=440, freq_r=880, duration_sec=2.0, sample_rate=44100)
    result = extract_audio_wav_segment(str(wav_path), start_sec=0, duration_sec=1.0, sample_rate=44100)
    assert result is not None
    assert len(result) > 44  # WAV header
    assert result[:4] == b"RIFF"  # WAV magic
    assert result[8:12] == b"WAVE"


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_wav_segment_with_offset(tmp_path: Path):
    """Extract segment starting at offset."""
    wav_path = tmp_path / "tone.wav"
    _write_sine_wav(wav_path, freq=440, duration_sec=3.0, sample_rate=16000)
    full = extract_audio_wav_segment(str(wav_path), start_sec=0, duration_sec=3.0, sample_rate=16000, channels=1)
    part = extract_audio_wav_segment(str(wav_path), start_sec=1.0, duration_sec=1.0, sample_rate=16000, channels=1)
    assert full is not None and part is not None
    assert len(part) < len(full)


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_wav_segment_clamps_duration(tmp_path: Path):
    """Duration clamped to 30s max."""
    wav_path = tmp_path / "tone.wav"
    _write_sine_wav(wav_path, freq=440, duration_sec=1.0, sample_rate=16000)
    result = extract_audio_wav_segment(str(wav_path), duration_sec=999.0, sample_rate=16000, channels=1)
    assert result is not None  # Should succeed (file is only 1s, 30s clamp is fine)


def test_wav_segment_nonexistent():
    """Nonexistent file → None."""
    result = extract_audio_wav_segment("/nonexistent/file.mp4")
    assert result is None


def test_wav_segment_no_ffmpeg(tmp_path: Path):
    """No FFmpeg → None."""
    wav_path = tmp_path / "test.wav"
    wav_path.write_bytes(b"RIFF" + b"\x00" * 40)
    with patch("src.services.cut_ffmpeg_waveform.HAS_FFMPEG", False):
        result = extract_audio_wav_segment(str(wav_path))
    assert result is None


# ─── MARKER_B40: compute_audio_levels tests ───


def test_audio_levels_nonexistent_file():
    """Nonexistent file → success=False, zero levels."""
    result = compute_audio_levels("/nonexistent/file.mp4", time_sec=0.0)
    assert result["success"] is False
    assert result["rms_left"] == 0.0
    assert result["rms_right"] == 0.0
    assert result["peak_left"] == 0.0
    assert result["peak_right"] == 0.0


def test_audio_levels_no_ffmpeg():
    """No FFmpeg → success=False."""
    with patch("src.services.cut_ffmpeg_waveform.HAS_FFMPEG", False):
        result = compute_audio_levels("/some/file.mp4", time_sec=1.0)
    assert result["success"] is False


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_audio_levels_from_stereo_wav(tmp_path: Path):
    """Extract audio levels from a stereo WAV at t=0.25s."""
    wav_path = tmp_path / "stereo.wav"
    _write_stereo_sine_wav(wav_path, freq_l=440, freq_r=880, duration_sec=1.0, sample_rate=16000)

    result = compute_audio_levels(str(wav_path), time_sec=0.25)
    assert result["success"] is True
    assert result["rms_left"] > 0.5   # sine wave ~0.707 RMS
    assert result["rms_right"] > 0.5
    assert result["peak_left"] > 0.9
    assert result["peak_right"] > 0.9
    assert result["time_sec"] == 0.25


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_audio_levels_with_waveform_bins(tmp_path: Path):
    """Request waveform bins → result includes waveform_left/right."""
    wav_path = tmp_path / "stereo.wav"
    _write_stereo_sine_wav(wav_path, freq_l=440, freq_r=880, duration_sec=1.0, sample_rate=16000)

    result = compute_audio_levels(str(wav_path), time_sec=0.5, waveform_bins=8)
    assert result["success"] is True
    assert "waveform_left" in result
    assert "waveform_right" in result
    assert len(result["waveform_left"]) == 8
    assert len(result["waveform_right"]) == 8
    assert all(b > 0.0 for b in result["waveform_left"])


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_audio_levels_no_waveform_by_default(tmp_path: Path):
    """Default mode: no waveform bins in result."""
    wav_path = tmp_path / "tone.wav"
    _write_sine_wav(wav_path, freq=440, duration_sec=0.5, sample_rate=16000)

    result = compute_audio_levels(str(wav_path), time_sec=0.1)
    assert result["success"] is True
    assert "waveform_left" not in result
    assert "waveform_right" not in result


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_audio_levels_silent_file(tmp_path: Path):
    """Silent audio → near-zero RMS."""
    wav_path = tmp_path / "silent.wav"
    # Write a WAV with all-zero samples
    num_samples = 16000  # 1 second
    pcm_data = b"\x00\x00\x00\x00" * num_samples  # stereo silence
    data_size = len(pcm_data)
    file_size = 36 + data_size
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", file_size, b"WAVE",
        b"fmt ", 16, 1, 2, 16000, 64000, 4, 16,
        b"data", data_size,
    )
    wav_path.write_bytes(header + pcm_data)

    result = compute_audio_levels(str(wav_path), time_sec=0.5)
    assert result["success"] is True
    assert result["rms_left"] == 0.0
    assert result["rms_right"] == 0.0
    assert result["peak_left"] == 0.0
    assert result["peak_right"] == 0.0


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_audio_levels_left_only(tmp_path: Path):
    """Left channel loud, right silent → asymmetric levels."""
    wav_path = tmp_path / "left_only.wav"
    num_samples = 16000
    frames = []
    for i in range(num_samples):
        t = i / 16000
        left = int(32000 * math.sin(2 * math.pi * 440 * t))
        frames.append(max(-32768, min(32767, left)))
        frames.append(0)  # right silent
    pcm_data = struct.pack(f"<{num_samples * 2}h", *frames)
    data_size = len(pcm_data)
    file_size = 36 + data_size
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", file_size, b"WAVE",
        b"fmt ", 16, 1, 2, 16000, 64000, 4, 16,
        b"data", data_size,
    )
    wav_path.write_bytes(header + pcm_data)

    result = compute_audio_levels(str(wav_path), time_sec=0.5)
    assert result["success"] is True
    assert result["rms_left"] > 0.5
    assert result["rms_right"] < 0.01


# ─── Helpers ───


def _write_stereo_sine_wav(
    path: Path, freq_l: float, freq_r: float, duration_sec: float, sample_rate: int
) -> None:
    """Write a stereo WAV file with different sine tones per channel."""
    num_samples = int(sample_rate * duration_sec)
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        left = int(32000 * math.sin(2 * math.pi * freq_l * t))
        right = int(32000 * math.sin(2 * math.pi * freq_r * t))
        samples.append(max(-32768, min(32767, left)))
        samples.append(max(-32768, min(32767, right)))

    pcm_data = struct.pack(f"<{num_samples * 2}h", *samples)

    data_size = len(pcm_data)
    file_size = 36 + data_size
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", file_size, b"WAVE",
        b"fmt ", 16,
        1,                   # PCM
        2,                   # stereo
        sample_rate,
        sample_rate * 4,     # byte rate (2 ch × 2 bytes)
        4,                   # block align (2 ch × 2 bytes)
        16,                  # bits per sample
        b"data", data_size,
    )
    path.write_bytes(header + pcm_data)


def _write_sine_wav(path: Path, freq: float, duration_sec: float, sample_rate: int) -> None:
    """Write a minimal WAV file with a sine tone."""
    num_samples = int(sample_rate * duration_sec)
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        value = int(32000 * math.sin(2 * math.pi * freq * t))
        samples.append(max(-32768, min(32767, value)))

    pcm_data = struct.pack(f"<{num_samples}h", *samples)

    # WAV header (44 bytes)
    data_size = len(pcm_data)
    file_size = 36 + data_size
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", file_size, b"WAVE",
        b"fmt ", 16,       # subchunk1 size
        1,                 # PCM format
        1,                 # mono
        sample_rate,
        sample_rate * 2,   # byte rate
        2,                 # block align
        16,                # bits per sample
        b"data", data_size,
    )
    path.write_bytes(header + pcm_data)
