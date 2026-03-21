"""
MARKER_W5.MF: Unit tests for Match Frame logic (FCP7 Ch.50).

Match Frame: find clip at playhead → calculate source-relative time.
"""
import pytest


def match_frame(lanes, current_time, locked_lanes=None):
    """
    Find clip under playhead, return (source_path, source_time) or None.
    Mirrors the matchFrame handler in CutEditorLayoutV2.
    """
    locked = locked_lanes or set()
    for lane in lanes:
        if lane["lane_id"] in locked:
            continue
        for clip in lane["clips"]:
            clip_end = clip["start_sec"] + clip["duration_sec"]
            if current_time >= clip["start_sec"] and current_time < clip_end:
                source_offset = clip.get("source_in", 0)
                source_time = (current_time - clip["start_sec"]) + source_offset
                return {
                    "source_path": clip["source_path"],
                    "source_time": round(source_time, 4),
                }
    return None


def toggle_source_program(current_focus):
    """Toggle between source and program focus."""
    return "program" if current_focus == "source" else "source"


# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture
def timeline():
    return [
        {
            "lane_id": "video_main",
            "clips": [
                {"clip_id": "A", "start_sec": 0.0, "duration_sec": 5.0,
                 "source_path": "/media/clip_A.mp4", "source_in": 0.0},
                {"clip_id": "B", "start_sec": 5.0, "duration_sec": 3.0,
                 "source_path": "/media/clip_B.mp4", "source_in": 2.0},
                {"clip_id": "C", "start_sec": 8.0, "duration_sec": 4.0,
                 "source_path": "/media/clip_C.mp4"},
            ]
        },
        {
            "lane_id": "audio_sync",
            "clips": [
                {"clip_id": "A_aud", "start_sec": 0.0, "duration_sec": 5.0,
                 "source_path": "/media/clip_A.mp4", "source_in": 0.0},
            ]
        },
    ]


# ── Tests ─────────────────────────────────────────────────────


class TestMatchFrame:
    def test_match_at_start(self, timeline):
        """Playhead at 0 → clip A, source_time = 0."""
        r = match_frame(timeline, 0.0)
        assert r is not None
        assert r["source_path"] == "/media/clip_A.mp4"
        assert r["source_time"] == 0.0

    def test_match_middle_of_clip(self, timeline):
        """Playhead at 2.5s → clip A, source_time = 2.5."""
        r = match_frame(timeline, 2.5)
        assert r is not None
        assert r["source_path"] == "/media/clip_A.mp4"
        assert r["source_time"] == 2.5

    def test_match_with_source_offset(self, timeline):
        """Playhead at 6.0s → clip B (source_in=2.0), source_time = 1.0 + 2.0 = 3.0."""
        r = match_frame(timeline, 6.0)
        assert r is not None
        assert r["source_path"] == "/media/clip_B.mp4"
        assert r["source_time"] == 3.0  # (6.0 - 5.0) + 2.0

    def test_match_no_source_in(self, timeline):
        """Playhead at 9.0s → clip C (no source_in), source_time = 1.0."""
        r = match_frame(timeline, 9.0)
        assert r is not None
        assert r["source_path"] == "/media/clip_C.mp4"
        assert r["source_time"] == 1.0  # 9.0 - 8.0

    def test_match_at_gap(self, timeline):
        """Playhead at 13.0s (past all clips) → None."""
        r = match_frame(timeline, 13.0)
        assert r is None

    def test_match_at_boundary(self, timeline):
        """Playhead exactly at clip B start (5.0s) → clip B."""
        r = match_frame(timeline, 5.0)
        assert r is not None
        assert r["source_path"] == "/media/clip_B.mp4"
        assert r["source_time"] == 2.0  # source_in offset

    def test_match_skips_locked_lanes(self, timeline):
        """Locked video lane → falls through to audio lane."""
        r = match_frame(timeline, 2.0, locked_lanes={"video_main"})
        assert r is not None
        assert r["source_path"] == "/media/clip_A.mp4"
        assert r["source_time"] == 2.0

    def test_match_all_locked(self, timeline):
        """All lanes locked → None."""
        r = match_frame(timeline, 2.0, locked_lanes={"video_main", "audio_sync"})
        assert r is None


class TestToggleSourceProgram:
    def test_source_to_program(self):
        assert toggle_source_program("source") == "program"

    def test_program_to_source(self):
        assert toggle_source_program("program") == "source"

    def test_timeline_to_source(self):
        """Non source/program focus → defaults to source."""
        assert toggle_source_program("timeline") == "source"

    def test_none_to_source(self):
        assert toggle_source_program(None) == "source"
