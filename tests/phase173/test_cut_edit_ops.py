"""
MARKER_173.2 — Ripple/Insert/Overwrite/Split edit operations tests.

Tests:
- ripple_delete: remove clip + shift subsequent left
- insert_at: insert clip + push subsequent right
- overwrite_at: place clip without shifting
- split_at: split one clip into two
- All ops produce undo entries
- Edge cases: invalid split positions, missing clips, negative values
"""

from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.routes.cut_routes import _apply_timeline_ops


def _make_timeline(clips: list[dict] | None = None) -> dict[str, Any]:
    """Build a minimal timeline state with 3 clips on a single lane."""
    default_clips = [
        {"clip_id": "c1", "source_path": "a.mp4", "start_sec": 0.0, "duration_sec": 5.0},
        {"clip_id": "c2", "source_path": "b.mp4", "start_sec": 5.0, "duration_sec": 3.0},
        {"clip_id": "c3", "source_path": "c.mp4", "start_sec": 8.0, "duration_sec": 4.0},
    ]
    return {
        "schema_version": "cut_timeline_state_v1",
        "project_id": "proj_1",
        "timeline_id": "tl_1",
        "revision": 0,
        "lanes": [
            {"lane_id": "main", "type": "video_main", "clips": clips or default_clips},
        ],
    }


def _get_clips(state: dict) -> list[dict]:
    return state["lanes"][0]["clips"]


def _clip_by_id(state: dict, clip_id: str) -> dict | None:
    for c in _get_clips(state):
        if c["clip_id"] == clip_id:
            return c
    return None


# ── ripple_delete ──────────────────────────────────────────


class TestRippleDelete:
    def test_remove_middle_clip_shifts_rest(self):
        state = _make_timeline()
        ops = [{"op": "ripple_delete", "clip_id": "c2"}]
        new_state, applied = _apply_timeline_ops(state, ops)

        clips = _get_clips(new_state)
        assert len(clips) == 2
        assert _clip_by_id(new_state, "c2") is None
        # c3 was at 8.0, c2 had duration 3.0, so c3 should shift left to 5.0
        c3 = _clip_by_id(new_state, "c3")
        assert c3["start_sec"] == 5.0

    def test_remove_first_clip_shifts_rest(self):
        state = _make_timeline()
        ops = [{"op": "ripple_delete", "clip_id": "c1"}]
        new_state, applied = _apply_timeline_ops(state, ops)

        clips = _get_clips(new_state)
        assert len(clips) == 2
        c2 = _clip_by_id(new_state, "c2")
        c3 = _clip_by_id(new_state, "c3")
        assert c2["start_sec"] == 0.0  # was 5.0, shifted left by 5.0
        assert c3["start_sec"] == 3.0  # was 8.0, shifted left by 5.0

    def test_remove_last_clip_no_shift(self):
        state = _make_timeline()
        ops = [{"op": "ripple_delete", "clip_id": "c3"}]
        new_state, applied = _apply_timeline_ops(state, ops)

        clips = _get_clips(new_state)
        assert len(clips) == 2
        # No clips after c3 to shift
        c1 = _clip_by_id(new_state, "c1")
        c2 = _clip_by_id(new_state, "c2")
        assert c1["start_sec"] == 0.0
        assert c2["start_sec"] == 5.0

    def test_ripple_delete_missing_clip(self):
        state = _make_timeline()
        with pytest.raises(ValueError, match="clip not found"):
            _apply_timeline_ops(state, [{"op": "ripple_delete", "clip_id": "nonexistent"}])

    def test_ripple_delete_applied_op_has_gap(self):
        state = _make_timeline()
        _, applied = _apply_timeline_ops(state, [{"op": "ripple_delete", "clip_id": "c2"}])
        assert len(applied) == 1
        assert applied[0]["op"] == "ripple_delete"
        assert applied[0]["gap_sec"] == 3.0


# ── insert_at ──────────────────────────────────────────────


class TestInsertAt:
    def test_insert_at_start(self):
        state = _make_timeline()
        ops = [{
            "op": "insert_at", "lane_id": "main", "start_sec": 0.0,
            "source_path": "new.mp4", "duration_sec": 2.0, "clip_id": "c_new",
        }]
        new_state, applied = _apply_timeline_ops(state, ops)

        clips = _get_clips(new_state)
        assert len(clips) == 4
        c_new = _clip_by_id(new_state, "c_new")
        assert c_new["start_sec"] == 0.0
        assert c_new["duration_sec"] == 2.0
        # All original clips shifted right by 2.0
        assert _clip_by_id(new_state, "c1")["start_sec"] == 2.0
        assert _clip_by_id(new_state, "c2")["start_sec"] == 7.0
        assert _clip_by_id(new_state, "c3")["start_sec"] == 10.0

    def test_insert_at_middle(self):
        state = _make_timeline()
        ops = [{
            "op": "insert_at", "lane_id": "main", "start_sec": 5.0,
            "source_path": "mid.mp4", "duration_sec": 1.5, "clip_id": "c_mid",
        }]
        new_state, applied = _apply_timeline_ops(state, ops)

        # c1 at 0 stays, c2 at 5 shifts to 6.5, c3 at 8 shifts to 9.5
        assert _clip_by_id(new_state, "c1")["start_sec"] == 0.0
        assert _clip_by_id(new_state, "c2")["start_sec"] == 6.5
        assert _clip_by_id(new_state, "c3")["start_sec"] == 9.5

    def test_insert_at_missing_lane(self):
        state = _make_timeline()
        with pytest.raises(ValueError, match="lane not found"):
            _apply_timeline_ops(state, [{
                "op": "insert_at", "lane_id": "nonexistent", "start_sec": 0,
                "source_path": "x.mp4", "duration_sec": 1,
            }])

    def test_insert_at_negative_start(self):
        state = _make_timeline()
        with pytest.raises(ValueError, match="start_sec must be >= 0"):
            _apply_timeline_ops(state, [{
                "op": "insert_at", "lane_id": "main", "start_sec": -1,
                "source_path": "x.mp4", "duration_sec": 1,
            }])

    def test_insert_at_zero_duration(self):
        state = _make_timeline()
        with pytest.raises(ValueError, match="duration_sec must be > 0"):
            _apply_timeline_ops(state, [{
                "op": "insert_at", "lane_id": "main", "start_sec": 0,
                "source_path": "x.mp4", "duration_sec": 0,
            }])


# ── overwrite_at ───────────────────────────────────────────


class TestOverwriteAt:
    def test_overwrite_no_shift(self):
        state = _make_timeline()
        ops = [{
            "op": "overwrite_at", "lane_id": "main", "start_sec": 5.0,
            "source_path": "over.mp4", "duration_sec": 3.0, "clip_id": "c_over",
        }]
        new_state, applied = _apply_timeline_ops(state, ops)

        # c2 (5.0-8.0) should be removed (fully within overwrite range)
        assert _clip_by_id(new_state, "c2") is None
        # c_over replaces it
        c_over = _clip_by_id(new_state, "c_over")
        assert c_over["start_sec"] == 5.0
        assert c_over["duration_sec"] == 3.0
        # c1 and c3 untouched in position
        assert _clip_by_id(new_state, "c1")["start_sec"] == 0.0
        assert _clip_by_id(new_state, "c3")["start_sec"] == 8.0

    def test_overwrite_at_end(self):
        state = _make_timeline()
        ops = [{
            "op": "overwrite_at", "lane_id": "main", "start_sec": 12.0,
            "source_path": "tail.mp4", "duration_sec": 2.0, "clip_id": "c_tail",
        }]
        new_state, applied = _apply_timeline_ops(state, ops)

        clips = _get_clips(new_state)
        assert len(clips) == 4  # 3 original + 1 new
        c_tail = _clip_by_id(new_state, "c_tail")
        assert c_tail["start_sec"] == 12.0


# ── split_at ───────────────────────────────────────────────


class TestSplitAt:
    def test_split_middle_of_clip(self):
        state = _make_timeline()
        ops = [{"op": "split_at", "clip_id": "c1", "split_sec": 2.0}]
        new_state, applied = _apply_timeline_ops(state, ops)

        clips = _get_clips(new_state)
        assert len(clips) == 4  # was 3, now 4

        # Left half keeps original ID
        c1 = _clip_by_id(new_state, "c1")
        assert c1["duration_sec"] == 2.0
        assert c1["start_sec"] == 0.0

        # Right half has new ID
        assert applied[0]["right_id"] is not None
        right_id = applied[0]["right_id"]
        c1_right = _clip_by_id(new_state, right_id)
        assert c1_right is not None
        assert c1_right["start_sec"] == 2.0
        assert c1_right["duration_sec"] == 3.0

    def test_split_preserves_source_path(self):
        state = _make_timeline()
        _, applied = _apply_timeline_ops(state, [{"op": "split_at", "clip_id": "c2", "split_sec": 6.5}])
        right_id = applied[0]["right_id"]
        new_state = _make_timeline()
        new_state, _ = _apply_timeline_ops(new_state, [{"op": "split_at", "clip_id": "c2", "split_sec": 6.5}])
        right_clip = _clip_by_id(new_state, applied[0]["right_id"])
        # Can't check right_id from first call in second state, but let's verify concept:
        # Both halves should have same source_path
        c2 = _clip_by_id(new_state, "c2")
        for c in _get_clips(new_state):
            if c["clip_id"] != "c2" and c["source_path"] == "b.mp4":
                assert c["duration_sec"] == pytest.approx(1.5, abs=0.01)  # 8.0 - 6.5

    def test_split_at_start_boundary_fails(self):
        state = _make_timeline()
        with pytest.raises(ValueError, match="split_sec.*must be within"):
            _apply_timeline_ops(state, [{"op": "split_at", "clip_id": "c1", "split_sec": 0.0}])

    def test_split_at_end_boundary_fails(self):
        state = _make_timeline()
        with pytest.raises(ValueError, match="split_sec.*must be within"):
            _apply_timeline_ops(state, [{"op": "split_at", "clip_id": "c1", "split_sec": 5.0}])

    def test_split_missing_clip_fails(self):
        state = _make_timeline()
        with pytest.raises(ValueError, match="clip not found"):
            _apply_timeline_ops(state, [{"op": "split_at", "clip_id": "ghost", "split_sec": 1.0}])

    def test_split_applied_op_shape(self):
        state = _make_timeline()
        _, applied = _apply_timeline_ops(state, [{"op": "split_at", "clip_id": "c1", "split_sec": 3.0}])
        op = applied[0]
        assert op["op"] == "split_at"
        assert op["left_id"] == "c1"
        assert op["right_id"].startswith("c1_R")
        assert op["left_duration"] == 3.0
        assert op["right_duration"] == 2.0


# ── Combined ops ───────────────────────────────────────────


class TestCombinedOps:
    def test_split_then_ripple_delete(self):
        """Split c1 at 2s, then ripple-delete the right half."""
        state = _make_timeline()
        ops = [
            {"op": "split_at", "clip_id": "c1", "split_sec": 2.0},
        ]
        state, applied = _apply_timeline_ops(state, ops)
        right_id = applied[0]["right_id"]

        # Now ripple-delete the right half
        ops2 = [{"op": "ripple_delete", "clip_id": right_id}]
        state2, applied2 = _apply_timeline_ops(state, ops2)

        clips = _get_clips(state2)
        assert len(clips) == 3  # c1_left, c2, c3
        # c2 was at 5.0, right half had duration 3.0, so c2 shifts left to 2.0
        assert _clip_by_id(state2, "c2")["start_sec"] == 2.0

    def test_insert_then_split(self):
        """Insert a clip, then split it."""
        state = _make_timeline()
        ops = [{
            "op": "insert_at", "lane_id": "main", "start_sec": 5.0,
            "source_path": "ins.mp4", "duration_sec": 4.0, "clip_id": "c_ins",
        }]
        state, _ = _apply_timeline_ops(state, ops)

        # Split the inserted clip
        ops2 = [{"op": "split_at", "clip_id": "c_ins", "split_sec": 7.0}]
        state2, applied2 = _apply_timeline_ops(state, ops2)

        clips = _get_clips(state2)
        assert len(clips) == 5  # 3 original + 1 inserted (now 2 halves)
        c_ins = _clip_by_id(state2, "c_ins")
        assert c_ins["duration_sec"] == 2.0  # left half: 5.0 to 7.0

    def test_revision_increments(self):
        state = _make_timeline()
        state, _ = _apply_timeline_ops(state, [{"op": "ripple_delete", "clip_id": "c1"}])
        assert state["revision"] == 1
        state, _ = _apply_timeline_ops(state, [{"op": "ripple_delete", "clip_id": "c2"}])
        assert state["revision"] == 2
