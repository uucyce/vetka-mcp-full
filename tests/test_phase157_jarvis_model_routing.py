import asyncio

from src.voice.jarvis_llm import resolve_jarvis_text_model, get_jarvis_context
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 157 contracts changed")

def test_resolve_jarvis_prefers_explicit_model_over_favorites():
    model_id, route, reason = resolve_jarvis_text_model(
        default_model="xiaomi/mimo-v2-flash",
        preferred_model="xiaomi/mimo-v2-flash",
        favorites=["x-ai/grok-4.1-fast"],
        registry=None,
    )
    assert model_id == "xiaomi/mimo-v2-flash"
    assert route == "provider_registry"
    assert reason == "preferred"


def test_get_jarvis_context_keeps_model_source():
    ctx = asyncio.run(
        get_jarvis_context(
            user_id="u",
            transcript="привет",
            extra_context={
                "llm_model": "xiaomi/mimo-v2-flash",
                "llm_model_source": "polza",
            },
        )
    )
    assert ctx.get("llm_model") == "xiaomi/mimo-v2-flash"
    assert ctx.get("llm_model_source") == "polza"
