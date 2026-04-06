"""
MARKER_B11: Unit tests for speed control filter compilation.

Tests:
- compile_video_speed_filter: setpts generation for video
- compile_audio_speed_filter: atempo/asetrate for audio
- compile_speed_filter: unified entry point
- Speed ranges: 0.25x to 4.0x
- Extreme speeds requiring chaining
- maintain_pitch toggle
- Edge cases: speed=1.0 (no-op), invalid speeds
"""
import pytest
from src.services.cut_render_pipeline import (
    compile_video_speed_filter,
    compile_audio_speed_filter,
    compile_speed_filter,
)


class TestCompileVideoSpeedFilter:
    """Test FFmpeg setpts filter generation for video speed."""

    def test_speed_2x_fast(self):
        """2x speed: setpts=0.5*PTS (halve timestamps = play faster)."""
        result = compile_video_speed_filter(2.0)
        assert result == "setpts=0.5000*PTS"

    def test_speed_0_5x_slow(self):
        """0.5x speed: setpts=2.0*PTS (double timestamps = play slower)."""
        result = compile_video_speed_filter(0.5)
        assert result == "setpts=2.0000*PTS"

    def test_speed_4x_very_fast(self):
        """4x speed: setpts=0.25*PTS."""
        result = compile_video_speed_filter(4.0)
        assert result == "setpts=0.2500*PTS"

    def test_speed_0_25x_very_slow(self):
        """0.25x speed: setpts=4.0*PTS."""
        result = compile_video_speed_filter(0.25)
        assert result == "setpts=4.0000*PTS"

    def test_speed_1x_noop(self):
        """Speed 1.0 (normal): return 'null' (no-op)."""
        result = compile_video_speed_filter(1.0)
        assert result == "null"

    def test_speed_near_1x_noop(self):
        """Speed near 1.0 (1.0001) treated as no-op."""
        result = compile_video_speed_filter(1.0001)
        assert result == "null"

    def test_speed_3x(self):
        """3x speed: setpts=0.333...*PTS."""
        result = compile_video_speed_filter(3.0)
        assert "setpts=" in result
        assert "0.3333*PTS" in result

    def test_speed_invalid_zero(self):
        """Speed 0: return 'null'."""
        result = compile_video_speed_filter(0.0)
        assert result == "null"

    def test_speed_invalid_negative(self):
        """Speed < 0: return 'null'."""
        result = compile_video_speed_filter(-1.0)
        assert result == "null"

    def test_precision_four_decimals(self):
        """PTS factor formatted to 4 decimal places."""
        result = compile_video_speed_filter(3.14159)
        assert "0.3183*PTS" in result  # 1/3.14159 ≈ 0.3183


class TestCompileAudioSpeedFilter:
    """Test FFmpeg audio filter generation for speed change."""

    def test_maintain_pitch_2x_speed(self):
        """2x speed with maintain_pitch=True: atempo=2.0."""
        result = compile_audio_speed_filter(2.0, maintain_pitch=True)
        assert result == "atempo=2.0000"

    def test_maintain_pitch_0_5x_speed(self):
        """0.5x speed with maintain_pitch=True: atempo=0.5."""
        result = compile_audio_speed_filter(0.5, maintain_pitch=True)
        assert result == "atempo=0.5000"

    def test_shift_pitch_2x_speed(self):
        """2x speed with maintain_pitch=False: asetrate (pitch shift)."""
        result = compile_audio_speed_filter(2.0, maintain_pitch=False)
        assert result == "asetrate=r=2.0000*44100"

    def test_shift_pitch_0_5x_speed(self):
        """0.5x speed with maintain_pitch=False: asetrate."""
        result = compile_audio_speed_filter(0.5, maintain_pitch=False)
        assert result == "asetrate=r=0.5000*44100"

    def test_speed_1x_noop(self):
        """Speed 1.0: return 'anull' (no-op)."""
        result = compile_audio_speed_filter(1.0, maintain_pitch=True)
        assert result == "anull"

    def test_speed_invalid_zero(self):
        """Speed 0: return 'anull'."""
        result = compile_audio_speed_filter(0.0, maintain_pitch=True)
        assert result == "anull"

    def test_speed_invalid_negative(self):
        """Speed < 0: return 'anull'."""
        result = compile_audio_speed_filter(-1.0, maintain_pitch=True)
        assert result == "anull"

    def test_extreme_speed_0_25x_chained(self):
        """0.25x (below 0.5 limit): atempo chain."""
        result = compile_audio_speed_filter(0.25, maintain_pitch=True)
        # Should chain: atempo=0.5, then atempo=0.5 again
        assert "atempo" in result
        assert result.count("atempo") >= 2

    def test_extreme_speed_4x_chained(self):
        """4x (above 100 limit, but within 0.5-100): single atempo=4.0."""
        result = compile_audio_speed_filter(4.0, maintain_pitch=True)
        assert result == "atempo=4.0000"

    def test_extreme_speed_150x_chained(self):
        """150x (exceeds 100 limit): atempo chain."""
        result = compile_audio_speed_filter(150.0, maintain_pitch=True)
        # Should chain: atempo=100, then atempo=1.5
        assert "atempo" in result
        assert result.count("atempo") >= 2

    def test_default_maintain_pitch_true(self):
        """Default maintain_pitch=True."""
        result = compile_audio_speed_filter(2.0)
        assert "atempo" in result
        assert "asetrate" not in result

    def test_precision_four_decimals(self):
        """Filter values formatted to 4 decimal places."""
        result = compile_audio_speed_filter(2.5, maintain_pitch=True)
        assert "2.5000" in result


class TestCompileSpeedFilter:
    """Test unified compile_speed_filter entry point."""

    def test_video_2x_speed(self):
        """Video at 2x: setpts=0.5*PTS."""
        result = compile_speed_filter(2.0, is_audio=False)
        assert result == "setpts=0.5000*PTS"

    def test_audio_2x_speed(self):
        """Audio at 2x: atempo=2.0."""
        result = compile_speed_filter(2.0, is_audio=True)
        assert result == "atempo=2.0000"

    def test_audio_2x_preserve_pitch(self):
        """Audio 2x with pitch preservation."""
        result = compile_speed_filter(2.0, is_audio=True, maintain_pitch=True)
        assert "atempo" in result

    def test_audio_2x_shift_pitch(self):
        """Audio 2x with pitch shift (old-school effect)."""
        result = compile_speed_filter(2.0, is_audio=True, maintain_pitch=False)
        assert "asetrate" in result

    def test_video_ignores_maintain_pitch(self):
        """maintain_pitch parameter ignored for video."""
        result1 = compile_speed_filter(2.0, is_audio=False, maintain_pitch=True)
        result2 = compile_speed_filter(2.0, is_audio=False, maintain_pitch=False)
        assert result1 == result2 == "setpts=0.5000*PTS"

    def test_video_0_5x(self):
        """Video at 0.5x (slow motion): setpts=2.0*PTS."""
        result = compile_speed_filter(0.5, is_audio=False)
        assert result == "setpts=2.0000*PTS"

    def test_audio_0_5x(self):
        """Audio at 0.5x (slow motion): atempo=0.5."""
        result = compile_speed_filter(0.5, is_audio=True)
        assert result == "atempo=0.5000"


class TestSpeedControlEdgeCases:
    """Edge cases and realistic scenarios."""

    def test_video_1x_noop(self):
        """Video 1x (normal speed): no-op."""
        result = compile_video_speed_filter(1.0)
        assert result == "null"

    def test_audio_1x_noop(self):
        """Audio 1x (normal speed): no-op."""
        result = compile_audio_speed_filter(1.0)
        assert result == "anull"

    def test_typical_slow_mo_0_5x(self):
        """Typical slow-motion: 0.5x."""
        video = compile_speed_filter(0.5, is_audio=False)
        audio = compile_speed_filter(0.5, is_audio=True, maintain_pitch=True)
        assert "setpts=2.0000*PTS" in video
        assert "atempo=0.5000" in audio

    def test_typical_fast_forward_2x(self):
        """Typical fast-forward: 2x."""
        video = compile_speed_filter(2.0, is_audio=False)
        audio = compile_speed_filter(2.0, is_audio=True, maintain_pitch=True)
        assert "setpts=0.5000*PTS" in video
        assert "atempo=2.0000" in audio

    def test_extreme_slow_0_25x(self):
        """Extreme slow-motion: 0.25x."""
        result = compile_speed_filter(0.25, is_audio=False)
        assert "setpts=4.0000*PTS" in result

    def test_extreme_fast_4x(self):
        """Extreme fast-forward: 4x."""
        result = compile_speed_filter(4.0, is_audio=False)
        assert "setpts=0.2500*PTS" in result

    def test_fractional_speed(self):
        """Fractional speed like 1.5x (realistic)."""
        result = compile_speed_filter(1.5, is_audio=False)
        assert "setpts=" in result
        assert "0.6667*PTS" in result  # 1/1.5

    def test_audio_extreme_with_chaining(self):
        """Audio at extreme speed requiring chaining."""
        result = compile_audio_speed_filter(200.0, maintain_pitch=True)
        # 200 > 100, should chain atempo=100 then atempo=2.0
        assert "atempo" in result
        parts = result.split(",")
        assert len(parts) >= 2

    def test_asetrate_with_48000_sample_rate(self):
        """asetrate always uses 44100 (default), not sample rate."""
        result = compile_audio_speed_filter(2.0, maintain_pitch=False)
        assert "44100" in result  # Hardcoded for now
