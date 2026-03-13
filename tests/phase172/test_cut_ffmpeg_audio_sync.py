"""
MARKER_172.14.FFMPEG_AUDIO_SYNC_TESTS
Tests for FFmpeg-based audio sync: signal extraction, cross-correlation,
two-pass sync, fallback behavior.
"""
import math
import struct
from pathlib import Path
from unittest.mock import patch

import pytest

from src.services.cut_ffmpeg_audio_sync import (
    _byte_scan_signal,
    _cross_correlate_at_lag,
    _downsample,
    _find_best_lag,
    extract_signal_ffmpeg,
    extract_signal_with_fallback,
    sync_two_files_ffmpeg,
)
from src.services.cut_ffmpeg_waveform import HAS_FFMPEG


# ─── Helpers ───


def _write_sine_wav(path: Path, freq: float, duration_sec: float, sample_rate: int) -> None:
    """Write a minimal WAV file with a sine tone."""
    num_samples = int(sample_rate * duration_sec)
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        value = int(32000 * math.sin(2 * math.pi * freq * t))
        samples.append(max(-32768, min(32767, value)))
    pcm_data = struct.pack(f"<{num_samples}h", *samples)
    data_size = len(pcm_data)
    file_size = 36 + data_size
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", file_size, b"WAVE",
        b"fmt ", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16,
        b"data", data_size,
    )
    path.write_bytes(header + pcm_data)


def _write_delayed_sine_wav(
    path: Path, freq: float, duration_sec: float, delay_sec: float, sample_rate: int,
) -> None:
    """Write a WAV with silence prefix followed by a sine tone."""
    silence_samples = int(sample_rate * delay_sec)
    tone_samples = int(sample_rate * (duration_sec - delay_sec))
    samples = [0] * silence_samples
    for i in range(tone_samples):
        t = i / sample_rate
        value = int(32000 * math.sin(2 * math.pi * freq * t))
        samples.append(max(-32768, min(32767, value)))
    num_samples = len(samples)
    pcm_data = struct.pack(f"<{num_samples}h", *samples)
    data_size = len(pcm_data)
    file_size = 36 + data_size
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", file_size, b"WAVE",
        b"fmt ", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16,
        b"data", data_size,
    )
    path.write_bytes(header + pcm_data)


# ─── Cross-correlation math ───


def test_cross_correlate_identical_signals():
    """Identical signals at lag 0 should have max correlation."""
    sig = [math.sin(i * 0.1) for i in range(200)]
    score_0 = _cross_correlate_at_lag(sig, sig, 0)
    score_50 = _cross_correlate_at_lag(sig, sig, 50)
    assert score_0 > score_50


def test_find_best_lag_identical():
    """Best lag for identical signals should be 0."""
    sig = [math.sin(i * 0.1) for i in range(200)]
    lag, score = _find_best_lag(sig, sig, max_lag=50)
    assert lag == 0
    assert score > 0.4


def test_find_best_lag_shifted():
    """Shifted signal should detect the shift."""
    sig = [math.sin(i * 0.1) for i in range(300)]
    shifted = [0.0] * 20 + sig[:280]  # 20-sample delay
    lag, score = _find_best_lag(sig, shifted, max_lag=50)
    assert abs(lag - 20) <= 2  # Should find ~20 samples offset


def test_downsample():
    """Downsampling should reduce signal length."""
    sig = list(range(100))
    ds = _downsample(sig, 10)
    assert len(ds) == 10
    # First chunk average: (0+1+...+9)/10 = 4.5
    assert abs(ds[0] - 4.5) < 0.01


def test_downsample_factor_1():
    sig = [1.0, 2.0, 3.0]
    assert _downsample(sig, 1) == sig


# ─── Byte-scan fallback ───


def test_byte_scan_signal_produces_data(tmp_path: Path):
    media = tmp_path / "test.mp4"
    media.write_bytes(bytes(range(256)) * 4)
    signal, rate, degraded, reason = _byte_scan_signal(str(media), 8192)
    assert len(signal) > 0
    assert rate == 1000
    assert degraded is True
    assert reason == "byte_scan_fallback"


def test_byte_scan_missing_file():
    signal, rate, degraded, reason = _byte_scan_signal("/nonexistent", 8192)
    assert signal == []
    assert degraded is True
    assert "read_failed" in reason


# ─── FFmpeg signal extraction ───


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_extract_signal_from_wav(tmp_path: Path):
    wav = tmp_path / "tone.wav"
    _write_sine_wav(wav, freq=440, duration_sec=0.5, sample_rate=16000)

    signal, degraded, reason = extract_signal_ffmpeg(str(wav), sample_rate=16000)
    assert not degraded
    assert reason == ""
    assert len(signal) == 8000  # 0.5s * 16000
    # Sine wave should have values in [-1, 1]
    assert all(-1.01 < s < 1.01 for s in signal)


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_extract_signal_with_fallback_uses_ffmpeg(tmp_path: Path):
    wav = tmp_path / "tone.wav"
    _write_sine_wav(wav, freq=440, duration_sec=0.5, sample_rate=16000)

    signal, rate, degraded, reason = extract_signal_with_fallback(str(wav))
    assert not degraded
    assert rate == 16000
    assert len(signal) > 0


def test_extract_signal_fallback_when_no_ffmpeg(tmp_path: Path):
    media = tmp_path / "test.dat"
    media.write_bytes(bytes(range(256)) * 4)

    with patch("src.services.cut_ffmpeg_audio_sync.HAS_FFMPEG", False):
        signal, rate, degraded, reason = extract_signal_with_fallback(str(media))
    assert degraded is True
    assert rate == 1000
    assert reason == "byte_scan_fallback"


def test_extract_signal_nonexistent_file():
    signal, degraded, reason = extract_signal_ffmpeg("/nonexistent/file.wav")
    assert degraded is True
    assert signal == []


# ─── Two-pass sync ───


def _write_chirp_wav(path: Path, duration_sec: float, sample_rate: int) -> None:
    """Write a chirp (frequency sweep 200→4000 Hz) — unique autocorrelation peak."""
    num_samples = int(sample_rate * duration_sec)
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        freq = 200 + (4000 - 200) * (t / duration_sec)
        value = int(28000 * math.sin(2 * math.pi * freq * t))
        samples.append(max(-32768, min(32767, value)))
    pcm_data = struct.pack(f"<{num_samples}h", *samples)
    data_size = len(pcm_data)
    file_size = 36 + data_size
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", file_size, b"WAVE",
        b"fmt ", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16,
        b"data", data_size,
    )
    path.write_bytes(header + pcm_data)


def _write_delayed_chirp_wav(
    path: Path, duration_sec: float, delay_sec: float, sample_rate: int,
) -> None:
    """Write a WAV with silence prefix followed by a chirp."""
    silence_samples = int(sample_rate * delay_sec)
    chirp_dur = duration_sec - delay_sec
    tone_samples = int(sample_rate * chirp_dur)
    samples = [0] * silence_samples
    for i in range(tone_samples):
        t = i / sample_rate
        freq = 200 + (4000 - 200) * (t / max(0.01, chirp_dur))
        value = int(28000 * math.sin(2 * math.pi * freq * t))
        samples.append(max(-32768, min(32767, value)))
    num_samples = len(samples)
    pcm_data = struct.pack(f"<{num_samples}h", *samples)
    data_size = len(pcm_data)
    file_size = 36 + data_size
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", file_size, b"WAVE",
        b"fmt ", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16,
        b"data", data_size,
    )
    path.write_bytes(header + pcm_data)


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_sync_identical_files(tmp_path: Path):
    """Identical chirp files should sync with ~0 offset."""
    wav = tmp_path / "chirp.wav"
    _write_chirp_wav(wav, duration_sec=2.0, sample_rate=16000)

    result = sync_two_files_ffmpeg(
        str(wav), str(wav),
        coarse_rate=2000, fine_rate=8000, max_lag_sec=1.0, max_duration_sec=3.0,
    )
    assert abs(result.detected_offset_sec) < 0.05
    assert result.confidence > 0.5
    assert result.method == "ffmpeg_sync_v1"


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_sync_detects_delay(tmp_path: Path):
    """Should detect a 0.5 sec delay between reference and candidate."""
    ref = tmp_path / "ref.wav"
    cand = tmp_path / "cand.wav"
    _write_chirp_wav(ref, duration_sec=2.0, sample_rate=16000)
    _write_delayed_chirp_wav(cand, duration_sec=2.0, delay_sec=0.5, sample_rate=16000)

    result = sync_two_files_ffmpeg(
        str(ref), str(cand),
        coarse_rate=2000, fine_rate=8000, max_lag_sec=2.0, max_duration_sec=3.0,
    )
    # Chirp has unique autocorrelation — should find offset near 0.5 sec
    assert abs(result.detected_offset_sec - 0.5) < 0.15
    assert result.confidence > 0.3


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_sync_nonexistent_reference(tmp_path: Path):
    wav = tmp_path / "tone.wav"
    _write_sine_wav(wav, freq=440, duration_sec=0.5, sample_rate=16000)

    result = sync_two_files_ffmpeg("/nonexistent.wav", str(wav))
    assert result.confidence == 0.0
    assert result.detected_offset_sec == 0.0
