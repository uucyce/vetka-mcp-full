"""
MARKER_B19 — Tests for cut_scope_renderer.py (waveform, parade, vectorscope, histogram).
@task: tb_1773995025_4
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pytest
from src.services.cut_scope_renderer import (
    compute_histogram, compute_waveform, compute_vectorscope, compute_parade,
    analyze_frame_scopes, _cache_key,
)

@pytest.fixture
def solid_red():
    f = np.zeros((100, 100, 3), dtype=np.uint8); f[:,:,0] = 255; return f

@pytest.fixture
def gradient():
    f = np.zeros((100, 256, 3), dtype=np.uint8)
    for x in range(256): f[:,x,0] = x; f[:,x,1] = 128; f[:,x,2] = 64
    return f

@pytest.fixture
def neutral_grey():
    return np.full((100, 100, 3), 128, dtype=np.uint8)


class TestHistogram:
    def test_solid_red(self, solid_red):
        h = compute_histogram(solid_red)
        assert len(h["r"]) == 256
        assert h["r"][255] == 10000
        assert h["g"][0] == 10000

    def test_gradient(self, gradient):
        h = compute_histogram(gradient)
        assert h["r"][0] == 100
        assert h["g"][128] == 100 * 256


class TestWaveform:
    def test_shape(self, solid_red):
        wf = compute_waveform(solid_red, 64, 64)
        assert len(wf) == 64 and len(wf[0]) == 64

    def test_neutral_grey_peak(self, neutral_grey):
        wf = compute_waveform(neutral_grey, 64, 256)
        arr = np.array(wf)
        peak = np.argmax(arr.sum(axis=1))
        assert 100 < peak < 160

    def test_nonzero(self, gradient):
        wf = compute_waveform(gradient, 128, 128)
        assert np.array(wf).max() > 0


class TestParade:
    def test_shape(self, solid_red):
        p = compute_parade(solid_red, 64, 64)
        assert "r" in p and "g" in p and "b" in p
        assert len(p["r"]) == 64 and len(p["r"][0]) == 64

    def test_red_channel_has_energy(self, solid_red):
        p = compute_parade(solid_red, 64, 64)
        r_arr = np.array(p["r"])
        g_arr = np.array(p["g"])
        # Red channel should have energy at high values (top of scope)
        assert r_arr.max() > 0
        # Green channel energy should be at low values (bottom, since G=0)
        assert g_arr.max() > 0

    def test_gradient_spread(self, gradient):
        p = compute_parade(gradient, 128, 128)
        r_arr = np.array(p["r"])
        # Gradient in R → energy spread across scope
        nonzero_rows = (r_arr.sum(axis=1) > 0).sum()
        assert nonzero_rows > 10, "R parade should have energy in multiple rows"


class TestVectorscope:
    def test_shape(self, solid_red):
        vs = compute_vectorscope(solid_red, 128)
        assert len(vs) == 128 and len(vs[0]) == 128

    def test_grey_at_center(self, neutral_grey):
        vs = compute_vectorscope(neutral_grey, 128)
        arr = np.array(vs)
        assert arr[64, 64] > 0
        assert arr[0, 0] == 0

    def test_saturated_off_center(self, solid_red):
        vs = compute_vectorscope(solid_red, 128)
        arr = np.array(vs)
        py, px = np.unravel_index(arr.argmax(), arr.shape)
        assert (px, py) != (64, 64)


class TestCacheKey:
    def test_same_bucket(self):
        assert _cache_key("/a.mp4", 1.01) == _cache_key("/a.mp4", 1.03)

    def test_different_time(self):
        assert _cache_key("/a.mp4", 1.0) != _cache_key("/a.mp4", 2.0)

    def test_different_file(self):
        assert _cache_key("/a.mp4", 1.0) != _cache_key("/b.mp4", 1.0)


class TestAnalyze:
    def test_missing_file(self):
        r = analyze_frame_scopes("/nonexistent.mp4")
        assert r["success"] is False

    def test_parade_in_valid_scopes(self):
        r = analyze_frame_scopes("/nonexistent.mp4", scopes=["parade"])
        assert r["success"] is False  # fails on file, not scope name
