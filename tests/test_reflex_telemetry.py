"""
Tests for REFLEX Telemetry — Phase 172.P5

MARKER_172.P5.TESTS

Tests REST API endpoints, pipeline_stats REFLEX section,
and observability markers.

T5.1 — /api/reflex/stats returns valid JSON
T5.2 — /api/reflex/recommend returns scored tools
T5.3 — pipeline_stats includes reflex section
T5.4 — REFLEX disabled returns disabled status
T5.5 — /api/reflex/health checks all components
T5.6 — _build_reflex_stats computes match rate
T5.7 — /api/reflex/feedback returns entry count
"""

import os
import sys
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ─── Mock ScoredTool ─────────────────────────────────────────────

@dataclass
class MockScoredTool:
    tool_id: str
    score: float
    reason: str = "test"


# ─── T5.1: Stats endpoint ────────────────────────────────────────

class TestStatsEndpoint:
    """T5.1: /api/reflex/stats returns valid JSON."""

    @pytest.mark.asyncio
    async def test_stats_disabled(self):
        from src.api.routes.reflex_routes import reflex_stats
        with patch("src.api.routes.reflex_routes._is_reflex_enabled", return_value=False):
            result = await reflex_stats()
            assert result["enabled"] == False
            assert "message" in result

    @pytest.mark.asyncio
    async def test_stats_enabled(self):
        from src.api.routes.reflex_routes import reflex_stats

        mock_fb = MagicMock()
        mock_fb.get_stats.return_value = {
            "total_entries": 42,
            "tool_count": 5,
            "top_tools": [{"tool_id": "vetka_read_file", "count": 20}],
            "avg_success_rate": 0.85,
            "avg_usefulness_rate": 0.72,
        }
        mock_fb.get_scores_bulk.return_value = {"vetka_read_file": 0.9}

        mock_reg = MagicMock()
        mock_tool = MagicMock()
        mock_tool.active = True
        mock_tool.namespace = "vetka"
        mock_reg.get_all_tools.return_value = [mock_tool]

        with patch("src.api.routes.reflex_routes._is_reflex_enabled", return_value=True), \
             patch("src.services.reflex_feedback.get_reflex_feedback", return_value=mock_fb), \
             patch("src.services.reflex_registry.get_reflex_registry", return_value=mock_reg):
            result = await reflex_stats()

        assert result["enabled"] == True
        assert result["registry"]["total_tools"] == 1
        assert result["feedback"]["total_entries"] == 42
        assert "scores" in result
        assert "timestamp" in result


# ─── T5.2: Recommend endpoint ────────────────────────────────────

class TestRecommendEndpoint:
    """T5.2: /api/reflex/recommend returns scored tools."""

    @pytest.mark.asyncio
    async def test_recommend_disabled(self):
        from src.api.routes.reflex_routes import reflex_recommend
        with patch("src.api.routes.reflex_routes._is_reflex_enabled", return_value=False):
            result = await reflex_recommend(task="fix bug", phase_type="fix", role="coder", top_n=5)
            assert result["enabled"] == False

    @pytest.mark.asyncio
    async def test_recommend_returns_tools(self):
        from src.api.routes.reflex_routes import reflex_recommend

        mock_scorer = MagicMock()
        mock_scorer.recommend.return_value = [
            MockScoredTool("vetka_read_file", 0.85, "file reading"),
            MockScoredTool("vetka_search_semantic", 0.72, "search"),
        ]
        mock_scorer.score_signals.return_value = {"semantic": 0.8, "phase": 1.0}

        mock_reg = MagicMock()
        mock_reg.get_tools_for_role.return_value = [MagicMock(), MagicMock()]
        mock_reg.get_tool.return_value = MagicMock()

        mock_fb = MagicMock()
        mock_fb.get_scores_bulk.return_value = {}

        with patch("src.api.routes.reflex_routes._is_reflex_enabled", return_value=True), \
             patch("src.services.reflex_scorer.get_reflex_scorer", return_value=mock_scorer), \
             patch("src.services.reflex_registry.get_reflex_registry", return_value=mock_reg), \
             patch("src.services.reflex_feedback.get_reflex_feedback", return_value=mock_fb):
            result = await reflex_recommend(task="fix login bug", phase_type="fix", role="coder", top_n=5)

        assert result["enabled"] == True
        assert result["task"] == "fix login bug"
        assert len(result["recommendations"]) == 2
        assert result["recommendations"][0]["tool_id"] == "vetka_read_file"
        assert "signals" in result["recommendations"][0]
        assert "duration_ms" in result


# ─── T5.3: Pipeline stats includes reflex section ────────────────

class TestPipelineStatsReflex:
    """T5.3: pipeline_stats includes reflex section with match rate."""

    def test_build_reflex_stats_disabled(self):
        """When REFLEX not used, returns enabled=False."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline.__new__(AgentPipeline)
        pipeline._reflex_stats = {
            "enabled": False,
            "recommendations_given": 0,
            "tools_recommended": [],
            "tools_used": [],
            "feedback_recorded": 0,
            "verifier_feedbacks": 0,
        }
        result = pipeline._build_reflex_stats()
        assert result == {"enabled": False}

    def test_build_reflex_stats_with_data(self):
        """When REFLEX was active, returns full stats with match rate."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline.__new__(AgentPipeline)
        pipeline._reflex_stats = {
            "enabled": True,
            "recommendations_given": 3,
            "tools_recommended": ["vetka_read_file", "vetka_search_semantic", "vetka_edit_file",
                                   "vetka_read_file", "vetka_search_semantic"],
            "tools_used": ["vetka_read_file", "vetka_edit_file", "vetka_run_tests"],
            "feedback_recorded": 6,
            "verifier_feedbacks": 4,
        }
        result = pipeline._build_reflex_stats()

        assert result["enabled"] == True
        assert result["recommendations_given"] == 3
        assert set(result["tools_recommended_unique"]) == {"vetka_read_file", "vetka_search_semantic", "vetka_edit_file"}
        assert set(result["tools_used_unique"]) == {"vetka_read_file", "vetka_edit_file", "vetka_run_tests"}
        # Match: read_file and edit_file are in both recommended and used
        assert set(result["matched_tools"]) == {"vetka_read_file", "vetka_edit_file"}
        # 2 out of 3 recommended were used = 0.667
        assert result["match_rate"] == pytest.approx(0.667, abs=0.01)
        assert result["feedback_recorded"] == 6
        assert result["verifier_feedbacks"] == 4

    def test_build_reflex_stats_no_recommendations(self):
        """Match rate is 0 when no recommendations were given."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline.__new__(AgentPipeline)
        pipeline._reflex_stats = {
            "enabled": True,
            "recommendations_given": 0,
            "tools_recommended": [],
            "tools_used": ["vetka_read_file"],
            "feedback_recorded": 1,
            "verifier_feedbacks": 0,
        }
        result = pipeline._build_reflex_stats()
        assert result["match_rate"] == 0.0

    def test_build_reflex_stats_perfect_match(self):
        """100% match rate when all recommended tools were used."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline.__new__(AgentPipeline)
        pipeline._reflex_stats = {
            "enabled": True,
            "recommendations_given": 1,
            "tools_recommended": ["vetka_read_file", "vetka_edit_file"],
            "tools_used": ["vetka_read_file", "vetka_edit_file", "vetka_search_semantic"],
            "feedback_recorded": 3,
            "verifier_feedbacks": 2,
        }
        result = pipeline._build_reflex_stats()
        assert result["match_rate"] == 1.0


# ─── T5.4: Disabled returns disabled ─────────────────────────────

class TestDisabledState:
    """T5.4: All endpoints gracefully handle disabled state."""

    @pytest.mark.asyncio
    async def test_feedback_disabled(self):
        from src.api.routes.reflex_routes import reflex_feedback_summary
        with patch("src.api.routes.reflex_routes._is_reflex_enabled", return_value=False):
            result = await reflex_feedback_summary()
            assert result["enabled"] == False


# ─── T5.5: Health check ──────────────────────────────────────────

class TestHealthEndpoint:
    """T5.5: /api/reflex/health checks all components."""

    @pytest.mark.asyncio
    async def test_health_all_ok(self):
        from src.api.routes.reflex_routes import reflex_health

        mock_reg = MagicMock()
        mock_reg.get_all_tools.return_value = [MagicMock() for _ in range(30)]
        mock_scorer = MagicMock()
        mock_fb = MagicMock()
        mock_fb.entry_count = 42

        with patch("src.api.routes.reflex_routes._is_reflex_enabled", return_value=True), \
             patch("src.services.reflex_registry.get_reflex_registry", return_value=mock_reg), \
             patch("src.services.reflex_scorer.get_reflex_scorer", return_value=mock_scorer), \
             patch("src.services.reflex_feedback.get_reflex_feedback", return_value=mock_fb):
            result = await reflex_health()

        assert result["enabled"] == True
        assert result["components"]["registry"]["status"] == "ok"
        assert result["components"]["registry"]["tools"] == 30
        assert result["components"]["scorer"]["status"] == "ok"
        assert result["components"]["feedback"]["status"] == "ok"
        assert result["components"]["feedback"]["entries"] == 42

    @pytest.mark.asyncio
    async def test_health_partial_failure(self):
        from src.api.routes.reflex_routes import reflex_health

        mock_reg = MagicMock()
        mock_reg.get_all_tools.return_value = []

        with patch("src.api.routes.reflex_routes._is_reflex_enabled", return_value=True), \
             patch("src.services.reflex_registry.get_reflex_registry", return_value=mock_reg), \
             patch("src.services.reflex_scorer.get_reflex_scorer", side_effect=RuntimeError("boom")), \
             patch("src.services.reflex_feedback.get_reflex_feedback", side_effect=RuntimeError("crash")):
            result = await reflex_health()

        assert result["components"]["registry"]["status"] == "ok"
        assert result["components"]["scorer"]["status"] == "error"
        assert result["components"]["feedback"]["status"] == "error"


# ─── T5.6: Match rate edge cases ─────────────────────────────────

class TestMatchRate:
    """T5.6: Match rate computation edge cases."""

    def _build(self, recommended, used):
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline.__new__(AgentPipeline)
        pipeline._reflex_stats = {
            "enabled": True,
            "recommendations_given": 1,
            "tools_recommended": recommended,
            "tools_used": used,
            "feedback_recorded": 0,
            "verifier_feedbacks": 0,
        }
        return pipeline._build_reflex_stats()

    def test_zero_match(self):
        result = self._build(["tool_a", "tool_b"], ["tool_c", "tool_d"])
        assert result["match_rate"] == 0.0

    def test_full_match(self):
        result = self._build(["tool_a"], ["tool_a", "tool_b"])
        assert result["match_rate"] == 1.0

    def test_partial_match(self):
        result = self._build(["tool_a", "tool_b", "tool_c", "tool_d"], ["tool_a", "tool_c"])
        assert result["match_rate"] == 0.5


# ─── T5.7: Feedback summary endpoint ─────────────────────────────

class TestFeedbackEndpoint:
    """T5.7: /api/reflex/feedback returns entry count and stats."""

    @pytest.mark.asyncio
    async def test_feedback_returns_data(self):
        from src.api.routes.reflex_routes import reflex_feedback_summary

        mock_fb = MagicMock()
        mock_fb.entry_count = 100
        mock_fb.get_stats.return_value = {"total_entries": 100, "tool_count": 8}

        with patch("src.api.routes.reflex_routes._is_reflex_enabled", return_value=True), \
             patch("src.services.reflex_feedback.get_reflex_feedback", return_value=mock_fb):
            result = await reflex_feedback_summary()

        assert result["enabled"] == True
        assert result["entry_count"] == 100
        assert result["stats"]["total_entries"] == 100


# ─── Router registration ─────────────────────────────────────────

class TestRouterRegistration:
    """Verify REFLEX router is registered in the route aggregator."""

    def test_reflex_router_in_all_routers(self):
        from src.api.routes import get_all_routers
        routers = get_all_routers()
        prefixes = []
        for r in routers:
            if hasattr(r, 'prefix'):
                prefixes.append(r.prefix)
        assert "/api/reflex" in prefixes, f"REFLEX router not found. Prefixes: {prefixes}"
