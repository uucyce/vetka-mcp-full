"""
MARKER_B18 — Tests for cut_color_pipeline.py

Tests camera log decode (builtin numpy curves), .cube LUT parser,
trilinear interpolation, and full pipeline integration.

@task: tb_1773995016_3
"""
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pytest

from src.services.cut_color_pipeline import (
    decode_log,
    list_log_profiles,
    LUT3D,
    read_lut,
    apply_color_pipeline,
    import_lut,
    list_project_luts,
    CAMERA_LOG_PROFILES,
    _decode_vlog,
    _decode_slog3,
    _decode_logc3,
    _decode_clog3,
    rgb_to_hsl,
    hsl_to_rgb,
    build_hsl_mask,
    apply_secondary_correction,
    write_secondary_lut_cube,
    _decode_srgb,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def gradient_frame_float():
    """256x4 horizontal gradient [0..1] in R, const G=0.5, B=0.3."""
    frame = np.zeros((4, 256, 3), dtype=np.float32)
    for x in range(256):
        frame[:, x, 0] = x / 255.0
        frame[:, x, 1] = 0.5
        frame[:, x, 2] = 0.3
    return frame


@pytest.fixture
def gradient_frame_uint8():
    """Same gradient but uint8."""
    frame = np.zeros((4, 256, 3), dtype=np.uint8)
    for x in range(256):
        frame[:, x, 0] = x
        frame[:, x, 1] = 128
        frame[:, x, 2] = 76
    return frame


@pytest.fixture
def identity_cube_file(tmp_path):
    """Create a minimal 2x2x2 identity .cube LUT."""
    path = tmp_path / "identity.cube"
    lines = [
        'TITLE "Identity LUT"',
        "LUT_3D_SIZE 2",
        "0.0 0.0 0.0",
        "1.0 0.0 0.0",
        "0.0 1.0 0.0",
        "1.0 1.0 0.0",
        "0.0 0.0 1.0",
        "1.0 0.0 1.0",
        "0.0 1.0 1.0",
        "1.0 1.0 1.0",
    ]
    path.write_text("\n".join(lines))
    return str(path)


@pytest.fixture
def warm_cube_file(tmp_path):
    """Create a 2x2x2 warm (reddish) .cube LUT."""
    path = tmp_path / "warm.cube"
    lines = [
        'TITLE "Warm LUT"',
        "LUT_3D_SIZE 2",
        # Shift all values towards red
        "0.1 0.0 0.0",
        "1.0 0.0 0.0",
        "0.1 0.9 0.0",
        "1.0 0.9 0.0",
        "0.1 0.0 0.9",
        "1.0 0.0 0.9",
        "0.1 0.9 0.9",
        "1.0 0.9 0.9",
    ]
    path.write_text("\n".join(lines))
    return str(path)


# ---------------------------------------------------------------------------
# Log decode tests
# ---------------------------------------------------------------------------

class TestLogDecode:
    def test_vlog_monotonic(self, gradient_frame_float):
        """V-Log decode should be monotonically increasing."""
        result = _decode_vlog(gradient_frame_float[:, :, 0])
        # Check monotonic (or at least non-decreasing)
        diffs = np.diff(result[0, :])
        assert np.all(diffs >= -1e-6), "V-Log decode should be non-decreasing"

    def test_slog3_monotonic(self, gradient_frame_float):
        result = _decode_slog3(gradient_frame_float[:, :, 0])
        diffs = np.diff(result[0, :])
        assert np.all(diffs >= -1e-6), "S-Log3 decode should be non-decreasing"

    def test_logc3_monotonic(self, gradient_frame_float):
        result = _decode_logc3(gradient_frame_float[:, :, 0])
        diffs = np.diff(result[0, :])
        assert np.all(diffs >= -1e-6), "LogC3 decode should be non-decreasing"

    def test_clog3_range(self, gradient_frame_float):
        result = _decode_clog3(gradient_frame_float[:, :, 0])
        assert result.min() >= 0, "Output should be >= 0"
        assert result.max() <= 1, "Output should be <= 1"

    def test_srgb_black_stays_black(self):
        black = np.zeros((1, 1, 3), dtype=np.float32)
        result = _decode_srgb(black)
        assert np.allclose(result, 0, atol=1e-6)

    def test_srgb_white_stays_white(self):
        white = np.ones((1, 1, 3), dtype=np.float32)
        result = _decode_srgb(white)
        assert np.allclose(result, 1, atol=1e-3)

    def test_decode_log_by_name(self, gradient_frame_float):
        """decode_log() should accept various name formats."""
        result = decode_log(gradient_frame_float, "V-Log")
        assert result.shape == gradient_frame_float.shape

        result2 = decode_log(gradient_frame_float, "slog3")
        assert result2.shape == gradient_frame_float.shape

    def test_unknown_profile_passthrough(self, gradient_frame_float):
        """Unknown profile should return input unchanged."""
        result = decode_log(gradient_frame_float, "NonExistentProfile")
        np.testing.assert_array_equal(result, gradient_frame_float)


class TestLogProfiles:
    def test_list_profiles(self):
        profiles = list_log_profiles()
        assert len(profiles) >= 5
        names = {p["name"] for p in profiles}
        assert "V-Log" in names
        assert "S-Log3" in names
        assert "ARRI LogC3" in names


# ---------------------------------------------------------------------------
# LUT tests
# ---------------------------------------------------------------------------

class TestLUT:
    def test_parse_identity_cube(self, identity_cube_file):
        lut = LUT3D.from_cube_file(identity_cube_file)
        assert lut.title == "Identity LUT"
        assert lut.size == 2
        assert lut.table.shape == (2, 2, 2, 3)

    def test_identity_lut_preserves_input(self, identity_cube_file, gradient_frame_float):
        lut = LUT3D.from_cube_file(identity_cube_file)
        result = lut.apply(gradient_frame_float)
        # Identity LUT should preserve input (within interpolation tolerance)
        np.testing.assert_allclose(result, gradient_frame_float, atol=0.02)

    def test_warm_lut_shifts_colors(self, warm_cube_file, gradient_frame_float):
        lut = LUT3D.from_cube_file(warm_cube_file)
        result = lut.apply(gradient_frame_float)
        # Warm LUT should not be identical to input
        assert not np.allclose(result, gradient_frame_float, atol=0.05)

    def test_lut_output_range(self, warm_cube_file, gradient_frame_float):
        lut = LUT3D.from_cube_file(warm_cube_file)
        result = lut.apply(gradient_frame_float)
        assert result.min() >= 0
        assert result.max() <= 1

    def test_read_lut_nonexistent(self):
        assert read_lut("/nonexistent/path.cube") is None

    def test_read_lut_cube(self, identity_cube_file):
        lut = read_lut(identity_cube_file)
        assert lut is not None
        assert lut.size == 2


# ---------------------------------------------------------------------------
# LUT storage tests
# ---------------------------------------------------------------------------

class TestLUTStorage:
    def test_import_and_list(self, identity_cube_file, tmp_path):
        sandbox = str(tmp_path / "sandbox")
        os.makedirs(sandbox, exist_ok=True)

        result = import_lut(sandbox, identity_cube_file)
        assert result["success"] is True
        assert result["lut_name"] == "identity"
        assert result["lut_size"] == 2

        luts = list_project_luts(sandbox)
        assert len(luts) == 1
        assert luts[0]["name"] == "identity"

    def test_import_nonexistent(self, tmp_path):
        result = import_lut(str(tmp_path), "/no/such/file.cube")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# Full pipeline tests
# ---------------------------------------------------------------------------

class TestColorPipeline:
    def test_pipeline_no_ops(self, gradient_frame_uint8):
        """Pipeline with no log/lut should return input unchanged."""
        result = apply_color_pipeline(gradient_frame_uint8)
        np.testing.assert_array_equal(result, gradient_frame_uint8)

    def test_pipeline_log_decode(self, gradient_frame_uint8):
        """Pipeline with log decode should change values."""
        result = apply_color_pipeline(gradient_frame_uint8, log_profile="V-Log")
        assert result.dtype == np.uint8
        # V-Log decode will change values
        assert not np.array_equal(result, gradient_frame_uint8)

    def test_pipeline_lut(self, gradient_frame_uint8, warm_cube_file):
        """Pipeline with LUT should change values."""
        result = apply_color_pipeline(gradient_frame_uint8, lut_path=warm_cube_file)
        assert result.dtype == np.uint8
        assert not np.array_equal(result, gradient_frame_uint8)

    def test_pipeline_log_plus_lut(self, gradient_frame_uint8, identity_cube_file):
        """Pipeline with both log decode and identity LUT."""
        result = apply_color_pipeline(
            gradient_frame_uint8,
            log_profile="sRGB",
            lut_path=identity_cube_file,
        )
        assert result.dtype == np.uint8
        assert result.shape == gradient_frame_uint8.shape


# ─────────────────────────────────────────────────────────────────────────────
# MARKER_SEC_COLOR: Secondary Color Correction tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSecondaryColor:
    """HSL qualifier + apply_secondary_correction + LUT generation."""

    def test_rgb_hsl_round_trip(self):
        """RGB → HSL → RGB should be identity (within float32 precision)."""
        rng = np.random.default_rng(42)
        frame = rng.random((4, 4, 3)).astype(np.float32)
        hsl = rgb_to_hsl(frame)
        back = hsl_to_rgb(hsl)
        assert np.allclose(frame, back, atol=1e-5), "Round-trip error too large"

    def test_known_hue_values(self):
        """Pure red/green/blue map to expected hue values."""
        red = np.array([[[1, 0, 0]]], dtype=np.float32)
        green = np.array([[[0, 1, 0]]], dtype=np.float32)
        blue = np.array([[[0, 0, 1]]], dtype=np.float32)
        assert abs(rgb_to_hsl(red)[0, 0, 0] * 360 - 0) < 1e-3
        assert abs(rgb_to_hsl(green)[0, 0, 0] * 360 - 120) < 1e-3
        assert abs(rgb_to_hsl(blue)[0, 0, 0] * 360 - 240) < 1e-3

    def test_mask_selects_green(self):
        """HSL mask fully selects pure green at hue_center=120."""
        green = np.array([[[0, 1, 0]]], dtype=np.float32)
        mask = build_hsl_mask(rgb_to_hsl(green), hue_center=120, hue_width=30, softness=0.0)
        assert mask[0, 0] > 0.99

    def test_mask_excludes_blue(self):
        """HSL mask excludes pure blue when qualifying for green (120°)."""
        blue = np.array([[[0, 0, 1]]], dtype=np.float32)
        mask = build_hsl_mask(rgb_to_hsl(blue), hue_center=120, hue_width=30, softness=0.0)
        assert mask[0, 0] < 0.01

    def test_mask_excludes_grey(self):
        """Grey (zero saturation) excluded by non-zero sat_min qualifier."""
        grey = np.array([[[0.5, 0.5, 0.5]]], dtype=np.float32)
        mask = build_hsl_mask(rgb_to_hsl(grey), hue_center=120, hue_width=60, sat_min=0.2, softness=0.0)
        assert mask[0, 0] < 0.01

    def test_mask_soft_falloff(self):
        """Soft edges produce values between 0 and 1 near boundaries."""
        # pixel at exact hue boundary
        # Hue 150° is exactly at the edge of [120 ± 30]
        r, g, b = 0.0, 0.5, 0.5  # hue ≈ 180 — just outside with soft fade
        pix = np.array([[[r, g, b]]], dtype=np.float32)
        mask_hard = build_hsl_mask(rgb_to_hsl(pix), hue_center=120, hue_width=30, softness=0.0)
        mask_soft = build_hsl_mask(rgb_to_hsl(pix), hue_center=120, hue_width=30, softness=0.5)
        # With softness, boundary pixel should have higher mask value
        assert mask_soft[0, 0] >= mask_hard[0, 0]

    def test_apply_correction_hue_shift(self):
        """Hue shift moves the hue of selected color."""
        green_frame = np.array([[[0.0, 0.8, 0.1]]], dtype=np.float32)
        qualifier = dict(hue_center=120, hue_width=40, sat_min=0, sat_max=1, luma_min=0, luma_max=1, softness=0.1)
        correction = dict(hue_shift=90, saturation=1.0, exposure=0.0)
        result = apply_secondary_correction(green_frame, qualifier, correction)
        assert not np.allclose(green_frame, result, atol=0.01), "Hue shift should change frame"

    def test_apply_correction_neutral_unchanged(self):
        """Pixels outside qualifier range are unchanged."""
        grey = np.array([[[0.5, 0.5, 0.5]]], dtype=np.float32)
        qualifier = dict(hue_center=120, hue_width=30, sat_min=0.3, sat_max=1, luma_min=0, luma_max=1, softness=0.0)
        correction = dict(hue_shift=180, saturation=0.1, exposure=-2.0)
        result = apply_secondary_correction(grey, qualifier, correction)
        assert np.allclose(grey, result, atol=1e-4), "Grey (s=0) outside sat qualifier should be unchanged"

    def test_apply_correction_output_in_range(self):
        """Output is always in [0, 1]."""
        rng = np.random.default_rng(7)
        frame = rng.random((8, 8, 3)).astype(np.float32)
        qualifier = dict(hue_center=60, hue_width=45, sat_min=0, sat_max=1, luma_min=0, luma_max=1, softness=0.2)
        correction = dict(hue_shift=120, saturation=2.0, exposure=2.0)
        result = apply_secondary_correction(frame, qualifier, correction)
        assert result.min() >= 0.0 and result.max() <= 1.0

    def test_write_secondary_lut_cube_trivial_returns_none(self):
        """Identity correction returns None (no LUT needed)."""
        path = write_secondary_lut_cube({}, dict(hue_shift=0, saturation=1.0, exposure=0.0), size=5)
        assert path is None

    def test_write_secondary_lut_cube_creates_valid_cube(self):
        """Non-trivial correction produces a valid .cube file."""
        qualifier = dict(hue_center=120, hue_width=30, sat_min=0, sat_max=1, luma_min=0, luma_max=1, softness=0.1)
        correction = dict(hue_shift=45, saturation=0.5, exposure=-0.5)
        path = write_secondary_lut_cube(qualifier, correction, size=5)
        assert path is not None
        assert path.endswith(".cube")
        lines = open(path).readlines()
        # 5^3 = 125 data lines + header lines
        data_lines = [l for l in lines if l.strip() and not l.startswith("TITLE") and not l.startswith("LUT_3D")]
        assert len(data_lines) == 5 ** 3
        os.unlink(path)
