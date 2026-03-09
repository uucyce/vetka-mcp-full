from src.api.handlers import jarvis_handler as jh


def test_jarvis_session_audio_methods_are_bound_to_class():
    s = jh.JarvisSession(user_id="u")
    s.add_audio_chunk(b"\x00\x01" * 1600)  # ~0.1s at 16kHz
    assert len(s.audio_buffer) == 1
    assert s.total_duration > 0
    assert isinstance(s.get_full_audio(), (bytes, bytearray))


def test_stage_machine_deep_query_trigger_keywords_and_length():
    assert jh._is_deep_query("Сделай подробный анализ архитектуры и исследование") is True
    assert jh._is_deep_query("привет") is False
    long_text = "слово " * 30
    assert jh._is_deep_query(long_text) is True


def test_select_filler_phrase_returns_non_empty_text():
    phrase = jh._select_filler_phrase("Найди документ по памяти")
    assert isinstance(phrase, str)
    assert phrase.strip()
