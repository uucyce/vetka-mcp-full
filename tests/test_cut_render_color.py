"""
MARKER_B16 — Tests for color pipeline in render engine.

Tests: log decode filters, LUT application, filter_complex detection,
color pipeline ordering (log → LUT → effects → speed).
"""
from __future__ import annotations

import os
import tempfile

import pytest

from src.services.cut_effects_engine import EffectParam
from src.services.cut_render_engine import (
    FilterGraphBuilder,
    RenderClip,
    RenderPlan,
    build_ffmpeg_command,
    _compile_log_decode_filter,
)


def _ep(effect_type: str, params: dict) -> EffectParam:
    """Helper: create an EffectParam."""
    return EffectParam(effect_id="test", type=effect_type, enabled=True, params=params)


def _plan_with_clip(**clip_kwargs) -> RenderPlan:
    """Helper: create a plan with a single clip."""
    clip = RenderClip(source_path="/tmp/test.mp4", duration_sec=10.0, **clip_kwargs)
    return RenderPlan(clips=[clip], width=1920, height=1080, fps=25)


# ── Log decode filters ──


class TestLogDecodeFilter:
    def test_vlog(self) -> None:
        f = _compile_log_decode_filter("V-Log")
        assert "curves=master=" in f
        assert f != ""

    def test_slog3(self) -> None:
        f = _compile_log_decode_filter("S-Log3")
        assert "curves=master=" in f

    def test_logc3(self) -> None:
        f = _compile_log_decode_filter("LogC3")
        assert "curves=master=" in f

    def test_arri_logc3_alias(self) -> None:
        f = _compile_log_decode_filter("ARRI LogC3")
        assert "curves=master=" in f

    def test_canon_log3(self) -> None:
        f = _compile_log_decode_filter("Canon Log 3")
        assert "curves=master=" in f

    def test_srgb_no_decode(self) -> None:
        f = _compile_log_decode_filter("sRGB")
        assert f == ""

    def test_hlg(self) -> None:
        f = _compile_log_decode_filter("HLG")
        assert "zscale" in f
        assert "arib-std-b67" in f

    def test_pq_tonemaps(self) -> None:
        f = _compile_log_decode_filter("PQ")
        assert "zscale" in f
        assert "smpte2084" in f

    def test_unknown_returns_empty(self) -> None:
        f = _compile_log_decode_filter("SomeUnknownProfile")
        assert f == ""

    def test_empty_returns_empty(self) -> None:
        f = _compile_log_decode_filter("")
        assert f == ""


# ── Log decode in filter graph ──


class TestLogDecodeInFilterGraph:
    def test_vlog_in_filter_graph(self) -> None:
        plan = _plan_with_clip(log_profile="V-Log")
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "curves=master=" in fg

    def test_no_log_no_curves(self) -> None:
        plan = _plan_with_clip()
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "curves=master=" not in fg

    def test_log_before_effects(self) -> None:
        """Log decode should appear before user effects in filter chain."""
        plan = _plan_with_clip(
            log_profile="V-Log",
            video_effects=[_ep("brightness", {"value": 0.1})],
        )
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        # curves (log) should come before eq (brightness)
        curves_pos = fg.find("curves=master=")
        eq_pos = fg.find("eq=")
        assert curves_pos < eq_pos, "Log decode must come before user effects"


# ── LUT in filter graph ──


class TestLutInFilterGraph:
    def test_lut_in_filter_graph(self) -> None:
        # Create a temp file to simulate LUT
        with tempfile.NamedTemporaryFile(suffix=".cube", delete=False) as f:
            f.write(b"LUT_3D_SIZE 2\n0 0 0\n1 0 0\n0 1 0\n1 1 0\n0 0 1\n1 0 1\n0 1 1\n1 1 1\n")
            lut_path = f.name
        try:
            plan = _plan_with_clip(lut_path=lut_path)
            builder = FilterGraphBuilder(plan)
            _, fg = builder.build()
            assert "lut3d=" in fg
            assert lut_path in fg
        finally:
            os.unlink(lut_path)

    def test_no_lut_no_lut3d(self) -> None:
        plan = _plan_with_clip()
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "lut3d=" not in fg

    def test_nonexistent_lut_skipped(self) -> None:
        plan = _plan_with_clip(lut_path="/nonexistent/path.cube")
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "lut3d=" not in fg  # File doesn't exist, skip

    def test_lut_before_effects(self) -> None:
        """LUT should appear before user effects."""
        with tempfile.NamedTemporaryFile(suffix=".cube", delete=False) as f:
            f.write(b"LUT_3D_SIZE 2\n0 0 0\n1 0 0\n0 1 0\n1 1 0\n0 0 1\n1 0 1\n0 1 1\n1 1 1\n")
            lut_path = f.name
        try:
            plan = _plan_with_clip(
                lut_path=lut_path,
                video_effects=[_ep("saturation", {"value": 0.5})],
            )
            builder = FilterGraphBuilder(plan)
            _, fg = builder.build()
            lut_pos = fg.find("lut3d=")
            eq_pos = fg.find("eq=")
            assert lut_pos < eq_pos, "LUT must come before user effects"
        finally:
            os.unlink(lut_path)


# ── Combined: log + LUT + effects ──


class TestCombinedColorPipeline:
    def test_full_pipeline_order(self) -> None:
        """Full color pipeline: log decode → LUT → effects → speed."""
        with tempfile.NamedTemporaryFile(suffix=".cube", delete=False) as f:
            f.write(b"LUT_3D_SIZE 2\n0 0 0\n1 0 0\n0 1 0\n1 1 0\n0 0 1\n1 0 1\n0 1 1\n1 1 1\n")
            lut_path = f.name
        try:
            plan = _plan_with_clip(
                log_profile="S-Log3",
                lut_path=lut_path,
                speed=0.5,
                video_effects=[_ep("contrast", {"value": 1.2})],
            )
            builder = FilterGraphBuilder(plan)
            _, fg = builder.build()

            curves_pos = fg.find("curves=master=")
            lut_pos = fg.find("lut3d=")
            eq_pos = fg.find("eq=")
            speed_pos = fg.find("setpts=2.0000")

            assert curves_pos >= 0, "Log decode missing"
            assert lut_pos >= 0, "LUT missing"
            assert eq_pos >= 0, "Effects missing"
            assert speed_pos >= 0, "Speed missing"
            assert curves_pos < lut_pos, "Log decode must come before LUT"
            assert lut_pos < eq_pos, "LUT must come before effects"
            assert eq_pos < speed_pos, "Effects must come before speed"
        finally:
            os.unlink(lut_path)


# ── filter_complex detection ──


class TestFilterComplexDetection:
    def test_log_profile_triggers_filter_complex(self) -> None:
        plan = _plan_with_clip(log_profile="V-Log")
        cmd = build_ffmpeg_command(plan)
        assert "-filter_complex" in cmd

    def test_lut_triggers_filter_complex(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".cube", delete=False) as f:
            f.write(b"LUT_3D_SIZE 2\n0 0 0\n1 0 0\n0 1 0\n1 1 0\n0 0 1\n1 0 1\n0 1 1\n1 1 1\n")
            lut_path = f.name
        try:
            plan = _plan_with_clip(lut_path=lut_path)
            cmd = build_ffmpeg_command(plan)
            assert "-filter_complex" in cmd
        finally:
            os.unlink(lut_path)


# ── RenderClip defaults ──


class TestRenderClipColorDefaults:
    def test_defaults(self) -> None:
        clip = RenderClip(source_path="/tmp/test.mp4")
        assert clip.log_profile == ""
        assert clip.lut_path == ""
