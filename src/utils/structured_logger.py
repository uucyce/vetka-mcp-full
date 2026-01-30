"""
@file structured_logger.py
@status ACTIVE
@phase Phase 43

Structured JSON logging for VETKA.
Replaces print() with structured logs for better observability.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Optional
from contextvars import ContextVar

# Context variable for request ID (thread-safe)
request_id_var: ContextVar[str] = ContextVar('request_id', default='-')


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for easy parsing."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "request_id": request_id_var.get('-'),
        }

        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


class VetkaLogger:
    """Structured logger for VETKA with request context."""

    def __init__(self, name: str = "vetka", json_output: bool = False):
        """
        Initialize VETKA logger.

        Args:
            name: Logger name
            json_output: If True, output JSON format. If False, human-readable format.
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.json_output = json_output

        # Remove existing handlers
        self.logger.handlers = []

        # Create handler based on output format
        handler = logging.StreamHandler(sys.stdout)

        if json_output:
            handler.setFormatter(JSONFormatter())
        else:
            # Human-readable format with request ID
            handler.setFormatter(logging.Formatter(
                '[%(asctime)s] [%(levelname)s] [%(request_id)s] %(message)s',
                datefmt='%H:%M:%S'
            ))

        self.logger.addHandler(handler)

        # Prevent propagation to root logger
        self.logger.propagate = False

    def _log(self, level: int, msg: str, **extra):
        """Internal log method with extra data."""
        # Add request_id to record for non-JSON formatter
        extra_with_request_id = {'request_id': request_id_var.get('-'), **extra}

        record = self.logger.makeRecord(
            self.logger.name,
            level,
            "(unknown file)",
            0,
            msg,
            (),
            None
        )
        record.extra_data = extra
        record.request_id = request_id_var.get('-')
        self.logger.handle(record)

    def info(self, msg: str, **extra):
        """Log info message."""
        self._log(logging.INFO, msg, **extra)

    def debug(self, msg: str, **extra):
        """Log debug message."""
        self._log(logging.DEBUG, msg, **extra)

    def warning(self, msg: str, **extra):
        """Log warning message."""
        self._log(logging.WARNING, msg, **extra)

    def error(self, msg: str, **extra):
        """Log error message."""
        self._log(logging.ERROR, msg, **extra)

    def request(self, method: str, path: str, status: int, duration: float, **extra):
        """Log HTTP request."""
        duration_ms = round(duration * 1000, 2)
        self.info(
            f"{method} {path} {status} ({duration_ms}ms)",
            type="request",
            method=method,
            path=path,
            status=status,
            duration_ms=duration_ms,
            **extra
        )

    def agent(self, agent_name: str, action: str, **extra):
        """Log agent activity."""
        self.info(
            f"[{agent_name}] {action}",
            type="agent",
            agent=agent_name,
            action=action,
            **extra
        )

    def llm(self, provider: str, model: str, tokens: int, duration: float, **extra):
        """Log LLM call."""
        duration_ms = round(duration * 1000, 2)
        self.info(
            f"LLM: {provider}/{model} ({tokens} tokens, {duration_ms}ms)",
            type="llm",
            provider=provider,
            model=model,
            tokens=tokens,
            duration_ms=duration_ms,
            **extra
        )

    def component(self, name: str, status: str, **extra):
        """Log component status."""
        self.info(
            f"[Component] {name}: {status}",
            type="component",
            component=name,
            status=status,
            **extra
        )


# Global logger instance (human-readable by default, set VETKA_JSON_LOGS=true for JSON)
import os
_json_output = os.getenv('VETKA_JSON_LOGS', 'false').lower() == 'true'
logger = VetkaLogger(json_output=_json_output)


def set_request_id(request_id: str):
    """Set request ID for current context."""
    request_id_var.set(request_id)


def get_request_id() -> str:
    """Get current request ID."""
    return request_id_var.get('-')


# Convenience function for quick logging
def log(msg: str, level: str = "info", **extra):
    """Quick log function."""
    getattr(logger, level.lower(), logger.info)(msg, **extra)
