"""
MARKER_B74 — Tests for cut_motion_analyzer.py

Verifies:
  - MotionProfile dataclass structure and field types
  - Graceful degradation when cv2 is unavailable
  - Normalization always produces values in [0.0, 1.0]
  - Spike detection logic correctness
  - to_dict() serialization

@task: tb_1774410751_1
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch, MagicMock

from src.services.cut_motion_analyzer import (
    MotionProfile,
    MotionAnalyzer,
    _normalize_samples,
    _compute_variance,
    _empty_profile,
    get_motion_analyzer,
)


# ---------------------------------------------------------------------------
# Tests: MotionProfile dataclass
# ---------------------------------------------------------------------------


class TestMotionProfile:
    def test_default_fields(self):
        """MotionProfile initializes with correct defaults."""
        p = MotionProfile()
        assert p.motion_samples == []
        assert p.avg_motion == 0.0
        assert p.max_motion == 0.0
        assert p.motion_variance == 0.0
        assert p.cut_density == 0.0
        assert p.sample_interval_sec == 0.0
        assert p.total_duration_sec == 0.0
        assert p.error == ""

    def test_to_dict_keys(self):
        """to_dict() returns all required keys."""
        p = MotionProfile(
            motion_samples=[0.1, 0.5, 0.8],
            avg_motion=0.467,
            max_motion=0.8,
            motion_variance=0.079,
            cut_density=1.5,
            sample_interval_sec=0.208,
            total_duration_sec=10.0,
        )
        d = p.to_dict()
        required_keys = {
            "motion_samples", "avg_motion", "max_motion",
            "motion_variance", "cut_density", "sample_interval_sec",
            "total_duration_sec", "error",
        }
        assert required_keys.issubset(d.keys()), f"Missing keys: {required_keys - d.keys()}"

    def test_to_dict_values(self):
        """to_dict() serializes values correctly."""
        p = MotionProfile(
            motion_samples=[0.1, 0.9],
            avg_motion=0.5,
            max_motion=0.9,
            motion_variance=0.16,
            cut_density=6.0,
            sample_interval_sec=0.2083,
            total_duration_sec=30.5,
        )
        d = p.to_dict()
        assert d["motion_samples"] == [0.1, 0.9]
        assert d["avg_motion"] == 0.5
        assert d["max_motion"] == 0.9
        assert d["total_duration_sec"] == 30.5

    def test_empty_profile_helper(self):
        """_empty_profile() returns a profile with the given error string."""
        p = _empty_profile("cv2_unavailable")
        assert p.error == "cv2_unavailable"
        assert p.motion_samples == []
        assert p.avg_motion == 0.0


# ---------------------------------------------------------------------------
# Tests: Normalization
# ---------------------------------------------------------------------------


class TestNormalizeSamples:
    def test_all_zero_input(self):
        """All-zero input stays all-zero."""
        result = _normalize_samples([0.0, 0.0, 0.0])
        assert result == [0.0, 0.0, 0.0]

    def test_empty_input(self):
        """Empty input returns empty list."""
        assert _normalize_samples([]) == []

    def test_values_clamped_to_0_1(self):
        """All output values are in [0.0, 1.0]."""
        raw = [0.0, 1.5, 5.0, 10.0, 0.3, 8.0]
        normalized = _normalize_samples(raw)
        for v in normalized:
            assert 0.0 <= v <= 1.0, f"Value {v} out of [0, 1]"

    def test_maximum_is_1_0(self):
        """The maximum normalized value should be 1.0 (from 95th percentile cap)."""
        raw = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        normalized = _normalize_samples(raw)
        # At least one value should be 1.0 (the max non-outlier)
        assert max(normalized) == 1.0

    def test_monotone_ordering_preserved(self):
        """Monotonically increasing input → monotonically increasing output."""
        raw = [1.0, 2.0, 3.0, 4.0, 5.0]
        normalized = _normalize_samples(raw)
        for i in range(len(normalized) - 1):
            assert normalized[i] <= normalized[i + 1]

    def test_single_value(self):
        """Single non-zero value normalizes to 1.0."""
        result = _normalize_samples([3.5])
        assert result == [1.0]


# ---------------------------------------------------------------------------
# Tests: Variance
# ---------------------------------------------------------------------------


class TestComputeVariance:
    def test_constant_input_zero_variance(self):
        """All-same values → zero variance."""
        assert _compute_variance([0.5, 0.5, 0.5]) == pytest.approx(0.0)

    def test_empty_input(self):
        """Empty input returns 0.0."""
        assert _compute_variance([]) == 0.0

    def test_single_value(self):
        """Single value → 0.0 variance."""
        assert _compute_variance([0.7]) == 0.0

    def test_high_variance(self):
        """Alternating extremes → high variance."""
        result = _compute_variance([0.0, 1.0, 0.0, 1.0])
        assert result > 0.2


# ---------------------------------------------------------------------------
# Tests: Graceful degradation (cv2 unavailable)
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    def test_cv2_unavailable_returns_stub(self, tmp_path):
        """When cv2 is not available, analyze_clip returns stub profile with error."""
        # Create a dummy video file (just to pass the file-exists check we'll mock)
        dummy = tmp_path / "test.mp4"
        dummy.write_bytes(b"dummy")

        analyzer = MotionAnalyzer()

        with patch("src.services.cut_motion_analyzer.HAS_CV2", False):
            profile = analyzer.analyze_clip(str(dummy))

        assert profile.error == "cv2_unavailable"
        assert profile.motion_samples == []
        assert profile.avg_motion == 0.0

    def test_file_not_found_returns_error_profile(self):
        """Non-existent path returns error profile."""
        analyzer = MotionAnalyzer()

        with patch("src.services.cut_motion_analyzer.HAS_CV2", True):
            profile = analyzer.analyze_clip("/nonexistent/path/video.mp4")

        assert profile.error == "file_not_found"
        assert profile.motion_samples == []

    def test_unopenable_video_returns_error(self, tmp_path):
        """File exists but can't be opened by cv2 → error profile."""
        dummy = tmp_path / "broken.mp4"
        dummy.write_bytes(b"not a real video")

        analyzer = MotionAnalyzer()

        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False

        with patch("src.services.cut_motion_analyzer.HAS_CV2", True), \
             patch("src.services.cut_motion_analyzer.cv2") as mock_cv2:
            mock_cv2.VideoCapture.return_value = mock_cap
            profile = analyzer.analyze_clip(str(dummy))

        assert profile.error == "cannot_open_video"


# ---------------------------------------------------------------------------
# Tests: Spike detection
# ---------------------------------------------------------------------------


class TestDetectMotionSpikes:
    def setup_method(self):
        self.analyzer = MotionAnalyzer()

    def _make_profile(self, samples, interval=0.2, duration=10.0):
        return MotionProfile(
            motion_samples=samples,
            sample_interval_sec=interval,
            total_duration_sec=duration,
        )

    def test_no_spikes_below_threshold(self):
        """All samples below threshold → no spikes."""
        p = self._make_profile([0.1, 0.2, 0.3, 0.5, 0.6])
        spikes = self.analyzer.detect_motion_spikes(p, threshold=0.7)
        assert spikes == []

    def test_all_spikes_above_threshold(self):
        """All samples above threshold → all timestamps."""
        p = self._make_profile([0.8, 0.9, 1.0], interval=0.5)
        spikes = self.analyzer.detect_motion_spikes(p, threshold=0.7)
        assert len(spikes) == 3

    def test_mixed_spikes(self):
        """Only samples >= threshold are included."""
        samples = [0.1, 0.8, 0.3, 0.95, 0.2, 0.7]
        p = self._make_profile(samples, interval=1.0)
        spikes = self.analyzer.detect_motion_spikes(p, threshold=0.7)
        # Samples at index 1 (0.8), 3 (0.95), 5 (0.7) meet the threshold
        assert len(spikes) == 3

    def test_spike_timestamps_are_sorted(self):
        """Returned timestamps are always sorted."""
        samples = [0.9, 0.1, 0.8, 0.2, 0.75]
        p = self._make_profile(samples, interval=0.5)
        spikes = self.analyzer.detect_motion_spikes(p, threshold=0.7)
        assert spikes == sorted(spikes)

    def test_empty_profile_no_spikes(self):
        """Empty motion_samples → empty list."""
        p = MotionProfile()
        spikes = self.analyzer.detect_motion_spikes(p, threshold=0.7)
        assert spikes == []

    def test_spike_timestamps_positive(self):
        """All spike timestamps are > 0."""
        samples = [0.8, 0.9, 0.95]
        p = self._make_profile(samples, interval=0.2)
        spikes = self.analyzer.detect_motion_spikes(p, threshold=0.7)
        assert all(t > 0 for t in spikes)

    def test_zero_interval_no_spikes(self):
        """Zero sample_interval_sec → no spikes (guard against division by zero)."""
        p = MotionProfile(motion_samples=[0.9, 0.8], sample_interval_sec=0.0)
        spikes = self.analyzer.detect_motion_spikes(p, threshold=0.7)
        assert spikes == []


# ---------------------------------------------------------------------------
# Tests: Full flow simulation with mock cv2
# ---------------------------------------------------------------------------


class TestAnalyzeClipMocked:
    """Simulate a full optical flow analysis with a mocked cv2 capture."""

    def _build_mock_cv2(self, frames):
        """
        Build a mock cv2 module that returns a sequence of gray frames.

        frames: list of (H, W) numpy-style lists (simulated grayscale).
        """
        import numpy as np

        mock_cv2 = MagicMock()
        mock_cv2.CAP_PROP_FPS = 0
        mock_cv2.CAP_PROP_FRAME_COUNT = 1

        # Simulate frames as BGR (H, W, 3) arrays
        bgr_frames = [np.zeros((4, 4, 3), dtype="uint8") for _ in range(len(frames))]
        gray_frames = [np.zeros((4, 4), dtype="uint8") for _ in range(len(frames))]

        read_results = [(True, f) for f in bgr_frames] + [(False, None)]
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {0: 6.0, 1: len(frames)}[prop]
        mock_cap.read.side_effect = read_results
        mock_cv2.VideoCapture.return_value = mock_cap

        # resize → returns a same-size frame
        mock_cv2.resize.side_effect = lambda f, size: f[:size[1], :size[0]] if len(f.shape) == 3 else f

        # cvtColor → return a gray frame
        gray_idx = [0]
        def fake_cvtcolor(frame, code):
            idx = gray_idx[0] % len(gray_frames)
            gray_idx[0] += 1
            return gray_frames[idx]
        mock_cv2.cvtColor.side_effect = fake_cvtcolor
        mock_cv2.COLOR_BGR2GRAY = 6

        # calcOpticalFlowFarneback → return flow with known magnitude
        def fake_flow(prev, curr, flow, *args, **kwargs):
            import numpy as np
            # Return flow with magnitude = 2.0 per pixel
            flow_arr = np.ones((4, 4, 2), dtype="float32") * 1.414
            return flow_arr
        mock_cv2.calcOpticalFlowFarneback.side_effect = fake_flow

        return mock_cv2, mock_cap

    def test_analyze_returns_profile_structure(self, tmp_path):
        """analyze_clip returns a valid MotionProfile with correct field types."""
        import numpy as np

        dummy = tmp_path / "clip.mp4"
        dummy.write_bytes(b"dummy")

        frames = [None] * 10  # 10 frames
        mock_cv2, _ = self._build_mock_cv2(frames)

        analyzer = MotionAnalyzer()
        with patch("src.services.cut_motion_analyzer.HAS_CV2", True), \
             patch("src.services.cut_motion_analyzer.cv2", mock_cv2):
            profile = analyzer.analyze_clip(str(dummy), sample_every_n=1)

        assert isinstance(profile, MotionProfile)
        assert isinstance(profile.motion_samples, list)
        assert isinstance(profile.avg_motion, float)
        assert isinstance(profile.max_motion, float)
        assert isinstance(profile.motion_variance, float)
        assert isinstance(profile.cut_density, float)
        assert isinstance(profile.total_duration_sec, float)

    def test_analyze_samples_within_range(self, tmp_path):
        """All motion_samples values are in [0.0, 1.0]."""
        dummy = tmp_path / "clip.mp4"
        dummy.write_bytes(b"dummy")

        frames = [None] * 15
        mock_cv2, _ = self._build_mock_cv2(frames)

        analyzer = MotionAnalyzer()
        with patch("src.services.cut_motion_analyzer.HAS_CV2", True), \
             patch("src.services.cut_motion_analyzer.cv2", mock_cv2):
            profile = analyzer.analyze_clip(str(dummy), sample_every_n=1)

        for v in profile.motion_samples:
            assert 0.0 <= v <= 1.0, f"motion_samples value {v} out of [0, 1]"


# ---------------------------------------------------------------------------
# Tests: Singleton
# ---------------------------------------------------------------------------


class TestSingleton:
    def test_get_motion_analyzer_same_instance(self):
        """get_motion_analyzer() returns the same instance on repeated calls."""
        a1 = get_motion_analyzer()
        a2 = get_motion_analyzer()
        assert a1 is a2
