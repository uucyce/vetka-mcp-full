"""
Phase 109.1 Tests - Dynamic MCP Context Injection

Tests for:
- ViewportDetailTool
- PinnedFilesTool
- ContextDAGTool
- SessionInitTool viewport/pinned integration
- emit_context_update Socket.IO helpers

@status: active
@phase: 109.1
"""

import pytest
import asyncio


class TestViewportDetailTool:
    """Tests for vetka_get_viewport_detail MCP tool."""

    def test_tool_name(self):
        from src.mcp.tools.viewport_tool import ViewportDetailTool
        tool = ViewportDetailTool()
        assert tool.name == "vetka_get_viewport_detail"

    def test_schema_has_session_id(self):
        from src.mcp.tools.viewport_tool import ViewportDetailTool
        tool = ViewportDetailTool()
        assert "session_id" in tool.schema["properties"]

    def test_schema_has_include_stats(self):
        from src.mcp.tools.viewport_tool import ViewportDetailTool
        tool = ViewportDetailTool()
        assert "include_stats" in tool.schema["properties"]

    def test_execute_returns_success(self):
        from src.mcp.tools.viewport_tool import ViewportDetailTool
        tool = ViewportDetailTool()
        result = tool.execute({})
        assert result["success"] == True

    def test_result_has_viewport_key(self):
        from src.mcp.tools.viewport_tool import ViewportDetailTool
        tool = ViewportDetailTool()
        result = tool.execute({})
        assert "viewport" in result["result"]

    def test_result_has_summary(self):
        from src.mcp.tools.viewport_tool import ViewportDetailTool
        tool = ViewportDetailTool()
        result = tool.execute({})
        assert "summary" in result["result"]
        assert "[→ viewport]" in result["result"]["summary"]


class TestPinnedFilesTool:
    """Tests for vetka_get_pinned_files MCP tool."""

    def test_tool_name(self):
        from src.mcp.tools.pinned_files_tool import PinnedFilesTool
        tool = PinnedFilesTool()
        assert tool.name == "vetka_get_pinned_files"

    def test_schema_has_include_content(self):
        from src.mcp.tools.pinned_files_tool import PinnedFilesTool
        tool = PinnedFilesTool()
        assert "include_content" in tool.schema["properties"]

    def test_execute_returns_success(self):
        from src.mcp.tools.pinned_files_tool import PinnedFilesTool
        tool = PinnedFilesTool()
        result = tool.execute({})
        assert result["success"] == True

    def test_result_has_pinned_files_list(self):
        from src.mcp.tools.pinned_files_tool import PinnedFilesTool
        tool = PinnedFilesTool()
        result = tool.execute({})
        assert "pinned_files" in result["result"]
        assert isinstance(result["result"]["pinned_files"], list)

    def test_result_has_count(self):
        from src.mcp.tools.pinned_files_tool import PinnedFilesTool
        tool = PinnedFilesTool()
        result = tool.execute({})
        assert "count" in result["result"]


class TestContextDAGTool:
    """Tests for vetka_get_context_dag MCP tool."""

    def test_tool_name(self):
        from src.mcp.tools.context_dag_tool import ContextDAGTool
        tool = ContextDAGTool()
        assert tool.name == "vetka_get_context_dag"

    def test_schema_requires_session_id(self):
        from src.mcp.tools.context_dag_tool import ContextDAGTool
        tool = ContextDAGTool()
        assert "session_id" in tool.schema["properties"]
        assert "session_id" in tool.schema.get("required", [])

    def test_schema_has_max_tokens(self):
        from src.mcp.tools.context_dag_tool import ContextDAGTool
        tool = ContextDAGTool()
        assert "max_tokens" in tool.schema["properties"]
        assert tool.schema["properties"]["max_tokens"]["default"] == 500

    def test_execute_returns_success(self):
        from src.mcp.tools.context_dag_tool import ContextDAGTool
        tool = ContextDAGTool()
        result = tool.execute({"session_id": "test_session"})
        assert result["success"] == True

    def test_result_has_context_dag(self):
        from src.mcp.tools.context_dag_tool import ContextDAGTool
        tool = ContextDAGTool()
        result = tool.execute({"session_id": "test_session"})
        assert "context_dag" in result["result"]

    def test_result_has_hyperlinks(self):
        from src.mcp.tools.context_dag_tool import ContextDAGTool
        tool = ContextDAGTool()
        result = tool.execute({"session_id": "test_session"})
        assert "hyperlinks" in result["result"]

    def test_hyperlinks_map_to_tools(self):
        from src.mcp.tools.context_dag_tool import ContextDAGTool
        tool = ContextDAGTool()
        result = tool.execute({"session_id": "test_session"})
        hyperlinks = result["result"]["hyperlinks"]
        assert "viewport" in hyperlinks
        assert hyperlinks["viewport"] == "vetka_get_viewport_detail"
        assert "pins" in hyperlinks
        assert hyperlinks["pins"] == "vetka_get_pinned_files"

    def test_result_has_tokens_estimate(self):
        from src.mcp.tools.context_dag_tool import ContextDAGTool
        tool = ContextDAGTool()
        result = tool.execute({"session_id": "test_session"})
        assert "tokens_estimate" in result["result"]


class TestSessionInitToolIntegration:
    """Tests for session_tools.py viewport/pinned integration."""

    def test_schema_has_include_viewport(self):
        from src.mcp.tools.session_tools import SessionInitTool
        tool = SessionInitTool()
        assert "include_viewport" in tool.schema["properties"]
        assert tool.schema["properties"]["include_viewport"]["default"] == True

    def test_schema_has_include_pinned(self):
        from src.mcp.tools.session_tools import SessionInitTool
        tool = SessionInitTool()
        assert "include_pinned" in tool.schema["properties"]
        assert tool.schema["properties"]["include_pinned"]["default"] == True


class TestActivityEmitterContextUpdate:
    """Tests for emit_context_update Socket.IO helpers."""

    def test_get_context_hyperlink_viewport(self):
        from src.services.activity_emitter import _get_context_hyperlink
        assert _get_context_hyperlink("viewport") == "vetka_get_viewport_detail"

    def test_get_context_hyperlink_pins(self):
        from src.services.activity_emitter import _get_context_hyperlink
        assert _get_context_hyperlink("pins") == "vetka_get_pinned_files"

    def test_get_context_hyperlink_chat(self):
        from src.services.activity_emitter import _get_context_hyperlink
        assert _get_context_hyperlink("chat") == "vetka_get_chat_digest"

    def test_get_context_hyperlink_cam(self):
        from src.services.activity_emitter import _get_context_hyperlink
        assert _get_context_hyperlink("cam") == "vetka_get_memory_summary"

    def test_get_context_hyperlink_prefs(self):
        from src.services.activity_emitter import _get_context_hyperlink
        assert _get_context_hyperlink("prefs") == "vetka_get_user_preferences"

    def test_get_context_hyperlink_unknown_type(self):
        from src.services.activity_emitter import _get_context_hyperlink
        # Should return vetka_get_{type} for unknown types
        assert _get_context_hyperlink("custom") == "vetka_get_custom"


class TestMarkers:
    """Verify all Phase 109 markers are present."""

    def test_marker_109_1_in_session_tools(self):
        import src.mcp.tools.session_tools as st
        assert "MARKER_109_1_VIEWPORT_INJECT" in st.__doc__

    def test_marker_109_2_in_viewport_tool(self):
        import src.mcp.tools.viewport_tool as vt
        assert "MARKER_109_2_VIEWPORT_TOOL" in vt.__doc__

    def test_marker_109_2_in_pinned_tool(self):
        import src.mcp.tools.pinned_files_tool as pt
        assert "MARKER_109_2_PINNED_TOOL" in pt.__doc__

    def test_marker_109_3_in_context_dag_tool(self):
        import src.mcp.tools.context_dag_tool as ct
        assert "MARKER_109_3_CONTEXT_DAG" in ct.__doc__

    def test_marker_109_4_in_activity_emitter(self):
        import src.services.activity_emitter as ae
        assert "MARKER_109_4_REALTIME_CONTEXT" in ae.__doc__
