# MARKER_138.S2_5_MODEL_AUTODETECT_TEST
import asyncio

from src.api.routes import model_routes


class DummyModel:
    def __init__(self, payload):
        self._payload = payload

    def to_dict(self):
        return dict(self._payload)


class DummyRegistry:
    async def discover_ollama_models(self):
        return 2

    async def discover_voice_models(self):
        return 1

    def get_local(self):
        return [
            DummyModel(
                {
                    "id": "llama3:8b",
                    "name": "Llama 3 8B",
                    "provider": "ollama",
                    "type": "local",
                    "capabilities": ["chat"],
                    "context_window": 8192,
                    "pricing": {"prompt": "0", "completion": "0"},
                }
            )
        ]

    def get_mcp_agents(self):
        return [
            DummyModel(
                {
                    "id": "mcp/claude_code",
                    "name": "Claude Code",
                    "provider": "mcp",
                    "type": "mcp_agent",
                    "capabilities": ["code"],
                    "context_window": 200000,
                    "pricing": {"prompt": "0", "completion": "0"},
                }
            )
        ]


def test_autodetect_models_payload(monkeypatch):
    async def fake_get_all_models(force_refresh=False):  # noqa: ARG001
        return [
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "provider": "openai",
                "source": "openrouter",
                "pricing": {"prompt": "0.000005", "completion": "0.000015"},
                "capabilities": ["chat"],
            },
            {
                "id": "polza/voice-tts-v1",
                "name": "Polza Voice",
                "provider": "polza",
                "source": "polza",
                "type": "voice",
                "capabilities": ["tts"],
                "pricing": {"prompt": "0.000001", "completion": "0.000002"},
            },
        ]

    monkeypatch.setattr(model_routes, "get_model_registry", lambda: DummyRegistry())
    monkeypatch.setattr("src.elisya.model_fetcher.get_all_models", fake_get_all_models)
    monkeypatch.setattr("src.elisya.model_fetcher.classify_model_type", lambda m: m)
    monkeypatch.setattr(
        model_routes,
        "_detect_qwen_tts_server",
        lambda: asyncio.sleep(0, result={"running": True, "url": "http://127.0.0.1:5003/health"}),
    )

    payload = asyncio.run(model_routes.autodetect_models(force_refresh=True))

    assert payload["success"] is True
    assert payload["force_refresh"] is True
    assert payload["qwen_tts"]["running"] is True
    assert payload["categories"]["voice"] >= 2  # polza voice + local qwen tts
    assert any(m.get("source_display") == "Polza" for m in payload["cloud_models"])


def test_refresh_model_cache_uses_autodetect(monkeypatch):
    monkeypatch.setattr(
        "src.elisya.model_fetcher.load_cache",
        lambda: {"models": [{"id": "old/model"}]},
    )

    async def fake_build(force_refresh=False):  # noqa: ARG001
        return {
            "models": [{"id": "new/model"}, {"id": "old/model"}],
            "categories": {"text": 2, "voice": 0, "image": 0, "embedding": 0},
            "qwen_tts": {"running": False},
        }

    monkeypatch.setattr(model_routes, "_build_autodetect_payload", fake_build)

    payload = asyncio.run(model_routes.refresh_model_cache())

    assert payload["success"] is True
    assert payload["count"] == 2
    assert payload["new_count"] == 1
    assert payload["categories"]["text"] == 2
