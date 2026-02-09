"""Tests for MyceliumWSBroadcaster (MARKER_129.5)"""

import pytest
import asyncio
import json
import time
from unittest.mock import patch, AsyncMock, MagicMock


from src.mcp.mycelium_ws_server import MyceliumWSBroadcaster, get_ws_broadcaster, _ws_broadcaster


class TestMyceliumWSBroadcaster:
    """Tests for MyceliumWSBroadcaster (MARKER_129.5)"""

    def test_default_port_and_host(self):
        b = MyceliumWSBroadcaster()
        assert b.port == 8082
        assert b.host == "localhost"

    def test_custom_port_via_env(self):
        with patch.dict("os.environ", {"MYCELIUM_WS_PORT": "9999"}):
            import importlib
            import src.mcp.mycelium_ws_server as mod
            importlib.reload(mod)
            b = mod.MyceliumWSBroadcaster()
            assert b.port == 9999
            # Restore default
            with patch.dict("os.environ", {}, clear=True):
                importlib.reload(mod)

    def test_singleton_returns_same_instance(self):
        import src.mcp.mycelium_ws_server as mod
        mod._ws_broadcaster = None
        first = mod.get_ws_broadcaster()
        second = mod.get_ws_broadcaster()
        assert first is second
        mod._ws_broadcaster = None  # cleanup

    def test_broadcast_sends_json_to_all_clients(self):
        b = MyceliumWSBroadcaster()
        c1 = MagicMock()
        c1.send = AsyncMock()
        c2 = MagicMock()
        c2.send = AsyncMock()
        b.clients = {c1, c2}

        asyncio.run(b.broadcast({"type": "test", "value": 42}))

        c1.send.assert_called_once()
        c2.send.assert_called_once()
        payload = json.loads(c1.send.call_args[0][0])
        assert payload["type"] == "test"
        assert payload["value"] == 42
        assert b._messages_sent == 2

    def test_broadcast_removes_disconnected_clients(self):
        b = MyceliumWSBroadcaster()
        good = MagicMock()
        good.send = AsyncMock()
        bad = MagicMock()
        bad.send = AsyncMock(side_effect=ConnectionError("gone"))
        b.clients = {good, bad}

        asyncio.run(b.broadcast({"type": "ping"}))

        assert good in b.clients
        assert bad not in b.clients
        assert len(b.clients) == 1

    def test_broadcast_pipeline_activity_format(self):
        b = MyceliumWSBroadcaster()
        c = MagicMock()
        c.send = AsyncMock()
        b.clients = {c}

        asyncio.run(b.broadcast_pipeline_activity(
            role="@coder", message="Writing code", model="qwen3",
            subtask_idx=1, total=3, task_id="tb_001", preset="dragon_silver"
        ))

        payload = json.loads(c.send.call_args[0][0])
        assert payload["type"] == "pipeline_activity"
        assert payload["role"] == "@coder"
        assert payload["message"] == "Writing code"
        assert payload["model"] == "qwen3"
        assert payload["subtask_idx"] == 1
        assert payload["total"] == 3
        assert payload["task_id"] == "tb_001"
        assert payload["preset"] == "dragon_silver"
        assert "timestamp" in payload

    def test_broadcast_board_update_format(self):
        b = MyceliumWSBroadcaster()
        c = MagicMock()
        c.send = AsyncMock()
        b.clients = {c}
        task_data = {"id": "tb_002", "title": "Fix bug", "status": "done"}

        asyncio.run(b.broadcast_board_update(action="updated", task_data=task_data))

        payload = json.loads(c.send.call_args[0][0])
        assert payload["type"] == "task_board_updated"
        assert payload["action"] == "updated"
        assert payload["task"]["id"] == "tb_002"
        assert "timestamp" in payload

    def test_broadcast_pipeline_stats_format(self):
        b = MyceliumWSBroadcaster()
        c = MagicMock()
        c.send = AsyncMock()
        b.clients = {c}
        stats = {"llm_calls": 5, "tokens_in": 1200, "duration": 12.5}

        asyncio.run(b.broadcast_pipeline_stats(stats=stats))

        payload = json.loads(c.send.call_args[0][0])
        assert payload["type"] == "pipeline_stats"
        assert payload["stats"]["llm_calls"] == 5
        assert payload["stats"]["tokens_in"] == 1200
        assert "timestamp" in payload

    def test_get_status_returns_correct_dict(self):
        b = MyceliumWSBroadcaster()
        c = MagicMock()
        b.clients = {c}
        b._messages_sent = 42

        status = b.get_status()

        assert status["running"] is False  # _server is None
        assert status["host"] == "localhost"
        assert status["port"] == 8082
        assert status["clients"] == 1
        assert status["messages_sent"] == 42
        assert isinstance(status["uptime"], int)

    def test_handler_processes_ping_pong(self):
        b = MyceliumWSBroadcaster()
        ws = AsyncMock()
        # Simulate async iteration: one ping message, then StopAsyncIteration
        ping_msg = json.dumps({"type": "ping"})
        ws.__aiter__ = MagicMock(return_value=iter([ping_msg]))
        ws.send = AsyncMock()

        async def run():
            # Manually invoke handler logic for ping
            await b._handle_client_message({"type": "ping"}, ws)

        asyncio.run(run())

        ws.send.assert_called_once()
        pong = json.loads(ws.send.call_args[0][0])
        assert pong["type"] == "pong"
        assert "timestamp" in pong

    def test_broadcast_noop_when_no_clients(self):
        b = MyceliumWSBroadcaster()
        assert len(b.clients) == 0
        # Should return immediately without error
        asyncio.run(b.broadcast({"type": "test"}))
        assert b._messages_sent == 0

    def test_websockets_import_error_handled(self):
        """When websockets not installed, start() logs warning but doesn't crash."""
        b = MyceliumWSBroadcaster()

        async def run():
            with patch.dict("sys.modules", {"websockets": None}):
                with patch("builtins.__import__", side_effect=ImportError("no websockets")):
                    await b.start()

        asyncio.run(run())
        assert b._server is None
        assert b.is_running is False
