"""
Unified Event Bus for TaskBoard — Phase 201+

Single trigger point for all agent events. Replaces fragmented notification channels
with one emit() call that fans out to multiple subscribers.

Architecture:
    TaskBoard._save_task() / _notify_board_update()
        → EventBus.emit(AgentEvent)
            → AuditSubscriber     (event_log table)
            → NotificationSubscriber (agent inbox)
            → HTTPNotifySubscriber   (SocketIO UI push — legacy bridge)
            → (future) UDSPublisher  (push to MCP servers)

Design constraints (from TaskBoard Bible):
    - emit() MUST be <1ms (no network I/O)
    - Subscriber failures MUST NOT propagate to emitter
    - SQLite remains authoritative store
    - No bulk writes in __init__

Origin: Two consecutive Eta agents independently proposed
"one event bus instead of 15 subsystems" (Phase 201).

@phase: 201
@marker: MARKER_201.EVENT_BUS
"""

import json
import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AgentEvent — the universal event type
# ---------------------------------------------------------------------------

@dataclass
class AgentEvent:
    """A single typed event emitted by any agent action.

    Every state change in TaskBoard produces one AgentEvent.
    Subscribers decide what to do with it.
    """
    event_type: str          # "task_created", "task_claimed", "task_completed", ...
    source_agent: str = ""   # "Alpha", "Commander", "system"
    source_tool: str = ""    # "claude_code", "local_ollama", "system"
    payload: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)  # routing hints

    # Auto-generated
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Subscriber interface
# ---------------------------------------------------------------------------

class EventSubscriber(Protocol):
    """Protocol for event subscribers. Implement accepts() + handle()."""

    def accepts(self, event: AgentEvent) -> bool:
        """Return True if this subscriber wants to handle this event."""
        ...

    def handle(self, event: AgentEvent) -> None:
        """Process the event. Must not raise — failures are logged and swallowed."""
        ...


# ---------------------------------------------------------------------------
# EventBus — the routing core
# ---------------------------------------------------------------------------

class EventBus:
    """Synchronous in-process event bus.

    emit() fans out to all registered subscribers. <1ms overhead.
    Subscriber exceptions are caught and logged — never propagate.
    """

    def __init__(self):
        self._subscribers: List[EventSubscriber] = []

    def subscribe(self, subscriber: EventSubscriber) -> None:
        """Register a subscriber. Idempotent — won't add duplicates."""
        if subscriber not in self._subscribers:
            self._subscribers.append(subscriber)

    def unsubscribe(self, subscriber: EventSubscriber) -> None:
        """Remove a subscriber."""
        try:
            self._subscribers.remove(subscriber)
        except ValueError:
            pass

    def emit(self, event: AgentEvent) -> int:
        """Emit an event to all subscribers. Returns count of handlers that ran.

        Guaranteed <1ms for typical subscriber count (<10).
        Subscriber failures are logged but never propagate.
        """
        handled = 0
        for sub in self._subscribers:
            try:
                if sub.accepts(event):
                    sub.handle(event)
                    handled += 1
            except Exception as exc:
                logger.warning(
                    "EventBus: subscriber %s failed on %s: %s",
                    type(sub).__name__, event.event_type, exc
                )
        return handled

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


# ---------------------------------------------------------------------------
# Built-in Subscribers
# ---------------------------------------------------------------------------

class AuditSubscriber:
    """Appends every event to the event_log SQLite table.

    Provides unified audit trail: "what happened in the system" in one query.
    """

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def _ensure_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS event_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    event_type TEXT NOT NULL,
                    source_agent TEXT,
                    source_tool TEXT,
                    timestamp TEXT NOT NULL,
                    payload JSON,
                    tags JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_event_log_type "
                "ON event_log(event_type)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_event_log_ts "
                "ON event_log(timestamp)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_event_log_agent "
                "ON event_log(source_agent)"
            )
            self._conn.commit()
        return self._conn

    def accepts(self, event: AgentEvent) -> bool:
        return True  # audit logs everything

    def handle(self, event: AgentEvent) -> None:
        conn = self._ensure_conn()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO event_log "
                "(event_id, event_type, source_agent, source_tool, "
                "timestamp, payload, tags) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    event.event_id,
                    event.event_type,
                    event.source_agent,
                    event.source_tool,
                    event.timestamp,
                    json.dumps(event.payload, default=str),
                    json.dumps(event.tags),
                ),
            )
            conn.commit()
        except Exception as exc:
            logger.warning("AuditSubscriber: write failed: %s", exc)

    def close(self):
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None


class HTTPNotifySubscriber:
    """Legacy bridge — fires HTTP POST to SocketIO endpoint.

    Replaces the inline httpx call in _notify_board_update().
    Same fire-and-forget semantics: async POST, swallow errors.
    """

    def __init__(self, url: str = "http://localhost:5001/api/debug/task-board/notify"):
        self._url = url

    def accepts(self, event: AgentEvent) -> bool:
        # Only task-level events need UI push
        return event.event_type.startswith("task_") or event.event_type in (
            "settings_updated", "stats_recorded", "cleanup"
        )

    def handle(self, event: AgentEvent) -> None:
        import asyncio

        payload = {
            "action": event.event_type,
            "event_id": event.event_id,
            "source_agent": event.source_agent,
        }
        payload.update(event.payload)

        async def _emit():
            try:
                import httpx
                async with httpx.AsyncClient(timeout=2.0) as client:
                    await client.post(self._url, json=payload)
            except Exception:
                pass

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_emit())
        except RuntimeError:
            pass  # No event loop (sync context) — skip silently


class PiggybackCollector:
    """Collects events for piggyback delivery in MCP responses.

    Events accumulate until drain() is called (typically during
    task_board MCP response construction).
    """

    def __init__(self):
        self._pending: List[Dict[str, Any]] = []
        self._max_pending: int = 100  # prevent unbounded growth

    def accepts(self, event: AgentEvent) -> bool:
        # Collect notification-worthy events
        return "notify" in event.tags or event.event_type in (
            "task_completed", "task_claimed", "task_needs_fix",
            "task_verified", "notification",
        )

    def handle(self, event: AgentEvent) -> None:
        entry = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "source_agent": event.source_agent,
            "timestamp": event.timestamp,
            "summary": event.payload.get("title", event.payload.get("message", "")),
        }
        self._pending.append(entry)
        # Trim if too many pending
        if len(self._pending) > self._max_pending:
            self._pending = self._pending[-self._max_pending:]

    def drain(self) -> List[Dict[str, Any]]:
        """Return and clear all pending events. Called during MCP response."""
        result = self._pending[:]
        self._pending.clear()
        return result

    @property
    def pending_count(self) -> int:
        return len(self._pending)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_bus: Optional[EventBus] = None
_piggyback: Optional[PiggybackCollector] = None


def get_event_bus() -> EventBus:
    """Get or create the module-level EventBus singleton."""
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus


def get_piggyback_collector() -> PiggybackCollector:
    """Get or create the module-level PiggybackCollector singleton."""
    global _piggyback
    if _piggyback is None:
        _piggyback = PiggybackCollector()
    return _piggyback


def init_event_bus(db_path: Optional[Path] = None) -> EventBus:
    """Initialize the event bus with default subscribers.

    Called once from TaskBoard.__init__. Safe to call multiple times
    (idempotent — checks if already initialized).

    Args:
        db_path: Path to SQLite DB for audit log. If None, uses task_board.db location.
    """
    bus = get_event_bus()

    # Only wire subscribers once
    if bus.subscriber_count > 0:
        return bus

    # 1. Audit trail — logs everything to event_log table
    if db_path:
        audit = AuditSubscriber(db_path)
        bus.subscribe(audit)

    # 2. HTTP notify — legacy SocketIO bridge
    http_notify = HTTPNotifySubscriber()
    bus.subscribe(http_notify)

    # 3. Piggyback collector — for MCP response injection
    piggyback = get_piggyback_collector()
    bus.subscribe(piggyback)

    logger.info(
        "EventBus initialized with %d subscribers", bus.subscriber_count
    )
    return bus
