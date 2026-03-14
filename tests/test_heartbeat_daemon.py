# MARKER_137.S1_6_HEARTBEAT_DAEMON_TEST
# MARKER_137.HEARTBEAT_CLEANUP: Updated to use debug_routes (heartbeat_health.py deleted)
import asyncio
import json
import time
from datetime import datetime, timezone

import pytest

from src.api.routes import debug_routes
from src.orchestration import mycelium_heartbeat as hb


@pytest.mark.asyncio
async def test_heartbeat_config_start_stop_roundtrip(monkeypatch, tmp_path):
    config_file = tmp_path / "heartbeat_config.json"

    monkeypatch.setattr(debug_routes, "HEARTBEAT_CONFIG_FILE", config_file)

    # Enable with interval=45
    payload_on = await debug_routes.update_heartbeat_settings({
        "enabled": True,
        "interval": 45,
        "profile_mode": "task",
        "project_id": "proj_alpha",
        "workflow_family": "g3_localguys",
        "task_id": "tb_local_1",
        "localguys_enabled": True,
        "localguys_idle_sec": 300,
        "localguys_action": "resume_task",
    })
    assert payload_on["success"] is True
    assert payload_on["enabled"] is True
    assert payload_on["interval"] == 45
    assert payload_on["profile_mode"] == "task"
    assert payload_on["project_id"] == "proj_alpha"
    assert payload_on["workflow_family"] == "g3_localguys"
    assert payload_on["task_id"] == "tb_local_1"
    assert payload_on["localguys_idle_sec"] == 300
    assert payload_on["localguys_action"] == "resume_task"

    # Read back settings
    payload_cfg = await debug_routes.get_heartbeat_settings()
    assert payload_cfg["success"] is True
    assert payload_cfg["enabled"] is True
    assert payload_cfg["profile_mode"] == "task"
    assert payload_cfg["task_id"] == "tb_local_1"
    assert payload_cfg["effective_profile"]["key"] == "task:tb_local_1"

    # Disable
    payload_off = await debug_routes.update_heartbeat_settings({"enabled": False})
    assert payload_off["enabled"] is False
    raw = json.loads(config_file.read_text())
    assert raw["profile_mode"] == "task"
    assert raw["localguys_action"] == "resume_task"


@pytest.mark.asyncio
async def test_heartbeat_tick_processes_task_via_board(monkeypatch, tmp_path):
    state_file = tmp_path / "state.json"
    fallback_file = tmp_path / "fallback.json"

    monkeypatch.setattr(hb, "_STATE_FILE", state_file)
    monkeypatch.setattr(hb, "_STATE_FILE_FALLBACK", fallback_file)
    monkeypatch.setattr(
        hb,
        "_fetch_new_messages",
        lambda group_id, since_id=None, limit=20: [
            {"id": "m1", "sender_id": "user", "content": "@dragon implement heartbeat e2e test path"}
        ],
    )
    monkeypatch.setattr(hb, "_emit_heartbeat_status", lambda *args, **kwargs: None)

    class FakeBoard:
        def __init__(self):
            self.settings = {"max_concurrent": 1}
            self.added = []
            self._dispatch_calls = 0

        def get_queue(self, status=None):  # noqa: ARG002
            return []

        def add_task(self, **kwargs):
            self.added.append(kwargs)
            return "tb_fake_1"

        async def dispatch_next(self, chat_id):  # noqa: ARG002
            self._dispatch_calls += 1
            if self._dispatch_calls == 1:
                return {
                    "success": True,
                    "task_id": "tb_fake_1",
                    "task_title": "heartbeat task",
                    "phase_type": "build",
                }
            return {"success": False}

    fake_board = FakeBoard()
    monkeypatch.setattr("src.orchestration.task_board.get_task_board", lambda: fake_board)

    result = await hb.heartbeat_tick(group_id="test-group", dry_run=False)

    assert result["tasks_found"] == 1
    assert result["tasks_dispatched"] == 1
    assert len(fake_board.added) == 1
    assert fake_board.added[0]["created_by"].startswith("heartbeat:")


@pytest.mark.asyncio
async def test_on_pipeline_complete_triggers_wakeup(monkeypatch):
    async def fake_tick(group_id, dry_run=False):  # noqa: ARG001
        return {"tasks_found": 2, "tasks_dispatched": 1}

    monkeypatch.setattr(hb, "heartbeat_tick", fake_tick)

    payload = await hb.on_pipeline_complete("group-123")

    assert payload["tasks_found"] == 2


@pytest.mark.asyncio
async def test_heartbeat_tick_nudges_scoped_localguys_run_without_chat_messages(monkeypatch, tmp_path):
    state_file = tmp_path / "state.json"
    fallback_file = tmp_path / "fallback.json"
    monkeypatch.setattr(hb, "_STATE_FILE", state_file)
    monkeypatch.setattr(hb, "_STATE_FILE_FALLBACK", fallback_file)
    monkeypatch.setattr(hb, "_CONFIG_FILE", tmp_path / "heartbeat_config.json")
    (tmp_path / "heartbeat_config.json").write_text(json.dumps({
        "enabled": True,
        "interval": 60,
        "monitor_all": True,
        "profile_mode": "task",
        "task_id": "tb_local_1",
        "project_id": "proj_alpha",
        "workflow_family": "g3_localguys",
        "localguys_enabled": True,
        "localguys_idle_sec": 60,
        "localguys_action": "nudge",
    }))
    monkeypatch.setattr(hb, "_fetch_new_messages", lambda *args, **kwargs: [])
    emitted: list[str] = []
    monkeypatch.setattr(hb, "_emit_heartbeat_status", lambda group_id, message: emitted.append(message))

    class FakeBoard:
        settings = {"max_concurrent": 1}

        def get_queue(self, status=None):  # noqa: ARG002
            return [{
                "id": "tb_local_1",
                "title": "Scoped localguys task",
                "workflow_family": "g3_localguys",
                "project_id": "proj_alpha",
                "status": "running",
                "priority": 2,
                "phase_type": "build",
                "team_profile": "dragon_silver",
                "tags": ["localguys"],
            }]

        def add_task(self, **kwargs):  # noqa: ARG002
            raise AssertionError("nudge mode must not create continuation task")

    class FakeRegistry:
        def __init__(self):
            self.updated = []

        def get_latest_for_task(self, task_id):
            assert task_id == "tb_local_1"
            return {
                "run_id": "lg_run_1",
                "task_id": task_id,
                "workflow_family": "g3_localguys",
                "status": "running",
                "current_step": "verify",
                "updated_at": "2026-03-13T10:00:00+00:00",
                "telemetry": {"idle_turn_count": 0},
            }

        def update_run(self, run_id, **updates):
            self.updated.append((run_id, updates))
            return {"run_id": run_id}

    fake_registry = FakeRegistry()
    monkeypatch.setattr("src.orchestration.task_board.get_task_board", lambda: FakeBoard())
    monkeypatch.setattr("src.services.mcc_local_run_registry.get_localguys_run_registry", lambda: fake_registry)
    monkeypatch.setattr(hb, "_fetch_localguys_runtime_snapshot", lambda task_id: {
        "run": {"run_id": "lg_run_1"},
        "runtime_guard": {
            "current_step": "verify",
            "allowed_tools": ["context", "tests"],
            "verification_target": "targeted_tests",
            "idle_nudge_template": "Continue verify in playground.",
        },
    })
    monkeypatch.setattr(
        hb.time,
        "time",
        lambda: datetime(2026, 3, 13, 10, 3, 0, tzinfo=timezone.utc).timestamp(),
    )

    result = await hb.heartbeat_tick(group_id="test-group", dry_run=False)

    assert result["new_messages"] == 0
    assert result["localguys"]["checked"] == 1
    assert result["localguys"]["stalled"] == 1
    assert result["localguys"]["nudged"] == 1
    assert result["localguys"]["resumed"] == 0
    assert result["localguys"]["effective_profile"]["key"] == "task:tb_local_1"
    assert fake_registry.updated[0][0] == "lg_run_1"
    assert fake_registry.updated[0][1]["metadata"]["recommended_tools"] == ["context", "tests"]
    assert any("localguys nudge" in row for row in emitted)


@pytest.mark.asyncio
async def test_heartbeat_tick_auto_resume_creates_continuation_task(monkeypatch, tmp_path):
    state_file = tmp_path / "state.json"
    fallback_file = tmp_path / "fallback.json"
    monkeypatch.setattr(hb, "_STATE_FILE", state_file)
    monkeypatch.setattr(hb, "_STATE_FILE_FALLBACK", fallback_file)
    monkeypatch.setattr(hb, "_CONFIG_FILE", tmp_path / "heartbeat_config.json")
    (tmp_path / "heartbeat_config.json").write_text(json.dumps({
        "enabled": True,
        "interval": 60,
        "profile_mode": "project",
        "project_id": "proj_alpha",
        "localguys_enabled": True,
        "localguys_idle_sec": 60,
        "localguys_action": "auto",
    }))
    monkeypatch.setattr(hb, "_fetch_new_messages", lambda *args, **kwargs: [])
    emitted: list[str] = []
    monkeypatch.setattr(hb, "_emit_heartbeat_status", lambda group_id, message: emitted.append(message))

    class FakeBoard:
        settings = {"max_concurrent": 1}

        def __init__(self):
            self.added = []

        def get_queue(self, status=None):  # noqa: ARG002
            return [{
                "id": "tb_local_1",
                "title": "Scoped localguys task",
                "workflow_family": "g3_localguys",
                "workflow_id": "g3_localguys",
                "project_id": "proj_alpha",
                "status": "running",
                "priority": 2,
                "phase_type": "build",
                "team_profile": "dragon_silver",
                "tags": ["localguys"],
                "architecture_docs": ["docs/a.md"],
                "closure_files": ["src/a.py"],
            }] + self.added

        def add_task(self, **kwargs):
            self.added.append(kwargs)
            return "tb_resume_1"

    class FakeRegistry:
        def get_latest_for_task(self, task_id):
            return {
                "run_id": "lg_run_1",
                "task_id": task_id,
                "workflow_family": "g3_localguys",
                "status": "running",
                "current_step": "execute",
                "updated_at": "2026-03-13T10:00:00+00:00",
                "telemetry": {"idle_turn_count": 1},
            }

        def update_run(self, run_id, **updates):  # noqa: ARG002
            return {"run_id": run_id}

    fake_board = FakeBoard()
    monkeypatch.setattr("src.orchestration.task_board.get_task_board", lambda: fake_board)
    monkeypatch.setattr("src.services.mcc_local_run_registry.get_localguys_run_registry", lambda: FakeRegistry())
    monkeypatch.setattr(hb, "_fetch_localguys_runtime_snapshot", lambda task_id: {
        "run": {"run_id": "lg_run_1"},
        "runtime_guard": {
            "current_step": "execute",
            "allowed_tools": ["context", "artifacts", "tests"],
            "verification_target": "targeted_tests",
            "idle_nudge_template": "Continue execute in playground.",
        },
    })
    monkeypatch.setattr(
        hb.time,
        "time",
        lambda: datetime(2026, 3, 13, 10, 3, 0, tzinfo=timezone.utc).timestamp(),
    )

    result = await hb.heartbeat_tick(group_id="test-group", dry_run=False)

    assert result["localguys"]["resumed"] == 1
    assert result["effective_profile"]["key"] == "project:proj_alpha"
    assert fake_board.added[0]["task_origin"] == "heartbeat_localguys_resume"
    assert fake_board.added[0]["parent_task_id"] == "tb_local_1"
    assert "run:lg_run_1" in fake_board.added[0]["tags"]
    assert any("localguys resume queued" in row for row in emitted)
