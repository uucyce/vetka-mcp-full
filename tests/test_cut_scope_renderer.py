"""
MARKER_SCOPES — Tests for cut_scope_renderer.py

Tests scope computation accuracy with synthetic numpy frames.
No FFmpeg needed — tests feed frames directly to compute_* functions.

@task: tb_1773997178_1
"""
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pytest

from src.services.cut_scope_renderer import (
    compute_histogram,
    compute_waveform,
    compute_vectorscope,
    analyze_frame_scopes,
    _cache_key,
    _scope_cache,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def solid_red_frame():
    """100x100 solid red frame (255, 0, 0)."""
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    frame[:, :, 0] = 255  # R
    return frame


@pytest.fixture
def gradient_frame():
    """100x256 horizontal gradient (0..255 in R, constant G/B)."""
    frame = np.zeros((100, 256, 3), dtype=np.uint8)
    for x in range(256):
        frame[:, x, 0] = x  # R gradient
        frame[:, x, 1] = 128  # constant G
        frame[:, x, 2] = 64  # constant B
    return frame


@pytest.fixture
def neutral_grey_frame():
    """100x100 neutral grey (128, 128, 128)."""
    frame = np.full((100, 100, 3), 128, dtype=np.uint8)
    return frame


# ---------------------------------------------------------------------------
# Histogram tests
# ---------------------------------------------------------------------------

class TestHistogram:
    def test_solid_red_histogram(self, solid_red_frame):
        hist = compute_histogram(solid_red_frame)
        assert "r" in hist and "g" in hist and "b" in hist
        assert len(hist["r"]) == 256
        # All pixels are R=255 → bin 255 should have 10000 hits
        assert hist["r"][255] == 10000
        assert hist["r"][0] == 0
        # All pixels are G=0 → bin 0 should have 10000 hits
        assert hist["g"][0] == 10000
        assert hist["b"][0] == 10000

    def test_gradient_histogram(self, gradient_frame):
        hist = compute_histogram(gradient_frame)
        # R channel: 100 pixels per value (100 rows × 1 column per value)
        assert hist["r"][0] == 100
        assert hist["r"][128] == 100
        assert hist["r"][255] == 100
        # G channel: all 128 → single spike
        assert hist["g"][128] == 100 * 256

    def test_histogram_length(self, solid_red_frame):
        hist = compute_histogram(solid_red_frame)
        for ch in ["r", "g", "b"]:
            assert len(hist[ch]) == 256
            assert all(isinstance(v, int) for v in hist[ch])


# ---------------------------------------------------------------------------
# Waveform tests
# ---------------------------------------------------------------------------

class TestWaveform:
    def test_waveform_shape(self, solid_red_frame):
        wf = compute_waveform(solid_red_frame, scope_w=64, scope_h=64)
        assert len(wf) == 64  # height
        assert len(wf[0]) == 64  # width

    def test_neutral_grey_waveform(self, neutral_grey_frame):
        """Neutral grey should produce a single horizontal band at ~50% luma."""
        wf = compute_waveform(neutral_grey_frame, scope_w=64, scope_h=256)
        wf_arr = np.array(wf)
        # Grey (128,128,128) → luma ≈ 128 → should appear at ~50% height
        # Find row with maximum total energy
        row_sums = wf_arr.sum(axis=1)
        peak_row = np.argmax(row_sums)
        # Peak should be roughly in the middle (row 128 in 256 scope = inverted → ~128)
        assert 100 < peak_row < 160, f"Peak row {peak_row} not in expected range"

    def test_waveform_nonzero(self, gradient_frame):
        """Gradient frame should produce non-trivial waveform."""
        wf = compute_waveform(gradient_frame, scope_w=128, scope_h=128)
        wf_arr = np.array(wf)
        assert wf_arr.max() > 0, "Waveform should have non-zero values"


# ---------------------------------------------------------------------------
# Vectorscope tests
# ---------------------------------------------------------------------------

class TestVectorscope:
    def test_vectorscope_shape(self, solid_red_frame):
        vs = compute_vectorscope(solid_red_frame, scope_size=128)
        assert len(vs) == 128
        assert len(vs[0]) == 128

    def test_neutral_grey_vectorscope(self, neutral_grey_frame):
        """Neutral grey has zero chroma → all energy at center."""
        vs = compute_vectorscope(neutral_grey_frame, scope_size=128)
        vs_arr = np.array(vs)
        # Center should have high value
        center = vs_arr[64, 64]
        assert center > 0, "Center of vectorscope should have energy for neutral grey"
        # Corners should be zero
        assert vs_arr[0, 0] == 0
        assert vs_arr[127, 127] == 0

    def test_saturated_frame_not_center(self, solid_red_frame):
        """Solid red is highly saturated → energy NOT at center."""
        vs = compute_vectorscope(solid_red_frame, scope_size=128)
        vs_arr = np.array(vs)
        # Find peak location
        peak_y, peak_x = np.unravel_index(vs_arr.argmax(), vs_arr.shape)
        # Peak should NOT be at exact center (64,64) for saturated red
        assert (peak_x, peak_y) != (64, 64), "Saturated red should not peak at center"


# ---------------------------------------------------------------------------
# Cache key tests
# ---------------------------------------------------------------------------

class TestCacheKey:
    def test_nearby_frames_same_key(self):
        """Frames within same cache bucket (0.08s) should hash to same key."""
        k1 = _cache_key("/video.mp4", 1.01)
        k2 = _cache_key("/video.mp4", 1.03)  # within same 0.08s bucket
        assert k1 == k2

    def test_distant_frames_different_key(self):
        k1 = _cache_key("/video.mp4", 1.0)
        k2 = _cache_key("/video.mp4", 2.0)
        assert k1 != k2

    def test_different_files_different_key(self):
        k1 = _cache_key("/a.mp4", 1.0)
        k2 = _cache_key("/b.mp4", 1.0)
        assert k1 != k2


# ---------------------------------------------------------------------------
# Integration: analyze_frame_scopes (without real video — tests error path)
# ---------------------------------------------------------------------------

class TestAnalyzeFrameScopes:
    def test_missing_file_returns_error(self):
        result = analyze_frame_scopes("/nonexistent/video.mp4", time_sec=0.0)
        assert result["success"] is False

    def test_invalid_scopes_filtered(self):
        """Invalid scope names should be filtered, not crash."""
        result = analyze_frame_scopes(
            "/nonexistent/video.mp4",
            scopes=["invalid_scope", "histogram"],
        )
        # Should fail due to missing file, not due to invalid scope name
        assert result["success"] is False
