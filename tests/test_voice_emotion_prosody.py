import pytest

from src.voice.emotion_prosody import infer_and_map_prosody


def test_emotion_inference_has_required_channels():
    result = infer_and_map_prosody("Срочно! Исправь критическую ошибку, пожалуйста.")
    assert "emotion" in result
    assert "prosody" in result
    for key in ("sentiment", "arousal", "urgency", "confidence", "politeness"):
        assert key in result["emotion"]
        assert 0.0 <= float(result["emotion"][key]) <= 1.0


def test_prosody_mapping_is_bounded():
    result = infer_and_map_prosody("Это отличный результат, спасибо!")
    prosody = result["prosody"]
    assert 0.94 <= float(prosody["speed"]) <= 1.06
    assert -1 <= int(prosody["pitch"]) <= 1
    assert 0.45 <= float(prosody["energy"]) <= 0.72
    assert prosody["pause_profile"] in {"balanced", "calm"}


def test_prosody_smoothing_limits_jump():
    prev = {"speed": 0.86, "pitch": -3, "energy": 0.34, "pause_profile": "calm"}
    result = infer_and_map_prosody("ASAP!!! NOW!!!", previous_prosody=prev)
    prosody = result["prosody"]
    assert 0.94 <= float(prosody["speed"]) <= 1.06
    assert -1 <= int(prosody["pitch"]) <= 1
    assert 0.45 <= float(prosody["energy"]) <= 0.72


def test_stability_guard_neutralizes_mixed_language_text():
    result = infer_and_map_prosody("Привет! Today we deploy hotfix and then проверяем снова.")
    prosody = result["prosody"]
    assert float(prosody["speed"]) == 1.0
    assert int(prosody["pitch"]) == 0
    assert float(prosody["energy"]) == 0.55
    assert prosody["pause_profile"] == "balanced"
