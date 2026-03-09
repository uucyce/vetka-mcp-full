from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np

from scripts.voice_wav_quality_audit import analyze_wav


def _write_wav(path: Path, audio: np.ndarray, sr: int = 24000) -> None:
    audio_i16 = np.clip(audio, -1.0, 1.0)
    audio_i16 = (audio_i16 * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_i16.tobytes())


def test_wav_quality_audit_detects_long_pause(tmp_path: Path):
    sr = 24000
    t1 = np.linspace(0, 0.8, int(sr * 0.8), endpoint=False)
    t2 = np.linspace(0, 0.8, int(sr * 0.8), endpoint=False)
    speech1 = 0.18 * np.sin(2 * math.pi * 210 * t1)
    pause = np.zeros(int(sr * 1.0), dtype=np.float32)
    speech2 = 0.16 * np.sin(2 * math.pi * 180 * t2)
    x = np.concatenate([speech1.astype(np.float32), pause, speech2.astype(np.float32)])
    p = tmp_path / "sample.wav"
    _write_wav(p, x, sr=sr)
    report = analyze_wav(p)
    assert report["ok"] is True
    assert report["longest_pause_ms"] >= 900
    assert report["pause_count"] >= 1

