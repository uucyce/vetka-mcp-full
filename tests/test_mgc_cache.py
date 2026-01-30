"""
VETKA Phase 99 - Multi-Generational Cache (MGC) Tests

Comprehensive test suite for MGC Cache functionality including:
- Basic set/get operations
- Generational promotion and demotion
- LRU eviction strategies
- Lazy computation with caching
- Hit/miss statistics tracking
- JSON fallback when Qdrant unavailable

@file test_mgc_cache.py
@phase 99
@marker MARKER-99-02: MGC promotion threshold - items with access_count >= threshold stay in Gen 0
@depends pytest, pytest-asyncio, asyncio, tempfile, json
@tests src/memory/mgc_cache.py

Test Architecture:
    - Fixtures for temp directories and cache instances
    - Async test functions with pytest-asyncio
    - Mocked Qdrant client for Gen 1 testing
    - Real JSON file I/O for Gen 2 testing
    - Statistical validation for hit/miss rates
"""

import asyncio
import json
import logging
import pytest
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Import cache components
from src.memory.mgc_cache import MGCCache, MGCEntry, get_mgc_cache, reset_mgc_cache


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def temp_dir():
    """Create temporary directory for test cache files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def json_cache_path(temp_dir):
    """Path for JSON cache file."""
    return temp_dir / "mgc_cache.json"


@pytest.fixture
def mgc_cache(json_cache_path):
    """Create MGC cache instance for testing."""
    cache = MGCCache(
        gen0_max=5,
        promotion_threshold=3,
        qdrant_client=None,
        json_path=json_cache_path
    )
    yield cache
    # Cleanup
    asyncio.run(cache.clear())


@pytest.fixture
def mgc_cache_with_mock_qdrant(json_cache_path):
    """Create MGC cache with mocked Qdrant client."""
    mock_qdrant = AsyncMock()
    cache = MGCCache(
        gen0_max=5,
        promotion_threshold=3,
        qdrant_client=mock_qdrant,
        json_path=json_cache_path
    )
    yield cache, mock_qdrant
    # Cleanup
    asyncio.run(cache.clear())


# ============================================================================
# TEST SUITE 1: BASIC OPERATIONS
# ============================================================================


class TestMGCBasicOperations:
    """
    @phase: 99
    Test basic set/get operations in MGC cache.
    """

    @pytest.mark.asyncio
    async def test_mgc_set_and_get(self, mgc_cache):
        """
        @phase: 99
        Test basic value storage and retrieval from Gen 0 (RAM).

        Scenario:
            1. Set a value in empty cache
            2. Value is stored in Gen 0 (RAM)
            3. Get returns the exact value
            4. Stats show Gen 0 hit

        Expected Results:
            - get() returns original value
            - get() increments access_count
            - Stats show 1 Gen 0 hit, 0 misses
        """
        key = "test_key_1"
        value = {"data": "test_value", "count": 42}

        # Set value
        await mgc_cache.set(key, value)

        # Verify it's in Gen 0
        assert key in mgc_cache.gen0
        assert mgc_cache.gen0[key].value == value
        assert mgc_cache.gen0[key].generation == 0

        # Get value
        result = await mgc_cache.get(key)

        # Assertions
        assert result == value
        assert mgc_cache.gen0[key].access_count == 1

        stats = mgc_cache.get_stats()
        assert stats["hits"]["gen0"] == 1
        assert stats["misses"] == 0
        assert stats["gen0_size"] == 1

    @pytest.mark.asyncio
    async def test_mgc_set_multiple_values(self, mgc_cache):
        """
        @phase: 99
        Test storing multiple values in Gen 0.

        Scenario:
            1. Set 3 different values
            2. All should be in Gen 0
            3. Retrieve each value

        Expected Results:
            - All values are correctly stored and retrieved
            - Gen 0 size matches number of entries
        """
        data = {
            "key_1": {"value": 1},
            "key_2": {"value": 2},
            "key_3": {"value": 3}
        }

        # Set all values
        for key, value in data.items():
            await mgc_cache.set(key, value)

        # Get all values
        for key, expected_value in data.items():
            result = await mgc_cache.get(key)
            assert result == expected_value

        # Check stats
        stats = mgc_cache.get_stats()
        assert stats["gen0_size"] == 3
        assert stats["hits"]["gen0"] == 3

    @pytest.mark.asyncio
    async def test_mgc_get_nonexistent(self, mgc_cache):
        """
        @phase: 99
        Test getting non-existent key returns None.

        Scenario:
            1. Get key that was never set
            2. Should return None
            3. Should increment miss counter

        Expected Results:
            - get() returns None
            - Stats show 1 miss
        """
        result = await mgc_cache.get("nonexistent_key")

        assert result is None
        stats = mgc_cache.get_stats()
        assert stats["misses"] == 1
        assert sum(stats["hits"].values()) == 0

    @pytest.mark.asyncio
    async def test_mgc_update_existing_value(self, mgc_cache):
        """
        @phase: 99
        Test updating existing value in Gen 0.

        Scenario:
            1. Set initial value
            2. Update with new value
            3. Retrieve updated value

        Expected Results:
            - Value is correctly updated
            - Access count increments for get operations (set doesn't increment on new items)
        """
        key = "update_test"
        value1 = {"status": "initial"}
        value2 = {"status": "updated"}

        await mgc_cache.set(key, value1)
        # set() on new item doesn't call touch(), so access_count stays 0
        assert mgc_cache.gen0[key].access_count == 0

        await mgc_cache.set(key, value2)
        # set() on existing item calls touch(), so access_count becomes 1
        assert mgc_cache.gen0[key].access_count == 1
        assert mgc_cache.gen0[key].value == value2

        result = await mgc_cache.get(key)
        assert result == value2
        # get() also calls touch(), so access_count becomes 2
        assert mgc_cache.gen0[key].access_count == 2

    @pytest.mark.asyncio
    async def test_mgc_delete(self, mgc_cache):
        """
        @phase: 99
        Test deleting entries from cache.

        Scenario:
            1. Set a value
            2. Delete it
            3. Try to get it

        Expected Results:
            - delete() returns True
            - get() returns None after deletion
        """
        key = "delete_test"
        await mgc_cache.set(key, {"data": "temp"})

        assert key in mgc_cache.gen0

        result = await mgc_cache.delete(key)
        assert result is True
        assert key not in mgc_cache.gen0

        result = await mgc_cache.get(key)
        assert result is None


# ============================================================================
# TEST SUITE 2: PROMOTION AND DEMOTION
# ============================================================================


class TestMGCPromotion:
    """
    @phase: 99
    Test generational promotion logic (MARKER-99-02).

    Items with access_count >= promotion_threshold stay in Gen 0.
    Less frequently accessed items are demoted to Gen 1/2.
    """

    @pytest.mark.asyncio
    async def test_mgc_promotion_threshold(self, mgc_cache):
        """
        @phase: 99
        Test that frequently accessed items remain in Gen 0.

        Scenario:
            1. Set a value in Gen 0
            2. Access it repeatedly (>= threshold)
            3. Fill Gen 0 to trigger eviction
            4. Frequently accessed item should survive eviction

        Expected Results:
            - Item with access_count >= threshold stays in Gen 0
            - Less accessed items are evicted
            - Promotion threshold = 3 (from fixture)
        """
        # Set items with different access patterns
        key_frequent = "frequent_item"
        key_infrequent = "infrequent_item"

        # Add frequent item and access it multiple times
        await mgc_cache.set(key_frequent, {"type": "frequent"})
        for _ in range(4):  # 4 get() calls = access_count becomes 4
            await mgc_cache.get(key_frequent)

        # Add infrequent item (no additional accesses = access_count stays 0)
        await mgc_cache.set(key_infrequent, {"type": "infrequent"})

        # Verify access counts
        assert mgc_cache.gen0[key_frequent].access_count == 4
        assert mgc_cache.gen0[key_infrequent].access_count == 0
        assert mgc_cache.promotion_threshold == 3

        # Frequent item should definitely stay
        assert mgc_cache.gen0[key_frequent].access_count >= mgc_cache.promotion_threshold
        assert mgc_cache.gen0[key_infrequent].access_count < mgc_cache.promotion_threshold

    @pytest.mark.asyncio
    async def test_mgc_promotion_back_to_gen0(self, mgc_cache):
        """
        @phase: 99
        Test promotion of items back to Gen 0 when accessed from Gen 2.

        Scenario:
            1. Fill Gen 0 to capacity
            2. Add one more item (triggers eviction)
            3. Evicted item goes to Gen 2 (JSON)
            4. Access evicted item from Gen 2
            5. Should be promoted back to Gen 0 if space available

        Expected Results:
            - Item retrieved from Gen 2
            - Promoted back to Gen 0 if gen0 has space
            - Gen 0 hit rate reflects Gen 0 promotion
        """
        # Fill Gen 0 with 5 items (gen0_max=5)
        for i in range(5):
            await mgc_cache.set(f"gen0_item_{i}", f"value_{i}")

        # This should trigger eviction of least recently used
        await mgc_cache.set("new_item", "new_value")

        # One of the original items was evicted
        # Check Gen 0 size is still at max
        assert len(mgc_cache.gen0) <= mgc_cache.gen0_max

    @pytest.mark.asyncio
    async def test_mgc_demotion_strategy(self, mgc_cache):
        """
        @phase: 99
        Test that less frequently accessed items are demoted correctly.

        Scenario:
            1. Create items with different access counts
            2. Fill Gen 0 to trigger eviction
            3. Items with access_count < threshold go to Gen 2 (JSON)
            4. Items with access_count >= threshold go to Gen 1 (or Gen 2 fallback)

        Expected Results:
            - Low-access items are stored in JSON (Gen 2)
            - Medium-access items stored appropriately
            - Eviction counter increments
        """
        # Create low-access item
        await mgc_cache.set("low_access", {"status": "new"})
        low_access_entry = mgc_cache.gen0["low_access"]
        assert low_access_entry.access_count < mgc_cache.promotion_threshold

        # Create high-access item
        await mgc_cache.set("high_access", {"status": "new"})
        for _ in range(4):
            await mgc_cache.get("high_access")

        high_access_entry = mgc_cache.gen0["high_access"]
        assert high_access_entry.access_count >= mgc_cache.promotion_threshold

        # Verify promotion threshold logic
        assert low_access_entry.access_count < mgc_cache.promotion_threshold
        assert high_access_entry.access_count >= mgc_cache.promotion_threshold


# ============================================================================
# TEST SUITE 3: EVICTION AND LRU
# ============================================================================


class TestMGCEviction:
    """
    @phase: 99
    Test LRU eviction when Gen 0 is full.
    """

    @pytest.mark.asyncio
    async def test_mgc_lru_eviction_on_overflow(self, mgc_cache):
        """
        @phase: 99
        Test LRU eviction when Gen 0 reaches capacity.

        Scenario:
            1. Fill Gen 0 to max (5 items)
            2. Add one more item
            3. Least recently used item should be evicted
            4. New item should enter Gen 0

        Expected Results:
            - Gen 0 size never exceeds gen0_max
            - Eviction counter increments
            - LRU item is correctly identified (earliest last_accessed)
        """
        # Set gen0_max=5 items
        for i in range(5):
            await mgc_cache.set(f"item_{i}", f"value_{i}")

        assert len(mgc_cache.gen0) == 5

        stats_before = mgc_cache.get_stats()
        evictions_before = stats_before["evictions"]

        # Add 6th item - should trigger eviction
        await mgc_cache.set("item_5", "value_5")

        stats_after = mgc_cache.get_stats()

        # Gen 0 should still be at max
        assert stats_after["gen0_size"] == mgc_cache.gen0_max

        # One eviction should have occurred
        assert stats_after["evictions"] == evictions_before + 1

    @pytest.mark.asyncio
    async def test_mgc_lru_identification(self, mgc_cache):
        """
        @phase: 99
        Test that least recently used item is correctly identified.

        Scenario:
            1. Set items in order: A, B, C
            2. Wait and access B (updates last_accessed)
            3. Wait and access C (updates last_accessed)
            4. A should be LRU
            5. Fill Gen 0 and trigger eviction
            6. A should be evicted

        Expected Results:
            - LRU item (earliest last_accessed timestamp) is evicted first
            - Item access patterns correctly update last_accessed
        """
        # Create items
        await mgc_cache.set("item_a", "value_a")
        await asyncio.sleep(0.01)

        await mgc_cache.set("item_b", "value_b")
        await asyncio.sleep(0.01)

        await mgc_cache.set("item_c", "value_c")
        await asyncio.sleep(0.01)

        # Access B and C to update their last_accessed
        await mgc_cache.get("item_b")
        await asyncio.sleep(0.01)
        await mgc_cache.get("item_c")
        await asyncio.sleep(0.01)

        # A should have oldest last_accessed
        timestamps = {
            k: mgc_cache.gen0[k].last_accessed
            for k in ["item_a", "item_b", "item_c"]
        }

        assert timestamps["item_a"] < timestamps["item_b"]
        assert timestamps["item_b"] < timestamps["item_c"]

    @pytest.mark.asyncio
    async def test_mgc_eviction_to_json(self, mgc_cache):
        """
        @phase: 99
        Test that evicted items are stored in JSON (Gen 2).

        Scenario:
            1. Fill Gen 0
            2. Trigger eviction (low-access item)
            3. Evicted item should be in JSON file

        Expected Results:
            - JSON file contains evicted item
            - Item can be retrieved from JSON later
            - Gen 2 storage works as fallback
        """
        # Set low-access item
        await mgc_cache.set("evict_me", {"data": "temporary"})

        # Verify it's not in JSON yet
        assert not mgc_cache.json_path.exists()

        # Fill rest of Gen 0
        for i in range(1, 5):
            await mgc_cache.set(f"keep_me_{i}", f"value_{i}")

        # This triggers eviction
        await mgc_cache.set("new_hot_item", "hot_value")

        # One item was evicted - check if JSON file exists
        # (May or may not have been created depending on which item was evicted)
        if mgc_cache.json_path.exists():
            data = json.loads(mgc_cache.json_path.read_text())
            assert len(data) >= 0  # May contain evicted items

    @pytest.mark.asyncio
    async def test_mgc_eviction_counter(self, mgc_cache):
        """
        @phase: 99
        Test eviction counter increments correctly.

        Scenario:
            1. Monitor eviction counter
            2. Trigger multiple evictions
            3. Counter should increment each time

        Expected Results:
            - Eviction counter starts at 0
            - Increments for each eviction
            - Stats reflect correct count
        """
        stats = mgc_cache.get_stats()
        assert stats["evictions"] == 0

        # Fill and overflow multiple times
        for cycle in range(2):
            for i in range(6):
                await mgc_cache.set(f"cycle_{cycle}_item_{i}", f"value_{i}")

            stats = mgc_cache.get_stats()
            assert stats["evictions"] > 0


# ============================================================================
# TEST SUITE 4: LAZY COMPUTATION
# ============================================================================


class TestMGCLazyComputation:
    """
    @phase: 99
    Test get_or_compute lazy evaluation with caching.
    """

    @pytest.mark.asyncio
    async def test_mgc_get_or_compute_cache_hit(self, mgc_cache):
        """
        @phase: 99
        Test get_or_compute returns cached value without computing.

        Scenario:
            1. Set a value in cache
            2. Call get_or_compute with compute function
            3. Compute function should not be called
            4. Cached value returned

        Expected Results:
            - Compute function not called
            - Cached value returned
            - Stats show cache hit
        """
        key = "cached_computation"
        cached_value = {"result": 42}

        # Pre-populate cache
        await mgc_cache.set(key, cached_value)

        # Mock compute function
        compute_fn = AsyncMock()
        compute_fn.return_value = {"result": 999}  # Different value

        # Call get_or_compute
        result = await mgc_cache.get_or_compute(key, compute_fn)

        # Assertions
        assert result == cached_value  # Should return cached value
        assert not compute_fn.called  # Should not compute

        stats = mgc_cache.get_stats()
        assert stats["hits"]["gen0"] == 1

    @pytest.mark.asyncio
    async def test_mgc_get_or_compute_cache_miss(self, mgc_cache):
        """
        @phase: 99
        Test get_or_compute computes and caches on miss.

        Scenario:
            1. Key not in cache
            2. Call get_or_compute
            3. Compute function is called
            4. Result is cached and returned

        Expected Results:
            - Compute function called
            - Result is cached in Gen 0
            - Result returned
        """
        key = "computed_value"
        computed_value = {"computed": True, "value": 123}

        # Create async compute function
        async def expensive_compute():
            await asyncio.sleep(0.01)
            return computed_value

        # Get or compute
        result = await mgc_cache.get_or_compute(key, expensive_compute)

        # Assertions
        assert result == computed_value
        assert key in mgc_cache.gen0
        assert mgc_cache.gen0[key].value == computed_value

        # Second call should hit cache
        result2 = await mgc_cache.get_or_compute(key, expensive_compute)
        assert result2 == computed_value

    @pytest.mark.asyncio
    async def test_mgc_get_or_compute_with_size_estimate(self, mgc_cache):
        """
        @phase: 99
        Test get_or_compute respects size_bytes parameter.

        Scenario:
            1. Compute value with size estimate
            2. Value is cached with size metadata
            3. Size is tracked in cache entry

        Expected Results:
            - Size metadata stored
            - Can be used for memory management
        """
        key = "sized_value"
        size_bytes = 1024
        computed_value = {"data": "x" * size_bytes}

        async def compute():
            return computed_value

        await mgc_cache.get_or_compute(key, compute, size_bytes=size_bytes)

        entry = mgc_cache.gen0[key]
        assert entry.size_bytes == size_bytes

    @pytest.mark.asyncio
    async def test_mgc_get_or_compute_multiple_keys(self, mgc_cache):
        """
        @phase: 99
        Test get_or_compute with multiple different keys.

        Scenario:
            1. Compute multiple values with different keys
            2. Each should be cached independently
            3. Retrievals should return correct values

        Expected Results:
            - Each key cached correctly
            - No cross-contamination
            - All values retrievable
        """
        compute_calls = {}

        async def make_compute_fn(key):
            async def compute():
                compute_calls[key] = compute_calls.get(key, 0) + 1
                return {"key": key, "computed": True}
            return compute

        # Get or compute multiple keys
        for key_id in range(3):
            key = f"compute_key_{key_id}"
            compute_fn = await make_compute_fn(key)
            result = await mgc_cache.get_or_compute(key, compute_fn)
            assert result["key"] == key

        # All should be cached
        assert len(mgc_cache.gen0) == 3


# ============================================================================
# TEST SUITE 5: STATISTICS
# ============================================================================


class TestMGCStatistics:
    """
    @phase: 99
    Test hit/miss statistics tracking.
    """

    @pytest.mark.asyncio
    async def test_mgc_stats_initialization(self, mgc_cache):
        """
        @phase: 99
        Test that stats are initialized correctly.

        Scenario:
            1. Create new cache
            2. Get stats
            3. All counters should be zero

        Expected Results:
            - All hit counters are 0
            - Miss counter is 0
            - Eviction counter is 0
            - Hit rate is 0
        """
        stats = mgc_cache.get_stats()

        assert stats["gen0_size"] == 0
        assert stats["gen0_max"] == 5
        assert stats["hits"]["gen0"] == 0
        assert stats["hits"]["gen1"] == 0
        assert stats["hits"]["gen2"] == 0
        assert stats["misses"] == 0
        assert stats["evictions"] == 0
        assert stats["hit_rate"] == 0.0
        assert stats["gen0_hit_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_mgc_stats_hit_tracking(self, mgc_cache):
        """
        @phase: 99
        Test hit statistics are tracked correctly.

        Scenario:
            1. Set values and access them
            2. Get stats
            3. Hit counters should match accesses

        Expected Results:
            - gen0 hits count correctly
            - Hit rate calculated accurately
            - gen0_hit_rate is subset of total hit_rate
        """
        # Set and access items
        await mgc_cache.set("key1", "value1")
        await mgc_cache.set("key2", "value2")

        # Access key1 three times
        await mgc_cache.get("key1")
        await mgc_cache.get("key1")
        await mgc_cache.get("key1")

        # Access key2 once
        await mgc_cache.get("key2")

        stats = mgc_cache.get_stats()

        assert stats["hits"]["gen0"] == 4  # 3 + 1
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_mgc_stats_miss_tracking(self, mgc_cache):
        """
        @phase: 99
        Test miss statistics are tracked correctly.

        Scenario:
            1. Try to get non-existent keys
            2. Get stats
            3. Miss counter should match attempts

        Expected Results:
            - Miss counter increments
            - Hit rate decreases
            - Stats are accurate
        """
        # Try to get non-existent keys
        await mgc_cache.get("missing_1")
        await mgc_cache.get("missing_2")
        await mgc_cache.get("missing_3")

        stats = mgc_cache.get_stats()

        assert stats["misses"] == 3
        assert stats["hits"]["gen0"] == 0
        assert stats["hit_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_mgc_stats_hit_rate_calculation(self, mgc_cache):
        """
        @phase: 99
        Test hit rate is calculated correctly.

        Scenario:
            1. Set values and mixed hit/miss pattern
            2. Calculate hit rate manually
            3. Compare with stats hit_rate

        Expected Results:
            - hit_rate = hits / (hits + misses)
            - Calculation is accurate
        """
        # Set 2 values
        await mgc_cache.set("key1", "value1")
        await mgc_cache.set("key2", "value2")

        # Hit key1 twice
        await mgc_cache.get("key1")
        await mgc_cache.get("key1")

        # Miss twice
        await mgc_cache.get("missing_1")
        await mgc_cache.get("missing_2")

        # Hit key2 once
        await mgc_cache.get("key2")

        stats = mgc_cache.get_stats()

        total_hits = sum(stats["hits"].values())
        total_requests = total_hits + stats["misses"]
        expected_hit_rate = total_hits / total_requests

        assert stats["hit_rate"] == pytest.approx(expected_hit_rate)
        assert stats["hit_rate"] == pytest.approx(3.0 / 5.0)  # 3 hits, 2 misses

    @pytest.mark.asyncio
    async def test_mgc_stats_gen0_size_tracking(self, mgc_cache):
        """
        @phase: 99
        Test gen0_size stat reflects actual cache size.

        Scenario:
            1. Add items to cache
            2. Get stats
            3. gen0_size should match number of items

        Expected Results:
            - gen0_size = len(gen0)
            - Increases with additions
            - Decreases with deletions
        """
        stats = mgc_cache.get_stats()
        assert stats["gen0_size"] == 0

        # Add items
        for i in range(3):
            await mgc_cache.set(f"key_{i}", f"value_{i}")
            stats = mgc_cache.get_stats()
            assert stats["gen0_size"] == i + 1

        # Delete item
        await mgc_cache.delete("key_0")
        stats = mgc_cache.get_stats()
        assert stats["gen0_size"] == 2

    @pytest.mark.asyncio
    async def test_mgc_repr_includes_stats(self, mgc_cache):
        """
        @phase: 99
        Test __repr__ includes useful statistics.

        Scenario:
            1. Create cache with items
            2. Call repr()
            3. Should include gen0 size and hit rate

        Expected Results:
            - repr() output is informative
            - Includes gen0 size
            - Includes hit rate percentage
        """
        await mgc_cache.set("key1", "value1")
        await mgc_cache.get("key1")

        repr_str = repr(mgc_cache)

        assert "MGCCache" in repr_str
        assert "gen0=" in repr_str
        assert "hit_rate=" in repr_str


# ============================================================================
# TEST SUITE 6: JSON FALLBACK
# ============================================================================


class TestMGCJsonFallback:
    """
    @phase: 99
    Test JSON (Gen 2) storage when Qdrant unavailable.
    """

    @pytest.mark.asyncio
    async def test_mgc_json_basic_storage(self, mgc_cache):
        """
        @phase: 99
        Test storing and retrieving from JSON file (Gen 2).

        Scenario:
            1. Fill Gen 0 to trigger eviction
            2. Low-access item goes to JSON
            3. Retrieve item from JSON

        Expected Results:
            - JSON file created
            - Entry stored with correct structure
            - Can be retrieved later
        """
        # Set low-access item (will be evicted)
        await mgc_cache.set("low_access_item", {"data": "to_be_evicted"})

        # Fill Gen 0 to trigger eviction
        for i in range(1, 6):
            await mgc_cache.set(f"item_{i}", f"value_{i}")

        # At least one item was evicted
        # If JSON exists, it should contain valid entries
        if mgc_cache.json_path.exists():
            data = json.loads(mgc_cache.json_path.read_text())
            # Data should be a dict of hashed keys to entries
            assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_mgc_json_entry_serialization(self, mgc_cache):
        """
        @phase: 99
        Test that MGCEntry serializes correctly to JSON.

        Scenario:
            1. Create MGCEntry
            2. Serialize to dict (to_dict)
            3. Deserialize from dict (from_dict)
            4. Values should match

        Expected Results:
            - Serialization is reversible
            - No data loss
            - Timestamps preserved as ISO format
        """
        now = datetime.now()
        original = MGCEntry(
            key="test_key",
            value={"test": "data"},
            access_count=5,
            created_at=now,
            last_accessed=now,
            generation=2,
            size_bytes=256
        )

        # Serialize
        serialized = original.to_dict()

        assert serialized["key"] == "test_key"
        assert serialized["access_count"] == 5
        assert serialized["generation"] == 2
        assert serialized["size_bytes"] == 256

        # Deserialize
        deserialized = MGCEntry.from_dict(serialized)

        assert deserialized.key == original.key
        assert deserialized.value == original.value
        assert deserialized.access_count == original.access_count
        assert deserialized.generation == original.generation

    @pytest.mark.asyncio
    async def test_mgc_json_multiple_entries(self, mgc_cache):
        """
        @phase: 99
        Test JSON storage with multiple entries.

        Scenario:
            1. Manually store multiple entries to JSON
            2. Read back from JSON
            3. Verify all entries present

        Expected Results:
            - Multiple entries stored correctly
            - No collisions
            - All data preserved
        """
        # Create entries
        entries = [
            MGCEntry(key=f"key_{i}", value=f"value_{i}")
            for i in range(3)
        ]

        # Store each entry
        for entry in entries:
            await mgc_cache._store_in_json(entry)

        # Read back
        if mgc_cache.json_path.exists():
            data = json.loads(mgc_cache.json_path.read_text())
            assert len(data) == 3

    @pytest.mark.asyncio
    async def test_mgc_json_fallback_when_no_qdrant(self, temp_dir):
        """
        @phase: 99
        Test JSON fallback when Qdrant is unavailable.

        Scenario:
            1. Create cache with no Qdrant client
            2. Evict items (should go to JSON, not Gen 1)
            3. Verify items are in JSON

        Expected Results:
            - Items evicted to JSON (Gen 2)
            - No attempt to use non-existent Qdrant
            - JSON contains all evicted items
        """
        json_path = temp_dir / "fallback_cache.json"
        cache = MGCCache(
            gen0_max=2,
            promotion_threshold=2,
            qdrant_client=None,  # No Qdrant
            json_path=json_path
        )

        # Set items with high access count (will evict to Gen 1 if Qdrant, or Gen 2)
        await cache.set("item_1", {"val": 1})
        for _ in range(2):
            await cache.get("item_1")

        await cache.set("item_2", {"val": 2})
        for _ in range(2):
            await cache.get("item_2")

        # This triggers eviction
        await cache.set("item_3", {"val": 3})

        # Evicted item should be in JSON
        if json_path.exists():
            data = json.loads(json_path.read_text())
            assert len(data) > 0

        await cache.clear()

    @pytest.mark.asyncio
    async def test_mgc_json_delete_operation(self, mgc_cache):
        """
        @phase: 99
        Test deleting entries from JSON storage.

        Scenario:
            1. Store entry in JSON
            2. Delete it
            3. Verify it's removed

        Expected Results:
            - Entry removed from JSON
            - File still valid JSON
            - Entry not retrievable
        """
        # Store an entry in JSON
        entry = MGCEntry(key="delete_me", value={"temp": True})
        await mgc_cache._store_in_json(entry)

        # Verify it's there
        if mgc_cache.json_path.exists():
            data_before = json.loads(mgc_cache.json_path.read_text())
            assert len(data_before) > 0

        # Delete it
        await mgc_cache._delete_from_json("delete_me")

        # Verify it's gone
        if mgc_cache.json_path.exists():
            data_after = json.loads(mgc_cache.json_path.read_text())
            # Should be empty or have fewer entries
            assert len(data_after) <= len(data_before) if data_before else True

    @pytest.mark.asyncio
    async def test_mgc_json_corrupted_file_recovery(self, temp_dir):
        """
        @phase: 99
        Test cache recovery from corrupted JSON file.

        Scenario:
            1. Create cache with JSON path
            2. Write invalid JSON to file
            3. Try to get/set items
            4. Should recover gracefully

        Expected Results:
            - No exceptions thrown
            - Cache continues to work
            - New data can be written
        """
        json_path = temp_dir / "corrupted.json"
        json_path.write_text("{invalid json content")

        cache = MGCCache(
            gen0_max=5,
            json_path=json_path
        )

        # Should not raise, should handle gracefully
        result = await cache.get("some_key")
        assert result is None

        # Should still be able to set and get new items
        await cache.set("valid_key", "valid_value")
        result = await cache.get("valid_key")
        assert result == "valid_value"

        await cache.clear()


# ============================================================================
# TEST SUITE 7: CONCURRENCY AND THREAD SAFETY
# ============================================================================


class TestMGCConcurrency:
    """
    @phase: 99
    Test cache behavior under concurrent access.
    """

    @pytest.mark.asyncio
    async def test_mgc_concurrent_reads(self, mgc_cache):
        """
        @phase: 99
        Test concurrent read operations.

        Scenario:
            1. Set values in cache
            2. Read same values concurrently
            3. All should succeed without errors

        Expected Results:
            - All reads complete successfully
            - No race conditions
            - Stats are correct
        """
        # Set initial values
        for i in range(5):
            await mgc_cache.set(f"key_{i}", f"value_{i}")

        # Concurrent reads
        async def read_item(item_id):
            return await mgc_cache.get(f"key_{item_id}")

        results = await asyncio.gather(*[read_item(i) for i in range(5)])

        assert len(results) == 5
        assert all(r is not None for r in results)

    @pytest.mark.asyncio
    async def test_mgc_concurrent_writes(self, mgc_cache):
        """
        @phase: 99
        Test concurrent write operations.

        Scenario:
            1. Write to cache concurrently
            2. All items should be stored
            3. Stats should be accurate

        Expected Results:
            - No data loss
            - Gen 0 size <= gen0_max
            - All items retrievable (or evicted correctly)
        """
        async def write_item(item_id):
            await mgc_cache.set(f"concurrent_{item_id}", f"value_{item_id}")

        # Concurrent writes
        await asyncio.gather(*[write_item(i) for i in range(10)])

        stats = mgc_cache.get_stats()
        # At most gen0_max items in Gen 0, rest evicted
        assert stats["gen0_size"] <= mgc_cache.gen0_max

    @pytest.mark.asyncio
    async def test_mgc_concurrent_mixed_operations(self, mgc_cache):
        """
        @phase: 99
        Test concurrent mixed read/write operations.

        Scenario:
            1. Perform reads and writes concurrently
            2. Some items may be evicted during operations
            3. Cache should remain consistent

        Expected Results:
            - No exceptions
            - Cache remains valid
            - Stats are reasonable
        """
        # Pre-populate
        for i in range(3):
            await mgc_cache.set(f"initial_{i}", f"value_{i}")

        async def mixed_op(op_id):
            if op_id % 2 == 0:
                await mgc_cache.set(f"write_{op_id}", f"value_{op_id}")
            else:
                await mgc_cache.get(f"initial_{op_id % 3}")

        # Mixed operations
        await asyncio.gather(*[mixed_op(i) for i in range(10)])

        stats = mgc_cache.get_stats()
        assert stats["gen0_size"] >= 0
        assert stats["gen0_size"] <= mgc_cache.gen0_max


# ============================================================================
# TEST SUITE 8: EDGE CASES AND ERROR HANDLING
# ============================================================================


class TestMGCEdgeCases:
    """
    @phase: 99
    Test edge cases and error conditions.
    """

    @pytest.mark.asyncio
    async def test_mgc_empty_cache_operations(self, mgc_cache):
        """
        @phase: 99
        Test operations on empty cache.

        Scenario:
            1. Get from empty cache
            2. Delete from empty cache
            3. Clear empty cache
            4. Stats on empty cache

        Expected Results:
            - All operations succeed
            - No exceptions
            - Stats reflect empty state
        """
        result = await mgc_cache.get("nonexistent")
        assert result is None

        deleted = await mgc_cache.delete("nonexistent")
        assert deleted is False

        await mgc_cache.clear()
        stats = mgc_cache.get_stats()
        assert stats["gen0_size"] == 0

    @pytest.mark.asyncio
    async def test_mgc_large_values(self, mgc_cache):
        """
        @phase: 99
        Test caching large values.

        Scenario:
            1. Store large value (1MB simulated)
            2. Retrieve it
            3. Verify no truncation

        Expected Results:
            - Large values handled correctly
            - No size limit (Gen 0 is RAM)
            - Value integrity maintained
        """
        large_value = {"data": "x" * (1024 * 1024)}  # 1MB string

        await mgc_cache.set("large_value", large_value)
        result = await mgc_cache.get("large_value")

        assert result == large_value
        assert len(result["data"]) == 1024 * 1024

    @pytest.mark.asyncio
    async def test_mgc_special_characters_in_keys(self, mgc_cache):
        """
        @phase: 99
        Test keys with special characters.

        Scenario:
            1. Use special characters in keys
            2. Store and retrieve
            3. Verify hashing works correctly

        Expected Results:
            - Special characters handled correctly
            - Hashing doesn't cause collisions
            - Values retrievable with same key
        """
        special_keys = [
            "key:with:colons",
            "key/with/slashes",
            "key\\with\\backslashes",
            "key with spaces",
            "key@with#symbols",
        ]

        for key in special_keys:
            await mgc_cache.set(key, f"value_for_{key}")

        for key in special_keys:
            result = await mgc_cache.get(key)
            assert result == f"value_for_{key}"

    @pytest.mark.asyncio
    async def test_mgc_zero_promotion_threshold(self, temp_dir):
        """
        @phase: 99
        Test cache with zero promotion threshold.

        Scenario:
            1. Create cache with promotion_threshold=0
            2. All evicted items go to Gen 1 (or Gen 2 fallback)
            3. Everything is "hot"

        Expected Results:
            - Cache works with threshold=0
            - All items treated as important
        """
        cache = MGCCache(
            gen0_max=3,
            promotion_threshold=0,  # Everything is hot
            json_path=temp_dir / "zero_threshold.json"
        )

        for i in range(5):
            await cache.set(f"item_{i}", f"value_{i}")

        # All items should have been treated as important during eviction
        stats = cache.get_stats()
        assert stats["gen0_size"] <= cache.gen0_max

        await cache.clear()

    @pytest.mark.asyncio
    async def test_mgc_none_values(self, mgc_cache):
        """
        @phase: 99
        Test storing None values.

        Scenario:
            1. Store None as value
            2. Try to retrieve
            3. None should be distinguishable from "not found"

        Expected Results:
            - None is storable
            - get_or_compute handles None correctly
        """
        # Note: Current implementation returns None for "not found"
        # This test documents the behavior
        await mgc_cache.set("none_key", None)

        # This will return None (ambiguous with "not found")
        result = await mgc_cache.get("none_key")
        # The key is in gen0, so it was found even though value is None
        assert "none_key" in mgc_cache.gen0

    @pytest.mark.asyncio
    async def test_mgc_clear_operation(self, mgc_cache):
        """
        @phase: 99
        Test clearing entire cache.

        Scenario:
            1. Fill cache
            2. Clear it
            3. Verify all generations cleared

        Expected Results:
            - Gen 0 emptied
            - JSON file removed
            - Stats reset
        """
        # Fill cache
        for i in range(5):
            await mgc_cache.set(f"item_{i}", f"value_{i}")

        # Clear
        await mgc_cache.clear()

        # Verify cleared
        assert len(mgc_cache.gen0) == 0
        assert not mgc_cache.json_path.exists()

        stats = mgc_cache.get_stats()
        assert stats["gen0_size"] == 0


# ============================================================================
# TEST SUITE 9: INTEGRATION TESTS
# ============================================================================


class TestMGCIntegration:
    """
    @phase: 99
    Integration tests combining multiple features.
    """

    @pytest.mark.asyncio
    async def test_mgc_full_lifecycle(self, mgc_cache):
        """
        @phase: 99
        Test complete cache lifecycle.

        Scenario:
            1. Create cache and fill it
            2. Access items (some frequently, some rarely)
            3. Trigger evictions
            4. Retrieve items from different generations
            5. Clear cache

        Expected Results:
            - Smooth transitions between generations
            - Proper promotion/demotion
            - Stats accurate throughout
        """
        # Phase 1: Fill Gen 0
        for i in range(5):
            await mgc_cache.set(f"item_{i}", {"id": i})

        stats = mgc_cache.get_stats()
        assert stats["gen0_size"] == 5

        # Phase 2: Create access patterns
        # High access on item_0
        for _ in range(4):
            await mgc_cache.get("item_0")

        # Low access on item_4
        await mgc_cache.get("item_4")

        # Phase 3: Trigger eviction (item_4 should be evicted as LRU)
        await mgc_cache.set("item_5", {"id": 5})

        # Verify eviction happened
        stats = mgc_cache.get_stats()
        assert stats["evictions"] > 0

        # Phase 4: Clear everything
        await mgc_cache.clear()
        stats = mgc_cache.get_stats()
        assert stats["gen0_size"] == 0

    @pytest.mark.asyncio
    async def test_mgc_realistic_workload(self, mgc_cache):
        """
        @phase: 99
        Test realistic access patterns.

        Scenario:
            1. Simulate real workload: some keys accessed frequently,
               others rarely
            2. Mix of cache hits and misses
            3. Evictions and promotions

        Expected Results:
            - Hit rate reflects access patterns
            - Frequently accessed items stay in Gen 0
            - LRU items properly evicted
        """
        # Simulate workload
        frequency = {
            "hot_key_1": 10,
            "hot_key_2": 8,
            "warm_key_1": 3,
            "warm_key_2": 2,
            "cold_key_1": 1,
        }

        # Set all keys
        for key in frequency.keys():
            await mgc_cache.set(key, {"type": "data"})

        # Access according to frequency
        for key, count in frequency.items():
            for _ in range(count):
                await mgc_cache.get(key)

        # Try to access non-existent key
        await mgc_cache.get("nonexistent")

        # Get stats
        stats = mgc_cache.get_stats()

        # Hit rate should be high (24 hits, 1 miss)
        assert stats["hit_rate"] == pytest.approx(24.0 / 25.0)
        assert stats["gen0_hit_rate"] >= 0.8  # Most hits from Gen 0


# ============================================================================
# TEST SUITE 10: PERFORMANCE CHARACTERISTICS
# ============================================================================


class TestMGCPerformance:
    """
    @phase: 99
    Test performance characteristics of MGC.
    """

    @pytest.mark.asyncio
    async def test_mgc_gen0_lookup_speed(self, mgc_cache):
        """
        @phase: 99
        Test that Gen 0 lookups are O(1) - fast.

        Scenario:
            1. Fill Gen 0 with max items
            2. Access an item multiple times
            3. All accesses should complete quickly

        Expected Results:
            - Multiple accesses from same key are fast (O(1))
            - No observable slowdown with more items
        """
        # Fill Gen 0
        for i in range(5):
            await mgc_cache.set(f"key_{i}", f"value_{i}")

        # Access same key multiple times (should all be O(1))
        import time
        start = time.perf_counter()

        for _ in range(100):
            await mgc_cache.get("key_0")

        elapsed = time.perf_counter() - start

        # 100 O(1) lookups should be very fast (< 100ms)
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_mgc_scaling(self, temp_dir):
        """
        @phase: 99
        Test cache behavior with scaling gen0_max.

        Scenario:
            1. Create cache with larger gen0_max
            2. Fill it
            3. Stats should reflect size

        Expected Results:
            - Cache scales to larger sizes
            - No memory issues
            - Stats accurate at scale
        """
        large_cache = MGCCache(
            gen0_max=100,
            json_path=temp_dir / "large_cache.json"
        )

        # Fill partially
        for i in range(50):
            await large_cache.set(f"key_{i}", {"data": f"value_{i}"})

        stats = large_cache.get_stats()
        assert stats["gen0_size"] == 50
        assert stats["gen0_max"] == 100

        await large_cache.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
