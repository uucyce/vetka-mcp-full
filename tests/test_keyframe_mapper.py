"""
MARKER_B44: Tests for keyframe→FFmpeg pipeline mapper.
Tests interpolation, effect resolution, and sendcmd generation.
"""
import pytest
from src.services.cut_effects_engine import (
    EffectParam,
    interpolate_keyframes,
    resolve_effect_params_at_time,
    compile_keyframed_sendcmd,
    compile_video_filters,
)


# ─── interpolate_keyframes ───


class TestInterpolateKeyframes:
    def test_empty(self):
        assert interpolate_keyframes([], 1.0) == 0.0

    def test_single(self):
        assert interpolate_keyframes([{"time_sec": 0, "value": 0.5}], 5.0) == 0.5

    def test_hold_before(self):
        kfs = [{"time_sec": 1.0, "value": 0.2}, {"time_sec": 3.0, "value": 0.8}]
        assert interpolate_keyframes(kfs, 0.0) == 0.2

    def test_hold_after(self):
        kfs = [{"time_sec": 1.0, "value": 0.2}, {"time_sec": 3.0, "value": 0.8}]
        assert interpolate_keyframes(kfs, 5.0) == 0.8

    def test_linear_midpoint(self):
        kfs = [{"time_sec": 0, "value": 0.0}, {"time_sec": 2.0, "value": 1.0}]
        result = interpolate_keyframes(kfs, 1.0)
        assert abs(result - 0.5) < 0.001

    def test_linear_quarter(self):
        kfs = [{"time_sec": 0, "value": 0.0}, {"time_sec": 4.0, "value": 1.0}]
        result = interpolate_keyframes(kfs, 1.0)
        assert abs(result - 0.25) < 0.001

    def test_ease_in(self):
        """ease_in = t^2 → at t=0.5, value = 0.25 of range."""
        kfs = [
            {"time_sec": 0, "value": 0.0, "easing": "ease_in"},
            {"time_sec": 2.0, "value": 1.0},
        ]
        result = interpolate_keyframes(kfs, 1.0)  # t=0.5 → 0.25
        assert abs(result - 0.25) < 0.001

    def test_ease_out(self):
        """ease_out = 1-(1-t)^2 → at t=0.5, value = 0.75 of range."""
        kfs = [
            {"time_sec": 0, "value": 0.0, "easing": "ease_out"},
            {"time_sec": 2.0, "value": 1.0},
        ]
        result = interpolate_keyframes(kfs, 1.0)  # t=0.5 → 0.75
        assert abs(result - 0.75) < 0.001

    def test_bezier_smoothstep(self):
        """bezier = 3t^2 - 2t^3 → at t=0.5, value = 0.5."""
        kfs = [
            {"time_sec": 0, "value": 0.0, "easing": "bezier"},
            {"time_sec": 2.0, "value": 1.0},
        ]
        result = interpolate_keyframes(kfs, 1.0)
        assert abs(result - 0.5) < 0.001

    def test_multi_segment(self):
        """Three keyframes, sample in second segment."""
        kfs = [
            {"time_sec": 0, "value": 0.0},
            {"time_sec": 1.0, "value": 1.0},
            {"time_sec": 3.0, "value": 0.5},
        ]
        # At t=2.0: between kf1(1.0→1.0) and kf2(3.0→0.5), t_norm=0.5
        result = interpolate_keyframes(kfs, 2.0)
        assert abs(result - 0.75) < 0.001


# ─── resolve_effect_params_at_time ───


class TestResolveEffectParams:
    def test_no_keyframes(self):
        """No keyframes → returns original effect."""
        e = EffectParam(type="brightness", params={"value": 0.3})
        result = resolve_effect_params_at_time(e, {}, 1.0)
        assert result.params["value"] == 0.3

    def test_keyframed_param(self):
        """Keyframed brightness.value → interpolated at time."""
        e = EffectParam(type="brightness", params={"value": 0.0})
        kfs = {
            "brightness.value": [
                {"time_sec": 0, "value": 0.0},
                {"time_sec": 4.0, "value": 1.0},
            ]
        }
        result = resolve_effect_params_at_time(e, kfs, 2.0)
        assert abs(result.params["value"] - 0.5) < 0.001

    def test_keyframed_by_param_name_only(self):
        """Fallback: keyframe key = just param_name (not effect_type.param_name)."""
        e = EffectParam(type="blur", params={"sigma": 0.0})
        kfs = {"sigma": [{"time_sec": 0, "value": 0.0}, {"time_sec": 2.0, "value": 10.0}]}
        result = resolve_effect_params_at_time(e, kfs, 1.0)
        assert abs(result.params["sigma"] - 5.0) < 0.001

    def test_preserves_non_keyframed_params(self):
        """Non-keyframed params stay at their original values."""
        e = EffectParam(type="sharpen", params={"amount": 2.0, "size": 5})
        kfs = {"sharpen.amount": [{"time_sec": 0, "value": 0.0}, {"time_sec": 2.0, "value": 4.0}]}
        result = resolve_effect_params_at_time(e, kfs, 1.0)
        assert abs(result.params["amount"] - 2.0) < 0.001
        assert result.params["size"] == 5  # unchanged


# ─── compile_keyframed_sendcmd ───


class TestCompileKeyframedSendcmd:
    def test_empty_keyframes(self):
        result = compile_keyframed_sendcmd([], {}, 5.0)
        assert result == ""

    def test_no_matching_effects(self):
        """Effect with no sendcmd target → empty."""
        e = EffectParam(type="vignette", params={"angle": 0.4})
        result = compile_keyframed_sendcmd([e], {"vignette.angle": [{"time_sec": 0, "value": 0.1}, {"time_sec": 2, "value": 0.8}]}, 3.0)
        assert result == ""  # vignette not in SENDCMD_TARGETS

    def test_brightness_sendcmd(self):
        """Keyframed brightness → generates sendcmd commands."""
        e = EffectParam(type="brightness", params={"value": 0.0})
        kfs = {
            "brightness.value": [
                {"time_sec": 0, "value": 0.0},
                {"time_sec": 1.0, "value": 0.5},
            ]
        }
        result = compile_keyframed_sendcmd([e], kfs, 1.0, sample_interval=0.5)
        assert "[eq]" in result
        assert "brightness" in result
        # Should have samples at t=0.0, 0.5, 1.0
        lines = result.split(";\n")
        assert len(lines) == 3

    def test_single_keyframe_no_output(self):
        """Only 1 keyframe → no animation → empty sendcmd."""
        e = EffectParam(type="brightness", params={"value": 0.0})
        kfs = {"brightness.value": [{"time_sec": 0, "value": 0.5}]}
        result = compile_keyframed_sendcmd([e], kfs, 2.0)
        assert result == ""  # single KF = no interpolation


# ─── Integration: keyframed effects → FFmpeg filters ───


class TestKeyframedCompileVideoFilters:
    def test_resolved_effect_compiles(self):
        """Keyframe-resolved brightness compiles to eq filter."""
        e = EffectParam(type="brightness", params={"value": 0.0})
        kfs = {
            "brightness.value": [
                {"time_sec": 0, "value": 0.0},
                {"time_sec": 4.0, "value": 0.4},
            ]
        }
        resolved = resolve_effect_params_at_time(e, kfs, 2.0)  # midpoint → 0.2
        filters = compile_video_filters([resolved])
        assert len(filters) == 1
        assert "eq=" in filters[0]
        assert "brightness=" in filters[0]
