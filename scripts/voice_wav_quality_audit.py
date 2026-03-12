#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import wave
from pathlib import Path
from typing import Any

import numpy as np


def _read_wav_mono(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        n = wf.getnframes()
        ch = wf.getnchannels()
        sw = wf.getsampwidth()
        raw = wf.readframes(n)
    if sw != 2:
        raise ValueError(f"Unsupported sample width: {sw}")
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        audio = audio.reshape(-1, ch).mean(axis=1)
    return audio, sr


def _run_lengths(mask: np.ndarray) -> list[tuple[int, int]]:
    if mask.size == 0:
        return []
    out: list[tuple[int, int]] = []
    start = 0
    val = bool(mask[0])
    for i in range(1, len(mask)):
        cur = bool(mask[i])
        if cur != val:
            out.append((start, i))
            start = i
            val = cur
    out.append((start, len(mask)))
    return out


def analyze_wav(path: Path) -> dict[str, Any]:
    x, sr = _read_wav_mono(path)
    if x.size == 0:
        return {
            "ok": False,
            "error": "empty_audio",
        }

    frame_ms = 20
    hop = int(sr * frame_ms / 1000)
    if hop < 1:
        hop = 1
    n_frames = max(1, x.size // hop)
    trimmed = x[: n_frames * hop]
    frames = trimmed.reshape(n_frames, hop)

    rms = np.sqrt(np.mean(frames * frames, axis=1) + 1e-12)
    p95 = float(np.percentile(rms, 95))
    silence_thr = max(0.004, p95 * 0.10)
    silent = rms < silence_thr
    voiced = ~silent

    runs = _run_lengths(silent)
    pause_ms = []
    for s, e in runs:
        if not silent[s]:
            continue
        dur = (e - s) * frame_ms
        if dur >= 120:  # micro-pauses filtered
            pause_ms.append(dur)

    long_pause_ms = [d for d in pause_ms if d >= 600]
    longest_pause = max(pause_ms) if pause_ms else 0

    # Stretch proxy: long voiced segments with very low energy modulation.
    # This often correlates with "drawn-out syllables".
    vruns = _run_lengths(voiced)
    stretch_events = 0
    for s, e in vruns:
        if not voiced[s]:
            continue
        dur = (e - s) * frame_ms
        if dur < 700:
            continue
        seg = rms[s:e]
        if seg.size < 3:
            continue
        mod = float(np.std(np.diff(seg)))
        if mod < 0.0025:
            stretch_events += 1

    dur_s = float(x.size / sr)
    silence_ratio = float(np.mean(silent))

    # Simple quality score (0-100), higher better
    score = 100.0
    score -= min(35.0, len(long_pause_ms) * 7.0)
    score -= min(25.0, max(0.0, (longest_pause - 700) / 80.0))
    score -= min(25.0, stretch_events * 8.0)
    score -= min(15.0, max(0.0, (silence_ratio - 0.32) * 120.0))
    score = max(0.0, round(score, 2))

    return {
        "ok": True,
        "sample_rate": sr,
        "duration_s": round(dur_s, 3),
        "frame_ms": frame_ms,
        "silence_threshold": round(silence_thr, 6),
        "silence_ratio": round(silence_ratio, 4),
        "pause_count": len(pause_ms),
        "long_pause_count": len(long_pause_ms),
        "longest_pause_ms": int(longest_pause),
        "stretch_events": int(stretch_events),
        "qc_score": score,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Analyze TTS wav quality (pauses/stretch proxies)")
    ap.add_argument("wav", type=str)
    args = ap.parse_args()
    data = analyze_wav(Path(args.wav))
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

