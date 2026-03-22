"""
MARKER_B14 — Tests for audio transitions (crossfade curves).

Tests: equal_power (+3dB) vs linear (0dB) curves, Transition dataclass,
filter graph generation, EFFECT_DEF.
"""
from __future__ import annotations

import pytest

from src.services.cut_effects_engine import EFFECT_DEFS
from src.services.cut_render_engine import (
    FilterGraphBuilder,
    RenderClip,
    RenderPlan,
    Transition,
)


def _plan_with_transition(audio_curve: str = "equal_power", duration: float = 1.0) -> RenderPlan:
    """Create a plan with 2 clips and one transition."""
    clips = [
        RenderClip(source_path="/tmp/a.mp4", duration_sec=5.0, start_sec=0),
        RenderClip(source_path="/tmp/b.mp4", duration_sec=5.0, start_sec=4.0),
    ]
    transition = Transition(
        type="crossfade",
        duration_sec=duration,
        between=(0, 1),
        audio_curve=audio_curve,
    )
    return RenderPlan(clips=clips, transitions=[transition], width=1920, height=1080, fps=25)


# ── Transition dataclass ──


class TestTransitionDataclass:
    def test_default_audio_curve(self) -> None:
        t = Transition()
        assert t.audio_curve == "equal_power"

    def test_linear_curve(self) -> None:
        t = Transition(audio_curve="linear")
        assert t.audio_curve == "linear"

    def test_equal_power_curve(self) -> None:
        t = Transition(audio_curve="equal_power")
        assert t.audio_curve == "equal_power"


# ── Equal power (+3dB) crossfade ──


class TestEqualPowerCrossfade:
    def test_uses_qsin_curve(self) -> None:
        plan = _plan_with_transition(audio_curve="equal_power")
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "c1=qsin" in fg
        assert "c2=qsin" in fg

    def test_acrossfade_present(self) -> None:
        plan = _plan_with_transition()
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "acrossfade" in fg


# ── Linear (0dB) crossfade ──


class TestLinearCrossfade:
    def test_uses_tri_curve(self) -> None:
        plan = _plan_with_transition(audio_curve="linear")
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "c1=tri" in fg
        assert "c2=tri" in fg


# ── Duration in filter ──


class TestCrossfadeDuration:
    def test_duration_in_filter(self) -> None:
        plan = _plan_with_transition(duration=0.5)
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "d=0.500" in fg

    def test_long_duration(self) -> None:
        plan = _plan_with_transition(duration=3.0)
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "d=3.000" in fg


# ── No transition = concat ──


class TestNoTransition:
    def test_no_transition_uses_concat(self) -> None:
        clips = [
            RenderClip(source_path="/tmp/a.mp4", duration_sec=5.0, start_sec=0),
            RenderClip(source_path="/tmp/b.mp4", duration_sec=5.0, start_sec=5.0),
        ]
        plan = RenderPlan(clips=clips, transitions=[], width=1920, height=1080, fps=25)
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "concat" in fg
        assert "acrossfade" not in fg


# ── EFFECT_DEF ──


class TestAudioCrossfadeEffectDef:
    def test_exists(self) -> None:
        assert "audio_crossfade" in EFFECT_DEFS
        d = EFFECT_DEFS["audio_crossfade"]
        assert d.category == "audio"
        assert d.ffmpeg_audio is True
        assert d.ffmpeg_video is False

    def test_params(self) -> None:
        d = EFFECT_DEFS["audio_crossfade"]
        assert "duration" in d.params_schema
        assert "curve" in d.params_schema
        assert d.params_schema["curve"]["default"] == "equal_power"

    def test_curve_options(self) -> None:
        d = EFFECT_DEFS["audio_crossfade"]
        options = d.params_schema["curve"]["options"]
        assert "equal_power" in options
        assert "linear" in options
