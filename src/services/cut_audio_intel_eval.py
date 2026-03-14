from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class SliceWindow:
    start_sec: float
    end_sec: float
    confidence: float
    method: str


@dataclass(frozen=True)
class SyncResult:
    detected_offset_sec: float
    confidence: float
    method: str
    peak_value: float


def _moving_average(values: list[float], radius: int) -> list[float]:
    if radius <= 0:
        return list(values)
    result: list[float] = []
    for idx in range(len(values)):
        start = max(0, idx - radius)
        end = min(len(values), idx + radius + 1)
        chunk = values[start:end]
        result.append(sum(chunk) / max(1, len(chunk)))
    return result


def build_energy_envelope(samples: list[float], sample_rate: int, frame_ms: int = 20) -> list[float]:
    frame_size = max(1, int(sample_rate * frame_ms / 1000.0))
    envelope: list[float] = []
    for start in range(0, len(samples), frame_size):
        frame = samples[start : start + frame_size]
        if not frame:
            continue
        energy = math.sqrt(sum(sample * sample for sample in frame) / len(frame))
        envelope.append(energy)
    return _moving_average(envelope, radius=1)


def detect_silence_windows(
    samples: list[float],
    sample_rate: int,
    *,
    frame_ms: int = 20,
    silence_threshold: float = 0.08,
    min_silence_ms: int = 250,
) -> list[tuple[float, float]]:
    envelope = build_energy_envelope(samples, sample_rate, frame_ms=frame_ms)
    silence_frames_needed = max(1, int(min_silence_ms / frame_ms))
    windows: list[tuple[float, float]] = []
    start_idx: int | None = None
    for idx, value in enumerate(envelope):
        if value <= silence_threshold:
            if start_idx is None:
                start_idx = idx
            continue
        if start_idx is not None and idx - start_idx >= silence_frames_needed:
            windows.append((start_idx * frame_ms / 1000.0, idx * frame_ms / 1000.0))
        start_idx = None
    if start_idx is not None and len(envelope) - start_idx >= silence_frames_needed:
        windows.append((start_idx * frame_ms / 1000.0, len(envelope) * frame_ms / 1000.0))
    return windows


def derive_pause_windows_from_silence(
    samples: list[float],
    sample_rate: int,
    *,
    frame_ms: int = 20,
    silence_threshold: float = 0.08,
    min_silence_ms: int = 250,
    keep_silence_ms: int = 80,
) -> list[SliceWindow]:
    silence_windows = detect_silence_windows(
        samples,
        sample_rate,
        frame_ms=frame_ms,
        silence_threshold=silence_threshold,
        min_silence_ms=min_silence_ms,
    )
    total_duration = len(samples) / max(1, sample_rate)
    windows: list[SliceWindow] = []
    cursor = 0.0
    keep = keep_silence_ms / 1000.0
    for start, end in silence_windows:
        if start > cursor:
            windows.append(
                SliceWindow(
                    start_sec=max(0.0, cursor - keep),
                    end_sec=min(total_duration, start + keep),
                    confidence=0.82,
                    method="energy_pause_v1",
                )
            )
        cursor = end
    if cursor < total_duration:
        windows.append(
            SliceWindow(
                start_sec=max(0.0, cursor - keep),
                end_sec=total_duration,
                confidence=0.82,
                method="energy_pause_v1",
            )
        )
    return [window for window in windows if window.end_sec > window.start_sec]


def transcript_pause_merge(
    segments: list[dict[str, float | str]],
    *,
    max_gap_sec: float = 0.35,
    max_window_sec: float = 6.0,
) -> list[SliceWindow]:
    normalized = [
        {
            "start": float(segment.get("start") or 0.0),
            "end": float(segment.get("end") or 0.0),
        }
        for segment in segments
        if float(segment.get("end") or 0.0) > float(segment.get("start") or 0.0)
    ]
    if not normalized:
        return []
    windows: list[SliceWindow] = []
    current_start = normalized[0]["start"]
    current_end = normalized[0]["end"]
    for segment in normalized[1:]:
        gap = float(segment["start"] - current_end)
        if gap <= max_gap_sec and float(segment["end"] - current_start) <= max_window_sec:
            current_end = float(segment["end"])
            continue
        windows.append(
            SliceWindow(
                start_sec=round(current_start, 2),
                end_sec=round(current_end, 2),
                confidence=0.88,
                method="transcript_pause_v1",
            )
        )
        current_start = float(segment["start"])
        current_end = float(segment["end"])
    windows.append(
        SliceWindow(
            start_sec=round(current_start, 2),
            end_sec=round(current_end, 2),
            confidence=0.88,
            method="transcript_pause_v1",
        )
    )
    return windows


def _normalize_signal(signal: list[float]) -> list[float]:
    if not signal:
        return []
    peak = max(abs(value) for value in signal) or 1.0
    mean = sum(signal) / len(signal)
    return [(value - mean) / peak for value in signal]


def detect_peak_offset(signal_a: list[float], signal_b: list[float], sample_rate: int) -> SyncResult:
    if not signal_a or not signal_b:
        return SyncResult(detected_offset_sec=0.0, confidence=0.0, method="peak_only_v1", peak_value=0.0)
    idx_a = max(range(len(signal_a)), key=lambda idx: abs(signal_a[idx]))
    idx_b = max(range(len(signal_b)), key=lambda idx: abs(signal_b[idx]))
    peak_value = min(abs(signal_a[idx_a]), abs(signal_b[idx_b]))
    return SyncResult(
        detected_offset_sec=round((idx_b - idx_a) / max(1, sample_rate), 4),
        confidence=round(min(1.0, peak_value), 4),
        method="peak_only_v1",
        peak_value=round(peak_value, 4),
    )


def detect_offset_via_correlation(
    signal_a: list[float],
    signal_b: list[float],
    sample_rate: int,
    *,
    max_lag_sec: float = 1.5,
) -> SyncResult:
    norm_a = _normalize_signal(signal_a)
    norm_b = _normalize_signal(signal_b)
    if not norm_a or not norm_b:
        return SyncResult(detected_offset_sec=0.0, confidence=0.0, method="correlation_v1", peak_value=0.0)
    max_lag = int(sample_rate * max_lag_sec)
    best_lag = 0
    best_score = float("-inf")
    for lag in range(-max_lag, max_lag + 1):
        score = 0.0
        count = 0
        for idx_a, value in enumerate(norm_a):
            idx_b = idx_a + lag
            if 0 <= idx_b < len(norm_b):
                score += value * norm_b[idx_b]
                count += 1
        if count == 0:
            continue
        score /= count
        if score > best_score:
            best_score = score
            best_lag = lag
    confidence = 0.0 if best_score == float("-inf") else max(0.0, min(1.0, (best_score + 1.0) / 2.0))
    return SyncResult(
        detected_offset_sec=round(best_lag / max(1, sample_rate), 4),
        confidence=round(confidence, 4),
        method="correlation_v1",
        peak_value=round(best_score if best_score != float("-inf") else 0.0, 4),
    )


def detect_offset_hybrid(signal_a: list[float], signal_b: list[float], sample_rate: int) -> SyncResult:
    peak = detect_peak_offset(signal_a, signal_b, sample_rate)
    correlation = detect_offset_via_correlation(signal_a, signal_b, sample_rate)
    if abs(correlation.detected_offset_sec - peak.detected_offset_sec) <= 0.05:
        confidence = min(1.0, correlation.confidence + 0.08)
        return SyncResult(
            detected_offset_sec=correlation.detected_offset_sec,
            confidence=round(confidence, 4),
            method="peaks+correlation_v1",
            peak_value=max(peak.peak_value, correlation.peak_value),
        )
    return correlation if correlation.confidence >= peak.confidence else peak
