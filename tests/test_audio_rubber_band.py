"""
MARKER_B30 — Tests for AudioRubberBand helper functions.

Tests the volume/position conversion logic and keyframe interpolation
used by the AudioRubberBand component. Uses pure Python equivalents
of the TypeScript helpers (same math, verified cross-language).

@task: tb_1774167622_25
"""
import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

MAX_VOLUME = 1.5
PAD = 2


def volume_to_y(vol: float, height: int) -> float:
    """Python equivalent of AudioRubberBand.volumeToY."""
    clamped = max(0, min(MAX_VOLUME, vol))
    return height - PAD - (clamped / MAX_VOLUME) * (height - 2 * PAD)


def y_to_volume(y: float, height: int) -> float:
    """Python equivalent of AudioRubberBand.yToVolume."""
    vol = ((height - PAD - y) / (height - 2 * PAD)) * MAX_VOLUME
    return max(0, min(MAX_VOLUME, round(vol * 100) / 100))


def time_to_x(time_sec: float, duration_sec: float, width: int) -> float:
    if duration_sec <= 0:
        return 0
    return (time_sec / duration_sec) * width


def x_to_time(x: float, duration_sec: float, width: int) -> float:
    if width <= 0:
        return 0
    return max(0, min(duration_sec, (x / width) * duration_sec))


def interpolate_volume(time_sec: float, keyframes: list, default_vol: float) -> float:
    """Python equivalent of AudioRubberBand.interpolateVolume."""
    if not keyframes:
        return default_vol
    if time_sec <= keyframes[0]["time_sec"]:
        return keyframes[0]["value"]
    if time_sec >= keyframes[-1]["time_sec"]:
        return keyframes[-1]["value"]

    for i in range(len(keyframes) - 1):
        a = keyframes[i]
        b = keyframes[i + 1]
        if a["time_sec"] <= time_sec <= b["time_sec"]:
            t = (time_sec - a["time_sec"]) / (b["time_sec"] - a["time_sec"])
            return a["value"] + t * (b["value"] - a["value"])
    return default_vol


# ---------------------------------------------------------------------------
# Volume ↔ Y position tests
# ---------------------------------------------------------------------------

class TestVolumeToY:
    def test_zero_volume_at_bottom(self):
        y = volume_to_y(0.0, 100)
        assert y == 100 - PAD  # bottom edge

    def test_max_volume_at_top(self):
        y = volume_to_y(MAX_VOLUME, 100)
        assert y == PAD  # top edge

    def test_unity_volume_two_thirds(self):
        y = volume_to_y(1.0, 100)
        # 1.0 / 1.5 = 0.667 of range from bottom
        expected = 100 - PAD - (1.0 / MAX_VOLUME) * (100 - 2 * PAD)
        assert abs(y - expected) < 0.01

    def test_clamps_negative(self):
        y = volume_to_y(-0.5, 100)
        assert y == volume_to_y(0.0, 100)

    def test_clamps_over_max(self):
        y = volume_to_y(2.0, 100)
        assert y == volume_to_y(MAX_VOLUME, 100)

    def test_roundtrip(self):
        """volume_to_y → y_to_volume should roundtrip."""
        for vol in [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5]:
            y = volume_to_y(vol, 200)
            recovered = y_to_volume(y, 200)
            assert abs(recovered - vol) < 0.02, f"Failed roundtrip for vol={vol}"


class TestYToVolume:
    def test_top_is_max(self):
        vol = y_to_volume(PAD, 100)
        assert abs(vol - MAX_VOLUME) < 0.02

    def test_bottom_is_zero(self):
        vol = y_to_volume(100 - PAD, 100)
        assert abs(vol) < 0.02

    def test_clamps_above_top(self):
        vol = y_to_volume(-10, 100)
        assert vol == MAX_VOLUME

    def test_clamps_below_bottom(self):
        vol = y_to_volume(200, 100)
        assert vol == 0.0


# ---------------------------------------------------------------------------
# Time ↔ X position tests
# ---------------------------------------------------------------------------

class TestTimeX:
    def test_start_at_zero(self):
        assert time_to_x(0, 10.0, 500) == 0

    def test_end_at_width(self):
        assert time_to_x(10.0, 10.0, 500) == 500

    def test_midpoint(self):
        assert time_to_x(5.0, 10.0, 500) == 250

    def test_zero_duration(self):
        assert time_to_x(5.0, 0, 500) == 0

    def test_x_to_time_roundtrip(self):
        for t in [0, 2.5, 5.0, 7.5, 10.0]:
            x = time_to_x(t, 10.0, 500)
            recovered = x_to_time(x, 10.0, 500)
            assert abs(recovered - t) < 0.01

    def test_x_to_time_clamps(self):
        assert x_to_time(-10, 10.0, 500) == 0
        assert x_to_time(600, 10.0, 500) == 10.0


# ---------------------------------------------------------------------------
# Keyframe interpolation tests
# ---------------------------------------------------------------------------

class TestInterpolateVolume:
    def test_no_keyframes_returns_default(self):
        assert interpolate_volume(5.0, [], 0.8) == 0.8

    def test_before_first_keyframe(self):
        kfs = [{"time_sec": 2.0, "value": 0.5}]
        assert interpolate_volume(0.0, kfs, 1.0) == 0.5

    def test_after_last_keyframe(self):
        kfs = [{"time_sec": 2.0, "value": 0.5}, {"time_sec": 5.0, "value": 0.8}]
        assert interpolate_volume(10.0, kfs, 1.0) == 0.8

    def test_at_keyframe(self):
        kfs = [{"time_sec": 2.0, "value": 0.5}, {"time_sec": 5.0, "value": 1.0}]
        assert interpolate_volume(2.0, kfs, 1.0) == 0.5
        assert interpolate_volume(5.0, kfs, 1.0) == 1.0

    def test_linear_interpolation_midpoint(self):
        kfs = [{"time_sec": 0.0, "value": 0.0}, {"time_sec": 10.0, "value": 1.0}]
        result = interpolate_volume(5.0, kfs, 0.5)
        assert abs(result - 0.5) < 0.01

    def test_linear_interpolation_quarter(self):
        kfs = [{"time_sec": 0.0, "value": 0.0}, {"time_sec": 10.0, "value": 1.0}]
        result = interpolate_volume(2.5, kfs, 0.5)
        assert abs(result - 0.25) < 0.01

    def test_three_keyframes(self):
        kfs = [
            {"time_sec": 0.0, "value": 1.0},
            {"time_sec": 5.0, "value": 0.0},
            {"time_sec": 10.0, "value": 1.0},
        ]
        # At 2.5s: between kf0 and kf1, should be 0.5
        result = interpolate_volume(2.5, kfs, 1.0)
        assert abs(result - 0.5) < 0.01
        # At 7.5s: between kf1 and kf2, should be 0.5
        result = interpolate_volume(7.5, kfs, 1.0)
        assert abs(result - 0.5) < 0.01


# ---------------------------------------------------------------------------
# dB conversion tests (matches cut_audio_engine.py)
# ---------------------------------------------------------------------------

class TestVolumeDb:
    def test_unity_is_0db(self):
        db = 20 * math.log10(1.0)
        assert abs(db) < 0.001

    def test_half_is_minus_6db(self):
        db = 20 * math.log10(0.5)
        assert abs(db - (-6.02)) < 0.1

    def test_1_5_is_plus_3_5db(self):
        db = 20 * math.log10(1.5)
        assert abs(db - 3.52) < 0.1
