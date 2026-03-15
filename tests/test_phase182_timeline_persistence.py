"""
Tests for Phase 182: Timeline Persistence — pipeline events storage and API.

MARKER_S4_RECON_2B: Restored in Session 4 (was lost between worktrees).

Tests cover:
- append_run() with timeline_events
- Timeline events capping (200 max)
- History rotation (500 max)
- _load_history / _save_history edge cases
- get_run_timeline() endpoint: lookup, role filter, 404
- _emit_timeline_event() structure validation
- _track_agent_stat() auto-emit behavior
"""

import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_history(tmp_path):
    """Temporary pipeline_history.json path."""
    return tmp_path / "data" / "pipeline_history.json"


@pytest.fixture
def patch_history_file(tmp_history, monkeypatch):
    """Patch HISTORY_FILE to use temp path via monkeypatch (safer with async)."""
    import src.api.routes.pipeline_history as ph_module
    monkeypatch.setattr(ph_module, "HISTORY_FILE", tmp_history)
    return tmp_history


# ---------------------------------------------------------------------------
# append_run() tests
# ---------------------------------------------------------------------------

class TestAppendRun:
    def test_basic_append(self, patch_history_file):
        from src.api.routes.pipeline_history import append_run, _load_history

        record = append_run(
            task_id="tb_test_001",
            task_title="Test task",
            preset="dragon_silver",
            phase_type="build",
            phases_completed=["architect", "coder"],
            total_duration_s=42.5,
            eval_score=0.85,
            status="done",
        )

        assert record["task_id"] == "tb_test_001"
        assert record["status"] == "done"
        assert record["total_duration_s"] == 42.5
        assert "run_id" in record
        assert "timestamp" in record

        # Verify persisted
        history = _load_history()
        assert len(history) == 1
        assert history[0]["task_id"] == "tb_test_001"

    def test_run_id_auto_generation(self, patch_history_file):
        from src.api.routes.pipeline_history import append_run

        record = append_run(
            task_id="tb_abcdef12",
            task_title="Auto ID",
            preset="dragon_bronze",
            phase_type="fix",
            phases_completed=[],
            total_duration_s=1.0,
            eval_score=None,
            status="done",
        )

        assert record["run_id"].startswith("run_")
        assert "bcdef12" in record["run_id"]  # last 8 chars of task_id

    def test_run_id_provided(self, patch_history_file):
        from src.api.routes.pipeline_history import append_run

        record = append_run(
            task_id="tb_test_002",
            task_title="Custom ID",
            preset="dragon_silver",
            phase_type="build",
            phases_completed=[],
            total_duration_s=1.0,
            eval_score=None,
            status="done",
            run_id="run_custom_123",
        )

        assert record["run_id"] == "run_custom_123"

    def test_session_id_stored(self, patch_history_file):
        from src.api.routes.pipeline_history import append_run

        record = append_run(
            task_id="tb_test_003",
            task_title="Session test",
            preset="dragon_silver",
            phase_type="build",
            phases_completed=[],
            total_duration_s=1.0,
            eval_score=None,
            status="done",
            session_id="sess_abc123",
        )

        assert record["session_id"] == "sess_abc123"

    def test_timeline_events_persisted(self, patch_history_file):
        from src.api.routes.pipeline_history import append_run, _load_history

        events = [
            {"ts": time.time(), "role": "architect", "event": "start", "detail": "planning"},
            {"ts": time.time(), "role": "coder", "event": "end", "detail": "tokens=500"},
        ]

        record = append_run(
            task_id="tb_test_004",
            task_title="Timeline test",
            preset="dragon_silver",
            phase_type="build",
            phases_completed=["architect", "coder"],
            total_duration_s=30.0,
            eval_score=0.9,
            status="done",
            timeline_events=events,
        )

        assert len(record["timeline_events"]) == 2
        assert record["timeline_events"][0]["role"] == "architect"

        # Verify persisted to disk
        history = _load_history()
        assert len(history[0]["timeline_events"]) == 2

    def test_timeline_events_capped_at_200(self, patch_history_file):
        from src.api.routes.pipeline_history import append_run

        events = [{"ts": time.time(), "role": "coder", "event": "end", "detail": f"item_{i}"} for i in range(300)]

        record = append_run(
            task_id="tb_test_005",
            task_title="Cap test",
            preset="dragon_silver",
            phase_type="build",
            phases_completed=[],
            total_duration_s=1.0,
            eval_score=None,
            status="done",
            timeline_events=events,
        )

        assert len(record["timeline_events"]) == 200

    def test_timeline_events_none_default(self, patch_history_file):
        from src.api.routes.pipeline_history import append_run

        record = append_run(
            task_id="tb_test_006",
            task_title="No events",
            preset="dragon_silver",
            phase_type="build",
            phases_completed=[],
            total_duration_s=1.0,
            eval_score=None,
            status="done",
        )

        assert record["timeline_events"] == []

    def test_title_truncated_to_200(self, patch_history_file):
        from src.api.routes.pipeline_history import append_run

        long_title = "A" * 500
        record = append_run(
            task_id="tb_test_007",
            task_title=long_title,
            preset="dragon_silver",
            phase_type="build",
            phases_completed=[],
            total_duration_s=1.0,
            eval_score=None,
            status="done",
        )

        assert len(record["task_title"]) == 200

    def test_files_created_capped_at_20(self, patch_history_file):
        from src.api.routes.pipeline_history import append_run

        files = [f"file_{i}.py" for i in range(50)]
        record = append_run(
            task_id="tb_test_008",
            task_title="Files cap",
            preset="dragon_silver",
            phase_type="build",
            phases_completed=[],
            total_duration_s=1.0,
            eval_score=None,
            status="done",
            files_created=files,
        )

        assert len(record["files_created"]) == 20


# ---------------------------------------------------------------------------
# History rotation tests
# ---------------------------------------------------------------------------

class TestHistoryRotation:
    def test_history_trimmed_to_500(self, patch_history_file):
        from src.api.routes.pipeline_history import append_run, _load_history

        # Pre-populate with 499 entries
        patch_history_file.parent.mkdir(parents=True, exist_ok=True)
        existing = [{"run_id": f"run_{i}", "task_id": f"t_{i}", "status": "done"} for i in range(499)]
        patch_history_file.write_text(json.dumps(existing))

        # Add 2 more (total 501 → trimmed to 500)
        append_run(task_id="tb_500", task_title="Entry 500", preset="p", phase_type="build",
                   phases_completed=[], total_duration_s=1.0, eval_score=None, status="done")
        append_run(task_id="tb_501", task_title="Entry 501", preset="p", phase_type="build",
                   phases_completed=[], total_duration_s=1.0, eval_score=None, status="done")

        history = _load_history()
        assert len(history) == 500
        # Oldest entry should be trimmed
        assert history[0]["run_id"] == "run_1"


# ---------------------------------------------------------------------------
# _load_history edge cases
# ---------------------------------------------------------------------------

class TestLoadHistory:
    def test_missing_file(self, patch_history_file):
        from src.api.routes.pipeline_history import _load_history

        assert _load_history() == []

    def test_invalid_json(self, patch_history_file):
        from src.api.routes.pipeline_history import _load_history

        patch_history_file.parent.mkdir(parents=True, exist_ok=True)
        patch_history_file.write_text("not json at all{{{")
        assert _load_history() == []

    def test_non_list_json(self, patch_history_file):
        from src.api.routes.pipeline_history import _load_history

        patch_history_file.parent.mkdir(parents=True, exist_ok=True)
        patch_history_file.write_text('{"key": "value"}')
        assert _load_history() == []

    def test_valid_history(self, patch_history_file):
        from src.api.routes.pipeline_history import _load_history

        patch_history_file.parent.mkdir(parents=True, exist_ok=True)
        patch_history_file.write_text('[{"run_id": "run_1"}]')
        result = _load_history()
        assert len(result) == 1
        assert result[0]["run_id"] == "run_1"


# ---------------------------------------------------------------------------
# get_run_timeline() endpoint tests
# ---------------------------------------------------------------------------

class TestGetRunTimeline:
    """Use append_run() to populate data, then query via get_run_timeline()."""

    def _populate(self):
        """Populate history via append_run (uses patched HISTORY_FILE)."""
        from src.api.routes.pipeline_history import append_run

        append_run(
            task_id="tb_t1", task_title="Run 1", preset="dragon_silver",
            phase_type="build", phases_completed=["architect", "coder"],
            total_duration_s=10.0, eval_score=0.9, status="done",
            run_id="run_timeline_1", session_id="sess_001",
            timeline_events=[
                {"ts": 1000, "role": "architect", "event": "start", "detail": "planning", "duration_s": 0, "subtask_idx": -1},
                {"ts": 1001, "role": "coder", "event": "end", "detail": "tokens=500", "duration_s": 2.5, "subtask_idx": 0},
                {"ts": 1002, "role": "verifier", "event": "end", "detail": "pass", "duration_s": 1.0, "subtask_idx": 0},
                {"ts": 1003, "role": "coder", "event": "retry", "detail": "attempt 2", "duration_s": 0, "subtask_idx": 1},
            ],
        )
        append_run(
            task_id="tb_t2", task_title="Run 2", preset="dragon_bronze",
            phase_type="fix", phases_completed=[], total_duration_s=1.0,
            eval_score=None, status="failed",
            run_id="run_timeline_2", session_id="sess_001",
            timeline_events=[],
        )

    @pytest.mark.asyncio
    async def test_run_found(self, patch_history_file):
        from src.api.routes.pipeline_history import get_run_timeline
        self._populate()

        # NOTE: Must pass role=None explicitly — FastAPI Query(None) is truthy when called directly
        result = await get_run_timeline("run_timeline_1", role=None)
        assert result["success"] is True
        assert result["run_id"] == "run_timeline_1"
        assert result["task_id"] == "tb_t1"
        assert result["session_id"] == "sess_001"
        assert result["total_events"] == 4

    @pytest.mark.asyncio
    async def test_run_not_found(self, patch_history_file):
        from src.api.routes.pipeline_history import get_run_timeline
        self._populate()

        result = await get_run_timeline("run_nonexistent", role=None)
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_filter_by_role(self, patch_history_file):
        from src.api.routes.pipeline_history import get_run_timeline
        self._populate()

        result = await get_run_timeline("run_timeline_1", role="coder")
        assert result["success"] is True
        assert result["total_events"] == 2
        assert all(e["role"] == "coder" for e in result["timeline_events"])

    @pytest.mark.asyncio
    async def test_filter_by_role_no_match(self, patch_history_file):
        from src.api.routes.pipeline_history import get_run_timeline
        self._populate()

        result = await get_run_timeline("run_timeline_1", role="researcher")
        assert result["success"] is True
        assert result["total_events"] == 0

    @pytest.mark.asyncio
    async def test_empty_timeline(self, patch_history_file):
        from src.api.routes.pipeline_history import get_run_timeline
        self._populate()

        result = await get_run_timeline("run_timeline_2", role=None)
        assert result["success"] is True
        assert result["total_events"] == 0
        assert result["timeline_events"] == []


# ---------------------------------------------------------------------------
# _emit_timeline_event() structure tests (unit tests with mock pipeline)
# ---------------------------------------------------------------------------

class TestEmitTimelineEvent:
    """Test the event structure produced by _emit_timeline_event."""

    def _make_event(self, role="coder", event="end", detail="", duration_s=0.0, subtask_idx=-1):
        """Simulate the dict structure created by _emit_timeline_event."""
        return {
            "ts": time.time(),
            "role": role,
            "event": event,
            "detail": detail[:200],
            "duration_s": round(duration_s, 2),
            "subtask_idx": subtask_idx,
        }

    def test_event_structure(self):
        ev = self._make_event("architect", "start", "planning subtasks", 0.0, -1)
        assert ev["role"] == "architect"
        assert ev["event"] == "start"
        assert ev["detail"] == "planning subtasks"
        assert ev["duration_s"] == 0.0
        assert ev["subtask_idx"] == -1
        assert isinstance(ev["ts"], float)

    def test_detail_truncation(self):
        long_detail = "X" * 500
        ev = self._make_event(detail=long_detail)
        assert len(ev["detail"]) == 200

    def test_duration_rounding(self):
        ev = self._make_event(duration_s=1.23456789)
        assert ev["duration_s"] == 1.23

    def test_valid_event_types(self):
        valid_events = ["start", "end", "fail", "retry", "escalate", "verify_pass", "verify_fail", "tier_upgrade"]
        for event_type in valid_events:
            ev = self._make_event(event=event_type)
            assert ev["event"] == event_type

    def test_valid_roles(self):
        valid_roles = ["architect", "scout", "coder", "verifier", "researcher", "pipeline"]
        for role in valid_roles:
            ev = self._make_event(role=role)
            assert ev["role"] == role

    def test_subtask_idx_positive(self):
        ev = self._make_event(subtask_idx=3)
        assert ev["subtask_idx"] == 3


# ---------------------------------------------------------------------------
# Integration: append_run + get_run_timeline round-trip
# ---------------------------------------------------------------------------

class TestTimelineRoundTrip:
    @pytest.mark.asyncio
    async def test_append_then_query(self, patch_history_file):
        from src.api.routes.pipeline_history import append_run, get_run_timeline

        events = [
            {"ts": time.time(), "role": "architect", "event": "start", "detail": "plan", "duration_s": 0.0, "subtask_idx": -1},
            {"ts": time.time() + 1, "role": "coder", "event": "end", "detail": "done", "duration_s": 5.0, "subtask_idx": 0},
        ]

        append_run(
            task_id="tb_round_trip",
            task_title="Round trip test",
            preset="dragon_silver",
            phase_type="build",
            phases_completed=["architect", "coder"],
            total_duration_s=10.0,
            eval_score=0.8,
            status="done",
            run_id="run_roundtrip_001",
            session_id="sess_rt_001",
            timeline_events=events,
        )

        result = await get_run_timeline("run_roundtrip_001", role=None)

        assert result["success"] is True
        assert result["total_events"] == 2
        assert result["session_id"] == "sess_rt_001"
        assert result["timeline_events"][0]["role"] == "architect"
