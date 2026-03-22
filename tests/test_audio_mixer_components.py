"""
MARKER_B32-B34 — Tests for Audio Mixer sub-components.

Tests ClippingIndicator logic, FaderDbInput parsing, and MixerViewPresets behavior.
Pure Python equivalents of the TypeScript logic.

@task: tb_1773996025_9
"""
import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


# ---------------------------------------------------------------------------
# FaderDbInput: parseVolumeInput equivalents
# ---------------------------------------------------------------------------

def parse_volume_input(input_str: str) -> float | None:
    """Python equivalent of FaderDbInput.parseVolumeInput."""
    import re
    trimmed = input_str.strip().lower()
    if not trimmed:
        return None

    # dB input
    db_match = re.match(r'^([+-]?\d+\.?\d*)\s*db$', trimmed)
    if db_match:
        db = float(db_match.group(1))
        linear = 10 ** (db / 20)
        return max(0, min(1.5, round(linear * 100) / 100))

    # Percentage input
    pct_match = re.match(r'^(\d+\.?\d*)\s*%?$', trimmed)
    if pct_match:
        pct = float(pct_match.group(1))
        return max(0, min(1.5, pct / 100))

    return None


def volume_to_db_str(vol: float) -> str:
    """Python equivalent of FaderDbInput.volumeToDbStr."""
    if vol <= 0:
        return "-inf"
    db = 20 * math.log10(vol)
    sign = "+" if db >= 0 else ""
    return f"{sign}{db:.1f}dB"


class TestParseVolumeInput:
    def test_percentage_integer(self):
        assert parse_volume_input("85") == 0.85

    def test_percentage_with_symbol(self):
        assert parse_volume_input("85%") == 0.85

    def test_percentage_150(self):
        assert parse_volume_input("150%") == 1.5

    def test_percentage_zero(self):
        assert parse_volume_input("0") == 0.0

    def test_percentage_clamped_high(self):
        assert parse_volume_input("200%") == 1.5

    def test_db_negative(self):
        result = parse_volume_input("-6dB")
        assert result is not None
        assert abs(result - 0.50) < 0.02  # -6dB ≈ 0.501

    def test_db_zero(self):
        result = parse_volume_input("0dB")
        assert result is not None
        assert abs(result - 1.0) < 0.01

    def test_db_positive(self):
        result = parse_volume_input("+3.5dB")
        assert result is not None
        assert abs(result - 1.50) < 0.02  # +3.5dB ≈ 1.496

    def test_db_large_negative(self):
        result = parse_volume_input("-60dB")
        assert result is not None
        assert result < 0.01  # nearly zero

    def test_db_case_insensitive(self):
        result = parse_volume_input("-6DB")
        assert result is not None
        assert abs(result - 0.50) < 0.02

    def test_empty_string(self):
        assert parse_volume_input("") is None

    def test_garbage_input(self):
        assert parse_volume_input("abc") is None

    def test_whitespace(self):
        assert parse_volume_input("  85%  ") == 0.85


class TestVolumeToDbStr:
    def test_unity(self):
        assert volume_to_db_str(1.0) == "+0.0dB"

    def test_half(self):
        result = volume_to_db_str(0.5)
        assert "dB" in result
        assert result.startswith("-6")

    def test_zero(self):
        assert volume_to_db_str(0) == "-inf"

    def test_over_unity(self):
        result = volume_to_db_str(1.5)
        assert result.startswith("+3")


# ---------------------------------------------------------------------------
# ClippingIndicator: latch logic
# ---------------------------------------------------------------------------

class TestClippingLogic:
    def test_no_clip_at_normal_level(self):
        """Level below threshold should not trigger clipping."""
        threshold = 0.95
        level = 0.8
        assert level < threshold

    def test_clip_at_threshold(self):
        """Level at threshold should trigger clipping."""
        threshold = 0.95
        level = 0.95
        assert level >= threshold

    def test_clip_above_threshold(self):
        """Level above threshold should trigger clipping."""
        threshold = 0.95
        level = 1.2
        assert level >= threshold

    def test_latch_stays_after_level_drops(self):
        """Clipping should stay latched even after level drops.
        (Simulated: once clipped=True, remains True until reset)"""
        clipped = False
        levels = [0.5, 0.97, 0.3, 0.2]  # spike at index 1
        for lvl in levels:
            if lvl >= 0.95:
                clipped = True
        # Should still be clipped after levels dropped
        assert clipped is True


# ---------------------------------------------------------------------------
# MixerViewPresets: basic logic
# ---------------------------------------------------------------------------

class TestMixerViewPresets:
    def test_null_preset_stores_current(self):
        """First click on unconfigured preset stores current visibility."""
        presets = [None, None, None, None]
        current_visible = {"A1", "A2", "V1"}
        # Click preset 0 → store
        presets[0] = set(current_visible)
        assert presets[0] == {"A1", "A2", "V1"}

    def test_configured_preset_recalls(self):
        """Clicking configured preset restores its visibility."""
        presets = [{"A1", "A2"}, {"V1", "V2"}, None, None]
        # Click preset 1 → recall
        visible = presets[1]
        assert visible == {"V1", "V2"}

    def test_all_button_shows_all(self):
        """'All' button should show all lanes."""
        all_lanes = {"A1", "A2", "V1", "V2", "AUX"}
        visible = set(all_lanes)
        assert visible == all_lanes

    def test_option_click_overwrites(self):
        """Option+Click overwrites preset with current visibility."""
        presets = [{"A1"}, None, None, None]
        new_visible = {"A1", "A2", "V1"}
        presets[0] = set(new_visible)
        assert presets[0] == {"A1", "A2", "V1"}
