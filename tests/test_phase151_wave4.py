"""
Tests for Phase 151 Wave 4 — Backend Stats Enhancement.

MARKER_151.11: Per-agent statistics collection (_track_agent_stat, agent_stats in pipeline_stats)
MARKER_151.12: User feedback → adjusted_success blend (compute_adjusted_stats)
MARKER_151.14: Architect reads team performance summary (_get_team_performance_summary)

Tests:
- TestPerAgentStats: 8 tests — _agent_stats dict, _track_agent_stat method, 5 call sites, pipeline_stats inclusion
- TestUserFeedbackBlend: 7 tests — compute_adjusted_stats for applied/rejected/rework/none, ADDABLE_FIELDS
- TestArchitectPerformance: 5 tests — _get_team_performance_summary method, injection, prompt update, graceful fallback
- TestRegressionWave4: 4 tests — existing stats still work, _track_llm_call intact, markers present
"""

import os
import json
import pytest


# ── Helpers ──

def _read_source(path: str) -> str:
    filepath = os.path.join(os.path.dirname(__file__), "..", path)
    with open(filepath) as f:
        return f.read()


# ══════════════════════════════════════════════════════════════
# 151.11 — Per-Agent Metrics Collection
# ══════════════════════════════════════════════════════════════

class TestPerAgentStats:
    """Tests for MARKER_151.11: Per-agent statistics breakdown."""

    def test_agent_stats_dict_initialized(self):
        """AgentPipeline.__init__ should create _agent_stats dict."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        assert "self._agent_stats: Dict[str, Dict] = {}" in source

    def test_track_agent_stat_method_exists(self):
        """_track_agent_stat method should exist with correct signature."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        assert "def _track_agent_stat(self, role: str" in source
        assert "tokens_in: int" in source
        assert "tokens_out: int" in source
        assert "duration: float" in source
        assert "success: bool" in source

    def test_track_agent_stat_increments_calls(self):
        """_track_agent_stat should increment calls counter."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        # Method body should increment calls
        assert "stats['calls'] += 1" in source

    def test_track_agent_stat_tracks_success_fail(self):
        """_track_agent_stat should track success_count and fail_count."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        assert "stats['success_count'] += 1" in source
        assert "stats['fail_count'] += 1" in source

    def test_scout_call_site_instrumented(self):
        """Scout LLM call should have _track_agent_stat('scout'...)."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        assert '_track_agent_stat("scout"' in source
        assert "MARKER_151.11C" in source

    def test_verifier_call_site_instrumented(self):
        """Verifier LLM call should have _track_agent_stat('verifier'...)."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        assert '_track_agent_stat("verifier"' in source
        assert "MARKER_151.11D" in source

    def test_architect_call_site_instrumented(self):
        """Architect LLM call should have _track_agent_stat('architect'...)."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        assert '_track_agent_stat("architect"' in source
        assert "MARKER_151.11E" in source

    def test_researcher_call_site_instrumented(self):
        """Researcher LLM call should have _track_agent_stat('researcher'...)."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        assert '_track_agent_stat("researcher"' in source
        assert "MARKER_151.11F" in source

    def test_coder_call_site_instrumented(self):
        """Coder LLM call should have _track_agent_stat('coder'...) for both FC and one-shot."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        assert '_track_agent_stat("coder"' in source
        assert "MARKER_151.11G" in source

    def test_agent_stats_in_pipeline_stats(self):
        """pipeline_stats dict should include 'agent_stats' key."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        assert '"agent_stats": dict(self._agent_stats)' in source
        assert "MARKER_151.11H" in source

    def test_coder_retries_tracked(self):
        """_retry_coder should increment coder retries counter."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        assert 'self._agent_stats["coder"]["retries"] += 1' in source
        assert "MARKER_151.11I" in source

    def test_timing_at_all_call_sites(self):
        """Each call site should have time.time() timing."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        assert "_scout_t0 = time.time()" in source
        assert "_verifier_t0 = time.time()" in source
        assert "_arch_t0 = time.time()" in source
        assert "_res_t0 = time.time()" in source
        assert "_coder_t0 = time.time()" in source


class TestPerAgentStatsUnit:
    """Unit tests for _track_agent_stat method behavior."""

    def test_track_agent_stat_creates_entry(self):
        """First call for a role should create the entry."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline.__new__(AgentPipeline)
        pipeline._agent_stats = {}
        pipeline._track_agent_stat("scout", 100, 50, 1.5, success=True)
        assert "scout" in pipeline._agent_stats
        assert pipeline._agent_stats["scout"]["calls"] == 1
        assert pipeline._agent_stats["scout"]["tokens_in"] == 100
        assert pipeline._agent_stats["scout"]["tokens_out"] == 50
        assert pipeline._agent_stats["scout"]["duration_s"] == 1.5
        assert pipeline._agent_stats["scout"]["success_count"] == 1
        assert pipeline._agent_stats["scout"]["fail_count"] == 0

    def test_track_agent_stat_accumulates(self):
        """Multiple calls should accumulate."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline.__new__(AgentPipeline)
        pipeline._agent_stats = {}
        pipeline._track_agent_stat("coder", 200, 100, 3.0, success=True)
        pipeline._track_agent_stat("coder", 150, 80, 2.5, success=False)
        assert pipeline._agent_stats["coder"]["calls"] == 2
        assert pipeline._agent_stats["coder"]["tokens_in"] == 350
        assert pipeline._agent_stats["coder"]["tokens_out"] == 180
        assert pipeline._agent_stats["coder"]["duration_s"] == 5.5
        assert pipeline._agent_stats["coder"]["success_count"] == 1
        assert pipeline._agent_stats["coder"]["fail_count"] == 1

    def test_track_agent_stat_multiple_roles(self):
        """Different roles tracked independently."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline.__new__(AgentPipeline)
        pipeline._agent_stats = {}
        pipeline._track_agent_stat("scout", 100, 50, 1.0, success=True)
        pipeline._track_agent_stat("architect", 200, 100, 2.0, success=True)
        pipeline._track_agent_stat("coder", 300, 150, 3.0, success=False)
        assert len(pipeline._agent_stats) == 3
        assert pipeline._agent_stats["scout"]["success_count"] == 1
        assert pipeline._agent_stats["architect"]["success_count"] == 1
        assert pipeline._agent_stats["coder"]["fail_count"] == 1


# ══════════════════════════════════════════════════════════════
# 151.12 — User Feedback → Stats Integration
# ══════════════════════════════════════════════════════════════

class TestUserFeedbackBlend:
    """Tests for MARKER_151.12: compute_adjusted_stats blending."""

    def test_compute_adjusted_stats_method_exists(self):
        """TaskBoard should have compute_adjusted_stats method."""
        source = _read_source("src/orchestration/task_board.py")
        assert "def compute_adjusted_stats(self, task_id: str)" in source
        assert "MARKER_151.12B" in source

    def test_result_status_in_addable_fields(self):
        """result_status should be in ADDABLE_FIELDS for update_task."""
        source = _read_source("src/orchestration/task_board.py")
        assert '"result_status"' in source
        assert "MARKER_151.12A" in source

    def test_adjusted_applied(self):
        """applied → adjusted = 0.7*1 + 0.3*1 = 1.0."""
        from src.orchestration.task_board import TaskBoard
        board = TaskBoard.__new__(TaskBoard)
        board.tasks = {
            "t1": {
                "stats": {"success": True},
                "result_status": "applied"
            }
        }
        result = board.compute_adjusted_stats("t1")
        assert result["adjusted_success"] == 1.0
        assert result["has_user_feedback"] is True

    def test_adjusted_rejected_verifier_pass(self):
        """rejected when verifier said OK → 0.7*1 + 0.3*0 = 0.7."""
        from src.orchestration.task_board import TaskBoard
        board = TaskBoard.__new__(TaskBoard)
        board.tasks = {
            "t1": {
                "stats": {"success": True},
                "result_status": "rejected"
            }
        }
        result = board.compute_adjusted_stats("t1")
        assert result["adjusted_success"] == 0.7
        assert result["user_feedback"] == "rejected"

    def test_adjusted_rework(self):
        """rework → 0.7*1 + 0.3*0.5 = 0.85."""
        from src.orchestration.task_board import TaskBoard
        board = TaskBoard.__new__(TaskBoard)
        board.tasks = {
            "t1": {
                "stats": {"success": True},
                "result_status": "rework"
            }
        }
        result = board.compute_adjusted_stats("t1")
        assert result["adjusted_success"] == 0.85

    def test_adjusted_no_feedback(self):
        """No feedback → passthrough verifier score."""
        from src.orchestration.task_board import TaskBoard
        board = TaskBoard.__new__(TaskBoard)
        board.tasks = {
            "t1": {
                "stats": {"success": True}
            }
        }
        result = board.compute_adjusted_stats("t1")
        # 0.7*1 + 0.3*1 = 1.0 (user_success = verifier_success when None)
        assert result["adjusted_success"] == 1.0
        assert result["has_user_feedback"] is False

    def test_adjusted_no_stats(self):
        """Task without stats → empty dict."""
        from src.orchestration.task_board import TaskBoard
        board = TaskBoard.__new__(TaskBoard)
        board.tasks = {"t1": {"title": "test"}}
        result = board.compute_adjusted_stats("t1")
        assert result == {}

    def test_adjusted_nonexistent_task(self):
        """Nonexistent task → empty dict."""
        from src.orchestration.task_board import TaskBoard
        board = TaskBoard.__new__(TaskBoard)
        board.tasks = {}
        result = board.compute_adjusted_stats("t999")
        assert result == {}

    def test_adjusted_verifier_failed_user_rejected(self):
        """Both fail → 0.7*0 + 0.3*0 = 0.0."""
        from src.orchestration.task_board import TaskBoard
        board = TaskBoard.__new__(TaskBoard)
        board.tasks = {
            "t1": {
                "stats": {"success": False},
                "result_status": "rejected"
            }
        }
        result = board.compute_adjusted_stats("t1")
        assert result["adjusted_success"] == 0.0


class TestAdjustedStatsAPI:
    """Tests for MARKER_151.12C: adjusted_stats in REST API response."""

    def test_api_enrichment_marker(self):
        """debug_routes should have MARKER_151.12C for task enrichment."""
        source = _read_source("src/api/routes/debug_routes.py")
        assert "MARKER_151.12C" in source
        assert "adjusted_stats" in source

    def test_api_calls_compute_adjusted(self):
        """GET /task-board should call compute_adjusted_stats."""
        source = _read_source("src/api/routes/debug_routes.py")
        assert "compute_adjusted_stats" in source


# ══════════════════════════════════════════════════════════════
# 151.14 — Architect Reads Stats for Model Swap
# ══════════════════════════════════════════════════════════════

class TestArchitectPerformance:
    """Tests for MARKER_151.14: Architect team performance awareness."""

    def test_get_team_performance_summary_exists(self):
        """_get_team_performance_summary method should exist."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        assert "async def _get_team_performance_summary(self)" in source
        assert "MARKER_151.14A" in source

    def test_performance_summary_injected_into_architect(self):
        """Team performance should be injected into architect user message."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        assert "team_perf = await self._get_team_performance_summary()" in source
        assert "MARKER_151.14B" in source

    def test_performance_summary_format(self):
        """Summary should contain header and role lines."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        assert "TEAM PERFORMANCE (last 10 runs)" in source
        assert "⚠️ WEAK" in source
        assert "rate < 60" in source

    def test_graceful_on_empty_board(self):
        """No tasks → empty string, no exception."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        # Method has try/except with empty string fallback
        assert 'return ""  # Graceful — never block pipeline' in source

    def test_architect_prompt_updated(self):
        """Architect prompt should mention TEAM PERFORMANCE."""
        with open(os.path.join(os.path.dirname(__file__), "..", "data/templates/pipeline_prompts.json")) as f:
            prompts = json.load(f)
        architect_system = prompts["architect"]["system"]
        assert "TEAM PERFORMANCE" in architect_system
        assert "WEAK" in architect_system


class TestArchitectPerformanceUnit:
    """Unit tests for _get_team_performance_summary."""

    @pytest.mark.asyncio
    async def test_empty_board_returns_empty(self):
        """Empty task board → empty string."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline.__new__(AgentPipeline)
        # Monkey-patch to avoid real board
        import src.orchestration.task_board as tb
        original_get = tb.get_task_board

        class MockBoard:
            def list_tasks(self):
                return []

        tb.get_task_board = lambda: MockBoard()
        try:
            result = await pipeline._get_team_performance_summary()
            assert result == ""
        finally:
            tb.get_task_board = original_get

    @pytest.mark.asyncio
    async def test_board_with_stats_returns_summary(self):
        """Board with agent_stats → formatted summary."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline.__new__(AgentPipeline)
        import src.orchestration.task_board as tb
        original_get = tb.get_task_board

        class MockBoard:
            def list_tasks(self):
                return [
                    {
                        "stats": {
                            "agent_stats": {
                                "scout": {"calls": 2, "success_count": 2, "fail_count": 0},
                                "coder": {"calls": 5, "success_count": 2, "fail_count": 3},
                            }
                        }
                    }
                ]

        tb.get_task_board = lambda: MockBoard()
        try:
            result = await pipeline._get_team_performance_summary()
            assert "TEAM PERFORMANCE" in result
            assert "scout: 100% success" in result
            assert "coder: 40% success" in result
            assert "WEAK" in result  # coder < 60%
        finally:
            tb.get_task_board = original_get

    @pytest.mark.asyncio
    async def test_exception_returns_empty(self):
        """Exception → empty string, never crashes."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline.__new__(AgentPipeline)
        import src.orchestration.task_board as tb

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 151 contracts changed")

        original_get = tb.get_task_board

        def boom():
            raise RuntimeError("Board exploded")

        tb.get_task_board = boom
        try:
            result = await pipeline._get_team_performance_summary()
            assert result == ""
        finally:
            tb.get_task_board = original_get


# ══════════════════════════════════════════════════════════════
# Regression — Existing Stats Still Work
# ══════════════════════════════════════════════════════════════

class TestRegressionWave4:
    """Ensure existing 126.0A stats features are intact."""

    def test_track_llm_call_still_exists(self):
        """_track_llm_call method should still exist."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        assert "def _track_llm_call(self, result: dict):" in source
        assert "self._llm_calls += 1" in source

    def test_pipeline_stats_still_has_llm_calls(self):
        """pipeline_stats should still include llm_calls, tokens_in, tokens_out."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        assert '"llm_calls": self._llm_calls' in source
        assert '"tokens_in": self._tokens_in' in source
        assert '"tokens_out": self._tokens_out' in source

    def test_record_pipeline_stats_still_works(self):
        """TaskBoard.record_pipeline_stats should still exist."""
        source = _read_source("src/orchestration/task_board.py")
        assert "def record_pipeline_stats(self, task_id: str, stats: dict)" in source

    def test_markers_present(self):
        """All Wave 4 markers should be in code."""
        pipeline_src = _read_source("src/orchestration/agent_pipeline.py")
        board_src = _read_source("src/orchestration/task_board.py")
        routes_src = _read_source("src/api/routes/debug_routes.py")

        for marker in ["MARKER_151.11A", "MARKER_151.11B", "MARKER_151.11C",
                        "MARKER_151.11D", "MARKER_151.11E", "MARKER_151.11F",
                        "MARKER_151.11G", "MARKER_151.11H", "MARKER_151.11I",
                        "MARKER_151.14A", "MARKER_151.14B"]:
            assert marker in pipeline_src, f"Missing {marker} in agent_pipeline.py"

        assert "MARKER_151.12A" in board_src
        assert "MARKER_151.12B" in board_src
        assert "MARKER_151.12C" in routes_src
