"""Phase 136 tests for TaskBoard claim/complete flow."""

from datetime import datetime

from src.orchestration.task_board import TaskBoard


def _create_board(tmp_path):
    return TaskBoard(board_file=tmp_path / "task_board.json")


def test_claim_task_from_queued_updates_assignment_and_emits_event(tmp_path):
    board = _create_board(tmp_path)
    task_id = board.add_task(title="Implement sync protocol")
    assert board.update_task(task_id, status="queued")

    events = []
    board._notify_board_update = lambda event_type, event_data=None: events.append((event_type, event_data))

    result = board.claim_task(task_id, "codex", "claude_code")

    assert result["success"] is True
    task = board.get_task(task_id)
    assert task["status"] == "claimed"
    assert task["assigned_to"] == "codex"
    assert task["agent_type"] == "claude_code"
    assert task["assigned_at"] is not None
    datetime.fromisoformat(task["assigned_at"])

    assert events
    event_type, payload = events[-1]
    assert event_type == "task_claimed"
    assert payload["task_id"] == task_id
    assert payload["assigned_to"] == "codex"
    assert payload["agent_type"] == "claude_code"


def test_claim_task_fails_for_running_status(tmp_path):
    board = _create_board(tmp_path)
    task_id = board.add_task(title="Already running task")
    assert board.update_task(task_id, status="running")

    result = board.claim_task(task_id, "codex", "claude_code")

    assert result["success"] is False
    assert "can't claim" in result["error"]


def test_claim_task_returns_not_found_for_unknown_id(tmp_path):
    board = _create_board(tmp_path)

    result = board.claim_task("tb_missing", "codex", "claude_code")

    assert result["success"] is False
    assert "not found" in result["error"]


def test_complete_task_stores_commit_and_emits_truncated_event(tmp_path):
    board = _create_board(tmp_path)
    task_id = board.add_task(title="Complete with commit metadata")
    board.claim_task(task_id, "codex", "claude_code")

    long_message = "A" * 260
    events = []
    board._notify_board_update = lambda event_type, event_data=None: events.append((event_type, event_data))

    result = board.complete_task(task_id, commit_hash="abcdef1234567890", commit_message=long_message)

    assert result["success"] is True
    assert result["commit_hash"] == "abcdef1234567890"

    task = board.get_task(task_id)
    assert task["status"] == "done"
    assert task["commit_hash"] == "abcdef1234567890"
    assert len(task["commit_message"]) == 200
    assert task["completed_at"] is not None
    datetime.fromisoformat(task["completed_at"])

    assert events
    event_type, payload = events[-1]
    assert event_type == "task_completed"
    assert payload["task_id"] == task_id
    assert payload["assigned_to"] == "codex"
    assert payload["commit_hash"] == "abcdef1234567890"
    assert len(payload["commit_message"]) == 50


def test_complete_task_without_commit_metadata(tmp_path):
    board = _create_board(tmp_path)
    task_id = board.add_task(title="Complete without commit metadata")

    result = board.complete_task(task_id)

    assert result["success"] is True
    task = board.get_task(task_id)
    assert task["status"] == "done"
    assert task["commit_hash"] is None
    assert task["commit_message"] is None


def test_complete_task_returns_not_found_for_unknown_id(tmp_path):
    board = _create_board(tmp_path)

    result = board.complete_task("tb_missing")

    assert result["success"] is False
    assert "not found" in result["error"]

