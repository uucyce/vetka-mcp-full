# MARKER_137.S1_6_HEARTBEAT_DAEMON_TEST
import asyncio

import pytest

from src.api.routes import heartbeat_health
from src.orchestration import mycelium_heartbeat as hb


@pytest.mark.asyncio
async def test_heartbeat_config_start_stop_roundtrip(monkeypatch, tmp_path):
    config_file = tmp_path / "heartbeat_config.json"
    state_file = tmp_path / "heartbeat_state.json"

    monkeypatch.setattr(heartbeat_health, "CONFIG_FILE", config_file)
    monkeypatch.setattr(heartbeat_health, "STATE_FILE", state_file)

    payload_on = await heartbeat_health.update_heartbeat_config({"enabled": True, "interval": 45})
    assert payload_on["success"] is True
    assert payload_on["config"]["enabled"] is True
    assert payload_on["config"]["interval"] == 45

    payload_cfg = await heartbeat_health.get_heartbeat_config()
    assert payload_cfg["success"] is True
    assert payload_cfg["config"]["enabled"] is True

    payload_off = await heartbeat_health.update_heartbeat_config({"enabled": False})
    assert payload_off["config"]["enabled"] is False


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
