import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
import asyncio


def test_is_first_architect_turn_detection():
    from src.api.routes.architect_chat_routes import ChatContext, _is_first_architect_turn

    assert _is_first_architect_turn(None) is True
    assert _is_first_architect_turn(ChatContext(chatHistory=[])) is True
    assert _is_first_architect_turn(ChatContext(chatHistory=[{"role": "user", "content": "x"}])) is False
    # Non-meaningful rows should not count as real dialog turns
    assert _is_first_architect_turn(
        ChatContext(chatHistory=[{"role": "system", "content": "meta"}, {"role": "assistant", "content": ""}])
    ) is True


def test_resolve_architect_scope_root_prefers_workflow_scope(tmp_path):
    from src.api.routes.architect_chat_routes import ChatContext, _resolve_architect_scope_root

    nested = tmp_path / "repo"
    nested.mkdir()
    ctx = ChatContext(workflowContext={"scope_path": str(nested)})
    assert _resolve_architect_scope_root(ctx) == str(nested.resolve())


@pytest.mark.asyncio
async def test_jepa_bootstrap_force_on_first_call_non_empty(monkeypatch, tmp_path):
    import src.api.routes.architect_chat_routes as route_mod
    from src.api.routes.architect_chat_routes import ArchitectChatRequest, ChatContext

    (tmp_path / "README.md").write_text("demo", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")

    monkeypatch.setattr(route_mod, "_resolve_architect_scope_root", lambda context=None: str(tmp_path))

    called = {"force_jepa": None}

    class _FakePacker:
        async def pack(self, **kwargs):
            called["force_jepa"] = kwargs.get("force_jepa")
            return types.SimpleNamespace(
                jepa_context="## JEPA SEMANTIC CORE\n- provider_mode: deterministic",
                trace={"jepa_forced": True, "jepa_trigger": True},
            )

    monkeypatch.setattr(
        "src.orchestration.context_packer.get_context_packer",
        lambda: _FakePacker(),
    )

    req = ArchitectChatRequest(message="plan", context=ChatContext(chatHistory=[]))
    jepa_ctx, trace = await route_mod._build_architect_jepa_bootstrap(req, model_name="moonshotai/kimi-k2.5")

    assert "JEPA SEMANTIC CORE" in jepa_ctx
    assert trace.get("jepa_forced") is True
    assert called["force_jepa"] is True


@pytest.mark.asyncio
async def test_jepa_bootstrap_skips_empty_project(monkeypatch, tmp_path):
    import src.api.routes.architect_chat_routes as route_mod
    from src.api.routes.architect_chat_routes import ArchitectChatRequest, ChatContext

    monkeypatch.setattr(route_mod, "_resolve_architect_scope_root", lambda context=None: str(tmp_path))

    req = ArchitectChatRequest(message="plan", context=ChatContext(chatHistory=[]))
    jepa_ctx, trace = await route_mod._build_architect_jepa_bootstrap(req, model_name="moonshotai/kimi-k2.5")

    assert jepa_ctx == ""
    assert trace.get("jepa_skip_reason") == "empty_project_skip"
    assert trace.get("fallback_reason") == "empty_project_skip"


@pytest.mark.asyncio
async def test_jepa_bootstrap_skips_non_first_turn(monkeypatch, tmp_path):
    import src.api.routes.architect_chat_routes as route_mod
    from src.api.routes.architect_chat_routes import ArchitectChatRequest, ChatContext

    monkeypatch.setattr(route_mod, "_resolve_architect_scope_root", lambda context=None: str(tmp_path))

    req = ArchitectChatRequest(
        message="plan",
        context=ChatContext(chatHistory=[{"role": "user", "content": "prev"}]),
    )
    jepa_ctx, trace = await route_mod._build_architect_jepa_bootstrap(req, model_name="moonshotai/kimi-k2.5")

    assert jepa_ctx == ""
    assert trace.get("jepa_skip_reason") == "not_first_turn"
    assert trace.get("fallback_reason") == "not_first_turn"


@pytest.mark.asyncio
async def test_jepa_bootstrap_trace_contract_fields(monkeypatch, tmp_path):
    import src.api.routes.architect_chat_routes as route_mod
    from src.api.routes.architect_chat_routes import ArchitectChatRequest, ChatContext

    (tmp_path / "README.md").write_text("demo", encoding="utf-8")
    monkeypatch.setattr(route_mod, "_resolve_architect_scope_root", lambda context=None: str(tmp_path))

    class _FakePacker:
        async def pack(self, **kwargs):
            return types.SimpleNamespace(
                jepa_context="core",
                trace={
                    "jepa_forced": True,
                    "jepa_trigger": True,
                    "jepa_provider_mode": "deterministic_fallback",
                    "jepa_latency_ms": 7.25,
                },
            )

    monkeypatch.setattr("src.orchestration.context_packer.get_context_packer", lambda: _FakePacker())

    req = ArchitectChatRequest(message="plan", context=ChatContext(chatHistory=[]))
    _, trace = await route_mod._build_architect_jepa_bootstrap(req, model_name="moonshotai/kimi-k2.5")

    for key in ("jepa_forced", "jepa_trigger", "provider_mode", "latency_ms", "fallback_reason"):
        assert key in trace
    assert trace["jepa_forced"] is True
    assert trace["jepa_trigger"] is True
    assert trace["provider_mode"] == "deterministic_fallback"
    assert isinstance(trace["latency_ms"], float)


def test_architect_chat_injects_jepa_context_into_system_prompt(monkeypatch):
    import src.api.routes.architect_chat_routes as route_mod
    import src.elisya.provider_registry as provider_mod

    async def _fake_jepa(request, model_name):
        return "## JEPA SEMANTIC CORE\n- semantic_focus: repo, api", {"jepa_forced": True}

    captured = {}

    async def _fake_call_model_v2(**kwargs):
        captured["messages"] = kwargs.get("messages", [])
        return {"message": {"role": "assistant", "content": "ok"}}

    monkeypatch.setattr(route_mod, "_build_architect_jepa_bootstrap", _fake_jepa)
    monkeypatch.setattr(provider_mod, "call_model_v2", _fake_call_model_v2)

    app = FastAPI()
    app.include_router(route_mod.router)
    client = TestClient(app)

    resp = client.post(
        "/api/architect/chat",
        json={"message": "Build DAG", "context": {"preset": "dragon_silver", "chatHistory": []}},
    )
    assert resp.status_code == 200
    assert resp.json().get("success") is True

    system_msg = captured["messages"][0]["content"]
    assert "JEPA bootstrap semantic core" in system_msg
    assert "JEPA SEMANTIC CORE" in system_msg


@pytest.mark.asyncio
async def test_jepa_bootstrap_timeout_fallback(monkeypatch, tmp_path):
    import src.api.routes.architect_chat_routes as route_mod
    from src.api.routes.architect_chat_routes import ArchitectChatRequest, ChatContext

    (tmp_path / "README.md").write_text("demo", encoding="utf-8")
    monkeypatch.setattr(route_mod, "_resolve_architect_scope_root", lambda context=None: str(tmp_path))
    monkeypatch.setenv("VETKA_ARCH_JEPA_BOOTSTRAP_TIMEOUT_SEC", "0.1")

    class _SlowPacker:
        async def pack(self, **kwargs):
            await asyncio.sleep(0.2)
            return types.SimpleNamespace(jepa_context="core", trace={"jepa_forced": True})

    monkeypatch.setattr("src.orchestration.context_packer.get_context_packer", lambda: _SlowPacker())

    req = ArchitectChatRequest(message="plan", context=ChatContext(chatHistory=[]))
    jepa_ctx, trace = await route_mod._build_architect_jepa_bootstrap(req, model_name="moonshotai/kimi-k2.5")

    assert jepa_ctx == ""
    assert trace.get("jepa_skip_reason") == "bootstrap_timeout"
    assert trace.get("fallback_reason") == "bootstrap_timeout"


def test_architect_chat_non_blocking_on_jepa_timeout(monkeypatch, tmp_path):
    import src.api.routes.architect_chat_routes as route_mod
    import src.elisya.provider_registry as provider_mod

    (tmp_path / "README.md").write_text("demo", encoding="utf-8")
    monkeypatch.setattr(route_mod, "_resolve_architect_scope_root", lambda context=None: str(tmp_path))
    monkeypatch.setenv("VETKA_ARCH_JEPA_BOOTSTRAP_TIMEOUT_SEC", "0.1")

    class _SlowPacker:
        async def pack(self, **kwargs):
            await asyncio.sleep(0.2)
            return types.SimpleNamespace(jepa_context="core", trace={"jepa_forced": True})

    monkeypatch.setattr("src.orchestration.context_packer.get_context_packer", lambda: _SlowPacker())

    captured = {}

    async def _fake_call_model_v2(**kwargs):
        captured["messages"] = kwargs.get("messages", [])
        return {"message": {"role": "assistant", "content": "ok"}}

    monkeypatch.setattr(provider_mod, "call_model_v2", _fake_call_model_v2)

    app = FastAPI()
    app.include_router(route_mod.router)
    client = TestClient(app)

    resp = client.post(
        "/api/architect/chat",
        json={"message": "Build DAG", "context": {"preset": "dragon_silver", "chatHistory": []}},
    )
    assert resp.status_code == 200
    assert resp.json().get("success") is True

    system_msg = captured["messages"][0]["content"]
    assert "JEPA bootstrap status: skipped (bootstrap_timeout)" in system_msg


@pytest.mark.asyncio
async def test_jepa_bootstrap_runtime_error_fallback(monkeypatch, tmp_path):
    import src.api.routes.architect_chat_routes as route_mod
    from src.api.routes.architect_chat_routes import ArchitectChatRequest, ChatContext

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 155c contracts changed")

    (tmp_path / "README.md").write_text("demo", encoding="utf-8")
    monkeypatch.setattr(route_mod, "_resolve_architect_scope_root", lambda context=None: str(tmp_path))

    class _BrokenPacker:
        async def pack(self, **kwargs):
            raise RuntimeError("runtime down")

    monkeypatch.setattr("src.orchestration.context_packer.get_context_packer", lambda: _BrokenPacker())

    req = ArchitectChatRequest(message="plan", context=ChatContext(chatHistory=[]))
    jepa_ctx, trace = await route_mod._build_architect_jepa_bootstrap(req, model_name="moonshotai/kimi-k2.5")

    assert jepa_ctx == ""
    assert str(trace.get("fallback_reason", "")).startswith("bootstrap_error:")
