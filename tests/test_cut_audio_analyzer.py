"""
MARKER_AUDIO_ANALYSIS — Tests for cut_audio_analyzer.py

Tests: AudioAnalysisResult dataclass, analyze_audio with nonexistent path,
analyze_audio with a synthesized silent WAV, energy contour shape,
and to_dict() serialisation.

@task: tb_1774786583_19025_1
"""
import os
import sys
import struct
import tempfile
import wave

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.services.cut_audio_analyzer import (
    AudioAnalysisResult,
    analyze_audio,
    _compute_energy_contour,
    _estimate_bpm_autocorrelation,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def silent_wav(tmp_path):
    """1-second silent 22050 Hz mono WAV."""
    path = tmp_path / "silent.wav"
    sr = 22050
    n = sr  # 1 second
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f"<{n}h", *([0] * n)))
    return str(path)


@pytest.fixture
def tone_wav(tmp_path):
    """1-second 440 Hz sine wave at 22050 Hz mono WAV."""
    path = tmp_path / "tone.wav"
    sr = 22050
    t = np.linspace(0, 1, sr, endpoint=False)
    samples = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(samples.tobytes())
    return str(path)


# ---------------------------------------------------------------------------
# AudioAnalysisResult dataclass
# ---------------------------------------------------------------------------

class TestAudioAnalysisResult:
    def test_default_fields(self):
        r = AudioAnalysisResult(source_path="/some/file.wav")
        assert r.bpm == 0.0
        assert r.key == ""
        assert r.camelot_key == ""
        assert r.energy_contour == []
        assert r.onset_times == []
        assert r.duration_sec == 0.0

    def test_to_dict_keys(self):
        r = AudioAnalysisResult(source_path="/some/file.wav", bpm=120.0, key="C major", camelot_key="8B")
        d = r.to_dict()
        assert "bpm" in d
        assert "key" in d
        assert "camelot_key" in d
        assert "energy_contour" in d
        assert "onset_times" in d
        assert "duration_sec" in d

    def test_to_dict_values_rounded(self):
        r = AudioAnalysisResult(
            source_path="/f",
            energy_contour=[0.123456789],
            onset_times=[1.23456789],
        )
        d = r.to_dict()
        assert d["energy_contour"][0] == round(0.123456789, 4)
        assert d["onset_times"][0] == round(1.23456789, 3)


# ---------------------------------------------------------------------------
# analyze_audio edge cases
# ---------------------------------------------------------------------------

class TestAnalyzeAudio:
    def test_nonexistent_returns_empty(self):
        """analyze_audio on missing file returns zero/empty result, no exception."""
        result = analyze_audio("/no/such/file.wav")
        assert result.bpm == 0.0
        assert result.key == ""
        assert result.energy_contour == []
        assert result.onset_times == []

    def test_silent_wav_runs(self, silent_wav):
        """analyze_audio should not raise on a valid silent file."""
        result = analyze_audio(silent_wav)
        # BPM may be 0 on silence, but should not crash
        assert isinstance(result.bpm, float)
        assert result.duration_sec > 0.5  # ~1 second

    def test_silent_wav_energy_shape(self, silent_wav):
        """Energy contour should have exactly energy_bins entries."""
        result = analyze_audio(silent_wav, energy_bins=32)
        assert len(result.energy_contour) == 32

    def test_energy_bins_default(self, silent_wav):
        result = analyze_audio(silent_wav)
        assert len(result.energy_contour) == 64

    def test_tone_wav_has_energy(self, tone_wav):
        """Non-silent tone should produce non-zero energy."""
        result = analyze_audio(tone_wav)
        assert any(e > 0 for e in result.energy_contour), "Tone should have non-zero energy"

    def test_result_source_path(self, silent_wav):
        result = analyze_audio(silent_wav)
        assert result.source_path == silent_wav


# ---------------------------------------------------------------------------
# _compute_energy_contour unit tests
# ---------------------------------------------------------------------------

class TestEnergyContour:
    def test_shape(self):
        sr = 22050
        samples = np.zeros(sr, dtype=np.float32)
        contour = _compute_energy_contour(samples, sr, n_bins=16)
        assert len(contour) == 16

    def test_all_zero_on_silence(self):
        sr = 22050
        samples = np.zeros(sr, dtype=np.float32)
        contour = _compute_energy_contour(samples, sr, n_bins=8)
        assert all(v == 0.0 for v in contour)

    def test_non_zero_on_tone(self):
        sr = 22050
        t = np.linspace(0, 1, sr, endpoint=False)
        samples = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        contour = _compute_energy_contour(samples, sr, n_bins=8)
        assert any(v > 0 for v in contour)

    def test_values_between_zero_and_one(self):
        sr = 22050
        t = np.linspace(0, 1, sr, endpoint=False)
        samples = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        contour = _compute_energy_contour(samples, sr, n_bins=16)
        assert all(0.0 <= v <= 1.0 for v in contour)


# ---------------------------------------------------------------------------
# _estimate_bpm_autocorrelation unit tests
# ---------------------------------------------------------------------------

class TestBpmAutocorrelation:
    def test_returns_tuple(self):
        sr = 22050
        samples = np.zeros(sr * 2, dtype=np.float32)
        bpm, onsets = _estimate_bpm_autocorrelation(samples, sr)
        assert isinstance(bpm, float)
        assert isinstance(onsets, list)

    def test_silence_gives_zero_bpm(self):
        sr = 22050
        samples = np.zeros(sr * 2, dtype=np.float32)
        bpm, _ = _estimate_bpm_autocorrelation(samples, sr)
        assert bpm == 0.0

    def test_too_short_gives_zero(self):
        sr = 22050
        samples = np.zeros(100, dtype=np.float32)
        bpm, onsets = _estimate_bpm_autocorrelation(samples, sr)
        assert bpm == 0.0
        assert onsets == []
