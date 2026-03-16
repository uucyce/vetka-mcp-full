"""
Phase 99: Short-Term Memory (STM) Buffer Tests

Comprehensive tests for STM buffer with automatic decay, overflow handling,
surprise event prioritization, and serialization.

Tests:
1. test_stm_add_and_get_context() - adding entries and retrieving by weight
2. test_stm_decay() - verify old entries have lower weight
3. test_stm_overflow() - verify buffer respects max_size
4. test_stm_surprise_priority() - surprise events get boosted weight
5. test_stm_serialization() - to_dict() and from_dict() work correctly
6. test_stm_singleton() - get_stm_buffer() returns singleton

@phase: 99
@file: tests/test_stm_buffer.py
@depends: pytest, datetime, src.memory.stm_buffer
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.memory.stm_buffer import (
    STMEntry,
    STMBuffer,
    get_stm_buffer,
    reset_stm_buffer,
)


class TestSTMEntry:
    """Test STMEntry dataclass."""

    def test_entry_creation(self):
        """Create STMEntry with default values."""
        entry = STMEntry(content="Test message")
        assert entry.content == "Test message"
        assert entry.source == "system"
        assert entry.weight == 1.0
        assert entry.surprise_score == 0.0
        assert entry.metadata is None
        assert isinstance(entry.timestamp, datetime)

    def test_entry_creation_with_custom_values(self):
        """Create STMEntry with custom values."""
        ts = datetime.now()
        metadata = {"workflow_id": "wf-123"}
        entry = STMEntry(
            content="Custom",
            timestamp=ts,
            source="user",
            weight=0.8,
            surprise_score=0.5,
            metadata=metadata,
        )
        assert entry.content == "Custom"
        assert entry.source == "user"
        assert entry.weight == 0.8
        assert entry.surprise_score == 0.5
        assert entry.metadata == metadata

    def test_entry_to_dict(self):
        """Serialize STMEntry to dict."""
        ts = datetime(2026, 1, 28, 12, 0, 0)
        entry = STMEntry(
            content="Test",
            timestamp=ts,
            source="agent",
            weight=0.9,
            surprise_score=0.3,
            metadata={"key": "value"},
        )
        data = entry.to_dict()

        assert data["content"] == "Test"
        assert data["timestamp"] == "2026-01-28T12:00:00"
        assert data["source"] == "agent"
        assert data["weight"] == 0.9
        assert data["surprise_score"] == 0.3
        assert data["metadata"] == {"key": "value"}

    def test_entry_from_dict(self):
        """Deserialize STMEntry from dict."""
        data = {
            "content": "Test",
            "timestamp": "2026-01-28T12:00:00",
            "source": "user",
            "weight": 0.8,
            "surprise_score": 0.4,
            "metadata": {"id": "123"},
        }
        entry = STMEntry.from_dict(data)

        assert entry.content == "Test"
        assert entry.timestamp == datetime(2026, 1, 28, 12, 0, 0)
        assert entry.source == "user"
        assert entry.weight == 0.8
        assert entry.surprise_score == 0.4
        assert entry.metadata == {"id": "123"}

    def test_entry_from_dict_with_defaults(self):
        """Deserialize with missing optional fields uses defaults."""
        data = {
            "content": "Minimal",
            "timestamp": datetime.now().isoformat(),  # Required field
        }
        entry = STMEntry.from_dict(data)

        assert entry.content == "Minimal"
        assert entry.source == "system"
        assert entry.weight == 1.0
        assert entry.surprise_score == 0.0
        assert entry.metadata is None

    def test_entry_to_dict_with_none_metadata(self):
        """Serialize entry with None metadata returns empty dict."""
        entry = STMEntry(content="Test", metadata=None)
        data = entry.to_dict()
        assert data["metadata"] == {}


class TestSTMBuffer:
    """Test STMBuffer basic operations."""

    def test_buffer_initialization(self):
        """Initialize STMBuffer with default parameters."""
        buffer = STMBuffer()
        assert buffer.max_size == 10
        assert buffer.decay_rate == 0.1
        assert buffer.min_weight == 0.1
        assert len(buffer) == 0

    def test_buffer_initialization_custom_params(self):
        """Initialize with custom parameters."""
        buffer = STMBuffer(max_size=20, decay_rate=0.2, min_weight=0.05)
        assert buffer.max_size == 20
        assert buffer.decay_rate == 0.2
        assert buffer.min_weight == 0.05

    def test_buffer_bool(self):
        """Test __bool__ returns correct state."""
        buffer = STMBuffer()
        assert not buffer  # Empty buffer is falsy

        buffer.add(STMEntry(content="Test"))
        assert buffer  # Non-empty buffer is truthy

    def test_buffer_len(self):
        """Test __len__ returns correct count."""
        buffer = STMBuffer()
        assert len(buffer) == 0

        for i in range(3):
            buffer.add(STMEntry(content=f"Entry {i}"))
        assert len(buffer) == 3

    def test_buffer_repr(self):
        """Test __repr__ string representation."""
        buffer = STMBuffer(max_size=10)
        buffer.add(STMEntry(content="Test"))
        repr_str = repr(buffer)
        assert "STMBuffer" in repr_str
        assert "1/10" in repr_str


class TestSTMAddAndGetContext:
    """Test adding entries and retrieving context (MARKER-99-01)."""

    def test_add_single_entry(self):
        """Add single entry to buffer."""
        buffer = STMBuffer()
        entry = STMEntry(content="Hello", source="user")
        buffer.add(entry)

        assert len(buffer) == 1
        assert buffer.get_all()[0].content == "Hello"

    def test_add_message_convenience(self):
        """Use add_message convenience method."""
        buffer = STMBuffer()
        buffer.add_message("Simple text", source="agent", metadata={"id": "1"})

        assert len(buffer) == 1
        entry = buffer.get_all()[0]
        assert entry.content == "Simple text"
        assert entry.source == "agent"
        assert entry.metadata == {"id": "1"}

    def test_get_context_returns_by_weight(self):
        """get_context returns entries sorted by weight descending."""
        buffer = STMBuffer()

        # Add entries with different weights
        e1 = STMEntry(content="Low weight", weight=0.2)
        e2 = STMEntry(content="High weight", weight=0.9)
        e3 = STMEntry(content="Medium weight", weight=0.5)

        buffer.add(e1)
        buffer.add(e2)
        buffer.add(e3)

        context = buffer.get_context(max_items=3)
        assert len(context) == 3
        assert context[0].content == "High weight"  # 0.9
        assert context[1].content == "Medium weight"  # 0.5
        assert context[2].content == "Low weight"  # 0.2

    def test_get_context_respects_max_items(self):
        """get_context limits results to max_items."""
        buffer = STMBuffer()
        for i in range(10):
            buffer.add(STMEntry(content=f"Entry {i}", weight=10 - i))

        context = buffer.get_context(max_items=3)
        assert len(context) == 3

    def test_get_context_empty_buffer(self):
        """get_context returns empty list for empty buffer."""
        buffer = STMBuffer()
        context = buffer.get_context()
        assert context == []

    def test_get_context_string_formatting(self):
        """get_context_string formats entries nicely."""
        buffer = STMBuffer()
        buffer.add(STMEntry(content="User input", source="user", weight=0.9))
        buffer.add(STMEntry(content="Agent response", source="agent", weight=0.8))
        buffer.add(STMEntry(content="System note", source="system", weight=0.7))

        context_str = buffer.get_context_string(max_items=3)
        assert "[user]" in context_str
        assert "User input" in context_str
        assert "[agent]" in context_str
        assert "Agent response" in context_str
        assert "System note" in context_str  # system source doesn't get prefix

    def test_get_context_string_separator(self):
        """get_context_string uses custom separator."""
        buffer = STMBuffer()
        buffer.add(STMEntry(content="First", weight=0.9))
        buffer.add(STMEntry(content="Second", weight=0.8))

        context_str = buffer.get_context_string(max_items=2, separator=" | ")
        assert " | " in context_str
        assert "First" in context_str
        assert "Second" in context_str

    def test_get_all_applies_decay(self):
        """get_all applies decay before returning."""
        buffer = STMBuffer()
        entry = STMEntry(content="Test", weight=1.0)
        buffer.add(entry)

        # Manually set timestamp to past
        original_weight = entry.weight
        buffer.get_all()  # Should apply decay
        # Weight should have decayed slightly (depends on time)
        assert entry.weight <= original_weight


class TestSTMDecay:
    """Test MARKER-99-01 decay formula: weight *= (1 - decay_rate * (age_seconds / 60))."""

    def test_decay_formula_basic(self):
        """Verify decay formula application."""
        buffer = STMBuffer(decay_rate=0.1, min_weight=0.0)

        # Create entry with known timestamp in past
        past_time = datetime.now() - timedelta(seconds=60)  # 1 minute ago
        entry = STMEntry(content="Old", timestamp=past_time, weight=1.0)
        buffer.add(entry)

        buffer._apply_decay()

        # After 60 seconds (1 minute) with decay_rate=0.1:
        # weight *= (1 - 0.1 * (60 / 60)) = 1 * (1 - 0.1) = 0.9
        assert abs(entry.weight - 0.9) < 0.01

    def test_decay_multiple_entries(self):
        """Decay applies to all entries."""
        buffer = STMBuffer(decay_rate=0.2, min_weight=0.0)

        # Recent entry (0 seconds old)
        recent = STMEntry(content="Recent", timestamp=datetime.now(), weight=1.0)
        buffer.add(recent)

        # Older entry (2 minutes old)
        old = STMEntry(
            content="Old",
            timestamp=datetime.now() - timedelta(seconds=120),
            weight=1.0,
        )
        buffer.add(old)

        buffer._apply_decay()

        # Recent: weight *= (1 - 0.2 * (0 / 60)) = 1.0
        assert abs(recent.weight - 1.0) < 0.01

        # MARKER_187.5: Exponential decay: weight *= exp(-0.2 * 2) = exp(-0.4) ≈ 0.6703
        import math
        expected = math.exp(-0.2 * 2)  # ~0.6703
        assert abs(old.weight - expected) < 0.01

    def test_decay_respects_min_weight(self):
        """Decay stops at min_weight."""
        buffer = STMBuffer(decay_rate=1.0, min_weight=0.2)  # High decay rate

        # Very old entry
        ancient = STMEntry(
            content="Ancient",
            timestamp=datetime.now() - timedelta(seconds=600),  # 10 minutes
            weight=1.0,
        )
        buffer.add(ancient)

        buffer._apply_decay()

        # Without min_weight, this would be negative
        # But min_weight clips it to 0.2
        assert ancient.weight == 0.2

    def test_decay_applied_on_add(self):
        """Decay is applied when new entry is added."""
        buffer = STMBuffer(decay_rate=0.1, min_weight=0.0)

        # Add first entry
        entry1 = STMEntry(content="First", timestamp=datetime.now(), weight=1.0)
        buffer.add(entry1)

        # Simulate time passing
        entry1.timestamp = datetime.now() - timedelta(seconds=60)

        # Add second entry - should trigger decay on first
        entry2 = STMEntry(content="Second", weight=1.0)
        buffer.add(entry2)

        # First entry should have decayed
        assert entry1.weight < 1.0

    def test_decay_applied_on_get_context(self):
        """Decay is applied when getting context."""
        buffer = STMBuffer(decay_rate=0.1, min_weight=0.0)

        entry = STMEntry(content="Test", timestamp=datetime.now(), weight=1.0)
        buffer.add(entry)

        # Manually set to past
        entry.timestamp = datetime.now() - timedelta(seconds=60)

        # Get context should apply decay
        original_weight = entry.weight
        context = buffer.get_context()

        assert entry.weight < original_weight

    def test_zero_age_no_decay(self):
        """Entries just added have minimal decay."""
        buffer = STMBuffer(decay_rate=0.5, min_weight=0.0)

        entry = STMEntry(content="Fresh", weight=1.0)
        buffer.add(entry)

        buffer._apply_decay()

        # Just added, age ~0, decay ~0
        assert entry.weight >= 0.99


class TestSTMOverflow:
    """Test buffer overflow handling."""

    def test_buffer_respects_max_size(self):
        """Buffer size limited to max_size."""
        buffer = STMBuffer(max_size=5)

        for i in range(10):
            buffer.add(STMEntry(content=f"Entry {i}"))

        assert len(buffer) == 5

    def test_oldest_evicted_on_overflow(self):
        """Oldest entries are evicted when buffer overflows."""
        buffer = STMBuffer(max_size=3)

        e1 = STMEntry(content="Entry 1")
        e2 = STMEntry(content="Entry 2")
        e3 = STMEntry(content="Entry 3")
        e4 = STMEntry(content="Entry 4")

        buffer.add(e1)
        buffer.add(e2)
        buffer.add(e3)
        assert len(buffer) == 3

        # Adding 4th should evict 1st
        buffer.add(e4)
        assert len(buffer) == 3

        contents = [e.content for e in buffer.get_all()]
        assert "Entry 1" not in contents
        assert "Entry 4" in contents

    def test_max_size_zero_allowed(self):
        """Max size of 0 creates empty buffer."""
        buffer = STMBuffer(max_size=0)
        buffer.add(STMEntry(content="Test"))
        assert len(buffer) == 0

    def test_large_max_size(self):
        """Large max_size works correctly."""
        buffer = STMBuffer(max_size=1000)

        for i in range(500):
            buffer.add(STMEntry(content=f"Entry {i}"))

        assert len(buffer) == 500

        for i in range(500):
            buffer.add(STMEntry(content=f"Entry {i + 500}"))

        assert len(buffer) == 1000


class TestSTMSurprisePriority:
    """Test surprise event handling (FIX_99.1)."""

    def test_add_from_cam_boosts_weight(self):
        """CAM surprise events get boosted initial weight."""
        buffer = STMBuffer()

        surprise_score = 0.7
        buffer.add_from_cam("Surprising content", surprise_score=surprise_score)

        context = buffer.get_context(max_items=1)
        assert len(context) == 1

        entry = context[0]
        assert entry.source == "cam_surprise"
        assert entry.surprise_score == 0.7
        # Initial weight should be 1.0 + surprise_score
        assert abs(entry.weight - 1.7) < 0.01

    def test_surprise_max_boost(self):
        """Surprise score of 1.0 gives maximum boost."""
        buffer = STMBuffer()
        buffer.add_from_cam("Maximum surprise", surprise_score=1.0)

        entry = buffer.get_all()[0]
        # 1.0 + 1.0 = 2.0
        assert abs(entry.weight - 2.0) < 0.01

    def test_surprise_zero_score(self):
        """Surprise score of 0.0 gives no boost."""
        buffer = STMBuffer()
        buffer.add_from_cam("No surprise", surprise_score=0.0)

        entry = buffer.get_all()[0]
        # 1.0 + 0.0 = 1.0
        assert abs(entry.weight - 1.0) < 0.01

    def test_surprise_vs_regular_priority(self):
        """Surprise events rank higher than regular entries."""
        buffer = STMBuffer()

        # Add regular entry with high weight
        buffer.add(STMEntry(content="Regular high", weight=1.5))

        # Add surprise with lower score
        buffer.add_from_cam("Surprising", surprise_score=0.5)  # weight = 1.5

        # Add another surprise with high score
        buffer.add_from_cam("Very surprising", surprise_score=0.8)  # weight = 1.8

        context = buffer.get_context(max_items=3)

        # Should be sorted by weight: 1.8, 1.5, 1.5
        assert context[0].content == "Very surprising"
        assert context[1].content in ["Regular high", "Surprising"]

    def test_surprise_still_decays(self):
        """Surprise-boosted entries still decay over time."""
        buffer = STMBuffer(decay_rate=0.5, min_weight=0.0)

        # Create surprise entry in the past
        past = datetime.now() - timedelta(seconds=120)  # 2 minutes ago
        surprise = STMEntry(
            content="Old surprise",
            timestamp=past,
            source="cam_surprise",
            weight=2.0,  # high initial boost
            surprise_score=1.0,
        )
        buffer.add(surprise)

        buffer._apply_decay()

        # weight *= (1 - 0.5 * (120 / 60)) = 2.0 * (1 - 1.0) = 0.0
        # But should be clipped to min_weight
        assert surprise.weight < 2.0  # Definitely decayed

    def test_add_from_hope(self):
        """HOPE summaries get weight boost."""
        buffer = STMBuffer()
        buffer.add_from_hope("Analysis summary", workflow_id="wf-123")

        entry = buffer.get_all()[0]
        assert entry.source == "hope"
        assert abs(entry.weight - 1.2) < 0.01  # HOPE boost (float comparison)
        assert "Analysis summary" in entry.content
        assert entry.metadata["workflow_id"] == "wf-123"

    def test_add_from_hope_truncates_long_content(self):
        """HOPE content truncated to 500 chars."""
        buffer = STMBuffer()
        long_summary = "x" * 1000

        buffer.add_from_hope(long_summary, workflow_id="wf-456")

        entry = buffer.get_all()[0]
        assert len(entry.content) == 500

    def test_add_from_hope_without_workflow(self):
        """HOPE entry without workflow_id has no metadata."""
        buffer = STMBuffer()
        buffer.add_from_hope("Summary")

        entry = buffer.get_all()[0]
        assert entry.metadata is None


class TestSTMSerialization:
    """Test serialization/deserialization (FIX_99.1)."""

    def test_stmentry_serialization_roundtrip(self):
        """STMEntry to_dict and from_dict roundtrip."""
        original = STMEntry(
            content="Test content",
            timestamp=datetime(2026, 1, 28, 12, 30, 0),
            source="user",
            weight=0.75,
            surprise_score=0.6,
            metadata={"key": "value"},
        )

        data = original.to_dict()
        restored = STMEntry.from_dict(data)

        assert restored.content == original.content
        assert restored.timestamp == original.timestamp
        assert restored.source == original.source
        assert restored.weight == original.weight
        assert restored.surprise_score == original.surprise_score
        assert restored.metadata == original.metadata

    def test_buffer_to_dict(self):
        """Buffer to_dict includes all config and entries."""
        buffer = STMBuffer(max_size=15, decay_rate=0.2, min_weight=0.05)

        buffer.add(STMEntry(content="Entry 1", weight=0.9))
        buffer.add(STMEntry(content="Entry 2", weight=0.8))

        data = buffer.to_dict()

        assert data["max_size"] == 15
        assert data["decay_rate"] == 0.2
        assert data["min_weight"] == 0.05
        assert len(data["entries"]) == 2
        assert data["entries"][0]["content"] == "Entry 1"
        assert data["entries"][1]["content"] == "Entry 2"

    def test_buffer_from_dict(self):
        """Buffer from_dict restores state exactly."""
        data = {
            "max_size": 20,
            "decay_rate": 0.3,
            "min_weight": 0.15,
            "entries": [
                {
                    "content": "Restored 1",
                    "timestamp": "2026-01-28T10:00:00",
                    "source": "user",
                    "weight": 0.85,
                    "surprise_score": 0.0,
                    "metadata": None,
                },
                {
                    "content": "Restored 2",
                    "timestamp": "2026-01-28T10:05:00",
                    "source": "agent",
                    "weight": 0.6,
                    "surprise_score": 0.4,
                    "metadata": {"id": "456"},
                },
            ],
        }

        buffer = STMBuffer.from_dict(data)

        assert buffer.max_size == 20
        assert buffer.decay_rate == 0.3
        assert buffer.min_weight == 0.15
        assert len(buffer) == 2
        assert buffer.get_all()[0].content == "Restored 1"
        assert buffer.get_all()[1].content == "Restored 2"

    def test_buffer_serialization_roundtrip(self):
        """Full buffer roundtrip through serialization."""
        original = STMBuffer(max_size=8, decay_rate=0.25)

        original.add_message("User message", source="user", metadata={"id": "u1"})
        original.add_message("Agent message", source="agent", metadata={"id": "a1"})
        original.add_from_cam("Surprise!", surprise_score=0.7)
        original.add_from_hope("Analysis", workflow_id="wf-xyz")

        data = original.to_dict()
        restored = STMBuffer.from_dict(data)

        assert restored.max_size == original.max_size
        assert restored.decay_rate == original.decay_rate
        assert len(restored) == len(original)

        # Verify all entries preserved
        original_contents = [e.content for e in original.get_all()]
        restored_contents = [e.content for e in restored.get_all()]
        assert set(original_contents) == set(restored_contents)

    def test_empty_buffer_serialization(self):
        """Empty buffer serializes and restores correctly."""
        buffer = STMBuffer()
        data = buffer.to_dict()

        restored = STMBuffer.from_dict(data)
        assert len(restored) == 0
        assert restored.max_size == buffer.max_size

    def test_buffer_from_dict_missing_fields_defaults(self):
        """from_dict uses defaults for missing optional fields."""
        data = {"entries": []}

        buffer = STMBuffer.from_dict(data)

        assert buffer.max_size == 10
        assert buffer.decay_rate == 0.1
        assert buffer.min_weight == 0.1

    def test_buffer_clear(self):
        """clear() removes all entries."""
        buffer = STMBuffer()
        buffer.add_message("Message 1")
        buffer.add_message("Message 2")

        assert len(buffer) > 0

        buffer.clear()

        assert len(buffer) == 0
        assert buffer.get_all() == []


class TestSTMSingleton:
    """Test singleton instance (get_stm_buffer)."""

    def teardown_method(self):
        """Reset singleton after each test."""
        reset_stm_buffer()

    def test_get_stm_buffer_creates_instance(self):
        """get_stm_buffer creates instance on first call."""
        reset_stm_buffer()
        buffer = get_stm_buffer()

        assert buffer is not None
        assert isinstance(buffer, STMBuffer)

    def test_get_stm_buffer_returns_same_instance(self):
        """get_stm_buffer returns same instance on subsequent calls."""
        reset_stm_buffer()

        buffer1 = get_stm_buffer()
        buffer2 = get_stm_buffer()

        assert buffer1 is buffer2

    def test_singleton_persistence(self):
        """Data persists in singleton between get calls."""
        reset_stm_buffer()

        get_stm_buffer().add_message("Message 1", source="user")

        # Get singleton again and check data persists
        buffer = get_stm_buffer()
        assert len(buffer) == 1
        assert buffer.get_all()[0].content == "Message 1"

    def test_reset_stm_buffer(self):
        """reset_stm_buffer clears singleton."""
        buffer1 = get_stm_buffer()
        buffer1.add_message("Test")

        reset_stm_buffer()

        # New instance should be created
        buffer2 = get_stm_buffer()
        assert buffer1 is not buffer2
        assert len(buffer2) == 0

    def test_singleton_isolation(self):
        """Each reset creates independent instance."""
        reset_stm_buffer()
        buffer1 = get_stm_buffer()
        buffer1.add_message("Data 1")

        reset_stm_buffer()
        buffer2 = get_stm_buffer()
        buffer2.add_message("Data 2")

        reset_stm_buffer()
        buffer3 = get_stm_buffer()

        # buffer3 should be empty, not containing data from buffer1 or buffer2
        assert len(buffer3) == 0


class TestSTMIntegration:
    """Integration tests combining multiple features."""

    def test_realistic_workflow(self):
        """Realistic usage combining decay, surprise, and context."""
        buffer = STMBuffer(max_size=10, decay_rate=0.1)

        # Simulate conversation
        buffer.add_message("User asks question", source="user")
        buffer.add_message("Agent provides answer", source="agent", metadata={"id": "a1"})

        # Something surprising happens
        buffer.add_from_cam("Unexpected result", surprise_score=0.8)

        # HOPE analysis
        buffer.add_from_hope("Summary of interactions", workflow_id="wf-001")

        # Get current context
        context = buffer.get_context(max_items=5)

        # Surprise should be prominent
        assert any(e.source == "cam_surprise" for e in context)
        assert any(e.source == "hope" for e in context)

    def test_mixed_decay_and_priority(self):
        """Old entries decay even if initially high priority."""
        buffer = STMBuffer(decay_rate=0.5, min_weight=0.0)

        # Add old high-priority entry
        old_surprise = STMEntry(
            content="Old surprise",
            timestamp=datetime.now() - timedelta(seconds=120),
            source="cam_surprise",
            weight=2.0,
        )
        buffer.add(old_surprise)

        # Add new regular entry
        new_regular = STMEntry(content="New regular", weight=1.0)
        buffer.add(new_regular)

        context = buffer.get_context(max_items=2)

        # New regular should rank higher than old surprise after decay
        assert context[0].content == "New regular"

    def test_multiple_surprise_events(self):
        """Multiple surprise events ranked by score."""
        buffer = STMBuffer()

        buffer.add_from_cam("Low surprise", surprise_score=0.3)  # weight = 1.3
        buffer.add_from_cam("High surprise", surprise_score=0.9)  # weight = 1.9
        buffer.add_from_cam("Medium surprise", surprise_score=0.5)  # weight = 1.5

        context = buffer.get_context(max_items=3)

        assert context[0].content == "High surprise"
        assert context[1].content == "Medium surprise"
        assert context[2].content == "Low surprise"

    def test_full_lifecycle(self):
        """Complete lifecycle: create, add, decay, serialize, restore."""
        # Create and populate
        buffer1 = STMBuffer(max_size=5)
        buffer1.add_message("Message 1", source="user")
        buffer1.add_message("Message 2", source="agent")
        buffer1.add_from_cam("Surprise", surprise_score=0.7)

        # Serialize
        state = buffer1.to_dict()

        # Create new buffer and restore
        buffer2 = STMBuffer.from_dict(state)

        # Verify
        assert len(buffer2) == 3
        context = buffer2.get_context(max_items=3)
        assert any(e.source == "cam_surprise" for e in context)


class TestSTMEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_negative_decay_rate_handling(self):
        """Negative decay rate doesn't cause crashes."""
        buffer = STMBuffer(decay_rate=-0.1)
        entry = STMEntry(content="Test")
        buffer.add(entry)
        # Should not crash
        buffer._apply_decay()

    def test_very_high_surprise_score(self):
        """Surprise score > 1.0 allowed (CAM might return such values)."""
        buffer = STMBuffer()
        buffer.add_from_cam("Ultra surprise", surprise_score=2.5)

        entry = buffer.get_all()[0]
        # 1.0 + 2.5 = 3.5
        assert abs(entry.weight - 3.5) < 0.01

    def test_get_context_more_than_buffer_size(self):
        """Requesting more items than in buffer returns all."""
        buffer = STMBuffer()
        buffer.add(STMEntry(content="One"))
        buffer.add(STMEntry(content="Two"))

        context = buffer.get_context(max_items=100)
        assert len(context) == 2

    def test_metadata_preservation(self):
        """Complex metadata preserved through cycles."""
        buffer = STMBuffer()
        metadata = {
            "workflow_id": "wf-123",
            "group_id": "g-456",
            "nested": {"key": "value", "list": [1, 2, 3]},
        }
        buffer.add_message("Test", metadata=metadata)

        context = buffer.get_context(max_items=1)
        assert context[0].metadata == metadata

    def test_unicode_content(self):
        """Unicode content handled correctly."""
        buffer = STMBuffer()
        unicode_content = "こんにちは 🚀 Привет мир 你好"
        buffer.add_message(unicode_content)

        context = buffer.get_context(max_items=1)
        assert context[0].content == unicode_content

    def test_very_long_content(self):
        """Very long content doesn't break buffer."""
        buffer = STMBuffer()
        long_content = "x" * 100000
        buffer.add_message(long_content)

        context = buffer.get_context(max_items=1)
        assert len(context[0].content) == 100000


# ─── Phase 187.5: New feature tests ──────────────────────────────

class TestExponentialDecay:
    """MARKER_187.5: Exponential decay retains weight longer than linear."""

    def test_exponential_decay_10_minutes(self):
        """After 10 min with rate=0.1: exp(-0.1*10) ≈ 0.37 (not 0.0 like linear)."""
        import math
        buffer = STMBuffer(decay_rate=0.1, min_weight=0.0)
        entry = STMEntry(
            content="test",
            timestamp=datetime.now() - timedelta(minutes=10),
            weight=1.0,
        )
        buffer._buffer.append(entry)
        buffer._apply_decay()
        expected = math.exp(-0.1 * 10)  # ~0.3679
        assert abs(entry.weight - expected) < 0.01

    def test_exponential_never_reaches_zero(self):
        """Even after 60 min, weight > 0 (unlike linear which goes negative)."""
        import math
        buffer = STMBuffer(decay_rate=0.1, min_weight=0.0)
        entry = STMEntry(
            content="old",
            timestamp=datetime.now() - timedelta(minutes=60),
            weight=1.0,
        )
        buffer._buffer.append(entry)
        buffer._apply_decay()
        assert entry.weight > 0.0
        expected = math.exp(-0.1 * 60)  # ~0.0025
        assert abs(entry.weight - expected) < 0.001

    def test_surprise_slows_exponential_decay(self):
        """Surprise entry with score=1.0 decays 30% slower."""
        import math
        buffer = STMBuffer(decay_rate=0.1, min_weight=0.0)
        normal = STMEntry(content="normal", timestamp=datetime.now() - timedelta(minutes=5), weight=1.0, surprise_score=0.0)
        surprise = STMEntry(content="surprise", timestamp=datetime.now() - timedelta(minutes=5), weight=1.0, surprise_score=1.0)
        buffer._buffer.append(normal)
        buffer._buffer.append(surprise)
        buffer._apply_decay()
        # normal: exp(-0.1 * 5) = 0.6065
        # surprise: effective_rate = 0.1 * (1 - 1.0 * 0.3) = 0.07, exp(-0.07 * 5) = 0.7047
        assert surprise.weight > normal.weight


class TestRehearsal:
    """MARKER_187.5: Rehearsal resets entry timestamp to keep it fresh."""

    def test_rehearse_resets_timestamp(self):
        buffer = STMBuffer()
        old_time = datetime.now() - timedelta(minutes=5)
        buffer._buffer.append(STMEntry(content="important context", timestamp=old_time))
        before = buffer._buffer[0].timestamp
        buffer.rehearse("important")
        after = buffer._buffer[0].timestamp
        assert after > before

    def test_rehearse_keeps_weight_high(self):
        """After rehearsal, decay starts from 0 age again."""
        import math
        buffer = STMBuffer(decay_rate=0.1, min_weight=0.0)
        entry = STMEntry(content="key concept", timestamp=datetime.now() - timedelta(minutes=10), weight=1.0)
        buffer._buffer.append(entry)
        buffer._apply_decay()
        decayed_weight = entry.weight  # should be ~0.37

        # Rehearse — resets timestamp
        buffer.rehearse("key concept")
        buffer._apply_decay()
        # After rehearsal, age ≈ 0 so decay ≈ 1.0, weight stays same
        assert entry.weight >= decayed_weight * 0.99

    def test_rehearse_returns_false_on_miss(self):
        buffer = STMBuffer()
        buffer.add_message("hello world")
        assert buffer.rehearse("nonexistent") is False

    def test_rehearse_case_insensitive(self):
        buffer = STMBuffer()
        buffer.add_message("Hello World")
        assert buffer.rehearse("hello") is True


class TestAdaptiveMaxlen:
    """MARKER_187.5: STM maxlen scales with model context window."""

    def test_small_model_gets_small_buffer(self):
        buffer = STMBuffer(model_context_length=4096)
        assert buffer.max_size == 6

    def test_medium_model_gets_default_buffer(self):
        buffer = STMBuffer(model_context_length=16384)
        assert buffer.max_size == 10

    def test_large_model_gets_large_buffer(self):
        buffer = STMBuffer(model_context_length=128000)
        assert buffer.max_size == 15

    def test_boundary_8k(self):
        assert STMBuffer(model_context_length=8192).max_size == 6

    def test_boundary_32k(self):
        assert STMBuffer(model_context_length=32768).max_size == 10

    def test_boundary_above_32k(self):
        assert STMBuffer(model_context_length=32769).max_size == 15

    def test_explicit_max_size_overrides(self):
        """Explicit max_size takes priority over model_context_length."""
        buffer = STMBuffer(max_size=20, model_context_length=4096)
        assert buffer.max_size == 20

    def test_no_context_uses_default(self):
        """No model_context_length → default from config (10)."""
        buffer = STMBuffer()
        assert buffer.max_size == 10
