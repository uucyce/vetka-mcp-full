import pytest

from src.mcp.tools.llm_call_tool import LLMCallTool
from src.mcp.tools.llm_call_tool_async import LLMCallToolAsync
from src.utils.unified_key_manager import UnifiedKeyManager, ProviderType, APIKeyRecord


def test_vetka_call_model_applies_favorite_key_hook(monkeypatch):
    tool = LLMCallTool()
    calls = {"favorite": 0}

    monkeypatch.setattr(tool, "_detect_provider", lambda model, source=None: "anthropic")
    monkeypatch.setattr(tool, "_apply_favorite_preferred_key", lambda provider: calls.__setitem__("favorite", calls["favorite"] + 1))
    monkeypatch.setattr(tool, "_emit_request_to_chat", lambda *args, **kwargs: None)
    monkeypatch.setattr(tool, "_emit_response_to_chat", lambda *args, **kwargs: None)
    monkeypatch.setattr(tool, "_track_usage_for_balance", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        tool,
        "_call_provider_sync",
        lambda **kwargs: {"message": {"content": "ok"}, "provider": "anthropic", "model": "claude", "usage": None},
    )

    result = tool.execute(
        {
            "model": "claude-sonnet-4-5",
            "messages": [{"role": "user", "content": "ping"}],
        }
    )

    assert result["success"] is True
    assert calls["favorite"] == 1


@pytest.mark.asyncio
async def test_mycelium_call_model_applies_favorite_key_hook(monkeypatch):
    tool = LLMCallToolAsync()
    calls = {"favorite": 0}

    async def fake_resilient_llm_call(**kwargs):
        return {"message": {"content": "ok"}, "provider": "anthropic", "model": "claude", "usage": None}

    monkeypatch.setattr(tool, "_detect_provider", lambda model, source=None: "anthropic")
    monkeypatch.setattr(tool, "_apply_favorite_preferred_key", lambda provider: calls.__setitem__("favorite", calls["favorite"] + 1))
    monkeypatch.setattr("src.mcp.tools.llm_call_tool_async.resilient_llm_call", fake_resilient_llm_call)
    monkeypatch.setattr(tool, "_track_usage_for_balance", lambda *args, **kwargs: None)

    result = await tool.execute(
        {
            "model": "claude-sonnet-4-5",
            "messages": [{"role": "user", "content": "ping"}],
        }
    )

    assert result["success"] is True
    assert calls["favorite"] == 1


def test_get_active_key_honors_preferred_key():
    km = UnifiedKeyManager()
    provider = ProviderType.OPENAI
    km.keys[provider] = [
        APIKeyRecord(provider=provider, key="sk-test-key-11111111"),
        APIKeyRecord(provider=provider, key="sk-test-key-22222222"),
    ]
    masked = km.keys[provider][1].mask()

    km.set_preferred_key("openai", masked)
    selected = km.get_active_key(provider)

    assert selected == "sk-test-key-22222222"
