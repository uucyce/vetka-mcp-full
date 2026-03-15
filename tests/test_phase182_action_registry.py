"""
Tests for Phase 182: ActionRegistry — central agent action log.

MARKER_182.ACTIONREGISTRY tests:
- Basic log + flush
- Query by run_id, session_id, file
- Rotating trim (max 10k)
- Thread safety
- Edit files for Verifier merge
"""

import json
import threading
import time
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from src.orchestration.action_registry import (
    ActionLogEntry,
    ActionRegistry,
    MAX_ENTRIES,
)


@pytest.fixture
def tmp_log(tmp_path):
    """Create a temporary action log file path."""
    return tmp_path / "action_log.json"


@pytest.fixture
def registry(tmp_log):
    """Create a fresh ActionRegistry with temporary storage."""
    return ActionRegistry(storage_path=tmp_log)


class TestActionLogEntry:
    def test_create_entry(self):
        entry = ActionLogEntry(
            run_id="run_123",
            agent="opus",
            action="edit",
            file="src/main.py",
            result="success",
            session_id="sess_456",
            task_id="tb_789",
            duration_ms=100,
            metadata={"lines_changed": 5},
        )
        assert entry.run_id == "run_123"
        assert entry.agent == "opus"
        assert entry.action == "edit"
        assert entry.file == "src/main.py"
        assert entry.result == "success"
        assert entry.session_id == "sess_456"
        assert entry.task_id == "tb_789"
        assert entry.duration_ms == 100
        assert entry.metadata == {"lines_changed": 5}
        assert len(entry.id) == 16
        assert entry.timestamp  # ISO8601

    def test_to_dict_roundtrip(self):
        entry = ActionLogEntry(
            run_id="run_abc",
            agent="dragon",
            action="create",
            file="src/new.py",
        )
        d = entry.to_dict()
        restored = ActionLogEntry.from_dict(d)
        assert restored.run_id == entry.run_id
        assert restored.agent == entry.agent
        assert restored.action == entry.action
        assert restored.file == entry.file
        assert restored.id == entry.id
        assert restored.timestamp == entry.timestamp

    def test_defaults(self):
        entry = ActionLogEntry(run_id="r1", agent="a1", action="read", file="f1")
        assert entry.result == "success"
        assert entry.session_id is None
        assert entry.task_id is None
        assert entry.duration_ms == 0
        assert entry.metadata == {}


class TestActionRegistryBasic:
    def test_log_and_flush(self, registry, tmp_log):
        registry.log_action(
            run_id="run_1",
            agent="opus",
            action="edit",
            file="src/main.py",
        )
        assert len(registry._buffer) == 1

        flushed = registry.flush()
        assert flushed == 1
        assert len(registry._buffer) == 0

        # Verify on disk
        data = json.loads(tmp_log.read_text())
        assert len(data) == 1
        assert data[0]["run_id"] == "run_1"
        assert data[0]["agent"] == "opus"
        assert data[0]["action"] == "edit"

    def test_auto_flush_at_threshold(self, registry, tmp_log):
        """Buffer auto-flushes at FLUSH_THRESHOLD (50)."""
        for i in range(50):
            registry.log_action(
                run_id="run_auto",
                agent="dragon",
                action="read",
                file=f"file_{i}.py",
            )

        # Should have auto-flushed
        assert len(registry._buffer) == 0
        data = json.loads(tmp_log.read_text())
        assert len(data) == 50

    def test_multiple_flushes_append(self, registry, tmp_log):
        registry.log_action(run_id="r1", agent="a1", action="edit", file="f1.py")
        registry.flush()

        registry.log_action(run_id="r2", agent="a2", action="create", file="f2.py")
        registry.flush()

        data = json.loads(tmp_log.read_text())
        assert len(data) == 2
        assert data[0]["run_id"] == "r1"
        assert data[1]["run_id"] == "r2"

    def test_empty_flush(self, registry):
        assert registry.flush() == 0


class TestActionRegistryQuery:
    def test_get_actions_for_run(self, registry):
        registry.log_action(run_id="run_A", agent="opus", action="edit", file="a.py")
        registry.log_action(run_id="run_B", agent="cursor", action="edit", file="b.py")
        registry.log_action(run_id="run_A", agent="opus", action="read", file="c.py")
        registry.flush()

        actions = registry.get_actions_for_run("run_A")
        assert len(actions) == 2
        assert all(a["run_id"] == "run_A" for a in actions)

    def test_get_actions_for_session(self, registry):
        registry.log_action(run_id="r1", agent="opus", action="edit", file="a.py", session_id="sess_1")
        registry.log_action(run_id="r2", agent="cursor", action="edit", file="b.py", session_id="sess_1")
        registry.log_action(run_id="r3", agent="dragon", action="edit", file="c.py", session_id="sess_2")
        registry.flush()

        actions = registry.get_actions_for_session("sess_1")
        assert len(actions) == 2
        assert all(a["session_id"] == "sess_1" for a in actions)

    def test_get_actions_for_file(self, registry):
        registry.log_action(run_id="r1", agent="opus", action="edit", file="src/main.py")
        registry.log_action(run_id="r1", agent="opus", action="read", file="src/main.py")
        registry.log_action(run_id="r1", agent="opus", action="edit", file="src/other.py")
        registry.flush()

        actions = registry.get_actions_for_file("src/main.py")
        assert len(actions) == 2

    def test_get_edit_files_for_run(self, registry):
        registry.log_action(run_id="run_X", agent="coder", action="edit", file="src/a.py")
        registry.log_action(run_id="run_X", agent="coder", action="create", file="src/b.py")
        registry.log_action(run_id="run_X", agent="coder", action="read", file="src/c.py")
        registry.log_action(run_id="run_X", agent="coder", action="edit", file="src/a.py")  # duplicate
        registry.log_action(run_id="run_X", agent="coder", action="edit", file="src/d.py", result="failed")
        registry.flush()

        files = registry.get_edit_files_for_run("run_X")
        assert files == ["src/a.py", "src/b.py"]  # sorted, unique, success only

    def test_query_includes_unflushed_buffer(self, registry):
        """Queries should include both persisted and buffered entries."""
        registry.log_action(run_id="run_Z", agent="opus", action="edit", file="a.py")
        registry.flush()

        # Add to buffer without flushing
        registry.log_action(run_id="run_Z", agent="opus", action="edit", file="b.py")

        actions = registry.get_actions_for_run("run_Z")
        assert len(actions) == 2


class TestActionRegistryTrim:
    def test_trim_to_max_entries(self, registry, tmp_log):
        """Log should trim to MAX_ENTRIES on flush."""
        # Pre-populate with MAX_ENTRIES - 10
        existing = [
            {"id": f"old_{i}", "run_id": "old", "agent": "old", "action": "read",
             "file": "old.py", "result": "success", "duration_ms": 0,
             "timestamp": "2026-01-01T00:00:00+00:00", "metadata": {},
             "session_id": None, "task_id": None}
            for i in range(MAX_ENTRIES - 10)
        ]
        tmp_log.write_text(json.dumps(existing))

        # Add 20 new entries (should trim to MAX_ENTRIES)
        for i in range(20):
            registry.log_action(run_id="new", agent="new", action="edit", file=f"new_{i}.py")
        registry.flush()

        data = json.loads(tmp_log.read_text())
        assert len(data) == MAX_ENTRIES
        # Newest entries should be preserved
        assert data[-1]["run_id"] == "new"


class TestActionRegistryThreadSafety:
    def test_concurrent_logging(self, registry):
        """Multiple threads should be able to log simultaneously."""
        errors = []

        def log_actions(thread_id):
            try:
                for i in range(20):
                    registry.log_action(
                        run_id=f"run_thread_{thread_id}",
                        agent=f"agent_{thread_id}",
                        action="edit",
                        file=f"file_{thread_id}_{i}.py",
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=log_actions, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

        # Flush remaining
        registry.flush()

        # All 100 entries should be present
        total = sum(
            len(registry.get_actions_for_run(f"run_thread_{t}"))
            for t in range(5)
        )
        assert total == 100


class TestActionRegistryStats:
    def test_get_stats(self, registry):
        registry.log_action(run_id="r1", agent="opus", action="edit", file="a.py")
        registry.log_action(run_id="r1", agent="opus", action="read", file="b.py")
        registry.log_action(run_id="r1", agent="dragon", action="edit", file="c.py")
        registry.flush()

        stats = registry.get_stats()
        assert stats["total_persisted"] == 3
        assert stats["buffered"] == 0
        assert stats["action_counts"]["edit"] == 2
        assert stats["action_counts"]["read"] == 1
        assert stats["agent_counts"]["opus"] == 2
        assert stats["agent_counts"]["dragon"] == 1


class TestActionRegistryEdgeCases:
    def test_nonexistent_log_file(self, tmp_path):
        """Should handle missing log file gracefully."""
        registry = ActionRegistry(storage_path=tmp_path / "nonexistent" / "log.json")
        actions = registry.get_actions_for_run("anything")
        assert actions == []

    def test_corrupted_log_file(self, tmp_log):
        """Should handle corrupted JSON gracefully."""
        tmp_log.write_text("this is not json {{{")
        registry = ActionRegistry(storage_path=tmp_log)
        actions = registry.get_actions_for_run("anything")
        assert actions == []

    def test_empty_log_file(self, tmp_log):
        """Should handle empty file gracefully."""
        tmp_log.write_text("")
        registry = ActionRegistry(storage_path=tmp_log)
        actions = registry.get_actions_for_run("anything")
        assert actions == []

    def test_run_id_uniqueness(self, registry):
        """Run IDs should be unique per entry."""
        entries = set()
        for i in range(100):
            entry = registry.log_action(
                run_id="run_same",
                agent="opus",
                action="edit",
                file=f"file_{i}.py",
            )
            entries.add(entry.id)
        assert len(entries) == 100  # All unique IDs
