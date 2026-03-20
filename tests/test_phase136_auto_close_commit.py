# MARKER_136.TEST_AUTO_CLOSE_COMMIT
# MARKER_191.1: Updated — auto-close only works on claimed/running tasks
# MARKER_195.2: Tests for keyword matching removal + activating_agent fix
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


# MARKER_195.2: Generic commit must NOT close unrelated tasks (keyword matching killed)
def test_generic_commit_does_not_close_unrelated_tasks(tmp_path):
    """Commit with generic words like 'fix update task scheduling' must NOT close
    tasks that happen to share those words in their title."""
    board = TaskBoard(board_file=tmp_path / "task_board.json")
    t1 = board.add_task(title="Fix task scheduling performance")
    t2 = board.add_task(title="Update scheduling algorithm")
    t3 = board.add_task(title="Fix update mechanism for config")
    for tid in (t1, t2, t3):
        board.update_task(tid, status="claimed", assigned_to="opus")

    # Generic commit that shares words with all 3 tasks but references NONE by ID
    completed = board.auto_complete_by_commit(
        commit_hash="bbb22222",
        commit_message="fix: update task scheduling logic for better perf",
    )

    assert completed == [], f"Generic commit falsely closed tasks: {completed}"
    for tid in (t1, t2, t3):
        assert board.get_task(tid)["status"] == "claimed"


def test_activating_agent_records_real_committer(tmp_path):
    """MARKER_195.2: activating_agent must record the actual committer (agent_id),
    not the task's assigned_to field."""
    board = TaskBoard(board_file=tmp_path / "task_board.json")
    task_id = board.add_task(title="Agent identity test")
    board.update_task(task_id, status="claimed", assigned_to="cursor")

    # Agent "opus" commits and closes cursor's task
    completed = board.auto_complete_by_commit(
        commit_hash="ccc33333",
        commit_message=f"fix: resolve issue [task:{task_id}]",
        agent_id="opus",
    )

    assert task_id in completed
    updated = board.get_task(task_id)
    proof = updated.get("closure_proof", {})
    assert proof["activating_agent"] == "opus", \
        f"Expected 'opus' but got '{proof.get('activating_agent')}'"
    assert updated.get("closed_by") == "opus"


def test_activating_agent_defaults_to_git_auto_close(tmp_path):
    """When no agent_id passed, activating_agent should be 'git_auto_close',
    not the task's assigned_to."""
    board = TaskBoard(board_file=tmp_path / "task_board.json")
    task_id = board.add_task(title="Default closer test")
    board.update_task(task_id, status="claimed", assigned_to="cursor")

    completed = board.auto_complete_by_commit(
        commit_hash="ddd44444",
        commit_message=f"fix: done [task:{task_id}]",
    )

    assert task_id in completed
    updated = board.get_task(task_id)
    proof = updated.get("closure_proof", {})
    assert proof["activating_agent"] == "git_auto_close"
    assert updated.get("closed_by") == "git_auto_close"
