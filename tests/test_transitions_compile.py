"""
MARKER_B10 + B14: Unit tests for transition filter compilation.

Tests:
- _compile_xfade_filter: video transition filter generation
- _compile_acrossfade_filter: audio crossfade filter generation
- Transition type mapping (crossfade → fade, dissolve, dip_to_black, wipe)
- Audio curve selection (equal_power → qsin, linear → tri)
"""
import pytest
from src.services.cut_render_pipeline import (
    Transition,
    RenderClip,
    _compile_xfade_filter,
    _compile_acrossfade_filter,
    _map_transition_type,
)


class TestMapTransitionType:
    """Test FFmpeg transition type mapping."""

    def test_crossfade_maps_to_fade(self):
        assert _map_transition_type("crossfade") == "fade"

    def test_dissolve_maps_to_dissolve(self):
        assert _map_transition_type("dissolve") == "dissolve"

    def test_dip_to_black_maps_to_fadeblack(self):
        assert _map_transition_type("dip_to_black") == "fadeblack"

    def test_wipe_maps_to_wipeleft(self):
        assert _map_transition_type("wipe") == "wipeleft"

    def test_wipe_left_maps_to_wipeleft(self):
        assert _map_transition_type("wipe_left") == "wipeleft"

    def test_wipe_right_maps_to_wiperight(self):
        assert _map_transition_type("wipe_right") == "wiperight"

    def test_slide_left_maps_to_slideleft(self):
        assert _map_transition_type("slide_left") == "slideleft"

    def test_unknown_maps_to_fade_default(self):
        assert _map_transition_type("unknown_transition") == "fade"


class TestCompileXfadeFilter:
    """Test video xfade filter generation."""

    def test_basic_crossfade(self):
        """Test simple crossfade between two clips."""
        result = _compile_xfade_filter(
            "[v0]", "[v1]", "[vout1]",
            trans_type="crossfade",
            duration_sec=1.0,
            timeline_offset=1.0,
        )
        assert result == "[v0][v1]xfade=transition=fade:duration=1.000:offset=1.000[vout1]"

    def test_dissolve_transition(self):
        """Test dissolve transition."""
        result = _compile_xfade_filter(
            "[v0]", "[v1]", "[vout1]",
            trans_type="dissolve",
            duration_sec=0.5,
            timeline_offset=2.5,
        )
        assert result == "[v0][v1]xfade=transition=dissolve:duration=0.500:offset=2.500[vout1]"

    def test_dip_to_black(self):
        """Test dip to black transition."""
        result = _compile_xfade_filter(
            "[v0]", "[v1]", "[vout1]",
            trans_type="dip_to_black",
            duration_sec=2.0,
            timeline_offset=3.0,
        )
        assert result == "[v0][v1]xfade=transition=fadeblack:duration=2.000:offset=3.000[vout1]"

    def test_wipe_transition(self):
        """Test wipe transition."""
        result = _compile_xfade_filter(
            "[vout0]", "[v2]", "[vout2]",
            trans_type="wipe",
            duration_sec=1.5,
            timeline_offset=2.5,
        )
        assert result == "[vout0][v2]xfade=transition=wipeleft:duration=1.500:offset=2.500[vout2]"

    def test_chained_labels(self):
        """Test with chained input/output labels."""
        result = _compile_xfade_filter(
            "[vout0]", "[v1]", "[vout1]",
            trans_type="crossfade",
            duration_sec=0.75,
            timeline_offset=1.25,
        )
        assert result == "[vout0][v1]xfade=transition=fade:duration=0.750:offset=1.250[vout1]"

    def test_zero_offset(self):
        """Test transition at timeline start (offset=0)."""
        result = _compile_xfade_filter(
            "[v0]", "[v1]", "[vout1]",
            trans_type="crossfade",
            duration_sec=1.0,
            timeline_offset=0.0,
        )
        assert result == "[v0][v1]xfade=transition=fade:duration=1.000:offset=0.000[vout1]"

    def test_precision_formatting(self):
        """Test that duration and offset are formatted to 3 decimal places."""
        result = _compile_xfade_filter(
            "[v0]", "[v1]", "[vout1]",
            trans_type="crossfade",
            duration_sec=1.23456,
            timeline_offset=2.3456789,
        )
        # Should be truncated to 3 decimal places
        assert "duration=1.235" in result
        assert "offset=2.346" in result


class TestCompileAcrossfadeFilter:
    """Test audio crossfade filter generation."""

    def test_equal_power_curve(self):
        """Test equal_power audio curve (+3dB, qsin)."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=1.0,
            audio_curve="equal_power",
        )
        assert result == "[a0][a1]acrossfade=d=1.000:c1=qsin:c2=qsin[aout1]"

    def test_linear_curve(self):
        """Test linear audio curve (0dB, tri)."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=1.0,
            audio_curve="linear",
        )
        assert result == "[a0][a1]acrossfade=d=1.000:c1=tri:c2=tri[aout1]"

    def test_default_curve_is_equal_power(self):
        """Test that omitting audio_curve defaults to equal_power."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=1.0,
        )
        assert "c1=qsin" in result
        assert "c2=qsin" in result

    def test_chained_audio_labels(self):
        """Test with chained audio input/output labels."""
        result = _compile_acrossfade_filter(
            "[aout0]", "[a2]", "[aout2]",
            duration_sec=0.5,
            audio_curve="equal_power",
        )
        assert result == "[aout0][a2]acrossfade=d=0.500:c1=qsin:c2=qsin[aout2]"

    def test_long_duration(self):
        """Test with long crossfade duration."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=3.5,
            audio_curve="equal_power",
        )
        assert result == "[a0][a1]acrossfade=d=3.500:c1=qsin:c2=qsin[aout1]"

    def test_short_duration(self):
        """Test with very short crossfade."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=0.1,
            audio_curve="linear",
        )
        assert result == "[a0][a1]acrossfade=d=0.100:c1=tri:c2=tri[aout1]"


class TestTransitionIntegration:
    """Integration tests for transition compilation in RenderPlan context."""

    def test_transition_dataclass_defaults(self):
        """Test Transition dataclass with defaults."""
        t = Transition()
        assert t.type == "crossfade"
        assert t.duration_sec == 1.0
        assert t.between == (0, 1)
        assert t.audio_curve == "equal_power"

    def test_transition_custom_values(self):
        """Test Transition with custom values."""
        t = Transition(
            type="dissolve",
            duration_sec=0.5,
            between=(2, 3),
            audio_curve="linear",
        )
        assert t.type == "dissolve"
        assert t.duration_sec == 0.5
        assert t.between == (2, 3)
        assert t.audio_curve == "linear"

    def test_xfade_with_transition_object(self):
        """Test xfade generation using Transition object attributes."""
        t = Transition(
            type="dip_to_black",
            duration_sec=1.5,
            between=(0, 1),
            audio_curve="linear",
        )
        xfade = _compile_xfade_filter(
            "[v0]", "[v1]", "[vout1]",
            trans_type=t.type,
            duration_sec=t.duration_sec,
            timeline_offset=1.0,
        )
        assert "transition=fadeblack" in xfade
        assert "duration=1.500" in xfade

    def test_acrossfade_with_transition_object(self):
        """Test acrossfade generation using Transition object attributes."""
        t = Transition(
            type="crossfade",
            duration_sec=2.0,
            between=(0, 1),
            audio_curve="linear",
        )
        acrossfade = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=t.duration_sec,
            audio_curve=t.audio_curve,
        )
        assert "d=2.000" in acrossfade
        assert "c1=tri" in acrossfade
        assert "c2=tri" in acrossfade


class TestTransitionEdgeCases:
    """Edge case tests for transition compilation."""

    def test_very_short_transition(self):
        """Test with minimal duration."""
        result = _compile_xfade_filter(
            "[v0]", "[v1]", "[vout1]",
            trans_type="crossfade",
            duration_sec=0.01,
            timeline_offset=0.0,
        )
        assert "duration=0.010" in result

    def test_very_long_transition(self):
        """Test with very long duration."""
        result = _compile_xfade_filter(
            "[v0]", "[v1]", "[vout1]",
            trans_type="crossfade",
            duration_sec=10.5,
            timeline_offset=15.0,
        )
        assert "duration=10.500" in result
        assert "offset=15.000" in result

    def test_large_offset(self):
        """Test with large timeline offset."""
        result = _compile_xfade_filter(
            "[v0]", "[v1]", "[vout1]",
            trans_type="crossfade",
            duration_sec=1.0,
            timeline_offset=100.0,
        )
        assert "offset=100.000" in result

    def test_transition_type_case_sensitivity(self):
        """Test that transition type is case-sensitive."""
        # lowercase
        result = _compile_xfade_filter(
            "[v0]", "[v1]", "[vout1]",
            trans_type="crossfade",
            duration_sec=1.0,
            timeline_offset=1.0,
        )
        assert "transition=fade" in result

    def test_audio_curve_invalid_defaults_to_equal_power(self):
        """Test that invalid audio curve names default to equal_power."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=1.0,
            audio_curve="unknown_curve",
        )
        # Should default to equal_power
        assert "c1=qsin" in result
        assert "c2=qsin" in result
