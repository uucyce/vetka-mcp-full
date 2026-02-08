"""Phase 119.2: Pipeline STM -> Global STMBuffer Bridge Tests

Tests that pipeline completion reports a summary to the global STMBuffer,
bridging the ephemeral pipeline context with persistent conversation memory.

MARKER_119.2
"""

import pytest
from src.memory.stm_buffer import get_stm_buffer, reset_stm_buffer


class TestPipelineSTMBridge:
    """Test _bridge_to_global_stm method."""

    def setup_method(self):
        """Reset global STM before each test."""
        reset_stm_buffer()

    def test_bridge_adds_to_stm(self):
        """Pipeline bridge adds summary message to global STMBuffer."""
        from src.orchestration.agent_pipeline import AgentPipeline

        pipeline = AgentPipeline.__new__(AgentPipeline)
        pipeline.stm = [
            {"marker": "STEP_1", "result": "Created auth module"},
            {"marker": "STEP_2", "result": "Added tests"}
        ]
        pipeline.preset_name = "dragon_silver"

        pipeline._bridge_to_global_stm("task_123", "build")

        stm_buffer = get_stm_buffer()
        entries = stm_buffer.get_all()
        assert len(entries) == 1
        assert entries[0].source == "pipeline"
        assert "task_123" in entries[0].content
        assert "build" in entries[0].content

    def test_bridge_empty_stm_does_nothing(self):
        """Bridge does nothing when pipeline STM is empty."""
        from src.orchestration.agent_pipeline import AgentPipeline

        pipeline = AgentPipeline.__new__(AgentPipeline)
        pipeline.stm = []
        pipeline.preset_name = None

        pipeline._bridge_to_global_stm("task_456", "research")

        stm_buffer = get_stm_buffer()
        assert len(stm_buffer) == 0

    def test_bridge_truncates_long_summary(self):
        """Bridge truncates summary to 500 chars max."""
        from src.orchestration.agent_pipeline import AgentPipeline

        pipeline = AgentPipeline.__new__(AgentPipeline)
        pipeline.stm = [
            {"marker": f"STEP_{i}", "result": "x" * 200}
            for i in range(10)
        ]
        pipeline.preset_name = "dragon_gold"

        pipeline._bridge_to_global_stm("task_long", "build")

        stm_buffer = get_stm_buffer()
        entries = stm_buffer.get_all()
        assert len(entries) == 1
        assert len(entries[0].content) <= 500
