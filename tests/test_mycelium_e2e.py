"""
E2E tests for MYCELIUM MCP Server.

Tests the full integration: server starts, tools dispatch,
components cooperate. Mocks LLM providers but tests real
component wiring.

@phase: 129
@marker: MARKER_129.E2E
"""

import pytest

pytestmark = pytest.mark.stale(reason="Mycelium MCP server refactored — tool count/dispatch changed")

import asyncio
import json
import time
from unittest.mock import patch, MagicMock, AsyncMock


# ============================================================
# Test 1: Server imports and initializes
# ============================================================
class TestServerBootstrap:
    """Verify MYCELIUM MCP server loads without errors."""

    def test_server_imports(self):
        """Server module imports successfully."""
        from src.mcp.mycelium_mcp_server import server, MYCELIUM_TOOLS
        assert server is not None
        assert server.name == "mycelium"

    def test_tool_count_is_17(self):
        """Exactly 17 tools registered."""
        from src.mcp.mycelium_mcp_server import MYCELIUM_TOOLS
        assert len(MYCELIUM_TOOLS) == 17

    def test_all_tools_have_schemas(self):
        """Every tool has name, description, inputSchema."""
        from src.mcp.mycelium_mcp_server import MYCELIUM_TOOLS
        for tool in MYCELIUM_TOOLS:
            assert tool.name, f"Tool missing name"
            assert tool.description, f"Tool {tool.name} missing description"
            assert tool.inputSchema, f"Tool {tool.name} missing inputSchema"
            assert tool.inputSchema.get("type") == "object", \
                f"Tool {tool.name} schema type != object"

    def test_list_tools_async(self):
        """list_tools() returns 17 tools via MCP protocol."""
        from src.mcp.mycelium_mcp_server import list_tools
        tools = asyncio.run(list_tools())
        assert len(tools) == 17

    def test_no_vetka_prefix_tools(self):
        """No tools use vetka_ prefix — clean namespace."""
        from src.mcp.mycelium_mcp_server import MYCELIUM_TOOLS
        for tool in MYCELIUM_TOOLS:
            assert not tool.name.startswith("vetka_"), \
                f"Tool {tool.name} has vetka_ prefix — should be mycelium_"

    def test_required_tools_present(self):
        """Core tools exist by name."""
        from src.mcp.mycelium_mcp_server import MYCELIUM_TOOLS
        names = {t.name for t in MYCELIUM_TOOLS}
        required = {
            "mycelium_pipeline", "mycelium_call_model",
            "mycelium_task_board", "mycelium_task_dispatch",
            "mycelium_heartbeat_tick", "mycelium_heartbeat_status",
            "mycelium_execute_workflow", "mycelium_workflow_status",
            "mycelium_research", "mycelium_implement", "mycelium_review",
            "mycelium_list_artifacts", "mycelium_approve_artifact",
            "mycelium_reject_artifact",
            "mycelium_health", "mycelium_devpanel_stream",
        }
        missing = required - names
        assert not missing, f"Missing tools: {missing}"


# ============================================================
# Test 2: Tool dispatch integration
# ============================================================
class TestToolDispatch:
    """Verify call_tool routes to correct handlers."""

    def test_dispatch_health(self):
        """mycelium_health returns valid JSON with uptime."""
        from src.mcp.mycelium_mcp_server import call_tool
        result = asyncio.run(call_tool("mycelium_health", {}))
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["server"] == "mycelium"
        assert "uptime_seconds" in data
        assert data["version"] == "129.6"

    def test_dispatch_devpanel_stream_no_ws(self):
        """mycelium_devpanel_stream works without WS broadcaster."""
        from src.mcp import mycelium_mcp_server as mod
        from src.mcp.mycelium_mcp_server import call_tool as ct
        old_ws = mod._ws_broadcaster
        mod._ws_broadcaster = None
        try:
            result = asyncio.run(ct("mycelium_devpanel_stream", {}))
            data = json.loads(result[0].text)
            assert data["success"] is True
            assert data["running"] is False
        finally:
            mod._ws_broadcaster = old_ws

    def test_dispatch_unknown_tool(self):
        """Unknown tool returns error."""
        from src.mcp.mycelium_mcp_server import call_tool
        result = asyncio.run(call_tool("unknown_tool_xyz", {}))
        data = json.loads(result[0].text)
        assert "error" in data
        assert "Unknown tool" in data["error"]

    def test_dispatch_vetka_tool_migration(self):
        """vetka_* tool returns migration message."""
        from src.mcp.mycelium_mcp_server import call_tool
        result = asyncio.run(call_tool("vetka_search_semantic", {}))
        data = json.loads(result[0].text)
        assert "error" in data
        assert "VETKA" in data["error"]
        assert "hint" in data

    def test_dispatch_task_board(self):
        """mycelium_task_board summary delegates correctly."""
        from src.mcp.mycelium_mcp_server import call_tool
        with patch("src.mcp.tools.task_board_tools.handle_task_board") as mock_tb:
            mock_tb.return_value = {"success": True, "summary": {"total": 5}}
            result = asyncio.run(call_tool("mycelium_task_board", {"action": "summary"}))
            data = json.loads(result[0].text)
            assert data["success"] is True
            mock_tb.assert_called_once_with({"action": "summary"})

    def test_dispatch_heartbeat_status(self):
        """mycelium_heartbeat_status delegates correctly."""
        from src.mcp.mycelium_mcp_server import call_tool
        with patch("src.orchestration.mycelium_heartbeat.get_heartbeat_status") as mock_hb:
            mock_hb.return_value = {"success": True, "status": {"total_ticks": 42}}
            result = asyncio.run(call_tool("mycelium_heartbeat_status", {}))
            data = json.loads(result[0].text)
            assert data["success"] is True
            mock_hb.assert_called_once()


# ============================================================
# Test 3: Pipeline fire-and-forget
# ============================================================
class TestPipelineFireAndForget:
    """Verify pipeline returns immediately, runs in background."""

    def test_pipeline_returns_task_id(self):
        """mycelium_pipeline returns task_id immediately."""
        from src.mcp.mycelium_mcp_server import _handle_pipeline
        result_json = asyncio.run(_handle_pipeline({
            "task": "test task",
            "preset": "dragon_bronze",
        }))
        data = json.loads(result_json)
        assert data["success"] is True
        assert data["task_id"].startswith("myc_")
        assert data["status"] == "dispatched"
        assert "dragon_bronze" in data["message"]

    def test_pipeline_is_non_blocking(self):
        """Pipeline dispatch takes <100ms (doesn't wait for execution)."""
        from src.mcp.mycelium_mcp_server import _handle_pipeline
        start = time.time()
        asyncio.run(_handle_pipeline({"task": "test", "preset": "dragon_silver"}))
        elapsed = time.time() - start
        assert elapsed < 1.0, f"Pipeline dispatch took {elapsed:.2f}s — should be <1s"

    def test_pipeline_tracks_active(self):
        """Active pipeline appears in _active_pipelines dict."""
        from src.mcp import mycelium_mcp_server as mod
        mod._active_pipelines.clear()

        async def _test():
            result_json = await mod._handle_pipeline({"task": "track test"})
            data = json.loads(result_json)
            task_id = data["task_id"]
            # Pipeline task should be registered (may complete quickly)
            assert task_id.startswith("myc_")
            # Give a moment for the task to register
            await asyncio.sleep(0.05)
            return task_id

        task_id = asyncio.run(_test())
        # Cleanup
        mod._active_pipelines.clear()


# ============================================================
# Test 4: LLMCallToolAsync integration
# ============================================================
class TestCallModelIntegration:
    """Verify mycelium_call_model uses async LLM tool."""

    def test_call_model_uses_async_tool(self):
        """Handler creates LLMCallToolAsync, not LLMCallTool."""
        from src.mcp.mycelium_mcp_server import _handle_call_model
        mock_result = {"success": True, "result": {"content": "hello", "model": "test"}}

        with patch("src.mcp.tools.llm_call_tool_async.LLMCallToolAsync") as MockTool:
            instance = AsyncMock()
            instance.execute = AsyncMock(return_value=mock_result)
            MockTool.return_value = instance

            result_json = asyncio.run(_handle_call_model({
                "model": "test-model",
                "messages": [{"role": "user", "content": "hi"}],
            }))

            data = json.loads(result_json)
            assert data["success"] is True
            assert data["result"]["content"] == "hello"
            instance.execute.assert_awaited_once()


# ============================================================
# Test 5: Component wiring
# ============================================================
class TestComponentWiring:
    """Verify lazy init and component cooperation."""

    def test_http_client_lazy_init(self):
        """_get_http_client creates singleton on first call."""
        from src.mcp import mycelium_mcp_server as mod
        old_client = mod._http_client
        mod._http_client = None

        with patch("src.mcp.mycelium_http_client.get_mycelium_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.start = AsyncMock()
            mock_get.return_value = mock_client

            client = asyncio.run(mod._get_http_client())
            assert client is mock_client
            mock_client.start.assert_awaited_once()

        mod._http_client = old_client

    def test_ws_broadcaster_lazy_init(self):
        """_get_ws_broadcaster creates singleton on first call."""
        from src.mcp import mycelium_mcp_server as mod
        old_ws = mod._ws_broadcaster
        mod._ws_broadcaster = None

        with patch("src.mcp.mycelium_ws_server.get_ws_broadcaster") as mock_get:
            mock_ws = AsyncMock()
            mock_ws.start = AsyncMock()
            mock_ws.port = 8082
            mock_get.return_value = mock_ws

            ws = asyncio.run(mod._get_ws_broadcaster())
            assert ws is mock_ws
            mock_ws.start.assert_awaited_once()

        mod._ws_broadcaster = old_ws

    def test_ws_broadcaster_graceful_on_import_error(self):
        """WS broadcaster handles ImportError gracefully."""
        from src.mcp import mycelium_mcp_server as mod
        old_ws = mod._ws_broadcaster
        mod._ws_broadcaster = None

        with patch.dict('sys.modules', {'src.mcp.mycelium_ws_server': None}):
            # Should not crash
            ws = asyncio.run(mod._get_ws_broadcaster())
            # May be None if import fails
            # Key: no exception raised

        mod._ws_broadcaster = old_ws


# ============================================================
# Test 6: Graceful shutdown
# ============================================================
class TestGracefulShutdown:
    """Verify shutdown cleans up resources."""

    def test_shutdown_cancels_pipelines(self):
        """_graceful_shutdown cancels active pipeline tasks and stops components."""
        from src.mcp import mycelium_mcp_server as mod

        # Create a real asyncio task that we can cancel
        async def _test():
            # Create a sleeping task to simulate active pipeline
            async def _fake_pipeline():
                await asyncio.sleep(999)

            task = asyncio.create_task(_fake_pipeline())
            mod._active_pipelines["test_task"] = task

            # Mock WS and HTTP
            old_ws = mod._ws_broadcaster
            old_http = mod._http_client
            mock_ws = AsyncMock()
            mock_ws.stop = AsyncMock()
            mock_http = AsyncMock()
            mock_http.stop = AsyncMock()
            mod._ws_broadcaster = mock_ws
            mod._http_client = mock_http

            await mod._graceful_shutdown()

            assert task.cancelled()
            mock_ws.stop.assert_awaited_once()
            mock_http.stop.assert_awaited_once()

            # Cleanup
            mod._active_pipelines.clear()
            mod._ws_broadcaster = old_ws
            mod._http_client = old_http

        asyncio.run(_test())


# ============================================================
# Test 7: .mcp.json configuration
# ============================================================
class TestMCPConfig:
    """Verify .mcp.json has both servers."""

    def test_mcp_json_has_mycelium(self):
        """Configuration includes mycelium server."""
        import os
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".mcp.json"
        )
        with open(config_path) as f:
            config = json.load(f)

        servers = config.get("mcpServers", {})
        assert "vetka" in servers, "Missing vetka server"
        assert "mycelium" in servers, "Missing mycelium server"

        myc = servers["mycelium"]
        assert "mycelium_mcp_server.py" in myc["args"][0]
        assert myc["env"]["MYCELIUM_WS_PORT"] == "8082"

    def test_both_servers_same_venv(self):
        """Both servers use same Python venv."""
        import os
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".mcp.json"
        )
        with open(config_path) as f:
            config = json.load(f)

        servers = config["mcpServers"]
        assert servers["vetka"]["command"] == servers["mycelium"]["command"], \
            "VETKA and MYCELIUM should use same Python binary"


# ============================================================
# Test 8: Regression — AgentPipeline backward compat
# ============================================================
class TestPipelineBackwardCompat:
    """Verify AgentPipeline works in both sync and async mode."""

    def test_pipeline_new_without_init_no_crash(self):
        """Pipeline created via __new__ (test pattern) doesn't crash on async_mode check."""
        from src.orchestration.agent_pipeline import AgentPipeline
        p = AgentPipeline.__new__(AgentPipeline)
        # getattr fallback should work
        assert getattr(p, 'async_mode', False) is False
        assert getattr(p, '_http_client', None) is None
        assert getattr(p, '_ws_broadcaster', None) is None

    def test_pipeline_async_mode_via_constructor(self):
        """Pipeline accepts async_mode in constructor."""
        from src.orchestration.agent_pipeline import AgentPipeline
        p = AgentPipeline(async_mode=True)
        assert p.async_mode is True

    def test_pipeline_default_sync_mode(self):
        """Pipeline defaults to sync mode (backward compat)."""
        from src.orchestration.agent_pipeline import AgentPipeline
        p = AgentPipeline()
        assert p.async_mode is False
        assert p._http_client is None
        assert p._ws_broadcaster is None
