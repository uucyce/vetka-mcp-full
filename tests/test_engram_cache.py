"""Tests for ENGRAM L1 Cache (Phase 187.8).

MARKER_187.8: Deterministic O(1) cache with 4-key lookup,
compound keys, wildcard fallback, LFU eviction, and per-category TTL.
"""

import json
import time
import pytest
from pathlib import Path
from unittest.mock import patch

from src.memory.engram_cache import (
    EngramCache,
    EngramEntry,
    get_engram_cache,
    reset_engram_cache,
    MAX_ENTRIES,
    CATEGORY_TTL,
)


@pytest.fixture
def tmp_cache(tmp_path):
    """Create EngramCache with temp file."""
    return EngramCache(cache_path=tmp_path / "engram_cache.json")


# ============ EngramEntry ============

class TestEngramEntry:
    def test_to_dict_roundtrip(self):
        entry = EngramEntry(key="a::b::c::d", value="test")
        restored = EngramEntry.from_dict(entry.to_dict())
        assert restored.key == entry.key
        assert restored.value == entry.value

    def test_from_dict_ignores_extra_keys(self):
        d = {"key": "x", "value": "y", "unknown_field": 42}
        entry = EngramEntry.from_dict(d)
        assert entry.key == "x"


# ============ Key Construction ============

class TestKeyConstruction:
    def test_make_key(self):
        key = EngramCache.make_key("opus", "session_tools.py", "edit", "fix")
        assert key == "opus::session_tools.py::edit::fix"

    def test_make_pair_key_sorted(self):
        k1 = EngramCache.make_pair_key("b.py", "a.py", "modify")
        k2 = EngramCache.make_pair_key("a.py", "b.py", "modify")
        assert k1 == k2 == "pair::a.py::b.py::modify"


# ============ Put & Get ============

class TestPutGet:
    def test_put_and_exact_get(self, tmp_cache):
        key = EngramCache.make_key("opus", "tools.py", "edit", "fix")
        tmp_cache.put(key, "always check imports")
        entry = tmp_cache.get("opus", "tools.py", "edit", "fix")
        assert entry is not None
        assert entry.value == "always check imports"
        assert entry.hit_count == 1

    def test_get_miss(self, tmp_cache):
        assert tmp_cache.get("opus", "nope.py", "edit", "fix") is None

    def test_wildcard_agent_fallback(self, tmp_cache):
        key = EngramCache.make_key("*", "tools.py", "edit", "fix")
        tmp_cache.put(key, "global rule")
        entry = tmp_cache.get("cursor", "tools.py", "edit", "fix")
        assert entry is not None
        assert entry.value == "global rule"

    def test_wildcard_phase_fallback(self, tmp_cache):
        key = EngramCache.make_key("*", "tools.py", "edit", "*")
        tmp_cache.put(key, "any phase")
        entry = tmp_cache.get("codex", "tools.py", "edit", "build")
        assert entry is not None
        assert entry.value == "any phase"

    def test_exact_match_priority(self, tmp_cache):
        tmp_cache.put(EngramCache.make_key("opus", "f.py", "edit", "fix"), "exact")
        tmp_cache.put(EngramCache.make_key("*", "f.py", "edit", "fix"), "wildcard")
        entry = tmp_cache.get("opus", "f.py", "edit", "fix")
        assert entry.value == "exact"

    def test_put_overwrites(self, tmp_cache):
        key = EngramCache.make_key("opus", "f.py", "edit", "fix")
        tmp_cache.put(key, "v1")
        tmp_cache.put(key, "v2")
        entry = tmp_cache.get("opus", "f.py", "edit", "fix")
        assert entry.value == "v2"


# ============ Pair Keys ============

class TestPairKeys:
    def test_pair_put_and_get(self, tmp_cache):
        key = EngramCache.make_pair_key("scorer.py", "feedback.py", "modify")
        tmp_cache.put(key, "always change together", category="pattern")
        entry = tmp_cache.get_pair("scorer.py", "feedback.py", "modify")
        assert entry is not None
        assert entry.value == "always change together"

    def test_pair_order_independent(self, tmp_cache):
        key = EngramCache.make_pair_key("a.py", "b.py", "fix")
        tmp_cache.put(key, "linked")
        assert tmp_cache.get_pair("b.py", "a.py", "fix") is not None

    def test_find_pair_warnings(self, tmp_cache):
        tmp_cache.put(EngramCache.make_pair_key("x.py", "y.py", "edit"), "warning 1")
        tmp_cache.put(EngramCache.make_pair_key("x.py", "z.py", "fix"), "warning 2")
        tmp_cache.put(EngramCache.make_pair_key("a.py", "b.py", "edit"), "unrelated")
        warnings = tmp_cache.find_pair_warnings("x.py")
        assert len(warnings) == 2


# ============ TTL & Expiration ============

class TestExpiration:
    def test_permanent_category_never_expires(self, tmp_cache):
        key = EngramCache.make_key("opus", "f.py", "edit", "fix")
        tmp_cache.put(key, "critical", category="danger")
        entry = tmp_cache._cache[key]
        entry.created_at = time.time() - 365 * 86400  # 1 year ago
        assert not tmp_cache._is_expired(entry)

    def test_default_category_expires(self, tmp_cache):
        key = EngramCache.make_key("opus", "f.py", "edit", "fix")
        tmp_cache.put(key, "temp", category="default")
        entry = tmp_cache._cache[key]
        entry.created_at = time.time() - 100 * 86400  # 100 days > 90 TTL
        assert tmp_cache._is_expired(entry)

    def test_expired_entry_not_returned(self, tmp_cache):
        key = EngramCache.make_key("opus", "f.py", "edit", "fix")
        tmp_cache.put(key, "old", category="tool_select")
        tmp_cache._cache[key].created_at = time.time() - 40 * 86400  # 40 > 30 TTL
        assert tmp_cache.get("opus", "f.py", "edit", "fix") is None


# ============ Eviction ============

class TestEviction:
    def test_eviction_at_max(self, tmp_cache):
        for i in range(MAX_ENTRIES):
            tmp_cache.put(f"key_{i}", f"val_{i}")
        assert len(tmp_cache) == MAX_ENTRIES
        tmp_cache.put("overflow", "new")
        assert len(tmp_cache) == MAX_ENTRIES
        assert "overflow" in tmp_cache._cache

    def test_evicts_lowest_hit_count(self, tmp_cache):
        tmp_cache.put("kept", "high hits")
        tmp_cache._cache["kept"].hit_count = 100
        tmp_cache.put("victim", "low hits")
        tmp_cache._cache["victim"].hit_count = 0
        # Fill to max
        for i in range(MAX_ENTRIES - 2):
            tmp_cache.put(f"filler_{i}", f"v_{i}")
            tmp_cache._cache[f"filler_{i}"].hit_count = 50
        # Trigger eviction
        tmp_cache.put("trigger", "new")
        assert "kept" in tmp_cache._cache
        assert "victim" not in tmp_cache._cache


# ============ Persistence ============

class TestPersistence:
    def test_save_and_load(self, tmp_path):
        path = tmp_path / "test_cache.json"
        cache1 = EngramCache(cache_path=path)
        cache1.put(EngramCache.make_key("opus", "f.py", "edit", "fix"), "lesson1")
        # New instance loads from disk
        cache2 = EngramCache(cache_path=path)
        entry = cache2.get("opus", "f.py", "edit", "fix")
        assert entry is not None
        assert entry.value == "lesson1"

    def test_remove_entry(self, tmp_cache):
        key = EngramCache.make_key("opus", "f.py", "edit", "fix")
        tmp_cache.put(key, "to remove")
        assert tmp_cache.remove(key)
        assert tmp_cache.get("opus", "f.py", "edit", "fix") is None

    def test_remove_nonexistent(self, tmp_cache):
        assert not tmp_cache.remove("nonexistent")


# ============ Stats ============

class TestStats:
    def test_stats_basic(self, tmp_cache):
        tmp_cache.put("k1", "v1", category="danger")
        tmp_cache.put("k2", "v2", category="pattern")
        s = tmp_cache.stats()
        assert s["total"] == 2
        assert s["active"] == 2
        assert s["categories"]["danger"] == 1
        assert s["categories"]["pattern"] == 1


# ============ Singleton ============

class TestSingleton:
    def test_singleton_returns_same(self):
        reset_engram_cache()
        c1 = get_engram_cache()
        c2 = get_engram_cache()
        assert c1 is c2
        reset_engram_cache()

    def test_reset_clears_singleton(self):
        reset_engram_cache()
        c1 = get_engram_cache()
        reset_engram_cache()
        c2 = get_engram_cache()
        assert c1 is not c2
        reset_engram_cache()
