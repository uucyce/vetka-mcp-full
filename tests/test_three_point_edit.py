"""
MARKER_W5.3PT: Unit tests for Three-Point Editing resolution logic.

FCP7 Ch.36: Set 3 of 4 edit points, system calculates 4th.
Tests mirror resolveThreePointEdit() from useThreePointEdit.ts.
"""
import pytest


# ── Python mirror of resolveThreePointEdit ──────────────────

def resolve_three_point_edit(
    source_mark_in=None, source_mark_out=None,
    sequence_mark_in=None, sequence_mark_out=None,
    current_time=0.0, source_duration=0.0,
    source_media_path=None, video_lane_id="V1", audio_lane_id="A1",
):
    """Resolve 4 edit points from up to 3 user-set points."""
    if not source_media_path:
        return None

    src_in = source_mark_in if source_mark_in is not None else 0
    src_out = source_mark_out

    seq_in = sequence_mark_in if sequence_mark_in is not None else current_time
    seq_out = sequence_mark_out

    has_src_in = source_mark_in is not None
    has_src_out = source_mark_out is not None
    has_seq_in = sequence_mark_in is not None
    has_seq_out = sequence_mark_out is not None

    # Rule: Sequence IN/OUT takes precedence for duration
    if has_seq_in and has_seq_out and seq_out is not None:
        seq_duration = seq_out - seq_in
        if seq_duration <= 0:
            return None
        if not has_src_out:
            src_out = src_in + seq_duration
        return {
            "source_in": src_in,
            "source_out": src_out if src_out is not None else src_in + seq_duration,
            "sequence_in": seq_in,
            "duration": seq_duration,
            "source_path": source_media_path,
            "video_lane_id": video_lane_id,
            "audio_lane_id": audio_lane_id,
        }

    # Source IN + OUT define duration
    if has_src_in and has_src_out and src_out is not None:
        src_duration = src_out - src_in
        if src_duration <= 0:
            return None
        if has_seq_out and seq_out is not None:
            # Backtracking
            seq_in = max(0, seq_out - src_duration)
        return {
            "source_in": src_in,
            "source_out": src_out,
            "sequence_in": seq_in,
            "duration": src_duration,
            "source_path": source_media_path,
            "video_lane_id": video_lane_id,
            "audio_lane_id": audio_lane_id,
        }

    # Only source IN
    if has_src_in and not has_src_out:
        dur = source_duration - src_in if source_duration > 0 else 5.0
        return {
            "source_in": src_in,
            "source_out": src_in + dur,
            "sequence_in": seq_in,
            "duration": dur,
            "source_path": source_media_path,
            "video_lane_id": video_lane_id,
            "audio_lane_id": audio_lane_id,
        }

    # No source marks
    if not has_src_in and not has_src_out:
        dur = source_duration if source_duration > 0 else 5.0
        return {
            "source_in": 0,
            "source_out": dur,
            "sequence_in": seq_in,
            "duration": dur,
            "source_path": source_media_path,
            "video_lane_id": video_lane_id,
            "audio_lane_id": audio_lane_id,
        }

    # Only source OUT
    if not has_src_in and has_src_out and src_out is not None:
        return {
            "source_in": 0,
            "source_out": src_out,
            "sequence_in": seq_in,
            "duration": src_out,
            "source_path": source_media_path,
            "video_lane_id": video_lane_id,
            "audio_lane_id": audio_lane_id,
        }

    return None


# ── Tests ────────────────────────────────────────────────────


class TestThreePointBasic:
    """Standard three-point scenarios from FCP7 Ch.36."""

    def test_src_in_out_seq_in(self):
        """Classic: source IN+OUT + sequence IN → auto-calculate seq OUT."""
        r = resolve_three_point_edit(
            source_mark_in=2.0, source_mark_out=5.0,
            sequence_mark_in=10.0,
            source_media_path="/clip.mp4",
        )
        assert r is not None
        assert r["source_in"] == 2.0
        assert r["source_out"] == 5.0
        assert r["sequence_in"] == 10.0
        assert abs(r["duration"] - 3.0) < 0.001

    def test_src_in_seq_in_out(self):
        """Source IN + sequence IN+OUT → auto-calculate source OUT."""
        r = resolve_three_point_edit(
            source_mark_in=1.0,
            sequence_mark_in=5.0, sequence_mark_out=8.0,
            source_media_path="/clip.mp4",
        )
        assert r is not None
        assert r["source_in"] == 1.0
        assert r["source_out"] == 4.0  # 1.0 + 3.0
        assert r["sequence_in"] == 5.0
        assert abs(r["duration"] - 3.0) < 0.001

    def test_src_in_out_seq_out_backtrack(self):
        """Backtracking: src IN+OUT + seq OUT → calculate seq IN."""
        r = resolve_three_point_edit(
            source_mark_in=0.0, source_mark_out=4.0,
            sequence_mark_out=20.0,
            source_media_path="/clip.mp4",
            current_time=15.0,
        )
        assert r is not None
        assert r["sequence_in"] == 16.0  # 20.0 - 4.0
        assert abs(r["duration"] - 4.0) < 0.001


class TestThreePointEdgeCases:
    """Edge cases and implicit point resolution."""

    def test_no_source_media(self):
        """No source → returns None."""
        r = resolve_three_point_edit(
            source_mark_in=0, source_mark_out=5,
            source_media_path=None,
        )
        assert r is None

    def test_no_marks_at_all(self):
        """No marks → uses entire source, playhead as seq IN."""
        r = resolve_three_point_edit(
            current_time=7.0, source_duration=10.0,
            source_media_path="/clip.mp4",
        )
        assert r is not None
        assert r["source_in"] == 0
        assert r["source_out"] == 10.0
        assert r["sequence_in"] == 7.0
        assert abs(r["duration"] - 10.0) < 0.001

    def test_only_source_in(self):
        """Only source IN → rest of source from that point."""
        r = resolve_three_point_edit(
            source_mark_in=3.0,
            current_time=0.0, source_duration=10.0,
            source_media_path="/clip.mp4",
        )
        assert r is not None
        assert r["source_in"] == 3.0
        assert abs(r["duration"] - 7.0) < 0.001

    def test_missing_seq_in_uses_playhead(self):
        """No sequence IN → uses current playhead position."""
        r = resolve_three_point_edit(
            source_mark_in=0.0, source_mark_out=2.0,
            current_time=5.0,
            source_media_path="/clip.mp4",
        )
        assert r is not None
        assert r["sequence_in"] == 5.0

    def test_seq_in_out_precedence(self):
        """Sequence IN/OUT takes precedence — overrides source duration."""
        r = resolve_three_point_edit(
            source_mark_in=0.0, source_mark_out=10.0,
            sequence_mark_in=5.0, sequence_mark_out=8.0,
            source_media_path="/clip.mp4",
        )
        assert r is not None
        # Duration from sequence (3s), not source (10s)
        assert abs(r["duration"] - 3.0) < 0.001

    def test_zero_duration_returns_none(self):
        """Source IN == OUT → invalid, returns None."""
        r = resolve_three_point_edit(
            source_mark_in=5.0, source_mark_out=5.0,
            source_media_path="/clip.mp4",
        )
        assert r is None

    def test_negative_duration_returns_none(self):
        """Source OUT < IN → invalid."""
        r = resolve_three_point_edit(
            source_mark_in=5.0, source_mark_out=3.0,
            source_media_path="/clip.mp4",
        )
        assert r is None

    def test_backtrack_clamps_to_zero(self):
        """Backtracking that would result in negative seq IN clamps to 0."""
        r = resolve_three_point_edit(
            source_mark_in=0.0, source_mark_out=10.0,
            sequence_mark_out=5.0,
            source_media_path="/clip.mp4",
        )
        assert r is not None
        assert r["sequence_in"] == 0  # max(0, 5.0 - 10.0)


class TestThreePointAllFourSet:
    """When all 4 points are set, sequence takes precedence."""

    def test_all_four_sequence_wins(self):
        """All 4 set → sequence duration wins."""
        r = resolve_three_point_edit(
            source_mark_in=0.0, source_mark_out=10.0,
            sequence_mark_in=5.0, sequence_mark_out=7.0,
            source_media_path="/clip.mp4",
        )
        assert r is not None
        assert abs(r["duration"] - 2.0) < 0.001  # seq: 7-5=2
        assert r["sequence_in"] == 5.0
