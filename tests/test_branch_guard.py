"""
MARKER_201.BRANCH_GUARD — Branch protection guard tests

Tests:
1. Branch mismatch produces warning in logs (warn-mode)
2. Tasks without role field are unaffected (no warning)
3. Matching branch produces no warning
4. Role not in registry — guard skips silently
5. Completion still succeeds despite branch mismatch (warn-mode)
"""

import logging
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def _make_board(tmp_path):
    """Create a TaskBoard with tmp storage."""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.orchestration.task_board import TaskBoard
    return TaskBoard(board_file=tmp_path / "board.json")


def _make_mock_role(callsign="Alpha", branch="claude/cut-engine"):
    """Create a mock AgentRole."""
    role = MagicMock()
    role.callsign = callsign
    role.branch = branch
    return role


def _patch_registry(role=None):
    """Return a context manager that patches get_agent_registry in the task_board module.

    Uses sys.modules injection to avoid importing the real agent_registry
    (which requires yaml dependency not available in test env).
    """
    mock_module = MagicMock()
    mock_registry = MagicMock()
    mock_registry.get_by_callsign.return_value = role
    mock_module.get_agent_registry.return_value = mock_registry
    return patch.dict(sys.modules, {"src.services.agent_registry": mock_module})


# ── Test 1: Branch mismatch produces warning ─────────────────

def test_branch_mismatch_warns(tmp_path, caplog):
    """complete_task should log a BRANCH_GUARD warning when branch doesn't match role."""
    board = _make_board(tmp_path)
    tid = board.add_task("Test branch guard", priority=3)
    board.update_task(tid, status="claimed", role="Alpha")

    mock_role = _make_mock_role(callsign="Alpha", branch="claude/cut-engine")

    with patch("src.orchestration.task_board.TaskBoard._detect_current_branch", return_value="claude/wrong-branch"), \
         _patch_registry(role=mock_role):
        with caplog.at_level(logging.WARNING):
            result = board.complete_task(
                tid,
                commit_hash="abc123",
                commit_message="test commit",
            )

    assert result["success"] is True  # warn-mode: still succeeds
    assert any("BRANCH_GUARD" in record.message for record in caplog.records)
    assert any("claude/cut-engine" in record.message for record in caplog.records)


# ── Test 2: No role field — guard skipped ────────────────────

def test_no_role_no_warning(tmp_path, caplog):
    """Tasks without role field should not trigger branch guard."""
    board = _make_board(tmp_path)
    tid = board.add_task("Task without role", priority=3)
    board.update_task(tid, status="claimed")

    with patch("src.orchestration.task_board.TaskBoard._detect_current_branch", return_value="claude/some-branch"):
        with caplog.at_level(logging.WARNING):
            result = board.complete_task(
                tid,
                commit_hash="abc123",
                commit_message="test commit",
            )

    assert result["success"] is True
    assert not any("BRANCH_GUARD" in record.message for record in caplog.records)


# ── Test 3: Matching branch — no warning ─────────────────────

def test_matching_branch_no_warning(tmp_path, caplog):
    """When branch matches role's expected branch, no warning should be logged."""
    board = _make_board(tmp_path)
    tid = board.add_task("Test matching branch", priority=3)
    board.update_task(tid, status="claimed", role="Alpha")

    mock_role = _make_mock_role(callsign="Alpha", branch="claude/cut-engine")

    with patch("src.orchestration.task_board.TaskBoard._detect_current_branch", return_value="claude/cut-engine"), \
         _patch_registry(role=mock_role):
        with caplog.at_level(logging.WARNING):
            result = board.complete_task(
                tid,
                commit_hash="abc123",
                commit_message="test commit",
            )

    assert result["success"] is True
    assert not any("BRANCH_GUARD" in record.message for record in caplog.records)


# ── Test 4: Role not in registry — guard skips ───────────────

def test_unknown_role_skips_guard(tmp_path, caplog):
    """If role is not found in agent_registry, guard should skip silently."""
    board = _make_board(tmp_path)
    tid = board.add_task("Task with unknown role", priority=3)
    board.update_task(tid, status="claimed", role="UnknownAgent")

    with patch("src.orchestration.task_board.TaskBoard._detect_current_branch", return_value="claude/some-branch"), \
         _patch_registry(role=None):
        with caplog.at_level(logging.WARNING):
            result = board.complete_task(
                tid,
                commit_hash="abc123",
                commit_message="test commit",
            )

    assert result["success"] is True
    assert not any("BRANCH_GUARD" in record.message for record in caplog.records)


# ── Test 5: Mismatch still completes (warn-mode proof) ───────

def test_mismatch_still_completes_done_worktree(tmp_path):
    """Branch mismatch in warn-mode should still result in done_worktree status."""
    board = _make_board(tmp_path)
    tid = board.add_task("Test warn-mode completion", priority=3)
    board.update_task(tid, status="claimed", role="Alpha")

    mock_role = _make_mock_role(callsign="Alpha", branch="claude/cut-engine")

    with patch("src.orchestration.task_board.TaskBoard._detect_current_branch", return_value="claude/wrong-branch"), \
         _patch_registry(role=mock_role):
        result = board.complete_task(
            tid,
            commit_hash="abc123",
            commit_message="test commit",
        )

    assert result["success"] is True
    assert result["status"] == "done_worktree"
    task = board.get_task(tid)
    assert task["status"] == "done_worktree"
