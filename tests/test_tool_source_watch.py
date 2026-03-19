"""
Tests for VETKA Tool Source Watch (Phase 195.2).

MARKER_195.2.TEST

Tests auto-discovery, git-based change detection, epoch tracking,
and freshness window logic.
"""

import json
import os
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.services.tool_source_watch import (
    ToolSourceWatch,
    ToolFreshnessEntry,
    FreshnessEvent,
    get_tool_source_watch,
    reset_tool_source_watch,
    FRESHNESS_WINDOW_HOURS,
)


# --- ToolFreshnessEntry unit tests ---

class TestToolFreshnessEntry:
    """Test ToolFreshnessEntry dataclass methods."""

    def test_is_recently_updated_true(self):
        now = datetime.now(timezone.utc).isoformat()
        entry = ToolFreshnessEntry(
            source_files=["src/mcp/tools/read_file_tool.py"],
            current_epoch=1,
            updated_at=now,
        )
        assert entry.is_recently_updated() is True

    def test_is_recently_updated_false_old(self):
        old = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
        entry = ToolFreshnessEntry(
            source_files=["src/mcp/tools/read_file_tool.py"],
            current_epoch=1,
            updated_at=old,
        )
        assert entry.is_recently_updated() is False

    def test_is_recently_updated_empty(self):
        entry = ToolFreshnessEntry(source_files=[])
        assert entry.is_recently_updated() is False

    def test_hours_since_update(self):
        two_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        entry = ToolFreshnessEntry(
            source_files=[],
            updated_at=two_hours_ago,
        )
        hours = entry.hours_since_update()
        assert 1.9 < hours < 2.1

    def test_hours_since_update_empty(self):
        entry = ToolFreshnessEntry(source_files=[])
        assert entry.hours_since_update() == float("inf")

    def test_epoch_for_timestamp(self):
        entry = ToolFreshnessEntry(
            source_files=[],
            current_epoch=3,
            history=[
                {"epoch": 0, "commit": "aaa", "ts": "2026-03-10T00:00:00+00:00"},
                {"epoch": 1, "commit": "bbb", "ts": "2026-03-12T00:00:00+00:00"},
                {"epoch": 2, "commit": "ccc", "ts": "2026-03-15T00:00:00+00:00"},
                {"epoch": 3, "commit": "ddd", "ts": "2026-03-18T00:00:00+00:00"},
            ],
        )
        # Before any epoch → 0
        assert entry.epoch_for_timestamp("2026-03-09T00:00:00+00:00") == 0
        # During epoch 0
        assert entry.epoch_for_timestamp("2026-03-11T00:00:00+00:00") == 0
        # During epoch 1
        assert entry.epoch_for_timestamp("2026-03-13T00:00:00+00:00") == 1
        # During epoch 2
        assert entry.epoch_for_timestamp("2026-03-16T00:00:00+00:00") == 2
        # During epoch 3 (current)
        assert entry.epoch_for_timestamp("2026-03-19T00:00:00+00:00") == 3

    def test_epoch_for_timestamp_empty_history(self):
        entry = ToolFreshnessEntry(source_files=[], history=[])
        assert entry.epoch_for_timestamp("2026-03-19T00:00:00+00:00") == 0

    def test_to_dict_and_from_dict_roundtrip(self):
        entry = ToolFreshnessEntry(
            source_files=["src/mcp/tools/read_file_tool.py"],
            current_epoch=2,
            last_commit="abc123",
            last_mtime=1234567.0,
            updated_at="2026-03-19T00:00:00+00:00",
            history=[
                {"epoch": 0, "commit": "aaa", "ts": "2026-03-10T00:00:00+00:00"},
                {"epoch": 1, "commit": "bbb", "ts": "2026-03-15T00:00:00+00:00"},
                {"epoch": 2, "commit": "abc123", "ts": "2026-03-19T00:00:00+00:00"},
            ],
        )
        d = entry.to_dict()
        restored = ToolFreshnessEntry.from_dict(d)
        assert restored.current_epoch == 2
        assert restored.last_commit == "abc123"
        assert len(restored.history) == 3
        assert restored.source_files == ["src/mcp/tools/read_file_tool.py"]


# --- FreshnessEvent tests ---

class TestFreshnessEvent:

    def test_event_creation(self):
        event = FreshnessEvent(
            tool_id="vetka_read_file",
            source_files=["src/mcp/tools/read_file_tool.py"],
            old_commit="aaa",
            new_commit="bbb",
            old_epoch=0,
            new_epoch=1,
        )
        assert event.tool_id == "vetka_read_file"
        assert event.new_epoch == 1
        assert event.updated_at  # auto-filled

    def test_event_to_dict(self):
        event = FreshnessEvent(
            tool_id="vetka_edit_file",
            source_files=["src/mcp/tools/edit_file_tool.py"],
            old_commit="x",
            new_commit="y",
            old_epoch=1,
            new_epoch=2,
        )
        d = event.to_dict()
        assert d["tool_id"] == "vetka_edit_file"
        assert d["new_epoch"] == 2


# --- ToolSourceWatch integration tests ---

class TestToolSourceWatchAutoDiscover:
    """Test auto-discovery of tool→source file mapping."""

    def test_auto_discover_finds_tools(self):
        """Verify auto-discovery finds tools from src/mcp/tools/*.py."""
        watch = ToolSourceWatch()
        source_map = watch._auto_discover()

        # Should find key tools
        assert "vetka_read_file" in source_map
        assert "vetka_edit_file" in source_map
        assert "vetka_search" in source_map
        assert "vetka_session_init" in source_map
        assert "vetka_git_status" in source_map
        assert "vetka_camera_focus" in source_map

        # Should map to correct files
        assert any("read_file_tool.py" in f for f in source_map["vetka_read_file"])
        assert any("edit_file_tool.py" in f for f in source_map["vetka_edit_file"])
        assert any("session_tools.py" in f for f in source_map["vetka_session_init"])

    def test_auto_discover_coverage(self):
        """At least 80% of tool_catalog.json tools should be discovered."""
        watch = ToolSourceWatch()
        source_map = watch._auto_discover()

        # Load tool catalog
        catalog_path = Path(__file__).parent.parent / "data" / "reflex" / "tool_catalog.json"
        if not catalog_path.exists():
            pytest.skip("tool_catalog.json not found")

        with open(catalog_path) as f:
            catalog = json.load(f)

        catalog_tools = {t["tool_id"] for t in catalog.get("tools", []) if t.get("active", True)}

        # Only count vetka/mycelium tools that have source in src/mcp/tools/
        # (cut/internal tools may be defined elsewhere)
        discoverable = {t for t in catalog_tools if t.startswith("vetka_")}
        discovered = {t for t in source_map if t.startswith("vetka_")}

        if discoverable:
            coverage = len(discovered & discoverable) / len(discoverable)
            assert coverage >= 0.8, (
                f"Coverage {coverage:.0%} < 80%. "
                f"Missing: {discoverable - discovered}"
            )


class TestToolSourceWatchPersistence:
    """Test persistence of freshness data."""

    def test_save_and_load_freshness(self, tmp_path):
        """Freshness data should survive save/load cycle."""
        freshness_path = tmp_path / "tool_freshness.json"

        watch = ToolSourceWatch()

        # Inject test data
        entry = ToolFreshnessEntry(
            source_files=["src/mcp/tools/read_file_tool.py"],
            current_epoch=2,
            last_commit="abc123",
            updated_at="2026-03-19T00:00:00+00:00",
            history=[
                {"epoch": 0, "commit": "x", "ts": "2026-03-10T00:00:00+00:00"},
                {"epoch": 1, "commit": "y", "ts": "2026-03-15T00:00:00+00:00"},
                {"epoch": 2, "commit": "abc123", "ts": "2026-03-19T00:00:00+00:00"},
            ],
        )
        data = {"vetka_read_file": entry}

        # Save
        with patch("src.services.tool_source_watch.TOOL_FRESHNESS_PATH", freshness_path):
            with patch("src.services.tool_source_watch.REFLEX_DATA_DIR", tmp_path):
                watch._save_freshness(data)

        assert freshness_path.exists()

        # Load in fresh instance
        watch2 = ToolSourceWatch()
        with patch("src.services.tool_source_watch.TOOL_FRESHNESS_PATH", freshness_path):
            loaded = watch2._load_freshness()

        assert "vetka_read_file" in loaded
        assert loaded["vetka_read_file"].current_epoch == 2
        assert loaded["vetka_read_file"].last_commit == "abc123"

    def test_save_and_load_source_map(self, tmp_path):
        """Source map should survive save/load cycle."""
        map_path = tmp_path / "tool_source_map.json"

        watch = ToolSourceWatch()
        test_map = {
            "vetka_read_file": ["src/mcp/tools/read_file_tool.py"],
            "vetka_edit_file": ["src/mcp/tools/edit_file_tool.py"],
        }

        with patch("src.services.tool_source_watch.TOOL_SOURCE_MAP_PATH", map_path):
            with patch("src.services.tool_source_watch.REFLEX_DATA_DIR", tmp_path):
                watch._save_source_map(test_map)

        assert map_path.exists()

        watch2 = ToolSourceWatch()
        with patch("src.services.tool_source_watch.TOOL_SOURCE_MAP_PATH", map_path):
            loaded = watch2._load_source_map()

        assert loaded == test_map


class TestToolSourceWatchScan:
    """Test scan_all() change detection."""

    def test_scan_detects_new_commit(self, tmp_path):
        """scan_all() should detect when git commit hash changes."""
        freshness_path = tmp_path / "tool_freshness.json"
        map_path = tmp_path / "tool_source_map.json"

        # Pre-populate with old commit
        old_freshness = {
            "vetka_read_file": {
                "source_files": ["src/mcp/tools/read_file_tool.py"],
                "current_epoch": 0,
                "last_commit": "old_commit_hash",
                "updated_at": "2026-03-10T00:00:00+00:00",
                "history": [
                    {"epoch": 0, "commit": "old_commit_hash", "ts": "2026-03-10T00:00:00+00:00"}
                ],
            }
        }
        with open(freshness_path, "w") as f:
            json.dump(old_freshness, f)

        source_map = {"vetka_read_file": ["src/mcp/tools/read_file_tool.py"]}
        with open(map_path, "w") as f:
            json.dump(source_map, f)

        watch = ToolSourceWatch()

        # Mock git to return new commit
        with patch("src.services.tool_source_watch.TOOL_FRESHNESS_PATH", freshness_path), \
             patch("src.services.tool_source_watch.TOOL_SOURCE_MAP_PATH", map_path), \
             patch("src.services.tool_source_watch.REFLEX_DATA_DIR", tmp_path), \
             patch.object(watch, "_batch_git_commits", return_value={
                 "src/mcp/tools/read_file_tool.py": "new_commit_hash"
             }):
            events = watch.scan_all()

        assert len(events) == 1
        assert events[0].tool_id == "vetka_read_file"
        assert events[0].old_epoch == 0
        assert events[0].new_epoch == 1
        assert events[0].new_commit == "new_commit_hash"

        # Verify persistence
        with open(freshness_path) as f:
            saved = json.load(f)
        assert saved["vetka_read_file"]["current_epoch"] == 1
        assert saved["vetka_read_file"]["last_commit"] == "new_commit_hash"

    def test_scan_no_change(self, tmp_path):
        """scan_all() should return empty when nothing changed."""
        freshness_path = tmp_path / "tool_freshness.json"
        map_path = tmp_path / "tool_source_map.json"

        old_freshness = {
            "vetka_read_file": {
                "source_files": ["src/mcp/tools/read_file_tool.py"],
                "current_epoch": 1,
                "last_commit": "same_commit",
                "updated_at": "2026-03-18T00:00:00+00:00",
                "history": [
                    {"epoch": 0, "commit": "old", "ts": "2026-03-10T00:00:00+00:00"},
                    {"epoch": 1, "commit": "same_commit", "ts": "2026-03-18T00:00:00+00:00"},
                ],
            }
        }
        with open(freshness_path, "w") as f:
            json.dump(old_freshness, f)

        source_map = {"vetka_read_file": ["src/mcp/tools/read_file_tool.py"]}
        with open(map_path, "w") as f:
            json.dump(source_map, f)

        watch = ToolSourceWatch()

        with patch("src.services.tool_source_watch.TOOL_FRESHNESS_PATH", freshness_path), \
             patch("src.services.tool_source_watch.TOOL_SOURCE_MAP_PATH", map_path), \
             patch("src.services.tool_source_watch.REFLEX_DATA_DIR", tmp_path), \
             patch.object(watch, "_batch_git_commits", return_value={
                 "src/mcp/tools/read_file_tool.py": "same_commit"
             }):
            events = watch.scan_all()

        assert len(events) == 0


class TestToolSourceWatchSingleton:
    """Test singleton pattern."""

    def test_singleton(self):
        reset_tool_source_watch()
        w1 = get_tool_source_watch()
        w2 = get_tool_source_watch()
        assert w1 is w2
        reset_tool_source_watch()

    def test_reset(self):
        reset_tool_source_watch()
        w1 = get_tool_source_watch()
        reset_tool_source_watch()
        w2 = get_tool_source_watch()
        assert w1 is not w2
        reset_tool_source_watch()
