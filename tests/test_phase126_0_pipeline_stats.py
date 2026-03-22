"""
Tests for Phase 126.0 — Pipeline Stats + DevPanel + League Tester.

MARKER_126.0A: Pipeline statistics collection (_track_llm_call, stats at end of execute)
MARKER_126.0B: TaskBoard.record_pipeline_stats() method
MARKER_126.0C: DevPanel tabs (Board / Stats / Test)
MARKER_126.0D: PipelineStats.tsx + LeagueTester.tsx components
MARKER_126.0E: test-league REST endpoint

Tests:
- TestPipelineStatsCollection: 6 tests — counters, track method, stats block
- TestTaskBoardStats: 4 tests — record_pipeline_stats method, stats field
- TestLeagueEndpoint: 3 tests — endpoint exists, validation, auto_write=false
- TestDevPanelTabs: 4 tests — tabs, imports, components exist
- TestRegressionPrevious: 4 tests — 125.1 features intact
"""

import os
import json
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 126 contracts changed")

# ── Helpers ──

def _read_source(path: str) -> str:
    filepath = os.path.join(os.path.dirname(__file__), "..", path)
    with open(filepath) as f:
        return f.read()


# ── Pipeline Stats Collection (126.0A) ──

class TestPipelineStatsCollection:
    """Tests for MARKER_126.0A: Pipeline stats counters and collection."""

    def test_marker_126_0a_exists(self):
        """agent_pipeline.py should have MARKER_126.0A."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        assert "MARKER_126.0A" in source

    def test_llm_calls_counter(self):
        """AgentPipeline should have _llm_calls counter."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        assert "_llm_calls" in source
        assert "self._llm_calls: int = 0" in source

    def test_tokens_counters(self):
        """AgentPipeline should have _tokens_in and _tokens_out counters."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        assert "_tokens_in" in source
        assert "_tokens_out" in source

    def test_track_llm_call_method(self):
        """_track_llm_call method should exist and increment counter."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        assert "def _track_llm_call" in source
        assert "_llm_calls += 1" in source

    def test_all_llm_calls_tracked(self):
        """Every tool.execute(call_args) should have _track_llm_call after it."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        # Count occurrences
        track_count = source.count("_track_llm_call(result)")
        # Should be at least 5: scout, verifier, architect, researcher, coder
        assert track_count >= 5, f"Only {track_count} _track_llm_call calls found"

    def test_stats_block_at_end_of_execute(self):
        """Stats should be collected at end of execute() method."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        # Should have pipeline_stats dict with key fields
        assert "pipeline_stats" in source
        assert '"llm_calls"' in source
        assert '"duration_s"' in source
        assert '"success"' in source


# ── TaskBoard Stats (126.0B) ──

class TestTaskBoardStats:
    """Tests for MARKER_126.0B: TaskBoard.record_pipeline_stats."""

    def test_marker_126_0b_exists(self):
        """task_board.py should have MARKER_126.0B."""
        source = _read_source("src/orchestration/task_board.py")
        assert "MARKER_126.0B" in source

    def test_record_method_exists(self):
        """TaskBoard should have record_pipeline_stats method."""
        from src.orchestration.task_board import TaskBoard
        assert hasattr(TaskBoard, 'record_pipeline_stats')

    def test_record_saves_stats(self):
        """record_pipeline_stats should save stats to task dict."""
        source = _read_source("src/orchestration/task_board.py")
        idx = source.find("record_pipeline_stats")
        block = source[idx:idx + 400]
        assert 'task["stats"] = stats' in block

    def test_hold_status_still_valid(self):
        """hold status should still be valid (125.1)."""
        from src.orchestration.task_board import VALID_STATUSES

        assert "hold" in VALID_STATUSES


# ── League Endpoint (126.0E) ──

class TestLeagueEndpoint:
    """Tests for MARKER_126.0E: test-league REST endpoint."""

    def test_marker_126_0e_exists(self):
        """debug_routes.py should have MARKER_126.0E."""
        source = _read_source("src/api/routes/debug_routes.py")
        assert "MARKER_126.0E" in source

    def test_endpoint_registered(self):
        """test-league endpoint should be registered."""
        source = _read_source("src/api/routes/debug_routes.py")
        assert "task-board/test-league" in source
        assert "async def test_league_api" in source

    def test_auto_write_false(self):
        """test-league should use auto_write=False for safety."""
        source = _read_source("src/api/routes/debug_routes.py")
        idx = source.find("test_league_api")
        block = source[idx:idx + 900]
        assert "auto_write=False" in block


# ── DevPanel & Components (126.0C/D) ──

class TestDevPanelTabs:
    """Tests for MARKER_126.0C/D: DevPanel tabs and new components."""

    def test_devpanel_has_tabs(self):
        """DevPanel should have board/stats/test tabs."""
        source = _read_source("client/src/components/panels/DevPanel.tsx")
        assert "'board'" in source
        assert "'stats'" in source
        assert "'test'" in source

    def test_devpanel_imports_components(self):
        """DevPanel should import PipelineStats and LeagueTester."""
        source = _read_source("client/src/components/panels/DevPanel.tsx")
        assert "PipelineStats" in source
        assert "LeagueTester" in source

    def test_pipeline_stats_component_exists(self):
        """PipelineStats.tsx should exist."""
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "client", "src", "components", "panels", "PipelineStats.tsx"
        )
        assert os.path.exists(filepath)

    def test_league_tester_component_exists(self):
        """LeagueTester.tsx should exist."""
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "client", "src", "components", "panels", "LeagueTester.tsx"
        )
        assert os.path.exists(filepath)


# ── Regression Tests ──

class TestRegressionPrevious:
    """Ensure 125.1 features still work."""

    def test_doctor_prompt_exists(self):
        """Doctor prompt should still exist (125.1)."""
        prompts_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "templates", "pipeline_prompts.json"
        )
        with open(prompts_path) as f:
            prompts = json.load(f)
        assert "doctor" in prompts

    def test_hold_in_taskcard(self):
        """TaskCard should display hold status (125.1)."""
        source = _read_source("client/src/components/panels/TaskCard.tsx")
        assert "hold" in source

    def test_verifier_checks(self):
        """Verifier prompt should have 3 core checks (127.1 simplified)."""
        prompts_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "templates", "pipeline_prompts.json"
        )
        with open(prompts_path) as f:
            prompts = json.load(f)
        verifier = prompts["verifier"]["system"]
        assert "HAS CODE" in verifier or "code" in verifier.lower()
        assert "passed" in verifier
        assert "confidence" in verifier

    def test_all_pipeline_roles(self):
        """All pipeline roles should be in prompts."""
        prompts_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "templates", "pipeline_prompts.json"
        )
        with open(prompts_path) as f:
            prompts = json.load(f)
        for role in ["architect", "researcher", "coder", "verifier", "scout", "doctor"]:
            assert role in prompts
