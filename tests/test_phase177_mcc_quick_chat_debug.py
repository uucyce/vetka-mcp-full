from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path):
    from src.api.routes.chat_routes import router as chat_router

    app = FastAPI()
    app.include_router(chat_router)
    app.state.flask_config = {"CHAT_HISTORY_DIR": tmp_path / "chat_history"}
    return TestClient(app)


def test_quick_chat_uses_selected_model_source_and_persists_history(client, monkeypatch):
    import src.elisya.provider_registry as provider_mod

    async def fake_call_model_v2(**kwargs):
        assert kwargs["model"] == "moonshotai/kimi-k2.5"
        assert kwargs["source"] == "openrouter"
        return {"message": {"content": "Kimi reply"}}

    monkeypatch.setattr(provider_mod, "call_model_v2", fake_call_model_v2)

    node_path = "mcc::architect::task::tb_debug"
    response = client.post(
        "/api/chat/quick",
        json={
            "message": "hello",
            "role": "architect",
            "context": {
                "model": "moonshotai/kimi-k2.5",
                "selected_key_provider": "openrouter",
                "node_path": node_path,
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["reply"] == "Kimi reply"
    assert data["model"] == "moonshotai/kimi-k2.5"
    assert data["provider"] == "openrouter"
    assert data["node_path"] == node_path

    history = client.get("/api/chat/history", params={"path": node_path}).json()["history"]
    assert [row["role"] for row in history] == ["user", "assistant"]
    assert history[0]["content"] == "hello"
    assert history[1]["content"] == "Kimi reply"


def test_quick_chat_fallback_still_persists_message(client, monkeypatch):
    import src.elisya.provider_registry as provider_mod

    async def fake_call_model_v2(**kwargs):
        raise RuntimeError("provider offline")

    monkeypatch.setattr(provider_mod, "call_model_v2", fake_call_model_v2)

    node_path = "mcc::architect::project::project"
    response = client.post(
        "/api/chat/quick",
        json={
            "message": "hello",
            "role": "architect",
            "context": {"node_path": node_path},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "fallback"
    assert data["reply"] == "Backend model unavailable"
    assert data["node_path"] == node_path

    history = client.get("/api/chat/history", params={"path": node_path}).json()["history"]
    assert [row["role"] for row in history] == ["user", "assistant"]
    assert history[-1]["content"] == "Backend model unavailable"
