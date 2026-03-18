"""Tests for ENGRAM L1 demotion (Phase 187.10).

MARKER_187.10: Demote L1 entries when agent ignores advice AND task succeeds.
Keep entries when task fails (lesson was correct).
Never demote 'danger' category.
"""

import pytest
from src.memory.engram_cache import EngramCache, EngramEntry


@pytest.fixture
def cache(tmp_path):
    """Create EngramCache with temp file."""
    return EngramCache(cache_path=tmp_path / "engram_cache.json")


class TestMarkPresented:
    def test_mark_sets_flag(self, cache):
        key = EngramCache.make_key("opus", "f.py", "edit", "fix")
        cache.put(key, "advice")
        assert cache.mark_presented(key)
        assert cache._cache[key].was_presented is True
        assert cache._cache[key].presented_at is not None

    def test_mark_nonexistent_returns_false(self, cache):
        assert not cache.mark_presented("nope")

    def test_get_presented(self, cache):
        k1 = "key1"
        k2 = "key2"
        cache.put(k1, "a")
        cache.put(k2, "b")
        cache.mark_presented(k1)
        presented = cache.get_presented()
        assert len(presented) == 1
        assert presented[0].key == k1


class TestDemotion:
    def test_demote_ignored_and_succeeded(self, cache):
        """Ignored advice + task succeeded → demote."""
        key = EngramCache.make_key("opus", "f.py", "edit", "fix")
        cache.put(key, "stale advice", category="pattern")
        cache.mark_presented(key)
        assert cache.demote_if_ignored(key, task_succeeded=True)
        assert key not in cache._cache

    def test_no_demote_when_task_failed(self, cache):
        """Ignored advice + task failed → keep (lesson was right)."""
        key = EngramCache.make_key("opus", "f.py", "edit", "fix")
        cache.put(key, "correct advice", category="pattern")
        original_hits = cache._cache[key].hit_count
        cache.mark_presented(key)
        assert not cache.demote_if_ignored(key, task_succeeded=False)
        assert key in cache._cache
        # Hit count boosted
        assert cache._cache[key].hit_count == original_hits + 1

    def test_never_demote_danger(self, cache):
        """Danger entries never demoted, regardless of outcome."""
        key = EngramCache.make_key("opus", "f.py", "edit", "fix")
        cache.put(key, "critical rule", category="danger")
        cache.mark_presented(key)
        assert not cache.demote_if_ignored(key, task_succeeded=True)
        assert key in cache._cache

    def test_no_demote_if_not_presented(self, cache):
        """Can't demote what was never presented."""
        key = EngramCache.make_key("opus", "f.py", "edit", "fix")
        cache.put(key, "advice")
        assert not cache.demote_if_ignored(key, task_succeeded=True)
        assert key in cache._cache

    def test_no_demote_nonexistent(self, cache):
        assert not cache.demote_if_ignored("nope", task_succeeded=True)


class TestResetPresented:
    def test_reset_clears_all_flags(self, cache):
        cache.put("k1", "a")
        cache.put("k2", "b")
        cache.mark_presented("k1")
        cache.mark_presented("k2")
        cache.reset_presented()
        assert all(not e.was_presented for e in cache._cache.values())
        assert all(e.presented_at is None for e in cache._cache.values())


class TestDemotionPersistence:
    def test_demotion_persists_to_disk(self, tmp_path):
        path = tmp_path / "test.json"
        c1 = EngramCache(cache_path=path)
        key = "test_key"
        c1.put(key, "advice", category="pattern")
        c1.mark_presented(key)
        c1.demote_if_ignored(key, task_succeeded=True)
        # Reload from disk
        c2 = EngramCache(cache_path=path)
        assert key not in c2._cache
