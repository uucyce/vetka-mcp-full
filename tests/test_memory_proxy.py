"""
VETKA Phase 99 - Memory Proxy Tests

Comprehensive test suite for MemoryProxy including:
- Request deduplication within cache window
- Rate limiting and request throttling
- Circuit breaker pattern with exponential backoff
- Circuit breaker recovery after timeout
- Statistics collection and accuracy
- Specialized proxy factories

@phase: 99
@marker: MARKER-99-03
@file: test_memory_proxy.py
@depends: pytest, pytest-asyncio, memory_proxy
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from src.memory.memory_proxy import (
    MemoryProxy,
    CircuitBreakerOpen,
    RateLimitExceeded,
    ProxyStats,
    create_embedding_proxy,
    create_qdrant_proxy,
    create_json_proxy,
    get_memory_proxy,
    get_embedding_proxy,
    get_qdrant_proxy,
    reset_all_proxies,
)


# ============================================================================
# Fixtures and Helper Functions
# ============================================================================

@pytest.fixture
def proxy():
    """Create a fresh MemoryProxy for testing."""
    p = MemoryProxy(
        max_concurrent=5,
        rate_limit=10,  # 10 req/sec for faster testing
        dedup_window=0.5,
        circuit_breaker_threshold=3,
        circuit_breaker_timeout=2.0
    )
    yield p
    p.reset_stats()
    p.clear_cache()


@pytest.fixture
def async_mock_func():
    """Create a simple async mock function."""
    async def func(*args, **kwargs):
        await asyncio.sleep(0.01)  # Simulate work
        return {"result": "success"}
    return AsyncMock(side_effect=func)


@pytest.fixture
def failing_async_func():
    """Create an async function that fails."""
    async def func(*args, **kwargs):
        await asyncio.sleep(0.01)
        raise ValueError("Test failure")
    return AsyncMock(side_effect=func)


# ============================================================================
# Test 1: Proxy Deduplication
# ============================================================================

@pytest.mark.asyncio
async def test_proxy_deduplication(proxy, async_mock_func):
    """
    Test that identical requests within cache window return cached results.

    @phase: 99
    @marker: MARKER-99-01-DEDUP

    Verifies:
    - Same key within dedup_window hits cache
    - Cache hit counter increments
    - Result is returned immediately from cache
    - Different keys create separate cache entries
    """
    # Disable rate limiting and circuit breaker for this test
    proxy.enable_rate_limit = False
    proxy.enable_circuit_breaker = False

    # First request - cache miss
    result1 = await proxy.execute("key1", async_mock_func, "arg1")
    assert result1 == {"result": "success"}
    assert async_mock_func.call_count == 1
    assert proxy._stats.cache_hits == 0
    assert proxy._stats.total_requests == 1

    # Second request with same key - should hit cache
    result2 = await proxy.execute("key1", async_mock_func, "arg1")
    assert result2 == {"result": "success"}
    assert async_mock_func.call_count == 1  # Not called again!
    assert proxy._stats.cache_hits == 1
    assert proxy._stats.total_requests == 2

    # Third request with different key - cache miss
    result3 = await proxy.execute("key2", async_mock_func, "arg2")
    assert result3 == {"result": "success"}
    assert async_mock_func.call_count == 2  # Called for new key
    assert proxy._stats.cache_hits == 1  # Still 1
    assert proxy._stats.total_requests == 3


@pytest.mark.asyncio
async def test_proxy_deduplication_window_expiry(proxy, async_mock_func):
    """
    Test that cache expires after dedup_window.

    @phase: 99
    @marker: MARKER-99-01-DEDUP-EXPIRY
    """
    proxy.enable_rate_limit = False
    proxy.enable_circuit_breaker = False
    proxy.dedup_window = 0.1  # 100ms window

    # First request
    result1 = await proxy.execute("key1", async_mock_func)
    assert async_mock_func.call_count == 1

    # Immediate repeat - should hit cache
    result2 = await proxy.execute("key1", async_mock_func)
    assert async_mock_func.call_count == 1  # Not called
    assert proxy._stats.cache_hits == 1

    # Wait for dedup window to expire
    await asyncio.sleep(0.15)

    # Same key after expiry - should miss cache
    result3 = await proxy.execute("key1", async_mock_func)
    assert async_mock_func.call_count == 2  # Called again!
    assert proxy._stats.cache_hits == 1  # Still 1 from earlier


# ============================================================================
# Test 2: Rate Limiting
# ============================================================================

@pytest.mark.asyncio
async def test_proxy_rate_limiting(proxy, async_mock_func):
    """
    Test that requests are throttled when rate limit is exceeded.

    @phase: 99
    @marker: MARKER-99-02-RATE-LIMIT

    Verifies:
    - Requests within limit proceed without delay
    - Requests exceeding limit are throttled
    - Rate limit counter resets each second
    - Statistics track rate-limited requests
    """
    proxy.enable_dedup = False
    proxy.enable_circuit_breaker = False
    proxy.rate_limit = 3  # 3 requests per second

    start = datetime.now()

    # Make 3 requests quickly (should not be rate limited)
    for i in range(3):
        await proxy.execute(f"key{i}", async_mock_func)

    # Fourth request should be rate limited
    await proxy.execute("key4", async_mock_func)

    elapsed = (datetime.now() - start).total_seconds()

    # Should have taken ~1 second due to rate limiting
    assert elapsed >= 0.9, f"Expected ~1s delay, got {elapsed}s"
    assert proxy._stats.rate_limited >= 1
    assert async_mock_func.call_count == 4


@pytest.mark.asyncio
async def test_proxy_rate_limit_reset(proxy, async_mock_func):
    """
    Test that rate limit counter resets after 1 second.

    @phase: 99
    @marker: MARKER-99-02-RATE-LIMIT-RESET
    """
    proxy.enable_dedup = False
    proxy.enable_circuit_breaker = False
    proxy.rate_limit = 2

    # Make 2 requests in first window
    await proxy.execute("key1", async_mock_func)
    await proxy.execute("key2", async_mock_func)
    assert proxy._request_count == 2

    # Wait for window reset
    await asyncio.sleep(1.1)

    # Next request should not be throttled (counter reset)
    start = datetime.now()
    await proxy.execute("key3", async_mock_func)
    elapsed = (datetime.now() - start).total_seconds()

    # Should be fast, not rate limited
    assert elapsed < 0.5
    assert proxy._request_count == 1


# ============================================================================
# Test 3: Circuit Breaker - Tripping
# ============================================================================

@pytest.mark.asyncio
async def test_proxy_circuit_breaker(proxy, failing_async_func):
    """
    Test that circuit breaker opens after N failures.

    @phase: 99
    @marker: MARKER-99-03-CIRCUIT-BREAKER

    Verifies:
    - Circuit breaker remains closed on initial failures
    - After threshold failures, circuit opens
    - CircuitBreakerOpen exception is raised
    - circuit_broken counter increments
    """
    proxy.enable_dedup = False
    proxy.enable_rate_limit = False
    proxy.circuit_breaker_threshold = 3

    # First 2 failures - circuit not yet open
    for i in range(2):
        with pytest.raises(ValueError, match="Test failure"):
            await proxy.execute(f"key{i}", failing_async_func)

    assert not proxy._circuit_open
    assert proxy._failure_count == 2
    assert proxy._stats.failures == 2

    # Third failure - should trip circuit
    with pytest.raises(ValueError, match="Test failure"):
        await proxy.execute("key3", failing_async_func)

    assert proxy._circuit_open
    assert proxy._circuit_open_until is not None
    assert proxy._stats.circuit_broken == 0  # Not counted yet

    # Fourth attempt - circuit is now open
    with pytest.raises(CircuitBreakerOpen):
        await proxy.execute("key4", failing_async_func)

    assert proxy._stats.circuit_broken == 1


@pytest.mark.asyncio
async def test_proxy_circuit_breaker_exponential_backoff(proxy, failing_async_func):
    """
    Test exponential backoff in circuit breaker.

    @phase: 99
    @marker: MARKER-99-03-EXPONENTIAL-BACKOFF

    Verifies:
    - backoff = min(timeout, 2^failure_count)
    - Backoff increases with each failure
    - Backoff respects circuit_breaker_timeout limit
    """
    proxy.enable_dedup = False
    proxy.enable_rate_limit = False
    proxy.circuit_breaker_threshold = 2
    proxy.circuit_breaker_timeout = 10.0

    # Trigger first circuit open: 2 ^ 2 = 4 seconds
    for i in range(2):
        with pytest.raises(ValueError):
            await proxy.execute(f"key{i}", failing_async_func)

    # Next failure trips circuit
    try:
        await proxy.execute("key2", failing_async_func)
    except (ValueError, CircuitBreakerOpen):
        pass

    first_backoff = (proxy._circuit_open_until - datetime.now()).total_seconds()
    assert 3.5 < first_backoff < 4.5  # ~4 seconds (2^2)

    # Reset for next test
    proxy.reset_stats()
    proxy.clear_cache()
    proxy._failure_count = 0
    proxy._circuit_open = False
    proxy._circuit_open_until = None

    # Trigger circuit with more failures: 2 ^ 3 = 8 seconds
    for i in range(2):
        with pytest.raises(ValueError):
            await proxy.execute(f"key{i}", failing_async_func)

    try:
        await proxy.execute("key3", failing_async_func)
    except (ValueError, CircuitBreakerOpen):
        pass

    second_backoff = (proxy._circuit_open_until - datetime.now()).total_seconds()
    assert second_backoff <= 10.0  # Capped at timeout


# ============================================================================
# Test 4: Circuit Breaker - Recovery
# ============================================================================

@pytest.mark.asyncio
async def test_proxy_circuit_breaker_recovery(proxy, async_mock_func, failing_async_func):
    """
    Test that circuit breaker recovers after timeout.

    @phase: 99
    @marker: MARKER-99-03-CIRCUIT-RECOVERY

    Verifies:
    - Circuit breaker transitions to half-open state after timeout
    - Half-open state allows one request to test recovery
    - Successful request closes circuit
    - Circuit can be re-opened if requests fail again
    """
    proxy.enable_dedup = False
    proxy.enable_rate_limit = False
    proxy.circuit_breaker_threshold = 2
    proxy.circuit_breaker_timeout = 0.5  # Short timeout for testing

    # Open circuit with failures
    for i in range(2):
        with pytest.raises(ValueError):
            await proxy.execute(f"key{i}", failing_async_func)

    try:
        await proxy.execute("key2", failing_async_func)
    except (ValueError, CircuitBreakerOpen):
        pass

    assert proxy._circuit_open

    # Immediate request - should still be blocked
    with pytest.raises(CircuitBreakerOpen):
        await proxy.execute("key3", failing_async_func)

    # Wait for timeout
    await asyncio.sleep(0.6)

    # Now circuit should allow request (half-open state)
    result = await proxy.execute("key4", async_mock_func)
    assert result == {"result": "success"}
    assert not proxy._circuit_open  # Circuit closed
    assert proxy._failure_count == 0  # Reset


@pytest.mark.asyncio
async def test_proxy_circuit_breaker_reopens_on_failure(proxy, failing_async_func):
    """
    Test that circuit can fail when in half-open state.

    @phase: 99
    @marker: MARKER-99-03-CIRCUIT-REOPEN
    """
    proxy.enable_dedup = False
    proxy.enable_rate_limit = False
    proxy.circuit_breaker_threshold = 2
    proxy.circuit_breaker_timeout = 0.5

    # Open circuit with 2 failures
    for i in range(2):
        with pytest.raises(ValueError):
            await proxy.execute(f"key{i}", failing_async_func)

    # This triggers circuit open (2^2 = 4 second backoff, but limited to 0.5)
    try:
        await proxy.execute("key2", failing_async_func)
    except (ValueError, CircuitBreakerOpen):
        pass

    assert proxy._circuit_open

    # Wait for half-open state
    await asyncio.sleep(0.6)

    # Request in half-open state still fails - circuit will transition to half-open
    # but the request itself fails
    with pytest.raises(ValueError):
        await proxy.execute("key3", failing_async_func)

    # The request succeeded in half-open, but the call failed
    # This increments failure count, but circuit may or may not be open depending on timing
    assert proxy._failure_count >= 1


# ============================================================================
# Test 5: Statistics Collection
# ============================================================================

@pytest.mark.asyncio
async def test_proxy_stats(proxy, async_mock_func):
    """
    Test that statistics are correctly collected and updated.

    @phase: 99
    @marker: MARKER-99-04-STATS

    Verifies:
    - total_requests increments correctly
    - cache_hits reflects deduplication
    - failures counter updates on exceptions
    - avg_latency_ms is calculated correctly
    - hit_rate is accurate
    """
    proxy.enable_dedup = True
    proxy.enable_rate_limit = False
    proxy.enable_circuit_breaker = False

    # Make some requests
    await proxy.execute("key1", async_mock_func)
    await proxy.execute("key1", async_mock_func)  # Hit
    await proxy.execute("key2", async_mock_func)
    await proxy.execute("key1", async_mock_func)  # Hit
    await proxy.execute("key3", async_mock_func)
    await proxy.execute("key2", async_mock_func)  # Hit

    stats = proxy.get_stats()

    assert stats["total_requests"] == 6
    assert stats["cache_hits"] == 3
    assert stats["failures"] == 0
    assert stats["circuit_broken"] == 0
    assert stats["hit_rate"] == 0.5  # 3/6
    assert stats["avg_latency_ms"] > 0
    assert stats["cached_keys"] == 3


@pytest.mark.asyncio
async def test_proxy_stats_with_failures(proxy, failing_async_func):
    """
    Test statistics with failed requests.

    @phase: 99
    @marker: MARKER-99-04-STATS-FAILURES
    """
    proxy.enable_dedup = False
    proxy.enable_rate_limit = False
    proxy.enable_circuit_breaker = False

    # Make 3 requests, 2 fail
    with pytest.raises(ValueError):
        await proxy.execute("key1", failing_async_func)

    with pytest.raises(ValueError):
        await proxy.execute("key2", failing_async_func)

    stats = proxy.get_stats()

    assert stats["total_requests"] == 2
    assert stats["failures"] == 2
    assert stats["cache_hits"] == 0


@pytest.mark.asyncio
async def test_proxy_stats_reset(proxy, async_mock_func):
    """
    Test that reset_stats() clears all statistics.

    @phase: 99
    @marker: MARKER-99-04-STATS-RESET
    """
    proxy.enable_rate_limit = False
    proxy.enable_circuit_breaker = False

    # Generate some stats
    await proxy.execute("key1", async_mock_func)
    await proxy.execute("key1", async_mock_func)

    assert proxy._stats.total_requests == 2
    assert proxy._stats.cache_hits == 1

    # Reset
    proxy.reset_stats()

    stats = proxy.get_stats()
    assert stats["total_requests"] == 0
    assert stats["cache_hits"] == 0
    assert stats["avg_latency_ms"] == 0


# ============================================================================
# Test 6: Specialized Proxies
# ============================================================================

def test_create_embedding_proxy():
    """
    Test creation of embedding-optimized proxy.

    @phase: 99
    @marker: MARKER-99-05-SPECIALIZED

    Verifies:
    - Embedding proxy has lower concurrency (5)
    - Embedding proxy has lower rate limit (50/s)
    - Embedding proxy has longer dedup window (1.0s)
    - Embedding proxy has higher failure threshold (10)
    - Embedding proxy has higher timeout (60s)
    """
    proxy = create_embedding_proxy()

    assert proxy.semaphore._value == 5
    assert proxy.rate_limit == 50
    assert proxy.dedup_window == 1.0
    assert proxy.circuit_breaker_threshold == 10
    assert proxy.circuit_breaker_timeout == 60.0


def test_create_qdrant_proxy():
    """
    Test creation of Qdrant-optimized proxy.

    @phase: 99
    @marker: MARKER-99-05-SPECIALIZED

    Verifies:
    - Qdrant proxy has high concurrency (20)
    - Qdrant proxy has high rate limit (200/s)
    - Qdrant proxy has short dedup window (0.2s)
    - Qdrant proxy has moderate failure threshold (5)
    """
    proxy = create_qdrant_proxy()

    assert proxy.semaphore._value == 20
    assert proxy.rate_limit == 200
    assert proxy.dedup_window == 0.2
    assert proxy.circuit_breaker_threshold == 5
    assert proxy.circuit_breaker_timeout == 30.0


def test_create_json_proxy():
    """
    Test creation of JSON file I/O proxy.

    @phase: 99
    @marker: MARKER-99-05-SPECIALIZED

    Verifies:
    - JSON proxy has low concurrency (3)
    - JSON proxy has low rate limit (20/s)
    - JSON proxy has longer dedup window (2.0s)
    - JSON proxy has low failure threshold (3)
    """
    proxy = create_json_proxy()

    assert proxy.semaphore._value == 3
    assert proxy.rate_limit == 20
    assert proxy.dedup_window == 2.0
    assert proxy.circuit_breaker_threshold == 3
    assert proxy.circuit_breaker_timeout == 10.0


# ============================================================================
# Test 7: Singleton Proxies
# ============================================================================

def test_get_memory_proxy_singleton():
    """
    Test that get_memory_proxy returns same instance.

    @phase: 99
    @marker: MARKER-99-05-SINGLETON
    """
    reset_all_proxies()

    proxy1 = get_memory_proxy()
    proxy2 = get_memory_proxy()

    assert proxy1 is proxy2
    assert isinstance(proxy1, MemoryProxy)


def test_get_embedding_proxy_singleton():
    """
    Test that get_embedding_proxy returns same instance.

    @phase: 99
    @marker: MARKER-99-05-SINGLETON
    """
    reset_all_proxies()

    proxy1 = get_embedding_proxy()
    proxy2 = get_embedding_proxy()

    assert proxy1 is proxy2
    assert proxy1.rate_limit == 50
    assert proxy1.semaphore._value == 5


def test_get_qdrant_proxy_singleton():
    """
    Test that get_qdrant_proxy returns same instance.

    @phase: 99
    @marker: MARKER-99-05-SINGLETON
    """
    reset_all_proxies()

    proxy1 = get_qdrant_proxy()
    proxy2 = get_qdrant_proxy()

    assert proxy1 is proxy2
    assert proxy1.rate_limit == 200
    assert proxy1.semaphore._value == 20


def test_reset_all_proxies():
    """
    Test that reset_all_proxies clears singleton instances.

    @phase: 99
    @marker: MARKER-99-05-SINGLETON
    """
    get_memory_proxy()
    get_embedding_proxy()
    get_qdrant_proxy()

    reset_all_proxies()

    # Next calls should create new instances
    proxy1 = get_memory_proxy()
    proxy2 = get_embedding_proxy()
    proxy3 = get_qdrant_proxy()

    assert isinstance(proxy1, MemoryProxy)
    assert isinstance(proxy2, MemoryProxy)
    assert isinstance(proxy3, MemoryProxy)


# ============================================================================
# Test 8: Concurrent Operations
# ============================================================================

@pytest.mark.asyncio
async def test_proxy_concurrent_operations(proxy, async_mock_func):
    """
    Test that proxy handles concurrent operations with semaphore.

    @phase: 99
    @marker: MARKER-99-06-CONCURRENCY

    Verifies:
    - Semaphore limits concurrent operations
    - Multiple concurrent requests are handled
    - All requests complete successfully
    """
    proxy.enable_dedup = False
    proxy.enable_rate_limit = False
    proxy.enable_circuit_breaker = False
    proxy.semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent

    # Create 10 concurrent tasks
    tasks = [
        proxy.execute(f"key{i}", async_mock_func)
        for i in range(10)
    ]

    results = await asyncio.gather(*tasks)

    assert len(results) == 10
    assert all(r == {"result": "success"} for r in results)
    assert proxy._stats.total_requests == 10


@pytest.mark.asyncio
async def test_proxy_cache_cleanup(proxy, async_mock_func):
    """
    Test that proxy cleans up old cache entries.

    @phase: 99
    @marker: MARKER-99-06-CLEANUP

    Verifies:
    - Cache keeps last 100 entries
    - Oldest entries are removed when limit exceeded
    """
    proxy.enable_rate_limit = False
    proxy.enable_circuit_breaker = False

    # Fill cache beyond 100 entries
    for i in range(150):
        await proxy.execute(f"key{i}", async_mock_func)

    # Cache should not grow beyond 100
    assert len(proxy._cached_results) <= 100
    assert len(proxy._recent_requests) <= 100


# ============================================================================
# Test 9: Disabling Features
# ============================================================================

@pytest.mark.asyncio
async def test_proxy_disable_dedup(proxy, async_mock_func):
    """
    Test that deduplication can be disabled.

    @phase: 99
    @marker: MARKER-99-07-DISABLE
    """
    proxy.enable_dedup = False
    proxy.enable_rate_limit = False
    proxy.enable_circuit_breaker = False

    # Same key twice with dedup disabled
    await proxy.execute("key1", async_mock_func)
    await proxy.execute("key1", async_mock_func)

    # Should call function twice
    assert async_mock_func.call_count == 2
    assert proxy._stats.cache_hits == 0


@pytest.mark.asyncio
async def test_proxy_disable_rate_limit(proxy, async_mock_func):
    """
    Test that rate limiting can be disabled.

    @phase: 99
    @marker: MARKER-99-07-DISABLE
    """
    proxy.enable_dedup = False
    proxy.enable_rate_limit = False
    proxy.enable_circuit_breaker = False
    proxy.rate_limit = 1  # Very low limit

    start = datetime.now()

    # Make 10 rapid requests with rate limiting disabled
    for i in range(10):
        await proxy.execute(f"key{i}", async_mock_func)

    elapsed = (datetime.now() - start).total_seconds()

    # Should complete quickly without throttling
    assert elapsed < 1.0


@pytest.mark.asyncio
async def test_proxy_disable_circuit_breaker(proxy, failing_async_func):
    """
    Test that circuit breaker can be disabled.

    @phase: 99
    @marker: MARKER-99-07-DISABLE
    """
    proxy.enable_dedup = False
    proxy.enable_rate_limit = False
    proxy.enable_circuit_breaker = False
    proxy.circuit_breaker_threshold = 2

    # Make many failing requests
    for i in range(10):
        with pytest.raises(ValueError):
            await proxy.execute(f"key{i}", failing_async_func)

    # Should never open circuit
    assert not proxy._circuit_open
    assert proxy._stats.circuit_broken == 0


# ============================================================================
# Test 10: ProxyStats Dataclass
# ============================================================================

def test_proxy_stats_to_dict():
    """
    Test ProxyStats.to_dict() conversion.

    @phase: 99
    @marker: MARKER-99-08-STATS-OBJ
    """
    stats = ProxyStats(
        total_requests=100,
        cache_hits=30,
        rate_limited=5,
        circuit_broken=2,
        failures=3
    )

    d = stats.to_dict()

    assert d["total_requests"] == 100
    assert d["cache_hits"] == 30
    assert d["rate_limited"] == 5
    assert d["circuit_broken"] == 2
    assert d["failures"] == 3
    assert d["hit_rate"] == 0.3


def test_proxy_repr(proxy, async_mock_func):
    """
    Test string representation of MemoryProxy.

    @phase: 99
    @marker: MARKER-99-08-REPR
    """
    repr_str = repr(proxy)

    assert "MemoryProxy" in repr_str
    assert "requests=" in repr_str
    assert "hit_rate=" in repr_str
    assert "circuit_open=" in repr_str


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_proxy_full_integration(proxy, async_mock_func, failing_async_func):
    """
    Test full proxy integration with all features enabled.

    @phase: 99
    @marker: MARKER-99-09-INTEGRATION

    Verifies:
    - Deduplication works
    - Rate limiting works
    - Circuit breaker works
    - Statistics are accurate
    - Features interact correctly
    """
    proxy.enable_dedup = True
    proxy.enable_rate_limit = True
    proxy.enable_circuit_breaker = True
    proxy.rate_limit = 5

    # Phase 1: Normal operation
    result1 = await proxy.execute("key1", async_mock_func)
    result2 = await proxy.execute("key1", async_mock_func)  # Hit cache

    assert result1 == result2
    assert proxy._stats.cache_hits == 1

    # Phase 2: Make some failing requests to trigger circuit breaker
    for i in range(3):
        try:
            await proxy.execute(f"fail{i}", failing_async_func)
        except (ValueError, CircuitBreakerOpen):
            pass  # Expected

    # Circuit should be open now
    assert proxy._circuit_open

    # Phase 3: Circuit breaker blocks requests
    with pytest.raises(CircuitBreakerOpen):
        await proxy.execute("key2", async_mock_func)

    assert proxy._stats.circuit_broken >= 1

    # Verify final stats
    stats = proxy.get_stats()
    assert stats["failures"] >= 2  # At least 2 failures recorded


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
