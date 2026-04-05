"""
MARKER_191.20: Tests for subtask progress tracking.

Tests:
- action=update sets subtasks list
- action=subtask_done marks subtask done by partial title
- action=get returns subtask_progress
- subtask_done partial matching (case-insensitive)
- subtask_done unknown title returns error
- subtask_done on task without subtasks returns error
- get_subtask_progress: None when no subtasks, correct percent
"""

import pytest
from pathlib import Path
import tempfile

from src.orchestration.task_board import TaskBoard


@pytest.fixture
def board(tmp_path):
    db_path = tmp_path / "test_tasks.db"
    b = TaskBoard(board_file=db_path)
    yield b
    b.close()


@pytest.fixture
def task_with_subtasks(board):
    task_id = board.add_task(
        title="Test subtask task",
        description="A task with subtasks",
        priority=3,
        phase_type="build",
    )
    board.update_task(task_id, subtasks=[
        {"title": "Write tests", "done": False},
        {"title": "Implement feature", "done": False},
        {"title": "Update docs", "done": False},
    ])
    return task_id


# ── get_subtask_progress static method ────────────────────────────────────────

def test_get_subtask_progress_none_when_no_subtasks(board):
    task_id = board.add_task(title="No subtasks", phase_type="build")
    task = board.get_task(task_id)
    assert TaskBoard.get_subtask_progress(task) is None


def test_get_subtask_progress_zero_percent(board, task_with_subtasks):
    task = board.get_task(task_with_subtasks)
    progress = TaskBoard.get_subtask_progress(task)
    assert progress is not None
    assert progress["done"] == 0
    assert progress["total"] == 3
    assert progress["percent"] == 0


def test_get_subtask_progress_partial(board, task_with_subtasks):
    board.subtask_done(task_with_subtasks, "Write tests")
    task = board.get_task(task_with_subtasks)
    progress = TaskBoard.get_subtask_progress(task)
    assert progress["done"] == 1
    assert progress["total"] == 3
    assert progress["percent"] == 33


def test_get_subtask_progress_complete(board, task_with_subtasks):
    board.subtask_done(task_with_subtasks, "Write tests")
    board.subtask_done(task_with_subtasks, "Implement feature")
    board.subtask_done(task_with_subtasks, "Update docs")
    task = board.get_task(task_with_subtasks)
    progress = TaskBoard.get_subtask_progress(task)
    assert progress["done"] == 3
    assert progress["total"] == 3
    assert progress["percent"] == 100


# ── subtask_done method ────────────────────────────────────────────────────────

def test_subtask_done_exact_match(board, task_with_subtasks):
    result = board.subtask_done(task_with_subtasks, "Write tests")
    assert result["success"] is True
    assert result["matched_title"] == "Write tests"
    assert result["progress"]["done"] == 1
    assert result["progress"]["total"] == 3


def test_subtask_done_partial_title(board, task_with_subtasks):
    result = board.subtask_done(task_with_subtasks, "Implement")
    assert result["success"] is True
    assert result["matched_title"] == "Implement feature"


def test_subtask_done_case_insensitive(board, task_with_subtasks):
    result = board.subtask_done(task_with_subtasks, "WRITE TESTS")
    assert result["success"] is True
    assert result["matched_title"] == "Write tests"


def test_subtask_done_unknown_title(board, task_with_subtasks):
    result = board.subtask_done(task_with_subtasks, "nonexistent subtask")
    assert result["success"] is False
    assert "Available" in result["error"]


def test_subtask_done_no_subtasks(board):
    task_id = board.add_task(title="No subtask list", phase_type="build")
    result = board.subtask_done(task_id, "anything")
    assert result["success"] is False
    assert "no subtasks" in result["error"].lower()


def test_subtask_done_task_not_found(board):
    result = board.subtask_done("tb_nonexistent", "anything")
    assert result["success"] is False
    assert "not found" in result["error"]


def test_subtask_done_idempotent(board, task_with_subtasks):
    board.subtask_done(task_with_subtasks, "Write tests")
    result = board.subtask_done(task_with_subtasks, "Write tests")
    assert result["success"] is True
    # Still 1 done (marking done again is idempotent)
    assert result["progress"]["done"] == 1


def test_subtask_done_persists_across_reload(tmp_path):
    db_path = tmp_path / "persist_test.db"
    board1 = TaskBoard(board_file=db_path)
    task_id = board1.add_task(title="Persist test", phase_type="build")
    board1.update_task(task_id, subtasks=[
        {"title": "Step A", "done": False},
        {"title": "Step B", "done": False},
    ])
    board1.subtask_done(task_id, "Step A")
    board1.close()

    board2 = TaskBoard(board_file=db_path)
    task = board2.get_task(task_id)
    progress = TaskBoard.get_subtask_progress(task)
    assert progress["done"] == 1
    assert progress["total"] == 2
    board2.close()
