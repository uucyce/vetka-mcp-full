"""
MARKER_W6.STORE: Unit tests for store migration Phase 1.

Tests the data flow logic: singleton → instance store reads,
onProjectStateRefresh → re-snapshot, effective value resolution.
"""
import pytest
from copy import deepcopy


# ── Simulated TimelineInstance ──────────────────────────────

def make_instance(id, lanes=None, zoom=80, scroll_x=0, playhead=0.0, duration=0.0):
    return {
        "id": id,
        "label": f"Cut {id}",
        "lanes": lanes or [],
        "waveforms": [],
        "thumbnails": [],
        "duration": duration,
        "zoom": zoom,
        "scrollX": scroll_x,
        "trackHeight": 60,
        "playheadPosition": playhead,
        "isPlaying": False,
        "markIn": None,
        "markOut": None,
        "selectedClipIds": [],
        "hoveredClipId": None,
        "mutedLanes": {},
        "soloLanes": {},
        "lockedLanes": {},
        "targetedLanes": {},
        "lastFocusedAt": 0,
    }


def make_lane(lane_id, clips=None):
    return {"lane_id": lane_id, "lane_type": "video_main", "clips": clips or []}


def make_clip(clip_id, start_sec, duration_sec):
    return {"clip_id": clip_id, "start_sec": start_sec, "duration_sec": duration_sec, "source_path": f"/m/{clip_id}.mp4"}


# ── Simulated effective value resolution ────────────────────

def resolve_effective(singleton_value, instance_value, is_multi_instance, inst_exists):
    """Mirror of: isMultiInstance && inst ? inst.X : singleton.X"""
    if is_multi_instance and inst_exists:
        return instance_value
    return singleton_value


# ── Simulated onProjectStateRefresh ─────────────────────────

def on_project_state_refresh(timelines, active_id, data):
    """Update active instance with fresh backend data."""
    if active_id not in timelines:
        return timelines
    tl = timelines[active_id]
    timelines[active_id] = {
        **tl,
        "lanes": data["lanes"],
        "waveforms": data.get("waveforms", []),
        "thumbnails": data.get("thumbnails", []),
        "duration": data.get("duration", 0),
    }
    return timelines


# ── Tests ────────────────────────────────────────────────────


class TestEffectiveValueResolution:
    """When instance exists, reads come from it; otherwise singleton."""

    def test_singleton_fallback(self):
        """No instance → use singleton value."""
        assert resolve_effective("singleton", "instance", False, False) == "singleton"

    def test_instance_override(self):
        """Instance exists → use instance value."""
        assert resolve_effective("singleton", "instance", True, True) == "instance"

    def test_multi_instance_no_inst(self):
        """Multi-instance mode but no instance data → fallback."""
        assert resolve_effective("singleton", "instance", True, False) == "singleton"

    def test_lanes_override(self):
        """Instance lanes override singleton lanes."""
        singleton_lanes = [make_lane("V1", [make_clip("A", 0, 5)])]
        instance_lanes = [make_lane("V1", [make_clip("B", 0, 3)])]
        effective = resolve_effective(singleton_lanes, instance_lanes, True, True)
        assert effective[0]["clips"][0]["clip_id"] == "B"

    def test_zoom_override(self):
        """Instance zoom overrides singleton zoom."""
        assert resolve_effective(60, 120, True, True) == 120

    def test_playhead_override(self):
        """Instance playhead overrides singleton currentTime."""
        assert resolve_effective(5.0, 10.0, True, True) == 10.0


class TestOnProjectStateRefresh:
    """Backend data flows into active instance."""

    def test_refresh_updates_active(self):
        """Refresh updates lanes/waveforms/duration of active timeline."""
        timelines = {
            "tl1": make_instance("tl1", lanes=[], duration=0),
            "tl2": make_instance("tl2", lanes=[], duration=0),
        }
        new_lanes = [make_lane("V1", [make_clip("X", 0, 10)])]
        on_project_state_refresh(timelines, "tl1", {
            "lanes": new_lanes,
            "waveforms": [{"id": "w1"}],
            "duration": 10.0,
        })
        assert len(timelines["tl1"]["lanes"]) == 1
        assert timelines["tl1"]["lanes"][0]["clips"][0]["clip_id"] == "X"
        assert timelines["tl1"]["duration"] == 10.0
        # tl2 untouched
        assert len(timelines["tl2"]["lanes"]) == 0

    def test_refresh_no_active(self):
        """Refresh with unknown active ID is a no-op."""
        timelines = {"tl1": make_instance("tl1")}
        original = deepcopy(timelines)
        result = on_project_state_refresh(timelines, "unknown", {
            "lanes": [make_lane("V1")], "duration": 5.0,
        })
        assert result["tl1"] == original["tl1"]

    def test_refresh_preserves_view_state(self):
        """Refresh updates data but NOT view state (zoom, scroll, playhead)."""
        timelines = {
            "tl1": make_instance("tl1", zoom=150, scroll_x=200, playhead=7.5),
        }
        on_project_state_refresh(timelines, "tl1", {
            "lanes": [make_lane("V1", [make_clip("A", 0, 5)])],
            "duration": 5.0,
        })
        assert timelines["tl1"]["zoom"] == 150
        assert timelines["tl1"]["scrollX"] == 200
        assert timelines["tl1"]["playheadPosition"] == 7.5


class TestMultiInstanceDataIsolation:
    """Different instances show different data."""

    def test_two_instances_different_lanes(self):
        """Two timelines with different content, effective reads differ."""
        inst1_lanes = [make_lane("V1", [make_clip("A", 0, 5)])]
        inst2_lanes = [make_lane("V1", [make_clip("B", 0, 3)])]

        # Viewing inst1
        eff1 = resolve_effective([], inst1_lanes, True, True)
        assert eff1[0]["clips"][0]["clip_id"] == "A"

        # Viewing inst2
        eff2 = resolve_effective([], inst2_lanes, True, True)
        assert eff2[0]["clips"][0]["clip_id"] == "B"

    def test_active_vs_inactive_zoom(self):
        """Active instance uses its own zoom, inactive does too."""
        inst_active = make_instance("active", zoom=200)
        inst_inactive = make_instance("inactive", zoom=50)

        assert resolve_effective(60, inst_active["zoom"], True, True) == 200
        assert resolve_effective(60, inst_inactive["zoom"], True, True) == 50
