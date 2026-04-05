"""Phase 117.2c — Mycelium Heartbeat Engine Tests

Tests for the Dragon's Heartbeat:
- State persistence (load/save with sandbox fallback)
- Message parsing (task trigger patterns)
- Loop prevention (skip pipeline's own messages)
- Phase type mapping (@dragon→build, /fix→fix, /research→research)
- Heartbeat tick flow (fetch → parse → dispatch)
- MCP tool registration

@status: active
@phase: 117.2c
@depends: src/orchestration/mycelium_heartbeat.py, src/mcp/vetka_mcp_bridge.py
"""

import pytest
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import asdict

from src.orchestration.mycelium_heartbeat import (
    HeartbeatState,
    ParsedTask,
    _parse_tasks,
    _load_state,
    _save_state,
    get_heartbeat_status,
    heartbeat_tick,
    TASK_PATTERNS,
    PHASE_TYPE_MAP,
    HEARTBEAT_GROUP_ID,
)

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 117 contracts changed")


# ═══════════════════════════════════════════════════════════════════════
# 1. State Persistence
# ═══════════════════════════════════════════════════════════════════════

class TestHeartbeatState:
    """Test HeartbeatState dataclass and persistence."""

    def test_default_state(self):
        """Fresh state has sensible defaults."""
        state = HeartbeatState()
        assert state.last_message_id is None
        assert state.total_ticks == 0
        assert state.tasks_dispatched == 0
        assert state.tasks_completed == 0
        assert state.tasks_failed == 0
        assert state.recent_runs == []

    def test_state_serialization(self, tmp_path):
        """State round-trips through JSON correctly."""
        state = HeartbeatState(
            last_message_id="msg-abc-123",
            total_ticks=42,
            tasks_dispatched=10,
            tasks_completed=8,
            tasks_failed=2,
            recent_runs=[{"tick": 1, "time": "2026-02-07 12:00:00"}]
        )
        data = json.dumps(asdict(state), indent=2, default=str)
        restored = json.loads(data)

        assert restored["last_message_id"] == "msg-abc-123"
        assert restored["total_ticks"] == 42
        assert restored["tasks_dispatched"] == 10

    def test_save_load_roundtrip(self, tmp_path):
        """State saves to disk and loads back correctly."""
        state_file = tmp_path / "heartbeat_state.json"

        state = HeartbeatState(
            last_message_id="test-msg-id",
            total_ticks=5,
            tasks_dispatched=3
        )

        with patch("src.orchestration.mycelium_heartbeat._STATE_FILE", state_file):
            _save_state(state)
            loaded = _load_state()

        assert loaded.last_message_id == "test-msg-id"
        assert loaded.total_ticks == 5
        assert loaded.tasks_dispatched == 3

    def test_load_missing_file_returns_default(self, tmp_path):
        """Loading from nonexistent file returns fresh state."""
        missing = tmp_path / "nonexistent.json"
        fallback = tmp_path / "also_missing.json"

        with patch("src.orchestration.mycelium_heartbeat._STATE_FILE", missing), \
             patch("src.orchestration.mycelium_heartbeat._STATE_FILE_FALLBACK", fallback):
            state = _load_state()

        assert state.last_message_id is None
        assert state.total_ticks == 0

    def test_save_fallback_on_permission_error(self, tmp_path):
        """State saves to fallback path when primary is read-only."""
        primary = tmp_path / "readonly" / "heartbeat_state.json"
        fallback = tmp_path / "fallback_state.json"

        state = HeartbeatState(last_message_id="fallback-test", total_ticks=1)

        # Make primary parent non-writable by patching
        with patch("src.orchestration.mycelium_heartbeat._STATE_FILE", primary), \
             patch("src.orchestration.mycelium_heartbeat._STATE_FILE_FALLBACK", fallback):
            # Patch mkdir to raise PermissionError
            with patch.object(Path, "mkdir", side_effect=PermissionError("sandbox")):
                _save_state(state)

        # Should have written to fallback
        assert fallback.exists()
        data = json.loads(fallback.read_text())
        assert data["last_message_id"] == "fallback-test"


# ═══════════════════════════════════════════════════════════════════════
# 2. Task Parsing
# ═══════════════════════════════════════════════════════════════════════

class TestTaskParsing:
    """Test _parse_tasks() with various message formats."""

    def test_parse_dragon_trigger(self):
        """@dragon trigger parsed correctly."""
        messages = [
            {"id": "m1", "sender_id": "user", "content": "@dragon fix the login bug"}
        ]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert tasks[0].task == "fix the login bug"
        assert tasks[0].trigger == "dragon"
        assert tasks[0].phase_type == "build"

    def test_parse_pipeline_trigger(self):
        """@pipeline trigger parsed correctly."""
        messages = [
            {"id": "m2", "sender_id": "user", "content": "@pipeline refactor auth module"}
        ]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert tasks[0].trigger == "pipeline"
        assert tasks[0].phase_type == "build"

    def test_parse_slash_task(self):
        """/task trigger parsed correctly."""
        messages = [
            {"id": "m3", "sender_id": "user", "content": "/task add dark mode toggle"}
        ]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert tasks[0].task == "add dark mode toggle"
        assert tasks[0].trigger == "task"
        assert tasks[0].phase_type == "build"

    def test_parse_slash_fix(self):
        """/fix trigger maps to fix phase."""
        messages = [
            {"id": "m4", "sender_id": "user", "content": "/fix broken CSS on mobile"}
        ]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert tasks[0].trigger == "fix"
        assert tasks[0].phase_type == "fix"

    def test_parse_slash_build(self):
        """/build trigger maps to build phase."""
        messages = [
            {"id": "m5", "sender_id": "user", "content": "/build new API endpoint for users"}
        ]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert tasks[0].trigger == "build"
        assert tasks[0].phase_type == "build"

    def test_parse_slash_research(self):
        """/research trigger maps to research phase."""
        messages = [
            {"id": "m6", "sender_id": "user", "content": "/research best practices for caching"}
        ]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert tasks[0].trigger == "research"
        assert tasks[0].phase_type == "research"

    def test_parse_case_insensitive(self):
        """Triggers are case-insensitive."""
        messages = [
            {"id": "m7", "sender_id": "user", "content": "@DRAGON uppercase test"}
        ]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert tasks[0].task == "uppercase test"

    def test_parse_no_trigger(self):
        """Normal messages without triggers produce no tasks."""
        messages = [
            {"id": "m8", "sender_id": "user", "content": "Hey team, how's it going?"},
            {"id": "m9", "sender_id": "user", "content": "The build looks good"},
        ]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 0

    def test_parse_multiple_messages(self):
        """Multiple task messages parsed correctly."""
        messages = [
            {"id": "m10", "sender_id": "user", "content": "@dragon task one"},
            {"id": "m11", "sender_id": "user", "content": "just chatting"},
            {"id": "m12", "sender_id": "user", "content": "/fix task two"},
        ]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 2
        assert tasks[0].task == "task one"
        assert tasks[1].task == "task two"

    def test_one_task_per_message(self):
        """Only first trigger in a message is parsed (no double dispatch)."""
        messages = [
            {"id": "m13", "sender_id": "user",
             "content": "@dragon first task\n/fix second task"}
        ]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1

    def test_multiline_task(self):
        """Task text can span multiple lines."""
        messages = [
            {"id": "m14", "sender_id": "user",
             "content": "@dragon fix the login bug\nAlso check the registration flow\nAnd the password reset"}
        ]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert "login bug" in tasks[0].task
        assert "registration" in tasks[0].task


# ═══════════════════════════════════════════════════════════════════════
# 3. Loop Prevention
# ═══════════════════════════════════════════════════════════════════════

class TestLoopPrevention:
    """Test that heartbeat doesn't dispatch its own messages (infinite loop prevention)."""

    def test_skip_pipeline_messages(self):
        """Messages from pipeline agent are skipped."""
        messages = [
            {"id": "m20", "sender_id": "@Mycelium Pipeline", "content": "@dragon self-reference"},
            {"id": "m21", "sender_id": "@pipeline", "content": "/task from pipeline"},
            {"id": "m22", "sender_id": "pipeline", "content": "@dragon another one"},
        ]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 0

    def test_skip_system_pipeline_progress(self):
        """System messages with @pipeline: prefix are skipped."""
        messages = [
            {"id": "m23", "sender_id": "system", "message_type": "system",
             "content": "@pipeline: ❤️ Heartbeat tick #5: 3 new messages"},
        ]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 0

    def test_user_messages_not_skipped(self):
        """Messages from real users are NOT skipped."""
        messages = [
            {"id": "m24", "sender_id": "user-123", "content": "@dragon real task"},
            {"id": "m25", "sender_id": "claude_code", "content": "/task from architect"},
        ]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 2


# ═══════════════════════════════════════════════════════════════════════
# 4. Phase Type Mapping
# ═══════════════════════════════════════════════════════════════════════

class TestPhaseTypeMapping:
    """Test trigger → phase type mapping."""

    def test_all_mappings(self):
        """All known triggers map to correct phase types."""
        assert PHASE_TYPE_MAP["dragon"] == "build"
        assert PHASE_TYPE_MAP["pipeline"] == "build"
        assert PHASE_TYPE_MAP["task"] == "build"
        assert PHASE_TYPE_MAP["fix"] == "fix"
        assert PHASE_TYPE_MAP["build"] == "build"
        assert PHASE_TYPE_MAP["research"] == "research"

    def test_default_group_id(self):
        """Default group ID is MCP Dev."""
        assert HEARTBEAT_GROUP_ID == "5e2198c2-8b1a-45df-807f-5c73c5496aa8"


# ═══════════════════════════════════════════════════════════════════════
# 5. Heartbeat Tick Flow
# ═══════════════════════════════════════════════════════════════════════

class TestHeartbeatTick:
    """Test heartbeat_tick() flow."""

    @pytest.mark.asyncio
    async def test_tick_no_messages(self, tmp_path):
        """Tick with no new messages returns early."""
        state_file = tmp_path / "state.json"
        fallback = tmp_path / "state_fallback.json"

        with patch("src.orchestration.mycelium_heartbeat._STATE_FILE", state_file), \
             patch("src.orchestration.mycelium_heartbeat._STATE_FILE_FALLBACK", fallback), \
             patch("src.orchestration.mycelium_heartbeat._fetch_new_messages", return_value=[]):

            result = await heartbeat_tick(group_id="test-group")

        assert result["new_messages"] == 0
        assert result["tasks_found"] == 0
        assert result["tasks_dispatched"] == 0

    @pytest.mark.asyncio
    async def test_tick_dry_run(self, tmp_path):
        """Tick in dry_run mode parses but doesn't dispatch."""
        state_file = tmp_path / "state.json"
        fallback = tmp_path / "state_fallback.json"

        mock_messages = [
            {"id": "msg-1", "sender_id": "user", "content": "@dragon test task"}
        ]

        with patch("src.orchestration.mycelium_heartbeat._STATE_FILE", state_file), \
             patch("src.orchestration.mycelium_heartbeat._STATE_FILE_FALLBACK", fallback), \
             patch("src.orchestration.mycelium_heartbeat._fetch_new_messages", return_value=mock_messages), \
             patch("src.orchestration.mycelium_heartbeat._emit_heartbeat_status"):

            result = await heartbeat_tick(group_id="test-group", dry_run=True)

        assert result["new_messages"] == 1
        assert result["tasks_found"] == 1
        assert result["tasks_dispatched"] == 1  # dry_run still adds to results list
        assert result["dry_run"] is True
        assert result["results"][0]["dry_run"] is True

    @pytest.mark.asyncio
    async def test_tick_dispatches_tasks(self, tmp_path):
        """Tick dispatches parsed tasks to pipeline."""
        state_file = tmp_path / "state.json"
        fallback = tmp_path / "state_fallback.json"

        mock_messages = [
            {"id": "msg-2", "sender_id": "user", "content": "/fix broken button"}
        ]

        mock_pipeline_result = {
            "task_id": "test-task-1",
            "status": "done",
            "results": {"subtasks_completed": 2, "subtasks_total": 2}
        }

        with patch("src.orchestration.mycelium_heartbeat._STATE_FILE", state_file), \
             patch("src.orchestration.mycelium_heartbeat._STATE_FILE_FALLBACK", fallback), \
             patch("src.orchestration.mycelium_heartbeat._fetch_new_messages", return_value=mock_messages), \
             patch("src.orchestration.mycelium_heartbeat._emit_heartbeat_status"), \
             patch("src.orchestration.mycelium_heartbeat._dispatch_task", new_callable=AsyncMock, return_value={"success": True, "task_id": "test-1"}):

            result = await heartbeat_tick(group_id="test-group", dry_run=False)

        assert result["tasks_found"] == 1
        assert result["tasks_dispatched"] == 1
        assert result["results"][0]["success"] is True

    @pytest.mark.asyncio
    async def test_tick_updates_state(self, tmp_path):
        """Tick updates last_message_id and tick count in state."""
        state_file = tmp_path / "state.json"
        fallback = tmp_path / "state_fallback.json"

        mock_messages = [
            {"id": "msg-latest", "sender_id": "user", "content": "just chatting"}
        ]

        with patch("src.orchestration.mycelium_heartbeat._STATE_FILE", state_file), \
             patch("src.orchestration.mycelium_heartbeat._STATE_FILE_FALLBACK", fallback), \
             patch("src.orchestration.mycelium_heartbeat._fetch_new_messages", return_value=mock_messages):

            await heartbeat_tick(group_id="test-group")

        # Verify state was saved
        assert state_file.exists()
        saved = json.loads(state_file.read_text())
        assert saved["last_message_id"] == "msg-latest"
        assert saved["total_ticks"] == 1


# ═══════════════════════════════════════════════════════════════════════
# 6. MCP Tool Registration
# ═══════════════════════════════════════════════════════════════════════

class TestMCPToolRegistration:
    """Test that heartbeat tools are registered in MCP bridge."""

    def test_heartbeat_tick_tool_defined(self):
        """vetka_heartbeat_tick tool is defined in bridge."""
        bridge_path = Path("src/mcp/vetka_mcp_bridge.py")
        content = bridge_path.read_text()

        assert '"vetka_heartbeat_tick"' in content or "'vetka_heartbeat_tick'" in content or \
               'name="vetka_heartbeat_tick"' in content, \
            "vetka_heartbeat_tick must be defined as MCP tool"

    def test_heartbeat_status_tool_defined(self):
        """vetka_heartbeat_status tool is defined in bridge."""
        bridge_path = Path("src/mcp/vetka_mcp_bridge.py")
        content = bridge_path.read_text()

        assert '"vetka_heartbeat_status"' in content or "'vetka_heartbeat_status'" in content or \
               'name="vetka_heartbeat_status"' in content, \
            "vetka_heartbeat_status must be defined as MCP tool"

    def test_heartbeat_tick_handler_exists(self):
        """Handler for vetka_heartbeat_tick exists in bridge."""
        bridge_path = Path("src/mcp/vetka_mcp_bridge.py")
        content = bridge_path.read_text()

        assert 'name == "vetka_heartbeat_tick"' in content, \
            "Handler for vetka_heartbeat_tick must exist"

    def test_heartbeat_status_handler_exists(self):
        """Handler for vetka_heartbeat_status exists in bridge."""
        bridge_path = Path("src/mcp/vetka_mcp_bridge.py")
        content = bridge_path.read_text()

        assert 'name == "vetka_heartbeat_status"' in content, \
            "Handler for vetka_heartbeat_status must exist"

    def test_heartbeat_imports_in_handler(self):
        """Handler imports heartbeat functions."""
        bridge_path = Path("src/mcp/vetka_mcp_bridge.py")
        content = bridge_path.read_text()

        assert "from src.orchestration.mycelium_heartbeat import heartbeat_tick" in content
        assert "from src.orchestration.mycelium_heartbeat import get_heartbeat_status" in content


# ═══════════════════════════════════════════════════════════════════════
# 7. Get Heartbeat Status
# ═══════════════════════════════════════════════════════════════════════

class TestGetHeartbeatStatus:
    """Test get_heartbeat_status() for MCP tool."""

    def test_status_returns_expected_keys(self, tmp_path):
        """Status returns all required fields."""
        state_file = tmp_path / "state.json"
        fallback = tmp_path / "fallback.json"

        with patch("src.orchestration.mycelium_heartbeat._STATE_FILE", state_file), \
             patch("src.orchestration.mycelium_heartbeat._STATE_FILE_FALLBACK", fallback):
            status = get_heartbeat_status()

        assert "last_message_id" in status
        assert "total_ticks" in status
        assert "tasks_dispatched" in status
        assert "tasks_completed" in status
        assert "tasks_failed" in status
        assert "recent_runs" in status

    def test_status_limits_recent_runs(self, tmp_path):
        """Status returns at most 5 recent runs."""
        state_file = tmp_path / "state.json"
        fallback = tmp_path / "fallback.json"

        state = HeartbeatState(
            total_ticks=50,
            recent_runs=[{"tick": i} for i in range(20)]
        )
        state_file.write_text(json.dumps(asdict(state), default=str))

        with patch("src.orchestration.mycelium_heartbeat._STATE_FILE", state_file), \
             patch("src.orchestration.mycelium_heartbeat._STATE_FILE_FALLBACK", fallback):
            status = get_heartbeat_status()

        assert len(status["recent_runs"]) == 5
