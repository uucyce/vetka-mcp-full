"""
Phase 191.19: action=complete with task_ids list (bulk complete)

Tests:
- test_bulk_complete_two_tasks: create 2 tasks, claim both, bulk complete with commit_hash → both done
- test_bulk_complete_mixed: 1 valid + 1 invalid → partial success
- test_bulk_complete_empty: empty task_ids → falls through to normal complete path (error: task_id required)
- test_single_complete_unchanged: single task_id still works as before

@status: active
@phase: 191.19
@marker: MARKER_191.19
@depends: pytest, src.orchestration.task_board, src.mcp.tools.task_board_tools
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestration.task_board import TaskBoard


def _make_board(tmp_path: Path) -> TaskBoard:
    """Create an isolated TaskBoard backed by a temp SQLite DB."""
    return TaskBoard(board_file=tmp_path / "test_board.db")


def _bulk_complete_via_handler(board: TaskBoard, task_ids: list, commit_hash: str = "abc123", **kwargs) -> dict:
    """Drive handle_task_board(action=complete, task_ids=[...]) with a patched get_task_board()."""
    from src.mcp.tools.task_board_tools import handle_task_board
    args = {
        "action": "complete",
        "task_ids": task_ids,
        "commit_hash": commit_hash,
    }
    args.update(kwargs)
    with patch("src.orchestration.task_board.get_task_board", return_value=board):
        return handle_task_board(args)


def _single_complete_via_handler(board: TaskBoard, task_id: str, commit_hash: str = "abc123") -> dict:
    """Drive handle_task_board(action=complete, task_id=...) with a patched get_task_board()."""
    from src.mcp.tools.task_board_tools import handle_task_board
    with patch("src.orchestration.task_board.get_task_board", return_value=board):
        return handle_task_board({
            "action": "complete",
            "task_id": task_id,
            "commit_hash": commit_hash,
        })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_bulk_complete_two_tasks(tmp_path):
    """Create 2 tasks, claim both, bulk complete with commit_hash → both done."""
    board = _make_board(tmp_path)
    tid1 = board.add_task(title="Bulk task A", source="test")
    tid2 = board.add_task(title="Bulk task B", source="test")

    # Claim both tasks so they can be completed
    board.claim_task(tid1, "agent_test", "sonnet")
    board.claim_task(tid2, "agent_test", "sonnet")

    result = _bulk_complete_via_handler(board, [tid1, tid2], commit_hash="deadbeef")

    assert result["success"] is True, f"Expected success, got: {result}"
    assert result["completed_count"] == 2
    assert result["total"] == 2
    assert result["commit_hash"] == "deadbeef"
    assert len(result["results"]) == 2

    # Both individual results should be successful
    for r in result["results"]:
        assert r["success"] is True, f"Expected success for {r['task_id']}, got: {r}"

    # Verify persisted state for both tasks
    task1 = board.get_task(tid1)
    task2 = board.get_task(tid2)
    assert task1["status"].startswith("done"), f"Expected done status, got: {task1['status']}"
    assert task2["status"].startswith("done"), f"Expected done status, got: {task2['status']}"


def test_bulk_complete_mixed(tmp_path):
    """1 valid task + 1 invalid ID → partial success (1 completed, 1 not found)."""
    board = _make_board(tmp_path)
    tid_valid = board.add_task(title="Valid task", source="test")
    board.claim_task(tid_valid, "agent_test", "sonnet")

    tid_invalid = "tb_0000000000_0"  # Does not exist

    result = _bulk_complete_via_handler(board, [tid_valid, tid_invalid], commit_hash="cafe1234")

    assert result["success"] is True, f"Expected top-level success, got: {result}"
    assert result["total"] == 2
    assert result["completed_count"] == 1

    results_by_id = {r["task_id"]: r for r in result["results"]}
    assert results_by_id[tid_valid]["success"] is True
    assert results_by_id[tid_invalid]["success"] is False
    assert "not found" in results_by_id[tid_invalid].get("error", "")


def test_bulk_complete_empty(tmp_path):
    """Empty task_ids list → falls through to normal complete path, requires task_id."""
    board = _make_board(tmp_path)

    result = _bulk_complete_via_handler(board, [], commit_hash="abc123")

    # Falls through to single-task path which requires task_id
    assert result["success"] is False
    assert "task_id" in result.get("error", "").lower()


def test_single_complete_unchanged(tmp_path):
    """Single task_id still works as before (no regression)."""
    board = _make_board(tmp_path)
    tid = board.add_task(title="Single task", source="test")
    board.claim_task(tid, "agent_test", "sonnet")

    result = _single_complete_via_handler(board, tid, commit_hash="f00d1234")

    assert result["success"] is True, f"Expected success, got: {result}"
    # Single complete does NOT return completed_count (bulk-only field)
    assert "completed_count" not in result

    task = board.get_task(tid)
    assert task["status"].startswith("done"), f"Expected done status, got: {task['status']}"
