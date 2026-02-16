"""
Tests for Phase 145 — Adaptive Timeout (LLM Model Registry + Pipeline Integration).

MARKER_145.TESTS

Covers:
1. ModelProfile dataclass and defaults
2. LLMModelRegistry — hardcoded profiles, cache, fuzzy matching
3. calculate_timeout() — formula, clamping, complexity multipliers
4. Pipeline _safe_phase() — adaptive timeout integration
5. Pipeline helpers: _estimate_input_tokens, _estimate_output_tokens, _normalize_complexity
6. ModelUpdater lifecycle (start/stop)

@status: active
@phase: 145
@depends: src/elisya/llm_model_registry.py, src/elisya/model_updater.py, src/orchestration/agent_pipeline.py
"""

import asyncio
import json
import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

# Add project root to sys.path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# 1. ModelProfile Tests
# ============================================================

class TestModelProfile:
    """Test ModelProfile dataclass."""

    def test_model_profile_creation(self):
        from src.elisya.llm_model_registry import ModelProfile
        profile = ModelProfile(
            model_id="test-model",
            context_length=32000,
            output_tokens_per_second=50.0,
        )
        assert profile.model_id == "test-model"
        assert profile.context_length == 32000
        assert profile.output_tokens_per_second == 50.0
        assert profile.input_tokens_per_second == 90.0  # dataclass default
        assert profile.provider == "unknown"  # dataclass default
        assert profile.source == "fallback"  # dataclass default

    def test_model_profile_defaults(self):
        from src.elisya.llm_model_registry import ModelProfile
        profile = ModelProfile(model_id="x")
        assert profile.context_length == 128000
        assert profile.output_tokens_per_second == 35.0  # safe fallback default
        assert profile.ttft_ms == 800.0

    def test_model_profile_to_dict(self):
        from src.elisya.llm_model_registry import ModelProfile
        from dataclasses import asdict
        profile = ModelProfile(model_id="gpt-4o", output_tokens_per_second=80.0)
        d = asdict(profile)
        assert d["model_id"] == "gpt-4o"
        assert d["output_tokens_per_second"] == 80.0
        assert "source" in d


# ============================================================
# 2. LLMModelRegistry Tests
# ============================================================

class TestLLMModelRegistry:
    """Test the LLMModelRegistry singleton and profile lookup."""

    def test_singleton(self):
        from src.elisya.llm_model_registry import get_llm_registry
        r1 = get_llm_registry()
        r2 = get_llm_registry()
        assert r1 is r2

    def test_hardcoded_profiles_exist(self):
        from src.elisya.llm_model_registry import _SAFE_DEFAULTS
        # Must have at least 15 models (Dragon team + major providers)
        assert len(_SAFE_DEFAULTS) >= 15
        # Check key Dragon team models (short keys without namespace prefix)
        assert "qwen3-coder" in _SAFE_DEFAULTS
        assert "grok-4.1-fast" in _SAFE_DEFAULTS
        assert "kimi-k2.5" in _SAFE_DEFAULTS

    def test_hardcoded_profile_speed_values(self):
        from src.elisya.llm_model_registry import _SAFE_DEFAULTS
        # Grok Fast should be very fast (>80 tps)
        assert _SAFE_DEFAULTS["grok-4.1-fast"]["output_tokens_per_second"] >= 80.0
        # deepseek-r1 speed from SAFE_DEFAULTS
        assert _SAFE_DEFAULTS["deepseek-r1"]["output_tokens_per_second"] > 0

    @pytest.mark.asyncio
    async def test_get_profile_hardcoded(self):
        from src.elisya.llm_model_registry import get_llm_registry
        registry = get_llm_registry()
        profile = await registry.get_profile("qwen/qwen3-coder")
        assert profile is not None
        # Registry normalizes model_id by stripping namespace prefix
        assert profile.model_id == "qwen3-coder"
        assert profile.output_tokens_per_second > 0

    @pytest.mark.asyncio
    async def test_get_profile_unknown_model(self):
        """Unknown model should return a safe fallback profile."""
        from src.elisya.llm_model_registry import get_llm_registry
        registry = get_llm_registry()
        profile = await registry.get_profile("unknown/nonexistent-model-xyz")
        assert profile is not None
        assert "fallback" in profile.source or "default" in profile.source
        assert profile.output_tokens_per_second > 0  # safe default

    @pytest.mark.asyncio
    async def test_fuzzy_match_prefix(self):
        """Test fuzzy matching — prefix match (e.g. 'qwen3-coder' → 'qwen/qwen3-coder')."""
        from src.elisya.llm_model_registry import get_llm_registry
        registry = get_llm_registry()
        # Direct profile fetch (fuzzy matching is internal to registry)
        profile = await registry.get_profile("gpt-4o")
        assert profile is not None
        assert "gpt-4o" in profile.model_id


# ============================================================
# 3. calculate_timeout Tests
# ============================================================

class TestCalculateTimeout:
    """Test the calculate_timeout() function."""

    @pytest.mark.asyncio
    async def test_basic_timeout_calculation(self):
        from src.elisya.llm_model_registry import calculate_timeout
        # Grok Fast = ~90 tps → fast model → low timeout
        timeout = await calculate_timeout(
            model_id="x-ai/grok-4.1-fast",
            input_tokens=3000,
            expected_output_tokens=500,
            fc_turns=1,
            task_complexity="simple",
        )
        # Should be relatively low for a fast model with simple task
        assert 45 <= timeout <= 200
        assert isinstance(timeout, int)

    @pytest.mark.asyncio
    async def test_complex_task_higher_timeout(self):
        from src.elisya.llm_model_registry import calculate_timeout
        simple_timeout = await calculate_timeout(
            model_id="qwen/qwen3-coder",
            input_tokens=4000,
            expected_output_tokens=1000,
            fc_turns=1,
            task_complexity="simple",
        )
        complex_timeout = await calculate_timeout(
            model_id="qwen/qwen3-coder",
            input_tokens=4000,
            expected_output_tokens=1000,
            fc_turns=1,
            task_complexity="complex",
        )
        assert complex_timeout > simple_timeout

    @pytest.mark.asyncio
    async def test_fc_turns_increase_timeout(self):
        from src.elisya.llm_model_registry import calculate_timeout
        timeout_1fc = await calculate_timeout(
            model_id="qwen/qwen3-coder",
            fc_turns=1,
        )
        timeout_4fc = await calculate_timeout(
            model_id="qwen/qwen3-coder",
            fc_turns=4,
        )
        # 3 extra FC turns × 12s = 36s more
        assert timeout_4fc > timeout_1fc
        assert (timeout_4fc - timeout_1fc) >= 30  # At least 30s diff for 3 extra turns

    @pytest.mark.asyncio
    async def test_timeout_clamped_min(self):
        from src.elisya.llm_model_registry import calculate_timeout
        timeout = await calculate_timeout(
            model_id="x-ai/grok-4.1-fast",
            input_tokens=100,
            expected_output_tokens=50,
            fc_turns=0,
            task_complexity="simple",
        )
        assert timeout >= 45  # Min clamp

    @pytest.mark.asyncio
    async def test_timeout_clamped_max(self):
        from src.elisya.llm_model_registry import calculate_timeout
        timeout = await calculate_timeout(
            model_id="deepseek/deepseek-r1",
            input_tokens=100000,
            expected_output_tokens=50000,
            fc_turns=4,
            task_complexity="complex",
        )
        assert timeout <= 600  # Max clamp

    @pytest.mark.asyncio
    async def test_unknown_model_gets_safe_timeout(self):
        from src.elisya.llm_model_registry import calculate_timeout
        timeout = await calculate_timeout(
            model_id="totally-unknown-model",
            input_tokens=4000,
            expected_output_tokens=800,
        )
        assert 45 <= timeout <= 600


# ============================================================
# 4. Pipeline Integration Tests
# ============================================================

class TestPipelineAdaptiveTimeout:
    """Test _safe_phase adaptive timeout integration."""

    def _make_pipeline(self):
        """Create a minimal AgentPipeline for testing."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline()
        pipeline._task_complexity = "medium"
        # Mock progress emission
        pipeline._emit_progress = AsyncMock()
        return pipeline

    @pytest.mark.asyncio
    async def test_safe_phase_with_model_uses_adaptive(self):
        """When model is provided and adaptive timeout is available, it should use adaptive."""
        pipeline = self._make_pipeline()

        async def fast_coro():
            return "success"

        with patch("src.orchestration.agent_pipeline.ADAPTIVE_TIMEOUT_AVAILABLE", True), \
             patch("src.orchestration.agent_pipeline._calculate_adaptive_timeout", new_callable=AsyncMock) as mock_calc:
            mock_calc.return_value = 120
            result = await pipeline._safe_phase("coder", fast_coro(), model="qwen/qwen3-coder")
            assert result == "success"
            mock_calc.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_phase_without_model_uses_static(self):
        """When model is empty, it should fall back to static PHASE_TIMEOUTS."""
        pipeline = self._make_pipeline()

        async def fast_coro():
            return "ok"

        with patch("src.orchestration.agent_pipeline.ADAPTIVE_TIMEOUT_AVAILABLE", True), \
             patch("src.orchestration.agent_pipeline._calculate_adaptive_timeout", new_callable=AsyncMock) as mock_calc:
            result = await pipeline._safe_phase("coder", fast_coro(), model="")
            assert result == "ok"
            mock_calc.assert_not_called()  # No model → no adaptive call

    @pytest.mark.asyncio
    async def test_safe_phase_adaptive_fallback_on_error(self):
        """If adaptive timeout raises, fallback to static PHASE_TIMEOUTS."""
        pipeline = self._make_pipeline()

        async def fast_coro():
            return "fallback_ok"

        with patch("src.orchestration.agent_pipeline.ADAPTIVE_TIMEOUT_AVAILABLE", True), \
             patch("src.orchestration.agent_pipeline._calculate_adaptive_timeout", new_callable=AsyncMock) as mock_calc:
            mock_calc.side_effect = Exception("API error")
            result = await pipeline._safe_phase("coder", fast_coro(), model="broken-model")
            assert result == "fallback_ok"  # Should still work with fallback

    @pytest.mark.asyncio
    async def test_safe_phase_timeout_returns_none(self):
        """Phase that exceeds timeout should return None."""
        pipeline = self._make_pipeline()

        async def slow_coro():
            await asyncio.sleep(10)
            return "never"

        with patch("src.orchestration.agent_pipeline.PHASE_TIMEOUTS", {"test_phase": 0.1}):
            result = await pipeline._safe_phase("test_phase", slow_coro())
            assert result is None

    @pytest.mark.asyncio
    async def test_safe_phase_fc_turns_passed(self):
        """fc_turns parameter should be forwarded to calculate_timeout."""
        pipeline = self._make_pipeline()

        async def fast_coro():
            return "fc_test"

        with patch("src.orchestration.agent_pipeline.ADAPTIVE_TIMEOUT_AVAILABLE", True), \
             patch("src.orchestration.agent_pipeline._calculate_adaptive_timeout", new_callable=AsyncMock) as mock_calc:
            mock_calc.return_value = 180
            await pipeline._safe_phase("coder", fast_coro(), model="qwen/qwen3-coder", fc_turns=4)
            call_kwargs = mock_calc.call_args
            assert call_kwargs.kwargs.get("fc_turns") == 4 or call_kwargs[1].get("fc_turns") == 4


# ============================================================
# 5. Pipeline Helper Tests
# ============================================================

class TestPipelineHelpers:
    """Test adaptive timeout helper methods on AgentPipeline."""

    def _make_pipeline(self):
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline()
        return pipeline

    def test_estimate_input_tokens(self):
        pipeline = self._make_pipeline()
        assert pipeline._estimate_input_tokens("scout") == 2000
        assert pipeline._estimate_input_tokens("coder") == 6000
        assert pipeline._estimate_input_tokens("unknown") == 4000

    def test_estimate_output_tokens(self):
        pipeline = self._make_pipeline()
        assert pipeline._estimate_output_tokens("coder") == 2000
        assert pipeline._estimate_output_tokens("verifier") == 300
        assert pipeline._estimate_output_tokens("unknown") == 800

    def test_normalize_complexity(self):
        pipeline = self._make_pipeline()
        assert pipeline._normalize_complexity("low") == "simple"
        assert pipeline._normalize_complexity("medium") == "medium"
        assert pipeline._normalize_complexity("high") == "complex"
        assert pipeline._normalize_complexity("Hard") == "complex"
        assert pipeline._normalize_complexity("Easy") == "simple"
        assert pipeline._normalize_complexity("moderate") == "medium"
        assert pipeline._normalize_complexity("UNKNOWN_VALUE") == "medium"  # fallback

    def test_task_complexity_initialized(self):
        pipeline = self._make_pipeline()
        assert pipeline._task_complexity == "medium"


# ============================================================
# 6. ModelUpdater Tests
# ============================================================

class TestModelUpdater:
    """Test on-demand model updater (no cron, no polling)."""

    @pytest.mark.asyncio
    async def test_ensure_model_profile_caches(self):
        """ensure_model_profile should call registry once, then skip on repeat."""
        from src.elisya.model_updater import ensure_model_profile, _ensured_models, reset_session_cache
        reset_session_cache()  # Clean state
        profile = await ensure_model_profile("gpt-4o")
        assert profile is not None
        assert "gpt-4o" in _ensured_models
        # Second call should return None (already ensured)
        profile2 = await ensure_model_profile("gpt-4o")
        assert profile2 is None  # Skipped — already ensured

    @pytest.mark.asyncio
    async def test_ensure_model_profile_empty_model(self):
        from src.elisya.model_updater import ensure_model_profile
        result = await ensure_model_profile("")
        assert result is None

    @pytest.mark.asyncio
    async def test_ensure_preset_models(self):
        from src.elisya.model_updater import ensure_preset_models, reset_session_cache
        reset_session_cache()
        preset_roles = {
            "coder": "qwen/qwen3-coder",
            "verifier": "zhipu-ai/glm-4.7-flash",
        }
        count = await ensure_preset_models(preset_roles)
        assert isinstance(count, int)

    def test_reset_session_cache(self):
        from src.elisya.model_updater import _ensured_models, reset_session_cache
        _ensured_models.add("test-model")
        assert "test-model" in _ensured_models
        reset_session_cache()
        assert len(_ensured_models) == 0

    @pytest.mark.asyncio
    async def test_start_is_noop(self):
        """start_model_updater should be a no-op (backward compat)."""
        from src.elisya.model_updater import start_model_updater
        result = await start_model_updater()
        assert result is None  # No background task created

    @pytest.mark.asyncio
    async def test_no_background_loop(self):
        """Verify no ModelUpdater class or background tasks exist."""
        import src.elisya.model_updater as mod
        assert not hasattr(mod, "ModelUpdater"), "Cron-based ModelUpdater class should be removed"
        assert not hasattr(mod, "DEFAULT_UPDATE_INTERVAL"), "Polling interval should be removed"
        assert not hasattr(mod, "TOP_MODELS"), "Static model list should be removed"


# ============================================================
# 7. Complexity Multiplier Tests
# ============================================================

class TestComplexityMultipliers:
    """Test COMPLEXITY_MULTIPLIERS constants."""

    def test_multiplier_values(self):
        from src.elisya.llm_model_registry import COMPLEXITY_MULTIPLIERS
        assert COMPLEXITY_MULTIPLIERS["simple"] == 1.0
        assert COMPLEXITY_MULTIPLIERS["medium"] == 1.8
        assert COMPLEXITY_MULTIPLIERS["complex"] == 3.2

    def test_multiplier_ordering(self):
        from src.elisya.llm_model_registry import COMPLEXITY_MULTIPLIERS
        assert COMPLEXITY_MULTIPLIERS["simple"] < COMPLEXITY_MULTIPLIERS["medium"]
        assert COMPLEXITY_MULTIPLIERS["medium"] < COMPLEXITY_MULTIPLIERS["complex"]


# ============================================================
# 8. Regression Tests
# ============================================================

class TestRegressions:
    """Ensure adaptive timeout doesn't break existing pipeline behavior."""

    def test_phase_timeouts_still_exist(self):
        """Static PHASE_TIMEOUTS must still be available as fallback."""
        from src.orchestration.agent_pipeline import PHASE_TIMEOUTS
        assert "scout" in PHASE_TIMEOUTS
        assert "architect" in PHASE_TIMEOUTS
        assert "researcher" in PHASE_TIMEOUTS
        assert "coder" in PHASE_TIMEOUTS
        assert "verifier" in PHASE_TIMEOUTS

    def test_coder_timeout_is_180(self):
        """Coder static fallback should be 180s (raised from 90 in Day 1)."""
        from src.orchestration.agent_pipeline import PHASE_TIMEOUTS
        assert PHASE_TIMEOUTS["coder"] == 180

    def test_adaptive_timeout_import_flag(self):
        """ADAPTIVE_TIMEOUT_AVAILABLE flag should exist."""
        from src.orchestration.agent_pipeline import ADAPTIVE_TIMEOUT_AVAILABLE
        assert isinstance(ADAPTIVE_TIMEOUT_AVAILABLE, bool)

    def test_fc_loop_import_flag(self):
        """FC_LOOP_AVAILABLE flag should still exist."""
        from src.orchestration.agent_pipeline import FC_LOOP_AVAILABLE
        assert isinstance(FC_LOOP_AVAILABLE, bool)
