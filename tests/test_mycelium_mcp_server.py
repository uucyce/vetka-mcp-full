"""Tests for MYCELIUM MCP Server (MARKER_129.6).

Covers: list_tools, call_tool dispatch, migration messages, handler delegation.
"""
import pytest
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock


# Import server components directly (no heavy deps needed for these)
import sys
sys.path.insert(0, "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


class TestMyceliumMCPServer:
    """Tests for MYCELIUM MCP Server (MARKER_129.6)."""

    def _import_server(self):
        """Lazy import to avoid import-time side effects."""
        from src.mcp.mycelium_mcp_server import (
            MYCELIUM_TOOLS, list_tools, call_tool,
            _handle_health, _handle_pipeline, _handle_devpanel_stream,
            _TOOL_DISPATCH,
        )
        return MYCELIUM_TOOLS, list_tools, call_tool, _handle_health, _handle_pipeline, _handle_devpanel_stream, _TOOL_DISPATCH

    # --- 1. list_tools returns baseline set including task board ---
    def test_list_tools_returns_baseline_set(self):
        TOOLS, list_tools_fn, *_ = self._import_server()
        result = asyncio.run(list_tools_fn())
        names = {tool.name for tool in result}
        assert len(result) >= 17, f"Expected at least 17 tools, got {len(result)}"
        assert "mycelium_task_board" in names

    # --- 2. All tool names start with mycelium_ ---
    def test_all_tools_prefixed_mycelium(self):
        TOOLS, *_ = self._import_server()
        for tool in TOOLS:
            assert tool.name.startswith("mycelium_"), f"Tool '{tool.name}' missing mycelium_ prefix"

    # --- 3. call_tool dispatches to correct handler ---
    def test_call_tool_dispatches_correctly(self):
        _, _, call_tool_fn, _, _, _, DISPATCH = self._import_server()
        mock_handler = AsyncMock(return_value='{"ok": true}')
        with patch.dict(DISPATCH, {"mycelium_health": mock_handler}):
            result = asyncio.run(call_tool_fn("mycelium_health", {}))
        mock_handler.assert_awaited_once_with({})
        assert result[0].text == '{"ok": true}'

    # --- 4. call_tool returns error for unknown tool ---
    def test_call_tool_unknown_tool(self):
        _, _, call_tool_fn, *_ = self._import_server()
        result = asyncio.run(call_tool_fn("nonexistent_tool", {}))
        data = json.loads(result[0].text)
        assert "error" in data
        assert "Unknown tool" in data["error"]

    # --- 5. call_tool returns migration message for vetka_* tools ---
    def test_call_tool_vetka_migration(self):
        _, _, call_tool_fn, *_ = self._import_server()
        result = asyncio.run(call_tool_fn("vetka_search_semantic", {}))
        data = json.loads(result[0].text)
        assert "error" in data
        assert "MCP VETKA server" in data["error"]
        assert "hint" in data

    # --- 6. _handle_health returns correct structure ---
    def test_handle_health_structure(self):
        from src.mcp import mycelium_mcp_server as mod
        mock_http = AsyncMock()
        mock_http.check_vetka_health = AsyncMock(return_value=True)
        mock_ws = MagicMock()
        mock_ws.get_status.return_value = {"clients": 2, "port": 8082}

        old_http, old_ws = mod._http_client, mod._ws_broadcaster
        mod._http_client = mock_http
        mod._ws_broadcaster = mock_ws
        try:
            with patch.object(mod, '_get_http_client', new=AsyncMock(return_value=mock_http)):
                raw = asyncio.run(mod._handle_health({}))
            data = json.loads(raw)
            assert data["success"] is True
            assert data["server"] == "mycelium"
            assert "uptime_seconds" in data
            assert data["vetka_connected"] is True
            assert data["websocket"] == {"clients": 2, "port": 8082}
        finally:
            mod._http_client, mod._ws_broadcaster = old_http, old_ws

    # --- 7. _handle_pipeline returns immediately with task_id ---
    def test_handle_pipeline_fire_and_forget(self):
        from src.mcp import mycelium_mcp_server as mod
        raw = asyncio.run(mod._handle_pipeline({"task": "test task", "preset": "dragon_bronze"}))
        data = json.loads(raw)
        assert data["success"] is True
        assert data["task_id"].startswith("myc_")
        assert data["status"] == "dispatched"
        assert len(data["task_id"]) == 12  # "myc_" + 8 hex chars

    # --- 8. _handle_call_model delegates to LLMCallToolAsync ---
    def test_handle_call_model_delegates(self):
        mock_tool = AsyncMock()
        mock_tool.execute = AsyncMock(return_value={"result": {"content": "hello"}})
        with patch("src.mcp.tools.llm_call_tool_async.LLMCallToolAsync", return_value=mock_tool):
            from src.mcp.mycelium_mcp_server import _handle_call_model
            raw = asyncio.run(_handle_call_model({"model": "grok-4", "messages": []}))
        data = json.loads(raw)
        assert data["result"]["content"] == "hello"
        mock_tool.execute.assert_awaited_once()

    # --- 9. _handle_task_board delegates to handle_task_board ---
    def test_handle_task_board_delegates(self):
        mock_fn = MagicMock(return_value={"tasks": [], "total": 0})
        with patch("src.mcp.tools.task_board_tools.handle_task_board", mock_fn):
            from src.mcp.mycelium_mcp_server import _handle_task_board
            raw = asyncio.run(_handle_task_board({"action": "list"}))
        data = json.loads(raw)
        assert data["total"] == 0
        mock_fn.assert_called_once_with({"action": "list"})

    # --- 10. _handle_devpanel_stream when no broadcaster ---
    def test_handle_devpanel_stream_no_broadcaster(self):
        from src.mcp import mycelium_mcp_server as mod
        old_ws = mod._ws_broadcaster
        mod._ws_broadcaster = None
        try:
            raw = asyncio.run(mod._handle_devpanel_stream({}))
            data = json.loads(raw)
            assert data["success"] is True
            assert data["running"] is False
        finally:
            mod._ws_broadcaster = old_ws
