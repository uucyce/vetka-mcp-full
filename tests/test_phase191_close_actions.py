"""
Phase 191.16: action=close + action=bulk_close for TaskBoard

Tests:
- test_close_task: create task → close with reason="obsolete" → status is done_main, history has close event
- test_close_nonexistent: close unknown ID → error
- test_bulk_close: create 3 tasks → bulk_close 2 → verify 2 closed, 1 still pending
- test_bulk_close_mixed: bulk_close with 1 valid + 1 invalid ID → partial success
- test_close_reason_preserved: close with reason="duplicate" → verify reason in history

@status: active
@phase: 191.16
@marker: MARKER_191.16
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


def _close_via_handler(board: TaskBoard, task_id: str, reason: str = "closed") -> dict:
    """Drive handle_task_board(action=close) with a patched get_task_board()."""
    from src.mcp.tools.task_board_tools import handle_task_board
    # get_task_board is imported locally inside handle_task_board, patch the source module
    with patch("src.orchestration.task_board.get_task_board", return_value=board):
        return handle_task_board({"action": "close", "task_id": task_id, "reason": reason})


def _bulk_close_via_handler(board: TaskBoard, task_ids: list, reason: str = "bulk_closed") -> dict:
    """Drive handle_task_board(action=bulk_close) with a patched get_task_board()."""
    from src.mcp.tools.task_board_tools import handle_task_board
    # get_task_board is imported locally inside handle_task_board, patch the source module
    with patch("src.orchestration.task_board.get_task_board", return_value=board):
        return handle_task_board({"action": "bulk_close", "task_ids": task_ids, "reason": reason})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_close_task(tmp_path):
    """Create a task → close with reason=obsolete → status is done_main, history has close event."""
    board = _make_board(tmp_path)
    task_id = board.add_task(title="Old feature", source="test")

    result = _close_via_handler(board, task_id, reason="obsolete")

    assert result["success"] is True, f"Expected success, got: {result}"
    assert result["closed"] is True
    assert result["reason"] == "obsolete"
    assert result["status"] == "done_main"

    # Verify persisted state
    task = board.get_task(task_id)
    assert task["status"] == "done_main"

    # Verify history has a close event
    history = task.get("status_history", [])
    close_events = [h for h in history if h.get("event") == "closed"]
    assert len(close_events) >= 1, f"Expected 'closed' event in history, got: {history}"


def test_close_nonexistent(tmp_path):
    """Close an unknown task ID → returns error."""
    board = _make_board(tmp_path)

    result = _close_via_handler(board, "tb_nonexistent_999", reason="obsolete")

    assert result["success"] is False
    assert "not found" in result["error"].lower() or "tb_nonexistent_999" in result["error"]


def test_close_missing_task_id(tmp_path):
    """Close without task_id → returns error."""
    board = _make_board(tmp_path)
    from src.mcp.tools.task_board_tools import handle_task_board
    with patch("src.orchestration.task_board.get_task_board", return_value=board):
        result = handle_task_board({"action": "close"})

    assert result["success"] is False
    assert "task_id" in result["error"].lower()


def test_bulk_close(tmp_path):
    """Create 3 tasks → bulk_close 2 → verify 2 closed, 1 still pending."""
    board = _make_board(tmp_path)

    id1 = board.add_task(title="Task A", source="test")
    id2 = board.add_task(title="Task B", source="test")
    id3 = board.add_task(title="Task C", source="test")

    result = _bulk_close_via_handler(board, [id1, id2], reason="obsolete")

    assert result["success"] is True
    assert result["closed_count"] == 2
    assert result["total"] == 2

    # Tasks A and B should be done_main
    assert board.get_task(id1)["status"] == "done_main"
    assert board.get_task(id2)["status"] == "done_main"

    # Task C should remain pending
    assert board.get_task(id3)["status"] == "pending"


def test_bulk_close_mixed(tmp_path):
    """bulk_close with 1 valid + 1 invalid ID → partial success."""
    board = _make_board(tmp_path)

    real_id = board.add_task(title="Real task", source="test")
    fake_id = "tb_does_not_exist_12345"

    result = _bulk_close_via_handler(board, [real_id, fake_id], reason="cancelled")

    assert result["success"] is True
    assert result["closed_count"] == 1
    assert result["total"] == 2

    # Check individual results
    by_id = {r["task_id"]: r for r in result["results"]}
    assert by_id[real_id]["success"] is True
    assert by_id[fake_id]["success"] is False
    assert "not found" in by_id[fake_id].get("error", "").lower()

    # Real task should be closed
    assert board.get_task(real_id)["status"] == "done_main"


def test_bulk_close_empty_list(tmp_path):
    """bulk_close with empty task_ids → returns error."""
    board = _make_board(tmp_path)
    from src.mcp.tools.task_board_tools import handle_task_board
    with patch("src.orchestration.task_board.get_task_board", return_value=board):
        result = handle_task_board({"action": "bulk_close", "task_ids": []})

    assert result["success"] is False
    assert "task_ids" in result["error"].lower()


def test_close_reason_preserved(tmp_path):
    """Close with reason=duplicate → verify reason stored in history."""
    board = _make_board(tmp_path)
    task_id = board.add_task(title="Duplicate task", source="test")

    result = _close_via_handler(board, task_id, reason="duplicate")

    assert result["success"] is True
    assert result["reason"] == "duplicate"

    task = board.get_task(task_id)
    history = task.get("status_history", [])
    close_events = [h for h in history if h.get("event") == "closed"]
    assert len(close_events) >= 1

    close_event = close_events[-1]
    assert close_event.get("reason") == "duplicate", (
        f"Expected reason='duplicate' in history event, got: {close_event}"
    )
