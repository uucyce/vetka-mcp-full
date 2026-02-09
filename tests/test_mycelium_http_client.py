"""Tests for MyceliumHTTPClient (MARKER_129.3)"""

import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

import httpx
from src.mcp.mycelium_http_client import MyceliumHTTPClient, get_mycelium_client
import src.mcp.mycelium_http_client as mhc_module


class TestMyceliumHTTPClientInit:
    def test_default_url(self):
        client = MyceliumHTTPClient()
        assert "localhost:5001" in client.vetka_url

    def test_custom_url(self):
        client = MyceliumHTTPClient(vetka_url="http://remote:9000")
        assert client.vetka_url == "http://remote:9000"

    @patch.dict("os.environ", {"VETKA_API_URL": "http://env-host:7777"})
    def test_env_var_url(self):
        # Re-evaluate module-level default by passing None explicitly
        import importlib
        importlib.reload(mhc_module)
        client = mhc_module.MyceliumHTTPClient()
        assert client.vetka_url == "http://env-host:7777"
        # Reload back to avoid side effects
        importlib.reload(mhc_module)


class TestMyceliumHTTPClientLifecycle:
    def test_start_creates_client(self):
        client = MyceliumHTTPClient()
        assert client._client is None
        asyncio.run(client.start())
        assert client._client is not None
        assert client.is_ready is True
        asyncio.run(client.stop())

    def test_stop_closes_client(self):
        client = MyceliumHTTPClient()
        asyncio.run(client.start())
        asyncio.run(client.stop())
        assert client._client is None
        assert client.is_ready is False


class TestGetMyceliumClientSingleton:
    def test_returns_singleton(self):
        mhc_module._mycelium_client = None
        a = get_mycelium_client()
        b = get_mycelium_client()
        assert a is b
        mhc_module._mycelium_client = None

    def test_creates_instance_when_none(self):
        mhc_module._mycelium_client = None
        result = mhc_module.get_mycelium_client()
        assert isinstance(result, mhc_module.MyceliumHTTPClient)
        mhc_module._mycelium_client = None


class TestEmitChatMessage:
    def test_sends_correct_body(self):
        client = MyceliumHTTPClient()
        mock_http = AsyncMock()
        client._client = mock_http
        asyncio.run(client.emit_chat_message("grp1", "hello", sender="bot", msg_type="info"))
        mock_http.post.assert_awaited_once_with(
            "/api/debug/mcp/groups/grp1/send",
            json={"agent_id": "bot", "content": "hello", "message_type": "info"},
        )

    def test_noop_when_client_none(self):
        client = MyceliumHTTPClient()
        # No error when _client is None
        asyncio.run(client.emit_chat_message("grp1", "hello"))


class TestEmitPipelineProgress:
    def test_formats_role_with_model(self):
        client = MyceliumHTTPClient()
        mock_http = AsyncMock()
        client._client = mock_http
        asyncio.run(client.emit_pipeline_progress("c1", "@coder", "done", model="org/qwen3"))
        body = mock_http.post.call_args[1]["json"]
        assert body["content"] == "@coder (qwen3): done"

    def test_system_model_no_parens(self):
        client = MyceliumHTTPClient()
        mock_http = AsyncMock()
        client._client = mock_http
        asyncio.run(client.emit_pipeline_progress("c1", "@scout", "scanning"))
        body = mock_http.post.call_args[1]["json"]
        assert body["content"] == "@scout: scanning"

    def test_skips_when_no_chat_id(self):
        client = MyceliumHTTPClient()
        mock_http = AsyncMock()
        client._client = mock_http
        asyncio.run(client.emit_pipeline_progress("", "@coder", "msg"))
        mock_http.post.assert_not_awaited()


class TestNotifyBoardUpdate:
    def test_sends_correct_payload(self):
        client = MyceliumHTTPClient()
        mock_http = AsyncMock()
        client._client = mock_http
        asyncio.run(client.notify_board_update(action="add", summary={"total": 5}))
        mock_http.post.assert_awaited_once_with(
            "/api/debug/task-board/notify",
            json={"action": "add", "summary": {"total": 5}},
        )

    def test_default_summary_empty_dict(self):
        client = MyceliumHTTPClient()
        mock_http = AsyncMock()
        client._client = mock_http
        asyncio.run(client.notify_board_update())
        body = mock_http.post.call_args[1]["json"]
        assert body == {"action": "update", "summary": {}}


class TestCheckVetkaHealth:
    def test_returns_true_on_200(self):
        client = MyceliumHTTPClient()
        mock_http = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_http.get.return_value = mock_resp
        client._client = mock_http
        assert asyncio.run(client.check_vetka_health()) is True

    def test_returns_false_on_500(self):
        client = MyceliumHTTPClient()
        mock_http = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_http.get.return_value = mock_resp
        client._client = mock_http
        assert asyncio.run(client.check_vetka_health()) is False

    def test_returns_false_when_no_client(self):
        client = MyceliumHTTPClient()
        assert asyncio.run(client.check_vetka_health()) is False

    def test_returns_false_on_exception(self):
        client = MyceliumHTTPClient()
        mock_http = AsyncMock()
        mock_http.get.side_effect = httpx.ConnectError("refused")
        client._client = mock_http
        assert asyncio.run(client.check_vetka_health()) is False
