# MARKER_138.S2_2_JARVIS_MCP_SERVER_TEST
import asyncio

from src.mcp import jarvis_mcp_server as srv


def test_health_handler():
    payload = asyncio.run(srv._handle_health())
    assert payload["success"] is True
    assert payload["server"] == "jarvis"


def test_workflow_route_handler():
    payload = asyncio.run(srv._handle_workflow_route({"request": "fix bug quickly"}))
    assert payload["success"] is True
    assert payload["plan"]["workflow"] == "jarvis_fix"


def test_context_handler(monkeypatch):
    class DummyBridge:
        async def build_context(self, user_id, request):  # noqa: ARG002
            return {"user_id": user_id, "request": request, "context": {"k": "v"}}

    monkeypatch.setattr(srv, "get_jarvis_engram_bridge", lambda: DummyBridge())
    payload = asyncio.run(srv._handle_context({"user_id": "u1", "request": "hello"}))
    assert payload["success"] is True
    assert payload["context"]["user_id"] == "u1"


def test_chat_handler_timeout(monkeypatch):
    async def fake_respond(transcript, user_id):  # noqa: ARG001
        await asyncio.sleep(0.05)
        return "ok"

    monkeypatch.setattr(srv, "_get_jarvis_respond", lambda: fake_respond)
    payload = asyncio.run(srv._handle_chat({"request": "hello", "user_id": "u", "timeout": 1}))
    assert payload["success"] is True
    assert payload["response"] == "ok"
