"""
Tests for the Unified Event Bus — Phase 201.

Tests:
1. AgentEvent creation with auto-generated fields
2. EventBus emit + subscriber dispatch
3. Subscriber failure isolation (one failing subscriber doesn't block others)
4. AuditSubscriber writes to event_log table
5. PiggybackCollector accumulates and drains events
6. HTTPNotifySubscriber accepts correct event types
7. init_event_bus idempotency
8. Performance: emit <1ms for 5 subscribers
"""

import json
import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.orchestration.event_bus import (
    AgentEvent,
    AuditSubscriber,
    EventBus,
    HTTPNotifySubscriber,
    PiggybackCollector,
    init_event_bus,
    get_event_bus,
    get_piggyback_collector,
)


class TestAgentEvent:
    def test_basic_creation(self):
        event = AgentEvent(event_type="task_created", source_agent="Alpha")
        assert event.event_type == "task_created"
        assert event.source_agent == "Alpha"
        assert event.event_id  # auto-generated
        assert event.timestamp  # auto-generated
        assert event.payload == {}
        assert event.tags == []

    def test_with_payload_and_tags(self):
        event = AgentEvent(
            event_type="task_completed",
            source_agent="Beta",
            source_tool="claude_code",
            payload={"task_id": "tb_123", "commit_hash": "abc"},
            tags=["persist", "notify_commander"],
        )
        assert event.payload["task_id"] == "tb_123"
        assert "persist" in event.tags
        assert event.source_tool == "claude_code"

    def test_unique_event_ids(self):
        e1 = AgentEvent(event_type="test")
        e2 = AgentEvent(event_type="test")
        assert e1.event_id != e2.event_id


class TestEventBus:
    def test_emit_no_subscribers(self):
        bus = EventBus()
        event = AgentEvent(event_type="test")
        handled = bus.emit(event)
        assert handled == 0

    def test_emit_with_subscriber(self):
        bus = EventBus()
        mock_sub = MagicMock()
        mock_sub.accepts.return_value = True
        bus.subscribe(mock_sub)

        event = AgentEvent(event_type="task_created")
        handled = bus.emit(event)

        assert handled == 1
        mock_sub.accepts.assert_called_once_with(event)
        mock_sub.handle.assert_called_once_with(event)

    def test_subscriber_filtering(self):
        bus = EventBus()
        sub_a = MagicMock()
        sub_a.accepts.return_value = True
        sub_b = MagicMock()
        sub_b.accepts.return_value = False
        bus.subscribe(sub_a)
        bus.subscribe(sub_b)

        event = AgentEvent(event_type="test")
        handled = bus.emit(event)

        assert handled == 1
        sub_b.handle.assert_not_called()

    def test_subscriber_failure_isolation(self):
        """One failing subscriber MUST NOT block others."""
        bus = EventBus()

        failing_sub = MagicMock()
        failing_sub.accepts.return_value = True
        failing_sub.handle.side_effect = RuntimeError("boom")

        good_sub = MagicMock()
        good_sub.accepts.return_value = True

        bus.subscribe(failing_sub)
        bus.subscribe(good_sub)

        event = AgentEvent(event_type="test")
        handled = bus.emit(event)

        # good_sub still ran despite failing_sub raising
        assert handled == 1
        good_sub.handle.assert_called_once_with(event)

    def test_idempotent_subscribe(self):
        bus = EventBus()
        sub = MagicMock()
        bus.subscribe(sub)
        bus.subscribe(sub)  # duplicate
        assert bus.subscriber_count == 1

    def test_unsubscribe(self):
        bus = EventBus()
        sub = MagicMock()
        bus.subscribe(sub)
        bus.unsubscribe(sub)
        assert bus.subscriber_count == 0

    def test_unsubscribe_nonexistent(self):
        bus = EventBus()
        sub = MagicMock()
        bus.unsubscribe(sub)  # should not raise
        assert bus.subscriber_count == 0


class TestAuditSubscriber:
    def test_writes_to_event_log(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            audit = AuditSubscriber(db_path)
            event = AgentEvent(
                event_type="task_completed",
                source_agent="Alpha",
                source_tool="claude_code",
                payload={"task_id": "tb_123"},
                tags=["persist"],
            )

            assert audit.accepts(event) is True
            audit.handle(event)

            # Verify in DB
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM event_log WHERE event_id = ?", (event.event_id,)
            ).fetchone()
            conn.close()

            assert row is not None
            assert row["event_type"] == "task_completed"
            assert row["source_agent"] == "Alpha"
            assert row["source_tool"] == "claude_code"
            assert json.loads(row["payload"])["task_id"] == "tb_123"
            assert "persist" in json.loads(row["tags"])

            audit.close()
        finally:
            db_path.unlink(missing_ok=True)

    def test_idempotent_insert(self):
        """Same event_id should not cause duplicate."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            audit = AuditSubscriber(db_path)
            event = AgentEvent(event_type="test", source_agent="Zeta")
            audit.handle(event)
            audit.handle(event)  # duplicate — INSERT OR IGNORE

            conn = sqlite3.connect(str(db_path))
            count = conn.execute(
                "SELECT COUNT(*) FROM event_log WHERE event_id = ?",
                (event.event_id,),
            ).fetchone()[0]
            conn.close()
            assert count == 1

            audit.close()
        finally:
            db_path.unlink(missing_ok=True)


class TestPiggybackCollector:
    def test_collects_notification_events(self):
        collector = PiggybackCollector()
        event = AgentEvent(
            event_type="task_completed",
            source_agent="Alpha",
            payload={"title": "Fix bug"},
        )
        assert collector.accepts(event) is True
        collector.handle(event)
        assert collector.pending_count == 1

    def test_drain_clears_pending(self):
        collector = PiggybackCollector()
        event = AgentEvent(
            event_type="task_completed",
            payload={"title": "Test"},
        )
        collector.handle(event)
        result = collector.drain()
        assert len(result) == 1
        assert result[0]["event_type"] == "task_completed"
        assert collector.pending_count == 0

    def test_drain_empty(self):
        collector = PiggybackCollector()
        assert collector.drain() == []

    def test_accepts_tagged_events(self):
        collector = PiggybackCollector()
        event = AgentEvent(
            event_type="custom_event",
            tags=["notify"],
        )
        assert collector.accepts(event) is True

    def test_rejects_unrelated_events(self):
        collector = PiggybackCollector()
        event = AgentEvent(event_type="settings_updated")
        assert collector.accepts(event) is False

    def test_max_pending_limit(self):
        collector = PiggybackCollector()
        collector._max_pending = 5
        for i in range(10):
            event = AgentEvent(
                event_type="task_completed",
                payload={"title": f"task_{i}"},
            )
            collector.handle(event)
        assert collector.pending_count == 5


class TestHTTPNotifySubscriber:
    def test_accepts_task_events(self):
        sub = HTTPNotifySubscriber()
        assert sub.accepts(AgentEvent(event_type="task_created")) is True
        assert sub.accepts(AgentEvent(event_type="task_completed")) is True
        assert sub.accepts(AgentEvent(event_type="settings_updated")) is True

    def test_rejects_unknown_events(self):
        sub = HTTPNotifySubscriber()
        assert sub.accepts(AgentEvent(event_type="memory_write")) is False


class TestPerformance:
    def test_emit_under_1ms(self):
        """Event Bus emit MUST be <1ms for 5 subscribers (Bible constraint)."""
        bus = EventBus()
        for _ in range(5):
            sub = MagicMock()
            sub.accepts.return_value = True
            bus.subscribe(sub)

        event = AgentEvent(
            event_type="task_completed",
            source_agent="Alpha",
            payload={"task_id": "tb_123"},
        )

        # Warm up
        bus.emit(event)

        # Measure
        start = time.perf_counter()
        for _ in range(100):
            bus.emit(AgentEvent(event_type="test"))
        elapsed = (time.perf_counter() - start) / 100

        assert elapsed < 0.001, f"emit took {elapsed*1000:.3f}ms, must be <1ms"


class TestInitEventBus:
    def test_idempotent(self):
        """init_event_bus called twice returns same bus with same subscriber count."""
        import src.orchestration.event_bus as mod
        # Reset singleton
        mod._bus = None
        mod._piggyback = None

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            bus1 = init_event_bus(db_path=db_path)
            count1 = bus1.subscriber_count
            bus2 = init_event_bus(db_path=db_path)
            assert bus1 is bus2
            assert bus2.subscriber_count == count1  # no duplicate subscribers
        finally:
            db_path.unlink(missing_ok=True)
            mod._bus = None
            mod._piggyback = None
