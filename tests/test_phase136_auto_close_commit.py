# MARKER_136.TEST_AUTO_CLOSE_COMMIT
from src.orchestration.task_board import TaskBoard


def test_auto_close_commit_closes_pending_task_by_id(tmp_path):
    board = TaskBoard(board_file=tmp_path / "task_board.json")
    task_id = board.add_task(title="Pending task for auto-close")
    task = board.get_task(task_id)
    assert task["status"] == "pending"

    completed = board.auto_complete_by_commit(
        commit_hash="abc12345",
        commit_message=f"fix: complete {task_id}",
    )

    assert task_id in completed
    updated = board.get_task(task_id)
    assert updated["status"] == "done"
    assert updated["commit_hash"] == "abc12345"


def test_auto_close_commit_closes_queued_task_by_id(tmp_path):
    board = TaskBoard(board_file=tmp_path / "task_board.json")
    task_id = board.add_task(title="Queued task for auto-close")
    assert board.update_task(task_id, status="queued")

    completed = board.auto_complete_by_commit(
        commit_hash="def67890",
        commit_message=f"Phase 136 infra {task_id} auto close",
    )

    assert task_id in completed
    updated = board.get_task(task_id)
    assert updated["status"] == "done"
    assert updated["commit_hash"] == "def67890"
