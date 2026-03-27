"""
MARKER_DEPTH_MAP — Tests for depth effect definitions and filter compilation.

Tests: EFFECT_DEFS entries, compile_video_filters for depth_map/depth_blur/
depth_fog/depth_grade, parameter validation, FFmpeg filter string format.
"""
from __future__ import annotations

import pytest

from src.services.cut_effects_engine import (
    EFFECT_DEFS,
    EffectParam,
    compile_video_filters,
    _compile_depth_map_filter,
    _compile_depth_blur_filter,
    _compile_depth_fog_filter,
    _compile_depth_grade_filter,
)


# ── EFFECT_DEFS entries ──


class TestDepthEffectDefs:
    def test_depth_map_exists(self) -> None:
        assert "depth_map" in EFFECT_DEFS
        d = EFFECT_DEFS["depth_map"]
        assert d.category == "depth"
        assert d.label == "Depth Map"
        assert d.ffmpeg_video is True

    def test_depth_map_params(self) -> None:
        schema = EFFECT_DEFS["depth_map"].params_schema
        assert "near" in schema
        assert "far" in schema
        assert "gamma" in schema
        assert "invert" in schema
        assert schema["near"]["default"] == 0.9
        assert schema["far"]["default"] == 0.1

    def test_depth_blur_exists(self) -> None:
        assert "depth_blur" in EFFECT_DEFS
        assert EFFECT_DEFS["depth_blur"].category == "depth"

    def test_depth_fog_exists(self) -> None:
        assert "depth_fog" in EFFECT_DEFS
        assert EFFECT_DEFS["depth_fog"].category == "depth"

    def test_depth_grade_exists(self) -> None:
        assert "depth_grade" in EFFECT_DEFS
        assert EFFECT_DEFS["depth_grade"].category == "depth"

    def test_all_depth_effects_have_schemas(self) -> None:
        for name in ["depth_map", "depth_blur", "depth_fog", "depth_grade"]:
            d = EFFECT_DEFS[name]
            assert len(d.params_schema) > 0, f"{name} has empty params"


# ── _compile_depth_map_filter ──


class TestCompileDepthMapFilter:
    def test_basic_output_is_geq(self) -> None:
        result = _compile_depth_map_filter(0.9, 0.1, 1.0, False)
        assert result.startswith("geq=lum='")
        assert ":cb=128:cr=128" in result

    def test_gamma_appears_in_expression(self) -> None:
        result = _compile_depth_map_filter(0.9, 0.1, 2.5, False)
        assert "2.50" in result

    def test_invert_flag(self) -> None:
        normal = _compile_depth_map_filter(0.9, 0.1, 1.0, False)
        inverted = _compile_depth_map_filter(0.9, 0.1, 1.0, True)
        assert normal != inverted
        assert "1-pow" in inverted

    def test_near_far_values_scale_to_255(self) -> None:
        result = _compile_depth_map_filter(1.0, 0.0, 1.0, False)
        # far=0.0 → 0.0, near=1.0 → range=255
        assert "0.0" in result

    def test_safe_division_when_near_equals_far(self) -> None:
        # Should not crash — uses max(denom, 0.001)
        result = _compile_depth_map_filter(0.5, 0.5, 1.0, False)
        assert "geq=" in result


# ── _compile_depth_blur_filter ──


class TestCompileDepthBlurFilter:
    def test_uses_maskedmerge(self) -> None:
        result = _compile_depth_blur_filter(0.7, 0.1, 8.0)
        assert "maskedmerge" in result

    def test_uses_gblur(self) -> None:
        result = _compile_depth_blur_filter(0.7, 0.1, 8.0)
        assert "gblur=sigma=8.0" in result

    def test_uses_split(self) -> None:
        result = _compile_depth_blur_filter(0.7, 0.1, 8.0)
        assert "split[" in result


# ── _compile_depth_fog_filter ──


class TestCompileDepthFogFilter:
    def test_uses_maskedmerge(self) -> None:
        result = _compile_depth_fog_filter(0.3, 0.3, 0.8, 0.85, 0.85, 0.9)
        assert "maskedmerge" in result

    def test_fog_color_in_geq(self) -> None:
        result = _compile_depth_fog_filter(0.5, 0.2, 0.9, 1.0, 0.0, 0.0)
        # fog_r=1.0 → 255
        assert "r=255" in result
        assert "g=0" in result

    def test_uses_split(self) -> None:
        result = _compile_depth_fog_filter(0.3, 0.3, 0.8, 0.85, 0.85, 0.9)
        assert "split[" in result


# ── _compile_depth_grade_filter ──


class TestCompileDepthGradeFilter:
    def test_uses_maskedmerge(self) -> None:
        result = _compile_depth_grade_filter(0.8, 0.2, 0.05, 0.1, 1.0, 1.0)
        assert "maskedmerge" in result

    def test_eq_params_in_output(self) -> None:
        result = _compile_depth_grade_filter(0.8, 0.2, 0.05, 0.1, 1.2, 0.8)
        assert "brightness=0.100" in result
        assert "contrast=1.200" in result
        assert "saturation=0.800" in result

    def test_uses_split(self) -> None:
        result = _compile_depth_grade_filter(0.8, 0.2, 0.05, 0.1, 1.0, 1.0)
        assert "split[" in result


# ── compile_video_filters integration ──


class TestCompileVideoFiltersDepth:
    def test_depth_map_via_compile(self) -> None:
        effects = [EffectParam(type="depth_map", params={"near": 0.9, "far": 0.1, "gamma": 1.0})]
        result = compile_video_filters(effects)
        assert len(result) == 1
        assert "geq=" in result[0]

    def test_depth_blur_via_compile(self) -> None:
        effects = [EffectParam(type="depth_blur", params={"focus_depth": 0.7, "max_blur": 10.0})]
        result = compile_video_filters(effects)
        assert len(result) == 1
        assert "maskedmerge" in result[0]

    def test_depth_fog_via_compile(self) -> None:
        effects = [EffectParam(type="depth_fog", params={"density": 0.5})]
        result = compile_video_filters(effects)
        assert len(result) == 1
        assert "maskedmerge" in result[0]

    def test_depth_grade_via_compile(self) -> None:
        effects = [EffectParam(type="depth_grade", params={
            "brightness": 0.2, "contrast": 1.5, "saturation": 0.8,
        })]
        result = compile_video_filters(effects)
        assert len(result) == 1
        assert "eq=" in result[0]

    def test_depth_grade_no_change_no_filter(self) -> None:
        """When all grade params are default, no filter should be added."""
        effects = [EffectParam(type="depth_grade", params={
            "brightness": 0.0, "contrast": 1.0, "saturation": 1.0,
        })]
        result = compile_video_filters(effects)
        assert len(result) == 0

    def test_depth_blur_zero_blur_no_filter(self) -> None:
        effects = [EffectParam(type="depth_blur", params={"max_blur": 0.0})]
        result = compile_video_filters(effects)
        assert len(result) == 0

    def test_depth_fog_zero_density_no_filter(self) -> None:
        effects = [EffectParam(type="depth_fog", params={"density": 0.0})]
        result = compile_video_filters(effects)
        assert len(result) == 0

    def test_depth_map_disabled_no_filter(self) -> None:
        effects = [EffectParam(type="depth_map", enabled=False, params={"near": 0.9})]
        result = compile_video_filters(effects)
        assert len(result) == 0

    def test_depth_with_color_effects(self) -> None:
        """Depth effects should compose with existing color effects."""
        effects = [
            EffectParam(type="brightness", params={"value": 0.1}),
            EffectParam(type="depth_map", params={"near": 0.9, "far": 0.1}),
        ]
        result = compile_video_filters(effects)
        assert len(result) == 2
        assert "eq=" in result[0]  # brightness → eq (inserted at 0)
        assert "geq=" in result[1]  # depth_map

    def test_depth_map_invert_via_compile(self) -> None:
        effects = [EffectParam(type="depth_map", params={"invert": True})]
        result = compile_video_filters(effects)
        assert len(result) == 1
        assert "1-pow" in result[0]
