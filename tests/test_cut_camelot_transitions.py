"""
MARKER_CAMELOT_TRANSITIONS — Tests for Camelot-aware transition durations.

Tests: suggest_transition on CamelotEngine, _apply_camelot_transitions in
PulseAutoMontage, MontageClip.transition_out serialization.
"""
from __future__ import annotations

import pytest

from src.services.pulse_camelot_engine import CamelotEngine, get_camelot_engine
from src.services.pulse_auto_montage import MontageClip, PulseAutoMontage


# ── CamelotEngine.suggest_transition ──


class TestSuggestTransition:
    """Verify distance → transition type/duration mapping."""

    def setup_method(self) -> None:
        self.engine = CamelotEngine()

    def test_same_key_short_dissolve(self) -> None:
        result = self.engine.suggest_transition("8A", "8A")
        assert result["distance"] == 0
        assert result["duration_sec"] == 0.5
        assert result["type"] == "cross_dissolve"
        assert result["quality"] == "perfect"

    def test_adjacent_key_short_dissolve(self) -> None:
        result = self.engine.suggest_transition("8A", "9A")
        assert result["distance"] == 1
        assert result["duration_sec"] == 0.5
        assert result["type"] == "cross_dissolve"
        assert result["quality"] == "harmonic"

    def test_parallel_key_short_dissolve(self) -> None:
        result = self.engine.suggest_transition("8A", "8B")
        assert result["distance"] == 1
        assert result["duration_sec"] == 0.5

    def test_distance_2_medium_dissolve(self) -> None:
        result = self.engine.suggest_transition("8A", "10A")
        assert result["distance"] == 2
        assert result["duration_sec"] == 1.0
        assert result["type"] == "cross_dissolve"
        assert result["quality"] == "acceptable"

    def test_distance_3_medium_dissolve(self) -> None:
        result = self.engine.suggest_transition("8A", "11A")
        assert result["distance"] == 3
        assert result["duration_sec"] == 1.0
        assert result["quality"] == "dramatic"

    def test_distance_4_long_dissolve(self) -> None:
        result = self.engine.suggest_transition("1A", "5A")
        assert result["distance"] == 4
        assert result["duration_sec"] == 2.0
        assert result["type"] == "cross_dissolve"

    def test_distance_5_long_dissolve(self) -> None:
        result = self.engine.suggest_transition("1A", "6A")
        assert result["distance"] == 5
        assert result["duration_sec"] == 2.0

    def test_distance_6_dip_to_black(self) -> None:
        # Max distance on wheel: 6 (opposite side)
        result = self.engine.suggest_transition("1A", "7A")
        assert result["distance"] == 6
        assert result["type"] == "dip_to_black"
        assert result["duration_sec"] == 2.0
        assert result["quality"] == "clash"

    def test_cross_ring_distance_6(self) -> None:
        # 1A to 6B = 5 steps + ring change = 6
        result = self.engine.suggest_transition("1A", "6B")
        assert result["distance"] == 6
        assert result["type"] == "dip_to_black"

    def test_returns_dict_keys(self) -> None:
        result = self.engine.suggest_transition("3B", "5A")
        assert set(result.keys()) == {"type", "duration_sec", "quality", "distance"}

    def test_singleton_engine(self) -> None:
        engine = get_camelot_engine()
        result = engine.suggest_transition("8A", "8B")
        assert result["distance"] == 1


# ── MontageClip with transition_out ──


class TestMontageClipTransition:
    def test_transition_out_default_none(self) -> None:
        clip = MontageClip(
            clip_id="c1", source_path="/a.mp4",
            in_sec=0, out_sec=5, timeline_start=0, timeline_end=5,
        )
        assert clip.transition_out is None

    def test_transition_out_serialized(self) -> None:
        clip = MontageClip(
            clip_id="c1", source_path="/a.mp4",
            in_sec=0, out_sec=5, timeline_start=0, timeline_end=5,
            transition_out={"type": "cross_dissolve", "duration_sec": 0.5,
                            "quality": "harmonic", "distance": 1},
        )
        d = clip.to_dict()
        assert d["transition_out"]["type"] == "cross_dissolve"
        assert d["transition_out"]["duration_sec"] == 0.5

    def test_transition_out_none_serialized(self) -> None:
        clip = MontageClip(
            clip_id="c1", source_path="/a.mp4",
            in_sec=0, out_sec=5, timeline_start=0, timeline_end=5,
        )
        d = clip.to_dict()
        assert d["transition_out"] is None


# ── _apply_camelot_transitions ──


class TestApplyCamelotTransitions:
    def setup_method(self) -> None:
        self.montage = PulseAutoMontage()

    def _make_clips(self, keys: list[str]) -> list[MontageClip]:
        return [
            MontageClip(
                clip_id=f"c{i}", source_path=f"/{i}.mp4",
                in_sec=0, out_sec=5, timeline_start=i * 5, timeline_end=(i + 1) * 5,
                camelot_key=k,
            )
            for i, k in enumerate(keys)
        ]

    def test_adjacent_keys_get_short_transition(self) -> None:
        clips = self._make_clips(["8A", "9A", "10A"])
        self.montage._apply_camelot_transitions(clips)
        # 8A→9A distance 1 → 0.5s
        assert clips[0].transition_out["duration_sec"] == 0.5
        # 9A→10A distance 1 → 0.5s
        assert clips[1].transition_out["duration_sec"] == 0.5
        # Last clip: no transition
        assert clips[2].transition_out is None

    def test_clash_keys_get_dip_to_black(self) -> None:
        clips = self._make_clips(["1A", "7A"])
        self.montage._apply_camelot_transitions(clips)
        assert clips[0].transition_out["type"] == "dip_to_black"
        assert clips[0].transition_out["distance"] == 6

    def test_empty_keys_no_transition(self) -> None:
        clips = self._make_clips(["8A", "", "10A"])
        self.montage._apply_camelot_transitions(clips)
        # 8A→"" → no transition (missing key)
        assert clips[0].transition_out is None
        # ""→10A → no transition
        assert clips[1].transition_out is None

    def test_single_clip_no_transition(self) -> None:
        clips = self._make_clips(["8A"])
        self.montage._apply_camelot_transitions(clips)
        assert clips[0].transition_out is None

    def test_empty_list_no_crash(self) -> None:
        self.montage._apply_camelot_transitions([])
