"""
VETKA Logging Setup Module.

Configures logging for the entire application with:
- SmartDuplicateFilter to prevent log spam
- Configurable log levels (DEBUG with --debug flag)
- Suppression of noisy third-party loggers

Usage:
    from src.initialization.logging_setup import setup_logging, LOGGER
    setup_logging(debug=True)
    LOGGER.info("Application started")

@status: active
@phase: 96
@depends: logging
@used_by: src.initialization, all modules
"""

import logging
from typing import Optional


class SmartDuplicateFilter(logging.Filter):
    """
    Filter out duplicate log messages after N occurrences.
    Prevents log spam from repeated initialization attempts.

    Example:
        >>> filter = SmartDuplicateFilter(max_repeats=3)
        >>> logger.addFilter(filter)
        # After 3 identical messages, further duplicates are suppressed
    """

    def __init__(self, max_repeats: int = 3):
        super().__init__()
        self.max_repeats = max_repeats
        self._message_counts = {}

    def filter(self, record: logging.LogRecord) -> bool:
        # Create a key from message content
        msg_key = f"{record.levelno}:{record.getMessage()[:100]}"
        count = self._message_counts.get(msg_key, 0) + 1
        self._message_counts[msg_key] = count

        if count == self.max_repeats:
            record.msg = f"{record.msg} [suppressing further duplicates]"
            return True
        elif count > self.max_repeats:
            return False
        return True

    def reset(self):
        """Reset message counts (useful for testing)"""
        self._message_counts.clear()


# Global logger instance for VETKA
LOGGER = logging.getLogger('VETKA')

# Track if logging has been set up
_logging_initialized = False


def setup_logging(debug: bool = False, force_reinit: bool = False) -> logging.Logger:
    """
    Configure logging for the entire application.

    Args:
        debug: If True, enable DEBUG level logging. Otherwise, WARNING+.
        force_reinit: If True, reinitialize even if already set up.

    Returns:
        The configured VETKA logger instance.

    Example:
        >>> setup_logging(debug=True)
        >>> LOGGER.info("This will be shown in debug mode")
    """
    global _logging_initialized

    if _logging_initialized and not force_reinit:
        return LOGGER

    level = logging.DEBUG if debug else logging.WARNING

    # Root logger configuration
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S',
        force=force_reinit  # Python 3.8+: allows reconfiguration
    )

    # Add duplicate filter to root logger
    root_logger = logging.getLogger()

    # Remove existing SmartDuplicateFilters to avoid duplicates
    for f in root_logger.filters[:]:
        if isinstance(f, SmartDuplicateFilter):
            root_logger.removeFilter(f)

    root_logger.addFilter(SmartDuplicateFilter(max_repeats=3))

    # Suppress noisy third-party loggers (always WARN+)
    noisy_loggers = [
        'httpx',
        'httpcore',
        'urllib3',
        'requests',
        'weaviate',
        'qdrant_client',
        'ollama',
        'openai',
        'anthropic',
        'grpc',
        'google',
        'werkzeug',
        'socketio',
        'engineio',
        'asyncio',
        'PIL',
        'matplotlib',
    ]

    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # VETKA loggers - configurable based on debug flag
    vetka_loggers = [
        'VETKA',
        'VetkaMemory',
        'VetkaOrchestrator',
        'VetkaElisya',
        'VetkaAgent',
        'VetkaLayout',
        'VetkaKG',
    ]

    for logger_name in vetka_loggers:
        logging.getLogger(logger_name).setLevel(level)

    # Configure the main VETKA logger
    LOGGER.setLevel(level)

    if debug:
        print("🐛 DEBUG logging enabled")
    else:
        print("📋 Logging: WARN+ only (use --debug for verbose)")

    _logging_initialized = True
    return LOGGER


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name. If None, returns the main VETKA logger.
              If provided, returns a child logger (e.g., 'VETKA.routes').

    Returns:
        Logger instance

    Example:
        >>> logger = get_logger('VETKA.routes')
        >>> logger.info("Route accessed")
    """
    if name is None:
        return LOGGER
    return logging.getLogger(name)


# Convenience functions
def debug(msg: str, *args, **kwargs):
    """Log a debug message to VETKA logger"""
    LOGGER.debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """Log an info message to VETKA logger"""
    LOGGER.info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """Log a warning message to VETKA logger"""
    LOGGER.warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """Log an error message to VETKA logger"""
    LOGGER.error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs):
    """Log a critical message to VETKA logger"""
    LOGGER.critical(msg, *args, **kwargs)
