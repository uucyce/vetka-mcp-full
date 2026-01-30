"""
Simple metrics collection for VETKA.

In-memory metrics collector with counters, gauges, and timing stats.
Can be extended with Prometheus later.

@status: active
@phase: 96
@depends: time, typing, collections, threading
@used_by: api.handlers, orchestration
"""

import time
from typing import Dict, Any, List
from collections import defaultdict
from threading import Lock


class SimpleMetrics:
    """Simple in-memory metrics collector."""

    def __init__(self):
        self._lock = Lock()
        self._counters: Dict[str, int] = defaultdict(int)
        self._timings: Dict[str, List[float]] = defaultdict(list)
        self._gauges: Dict[str, float] = {}
        self._start_time = time.time()

    def inc(self, name: str, value: int = 1):
        """Increment counter."""
        with self._lock:
            self._counters[name] += value

    def dec(self, name: str, value: int = 1):
        """Decrement counter."""
        with self._lock:
            self._counters[name] -= value

    def timing(self, name: str, duration: float):
        """Record timing (keeps last 100 samples)."""
        with self._lock:
            self._timings[name].append(duration)
            if len(self._timings[name]) > 100:
                self._timings[name] = self._timings[name][-100:]

    def gauge(self, name: str, value: float):
        """Set gauge value."""
        with self._lock:
            self._gauges[name] = value

    def get_counter(self, name: str) -> int:
        """Get counter value."""
        with self._lock:
            return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> float:
        """Get gauge value."""
        with self._lock:
            return self._gauges.get(name, 0.0)

    def get_timing_stats(self, name: str) -> Dict[str, Any]:
        """Get timing statistics for a metric."""
        with self._lock:
            values = self._timings.get(name, [])
            if not values:
                return {"count": 0}

            return {
                "count": len(values),
                "avg_ms": round(sum(values) / len(values) * 1000, 2),
                "min_ms": round(min(values) * 1000, 2),
                "max_ms": round(max(values) * 1000, 2),
                "p50_ms": round(sorted(values)[len(values) // 2] * 1000, 2),
                "p99_ms": round(sorted(values)[int(len(values) * 0.99)] * 1000, 2) if len(values) >= 100 else None,
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get all metrics."""
        with self._lock:
            timing_stats = {}
            for name, values in self._timings.items():
                if values:
                    timing_stats[name] = {
                        "count": len(values),
                        "avg_ms": round(sum(values) / len(values) * 1000, 2),
                        "min_ms": round(min(values) * 1000, 2),
                        "max_ms": round(max(values) * 1000, 2),
                    }

            return {
                "uptime_seconds": round(time.time() - self._start_time, 2),
                "counters": dict(self._counters),
                "timings": timing_stats,
                "gauges": dict(self._gauges),
            }

    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._timings.clear()
            self._gauges.clear()
            self._start_time = time.time()


# Global metrics instance
metrics = SimpleMetrics()


# Convenience functions
def count_request(endpoint: str):
    """Count request to endpoint."""
    metrics.inc("requests_total")
    metrics.inc(f"requests_{endpoint}")


def count_error(endpoint: str):
    """Count error."""
    metrics.inc("errors_total")
    metrics.inc(f"errors_{endpoint}")


def count_llm_call(provider: str):
    """Count LLM API call."""
    metrics.inc("llm_calls_total")
    metrics.inc(f"llm_calls_{provider}")


def count_llm_tokens(provider: str, tokens: int):
    """Count LLM tokens used."""
    metrics.inc("llm_tokens_total", tokens)
    metrics.inc(f"llm_tokens_{provider}", tokens)


def time_request(endpoint: str, duration: float):
    """Record request timing."""
    metrics.timing("request_duration", duration)
    metrics.timing(f"request_{endpoint}_duration", duration)


def time_llm_call(provider: str, duration: float):
    """Record LLM call timing."""
    metrics.timing("llm_call_duration", duration)
    metrics.timing(f"llm_{provider}_duration", duration)


def set_active_connections(count: int):
    """Set number of active connections."""
    metrics.gauge("active_connections", count)


def set_queue_size(size: int):
    """Set task queue size."""
    metrics.gauge("queue_size", size)
