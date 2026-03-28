"""Tests for MARKER_201.TOOL_GUARD — tool isolation feature in TaskBoard."""
import pytest
from pathlib import Path

from src.orchestration.task_board import TaskBoard


def make_board(tmp_path: Path) -> TaskBoard:
    board_file = tmp_path / "task_board.json"
    return TaskBoard(board_file=board_file)


def test_locked_task_rejects_wrong_tool_type(tmp_path: Path):
    board = make_board(tmp_path)
    task_id = board.add_task("locked task", allowed_tools=["claude_code"])
    result = board.claim_task(task_id, agent_name="agent_ollama", agent_type="local_ollama")
    assert result["success"] is False
    assert result.get("tool_isolation_rejected") is True
    assert "error" in result


def test_locked_task_accepts_correct_tool_type(tmp_path: Path):
    board = make_board(tmp_path)
    task_id = board.add_task("locked task", allowed_tools=["claude_code"])
    result = board.claim_task(task_id, agent_name="agent_claude", agent_type="claude_code")
    assert result["success"] is True


def test_unlocked_task_accepts_any_tool_type(tmp_path: Path):
    board = make_board(tmp_path)
    task_id = board.add_task("unlocked task")
    result = board.claim_task(task_id, agent_name="agent_ollama", agent_type="local_ollama")
    assert result["success"] is True


def test_manual_agent_types_includes_opencode_and_local_ollama():
    assert "opencode" in TaskBoard._MANUAL_AGENT_TYPES
    assert "local_ollama" in TaskBoard._MANUAL_AGENT_TYPES
