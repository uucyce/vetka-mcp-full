"""
Phase 126.5: Pipeline Stop/Cancel Tests

Tests for cancellation mechanism: PipelineCancelled exception,
asyncio.Event cancellation, TaskBoard.cancel_task(), UI stop button.

21 tests across 5 classes.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ============================================================================
# TestPipelineCancelledException
# ============================================================================

class TestPipelineCancelledException:
    """Test PipelineCancelled exception and cancel() method."""

    def test_exception_exists(self):
        """PipelineCancelled class should exist in agent_pipeline."""
        from src.orchestration.agent_pipeline import PipelineCancelled
        assert issubclass(PipelineCancelled, Exception)

    def test_marker_126_5a_in_code(self):
        """MARKER_126.5A should be in agent_pipeline.py."""
        content = open("src/orchestration/agent_pipeline.py").read()
        assert "MARKER_126.5A" in content

    def test_cancel_method_exists(self):
        """AgentPipeline should have cancel() method."""
        from src.orchestration.agent_pipeline import AgentPipeline
        assert hasattr(AgentPipeline, 'cancel')
        assert callable(getattr(AgentPipeline, 'cancel'))

    def test_check_cancelled_method_exists(self):
        """AgentPipeline should have _check_cancelled() method."""
        from src.orchestration.agent_pipeline import AgentPipeline
        assert hasattr(AgentPipeline, '_check_cancelled')

    def test_cancelled_event_in_init(self):
        """AgentPipeline.__init__ should create _cancelled Event."""
        content = open("src/orchestration/agent_pipeline.py").read()
        assert "_cancelled" in content
        assert "Event()" in content


# ============================================================================
# TestCancelMechanism
# ============================================================================

class TestCancelMechanism:
    """Test cancel() sets event and _check_cancelled() raises."""

    def _make_pipeline(self):
        from src.orchestration.agent_pipeline import AgentPipeline
        p = AgentPipeline.__new__(AgentPipeline)
        import asyncio
        p._cancelled = asyncio.Event()
        p._cancel_reason = ""
        return p

    def test_cancel_sets_event(self):
        """cancel() should set the _cancelled Event."""
        p = self._make_pipeline()
        assert not p._cancelled.is_set()
        p.cancel("test reason")
        assert p._cancelled.is_set()
        assert p._cancel_reason == "test reason"

    def test_check_cancelled_raises(self):
        """_check_cancelled() should raise PipelineCancelled when cancelled."""
        from src.orchestration.agent_pipeline import PipelineCancelled
        p = self._make_pipeline()
        p.cancel("stop!")
        with pytest.raises(PipelineCancelled, match="stop!"):
            p._check_cancelled()

    def test_check_cancelled_noop_when_not_cancelled(self):
        """_check_cancelled() should NOT raise when not cancelled."""
        p = self._make_pipeline()
        p._check_cancelled()  # Should not raise


# ============================================================================
# TestTaskBoardCancel
# ============================================================================

class TestTaskBoardCancel:
    """Test TaskBoard.cancel_task() method."""

    def test_cancel_task_method_exists(self):
        """TaskBoard should have cancel_task() method."""
        from src.orchestration.task_board import TaskBoard
        assert hasattr(TaskBoard, 'cancel_task')

    def test_marker_126_5d_in_code(self):
        """MARKER_126.5D should be in task_board.py."""
        content = open("src/orchestration/task_board.py").read()
        assert "MARKER_126.5D" in content

    def test_register_pipeline_classmethod(self):
        """TaskBoard should have register_pipeline classmethod."""
        from src.orchestration.task_board import TaskBoard
        assert hasattr(TaskBoard, 'register_pipeline')

    def test_cancel_pending_task(self):
        """cancel_task on pending task should set status=cancelled."""
        from src.orchestration.task_board import TaskBoard
        board = TaskBoard.__new__(TaskBoard)
        board.tasks = {
            "tb_test": {
                "id": "tb_test", "title": "test", "status": "pending",
                "priority": 2, "phase_type": "build", "created_at": "2026-01-01"
            }
        }
        board.settings = {}
        board._save = MagicMock()

        ok = board.cancel_task("tb_test", "user request")
        assert ok
        assert board.tasks["tb_test"]["status"] == "cancelled"

    def test_cancel_done_task_returns_false(self):
        """cancel_task on done task should return False."""
        from src.orchestration.task_board import TaskBoard
        board = TaskBoard.__new__(TaskBoard)
        board.tasks = {
            "tb_done": {
                "id": "tb_done", "title": "done task", "status": "done",
                "priority": 2, "phase_type": "build", "created_at": "2026-01-01"
            }
        }
        ok = board.cancel_task("tb_done")
        assert not ok


# ============================================================================
# TestCancelAPI
# ============================================================================

class TestCancelAPI:
    """Test REST API cancel endpoint."""

    def test_cancel_endpoint_registered(self):
        """POST /task-board/cancel should be registered."""
        content = open("src/api/routes/debug_routes.py").read()
        assert "/task-board/cancel" in content
        assert "MARKER_126.5F" in content

    def test_marker_126_5e_in_dispatch(self):
        """MARKER_126.5E should be in task_board.py dispatch."""
        content = open("src/orchestration/task_board.py").read()
        assert "MARKER_126.5E" in content
        assert "register_pipeline" in content
        assert "unregister_pipeline" in content


# ============================================================================
# TestUIStopButton
# ============================================================================

class TestUIStopButton:
    """Test UI stop button in TaskCard."""

    def test_stop_button_in_taskcard(self):
        """TaskCard should have stop button for running tasks."""
        content = open("client/src/components/panels/TaskCard.tsx").read()
        assert "MARKER_126.5G" in content
        assert "onCancel" in content
        assert "stop" in content.lower()

    def test_cancel_handler_in_devpanel(self):
        """DevPanel should have handleCancelTask function."""
        content = open("client/src/components/panels/DevPanel.tsx").read()
        assert "handleCancelTask" in content
        assert "task-board/cancel" in content
        assert "onCancel={handleCancelTask}" in content

    def test_cancelled_status_handled(self):
        """TaskCard STATUS_DEF should handle 'cancelled' status."""
        content = open("client/src/components/panels/TaskCard.tsx").read()
        # 'cancelled' should be in STATUS_DEF
        assert "cancelled" in content

    def test_cancellation_handler_in_execute(self):
        """execute() should catch PipelineCancelled."""
        content = open("src/orchestration/agent_pipeline.py").read()
        assert "except PipelineCancelled" in content
        assert "MARKER_126.5C" in content
