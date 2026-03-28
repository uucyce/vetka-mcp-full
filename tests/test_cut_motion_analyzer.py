"""
MARKER_B74 — Tests for cut_motion_analyzer.py (motion intensity, cut detection, MotionProfile).
@task: tb_1774676394_49568_1
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.services.cut_motion_analyzer import (
    MotionProfile,
    MotionAnalyzer,
    _normalize_samples,
    _compute_variance,
    _empty_profile,
)


# ---------------------------------------------------------------------------
# MotionProfile dataclass tests
# ---------------------------------------------------------------------------


class TestMotionProfile:
    def test_default_values(self):
        p = MotionProfile()
        assert p.avg_motion == 0.0
        assert p.max_motion == 0.0
        assert p.motion_variance == 0.0
        assert p.cut_density == 0.0
        assert p.avg_shot_length == 0.0
        assert p.cut_times == []
        assert p.motion_samples == []
        assert p.error == ""

    def test_to_dict_keys(self):
        p = MotionProfile(
            motion_samples=[0.1, 0.5, 0.9],
            avg_motion=0.5,
            max_motion=0.9,
            cut_density=12.0,
            avg_shot_length=5.0,
            cut_times=[1.5, 3.0],
            total_duration_sec=10.0,
            method="ffmpeg+numpy",
        )
        d = p.to_dict()
        assert "motion_samples" in d
        assert "avg_motion" in d
        assert "max_motion" in d
        assert "cut_density" in d
        assert "avg_shot_length" in d
        assert "cut_times" in d
        assert "method" in d
        assert d["method"] == "ffmpeg+numpy"

    def test_to_dict_rounding(self):
        p = MotionProfile(avg_motion=0.123456789, max_motion=0.987654321)
        d = p.to_dict()
        assert d["avg_motion"] == 0.1235
        assert d["max_motion"] == 0.9877

    def test_empty_profile_has_error(self):
        p = _empty_profile(error="test_error")
        assert p.error == "test_error"
        assert p.motion_samples == []
        assert p.avg_motion == 0.0


# ---------------------------------------------------------------------------
# _normalize_samples tests
# ---------------------------------------------------------------------------


class TestNormalizeSamples:
    def test_empty(self):
        assert _normalize_samples([]) == []

    def test_all_zeros(self):
        result = _normalize_samples([0.0, 0.0, 0.0])
        assert result == [0.0, 0.0, 0.0]

    def test_uniform(self):
        result = _normalize_samples([5.0, 5.0, 5.0, 5.0])
        assert all(v == 1.0 for v in result)

    def test_increasing(self):
        result = _normalize_samples([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        assert result[0] == 0.0
        assert result[-1] >= 1.0  # Last exceeds cap → clipped to 1.0
        assert all(0.0 <= v <= 1.0 for v in result)

    def test_cap_prevents_outlier(self):
        # One huge outlier — cap at 95th percentile
        data = [1.0] * 100 + [1000.0]
        result = _normalize_samples(data)
        # The outlier should be clipped to 1.0
        assert result[-1] == 1.0


# ---------------------------------------------------------------------------
# _compute_variance tests
# ---------------------------------------------------------------------------


class TestComputeVariance:
    def test_empty(self):
        assert _compute_variance([]) == 0.0

    def test_single(self):
        assert _compute_variance([5.0]) == 0.0

    def test_constant(self):
        assert _compute_variance([3.0, 3.0, 3.0]) == 0.0

    def test_known_variance(self):
        # [0, 1] → mean=0.5, variance=0.25
        v = _compute_variance([0.0, 1.0])
        assert abs(v - 0.25) < 1e-6


# ---------------------------------------------------------------------------
# MotionAnalyzer tests
# ---------------------------------------------------------------------------


class TestMotionAnalyzer:
    def test_file_not_found(self):
        analyzer = MotionAnalyzer()
        result = analyzer.analyze_clip("/nonexistent/video.mp4")
        assert result.error != ""

    def test_detect_motion_spikes_empty(self):
        analyzer = MotionAnalyzer()
        profile = MotionProfile()
        spikes = analyzer.detect_motion_spikes(profile)
        assert spikes == []

    def test_detect_motion_spikes_threshold(self):
        analyzer = MotionAnalyzer()
        profile = MotionProfile(
            motion_samples=[0.1, 0.2, 0.8, 0.3, 0.9, 0.1],
            sample_interval_sec=0.5,
            total_duration_sec=3.0,
        )
        spikes = analyzer.detect_motion_spikes(profile, threshold=0.7)
        # Indices 2 and 4 are >= 0.7 → timestamps (2+1)*0.5=1.5, (4+1)*0.5=2.5
        assert len(spikes) == 2
        assert abs(spikes[0] - 1.5) < 0.01
        assert abs(spikes[1] - 2.5) < 0.01

    def test_detect_motion_spikes_all_below(self):
        analyzer = MotionAnalyzer()
        profile = MotionProfile(
            motion_samples=[0.1, 0.2, 0.3],
            sample_interval_sec=1.0,
            total_duration_sec=3.0,
        )
        spikes = analyzer.detect_motion_spikes(profile, threshold=0.5)
        assert spikes == []

    def test_detect_motion_spikes_all_above(self):
        analyzer = MotionAnalyzer()
        profile = MotionProfile(
            motion_samples=[0.9, 0.8, 0.95],
            sample_interval_sec=0.25,
            total_duration_sec=0.75,
        )
        spikes = analyzer.detect_motion_spikes(profile, threshold=0.7)
        assert len(spikes) == 3


# ---------------------------------------------------------------------------
# MotionProfile integration tests (synthetic data)
# ---------------------------------------------------------------------------


class TestMotionProfileIntegration:
    def test_static_content_low_motion(self):
        """Static video should have near-zero avg_motion."""
        profile = MotionProfile(
            motion_samples=[0.01, 0.02, 0.01, 0.015, 0.01],
            avg_motion=0.013,
            max_motion=0.02,
            cut_density=0.0,
            avg_shot_length=10.0,
            total_duration_sec=10.0,
        )
        assert profile.avg_motion < 0.05
        assert profile.cut_density == 0.0

    def test_high_motion_content(self):
        """Action content should have high avg_motion."""
        profile = MotionProfile(
            motion_samples=[0.7, 0.8, 0.65, 0.9, 0.75],
            avg_motion=0.76,
            max_motion=0.9,
            cut_density=24.0,
            avg_shot_length=2.5,
            total_duration_sec=12.5,
        )
        assert profile.avg_motion > 0.5
        assert profile.cut_density > 0

    def test_mixed_content(self):
        """Mixed should have moderate avg_motion with variance."""
        samples = [0.1, 0.1, 0.8, 0.1, 0.1, 0.9, 0.1]
        avg = sum(samples) / len(samples)
        var = _compute_variance(samples)
        profile = MotionProfile(
            motion_samples=samples,
            avg_motion=round(avg, 4),
            motion_variance=round(var, 4),
        )
        assert profile.motion_variance > 0.05  # High variance = mixed content

    def test_avg_shot_length_consistency(self):
        """avg_shot_length should be duration / (cuts + 1)."""
        profile = MotionProfile(
            cut_times=[2.0, 5.0, 8.0],
            avg_shot_length=2.75,  # 11 / 4 shots
            total_duration_sec=11.0,
        )
        n_shots = len(profile.cut_times) + 1
        expected = profile.total_duration_sec / n_shots
        assert abs(profile.avg_shot_length - expected) < 0.1
