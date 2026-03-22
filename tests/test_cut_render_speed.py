"""
MARKER_B11 — Tests for speed control in render engine.

Tests: reverse playback, frame blending, maintain_pitch, speed detection.
"""
from __future__ import annotations

import pytest

from src.services.cut_render_engine import (
    FilterGraphBuilder,
    RenderClip,
    RenderPlan,
    build_ffmpeg_command,
    _build_atempo_chain,
)


def _plan_with_clip(**clip_kwargs) -> RenderPlan:
    """Helper: create a plan with a single clip."""
    clip = RenderClip(source_path="/tmp/test.mp4", duration_sec=10.0, **clip_kwargs)
    return RenderPlan(clips=[clip], width=1920, height=1080, fps=25)


# ── Speed via setpts ──


class TestSpeedFilters:
    def test_normal_speed_no_setpts(self) -> None:
        plan = _plan_with_clip(speed=1.0)
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "setpts=1.0000" not in fg  # no speed filter for 1.0x

    def test_2x_speed(self) -> None:
        plan = _plan_with_clip(speed=2.0)
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "setpts=0.5000*PTS" in fg

    def test_half_speed(self) -> None:
        plan = _plan_with_clip(speed=0.5)
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "setpts=2.0000*PTS" in fg

    def test_quarter_speed(self) -> None:
        plan = _plan_with_clip(speed=0.25)
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "setpts=4.0000*PTS" in fg


# ── Reverse playback ──


class TestReverse:
    def test_reverse_video_filter(self) -> None:
        plan = _plan_with_clip(reverse=True)
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "reverse" in fg
        assert "areverse" in fg

    def test_reverse_with_speed(self) -> None:
        plan = _plan_with_clip(speed=2.0, reverse=True)
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        # Speed applied first, then reverse
        assert "setpts=0.5000*PTS" in fg
        assert "reverse" in fg

    def test_no_reverse_by_default(self) -> None:
        plan = _plan_with_clip()
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "reverse" not in fg
        assert "areverse" not in fg


# ── Frame blending (minterpolate) ──


class TestFrameBlend:
    def test_frame_blend_slow_motion(self) -> None:
        plan = _plan_with_clip(speed=0.5, frame_blend=True)
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "minterpolate" in fg
        assert "fps=25" in fg

    def test_frame_blend_ignored_at_normal_speed(self) -> None:
        plan = _plan_with_clip(speed=1.0, frame_blend=True)
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "minterpolate" not in fg

    def test_frame_blend_ignored_at_fast_speed(self) -> None:
        plan = _plan_with_clip(speed=2.0, frame_blend=True)
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "minterpolate" not in fg

    def test_no_frame_blend_by_default(self) -> None:
        plan = _plan_with_clip(speed=0.5, frame_blend=False)
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "minterpolate" not in fg


# ── Maintain pitch ──


class TestMaintainPitch:
    def test_maintain_pitch_uses_atempo(self) -> None:
        plan = _plan_with_clip(speed=2.0, maintain_pitch=True)
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "atempo=" in fg
        assert "asetrate" not in fg

    def test_no_maintain_pitch_uses_asetrate(self) -> None:
        plan = _plan_with_clip(speed=2.0, maintain_pitch=False)
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "asetrate" in fg
        assert "aresample" in fg

    def test_default_maintains_pitch(self) -> None:
        clip = RenderClip(source_path="/tmp/test.mp4", duration_sec=10.0, speed=2.0)
        assert clip.maintain_pitch is True


# ── atempo chaining ──


class TestAtempoChain:
    def test_normal_range(self) -> None:
        chain = _build_atempo_chain(2.0)
        assert chain == ["atempo=2.0000"]

    def test_slow_chains(self) -> None:
        chain = _build_atempo_chain(0.25)
        # 0.25 < 0.5: append atempo=0.5, remaining = 0.25/0.5 = 0.5 (exits loop)
        assert chain == ["atempo=0.5", "atempo=0.5000"]

    def test_zero_speed(self) -> None:
        chain = _build_atempo_chain(0)
        assert chain == ["anull"]


# ── filter_complex detection ──


class TestFilterComplexDetection:
    def test_reverse_triggers_filter_complex(self) -> None:
        plan = _plan_with_clip(reverse=True)
        cmd = build_ffmpeg_command(plan)
        assert "-filter_complex" in cmd

    def test_frame_blend_triggers_filter_complex(self) -> None:
        plan = _plan_with_clip(speed=0.5, frame_blend=True)
        cmd = build_ffmpeg_command(plan)
        assert "-filter_complex" in cmd

    def test_speed_triggers_filter_complex(self) -> None:
        plan = _plan_with_clip(speed=2.0)
        cmd = build_ffmpeg_command(plan)
        assert "-filter_complex" in cmd


# ── RenderClip defaults ──


class TestRenderClipDefaults:
    def test_speed_defaults(self) -> None:
        clip = RenderClip(source_path="/tmp/test.mp4")
        assert clip.speed == 1.0
        assert clip.reverse is False
        assert clip.frame_blend is False
        assert clip.maintain_pitch is True
