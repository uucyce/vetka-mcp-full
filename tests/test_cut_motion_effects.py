"""
MARKER_FCP7-66 — Tests for Motion attributes: Drop Shadow, Distort, Motion Blur.

Tests EFFECT_DEFS, FFmpeg compilation, CSS preview.
"""
from __future__ import annotations

import pytest

from src.services.cut_effects_engine import (
    EFFECT_DEFS,
    EffectParam,
    compile_video_filters,
    compile_css_filters,
    list_effects,
)


def _ep(t: str, params: dict) -> EffectParam:
    return EffectParam(effect_id="test", type=t, enabled=True, params=params)


# ── EFFECT_DEFS ──


class TestMotionEffectDefs:
    def test_drop_shadow_exists(self) -> None:
        assert "drop_shadow" in EFFECT_DEFS
        d = EFFECT_DEFS["drop_shadow"]
        assert d.category == "motion"
        assert "offset" in d.params_schema
        assert "angle" in d.params_schema
        assert "softness" in d.params_schema
        assert "opacity" in d.params_schema

    def test_distort_exists(self) -> None:
        assert "distort" in EFFECT_DEFS
        d = EFFECT_DEFS["distort"]
        assert d.category == "motion"
        # 4 corners × 2 coords = 8 params
        assert len(d.params_schema) == 8
        assert "tl_x" in d.params_schema
        assert "br_y" in d.params_schema

    def test_motion_blur_exists(self) -> None:
        assert "motion_blur" in EFFECT_DEFS
        d = EFFECT_DEFS["motion_blur"]
        assert d.category == "motion"
        assert "amount" in d.params_schema
        assert "samples" in d.params_schema

    def test_list_motion_effects(self) -> None:
        motion = list_effects(category="motion")
        types = {e["type"] for e in motion}
        assert "drop_shadow" in types
        assert "distort" in types
        assert "motion_blur" in types
        assert "position" in types
        assert "scale" in types
        assert "rotation" in types
        assert "opacity" in types


# ── Drop Shadow FFmpeg ──


class TestDropShadowFFmpeg:
    def test_basic_shadow(self) -> None:
        filters = compile_video_filters([_ep("drop_shadow", {
            "offset": 10, "angle": 135, "softness": 5, "opacity": 0.5,
        })])
        assert len(filters) >= 1
        combined = ";".join(filters)
        assert "split" in combined
        assert "boxblur" in combined
        assert "overlay" in combined

    def test_zero_offset_no_filter(self) -> None:
        filters = compile_video_filters([_ep("drop_shadow", {
            "offset": 0, "angle": 135, "softness": 5, "opacity": 0.5,
        })])
        shadow_filters = [f for f in filters if "split" in f]
        assert len(shadow_filters) == 0

    def test_zero_opacity_no_filter(self) -> None:
        filters = compile_video_filters([_ep("drop_shadow", {
            "offset": 10, "angle": 135, "softness": 5, "opacity": 0,
        })])
        shadow_filters = [f for f in filters if "split" in f]
        assert len(shadow_filters) == 0


# ── Drop Shadow CSS ──


class TestDropShadowCSS:
    def test_css_drop_shadow(self) -> None:
        css = compile_css_filters([_ep("drop_shadow", {
            "offset": 10, "angle": 135, "softness": 5, "opacity": 0.5,
        })])
        assert "drop-shadow(" in css
        assert "rgba(0,0,0,0.50)" in css


# ── Distort FFmpeg ──


class TestDistortFFmpeg:
    def test_perspective_transform(self) -> None:
        filters = compile_video_filters([_ep("distort", {
            "tl_x": 0.1, "tl_y": 0.0,
            "tr_x": 0.9, "tr_y": 0.0,
            "bl_x": 0.0, "bl_y": 1.0,
            "br_x": 1.0, "br_y": 1.0,
        })])
        assert len(filters) >= 1
        assert "perspective=" in filters[0]
        assert "interpolation=linear" in filters[0]

    def test_identity_no_filter(self) -> None:
        """Default corner positions = identity = no filter needed."""
        filters = compile_video_filters([_ep("distort", {
            "tl_x": 0, "tl_y": 0,
            "tr_x": 1, "tr_y": 0,
            "bl_x": 0, "bl_y": 1,
            "br_x": 1, "br_y": 1,
        })])
        perspective_filters = [f for f in filters if "perspective" in f]
        assert len(perspective_filters) == 0

    def test_corner_pin_uses_iw_ih(self) -> None:
        """Coordinates should reference iw/ih for resolution independence."""
        filters = compile_video_filters([_ep("distort", {
            "tl_x": 0.05, "tl_y": 0.05,
            "tr_x": 0.95, "tr_y": 0.05,
            "bl_x": 0.05, "bl_y": 0.95,
            "br_x": 0.95, "br_y": 0.95,
        })])
        assert "iw" in filters[0]
        assert "ih" in filters[0]


# ── Motion Blur FFmpeg ──


class TestMotionBlurFFmpeg:
    def test_basic_blur(self) -> None:
        filters = compile_video_filters([_ep("motion_blur", {
            "amount": 50, "samples": 4,
        })])
        assert len(filters) >= 1
        assert "avgblur" in filters[0]

    def test_zero_amount_no_filter(self) -> None:
        filters = compile_video_filters([_ep("motion_blur", {
            "amount": 0, "samples": 4,
        })])
        blur_filters = [f for f in filters if "avgblur" in f]
        assert len(blur_filters) == 0

    def test_high_samples_larger_radius(self) -> None:
        f1 = compile_video_filters([_ep("motion_blur", {"amount": 50, "samples": 2})])
        f2 = compile_video_filters([_ep("motion_blur", {"amount": 50, "samples": 16})])
        # Higher samples → larger blur radius
        r1 = int(f1[0].split("sizeX=")[1].split(":")[0])
        r2 = int(f2[0].split("sizeX=")[1].split(":")[0])
        assert r2 > r1


# ── Combined with existing effects ──


class TestCombinedMotionEffects:
    def test_shadow_plus_rotation(self) -> None:
        filters = compile_video_filters([
            _ep("rotation", {"degrees": 45}),
            _ep("drop_shadow", {"offset": 10, "angle": 90, "softness": 3, "opacity": 0.7}),
        ])
        combined = ";".join(filters)
        assert "rotate" in combined
        assert "split" in combined  # shadow

    def test_distort_plus_opacity(self) -> None:
        filters = compile_video_filters([
            _ep("distort", {"tl_x": 0.1, "tl_y": 0, "tr_x": 0.9, "tr_y": 0,
                            "bl_x": 0, "bl_y": 1, "br_x": 1, "br_y": 1}),
            _ep("opacity", {"value": 0.8}),
        ])
        assert any("perspective" in f for f in filters)
        assert any("colorchannelmixer" in f for f in filters)

    def test_disabled_effect_skipped(self) -> None:
        e = EffectParam(effect_id="test", type="drop_shadow", enabled=False,
                       params={"offset": 10, "angle": 135, "softness": 5, "opacity": 0.5})
        filters = compile_video_filters([e])
        assert len(filters) == 0
