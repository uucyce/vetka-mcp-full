"""
Phase 184.5 — Worktree → Main Merge via TaskBoard Tests

Tests:
1. merge_request with missing branch_name returns error
2. merge_request with nonexistent task returns error
3. update_task accepts merge fields (branch_name, merge_commits, etc.)
4. _count_tests returns integer
5. _execute_merge cherry-pick flow (mocked git)
6. _execute_merge merge --no-ff flow (mocked git)
7. _execute_merge squash flow (mocked git)
8. _execute_merge unknown strategy returns error
9. merge_request full flow (mocked git + ActionRegistry)
10. merge_request closure_tests failure aborts merge
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock


def _make_board(tmp_path):
    """Create a TaskBoard with tmp storage."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.orchestration.task_board import TaskBoard
    return TaskBoard(board_file=tmp_path / "board.json")


async def _passthrough_wait_for(coro, timeout=None):
    """Pass through to the coroutine without actual timeout."""
    return await coro


# ── Test 1: Missing branch_name ───────────────────────────────────

@pytest.mark.asyncio
async def test_merge_request_no_branch(tmp_path):
    """merge_request returns error when task has no branch_name."""
    board = _make_board(tmp_path)
    tid = board.add_task("Test task", priority=3)

    result = await board.merge_request(tid)
    assert result["success"] is False
    assert "branch_name" in result["error"]


# ── Test 2: Nonexistent task ──────────────────────────────────────

@pytest.mark.asyncio
async def test_merge_request_nonexistent_task(tmp_path):
    """merge_request returns error for unknown task_id."""
    board = _make_board(tmp_path)
    result = await board.merge_request("nonexistent_task_id")
    assert result["success"] is False
    assert "not found" in result["error"]


# ── Test 3: update_task accepts merge fields ─────────────────────

def test_update_task_accepts_merge_fields(tmp_path):
    """update_task stores branch_name, merge_commits, merge_strategy, merge_result."""
    board = _make_board(tmp_path)
    tid = board.add_task("Merge feature", priority=2)

    board.update_task(tid,
        branch_name="feature/x",
        merge_commits=["abc123", "def456"],
        merge_strategy="squash",
        merge_result={"status": "pending"},
    )

    task = board.tasks[tid]
    assert task["branch_name"] == "feature/x"
    assert task["merge_commits"] == ["abc123", "def456"]
    assert task["merge_strategy"] == "squash"
    assert task["merge_result"]["status"] == "pending"


# ── Test 4: _count_tests returns integer ──────────────────────────

@pytest.mark.asyncio
async def test_count_tests_returns_int(tmp_path):
    """_count_tests returns an integer (0 on failure)."""
    board = _make_board(tmp_path)

    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(b"42 tests collected\n", b""))
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc), \
         patch("asyncio.wait_for", side_effect=_passthrough_wait_for):
        count = await board._count_tests()
    assert isinstance(count, int)
    assert count == 42


# ── Test 5: _execute_merge cherry-pick ────────────────────────────

@pytest.mark.asyncio
async def test_execute_merge_cherry_pick(tmp_path):
    """_execute_merge cherry-pick calls git cherry-pick for each commit."""
    board = _make_board(tmp_path)

    call_args = []

    async def mock_exec(*args, **kwargs):
        call_args.append(args)
        proc = AsyncMock()
        if "rev-parse" in args and "HEAD" in args:
            proc.communicate = AsyncMock(return_value=(b"abc123def456\n", b""))
        else:
            proc.communicate = AsyncMock(return_value=(b"ok\n", b""))
        proc.returncode = 0
        return proc

    with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
        result = await board._execute_merge("feature/test", "cherry-pick", ["aaa", "bbb"])

    assert result["success"] is True
    assert result["commit_hash"] == "abc123def456"

    git_cmds = [a[1] for a in call_args]
    assert "checkout" in git_cmds
    assert "cherry-pick" in git_cmds


# ── Test 6: _execute_merge merge --no-ff ──────────────────────────

@pytest.mark.asyncio
async def test_execute_merge_no_ff(tmp_path):
    """_execute_merge merge strategy calls git merge --no-ff."""
    board = _make_board(tmp_path)

    async def mock_exec(*args, **kwargs):
        proc = AsyncMock()
        if "rev-parse" in args and "HEAD" in args:
            proc.communicate = AsyncMock(return_value=(b"merge_hash_123456\n", b""))
        else:
            proc.communicate = AsyncMock(return_value=(b"ok\n", b""))
        proc.returncode = 0
        return proc

    with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
        result = await board._execute_merge("feature/test", "merge", ["aaa"])

    assert result["success"] is True
    assert "merge_hash" in result["commit_hash"]


# ── Test 7: _execute_merge squash ─────────────────────────────────

@pytest.mark.asyncio
async def test_execute_merge_squash(tmp_path):
    """_execute_merge squash strategy calls git merge --squash + commit."""
    board = _make_board(tmp_path)

    call_args = []

    async def mock_exec(*args, **kwargs):
        call_args.append(args)
        proc = AsyncMock()
        if "rev-parse" in args and "HEAD" in args:
            proc.communicate = AsyncMock(return_value=(b"squash_hash_abcdef\n", b""))
        else:
            proc.communicate = AsyncMock(return_value=(b"ok\n", b""))
        proc.returncode = 0
        return proc

    with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
        result = await board._execute_merge("feature/test", "squash", ["aaa"])

    assert result["success"] is True
    git_cmds = [a[1] for a in call_args]
    assert "checkout" in git_cmds
    assert "commit" in git_cmds


# ── Test 8: Unknown strategy ─────────────────────────────────────

@pytest.mark.asyncio
async def test_execute_merge_unknown_strategy(tmp_path):
    """_execute_merge with unknown strategy returns error."""
    board = _make_board(tmp_path)

    async def mock_exec(*args, **kwargs):
        proc = AsyncMock()
        proc.communicate = AsyncMock(return_value=(b"ok\n", b""))
        proc.returncode = 0
        return proc

    with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
        result = await board._execute_merge("feature/test", "rebase", ["aaa"])

    assert result["success"] is False
    assert "Unknown strategy" in result["error"]


# ── Test 9: Full merge_request flow ──────────────────────────────

@pytest.mark.asyncio
async def test_merge_request_full_flow(tmp_path):
    """merge_request full flow: validate → tests → merge → log → close."""
    board = _make_board(tmp_path)
    tid = board.add_task("Merge feature X", priority=2)
    board.update_task(tid, branch_name="feature/x", merge_commits=["abc123"])

    async def mock_exec(*args, **kwargs):
        proc = AsyncMock()
        if "rev-parse" in args and "--verify" in args:
            proc.communicate = AsyncMock(return_value=(b"abc123\n", b""))
        elif "rev-parse" in args and "HEAD" in args:
            proc.communicate = AsyncMock(return_value=(b"final_hash_abc123\n", b""))
        elif "pytest" in str(args):
            proc.communicate = AsyncMock(return_value=(b"50 tests collected\n", b""))
        else:
            proc.communicate = AsyncMock(return_value=(b"ok\n", b""))
        proc.returncode = 0
        return proc

    with patch("asyncio.create_subprocess_exec", side_effect=mock_exec), \
         patch("asyncio.wait_for", side_effect=_passthrough_wait_for), \
         patch("src.orchestration.action_registry.ActionRegistry") as mock_ar:
        mock_instance = MagicMock()
        mock_ar.return_value = mock_instance

        result = await board.merge_request(tid)

    assert result["success"] is True
    assert "eval_delta" in result
    assert result["eval_delta"]["strategy"] == "cherry-pick"
    assert result["eval_delta"]["branch"] == "feature/x"

    # Task should be done
    task = board.tasks[tid]
    assert task["status"] == "done"
    assert "merge_result" in task


# ── Test 10: Closure tests failure aborts merge ──────────────────

@pytest.mark.asyncio
async def test_merge_request_closure_tests_fail(tmp_path):
    """merge_request aborts if closure_tests fail."""
    board = _make_board(tmp_path)
    tid = board.add_task("Merge with tests", priority=2)
    board.update_task(
        tid,
        branch_name="feature/y",
        merge_commits=["def456"],
        closure_tests=["test_something"],
    )

    call_idx = {"n": 0}

    async def mock_exec(*args, **kwargs):
        call_idx["n"] += 1
        proc = AsyncMock()
        if "rev-parse" in args and "--verify" in args:
            proc.communicate = AsyncMock(return_value=(b"def456\n", b""))
            proc.returncode = 0
        elif "pytest" in str(args) and "--co" not in args:
            # Closure test run fails
            proc.communicate = AsyncMock(return_value=(b"FAILED\n", b""))
            proc.returncode = 1
        else:
            proc.communicate = AsyncMock(return_value=(b"50 tests collected\n", b""))
            proc.returncode = 0
        return proc

    with patch("asyncio.create_subprocess_exec", side_effect=mock_exec), \
         patch("asyncio.wait_for", side_effect=_passthrough_wait_for):
        result = await board.merge_request(tid)

    assert result["success"] is False
    assert "closure" in result.get("error", "").lower() or "test" in result.get("error", "").lower()
