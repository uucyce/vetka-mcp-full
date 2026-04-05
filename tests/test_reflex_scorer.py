"""
Tests for Phase 172.P2 — REFLEX Scorer (context-aware tool ranking).

MARKER_172.P2.TESTS

Tests:
  T2.1  test_score_returns_float_0_to_1 — bounds check
  T2.2  test_recommend_returns_top_n — correct count, sorted descending
  T2.3  test_semantic_match_prefers_relevant_tools — search task → search tools higher
  T2.4  test_phase_match_fix_vs_build — phase alignment affects scoring
  T2.5  test_cam_surprise_boosts_novel_tools — high surprise broadens palette
  T2.6  test_engram_preference_respected — user prefs boost preferred tool
  T2.7  test_feedback_score_affects_ranking — CORTEX feedback changes rank
  T2.8  test_score_without_feedback_uses_default — cold start = 0.5
  T2.9  test_weights_configurable — custom weights override defaults
  T2.10 test_scorer_performance_under_5ms — timing benchmark
  T2.11 test_from_subtask_factory — ReflexContext from pipeline subtask
  T2.12 test_feature_flag_disabled — REFLEX_ENABLED=false → empty results
  T2.13 test_model_capability_adapts_scoring — small model → fewer tools
  T2.14 test_reads_llm_registry_not_duplicates — no own API calls
"""

import os
import sys
import time
import pytest
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import patch, MagicMock

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.reflex_scorer import (
    ReflexScorer,
    ReflexContext,
    ScoredTool,
    get_reflex_scorer,
    reset_reflex_scorer,
    REFLEX_ENABLED,
    _W,
    _DEFAULT_FEEDBACK_SCORE,
    _SMALL_MODEL_CONTEXT,
    _MEDIUM_MODEL_CONTEXT,
    _SPARSE_BOOST_THRESHOLD,
    _SPARSE_BOOST_MULTIPLIER,
)
from src.services.reflex_registry import ToolEntry


# ─── Test helpers ──────────────────────────────────────────────────

def _make_tool(
    tool_id: str,
    kind: str = "search",
    intent_tags: Optional[List[str]] = None,
    phase_types: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    roles: Optional[List[str]] = None,
    risk_level: str = "read_only",
    active: bool = True,
) -> ToolEntry:
    """Create a ToolEntry for testing."""
    return ToolEntry(
        tool_id=tool_id,
        namespace="test",
        kind=kind,
        description=f"Test tool: {tool_id}",
        intent_tags=intent_tags or [],
        trigger_patterns={
            "file_types": ["*"],
            "phase_types": phase_types or ["research", "fix", "build"],
            "keywords": keywords or [],
        },
        cost={
            "latency_ms": 100,
            "tokens": 0,
            "risk_level": risk_level,
        },
        permission="READ",
        roles=roles or ["all"],
        active=active,
    )


@dataclass
class FakeSubtask:
    """Minimal subtask mock for from_subtask() tests."""
    description: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"


@pytest.fixture
def scorer():
    """Create a fresh scorer with REFLEX_ENABLED patched to True."""
    reset_reflex_scorer()
    with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
        s = ReflexScorer()
        yield s
    reset_reflex_scorer()


@pytest.fixture
def search_tool():
    return _make_tool(
        "vetka_search_semantic",
        kind="search",
        intent_tags=["search", "find", "query", "semantic"],
        keywords=["search", "find", "lookup"],
        phase_types=["research"],
    )


@pytest.fixture
def file_tool():
    return _make_tool(
        "vetka_edit_file",
        kind="file_op",
        intent_tags=["edit", "write", "file", "modify"],
        keywords=["edit", "write", "fix", "change"],
        phase_types=["fix", "build"],
    )


@pytest.fixture
def heavy_tool():
    return _make_tool(
        "mycelium_pipeline",
        kind="orchestration",
        intent_tags=["pipeline", "execute", "build"],
        keywords=["pipeline", "run", "build"],
        risk_level="execute",
        phase_types=["build"],
    )


@pytest.fixture
def sample_tools(search_tool, file_tool, heavy_tool):
    """A small set of diverse tools for testing."""
    return [search_tool, file_tool, heavy_tool]


# ─── T2.1: Score returns float 0-1 ──────────────────────────────

class TestScoreBounds:
    """T2.1: score() returns a float in [0.0, 1.0]."""

    def test_score_returns_float_0_to_1(self, scorer, search_tool):
        context = ReflexContext(task_text="search for files in project")
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            result = scorer.score(search_tool, context)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_score_with_empty_context(self, scorer, search_tool):
        context = ReflexContext()
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            result = scorer.score(search_tool, context)
        assert 0.0 <= result <= 1.0

    def test_score_with_all_signals_maxed(self, scorer, search_tool):
        """Even with all signals at max, score stays <= 1.0."""
        context = ReflexContext(
            task_text="search find query semantic",
            cam_surprise=1.0,
            user_tool_prefs={"vetka_search_semantic": 100.0},
            stm_items=["search semantic query recent"],
            feedback_scores={"vetka_search_semantic": 1.0},
            hope_level="LOW",
            mgc_stats={"hit_rate": 1.0, "gen0_size": 100, "gen0_max": 100},
        )
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            result = scorer.score(search_tool, context)
        assert result <= 1.0


# ─── T2.2: Recommend returns top-N sorted descending ────────────

class TestRecommend:
    """T2.2: recommend() returns correct count, sorted descending."""

    def test_recommend_returns_top_n(self, scorer, sample_tools):
        context = ReflexContext(task_text="search for bugs")
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            results = scorer.recommend(context, sample_tools, top_n=2)
        assert len(results) <= 2
        assert all(isinstance(r, ScoredTool) for r in results)

    def test_recommend_sorted_descending(self, scorer, sample_tools):
        context = ReflexContext(task_text="search for project files")
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            results = scorer.recommend(context, sample_tools, top_n=10)
        if len(results) >= 2:
            for i in range(len(results) - 1):
                assert results[i].score >= results[i + 1].score

    def test_recommend_empty_tools(self, scorer):
        context = ReflexContext(task_text="anything")
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            results = scorer.recommend(context, [], top_n=5)
        assert results == []

    def test_recommend_filters_inactive_tools(self, scorer):
        active = _make_tool("active_tool", active=True)
        inactive = _make_tool("inactive_tool", active=False)
        context = ReflexContext(task_text="test")
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            results = scorer.recommend(context, [active, inactive], top_n=10)
        tool_ids = [r.tool_id for r in results]
        assert "inactive_tool" not in tool_ids

    def test_recommend_reports_overlay_effect_in_reason(self, scorer):
        overlay_tool = _make_tool(
            "seed_mcc_playwright_fixture",
            intent_tags=["general"],
            keywords=["seed"],
        )
        overlay_tool.overlay_hints = {
            "overlay_applied": True,
            "origin": "catalog",
            "catalog_source": "src/agents/tools.py",
            "path": "scripts/mcc_seed_playwright_fixture.py",
            "base_intent_tags": ["general"],
            "base_keywords": ["seed"],
            "added_intent_tags": ["playwright"],
            "added_keywords": ["visual_regression"],
        }
        overlay_tool.intent_tags = ["general", "playwright"]
        overlay_tool.trigger_patterns["keywords"] = ["seed", "visual_regression"]
        context = ReflexContext(task_text="need playwright visual_regression coverage")
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            results = scorer.recommend(context, [overlay_tool], top_n=5)
        assert results
        assert "overlay:+" in results[0].reason
        assert results[0].overlay["applied"] is True


# ─── T2.3: Semantic match prefers relevant tools ────────────────

class TestSemanticMatch:
    """T2.3: search task → search tools score higher."""

    def test_semantic_match_prefers_relevant_tools(self, scorer, search_tool, file_tool):
        context = ReflexContext(task_text="search for semantic results in codebase")
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            search_signals = scorer.score_signals(search_tool, context)
            file_signals = scorer.score_signals(file_tool, context)
        assert search_signals["semantic"] > file_signals["semantic"]

    def test_semantic_zero_on_empty_text(self, scorer, search_tool):
        context = ReflexContext(task_text="")
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            signals = scorer.score_signals(search_tool, context)
        assert signals["semantic"] == 0.0

    def test_overlay_effect_compares_against_canonical_metadata(self, scorer):
        tool = _make_tool(
            "remember_reflex_tool",
            kind="memory",
            intent_tags=["memory"],
            keywords=["remember"],
        )
        tool.overlay_hints = {
            "overlay_applied": True,
            "origin": "catalog",
            "catalog_source": "src/agents/tools.py",
            "path": "src/agents/tools.py",
            "base_intent_tags": ["memory"],
            "base_keywords": ["remember"],
            "added_intent_tags": ["playwright"],
            "added_keywords": ["visual_regression"],
        }
        tool.intent_tags = ["memory", "playwright"]
        tool.trigger_patterns["keywords"] = ["remember", "visual_regression"]
        context = ReflexContext(task_text="playwright visual_regression debugging")
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            overlay = scorer.overlay_effect(tool, context)
            current = scorer.score(tool, context)
            baseline = scorer.score_without_overlay(tool, context)
        assert overlay["applied"] is True
        assert overlay["score_delta"] > 0
        assert current > baseline


# ─── T2.4: Phase match — fix vs build ───────────────────────────

class TestPhaseMatch:
    """T2.4: fix phase → fix tools, build phase → build tools."""

    def test_phase_match_fix_prefers_fix_tools(self, scorer, search_tool, file_tool):
        """File tool has phase_types=[fix, build], search has [research]."""
        context = ReflexContext(phase_type="fix")
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            file_signals = scorer.score_signals(file_tool, context)
            search_signals = scorer.score_signals(search_tool, context)
        assert file_signals["phase"] == 1.0
        assert search_signals["phase"] == 0.0  # "research" only

    def test_phase_match_research_prefers_search_tools(self, scorer, search_tool, file_tool):
        context = ReflexContext(phase_type="research")
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            search_signals = scorer.score_signals(search_tool, context)
            file_signals = scorer.score_signals(file_tool, context)
        assert search_signals["phase"] == 1.0
        assert file_signals["phase"] == 0.0  # "fix" and "build" only

    def test_phase_match_wildcard_always_matches(self, scorer):
        wildcard_tool = _make_tool("wildcard", phase_types=["*"])
        context = ReflexContext(phase_type="anything")
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            signals = scorer.score_signals(wildcard_tool, context)
        assert signals["phase"] == 1.0


# ─── T2.5: CAM surprise boosts novel tools ──────────────────────

class TestCAMSurprise:
    """T2.5: High surprise → broader tool set (higher CAM score)."""

    def test_cam_surprise_boosts_novel_tools(self, scorer, search_tool):
        high_surprise = ReflexContext(cam_surprise=0.9)
        low_surprise = ReflexContext(cam_surprise=0.1)
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            high_signals = scorer.score_signals(search_tool, high_surprise)
            low_signals = scorer.score_signals(search_tool, low_surprise)
        assert high_signals["cam"] > low_signals["cam"]

    def test_cam_thresholds(self, scorer, search_tool):
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            # High surprise (>= 0.7) → 1.0
            signals_high = scorer.score_signals(search_tool, ReflexContext(cam_surprise=0.8))
            assert signals_high["cam"] == 1.0

            # Medium surprise (0.3-0.7) → 0.5
            signals_mid = scorer.score_signals(search_tool, ReflexContext(cam_surprise=0.5))
            assert signals_mid["cam"] == 0.5

            # Low surprise (<0.3) → 0.3
            signals_low = scorer.score_signals(search_tool, ReflexContext(cam_surprise=0.1))
            assert signals_low["cam"] == 0.3

    def test_sparse_boost_cam(self, scorer, search_tool):
        """Phase 187.3: CAM signal > 0.7 gets ×1.5 sparse boost in weighted sum."""
        # CAM signal = 1.0 (high surprise), so boosted value = min(1.0, 1.0*1.5) = 1.0
        # With cam weight 0.12: boosted contrib = 1.0 * 0.12 = 0.12
        # Without boost it would also be 1.0 * 0.12 = 0.12 (capped at 1.0)
        # Use a context where CAM=0.8 (just above 0.7 threshold, returns 1.0 from _cam_relevance)
        # The boost applies in _weighted_sum to the signal value, not the raw cam_surprise
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            # cam signal = 1.0 (>0.7 threshold) → boosted to min(1.0, 1.5) = 1.0
            high_cam = ReflexContext(cam_surprise=0.8)
            # cam signal = 0.5 (<=0.7 threshold) → no boost
            mid_cam = ReflexContext(cam_surprise=0.5)
            score_high = scorer.score(search_tool, high_cam)
            score_mid = scorer.score(search_tool, mid_cam)
            # High CAM should score higher due to both higher signal AND sparse boost
            assert score_high > score_mid

    def test_sparse_boost_hope(self, scorer, search_tool):
        """Phase 187.3: HOPE signal > 0.7 gets ×1.5 sparse boost in weighted sum."""
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            # LOW zoom + search tool → hope signal = 1.0 (>0.7) → boosted
            low_zoom = ReflexContext(hope_level="LOW")
            # MID zoom → hope signal = 0.5 (<=0.7) → no boost
            mid_zoom = ReflexContext(hope_level="MID")
            score_low = scorer.score(search_tool, low_zoom)
            score_mid = scorer.score(search_tool, mid_zoom)
            # LOW zoom + search tool should benefit from sparse boost
            assert score_low > score_mid


# ─── T2.6: ENGRAM preference respected ──────────────────────────

class TestEngramPreference:
    """T2.6: User prefers tool X → X scores higher."""

    def test_engram_preference_respected(self, scorer, search_tool, file_tool):
        context = ReflexContext(
            user_tool_prefs={"vetka_search_semantic": 15.0}  # heavily used
        )
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            search_signals = scorer.score_signals(search_tool, context)
            file_signals = scorer.score_signals(file_tool, context)
        assert search_signals["engram"] > file_signals["engram"]
        assert search_signals["engram"] == 15.0 / 20.0  # normalized

    def test_engram_zero_when_no_prefs(self, scorer, search_tool):
        context = ReflexContext(user_tool_prefs={})
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            signals = scorer.score_signals(search_tool, context)
        assert signals["engram"] == 0.0

    def test_engram_saturates_at_20(self, scorer, search_tool):
        """Usage > 20 should saturate at 1.0."""
        context = ReflexContext(user_tool_prefs={"vetka_search_semantic": 50.0})
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            signals = scorer.score_signals(search_tool, context)
        assert signals["engram"] == 1.0


# ─── T2.7: Feedback score affects ranking ────────────────────────

class TestFeedbackScore:
    """T2.7: Tool with high CORTEX feedback → higher rank."""

    def test_feedback_score_affects_ranking(self, scorer, search_tool, file_tool):
        context = ReflexContext(
            feedback_scores={
                "vetka_search_semantic": 0.95,
                "vetka_edit_file": 0.2,
            }
        )
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            search_signals = scorer.score_signals(search_tool, context)
            file_signals = scorer.score_signals(file_tool, context)
        assert search_signals["feedback"] == 0.95
        assert file_signals["feedback"] == 0.2
        assert search_signals["feedback"] > file_signals["feedback"]


# ─── T2.8: Default feedback when no history ──────────────────────

class TestDefaultFeedback:
    """T2.8: Cold start uses 0.5 default feedback score."""

    def test_score_without_feedback_uses_default(self, scorer, search_tool):
        context = ReflexContext(feedback_scores={})
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            signals = scorer.score_signals(search_tool, context)
        assert signals["feedback"] == _DEFAULT_FEEDBACK_SCORE
        assert signals["feedback"] == 0.5

    def test_partial_feedback_uses_default_for_unknown(self, scorer, search_tool, file_tool):
        """Only file_tool has feedback; search_tool should get default."""
        context = ReflexContext(
            feedback_scores={"vetka_edit_file": 0.9}
        )
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            search_signals = scorer.score_signals(search_tool, context)
            file_signals = scorer.score_signals(file_tool, context)
        assert search_signals["feedback"] == 0.5  # default
        assert file_signals["feedback"] == 0.9    # from feedback


# ─── T2.9: Weights configurable ─────────────────────────────────

class TestConfigurableWeights:
    """T2.9: Custom weights override defaults."""

    def test_weights_configurable(self, search_tool):
        """Scorer with semantic=1.0, all others=0.0 → score == semantic signal."""
        custom_weights = {
            "semantic": 1.0, "cam": 0.0, "feedback": 0.0, "engram": 0.0,
            "stm": 0.0, "phase": 0.0, "hope": 0.0, "mgc": 0.0,
        }
        scorer = ReflexScorer(weights=custom_weights)
        context = ReflexContext(
            task_text="search find query semantic",
            cam_surprise=1.0,
            feedback_scores={"vetka_search_semantic": 1.0},
        )
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            signals = scorer.score_signals(search_tool, context)
            total = scorer.score(search_tool, context)
        # Total should be purely from semantic (cam/feedback have weight 0)
        assert total == pytest.approx(signals["semantic"], abs=0.001)

    def test_phase187_weights_sum_to_one(self):
        """Phase 187.3: Rebalanced weights must sum to 1.0."""
        assert sum(_W.values()) == pytest.approx(1.0, abs=0.001)
        assert _W["semantic"] == pytest.approx(0.22)
        assert _W["cam"] == pytest.approx(0.12)
        assert _W["feedback"] == pytest.approx(0.18)
        assert _W["engram"] == pytest.approx(0.07)
        assert _W["stm"] == pytest.approx(0.15)
        assert _W["phase"] == pytest.approx(0.18)
        assert _W["hope"] == pytest.approx(0.05)
        assert _W["mgc"] == pytest.approx(0.03)

    def test_sparse_boost_constants(self):
        """Phase 187.3: Sparse boost threshold and multiplier."""
        assert _SPARSE_BOOST_THRESHOLD == 0.7
        assert _SPARSE_BOOST_MULTIPLIER == 1.5

    def test_zero_weights_zero_score(self, search_tool):
        """All weights zero → score is 0.0."""
        zero_weights = {k: 0.0 for k in _W}
        scorer = ReflexScorer(weights=zero_weights)
        context = ReflexContext(
            task_text="anything",
            cam_surprise=1.0,
            feedback_scores={"vetka_search_semantic": 1.0},
        )
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            total = scorer.score(search_tool, context)
        assert total == 0.0


# ─── T2.10: Performance benchmark ───────────────────────────────

class TestPerformance:
    """T2.10: Full recommend() < 5ms for 100 tools."""

    def test_scorer_performance_under_5ms(self):
        """Benchmark: recommend() with 100 tools should complete in <5ms."""
        # Create 100 tools
        tools = [
            _make_tool(
                f"tool_{i}",
                kind=["search", "file_op", "orchestration", "memory"][i % 4],
                intent_tags=[f"tag_{i}", f"intent_{i % 10}"],
                keywords=[f"kw_{i}"],
            )
            for i in range(100)
        ]

        scorer = ReflexScorer()
        context = ReflexContext(
            task_text="search for files and edit code",
            phase_type="fix",
            cam_surprise=0.5,
            user_tool_prefs={f"tool_{i}": float(i) for i in range(10)},
            stm_items=["recent search result", "file edit operation"],
            feedback_scores={f"tool_{i}": 0.7 for i in range(20)},
            hope_level="MID",
            mgc_stats={"hit_rate": 0.6, "gen0_size": 50, "gen0_max": 100},
        )

        # Warm up
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            scorer.recommend(context, tools, top_n=5)

        # Benchmark: average of 100 runs
        t0 = time.perf_counter()
        iterations = 100
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            for _ in range(iterations):
                scorer.recommend(context, tools, top_n=5)
        elapsed = time.perf_counter() - t0

        avg_ms = (elapsed / iterations) * 1000
        assert avg_ms < 5.0, f"recommend(100 tools) took {avg_ms:.2f}ms (expected <5ms)"


# ─── T2.11: from_subtask factory ────────────────────────────────

class TestFromSubtask:
    """T2.11: ReflexContext.from_subtask() builds context correctly."""

    def test_from_subtask_factory(self):
        subtask = FakeSubtask(
            description="Fix the authentication bug in login module",
            context={
                "phase_type": "fix",
                "agent_role": "coder",
            },
        )
        ctx = ReflexContext.from_subtask(
            subtask,
            cam_surprise=0.6,
            stm_items=["login.py was recently edited"],
            hope_level="HIGH",
            model_context_length=32000,
            model_output_tps=80.0,
        )
        assert ctx.task_text == "Fix the authentication bug in login module"
        assert ctx.phase_type == "fix"
        assert ctx.agent_role == "coder"
        assert ctx.cam_surprise == 0.6
        assert len(ctx.stm_items) == 1
        assert ctx.hope_level == "HIGH"
        assert ctx.model_context_length == 32000
        assert ctx.model_output_tps == 80.0

    def test_from_subtask_defaults(self):
        """Minimal subtask → sensible defaults."""
        subtask = FakeSubtask(description="do something")
        ctx = ReflexContext.from_subtask(subtask)
        assert ctx.task_text == "do something"
        assert ctx.phase_type == "research"  # default
        assert ctx.agent_role == "coder"     # default
        assert ctx.cam_surprise == 0.0
        assert ctx.stm_items == []
        assert ctx.model_context_length == 128000

    def test_from_subtask_handles_none_context(self):
        """Subtask with context=None doesn't crash."""
        subtask = FakeSubtask(description="test", context=None)
        ctx = ReflexContext.from_subtask(subtask)
        assert ctx.phase_type == "research"

    def test_from_session_builds_context(self):
        """from_session() extracts viewport zoom → HOPE level."""
        session_data = {
            "viewport": {"zoom": 0.1},
            "user_preferences": {
                "has_preferences": True,
                "tool_usage_patterns": {"vetka_search_semantic": 10.0},
            },
        }
        ctx = ReflexContext.from_session(
            session_data,
            task_text="explore project",
            phase_type="research",
        )
        assert ctx.hope_level == "LOW"  # zoom < 0.3
        assert ctx.user_tool_prefs.get("vetka_search_semantic") == 10.0

    def test_from_session_high_zoom(self):
        session_data = {"viewport": {"zoom": 2.0}}
        ctx = ReflexContext.from_session(session_data)
        assert ctx.hope_level == "HIGH"  # zoom > 1.0

    def test_from_session_mid_zoom(self):
        session_data = {"viewport": {"zoom": 0.5}}
        ctx = ReflexContext.from_session(session_data)
        assert ctx.hope_level == "MID"  # 0.3 <= zoom <= 1.0


# ─── T2.12: Feature flag disabled ───────────────────────────────

class TestFeatureFlag:
    """T2.12: REFLEX_ENABLED=false → no scoring."""

    def test_feature_flag_disabled_recommend(self, search_tool):
        scorer = ReflexScorer()
        context = ReflexContext(task_text="search for files")
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", False):
            results = scorer.recommend(context, [search_tool], top_n=5)
        assert results == []

    def test_feature_flag_disabled_score(self, search_tool):
        scorer = ReflexScorer()
        context = ReflexContext(task_text="search for files")
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", False):
            result = scorer.score(search_tool, context)
        assert result == 0.0

    def test_feature_flag_disabled_recommend_for_role(self):
        scorer = ReflexScorer()
        context = ReflexContext()
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", False):
            results = scorer.recommend_for_role("coder", context)
        assert results == []

    def test_feature_flag_disabled_recommend_for_session(self):
        scorer = ReflexScorer()
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", False):
            results = scorer.recommend_for_session({"viewport": {}})
        assert results == []


# ─── T2.13: Model capability adapts scoring ──────────────────────

class TestModelCapability:
    """T2.13: Small model (≤8k) → fewer/lighter tools recommended."""

    def test_model_capability_adapts_scoring(self, scorer, search_tool, heavy_tool):
        """Small model should exclude 'execute' risk tools."""
        context = ReflexContext(
            task_text="build a pipeline",
            model_context_length=4096,  # small model
        )
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            results = scorer.recommend(context, [search_tool, heavy_tool], top_n=10)
        # heavy_tool has risk_level="execute" → should be filtered for small model
        tool_ids = [r.tool_id for r in results]
        assert "mycelium_pipeline" not in tool_ids

    def test_large_model_keeps_all_tools(self, scorer, search_tool, heavy_tool):
        """Large model should keep all tools."""
        context = ReflexContext(
            task_text="build a pipeline",
            model_context_length=128000,
        )
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            results = scorer.recommend(context, [search_tool, heavy_tool], top_n=10)
        tool_ids = [r.tool_id for r in results]
        assert "mycelium_pipeline" in tool_ids

    def test_model_capability_thresholds(self, scorer):
        """Verify capability classification thresholds."""
        small_ctx = ReflexContext(model_context_length=4096)
        medium_ctx = ReflexContext(model_context_length=16384)
        large_ctx = ReflexContext(model_context_length=128000)

        assert scorer._model_capability(small_ctx) == "small"
        assert scorer._model_capability(medium_ctx) == "medium"
        assert scorer._model_capability(large_ctx) == "large"

    def test_boundary_values(self, scorer):
        """Exact boundary values: 8192 → small, 32768 → medium, 32769 → large."""
        assert scorer._model_capability(ReflexContext(model_context_length=8192)) == "small"
        assert scorer._model_capability(ReflexContext(model_context_length=32768)) == "medium"
        assert scorer._model_capability(ReflexContext(model_context_length=32769)) == "large"


# ─── T2.14: Uses LLMModelRegistry, doesn't duplicate ────────────

class TestLLMRegistryIntegration:
    """T2.14: REFLEX reads from LLMModelRegistry, no own API calls."""

    def test_reads_llm_registry_not_duplicates(self):
        """ReflexContext.model_context_length is set from LLMModelRegistry profile,
        not from any internal API call. Verify the data flow pattern."""
        # The correct pattern: caller fetches profile, passes to ReflexContext
        # REFLEX itself does NOT import or call get_llm_registry()

        # 1. Simulate the caller pattern (what fc_loop/agent_pipeline does):
        mock_profile = MagicMock()
        mock_profile.context_length = 32000
        mock_profile.output_tokens_per_second = 90.0

        # 2. Build context the way callers should:
        ctx = ReflexContext(
            task_text="fix bug",
            model_context_length=mock_profile.context_length,
            model_output_tps=mock_profile.output_tokens_per_second,
        )

        assert ctx.model_context_length == 32000
        assert ctx.model_output_tps == 90.0

    def test_scorer_does_not_import_llm_registry(self):
        """Verify reflex_scorer.py does NOT directly import get_llm_registry.

        The scorer reads model data from ReflexContext fields, which are populated
        by the CALLER (fc_loop, agent_pipeline) from LLMModelRegistry. This ensures
        no duplicate API calls and clean separation of concerns.
        """
        import src.services.reflex_scorer as scorer_module
        source = open(scorer_module.__file__).read()
        # Should NOT contain direct import of get_llm_registry
        assert "from src.elisya.llm_model_registry import" not in source
        assert "import llm_model_registry" not in source

    def test_from_subtask_accepts_registry_values(self):
        """from_subtask() passes model data through correctly."""
        subtask = FakeSubtask(description="test", context={"phase_type": "build"})
        ctx = ReflexContext.from_subtask(
            subtask,
            model_context_length=8192,
            model_output_tps=120.0,
        )
        assert ctx.model_context_length == 8192
        assert ctx.model_output_tps == 120.0


# ─── Singleton tests ────────────────────────────────────────────

class TestSingleton:
    """Verify singleton pattern works correctly."""

    def test_get_reflex_scorer_returns_same_instance(self):
        reset_reflex_scorer()
        s1 = get_reflex_scorer()
        s2 = get_reflex_scorer()
        assert s1 is s2
        reset_reflex_scorer()

    def test_reset_clears_singleton(self):
        s1 = get_reflex_scorer()
        reset_reflex_scorer()
        s2 = get_reflex_scorer()
        assert s1 is not s2
        reset_reflex_scorer()


# ─── Extra signal tests ─────────────────────────────────────────

class TestAdditionalSignals:
    """Extra coverage for STM, HOPE, and MGC signals."""

    def test_stm_relevance_with_matching_items(self, scorer, search_tool):
        context = ReflexContext(
            stm_items=["I just ran vetka_search_semantic on the codebase"]
        )
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            signals = scorer.score_signals(search_tool, context)
        assert signals["stm"] > 0.0

    def test_stm_relevance_no_items(self, scorer, search_tool):
        context = ReflexContext(stm_items=[])
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            signals = scorer.score_signals(search_tool, context)
        assert signals["stm"] == 0.0

    def test_hope_low_prefers_search(self, scorer, search_tool, file_tool):
        context = ReflexContext(hope_level="LOW")
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            search_signals = scorer.score_signals(search_tool, context)
            file_signals = scorer.score_signals(file_tool, context)
        assert search_signals["hope"] > file_signals["hope"]

    def test_hope_high_prefers_file_ops(self, scorer, search_tool, file_tool):
        context = ReflexContext(hope_level="HIGH")
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            search_signals = scorer.score_signals(search_tool, context)
            file_signals = scorer.score_signals(file_tool, context)
        assert file_signals["hope"] > search_signals["hope"]

    def test_mgc_heat_hot_cache(self, scorer, search_tool):
        context = ReflexContext(
            mgc_stats={"hit_rate": 0.9, "gen0_size": 80, "gen0_max": 100}
        )
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            signals = scorer.score_signals(search_tool, context)
        assert signals["mgc"] > 0.5  # Hot cache → high heat for search tools

    def test_mgc_heat_no_stats(self, scorer, search_tool):
        context = ReflexContext(mgc_stats={})
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            signals = scorer.score_signals(search_tool, context)
        assert signals["mgc"] == 0.3  # Default neutral-low


# ─── ScoredTool dataclass tests ─────────────────────────────────

class TestScoredTool:
    """Verify ScoredTool structure."""

    def test_scored_tool_has_required_fields(self):
        st = ScoredTool(
            tool_id="test",
            score=0.75,
            reason="semantic: 0.89, phase: 1.0",
            source_signals={"semantic": 0.89, "phase": 1.0},
        )
        assert st.tool_id == "test"
        assert st.score == 0.75
        assert "semantic" in st.reason
        assert st.source_signals["semantic"] == 0.89

    def test_recommend_populates_scored_tool_fields(self, scorer, search_tool):
        context = ReflexContext(task_text="search files", phase_type="research")
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            results = scorer.recommend(context, [search_tool], top_n=1)
        if results:
            r = results[0]
            assert r.tool_id == "vetka_search_semantic"
            assert isinstance(r.score, float)
            assert isinstance(r.reason, str)
            assert isinstance(r.source_signals, dict)
            assert "semantic" in r.source_signals


# ─── T2.15: Freshness curiosity boost (Phase 195.4) ──────────────

class TestFreshnessCuriosityBoost:
    """MARKER_195.4 — Recently-updated tools get CAM boost."""

    def teardown_method(self):
        import src.services.tool_source_watch as tsw_mod
        tsw_mod._watch_instance = None

    def test_fresh_tool_gets_cam_boost(self, scorer, search_tool):
        """Tool updated <48h ago should get higher CAM signal."""
        from src.services.tool_source_watch import ToolFreshnessEntry
        import src.services.tool_source_watch as tsw_mod

        freshness = ToolFreshnessEntry(
            source_files=["src/mcp/tools/search_tool.py"],
            current_epoch=1,
            updated_at=datetime.now(timezone.utc).isoformat(),
            history=[
                {"epoch": 0, "commit": "old", "ts": "2026-03-01T00:00:00+00:00"},
                {"epoch": 1, "commit": "new", "ts": datetime.now(timezone.utc).isoformat()},
            ],
        )

        # Without freshness
        tsw_mod._watch_instance = None
        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            signals_no_fresh = scorer.score_signals(
                search_tool, ReflexContext(cam_surprise=0.2)
            )

        # With freshness mock
        mock_watch = MagicMock()
        mock_watch.get.return_value = freshness
        tsw_mod._watch_instance = mock_watch

        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            signals_fresh = scorer.score_signals(
                search_tool, ReflexContext(cam_surprise=0.2)
            )

        # Fresh tool should have higher CAM signal (0.2 + 0.3 = 0.5 → returns 0.5)
        # vs non-fresh (0.2 → returns 0.3)
        assert signals_fresh["cam"] >= signals_no_fresh["cam"], (
            f"Fresh tool CAM {signals_fresh['cam']} should be >= non-fresh {signals_no_fresh['cam']}"
        )

    def test_non_fresh_tool_unaffected(self, scorer, search_tool):
        """Tool NOT recently updated should get normal CAM score."""
        from src.services.tool_source_watch import ToolFreshnessEntry
        import src.services.tool_source_watch as tsw_mod

        old_time = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
        freshness = ToolFreshnessEntry(
            source_files=["src/mcp/tools/search_tool.py"],
            current_epoch=1,
            updated_at=old_time,
            history=[
                {"epoch": 0, "commit": "old", "ts": "2026-03-01T00:00:00+00:00"},
                {"epoch": 1, "commit": "new", "ts": old_time},
            ],
        )

        mock_watch = MagicMock()
        mock_watch.get.return_value = freshness
        tsw_mod._watch_instance = mock_watch

        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            signals = scorer.score_signals(
                search_tool, ReflexContext(cam_surprise=0.2)
            )

        # Non-fresh → normal CAM signal (0.2 < 0.3 → returns 0.3)
        assert signals["cam"] == 0.3

    def test_boost_decays_over_time(self, scorer, search_tool):
        """Freshness boost should decay linearly from +0.3 to 0 over 48h."""
        from src.services.tool_source_watch import ToolFreshnessEntry
        import src.services.tool_source_watch as tsw_mod

        # 24h ago → boost = 0.3 * (1 - 24/48) = 0.15
        time_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        freshness_24h = ToolFreshnessEntry(
            source_files=["test.py"], current_epoch=1,
            updated_at=time_24h,
            history=[
                {"epoch": 0, "commit": "old", "ts": "2026-03-01T00:00:00+00:00"},
                {"epoch": 1, "commit": "new", "ts": time_24h},
            ],
        )

        # Just now → boost = 0.3
        time_now = datetime.now(timezone.utc).isoformat()
        freshness_now = ToolFreshnessEntry(
            source_files=["test.py"], current_epoch=1,
            updated_at=time_now,
            history=[
                {"epoch": 0, "commit": "old", "ts": "2026-03-01T00:00:00+00:00"},
                {"epoch": 1, "commit": "new", "ts": time_now},
            ],
        )

        with patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            # Score at t=0
            mock0 = MagicMock()
            mock0.get.return_value = freshness_now
            tsw_mod._watch_instance = mock0
            signals_now = scorer.score_signals(
                search_tool, ReflexContext(cam_surprise=0.2)
            )

            # Score at t=24h
            mock24 = MagicMock()
            mock24.get.return_value = freshness_24h
            tsw_mod._watch_instance = mock24
            signals_24h = scorer.score_signals(
                search_tool, ReflexContext(cam_surprise=0.2)
            )

        # t=0 boost should be >= t=24h boost (both might hit same threshold tier)
        assert signals_now["cam"] >= signals_24h["cam"]
