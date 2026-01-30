"""
VETKA Phase 99 Integration Tests

Tests the full memory flow: CAM → STM → MGC
Verifies that all Phase 99 components work together correctly.

@file test_phase99_integration.py
@status active
@phase 99
@depends pytest, pytest-asyncio, src.memory
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path
import tempfile

from src.memory.stm_buffer import STMBuffer, STMEntry, get_stm_buffer, reset_stm_buffer
from src.memory.mgc_cache import MGCCache, MGCEntry, get_mgc_cache, reset_mgc_cache
from src.memory.memory_proxy import (
    MemoryProxy,
    CircuitBreakerOpen,
    get_memory_proxy,
    reset_all_proxies,
)


# ============================================================
# INTEGRATION TEST: Full CAM → STM → MGC Flow
# ============================================================

class TestPhase99Integration:
    """Integration tests for Phase 99 memory architecture."""

    def setup_method(self):
        """Reset singletons before each test."""
        reset_stm_buffer()
        reset_mgc_cache()
        reset_all_proxies()

    def teardown_method(self):
        """Cleanup after each test."""
        reset_stm_buffer()
        reset_mgc_cache()
        reset_all_proxies()

    # --- CAM → STM Integration ---

    def test_cam_surprise_to_stm(self):
        """
        Test that CAM surprise events are properly added to STM.

        Scenario:
        1. Simulate CAM detecting surprise content
        2. Add to STM via add_from_cam()
        3. Verify boosted weight and correct source
        """
        # Use decay_rate=0.0 to isolate surprise boost from decay effects
        stm = STMBuffer(max_size=10, decay_rate=0.0)

        # Simulate CAM surprise event
        surprise_content = "Novel concept: quantum entanglement in neural networks"
        surprise_score = 0.75

        stm.add_from_cam(surprise_content, surprise_score)

        # Verify entry
        entries = stm.get_context(max_items=1)
        assert len(entries) == 1
        entry = entries[0]

        assert entry.content == surprise_content
        assert entry.source == "cam_surprise"
        assert entry.surprise_score == surprise_score
        # Boosted weight = 1.0 + surprise_score (with decay_rate=0, no further modification)
        assert entry.weight == pytest.approx(1.75, rel=0.01)

    def test_cam_surprise_priority_over_regular(self):
        """
        Test that high-surprise items have priority in STM context.

        Scenario:
        1. Add regular message
        2. Add CAM surprise with high score
        3. Verify surprise item appears first in context
        """
        stm = STMBuffer(max_size=10, decay_rate=0.0)  # No decay for this test

        # Regular message
        stm.add_message("Regular chat message", source="user")

        # CAM surprise (higher priority)
        stm.add_from_cam("Unexpected pattern detected", surprise_score=0.9)

        context = stm.get_context(max_items=2)

        # Surprise should be first (weight 1.9 vs 1.0)
        assert context[0].source == "cam_surprise"
        assert context[0].weight > context[1].weight

    # --- STM Adaptive Decay (FIX_99.2) ---

    def test_adaptive_decay_preserves_surprise(self):
        """
        Test FIX_99.2: Surprise items decay 30% slower.

        Scenario:
        1. Add regular item and surprise item with same initial weight
        2. Apply decay
        3. Verify surprise item retains more weight
        """
        stm = STMBuffer(max_size=10, decay_rate=0.5)  # High decay for visible effect

        # Add entries manually with controlled timestamps
        regular_entry = STMEntry(
            content="Regular item",
            timestamp=datetime.now() - timedelta(seconds=60),  # 1 minute old
            source="user",
            weight=1.0,
            surprise_score=0.0
        )
        surprise_entry = STMEntry(
            content="Surprise item",
            timestamp=datetime.now() - timedelta(seconds=60),  # Same age
            source="cam_surprise",
            weight=1.0,
            surprise_score=1.0  # Max surprise
        )

        stm._buffer.append(regular_entry)
        stm._buffer.append(surprise_entry)

        # Apply decay
        stm._apply_decay()

        # Get entries
        entries = list(stm._buffer)

        # With decay_rate=0.5, after 1 minute:
        # Base decay_factor = 1 - 0.5 * 1 = 0.5
        # Regular: weight = 1.0 * 0.5 * 1.0 = 0.5
        # Surprise: weight = 1.0 * 0.5 * 1.3 = 0.65 (30% preservation)

        regular_weight = entries[0].weight
        surprise_weight = entries[1].weight

        assert surprise_weight > regular_weight
        # Surprise should be ~30% higher
        assert surprise_weight / regular_weight == pytest.approx(1.3, rel=0.1)

    # --- STM → MGC Overflow ---

    @pytest.mark.asyncio
    async def test_stm_overflow_to_mgc(self):
        """
        Test that STM overflow could trigger MGC storage.

        Scenario:
        1. Fill STM to capacity
        2. Add one more item (triggers eviction)
        3. Verify oldest item is removed from STM
        4. (In real implementation, evicted items could go to MGC)
        """
        stm = STMBuffer(max_size=3, decay_rate=0.0)
        mgc = MGCCache(gen0_max=10)

        # Fill STM
        for i in range(3):
            stm.add_message(f"Message {i}", source="user")
            await asyncio.sleep(0.01)  # Ensure different timestamps

        assert len(stm) == 3

        # Add one more - oldest should be evicted
        stm.add_message("Message 3 (overflow)", source="user")

        assert len(stm) == 3  # Still 3 (max_size)

        # Verify oldest was evicted
        contents = [e.content for e in stm.get_all()]
        assert "Message 0" not in contents
        assert "Message 3 (overflow)" in contents

    # --- MGC Multi-Generation Flow ---

    @pytest.mark.asyncio
    async def test_mgc_generation_flow(self):
        """
        Test MGC promotion/demotion between generations.

        Scenario:
        1. Add items to Gen 0 (RAM)
        2. Fill Gen 0 to capacity
        3. Trigger eviction
        4. Verify LRU item demoted
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "mgc_test.json"
            mgc = MGCCache(gen0_max=3, promotion_threshold=2, json_path=json_path)

            # Add items
            await mgc.set("key1", "value1")
            await mgc.set("key2", "value2")
            await mgc.set("key3", "value3")

            # Access key2 and key3 multiple times (will be promoted)
            for _ in range(3):
                await mgc.get("key2")
                await mgc.get("key3")

            # Gen 0 is full, add new item - key1 should be evicted (LRU)
            await mgc.set("key4", "value4")

            # Verify key1 evicted from Gen 0
            assert "key1" not in mgc.gen0
            assert "key4" in mgc.gen0

            stats = mgc.get_stats()
            assert stats["evictions"] >= 1

    # --- MemoryProxy Protection ---

    @pytest.mark.asyncio
    async def test_proxy_protects_memory_operations(self):
        """
        Test that MemoryProxy protects memory operations.

        Scenario:
        1. Create proxy with rate limiting
        2. Execute multiple operations rapidly
        3. Verify rate limiting kicks in (throttles, doesn't reject)
        """
        proxy = MemoryProxy(
            max_concurrent=5,
            rate_limit=5,  # Low limit to trigger throttling faster
            dedup_window=0.01,  # Short dedup window
            enable_circuit_breaker=False  # Focus on rate limiting
        )

        async def dummy_operation():
            return "success"

        # Execute operations rapidly (no sleep between them)
        results = []
        for i in range(20):
            result = await proxy.execute(f"key_{i}", dummy_operation)
            results.append(result)

        # All should succeed (rate limiting just throttles, doesn't reject)
        assert len(results) == 20
        assert all(r == "success" for r in results)

        stats = proxy.get_stats()
        assert stats["total_requests"] == 20
        # Rate limiting should have triggered at least once
        # (throttles when exceeding rate_limit per second window)
        assert stats["rate_limited"] >= 1

    @pytest.mark.asyncio
    async def test_proxy_circuit_breaker_integration(self):
        """
        Test circuit breaker protects against cascading failures.

        Scenario:
        1. Create proxy with circuit breaker
        2. Simulate repeated failures
        3. Verify circuit opens
        4. Verify subsequent requests blocked
        """
        proxy = MemoryProxy(
            max_concurrent=5,
            rate_limit=100,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=1.0
        )

        failure_count = 0

        async def failing_operation():
            nonlocal failure_count
            failure_count += 1
            raise RuntimeError("Simulated failure")

        # Trigger failures until circuit opens
        for i in range(5):
            try:
                await proxy.execute(f"fail_{i}", failing_operation)
            except (RuntimeError, CircuitBreakerOpen):
                pass

        # Circuit should be open after 3 failures
        assert proxy._circuit_open

        # Next request should be blocked immediately
        with pytest.raises(CircuitBreakerOpen):
            await proxy.execute("blocked", failing_operation)

    # --- Full Integration: CAM → STM → MGC with Proxy ---

    @pytest.mark.asyncio
    async def test_full_memory_pipeline(self):
        """
        Test complete Phase 99 memory pipeline.

        Scenario:
        1. CAM detects surprise content
        2. Surprise added to STM
        3. STM applies adaptive decay
        4. Frequently accessed items cached in MGC
        5. All operations protected by MemoryProxy
        """
        # Initialize components
        stm = STMBuffer(max_size=5, decay_rate=0.1)
        mgc = MGCCache(gen0_max=10)
        proxy = MemoryProxy(max_concurrent=10, rate_limit=100)

        # Step 1: CAM surprise events
        surprises = [
            ("New architecture pattern", 0.8),
            ("Unexpected optimization", 0.6),
            ("Regular observation", 0.2),
        ]

        for content, score in surprises:
            stm.add_from_cam(content, score)

        assert len(stm) == 3

        # Step 2: Get context (triggers decay)
        context = stm.get_context(max_items=3)

        # Highest surprise should be first
        assert context[0].content == "New architecture pattern"
        assert context[0].surprise_score == 0.8

        # Step 3: Cache in MGC via proxy
        async def cache_context():
            context_str = stm.get_context_string()
            await mgc.set("stm_snapshot", context_str)
            return context_str

        cached = await proxy.execute("cache_stm", cache_context)
        assert cached is not None

        # Step 4: Retrieve from MGC
        retrieved = await mgc.get("stm_snapshot")
        assert retrieved is not None
        assert "New architecture pattern" in retrieved

        # Step 5: Verify stats
        proxy_stats = proxy.get_stats()
        mgc_stats = mgc.get_stats()

        assert proxy_stats["total_requests"] >= 1
        assert mgc_stats["hits"]["gen0"] >= 1

    # --- Edge Cases ---

    def test_empty_stm_to_mgc(self):
        """Test handling of empty STM buffer."""
        stm = STMBuffer(max_size=5)
        context = stm.get_context()
        assert context == []
        assert stm.get_context_string() == ""

    @pytest.mark.asyncio
    async def test_mgc_fallback_to_json(self):
        """Test MGC falls back to JSON when Qdrant unavailable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "fallback.json"
            mgc = MGCCache(gen0_max=2, qdrant_client=None, json_path=json_path)

            # Fill Gen 0
            await mgc.set("key1", "value1")
            await mgc.set("key2", "value2")

            # Trigger eviction to JSON
            await mgc.set("key3", "value3")

            # Verify JSON file created
            assert json_path.exists()

    def test_stm_serialization_with_surprise(self):
        """Test STM serialization preserves surprise scores."""
        stm = STMBuffer(max_size=5)
        stm.add_from_cam("Surprise content", surprise_score=0.9)

        # Serialize
        data = stm.to_dict()

        # Restore
        restored = STMBuffer.from_dict(data)

        # Verify
        entries = restored.get_context()
        assert len(entries) == 1
        assert entries[0].surprise_score == 0.9


# ============================================================
# Run tests
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
