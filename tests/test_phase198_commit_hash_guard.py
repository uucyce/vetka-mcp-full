"""Phase 198 tests: commit_hash guard for done_worktree.

MARKER_198.GUARD: Agents must provide commit_hash to reach done_worktree.
Prevents phantom task closures that waste QA cycles.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.orchestration.task_board import TaskBoard

_NONEXISTENT = Path("/tmp/_vetka_test_nonexistent_board.json")


@pytest.fixture(autouse=True)
def _isolate_task_board_from_production():
    with patch("src.orchestration.task_board.TASK_BOARD_FILE", _NONEXISTENT), \
         patch("src.orchestration.task_board._TASK_BOARD_FALLBACK", _NONEXISTENT):
        yield


def _board(tmp_path):
    return TaskBoard(board_file=tmp_path / "task_board.json")


# --- complete_task guard ---

def test_complete_rejects_done_worktree_without_commit_hash(tmp_path):
    """action=complete on a worktree branch without commit_hash must fail."""
    board = _board(tmp_path)
    tid = board.add_task(title="Test task")
    board.claim_task(tid, "agent", "claude_code")

    result = board.complete_task(tid, branch="claude/harness")

    assert result["success"] is False
    assert "commit_hash" in result["error"]
    # Task status must NOT have changed
    assert board.get_task(tid)["status"] == "claimed"


def test_complete_allows_done_worktree_with_commit_hash(tmp_path):
    """action=complete with commit_hash should succeed."""
    board = _board(tmp_path)
    tid = board.add_task(title="Test task")
    board.claim_task(tid, "agent", "claude_code")

    result = board.complete_task(tid, commit_hash="abc123", branch="claude/harness")

    assert result["success"] is True
    assert board.get_task(tid)["status"] == "done_worktree"


def test_complete_allows_done_worktree_with_manual_override(tmp_path):
    """manual_override=True bypasses the commit_hash requirement."""
    board = _board(tmp_path)
    tid = board.add_task(title="Test task")
    board.claim_task(tid, "agent", "claude_code")

    result = board.complete_task(
        tid, branch="claude/harness",
        manual_override=True, override_reason="research task, no code"
    )

    assert result["success"] is True
    assert board.get_task(tid)["status"] == "done_worktree"


def test_complete_done_main_does_not_require_commit_hash(tmp_path):
    """Completing on main (done_main) should work without commit_hash."""
    board = _board(tmp_path)
    tid = board.add_task(title="Test task")
    board.claim_task(tid, "agent", "claude_code")

    result = board.complete_task(tid, branch="main")

    assert result["success"] is True
    assert board.get_task(tid)["status"] == "done_main"


# --- update_task guard ---

def test_update_blocks_done_worktree_without_commit_hash(tmp_path):
    """Raw update_task to done_worktree without commit_hash must be blocked."""
    board = _board(tmp_path)
    tid = board.add_task(title="Test task")
    board.claim_task(tid, "agent", "claude_code")

    result = board.update_task(tid, status="done_worktree")

    assert result is False
    assert board.get_task(tid)["status"] == "claimed"


def test_update_allows_done_worktree_with_commit_hash_in_update(tmp_path):
    """update_task with commit_hash in same call should pass."""
    board = _board(tmp_path)
    tid = board.add_task(title="Test task")
    board.claim_task(tid, "agent", "claude_code")

    result = board.update_task(tid, status="done_worktree", commit_hash="def456")

    assert result is True
    assert board.get_task(tid)["status"] == "done_worktree"


def test_update_allows_done_worktree_with_preexisting_commit_hash(tmp_path):
    """If task already has commit_hash, update to done_worktree should pass."""
    board = _board(tmp_path)
    tid = board.add_task(title="Test task")
    board.claim_task(tid, "agent", "claude_code")
    board.update_task(tid, commit_hash="pre789")

    result = board.update_task(tid, status="done_worktree")

    assert result is True
    assert board.get_task(tid)["status"] == "done_worktree"
