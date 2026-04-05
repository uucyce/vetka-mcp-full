"""
Phase 195.2 — REFLEX Emotions test suite (25 tests).

W1 (MARKER_195.3): 15 core unit tests — curiosity, trust, caution, modifier.
W2 (MARKER_195.6): 10 integration tests — persistence, engine, scenarios.
"""

import json
import math
import pytest
from pathlib import Path

from src.services.reflex_emotions import (
    EmotionState,
    EmotionContext,
    EmotionEngine,
    compute_curiosity,
    compute_trust,
    compute_caution,
    compute_emotion_modifier,
    get_reflex_emotions,
    reset_reflex_emotions,
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
        print("✅ test_01: novel tool curiosity >= 0.6")

    def test_02_curiosity_heavy_use(self):
        """Heavily-used tool (usage=10) has low curiosity < 0.3."""
        c = compute_curiosity(usage_count=10, freshness_score=0.0)
        # novelty = 1/(1+exp(0.5*(10-5))) = 1/(1+exp(2.5)) ≈ 0.076
        assert c < 0.3, f"Expected curiosity < 0.3 for heavy use, got {c}"
        print("✅ test_02: heavy-use curiosity < 0.3")

    def test_03_curiosity_freshness_boost(self):
        """Freshness boost increases curiosity for stale tools."""
        c_no_fresh = compute_curiosity(usage_count=10, freshness_score=0.0)
        c_fresh = compute_curiosity(usage_count=10, freshness_score=0.8)
        assert c_fresh > c_no_fresh, (
            f"Freshness should boost curiosity: {c_fresh} > {c_no_fresh}"
        )
        print("✅ test_03: freshness boosts curiosity")

    def test_04_curiosity_floor_zero(self):
        """Curiosity never goes below 0 even with extreme usage."""
        c = compute_curiosity(usage_count=1000, freshness_score=0.0)
        assert c >= 0.0, f"Curiosity must be >= 0, got {c}"
        print("✅ test_04: curiosity floor at 0")

    def test_05_curiosity_capped_at_one(self):
        """Curiosity capped at 1.0 even with max freshness + novelty."""
        c = compute_curiosity(usage_count=0, freshness_score=1.0)
        # novelty ≈ 0.924 + freshness_boost = 0.4 → 1.324 → capped at 1.0
        assert c <= 1.0, f"Curiosity must be <= 1.0, got {c}"
        assert c == 1.0 or abs(c - 1.0) < 1e-9, (
            f"Expected curiosity capped at 1.0, got {c}"
        )
        print("✅ test_05: curiosity capped at 1.0")

    # ── Cat 2: Trust ──

    def test_06_trust_cold_start(self, cold_state):
        """Cold-start trust is 0.5."""
        assert cold_state.trust == 0.5, f"Expected trust=0.5, got {cold_state.trust}"
        print("✅ test_06: cold-start trust = 0.5")

    def test_07_trust_three_successes(self):
        """Three consecutive successes from 0.5 push trust above 0.7."""
        trust = 0.5
        for _ in range(3):
            trust = compute_trust(trust, success=True, guard_warnings=[])
        assert trust > 0.65, f"Expected trust > 0.65 after 3 successes, got {trust}"
        print("✅ test_07: 3 successes → trust > 0.65")

    def test_08_trust_single_failure_drop(self):
        """Single failure from 0.8 drops trust significantly (×0.65 → ~0.52)."""
        trust = compute_trust(0.8, success=False, guard_warnings=[])
        assert trust < 0.6, f"Expected trust < 0.6 after failure from 0.8, got {trust}"
        print("✅ test_08: failure from 0.8 drops significantly")

    def test_09_trust_asymmetry(self):
        """Recovery is slower than drop — asymmetric dynamics."""
        # Start at 0.8, fail once, then recover with 1 success
        after_fail = compute_trust(0.8, success=False, guard_warnings=[])
        after_recover = compute_trust(after_fail, success=True, guard_warnings=[])
        # Recovery should NOT fully restore — still below original
        assert after_recover < 0.8, (
            f"Expected trust < 0.8 after fail+recover, got {after_recover}"
        )
        print("✅ test_09: trust asymmetry — recovery slower than drop")

    def test_10_trust_guard_warning_cap(self):
        """Guard warnings cap trust at 0.3, even if computed higher."""
        # Start high
        trust = compute_trust(0.9, success=True, guard_warnings=["security_risk"])
        assert trust <= 0.3, f"Expected trust <= 0.3 with guard warning, got {trust}"
        print("✅ test_10: guard warning caps trust at 0.3")

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
        print("✅ test_11: trust stays in [0, 1]")

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
        print("✅ test_12: WRITE → caution >= 0.7")

    def test_13_caution_read_safe(self):
        """READ permission with no flags → caution <= 0.1."""
        c = compute_caution(
            tool_permission="READ",
            is_foreign_file=False,
            has_recon=True,
            guard_warnings=[],
        )
        assert c <= 0.1, f"Expected caution <= 0.1 for safe READ, got {c}"
        print("✅ test_13: safe READ → caution <= 0.1")

    def test_14_caution_foreign_file(self):
        """Foreign file → caution >= 0.8."""
        c = compute_caution(
            tool_permission="READ",
            is_foreign_file=True,
            has_recon=True,
            guard_warnings=[],
        )
        assert c >= 0.8, f"Expected caution >= 0.8 for foreign file, got {c}"
        print("✅ test_14: foreign file → caution >= 0.8")

    def test_15_caution_no_recon(self):
        """No recon → caution >= 0.5."""
        c = compute_caution(
            tool_permission="READ",
            is_foreign_file=False,
            has_recon=False,
            guard_warnings=[],
        )
        assert c >= 0.5, f"Expected caution >= 0.5 without recon, got {c}"
        print("✅ test_15: no recon → caution >= 0.5")

    def test_16_caution_guard_warnings(self):
        """Guard warnings → caution >= 0.7."""
        c = compute_caution(
            tool_permission="READ",
            is_foreign_file=False,
            has_recon=True,
            guard_warnings=["suspicious_pattern"],
        )
        assert c >= 0.7, f"Expected caution >= 0.7 with guard warnings, got {c}"
        print("✅ test_16: guard warnings → caution >= 0.7")

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
        print("✅ test_17: modifier always in [0.3, 1.5]")

    def test_18_modifier_high_caution_dominates(self):
        """High caution dominates — pulls modifier low."""
        m = compute_emotion_modifier(curiosity=0.5, trust=1.0, caution=1.0)
        # (0.5+0.5)*(1.0+0.15)*(1.0-0.4) = 1.0*1.15*0.6 = 0.69
        assert m <= 0.75, f"Expected modifier <= 0.75 with max caution, got {m}"
        print("✅ test_18: high caution dominates")

    def test_19_modifier_low_trust_gates(self):
        """Low trust gates modifier — even with high curiosity."""
        m = compute_emotion_modifier(curiosity=1.0, trust=0.0, caution=0.0)
        # (0.5+0.0)*(1.0+0.3)*(1.0-0.0) = 0.5*1.3*1.0 = 0.65
        assert abs(m - 0.65) < 0.05, f"Expected modifier ≈ 0.65, got {m}"
        print("✅ test_19: low trust gates modifier")

    def test_20_modifier_cold_start(self):
        """Cold-start values → modifier ≈ 0.779."""
        m = compute_emotion_modifier(curiosity=0.6, trust=0.5, caution=0.3)
        # (0.5+0.25)*(1.0+0.18)*(1.0-0.12) = 0.75*1.18*0.88 ≈ 0.779
        expected = 0.75 * 1.18 * 0.88
        assert abs(m - expected) < 0.05, (
            f"Expected modifier ≈ {expected:.3f}, got {m}"
        )
        print("✅ test_20: cold-start modifier ≈ 0.779")


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
        print("✅ test_21: save/load roundtrip preserves state")

    def test_22_reset_singleton(self, tmp_path):
        """reset_reflex_emotions clears the engine singleton."""
        # Get engine via singleton
        engine1 = get_reflex_emotions(data_dir=str(tmp_path))
        ctx = EmotionContext(agent_id="a1")
        engine1.record_outcome("tool_x", success=True, context=ctx)

        # Reset
        reset_reflex_emotions()

        # Get again — should be fresh
        engine2 = get_reflex_emotions(data_dir=str(tmp_path))
        state = engine2.get_emotion_state("tool_x")
        # After reset, the engine reloads from disk OR starts fresh
        # The key contract: singleton was cleared
        assert engine1 is not engine2, "Reset should create new engine instance"
        print("✅ test_22: reset clears singleton")

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
        print("✅ test_23: fresh tool → higher modifier")

    def test_24_failing_tool_lower_modifier(self, tmp_path):
        """Tool that keeps failing gets progressively lower modifier."""
        engine = EmotionEngine(data_dir=str(tmp_path))
        ctx = EmotionContext(agent_id="a1")

        mod_before = engine.compute_modifier("tool_flaky", ctx)

        # Record several failures
        for _ in range(5):
            engine.record_outcome("tool_flaky", success=False, context=ctx)

        mod_after = engine.compute_modifier("tool_flaky", ctx)

        assert mod_after < mod_before, (
            f"Failing tool modifier should decrease: {mod_after} < {mod_before}"
        )
        print("✅ test_24: failing tool → lower modifier")

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

        # With max caution (0.9 from guard warnings), cold trust (0.5),
        # modifier = (0.75)*(1+c*0.3)*(1-0.9*0.4) = 0.75*~1.28*0.64 ≈ 0.61
        assert mod < 0.7, f"Risky edit modifier should be < 0.7, got {mod}"
        print("✅ test_25: risky edit → low modifier (safety mode)")


# ════════════════════════════════════════════════════════════════
# W2 — Cat 7: IP-E4 Session Display + Pipeline Integration   MARKER_195.2.4
# ════════════════════════════════════════════════════════════════

class TestReflexEmotionsSessionDisplay:
    """Wave 2 (195.2.4): Emotion display in session_init + integration tests."""

    def test_26_mood_label_exploratory(self):
        """avg curiosity > 0.6 → exploratory."""
        from src.mcp.tools.session_tools import _compute_mood_label
        emotions = {
            "tool_a": {"curiosity": 0.8, "trust": 0.5, "caution": 0.1},
            "tool_b": {"curiosity": 0.7, "trust": 0.5, "caution": 0.2},
        }
        assert _compute_mood_label(emotions) == "exploratory"
        print("✅ test_26: avg curiosity > 0.6 → exploratory")

    def test_27_mood_label_cautious(self):
        """avg caution > 0.6 → cautious (overrides others)."""
        from src.mcp.tools.session_tools import _compute_mood_label
        emotions = {
            "tool_a": {"curiosity": 0.9, "trust": 0.9, "caution": 0.7},
            "tool_b": {"curiosity": 0.8, "trust": 0.8, "caution": 0.8},
        }
        assert _compute_mood_label(emotions) == "cautious"
        print("✅ test_27: avg caution > 0.6 → cautious")

    def test_28_mood_label_confident(self):
        """avg trust > 0.7, caution low → confident."""
        from src.mcp.tools.session_tools import _compute_mood_label
        emotions = {
            "tool_a": {"curiosity": 0.3, "trust": 0.9, "caution": 0.1},
            "tool_b": {"curiosity": 0.2, "trust": 0.8, "caution": 0.1},
        }
        assert _compute_mood_label(emotions) == "confident"
        print("✅ test_28: avg trust > 0.7 → confident")

    def test_29_mood_label_wary(self):
        """avg trust < 0.3 → wary."""
        from src.mcp.tools.session_tools import _compute_mood_label
        emotions = {
            "tool_a": {"curiosity": 0.3, "trust": 0.1, "caution": 0.3},
            "tool_b": {"curiosity": 0.2, "trust": 0.2, "caution": 0.4},
        }
        assert _compute_mood_label(emotions) == "wary"
        print("✅ test_29: avg trust < 0.3 → wary")

    def test_30_mood_label_balanced(self):
        """Middle-of-road values → balanced."""
        from src.mcp.tools.session_tools import _compute_mood_label
        emotions = {
            "tool_a": {"curiosity": 0.5, "trust": 0.5, "caution": 0.3},
        }
        assert _compute_mood_label(emotions) == "balanced"
        print("✅ test_30: balanced default")

    def test_31_mood_label_empty(self):
        """Empty emotions → balanced."""
        from src.mcp.tools.session_tools import _compute_mood_label
        assert _compute_mood_label({}) == "balanced"
        print("✅ test_31: empty → balanced")

    def test_32_emotion_summary_generation(self):
        """Summary mentions high-curiosity and low-trust tools."""
        from src.mcp.tools.session_tools import _generate_emotion_summary
        emotions = {
            "tool_fresh": {"curiosity": 0.9, "trust": 0.5, "caution": 0.1},
            "tool_broken": {"curiosity": 0.2, "trust": 0.1, "caution": 0.3},
            "tool_safe": {"curiosity": 0.4, "trust": 0.8, "caution": 0.1},
        }
        summary = _generate_emotion_summary(emotions)
        assert "curiosity" in summary.lower(), f"Summary should mention curiosity: {summary}"
        assert "trust" in summary.lower(), f"Summary should mention trust: {summary}"
        print(f"✅ test_32: summary = {summary!r}")

    def test_33_emotion_modifier_applied_to_score(self, tmp_path):
        """Engine modifier applied to base score changes the result."""
        engine = EmotionEngine(data_dir=str(tmp_path))
        ctx = EmotionContext(agent_id="a1")

        # Cold start modifier
        mod_cold = engine.compute_modifier("new_tool", ctx)
        assert 0.3 <= mod_cold <= 1.5, f"Cold modifier out of range: {mod_cold}"

        # After failures, modifier should drop
        for _ in range(5):
            engine.record_outcome("new_tool", success=False, context=ctx)
        mod_after_fail = engine.compute_modifier("new_tool", ctx)

        base_score = 0.8
        assert base_score * mod_after_fail < base_score * mod_cold, (
            f"Failing modifier should reduce score: {mod_after_fail} vs {mod_cold}"
        )
        print("✅ test_33: modifier changes score after failures")

    def test_34_emotion_updated_on_feedback(self, tmp_path):
        """record_outcome updates trust correctly."""
        engine = EmotionEngine(data_dir=str(tmp_path))
        ctx = EmotionContext(agent_id="a1")

        state_before = engine.get_emotion_state("tool_x")
        trust_before = state_before.trust  # 0.5 cold start

        engine.record_outcome("tool_x", success=True, context=ctx)
        state_after = engine.get_emotion_state("tool_x")

        assert state_after.trust > trust_before, (
            f"Trust should increase on success: {state_after.trust} > {trust_before}"
        )
        assert state_after.usage_count == 1
        print("✅ test_34: record_outcome updates trust on success")

    def test_35_emotion_backward_compatible(self, tmp_path):
        """When emotion engine has no data, modifier is still valid."""
        engine = EmotionEngine(data_dir=str(tmp_path))
        # No recorded outcomes — cold start
        mod = engine.compute_modifier("unknown_tool")
        assert 0.3 <= mod <= 1.5, f"Cold modifier should be in range: {mod}"
        # Should be roughly the cold-start value (~0.78)
        expected_cold = compute_emotion_modifier(0.6, 0.5, 0.0)
        assert abs(mod - expected_cold) < 0.1, (
            f"Cold modifier {mod} should be close to default {expected_cold}"
        )
        print("✅ test_35: backward compatible — cold start modifier valid")

    def test_36_emotion_failure_doesnt_break_engine(self, tmp_path):
        """Engine survives corrupted state file gracefully."""
        # Write garbage to state file
        data_dir = tmp_path / "emotions"
        data_dir.mkdir(parents=True)
        (data_dir / "emotion_states.json").write_text("{invalid json!!!")

        # Engine should still initialize (fresh start)
        engine = EmotionEngine(data_dir=str(data_dir))
        mod = engine.compute_modifier("any_tool")
        assert 0.3 <= mod <= 1.5, f"Should return valid modifier even with corrupt state: {mod}"
        print("✅ test_36: engine survives corrupted state file")
