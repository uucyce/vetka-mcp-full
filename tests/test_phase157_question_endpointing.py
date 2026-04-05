"""
Phase 157.2.8 tests:
- Question-end endpointing heuristic (test-only mode)
- VAD silence threshold switching
- A/B metric calculation for false-cut vs latency gain
"""

from __future__ import annotations


def test_question_hint_detection_basic():
    from src.api.handlers import jarvis_handler as jh

    assert jh._looks_like_question_hint("Как устроен CAM?")
    assert not jh._looks_like_question_hint("Как устроен CAM")
    assert not jh._looks_like_question_hint("а?")


def test_effective_vad_silence_duration_switches_only_in_test_mode(monkeypatch):
    from src.api.handlers import jarvis_handler as jh

    session = jh.JarvisSession(user_id="u1")
    session.transcript_hint_live = "Почему так происходит?"

    monkeypatch.setattr(jh, "VAD_SILENCE_DURATION", 1.5)
    monkeypatch.setattr(jh, "VAD_QEND_SILENCE_DURATION", 0.8)

    monkeypatch.setattr(jh, "VAD_QEND_TEST_MODE", False)
    assert jh._effective_vad_silence_duration(session) == 1.5

    monkeypatch.setattr(jh, "VAD_QEND_TEST_MODE", True)
    assert jh._effective_vad_silence_duration(session) == 0.8

    session.transcript_hint_live = "Это не вопрос"
    assert jh._effective_vad_silence_duration(session) == 1.5


def test_question_endpointing_ab_metrics(monkeypatch):
    from src.api.handlers import jarvis_handler as jh

    # Baseline 1.5s, experiment 0.9s on question hints.
    cases = [
        {"is_question_hint": True, "silence_observed_s": 1.0, "truly_finished": True},   # gain, no false-cut
        {"is_question_hint": True, "silence_observed_s": 1.0, "truly_finished": False},  # experiment false-cut
        {"is_question_hint": False, "silence_observed_s": 1.0, "truly_finished": True},  # no trigger in both
        {"is_question_hint": True, "silence_observed_s": 1.7, "truly_finished": True},   # trigger both
    ]

    monkeypatch.setattr(jh, "VAD_SILENCE_DURATION", 1.5)
    monkeypatch.setattr(jh, "VAD_QEND_SILENCE_DURATION", 0.9)

    report = jh.compute_question_endpointing_ab(cases)
    assert report["cases"] == 4
    # Baseline does not false-cut in this set; experiment should cut once.
    assert report["baseline_false_cut_rate"] == 0.0
    assert report["experiment_false_cut_rate"] == 0.25
    # Gains should be positive for true-finish question cases that can trigger earlier.
    assert report["latency_gain_ms_avg_on_true_finish"] > 0


def test_sentence_chunk_extraction():
    from src.api.handlers import jarvis_handler as jh

    ready, tail = jh._extract_ready_sentences("Привет. Как дела? Я")
    assert ready == ["Привет.", "Как дела?"]
    assert tail == "Я"
