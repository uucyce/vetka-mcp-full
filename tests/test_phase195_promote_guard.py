"""
Phase 195.1 — Promote-to-main Guard Tests

MARKER_195.1: Prevent false done_main when commits are not on main branch.
MARKER_195.20: _detect_current_branch accepts cwd override for worktree-correct detection.

Tests:
1. promote_to_main rejects when commit is not on main (git merge-base fails)
2. promote_to_main succeeds when commit IS on main
3. promote_to_main rejects wrong status (not done_worktree)
4. _detect_current_branch returns None on failure (not "main")
5. _is_commit_on_main returns False on subprocess error
6. Hook dedup: only .git/hooks/post-merge should exist
7. complete_task with None branch → done_worktree (safe default)
8. promote uses task's stored commit hash
9. _detect_current_branch passes cwd to subprocess
10. complete_task with worktree_path uses it for branch detection
11. complete_task worktree_path detects worktree branch → done_worktree
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def _make_board(tmp_path):
    """Create a TaskBoard with tmp storage."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.orchestration.task_board import TaskBoard
    return TaskBoard(board_file=tmp_path / "board.json")


# ── Test 1: promote_to_main rejects unmerged commit ──────────────

def test_promote_rejects_unmerged_commit(tmp_path):
    """promote_to_main should refuse when commit is NOT on main."""
    board = _make_board(tmp_path)
    tid = board.add_task("Test worktree task", priority=3)
    board.update_task(tid, status="done_worktree", commit_hash="abc123def")

    with patch.object(type(board), '_is_commit_on_main', return_value=False):
        result = board.promote_to_main(tid, merge_commit_hash="abc123def")

    assert result["success"] is False
    assert "NOT on main" in result["error"]
    # Task should remain done_worktree
    task = board.get_task(tid)
    assert task["status"] == "done_worktree"


# ── Test 2: promote_to_main succeeds when commit is on main ─────

def test_promote_succeeds_when_on_main(tmp_path):
    """promote_to_main should succeed when commit IS on main."""
    board = _make_board(tmp_path)
    tid = board.add_task("Test merged task", priority=3)
    board.update_task(tid, status="done_worktree", commit_hash="abc123def")

    with patch.object(type(board), '_is_commit_on_main', return_value=True):
        result = board.promote_to_main(tid, merge_commit_hash="merge456")

    assert result["success"] is True
    assert result["status"] == "done_main"
    task = board.get_task(tid)
    assert task["status"] == "done_main"
    assert task["commit_hash"] == "merge456"


# ── Test 3: promote_to_main rejects wrong status ────────────────

def test_promote_rejects_wrong_status(tmp_path):
    """promote_to_main should reject tasks not in done_worktree/done."""
    board = _make_board(tmp_path)
    tid = board.add_task("Pending task", priority=3)
    # Task is still 'pending'

    result = board.promote_to_main(tid)
    assert result["success"] is False
    assert "expected done_worktree" in result["error"]


# ── Test 4: _detect_current_branch returns None on failure ───────

def test_detect_branch_returns_none_on_failure(tmp_path):
    """_detect_current_branch should return None, not 'main', on failure."""
    from src.orchestration.task_board import TaskBoard

    with patch('subprocess.run', side_effect=Exception("git not found")):
        result = TaskBoard._detect_current_branch()

    assert result is None, f"Expected None on failure, got '{result}' — silent fallback to 'main' would cause false done_main"


# ── Test 5: _is_commit_on_main returns False on error ────────────

def test_is_commit_on_main_false_on_error(tmp_path):
    """_is_commit_on_main should return False if subprocess fails."""
    from src.orchestration.task_board import TaskBoard

    with patch('subprocess.run', side_effect=Exception("git not available")):
        result = TaskBoard._is_commit_on_main("abc123")

    assert result is False


# ── Test 6: Hook dedup — only .git/hooks/post-merge exists ───────

def test_no_duplicate_post_merge_hooks():
    """Only .git/hooks/post-merge should exist. No stale copies in hooks/ or worktrees."""
    repo_root = Path(__file__).parent.parent

    # Find all post-merge hooks
    all_hooks = list(repo_root.glob("**/post-merge"))

    # Filter: only .git/hooks/post-merge is allowed
    stale_hooks = [
        h for h in all_hooks
        if ".git/hooks/post-merge" not in str(h)
    ]

    assert len(stale_hooks) == 0, (
        f"Found {len(stale_hooks)} stale post-merge hook(s) that could cause false done_main:\n"
        + "\n".join(f"  - {h}" for h in stale_hooks)
        + "\nOnly .git/hooks/post-merge should exist."
    )


# ── Test 7: complete_task with None branch → done_worktree ───────

def test_complete_with_none_branch_is_safe(tmp_path):
    """When _detect_current_branch returns None, complete_task should
    default to done_worktree (safe), NOT done_main (dangerous)."""
    board = _make_board(tmp_path)
    tid = board.add_task("Task with unknown branch", priority=3)
    board.update_task(tid, status="claimed", assigned_to="test-agent")

    with patch.object(type(board), '_detect_current_branch', return_value=None):
        with patch.object(type(board), '_validate_closure_proof', return_value=None):
            result = board.complete_task(tid, commit_hash="abc123")

    assert result["success"] is True
    task = board.get_task(tid)
    # None != "main" → is_worktree=True → done_worktree
    assert task["status"] == "done_worktree", (
        f"Expected done_worktree (safe default), got {task['status']}. "
        "If branch detection fails, we must NOT assume main."
    )


# ── Test 8: promote without commit hash uses task's stored hash ──

def test_promote_uses_task_commit_hash(tmp_path):
    """promote_to_main should check task's stored commit_hash when no merge_commit_hash provided."""
    board = _make_board(tmp_path)
    tid = board.add_task("Task with stored hash", priority=3)
    board.update_task(tid, status="done_worktree", commit_hash="stored_hash_123")

    with patch.object(type(board), '_is_commit_on_main', return_value=False) as mock_check:
        result = board.promote_to_main(tid)  # No merge_commit_hash

    # Should have checked the stored hash
    mock_check.assert_called_once_with("stored_hash_123")
    assert result["success"] is False
    assert "NOT on main" in result["error"]


# ── Test 9: _detect_current_branch passes cwd to subprocess ───

def test_detect_branch_uses_cwd_override():
    """MARKER_195.20: _detect_current_branch(cwd=X) should pass X to subprocess."""
    from src.orchestration.task_board import TaskBoard

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "claude/cut-engine\n"

    with patch('subprocess.run', return_value=mock_result) as mock_run:
        result = TaskBoard._detect_current_branch(cwd="/fake/worktree/path")

    assert result == "claude/cut-engine"
    call_kwargs = mock_run.call_args
    assert call_kwargs.kwargs.get("cwd") == "/fake/worktree/path" or call_kwargs[1].get("cwd") == "/fake/worktree/path"


# ── Test 10: complete_task with worktree_path detects branch ──

def test_complete_task_with_worktree_path(tmp_path):
    """MARKER_195.20: worktree_path is passed to _detect_current_branch for auto-detection."""
    board = _make_board(tmp_path)
    tid = board.add_task("Worktree task", priority=3)
    board.update_task(tid, status="claimed", assigned_to="Alpha")

    with patch.object(type(board), '_detect_current_branch', return_value="claude/cut-engine") as mock_detect:
        with patch.object(type(board), '_validate_closure_proof', return_value=None):
            result = board.complete_task(tid, commit_hash="abc123", worktree_path="/fake/wt")

    assert result["success"] is True
    # Verify cwd was passed through
    mock_detect.assert_called_once_with(cwd="/fake/wt")
    task = board.get_task(tid)
    assert task["status"] == "done_worktree"


# ── Test 11: worktree branch → done_worktree, not done_main ──

def test_worktree_branch_yields_done_worktree(tmp_path):
    """MARKER_195.20: When worktree cwd detects a non-main branch → done_worktree."""
    board = _make_board(tmp_path)
    tid = board.add_task("Media task", priority=3)
    board.update_task(tid, status="claimed", assigned_to="Beta")

    # Simulate: no explicit branch, but worktree_path resolves to claude/cut-media
    with patch.object(type(board), '_detect_current_branch', return_value="claude/cut-media"):
        with patch.object(type(board), '_validate_closure_proof', return_value=None):
            result = board.complete_task(tid, commit_hash="def456", worktree_path="/wt/cut-media")

    assert result["success"] is True
    task = board.get_task(tid)
    assert task["status"] == "done_worktree", (
        f"Expected done_worktree for branch claude/cut-media, got {task['status']}"
    )
