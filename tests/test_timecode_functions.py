"""
MARKER_W5.TC: Unit tests for TimecodeField formatTimecode / parseTimecodeInput.

These test the same logic in Python (reference implementation).
The TypeScript functions must produce identical results.

Tests cover:
  - 23.976 fps (film)
  - 25 fps (PAL)
  - 29.97 fps drop-frame (NTSC broadcast)
  - 29.97 fps non-drop-frame
  - 30 fps
  - Relative entry (+/- frames/seconds)
  - Partial entry (FCP7-style numeric shorthand)
  - Edge cases (zero, boundary, negative)
"""
import pytest
import math


# ── Python reference implementation (mirrors TypeScript) ──────────

def format_timecode(seconds: float, fps: float = 25.0, drop_frame: bool = False) -> str:
    """Convert seconds to SMPTE timecode string."""
    if not math.isfinite(seconds) or seconds < 0:
        seconds = 0.0

    use_df = drop_frame and (abs(fps - 29.97) < 0.1 or abs(fps - 59.94) < 0.1)
    sep = ';' if use_df else ':'

    total_frames = round(seconds * fps)

    if not use_df:
        round_fps = round(fps)
        f = total_frames % round_fps
        total_sec = total_frames // round_fps
        s = total_sec % 60
        total_min = total_sec // 60
        m = total_min % 60
        h = total_min // 60
        return f"{h:02d}:{m:02d}:{s:02d}{sep}{f:02d}"

    # Drop-frame (SMPTE 12M)
    drop_frames = 2 if abs(fps - 29.97) < 0.1 else 4
    frames_per_min = round(fps) * 60 - drop_frames
    frames_per_10min = frames_per_min * 10 + drop_frames

    d = total_frames
    d10 = d // frames_per_10min
    m10 = d % frames_per_10min

    if m10 < drop_frames:
        m10 = drop_frames

    frame_adjust = drop_frames * ((m10 - drop_frames) // frames_per_min)
    d += d10 * drop_frames * 9 + frame_adjust

    round_fps = round(fps)
    f = d % round_fps
    d = d // round_fps
    s = d % 60
    d = d // 60
    m = d % 60
    h = d // 60

    return f"{h:02d}:{m:02d}:{s:02d}{sep}{f:02d}"


def parse_timecode_input(input_str: str, fps: float = 25.0, current_time: float = 0.0):
    """Parse timecode input to seconds. Returns None if unparseable."""
    trimmed = input_str.strip()
    if not trimmed:
        return None

    is_relative = trimmed[0] in ('+', '-')
    sign = -1 if trimmed[0] == '-' else 1
    body = trimmed[1:] if is_relative else trimmed

    # Raw seconds (decimal without colons)
    import re
    if re.match(r'^\d+\.\d+$', body):
        raw = float(body)
        if math.isnan(raw):
            return None
        return max(0, current_time + sign * raw) if is_relative else raw

    parts = re.split(r'[:;]', body)

    h, m, s, f = 0, 0, 0, 0

    if len(parts) == 1:
        num = parts[0]
        if re.match(r'^\d+$', num):
            if is_relative:
                # Relative: treat as raw frame count (e.g. +10, -100)
                raw_frames = int(num)
                return max(0, current_time + sign * raw_frames / fps)
            if len(num) <= 3:
                f = int(num)
            else:
                padded = num.zfill(8)
                h = int(padded[0:2])
                m = int(padded[2:4])
                s = int(padded[4:6])
                f = int(padded[6:8])
        else:
            return None
    elif len(parts) == 2:
        s = int(parts[0]) if parts[0] else 0
        f = int(parts[1]) if parts[1] else 0
    elif len(parts) == 3:
        m = int(parts[0]) if parts[0] else 0
        s = int(parts[1]) if parts[1] else 0
        f = int(parts[2]) if parts[2] else 0
    elif len(parts) == 4:
        h = int(parts[0]) if parts[0] else 0
        m = int(parts[1]) if parts[1] else 0
        s = int(parts[2]) if parts[2] else 0
        f = int(parts[3]) if parts[3] else 0
    else:
        return None

    round_fps = round(fps)
    if f >= round_fps or f < 0:
        return None
    if s >= 60 or s < 0:
        return None
    if m >= 60 or m < 0:
        return None
    if h < 0:
        return None

    total_seconds = h * 3600 + m * 60 + s + f / fps

    if is_relative:
        return max(0, current_time + sign * total_seconds)
    return total_seconds


# ── Tests ────────────────────────────────────────────────────────


class TestFormatTimecode:
    """10+ cases covering all major framerates."""

    def test_25fps_zero(self):
        assert format_timecode(0, 25) == "00:00:00:00"

    def test_25fps_one_frame(self):
        assert format_timecode(1 / 25, 25) == "00:00:00:01"

    def test_25fps_one_second(self):
        assert format_timecode(1.0, 25) == "00:00:01:00"

    def test_25fps_one_minute(self):
        assert format_timecode(60.0, 25) == "00:01:00:00"

    def test_25fps_one_hour(self):
        assert format_timecode(3600.0, 25) == "01:00:00:00"

    def test_25fps_complex(self):
        # 1h 23m 45s 12f = 5025 + 12/25 = 5025.48
        assert format_timecode(5025.48, 25) == "01:23:45:12"

    def test_24fps_film(self):
        assert format_timecode(1.0, 24) == "00:00:01:00"
        assert format_timecode(0.5, 24) == "00:00:00:12"

    def test_23976_film(self):
        # 23.976 rounds to 24 fps for frame count
        assert format_timecode(1.0, 23.976) == "00:00:01:00"

    def test_30fps(self):
        assert format_timecode(1.0, 30) == "00:00:01:00"
        assert format_timecode(0.5, 30) == "00:00:00:15"

    def test_2997_nondrop(self):
        """29.97 NDF: same as 30fps counting, no frame skip."""
        assert format_timecode(0, 29.97, drop_frame=False) == "00:00:00:00"
        assert format_timecode(1.0, 29.97, drop_frame=False) == "00:00:01:00"

    def test_2997_dropframe_separator(self):
        """Drop-frame uses semicolon separator."""
        tc = format_timecode(0, 29.97, drop_frame=True)
        assert ";" in tc
        assert tc == "00:00:00;00"

    def test_2997_dropframe_one_second(self):
        tc = format_timecode(1.0, 29.97, drop_frame=True)
        assert tc == "00:00:01;00"

    def test_2997_dropframe_one_minute(self):
        """At 60.0s, frame=round(60*29.97)=1798, still in minute 0.
        DF 00:01:00;02 = frame 1800 ≈ 60.06s.
        So 60.0s → 00:00:59;28 is correct."""
        tc = format_timecode(60.0, 29.97, drop_frame=True)
        assert tc == "00:00:59;28"
        # Verify that frame 1800 (≈60.06s) gives the minute boundary
        tc2 = format_timecode(1800 / 29.97, 29.97, drop_frame=True)
        assert tc2 == "00:01:00;02"

    def test_2997_dropframe_ten_minutes(self):
        """At 10 minutes, NO skip (every 10th minute is exception)."""
        tc = format_timecode(600.0, 29.97, drop_frame=True)
        assert tc == "00:10:00;00"

    def test_negative_clamps_to_zero(self):
        assert format_timecode(-5, 25) == "00:00:00:00"

    def test_nan_clamps_to_zero(self):
        assert format_timecode(float('nan'), 25) == "00:00:00:00"


class TestParseTimecodeInput:
    """Absolute and relative entry tests."""

    def test_full_smpte(self):
        result = parse_timecode_input("01:02:03:04", 25)
        expected = 1 * 3600 + 2 * 60 + 3 + 4 / 25
        assert abs(result - expected) < 0.001

    def test_partial_4digit(self):
        """FCP7 style: 1419 → 00:00:14:19"""
        result = parse_timecode_input("1419", 25)
        expected = 14 + 19 / 25
        assert abs(result - expected) < 0.001

    def test_partial_2digit_frames(self):
        """12 → 12 frames"""
        result = parse_timecode_input("12", 25)
        expected = 12 / 25
        assert abs(result - expected) < 0.001

    def test_relative_forward_frames(self):
        """+10 from 5.0s → 5.0 + 10/25"""
        result = parse_timecode_input("+10", 25, current_time=5.0)
        expected = 5.0 + 10 / 25
        assert abs(result - expected) < 0.001

    def test_relative_backward_seconds(self):
        """-1:00 from 10.0s → 9.0s"""
        result = parse_timecode_input("-1:00", 25, current_time=10.0)
        expected = 10.0 - 1.0
        assert abs(result - expected) < 0.001

    def test_relative_clamps_to_zero(self):
        """-100 frames from 0.5s → 0.5 - 100/25 = 0.5 - 4.0 = -3.5 → clamped to 0"""
        result = parse_timecode_input("-100", 25, current_time=0.5)
        assert result == 0.0

    def test_raw_seconds(self):
        result = parse_timecode_input("10.5", 25)
        assert abs(result - 10.5) < 0.001

    def test_relative_raw_seconds(self):
        result = parse_timecode_input("+2.5", 25, current_time=3.0)
        assert abs(result - 5.5) < 0.001

    def test_mm_ss_ff(self):
        """2:30:12 → 2min 30sec 12frames"""
        result = parse_timecode_input("2:30:12", 25)
        expected = 2 * 60 + 30 + 12 / 25
        assert abs(result - expected) < 0.001

    def test_ss_ff(self):
        """45:10 → 45sec 10frames"""
        result = parse_timecode_input("45:10", 25)
        expected = 45 + 10 / 25
        assert abs(result - expected) < 0.001

    def test_invalid_frames_over_fps(self):
        """Frame >= fps should return None"""
        assert parse_timecode_input("00:00:00:30", 25) is None

    def test_invalid_seconds_over_60(self):
        assert parse_timecode_input("00:00:70:00", 25) is None

    def test_empty_string(self):
        assert parse_timecode_input("", 25) is None

    def test_dropframe_semicolon(self):
        """Drop-frame input with semicolon separator."""
        result = parse_timecode_input("01:00:00;00", 29.97)
        expected = 1 * 3600 + 0 / 29.97
        assert abs(result - expected) < 0.001

    def test_8digit_padded(self):
        """01020304 → 01:02:03:04"""
        result = parse_timecode_input("01020304", 25)
        expected = 1 * 3600 + 2 * 60 + 3 + 4 / 25
        assert abs(result - expected) < 0.001


class TestRoundTrip:
    """Format → parse → format should be stable."""

    @pytest.mark.parametrize("seconds,fps", [
        (0, 25),
        (1.0, 25),
        (3661.48, 25),
        (0, 24),
        (100.0, 24),
        (0, 30),
        (59.9, 30),
    ])
    def test_roundtrip_ndf(self, seconds, fps):
        tc = format_timecode(seconds, fps)
        parsed = parse_timecode_input(tc, fps)
        assert parsed is not None
        # Re-format should match
        assert format_timecode(parsed, fps) == tc
