"""
MARKER_B20 — Tests for cut_preview_decoder.py

Tests preview decode pipeline, numpy effects, and session management.
Uses synthetic frames (no real video needed for unit tests).

@task: tb_1773995026_5
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pytest

from src.services.cut_preview_decoder import (
    apply_numpy_effects,
    encode_preview_jpeg,
    _compute_proxy_dims,
    HAS_PYAV,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mid_grey_frame():
    """100x100 mid-grey frame, float32 [0, 1]."""
    return np.full((100, 100, 3), 0.5, dtype=np.float32)


@pytest.fixture
def gradient_frame():
    """100x256 gradient frame, float32."""
    frame = np.zeros((100, 256, 3), dtype=np.float32)
    for x in range(256):
        frame[:, x, :] = x / 255.0
    return frame


@pytest.fixture
def rgb_frame_uint8():
    """100x100 RGB uint8 frame."""
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    frame[:, :, 0] = 200  # red
    frame[:, :, 1] = 100  # green
    frame[:, :, 2] = 50  # blue
    return frame


# ---------------------------------------------------------------------------
# Proxy dimension tests
# ---------------------------------------------------------------------------

class TestProxyDims:
    def test_4k_to_540(self):
        w, h = _compute_proxy_dims(3840, 2160, 540)
        assert h == 540
        assert w == 960

    def test_1080_to_540(self):
        w, h = _compute_proxy_dims(1920, 1080, 540)
        assert h == 540
        assert w == 960

    def test_small_video_unchanged(self):
        w, h = _compute_proxy_dims(640, 480, 540)
        assert w == 640 and h == 480

    def test_even_dimensions(self):
        w, h = _compute_proxy_dims(1921, 1081, 540)
        assert w % 2 == 0
        assert h % 2 == 0


# ---------------------------------------------------------------------------
# Numpy effects tests
# ---------------------------------------------------------------------------

class TestNumpyEffects:
    def test_brightness_positive(self, mid_grey_frame):
        result = apply_numpy_effects(mid_grey_frame, [
            {"type": "brightness", "params": {"value": 0.2}, "enabled": True}
        ])
        assert result.mean() > 0.6

    def test_brightness_negative(self, mid_grey_frame):
        result = apply_numpy_effects(mid_grey_frame, [
            {"type": "brightness", "params": {"value": -0.3}, "enabled": True}
        ])
        assert result.mean() < 0.3

    def test_contrast_increase(self, gradient_frame):
        result = apply_numpy_effects(gradient_frame, [
            {"type": "contrast", "params": {"value": 2.0}, "enabled": True}
        ])
        # Higher contrast → wider range of values
        original_std = gradient_frame.std()
        result_std = result.std()
        assert result_std > original_std * 1.3

    def test_saturation_zero(self, mid_grey_frame):
        # Make a colored frame first
        colored = mid_grey_frame.copy()
        colored[:, :, 0] = 0.8  # R
        colored[:, :, 1] = 0.3  # G
        colored[:, :, 2] = 0.2  # B

        result = apply_numpy_effects(colored, [
            {"type": "saturation", "params": {"value": 0.0}, "enabled": True}
        ])
        # Saturation 0 → greyscale (R ≈ G ≈ B)
        r_mean = result[:, :, 0].mean()
        g_mean = result[:, :, 1].mean()
        b_mean = result[:, :, 2].mean()
        assert abs(r_mean - g_mean) < 0.01
        assert abs(g_mean - b_mean) < 0.01

    def test_gamma(self, mid_grey_frame):
        result = apply_numpy_effects(mid_grey_frame, [
            {"type": "gamma", "params": {"value": 2.2}, "enabled": True}
        ])
        # Gamma > 1 → brighter midtones
        assert result.mean() > mid_grey_frame.mean()

    def test_exposure_positive(self, mid_grey_frame):
        result = apply_numpy_effects(mid_grey_frame, [
            {"type": "exposure", "params": {"stops": 1.0}, "enabled": True}
        ])
        # +1 stop → roughly 2x brighter (clamped to 1.0)
        assert result.mean() > mid_grey_frame.mean()

    def test_opacity(self, mid_grey_frame):
        result = apply_numpy_effects(mid_grey_frame, [
            {"type": "opacity", "params": {"value": 0.5}, "enabled": True}
        ])
        np.testing.assert_allclose(result.mean(), 0.25, atol=0.01)

    def test_disabled_effect_skipped(self, mid_grey_frame):
        result = apply_numpy_effects(mid_grey_frame, [
            {"type": "brightness", "params": {"value": 1.0}, "enabled": False}
        ])
        np.testing.assert_array_equal(result, mid_grey_frame)

    def test_multiple_effects_chain(self, mid_grey_frame):
        """Multiple effects should chain sequentially."""
        result = apply_numpy_effects(mid_grey_frame, [
            {"type": "brightness", "params": {"value": 0.1}, "enabled": True},
            {"type": "contrast", "params": {"value": 1.5}, "enabled": True},
        ])
        # Should be different from single effect
        single = apply_numpy_effects(mid_grey_frame, [
            {"type": "brightness", "params": {"value": 0.1}, "enabled": True},
        ])
        assert not np.allclose(result, single)

    def test_output_range_clamped(self, mid_grey_frame):
        result = apply_numpy_effects(mid_grey_frame, [
            {"type": "brightness", "params": {"value": 2.0}, "enabled": True}
        ])
        assert result.max() <= 1.0
        assert result.min() >= 0.0

    def test_hue_rotation(self, mid_grey_frame):
        colored = mid_grey_frame.copy()
        colored[:, :, 0] = 0.9
        colored[:, :, 1] = 0.1
        colored[:, :, 2] = 0.1

        result = apply_numpy_effects(colored, [
            {"type": "hue", "params": {"degrees": 120}, "enabled": True}
        ])
        # 120° rotation should shift red towards green
        assert result[:, :, 1].mean() > colored[:, :, 1].mean()


# ---------------------------------------------------------------------------
# MARKER_B9: Color grading effects preview tests
# ---------------------------------------------------------------------------

class TestLiftEffect:
    def test_lift_shifts_shadows(self, gradient_frame):
        result = apply_numpy_effects(gradient_frame, [
            {"type": "lift", "params": {"r": 0.3, "g": 0, "b": 0}, "enabled": True}
        ])
        # Red channel in dark areas should increase
        dark_region = result[:, :20, 0].mean()
        original_dark = gradient_frame[:, :20, 0].mean()
        assert dark_region > original_dark + 0.05

    def test_lift_zero_noop(self, mid_grey_frame):
        result = apply_numpy_effects(mid_grey_frame, [
            {"type": "lift", "params": {"r": 0, "g": 0, "b": 0}, "enabled": True}
        ])
        np.testing.assert_array_equal(result, mid_grey_frame)


class TestMidtoneEffect:
    def test_midtone_shifts_mids(self, mid_grey_frame):
        result = apply_numpy_effects(mid_grey_frame, [
            {"type": "midtone", "params": {"r": 0, "g": 0.3, "b": 0}, "enabled": True}
        ])
        # Green channel at 0.5 luma should increase
        assert result[:, :, 1].mean() > mid_grey_frame[:, :, 1].mean()

    def test_midtone_zero_noop(self, mid_grey_frame):
        result = apply_numpy_effects(mid_grey_frame, [
            {"type": "midtone", "params": {"r": 0, "g": 0, "b": 0}, "enabled": True}
        ])
        np.testing.assert_array_equal(result, mid_grey_frame)


class TestGainEffect:
    def test_gain_shifts_highlights(self, gradient_frame):
        result = apply_numpy_effects(gradient_frame, [
            {"type": "gain", "params": {"r": 0, "g": 0, "b": 0.3}, "enabled": True}
        ])
        # Blue channel in bright areas should increase
        bright_region = result[:, 200:, 2].mean()
        original_bright = gradient_frame[:, 200:, 2].mean()
        assert bright_region > original_bright + 0.05

    def test_gain_zero_noop(self, mid_grey_frame):
        result = apply_numpy_effects(mid_grey_frame, [
            {"type": "gain", "params": {"r": 0, "g": 0, "b": 0}, "enabled": True}
        ])
        np.testing.assert_array_equal(result, mid_grey_frame)


class TestWhiteBalanceEffect:
    def test_warm_shifts_red(self):
        frame = np.full((50, 50, 3), 0.5, dtype=np.float32)
        result = apply_numpy_effects(frame.copy(), [
            {"type": "white_balance", "params": {"temperature": 10000}, "enabled": True}
        ])
        assert result[:, :, 0].mean() > 0.5  # warmer = more red
        assert result[:, :, 2].mean() < 0.5  # less blue

    def test_cool_shifts_blue(self):
        frame = np.full((50, 50, 3), 0.5, dtype=np.float32)
        result = apply_numpy_effects(frame.copy(), [
            {"type": "white_balance", "params": {"temperature": 3000}, "enabled": True}
        ])
        assert result[:, :, 2].mean() > 0.5  # cooler = more blue
        assert result[:, :, 0].mean() < 0.5  # less red

    def test_neutral_noop(self):
        frame = np.full((50, 50, 3), 0.5, dtype=np.float32)
        result = apply_numpy_effects(frame.copy(), [
            {"type": "white_balance", "params": {"temperature": 6500}, "enabled": True}
        ])
        np.testing.assert_allclose(result, frame, atol=0.001)


class TestCurvesEffect:
    def test_lighter_brightens(self, mid_grey_frame):
        result = apply_numpy_effects(mid_grey_frame, [
            {"type": "curves", "params": {"preset": "lighter"}, "enabled": True}
        ])
        assert result.mean() > mid_grey_frame.mean()

    def test_darker_darkens(self, mid_grey_frame):
        result = apply_numpy_effects(mid_grey_frame, [
            {"type": "curves", "params": {"preset": "darker"}, "enabled": True}
        ])
        assert result.mean() < mid_grey_frame.mean()

    def test_negative_inverts(self, mid_grey_frame):
        colored = mid_grey_frame.copy()
        colored[:, :, 0] = 0.8
        result = apply_numpy_effects(colored, [
            {"type": "curves", "params": {"preset": "negative"}, "enabled": True}
        ])
        assert result[:, :, 0].mean() < 0.3  # inverted

    def test_none_noop(self, mid_grey_frame):
        result = apply_numpy_effects(mid_grey_frame, [
            {"type": "curves", "params": {"preset": "none"}, "enabled": True}
        ])
        np.testing.assert_array_equal(result, mid_grey_frame)


class TestColorBalanceEffect:
    def test_shadow_red_shift(self, gradient_frame):
        result = apply_numpy_effects(gradient_frame, [
            {"type": "color_balance", "params": {"rs": 0.3, "gs": 0, "bs": 0}, "enabled": True}
        ])
        dark_red = result[:, :20, 0].mean()
        orig_dark_red = gradient_frame[:, :20, 0].mean()
        assert dark_red > orig_dark_red

    def test_all_zero_noop(self, mid_grey_frame):
        result = apply_numpy_effects(mid_grey_frame, [
            {"type": "color_balance", "params": {
                "rs": 0, "gs": 0, "bs": 0, "rm": 0, "gm": 0, "bm": 0, "rh": 0, "gh": 0, "bh": 0
            }, "enabled": True}
        ])
        np.testing.assert_array_equal(result, mid_grey_frame)


# ---------------------------------------------------------------------------
# MARKER_B28: Motion effects preview tests
# ---------------------------------------------------------------------------

class TestDropShadowEffect:
    def test_shadow_darkens_frame(self, mid_grey_frame):
        result = apply_numpy_effects(mid_grey_frame, [
            {"type": "drop_shadow", "params": {"offset": 10, "angle": 135, "softness": 3, "opacity": 0.5}, "enabled": True}
        ])
        # Shadow compositing should alter the frame
        assert not np.allclose(result, mid_grey_frame, atol=0.01)
        assert result.shape == mid_grey_frame.shape

    def test_shadow_zero_offset_noop(self, mid_grey_frame):
        result = apply_numpy_effects(mid_grey_frame, [
            {"type": "drop_shadow", "params": {"offset": 0, "angle": 135, "softness": 5, "opacity": 0.5}, "enabled": True}
        ])
        np.testing.assert_array_equal(result, mid_grey_frame)

    def test_shadow_zero_opacity_noop(self, mid_grey_frame):
        result = apply_numpy_effects(mid_grey_frame, [
            {"type": "drop_shadow", "params": {"offset": 10, "angle": 135, "softness": 5, "opacity": 0.0}, "enabled": True}
        ])
        np.testing.assert_array_equal(result, mid_grey_frame)

    def test_shadow_output_clamped(self, mid_grey_frame):
        result = apply_numpy_effects(mid_grey_frame, [
            {"type": "drop_shadow", "params": {"offset": 50, "angle": 45, "softness": 20, "opacity": 1.0}, "enabled": True}
        ])
        assert result.min() >= 0.0
        assert result.max() <= 1.0


class TestDistortEffect:
    def test_distort_identity_noop(self, mid_grey_frame):
        """Default corners (identity) should leave frame unchanged."""
        result = apply_numpy_effects(mid_grey_frame, [
            {"type": "distort", "params": {
                "tl_x": 0.0, "tl_y": 0.0, "tr_x": 1.0, "tr_y": 0.0,
                "bl_x": 0.0, "bl_y": 1.0, "br_x": 1.0, "br_y": 1.0,
            }, "enabled": True}
        ])
        np.testing.assert_array_equal(result, mid_grey_frame)

    def test_distort_modifies_frame(self, gradient_frame):
        """Non-identity corners should warp the frame."""
        result = apply_numpy_effects(gradient_frame, [
            {"type": "distort", "params": {
                "tl_x": 0.1, "tl_y": 0.1, "tr_x": 0.9, "tr_y": 0.05,
                "bl_x": 0.05, "bl_y": 0.95, "br_x": 0.95, "br_y": 0.9,
            }, "enabled": True}
        ])
        assert not np.allclose(result, gradient_frame)
        assert result.shape == gradient_frame.shape

    def test_distort_output_valid(self, gradient_frame):
        result = apply_numpy_effects(gradient_frame, [
            {"type": "distort", "params": {
                "tl_x": 0.2, "tl_y": 0.2, "tr_x": 0.8, "tr_y": 0.1,
                "bl_x": 0.1, "bl_y": 0.9, "br_x": 0.9, "br_y": 0.8,
            }, "enabled": True}
        ])
        assert result.min() >= 0.0
        assert result.max() <= 1.0


class TestMotionBlurEffect:
    def test_blur_smooths_gradient(self, gradient_frame):
        result = apply_numpy_effects(gradient_frame, [
            {"type": "motion_blur", "params": {"amount": 20}, "enabled": True}
        ])
        # Motion blur reduces sharp transitions
        orig_diff = np.abs(np.diff(gradient_frame[:, :, 0], axis=1)).mean()
        blur_diff = np.abs(np.diff(result[:, :, 0], axis=1)).mean()
        assert blur_diff < orig_diff

    def test_blur_zero_amount_noop(self, mid_grey_frame):
        result = apply_numpy_effects(mid_grey_frame, [
            {"type": "motion_blur", "params": {"amount": 0}, "enabled": True}
        ])
        np.testing.assert_array_equal(result, mid_grey_frame)

    def test_blur_preserves_shape(self, gradient_frame):
        result = apply_numpy_effects(gradient_frame, [
            {"type": "motion_blur", "params": {"amount": 30}, "enabled": True}
        ])
        assert result.shape == gradient_frame.shape
        assert result.min() >= 0.0
        assert result.max() <= 1.0


# ---------------------------------------------------------------------------
# JPEG encode tests
# ---------------------------------------------------------------------------

class TestJpegEncode:
    def test_encode_produces_bytes(self, rgb_frame_uint8):
        jpeg = encode_preview_jpeg(rgb_frame_uint8)
        assert jpeg is not None
        assert len(jpeg) > 100
        # JPEG magic bytes
        assert jpeg[:2] == b'\xff\xd8'

    def test_quality_affects_size(self):
        """Quality parameter should affect JPEG file size (noisy frame)."""
        # Use random noise to ensure quality matters
        rng = np.random.RandomState(42)
        noisy = rng.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        jpeg_low = encode_preview_jpeg(noisy, quality=10)
        jpeg_high = encode_preview_jpeg(noisy, quality=95)
        assert jpeg_low is not None and jpeg_high is not None
        assert len(jpeg_high) > len(jpeg_low)


# ---------------------------------------------------------------------------
# Integration check
# ---------------------------------------------------------------------------

class TestDecoderInfo:
    def test_pyav_detection(self):
        """Just verify we correctly detect PyAV availability."""
        assert isinstance(HAS_PYAV, bool)
