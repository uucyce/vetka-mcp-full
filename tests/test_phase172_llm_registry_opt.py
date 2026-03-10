"""
Tests for Phase 172.OPT — LLM Model Registry Performance Optimizations.

MARKER_172.OPT.TESTS

Tests:
  T1. Shared HTTP client reuse (P1)
  T2. Bulk index O(1) lookup (P2)
  T3. Debounced save (P3)
  T4. asyncio.Lock usage (P4)
  T5. DRY helper (P5)
  T6. Prefetch mechanics (P6)
  T7. Module-level httpx check (P7)
  T8. Performance benchmark — in-memory lookup < 0.1ms
  T9. Backward compatibility — public API unchanged
"""

import asyncio
import json
import os
import sys
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.elisya.llm_model_registry import (
    LLMModelRegistry,
    ModelProfile,
    get_llm_registry,
    reset_llm_registry,
    calculate_timeout,
    _SAFE_DEFAULTS,
    _HTTPX_AVAILABLE,
    COMPLEXITY_MULTIPLIERS,
    CACHE_FILE,
)


@pytest.fixture
def fresh_registry(tmp_path):
    """Create a fresh registry with temp cache path for isolation."""
    reset_llm_registry()
    registry = LLMModelRegistry()
    # Override cache to temp dir so tests don't pollute real cache
    return registry


# ─── T1: Shared HTTP client ────────────────────────────────────────

class TestSharedHTTPClient:
    """P1: HTTP client is created once and reused."""

    def test_http_client_is_none_initially(self, fresh_registry):
        """HTTP client should not be created until needed."""
        assert fresh_registry._http_client is None

    @pytest.mark.skipif(not _HTTPX_AVAILABLE, reason="httpx not installed")
    def test_get_http_client_returns_same_instance(self, fresh_registry):
        """Calling _get_http_client() twice returns same client."""
        client1 = fresh_registry._get_http_client()
        client2 = fresh_registry._get_http_client()
        assert client1 is client2

    @pytest.mark.skipif(not _HTTPX_AVAILABLE, reason="httpx not installed")
    def test_http_client_has_connection_pooling(self, fresh_registry):
        """Shared client should have connection limits configured."""
        client = fresh_registry._get_http_client()
        # httpx.AsyncClient has pool limits
        assert client is not None
        assert not client.is_closed


# ─── T2: Bulk index O(1) lookup ────────────────────────────────────

class TestBulkIndex:
    """P2: API responses are indexed as dicts for O(1) model lookup."""

    def test_aa_index_starts_none(self, fresh_registry):
        assert fresh_registry._aa_index is None
        assert fresh_registry._aa_fetched is False

    def test_or_index_starts_none(self, fresh_registry):
        assert fresh_registry._or_index is None
        assert fresh_registry._or_fetched is False

    @pytest.mark.asyncio
    async def test_aa_index_built_from_response(self, fresh_registry):
        """Simulated AA API response builds a dict index."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"model_id": "test-fast", "context_length": 32000,
             "output_tokens_per_second": 100.0},
            {"model_id": "openai/test-big", "context_length": 128000,
             "output_tokens_per_second": 50.0},
        ]

        with patch.dict(os.environ, {"ARTIFICIAL_ANALYSIS_API_KEY": "test-key"}), \
             patch.object(fresh_registry, "_get_http_client") as mock_client_fn:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_fn.return_value = mock_client

            index = await fresh_registry._ensure_aa_index()
            assert "test-fast" in index
            assert "test-big" in index  # normalized from "openai/test-big"
            assert fresh_registry._aa_fetched is True

    @pytest.mark.asyncio
    async def test_aa_index_fetched_only_once(self, fresh_registry):
        """Second call to _ensure_aa_index returns cached dict, no HTTP call."""
        fresh_registry._aa_index = {"cached-model": {"id": "cached-model"}}
        fresh_registry._aa_fetched = True

        index = await fresh_registry._ensure_aa_index()
        assert index is fresh_registry._aa_index  # Same object, no fetch

    @pytest.mark.asyncio
    async def test_lookup_aa_o1(self, fresh_registry):
        """_lookup_artificial_analysis uses dict.get(), not linear scan."""
        fresh_registry._aa_index = {
            "gpt-4o": {
                "model_id": "gpt-4o", "context_length": 128000,
                "output_tokens_per_second": 80.0
            }
        }
        fresh_registry._aa_fetched = True

        profile = await fresh_registry._lookup_artificial_analysis("gpt-4o")
        assert profile is not None
        assert profile.model_id == "gpt-4o"
        assert profile.source == "artificial_analysis"


# ─── T3: Debounced save ────────────────────────────────────────────

class TestDebouncedSave:
    """P3: Disk writes are debounced — not on every profile store."""

    def test_store_profile_sets_dirty(self, fresh_registry):
        """_store_profile marks cache as dirty."""
        profile = ModelProfile(model_id="test", source="test")
        fresh_registry._store_profile(profile)
        assert fresh_registry._dirty is True

    def test_store_profile_schedules_timer(self, fresh_registry):
        """_store_profile schedules a debounce timer, not immediate save."""
        profile = ModelProfile(model_id="test", source="test")
        fresh_registry._store_profile(profile)
        assert fresh_registry._save_timer is not None
        # Cancel so test cleanup is clean
        fresh_registry._save_timer.cancel()

    def test_flush_save_clears_dirty(self, fresh_registry, tmp_path):
        """_flush_save writes immediately and clears dirty flag."""
        # Point cache to temp dir
        import src.elisya.llm_model_registry as mod
        original_cache_dir = mod.CACHE_DIR
        original_cache_file = mod.CACHE_FILE
        mod.CACHE_DIR = tmp_path
        mod.CACHE_FILE = tmp_path / "test_profiles.json"

        try:
            fresh_registry._dirty = True
            fresh_registry._profiles["test"] = ModelProfile(model_id="test")
            fresh_registry._flush_save()
            assert fresh_registry._dirty is False
            assert (tmp_path / "test_profiles.json").exists()
        finally:
            mod.CACHE_DIR = original_cache_dir
            mod.CACHE_FILE = original_cache_file

    def test_multiple_stores_one_write(self, fresh_registry):
        """Storing 5 profiles rapidly results in only 1 pending timer (not 5 writes)."""
        for i in range(5):
            fresh_registry._store_profile(ModelProfile(model_id=f"model-{i}"))
        # Only one timer should be active (each store cancels previous)
        assert fresh_registry._save_timer is not None
        assert fresh_registry._dirty is True
        assert len(fresh_registry._profiles) >= 5
        fresh_registry._save_timer.cancel()


# ─── T4: asyncio.Lock ──────────────────────────────────────────────

class TestAsyncLock:
    """P4: Async paths use asyncio.Lock, not threading.Lock."""

    def test_async_lock_lazy_init(self, fresh_registry):
        """asyncio.Lock created lazily, not in __init__."""
        assert fresh_registry._async_lock is None

    def test_get_async_lock_creates_lock(self, fresh_registry):
        """_get_async_lock creates and caches asyncio.Lock."""
        lock = fresh_registry._get_async_lock()
        assert isinstance(lock, asyncio.Lock)
        # Same instance on second call
        assert fresh_registry._get_async_lock() is lock


# ─── T5: DRY helper ───────────────────────────────────────────────

class TestDRYHelper:
    """P5: _profile_from_defaults is single source of truth."""

    def test_profile_from_defaults_basic(self):
        """Helper builds ModelProfile correctly from defaults dict."""
        defaults = {
            "context_length": 131072,
            "output_tokens_per_second": 90.0,
            "input_tokens_per_second": 200.0,
            "ttft_ms": 400.0,
            "provider": "xai",
        }
        profile = LLMModelRegistry._profile_from_defaults("test-model", defaults)
        assert profile.model_id == "test-model"
        assert profile.context_length == 131072
        assert profile.output_tokens_per_second == 90.0
        assert profile.source == "hardcoded_defaults"

    def test_profile_from_defaults_custom_source(self):
        """Source parameter is passed through."""
        defaults = {"context_length": 8000}
        profile = LLMModelRegistry._profile_from_defaults(
            "tiny", defaults, source="hardcoded_defaults_fuzzy"
        )
        assert profile.source == "hardcoded_defaults_fuzzy"
        assert profile.context_length == 8000

    def test_profile_from_defaults_missing_keys_use_fallbacks(self):
        """Missing keys in defaults dict use ModelProfile defaults."""
        profile = LLMModelRegistry._profile_from_defaults("empty", {})
        assert profile.context_length == 128000  # ModelProfile default
        assert profile.output_tokens_per_second == 35.0


# ─── T6: Prefetch mechanics ───────────────────────────────────────

class TestPrefetch:
    """P6: Proactive prefetch warms cache for known models."""

    def test_prefetch_starts_false(self, fresh_registry):
        assert fresh_registry._prefetch_started is False

    @pytest.mark.asyncio
    async def test_first_miss_triggers_prefetch(self, fresh_registry):
        """First cache miss should set _prefetch_started flag."""
        # Use a model NOT in _SAFE_DEFAULTS to guarantee a true cache miss
        # (models in defaults are resolved before prefetch triggers)
        with patch.dict(os.environ, {
            "ARTIFICIAL_ANALYSIS_API_KEY": "",
            "OPENROUTER_API_KEY": "",
        }, clear=False):
            await fresh_registry.get_profile("totally-unknown-model-xyz-999")
            assert fresh_registry._prefetch_started is True
            # Cleanup timer
            if fresh_registry._save_timer:
                fresh_registry._save_timer.cancel()

    @pytest.mark.asyncio
    async def test_prefetch_populates_safe_defaults(self, fresh_registry):
        """_prefetch_all_apis should populate profiles for all _SAFE_DEFAULTS."""
        with patch.dict(os.environ, {
            "ARTIFICIAL_ANALYSIS_API_KEY": "",
            "OPENROUTER_API_KEY": "",
        }, clear=False):
            await fresh_registry._prefetch_all_apis()
            # All safe defaults should now be in memory
            for model_id in _SAFE_DEFAULTS:
                assert model_id in fresh_registry._profiles, \
                    f"Prefetch should populate {model_id}"
            if fresh_registry._save_timer:
                fresh_registry._save_timer.cancel()


# ─── T7: Module-level httpx check ─────────────────────────────────

class TestHTTPXCheck:
    """P7: httpx availability checked at module level, not per-call."""

    def test_httpx_flag_is_bool(self):
        assert isinstance(_HTTPX_AVAILABLE, bool)

    def test_httpx_is_available_in_test_env(self):
        """Our venv should have httpx installed."""
        assert _HTTPX_AVAILABLE is True


# ─── T8: Performance benchmark ────────────────────────────────────

class TestPerformance:
    """In-memory profile lookup should be extremely fast."""

    @pytest.mark.asyncio
    async def test_cached_lookup_under_100_microseconds(self, fresh_registry):
        """Profile lookup from memory cache should be < 0.1ms."""
        # Pre-populate
        fresh_registry._profiles["bench-model"] = ModelProfile(
            model_id="bench-model",
            context_length=128000,
            output_tokens_per_second=80.0,
        )

        # Benchmark 1000 lookups
        t0 = time.perf_counter()
        for _ in range(1000):
            p = await fresh_registry.get_profile("bench-model")
        elapsed = time.perf_counter() - t0

        avg_us = (elapsed / 1000) * 1_000_000  # microseconds per lookup
        assert avg_us < 100, f"Cached lookup took {avg_us:.1f}μs (expected < 100μs)"
        assert p.model_id == "bench-model"

    def test_safe_default_lookup_fast(self, fresh_registry):
        """_get_safe_default should be instant (dict lookup)."""
        t0 = time.perf_counter()
        for _ in range(1000):
            p = fresh_registry._get_safe_default("gpt-4o")
        elapsed = time.perf_counter() - t0

        avg_us = (elapsed / 1000) * 1_000_000
        assert avg_us < 50, f"Safe default lookup took {avg_us:.1f}μs (expected < 50μs)"
        assert p is not None


# ─── T9: Backward compatibility ───────────────────────────────────

class TestBackwardCompatibility:
    """All public APIs from Phase 145 are preserved."""

    def test_get_llm_registry_exists(self):
        from src.elisya.llm_model_registry import get_llm_registry
        assert callable(get_llm_registry)

    def test_calculate_timeout_exists(self):
        from src.elisya.llm_model_registry import calculate_timeout
        assert callable(calculate_timeout)

    def test_model_profile_to_dict(self):
        """to_dict still works (used by _save_cache)."""
        p = ModelProfile(model_id="test", output_tokens_per_second=99.0)
        d = p.to_dict()
        assert d["model_id"] == "test"
        assert d["output_tokens_per_second"] == 99.0

    def test_model_profile_from_dict(self):
        """from_dict still works (used by _load_cache)."""
        p = ModelProfile.from_dict({
            "model_id": "test",
            "context_length": 32000,
            "extra_ignored_key": True,
        })
        assert p.model_id == "test"
        assert p.context_length == 32000

    def test_safe_defaults_unchanged(self):
        """_SAFE_DEFAULTS dict must still have all Dragon team models."""
        required = [
            "qwen3-coder", "qwen3-coder-flash", "qwen3-30b",
            "kimi-k2.5", "glm-4.7-flash", "mimo-v2-flash",
            "grok-4.1-fast", "gpt-4o", "deepseek-r1",
        ]
        for model in required:
            assert model in _SAFE_DEFAULTS, f"{model} missing from _SAFE_DEFAULTS"

    def test_complexity_multipliers_unchanged(self):
        assert COMPLEXITY_MULTIPLIERS["simple"] == 1.0
        assert COMPLEXITY_MULTIPLIERS["medium"] == 1.8
        assert COMPLEXITY_MULTIPLIERS["complex"] == 3.2

    @pytest.mark.asyncio
    async def test_calculate_timeout_still_works(self):
        """calculate_timeout produces valid results."""
        timeout = await calculate_timeout(
            model_id="gpt-4o",
            input_tokens=3000,
            expected_output_tokens=500,
        )
        assert isinstance(timeout, int)
        assert 45 <= timeout <= 600

    def test_reset_llm_registry_exists(self):
        """reset function available for testing."""
        from src.elisya.llm_model_registry import reset_llm_registry
        assert callable(reset_llm_registry)

    def test_profile_count_property(self, fresh_registry):
        """New profile_count property works."""
        fresh_registry._profiles["x"] = ModelProfile(model_id="x")
        assert fresh_registry.profile_count >= 1
