import importlib
import sys
from types import ModuleType


def _load_jarvis_handler():
    fake_tts_engine = ModuleType("src.voice.tts_engine")
    fake_tts_engine.Qwen3TTSClient = object
    fake_tts_engine.FastTTSClient = object
    fake_tts_engine.ESpeakTTSClient = object
    sys.modules["src.voice.tts_engine"] = fake_tts_engine

    fake_whisper = ModuleType("mlx_whisper")
    fake_whisper.transcribe = lambda *args, **kwargs: {"text": "", "segments": []}
    sys.modules["mlx_whisper"] = fake_whisper
    return importlib.import_module("src.api.handlers.jarvis_handler")


def test_myco_help_fact_bundle_prefers_pinned_then_keeps_visible_as_anchor():
    jh = _load_jarvis_handler()
    facts = jh._build_myco_help_fact_bundle(
        {
            "viewport_context": {
                "viewport_nodes": [
                    {"name": "tree_handlers.py"},
                    {"name": "workflow_handlers.py"},
                ]
            },
            "pinned_files": [{"path": "/tmp/commands.rs"}],
        }
    )
    assert "/tmp/commands.rs" in facts["see_now"]
    assert "Artifact" in " ".join(facts["actions"])
    assert "/tmp/commands.rs" in facts["next_step"]
    assert "tree_handlers.py" in " ".join(facts["anchors"])


def test_myco_help_fallback_is_fact_bound():
    jh = _load_jarvis_handler()
    text = jh._build_myco_help_fallback_response(
        {
            "label": "Artifact Panel",
            "open_chat_context": {"chat_id": "chat-1"},
        }
    )
    assert "Artifact Panel" in text
    assert "рабочем окне ВЕТКА" not in text


def test_myco_help_guard_replaces_generic_answer_when_anchor_missing():
    jh = _load_jarvis_handler()
    context = {
        "viewport_context": {"viewport_nodes": [{"name": "commands.rs"}]},
        "label": "commands.rs",
    }
    assert jh._should_replace_with_myco_fact_fallback("Я готов помочь и объяснить интерфейс.", context) is True
    assert jh._should_replace_with_myco_fact_fallback("Сейчас в фокусе commands.rs. Можно открыть его в Artifact.", context) is False


def test_myco_help_clarify_response_is_short_and_guided():
    jh = _load_jarvis_handler()
    text = jh._build_myco_help_clarify_response({"viewport_summary": "чат и дерево проекта"})
    assert "неуверенно расслышала" in text
    assert "что я вижу" in text
