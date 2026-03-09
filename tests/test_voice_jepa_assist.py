import os
from types import SimpleNamespace

from src.services.mcc_jepa_adapter import JepaRuntimeUnavailableError
from src.services.progressive_tts_service import ProgressiveTtsService


def test_voice_jepa_disabled_keeps_baseline(monkeypatch):
    monkeypatch.setenv("VETKA_VOICE_JEPA_ASSIST_ENABLE", "false")
    svc = ProgressiveTtsService()
    sentences = ["one.", "two.", "three.", "four."]
    text = " ".join(["token"] * 60)
    reduced, trace = svc._condense_sentences_with_jepa(
        text=text,
        sentences=sentences,
        session_key="baseline-no-jepa",
    )
    assert reduced == sentences
    assert trace["enabled"] is False
    assert trace["triggered"] is False


def test_voice_jepa_trigger_requires_long_descriptive_text(monkeypatch):
    monkeypatch.setenv("VETKA_VOICE_JEPA_ASSIST_ENABLE", "true")
    svc = ProgressiveTtsService()

    short_text = "Hi."
    short_sentences = ["Hi."]
    assert svc._should_trigger_jepa(short_text, short_sentences) is False

    long_text = " ".join(["word"] * 30)
    long_sentences = ["a.", "b.", "c.", "d."]
    assert svc._should_trigger_jepa(long_text, long_sentences) is True


def test_voice_jepa_condenses_when_triggered(monkeypatch):
    monkeypatch.setenv("VETKA_VOICE_JEPA_ASSIST_ENABLE", "true")
    monkeypatch.setenv("VETKA_VOICE_JEPA_HYSTERESIS_ON", "1")
    monkeypatch.setenv("VETKA_VOICE_JEPA_KEEP_SENTENCES", "3")

    svc = ProgressiveTtsService()
    sentences = [
        "Opening sentence.",
        "Memory CAM ARC ELISION summary.",
        "Secondary detail for implementation.",
        "Another contextual sentence.",
        "Tail sentence that can be dropped.",
    ]
    text = " ".join(["token"] * 40)

    def fake_embed(
        *,
        texts,
        target_dim,
        provider_override=None,
        strict_runtime=False,
        timeout_sec=None,
        allow_local_fallback=True,
    ):
        vectors = [[0.0, 0.0] for _ in texts]
        vectors[0] = [1.0, 0.0]
        vectors[1] = [0.99, 0.0]
        vectors[2] = [0.98, 0.0]
        vectors[3] = [0.1, 0.0]
        vectors[4] = [0.01, 0.0]
        return SimpleNamespace(vectors=vectors, provider_mode="jepa_runtime_module")

    monkeypatch.setattr("src.services.progressive_tts_service.embed_texts_for_overlay", fake_embed)

    reduced, trace = svc._condense_sentences_with_jepa(
        text=text,
        sentences=sentences,
        session_key="voice-test",
    )

    assert trace["triggered"] is True
    assert trace["provider_mode"] == "jepa_runtime_module"
    assert len(reduced) == 3
    assert reduced[0] == "Opening sentence."


def test_voice_jepa_hysteresis_turns_off(monkeypatch):
    monkeypatch.setenv("VETKA_VOICE_JEPA_ASSIST_ENABLE", "true")
    monkeypatch.setenv("VETKA_VOICE_JEPA_HYSTERESIS_ON", "1")
    monkeypatch.setenv("VETKA_VOICE_JEPA_HYSTERESIS_OFF", "1")

    svc = ProgressiveTtsService()
    session = "hyst-session"

    assert svc._apply_hysteresis(session_key=session, trigger_raw=True) is True
    assert svc._apply_hysteresis(session_key=session, trigger_raw=False) is False


def test_voice_jepa_runtime_unavailable_uses_deterministic_fallback(monkeypatch):
    monkeypatch.setenv("VETKA_VOICE_JEPA_ASSIST_ENABLE", "true")
    monkeypatch.setenv("VETKA_VOICE_JEPA_HYSTERESIS_ON", "1")
    monkeypatch.setenv("VETKA_VOICE_JEPA_KEEP_SENTENCES", "3")
    svc = ProgressiveTtsService()
    sentences = ["one.", "two.", "three.", "four."]
    text = " ".join(["token"] * 30)

    calls = {"n": 0}

    def fake_embed(
        *,
        texts,
        target_dim,
        provider_override=None,
        strict_runtime=False,
        timeout_sec=None,
        allow_local_fallback=True,
    ):
        calls["n"] += 1
        if provider_override == "runtime":
            raise JepaRuntimeUnavailableError("runtime unavailable in test")
        vectors = [[0.1, 0.2] for _ in texts]
        return SimpleNamespace(vectors=vectors, provider_mode="deterministic_fallback")

    monkeypatch.setattr("src.services.progressive_tts_service.embed_texts_for_overlay", fake_embed)
    reduced, trace = svc._condense_sentences_with_jepa(
        text=text,
        sentences=sentences,
        session_key="timeout-test",
    )
    assert calls["n"] == 2
    assert len(reduced) == 3
    assert trace.get("provider_mode") == "deterministic_fallback"
