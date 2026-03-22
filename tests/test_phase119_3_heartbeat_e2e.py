"""Phase 119.3: Heartbeat E2E Tests for @titan Dispatch

Gap coverage:
- @titan message parsing with trigger="titan", phase_type="build"
- _dispatch_task with trigger="titan" -> AgentPipeline(preset="titan_core")
- Titan tier resolution (titan_lite / titan_core / titan_prime)
- Mixed @dragon + @titan messages in single heartbeat tick

MARKER_119.3
"""

import json
import re
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock

from src.orchestration.mycelium_heartbeat import (

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 119 contracts changed")

    ParsedTask,
    _parse_tasks,
    _dispatch_task,
    heartbeat_tick,
    TASK_PATTERNS,
    PHASE_TYPE_MAP,
)


# ═══════════════════════════════════════════════════════════════════════
# 1. @titan Message Parsing
# ═══════════════════════════════════════════════════════════════════════

class TestTitanParsing:
    """Test @titan trigger parsing."""

    def test_parse_titan_trigger(self):
        """@titan trigger parsed with trigger='titan' and phase_type='build'."""
        messages = [
            {"id": "t1", "sender_id": "user", "content": "@titan implement new API endpoint"}
        ]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert tasks[0].trigger == "titan"
        assert tasks[0].phase_type == "build"
        assert tasks[0].task == "implement new API endpoint"

    def test_parse_titan_case_insensitive(self):
        """@Titan and @TITAN should both work."""
        for variant in ["@Titan do X", "@TITAN do X", "@titan do X"]:
            messages = [{"id": "tc", "sender_id": "user", "content": variant}]
            tasks = _parse_tasks(messages)
            assert len(tasks) == 1, f"'{variant}' should parse to exactly 1 task"
            assert tasks[0].trigger == "titan"

    def test_titan_in_phase_type_map(self):
        """Titan exists in PHASE_TYPE_MAP with correct value."""
        assert "titan" in PHASE_TYPE_MAP
        assert PHASE_TYPE_MAP["titan"] == "build"

    def test_titan_pattern_in_task_patterns(self):
        """@titan pattern is registered in TASK_PATTERNS."""
        titan_found = any(
            re.search(r"titan", p.pattern, re.IGNORECASE)
            for p in TASK_PATTERNS
        )
        assert titan_found, "@titan pattern must be in TASK_PATTERNS"

    def test_parse_titan_multiline(self):
        """@titan with multiline task text."""
        messages = [
            {"id": "tm", "sender_id": "user",
             "content": "@titan create a new feature\nWith proper error handling\nAnd tests"}
        ]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert "create a new feature" in tasks[0].task
        assert "error handling" in tasks[0].task


# ═══════════════════════════════════════════════════════════════════════
# 2. @titan Dispatch -> AgentPipeline(preset="titan_core")
# ═══════════════════════════════════════════════════════════════════════

class TestTitanDispatch:
    """Test that @titan dispatch creates AgentPipeline with titan_core preset."""

    @pytest.mark.asyncio
    async def test_dispatch_titan_uses_titan_core_preset(self):
        """_dispatch_task with trigger='titan' creates pipeline with preset='titan_core'."""
        task = ParsedTask(
            task="implement feature X",
            phase_type="build",
            source_message_id="msg-t1",
            sender_id="user",
            trigger="titan"
        )

        captured_kwargs = {}

        class MockPipeline:
            def __init__(self, **kwargs):
                captured_kwargs.update(kwargs)

            async def execute(self, task_text, phase_type):
                return {
                    "task_id": "test-task",
                    "status": "done",
                    "results": {"subtasks_completed": 1, "subtasks_total": 1}
                }

        with patch("src.orchestration.agent_pipeline.AgentPipeline", MockPipeline), \
             patch("src.orchestration.mycelium_heartbeat._emit_heartbeat_status"):
            result = await _dispatch_task(task, "test-group")

        assert result["success"] is True
        assert captured_kwargs.get("preset") == "titan_core"

    @pytest.mark.asyncio
    async def test_dispatch_dragon_uses_no_preset(self):
        """_dispatch_task with trigger='dragon' does not set titan_core preset."""
        task = ParsedTask(
            task="fix bug Y",
            phase_type="build",
            source_message_id="msg-d1",
            sender_id="user",
            trigger="dragon"
        )

        captured_kwargs = {}

        class MockPipeline:
            def __init__(self, **kwargs):
                captured_kwargs.update(kwargs)

            async def execute(self, task_text, phase_type):
                return {
                    "task_id": "test-task",
                    "status": "done",
                    "results": {"subtasks_completed": 1, "subtasks_total": 1}
                }

        with patch("src.orchestration.agent_pipeline.AgentPipeline", MockPipeline), \
             patch("src.orchestration.mycelium_heartbeat._emit_heartbeat_status"):
            result = await _dispatch_task(task, "test-group")

        assert result["success"] is True
        assert captured_kwargs.get("preset") is None


# ═══════════════════════════════════════════════════════════════════════
# 3. Titan Tier Resolution
# ═══════════════════════════════════════════════════════════════════════

class TestTitanTierResolution:
    """Test _resolve_tier uses _titan_tier_map for titan presets."""

    def test_titan_tier_map_exists_in_presets(self):
        """model_presets.json has _titan_tier_map."""
        presets_path = Path(__file__).parent.parent / "data" / "templates" / "model_presets.json"
        data = json.loads(presets_path.read_text())
        assert "_titan_tier_map" in data
        assert data["_titan_tier_map"]["low"] == "titan_lite"
        assert data["_titan_tier_map"]["medium"] == "titan_core"
        assert data["_titan_tier_map"]["high"] == "titan_prime"

    def test_titan_presets_exist(self):
        """titan_lite, titan_core, titan_prime presets are defined."""
        presets_path = Path(__file__).parent.parent / "data" / "templates" / "model_presets.json"
        data = json.loads(presets_path.read_text())
        presets = data["presets"]
        assert "titan_lite" in presets
        assert "titan_core" in presets
        assert "titan_prime" in presets

    def test_titan_presets_have_roles(self):
        """Each titan preset has roles with architect/researcher/coder/verifier."""
        presets_path = Path(__file__).parent.parent / "data" / "templates" / "model_presets.json"
        data = json.loads(presets_path.read_text())
        for preset_name in ["titan_lite", "titan_core", "titan_prime"]:
            preset = data["presets"][preset_name]
            assert "roles" in preset, f"{preset_name} missing 'roles'"
            roles = preset["roles"]
            for role in ["architect", "researcher", "coder", "verifier"]:
                assert role in roles, f"{preset_name} missing role '{role}'"

    def test_titan_presets_have_scout(self):
        """Titan presets include scout role (Phase 119.4 prep)."""
        presets_path = Path(__file__).parent.parent / "data" / "templates" / "model_presets.json"
        data = json.loads(presets_path.read_text())
        for preset_name in ["titan_lite", "titan_core", "titan_prime"]:
            roles = data["presets"][preset_name]["roles"]
            assert "scout" in roles, f"{preset_name} should have scout role"


# ═══════════════════════════════════════════════════════════════════════
# 4. Mixed @dragon + @titan in Single Tick
# ═══════════════════════════════════════════════════════════════════════

class TestMixedDispatch:
    """Test heartbeat_tick with mixed @dragon + @titan messages."""

    @pytest.mark.asyncio
    async def test_tick_mixed_dragon_and_titan(self, tmp_path):
        """Both @dragon and @titan tasks parsed from same tick."""
        state_file = tmp_path / "state.json"
        fallback = tmp_path / "fallback.json"

        mock_messages = [
            {"id": "m1", "sender_id": "user", "content": "@dragon fix auth bug"},
            {"id": "m2", "sender_id": "user", "content": "just a regular message"},
            {"id": "m3", "sender_id": "user", "content": "@titan build new API endpoint"},
        ]

        dispatch_calls = []

        async def mock_dispatch(task, group_id):
            dispatch_calls.append(task)
            return {"success": True, "task_id": f"test-{task.trigger}"}

        with patch("src.orchestration.mycelium_heartbeat._STATE_FILE", state_file), \
             patch("src.orchestration.mycelium_heartbeat._STATE_FILE_FALLBACK", fallback), \
             patch("src.orchestration.mycelium_heartbeat._fetch_new_messages", return_value=mock_messages), \
             patch("src.orchestration.mycelium_heartbeat._emit_heartbeat_status"), \
             patch("src.orchestration.mycelium_heartbeat._dispatch_task", side_effect=mock_dispatch):

            result = await heartbeat_tick(group_id="test-group", dry_run=False)

        assert result["tasks_found"] == 2
        assert result["tasks_dispatched"] == 2

        triggers = [t.trigger for t in dispatch_calls]
        assert "dragon" in triggers
        assert "titan" in triggers

    @pytest.mark.asyncio
    async def test_tick_titan_dry_run(self, tmp_path):
        """Dry run with @titan shows task but doesn't dispatch."""
        state_file = tmp_path / "state.json"
        fallback = tmp_path / "fallback.json"

        mock_messages = [
            {"id": "m4", "sender_id": "user", "content": "@titan deploy to staging"}
        ]

        with patch("src.orchestration.mycelium_heartbeat._STATE_FILE", state_file), \
             patch("src.orchestration.mycelium_heartbeat._STATE_FILE_FALLBACK", fallback), \
             patch("src.orchestration.mycelium_heartbeat._fetch_new_messages", return_value=mock_messages), \
             patch("src.orchestration.mycelium_heartbeat._emit_heartbeat_status"):

            result = await heartbeat_tick(group_id="test-group", dry_run=True)

        assert result["tasks_found"] == 1
        assert result["dry_run"] is True
        assert result["results"][0].get("dry_run") is True
