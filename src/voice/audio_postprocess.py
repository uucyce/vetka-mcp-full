"""
Audio post-processing helpers for local TTS prosody control.
"""

from __future__ import annotations

import io
import wave
import numpy as np


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _resample_linear(audio: np.ndarray, target_len: int) -> np.ndarray:
    if target_len <= 0:
        return np.zeros(0, dtype=np.float32)
    if audio.size == 0:
        return np.zeros(target_len, dtype=np.float32)
    if audio.size == 1:
        return np.full(target_len, float(audio[0]), dtype=np.float32)
    x_old = np.linspace(0.0, 1.0, num=audio.size, dtype=np.float32)
    x_new = np.linspace(0.0, 1.0, num=target_len, dtype=np.float32)
    return np.interp(x_new, x_old, audio).astype(np.float32, copy=False)


def apply_speed(audio: np.ndarray, speed: float) -> np.ndarray:
    speed = _clamp(float(speed or 1.0), 0.75, 1.35)
    if audio.size == 0 or abs(speed - 1.0) < 1e-6:
        return audio.astype(np.float32, copy=False)
    target_len = max(1, int(round(audio.size / speed)))
    return _resample_linear(audio.astype(np.float32, copy=False), target_len)


def apply_pitch_preserve_length(audio: np.ndarray, semitones: int) -> np.ndarray:
    semitones = int(max(-6, min(6, int(semitones or 0))))
    if audio.size == 0 or semitones == 0:
        return audio.astype(np.float32, copy=False)
    # Classic quick pitch shift approximation:
    # 1) resample by factor (changes pitch + duration),
    # 2) resample back to original length (restore duration).
    factor = float(2.0 ** (semitones / 12.0))
    temp_len = max(1, int(round(audio.size / factor)))
    pitched = _resample_linear(audio.astype(np.float32, copy=False), temp_len)
    return _resample_linear(pitched, audio.size)


def apply_energy(audio: np.ndarray, energy: float) -> np.ndarray:
    energy = _clamp(float(energy or 0.5), 0.2, 1.2)
    # Keep changes moderate: around 0.76..1.28 gain for allowed range.
    gain = 0.6 + energy * 0.55
    out = audio.astype(np.float32, copy=False) * gain
    return np.clip(out, -1.0, 1.0).astype(np.float32, copy=False)


def append_pause(audio: np.ndarray, sample_rate: int, pause_profile: str | None) -> np.ndarray:
    profile = str(pause_profile or "balanced").strip().lower()
    if profile == "short":
        pause_ms = 40
    elif profile == "calm":
        pause_ms = 140
    else:
        pause_ms = 80
    if pause_ms <= 0:
        return audio.astype(np.float32, copy=False)
    pause_samples = int(sample_rate * (pause_ms / 1000.0))
    if pause_samples <= 0:
        return audio.astype(np.float32, copy=False)
    silence = np.zeros(pause_samples, dtype=np.float32)
    return np.concatenate([audio.astype(np.float32, copy=False), silence], axis=0)


def apply_prosody_to_audio(
    audio: np.ndarray,
    *,
    sample_rate: int,
    speed: float | None = None,
    pitch: int | None = None,
    energy: float | None = None,
    pause_profile: str | None = None,
) -> np.ndarray:
    out = audio.astype(np.float32, copy=False)
    if speed is not None:
        out = apply_speed(out, speed)
    if pitch is not None:
        out = apply_pitch_preserve_length(out, int(pitch))
    if energy is not None:
        out = apply_energy(out, energy)
    out = append_pause(out, sample_rate, pause_profile)
    return np.clip(out, -1.0, 1.0).astype(np.float32, copy=False)


def float_audio_to_wav_bytes(audio: np.ndarray, sample_rate: int = 24000) -> bytes:
    pcm16 = (np.clip(audio.astype(np.float32, copy=False), -1.0, 1.0) * 32767.0).astype(np.int16)
    with io.BytesIO() as buffer:
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(int(sample_rate))
            wav.writeframes(pcm16.tobytes())
        return buffer.getvalue()

