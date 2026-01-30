"""
QuietLogger - Initialization-aware logging utility for VETKA.

Prevents log flooding by tracking whether a class has been initialized before
and suppressing repeated initialization messages.

@status: active
@phase: 96
@depends: threading, logging
@used_by: singletons.py, various handlers

Usage:
    from src.utils.quiet_logger import QuietLogger

    class MyClass:
        _quiet_logger = QuietLogger("MyClass")

        def __init__(self):
            if self._quiet_logger.is_first_init():
                print("MyClass initialized")  # Only prints once

Author: AI Council + Opus 4.5
Date: December 13, 2025
"""

import threading
from typing import Dict, Set, Optional, Callable, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class QuietLogger:
    """
    Thread-safe logging utility that tracks initialization state.

    Features:
    - Tracks whether a class has been initialized before
    - Suppresses repeated initialization messages
    - Thread-safe with double-checked locking
    - Optional rate limiting for repeated log messages
    - Provides initialization summary at the end
    """

    # Global registry of all QuietLogger instances
    _registry: Dict[str, "QuietLogger"] = {}
    _registry_lock = threading.Lock()

    # Global initialization tracking
    _initialized_classes: Set[str] = set()
    _init_lock = threading.Lock()

    # Statistics
    _suppressed_count: Dict[str, int] = {}
    _first_init_times: Dict[str, datetime] = {}

    def __init__(self, class_name: str):
        """
        Create a QuietLogger for a specific class.

        Args:
            class_name: Name of the class this logger is for
        """
        self.class_name = class_name
        self._local_initialized = False

        # Register this logger
        with QuietLogger._registry_lock:
            QuietLogger._registry[class_name] = self

    def is_first_init(self) -> bool:
        """
        Check if this is the first initialization of the class.
        Thread-safe with double-checked locking.

        Returns:
            True if this is the first initialization, False otherwise
        """
        if self._local_initialized:
            # Fast path - already initialized
            with QuietLogger._init_lock:
                QuietLogger._suppressed_count[self.class_name] = (
                    QuietLogger._suppressed_count.get(self.class_name, 0) + 1
                )
            return False

        with QuietLogger._init_lock:
            # Double-check after acquiring lock
            if self.class_name in QuietLogger._initialized_classes:
                QuietLogger._suppressed_count[self.class_name] = (
                    QuietLogger._suppressed_count.get(self.class_name, 0) + 1
                )
                return False

            # First initialization
            QuietLogger._initialized_classes.add(self.class_name)
            QuietLogger._first_init_times[self.class_name] = datetime.now()
            self._local_initialized = True
            return True

    def log_once(self, message: str, level: str = "info") -> bool:
        """
        Log a message only if this is the first initialization.

        Args:
            message: Message to log
            level: Log level ("debug", "info", "warning", "error")

        Returns:
            True if message was logged, False if suppressed
        """
        if self.is_first_init():
            log_func = getattr(logger, level, logger.info)
            log_func(f"[{self.class_name}] {message}")
            return True
        return False

    def print_once(self, message: str) -> bool:
        """
        Print a message only if this is the first initialization.

        Args:
            message: Message to print

        Returns:
            True if message was printed, False if suppressed
        """
        if self.is_first_init():
            print(message)
            return True
        return False

    @classmethod
    def get_summary(cls) -> Dict[str, Any]:
        """
        Get a summary of all initialization activity.

        Returns:
            Dictionary with initialization statistics
        """
        with cls._init_lock:
            return {
                "initialized_classes": list(cls._initialized_classes),
                "total_classes": len(cls._initialized_classes),
                "suppressed_logs": dict(cls._suppressed_count),
                "total_suppressed": sum(cls._suppressed_count.values()),
                "first_init_times": {
                    k: v.isoformat() for k, v in cls._first_init_times.items()
                },
            }

    @classmethod
    def print_summary(cls) -> None:
        """Print a formatted summary of initialization activity."""
        summary = cls.get_summary()
        total_suppressed = summary["total_suppressed"]

        if total_suppressed > 0:
            print(f"\n📊 QuietLogger Summary:")
            print(f"   • Classes initialized: {summary['total_classes']}")
            print(f"   • Duplicate logs suppressed: {total_suppressed}")

            # Show top suppressions
            if summary["suppressed_logs"]:
                top_3 = sorted(
                    summary["suppressed_logs"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:3]
                for class_name, count in top_3:
                    print(f"     - {class_name}: {count} suppressed")

    @classmethod
    def reset(cls) -> None:
        """Reset all tracking state. Useful for testing."""
        with cls._init_lock:
            cls._initialized_classes.clear()
            cls._suppressed_count.clear()
            cls._first_init_times.clear()

        with cls._registry_lock:
            for logger_instance in cls._registry.values():
                logger_instance._local_initialized = False


class RateLimitedLogger:
    """
    Logger that rate-limits messages by key.

    Useful for logging events that may happen frequently but should
    only be logged once per interval.
    """

    def __init__(self, interval_seconds: float = 5.0):
        """
        Initialize rate-limited logger.

        Args:
            interval_seconds: Minimum time between logs of the same key
        """
        self.interval = interval_seconds
        self._last_log_times: Dict[str, float] = {}
        self._lock = threading.Lock()

    def should_log(self, key: str) -> bool:
        """
        Check if a message with this key should be logged.

        Args:
            key: Unique key for this log message type

        Returns:
            True if enough time has passed since last log with this key
        """
        import time
        now = time.time()

        with self._lock:
            last_time = self._last_log_times.get(key, 0)
            if now - last_time >= self.interval:
                self._last_log_times[key] = now
                return True
            return False

    def log_if_allowed(
        self,
        key: str,
        message: str,
        log_func: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Log a message if rate limit allows.

        Args:
            key: Unique key for this log message type
            message: Message to log
            log_func: Function to call for logging (default: print)

        Returns:
            True if message was logged, False if rate-limited
        """
        if self.should_log(key):
            if log_func:
                log_func(message)
            else:
                print(message)
            return True
        return False


# Convenience function for one-off use
def log_once(class_name: str, message: str) -> bool:
    """
    Log a message only once for a given class name.

    Args:
        class_name: Name of the class/context
        message: Message to log

    Returns:
        True if logged, False if suppressed
    """
    with QuietLogger._registry_lock:
        if class_name not in QuietLogger._registry:
            QuietLogger._registry[class_name] = QuietLogger(class_name)

    return QuietLogger._registry[class_name].print_once(message)
