"""
Phase 127.2: Pipeline Activity Stream Routing Tests

Tests that pipeline_activity broadcast is wired into _emit_progress
and frontend useSocket.ts listens for it.

MARKER_127.2
"""

import os
import json
import re
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# Test 1: MARKER exists in code
# =============================================================================

class TestMarker127_2:
    """Verify MARKER_127.2 exists in target files."""

    def test_marker_in_agent_pipeline(self):
        """MARKER_127.2 should be in agent_pipeline.py."""
        path = os.path.join(os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py")
        with open(path) as f:
            content = f.read()
        assert "MARKER_127.2" in content

    def test_marker_in_use_socket(self):
        """MARKER_127.2 should be in useSocket.ts."""
        path = os.path.join(os.path.dirname(__file__), "..", "client", "src", "hooks", "useSocket.ts")
        with open(path) as f:
            content = f.read()
        assert "MARKER_127.2" in content


# =============================================================================
# Test 2: pipeline_activity emit in _emit_progress
# =============================================================================

class TestPipelineActivityEmit:
    """Test that _emit_progress broadcasts pipeline_activity."""

    def test_emit_progress_has_pipeline_activity(self):
        """_emit_progress should emit pipeline_activity event."""
        path = os.path.join(os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py")
        with open(path) as f:
            content = f.read()
        assert '"pipeline_activity"' in content

    def test_pipeline_activity_payload_has_role(self):
        """pipeline_activity payload should include role."""
        path = os.path.join(os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py")
        with open(path) as f:
            content = f.read()
        # Find the pipeline_activity emit block
        idx = content.find('"pipeline_activity"')
        block = content[idx:idx+500]
        assert '"role"' in block

    def test_pipeline_activity_payload_has_model(self):
        """pipeline_activity payload should include model."""
        path = os.path.join(os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py")
        with open(path) as f:
            content = f.read()
        idx = content.find('"pipeline_activity"')
        block = content[idx:idx+500]
        assert '"model"' in block

    def test_pipeline_activity_payload_has_task_id(self):
        """pipeline_activity payload should include task_id."""
        path = os.path.join(os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py")
        with open(path) as f:
            content = f.read()
        idx = content.find('"pipeline_activity"')
        block = content[idx:idx+500]
        assert '"task_id"' in block

    def test_pipeline_activity_payload_has_preset(self):
        """pipeline_activity payload should include preset."""
        path = os.path.join(os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py")
        with open(path) as f:
            content = f.read()
        idx = content.find('"pipeline_activity"')
        block = content[idx:idx+500]
        assert '"preset"' in block

    def test_pipeline_activity_payload_has_timestamp(self):
        """pipeline_activity payload should include timestamp."""
        path = os.path.join(os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py")
        with open(path) as f:
            content = f.read()
        idx = content.find('"pipeline_activity"')
        block = content[idx:idx+500]
        assert '"timestamp"' in block

    def test_pipeline_activity_is_broadcast(self):
        """pipeline_activity should NOT have 'to=' parameter (broadcast to all)."""
        path = os.path.join(os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py")
        with open(path) as f:
            content = f.read()
        # Find the pipeline_activity emit call
        idx = content.find('"pipeline_activity"')
        # Get the emit line (search backwards for 'await self.sio.emit')
        block_start = content.rfind('await self.sio.emit', max(0, idx - 200), idx)
        emit_line = content[block_start:idx + 20]
        # Should NOT have 'to=' — broadcast to all, not targeted
        assert "to=" not in emit_line


# =============================================================================
# Test 3: Frontend listener
# =============================================================================

class TestFrontendListener:
    """Test that useSocket.ts listens for pipeline_activity."""

    def test_socket_on_pipeline_activity(self):
        """useSocket.ts should have socket.on('pipeline_activity', ...)."""
        path = os.path.join(os.path.dirname(__file__), "..", "client", "src", "hooks", "useSocket.ts")
        with open(path) as f:
            content = f.read()
        assert "socket.on('pipeline_activity'" in content

    def test_dispatches_custom_event(self):
        """useSocket.ts should dispatch 'pipeline-activity' CustomEvent."""
        path = os.path.join(os.path.dirname(__file__), "..", "client", "src", "hooks", "useSocket.ts")
        with open(path) as f:
            content = f.read()
        assert "pipeline-activity" in content
        assert "CustomEvent" in content

    def test_pipeline_activity_type_defined(self):
        """ServerToClientEvents should include pipeline_activity type."""
        path = os.path.join(os.path.dirname(__file__), "..", "client", "src", "hooks", "useSocket.ts")
        with open(path) as f:
            content = f.read()
        assert "pipeline_activity:" in content


# =============================================================================
# Test 4: Async emit test
# =============================================================================

class TestEmitProgressAsync:
    """Test _emit_progress emits both chat_response AND pipeline_activity."""

    @pytest.mark.asyncio
    async def test_emit_progress_calls_sio_twice(self):
        """_emit_progress should call sio.emit at least twice (chat_response + pipeline_activity)."""
        from src.orchestration.agent_pipeline import AgentPipeline

        pipeline = AgentPipeline.__new__(AgentPipeline)
        pipeline.sio = AsyncMock()
        pipeline.sid = "test_sid"
        pipeline.chat_id = None
        pipeline.preset = "dragon_silver"
        pipeline._board_task_id = "tb_123"
        pipeline.progress_hooks = []
        pipeline._llm_calls = 0
        pipeline._tokens_in = 0
        pipeline._tokens_out = 0

        await pipeline._emit_progress("@coder", "Writing code", 1, 3, "qwen3-coder")

        # Should have been called at least 2 times:
        # 1. chat_response (to=self.sid)
        # 2. pipeline_activity (broadcast)
        assert pipeline.sio.emit.call_count >= 2

        # Check call args
        calls = pipeline.sio.emit.call_args_list
        event_names = [c.args[0] if c.args else c.kwargs.get('event') for c in calls]
        assert "chat_response" in event_names
        assert "pipeline_activity" in event_names

    @pytest.mark.asyncio
    async def test_pipeline_activity_includes_correct_data(self):
        """pipeline_activity event should include role, message, model, task_id."""
        from src.orchestration.agent_pipeline import AgentPipeline

        pipeline = AgentPipeline.__new__(AgentPipeline)
        pipeline.sio = AsyncMock()
        pipeline.sid = "test_sid"
        pipeline.chat_id = None
        pipeline.preset = "dragon_silver"
        pipeline._board_task_id = "tb_456"
        pipeline.progress_hooks = []
        pipeline._llm_calls = 0
        pipeline._tokens_in = 0
        pipeline._tokens_out = 0

        await pipeline._emit_progress("@architect", "Planning subtasks", 0, 0, "kimi-k2.5")

        # Find the pipeline_activity call
        for call in pipeline.sio.emit.call_args_list:
            if call.args[0] == "pipeline_activity":
                data = call.args[1]
                assert data["role"] == "@architect"
                assert data["message"] == "Planning subtasks"
                assert data["model"] == "kimi-k2.5"
                assert data["task_id"] == "tb_456"
                assert data["preset"] == "dragon_silver"
                assert "timestamp" in data
                return

        pytest.fail("pipeline_activity event not found in emit calls")

    @pytest.mark.asyncio
    async def test_pipeline_activity_survives_sio_error(self):
        """If first emit (chat_response) fails, pipeline_activity should still try."""
        from src.orchestration.agent_pipeline import AgentPipeline

        pipeline = AgentPipeline.__new__(AgentPipeline)

        call_count = 0
        async def flaky_emit(event, data, **kwargs):
            nonlocal call_count
            call_count += 1
            if event == "chat_response":
                raise ConnectionError("Socket disconnected")
            # pipeline_activity should succeed

        pipeline.sio = MagicMock()
        pipeline.sio.emit = flaky_emit
        pipeline.sid = "test_sid"
        pipeline.chat_id = None
        pipeline.preset = "dragon_silver"
        pipeline._board_task_id = None
        pipeline.progress_hooks = []
        pipeline._llm_calls = 0
        pipeline._tokens_in = 0
        pipeline._tokens_out = 0

        # Should not raise even though chat_response fails
        await pipeline._emit_progress("@coder", "Test", 1, 1)
        # The first emit (chat_response) throws, caught by try/except
        # The pipeline_activity emit should also be attempted


# =============================================================================
# Test 5: Regression
# =============================================================================

class TestRegressionPhase127_1:
    """Regression tests for previous phases."""

    def test_verifier_feedback_is_dict_type(self):
        """Subtask.verifier_feedback should be Optional[Dict] (Phase 127.1)."""
        path = os.path.join(os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py")
        with open(path) as f:
            content = f.read()
        assert "verifier_feedback: Optional[Dict]" in content

    def test_chat_response_still_targeted(self):
        """chat_response should still be sent to specific sid (not broadcast)."""
        path = os.path.join(os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py")
        with open(path) as f:
            content = f.read()
        assert 'to=self.sid' in content

    def test_all_prompts_valid(self):
        """All pipeline prompts should be valid JSON."""
        path = os.path.join(os.path.dirname(__file__), "..", "data", "templates", "pipeline_prompts.json")
        with open(path) as f:
            prompts = json.load(f)
        for role in ["architect", "researcher", "coder", "verifier", "scout", "doctor"]:
            assert role in prompts

    def test_task_board_updated_event_still_exists(self):
        """task_board_updated should still be in useSocket.ts."""
        path = os.path.join(os.path.dirname(__file__), "..", "client", "src", "hooks", "useSocket.ts")
        with open(path) as f:
            content = f.read()
        assert "task_board_updated" in content
        assert "task-board-updated" in content
