import pytest

pytestmark = pytest.mark.stale(reason="Jarvis live context — client extraction API changed")

import asyncio
import importlib
import sys
from types import ModuleType


def test_extract_client_context_keeps_llm_model_and_bounds_messages():
    fake_tts_engine = ModuleType("src.voice.tts_engine")
    fake_tts_engine.Qwen3TTSClient = object
    fake_tts_engine.FastTTSClient = object
    sys.modules["src.voice.tts_engine"] = fake_tts_engine

    fake_whisper = ModuleType("mlx_whisper")
    fake_whisper.transcribe = lambda *args, **kwargs: {"text": "", "segments": []}
    sys.modules["mlx_whisper"] = fake_whisper

    jarvis_handler = importlib.import_module("src.api.handlers.jarvis_handler")
    _extract_client_context = jarvis_handler._extract_client_context

    payload = {
        "llm_model": "x-ai/grok-4.1-fast",
        "pinned_files": [{"path": f"/tmp/f{i}.py"} for i in range(20)],
        "open_chat_context": {
            "chat_id": "chat-1",
            "messages": [{"role": "user", "content": str(i)} for i in range(30)],
        },
        "viewport_context": {"zoom_level": 2},
    }
    ctx = _extract_client_context(payload)

    assert ctx["llm_model"] == "x-ai/grok-4.1-fast"
    assert len(ctx["pinned_files"]) == 12
    assert len(ctx["open_chat_context"]["messages"]) == 10
    assert ctx["viewport_context"]["zoom_level"] == 2


def test_resolve_jarvis_text_model_prefers_preferred():
    from src.voice.jarvis_llm import resolve_jarvis_text_model

    model_id, route, reason = resolve_jarvis_text_model(
        default_model="qwen2.5:3b",
        preferred_model="x-ai/grok-4.1-fast",
        favorites=["meta-llama/llama-3.1-405b-instruct:free"],
        registry=None,
    )
    assert model_id == "x-ai/grok-4.1-fast"
    assert route == "provider_registry"
    assert reason == "preferred"


def test_get_jarvis_context_merges_live_context_payload():
    from src.voice.jarvis_llm import get_jarvis_context

    ctx = asyncio.run(
        get_jarvis_context(
            user_id="default_user",
            transcript="hello",
            extra_context={
                "llm_model": "x-ai/grok-4.1-fast",
                "open_chat_context": {"chat_id": "abc", "messages": [{"role": "user", "content": "hi"}]},
            },
        )
    )
    assert ctx["llm_model"] == "x-ai/grok-4.1-fast"
    assert ctx["open_chat_context"]["chat_id"] == "abc"
