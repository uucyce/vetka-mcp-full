"""
MARKER_UNDO-FIX: Tests for new backend ops — remove_clip, replace_media, set_transition.
These ops enable undo support for operations that previously bypassed the undo stack.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _make_state(clips_data: list[dict]) -> dict:
    """Create minimal timeline state with one lane."""
    return {
        "schema_version": "cut_timeline_state_v1",
        "project_id": "test",
        "timeline_id": "main",
        "revision": 1,
        "fps": 25,
        "lanes": [
            {
                "lane_id": "v1",
                "lane_type": "video_main",
                "clips": sorted(clips_data, key=lambda c: c["start_sec"]),
            }
        ],
        "selection": {"clip_ids": [], "scene_ids": []},
        "view": {"zoom": 60, "scroll_sec": 0},
        "updated_at": "2026-01-01T00:00:00Z",
    }


def _get_clip(state: dict, clip_id: str) -> dict | None:
    for lane in state["lanes"]:
        for clip in lane["clips"]:
            if clip["clip_id"] == clip_id:
                return clip
    return None


def _get_clips(state: dict, lane_id: str = "v1") -> list[dict]:
    for lane in state["lanes"]:
        if lane["lane_id"] == lane_id:
            return lane["clips"]
    return []


@pytest.fixture(autouse=True)
def _import_ops():
    """Import _apply_timeline_ops from cut_routes."""
    from src.api.routes.cut_routes import _apply_timeline_ops
    global apply_ops
    apply_ops = _apply_timeline_ops


# ─── remove_clip ───

class TestRemoveClip:
    def test_removes_clip_leaves_gap(self):
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5},
            {"clip_id": "B", "source_path": "/b.mp4", "start_sec": 5, "duration_sec": 5},
            {"clip_id": "C", "source_path": "/c.mp4", "start_sec": 10, "duration_sec": 5},
        ])
        new_state, applied = apply_ops(state, [{"op": "remove_clip", "clip_id": "B"}])
        clips = _get_clips(new_state)
        assert len(clips) == 2
        assert clips[0]["clip_id"] == "A"
        assert clips[1]["clip_id"] == "C"
        # C stays at 10 — gap is preserved (not rippled)
        assert clips[1]["start_sec"] == 10
        assert applied[0]["op"] == "remove_clip"
        assert applied[0]["clip_id"] == "B"

    def test_remove_nonexistent_raises(self):
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5},
        ])
        with pytest.raises(ValueError, match="clip not found"):
            apply_ops(state, [{"op": "remove_clip", "clip_id": "Z"}])

    def test_remove_only_clip(self):
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5},
        ])
        new_state, applied = apply_ops(state, [{"op": "remove_clip", "clip_id": "A"}])
        assert len(_get_clips(new_state)) == 0


# ─── replace_media ───

class TestReplaceMedia:
    def test_replaces_source_path(self):
        state = _make_state([
            {"clip_id": "A", "source_path": "/old.mp4", "start_sec": 0, "duration_sec": 5},
        ])
        new_state, applied = apply_ops(state, [{
            "op": "replace_media", "clip_id": "A",
            "source_path": "/new.mp4", "source_in": 2.5,
        }])
        clip = _get_clip(new_state, "A")
        assert clip["source_path"] == "/new.mp4"
        assert clip["source_in"] == 2.5
        # Position and duration unchanged
        assert clip["start_sec"] == 0
        assert clip["duration_sec"] == 5
        assert applied[0]["old_source_path"] == "/old.mp4"

    def test_replace_preserves_position(self):
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 3, "duration_sec": 7},
        ])
        new_state, _ = apply_ops(state, [{
            "op": "replace_media", "clip_id": "A",
            "source_path": "/b.mp4", "source_in": 0,
        }])
        clip = _get_clip(new_state, "A")
        assert clip["start_sec"] == 3
        assert clip["duration_sec"] == 7

    def test_replace_nonexistent_raises(self):
        state = _make_state([])
        with pytest.raises(ValueError, match="clip not found"):
            apply_ops(state, [{"op": "replace_media", "clip_id": "Z", "source_path": "/x.mp4"}])

    def test_replace_no_source_path_raises(self):
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5},
        ])
        with pytest.raises(ValueError, match="source_path is required"):
            apply_ops(state, [{"op": "replace_media", "clip_id": "A", "source_path": ""}])


# ─── set_transition ───

class TestSetTransition:
    def test_add_transition(self):
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5},
        ])
        new_state, applied = apply_ops(state, [{
            "op": "set_transition", "clip_id": "A",
            "transition": {"type": "cross_dissolve", "duration_sec": 1.0, "alignment": "center"},
        }])
        clip = _get_clip(new_state, "A")
        assert clip["transition_out"]["type"] == "cross_dissolve"
        assert clip["transition_out"]["duration_sec"] == 1.0
        assert applied[0]["old_transition"] is None

    def test_remove_transition(self):
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5,
             "transition_out": {"type": "cross_dissolve", "duration_sec": 1.0, "alignment": "center"}},
        ])
        new_state, applied = apply_ops(state, [{
            "op": "set_transition", "clip_id": "A", "transition": None,
        }])
        clip = _get_clip(new_state, "A")
        assert "transition_out" not in clip
        assert applied[0]["old_transition"]["type"] == "cross_dissolve"

    def test_replace_transition(self):
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5,
             "transition_out": {"type": "cross_dissolve", "duration_sec": 1.0, "alignment": "center"}},
        ])
        new_state, applied = apply_ops(state, [{
            "op": "set_transition", "clip_id": "A",
            "transition": {"type": "wipe", "duration_sec": 2.0, "alignment": "start"},
        }])
        clip = _get_clip(new_state, "A")
        assert clip["transition_out"]["type"] == "wipe"
        assert clip["transition_out"]["duration_sec"] == 2.0

    def test_transition_nonexistent_raises(self):
        state = _make_state([])
        with pytest.raises(ValueError, match="clip not found"):
            apply_ops(state, [{"op": "set_transition", "clip_id": "Z", "transition": None}])
