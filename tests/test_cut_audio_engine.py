"""
MARKER_B13 — Tests for cut_audio_engine (mixer → render pipeline).

Tests: mute, solo, volume, pan, mixer application to render plan.
"""
from __future__ import annotations

import math

import pytest

from src.services.cut_audio_engine import (
    LaneMixerState,
    MixerState,
    apply_mixer_to_plan,
    build_lane_audio_filters,
    compile_pan_filter,
    _volume_to_db,
)
from src.services.cut_render_engine import RenderClip, RenderPlan


def _plan_with_lanes(*lane_ids: str) -> RenderPlan:
    """Create a plan with one clip per lane."""
    clips = [
        RenderClip(source_path=f"/tmp/{lid}.mp4", duration_sec=10.0, lane_id=lid)
        for lid in lane_ids
    ]
    return RenderPlan(clips=clips, width=1920, height=1080, fps=25)


# ── Volume → dB ──


class TestVolumeToDb:
    def test_unity_is_zero_db(self) -> None:
        assert _volume_to_db(1.0) == pytest.approx(0.0, abs=0.01)

    def test_half_is_minus_6db(self) -> None:
        assert _volume_to_db(0.5) == pytest.approx(-6.02, abs=0.1)

    def test_double_is_plus_6db(self) -> None:
        assert _volume_to_db(2.0) == pytest.approx(6.02, abs=0.1)

    def test_zero_is_silence(self) -> None:
        assert _volume_to_db(0.0) == -96.0

    def test_1_5x_is_positive(self) -> None:
        assert _volume_to_db(1.5) > 0


# ── Pan filter ──


class TestPanFilter:
    def test_center_no_filter(self) -> None:
        assert compile_pan_filter(0.0) == ""

    def test_left(self) -> None:
        f = compile_pan_filter(-1.0)
        assert "stereotools" in f
        assert "balance_out=-1.000" in f

    def test_right(self) -> None:
        f = compile_pan_filter(0.5)
        assert "balance_out=0.500" in f


# ── Mute ──


class TestMute:
    def test_muted_lane_gets_silence(self) -> None:
        state = LaneMixerState(lane_id="a1", mute=True)
        effects = build_lane_audio_filters(state)
        assert len(effects) == 1
        assert effects[0]["params"]["db"] == -96.0

    def test_unmuted_lane_no_silence(self) -> None:
        state = LaneMixerState(lane_id="a1", mute=False, volume=1.0)
        effects = build_lane_audio_filters(state)
        # Volume=1.0 → no effect needed
        assert len(effects) == 0


# ── Solo ──


class TestSolo:
    def test_non_soloed_muted_when_any_solo(self) -> None:
        state = LaneMixerState(lane_id="a1", solo=False)
        effects = build_lane_audio_filters(state, any_solo=True)
        assert len(effects) == 1
        assert effects[0]["params"]["db"] == -96.0

    def test_soloed_lane_plays(self) -> None:
        state = LaneMixerState(lane_id="a1", solo=True, volume=1.0)
        effects = build_lane_audio_filters(state, any_solo=True)
        assert len(effects) == 0  # volume=1.0, no effect needed

    def test_mute_overrides_solo(self) -> None:
        state = LaneMixerState(lane_id="a1", solo=True, mute=True)
        effects = build_lane_audio_filters(state, any_solo=True)
        assert len(effects) == 1
        assert effects[0]["params"]["db"] == -96.0


# ── Volume ──


class TestVolume:
    def test_half_volume(self) -> None:
        state = LaneMixerState(lane_id="a1", volume=0.5)
        effects = build_lane_audio_filters(state)
        assert len(effects) == 1
        assert effects[0]["type"] == "volume"
        assert effects[0]["params"]["db"] < 0

    def test_150_percent_volume(self) -> None:
        state = LaneMixerState(lane_id="a1", volume=1.5)
        effects = build_lane_audio_filters(state)
        assert len(effects) == 1
        assert effects[0]["params"]["db"] > 0

    def test_master_volume_applied(self) -> None:
        state = LaneMixerState(lane_id="a1", volume=1.0)
        effects = build_lane_audio_filters(state, master_volume=0.5)
        assert len(effects) == 1
        assert effects[0]["params"]["db"] < 0


# ── Pan ──


class TestPan:
    def test_pan_left(self) -> None:
        state = LaneMixerState(lane_id="a1", pan=-0.7)
        effects = build_lane_audio_filters(state)
        pan_effects = [e for e in effects if e["type"] == "_pan"]
        assert len(pan_effects) == 1
        assert pan_effects[0]["params"]["pan"] == -0.7

    def test_center_no_pan_effect(self) -> None:
        state = LaneMixerState(lane_id="a1", pan=0.0)
        effects = build_lane_audio_filters(state)
        pan_effects = [e for e in effects if e["type"] == "_pan"]
        assert len(pan_effects) == 0


# ── MixerState.from_dict ──


class TestMixerStateFromDict:
    def test_parse(self) -> None:
        d = {
            "lanes": {
                "a1": {"volume": 0.8, "pan": -0.5, "mute": False, "solo": True},
                "a2": {"volume": 1.0, "mute": True},
            },
            "master_volume": 0.9,
        }
        ms = MixerState.from_dict(d)
        assert len(ms.lanes) == 2
        assert ms.lanes["a1"].volume == 0.8
        assert ms.lanes["a1"].pan == -0.5
        assert ms.lanes["a1"].solo is True
        assert ms.lanes["a2"].mute is True
        assert ms.master_volume == 0.9

    def test_empty(self) -> None:
        ms = MixerState.from_dict({})
        assert len(ms.lanes) == 0
        assert ms.master_volume == 1.0


# ── apply_mixer_to_plan ──


class TestApplyMixerToPlan:
    def test_mute_lane(self) -> None:
        plan = _plan_with_lanes("v1", "a1", "a2")
        mixer = MixerState(lanes={
            "a1": LaneMixerState(lane_id="a1", mute=True),
        })
        apply_mixer_to_plan(plan, mixer)
        # a1 clip should have mute effect
        a1_clip = [c for c in plan.clips if c.lane_id == "a1"][0]
        assert any(e.get("params", {}).get("db") == -96.0 for e in a1_clip.audio_effects)

    def test_solo_silences_others(self) -> None:
        plan = _plan_with_lanes("a1", "a2")
        mixer = MixerState(lanes={
            "a1": LaneMixerState(lane_id="a1", solo=True),
            "a2": LaneMixerState(lane_id="a2"),
        })
        apply_mixer_to_plan(plan, mixer)
        # a2 should be silenced
        a2_clip = [c for c in plan.clips if c.lane_id == "a2"][0]
        assert any(e.get("params", {}).get("db") == -96.0 for e in a2_clip.audio_effects)
        # a1 should NOT be silenced
        a1_clip = [c for c in plan.clips if c.lane_id == "a1"][0]
        assert not any(e.get("params", {}).get("db") == -96.0 for e in a1_clip.audio_effects)

    def test_no_mixer_no_changes(self) -> None:
        plan = _plan_with_lanes("a1")
        mixer = MixerState()
        apply_mixer_to_plan(plan, mixer)
        assert plan.clips[0].audio_effects == []

    def test_volume_and_pan_combined(self) -> None:
        plan = _plan_with_lanes("a1")
        mixer = MixerState(lanes={
            "a1": LaneMixerState(lane_id="a1", volume=0.5, pan=0.7),
        })
        apply_mixer_to_plan(plan, mixer)
        effects = plan.clips[0].audio_effects
        assert len(effects) == 2  # volume + pan
        types = {e["type"] for e in effects}
        assert "volume" in types
        assert "_pan" in types
