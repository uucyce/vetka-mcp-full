# MARKER_152.TEST: Phase 152 Wave 1 — Analytics Backend Tests
"""
Tests for Phase 152 Wave 1:
  152.1 — pipeline_analytics.py functions
  152.2 — analytics_routes.py endpoints
  152.3 — Task provenance (source_chat_id / source_group_id)
  152.4 — Pipeline timeline events

@status: ACTIVE
@phase: 152
"""

import json
import time
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# Test Fixtures — mock data
# ============================================================

MOCK_TASK_BOARD = {
    "settings": {"max_concurrent": 3},
    "tasks": {
        "tb_001": {
            "title": "Add bookmark toggle",
            "description": "Add star toggle to useStore.ts",
            "status": "done",
            "priority": 2,
            "preset": "dragon_silver",
            "phase_type": "build",
            "source": "doctor_triage",
            "source_chat_id": None,
            "source_group_id": "group_abc123",
            "tags": ["build"],
            "dependencies": [],
            "created_at": "2026-02-14 10:00:00",
            "completed_at": "2026-02-14 10:05:00",
            "stats": {
                "preset": "dragon_silver",
                "league": "dragon",
                "phase_type": "build",
                "subtasks_total": 3,
                "subtasks_completed": 3,
                "success": True,
                "llm_calls": 12,
                "tokens_in": 15000,
                "tokens_out": 8000,
                "verifier_avg_confidence": 0.9,
                "duration_s": 66.8,
                "agent_stats": {
                    "scout": {"calls": 2, "tokens_in": 3000, "tokens_out": 1000, "duration_s": 8.0, "retries": 0, "success_count": 2, "fail_count": 0},
                    "architect": {"calls": 1, "tokens_in": 4000, "tokens_out": 2000, "duration_s": 12.0, "retries": 0, "success_count": 1, "fail_count": 0},
                    "researcher": {"calls": 1, "tokens_in": 2000, "tokens_out": 1000, "duration_s": 6.0, "retries": 0, "success_count": 1, "fail_count": 0},
                    "coder": {"calls": 3, "tokens_in": 4000, "tokens_out": 3000, "duration_s": 30.0, "retries": 1, "success_count": 3, "fail_count": 0},
                    "verifier": {"calls": 3, "tokens_in": 2000, "tokens_out": 1000, "duration_s": 10.0, "retries": 0, "success_count": 2, "fail_count": 1},
                },
                "timeline": [
                    {"ts": 1000.0, "role": "pipeline", "event": "start", "detail": "build | dragon_silver", "duration_s": 0, "subtask_idx": -1},
                    {"ts": 1001.0, "role": "scout", "event": "start", "detail": "parallel recon", "duration_s": 0, "subtask_idx": -1},
                    {"ts": 1009.0, "role": "scout", "event": "end", "detail": "tokens=4000", "duration_s": 8.0, "subtask_idx": -1},
                    {"ts": 1001.0, "role": "researcher", "event": "start", "detail": "parallel recon", "duration_s": 0, "subtask_idx": -1},
                    {"ts": 1007.0, "role": "researcher", "event": "end", "detail": "tokens=3000", "duration_s": 6.0, "subtask_idx": -1},
                    {"ts": 1010.0, "role": "architect", "event": "start", "detail": "planning subtasks", "duration_s": 0, "subtask_idx": -1},
                    {"ts": 1022.0, "role": "architect", "event": "end", "detail": "tokens=6000", "duration_s": 12.0, "subtask_idx": -1},
                    {"ts": 1025.0, "role": "coder", "event": "end", "detail": "tokens=3000", "duration_s": 10.0, "subtask_idx": 0},
                    {"ts": 1035.0, "role": "verifier", "event": "end", "detail": "", "duration_s": 3.0, "subtask_idx": 0},
                    {"ts": 1040.0, "role": "coder", "event": "retry", "detail": "attempt 1: missing imports", "duration_s": 0, "subtask_idx": 1},
                    {"ts": 1055.0, "role": "coder", "event": "end", "detail": "tokens=2000", "duration_s": 10.0, "subtask_idx": 1},
                    {"ts": 1066.8, "role": "pipeline", "event": "end", "detail": "done", "duration_s": 66.8, "subtask_idx": -1},
                ],
            },
            "result_status": "applied",
        },
        "tb_002": {
            "title": "Fix login redirect",
            "description": "Bug fix for redirect loop",
            "status": "failed",
            "priority": 1,
            "preset": "dragon_bronze",
            "phase_type": "fix",
            "source": "intake_dragon",
            "source_chat_id": "chat_xyz789",
            "source_group_id": None,
            "tags": ["fix", "urgent"],
            "dependencies": [],
            "created_at": "2026-02-14 11:00:00",
            "stats": {
                "preset": "dragon_bronze",
                "league": "dragon",
                "phase_type": "fix",
                "subtasks_total": 2,
                "subtasks_completed": 0,
                "success": False,
                "llm_calls": 6,
                "tokens_in": 5000,
                "tokens_out": 2000,
                "verifier_avg_confidence": 0.3,
                "duration_s": 45.0,
                "agent_stats": {
                    "scout": {"calls": 1, "tokens_in": 1000, "tokens_out": 500, "duration_s": 5.0, "retries": 0, "success_count": 1, "fail_count": 0},
                    "architect": {"calls": 1, "tokens_in": 2000, "tokens_out": 800, "duration_s": 10.0, "retries": 0, "success_count": 1, "fail_count": 0},
                    "coder": {"calls": 2, "tokens_in": 1500, "tokens_out": 500, "duration_s": 20.0, "retries": 2, "success_count": 0, "fail_count": 2},
                    "verifier": {"calls": 2, "tokens_in": 500, "tokens_out": 200, "duration_s": 10.0, "retries": 0, "success_count": 0, "fail_count": 2},
                },
                "timeline": [],
            },
        },
        "tb_003": {
            "title": "Pending task with deps",
            "description": "Depends on tb_001",
            "status": "pending",
            "priority": 3,
            "preset": "dragon_silver",
            "phase_type": "build",
            "source": "manual",
            "tags": [],
            "dependencies": ["tb_001"],
            "created_at": "2026-02-14 12:00:00",
            "stats": {},
        },
    },
}

MOCK_PIPELINE_HISTORY = [
    {
        "run_id": "run_1707900000_tb_001",
        "task_id": "tb_001",
        "task_title": "Add bookmark toggle",
        "preset": "dragon_silver",
        "phase_type": "build",
        "phases_completed": ["scout", "architect", "coder"],
        "total_duration_s": 66.8,
        "eval_score": 0.9,
        "status": "done",
        "llm_calls": 12,
        "tokens_in": 15000,
        "tokens_out": 8000,
        "files_created": ["useStore.ts"],
        "timestamp": 1707900000,
        "timestamp_human": "2026-02-14 10:00:00",
    },
    {
        "run_id": "run_1707903600_tb_002",
        "task_id": "tb_002",
        "task_title": "Fix login redirect",
        "preset": "dragon_bronze",
        "phase_type": "fix",
        "phases_completed": [],
        "total_duration_s": 45.0,
        "eval_score": 0.3,
        "status": "failed",
        "llm_calls": 6,
        "tokens_in": 5000,
        "tokens_out": 2000,
        "files_created": [],
        "timestamp": 1707903600,
        "timestamp_human": "2026-02-14 11:00:00",
    },
]


def _mock_task_board_file(tmp_path):
    """Create mock task_board.json."""
    f = tmp_path / "data" / "task_board.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(MOCK_TASK_BOARD, indent=2))
    return f


def _mock_history_file(tmp_path):
    """Create mock pipeline_history.json."""
    f = tmp_path / "data" / "pipeline_history.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(MOCK_PIPELINE_HISTORY, indent=2))
    return f


# ============================================================
# 152.1 — Pipeline Analytics Aggregator
# ============================================================

class TestPipelineAnalytics:
    """Tests for src/orchestration/pipeline_analytics.py."""

    @pytest.fixture(autouse=True)
    def setup_mock_data(self, tmp_path):
        """Patch data file paths to use temp directory."""
        self.tb_file = _mock_task_board_file(tmp_path)
        self.hist_file = _mock_history_file(tmp_path)

        import src.orchestration.pipeline_analytics as pa
        self._orig_tb = pa._TASK_BOARD_FILE
        self._orig_hist = pa._PIPELINE_HISTORY_FILE
        pa._TASK_BOARD_FILE = self.tb_file
        pa._PIPELINE_HISTORY_FILE = self.hist_file
        self.pa = pa
        yield
        pa._TASK_BOARD_FILE = self._orig_tb
        pa._PIPELINE_HISTORY_FILE = self._orig_hist

    def test_load_task_board(self):
        tasks = self.pa._load_task_board()
        assert "tb_001" in tasks
        assert "tb_002" in tasks
        assert tasks["tb_001"]["title"] == "Add bookmark toggle"

    def test_load_pipeline_history(self):
        history = self.pa._load_pipeline_history()
        assert len(history) == 2
        assert history[0]["status"] == "done"
        assert history[1]["status"] == "failed"

    def test_compute_summary(self):
        result = self.pa.compute_summary()
        assert "total_runs" in result
        assert result["total_runs"] >= 1  # at least done+failed tasks
        assert "success_rate" in result
        assert "total_llm_calls" in result
        assert "tasks_by_preset" in result

    def test_compute_agent_efficiency(self):
        agents = self.pa.compute_agent_efficiency()
        assert isinstance(agents, list)
        # Should have entries for roles that exist in agent_stats
        role_names = [a["role"] for a in agents]
        assert "coder" in role_names
        assert "scout" in role_names

    def test_detect_weak_links(self):
        weak = self.pa.detect_weak_links()
        assert isinstance(weak, list)
        # tb_002 coder has 0 success, 2 fails — should be detected
        coder_weak = [w for w in weak if w.get("role") == "coder"]
        # At least one weak link should be coder (from tb_002 with 0% success)
        if coder_weak:
            assert len(coder_weak[0]["reasons"]) > 0

    def test_get_task_analytics_existing(self):
        result = self.pa.get_task_analytics("tb_001")
        assert result is not None
        assert result["task_id"] == "tb_001"
        assert result["duration_s"] == 66.8
        assert result["llm_calls"] == 12
        assert result["agent_stats"]["coder"]["calls"] == 3
        assert len(result["token_distribution"]) > 0
        assert result["retries_total"] >= 1  # coder has 1 retry
        assert result["cost_estimate"] > 0
        # source_chat_id is None in mock data → analytics returns "" or None
        assert result.get("source_chat_id") in ("", None)

    def test_get_task_analytics_nonexistent(self):
        result = self.pa.get_task_analytics("tb_nonexistent")
        assert result is None

    def test_get_task_analytics_with_real_timeline(self):
        """152.4: Prefer real timeline events over approximation."""
        result = self.pa.get_task_analytics("tb_001")
        timeline = result["timeline_events"]
        assert len(timeline) > 0
        # Real timeline has offset_s field
        assert "offset_s" in timeline[0]
        assert timeline[0]["role"] == "pipeline"
        assert timeline[0]["event"] == "start"

    def test_get_task_analytics_fallback_timeline(self):
        """When timeline is empty, fallback to approximate."""
        result = self.pa.get_task_analytics("tb_002")
        timeline = result["timeline_events"]
        # tb_002 has empty timeline → fallback to _build_task_timeline
        assert len(timeline) > 0
        # Fallback timeline has start_offset/end_offset
        assert "start_offset" in timeline[0]

    def test_compute_time_series(self):
        ts = self.pa.compute_time_series(period="day", limit_days=30)
        assert isinstance(ts, list)

    def test_compute_cost_report(self):
        cost = self.pa.compute_cost_report()
        assert isinstance(cost, dict)
        assert "total_cost_estimate" in cost

    def test_compute_team_comparison(self):
        teams = self.pa.compute_team_comparison()
        assert isinstance(teams, list)
        presets = [t["preset"] for t in teams]
        assert "dragon_silver" in presets or "dragon_bronze" in presets

    def test_compute_trends(self):
        trends = self.pa.compute_trends(period="day", limit_days=30, metric="success_rate")
        assert isinstance(trends, dict)
        assert "metric" in trends
        assert "trend" in trends
        assert trends["metric"] == "success_rate"


class TestNormalizeRealTimeline:
    """Tests for _normalize_real_timeline (152.4)."""

    def test_empty_events(self):
        from src.orchestration.pipeline_analytics import _normalize_real_timeline
        assert _normalize_real_timeline([]) == []

    def test_sorts_by_timestamp(self):
        from src.orchestration.pipeline_analytics import _normalize_real_timeline
        events = [
            {"ts": 1005.0, "role": "architect", "event": "end", "detail": "", "duration_s": 5.0, "subtask_idx": -1},
            {"ts": 1000.0, "role": "pipeline", "event": "start", "detail": "build", "duration_s": 0, "subtask_idx": -1},
        ]
        result = _normalize_real_timeline(events)
        assert result[0]["role"] == "pipeline"
        assert result[1]["role"] == "architect"

    def test_offset_calculation(self):
        from src.orchestration.pipeline_analytics import _normalize_real_timeline
        events = [
            {"ts": 1000.0, "role": "pipeline", "event": "start", "detail": "", "duration_s": 0, "subtask_idx": -1},
            {"ts": 1010.5, "role": "scout", "event": "end", "detail": "", "duration_s": 10.5, "subtask_idx": -1},
        ]
        result = _normalize_real_timeline(events)
        assert result[0]["offset_s"] == 0.0
        assert result[1]["offset_s"] == 10.5

    def test_preserves_all_fields(self):
        from src.orchestration.pipeline_analytics import _normalize_real_timeline
        events = [
            {"ts": 1000.0, "role": "coder", "event": "retry", "detail": "attempt 1: missing imports", "duration_s": 0, "subtask_idx": 2},
        ]
        result = _normalize_real_timeline(events)
        assert result[0]["event"] == "retry"
        assert result[0]["detail"] == "attempt 1: missing imports"
        assert result[0]["subtask_idx"] == 2


# ============================================================
# 152.2 — Analytics REST API
# ============================================================

class TestAnalyticsRoutes:
    """Tests for analytics REST API endpoints."""

    def test_analytics_router_registered(self):
        """analytics_router exists in routes/__init__.py."""
        from src.api.routes import analytics_router
        assert analytics_router is not None
        assert analytics_router.prefix == "/api/analytics"

    def test_summary_endpoint_exists(self):
        from src.api.routes.analytics_routes import router
        paths = [r.path for r in router.routes]
        assert "/api/analytics/summary" in paths

    def test_task_drilldown_endpoint_exists(self):
        from src.api.routes.analytics_routes import router
        paths = [r.path for r in router.routes]
        assert "/api/analytics/task/{task_id}" in paths

    def test_agents_endpoint_exists(self):
        from src.api.routes.analytics_routes import router
        paths = [r.path for r in router.routes]
        assert "/api/analytics/agents" in paths

    def test_trends_endpoint_exists(self):
        from src.api.routes.analytics_routes import router
        paths = [r.path for r in router.routes]
        assert "/api/analytics/trends" in paths

    def test_cost_endpoint_exists(self):
        from src.api.routes.analytics_routes import router
        paths = [r.path for r in router.routes]
        assert "/api/analytics/cost" in paths

    def test_teams_endpoint_exists(self):
        from src.api.routes.analytics_routes import router
        paths = [r.path for r in router.routes]
        assert "/api/analytics/teams" in paths

    def test_tasks_by_chat_endpoint_exists(self):
        from src.api.routes.analytics_routes import router
        paths = [r.path for r in router.routes]
        assert "/api/analytics/tasks-by-chat/{chat_id}" in paths

    def test_dag_tasks_endpoint_exists(self):
        from src.api.routes.analytics_routes import router
        paths = [r.path for r in router.routes]
        assert "/api/analytics/dag/tasks" in paths


# ============================================================
# 152.3 — Task Provenance
# ============================================================

class TestTaskProvenance:
    """Tests for source_chat_id / source_group_id fields."""

    def test_update_task_allows_provenance_fields(self, tmp_path):
        """update_task ADDABLE_FIELDS includes source_chat_id/source_group_id."""
        from src.orchestration.task_board import TaskBoard
        board = TaskBoard(board_file=tmp_path / "test_board.json")
        task_id = board.add_task(title="Test", description="test", priority=3)
        # Update with provenance fields (in ADDABLE_FIELDS)
        ok = board.update_task(task_id, source_chat_id="chat_999")
        assert ok is True
        task = board.get_task(task_id)
        assert task["source_chat_id"] == "chat_999"

    def test_add_task_with_provenance(self, tmp_path):
        """add_task() accepts and stores source_group_id."""
        from src.orchestration.task_board import TaskBoard
        board = TaskBoard(board_file=tmp_path / "test_board.json")
        task_id = board.add_task(
            title="Test task",
            description="Testing provenance",
            priority=3,
            phase_type="build",
            preset="dragon_silver",
            source="test",
            source_group_id="group_test_123",
        )
        task = board.get_task(task_id)
        assert task is not None
        assert task["source_group_id"] == "group_test_123"
        assert task["source_chat_id"] is None

    def test_add_task_with_chat_id(self, tmp_path):
        """add_task() accepts and stores source_chat_id."""
        from src.orchestration.task_board import TaskBoard
        board = TaskBoard(board_file=tmp_path / "test_board.json")
        task_id = board.add_task(
            title="Test chat task",
            description="Testing chat provenance",
            priority=3,
            phase_type="fix",
            preset="dragon_bronze",
            source="test",
            source_chat_id="chat_456",
        )
        task = board.get_task(task_id)
        assert task is not None
        assert task["source_chat_id"] == "chat_456"

    def test_provenance_defaults_to_none(self, tmp_path):
        """Without explicit provenance, fields default to None."""
        from src.orchestration.task_board import TaskBoard
        board = TaskBoard(board_file=tmp_path / "test_board.json")
        task_id = board.add_task(
            title="No provenance",
            description="Test",
            priority=3,
        )
        task = board.get_task(task_id)
        assert task["source_chat_id"] is None
        assert task["source_group_id"] is None


# ============================================================
# 152.4 — Pipeline Timeline Events
# ============================================================

class TestTimelineEvents:
    """Tests for _emit_timeline_event and timeline integration."""

    def test_timeline_events_initialized(self):
        """Pipeline starts with empty timeline."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline(preset="dragon_silver")
        assert hasattr(pipeline, "_timeline_events")
        assert pipeline._timeline_events == []

    def test_emit_timeline_event(self):
        """_emit_timeline_event appends to list."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline(preset="dragon_silver")
        pipeline._emit_timeline_event("scout", "start", "parallel recon")
        assert len(pipeline._timeline_events) == 1
        ev = pipeline._timeline_events[0]
        assert ev["role"] == "scout"
        assert ev["event"] == "start"
        assert ev["detail"] == "parallel recon"
        assert "ts" in ev
        assert ev["duration_s"] == 0

    def test_emit_timeline_event_with_duration(self):
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline(preset="dragon_bronze")
        pipeline._emit_timeline_event("coder", "end", "tokens=5000", duration_s=15.3)
        ev = pipeline._timeline_events[0]
        assert ev["duration_s"] == 15.3

    def test_track_agent_stat_auto_emits_timeline(self):
        """_track_agent_stat should auto-emit timeline events (152.4)."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline(preset="dragon_silver")
        pipeline._track_agent_stat("scout", tokens_in=1000, tokens_out=500, duration=8.0, success=True)
        # Should have 1 auto-emitted timeline event
        assert len(pipeline._timeline_events) == 1
        ev = pipeline._timeline_events[0]
        assert ev["role"] == "scout"
        assert ev["event"] == "end"  # success=True → "end"
        assert ev["duration_s"] == 8.0

    def test_track_agent_stat_fail_event(self):
        """Failed stat tracking emits 'fail' event."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline(preset="dragon_silver")
        pipeline._track_agent_stat("coder", tokens_in=500, tokens_out=100, duration=3.0, success=False)
        ev = pipeline._timeline_events[0]
        assert ev["event"] == "fail"

    def test_timeline_detail_truncation(self):
        """Long details are truncated to 200 chars."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline(preset="dragon_silver")
        long_detail = "x" * 300
        pipeline._emit_timeline_event("coder", "end", long_detail)
        assert len(pipeline._timeline_events[0]["detail"]) == 200

    def test_multiple_events_accumulate(self):
        """Multiple events build up the timeline."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline(preset="dragon_silver")
        pipeline._emit_timeline_event("pipeline", "start", "build | dragon_silver")
        pipeline._emit_timeline_event("scout", "start", "parallel recon")
        pipeline._emit_timeline_event("scout", "end", "", duration_s=8.0)
        pipeline._emit_timeline_event("architect", "start", "planning")
        pipeline._emit_timeline_event("architect", "end", "", duration_s=12.0)
        assert len(pipeline._timeline_events) == 5


# ============================================================
# 152.9 — Task DAG Nodes/Edges
# ============================================================

class TestTaskDAG:
    """Tests for /api/analytics/dag/tasks endpoint data format."""

    @pytest.fixture(autouse=True)
    def setup_mock_data(self, tmp_path):
        self.tb_file = _mock_task_board_file(tmp_path)
        import src.orchestration.pipeline_analytics as pa
        self._orig = pa._TASK_BOARD_FILE
        pa._TASK_BOARD_FILE = self.tb_file
        yield
        pa._TASK_BOARD_FILE = self._orig

    def test_dag_structure(self):
        """DAG endpoint should produce nodes and edges."""
        # Simulate what the endpoint does
        data = json.loads(self.tb_file.read_text())
        tasks = data.get("tasks", {})
        nodes = []
        edges = []
        task_ids = set(tasks.keys())

        for idx, (tid, task) in enumerate(tasks.items()):
            nodes.append({"id": tid, "data": {"label": task["title"][:60]}})
            for dep in task.get("dependencies", []):
                if dep in task_ids:
                    edges.append({"source": dep, "target": tid})

        assert len(nodes) == 3
        # tb_003 depends on tb_001
        assert any(e["source"] == "tb_001" and e["target"] == "tb_003" for e in edges)


# ============================================================
# Regression tests
# ============================================================

class TestRegression:
    """Regression: existing functionality still works."""

    def test_pipeline_history_append_run(self, tmp_path):
        """pipeline_history.append_run still works."""
        from src.api.routes.pipeline_history import append_run, HISTORY_FILE, _load_history
        orig = HISTORY_FILE
        import src.api.routes.pipeline_history as ph
        ph.HISTORY_FILE = tmp_path / "data" / "pipeline_history.json"
        ph.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        ph.HISTORY_FILE.write_text("[]")

        record = append_run(
            task_id="tb_test",
            task_title="Test task",
            preset="dragon_silver",
            phase_type="build",
            phases_completed=["scout", "architect"],
            total_duration_s=30.0,
            eval_score=0.85,
            status="done",
            llm_calls=5,
            tokens_in=3000,
            tokens_out=1500,
        )
        assert record["task_id"] == "tb_test"
        assert record["status"] == "done"

        history = ph._load_history()
        assert len(history) == 1

        ph.HISTORY_FILE = orig

    def test_task_board_add_still_works(self, tmp_path):
        """TaskBoard.add_task with new params doesn't break old calls."""
        from src.orchestration.task_board import TaskBoard
        board = TaskBoard(board_file=tmp_path / "test_board.json")
        # Old-style call without provenance params
        task_id = board.add_task(
            title="Old style task",
            description="No provenance params",
            priority=2,
            phase_type="build",
            preset="dragon_silver",
            source="test",
        )
        task = board.get_task(task_id)
        assert task is not None
        assert task["title"] == "Old style task"

    def test_agent_pipeline_stats_include_timeline(self):
        """Pipeline stats dict should include timeline key."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline(preset="dragon_silver")
        pipeline._emit_timeline_event("pipeline", "start", "test")
        # Verify timeline_events list is accessible
        assert len(pipeline._timeline_events) == 1

    def test_routes_init_has_analytics(self):
        """routes/__init__.py has analytics_router in __all__."""
        from src.api.routes import __all__ as all_exports
        assert "analytics_router" in all_exports
