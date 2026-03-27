"""
MARKER_PARALLAX_MOTION — Tests for parallax motion effect and depth engine.

Tests: CameraGeometry, depth band math, FFmpeg expression builders,
parallax_motion EffectDef, sentinel pattern, filter chain generation.
"""
from __future__ import annotations

import json
import math

import pytest

from src.services.cut_effects_engine import (
    EFFECT_DEFS,
    EffectParam,
    compile_video_filters,
    is_parallax_motion_filter,
    parse_parallax_motion_params,
)
from src.services.cut_depth_engine import (
    DEPTH_BANDS,
    CameraGeometry,
    build_band_motion_expr,
    build_band_zoom_expr,
    build_parallax_ffmpeg_cmd,
    build_parallax_filter,
    compute_motion_pixels,
    depth_byte_to_z,
    normalize_motion_type,
)
from src.services.cut_layer_manifest import CameraContract


# ── CameraGeometry ──


class TestCameraGeometry:
    def test_default_values(self) -> None:
        cam = CameraGeometry()
        assert cam.focal_length_mm == 50.0
        assert cam.z_near == 0.72
        assert cam.z_far == 1.85
        assert cam.motion_type == "orbit"

    def test_aov_rad(self) -> None:
        cam = CameraGeometry(focal_length_mm=50.0, film_width_mm=36.0)
        expected = 2.0 * math.atan(36.0 / (2.0 * 50.0))
        assert abs(cam.aov_rad - expected) < 1e-6

    def test_reference_z(self) -> None:
        cam = CameraGeometry(z_near=0.5, z_far=1.5)
        assert cam.reference_z == 1.0

    def test_zoom_px(self) -> None:
        cam = CameraGeometry(focal_length_mm=50.0, film_width_mm=36.0)
        zp = cam.zoom_px(1920)
        assert zp > 0
        # Higher focal length → more zoom → larger zoom_px
        cam2 = CameraGeometry(focal_length_mm=100.0)
        assert cam2.zoom_px(1920) > cam.zoom_px(1920)

    def test_from_effect_params(self) -> None:
        params = {"travel_x": 10.0, "zoom": 1.1, "motion_type": "linear"}
        cam = CameraGeometry.from_effect_params(params)
        assert cam.travel_x == 10.0
        assert cam.zoom == 1.1
        assert cam.motion_type == "linear"

    def test_from_effect_params_defaults(self) -> None:
        cam = CameraGeometry.from_effect_params({})
        assert cam.focal_length_mm == 50.0
        assert cam.duration_sec == 4.0


# ── Depth math ──


class TestDepthMath:
    def test_depth_byte_255_is_near(self) -> None:
        z = depth_byte_to_z(255, 0.72, 1.85)
        assert abs(z - 0.72) < 0.01  # white = near

    def test_depth_byte_0_is_far(self) -> None:
        z = depth_byte_to_z(0, 0.72, 1.85)
        assert abs(z - 1.85) < 0.01  # black = far

    def test_depth_byte_128_is_mid(self) -> None:
        z = depth_byte_to_z(128, 0.72, 1.85)
        assert 0.72 < z < 1.85

    def test_depth_bands_cover_full_range(self) -> None:
        mins = [b["min"] for b in DEPTH_BANDS]
        maxs = [b["max"] for b in DEPTH_BANDS]
        assert min(mins) == 1   # no black (0 = background)
        assert max(maxs) == 255


# ── Motion expressions ──


class TestMotionExpressions:
    def setup_method(self) -> None:
        self.cam = CameraGeometry(travel_x=5.0, duration_sec=4.0)

    def test_compute_motion_pixels_returns_float(self) -> None:
        px = compute_motion_pixels(self.cam, 1920, 200, "x")
        assert isinstance(px, float)

    def test_near_objects_move_more(self) -> None:
        near_px = abs(compute_motion_pixels(self.cam, 1920, 240, "x"))
        far_px = abs(compute_motion_pixels(self.cam, 1920, 50, "x"))
        assert near_px > far_px  # near objects have more parallax

    def test_build_band_motion_expr_orbit(self) -> None:
        expr = build_band_motion_expr(self.cam, 1920, 200, "x")
        assert "sin" in expr  # orbit uses sin for x

    def test_build_band_motion_expr_orbit_y(self) -> None:
        expr = build_band_motion_expr(self.cam, 1920, 200, "y")
        assert "cos" in expr  # orbit uses cos for y

    def test_build_band_motion_expr_linear(self) -> None:
        cam = CameraGeometry(travel_x=5.0, motion_type="linear")
        expr = build_band_motion_expr(cam, 1920, 200, "x")
        assert "sin" in expr

    def test_build_band_zoom_expr_orbit(self) -> None:
        cam = CameraGeometry(zoom=1.1, motion_type="orbit")
        expr = build_band_zoom_expr(cam, 1.0)
        assert "cos" in expr

    def test_build_band_zoom_expr_no_zoom(self) -> None:
        cam = CameraGeometry(zoom=1.0)
        expr = build_band_zoom_expr(cam, 1.0)
        assert "0.000000" in expr  # zoom_delta = 0


# ── Parallax filter chain ──


class TestParallaxFilter:
    def test_builds_valid_filter_complex(self) -> None:
        cam = CameraGeometry(travel_x=5.0, duration_sec=3.0)
        fc = build_parallax_filter(cam, 1920, 1080)
        assert "color=c=black" in fc
        assert "overlay" in fc
        assert "parallax_out" in fc

    def test_contains_depth_bands(self) -> None:
        cam = CameraGeometry()
        fc = build_parallax_filter(cam, 1920, 1080)
        for band in DEPTH_BANDS:
            assert band["name"] in fc

    def test_output_label_customizable(self) -> None:
        cam = CameraGeometry()
        fc = build_parallax_filter(cam, 1920, 1080, output_label="my_out")
        assert "[my_out]" in fc

    def test_contains_crop_to_output(self) -> None:
        cam = CameraGeometry()
        fc = build_parallax_filter(cam, 1920, 1080)
        assert "crop=1920:1080" in fc

    def test_contains_fps(self) -> None:
        cam = CameraGeometry()
        fc = build_parallax_filter(cam, 1920, 1080)
        assert "fps=25" in fc


# ── FFmpeg command builder ──


class TestParallaxFfmpegCmd:
    def test_builds_valid_command(self) -> None:
        cam = CameraGeometry()
        cmd = build_parallax_ffmpeg_cmd("/src.jpg", "/depth.png", "/out.mp4", cam)
        assert cmd[0] == "ffmpeg"
        assert "/src.jpg" in cmd
        assert "/depth.png" in cmd
        assert "/out.mp4" in cmd
        assert "-filter_complex" in cmd
        assert "-c:v" in cmd

    def test_duration_in_command(self) -> None:
        cam = CameraGeometry(duration_sec=5.0)
        cmd = build_parallax_ffmpeg_cmd("/src.jpg", "/depth.png", "/out.mp4", cam)
        t_idx = cmd.index("-t")
        assert cmd[t_idx + 1] == "5.0"

    def test_loop_inputs(self) -> None:
        cam = CameraGeometry()
        cmd = build_parallax_ffmpeg_cmd("/src.jpg", "/depth.png", "/out.mp4", cam)
        assert cmd.count("-loop") == 2  # both inputs looped


# ── EFFECT_DEFS entry ──


class TestParallaxMotionEffectDef:
    def test_exists_in_defs(self) -> None:
        assert "parallax_motion" in EFFECT_DEFS
        d = EFFECT_DEFS["parallax_motion"]
        assert d.category == "parallax"
        assert d.label == "Parallax Motion"

    def test_has_key_params(self) -> None:
        schema = EFFECT_DEFS["parallax_motion"].params_schema
        assert "travel_x" in schema
        assert "travel_y" in schema
        assert "zoom" in schema
        assert "focal_length_mm" in schema
        assert "motion_type" in schema
        assert "duration_sec" in schema

    def test_motion_type_options(self) -> None:
        options = EFFECT_DEFS["parallax_motion"].params_schema["motion_type"]["options"]
        assert "orbit" in options
        assert "linear" in options


# ── Sentinel pattern ──


class TestParallaxSentinel:
    def test_compile_produces_sentinel(self) -> None:
        effects = [EffectParam(type="parallax_motion", params={"travel_x": 8.0})]
        result = compile_video_filters(effects)
        assert len(result) == 1
        assert is_parallax_motion_filter(result[0])

    def test_parse_sentinel_params(self) -> None:
        effects = [EffectParam(type="parallax_motion", params={
            "travel_x": 8.0, "zoom": 1.1, "motion_type": "linear",
        })]
        result = compile_video_filters(effects)
        params = parse_parallax_motion_params(result[0])
        assert params["travel_x"] == 8.0
        assert params["zoom"] == 1.1
        assert params["motion_type"] == "linear"

    def test_sentinel_with_defaults(self) -> None:
        effects = [EffectParam(type="parallax_motion", params={})]
        result = compile_video_filters(effects)
        params = parse_parallax_motion_params(result[0])
        assert params["travel_x"] == 5.0  # default
        assert params["duration_sec"] == 4.0

    def test_non_sentinel_returns_false(self) -> None:
        assert not is_parallax_motion_filter("gblur=sigma=5.0")

    def test_parse_non_sentinel_returns_empty(self) -> None:
        assert parse_parallax_motion_params("gblur=sigma=5.0") == {}

    def test_disabled_effect_no_sentinel(self) -> None:
        effects = [EffectParam(type="parallax_motion", enabled=False, params={"travel_x": 5.0})]
        result = compile_video_filters(effects)
        assert len(result) == 0

    def test_parallax_with_other_effects(self) -> None:
        effects = [
            EffectParam(type="brightness", params={"value": 0.1}),
            EffectParam(type="parallax_motion", params={"travel_x": 5.0}),
        ]
        result = compile_video_filters(effects)
        assert len(result) == 2
        assert "eq=" in result[0]
        assert is_parallax_motion_filter(result[1])


# ── CameraContract → CameraGeometry bridge ──


class TestCameraContractBridge:
    """LAYERFX-3: Verify CameraContract from manifest converts to CameraGeometry."""

    def test_from_camera_contract_basic(self) -> None:
        contract = CameraContract(
            focal_length_mm=50.0, film_width_mm=36.0,
            z_near=0.72, z_far=1.85,
            travel_x_pct=3.0, travel_y_pct=1.0,
            zoom=1.05, motion_type="orbit",
            duration_sec=4.0, overscan_pct=20.0,
        )
        cam = CameraGeometry.from_camera_contract(contract, 1920, 1080)
        assert cam.focal_length_mm == 50.0
        assert cam.z_near == 0.72
        assert cam.z_far == 1.85
        assert cam.zoom == 1.05
        assert cam.motion_type == "orbit"
        assert cam.duration_sec == 4.0
        assert cam.overscan_pct == 20.0

    def test_travel_pct_to_pixels(self) -> None:
        contract = CameraContract(travel_x_pct=5.0, travel_y_pct=2.0)
        cam = CameraGeometry.from_camera_contract(contract, 1920, 1080)
        assert cam.travel_x == 1920 * 5.0 / 100.0  # 96.0
        assert cam.travel_y == 1080 * 2.0 / 100.0  # 21.6

    def test_motion_type_normalization_portrait_base(self) -> None:
        """Alpha uses 'portrait-base' which maps to 'orbit'."""
        contract = CameraContract(motion_type="portrait-base")
        cam = CameraGeometry.from_camera_contract(contract, 1920, 1080)
        assert cam.motion_type == "orbit"

    def test_motion_type_normalization_dolly(self) -> None:
        contract = CameraContract(motion_type="dolly-out + zoom-in")
        cam = CameraGeometry.from_camera_contract(contract, 1920, 1080)
        assert cam.motion_type == "dolly_zoom_in"

    def test_real_alpha_camera(self) -> None:
        """Test with real hover-politsia camera contract values."""
        contract = CameraContract.from_dict({
            "focalLengthMm": 50, "filmWidthMm": 36,
            "zNear": 0.72, "zFar": 1.85,
            "motionType": "portrait-base",
            "durationSec": 4.0, "travelXPct": 3.0, "travelYPct": 0.6,
            "zoom": 1.06, "overscanPct": 26.07,
        })
        cam = CameraGeometry.from_camera_contract(contract, 2560, 1440)
        assert cam.focal_length_mm == 50.0
        assert cam.motion_type == "orbit"  # portrait-base → orbit
        assert abs(cam.travel_x - 76.8) < 0.1  # 2560 * 3.0 / 100
        assert abs(cam.travel_y - 8.64) < 0.1  # 1440 * 0.6 / 100
        assert cam.overscan_pct == 26.07
        # Verify it produces valid filter output
        fc = build_parallax_filter(cam, 2560, 1440)
        assert "overlay" in fc

    def test_film_width_preserved(self) -> None:
        contract = CameraContract(film_width_mm=24.0)  # Super 35
        cam = CameraGeometry.from_camera_contract(contract, 1920, 1080)
        assert cam.film_width_mm == 24.0


# ── Motion type normalization ──


class TestMotionTypeNormalization:
    def test_orbit_passthrough(self) -> None:
        assert normalize_motion_type("orbit") == "orbit"

    def test_portrait_base_to_orbit(self) -> None:
        assert normalize_motion_type("portrait-base") == "orbit"

    def test_dolly_out_zoom_in(self) -> None:
        assert normalize_motion_type("dolly-out + zoom-in") == "dolly_zoom_in"

    def test_dolly_in_zoom_out(self) -> None:
        assert normalize_motion_type("dolly-in + zoom-out") == "dolly_zoom_out"

    def test_unknown_defaults_to_orbit(self) -> None:
        assert normalize_motion_type("weird-type") == "orbit"

    def test_already_canonical(self) -> None:
        assert normalize_motion_type("dolly_zoom_in") == "dolly_zoom_in"
        assert normalize_motion_type("linear") == "linear"
