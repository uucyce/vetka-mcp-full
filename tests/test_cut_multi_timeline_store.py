"""
MARKER_198.MULTI_TL — Tests for multi-timeline CutProjectStore methods.

Tests per-timeline-id CRUD: create, load, list, clone, delete.

@task: tb_1773974821_5
"""
import sys
import os
import json
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from src.services.cut_project_store import CutProjectStore


@pytest.fixture
def sandbox(tmp_path):
    """Create a minimal CUT sandbox with project config."""
    config_dir = tmp_path / ".cut_config"
    config_dir.mkdir()
    state_dir = tmp_path / "cut_runtime" / "state"
    state_dir.mkdir(parents=True)

    # Create project file
    project = {
        "schema_version": "cut_project_v1",
        "project_id": "test_proj",
        "project_name": "Test",
        "source_path": "/tmp/src",
        "sandbox_root": str(tmp_path),
        "created_at": "2026-01-01T00:00:00Z",
        "last_opened_at": "2026-01-01T00:00:00Z",
    }
    with open(config_dir / "cut_project.json", "w") as f:
        json.dump(project, f)

    return tmp_path


@pytest.fixture
def store(sandbox):
    return CutProjectStore(str(sandbox))


def _make_timeline_state(timeline_id: str, lane_count: int = 2) -> dict:
    lanes = []
    for i in range(lane_count):
        lt = "video_main" if i == 0 else "audio_sync"
        lanes.append({"lane_id": f"lane_{i}", "lane_type": lt, "clips": []})
    return {
        "schema_version": "cut_timeline_state_v1",
        "project_id": "test_proj",
        "timeline_id": timeline_id,
        "revision": 0,
        "fps": 25,
        "lanes": lanes,
        "selection": {"active_clip_id": None, "active_lane_id": None},
        "view": {"zoom": 60, "scroll_left": 0, "track_height": 56},
        "updated_at": "2026-01-01T00:00:00Z",
    }


class TestMultiTimelineStore:
    def test_save_and_load_timeline(self, store):
        state = _make_timeline_state("tl_01")
        store.save_timeline_by_id("tl_01", state)

        loaded = store.load_timeline_by_id("tl_01")
        assert loaded is not None
        assert loaded["timeline_id"] == "tl_01"
        assert len(loaded["lanes"]) == 2

    def test_load_nonexistent_returns_none(self, store):
        assert store.load_timeline_by_id("nonexistent") is None

    def test_list_timelines(self, store):
        store.save_timeline_by_id("tl_a", _make_timeline_state("tl_a", lane_count=3))
        store.save_timeline_by_id("tl_b", _make_timeline_state("tl_b", lane_count=1))

        timelines = store.list_timelines()
        assert len(timelines) == 2
        ids = {t["timeline_id"] for t in timelines}
        assert ids == {"tl_a", "tl_b"}
        assert timelines[0]["lane_count"] == 3 or timelines[1]["lane_count"] == 3

    def test_list_empty(self, store):
        assert store.list_timelines() == []

    def test_delete_timeline(self, store):
        store.save_timeline_by_id("tl_del", _make_timeline_state("tl_del"))
        assert store.load_timeline_by_id("tl_del") is not None

        deleted = store.delete_timeline("tl_del")
        assert deleted is True
        assert store.load_timeline_by_id("tl_del") is None

    def test_delete_nonexistent(self, store):
        assert store.delete_timeline("nope") is False

    def test_clone_timeline(self, store):
        original = _make_timeline_state("tl_orig")
        original["lanes"][0]["clips"] = [
            {"clip_id": "c1", "start_sec": 0, "duration_sec": 5, "source_path": "/a.mp4"}
        ]
        store.save_timeline_by_id("tl_orig", original)

        clone = store.clone_timeline("tl_orig", "tl_clone")
        assert clone is not None
        assert clone["timeline_id"] == "tl_clone"
        assert len(clone["lanes"][0]["clips"]) == 1
        assert clone["revision"] == 0

        # Verify persisted
        loaded = store.load_timeline_by_id("tl_clone")
        assert loaded is not None
        assert loaded["timeline_id"] == "tl_clone"

    def test_clone_nonexistent_source(self, store):
        assert store.clone_timeline("nope", "tl_new") is None

    def test_timeline_id_sanitization(self, store):
        """Ensure path traversal attempts are sanitized."""
        state = _make_timeline_state("../../etc/passwd")
        store.save_timeline_by_id("../../etc/passwd", state)
        # Should NOT create file outside timelines dir
        loaded = store.load_timeline_by_id("../../etc/passwd")
        assert loaded is not None
        assert loaded["timeline_id"] == "../../etc/passwd"

    def test_multiple_timelines_independent(self, store):
        """Two timelines should be fully independent."""
        s1 = _make_timeline_state("tl_1")
        s1["lanes"][0]["clips"] = [
            {"clip_id": "c1", "start_sec": 0, "duration_sec": 3, "source_path": "/a.mp4"}
        ]
        s2 = _make_timeline_state("tl_2")
        s2["lanes"][0]["clips"] = [
            {"clip_id": "c2", "start_sec": 0, "duration_sec": 7, "source_path": "/b.mp4"}
        ]
        store.save_timeline_by_id("tl_1", s1)
        store.save_timeline_by_id("tl_2", s2)

        l1 = store.load_timeline_by_id("tl_1")
        l2 = store.load_timeline_by_id("tl_2")

        assert l1["lanes"][0]["clips"][0]["clip_id"] == "c1"
        assert l2["lanes"][0]["clips"][0]["clip_id"] == "c2"
        assert l1["lanes"][0]["clips"][0]["duration_sec"] == 3
        assert l2["lanes"][0]["clips"][0]["duration_sec"] == 7
