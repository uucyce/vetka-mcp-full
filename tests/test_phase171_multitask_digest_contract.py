from src.api.routes.chat_routes import _build_myco_quick_reply
from src.services import myco_memory_bridge as bridge


def test_phase171_multitask_stats_splits_failed_and_queued(monkeypatch):
    payload = {
        "tasks": {
            "t1": {"status": "done"},
            "t2": {"status": "running"},
            "t3": {"status": "claimed"},
            "t4": {"status": "failed"},
            "t5": {"status": "cancelled"},
            "t6": {"status": "pending"},
            "t7": {"status": "queued"},
            "t8": {"status": "hold"},
        },
        "settings": {"max_concurrent": 3, "auto_dispatch": True},
        "_meta": {"phase": "171"},
    }
    monkeypatch.setattr(bridge, "_load_task_board", lambda: payload)

    stats = bridge._multitask_stats()

    assert stats["total"] == 8
    assert stats["done"] == 1
    assert stats["active"] == 2
    assert stats["failed"] == 2
    assert stats["queued"] == 3
    assert stats["phase"] == "171"
    assert stats["max_concurrent"] == 3
    assert stats["auto_dispatch"] is True


def test_phase171_digest_snapshot_normalizes_dict_fields():
    snap = bridge._digest_snapshot(
        {
            "last_updated": "2026-03-09T03:01:16.915381+00:00",
            "current_phase": {
                "number": 155,
                "subphase": "0",
                "name": "157 research corpus and updates",
                "status": "IN_PROGRESS",
            },
            "summary": {
                "headline": "Phase 155.0 DONE! 157 research corpus and updates",
                "key_achievements": ["[abc] test"],
            },
            "status": {"summary": "green"},
        }
    )

    assert snap["phase"] == "155.0 IN_PROGRESS"
    assert snap["phase_number"] == "155"
    assert snap["phase_subphase"] == "0"
    assert snap["phase_name"] == "157 research corpus and updates"
    assert snap["phase_status"] == "IN_PROGRESS"
    assert snap["summary"] == "Phase 155.0 DONE! 157 research corpus and updates"
    assert snap["status"] == "green"


def test_phase171_myco_quick_reply_includes_failed_counter():
    payload = {
        "user_name": "Danila",
        "user_id": "danila",
        "active_project_id": "vetka_live_03",
        "recent_tasks_by_project": {},
        "hidden_index": {"source_count": 1},
        "fastpath": {"mode": "local_jepa_gemma_first"},
        "orchestration": {
            "multitask": {
                "active": 1,
                "queued": 2,
                "done": 3,
                "failed": 4,
                "max_concurrent": 4,
                "auto_dispatch": True,
                "phase": "171",
            },
            "digest": {"phase": "171.1", "summary": "ok"},
        },
    }
    reply = _build_myco_quick_reply("/myco", payload, {"label": "tests/mcc"})
    assert "multitask errors: failed 4" in reply
