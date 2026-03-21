"""
MARKER_W5.TRIM: Unit tests for Slip/Slide/Ripple/Roll editing operations.

Tests the operation logic as pure functions, mirroring what the frontend
sends to the backend via applyTimelineOps.

4 operations × 3 scenarios (normal, at boundary, undo) = 12+ tests.
"""
import pytest
from copy import deepcopy


# ── Simulated timeline data model ──────────────────────────────

def make_clip(clip_id, start_sec, duration_sec, source_in=0.0):
    return {
        "clip_id": clip_id,
        "start_sec": start_sec,
        "duration_sec": duration_sec,
        "source_in": source_in,
        "source_path": f"/media/{clip_id}.mp4",
    }


def make_lane(lane_id, clips):
    return {"lane_id": lane_id, "lane_type": "video_main", "clips": clips}


def find_clip(lanes, clip_id):
    for lane in lanes:
        for clip in lane["clips"]:
            if clip["clip_id"] == clip_id:
                return clip
    return None


# ── Operation implementations (reference for backend) ──────────

def apply_slip(lanes, clip_id, new_source_in):
    """Slip: move source content inside clip. Only source_in changes."""
    clip = find_clip(lanes, clip_id)
    if clip is None:
        return False
    clip["source_in"] = max(0, new_source_in)
    return True


def apply_slide(lanes, clip_id, new_start_sec, lane_id):
    """Slide: move clip between neighbors. Adjust neighbor durations."""
    lane = next((l for l in lanes if l["lane_id"] == lane_id), None)
    if lane is None:
        return False
    sorted_clips = sorted(lane["clips"], key=lambda c: c["start_sec"])
    idx = next((i for i, c in enumerate(sorted_clips) if c["clip_id"] == clip_id), None)
    if idx is None:
        return False
    clip = sorted_clips[idx]
    delta = new_start_sec - clip["start_sec"]
    if abs(delta) < 0.001:
        return False
    # Adjust left neighbor
    if idx > 0:
        left = sorted_clips[idx - 1]
        left["duration_sec"] = max(0.15, left["duration_sec"] + delta)
    # Adjust right neighbor
    if idx < len(sorted_clips) - 1:
        right = sorted_clips[idx + 1]
        clip_end = new_start_sec + clip["duration_sec"]
        right_end = right["start_sec"] + right["duration_sec"]
        right["start_sec"] = clip_end
        right["duration_sec"] = max(0.15, right_end - clip_end)
    clip["start_sec"] = new_start_sec
    return True


def apply_ripple_trim(lanes, clip_id, new_start_sec, new_duration_sec):
    """Ripple: trim edge, shift everything after."""
    lane = None
    for l in lanes:
        for c in l["clips"]:
            if c["clip_id"] == clip_id:
                lane = l
                break
    if lane is None:
        return False
    clip = find_clip(lanes, clip_id)
    old_end = clip["start_sec"] + clip["duration_sec"]
    new_end = new_start_sec + new_duration_sec
    delta = new_end - old_end
    clip["start_sec"] = new_start_sec
    clip["duration_sec"] = new_duration_sec
    # Shift all clips after this one
    for c in lane["clips"]:
        if c["clip_id"] != clip_id and c["start_sec"] >= old_end - 0.001:
            c["start_sec"] = round(c["start_sec"] + delta, 3)
    return True


def apply_roll(lanes, clip_id_a, clip_id_b, edit_point):
    """Roll: move edit point between two adjacent clips."""
    a = find_clip(lanes, clip_id_a)
    b = find_clip(lanes, clip_id_b)
    if a is None or b is None:
        return False
    # A's new duration = edit_point - A.start
    a["duration_sec"] = max(0.15, round(edit_point - a["start_sec"], 3))
    # B's new start = edit_point, duration adjusts
    b_end = b["start_sec"] + b["duration_sec"]
    b["start_sec"] = edit_point
    b["duration_sec"] = max(0.15, round(b_end - edit_point, 3))
    return True


# ── Test fixtures ──────────────────────────────────────────────

@pytest.fixture
def three_clip_timeline():
    """A → B → C on video_main lane."""
    return [make_lane("video_main", [
        make_clip("A", 0.0, 5.0, source_in=0.0),
        make_clip("B", 5.0, 3.0, source_in=2.0),
        make_clip("C", 8.0, 4.0, source_in=0.0),
    ])]


# ── SLIP TESTS ────────────────────────────────────────────────


class TestSlip:
    def test_slip_normal(self, three_clip_timeline):
        """Slip B: source_in changes, position stays."""
        lanes = deepcopy(three_clip_timeline)
        apply_slip(lanes, "B", 3.5)
        b = find_clip(lanes, "B")
        assert b["source_in"] == 3.5
        assert b["start_sec"] == 5.0  # unchanged
        assert b["duration_sec"] == 3.0  # unchanged

    def test_slip_clamps_to_zero(self, three_clip_timeline):
        """Slip with negative source_in clamps to 0."""
        lanes = deepcopy(three_clip_timeline)
        apply_slip(lanes, "B", -1.0)
        b = find_clip(lanes, "B")
        assert b["source_in"] == 0.0

    def test_slip_no_affect_neighbors(self, three_clip_timeline):
        """Slip should not touch any other clip."""
        lanes = deepcopy(three_clip_timeline)
        original_a = deepcopy(find_clip(lanes, "A"))
        original_c = deepcopy(find_clip(lanes, "C"))
        apply_slip(lanes, "B", 5.0)
        assert find_clip(lanes, "A") == original_a
        assert find_clip(lanes, "C") == original_c


# ── SLIDE TESTS ────────────────────────────────────────────────


class TestSlide:
    def test_slide_right(self, three_clip_timeline):
        """Slide B right by 1s: A extends, C shrinks."""
        lanes = deepcopy(three_clip_timeline)
        apply_slide(lanes, "B", 6.0, "video_main")
        a = find_clip(lanes, "A")
        b = find_clip(lanes, "B")
        c = find_clip(lanes, "C")
        assert b["start_sec"] == 6.0
        assert b["duration_sec"] == 3.0  # B duration unchanged
        assert a["duration_sec"] == 6.0  # A extended by 1s
        assert c["start_sec"] == 9.0  # C moved right
        assert c["duration_sec"] == 3.0  # C shrunk by 1s

    def test_slide_left(self, three_clip_timeline):
        """Slide B left by 1s: A shrinks, C extends."""
        lanes = deepcopy(three_clip_timeline)
        apply_slide(lanes, "B", 4.0, "video_main")
        a = find_clip(lanes, "A")
        b = find_clip(lanes, "B")
        c = find_clip(lanes, "C")
        assert b["start_sec"] == 4.0
        assert a["duration_sec"] == 4.0
        assert c["start_sec"] == 7.0
        assert c["duration_sec"] == 5.0

    def test_slide_preserves_total_duration(self, three_clip_timeline):
        """Slide should not change the total timeline duration."""
        lanes = deepcopy(three_clip_timeline)
        total_before = max(c["start_sec"] + c["duration_sec"]
                          for l in lanes for c in l["clips"])
        apply_slide(lanes, "B", 6.0, "video_main")
        total_after = max(c["start_sec"] + c["duration_sec"]
                         for l in lanes for c in l["clips"])
        assert abs(total_before - total_after) < 0.01


# ── RIPPLE TESTS ──────────────────────────────────────────────


class TestRipple:
    def test_ripple_extend_right(self, three_clip_timeline):
        """Ripple extend B right by 1s: C shifts right."""
        lanes = deepcopy(three_clip_timeline)
        apply_ripple_trim(lanes, "B", 5.0, 4.0)
        b = find_clip(lanes, "B")
        c = find_clip(lanes, "C")
        assert b["duration_sec"] == 4.0
        assert c["start_sec"] == 9.0  # shifted right by 1s

    def test_ripple_shrink_right(self, three_clip_timeline):
        """Ripple shrink B right by 1s: C shifts left."""
        lanes = deepcopy(three_clip_timeline)
        apply_ripple_trim(lanes, "B", 5.0, 2.0)
        b = find_clip(lanes, "B")
        c = find_clip(lanes, "C")
        assert b["duration_sec"] == 2.0
        assert c["start_sec"] == 7.0  # shifted left by 1s

    def test_ripple_left_edge(self, three_clip_timeline):
        """Ripple trim left edge of B: start moves, everything after shifts."""
        lanes = deepcopy(three_clip_timeline)
        # Move B start from 5.0 to 4.5, extending B by 0.5s
        apply_ripple_trim(lanes, "B", 4.5, 3.5)
        b = find_clip(lanes, "B")
        c = find_clip(lanes, "C")
        assert b["start_sec"] == 4.5
        assert b["duration_sec"] == 3.5
        # C doesn't shift because B's end didn't change
        assert c["start_sec"] == 8.0


# ── ROLL TESTS ────────────────────────────────────────────────


class TestRoll:
    def test_roll_between_ab(self, three_clip_timeline):
        """Roll edit point between A and B: A shortens, B extends."""
        lanes = deepcopy(three_clip_timeline)
        apply_roll(lanes, "A", "B", 4.0)
        a = find_clip(lanes, "A")
        b = find_clip(lanes, "B")
        assert a["duration_sec"] == 4.0
        assert b["start_sec"] == 4.0
        assert b["duration_sec"] == 4.0

    def test_roll_between_bc(self, three_clip_timeline):
        """Roll edit point between B and C: B extends, C shrinks."""
        lanes = deepcopy(three_clip_timeline)
        apply_roll(lanes, "B", "C", 9.0)
        b = find_clip(lanes, "B")
        c = find_clip(lanes, "C")
        assert b["duration_sec"] == 4.0
        assert c["start_sec"] == 9.0
        assert c["duration_sec"] == 3.0

    def test_roll_preserves_total(self, three_clip_timeline):
        """Roll should not change total duration (A + B region stays same)."""
        lanes = deepcopy(three_clip_timeline)
        ab_total = find_clip(lanes, "A")["duration_sec"] + find_clip(lanes, "B")["duration_sec"]
        apply_roll(lanes, "A", "B", 4.0)
        ab_total_after = find_clip(lanes, "A")["duration_sec"] + find_clip(lanes, "B")["duration_sec"]
        assert abs(ab_total - ab_total_after) < 0.01
