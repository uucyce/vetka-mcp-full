"""
MARKER_W6.JKL: Unit tests for JKL progressive shuttle logic.

FCP7 App A: J/L = progressive speed ramp, K = stop.
Speed steps: [-8, -4, -2, -1, 0, 1, 2, 4, 8]
"""
import pytest


# ── Pure logic mirroring the handlers ────────────────────────

FORWARD_STEPS = [0, 1, 2, 4, 8]
REVERSE_STEPS = [0, -1, -2, -4, -8]


def shuttle_forward(current_speed: int) -> tuple[int, str]:
    """Returns (new_speed, action). Action: 'play', 'pause', or 'none'."""
    if current_speed < 0:
        return (0, 'pause')
    idx = FORWARD_STEPS.index(current_speed) if current_speed in FORWARD_STEPS else -1
    if idx >= 0 and idx < len(FORWARD_STEPS) - 1:
        return (FORWARD_STEPS[idx + 1], 'play')
    return (8, 'play')  # max


def shuttle_back(current_speed: int) -> tuple[int, str]:
    """Returns (new_speed, action)."""
    if current_speed > 0:
        return (0, 'pause')
    idx = REVERSE_STEPS.index(current_speed) if current_speed in REVERSE_STEPS else -1
    if idx >= 0 and idx < len(REVERSE_STEPS) - 1:
        return (REVERSE_STEPS[idx + 1], 'play')
    return (-8, 'play')  # max reverse


def shuttle_stop() -> tuple[int, str]:
    return (0, 'pause')


def shuttle_seek(current_time: float, dt: float, speed: int, duration: float) -> float:
    """Calculate new playhead position from shuttle speed."""
    new_time = current_time + dt * speed
    return max(0.0, min(new_time, duration))


# ── Tests ────────────────────────────────────────────────────


class TestShuttleForward:
    """L key: progressive forward speed ramp."""

    def test_from_stop(self):
        speed, action = shuttle_forward(0)
        assert speed == 1
        assert action == 'play'

    def test_from_1x(self):
        speed, _ = shuttle_forward(1)
        assert speed == 2

    def test_from_2x(self):
        speed, _ = shuttle_forward(2)
        assert speed == 4

    def test_from_4x(self):
        speed, _ = shuttle_forward(4)
        assert speed == 8

    def test_from_8x_stays_max(self):
        speed, _ = shuttle_forward(8)
        assert speed == 8

    def test_from_reverse_stops(self):
        """Pressing L while going reverse → stop."""
        speed, action = shuttle_forward(-2)
        assert speed == 0
        assert action == 'pause'


class TestShuttleBack:
    """J key: progressive reverse speed ramp."""

    def test_from_stop(self):
        speed, action = shuttle_back(0)
        assert speed == -1
        assert action == 'play'

    def test_from_minus1x(self):
        speed, _ = shuttle_back(-1)
        assert speed == -2

    def test_from_minus2x(self):
        speed, _ = shuttle_back(-2)
        assert speed == -4

    def test_from_minus4x(self):
        speed, _ = shuttle_back(-4)
        assert speed == -8

    def test_from_minus8x_stays_max(self):
        speed, _ = shuttle_back(-8)
        assert speed == -8

    def test_from_forward_stops(self):
        """Pressing J while going forward → stop."""
        speed, action = shuttle_back(4)
        assert speed == 0
        assert action == 'pause'


class TestShuttleStop:
    """K key: stop."""

    def test_stop(self):
        speed, action = shuttle_stop()
        assert speed == 0
        assert action == 'pause'


class TestShuttleSeek:
    """rAF loop seek calculation."""

    def test_forward_1x(self):
        """1x forward: 0.5s elapsed → advance 0.5s."""
        pos = shuttle_seek(10.0, 0.5, 1, 60.0)
        assert abs(pos - 10.5) < 0.001

    def test_forward_4x(self):
        """4x forward: 0.25s elapsed → advance 1.0s."""
        pos = shuttle_seek(10.0, 0.25, 4, 60.0)
        assert abs(pos - 11.0) < 0.001

    def test_reverse_2x(self):
        """2x reverse: 0.5s elapsed → go back 1.0s."""
        pos = shuttle_seek(10.0, 0.5, -2, 60.0)
        assert abs(pos - 9.0) < 0.001

    def test_clamp_at_zero(self):
        """Reverse past start clamps to 0."""
        pos = shuttle_seek(0.5, 1.0, -2, 60.0)
        assert pos == 0.0

    def test_clamp_at_duration(self):
        """Forward past end clamps to duration."""
        pos = shuttle_seek(59.0, 1.0, 4, 60.0)
        assert pos == 60.0

    def test_8x_forward(self):
        """8x forward: 0.1s elapsed → advance 0.8s."""
        pos = shuttle_seek(5.0, 0.1, 8, 60.0)
        assert abs(pos - 5.8) < 0.001


class TestFullSequence:
    """Simulate realistic JKL interaction sequences."""

    def test_jjj_sequence(self):
        """J → -1x → J → -2x → J → -4x."""
        speed = 0
        speed, _ = shuttle_back(speed)
        assert speed == -1
        speed, _ = shuttle_back(speed)
        assert speed == -2
        speed, _ = shuttle_back(speed)
        assert speed == -4

    def test_lll_sequence(self):
        """L → 1x → L → 2x → L → 4x → L → 8x."""
        speed = 0
        for expected in [1, 2, 4, 8]:
            speed, _ = shuttle_forward(speed)
            assert speed == expected

    def test_jl_reversal(self):
        """J J → -2x, then L → stop, L → 1x."""
        speed = 0
        speed, _ = shuttle_back(speed)  # -1
        speed, _ = shuttle_back(speed)  # -2
        speed, action = shuttle_forward(speed)  # stop (was reverse)
        assert speed == 0
        assert action == 'pause'
        speed, _ = shuttle_forward(speed)  # 1x
        assert speed == 1

    def test_k_resets(self):
        """L L L → 4x, K → 0."""
        speed = 0
        speed, _ = shuttle_forward(speed)  # 1
        speed, _ = shuttle_forward(speed)  # 2
        speed, _ = shuttle_forward(speed)  # 4
        speed, _ = shuttle_stop()
        assert speed == 0
