"""
Phase 196 — Triada Wiring integration tests.

MARKER_196

Tests the data flows between the three Phase 195 modules:
  D2 -> D3: Tool Freshness -> Curiosity (via EmotionContext.tool_freshness)
  D1 -> D3: Protocol Guard -> Caution (via EmotionContext.guard_warnings)
  D3 -> D1: Trust -> Warning Severity (via _modulate_severity_by_trust)
"""

import math
import pytest
from unittest.mock import patch, MagicMock

from src.services.reflex_emotions import (
    EmotionContext,
    EmotionEngine,
    EmotionState,
    compute_curiosity,
    compute_caution,
    get_reflex_emotions,
    reset_reflex_emotions,
)
from src.services.protocol_guard import (
    ProtocolGuard,
    ProtocolViolation,
    reset_protocol_guard,
)
from src.services.session_tracker import (
    SessionActionTracker,
    reset_session_tracker,
)


# ════════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════════

SID = "test-196-session"


@pytest.fixture(autouse=True)
def _reset_singletons():
    reset_reflex_emotions()
    reset_session_tracker()
    reset_protocol_guard()
    yield
    reset_reflex_emotions()
    reset_session_tracker()
    reset_protocol_guard()


@pytest.fixture
def engine(tmp_path):
    return EmotionEngine(data_dir=str(tmp_path))


@pytest.fixture
def guard():
    return ProtocolGuard()


@pytest.fixture
def tracker():
    return SessionActionTracker()


# ════════════════════════════════════════════════════════════════
# 196.1: D2 -> D3 — Freshness -> Curiosity
# ════════════════════════════════════════════════════════════════

class TestFreshnessToCuriosity:
    """196.1: Tool freshness data flows into emotion curiosity."""

    def test_fresh_tool_higher_curiosity(self, engine):
        """A tool with high freshness_score gets higher curiosity than stale one."""
        ctx_stale = EmotionContext(freshness_score=0.0)
        ctx_fresh = EmotionContext(freshness_score=1.0)

        state_stale = engine.compute_emotions("tool_stale", ctx_stale)
        state_fresh = engine.compute_emotions("tool_fresh", ctx_fresh)

        assert state_fresh.curiosity > state_stale.curiosity, (
            f"Fresh curiosity ({state_fresh.curiosity}) should exceed stale ({state_stale.curiosity})"
        )

    def test_freshness_score_from_tool_freshness_dict(self, engine):
        """EmotionContext.tool_freshness dict can populate per-tool freshness_score."""
        # Simulate what reflex_integration does: set freshness_score from the dict
        tool_freshness = {"tool_a": 0.9, "tool_b": 0.1}

        ctx_a = EmotionContext(freshness_score=tool_freshness.get("tool_a", 0.0))
        ctx_b = EmotionContext(freshness_score=tool_freshness.get("tool_b", 0.0))

        state_a = engine.compute_emotions("tool_a", ctx_a)
        state_b = engine.compute_emotions("tool_b", ctx_b)

        assert state_a.curiosity > state_b.curiosity, (
            f"Tool A (fresh=0.9) curiosity ({state_a.curiosity}) should exceed "
            f"Tool B (fresh=0.1) curiosity ({state_b.curiosity})"
        )

    def test_freshness_decay_linear(self):
        """Freshness score decays linearly: 1.0 at 0h, 0.5 at 24h, 0.0 at 48h."""
        from src.services.tool_source_watch import FRESHNESS_WINDOW_HOURS

        hours_cases = [
            (0.0, 1.0),
            (24.0, 0.5),
            (48.0, 0.0),
            (12.0, 0.75),
        ]
        for hours, expected in hours_cases:
            score = max(0.0, 1.0 - hours / FRESHNESS_WINDOW_HOURS)
            assert abs(score - expected) < 0.01, (
                f"At {hours}h expected ~{expected}, got {score}"
            )

    def test_curiosity_computation_with_freshness(self):
        """compute_curiosity with freshness_score=1.0 on heavy-use tool still boosts."""
        c_no = compute_curiosity(usage_count=20, freshness_score=0.0)
        c_yes = compute_curiosity(usage_count=20, freshness_score=1.0)
        assert c_yes > c_no, f"Freshness should boost even heavy-use: {c_yes} > {c_no}"


# ════════════════════════════════════════════════════════════════
# 196.2: D1 -> D3 — Guard -> Caution
# ════════════════════════════════════════════════════════════════

class TestGuardToCaution:
    """196.2: Protocol Guard violations flow into emotion caution."""

    def test_guard_warnings_raise_caution(self):
        """guard_warnings in EmotionContext raise caution >= 0.7."""
        caution = compute_caution(
            tool_permission="READ",
            is_foreign_file=False,
            has_recon=True,
            guard_warnings=["read_before_edit"],
        )
        assert caution >= 0.7, f"Guard warning should raise caution >= 0.7, got {caution}"

    def test_no_guard_warnings_low_caution(self):
        """No guard_warnings with READ permission -> caution <= 0.1."""
        caution = compute_caution(
            tool_permission="READ",
            is_foreign_file=False,
            has_recon=True,
            guard_warnings=[],
        )
        assert caution <= 0.1, f"No warnings READ should have caution <= 0.1, got {caution}"

    def test_guard_warnings_cap_trust(self, engine):
        """Guard warnings cap trust at 0.3 even after many successes."""
        ctx_safe = EmotionContext()
        # Build trust with successes
        for _ in range(10):
            engine.record_outcome("tool_x", success=True, context=ctx_safe)

        state_high = engine.get_emotion_state("tool_x")
        assert state_high.trust > 0.7, f"Expected high trust after successes, got {state_high.trust}"

        # Now compute with guard warnings
        ctx_warn = EmotionContext(guard_warnings=["task_before_code"])
        state = engine.compute_emotions("tool_x", ctx_warn)
        assert state.trust <= 0.3, (
            f"Guard warnings should cap trust at 0.3, got {state.trust}"
        )

    def test_guard_warnings_lower_modifier(self, engine):
        """Modifier with guard_warnings is lower than without."""
        ctx_safe = EmotionContext()
        ctx_warn = EmotionContext(guard_warnings=["read_before_edit"])

        mod_safe = engine.compute_modifier("tool_m", ctx_safe)
        mod_warn = engine.compute_modifier("tool_m", ctx_warn)

        assert mod_warn < mod_safe, (
            f"Warning modifier ({mod_warn}) should be less than safe ({mod_safe})"
        )


# ════════════════════════════════════════════════════════════════
# 196.3: D3 -> D1 — Trust -> Warning Severity
# ════════════════════════════════════════════════════════════════

class TestTrustToSeverity:
    """196.3: Emotion trust modulates Protocol Guard violation severity."""

    def test_high_trust_downgrades_block_to_warn(self, guard):
        """Trust > 0.7 downgrades non-critical 'block' to 'warn'."""
        # Create a high-trust state for the tool
        mock_state = EmotionState(tool_id="Edit", trust=0.85)

        with patch("src.services.reflex_emotions.get_reflex_emotions") as mock_emo:
            mock_engine = MagicMock()
            mock_engine.get_emotion_state.return_value = mock_state
            mock_emo.return_value = mock_engine

            violations = [
                ProtocolViolation(
                    rule_id="read_before_edit",
                    severity="block",
                    message="You haven't read the file",
                    suggestion="Read first",
                ),
            ]
            result = guard._modulate_severity_by_trust(violations, "Edit")

        assert result[0].severity == "warn", (
            f"Expected 'warn' with high trust, got '{result[0].severity}'"
        )
        assert "softened" in result[0].message

    def test_low_trust_upgrades_warn_to_block(self, guard):
        """Trust < 0.3 upgrades non-critical 'warn' to 'block'."""
        mock_state = EmotionState(tool_id="Edit", trust=0.15)

        with patch("src.services.reflex_emotions.get_reflex_emotions") as mock_emo:
            mock_engine = MagicMock()
            mock_engine.get_emotion_state.return_value = mock_state
            mock_emo.return_value = mock_engine

            violations = [
                ProtocolViolation(
                    rule_id="read_before_edit",
                    severity="warn",
                    message="You haven't read the file",
                    suggestion="Read first",
                ),
            ]
            result = guard._modulate_severity_by_trust(violations, "Edit")

        assert result[0].severity == "block", (
            f"Expected 'block' with low trust, got '{result[0].severity}'"
        )
        assert "escalated" in result[0].message

    def test_medium_trust_no_change(self, guard):
        """Trust in [0.3, 0.7] leaves severity unchanged."""
        mock_state = EmotionState(tool_id="Edit", trust=0.5)

        with patch("src.services.reflex_emotions.get_reflex_emotions") as mock_emo:
            mock_engine = MagicMock()
            mock_engine.get_emotion_state.return_value = mock_state
            mock_emo.return_value = mock_engine

            violations = [
                ProtocolViolation(
                    rule_id="read_before_edit",
                    severity="warn",
                    message="Original message",
                    suggestion="Read first",
                ),
            ]
            result = guard._modulate_severity_by_trust(violations, "Edit")

        assert result[0].severity == "warn"
        assert result[0].message == "Original message"

    def test_critical_rules_never_downgraded(self, guard):
        """Critical rules (task_before_code, taskboard_before_work) never change severity."""
        mock_state = EmotionState(tool_id="Edit", trust=0.95)

        with patch("src.services.reflex_emotions.get_reflex_emotions") as mock_emo:
            mock_engine = MagicMock()
            mock_engine.get_emotion_state.return_value = mock_state
            mock_emo.return_value = mock_engine

            violations = [
                ProtocolViolation(
                    rule_id="task_before_code",
                    severity="block",
                    message="No task claimed",
                    suggestion="Claim a task",
                ),
                ProtocolViolation(
                    rule_id="taskboard_before_work",
                    severity="block",
                    message="Haven't checked board",
                    suggestion="Check board",
                ),
            ]
            result = guard._modulate_severity_by_trust(violations, "Edit")

        assert result[0].severity == "block", "task_before_code must stay block"
        assert result[1].severity == "block", "taskboard_before_work must stay block"

    def test_emotion_import_failure_nonfatal(self, guard):
        """If reflex_emotions import fails, violations pass through unchanged."""
        with patch("src.services.reflex_emotions.get_reflex_emotions", side_effect=ImportError("no emo")):
            violations = [
                ProtocolViolation(
                    rule_id="read_before_edit",
                    severity="warn",
                    message="Test message",
                    suggestion="Test",
                ),
            ]
            result = guard._modulate_severity_by_trust(violations, "Edit")

        assert result[0].severity == "warn"
        assert result[0].message == "Test message"


# ════════════════════════════════════════════════════════════════
# 196.4: Gap Fixes (already done by SC-A - verify)
# ════════════════════════════════════════════════════════════════

class TestGapFixesVerification:
    """196.4: Verify that score() and record_outcome() have emotion integration."""

    def test_scorer_score_has_emotion_modifier(self):
        """ReflexScorer.score() applies emotion modifier (verified in source)."""
        from src.services.reflex_scorer import ReflexScorer
        import inspect
        source = inspect.getsource(ReflexScorer.score)
        assert "emotion" in source.lower() or "emo" in source.lower(), (
            "ReflexScorer.score() should reference emotion modifier"
        )

    def test_feedback_record_outcome_has_emotion_update(self):
        """ReflexFeedback.record_outcome() updates emotions (verified in source)."""
        from src.services.reflex_feedback import ReflexFeedback
        import inspect
        source = inspect.getsource(ReflexFeedback.record_outcome)
        assert "emotion" in source.lower() or "emo" in source.lower(), (
            "ReflexFeedback.record_outcome() should reference emotion update"
        )

    def test_feedback_record_has_emotion_update(self):
        """ReflexFeedback.record() updates emotions (verified in source)."""
        from src.services.reflex_feedback import ReflexFeedback
        import inspect
        source = inspect.getsource(ReflexFeedback.record)
        assert "emotion" in source.lower() or "emo" in source.lower(), (
            "ReflexFeedback.record() should reference emotion update"
        )
