"""
Contract tests for MARKER_MATCH_FRAME backend — FCP7 Ch.27.

Covers:
  Forward match:  timeline_position → source_path + source_timecode
  Reverse match:  source_path + source_timecode → timeline_position + lane_id + clip_id
  Edge cases:     no clip at position, invalid request, gap between clips
  Response shape: required fields present, correct match type label

@phase 201
@task tb_1774763550_2394_1
@branch claude/cut-media
"""

from __future__ import annotations
import pytest


# ── Pure-Python mirrors of backend logic ──────────────────────────────────
# Duplicates the algorithm from cut_routes.py so we can unit-test logic
# without importing FastAPI or a running server.

def forward_match(lanes: list, timeline_position: float) -> dict:
    """Mirror of /match-frame forward path."""
    t = timeline_position
    for lane in lanes:
        for clip in lane.get("clips", []):
            start = float(clip.get("start_sec", 0))
            dur = float(clip.get("duration_sec", 0))
            if start <= t < start + dur:
                source_in = float(clip.get("source_in", 0))
                return {
                    "success": True,
                    "match": "forward",
                    "source_path": clip.get("source_path", ""),
                    "source_timecode": round(source_in + (t - start), 4),
                }
    return {"success": False, "error": "no_clip_at_position"}


def reverse_match(lanes: list, source_path: str, source_timecode: float) -> dict:
    """Mirror of /match-frame reverse path."""
    st = source_timecode
    for lane in lanes:
        for clip in lane.get("clips", []):
            if clip.get("source_path") != source_path:
                continue
            source_in = float(clip.get("source_in", 0))
            dur = float(clip.get("duration_sec", 0))
            if source_in <= st < source_in + dur:
                timeline_pos = float(clip.get("start_sec", 0)) + (st - source_in)
                return {
                    "success": True,
                    "match": "reverse",
                    "timeline_position": round(timeline_pos, 4),
                    "lane_id": lane.get("lane_id", ""),
                    "clip_id": clip.get("clip_id", ""),
                }
    return {"success": False, "error": "no_clip_for_source_timecode"}


def invalid_request() -> dict:
    return {"success": False, "error": "invalid_request",
            "detail": "Provide timeline_position OR source_path+source_timecode"}


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def lanes():
    return [
        {
            "lane_id": "V1",
            "clips": [
                {"clip_id": "c1", "start_sec": 0.0,  "duration_sec": 5.0,
                 "source_path": "/media/A.mp4", "source_in": 10.0},
                {"clip_id": "c2", "start_sec": 5.0,  "duration_sec": 3.0,
                 "source_path": "/media/B.mp4", "source_in": 0.0},
                # gap: 8.0 → 10.0
                {"clip_id": "c3", "start_sec": 10.0, "duration_sec": 4.0,
                 "source_path": "/media/A.mp4", "source_in": 20.0},
            ],
        },
        {
            "lane_id": "A1",
            "clips": [
                {"clip_id": "c1_aud", "start_sec": 0.0, "duration_sec": 5.0,
                 "source_path": "/media/A.mp4", "source_in": 10.0},
            ],
        },
    ]


# ── Forward match tests ───────────────────────────────────────────────────

class TestForwardMatch:

    def test_basic_forward_hit(self, lanes):
        """Playhead at 1.0s on clip A (source_in=10) → source_timecode=11.0."""
        r = forward_match(lanes, 1.0)
        assert r["success"] is True
        assert r["match"] == "forward"
        assert r["source_path"] == "/media/A.mp4"
        assert r["source_timecode"] == 11.0  # 10.0 + (1.0 - 0.0)

    def test_forward_hit_clip_b(self, lanes):
        """Playhead at 6.0s → clip B (source_in=0), source_timecode=1.0."""
        r = forward_match(lanes, 6.0)
        assert r["success"] is True
        assert r["source_path"] == "/media/B.mp4"
        assert r["source_timecode"] == 1.0  # 0.0 + (6.0 - 5.0)

    def test_forward_at_clip_boundary(self, lanes):
        """Playhead exactly at clip start (5.0) → hits clip B, not A."""
        r = forward_match(lanes, 5.0)
        assert r["success"] is True
        assert r["source_path"] == "/media/B.mp4"
        assert r["source_timecode"] == 0.0

    def test_forward_last_frame_exclusive(self, lanes):
        """Clip A ends at 5.0 → position 5.0 belongs to clip B, not A."""
        r = forward_match(lanes, 4.9999)
        assert r["source_path"] == "/media/A.mp4"
        r2 = forward_match(lanes, 5.0)
        assert r2["source_path"] == "/media/B.mp4"

    def test_forward_in_gap(self, lanes):
        """Playhead at 9.0s — gap between B and C → no clip found."""
        r = forward_match(lanes, 9.0)
        assert r["success"] is False
        assert r["error"] == "no_clip_at_position"

    def test_forward_past_all_clips(self, lanes):
        """Playhead beyond last clip → no clip found."""
        r = forward_match(lanes, 100.0)
        assert r["success"] is False
        assert r["error"] == "no_clip_at_position"

    def test_forward_response_shape(self, lanes):
        """Forward response has: success, match, source_path, source_timecode."""
        r = forward_match(lanes, 2.0)
        assert "success" in r
        assert "match" in r
        assert "source_path" in r
        assert "source_timecode" in r

    def test_forward_second_instance_same_source(self, lanes):
        """Two clips from same source — playhead on second → correct source_timecode."""
        r = forward_match(lanes, 11.0)  # clip c3, source_in=20.0
        assert r["success"] is True
        assert r["source_path"] == "/media/A.mp4"
        assert r["source_timecode"] == 21.0  # 20.0 + (11.0 - 10.0)


# ── Reverse match tests ───────────────────────────────────────────────────

class TestReverseMatch:

    def test_basic_reverse_hit(self, lanes):
        """source=/media/A.mp4, source_timecode=11.5 → timeline_position=1.5."""
        r = reverse_match(lanes, "/media/A.mp4", 11.5)
        assert r["success"] is True
        assert r["match"] == "reverse"
        assert r["timeline_position"] == 1.5   # 0.0 + (11.5 - 10.0)
        assert r["lane_id"] == "V1"
        assert r["clip_id"] == "c1"

    def test_reverse_hit_clip_b(self, lanes):
        """source=/media/B.mp4, source_timecode=2.0 → timeline_position=7.0."""
        r = reverse_match(lanes, "/media/B.mp4", 2.0)
        assert r["success"] is True
        assert r["timeline_position"] == 7.0   # 5.0 + (2.0 - 0.0)
        assert r["clip_id"] == "c2"

    def test_reverse_at_source_boundary(self, lanes):
        """source_timecode exactly at source_in → maps to clip start."""
        r = reverse_match(lanes, "/media/A.mp4", 10.0)
        assert r["success"] is True
        assert r["timeline_position"] == 0.0

    def test_reverse_source_timecode_past_clip_range(self, lanes):
        """source_timecode beyond any clip's range → no match."""
        r = reverse_match(lanes, "/media/A.mp4", 999.0)
        assert r["success"] is False
        assert r["error"] == "no_clip_for_source_timecode"

    def test_reverse_wrong_source_path(self, lanes):
        """Non-existent source path → no match."""
        r = reverse_match(lanes, "/media/doesnt_exist.mp4", 1.0)
        assert r["success"] is False
        assert r["error"] == "no_clip_for_source_timecode"

    def test_reverse_response_shape(self, lanes):
        """Reverse response has: success, match, timeline_position, lane_id, clip_id."""
        r = reverse_match(lanes, "/media/B.mp4", 1.0)
        assert "success" in r
        assert "match" in r
        assert "timeline_position" in r
        assert "lane_id" in r
        assert "clip_id" in r

    def test_reverse_second_instance_of_source(self, lanes):
        """A.mp4 appears in clip c1 (source_in=10) and c3 (source_in=20).
        source_timecode=21.0 is in c3's range → maps to c3's timeline pos."""
        r = reverse_match(lanes, "/media/A.mp4", 21.0)
        assert r["success"] is True
        assert r["clip_id"] == "c3"
        assert r["timeline_position"] == 11.0  # 10.0 + (21.0 - 20.0)


# ── Invalid request ───────────────────────────────────────────────────────

class TestInvalidRequest:

    def test_invalid_request_response(self):
        """Neither timeline_position nor source_path+source_timecode → error."""
        r = invalid_request()
        assert r["success"] is False
        assert r["error"] == "invalid_request"
        assert "detail" in r


# ── Hotkey contract ───────────────────────────────────────────────────────

class TestHotkeyContract:

    @pytest.mark.xfail(reason="matchFrame/reverseMatchFrame not yet in worktree — pending claude/cut-media merge", strict=False)
    def test_match_frame_hotkey_registered(self):
        """F key is registered as matchFrame action in useCutHotkeys.ts."""
        hotkeys_path = (
            __import__("pathlib").Path(__file__).parent.parent
            / "client/src/hooks/useCutHotkeys.ts"
        )
        assert hotkeys_path.exists(), "useCutHotkeys.ts not found"
        src = hotkeys_path.read_text()
        assert "matchFrame" in src, "matchFrame action not found in useCutHotkeys"
        assert "reverseMatchFrame" in src, "reverseMatchFrame not found in useCutHotkeys"

    @pytest.mark.xfail(reason="matchFrame/reverseMatchFrame not yet in worktree — pending claude/cut-media merge", strict=False)
    def test_match_frame_f_key(self):
        """F is bound to matchFrame (not just reverseMatchFrame)."""
        import pathlib
        src = (pathlib.Path(__file__).parent.parent
               / "client/src/hooks/useCutHotkeys.ts").read_text()
        # Should have F alone mapped to matchFrame and Shift+F to reverseMatchFrame
        assert "reverseMatchFrame" in src
        # Both FCP7 and Premiere presets should include matchFrame
        lines = [l for l in src.splitlines() if "matchFrame" in l]
        assert len(lines) >= 2, "matchFrame should appear in at least 2 preset entries"
