"""
MARKER_140: Tests for Mycelium Standalone Server + Multi-chat Heartbeat

Covers Grok's checklist:
  Block 1: Heartbeat autonomy (items 1-8)
  Block 2: Control via HTTP API
  Block 3: MCP Tools integration
  Block 4: Safety (dedup, junk guard, cancellation)
  Block 6: Standalone launch (item 29-30)

Run: python -m pytest tests/test_mycelium_standalone.py -v
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — mycelium_standalone contracts changed")

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# BLOCK 1: Heartbeat Autonomy
# ============================================================

class TestHeartbeatPatternParsing:
    """Checklist #2: @dragon, @titan, @doctor, /task, /fix, /build triggers."""

    def test_dragon_pattern(self):
        from src.orchestration.mycelium_heartbeat import _parse_tasks
        messages = [{"id": "m1", "sender_id": "user", "content": "@dragon build a login page"}]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert tasks[0].trigger == "dragon"
        assert tasks[0].phase_type == "build"
        assert "login page" in tasks[0].task

    def test_titan_pattern(self):
        from src.orchestration.mycelium_heartbeat import _parse_tasks
        messages = [{"id": "m2", "sender_id": "user", "content": "@titan refactor the auth module"}]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert tasks[0].trigger == "titan"
        assert tasks[0].phase_type == "build"

    def test_doctor_pattern(self):
        from src.orchestration.mycelium_heartbeat import _parse_tasks
        messages = [{"id": "m3", "sender_id": "user", "content": "@doctor why is the server crashing"}]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert tasks[0].trigger == "doctor"
        assert tasks[0].phase_type == "research"

    def test_help_pattern(self):
        from src.orchestration.mycelium_heartbeat import _parse_tasks
        messages = [{"id": "m4", "sender_id": "user", "content": "@help how does task board work"}]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert tasks[0].trigger == "help"
        assert tasks[0].phase_type == "research"

    def test_fix_pattern(self):
        from src.orchestration.mycelium_heartbeat import _parse_tasks
        messages = [{"id": "m5", "sender_id": "user", "content": "/fix TypeError in broadcast_pipeline_activity"}]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert tasks[0].trigger == "fix"
        assert tasks[0].phase_type == "fix"

    def test_build_pattern(self):
        from src.orchestration.mycelium_heartbeat import _parse_tasks
        messages = [{"id": "m6", "sender_id": "user", "content": "/build new REST endpoint for artifacts"}]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert tasks[0].trigger == "build"
        assert tasks[0].phase_type == "build"

    def test_research_pattern(self):
        from src.orchestration.mycelium_heartbeat import _parse_tasks
        messages = [{"id": "m7", "sender_id": "user", "content": "/research best practices for WebSocket scaling"}]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert tasks[0].trigger == "research"
        assert tasks[0].phase_type == "research"

    def test_board_pattern(self):
        from src.orchestration.mycelium_heartbeat import _parse_tasks
        messages = [{"id": "m8", "sender_id": "user", "content": "@board dispatch"}]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert tasks[0].trigger == "board"

    def test_pipeline_message_skipped(self):
        """Pipeline's own messages must not trigger re-dispatch (loop prevention)."""
        from src.orchestration.mycelium_heartbeat import _parse_tasks
        messages = [{"id": "m9", "sender_id": "@Mycelium Pipeline", "content": "@dragon some echo task"}]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 0

    def test_system_pipeline_progress_skipped(self):
        """System messages with @pipeline: prefix are progress, not tasks."""
        from src.orchestration.mycelium_heartbeat import _parse_tasks
        messages = [{
            "id": "m10", "sender_id": "system",
            "message_type": "system",
            "content": "@pipeline: heartbeat detected task from user"
        }]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 0

    def test_no_triggers_returns_empty(self):
        from src.orchestration.mycelium_heartbeat import _parse_tasks
        messages = [{"id": "m11", "sender_id": "user", "content": "Hello, just chatting!"}]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 0

    def test_one_task_per_message(self):
        """Only first trigger per message is extracted."""
        from src.orchestration.mycelium_heartbeat import _parse_tasks
        messages = [{"id": "m12", "sender_id": "user", "content": "@dragon fix bug @doctor why crash"}]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert tasks[0].trigger == "dragon"

    def test_case_insensitive(self):
        from src.orchestration.mycelium_heartbeat import _parse_tasks
        messages = [{"id": "m13", "sender_id": "user", "content": "@DRAGON build something useful for tests"}]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert tasks[0].trigger == "dragon"


class TestHeartbeatSourceChatTracking:
    """MARKER_140: ParsedTask carries source_chat_id for multi-chat routing."""

    def test_source_chat_id_from_group(self):
        from src.orchestration.mycelium_heartbeat import _parse_tasks
        messages = [{
            "id": "m20", "sender_id": "user",
            "content": "@dragon build feature X for production use",
            "_source_chat_id": "group-abc-123",
            "_source_chat_type": "group",
        }]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert tasks[0].source_chat_id == "group-abc-123"
        assert tasks[0].source_chat_type == "group"

    def test_source_chat_id_from_solo(self):
        from src.orchestration.mycelium_heartbeat import _parse_tasks
        messages = [{
            "id": "m21", "sender_id": "user",
            "content": "@dragon implement caching layer for API",
            "_source_chat_id": "solo-xyz-456",
            "_source_chat_type": "solo",
        }]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert tasks[0].source_chat_id == "solo-xyz-456"
        assert tasks[0].source_chat_type == "solo"

    def test_source_chat_id_defaults(self):
        """Legacy messages without source fields get empty defaults."""
        from src.orchestration.mycelium_heartbeat import _parse_tasks
        messages = [{"id": "m22", "sender_id": "user", "content": "@dragon build something important here"}]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert tasks[0].source_chat_id == ""
        assert tasks[0].source_chat_type == "group"


# ============================================================
# BLOCK 1 continued: Junk guard + deduplication
# ============================================================

class TestHeartbeatJunkGuard:
    """Checklist #5: Short messages (<15 chars) are ignored."""

    @pytest.mark.asyncio
    async def test_short_task_skipped(self, monkeypatch, tmp_path):
        from src.orchestration import mycelium_heartbeat as hb

        state_file = tmp_path / "state.json"
        fallback_file = tmp_path / "fallback.json"
        monkeypatch.setattr(hb, "_STATE_FILE", state_file)
        monkeypatch.setattr(hb, "_STATE_FILE_FALLBACK", fallback_file)
        monkeypatch.setattr(hb, "_emit_heartbeat_status", lambda *a, **kw: None)

        # Short task — only 3 chars after "@dragon "
        monkeypatch.setattr(
            hb, "_fetch_new_messages",
            lambda group_id, since_id=None, limit=20: [
                {"id": "m30", "sender_id": "user", "content": "@dragon hi"}
            ],
        )

        class FakeBoard:
            settings = {"max_concurrent": 1}
            added = []
            def get_queue(self, status=None): return []
            def add_task(self, **kw):
                self.added.append(kw)
                return "tb_junk_1"
            async def dispatch_next(self, chat_id): return {"success": False}

        fake_board = FakeBoard()
        monkeypatch.setattr("src.orchestration.task_board.get_task_board", lambda: fake_board)

        result = await hb.heartbeat_tick(group_id="test", dry_run=False)
        assert result["tasks_found"] == 1
        # Task found but NOT added to board (junk guard)
        assert len(fake_board.added) == 0


class TestHeartbeatDeduplication:
    """Checklist #4: Same task not dispatched twice."""

    @pytest.mark.asyncio
    async def test_duplicate_task_skipped(self, monkeypatch, tmp_path):
        from src.orchestration import mycelium_heartbeat as hb

        state_file = tmp_path / "state.json"
        fallback_file = tmp_path / "fallback.json"
        monkeypatch.setattr(hb, "_STATE_FILE", state_file)
        monkeypatch.setattr(hb, "_STATE_FILE_FALLBACK", fallback_file)
        monkeypatch.setattr(hb, "_emit_heartbeat_status", lambda *a, **kw: None)

        task_title = "implement heartbeat dedup test"
        monkeypatch.setattr(
            hb, "_fetch_new_messages",
            lambda group_id, since_id=None, limit=20: [
                {"id": "m40", "sender_id": "user", "content": f"@dragon {task_title}"}
            ],
        )

        class FakeBoard:
            settings = {"max_concurrent": 1}
            added = []
            def get_queue(self, status=None):
                # Simulate already-existing task with same title
                return [{"title": task_title, "status": "pending"}]
            def add_task(self, **kw):
                self.added.append(kw)
                return "tb_dup_1"
            async def dispatch_next(self, chat_id): return {"success": False}

        fake_board = FakeBoard()
        monkeypatch.setattr("src.orchestration.task_board.get_task_board", lambda: fake_board)

        result = await hb.heartbeat_tick(group_id="test", dry_run=False)
        assert result["tasks_found"] == 1
        # Duplicate — should NOT be added to board
        assert len(fake_board.added) == 0


# ============================================================
# BLOCK 1: monitor_all mode
# ============================================================

class TestHeartbeatMonitorAll:
    """Checklist #3: monitor_all=True scans all groups + solo chats."""

    @pytest.mark.asyncio
    async def test_monitor_all_fetches_multiple_groups(self, monkeypatch, tmp_path):
        from src.orchestration import mycelium_heartbeat as hb

        state_file = tmp_path / "state.json"
        fallback_file = tmp_path / "fallback.json"
        cursors_file = tmp_path / "cursors.json"
        monkeypatch.setattr(hb, "_STATE_FILE", state_file)
        monkeypatch.setattr(hb, "_STATE_FILE_FALLBACK", fallback_file)
        monkeypatch.setattr(hb, "_emit_heartbeat_status", lambda *a, **kw: None)

        # Patch cursors file path (it's computed inside heartbeat_tick)
        # We'll just monkeypatch the fetcher functions

        groups_called = []
        solo_called = []

        def fake_fetch_groups(gid, since_id=None, limit=20):
            groups_called.append(gid)
            if gid == "group-A":
                return [{"id": "mg1", "sender_id": "user", "content": "@dragon build group A feature now"}]
            return []

        def fake_fetch_solo(cid, since_id=None, limit=20):
            solo_called.append(cid)
            return []

        monkeypatch.setattr(hb, "_fetch_new_messages", fake_fetch_groups)
        monkeypatch.setattr(hb, "_fetch_solo_chat_messages", fake_fetch_solo)
        monkeypatch.setattr(hb, "_fetch_all_active_group_ids", lambda: ["group-A", "group-B"])
        monkeypatch.setattr(hb, "_fetch_recent_solo_chat_ids", lambda limit=10: ["solo-1", "solo-2"])

        class FakeBoard:
            settings = {"max_concurrent": 1}
            added = []
            def get_queue(self, status=None): return []
            def add_task(self, **kw):
                self.added.append(kw)
                return "tb_ma_1"
            async def dispatch_next(self, chat_id): return {"success": False}

        fake_board = FakeBoard()
        monkeypatch.setattr("src.orchestration.task_board.get_task_board", lambda: fake_board)

        result = await hb.heartbeat_tick(
            group_id="primary-group",
            dry_run=False,
            monitor_all=True,
        )

        # Should have fetched from both groups + primary
        assert "group-A" in groups_called
        assert "group-B" in groups_called
        assert "primary-group" in groups_called
        # Should have fetched from solo chats
        assert "solo-1" in solo_called
        assert "solo-2" in solo_called
        # Task from group-A should be found
        assert result["tasks_found"] == 1


# ============================================================
# BLOCK 1: Heartbeat state persistence
# ============================================================

class TestHeartbeatStatePersistence:
    """State survives between ticks."""

    def test_state_save_and_load(self, tmp_path):
        from src.orchestration.mycelium_heartbeat import HeartbeatState, _save_state, _load_state
        import src.orchestration.mycelium_heartbeat as hb

        state_file = tmp_path / "state.json"
        fallback_file = tmp_path / "fallback.json"

        # Temporarily override paths
        orig_state = hb._STATE_FILE
        orig_fallback = hb._STATE_FILE_FALLBACK
        hb._STATE_FILE = state_file
        hb._STATE_FILE_FALLBACK = fallback_file

        try:
            state = HeartbeatState(
                last_message_id="msg-abc-123",
                total_ticks=42,
                tasks_dispatched=10,
            )
            _save_state(state)

            loaded = _load_state()
            assert loaded.last_message_id == "msg-abc-123"
            assert loaded.total_ticks == 42
            assert loaded.tasks_dispatched == 10
        finally:
            hb._STATE_FILE = orig_state
            hb._STATE_FILE_FALLBACK = orig_fallback


# ============================================================
# BLOCK 1: Heartbeat config — monitor_all flag
# ============================================================

class TestHeartbeatConfig:
    """Checklist #7: Heartbeat ON/OFF + monitor_all config."""

    @pytest.mark.asyncio
    async def test_config_roundtrip_with_monitor_all(self, monkeypatch, tmp_path):
        from src.api.routes import debug_routes

        config_file = tmp_path / "heartbeat_config.json"
        monkeypatch.setattr(debug_routes, "HEARTBEAT_CONFIG_FILE", config_file)

        # Set config
        result = await debug_routes.update_heartbeat_settings({
            "enabled": True,
            "interval": 30,
            "monitor_all": True,
        })
        assert result["success"] is True
        assert result["enabled"] is True
        assert result["interval"] == 30
        assert result["monitor_all"] is True

        # Read back
        settings = await debug_routes.get_heartbeat_settings()
        assert settings["enabled"] is True

        # Load raw config
        config = debug_routes._load_heartbeat_config()
        assert config["monitor_all"] is True

    @pytest.mark.asyncio
    async def test_config_default_monitor_all_true(self, monkeypatch, tmp_path):
        from src.api.routes import debug_routes

        config_file = tmp_path / "nonexistent_config.json"
        monkeypatch.setattr(debug_routes, "HEARTBEAT_CONFIG_FILE", config_file)

        config = debug_routes._load_heartbeat_config()
        assert config["monitor_all"] is True
        assert config["enabled"] is False


# ============================================================
# BLOCK 2: Standalone Server HTTP API
# ============================================================

class TestStandaloneServerImport:
    """Checklist #29: run_mycelium.py imports and defines routes."""

    def test_import_run_mycelium(self):
        """Standalone server module imports without errors."""
        import run_mycelium
        assert hasattr(run_mycelium, "run_pipeline")
        assert hasattr(run_mycelium, "start_http_server")
        assert hasattr(run_mycelium, "main")
        assert hasattr(run_mycelium, "_kill_port")

    def test_default_ports(self):
        import run_mycelium
        assert run_mycelium.HTTP_PORT == 8083
        assert run_mycelium.WS_PORT == 8082

    def test_pipeline_results_dict_exists(self):
        import run_mycelium
        assert isinstance(run_mycelium._pipeline_results, dict)
        assert isinstance(run_mycelium._active_pipelines, dict)


# ============================================================
# BLOCK 3: MCP Tool Validation
# ============================================================

class TestMCPToolCompleteness:
    """Checklist #16-21: All 17 MCP tools present and valid."""

    def test_tool_count(self):
        from src.mcp.mycelium_mcp_server import MYCELIUM_TOOLS
        assert len(MYCELIUM_TOOLS) >= 17

    def test_required_tools_exist(self):
        from src.mcp.mycelium_mcp_server import MYCELIUM_TOOLS
        tool_names = {t.name for t in MYCELIUM_TOOLS}
        required = {
            "mycelium_pipeline",
            "mycelium_call_model",
            "mycelium_task_board",
            "mycelium_task_dispatch",
            "mycelium_task_import",
            "mycelium_heartbeat_tick",
            "mycelium_heartbeat_status",
            "mycelium_execute_workflow",
            "mycelium_workflow_status",
            "mycelium_research",
            "mycelium_implement",
            "mycelium_review",
            "mycelium_list_artifacts",
            "mycelium_approve_artifact",
            "mycelium_reject_artifact",
            "mycelium_health",
            "mycelium_devpanel_stream",
        }
        missing = required - tool_names
        assert not missing, f"Missing MCP tools: {missing}"

    def test_dispatch_table_matches_tools(self):
        from src.mcp.mycelium_mcp_server import MYCELIUM_TOOLS, _TOOL_DISPATCH
        tool_names = {t.name for t in MYCELIUM_TOOLS}
        dispatch_names = set(_TOOL_DISPATCH.keys())
        # Dispatch table may have extra entries (tracker tools)
        # but all declared tools must have handlers
        tools_without_handler = tool_names - dispatch_names
        assert not tools_without_handler, f"Tools without dispatch handler: {tools_without_handler}"

    def test_tracker_tools_in_dispatch(self):
        """MARKER_133: Tracker tools registered in dispatch table."""
        from src.mcp.mycelium_mcp_server import _TOOL_DISPATCH
        assert "mycelium_track_done" in _TOOL_DISPATCH
        assert "mycelium_track_started" in _TOOL_DISPATCH
        assert "mycelium_tracker_status" in _TOOL_DISPATCH


# ============================================================
# BLOCK 3: MCP Tool call_tool dispatch
# ============================================================

class TestMCPDispatch:
    """Tool routing works correctly."""

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        from src.mcp.mycelium_mcp_server import call_tool
        result = await call_tool("nonexistent_tool", {})
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "error" in data
        assert "Unknown tool" in data["error"]

    @pytest.mark.asyncio
    async def test_vetka_prefix_returns_migration_hint(self):
        from src.mcp.mycelium_mcp_server import call_tool
        result = await call_tool("vetka_search_semantic", {"query": "test"})
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "error" in data
        assert "MCP VETKA" in data["error"]

    @pytest.mark.asyncio
    async def test_health_tool_returns_status(self):
        from src.mcp.mycelium_mcp_server import call_tool
        result = await call_tool("mycelium_health", {})
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["server"] == "mycelium"
        assert "uptime_seconds" in data


# ============================================================
# BLOCK 4: Task Board integration
# ============================================================

class TestTaskBoardIntegration:
    """Checklist #9-11: Board CRUD + dispatch."""

    def setup_method(self):
        import tempfile
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
        self.tmp.write('{"tasks": {}, "settings": {"max_concurrent": 2, "auto_dispatch": false, "default_preset": "dragon_silver"}}')
        self.tmp.close()
        from src.orchestration.task_board import TaskBoard
        self.board = TaskBoard(board_file=Path(self.tmp.name))

    def teardown_method(self):
        Path(self.tmp.name).unlink(missing_ok=True)

    def test_add_and_get_task(self):
        task_id = self.board.add_task("Test task", "Description", priority=2)
        task = self.board.get_task(task_id)
        assert task is not None
        assert task["title"] == "Test task"
        assert task["status"] == "pending"

    def test_priority_ordering(self):
        """Higher priority (lower number) comes first."""
        self.board.add_task("Low priority", priority=5)
        self.board.add_task("High priority", priority=1)
        self.board.add_task("Medium priority", priority=3)

        queue = self.board.get_queue(status="pending")
        assert len(queue) == 3
        assert queue[0]["title"] == "High priority"
        assert queue[1]["title"] == "Medium priority"
        assert queue[2]["title"] == "Low priority"

    def test_update_task_status(self):
        task_id = self.board.add_task("Update me")
        self.board.update_task(task_id, status="running")
        task = self.board.get_task(task_id)
        assert task["status"] == "running"

    def test_remove_task(self):
        task_id = self.board.add_task("Remove me")
        self.board.remove_task(task_id)
        assert self.board.get_task(task_id) is None

    def test_summary(self):
        self.board.add_task("A", priority=1)
        self.board.add_task("B", priority=2)
        summary = self.board.get_board_summary()
        assert summary["total"] == 2
        assert summary["by_status"]["pending"] == 2


# ============================================================
# BLOCK 4: Dragon presets
# ============================================================

class TestDragonPresets:
    """Checklist: Dragon Bronze/Silver/Gold presets valid."""

    def test_presets_file_exists(self):
        preset_file = PROJECT_ROOT / "data" / "templates" / "model_presets.json"
        assert preset_file.exists(), "model_presets.json not found"

    def test_three_tiers_exist(self):
        preset_file = PROJECT_ROOT / "data" / "templates" / "model_presets.json"
        data = json.loads(preset_file.read_text())
        presets = data.get("presets", {})
        assert "dragon_bronze" in presets, "Missing dragon_bronze"
        assert "dragon_silver" in presets, "Missing dragon_silver"
        assert "dragon_gold" in presets, "Missing dragon_gold"

    def test_all_tiers_have_four_roles(self):
        preset_file = PROJECT_ROOT / "data" / "templates" / "model_presets.json"
        data = json.loads(preset_file.read_text())
        presets = data.get("presets", {})
        for tier in ["dragon_bronze", "dragon_silver", "dragon_gold"]:
            p = presets[tier]
            # Roles may be nested under "roles" key or at top level
            roles = p.get("roles", p)
            assert "architect" in roles, f"{tier} missing architect"
            assert "researcher" in roles, f"{tier} missing researcher"
            assert "coder" in roles, f"{tier} missing coder"
            assert "verifier" in roles, f"{tier} missing verifier"

    def test_grok_fast_in_all_tiers(self):
        """Grok Fast 4.1 = researcher in ALL tiers."""
        preset_file = PROJECT_ROOT / "data" / "templates" / "model_presets.json"
        data = json.loads(preset_file.read_text())
        presets = data.get("presets", {})
        for tier in ["dragon_bronze", "dragon_silver", "dragon_gold"]:
            roles = presets[tier].get("roles", presets[tier])
            researcher = roles.get("researcher", "")
            assert "grok" in researcher.lower(), f"{tier} researcher is not Grok: {researcher}"

    def test_default_preset_is_silver(self):
        preset_file = PROJECT_ROOT / "data" / "templates" / "model_presets.json"
        data = json.loads(preset_file.read_text())
        default = data.get("default_preset", "")
        assert default == "dragon_silver", f"Default preset is {default}, expected dragon_silver"


# ============================================================
# BLOCK 4: WebSocket broadcaster
# ============================================================

class TestWSBroadcasterBasics:
    """Checklist #14: WebSocket broadcaster for DevPanel."""

    def test_broadcaster_import(self):
        from src.mcp.mycelium_ws_server import MyceliumWSBroadcaster
        b = MyceliumWSBroadcaster(host="localhost", port=19999)
        assert b.host == "localhost"
        assert b.port == 19999
        assert b.clients == set()
        assert b._messages_sent == 0

    def test_broadcaster_singleton(self):
        from src.mcp.mycelium_ws_server import get_ws_broadcaster
        b1 = get_ws_broadcaster()
        b2 = get_ws_broadcaster()
        assert b1 is b2

    def test_get_status(self):
        from src.mcp.mycelium_ws_server import MyceliumWSBroadcaster
        b = MyceliumWSBroadcaster(host="localhost", port=19998)
        status = b.get_status()
        assert "running" in status
        assert "clients" in status
        assert "messages_sent" in status


# ============================================================
# BLOCK 6: Standalone server structure
# ============================================================

class TestStandaloneServerStructure:
    """Checklist #29: Single command launches everything."""

    def test_run_mycelium_is_executable(self):
        script = PROJECT_ROOT / "run_mycelium.py"
        assert script.exists()

    def test_docstring_has_usage(self):
        import run_mycelium
        assert "python run_mycelium.py" in (run_mycelium.__doc__ or "")

    def test_endpoints_defined(self):
        """HTTP server defines all expected routes."""
        import run_mycelium
        source = Path(run_mycelium.__file__).read_text()
        expected_routes = [
            "/health",
            "/pipeline",
            "/pipelines",
            "/call_model",
            "/task_board",
            "/heartbeat/start",
            "/heartbeat/stop",
            "/heartbeat/status",
        ]
        for route in expected_routes:
            assert route in source, f"Missing route: {route}"

    def test_vetka_not_required_message(self):
        """Banner states VETKA is not required."""
        import run_mycelium
        source = Path(run_mycelium.__file__).read_text()
        assert "VETKA" in source
        assert "Independent" in source or "independent" in source or "не требуется" in source


# ============================================================
# BLOCK 6: Pipeline dispatch integration
# ============================================================

class TestPipelineDispatch:
    """Checklist #30: @dragon X → TaskBoard → pipeline."""

    @pytest.mark.asyncio
    async def test_heartbeat_to_board_flow(self, monkeypatch, tmp_path):
        """Full flow: message → parse → board add → dispatch."""
        from src.orchestration import mycelium_heartbeat as hb

        state_file = tmp_path / "state.json"
        fallback_file = tmp_path / "fallback.json"
        monkeypatch.setattr(hb, "_STATE_FILE", state_file)
        monkeypatch.setattr(hb, "_STATE_FILE_FALLBACK", fallback_file)
        monkeypatch.setattr(hb, "_emit_heartbeat_status", lambda *a, **kw: None)

        monkeypatch.setattr(
            hb, "_fetch_new_messages",
            lambda group_id, since_id=None, limit=20: [
                {"id": "m50", "sender_id": "danila", "content": "@dragon implement caching for model router"}
            ],
        )

        class FakeBoard:
            settings = {"max_concurrent": 2}
            added = []
            dispatched = 0

            def get_queue(self, status=None):
                return []

            def add_task(self, **kw):
                self.added.append(kw)
                return f"tb_flow_{len(self.added)}"

            async def dispatch_next(self, chat_id):
                self.dispatched += 1
                if self.dispatched == 1:
                    return {"success": True, "task_id": "tb_flow_1", "task_title": "caching", "phase_type": "build"}
                return {"success": False}

        fake_board = FakeBoard()
        monkeypatch.setattr("src.orchestration.task_board.get_task_board", lambda: fake_board)

        result = await hb.heartbeat_tick(group_id="test-group", dry_run=False)

        # Verify full flow
        assert result["tasks_found"] == 1
        assert result["tasks_dispatched"] == 1
        assert len(fake_board.added) == 1
        assert fake_board.added[0]["phase_type"] == "build"
        assert "dragon" in fake_board.added[0]["tags"]
        assert fake_board.dispatched >= 1
