"""Tests for AURA → ENGRAM L1 auto-promotion feed (Phase 187.11).

MARKER_187.11: When tool_usage_patterns count reaches threshold (5),
the pattern is auto-promoted to ENGRAM L1 cache.
"""

import pytest
from src.memory.aura_store import AuraStore
from src.memory.engram_cache import EngramCache, reset_engram_cache


@pytest.fixture
def aura():
    """Create AuraStore without Qdrant."""
    return AuraStore(qdrant_client=None)


@pytest.fixture
def engram(tmp_path):
    """Create fresh EngramCache with temp path."""
    reset_engram_cache()
    cache = EngramCache(cache_path=tmp_path / "engram_cache.json")
    # Monkey-patch singleton for test
    import src.memory.engram_cache as mod
    mod._instance = cache
    yield cache
    reset_engram_cache()


class TestAuraEngramFeed:
    def test_no_promotion_below_threshold(self, aura, engram):
        """Under 5 uses → no L1 entry."""
        for _ in range(4):
            aura._increment_usage("danila", "tool_usage_patterns", "vetka_search_files")
        assert len(engram) == 0

    def test_promotion_at_threshold(self, aura, engram):
        """Exactly 5 uses → promotes to L1."""
        for _ in range(5):
            aura._increment_usage("danila", "tool_usage_patterns", "vetka_search_files")
        assert len(engram) == 1
        # Verify entry content
        entries = engram.get_all()
        key = list(entries.keys())[0]
        assert "vetka_search_files" in key
        assert "tool_select" == entries[key]["category"]
        assert "aura:danila" in entries[key]["source_learning_id"]

    def test_no_duplicate_promotion(self, aura, engram):
        """6th use doesn't create duplicate."""
        for _ in range(6):
            aura._increment_usage("danila", "tool_usage_patterns", "vetka_search_files")
        assert len(engram) == 1

    def test_non_tool_category_no_promotion(self, aura, engram):
        """Non tool_usage_patterns categories don't trigger promotion."""
        for _ in range(10):
            aura._increment_usage("danila", "communication_style", "formality")
        assert len(engram) == 0

    def test_multiple_tools_promoted(self, aura, engram):
        """Different tools get separate L1 entries."""
        for _ in range(5):
            aura._increment_usage("danila", "tool_usage_patterns", "vetka_search_files")
        for _ in range(5):
            aura._increment_usage("danila", "tool_usage_patterns", "vetka_read_file")
        assert len(engram) == 2
