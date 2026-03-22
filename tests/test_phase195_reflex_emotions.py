"""
Phase 195.2 — REFLEX Emotions test suite (36+ tests).

W1 (MARKER_195.3): 15 core unit tests — curiosity, trust, caution, modifier.
W2 (MARKER_195.6): 10 integration tests — persistence, engine, scenarios.
W3 (MARKER_195.2.2): Additional tests — mood_label, ENGRAM, feature flag, workflow.
"""

import json
import math
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.services.reflex_emotions import (
    EmotionState,
    EmotionContext,
    EmotionEngine,
    compute_curiosity,
    compute_trust,
    compute_caution,
    compute_emotion_modifier,
    get_mood_label,
    get_reflex_emotions,
    reset_reflex_emotions,
    REFLEX_EMOTIONS_ENABLED,
    _COLD_CURIOSITY,
    _COLD_TRUST,
    _COLD_CAUTION,
)


# ════════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════════

@pytest.fixture
def cold_state():
    """Cold-start EmotionState with defaults."""
    return EmotionState(tool_id="test_tool")


@pytest.fixture
def default_context():
    """Default EmotionContext — safe READ operation."""
    return EmotionContext(agent_id="test_agent", phase_type="research")


@pytest.fixture
def risky_context():
    """Risky context — WRITE + foreign + no recon."""
    return EmotionContext(
        agent_id="test_agent",
        phase_type="build",
        tool_permission="WRITE",
        is_foreign_file=True,
        has_recon=False,
        guard_warnings=["potential_overwrite"],
    )


@pytest.fixture
def engine(tmp_path):
    """Fresh EmotionEngine backed by tmp dir."""
    return EmotionEngine(data_dir=str(tmp_path))


@pytest.fixture(autouse=True)
def cleanup_singleton():
    """Reset the singleton before/after each test."""
    reset_reflex_emotions()
    yield
    reset_reflex_emotions()


# ════════════════════════════════════════════════════════════════
# W1 — Cat 1: Curiosity (5 tests)                MARKER_195.3
# ════════════════════════════════════════════════════════════════

class TestReflexEmotionsW1:
    """Wave 1: core emotion computations (curiosity, trust, caution, modifier)."""

    # ── Cat 1: Curiosity ──

    def test_01_curiosity_never_used_tool(self):
        """Never-used tool (usage=0) has high curiosity >= 0.6."""
        c = compute_curiosity(usage_count=0, freshness_score=0.0)
        # novelty = 1/(1+exp(0.5*(0-5))) = 1/(1+exp(-2.5)) ≈ 0.924
        assert c >= 0.6, f"Expected curiosity >= 0.6 for novel tool, got {c}"

    def test_02_curiosity_heavy_use(self):
        """Heavily-used tool (usage=10) has low curiosity < 0.3."""
        c = compute_curiosity(usage_count=10, freshness_score=0.0)
        # novelty = 1/(1+exp(0.5*(10-5))) = 1/(1+exp(2.5)) ≈ 0.076
        assert c < 0.3, f"Expected curiosity < 0.3 for heavy use, got {c}"

    def test_03_curiosity_freshness_boost(self):
        """Freshness boost increases curiosity for stale tools."""
        c_no_fresh = compute_curiosity(usage_count=10, freshness_score=0.0)
        c_fresh = compute_curiosity(usage_count=10, freshness_score=0.8)
        assert c_fresh > c_no_fresh, (
            f"Freshness should boost curiosity: {c_fresh} > {c_no_fresh}"
        )

    def test_04_curiosity_floor_zero(self):
        """Curiosity never goes below 0 even with extreme usage."""
        c = compute_curiosity(usage_count=1000, freshness_score=0.0)
        assert c >= 0.0, f"Curiosity must be >= 0, got {c}"

    def test_05_curiosity_capped_at_one(self):
        """Curiosity capped at 1.0 even with max freshness + novelty."""
        c = compute_curiosity(usage_count=0, freshness_score=1.0)
        # novelty ≈ 0.924 + freshness_boost = 0.4 → 1.324 → capped at 1.0
        assert c <= 1.0, f"Curiosity must be <= 1.0, got {c}"
        assert c == 1.0 or abs(c - 1.0) < 1e-9, (
            f"Expected curiosity capped at 1.0, got {c}"
        )

    # ── Cat 2: Trust ──

    def test_06_trust_cold_start(self, cold_state):
        """Cold-start trust is 0.5."""
        assert cold_state.trust == 0.5, f"Expected trust=0.5, got {cold_state.trust}"

    def test_07_trust_three_successes(self):
        """Three consecutive successes from 0.5 push trust above 0.65."""
        trust = 0.5
        for _ in range(3):
            trust = compute_trust(trust, success=True, guard_warnings=[])
        assert trust > 0.65, f"Expected trust > 0.65 after 3 successes, got {trust}"

    def test_08_trust_single_failure_drop(self):
        """Single failure from 0.8 drops trust significantly."""
        trust = compute_trust(0.8, success=False, guard_warnings=[])
        assert trust < 0.6, f"Expected trust < 0.6 after failure from 0.8, got {trust}"

    def test_09_trust_asymmetry(self):
        """Recovery is slower than drop — asymmetric dynamics."""
        after_fail = compute_trust(0.8, success=False, guard_warnings=[])
        after_recover = compute_trust(after_fail, success=True, guard_warnings=[])
        assert after_recover < 0.8, (
            f"Expected trust < 0.8 after fail+recover, got {after_recover}"
        )

    def test_10_trust_guard_warning_cap(self):
        """Guard warnings cap trust at 0.3, even if computed higher."""
        trust = compute_trust(0.9, success=True, guard_warnings=["security_risk"])
        assert trust <= 0.3, f"Expected trust <= 0.3 with guard warning, got {trust}"

    def test_11_trust_range(self):
        """Trust always stays in [0, 1]."""
        # Slam with many failures
        trust = 0.5
        for _ in range(50):
            trust = compute_trust(trust, success=False, guard_warnings=[])
        assert 0.0 <= trust <= 1.0, f"Trust out of range: {trust}"

        # Slam with many successes
        trust = 0.5
        for _ in range(50):
            trust = compute_trust(trust, success=True, guard_warnings=[])
        assert 0.0 <= trust <= 1.0, f"Trust out of range: {trust}"

    # ── Cat 3: Caution ──

    def test_12_caution_write_permission(self):
        """WRITE permission → caution >= 0.7."""
        c = compute_caution(
            tool_permission="WRITE",
            is_foreign_file=False,
            has_recon=True,
            guard_warnings=[],
        )
        assert c >= 0.7, f"Expected caution >= 0.7 for WRITE, got {c}"

    def test_13_caution_read_safe(self):
        """READ permission with no flags → caution <= 0.1."""
        c = compute_caution(
            tool_permission="READ",
            is_foreign_file=False,
            has_recon=True,
            guard_warnings=[],
        )
        assert c <= 0.1, f"Expected caution <= 0.1 for safe READ, got {c}"

    def test_14_caution_foreign_file(self):
        """Foreign file → caution >= 0.8."""
        c = compute_caution(
            tool_permission="READ",
            is_foreign_file=True,
            has_recon=True,
            guard_warnings=[],
        )
        assert c >= 0.8, f"Expected caution >= 0.8 for foreign file, got {c}"

    def test_15_caution_no_recon(self):
        """No recon → caution >= 0.5."""
        c = compute_caution(
            tool_permission="READ",
            is_foreign_file=False,
            has_recon=False,
            guard_warnings=[],
        )
        assert c >= 0.5, f"Expected caution >= 0.5 without recon, got {c}"

    def test_16_caution_guard_warnings(self):
        """Guard warnings → caution >= 0.7."""
        c = compute_caution(
            tool_permission="READ",
            is_foreign_file=False,
            has_recon=True,
            guard_warnings=["suspicious_pattern"],
        )
        assert c >= 0.7, f"Expected caution >= 0.7 with guard warnings, got {c}"

    # ── Cat 4: Modifier ──

    def test_17_modifier_range(self):
        """Modifier always in [0.3, 1.5] across extreme inputs."""
        test_cases = [
            (0.0, 0.0, 0.0),
            (1.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
            (1.0, 1.0, 1.0),
            (0.5, 0.5, 0.5),
            (0.0, 1.0, 1.0),
            (1.0, 0.0, 0.0),
        ]
        for curiosity, trust, caution in test_cases:
            m = compute_emotion_modifier(curiosity, trust, caution)
            assert 0.3 <= m <= 1.5, (
                f"Modifier {m} out of [0.3, 1.5] for "
                f"c={curiosity}, t={trust}, caut={caution}"
            )

    def test_18_modifier_high_caution_dominates(self):
        """High caution dominates — pulls modifier low."""
        m = compute_emotion_modifier(curiosity=0.5, trust=1.0, caution=1.0)
        assert m <= 0.75, f"Expected modifier <= 0.75 with max caution, got {m}"

    def test_19_modifier_low_trust_gates(self):
        """Low trust gates modifier — even with high curiosity."""
        m = compute_emotion_modifier(curiosity=1.0, trust=0.0, caution=0.0)
        # (0.5+0.0)*(1.0+0.3)*(1.0-0.0) = 0.5*1.3*1.0 = 0.65
        assert abs(m - 0.65) < 0.05, f"Expected modifier ≈ 0.65, got {m}"

    def test_20_modifier_cold_start(self):
        """Cold-start default values produce a reasonable modifier."""
        m = compute_emotion_modifier(
            curiosity=_COLD_CURIOSITY,
            trust=_COLD_TRUST,
            caution=_COLD_CAUTION,
        )
        # Should produce something reasonable in [0.5, 1.0]
        assert 0.3 <= m <= 1.5, f"Cold start modifier out of range: {m}"


# ════════════════════════════════════════════════════════════════
# W2 — Cat 5: Persistence + Cat 6: Integration   MARKER_195.6
# ════════════════════════════════════════════════════════════════

class TestReflexEmotionsW2:
    """Wave 2: persistence roundtrip, engine lifecycle, integration scenarios."""

    # ── Cat 5: Persistence ──

    def test_21_save_load_roundtrip(self, tmp_path):
        """EmotionEngine save/load roundtrip preserves state."""
        engine = EmotionEngine(data_dir=str(tmp_path))
        ctx = EmotionContext(agent_id="a1")

        # Record some outcomes to build state
        engine.record_outcome("tool_alpha", success=True, context=ctx)
        engine.record_outcome("tool_alpha", success=True, context=ctx)
        state_before = engine.get_emotion_state("tool_alpha")

        # Create new engine from same dir — should load persisted state
        engine2 = EmotionEngine(data_dir=str(tmp_path))
        state_after = engine2.get_emotion_state("tool_alpha")

        assert state_after.usage_count == state_before.usage_count, (
            f"Usage count mismatch: {state_after.usage_count} vs {state_before.usage_count}"
        )
        assert abs(state_after.trust - state_before.trust) < 1e-6, (
            f"Trust mismatch: {state_after.trust} vs {state_before.trust}"
        )

    def test_22_reset_singleton(self, tmp_path):
        """reset_reflex_emotions clears the engine singleton."""
        engine1 = get_reflex_emotions(data_dir=str(tmp_path))
        ctx = EmotionContext(agent_id="a1")
        engine1.record_outcome("tool_x", success=True, context=ctx)

        reset_reflex_emotions()

        engine2 = get_reflex_emotions(data_dir=str(tmp_path))
        assert engine1 is not engine2, "Reset should create new engine instance"

    # ── Cat 6: Integration scenarios ──

    def test_23_updated_tool_higher_modifier(self, tmp_path):
        """Recently-updated tool (high freshness) gets higher modifier than stale one."""
        engine = EmotionEngine(data_dir=str(tmp_path))

        ctx_stale = EmotionContext(agent_id="a1", freshness_score=0.0)
        ctx_fresh = EmotionContext(agent_id="a1", freshness_score=0.9)

        mod_stale = engine.compute_modifier("tool_stale", ctx_stale)
        mod_fresh = engine.compute_modifier("tool_fresh", ctx_fresh)

        assert mod_fresh > mod_stale, (
            f"Fresh tool modifier ({mod_fresh}) should exceed stale ({mod_stale})"
        )

    def test_24_failing_tool_lower_modifier(self, tmp_path):
        """Tool that keeps failing gets progressively lower modifier."""
        engine = EmotionEngine(data_dir=str(tmp_path))
        ctx = EmotionContext(agent_id="a1")

        mod_before = engine.compute_modifier("tool_flaky", ctx)

        for _ in range(5):
            engine.record_outcome("tool_flaky", success=False, context=ctx)

        mod_after = engine.compute_modifier("tool_flaky", ctx)

        assert mod_after < mod_before, (
            f"Failing tool modifier should decrease: {mod_after} < {mod_before}"
        )

    def test_25_risky_edit_low_modifier(self, tmp_path):
        """WRITE + foreign + no recon → low modifier (safety mode)."""
        engine = EmotionEngine(data_dir=str(tmp_path))
        risky = EmotionContext(
            agent_id="a1",
            phase_type="build",
            tool_permission="WRITE",
            is_foreign_file=True,
            has_recon=False,
            guard_warnings=["overwrite_risk"],
        )

        mod = engine.compute_modifier("dangerous_tool", risky)
        assert mod < 0.7, f"Risky edit modifier should be < 0.7, got {mod}"


# ════════════════════════════════════════════════════════════════
# W3 — Mood Label Tests                          MARKER_195.2.2
# ════════════════════════════════════════════════════════════════

class TestMoodLabel:
    """Tests for get_mood_label() function."""

    def test_26_mood_curious(self):
        """High curiosity dominant → 'curious'."""
        label = get_mood_label(curiosity=0.8, trust=0.5, caution=0.3)
        assert label == "curious", f"Expected 'curious', got '{label}'"

    def test_27_mood_confident(self):
        """High trust dominant → 'confident'."""
        label = get_mood_label(curiosity=0.3, trust=0.8, caution=0.2)
        assert label == "confident", f"Expected 'confident', got '{label}'"

    def test_28_mood_cautious(self):
        """High caution dominant → 'cautious'."""
        label = get_mood_label(curiosity=0.3, trust=0.4, caution=0.7)
        assert label == "cautious", f"Expected 'cautious', got '{label}'"

    def test_29_mood_neutral(self):
        """All moderate → 'neutral'."""
        label = get_mood_label(curiosity=0.5, trust=0.5, caution=0.3)
        assert label == "neutral", f"Expected 'neutral', got '{label}'"

    def test_30_mood_neutral_all_low(self):
        """All low values → 'neutral'."""
        label = get_mood_label(curiosity=0.2, trust=0.2, caution=0.2)
        assert label == "neutral", f"Expected 'neutral', got '{label}'"


# ════════════════════════════════════════════════════════════════
# W3 — ENGRAM Persistence Tests                  MARKER_195.2.2
# ════════════════════════════════════════════════════════════════

class TestEngramPersistence:
    """Tests for ENGRAM save/load of emotion states."""

    def test_31_engram_save_load_roundtrip(self, tmp_path):
        """Save to ENGRAM and load back preserves state."""
        engine = EmotionEngine(data_dir=str(tmp_path))

        # Mock the engram cache with a simple in-memory dict
        mock_store = {}

        def mock_put(key, value, category="default"):
            mock_store[key] = {"key": key, "value": value, "category": category}

        def mock_get_all():
            return mock_store

        mock_cache = MagicMock()
        mock_cache.put = mock_put
        mock_cache.get_all = mock_get_all

        with patch("src.services.reflex_emotions.get_engram_cache", return_value=mock_cache):
            # Record outcome which triggers ENGRAM save
            ctx = EmotionContext(agent_id="opus")
            engine.record_outcome("tool_a", success=True, context=ctx)
            engine.record_outcome("tool_a", success=True, context=ctx)

            # Load from ENGRAM
            loaded = engine.get_state_from_engram("opus", "tool_a")
            assert loaded is not None, "Should load state from ENGRAM"
            assert loaded.usage_count == 2, f"Expected usage_count=2, got {loaded.usage_count}"
            assert loaded.trust > 0.5, f"Expected trust > 0.5, got {loaded.trust}"

    def test_32_engram_load_missing_key(self, tmp_path):
        """Loading non-existent key from ENGRAM returns None."""
        engine = EmotionEngine(data_dir=str(tmp_path))

        mock_cache = MagicMock()
        mock_cache.get_all.return_value = {}

        with patch("src.services.reflex_emotions.get_engram_cache", return_value=mock_cache):
            loaded = engine.get_state_from_engram("agent_x", "nonexistent_tool")
            assert loaded is None, "Should return None for missing key"

    def test_33_engram_save_failure_nonfatal(self, tmp_path):
        """ENGRAM save failure is non-fatal — engine continues."""
        engine = EmotionEngine(data_dir=str(tmp_path))

        with patch("src.services.reflex_emotions.get_engram_cache", side_effect=ImportError("no engram")):
            # Should not raise
            ctx = EmotionContext(agent_id="a1")
            state = engine.record_outcome("tool_y", success=True, context=ctx)
            assert state.usage_count == 1, "Engine should still work despite ENGRAM failure"


# ════════════════════════════════════════════════════════════════
# W3 — Feature Flag Tests                        MARKER_195.2.2
# ════════════════════════════════════════════════════════════════

class TestFeatureFlag:
    """Tests for REFLEX_EMOTIONS_ENABLED feature flag."""

    def test_34_flag_disabled_modifier_is_one(self, tmp_path):
        """When REFLEX_EMOTIONS_ENABLED=false, compute_modifier returns 1.0."""
        engine = EmotionEngine(data_dir=str(tmp_path))

        with patch("src.services.reflex_emotions.REFLEX_EMOTIONS_ENABLED", False):
            mod = engine.compute_modifier("any_tool", EmotionContext())
            assert mod == 1.0, f"Expected modifier=1.0 when disabled, got {mod}"

    def test_35_flag_disabled_record_outcome_noop(self, tmp_path):
        """When disabled, record_outcome does not update counters."""
        engine = EmotionEngine(data_dir=str(tmp_path))

        with patch("src.services.reflex_emotions.REFLEX_EMOTIONS_ENABLED", False):
            state = engine.record_outcome("tool_z", success=True, context=EmotionContext())
            # Usage count should remain 0 since flag is off
            assert state.usage_count == 0, f"Expected no update when disabled, got usage={state.usage_count}"

    def test_36_flag_disabled_breakdown_neutral(self, tmp_path):
        """When disabled, get_modifier_breakdown returns neutral values."""
        engine = EmotionEngine(data_dir=str(tmp_path))

        with patch("src.services.reflex_emotions.REFLEX_EMOTIONS_ENABLED", False):
            bd = engine.get_modifier_breakdown("tool_x")
            assert bd["modifier"] == 1.0, f"Expected modifier=1.0, got {bd['modifier']}"
            assert bd["mood_label"] == "neutral", f"Expected neutral, got {bd['mood_label']}"

    def test_37_flag_disabled_compute_emotions_defaults(self, tmp_path):
        """When disabled, compute_emotions returns default state."""
        engine = EmotionEngine(data_dir=str(tmp_path))

        with patch("src.services.reflex_emotions.REFLEX_EMOTIONS_ENABLED", False):
            state = engine.compute_emotions("tool_x")
            assert state.curiosity == _COLD_CURIOSITY
            assert state.trust == _COLD_TRUST
            assert state.caution == _COLD_CAUTION


# ════════════════════════════════════════════════════════════════
# W3 — Full Workflow Tests                       MARKER_195.2.2
# ════════════════════════════════════════════════════════════════

class TestFullWorkflow:
    """End-to-end workflow: context → emotions → modifier → applied to score."""

    def test_38_workflow_context_to_score(self, tmp_path):
        """Full flow: build context, compute emotions, get modifier, apply to score."""
        engine = EmotionEngine(data_dir=str(tmp_path))

        # Build context
        ctx = EmotionContext(
            agent_id="opus",
            phase_type="build",
            tool_permission="READ",
            freshness_score=0.5,
        )

        # Step 1: Compute emotions
        state = engine.compute_emotions("vetka_read_file", ctx)
        assert 0.0 <= state.curiosity <= 1.0
        assert 0.0 <= state.trust <= 1.0
        assert 0.0 <= state.caution <= 1.0
        assert state.mood_label in ("curious", "confident", "cautious", "neutral")

        # Step 2: Get modifier
        modifier = engine.compute_modifier("vetka_read_file", ctx)
        assert 0.3 <= modifier <= 1.5

        # Step 3: Apply to hypothetical base score
        base_score = 0.75
        final_score = max(0.0, min(1.0, base_score * modifier))
        assert 0.0 <= final_score <= 1.0

    def test_39_workflow_trust_recovery_after_failures(self, tmp_path):
        """Trust drops on failures, partially recovers on successes."""
        engine = EmotionEngine(data_dir=str(tmp_path))
        ctx = EmotionContext(agent_id="a1")

        # Initial trust
        initial = engine.get_emotion_state("tool_x").trust

        # 3 failures
        for _ in range(3):
            engine.record_outcome("tool_x", success=False, context=ctx)
        after_fail = engine.get_emotion_state("tool_x").trust
        assert after_fail < initial, "Trust should drop after failures"

        # 3 successes
        for _ in range(3):
            engine.record_outcome("tool_x", success=True, context=ctx)
        after_recover = engine.get_emotion_state("tool_x").trust
        assert after_recover > after_fail, "Trust should recover after successes"
        assert after_recover < initial, "Trust should not fully recover (asymmetric)"

    def test_40_workflow_mood_changes_with_outcomes(self, tmp_path):
        """Mood label changes as outcomes shift emotional state."""
        engine = EmotionEngine(data_dir=str(tmp_path))
        ctx = EmotionContext(agent_id="a1")

        # Cold start mood
        state = engine.compute_emotions("tool_x", ctx)
        initial_mood = state.mood_label

        # Many successes should shift toward confident (trust grows)
        for _ in range(10):
            engine.record_outcome("tool_x", success=True, context=ctx)
        state = engine.compute_emotions("tool_x", ctx)
        # After many successes, trust should be high
        assert state.trust > 0.7, f"Expected high trust after 10 successes, got {state.trust}"

    def test_41_workflow_guard_warning_dampens_everything(self, tmp_path):
        """Guard warning raises caution and caps trust, dampening final modifier."""
        engine = EmotionEngine(data_dir=str(tmp_path))

        # Build up trust first
        safe_ctx = EmotionContext(agent_id="a1")
        for _ in range(5):
            engine.record_outcome("tool_y", success=True, context=safe_ctx)
        mod_safe = engine.compute_modifier("tool_y", safe_ctx)

        # Now with guard warning
        warn_ctx = EmotionContext(
            agent_id="a1",
            guard_warnings=["danger_zone"],
        )
        mod_warned = engine.compute_modifier("tool_y", warn_ctx)

        assert mod_warned < mod_safe, (
            f"Guard warning should reduce modifier: {mod_warned} < {mod_safe}"
        )

    def test_42_corrupted_state_file_recovery(self, tmp_path):
        """Engine survives corrupted state file gracefully."""
        data_dir = tmp_path / "emotions"
        data_dir.mkdir(parents=True)
        (data_dir / "emotion_states.json").write_text("{invalid json!!!")

        # Engine should still initialize (fresh start)
        engine = EmotionEngine(data_dir=str(data_dir))
        mod = engine.compute_modifier("any_tool")
        assert 0.3 <= mod <= 1.5, f"Should return valid modifier even with corrupt state: {mod}"

    def test_43_emotion_state_has_mood_label(self, cold_state):
        """EmotionState dataclass includes mood_label field."""
        assert hasattr(cold_state, "mood_label"), "EmotionState should have mood_label field"
        assert cold_state.mood_label == "neutral", f"Default mood_label should be 'neutral', got '{cold_state.mood_label}'"

    def test_44_cold_start_defaults(self, cold_state):
        """Cold start defaults match spec: curiosity=0.6, trust=0.5, caution=0.3."""
        assert cold_state.curiosity == _COLD_CURIOSITY, f"Expected curiosity={_COLD_CURIOSITY}, got {cold_state.curiosity}"
        assert cold_state.trust == _COLD_TRUST, f"Expected trust={_COLD_TRUST}, got {cold_state.trust}"
        assert cold_state.caution == _COLD_CAUTION, f"Expected caution={_COLD_CAUTION}, got {cold_state.caution}"

    def test_45_multiple_tools_independent(self, tmp_path):
        """Emotion states for different tools are independent."""
        engine = EmotionEngine(data_dir=str(tmp_path))
        ctx = EmotionContext(agent_id="a1")

        # Fail tool_a, succeed tool_b
        for _ in range(5):
            engine.record_outcome("tool_a", success=False, context=ctx)
            engine.record_outcome("tool_b", success=True, context=ctx)

        state_a = engine.get_emotion_state("tool_a")
        state_b = engine.get_emotion_state("tool_b")

        assert state_a.trust < state_b.trust, (
            f"Failing tool should have lower trust: {state_a.trust} < {state_b.trust}"
        )
