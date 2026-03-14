import os

from scripts.voice_mode_benchmark import _extract_ready_sentences


def test_stream_flush_fallback_emits_phrase_without_punctuation(monkeypatch):
    monkeypatch.setenv("BENCH_STREAM_FLUSH_MIN_WORDS", "6")
    monkeypatch.setenv("BENCH_STREAM_FLUSH_MIN_CHARS", "20")
    ready, remainder = _extract_ready_sentences(
        "это длинный поток без знаков препинания который должен стартовать tts раньше"
    )
    assert ready, "expected fallback phrase flush"
    assert len(ready[0].split()) == 6
    assert remainder


def test_stream_flush_prefers_punctuation_boundaries(monkeypatch):
    monkeypatch.setenv("BENCH_STREAM_FLUSH_MIN_WORDS", "6")
    monkeypatch.setenv("BENCH_STREAM_FLUSH_MIN_CHARS", "20")
    ready, remainder = _extract_ready_sentences("первая фраза готова. вторая еще")
    assert ready == ["первая фраза готова."]
    assert remainder == "вторая еще"


def test_stream_flush_handles_clause_boundaries(monkeypatch):
    monkeypatch.setenv("BENCH_STREAM_FLUSH_MIN_WORDS", "5")
    monkeypatch.setenv("BENCH_STREAM_FLUSH_MIN_CHARS", "20")
    ready, remainder = _extract_ready_sentences("это важный момент, который нужно сказать аккуратно и без разрыва")
    assert ready
    assert "момент," in ready[0]
    assert remainder or len(ready) > 1
