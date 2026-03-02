import io
import wave

import numpy as np

from src.voice.audio_postprocess import apply_prosody_to_audio, float_audio_to_wav_bytes


def _sine_wave(seconds: float = 1.0, sr: int = 24000, freq: float = 220.0) -> np.ndarray:
    t = np.linspace(0.0, seconds, int(sr * seconds), endpoint=False, dtype=np.float32)
    return 0.2 * np.sin(2.0 * np.pi * freq * t).astype(np.float32)


def test_apply_prosody_changes_length_for_speed_and_pause():
    sr = 24000
    audio = _sine_wave(seconds=1.0, sr=sr)
    out = apply_prosody_to_audio(
        audio,
        sample_rate=sr,
        speed=1.15,
        pitch=2,
        energy=0.9,
        pause_profile="calm",
    )
    assert out.dtype == np.float32
    assert out.size > 0
    # Speed up shortens, pause extends; resulting duration should be non-identical.
    assert abs(out.size - audio.size) > 150


def test_float_audio_to_wav_bytes_produces_valid_wav_container():
    sr = 24000
    audio = _sine_wave(seconds=0.25, sr=sr)
    wav_bytes = float_audio_to_wav_bytes(audio, sample_rate=sr)
    assert isinstance(wav_bytes, (bytes, bytearray))
    assert len(wav_bytes) > 44  # WAV header + payload
    assert wav_bytes[:4] == b"RIFF"
    assert wav_bytes[8:12] == b"WAVE"

    with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == sr
        assert wav.getnframes() > 0
