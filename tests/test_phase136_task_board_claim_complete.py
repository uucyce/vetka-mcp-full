"""Phase 136 tests for TaskBoard claim/complete flow.

MARKER_192.4: Updated for SQLite backend — 'done' → 'done_main' (MARKER_186.4),
and patched production JSON paths to isolate tests.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.orchestration.task_board import TaskBoard

# MARKER_192.4: Prevent loading production task_board.json during auto-migration
_NONEXISTENT = Path("/tmp/_vetka_test_nonexistent_board.json")

@pytest.fixture(autouse=True)
def _isolate_task_board_from_production():
    with patch("src.orchestration.task_board.TASK_BOARD_FILE", _NONEXISTENT), \
         patch("src.orchestration.task_board._TASK_BOARD_FALLBACK", _NONEXISTENT):
        yield


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
    assert task["status"] in ("done", "done_main", "done_worktree")
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
    """MARKER_198.GUARD: On worktree branch without commit_hash, guard rejects.
    With branch=main (or None resolving to main), done_main still works."""
    board = _create_board(tmp_path)
    task_id = board.add_task(title="Complete without commit metadata")

    # On main branch, no commit_hash is fine → done_main
    result = board.complete_task(task_id, branch="main")

    assert result["success"] is True
    task = board.get_task(task_id)
    assert task["status"] == "done_main"
    assert task["commit_hash"] is None
    assert task["commit_message"] is None


def test_complete_task_returns_not_found_for_unknown_id(tmp_path):
    board = _create_board(tmp_path)

    result = board.complete_task("tb_missing")

    assert result["success"] is False
    assert "not found" in result["error"]


def test_status_history_tracks_created_claimed_and_closed(tmp_path):
    board = _create_board(tmp_path)
    task_id = board.add_task(title="History protocol")
    board.claim_task(task_id, "codex", "claude_code")
    board.complete_task(task_id, commit_hash="abc123", commit_message="history close")

    history = board.get_task_history(task_id)
    assert [row["event"] for row in history] == ["created", "claimed", "closed"]
    assert history[1]["agent_name"] == "codex"
    assert history[-1]["status"] in ("done", "done_main", "done_worktree")


def test_protocol_task_manual_agent_needs_commit_hash(tmp_path):
    """MARKER_192.2: Manual agents (claude_code) can close protocol tasks with commit_hash."""
    board = _create_board(tmp_path)
    task_id = board.add_task(
        title="Protocol close",
        require_closure_proof=True,
        closure_tests=["python -c \"print('ok')\""],
        closure_files=["src/orchestration/task_board.py"],
    )
    board.claim_task(task_id, "codex", "claude_code")

    # Manual agent with commit_hash → success (relaxed proof per MARKER_192.2)
    result = board.complete_task(task_id, commit_hash="abc123", commit_message="manual close")
    assert result["success"] is True

def test_protocol_task_pipeline_agent_requires_full_proof(tmp_path):
    """MARKER_192.2: Pipeline agents need full closure proof."""
    board = _create_board(tmp_path)
    task_id = board.add_task(
        title="Protocol close pipeline",
        require_closure_proof=True,
        agent_type="mycelium",
        closure_tests=["python -c \"print('ok')\""],
        closure_files=["src/orchestration/task_board.py"],
    )
    board.claim_task(task_id, "dragon", "mycelium")

    # Pipeline agent with only commit_hash → failure (needs full proof)
    result = board.complete_task(task_id, commit_hash="abc123", commit_message="pipeline close")
    assert result["success"] is False
    assert "pipeline_success" in result["error"]


def test_run_closure_protocol_executes_tests_commit_and_tracker(monkeypatch, tmp_path):
    board = _create_board(tmp_path)
    task_id = board.add_task(
        title="Protocol success path",
        assigned_to="codex",
        agent_type="claude_code",
        require_closure_proof=True,
        closure_tests=["python3 -c \"print('ok')\""],
        closure_files=["src/orchestration/task_board.py"],
    )
    board.record_pipeline_stats(task_id, {"success": True, "verifier_avg_confidence": 0.92, "duration_s": 1.5})

    class _FakeCommitTool:
        def execute(self, arguments):
            return {
                "success": True,
                "result": {
                    "hash": "cafebabe",
                    "message": arguments["message"],
                    "digest_updated": True,
                },
                "error": None,
            }

    tracker_mock = AsyncMock()
    monkeypatch.setattr("src.mcp.tools.git_tool.GitCommitTool", _FakeCommitTool)
    monkeypatch.setattr("src.services.task_tracker.on_task_completed", tracker_mock)

    result = asyncio.run(
        board.run_closure_protocol(task_id, activating_agent="codex", agent_type="claude_code")
    )

    assert result["success"] is True
    assert result["commit_hash"] == "cafebabe"
    assert result["tests"][0]["passed"] is True
    task = board.get_task(task_id)
    assert task["status"] in ("done", "done_main", "done_worktree")
    assert task["closed_by"] == "codex"
    assert task["closure_proof"]["commit_hash"] == "cafebabe"
    tracker_mock.assert_awaited_once()
