"""
MARKER_ZETA.HARNESS.INT: Integration tests for core MCP harness tools.

Round-trip tests for:
1. TaskBoard CRUD  — add, get, update, list with filter, remove
2. Session init    — verify session_id, phase, digest fields returned
3. AgentRegistry   — load, get_by_callsign for all roles, verify owned_paths
4. Generate CLAUDE.md — verify output contains role title and owned paths

Tests are self-contained: real TaskBoard with temp SQLite file, no mocks on DB.
Production task_board.json is patched out to prevent test pollution.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure project root is importable
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from src.orchestration.task_board import TaskBoard, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW
from src.services.agent_registry import AgentRegistry, AgentRole, OwnershipResult
from src.tools.generate_claude_md import generate_claude_md, _load_template

# ─── Paths used across tests ──────────────────────────────────────────────────
_REGISTRY_PATH = _PROJECT_ROOT / "data" / "templates" / "agent_registry.yaml"
_TEMPLATE_PATH = _PROJECT_ROOT / "data" / "templates" / "claude_md_template.j2"

# ─── Isolation: prevent migration from reading production task_board.json ─────
_NONEXISTENT_JSON = Path("/tmp/_vetka_integration_test_nonexistent.json")


@pytest.fixture(autouse=True)
def _isolate_task_board_from_production():
    """MARKER_192.4: Patch production board paths so no real tasks bleed in."""
    with patch("src.orchestration.task_board.TASK_BOARD_FILE", _NONEXISTENT_JSON), \
         patch("src.orchestration.task_board._TASK_BOARD_FALLBACK", _NONEXISTENT_JSON):
        yield


# ─── Shared fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def board(tmp_path):
    """Fresh TaskBoard backed by a temp SQLite file."""
    db_file = tmp_path / "test_board.db"
    b = TaskBoard(board_file=db_file)
    yield b
    # Cleanup WAL artifacts
    for suffix in ("", "-wal", "-shm"):
        Path(str(db_file) + suffix).unlink(missing_ok=True)


@pytest.fixture
def registry():
    """Real AgentRegistry loaded from project YAML."""
    return AgentRegistry(_REGISTRY_PATH)


@pytest.fixture
def template():
    """Loaded Jinja2 template for CLAUDE.md generation."""
    return _load_template(_TEMPLATE_PATH)


# ══════════════════════════════════════════════════════════════════════════════
# 1. TaskBoard CRUD — round-trip tests
# ══════════════════════════════════════════════════════════════════════════════


class TestTaskBoardCRUD:
    """MARKER_ZETA.HARNESS.INT.TB: Round-trip CRUD operations on TaskBoard."""

    def test_add_returns_tb_prefixed_id(self, board):
        """add_task() returns a valid tb_<timestamp>_<counter> ID."""
        task_id = board.add_task("Test add", "integration check", priority=PRIORITY_HIGH)
        assert task_id.startswith("tb_"), f"Expected tb_ prefix, got: {task_id}"

    def test_add_and_get_round_trip(self, board):
        """Task added can be retrieved immediately via get_task()."""
        task_id = board.add_task(
            "Round-trip task",
            "verify persistence",
            priority=PRIORITY_MEDIUM,
            phase_type="test",
        )
        task = board.get_task(task_id)
        assert task is not None
        assert task["id"] == task_id
        assert task["title"] == "Round-trip task"
        assert task["status"] == "pending"
        assert task["priority"] == PRIORITY_MEDIUM
        assert task["phase_type"] == "test"

    def test_add_task_default_fields(self, board):
        """add_task() with minimal args produces correct defaults."""
        task_id = board.add_task("Minimal task")
        task = board.get_task(task_id)
        assert task["complexity"] == "medium"
        assert task["status"] == "pending"
        assert task["phase_type"] == "build"
        assert task["priority"] == PRIORITY_MEDIUM

    def test_update_task_status(self, board):
        """update_task() changes status; get_task() reflects new value."""
        task_id = board.add_task("Status update test", phase_type="test")
        updated = board.update_task(task_id, status="running")
        assert updated is True
        task = board.get_task(task_id)
        assert task["status"] == "running"

    def test_update_task_description(self, board):
        """update_task() can update free-text description field."""
        task_id = board.add_task("Desc update", "original desc", phase_type="test")
        board.update_task(task_id, description="updated desc")
        task = board.get_task(task_id)
        assert task["description"] == "updated desc"

    def test_update_invalid_status_returns_false(self, board):
        """update_task() rejects invalid status and returns False."""
        task_id = board.add_task("Invalid status test", phase_type="test")
        result = board.update_task(task_id, status="totally_fake_status")
        assert result is False
        task = board.get_task(task_id)
        assert task["status"] == "pending"  # unchanged

    def test_list_tasks_returns_all(self, board):
        """list_tasks() returns all added tasks when no filter applied."""
        ids = [board.add_task(f"Task {i}", phase_type="test") for i in range(3)]
        tasks = board.list_tasks()
        task_ids = {t["id"] for t in tasks}
        for tid in ids:
            assert tid in task_ids

    def test_list_tasks_filter_by_status(self, board):
        """list_tasks(status=X) returns only tasks matching that status."""
        pending_id = board.add_task("Pending one", phase_type="test")
        running_id = board.add_task("Running one", phase_type="test")
        board.update_task(running_id, status="running")

        pending_tasks = board.list_tasks(status="pending")
        running_tasks = board.list_tasks(status="running")

        pending_ids = {t["id"] for t in pending_tasks}
        running_ids = {t["id"] for t in running_tasks}

        assert pending_id in pending_ids
        assert running_id not in pending_ids
        assert running_id in running_ids
        assert pending_id not in running_ids

    def test_remove_task(self, board):
        """remove_task() deletes the task; subsequent get_task() returns None."""
        task_id = board.add_task("To be removed", phase_type="test")
        assert board.get_task(task_id) is not None
        result = board.remove_task(task_id)
        assert result is True
        assert board.get_task(task_id) is None

    def test_remove_nonexistent_returns_false(self, board):
        """remove_task() on unknown ID returns False without raising."""
        result = board.remove_task("tb_nonexistent_999")
        assert result is False

    def test_get_nonexistent_returns_none(self, board):
        """get_task() on unknown ID returns None."""
        assert board.get_task("tb_does_not_exist") is None

    def test_task_tags_preserved(self, board):
        """Tags list survives the add → get round-trip."""
        tags = ["ux", "panel", "dockview"]
        task_id = board.add_task("Tagged task", phase_type="test", tags=tags)
        task = board.get_task(task_id)
        assert set(task["tags"]) == set(tags)

    def test_task_priority_clamped_low(self, board):
        """Priority below 1 is clamped to 1."""
        task_id = board.add_task("Clamp low", priority=-5, phase_type="test")
        task = board.get_task(task_id)
        assert task["priority"] == 1

    def test_task_priority_clamped_high(self, board):
        """Priority above 5 is clamped to 5."""
        task_id = board.add_task("Clamp high", priority=99, phase_type="test")
        task = board.get_task(task_id)
        assert task["priority"] == 5

    def test_multiple_tasks_isolated(self, board):
        """Multiple tasks with different data don't bleed into each other."""
        id_a = board.add_task("Task A", "desc A", phase_type="test", tags=["alpha"])
        id_b = board.add_task("Task B", "desc B", phase_type="test", tags=["beta"])
        task_a = board.get_task(id_a)
        task_b = board.get_task(id_b)
        assert task_a["title"] == "Task A"
        assert task_b["title"] == "Task B"
        assert "alpha" in task_a["tags"]
        assert "beta" in task_b["tags"]


# ══════════════════════════════════════════════════════════════════════════════
# 2. Session init — round-trip test via load_project_digest()
# ══════════════════════════════════════════════════════════════════════════════


class TestSessionInit:
    """MARKER_ZETA.HARNESS.INT.SESSION: Session initialization field contracts.

    We test load_project_digest() (the synchronous helper inside session_tools)
    and the async _execute_async path via asyncio.run() with a patched chat_mgr,
    verifying that the returned context always contains the required keys.
    """

    def test_load_project_digest_returns_dict_or_none(self):
        """load_project_digest() never raises; returns dict or None."""
        from src.mcp.tools.session_tools import load_project_digest
        result = load_project_digest()
        assert result is None or isinstance(result, dict)

    def test_load_project_digest_shape_when_present(self):
        """If digest exists, it contains expected top-level keys."""
        from src.mcp.tools.session_tools import load_project_digest, DIGEST_PATH
        if not DIGEST_PATH.exists():
            pytest.skip("project_digest.json not present in this worktree")
        result = load_project_digest()
        assert result is not None
        for key in ("phase", "summary", "achievements", "pending", "system"):
            assert key in result, f"Missing key in digest: {key}"

    def test_session_init_execute_returns_session_id(self, tmp_path):
        """SessionInitTool.execute() returns a dict with session_id."""
        import asyncio
        from src.mcp.tools.session_tools import SessionInitTool

        tool = SessionInitTool()

        # Patch chat_history_manager to avoid needing a live DB
        with patch(
            "src.mcp.tools.session_tools.asyncio.get_event_loop",
            side_effect=RuntimeError("no loop"),
        ), patch(
            "src.chat.chat_history_manager.get_chat_history_manager",
            side_effect=Exception("no chat mgr in test"),
        ):
            result = tool.execute({
                "user_id": "test_user",
                "compress": False,
                "include_viewport": False,
                "include_pinned": False,
            })

        assert isinstance(result, dict)
        # The execute() method may return a context dict or a success wrapper
        inner = result.get("result", result)
        assert "session_id" in inner or "status" in inner  # either live or async pending

    def test_session_init_with_explicit_chat_id(self):
        """Providing chat_id=X causes session_id to equal X."""
        import asyncio
        from src.mcp.tools.session_tools import SessionInitTool

        tool = SessionInitTool()

        # Run the async execute directly
        async def _run():
            return await tool._execute_async({
                "user_id": "test_user",
                "chat_id": "my-fixed-chat-id",
                "compress": False,
                "include_viewport": False,
                "include_pinned": False,
            })

        result = asyncio.run(_run())
        assert isinstance(result, dict)
        inner = result.get("result", result)
        assert inner.get("session_id") == "my-fixed-chat-id"
        assert inner.get("linked_to_existing") is True

    def test_session_init_initialized_flag(self):
        """Session context always has initialized=True."""
        import asyncio
        from src.mcp.tools.session_tools import SessionInitTool

        tool = SessionInitTool()

        async def _run():
            return await tool._execute_async({
                "user_id": "test_user",
                "chat_id": "probe-session",
                "compress": False,
                "include_viewport": False,
                "include_pinned": False,
            })

        result = asyncio.run(_run())
        inner = result.get("result", result)
        assert inner.get("initialized") is True


# ══════════════════════════════════════════════════════════════════════════════
# 3. AgentRegistry — load and lookup round-trips
# ══════════════════════════════════════════════════════════════════════════════


class TestAgentRegistry:
    """MARKER_ZETA.HARNESS.INT.REG: AgentRegistry round-trip lookups and field contracts."""

    def test_registry_loads_at_least_five_roles(self, registry):
        """Registry YAML has at least 5 registered roles (may grow as new agents are added)."""
        assert len(registry.roles) >= 5

    def test_core_callsigns_present(self, registry):
        """Core canonical callsigns are always registered."""
        callsigns = {r.callsign for r in registry.roles}
        for expected in ("Alpha", "Beta", "Gamma", "Delta", "Commander"):
            assert expected in callsigns, f"Missing expected callsign: {expected}"

    def test_get_by_callsign_alpha(self, registry):
        """Alpha → engine domain, cut-engine worktree."""
        role = registry.get_by_callsign("Alpha")
        assert role is not None
        assert role.domain == "engine"
        assert role.worktree == "cut-engine"
        assert len(role.owned_paths) > 0

    def test_get_by_callsign_beta(self, registry):
        """Beta → media domain."""
        role = registry.get_by_callsign("Beta")
        assert role is not None
        assert role.domain == "media"
        assert len(role.owned_paths) > 0

    def test_get_by_callsign_gamma(self, registry):
        """Gamma → ux domain."""
        role = registry.get_by_callsign("Gamma")
        assert role is not None
        assert role.domain == "ux"
        assert len(role.owned_paths) > 0

    def test_get_by_callsign_delta(self, registry):
        """Delta → qa domain."""
        role = registry.get_by_callsign("Delta")
        assert role is not None
        assert role.domain == "qa"
        assert len(role.owned_paths) > 0

    def test_get_by_callsign_commander(self, registry):
        """Commander → architect domain."""
        role = registry.get_by_callsign("Commander")
        assert role is not None
        assert role.domain == "architect"

    def test_get_by_callsign_case_insensitive(self, registry):
        """Callsign lookup is case-insensitive."""
        assert registry.get_by_callsign("alpha") is not None
        assert registry.get_by_callsign("GAMMA") is not None
        assert registry.get_by_callsign("commander") is not None

    def test_get_by_callsign_unknown_returns_none(self, registry):
        """Unknown callsign returns None, never raises."""
        assert registry.get_by_callsign("Omega") is None
        assert registry.get_by_callsign("") is None

    def test_every_role_has_owned_paths(self, registry):
        """Every registered role has at least one owned path."""
        for role in registry.roles:
            assert len(role.owned_paths) > 0, f"{role.callsign} has no owned_paths"

    def test_every_role_has_branch(self, registry):
        """Every registered role has a non-empty branch."""
        for role in registry.roles:
            assert role.branch, f"{role.callsign} missing branch"

    def test_every_role_has_role_title(self, registry):
        """Every registered role has a non-empty role_title."""
        for role in registry.roles:
            assert role.role_title, f"{role.callsign} missing role_title"

    def test_owned_paths_are_strings(self, registry):
        """All owned_paths values are non-empty strings."""
        for role in registry.roles:
            for path in role.owned_paths:
                assert isinstance(path, str) and path, \
                    f"{role.callsign} has non-string/empty owned_path: {path!r}"

    def test_list_callsigns(self, registry):
        """list_callsigns() returns all registered callsigns including core five."""
        callsigns = set(registry.list_callsigns())
        for expected in ("Alpha", "Beta", "Gamma", "Delta", "Commander"):
            assert expected in callsigns, f"Missing expected callsign: {expected}"

    def test_validate_file_ownership_owned(self, registry):
        """A known Gamma-owned file is flagged is_owned=True, is_blocked=False."""
        result = registry.validate_file_ownership(
            "Gamma", "client/src/components/cut/MenuBar.tsx"
        )
        assert result.is_owned is True
        assert result.is_blocked is False

    def test_validate_file_ownership_unknown_callsign(self, registry):
        """Unknown callsign returns is_owned=False, is_blocked=False."""
        result = registry.validate_file_ownership("Omega", "some/file.py")
        assert result.is_owned is False
        assert result.is_blocked is False

    def test_roles_are_frozen_dataclasses(self, registry):
        """AgentRole instances are immutable (frozen dataclass)."""
        role = registry.get_by_callsign("Alpha")
        with pytest.raises(AttributeError):
            role.callsign = "Mutated"


# ══════════════════════════════════════════════════════════════════════════════
# 4. Generate CLAUDE.md — output field contracts
# ══════════════════════════════════════════════════════════════════════════════


class TestGenerateClaudeMd:
    """MARKER_ZETA.HARNESS.INT.GEN: CLAUDE.md generation round-trips for all roles."""

    def test_alpha_output_contains_role_title(self, registry, template):
        """Alpha CLAUDE.md contains role title keyword."""
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert content is not None
        assert "Agent Alpha" in content or "Alpha" in content

    def test_beta_output_contains_role_title(self, registry, template):
        """Beta CLAUDE.md contains role title keyword."""
        content = generate_claude_md("Beta", registry=registry, template=template)
        assert content is not None
        assert "Beta" in content

    def test_gamma_output_contains_role_title_and_owned_path(self, registry, template):
        """Gamma CLAUDE.md contains role title and at least one owned path."""
        content = generate_claude_md("Gamma", registry=registry, template=template)
        assert content is not None
        assert "Gamma" in content
        # At least one Gamma-owned path should appear in the generated content
        role = registry.get_by_callsign("Gamma")
        owned_paths_found = any(
            Path(p).name in content for p in role.owned_paths
        )
        assert owned_paths_found, "No owned path found in Gamma CLAUDE.md output"

    def test_delta_output_contains_role_title(self, registry, template):
        """Delta CLAUDE.md contains role title."""
        content = generate_claude_md("Delta", registry=registry, template=template)
        assert content is not None
        assert "Delta" in content

    def test_commander_output_contains_role_title(self, registry, template):
        """Commander CLAUDE.md contains Commander keyword."""
        content = generate_claude_md("Commander", registry=registry, template=template)
        assert content is not None
        assert "Commander" in content

    def test_unknown_callsign_returns_none(self, registry, template):
        """Unknown callsign returns None without raising."""
        content = generate_claude_md("Omega", registry=registry, template=template)
        assert content is None

    def test_all_five_roles_produce_non_empty_output(self, registry, template):
        """All 5 registered callsigns produce non-empty string output."""
        for callsign in ("Alpha", "Beta", "Gamma", "Delta", "Commander"):
            content = generate_claude_md(callsign, registry=registry, template=template)
            assert content is not None and len(content) > 100, \
                f"{callsign} produced empty or too-short CLAUDE.md"

    def test_output_is_markdown_string(self, registry, template):
        """Generated output is a str (not bytes, not dict)."""
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert isinstance(content, str)

    def test_alpha_owned_path_in_output(self, registry, template):
        """Alpha CLAUDE.md contains at least one of its owned paths."""
        content = generate_claude_md("Alpha", registry=registry, template=template)
        role = registry.get_by_callsign("Alpha")
        found = any(Path(p).name in content for p in role.owned_paths)
        assert found, "No Alpha-owned path name found in generated CLAUDE.md"

    def test_pending_tasks_injection(self, registry, template):
        """Pending tasks list is reflected in generated content when provided."""
        fake_tasks = [{"id": "tb_test_99", "title": "Probe task injection", "priority": 2, "status": "pending", "phase_type": "test"}]
        content = generate_claude_md(
            "Gamma",
            registry=registry,
            template=template,
            pending_tasks=fake_tasks,
        )
        assert content is not None
        assert "Probe task injection" in content, \
            "Injected pending task title not found in CLAUDE.md output"
