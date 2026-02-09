"""Tests for AgentPipeline async_mode (MARKER_129.4).

Covers: constructor params, backward compat, _get_llm_tool dispatch,
_emit_progress with ws_broadcaster and http_client.
"""
import pytest
import json
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock

import sys
sys.path.insert(0, "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _make_pipeline(**kwargs):
    """Create AgentPipeline with heavy deps mocked out."""
    defaults = dict(chat_id="test", auto_write=False, preset="dragon_bronze")
    defaults.update(kwargs)
    with patch.dict('sys.modules', {
        'src.initialization.singletons': MagicMock(),
        'src.initialization': MagicMock(),
    }):
        from src.orchestration.agent_pipeline import AgentPipeline
        return AgentPipeline(**defaults)


class TestAgentPipelineAsyncMode:
    """Tests for AgentPipeline async_mode + MYCELIUM integration (MARKER_129.4)."""

    # --- 1. Constructor accepts async_mode, http_client, ws_broadcaster ---
    def test_constructor_accepts_async_params(self):
        mock_http = MagicMock()
        mock_ws = MagicMock()
        p = _make_pipeline(async_mode=True, http_client=mock_http, ws_broadcaster=mock_ws)
        assert p.async_mode is True
        assert p._http_client is mock_http
        assert p._ws_broadcaster is mock_ws

    # --- 2. async_mode=False is default (backward compat) ---
    def test_async_mode_default_false(self):
        p = _make_pipeline()
        assert p.async_mode is False
        assert p._http_client is None
        assert p._ws_broadcaster is None

    # --- 3. _get_llm_tool returns LLMCallTool when async_mode=False ---
    def test_get_llm_tool_sync(self):
        p = _make_pipeline(async_mode=False)
        mock_sync = MagicMock()
        with patch("src.mcp.tools.llm_call_tool.LLMCallTool", return_value=mock_sync):
            p._get_llm_tool()
        assert p.llm_tool is mock_sync

    # --- 4. _get_llm_tool returns LLMCallToolAsync when async_mode=True ---
    def test_get_llm_tool_async(self):
        p = _make_pipeline(async_mode=True)
        mock_async = MagicMock()
        with patch("src.mcp.tools.llm_call_tool_async.LLMCallToolAsync", return_value=mock_async):
            p._get_llm_tool()
        assert p.llm_tool is mock_async

    # --- 5. _emit_progress uses ws_broadcaster (MARKER_129.4A) ---
    def test_emit_progress_ws_broadcaster(self):
        mock_ws = AsyncMock()
        mock_ws.broadcast = AsyncMock()
        p = _make_pipeline(async_mode=True, ws_broadcaster=mock_ws)
        asyncio.run(p._emit_progress("@coder", "Building...", subtask_idx=1, total=3, model="qwen3"))
        mock_ws.broadcast.assert_awaited_once()
        call_data = mock_ws.broadcast.call_args[0][0]
        assert call_data["type"] == "pipeline_activity"
        assert call_data["role"] == "@coder"
        assert call_data["message"] == "Building..."

    # --- 6. _emit_progress uses http_client (MARKER_129.4B) ---
    def test_emit_progress_http_client(self):
        mock_http = AsyncMock()
        mock_http.emit_pipeline_progress = AsyncMock()
        p = _make_pipeline(async_mode=True, http_client=mock_http)
        p.chat_id = "chat_123"
        asyncio.run(p._emit_progress("@architect", "Planning...", subtask_idx=2, total=5, model="kimi"))
        mock_http.emit_pipeline_progress.assert_awaited_once()
        args = mock_http.emit_pipeline_progress.call_args
        assert args[0][0] == "chat_123"  # chat_id
        assert args[0][1] == "@architect"  # role
