"""
MARKER_KF-BEZIER: Reference tests for keyframe interpolation with easing.
Tests the pure interpolation logic (same algorithm as TypeScript version).
"""
import pytest
import math


def interpolate_keyframes(keyframes: list[dict], time_sec: float) -> float:
    """Python reference implementation of interpolateKeyframes."""
    if not keyframes:
        return 0.0
    if len(keyframes) == 1:
        return keyframes[0]["value"]

    # Before first → hold
    if time_sec <= keyframes[0]["time_sec"]:
        return keyframes[0]["value"]
    # After last → hold
    if time_sec >= keyframes[-1]["time_sec"]:
        return keyframes[-1]["value"]

    # Find surrounding keyframes
    i = 0
    while i < len(keyframes) - 1 and keyframes[i + 1]["time_sec"] <= time_sec:
        i += 1
    kf_a = keyframes[i]
    kf_b = keyframes[i + 1]
    dt = kf_b["time_sec"] - kf_a["time_sec"]
    if dt <= 0:
        return kf_a["value"]
    t = (time_sec - kf_a["time_sec"]) / dt

    easing = kf_a.get("easing", "linear")
    if easing == "ease_in":
        eased = t * t
    elif easing == "ease_out":
        eased = 1 - (1 - t) * (1 - t)
    elif easing == "bezier":
        eased = t * t * (3 - 2 * t)  # smoothstep
    else:
        eased = t  # linear

    return kf_a["value"] + (kf_b["value"] - kf_a["value"]) * eased


class TestInterpolation:
    def test_empty_returns_zero(self):
        assert interpolate_keyframes([], 5.0) == 0.0

    def test_single_keyframe_returns_value(self):
        assert interpolate_keyframes([{"time_sec": 1, "value": 0.8, "easing": "linear"}], 5.0) == 0.8

    def test_before_first_holds(self):
        kfs = [
            {"time_sec": 2, "value": 0.5, "easing": "linear"},
            {"time_sec": 4, "value": 1.0, "easing": "linear"},
        ]
        assert interpolate_keyframes(kfs, 0) == 0.5
        assert interpolate_keyframes(kfs, 1) == 0.5

    def test_after_last_holds(self):
        kfs = [
            {"time_sec": 0, "value": 0.0, "easing": "linear"},
            {"time_sec": 2, "value": 1.0, "easing": "linear"},
        ]
        assert interpolate_keyframes(kfs, 5) == 1.0

    def test_linear_midpoint(self):
        kfs = [
            {"time_sec": 0, "value": 0.0, "easing": "linear"},
            {"time_sec": 2, "value": 1.0, "easing": "linear"},
        ]
        assert interpolate_keyframes(kfs, 1.0) == pytest.approx(0.5)

    def test_linear_quarter(self):
        kfs = [
            {"time_sec": 0, "value": 0.0, "easing": "linear"},
            {"time_sec": 4, "value": 1.0, "easing": "linear"},
        ]
        assert interpolate_keyframes(kfs, 1.0) == pytest.approx(0.25)

    def test_ease_in_starts_slow(self):
        kfs = [
            {"time_sec": 0, "value": 0.0, "easing": "ease_in"},
            {"time_sec": 2, "value": 1.0, "easing": "linear"},
        ]
        # At t=0.5 (midpoint), ease_in = 0.25 (slower than linear 0.5)
        val = interpolate_keyframes(kfs, 1.0)
        assert val == pytest.approx(0.25)
        assert val < 0.5  # slower than linear

    def test_ease_out_starts_fast(self):
        kfs = [
            {"time_sec": 0, "value": 0.0, "easing": "ease_out"},
            {"time_sec": 2, "value": 1.0, "easing": "linear"},
        ]
        # At t=0.5, ease_out = 0.75 (faster than linear 0.5)
        val = interpolate_keyframes(kfs, 1.0)
        assert val == pytest.approx(0.75)
        assert val > 0.5  # faster than linear

    def test_bezier_smoothstep(self):
        kfs = [
            {"time_sec": 0, "value": 0.0, "easing": "bezier"},
            {"time_sec": 2, "value": 1.0, "easing": "linear"},
        ]
        # At t=0.5, smoothstep = 0.5 (symmetric S-curve passes through midpoint)
        val = interpolate_keyframes(kfs, 1.0)
        assert val == pytest.approx(0.5)

    def test_bezier_quarter_slow_start(self):
        kfs = [
            {"time_sec": 0, "value": 0.0, "easing": "bezier"},
            {"time_sec": 4, "value": 1.0, "easing": "linear"},
        ]
        # At t=0.25, smoothstep = 0.25*0.25*(3-0.5) = 0.15625
        val = interpolate_keyframes(kfs, 1.0)
        assert val < 0.25  # slower than linear at start

    def test_multi_segment(self):
        kfs = [
            {"time_sec": 0, "value": 0.0, "easing": "linear"},
            {"time_sec": 2, "value": 1.0, "easing": "linear"},
            {"time_sec": 4, "value": 0.0, "easing": "linear"},
        ]
        assert interpolate_keyframes(kfs, 1.0) == pytest.approx(0.5)
        assert interpolate_keyframes(kfs, 2.0) == pytest.approx(1.0)
        assert interpolate_keyframes(kfs, 3.0) == pytest.approx(0.5)

    def test_fade_out_curve(self):
        """Typical use case: opacity fade from 1.0 to 0.0 with ease_out."""
        kfs = [
            {"time_sec": 0, "value": 1.0, "easing": "ease_out"},
            {"time_sec": 1, "value": 0.0, "easing": "linear"},
        ]
        val_25 = interpolate_keyframes(kfs, 0.25)
        val_50 = interpolate_keyframes(kfs, 0.50)
        val_75 = interpolate_keyframes(kfs, 0.75)
        # ease_out: fast start, slow end
        assert val_25 < 1.0 - 0.25  # already past linear at 25%
        assert val_50 < 1.0 - 0.50  # past linear midpoint
        assert val_75 > 0.0  # hasn't reached 0 yet
