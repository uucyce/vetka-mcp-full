"""
MARKER_B67 — Audio analysis service for PULSE pipeline.

Extracts: BPM, musical key, Camelot key, energy contour, onset times.
Uses FFmpeg for PCM extraction + numpy/scipy for signal analysis.
Optional librosa integration when available (better BPM/key detection).

@status: active
@phase: B67 (ROADMAP_B7 Phase 1)
@task: tb_1774311908_1
"""
from __future__ import annotations

import logging
import os
import struct
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger("cut.audio_analyzer")

# Try optional librosa import
try:
    import librosa  # type: ignore
    _HAS_LIBROSA = True
except ImportError:
    _HAS_LIBROSA = False

# Chromatic note names for key detection
_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Musical key → Camelot mapping (subset, full mapping in pulse_camelot_engine)
_KEY_TO_CAMELOT = {
    "C major": "8B", "G major": "9B", "D major": "10B", "A major": "11B",
    "E major": "12B", "B major": "1B", "F# major": "2B", "Db major": "3B",
    "Ab major": "4B", "Eb major": "5B", "Bb major": "6B", "F major": "7B",
    "A minor": "8A", "E minor": "9A", "B minor": "10A", "F# minor": "11A",
    "Db minor": "12A", "Ab minor": "1A", "Eb minor": "2A", "Bb minor": "3A",
    "F minor": "4A", "C minor": "5A", "G minor": "6A", "D minor": "7A",
    # Enharmonic
    "C# major": "3B", "G# major": "4B", "D# major": "5B", "A# major": "6B",
    "G# minor": "1A", "D# minor": "2A", "A# minor": "3A", "C# minor": "12A",
}


@dataclass
class AudioAnalysisResult:
    """Result of audio analysis for a single file."""
    source_path: str
    bpm: float = 0.0
    key: str = ""  # e.g. "C major", "A minor"
    camelot_key: str = ""  # e.g. "8B", "8A"
    energy_contour: list[float] = field(default_factory=list)
    onset_times: list[float] = field(default_factory=list)
    duration_sec: float = 0.0
    sample_rate: int = 0
    method: str = "ffmpeg+scipy"  # or "librosa"
    confidence: float = 0.0
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "bpm": round(self.bpm, 1),
            "key": self.key,
            "camelot_key": self.camelot_key,
            "energy_contour": [round(e, 4) for e in self.energy_contour],
            "onset_times": [round(t, 3) for t in self.onset_times],
            "duration_sec": round(self.duration_sec, 3),
            "sample_rate": self.sample_rate,
            "method": self.method,
            "confidence": round(self.confidence, 3),
            "error": self.error,
        }


def _extract_pcm_mono(source_path: str, sr: int = 22050, max_duration: float = 300.0) -> tuple[NDArray[np.float32], int]:
    """Extract mono PCM float32 audio via FFmpeg. Returns (samples, sample_rate)."""
    cmd = [
        "ffmpeg", "-y", "-i", source_path,
        "-vn",  # no video
        "-ac", "1",  # mono
        "-ar", str(sr),
        "-f", "f32le",  # raw float32 little-endian
        "-t", str(max_duration),
        "pipe:1",
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, timeout=60,
        )
        if proc.returncode != 0:
            return np.array([], dtype=np.float32), sr
        raw = proc.stdout
        if len(raw) < 4:
            return np.array([], dtype=np.float32), sr
        samples = np.frombuffer(raw, dtype=np.float32)
        return samples, sr
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        logger.warning("FFmpeg PCM extraction failed for %s: %s", source_path, e)
        return np.array([], dtype=np.float32), sr


def _estimate_bpm_autocorrelation(samples: NDArray[np.float32], sr: int) -> tuple[float, list[float]]:
    """Estimate BPM using onset detection + autocorrelation. Returns (bpm, onset_times)."""
    if len(samples) < sr:
        return 0.0, []

    # Compute onset strength envelope
    hop = 512
    frame_count = len(samples) // hop
    if frame_count < 4:
        return 0.0, []

    # Spectral flux onset detection
    onset_env = np.zeros(frame_count, dtype=np.float32)
    prev_spec = None
    for i in range(frame_count):
        frame = samples[i * hop:(i + 1) * hop]
        if len(frame) < hop:
            break
        spec = np.abs(np.fft.rfft(frame * np.hanning(hop)))
        if prev_spec is not None:
            diff = spec - prev_spec
            onset_env[i] = float(np.sum(np.maximum(diff, 0)))
        prev_spec = spec

    # Normalize
    mx = onset_env.max()
    if mx > 0:
        onset_env /= mx

    # Find onset peaks
    from scipy.signal import find_peaks
    peak_indices, _ = find_peaks(onset_env, height=0.3, distance=sr // (hop * 4))
    onset_times = [float(idx * hop / sr) for idx in peak_indices]

    # Autocorrelation for BPM
    if len(onset_env) < 100:
        return 0.0, onset_times

    corr = np.correlate(onset_env, onset_env, mode="full")
    corr = corr[len(corr) // 2:]  # keep positive lags only

    # BPM range: 60-200 BPM → lag range
    min_lag = int(sr * 60 / (hop * 200))  # 200 BPM
    max_lag = int(sr * 60 / (hop * 60))   # 60 BPM

    if max_lag >= len(corr):
        max_lag = len(corr) - 1
    if min_lag >= max_lag:
        return 0.0, onset_times

    search = corr[min_lag:max_lag + 1]
    if len(search) == 0:
        return 0.0, onset_times

    best_lag = int(np.argmax(search)) + min_lag
    if best_lag <= 0:
        return 0.0, onset_times

    bpm = 60.0 * sr / (hop * best_lag)
    return round(bpm, 1), onset_times


def _estimate_key_chroma(samples: NDArray[np.float32], sr: int) -> tuple[str, float]:
    """Estimate musical key using chroma analysis. Returns (key_name, confidence)."""
    if len(samples) < sr * 2:
        return "", 0.0

    hop = 2048
    n_fft = 4096
    frame_count = (len(samples) - n_fft) // hop
    if frame_count < 1:
        return "", 0.0

    # Compute chroma features (12 pitch classes)
    chroma = np.zeros((12, frame_count), dtype=np.float32)
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)

    for i in range(frame_count):
        frame = samples[i * hop:i * hop + n_fft]
        if len(frame) < n_fft:
            break
        windowed = frame * np.hanning(n_fft)
        spec = np.abs(np.fft.rfft(windowed))

        # Map frequencies to pitch classes
        for bin_idx in range(1, len(freqs)):
            freq = freqs[bin_idx]
            if freq < 65 or freq > 5000:  # A2 to ~D8
                continue
            # Frequency to MIDI note
            midi = 12 * np.log2(freq / 440.0) + 69
            pitch_class = int(round(midi)) % 12
            chroma[pitch_class, i] += spec[bin_idx] ** 2

    # Average chroma profile
    avg_chroma = chroma.mean(axis=1)
    if avg_chroma.max() == 0:
        return "", 0.0
    avg_chroma /= avg_chroma.max()

    # Krumhansl-Kessler key profiles
    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

    best_key = ""
    best_corr = -1.0

    for shift in range(12):
        # Rotate chroma to test each root note
        rotated = np.roll(avg_chroma, -shift)

        # Test major
        corr_maj = float(np.corrcoef(rotated, major_profile)[0, 1])
        if corr_maj > best_corr:
            best_corr = corr_maj
            best_key = f"{_NOTE_NAMES[shift]} major"

        # Test minor
        corr_min = float(np.corrcoef(rotated, minor_profile)[0, 1])
        if corr_min > best_corr:
            best_corr = corr_min
            best_key = f"{_NOTE_NAMES[shift]} minor"

    confidence = max(0.0, min(1.0, (best_corr + 1.0) / 2.0))  # normalize to 0-1
    return best_key, confidence


def _compute_energy_contour(samples: NDArray[np.float32], sr: int, n_bins: int = 64) -> list[float]:
    """Compute RMS energy contour (n_bins values over the full duration)."""
    if len(samples) < 100:
        return []
    bin_size = len(samples) // n_bins
    if bin_size < 1:
        return []
    contour = []
    for i in range(n_bins):
        chunk = samples[i * bin_size:(i + 1) * bin_size]
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        contour.append(rms)
    # Normalize
    mx = max(contour) if contour else 1.0
    if mx > 0:
        contour = [v / mx for v in contour]
    return contour


def analyze_audio(
    source_path: str,
    *,
    sr: int = 22050,
    max_duration: float = 300.0,
    energy_bins: int = 64,
) -> AudioAnalysisResult:
    """
    Analyze audio file: extract BPM, key, Camelot key, energy contour, onsets.

    Uses librosa if available, falls back to FFmpeg + scipy.
    """
    result = AudioAnalysisResult(source_path=source_path)

    if not os.path.isfile(source_path):
        result.error = "File not found"
        return result

    if _HAS_LIBROSA:
        return _analyze_with_librosa(source_path, sr=sr, max_duration=max_duration, energy_bins=energy_bins)

    # FFmpeg + scipy fallback
    samples, actual_sr = _extract_pcm_mono(source_path, sr=sr, max_duration=max_duration)
    if len(samples) == 0:
        result.error = "Failed to extract audio"
        return result

    result.sample_rate = actual_sr
    result.duration_sec = len(samples) / actual_sr
    result.method = "ffmpeg+scipy"

    # BPM + onsets
    bpm, onsets = _estimate_bpm_autocorrelation(samples, actual_sr)
    result.bpm = bpm
    result.onset_times = onsets

    # Key detection
    key, confidence = _estimate_key_chroma(samples, actual_sr)
    result.key = key
    result.confidence = confidence
    result.camelot_key = _KEY_TO_CAMELOT.get(key, "")

    # Energy contour
    result.energy_contour = _compute_energy_contour(samples, actual_sr, n_bins=energy_bins)

    return result


def _analyze_with_librosa(
    source_path: str,
    *,
    sr: int = 22050,
    max_duration: float = 300.0,
    energy_bins: int = 64,
) -> AudioAnalysisResult:
    """Full analysis using librosa (higher quality)."""
    result = AudioAnalysisResult(source_path=source_path, method="librosa")

    try:
        y, actual_sr = librosa.load(source_path, sr=sr, mono=True, duration=max_duration)
    except Exception as e:
        result.error = f"librosa load failed: {e}"
        return result

    result.sample_rate = actual_sr
    result.duration_sec = len(y) / actual_sr

    # BPM
    try:
        tempo, _ = librosa.beat.beat_track(y=y, sr=actual_sr)
        result.bpm = float(tempo[0]) if hasattr(tempo, '__len__') else float(tempo)
    except Exception:
        result.bpm = 0.0

    # Onsets
    try:
        onset_frames = librosa.onset.onset_detect(y=y, sr=actual_sr)
        result.onset_times = [float(t) for t in librosa.frames_to_time(onset_frames, sr=actual_sr)]
    except Exception:
        result.onset_times = []

    # Key (chroma-based)
    try:
        chromagram = librosa.feature.chroma_cqt(y=y, sr=actual_sr)
        avg_chroma = chromagram.mean(axis=1)
        if avg_chroma.max() > 0:
            avg_chroma /= avg_chroma.max()
        key, confidence = _estimate_key_from_chroma_array(avg_chroma)
        result.key = key
        result.confidence = confidence
        result.camelot_key = _KEY_TO_CAMELOT.get(key, "")
    except Exception:
        pass

    # Energy contour
    result.energy_contour = _compute_energy_contour(y, actual_sr, n_bins=energy_bins)

    return result


def _estimate_key_from_chroma_array(avg_chroma: NDArray[np.float32]) -> tuple[str, float]:
    """Key estimation from pre-computed chroma array."""
    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

    best_key = ""
    best_corr = -1.0

    for shift in range(12):
        rotated = np.roll(avg_chroma, -shift)
        corr_maj = float(np.corrcoef(rotated, major_profile)[0, 1])
        if corr_maj > best_corr:
            best_corr = corr_maj
            best_key = f"{_NOTE_NAMES[shift]} major"
        corr_min = float(np.corrcoef(rotated, minor_profile)[0, 1])
        if corr_min > best_corr:
            best_corr = corr_min
            best_key = f"{_NOTE_NAMES[shift]} minor"

    confidence = max(0.0, min(1.0, (best_corr + 1.0) / 2.0))
    return best_key, confidence
