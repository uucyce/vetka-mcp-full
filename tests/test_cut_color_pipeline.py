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
