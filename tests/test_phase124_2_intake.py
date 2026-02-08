"""
Tests for Phase 124.2: Interactive Task Intake + Heartbeat TaskBoard Routing

Tests cover:
- 124.2A: Interactive intake prompt and reply handling
- 124.2B: Heartbeat routing through TaskBoard
- 124.2C: Task Board REST API helpers

@status: active
@phase: 124.2
@depends: pytest, asyncio
"""

import pytest
import asyncio
import time
from unittest.mock import patch, AsyncMock, MagicMock


# =====================================================
# Test 124.2A: Interactive Task Intake
# =====================================================

class TestIntakePrompt:
    """Test intake prompt creation and management."""

    def test_pending_intakes_dict_exists(self):
        """_PENDING_INTAKES should be importable."""
        from src.api.handlers.group_message_handler import _PENDING_INTAKES
        assert isinstance(_PENDING_INTAKES, dict)

    def test_has_pending_intake_empty(self):
        """has_pending_intake returns False for unknown chat."""
        from src.api.handlers.group_message_handler import has_pending_intake
        assert has_pending_intake("nonexistent-chat") is False

    def test_has_pending_intake_with_pending(self):
        """has_pending_intake returns True when intake exists."""
        from src.api.handlers.group_message_handler import _PENDING_INTAKES, has_pending_intake
        _PENDING_INTAKES["test-chat-1"] = {
            "agent_id": "dragon",
            "task_text": "fix bug",
            "sender_id": "user",
            "created_at": time.time(),
        }
        try:
            assert has_pending_intake("test-chat-1") is True
        finally:
            _PENDING_INTAKES.pop("test-chat-1", None)

    def test_has_pending_intake_expired(self):
        """has_pending_intake returns False for expired intake."""
        from src.api.handlers.group_message_handler import (
            _PENDING_INTAKES, has_pending_intake, _INTAKE_TIMEOUT_SEC
        )
        _PENDING_INTAKES["test-chat-2"] = {
            "agent_id": "dragon",
            "task_text": "fix bug",
            "sender_id": "user",
            "created_at": time.time() - _INTAKE_TIMEOUT_SEC - 10,
        }
        try:
            assert has_pending_intake("test-chat-2") is False
        finally:
            _PENDING_INTAKES.pop("test-chat-2", None)

    def test_intake_timeout_constant(self):
        """Intake timeout should be 60 seconds."""
        from src.api.handlers.group_message_handler import _INTAKE_TIMEOUT_SEC
        assert _INTAKE_TIMEOUT_SEC == 60


class TestIntakeReply:
    """Test intake reply parsing and dispatch."""

    @pytest.mark.asyncio
    async def test_handle_intake_no_pending(self):
        """handle_intake_reply returns False when no pending intake."""
        from src.api.handlers.group_message_handler import handle_intake_reply
        result = await handle_intake_reply("no-pending-chat", "1d")
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_intake_now_dragon(self):
        """Reply '1d' = now + dragon → immediate pipeline dispatch."""
        from src.api.handlers.group_message_handler import (
            _PENDING_INTAKES, handle_intake_reply
        )
        _PENDING_INTAKES["test-now-dragon"] = {
            "agent_id": "dragon",
            "task_text": "build sidebar",
            "sender_id": "user",
            "created_at": time.time(),
        }

        with patch("src.orchestration.agent_pipeline.AgentPipeline") as MockPipeline, \
             patch("httpx.AsyncClient") as MockClient:
            mock_pipeline = MagicMock()
            mock_pipeline.execute = AsyncMock(return_value={"status": "done", "results": {"subtasks_completed": 3, "subtasks_total": 3}})
            MockPipeline.return_value = mock_pipeline

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock()
            MockClient.return_value = mock_client

            result = await handle_intake_reply("test-now-dragon", "1d")

            assert result is True
            assert "test-now-dragon" not in _PENDING_INTAKES
            # Pipeline should have been called
            MockPipeline.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_intake_queue_titan(self):
        """Reply '2t' = queue + titan → TaskBoard.add_task()."""
        from src.api.handlers.group_message_handler import (
            _PENDING_INTAKES, handle_intake_reply
        )
        _PENDING_INTAKES["test-queue-titan"] = {
            "agent_id": "doctor",
            "task_text": "research sidebar architecture",
            "sender_id": "user",
            "created_at": time.time(),
        }

        with patch("src.orchestration.task_board.get_task_board") as MockGetBoard, \
             patch("httpx.AsyncClient") as MockClient:
            mock_board = MagicMock()
            mock_board.add_task.return_value = "tb_123"
            MockGetBoard.return_value = mock_board

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock()
            MockClient.return_value = mock_client

            result = await handle_intake_reply("test-queue-titan", "2t")

            assert result is True
            assert "test-queue-titan" not in _PENDING_INTAKES
            # Board should have been called with titan preset
            mock_board.add_task.assert_called_once()
            call_kwargs = mock_board.add_task.call_args[1]
            assert call_kwargs["preset"] == "titan_core"
            assert "titan" in call_kwargs["tags"]

    def test_parse_reply_urgency(self):
        """Test urgency parsing from reply text."""
        # "1" in reply → now, "2" → queue
        assert "1" in "1d"  # now
        assert "1" not in "2d"  # queue
        assert "1" in "1t"  # now

    def test_parse_reply_team(self):
        """Test team parsing from reply text."""
        # "t" in reply → titan, else dragon
        assert "t" in "1t".lower()  # titan
        assert "t" in "2t".lower()  # titan
        assert "t" not in "1d".lower()  # dragon
        assert "t" not in "2d".lower()  # dragon


class TestIntakeDispatchModified:
    """Test that _dispatch_system_command now uses intake flow."""

    @pytest.mark.asyncio
    async def test_dispatch_sends_intake_prompt(self):
        """_dispatch_system_command should call _send_intake_prompt instead of direct dispatch."""
        from src.api.handlers.group_message_handler import _dispatch_system_command

        with patch("src.api.handlers.group_message_handler._send_intake_prompt") as mock_prompt:
            mock_prompt.return_value = None  # It's a coroutine
            mock_prompt.side_effect = AsyncMock(return_value=None)

            await _dispatch_system_command(
                agent_id="dragon",
                chat_id="test-chat-dispatch",
                content="@dragon build sidebar",
                message_id="msg-1",
                sender_id="user",
            )

            # Should have called _send_intake_prompt, not AgentPipeline directly
            mock_prompt.assert_called_once()
            call_args = mock_prompt.call_args[0]
            assert call_args[0] == "test-chat-dispatch"  # chat_id
            assert call_args[1] == "dragon"  # agent_id
            assert "build sidebar" in call_args[2]  # task_text


# =====================================================
# Test 124.2B: Heartbeat → TaskBoard Routing
# =====================================================

class TestHeartbeatBoardRouting:
    """Test heartbeat routes tasks through TaskBoard."""

    def test_heartbeat_imports_task_board(self):
        """Heartbeat should reference TaskBoard."""
        import src.orchestration.mycelium_heartbeat as hb
        source = open(hb.__file__).read()
        assert "get_task_board" in source
        assert "MARKER_124.2B" in source

    def test_heartbeat_has_board_routing_marker(self):
        """Heartbeat should have MARKER_124.2B in dispatch section."""
        from pathlib import Path
        content = Path("src/orchestration/mycelium_heartbeat.py").read_text()
        assert "MARKER_124.2B" in content
        assert "board.add_task" in content
        assert "board.dispatch_next" in content

    def test_heartbeat_parse_tasks(self):
        """Parse tasks should still work with @dragon/@doctor triggers."""
        from src.orchestration.mycelium_heartbeat import _parse_tasks

        messages = [
            {"id": "m1", "content": "@dragon build new feature", "sender_id": "user"},
            {"id": "m2", "content": "@doctor check health", "sender_id": "user"},
            {"id": "m3", "content": "@board list", "sender_id": "user"},
        ]

        tasks = _parse_tasks(messages)
        assert len(tasks) == 3
        assert tasks[0].trigger == "dragon"
        assert tasks[0].phase_type == "build"
        assert tasks[1].trigger == "doctor"
        assert tasks[1].phase_type == "research"
        assert tasks[2].trigger == "board"

    def test_heartbeat_skip_pipeline_messages(self):
        """Parser should skip messages from pipeline to avoid loops."""
        from src.orchestration.mycelium_heartbeat import _parse_tasks

        messages = [
            {"id": "m1", "content": "@dragon build feature", "sender_id": "@Mycelium Pipeline"},
            {"id": "m2", "content": "@pipeline: progress 50%", "sender_id": "system", "message_type": "system"},
        ]

        tasks = _parse_tasks(messages)
        assert len(tasks) == 0


# =====================================================
# Test 124.2C: Task Board REST API
# =====================================================

class TestTaskBoardAPI:
    """Test Task Board REST API endpoint existence."""

    def test_api_endpoints_registered(self):
        """Task Board endpoints should be in debug_routes.py."""
        from pathlib import Path
        routes_file = Path("src/api/routes/debug_routes.py")
        content = routes_file.read_text()

        assert "/task-board" in content
        assert "/task-board/add" in content
        assert "/task-board/dispatch" in content
        assert "MARKER_124.2C" in content

    def test_get_task_board_import(self):
        """get_task_board should be importable."""
        from src.orchestration.task_board import get_task_board
        board = get_task_board()
        assert board is not None

    def test_task_board_add_and_remove(self):
        """TaskBoard CRUD should work."""
        from src.orchestration.task_board import TaskBoard
        from pathlib import Path
        import tempfile, os

        # Use temp file to avoid affecting real board
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp.close()

        try:
            board = TaskBoard(board_file=Path(tmp.name))
            task_id = board.add_task(
                title="Test task",
                description="Test description",
                priority=2,
                phase_type="build",
            )
            assert task_id.startswith("tb_")

            # Verify task exists
            task = board.get_task(task_id)
            assert task is not None
            assert task["title"] == "Test task"
            assert task["priority"] == 2

            # Update priority
            ok = board.update_task(task_id, priority=1)
            assert ok is True
            assert board.get_task(task_id)["priority"] == 1

            # Remove
            ok = board.remove_task(task_id)
            assert ok is True
            assert board.get_task(task_id) is None
        finally:
            os.unlink(tmp.name)


# =====================================================
# Test: Frontend files exist
# =====================================================

class TestFrontendFiles:
    """Test frontend files were created/modified."""

    def test_task_card_exists(self):
        """TaskCard.tsx should exist."""
        from pathlib import Path
        assert Path("client/src/components/panels/TaskCard.tsx").exists()

    def test_dev_panel_has_task_board(self):
        """DevPanel.tsx should reference Task Board, not Y-Axis Formula."""
        from pathlib import Path
        content = Path("client/src/components/panels/DevPanel.tsx").read_text()
        assert "Task Board" in content
        assert "MARKER_124.2C" in content
        # Old content should be gone
        assert "Y-Axis Formula" not in content
        assert "Y_WEIGHT_TIME" not in content
        assert "FALLBACK_THRESHOLD" not in content

    def test_dev_panel_keeps_spatial_memory(self):
        """DevPanel should keep Persist Positions and Reset Positions."""
        from pathlib import Path
        content = Path("client/src/components/panels/DevPanel.tsx").read_text()
        assert "Persist Positions" in content
        assert "resetLayout" in content
