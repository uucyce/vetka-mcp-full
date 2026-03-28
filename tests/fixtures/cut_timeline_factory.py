"""
Timeline, lane, and clip factory functions for CUT backend tests.

Replaces 8+ independently defined _make_state/_make_timeline/_make_clip
functions across test files, all producing cut_timeline_state_v1 dicts.

Usage:
    from tests.fixtures.cut_timeline_factory import make_clip, make_lane, make_timeline_state

    clip = make_clip("c1", "/tmp/a.mov", start_sec=0, duration_sec=5)
    lane = make_lane("V1", "video_main", clips=[clip])
    state = make_timeline_state(lanes=[lane])
"""

import time
from typing import Any, Dict, List, Optional


def make_clip(
    clip_id: str = "clip_a",
    source_path: str = "/tmp/cut/shot-a.mov",
    start_sec: float = 0.0,
    duration_sec: float = 5.0,
    scene_id: Optional[str] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """
    Create a single clip dict matching cut_timeline_state_v1 schema.

    Args:
        clip_id: Unique identifier for the clip.
        source_path: Path to source media file.
        start_sec: Start position in seconds on the timeline.
        duration_sec: Clip duration in seconds.
        scene_id: Optional scene graph node reference.
        **extra: Additional fields merged into the clip dict
                 (e.g. effects, color_correction, speed).
    """
    clip = {
        "clip_id": clip_id,
        "source_path": source_path,
        "start_sec": start_sec,
        "duration_sec": duration_sec,
    }
    if scene_id is not None:
        clip["scene_id"] = scene_id
    clip.update(extra)
    return clip


def make_lane(
    lane_id: str = "V1",
    lane_type: str = "video_main",
    clips: Optional[List[Dict]] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """
    Create a single timeline lane dict.

    Args:
        lane_id: Lane identifier (V1, A1, etc.)
        lane_type: One of video_main, audio_main, video_overlay, audio_sub.
        clips: List of clip dicts. Defaults to empty.
        **extra: Additional fields (muted, solo, locked, volume, etc.)
    """
    lane = {
        "lane_id": lane_id,
        "lane_type": lane_type,
        "clips": clips or [],
    }
    lane.update(extra)
    return lane


def make_timeline_state(
    timeline_id: str = "main",
    lanes: Optional[List[Dict]] = None,
    fps: int = 25,
    selection: Optional[Dict] = None,
    project_id: str = "test-project",
    **extra: Any,
) -> Dict[str, Any]:
    """
    Create a full cut_timeline_state_v1 dict.

    This is the canonical timeline state used by CutProjectStore
    and returned by /api/cut/project-state endpoint.

    Args:
        timeline_id: Timeline identifier.
        lanes: List of lane dicts. Defaults to empty.
        fps: Frames per second (default 25 for PAL).
        selection: Selection state dict. Defaults to empty selection.
        project_id: Parent project identifier.
        **extra: Additional top-level fields.
    """
    state = {
        "schema_version": "cut_timeline_state_v1",
        "project_id": project_id,
        "timeline_id": timeline_id,
        "fps": fps,
        "selection": selection or {"clip_ids": [], "scene_ids": []},
        "lanes": lanes or [],
        "view": {
            "scroll_x": 0.0,
            "zoom": 1.0,
        },
        "updated_at": time.time(),
    }
    state.update(extra)
    return state


# ── Preset factories ──────────────────────────────────────────────────────

def empty_timeline(timeline_id: str = "main", **kw) -> Dict[str, Any]:
    """Empty timeline with no lanes — the most common test starting point."""
    return make_timeline_state(timeline_id=timeline_id, **kw)


def two_clip_timeline(**kw) -> Dict[str, Any]:
    """
    Standard two-clip, single-lane timeline.

    Used by 6+ E2E specs and contract tests as the baseline
    for editing, trimming, and playback tests.
    """
    clips = [
        make_clip("clip_a", "/tmp/cut/shot-a.mov", start_sec=1.0, duration_sec=4.0,
                  scene_id="scene_a"),
        make_clip("clip_b", "/tmp/cut/shot-b.mov", start_sec=6.0, duration_sec=3.5,
                  scene_id="scene_b"),
    ]
    lane = make_lane("video_main", "video_main", clips=clips)
    return make_timeline_state(lanes=[lane], **kw)


def multi_lane_timeline(**kw) -> Dict[str, Any]:
    """
    Multi-lane V+A timeline for editing, FCP7 compliance, and export tests.
    """
    v_clips = [
        make_clip("v1", "/tmp/cut/shot-a.mov", 0.0, 5.0, scene_id="s1"),
        make_clip("v2", "/tmp/cut/shot-b.mov", 5.0, 3.0, scene_id="s2"),
        make_clip("v3", "/tmp/cut/shot-c.mov", 8.0, 4.0, scene_id="s3"),
    ]
    a_clips = [
        make_clip("a1", "/tmp/cut/master.wav", 0.0, 8.0),
        make_clip("a2", "/tmp/cut/sfx.wav", 8.0, 4.0),
    ]
    lanes = [
        make_lane("V1", "video_main", v_clips),
        make_lane("A1", "audio_main", a_clips),
    ]
    return make_timeline_state(lanes=lanes, **kw)


def make_project_sandbox_config(
    project_id: str = "test-project",
    sandbox_root: str = "/tmp/cut-test",
    source_path: str = "/tmp/cut/source.mov",
) -> Dict[str, Any]:
    """
    Create a cut_project_v1 config dict for sandbox bootstrapping.

    Used by CutProjectStore tests that need .cut_config/cut_project.json.
    """
    return {
        "schema_version": "cut_project_v1",
        "project_id": project_id,
        "display_name": f"Test Project {project_id}",
        "source_path": source_path,
        "sandbox_root": sandbox_root,
        "state": "ready",
        "created_at": time.time(),
    }
