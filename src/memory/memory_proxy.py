"""
VETKA Phase 99 - Memory Proxy

PgBouncer-like proxy to prevent vicious cycles and manage memory operations.
Provides rate limiting, connection pooling, deduplication, and circuit breaker.

@file memory_proxy.py
@status active
@phase 99
@depends asyncio, datetime, typing, logging, collections
@used_by qdrant_client.py, embedding_service.py, all memory operations

MARKER-99-03: Circuit breaker - backs off exponentially on repeated failures
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, Awaitable, TypeVar
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class ProxyStats:
    """Statistics for memory proxy operations."""
    total_requests: int = 0
    cache_hits: int = 0
    rate_limited: int = 0
    circuit_broken: int = 0
    failures: int = 0
    avg_latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "rate_limited": self.rate_limited,
            "circuit_broken": self.circuit_broken,
            "failures": self.failures,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "hit_rate": self.cache_hits / max(1, self.total_requests)
        }


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    pass


class MemoryProxy:
    """
    PgBouncer-like proxy for memory operations.

    Prevents vicious cycles (overload -> retries -> more overload):
    - Rate limiting: max N requests per second
    - Connection pooling: semaphore limits concurrent ops
    - Deduplication: same request within window returns cached
    - Circuit breaker: backs off on repeated failures

    Usage:
        proxy = MemoryProxy(max_concurrent=10, rate_limit=100)
        result = await proxy.execute("key", some_async_func, arg1, arg2)

    MARKER-99-03: Circuit breaker tuning parameters
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        rate_limit: int = 100,  # requests per second
        dedup_window: float = 0.5,  # seconds
        circuit_breaker_threshold: int = 5,  # failures before tripping
        circuit_breaker_timeout: float = 30.0,  # max backoff seconds
        enable_dedup: bool = True,
        enable_rate_limit: bool = True,
        enable_circuit_breaker: bool = True
    ):
        """
        Initialize memory proxy.

        Args:
            max_concurrent: Maximum concurrent operations (semaphore)
            rate_limit: Maximum requests per second
            dedup_window: Seconds to cache duplicate requests
            circuit_breaker_threshold: Failures before circuit opens
            circuit_breaker_timeout: Maximum circuit breaker backoff
            enable_dedup: Enable request deduplication
            enable_rate_limit: Enable rate limiting
            enable_circuit_breaker: Enable circuit breaker pattern
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.rate_limit = rate_limit
        self.dedup_window = dedup_window
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout

        self.enable_dedup = enable_dedup
        self.enable_rate_limit = enable_rate_limit
        self.enable_circuit_breaker = enable_circuit_breaker

        # Deduplication cache
        self._recent_requests: Dict[str, datetime] = {}
        self._cached_results: Dict[str, Any] = {}

        # Rate limiting
        self._request_count = 0
        self._last_reset = datetime.now()

        # Circuit breaker
        self._failure_count = 0
        self._circuit_open = False
        self._circuit_open_until: Optional[datetime] = None

        # Statistics
        self._stats = ProxyStats()
        self._latencies: list = []

        logger.debug(
            f"MemoryProxy initialized: concurrent={max_concurrent}, "
            f"rate_limit={rate_limit}/s, dedup_window={dedup_window}s"
        )

    async def execute(
        self,
        key: str,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs
    ) -> T:
        """
        Execute function with rate limiting, deduplication, and circuit breaker.

        Args:
            key: Unique key for this operation (used for dedup)
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func execution

        Raises:
            CircuitBreakerOpen: If circuit breaker is tripped
            RateLimitExceeded: If rate limit exceeded (only if blocking disabled)
        """
        start_time = datetime.now()
        self._stats.total_requests += 1

        # 1. Circuit breaker check
        if self.enable_circuit_breaker:
            self._check_circuit_breaker()

        # 2. Deduplication check
        if self.enable_dedup and self._is_duplicate(key):
            self._stats.cache_hits += 1
            logger.debug(f"Proxy dedup hit: {key}")
            return self._cached_results.get(key)

        # 3. Rate limiting
        if self.enable_rate_limit:
            await self._check_rate_limit()

        # 4. Execute with semaphore (connection pooling)
        async with self.semaphore:
            try:
                result = await func(*args, **kwargs)

                # Cache result for deduplication
                self._cache_result(key, result)

                # Reset failure count on success
                self._failure_count = 0

                # Track latency
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                self._update_latency(latency_ms)

                return result

            except Exception as e:
                self._stats.failures += 1
                self._failure_count += 1

                if self.enable_circuit_breaker:
                    if self._failure_count >= self.circuit_breaker_threshold:
                        self._trip_circuit_breaker()

                # FIX_99.2: Enhanced failure logging with threshold context
                logger.warning(
                    f"Proxy execution failed: key={key}, "
                    f"failure_count={self._failure_count}/{self.circuit_breaker_threshold}, "
                    f"error_type={type(e).__name__}"
                )
                raise

    def _check_circuit_breaker(self) -> None:
        """
        Check if circuit breaker allows request.

        MARKER-99-03: Circuit breaker logic
        """
        if not self._circuit_open:
            return

        now = datetime.now()
        if self._circuit_open_until and now >= self._circuit_open_until:
            # Circuit can be closed (half-open state)
            logger.info("Circuit breaker: half-open, allowing request")
            self._circuit_open = False
            self._failure_count = 0
        else:
            self._stats.circuit_broken += 1
            remaining = (self._circuit_open_until - now).total_seconds() if self._circuit_open_until else 0
            # FIX_99.2: Log blocked requests for monitoring
            logger.warning(
                f"Circuit breaker BLOCKING request: "
                f"blocked_count={self._stats.circuit_broken}, remaining={remaining:.1f}s"
            )
            raise CircuitBreakerOpen(
                f"Circuit breaker open - backing off for {remaining:.1f}s"
            )

    def _trip_circuit_breaker(self) -> None:
        """
        Open circuit breaker with exponential backoff.

        MARKER-99-03: Exponential backoff formula
        backoff = min(max_timeout, 2 ** failure_count)
        """
        self._circuit_open = True
        backoff = min(self.circuit_breaker_timeout, 2 ** self._failure_count)
        self._circuit_open_until = datetime.now() + timedelta(seconds=backoff)

        logger.warning(
            f"Circuit breaker TRIPPED: {self._failure_count} failures, "
            f"backoff={backoff:.1f}s"
        )

    def _is_duplicate(self, key: str) -> bool:
        """Check if same request within dedup window."""
        last_time = self._recent_requests.get(key)
        if last_time:
            age = (datetime.now() - last_time).total_seconds()
            if age < self.dedup_window:
                return True

        self._recent_requests[key] = datetime.now()
        return False

    def _cache_result(self, key: str, result: Any) -> None:
        """Cache result for deduplication."""
        self._cached_results[key] = result

        # Cleanup old entries (keep last 100)
        if len(self._cached_results) > 100:
            # Remove oldest
            oldest_key = min(
                self._recent_requests,
                key=lambda k: self._recent_requests.get(k, datetime.min)
            )
            self._cached_results.pop(oldest_key, None)
            self._recent_requests.pop(oldest_key, None)

    async def _check_rate_limit(self) -> None:
        """Enforce rate limiting with sliding window."""
        now = datetime.now()

        # Reset counter every second
        if (now - self._last_reset).total_seconds() >= 1.0:
            self._request_count = 0
            self._last_reset = now

        self._request_count += 1

        if self._request_count > self.rate_limit:
            self._stats.rate_limited += 1
            # Calculate wait time to next window
            wait_time = 1.0 - (now - self._last_reset).total_seconds()
            if wait_time > 0:
                # FIX_99.2: Elevated to WARNING for production visibility
                logger.warning(
                    f"Rate limit EXCEEDED: {self._request_count}/{self.rate_limit} req/s, "
                    f"throttling for {wait_time:.3f}s"
                )
                await asyncio.sleep(wait_time)
                self._request_count = 1
                self._last_reset = datetime.now()

    def _update_latency(self, latency_ms: float) -> None:
        """Update rolling average latency."""
        self._latencies.append(latency_ms)
        # Keep last 100 measurements
        if len(self._latencies) > 100:
            self._latencies = self._latencies[-100:]
        self._stats.avg_latency_ms = sum(self._latencies) / len(self._latencies)

    def get_stats(self) -> Dict[str, Any]:
        """Get proxy statistics."""
        return {
            **self._stats.to_dict(),
            "circuit_open": self._circuit_open,
            "failure_count": self._failure_count,
            "cached_keys": len(self._cached_results)
        }

    def reset_stats(self) -> None:
        """Reset statistics (for testing)."""
        self._stats = ProxyStats()
        self._latencies = []
        self._failure_count = 0
        self._circuit_open = False
        self._circuit_open_until = None

    def clear_cache(self) -> None:
        """Clear deduplication cache."""
        self._recent_requests.clear()
        self._cached_results.clear()

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"MemoryProxy(requests={stats['total_requests']}, "
            f"hit_rate={stats['hit_rate']:.2%}, circuit_open={self._circuit_open})"
        )


# === Specialized Proxy Factories ===

def create_embedding_proxy() -> MemoryProxy:
    """
    Create proxy optimized for embedding operations.

    Embeddings are expensive (100-500ms), so we:
    - Allow longer dedup window
    - Lower rate limit to prevent API overload
    - Higher circuit breaker threshold
    """
    return MemoryProxy(
        max_concurrent=5,
        rate_limit=50,
        dedup_window=1.0,  # Embeddings don't change quickly
        circuit_breaker_threshold=10,
        circuit_breaker_timeout=60.0
    )


def create_qdrant_proxy() -> MemoryProxy:
    """
    Create proxy optimized for Qdrant operations.

    Qdrant is fast but can be overwhelmed by batch operations:
    - Higher concurrency
    - Higher rate limit
    - Shorter dedup window for real-time updates
    """
    return MemoryProxy(
        max_concurrent=20,
        rate_limit=200,
        dedup_window=0.2,
        circuit_breaker_threshold=5,
        circuit_breaker_timeout=30.0
    )


def create_json_proxy() -> MemoryProxy:
    """
    Create proxy optimized for JSON file operations.

    File I/O is slow and contentious:
    - Low concurrency to prevent file conflicts
    - Low rate limit
    - Longer dedup window
    """
    return MemoryProxy(
        max_concurrent=3,
        rate_limit=20,
        dedup_window=2.0,
        circuit_breaker_threshold=3,
        circuit_breaker_timeout=10.0
    )


# === Singleton instances ===
_global_proxy: Optional[MemoryProxy] = None
_embedding_proxy: Optional[MemoryProxy] = None
_qdrant_proxy: Optional[MemoryProxy] = None


def get_memory_proxy() -> MemoryProxy:
    """Get global general-purpose proxy."""
    global _global_proxy
    if _global_proxy is None:
        _global_proxy = MemoryProxy()
        logger.info("Global memory proxy initialized")
    return _global_proxy


def get_embedding_proxy() -> MemoryProxy:
    """Get specialized embedding proxy."""
    global _embedding_proxy
    if _embedding_proxy is None:
        _embedding_proxy = create_embedding_proxy()
        logger.info("Embedding proxy initialized")
    return _embedding_proxy


def get_qdrant_proxy() -> MemoryProxy:
    """Get specialized Qdrant proxy."""
    global _qdrant_proxy
    if _qdrant_proxy is None:
        _qdrant_proxy = create_qdrant_proxy()
        logger.info("Qdrant proxy initialized")
    return _qdrant_proxy


def reset_all_proxies() -> None:
    """Reset all proxy instances (for testing)."""
    global _global_proxy, _embedding_proxy, _qdrant_proxy
    _global_proxy = None
    _embedding_proxy = None
    _qdrant_proxy = None
