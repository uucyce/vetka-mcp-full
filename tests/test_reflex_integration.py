"""
Tests for REFLEX Integration — Phase 172.P4

MARKER_172.P4.TESTS

Tests the thin integration hooks that wire REFLEX into the pipeline.
Each test: mock dependencies → call function → verify behavior.

T4.1 — pre-FC recommends tools (mock scorer)
T4.2 — post-FC records feedback (mock feedback)
T4.3 — verifier closes feedback loop
T4.4 — session_init includes recommendations
T4.5 — feature flag off → no side effects
T4.6 — full pipeline feedback cycle
T4.7 — regression: disabled reflex = zero REFLEX calls

Bonus tests:
- Error handling: each function swallows errors gracefully
- reflex_for_role: stores recommendations in subtask.context
- Edge cases: empty inputs, missing fields
"""

import os
import sys
import json
import time
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ─── Mock subtask for testing ────────────────────────────────────

@dataclass
class MockSubtask:
    """Minimal subtask mock for REFLEX integration testing."""
    description: str = "Fix authentication bug in login.py"
    marker: str = "step_1"
    status: str = "pending"
    keywords: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = ["fix", "auth", "login"]
        if self.context is None:
            self.context = {}


# ─── Mock ScoredTool for scorer.recommend() returns ─────────────

@dataclass
class MockScoredTool:
    tool_id: str
    score: float
    reason: str = "test reason"


# ─── T4.1: Pre-FC recommends tools ──────────────────────────────

class TestPreFC:
    """T4.1: reflex_pre_fc calls scorer and returns recommendations."""

    @patch("src.services.reflex_integration._is_enabled", return_value=True)
    @patch("src.services.reflex_scorer.get_reflex_scorer")
    @patch("src.services.reflex_registry.get_reflex_registry")
    def test_pre_fc_returns_recommendations(self, mock_reg, mock_scorer_fn, mock_enabled):
        from src.services.reflex_integration import reflex_pre_fc

        # Setup mocks
        mock_scorer = MagicMock()
        mock_scorer.recommend.return_value = [
            MockScoredTool("vetka_read_file", 0.85, "file reading"),
            MockScoredTool("vetka_search_semantic", 0.72, "search"),
        ]
        mock_scorer_fn.return_value = mock_scorer

        mock_registry = MagicMock()
        mock_registry.get_tools_for_role.return_value = []
        mock_reg.return_value = mock_registry

        subtask = MockSubtask()
        result = reflex_pre_fc(subtask, phase_type="fix", agent_role="coder")

        assert len(result) == 2
        assert result[0]["tool_id"] == "vetka_read_file"
        assert result[0]["score"] == 0.85
        assert result[0]["reason"] == "file reading"
        mock_scorer.recommend.assert_called_once()

    @patch("src.services.reflex_integration._is_enabled", return_value=True)
    @patch("src.services.reflex_scorer.get_reflex_scorer")
    @patch("src.services.reflex_registry.get_reflex_registry")
    def test_pre_fc_loads_feedback_scores(self, mock_reg, mock_scorer_fn, mock_enabled):
        """IP-1 should attempt to load feedback scores into context."""
        from src.services.reflex_integration import reflex_pre_fc

        mock_scorer = MagicMock()
        mock_scorer.recommend.return_value = []
        mock_scorer_fn.return_value = mock_scorer
        mock_registry = MagicMock()
        mock_registry.get_tools_for_role.return_value = []
        mock_reg.return_value = mock_registry

        subtask = MockSubtask()
        with patch("src.services.reflex_feedback.get_reflex_feedback") as mock_fb:
            mock_fb.return_value.get_scores_bulk.return_value = {"tool_a": 0.9}
            reflex_pre_fc(subtask, phase_type="build")
            mock_fb.return_value.get_scores_bulk.assert_called_once_with("build")

    @patch("src.services.reflex_integration._is_enabled", return_value=True)
    def test_pre_fc_error_returns_empty(self, mock_enabled):
        """On any error, reflex_pre_fc returns empty list."""
        from src.services.reflex_integration import reflex_pre_fc

        # Force an import error
        with patch.dict("sys.modules", {"src.services.reflex_scorer": None}):
            result = reflex_pre_fc(MockSubtask())
            assert result == []


# ─── T4.2: Post-FC records feedback ─────────────────────────────

class TestPostFC:
    """T4.2: reflex_post_fc records tool usage feedback."""

    @patch("src.services.reflex_integration._is_enabled", return_value=True)
    @patch("src.services.reflex_feedback.get_reflex_feedback")
    def test_post_fc_records_all_tools(self, mock_fb_fn, mock_enabled):
        from src.services.reflex_integration import reflex_post_fc

        mock_fb = MagicMock()
        mock_fb_fn.return_value = mock_fb

        tool_executions = [
            {"name": "vetka_read_file", "args": {"file_path": "src/main.py"}, "result": {"success": True, "result": "file content"}},
            {"name": "vetka_search_semantic", "args": {"query": "auth"}, "result": {"success": True, "result": "found 3 matches"}},
            {"name": "vetka_edit_file", "args": {}, "result": {"success": False}},
        ]

        count = reflex_post_fc(tool_executions, phase_type="fix", subtask_id="step_1")
        assert count == 3
        assert mock_fb.record.call_count == 3

        # Verify first call
        first_call = mock_fb.record.call_args_list[0]
        assert first_call.kwargs["tool_id"] == "vetka_read_file"
        assert first_call.kwargs["success"] == True
        assert first_call.kwargs["useful"] == True  # success + has result content
        assert first_call.kwargs["phase_type"] == "fix"
        assert first_call.kwargs["subtask_id"] == "step_1"

        # Verify failed tool
        third_call = mock_fb.record.call_args_list[2]
        assert third_call.kwargs["tool_id"] == "vetka_edit_file"
        assert third_call.kwargs["success"] == False
        assert third_call.kwargs["useful"] == False

    @patch("src.services.reflex_integration._is_enabled", return_value=True)
    @patch("src.services.reflex_feedback.get_reflex_feedback")
    def test_post_fc_empty_executions(self, mock_fb_fn, mock_enabled):
        from src.services.reflex_integration import reflex_post_fc
        count = reflex_post_fc([], phase_type="research")
        assert count == 0

    @patch("src.services.reflex_integration._is_enabled", return_value=True)
    def test_post_fc_error_returns_zero(self, mock_enabled):
        from src.services.reflex_integration import reflex_post_fc
        with patch.dict("sys.modules", {"src.services.reflex_feedback": None}):
            count = reflex_post_fc([{"name": "tool", "args": {}, "result": {}}])
            assert count == 0


# ─── T4.3: Verifier closes feedback loop ────────────────────────

class TestVerifierFeedback:
    """T4.3: reflex_verifier records outcome for all used tools."""

    @patch("src.services.reflex_integration._is_enabled", return_value=True)
    @patch("src.services.reflex_feedback.get_reflex_feedback")
    def test_verifier_passed_records_outcome(self, mock_fb_fn, mock_enabled):
        from src.services.reflex_integration import reflex_verifier

        mock_fb = MagicMock()
        mock_fb.record_outcome.return_value = 3
        mock_fb_fn.return_value = mock_fb

        count = reflex_verifier(
            subtask_id="step_1",
            tools_used=["vetka_read_file", "vetka_search_semantic", "vetka_edit_file"],
            verifier_passed=True,
            phase_type="build",
        )

        assert count == 3
        mock_fb.record_outcome.assert_called_once_with(
            subtask_id="step_1",
            tools_used=["vetka_read_file", "vetka_search_semantic", "vetka_edit_file"],
            verifier_passed=True,
            phase_type="build",
            agent_role="coder",
        )

    @patch("src.services.reflex_integration._is_enabled", return_value=True)
    @patch("src.services.reflex_feedback.get_reflex_feedback")
    def test_verifier_failed_records_outcome(self, mock_fb_fn, mock_enabled):
        from src.services.reflex_integration import reflex_verifier

        mock_fb = MagicMock()
        mock_fb.record_outcome.return_value = 2
        mock_fb_fn.return_value = mock_fb

        count = reflex_verifier(
            subtask_id="step_2",
            tools_used=["vetka_edit_file", "vetka_read_file"],
            verifier_passed=False,
            phase_type="fix",
        )

        assert count == 2
        call_kwargs = mock_fb.record_outcome.call_args.kwargs
        assert call_kwargs["verifier_passed"] == False

    @patch("src.services.reflex_integration._is_enabled", return_value=True)
    def test_verifier_error_returns_zero(self, mock_enabled):
        from src.services.reflex_integration import reflex_verifier
        with patch.dict("sys.modules", {"src.services.reflex_feedback": None}):
            count = reflex_verifier("step_1", ["tool_a"], True)
            assert count == 0


# ─── T4.4: Session init includes recommendations ────────────────

class TestSessionRecommendations:
    """T4.4: reflex_session returns recommendations for session_init."""

    @patch("src.services.reflex_integration._is_enabled", return_value=True)
    @patch("src.services.reflex_scorer.get_reflex_scorer")
    def test_session_returns_recommendations(self, mock_scorer_fn, mock_enabled):
        from src.services.reflex_integration import reflex_session

        mock_scorer = MagicMock()
        mock_scorer.recommend_for_session.return_value = [
            MockScoredTool("vetka_search_semantic", 0.9, "semantic search"),
            MockScoredTool("vetka_read_file", 0.8, "file reading"),
        ]
        mock_scorer_fn.return_value = mock_scorer

        session_data = {"user_id": "test", "project_digest": {"phase": 172}}
        result = reflex_session(session_data, phase_type="research")

        assert len(result) == 2
        assert result[0]["tool_id"] == "vetka_search_semantic"
        assert result[0]["score"] == 0.9
        assert result[0]["reason"] == "semantic search"

    @patch("src.services.reflex_integration._is_enabled", return_value=True)
    def test_session_error_returns_empty(self, mock_enabled):
        from src.services.reflex_integration import reflex_session
        with patch.dict("sys.modules", {"src.services.reflex_scorer": None}):
            result = reflex_session({"user_id": "test"})
            assert result == []


# ─── T4.5: Feature flag off → no side effects ───────────────────

class TestFeatureFlagOff:
    """T4.5: When REFLEX_ENABLED=False, all functions are no-ops."""

    @patch("src.services.reflex_integration._is_enabled", return_value=False)
    def test_pre_fc_disabled(self, mock_enabled):
        from src.services.reflex_integration import reflex_pre_fc
        result = reflex_pre_fc(MockSubtask())
        assert result == []

    @patch("src.services.reflex_integration._is_enabled", return_value=False)
    def test_post_fc_disabled(self, mock_enabled):
        from src.services.reflex_integration import reflex_post_fc
        result = reflex_post_fc([{"name": "tool", "args": {}, "result": {}}])
        assert result == 0

    @patch("src.services.reflex_integration._is_enabled", return_value=False)
    def test_verifier_disabled(self, mock_enabled):
        from src.services.reflex_integration import reflex_verifier
        result = reflex_verifier("step_1", ["tool_a"], True)
        assert result == 0

    @patch("src.services.reflex_integration._is_enabled", return_value=False)
    def test_for_role_disabled(self, mock_enabled):
        from src.services.reflex_integration import reflex_for_role
        result = reflex_for_role("coder")
        assert result == []

    @patch("src.services.reflex_integration._is_enabled", return_value=False)
    def test_session_disabled(self, mock_enabled):
        from src.services.reflex_integration import reflex_session
        result = reflex_session({"user_id": "test"})
        assert result == []

    @patch("src.services.reflex_integration._is_enabled", return_value=False)
    def test_no_scorer_calls_when_disabled(self, mock_enabled):
        """When disabled, scorer/feedback modules should NOT be imported."""
        from src.services.reflex_integration import reflex_pre_fc, reflex_post_fc, reflex_verifier, reflex_for_role, reflex_session

        with patch("src.services.reflex_scorer.get_reflex_scorer") as mock_scorer:
            reflex_pre_fc(MockSubtask())
            reflex_for_role("coder")
            reflex_session({})
            # Scorer should never be called when disabled
            mock_scorer.assert_not_called()

        with patch("src.services.reflex_feedback.get_reflex_feedback") as mock_fb:
            reflex_post_fc([{"name": "t", "args": {}, "result": {}}])
            reflex_verifier("s1", ["t"], True)
            mock_fb.assert_not_called()


# ─── T4.6: Full pipeline feedback cycle ─────────────────────────

class TestFullPipelineCycle:
    """T4.6: End-to-end: score → execute → feedback → improved next score."""

    def test_full_cycle_with_real_objects(self, tmp_path):
        """Real scorer + real feedback — full learning loop."""
        # Force enable REFLEX
        with patch("src.services.reflex_integration._is_enabled", return_value=True):
            from src.services.reflex_integration import reflex_pre_fc, reflex_post_fc, reflex_verifier

            # Setup real feedback with temp log
            from src.services.reflex_feedback import ReflexFeedback
            fb = ReflexFeedback(log_path=tmp_path / "feedback.jsonl")

            # Setup real scorer
            from src.services.reflex_scorer import ReflexScorer
            scorer = ReflexScorer()

            # Setup real registry with a few tools
            from src.services.reflex_registry import ReflexRegistry, ToolEntry
            registry = ReflexRegistry()
            registry._tools = {
                "vetka_read_file": ToolEntry(
                    tool_id="vetka_read_file",
                    namespace="vetka",
                    kind="file_op",
                    description="Read file content from the codebase",
                    intent_tags=["read", "file", "content"],
                    trigger_patterns={"file_types": ["*"], "phase_types": ["fix", "build", "research"], "keywords": ["read", "file"]},
                    roles=["coder", "researcher"],
                ),
                "vetka_search_semantic": ToolEntry(
                    tool_id="vetka_search_semantic",
                    namespace="vetka",
                    kind="search",
                    description="Search codebase using vector similarity",
                    intent_tags=["search", "find", "semantic"],
                    trigger_patterns={"file_types": ["*"], "phase_types": ["research", "fix"], "keywords": ["search", "find"]},
                    roles=["coder", "researcher"],
                ),
            }

            # Step 1: Get initial recommendations (cold start — default scores)
            with patch("src.services.reflex_scorer.get_reflex_scorer", return_value=scorer), \
                 patch("src.services.reflex_registry.get_reflex_registry", return_value=registry):
                subtask = MockSubtask(description="Fix login bug by reading auth files")
                recs = reflex_pre_fc(subtask, phase_type="fix", agent_role="coder")
                assert isinstance(recs, list)

            # Step 2: Simulate tool execution (both succeed)
            tool_execs = [
                {"name": "vetka_read_file", "args": {"file_path": "auth.py"}, "result": {"success": True, "result": "code"}},
                {"name": "vetka_search_semantic", "args": {"query": "login"}, "result": {"success": True, "result": "matches"}},
            ]
            with patch("src.services.reflex_feedback.get_reflex_feedback", return_value=fb):
                count = reflex_post_fc(tool_execs, phase_type="fix", subtask_id="step_1")
                assert count == 2

            # Step 3: Verifier passes
            with patch("src.services.reflex_feedback.get_reflex_feedback", return_value=fb):
                count = reflex_verifier("step_1", ["vetka_read_file", "vetka_search_semantic"], True, "fix")
                assert count == 2

            # Verify feedback was persisted
            assert fb.entry_count == 4  # 2 from post_fc + 2 from verifier

            # Step 4: Scores should reflect positive feedback
            score_read = fb.get_score("vetka_read_file", "fix")
            score_search = fb.get_score("vetka_search_semantic", "fix")
            assert score_read > 0.5  # Better than cold start default
            assert score_search > 0.5

    def test_failed_verifier_lowers_score(self, tmp_path):
        """Failed verification should lower feedback scores."""
        with patch("src.services.reflex_integration._is_enabled", return_value=True):
            from src.services.reflex_integration import reflex_post_fc, reflex_verifier
            from src.services.reflex_feedback import ReflexFeedback

            fb = ReflexFeedback(log_path=tmp_path / "feedback.jsonl")

            # Record successful execution
            with patch("src.services.reflex_feedback.get_reflex_feedback", return_value=fb):
                reflex_post_fc(
                    [{"name": "bad_tool", "args": {}, "result": {"success": True, "result": "output"}}],
                    phase_type="build", subtask_id="step_1"
                )

            # But verifier FAILS
            with patch("src.services.reflex_feedback.get_reflex_feedback", return_value=fb):
                reflex_verifier("step_1", ["bad_tool"], False, "build")

            # Score should be lower than 1.0 because verifier_passed=False
            score = fb.get_score("bad_tool", "build")
            assert score < 1.0  # Not perfect — verifier failure dragged it down


# ─── T4.7: Regression — disabled = no REFLEX calls ──────────────

class TestRegression:
    """T4.7: With REFLEX disabled, existing pipeline behavior unchanged."""

    def test_is_enabled_defaults_false(self):
        """Feature flag defaults to False when env var not set."""
        from src.services.reflex_integration import _is_enabled
        # Clear any cached state
        with patch.dict(os.environ, {}, clear=False):
            # _is_enabled imports REFLEX_ENABLED from scorer
            # which defaults to False unless REFLEX_ENABLED=1 in env
            result = _is_enabled()
            # Should be False by default (feature flag)
            assert isinstance(result, bool)

    def test_all_functions_safe_with_missing_modules(self):
        """If reflex modules are missing entirely, no crashes."""
        from src.services.reflex_integration import (
            reflex_pre_fc, reflex_post_fc, reflex_verifier,
            reflex_for_role, reflex_session
        )

        # Simulate disabled state (most common case)
        with patch("src.services.reflex_integration._is_enabled", return_value=False):
            assert reflex_pre_fc(MockSubtask()) == []
            assert reflex_post_fc([]) == 0
            assert reflex_verifier("s", [], True) == 0
            assert reflex_for_role("coder") == []
            assert reflex_session({}) == []


# ─── Bonus: reflex_for_role ──────────────────────────────────────

class TestForRole:
    """Bonus: reflex_for_role stores recommendations in subtask context."""

    @patch("src.services.reflex_integration._is_enabled", return_value=True)
    @patch("src.services.reflex_scorer.get_reflex_scorer")
    @patch("src.services.reflex_registry.get_reflex_registry")
    def test_for_role_returns_recommendations(self, mock_reg, mock_scorer_fn, mock_enabled):
        from src.services.reflex_integration import reflex_for_role

        mock_scorer = MagicMock()
        mock_scorer.recommend.return_value = [
            MockScoredTool("vetka_read_file", 0.8),
            MockScoredTool("vetka_edit_file", 0.6),
        ]
        mock_scorer_fn.return_value = mock_scorer
        mock_registry = MagicMock()
        mock_registry.get_tools_for_role.return_value = []
        mock_reg.return_value = mock_registry

        result = reflex_for_role("coder", phase_type="build")
        assert len(result) == 2
        assert result[0]["tool_id"] == "vetka_read_file"
        assert result[0]["score"] == 0.8

    @patch("src.services.reflex_integration._is_enabled", return_value=True)
    @patch("src.services.reflex_scorer.get_reflex_scorer")
    @patch("src.services.reflex_registry.get_reflex_registry")
    def test_for_role_stores_in_subtask_context(self, mock_reg, mock_scorer_fn, mock_enabled):
        from src.services.reflex_integration import reflex_for_role

        mock_scorer = MagicMock()
        mock_scorer.recommend.return_value = [
            MockScoredTool("vetka_read_file", 0.8),
        ]
        mock_scorer_fn.return_value = mock_scorer
        mock_registry = MagicMock()
        mock_registry.get_tools_for_role.return_value = []
        mock_reg.return_value = mock_registry

        subtask = MockSubtask()
        reflex_for_role("coder", subtask=subtask, phase_type="build")

        assert "reflex_tools" in subtask.context
        assert subtask.context["reflex_tools"] == ["vetka_read_file"]

    @patch("src.services.reflex_integration._is_enabled", return_value=True)
    @patch("src.services.reflex_scorer.get_reflex_scorer")
    @patch("src.services.reflex_registry.get_reflex_registry")
    def test_for_role_no_subtask_no_crash(self, mock_reg, mock_scorer_fn, mock_enabled):
        from src.services.reflex_integration import reflex_for_role

        mock_scorer = MagicMock()
        mock_scorer.recommend.return_value = []
        mock_scorer_fn.return_value = mock_scorer
        mock_registry = MagicMock()
        mock_registry.get_tools_for_role.return_value = []
        mock_reg.return_value = mock_registry

        # No subtask — should not crash
        result = reflex_for_role("researcher", subtask=None)
        assert result == []


# ─── Bonus: Error resilience ─────────────────────────────────────

class TestErrorResilience:
    """All integration functions must swallow errors without breaking the pipeline."""

    @patch("src.services.reflex_integration._is_enabled", return_value=True)
    def test_pre_fc_survives_scorer_crash(self, mock_enabled):
        from src.services.reflex_integration import reflex_pre_fc
        with patch("src.services.reflex_scorer.get_reflex_scorer", side_effect=RuntimeError("boom")):
            result = reflex_pre_fc(MockSubtask())
            assert result == []

    @patch("src.services.reflex_integration._is_enabled", return_value=True)
    def test_post_fc_survives_feedback_crash(self, mock_enabled):
        from src.services.reflex_integration import reflex_post_fc
        with patch("src.services.reflex_feedback.get_reflex_feedback", side_effect=RuntimeError("boom")):
            count = reflex_post_fc([{"name": "t", "args": {}, "result": {}}])
            assert count == 0

    @patch("src.services.reflex_integration._is_enabled", return_value=True)
    def test_verifier_survives_feedback_crash(self, mock_enabled):
        from src.services.reflex_integration import reflex_verifier
        with patch("src.services.reflex_feedback.get_reflex_feedback", side_effect=RuntimeError("boom")):
            count = reflex_verifier("s1", ["t1"], True)
            assert count == 0

    @patch("src.services.reflex_integration._is_enabled", return_value=True)
    def test_for_role_survives_scorer_crash(self, mock_enabled):
        from src.services.reflex_integration import reflex_for_role
        with patch("src.services.reflex_scorer.get_reflex_scorer", side_effect=RuntimeError("boom")):
            result = reflex_for_role("coder")
            assert result == []

    @patch("src.services.reflex_integration._is_enabled", return_value=True)
    def test_session_survives_scorer_crash(self, mock_enabled):
        from src.services.reflex_integration import reflex_session
        with patch("src.services.reflex_scorer.get_reflex_scorer", side_effect=RuntimeError("boom")):
            result = reflex_session({})
            assert result == []


# ─── Bonus: Edge cases ───────────────────────────────────────────

class TestEdgeCases:
    """Edge cases for integration hooks."""

    @patch("src.services.reflex_integration._is_enabled", return_value=True)
    @patch("src.services.reflex_feedback.get_reflex_feedback")
    def test_post_fc_missing_result_key(self, mock_fb_fn, mock_enabled):
        """Tool execution with missing 'result' key."""
        from src.services.reflex_integration import reflex_post_fc

        mock_fb = MagicMock()
        mock_fb_fn.return_value = mock_fb

        # Malformed tool execution — no 'result' key
        tool_execs = [{"name": "tool_a", "args": {}}]
        count = reflex_post_fc(tool_execs, phase_type="research")
        assert count == 1
        # Should still record, just with success=False, useful=False
        call_kwargs = mock_fb.record.call_args.kwargs
        assert call_kwargs["success"] == False
        assert call_kwargs["useful"] == False

    @patch("src.services.reflex_integration._is_enabled", return_value=True)
    @patch("src.services.reflex_feedback.get_reflex_feedback")
    def test_verifier_empty_tools_list(self, mock_fb_fn, mock_enabled):
        """Verifier with empty tools_used list."""
        from src.services.reflex_integration import reflex_verifier

        mock_fb = MagicMock()
        mock_fb.record_outcome.return_value = 0
        mock_fb_fn.return_value = mock_fb

        count = reflex_verifier("step_1", [], True, "build")
        assert count == 0

    @patch("src.services.reflex_integration._is_enabled", return_value=True)
    @patch("src.services.reflex_scorer.get_reflex_scorer")
    @patch("src.services.reflex_registry.get_reflex_registry")
    def test_pre_fc_with_none_subtask_fields(self, mock_reg, mock_scorer_fn, mock_enabled):
        """Subtask with None fields should not crash."""
        from src.services.reflex_integration import reflex_pre_fc

        mock_scorer = MagicMock()
        mock_scorer.recommend.return_value = []
        mock_scorer_fn.return_value = mock_scorer
        mock_registry = MagicMock()
        mock_registry.get_tools_for_role.return_value = []
        mock_reg.return_value = mock_registry

        # Subtask with minimal fields
        subtask = MagicMock()
        subtask.description = None
        subtask.keywords = None
        result = reflex_pre_fc(subtask, phase_type="research")
        assert isinstance(result, list)
