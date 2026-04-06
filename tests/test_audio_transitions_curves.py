"""
MARKER_B14: Unit tests for advanced audio transition curves.

Tests:
- _map_audio_curve: FFmpeg curve type mapping
- _compile_acrossfade_filter with all curve types
- Curve-specific behavior and fade characteristics
"""
import pytest
from src.services.cut_render_pipeline import (
    _map_audio_curve,
    _compile_acrossfade_filter,
)


class TestMapAudioCurve:
    """Test audio curve type mapping to FFmpeg parameters."""

    def test_equal_power_maps_to_qsin(self):
        """equal_power (+3dB, smooth) → qsin."""
        c1, c2 = _map_audio_curve("equal_power")
        assert c1 == "qsin"
        assert c2 == "qsin"

    def test_linear_maps_to_tri(self):
        """linear (0dB, dip) → tri."""
        c1, c2 = _map_audio_curve("linear")
        assert c1 == "tri"
        assert c2 == "tri"

    def test_exponential_maps_to_esin(self):
        """exponential (smooth accel/decel) → esin."""
        c1, c2 = _map_audio_curve("exponential")
        assert c1 == "esin"
        assert c2 == "esin"

    def test_smooth_start_maps_to_hsin(self):
        """smooth_start (gradual entrance) → hsin."""
        c1, c2 = _map_audio_curve("smooth_start")
        assert c1 == "hsin"
        assert c2 == "hsin"

    def test_smooth_end_maps_to_qcos(self):
        """smooth_end (gradual exit) → qcos."""
        c1, c2 = _map_audio_curve("smooth_end")
        assert c1 == "qcos"
        assert c2 == "qcos"

    def test_logarithmic_maps_to_log(self):
        """logarithmic (slow start, sharp end) → log."""
        c1, c2 = _map_audio_curve("logarithmic")
        assert c1 == "log"
        assert c2 == "log"

    def test_exponential_log_maps_to_sqrt(self):
        """exponential_log (gentle accel) → sqrt."""
        c1, c2 = _map_audio_curve("exponential_log")
        assert c1 == "sqrt"
        assert c2 == "sqrt"

    def test_inverse_log_maps_to_ilog(self):
        """inverse_log (sharp start, slow end) → ilog."""
        c1, c2 = _map_audio_curve("inverse_log")
        assert c1 == "ilog"
        assert c2 == "ilog"

    def test_s_curve_maps_to_ssin(self):
        """s_curve (smooth both ends) → ssin."""
        c1, c2 = _map_audio_curve("s_curve")
        assert c1 == "ssin"
        assert c2 == "ssin"

    def test_cubic_maps_to_cbrt(self):
        """cubic (gentle curve) → cbrt."""
        c1, c2 = _map_audio_curve("cubic")
        assert c1 == "cbrt"
        assert c2 == "cbrt"

    def test_unknown_defaults_to_equal_power(self):
        """Unknown curve type defaults to equal_power (qsin)."""
        c1, c2 = _map_audio_curve("unknown_curve_type")
        assert c1 == "qsin"
        assert c2 == "qsin"


class TestCompileAcrossfadeWithCurves:
    """Test acrossfade filter generation with all curve types."""

    def test_equal_power_curve(self):
        """Generate acrossfade with equal_power (default) curve."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=1.0,
            audio_curve="equal_power",
        )
        assert result == "[a0][a1]acrossfade=d=1.000:c1=qsin:c2=qsin[aout1]"

    def test_linear_curve(self):
        """Generate acrossfade with linear curve."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=1.0,
            audio_curve="linear",
        )
        assert result == "[a0][a1]acrossfade=d=1.000:c1=tri:c2=tri[aout1]"

    def test_exponential_curve(self):
        """Generate acrossfade with exponential curve."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=0.5,
            audio_curve="exponential",
        )
        assert result == "[a0][a1]acrossfade=d=0.500:c1=esin:c2=esin[aout1]"

    def test_smooth_start_curve(self):
        """Generate acrossfade with smooth_start curve."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=2.0,
            audio_curve="smooth_start",
        )
        assert result == "[a0][a1]acrossfade=d=2.000:c1=hsin:c2=hsin[aout1]"

    def test_smooth_end_curve(self):
        """Generate acrossfade with smooth_end curve."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=1.5,
            audio_curve="smooth_end",
        )
        assert result == "[a0][a1]acrossfade=d=1.500:c1=qcos:c2=qcos[aout1]"

    def test_logarithmic_curve(self):
        """Generate acrossfade with logarithmic curve."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=1.0,
            audio_curve="logarithmic",
        )
        assert result == "[a0][a1]acrossfade=d=1.000:c1=log:c2=log[aout1]"

    def test_exponential_log_curve(self):
        """Generate acrossfade with exponential_log curve."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=0.8,
            audio_curve="exponential_log",
        )
        assert result == "[a0][a1]acrossfade=d=0.800:c1=sqrt:c2=sqrt[aout1]"

    def test_inverse_log_curve(self):
        """Generate acrossfade with inverse_log curve."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=1.2,
            audio_curve="inverse_log",
        )
        assert result == "[a0][a1]acrossfade=d=1.200:c1=ilog:c2=ilog[aout1]"

    def test_s_curve(self):
        """Generate acrossfade with s_curve."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=1.0,
            audio_curve="s_curve",
        )
        assert result == "[a0][a1]acrossfade=d=1.000:c1=ssin:c2=ssin[aout1]"

    def test_cubic_curve(self):
        """Generate acrossfade with cubic curve."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=0.9,
            audio_curve="cubic",
        )
        assert result == "[a0][a1]acrossfade=d=0.900:c1=cbrt:c2=cbrt[aout1]"

    def test_default_curve_is_equal_power(self):
        """Omitting audio_curve defaults to equal_power."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=1.0,
        )
        assert "c1=qsin" in result
        assert "c2=qsin" in result

    def test_chained_labels_with_various_curves(self):
        """Test chained audio labels with different curves."""
        result = _compile_acrossfade_filter(
            "[aout0]", "[a2]", "[aout2]",
            duration_sec=1.0,
            audio_curve="smooth_start",
        )
        assert result == "[aout0][a2]acrossfade=d=1.000:c1=hsin:c2=hsin[aout2]"


class TestAudioCurveCharacteristics:
    """Test audio curve characteristics and use cases."""

    def test_equal_power_smooth_fade(self):
        """equal_power provides +3dB at midpoint for smooth sound."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=1.0,
            audio_curve="equal_power",
        )
        # Should use qsin for smooth equal-power curve
        assert "qsin" in result
        assert "equal_power" not in result  # FFmpeg doesn't know "equal_power", uses qsin

    def test_linear_dip_at_midpoint(self):
        """linear curve has 0dB dip at midpoint."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=1.0,
            audio_curve="linear",
        )
        # Should use tri (triangle) curve
        assert "tri" in result

    def test_exponential_smooth_acceleration(self):
        """exponential curve has smooth acceleration/deceleration."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=1.0,
            audio_curve="exponential",
        )
        assert "esin" in result

    def test_short_duration_transition(self):
        """Test very short crossfade duration."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=0.1,
            audio_curve="equal_power",
        )
        assert "d=0.100" in result

    def test_long_duration_transition(self):
        """Test very long crossfade duration."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=5.0,
            audio_curve="equal_power",
        )
        assert "d=5.000" in result

    def test_precision_three_decimals(self):
        """Duration formatted to 3 decimal places."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=1.23456,
            audio_curve="equal_power",
        )
        assert "d=1.235" in result

    def test_all_curves_have_same_channel_curves(self):
        """All curves apply same c1 and c2 (both channels fade together)."""
        for curve in ["equal_power", "linear", "exponential", "smooth_start",
                      "smooth_end", "logarithmic", "exponential_log", "inverse_log",
                      "s_curve", "cubic"]:
            result = _compile_acrossfade_filter(
                "[a0]", "[a1]", "[aout1]",
                duration_sec=1.0,
                audio_curve=curve,
            )
            # Extract c1 and c2 values
            assert ":c1=" in result and ":c2=" in result
            # Parse to verify c1 == c2 (symmetric curves)
            import re
            match = re.search(r':c1=(\w+):c2=(\w+)', result)
            if match:
                c1, c2 = match.groups()
                assert c1 == c2, f"Curve {curve} should have c1 == c2"


class TestBackwardCompatibility:
    """Ensure B14 changes don't break B10 API."""

    def test_old_code_still_works_with_equal_power(self):
        """Existing code using equal_power continues to work."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=1.0,
            audio_curve="equal_power",
        )
        assert result == "[a0][a1]acrossfade=d=1.000:c1=qsin:c2=qsin[aout1]"

    def test_old_code_still_works_with_linear(self):
        """Existing code using linear continues to work."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=1.0,
            audio_curve="linear",
        )
        assert result == "[a0][a1]acrossfade=d=1.000:c1=tri:c2=tri[aout1]"

    def test_default_remains_equal_power(self):
        """Default curve behavior unchanged."""
        result = _compile_acrossfade_filter(
            "[a0]", "[a1]", "[aout1]",
            duration_sec=1.0,
        )
        assert "c1=qsin" in result  # Should be equal_power (qsin)
