import math

from src.services.cut_audio_intel_eval import (
    build_energy_envelope,
    detect_offset_hybrid,
    detect_offset_via_correlation,
    detect_peak_offset,
    derive_pause_windows_from_silence,
    transcript_pause_merge,
)


def _tone(duration_sec: float, sample_rate: int, *, amplitude: float = 0.8, freq_hz: float = 220.0) -> list[float]:
    samples = int(duration_sec * sample_rate)
    return [amplitude * math.sin(2.0 * math.pi * freq_hz * idx / sample_rate) for idx in range(samples)]


def _silence(duration_sec: float, sample_rate: int) -> list[float]:
    return [0.0] * int(duration_sec * sample_rate)


def _shift(signal: list[float], offset_samples: int) -> list[float]:
    if offset_samples >= 0:
        return ([0.0] * offset_samples) + signal
    trim = abs(offset_samples)
    return signal[trim:]


def _add_noise(signal: list[float], *, amplitude: float = 0.08) -> list[float]:
    noisy: list[float] = []
    for idx, value in enumerate(signal):
        noise = amplitude * math.sin(idx * 0.37) * math.cos(idx * 0.11)
        noisy.append(value + noise)
    return noisy


def test_energy_pause_windows_detect_clean_speech_segments():
    sample_rate = 1000
    signal = _tone(1.0, sample_rate) + _silence(0.4, sample_rate) + _tone(1.2, sample_rate)

    envelope = build_energy_envelope(signal, sample_rate, frame_ms=20)
    windows = derive_pause_windows_from_silence(
        signal,
        sample_rate,
        frame_ms=20,
        silence_threshold=0.08,
        min_silence_ms=250,
        keep_silence_ms=80,
    )

    assert envelope
    assert len(windows) == 2
    assert windows[0].start_sec == 0.0
    assert 0.9 <= windows[0].end_sec <= 1.1
    assert 1.2 <= windows[1].start_sec <= 1.5
    assert 2.4 <= windows[1].end_sec <= 2.7


def test_transcript_pause_merge_produces_editorial_windows():
    segments = [
        {"start": 0.0, "end": 0.42, "text": "hello"},
        {"start": 0.5, "end": 0.92, "text": "world"},
        {"start": 1.7, "end": 2.05, "text": "next"},
    ]

    windows = transcript_pause_merge(segments, max_gap_sec=0.35, max_window_sec=2.0)

    assert len(windows) == 2
    assert windows[0].method == "transcript_pause_v1"
    assert windows[0].start_sec == 0.0
    assert windows[0].end_sec == 0.92
    assert windows[1].start_sec == 1.7
    assert windows[1].end_sec == 2.05


def test_correlation_detects_known_audio_offset_more_accurately_than_peak_only():
    sample_rate = 1000
    base = _tone(0.8, sample_rate, amplitude=0.5, freq_hz=180.0) + _silence(0.2, sample_rate) + _tone(0.9, sample_rate, amplitude=0.9, freq_hz=260.0)
    shifted = _shift(base, 45)

    peak = detect_peak_offset(base, shifted, sample_rate)
    corr = detect_offset_via_correlation(base, shifted, sample_rate, max_lag_sec=0.2)

    assert abs(corr.detected_offset_sec - 0.045) <= 0.005
    assert abs(corr.detected_offset_sec - 0.045) <= abs(peak.detected_offset_sec - 0.045)


def test_hybrid_sync_is_no_worse_than_peak_or_correlation_on_noisy_signal():
    sample_rate = 1000
    base = _tone(0.7, sample_rate, amplitude=0.6, freq_hz=150.0) + _silence(0.15, sample_rate) + _tone(0.8, sample_rate, amplitude=1.0, freq_hz=320.0)
    shifted = _shift(_add_noise(base, amplitude=0.12), 32)
    noisy_base = _add_noise(base, amplitude=0.06)

    peak = detect_peak_offset(noisy_base, shifted, sample_rate)
    corr = detect_offset_via_correlation(noisy_base, shifted, sample_rate, max_lag_sec=0.2)
    hybrid = detect_offset_hybrid(noisy_base, shifted, sample_rate)

    target = 0.032
    hybrid_error = abs(hybrid.detected_offset_sec - target)
    peak_error = abs(peak.detected_offset_sec - target)
    corr_error = abs(corr.detected_offset_sec - target)

    assert hybrid.method in {"peaks+correlation_v1", "correlation_v1", "peak_only_v1"}
    assert hybrid_error <= max(peak_error, corr_error)
    assert hybrid.confidence >= min(peak.confidence, corr.confidence)
