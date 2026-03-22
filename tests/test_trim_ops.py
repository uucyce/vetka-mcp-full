"""
MARKER_A2.7: Reference tests for slip_clip and ripple_trim backend ops.
Tests the pure _apply_timeline_ops logic without HTTP overhead.
"""
import pytest
import sys
import os

# Add project root to path so we can import the ops function
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


class TestSlipClip:
    """MARKER_A2.1: slip_clip changes source_in without moving clip."""

    def _apply(self, state, ops):
        from src.api.routes.cut_routes import _apply_timeline_ops
        return _apply_timeline_ops(state, ops)

    def test_slip_sets_source_in(self):
        state = _make_state([
            {"clip_id": "c1", "start_sec": 0, "duration_sec": 5, "source_path": "/a.mp4"},
        ])
        new_state, applied = self._apply(state, [
            {"op": "slip_clip", "clip_id": "c1", "source_in": 2.5},
        ])
        clip = _get_clip(new_state, "c1")
        assert clip["source_in"] == 2.5
        assert clip["start_sec"] == 0  # position unchanged
        assert clip["duration_sec"] == 5  # duration unchanged

    def test_slip_does_not_move_clip(self):
        state = _make_state([
            {"clip_id": "c1", "start_sec": 3.0, "duration_sec": 4, "source_path": "/a.mp4"},
            {"clip_id": "c2", "start_sec": 7.0, "duration_sec": 3, "source_path": "/b.mp4"},
        ])
        new_state, _ = self._apply(state, [
            {"op": "slip_clip", "clip_id": "c1", "source_in": 1.0},
        ])
        c1 = _get_clip(new_state, "c1")
        c2 = _get_clip(new_state, "c2")
        assert c1["start_sec"] == 3.0
        assert c2["start_sec"] == 7.0  # neighbor not affected

    def test_slip_negative_clamped_to_zero(self):
        state = _make_state([
            {"clip_id": "c1", "start_sec": 0, "duration_sec": 5, "source_path": "/a.mp4"},
        ])
        new_state, _ = self._apply(state, [
            {"op": "slip_clip", "clip_id": "c1", "source_in": -3.0},
        ])
        clip = _get_clip(new_state, "c1")
        assert clip["source_in"] == 0.0

    def test_slip_unknown_clip_raises(self):
        state = _make_state([
            {"clip_id": "c1", "start_sec": 0, "duration_sec": 5, "source_path": "/a.mp4"},
        ])
        with pytest.raises(ValueError, match="clip not found"):
            self._apply(state, [{"op": "slip_clip", "clip_id": "nonexistent", "source_in": 1.0}])


class TestRippleTrim:
    """MARKER_A2.2: ripple_trim trims clip edge and shifts subsequent clips."""

    def _apply(self, state, ops):
        from src.api.routes.cut_routes import _apply_timeline_ops
        return _apply_timeline_ops(state, ops)

    def test_ripple_extend_right_shifts_subsequent(self):
        """Extend clip right edge → subsequent clips shift right."""
        state = _make_state([
            {"clip_id": "c1", "start_sec": 0, "duration_sec": 5, "source_path": "/a.mp4"},
            {"clip_id": "c2", "start_sec": 5, "duration_sec": 3, "source_path": "/b.mp4"},
            {"clip_id": "c3", "start_sec": 8, "duration_sec": 4, "source_path": "/c.mp4"},
        ])
        # Extend c1 from 5s to 7s → delta = +2s
        new_state, applied = self._apply(state, [
            {"op": "ripple_trim", "clip_id": "c1", "start_sec": 0, "duration_sec": 7},
        ])
        c1 = _get_clip(new_state, "c1")
        c2 = _get_clip(new_state, "c2")
        c3 = _get_clip(new_state, "c3")
        assert c1["duration_sec"] == 7
        assert c2["start_sec"] == 7  # was 5, shifted +2
        assert c3["start_sec"] == 10  # was 8, shifted +2

    def test_ripple_shorten_right_shifts_subsequent_left(self):
        """Shorten clip right edge → subsequent clips shift left."""
        state = _make_state([
            {"clip_id": "c1", "start_sec": 0, "duration_sec": 5, "source_path": "/a.mp4"},
            {"clip_id": "c2", "start_sec": 5, "duration_sec": 3, "source_path": "/b.mp4"},
            {"clip_id": "c3", "start_sec": 8, "duration_sec": 4, "source_path": "/c.mp4"},
        ])
        # Shorten c1 from 5s to 3s → delta = -2s
        new_state, _ = self._apply(state, [
            {"op": "ripple_trim", "clip_id": "c1", "start_sec": 0, "duration_sec": 3},
        ])
        c1 = _get_clip(new_state, "c1")
        c2 = _get_clip(new_state, "c2")
        c3 = _get_clip(new_state, "c3")
        assert c1["duration_sec"] == 3
        assert c2["start_sec"] == 3  # was 5, shifted -2
        assert c3["start_sec"] == 6  # was 8, shifted -2

    def test_ripple_trim_left_edge(self):
        """Trim left edge (change start_sec) with ripple."""
        state = _make_state([
            {"clip_id": "c1", "start_sec": 2, "duration_sec": 5, "source_path": "/a.mp4"},
            {"clip_id": "c2", "start_sec": 7, "duration_sec": 3, "source_path": "/b.mp4"},
        ])
        # Trim c1 left edge: start 2→3, dur 5→4 → end stays at 7, delta = 0
        new_state, _ = self._apply(state, [
            {"op": "ripple_trim", "clip_id": "c1", "start_sec": 3, "duration_sec": 4},
        ])
        c1 = _get_clip(new_state, "c1")
        c2 = _get_clip(new_state, "c2")
        assert c1["start_sec"] == 3
        assert c1["duration_sec"] == 4
        assert c2["start_sec"] == 7  # end unchanged, no shift

    def test_ripple_does_not_affect_earlier_clips(self):
        """Clips before the trimmed clip should not shift."""
        state = _make_state([
            {"clip_id": "c0", "start_sec": 0, "duration_sec": 2, "source_path": "/z.mp4"},
            {"clip_id": "c1", "start_sec": 2, "duration_sec": 3, "source_path": "/a.mp4"},
            {"clip_id": "c2", "start_sec": 5, "duration_sec": 4, "source_path": "/b.mp4"},
        ])
        # Extend c1 by 1s → delta = +1
        new_state, _ = self._apply(state, [
            {"op": "ripple_trim", "clip_id": "c1", "start_sec": 2, "duration_sec": 4},
        ])
        c0 = _get_clip(new_state, "c0")
        c2 = _get_clip(new_state, "c2")
        assert c0["start_sec"] == 0  # earlier clip untouched
        assert c2["start_sec"] == 6  # was 5, shifted +1

    def test_ripple_invalid_duration_raises(self):
        state = _make_state([
            {"clip_id": "c1", "start_sec": 0, "duration_sec": 5, "source_path": "/a.mp4"},
        ])
        with pytest.raises(ValueError, match="duration_sec must be > 0"):
            self._apply(state, [{"op": "ripple_trim", "clip_id": "c1", "start_sec": 0, "duration_sec": -1}])

    def test_ripple_unknown_clip_raises(self):
        state = _make_state([
            {"clip_id": "c1", "start_sec": 0, "duration_sec": 5, "source_path": "/a.mp4"},
        ])
        with pytest.raises(ValueError, match="clip not found"):
            self._apply(state, [{"op": "ripple_trim", "clip_id": "ghost", "start_sec": 0, "duration_sec": 3}])
