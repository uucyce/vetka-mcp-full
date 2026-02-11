# MARKER_136.TEST_TASK_TRACKER
import asyncio
import json

import src.services.task_tracker as tracker


def _patch_tracker_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(tracker, "DIGEST_FILE", tmp_path / "data" / "project_digest.json")
    monkeypatch.setattr(tracker, "TRACKER_FILE", tmp_path / "data" / "task_tracker.json")


def test_on_task_started_adds_in_progress(monkeypatch, tmp_path):
    _patch_tracker_paths(monkeypatch, tmp_path)

    tracker.on_task_started("tb_1", "Implement API", source="codex")
    status = tracker.get_tracker_status()

    assert len(status["in_progress"]) == 1
    row = status["in_progress"][0]
    assert row["task_id"] == "tb_1"
    assert row["title"] == "Implement API"
    assert row["source"] == "codex"


def test_on_task_completed_moves_task_and_updates_digest(monkeypatch, tmp_path):
    _patch_tracker_paths(monkeypatch, tmp_path)

    tracker.on_task_started("tb_2", "Build tests", source="dragon")
    asyncio.run(
        tracker.on_task_completed(
            task_id="tb_2",
            task_title="Build tests",
            status="done",
            stats={"duration_s": 12.5, "llm_calls": 3, "preset": "dragon_bronze"},
            source="dragon",
        )
    )

    state = json.loads(tracker.TRACKER_FILE.read_text())
    assert state["in_progress"] == []
    assert len(state["completed"]) == 1
    completed = state["completed"][0]
    assert completed["task_id"] == "tb_2"
    assert completed["stats"]["duration_s"] == 12.5
    assert completed["stats"]["llm_calls"] == 3
    assert completed["stats"]["preset"] == "dragon_bronze"

    digest = json.loads(tracker.DIGEST_FILE.read_text())
    assert digest["summary"]["headline"].startswith("Phase")
    assert digest["summary"]["key_achievements"][0].startswith("[dragon] Build tests")


def test_on_cursor_task_completed_updates_tracker_and_digest(monkeypatch, tmp_path):
    _patch_tracker_paths(monkeypatch, tmp_path)

    asyncio.run(
        tracker.on_cursor_task_completed(
            marker="C136",
            description="Added tracker tests",
            files_changed=["tests/test_task_tracker.py"],
        )
    )

    state = json.loads(tracker.TRACKER_FILE.read_text())
    assert len(state["completed"]) == 1
    row = state["completed"][0]
    assert row["task_id"] == "C136"
    assert row["source"] == "cursor"
    assert row["files_changed"] == ["tests/test_task_tracker.py"]

    digest = json.loads(tracker.DIGEST_FILE.read_text())
    assert digest["summary"]["key_achievements"][0].startswith("[cursor] [C136] Added tracker tests")


def test_get_tracker_status_returns_last_completed(monkeypatch, tmp_path):
    _patch_tracker_paths(monkeypatch, tmp_path)

    asyncio.run(tracker.on_task_completed("a1", "First", "done", source="dragon"))
    asyncio.run(tracker.on_task_completed("a2", "Second", "done", source="dragon"))

    status = tracker.get_tracker_status()
    assert status["completed_count"] == 2
    assert status["last_completed"]["task_id"] == "a2"
