"""Phase 117.2a — Dragon/Mycelium Streaming Bug Fix Tests

Tests for Phase 117.2a fixes:
- MARKER_117_2A_FIX_A: Correct endpoint URL in agent_pipeline._emit_progress()
- MARKER_117_2A_FIX_B: Capture pipeline.execute() result in MCP bridge
- MARKER_117_2A_FIX_C: HTTP fallback in llm_call_tool._emit_to_chat()
- MARKER_117_2A_FIX_D: Emit Architect/Researcher/Coder results to chat
- KNOWN_AGENTS: "pipeline" agent registered in debug_routes.py

Root cause: Pipeline POST'd to /api/chat/send (doesn't exist), all messages lost.
Fix: POST to /api/debug/mcp/groups/{chat_id}/send (real endpoint with SocketIO broadcast).

@status: active
@phase: 117.2a
@depends: src/orchestration/agent_pipeline.py, src/mcp/vetka_mcp_bridge.py,
          src/mcp/tools/llm_call_tool.py, src/api/routes/debug_routes.py
"""

import pytest
import json
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from dataclasses import asdict

from src.orchestration.agent_pipeline import AgentPipeline


# ═══════════════════════════════════════════════════════════════════════
# 1. FIX-A: Correct Endpoint URL Tests
# ═══════════════════════════════════════════════════════════════════════

class TestFixA_CorrectEndpoint:
    """Test that _emit_progress() uses the correct endpoint URL (MARKER_117_2A_FIX_A)"""

    @pytest.mark.asyncio
    async def test_emit_progress_uses_correct_url(self):
        """_emit_progress should POST to /api/debug/mcp/groups/{chat_id}/send"""
        pipeline = AgentPipeline(chat_id="test-group-123")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response

            await pipeline._emit_progress("@architect", "Test message")

            # Verify correct URL used
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")

            assert "/api/debug/mcp/groups/test-group-123/send" in url
            assert "/api/chat/send" not in url  # Old broken URL must NOT be used

    @pytest.mark.asyncio
    async def test_emit_progress_sends_correct_body(self):
        """_emit_progress should send agent_id, content, message_type (not group_id/sender_id)"""
        pipeline = AgentPipeline(chat_id="test-group-123")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response

            await pipeline._emit_progress("@coder", "Building feature", 2, 5)

            call_args = mock_client.post.call_args
            body = call_args[1].get("json", call_args[0][1] if len(call_args[0]) > 1 else {})

            # New format: agent_id (not sender_id), no group_id in body
            assert body.get("agent_id") == "pipeline"
            assert body.get("message_type") == "system"
            assert "@coder" in body.get("content", "")
            assert "[2/5]" in body.get("content", "")
            # Old format fields must NOT be present
            assert "sender_id" not in body
            assert "group_id" not in body

    @pytest.mark.asyncio
    async def test_emit_progress_does_not_crash_on_failure(self):
        """_emit_progress should not raise even if HTTP fails"""
        pipeline = AgentPipeline(chat_id="test-group-123")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.side_effect = Exception("Connection refused")

            # Should not raise
            await pipeline._emit_progress("@pipeline", "Test message")

    @pytest.mark.asyncio
    async def test_emit_progress_calls_hooks_when_no_emit_target(self):
        """Hooks are called on fallback path (no sio/sid and no chat_id)."""
        pipeline = AgentPipeline(chat_id=None)
        hook_called = []
        pipeline.progress_hooks.append(lambda role, msg, idx, total: hook_called.append((role, msg)))

        await pipeline._emit_progress("@coder", "Executing")

        assert len(hook_called) == 1
        assert hook_called[0] == ("@coder", "Executing")


# ═══════════════════════════════════════════════════════════════════════
# 2. FIX-A (Part 2): _emit_to_chat correct endpoint
# ═══════════════════════════════════════════════════════════════════════

class TestFixA_EmitToChat:
    """Test that _emit_to_chat() uses correct endpoint (MARKER_117_2A_FIX_A)"""

    @pytest.mark.asyncio
    async def test_emit_to_chat_uses_correct_url(self):
        """_emit_to_chat should POST to /api/debug/mcp/groups/{chat_id}/send"""
        pipeline = AgentPipeline(chat_id="test-group-456")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await pipeline._emit_to_chat("subtask_completed", {"result": "test"})

            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")

            assert "/api/debug/mcp/groups/test-group-456/send" in url
            assert "/api/stream/event" not in url  # Old broken URL

    @pytest.mark.asyncio
    async def test_emit_to_chat_does_not_crash(self):
        """_emit_to_chat should not raise on failure"""
        pipeline = AgentPipeline(chat_id="test-group-456")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.side_effect = Exception("Connection refused")

            # Should not raise
            await pipeline._emit_to_chat("test_event", {"key": "value"})


# ═══════════════════════════════════════════════════════════════════════
# 3. FIX-B: MCP Bridge Result Capture Tests
# ═══════════════════════════════════════════════════════════════════════

class TestFixB_MCPBridgeResultCapture:
    """Phase 129+: vetka bridge delegates pipeline tools to MCP MYCELIUM."""

    def test_bridge_pipeline_tool_is_deprecated_stub(self):
        """vetka_mycelium_pipeline should be present as deprecation notice."""
        bridge_path = Path("src/mcp/vetka_mcp_bridge.py")
        content = bridge_path.read_text()

        assert "DEPRECATED: vetka_mycelium_pipeline moved to MCP MYCELIUM" in content
        assert "Use mycelium_pipeline instead" in content

    def test_bridge_code_has_completion_notification(self):
        """Verify the MCP bridge sends completion notification to group chat"""
        bridge_path = Path("src/mcp/vetka_mcp_bridge.py")
        content = bridge_path.read_text()

        # Must have POST to correct endpoint for notification
        assert "/api/debug/mcp/groups/" in content, \
            "MCP bridge must POST completion notification to group endpoint"

    def test_bridge_code_has_failure_notification(self):
        """Verify the MCP bridge sends failure notification on error"""
        bridge_path = Path("src/mcp/vetka_mcp_bridge.py")
        content = bridge_path.read_text()

        # Must have error notification with ❌ marker
        assert "Pipeline" in content and "failed" in content, \
            "MCP bridge must notify on pipeline failure"


# ═══════════════════════════════════════════════════════════════════════
# 4. FIX-C: LLMCallTool HTTP Fallback Tests
# ═══════════════════════════════════════════════════════════════════════

class TestFixC_LLMCallToolFallback:
    """Test HTTP fallback in llm_call_tool._emit_to_chat() (MARKER_117_2A_FIX_C)"""

    def test_llm_call_tool_has_http_fallback(self):
        """Verify llm_call_tool has HTTP fallback when SocketIO fails"""
        tool_path = Path("src/mcp/tools/llm_call_tool.py")
        content = tool_path.read_text()

        # Must have HTTP fallback code
        assert "HTTP fallback" in content or "http_fallback" in content or "httpx" in content, \
            "llm_call_tool must have HTTP fallback for SocketIO failures"

        # Must use warning level (not debug) for SocketIO failures
        assert "logger.warning" in content, \
            "llm_call_tool must log SocketIO failures at warning level"

    def test_llm_call_tool_uses_correct_fallback_endpoint(self):
        """Verify HTTP fallback uses /api/debug/mcp/groups/{id}/send"""
        tool_path = Path("src/mcp/tools/llm_call_tool.py")
        content = tool_path.read_text()

        assert "/api/debug/mcp/groups/" in content, \
            "HTTP fallback must use /api/debug/mcp/groups/{id}/send endpoint"


# ═══════════════════════════════════════════════════════════════════════
# 5. FIX-D: Architect/Researcher/Coder Emission Tests
# ═══════════════════════════════════════════════════════════════════════

class TestFixD_AllPhasesEmitted:
    """Test that all pipeline phases emit results to chat (MARKER_117_2A_FIX_D)"""

    def test_architect_plan_emitted(self):
        """Verify execute() emits architect plan details after planning"""
        pipeline_path = Path("src/orchestration/agent_pipeline.py")
        content = pipeline_path.read_text()

        # Must have plan emission after architect
        assert "📋 Plan:" in content or "Plan:" in content, \
            "Pipeline must emit architect plan details to chat"

    def test_research_results_emitted_sequential(self):
        """Verify sequential execution emits research results"""
        pipeline_path = Path("src/orchestration/agent_pipeline.py")
        content = pipeline_path.read_text()

        # Must have research emission in sequential path
        assert "Research done" in content, \
            "Pipeline must emit research results in sequential execution"

    def test_research_results_emitted_parallel(self):
        """Verify parallel execution emits research results"""
        pipeline_path = Path("src/orchestration/agent_pipeline.py")
        content = pipeline_path.read_text()

        # Must have research emission in parallel path with [P] marker
        assert "[P] Research done" in content, \
            "Pipeline must emit research results in parallel execution"

    def test_coder_results_emitted_sequential(self):
        """Verify sequential execution emits coder results"""
        pipeline_path = Path("src/orchestration/agent_pipeline.py")
        content = pipeline_path.read_text()

        assert "💻 Result:" in content, \
            "Pipeline must emit coder result preview in sequential execution"

    def test_coder_results_emitted_parallel(self):
        """Verify parallel execution emits coder results"""
        pipeline_path = Path("src/orchestration/agent_pipeline.py")
        content = pipeline_path.read_text()

        assert "💻 [P] Result:" in content, \
            "Pipeline must emit coder result preview in parallel execution"


# ═══════════════════════════════════════════════════════════════════════
# 6. KNOWN_AGENTS: Pipeline Agent Registration
# ═══════════════════════════════════════════════════════════════════════

class TestKnownAgentsPipeline:
    """Test that 'pipeline' agent is registered in KNOWN_AGENTS"""

    def test_pipeline_in_known_agents(self):
        """'pipeline' must be in KNOWN_AGENTS dict"""
        from src.api.routes.debug_routes import KNOWN_AGENTS

        assert "pipeline" in KNOWN_AGENTS, \
            "'pipeline' must be registered in KNOWN_AGENTS"

    def test_pipeline_has_required_fields(self):
        """Pipeline agent entry must have name, icon, role"""
        from src.api.routes.debug_routes import KNOWN_AGENTS

        pipeline_info = KNOWN_AGENTS["pipeline"]
        assert "name" in pipeline_info
        assert "icon" in pipeline_info
        assert "role" in pipeline_info
        assert pipeline_info["role"] == "Pipeline"


# ═══════════════════════════════════════════════════════════════════════
# 7. Integration: No Old Broken URLs Remain
# ═══════════════════════════════════════════════════════════════════════

class TestNoOldBrokenURLs:
    """Ensure no code still uses the old broken endpoints"""

    def test_no_api_chat_send_in_pipeline(self):
        """agent_pipeline.py must NOT contain /api/chat/send"""
        pipeline_path = Path("src/orchestration/agent_pipeline.py")
        content = pipeline_path.read_text()

        # Filter out comments
        code_lines = [
            line for line in content.split('\n')
            if not line.strip().startswith('#') and not line.strip().startswith('//')
        ]
        code_only = '\n'.join(code_lines)

        assert "/api/chat/send" not in code_only, \
            "Old broken URL /api/chat/send must not be in active code"

    def test_no_api_stream_event_in_pipeline(self):
        """agent_pipeline.py must NOT use /api/stream/event in actual HTTP calls"""
        pipeline_path = Path("src/orchestration/agent_pipeline.py")
        content = pipeline_path.read_text()

        # Filter out comments, docstrings, and lines referencing "Old:" patterns
        code_lines = [
            line for line in content.split('\n')
            if not line.strip().startswith('#')
            and not line.strip().startswith('//')
            and not line.strip().startswith('Old:')
            and not line.strip().startswith('"""')
            and 'Old:' not in line
        ]
        code_only = '\n'.join(code_lines)

        assert "/api/stream/event" not in code_only, \
            "Old broken URL /api/stream/event must not be in active code"

    def test_correct_url_pattern_in_pipeline(self):
        """agent_pipeline.py must use /api/debug/mcp/groups/ pattern"""
        pipeline_path = Path("src/orchestration/agent_pipeline.py")
        content = pipeline_path.read_text()

        assert "/api/debug/mcp/groups/" in content, \
            "Pipeline must use correct /api/debug/mcp/groups/{id}/send endpoint"
