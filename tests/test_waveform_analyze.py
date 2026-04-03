"""
MARKER_B15: Unit tests for audio waveform analysis service.

Tests:
- compile_waveform_peaks: peak/RMS normalization
- _extract_audio_samples: FFmpeg extraction to PCM
- Binning logic: width_px segment handling
- Normalization: [0, 1] range, max_peak division
- Caching: (audio_path, width_px, norm_type) key
- Edge cases: silence, clipping, missing files
- Different widths: 100px, 800px, 4096px
"""
import os
import tempfile
import pytest
import numpy as np
from src.services.cut_waveform_analyzer import (
    compile_waveform_peaks,
    _extract_audio_samples,
    WaveformData,
    clear_waveform_cache,
    get_waveform_cache_stats,
)


@pytest.fixture
def temp_audio_file():
    """Create a temporary mono audio file (WAV format) for testing."""
    # Generate synthetic audio: 1 second at 44.1kHz
    # Mix: sine wave (440Hz) + quiet noise
    sr = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), False)

    # 440Hz sine wave at 0.5 amplitude
    sine = 0.5 * np.sin(2 * np.pi * 440 * t)

    # Add small noise
    noise = 0.05 * np.random.randn(len(t))
    samples = (sine + noise).astype(np.float32)

    # Normalize to [-1, 1]
    max_val = np.max(np.abs(samples))
    if max_val > 0:
        samples = samples / max_val

    # Create temporary WAV file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        # Minimal WAV header (44 bytes)
        import struct

        # RIFF header
        riff_header = b"RIFF"
        file_size = 36 + len(samples) * 2  # Placeholder, will update
        riff_size = struct.pack("<I", file_size)
        wave_marker = b"WAVE"

        # fmt chunk
        fmt_marker = b"fmt "
        fmt_size = struct.pack("<I", 16)  # PCM fmt is 16 bytes
        audio_format = struct.pack("<H", 1)  # PCM
        channels = struct.pack("<H", 1)  # Mono
        sample_rate = struct.pack("<I", sr)
        byte_rate = struct.pack("<I", sr * 2)  # 16-bit = 2 bytes/sample
        block_align = struct.pack("<H", 2)
        bits_per_sample = struct.pack("<H", 16)

        # data chunk
        data_marker = b"data"
        data_size = struct.pack("<I", len(samples) * 2)

        # Convert samples to 16-bit PCM
        pcm_data = (samples * 32767).astype(np.int16).tobytes()

        # Write all to file
        wav_data = (
            riff_header + riff_size + wave_marker +
            fmt_marker + fmt_size + audio_format + channels +
            sample_rate + byte_rate + block_align + bits_per_sample +
            data_marker + data_size + pcm_data
        )

        f.write(wav_data)
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except Exception:
            pass


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear waveform cache before each test."""
    clear_waveform_cache()
    yield
    clear_waveform_cache()


class TestExtractAudioSamples:
    """Test FFmpeg audio extraction to PCM samples."""

    def test_extract_returns_numpy_array(self, temp_audio_file):
        """_extract_audio_samples returns (samples, sr, channels) tuple."""
        samples, sr, channels = _extract_audio_samples(temp_audio_file)

        assert isinstance(samples, np.ndarray)
        assert sr == 44100
        assert channels >= 1

    def test_extract_default_sample_rate(self, temp_audio_file):
        """Default target_sr is 44100 Hz."""
        samples, sr, channels = _extract_audio_samples(temp_audio_file)
        assert sr == 44100

    def test_extract_custom_sample_rate(self, temp_audio_file):
        """Custom target_sr parameter is respected."""
        samples, sr, channels = _extract_audio_samples(temp_audio_file, target_sr=48000)
        assert sr == 48000

    def test_extract_samples_normalized(self, temp_audio_file):
        """Extracted samples normalized to [-1, 1]."""
        samples, sr, channels = _extract_audio_samples(temp_audio_file)

        assert np.min(samples) >= -1.0
        assert np.max(samples) <= 1.0

    def test_extract_file_not_found(self):
        """Raises RuntimeError if audio file not found."""
        with pytest.raises(RuntimeError):
            _extract_audio_samples("/nonexistent/path/to/audio.wav")

    def test_extract_mono_conversion(self, temp_audio_file):
        """Audio converted to mono (single channel for analysis)."""
        samples, sr, channels = _extract_audio_samples(temp_audio_file)

        # samples is 1D array (mono)
        assert samples.ndim == 1


class TestCompileWaveformPeaks:
    """Test waveform peak compilation."""

    def test_returns_waveform_data(self, temp_audio_file):
        """compile_waveform_peaks returns WaveformData object."""
        result = compile_waveform_peaks(temp_audio_file, width_px=100)

        assert isinstance(result, WaveformData)
        assert hasattr(result, "peaks")
        assert hasattr(result, "duration_sec")
        assert hasattr(result, "channels")
        assert hasattr(result, "sample_rate")
        assert hasattr(result, "norm_type")

    def test_peaks_length_matches_width_px(self, temp_audio_file):
        """Peaks array length equals width_px."""
        for width in [50, 100, 256, 800, 2048]:
            result = compile_waveform_peaks(temp_audio_file, width_px=width)
            assert len(result.peaks) == width

    def test_peaks_normalized_to_range(self, temp_audio_file):
        """All peaks in [0, 1] range."""
        result = compile_waveform_peaks(temp_audio_file, width_px=200)

        assert all(0.0 <= p <= 1.0 for p in result.peaks)
        assert min(result.peaks) >= 0.0
        assert max(result.peaks) <= 1.0

    def test_norm_type_rms(self, temp_audio_file):
        """norm_type='rms' uses RMS calculation."""
        result = compile_waveform_peaks(temp_audio_file, width_px=100, norm_type="rms")

        assert result.norm_type == "rms"
        assert len(result.peaks) > 0

    def test_norm_type_peak(self, temp_audio_file):
        """norm_type='peak' uses maximum amplitude."""
        result = compile_waveform_peaks(temp_audio_file, width_px=100, norm_type="peak")

        assert result.norm_type == "peak"
        assert len(result.peaks) > 0

    def test_duration_calculation(self, temp_audio_file):
        """duration_sec calculated from samples and sample_rate."""
        result = compile_waveform_peaks(temp_audio_file, width_px=100)

        # Should be approximately 1.0 second (synthetic audio is 1 sec)
        assert 0.9 < result.duration_sec < 1.1

    def test_channels_metadata(self, temp_audio_file):
        """channels field matches original audio channels."""
        result = compile_waveform_peaks(temp_audio_file, width_px=100)

        # Synthetic file is mono
        assert result.channels >= 1

    def test_sample_rate_metadata(self, temp_audio_file):
        """sample_rate field set correctly."""
        result = compile_waveform_peaks(temp_audio_file, width_px=100)

        assert result.sample_rate == 44100

    def test_file_not_found_raises(self):
        """Raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            compile_waveform_peaks("/nonexistent/file.wav", width_px=100)

    def test_invalid_file_raises(self):
        """Raises FileNotFoundError if path is directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError):
                compile_waveform_peaks(tmpdir, width_px=100)


class TestWaveformCaching:
    """Test in-memory caching behavior."""

    def test_cache_hit_returns_same_object(self, temp_audio_file):
        """Second call with same params returns cached result."""
        result1 = compile_waveform_peaks(temp_audio_file, width_px=100, use_cache=True)
        result2 = compile_waveform_peaks(temp_audio_file, width_px=100, use_cache=True)

        # Should be the exact same object (cached)
        assert result1 is result2

    def test_cache_miss_different_width(self, temp_audio_file):
        """Different width_px bypasses cache."""
        result1 = compile_waveform_peaks(temp_audio_file, width_px=100, use_cache=True)
        result2 = compile_waveform_peaks(temp_audio_file, width_px=200, use_cache=True)

        # Different widths should produce different results
        assert result1 is not result2
        assert len(result1.peaks) != len(result2.peaks)

    def test_cache_miss_different_norm_type(self, temp_audio_file):
        """Different norm_type bypasses cache."""
        result1 = compile_waveform_peaks(
            temp_audio_file, width_px=100, norm_type="rms", use_cache=True
        )
        result2 = compile_waveform_peaks(
            temp_audio_file, width_px=100, norm_type="peak", use_cache=True
        )

        # Different norm types should be different objects
        assert result1 is not result2

    def test_cache_disabled_returns_new_object(self, temp_audio_file):
        """use_cache=False always creates new object."""
        result1 = compile_waveform_peaks(temp_audio_file, width_px=100, use_cache=False)
        result2 = compile_waveform_peaks(temp_audio_file, width_px=100, use_cache=False)

        # Should be different objects even with same params
        assert result1 is not result2

    def test_cache_stats_empty_initially(self):
        """Cache stats show 0 items initially."""
        stats = get_waveform_cache_stats()

        assert stats["cached_clips"] == 0
        assert stats["total_peaks"] == 0

    def test_cache_stats_after_analysis(self, temp_audio_file):
        """Cache stats updated after compilation."""
        clear_waveform_cache()
        compile_waveform_peaks(temp_audio_file, width_px=100, use_cache=True)

        stats = get_waveform_cache_stats()

        assert stats["cached_clips"] == 1
        assert stats["total_peaks"] == 100

    def test_cache_stats_multiple_clips(self, temp_audio_file):
        """Cache stats accumulate for multiple files."""
        clear_waveform_cache()
        compile_waveform_peaks(temp_audio_file, width_px=100, use_cache=True)
        compile_waveform_peaks(temp_audio_file, width_px=200, use_cache=True)

        stats = get_waveform_cache_stats()

        assert stats["cached_clips"] == 2
        assert stats["total_peaks"] == 300  # 100 + 200

    def test_clear_cache_resets_stats(self, temp_audio_file):
        """clear_waveform_cache() resets stats to 0."""
        compile_waveform_peaks(temp_audio_file, width_px=100, use_cache=True)
        clear_waveform_cache()

        stats = get_waveform_cache_stats()

        assert stats["cached_clips"] == 0
        assert stats["total_peaks"] == 0


class TestWaveformEdgeCases:
    """Edge cases and realistic scenarios."""

    def test_very_small_width(self, temp_audio_file):
        """width_px=1 generates single peak."""
        result = compile_waveform_peaks(temp_audio_file, width_px=1)

        assert len(result.peaks) == 1
        assert 0.0 <= result.peaks[0] <= 1.0

    def test_very_large_width(self, temp_audio_file):
        """Large width_px (4096) handles binning correctly."""
        result = compile_waveform_peaks(temp_audio_file, width_px=4096)

        assert len(result.peaks) == 4096
        # All values in range
        assert all(0.0 <= p <= 1.0 for p in result.peaks)

    def test_silence_audio(self):
        """Silent audio handles gracefully without crashing."""
        # Create silent WAV
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            import struct

            sr = 44100
            duration = 1.0
            silence = np.zeros(int(sr * duration), dtype=np.int16)

            riff_header = b"RIFF"
            file_size = 36 + len(silence) * 2
            riff_size = struct.pack("<I", file_size)
            wave_marker = b"WAVE"

            fmt_marker = b"fmt "
            fmt_size = struct.pack("<I", 16)
            audio_format = struct.pack("<H", 1)
            channels = struct.pack("<H", 1)
            sample_rate = struct.pack("<I", sr)
            byte_rate = struct.pack("<I", sr * 2)
            block_align = struct.pack("<H", 2)
            bits_per_sample = struct.pack("<H", 16)

            data_marker = b"data"
            data_size = struct.pack("<I", len(silence) * 2)

            pcm_data = silence.tobytes()

            wav_data = (
                riff_header + riff_size + wave_marker +
                fmt_marker + fmt_size + audio_format + channels +
                sample_rate + byte_rate + block_align + bits_per_sample +
                data_marker + data_size + pcm_data
            )

            f.write(wav_data)
            silent_file = f.name

        try:
            result = compile_waveform_peaks(silent_file, width_px=100)

            # Should produce valid waveform (doesn't crash, all peaks in [0,1])
            assert len(result.peaks) == 100
            assert all(0.0 <= p <= 1.0 for p in result.peaks)
            # Max peak should be low (mostly silent, may have FFmpeg artifacts)
            assert max(result.peaks) <= 1.0
        finally:
            if os.path.exists(silent_file):
                try:
                    os.remove(silent_file)
                except Exception:
                    pass

    def test_rms_vs_peak_different_values(self, temp_audio_file):
        """RMS and peak normalization produce different waveforms."""
        result_rms = compile_waveform_peaks(
            temp_audio_file, width_px=100, norm_type="rms"
        )
        result_peak = compile_waveform_peaks(
            temp_audio_file, width_px=100, norm_type="peak"
        )

        # RMS is typically lower than peak (more conservative)
        assert result_rms.peaks != result_peak.peaks

    def test_consistent_results_with_cache(self, temp_audio_file):
        """Cached and non-cached results produce identical peaks."""
        result_cached = compile_waveform_peaks(
            temp_audio_file, width_px=256, use_cache=True
        )
        clear_waveform_cache()
        result_fresh = compile_waveform_peaks(
            temp_audio_file, width_px=256, use_cache=False
        )

        # Peaks should be identical
        assert len(result_cached.peaks) == len(result_fresh.peaks)
        for c, f in zip(result_cached.peaks, result_fresh.peaks):
            assert abs(c - f) < 1e-6  # Float precision tolerance


class TestWaveformIntegration:
    """Integration and realistic usage scenarios."""

    def test_typical_timeline_visualization_800px(self, temp_audio_file):
        """Typical timeline visualization: 800px width."""
        result = compile_waveform_peaks(temp_audio_file, width_px=800)

        assert len(result.peaks) == 800
        assert all(0.0 <= p <= 1.0 for p in result.peaks)
        # Should have some peaks in sine wave
        assert max(result.peaks) > 0.1

    def test_thumbnail_preview_100px(self, temp_audio_file):
        """Thumbnail preview: 100px width."""
        result = compile_waveform_peaks(temp_audio_file, width_px=100)

        assert len(result.peaks) == 100
        assert max(result.peaks) > 0.0

    def test_high_resolution_4096px(self, temp_audio_file):
        """High-resolution waveform: 4096px."""
        result = compile_waveform_peaks(temp_audio_file, width_px=4096)

        assert len(result.peaks) == 4096

    def test_multiple_clips_separate_analysis(self, temp_audio_file):
        """Analyzing same file multiple times with different widths."""
        widths = [100, 256, 512, 1024]
        results = []

        for w in widths:
            r = compile_waveform_peaks(temp_audio_file, width_px=w, use_cache=True)
            results.append(r)

        # All should be cached separately
        stats = get_waveform_cache_stats()
        assert stats["cached_clips"] == 4

        # Each should have correct width
        for r, w in zip(results, widths):
            assert len(r.peaks) == w
