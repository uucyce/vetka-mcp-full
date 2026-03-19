# MARKER_136.TEST_AUTO_CLOSE_COMMIT
# MARKER_191.1: Updated — auto-close only works on claimed/running tasks
from src.orchestration.task_board import TaskBoard


def test_auto_close_commit_closes_claimed_task_by_id(tmp_path):
    """Claimed task with matching [task:tb_xxx] in commit → auto-closed."""
    board = TaskBoard(board_file=tmp_path / "task_board.json")
    task_id = board.add_task(title="Claimed task for auto-close")
    board.update_task(task_id, status="claimed", assigned_to="opus")

    completed = board.auto_complete_by_commit(
        commit_hash="abc12345",
        commit_message=f"fix: complete [task:{task_id}]",
    )

    assert task_id in completed
    updated = board.get_task(task_id)
    assert updated["status"].startswith("done")
    assert updated["commit_hash"] == "abc12345"


def test_auto_close_skips_pending_task(tmp_path):
    """Pending (unclaimed) task must NOT be auto-closed — prevents false positives."""
    board = TaskBoard(board_file=tmp_path / "task_board.json")
    task_id = board.add_task(title="Pending task should not auto-close")

    completed = board.auto_complete_by_commit(
        commit_hash="def67890",
        commit_message=f"fix: complete [task:{task_id}]",
    )

    assert task_id not in completed
    updated = board.get_task(task_id)
    assert updated["status"] == "pending"


def test_auto_close_skips_queued_task(tmp_path):
    """Queued task must NOT be auto-closed."""
    board = TaskBoard(board_file=tmp_path / "task_board.json")
    task_id = board.add_task(title="Queued task should not auto-close")
    board.update_task(task_id, status="queued")

    completed = board.auto_complete_by_commit(
        commit_hash="aaa11111",
        commit_message=f"fix: complete [task:{task_id}]",
    )

    assert task_id not in completed
    updated = board.get_task(task_id)
    assert updated["status"] == "queued"


def test_auto_close_commit_skips_protocol_task(tmp_path):
    """Task with require_closure_proof=True must NOT be auto-closed."""
    board = TaskBoard(board_file=tmp_path / "task_board.json")
    task_id = board.add_task(
        title="Protocol task for auto-close skip",
        require_closure_proof=True,
        closure_tests=["pytest tests/test_phase136_auto_close_commit.py"],
        closure_files=["src/orchestration/task_board.py"],
    )
    board.update_task(task_id, status="claimed", assigned_to="opus")

    completed = board.auto_complete_by_commit(
        commit_hash="fedcba98",
        commit_message=f"fix: complete [task:{task_id}]",
    )

    assert task_id not in completed
    updated = board.get_task(task_id)
    assert updated["status"] == "claimed"


def test_double_close_is_idempotent(tmp_path):
    """Calling complete_task twice on same task should not create duplicate events."""
    board = TaskBoard(board_file=tmp_path / "task_board.json")
    task_id = board.add_task(title="Double close test")
    board.update_task(task_id, status="claimed", assigned_to="opus")

    # First close
    r1 = board.complete_task(task_id, commit_hash="aaa", commit_message="first close")
    assert r1["success"]

    # Second close — should be idempotent
    r2 = board.complete_task(task_id, commit_hash="bbb", commit_message="second close")
    assert r2["success"]
    assert r2.get("note") == "already closed"

    # Status history should have only ONE closed event
    updated = board.get_task(task_id)
    closed_events = [e for e in updated.get("status_history", []) if e.get("event", "").startswith("closed")]
    assert len(closed_events) == 1
