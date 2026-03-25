# MARKER_198.P1.9
"""
VETKA Phase 198.P1.9 - Post-commit task match by changed files

Tests for TaskBoard.find_tasks_by_changed_files():
- Basic matching: file in allowed_paths → task returned
- Prefix matching: 'src/mcp/' matches 'src/mcp/tools/foo.py'
- No match: no tasks overlap → empty list
- Excludes done tasks even if paths match

@status: active
@phase: 198.P1.9
@marker: MARKER_198.P1.9
@depends: pytest, src.orchestration.task_board
"""

import sys
import os
from pathlib import Path

import pytest

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestration.task_board import TaskBoard


def _make_board(tmp_path: Path) -> TaskBoard:
    """Create an isolated TaskBoard backed by a temp SQLite DB."""
    return TaskBoard(board_file=tmp_path / "test_board.db")


def test_find_tasks_by_changed_files_basic(tmp_path):
    """Only the task whose allowed_paths overlaps the changed file is returned."""
    board = _make_board(tmp_path)

    board.add_task(
        title="MCP tool task",
        allowed_paths=["src/mcp/tools/git_tool.py"],
        source="test",
    )
    board.add_task(
        title="Frontend task",
        allowed_paths=["src/frontend/"],
        source="test",
    )
    board.add_task(
        title="Orchestration task",
        allowed_paths=["src/orchestration/"],
        source="test",
    )

    changed = ["src/mcp/tools/git_tool.py"]
    result = board.find_tasks_by_changed_files(changed)

    assert len(result) == 1
    assert result[0]["title"] == "MCP tool task"


def test_find_tasks_by_changed_files_prefix(tmp_path):
    """allowed_paths=['src/mcp/'] matches file 'src/mcp/tools/foo.py' via prefix."""
    board = _make_board(tmp_path)

    board.add_task(
        title="MCP prefix task",
        allowed_paths=["src/mcp/"],
        source="test",
    )

    changed = ["src/mcp/tools/foo.py"]
    result = board.find_tasks_by_changed_files(changed)

    assert len(result) == 1
    assert result[0]["title"] == "MCP prefix task"


def test_find_tasks_by_changed_files_no_match(tmp_path):
    """Returns empty list when no tasks have overlapping allowed_paths."""
    board = _make_board(tmp_path)

    board.add_task(
        title="Unrelated task",
        allowed_paths=["src/frontend/"],
        source="test",
    )

    changed = ["src/mcp/tools/git_tool.py"]
    result = board.find_tasks_by_changed_files(changed)

    assert result == []


def test_find_tasks_by_changed_files_excludes_done(tmp_path):
    """Done tasks are NOT returned even if their allowed_paths overlap."""
    board = _make_board(tmp_path)

    task_id = board.add_task(
        title="Done task",
        allowed_paths=["src/mcp/"],
        source="test",
    )

    # Mark it done via DB directly to avoid full closure pipeline
    board.db.execute(
        "UPDATE tasks SET status = 'done' WHERE id = ?", (task_id,)
    )
    board.db.commit()

    changed = ["src/mcp/tools/git_tool.py"]
    result = board.find_tasks_by_changed_files(changed)

    assert result == []


def test_find_tasks_by_changed_files_empty_input(tmp_path):
    """Empty changed_files list → empty result without touching DB."""
    board = _make_board(tmp_path)

    board.add_task(
        title="Any task",
        allowed_paths=["src/mcp/"],
        source="test",
    )

    result = board.find_tasks_by_changed_files([])
    assert result == []
