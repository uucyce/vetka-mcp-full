"""
MARKER_B48: Tests for Multicam Sync Engine (FCP7 Ch.46-47).
Tests waveform cross-correlation sync, timecode sync, marker sync,
and multicam switch clip generation.
"""
import math
import struct
from pathlib import Path
from unittest.mock import patch

import pytest

from src.services.cut_multicam_sync import (
    MulticamAngle,
    MulticamClip,
    sync_by_waveform,
    sync_by_timecode,
    sync_by_markers,
    build_multicam_switch_clip,
    _timecode_to_seconds,
    _extract_timecode_from_file,
    _probe_duration,
)
from src.services.cut_ffmpeg_waveform import HAS_FFMPEG


# ─── Timecode parsing ───


class TestTimecodeToSeconds:
    def test_zero(self):
        assert _timecode_to_seconds("00:00:00:00") == 0.0

    def test_one_second(self):
        assert _timecode_to_seconds("00:00:01:00", fps=25.0) == 1.0

    def test_one_frame(self):
        assert abs(_timecode_to_seconds("00:00:00:01", fps=25.0) - 0.04) < 0.001

    def test_one_minute(self):
        assert _timecode_to_seconds("00:01:00:00") == 60.0

    def test_complex_tc(self):
        # 01:02:03:12 at 25fps = 3600 + 120 + 3 + 12/25 = 3723.48
        result = _timecode_to_seconds("01:02:03:12", fps=25.0)
        assert abs(result - 3723.48) < 0.01

    def test_semicolon_separator(self):
        """Drop-frame timecode uses semicolons."""
        result = _timecode_to_seconds("00:00:10;15", fps=30.0)
        assert abs(result - 10.5) < 0.01

    def test_invalid(self):
        assert _timecode_to_seconds("invalid") == 0.0
        assert _timecode_to_seconds("00:00:00") == 0.0  # only 3 parts


# ─── Marker sync ───


class TestSyncByMarkers:
    def test_basic_two_angles(self):
        mc = sync_by_markers(
            ["/cam_a.mp4", "/cam_b.mp4"],
            [5.0, 7.0],  # cam_b starts 2s later
        )
        assert len(mc.angles) == 2
        assert mc.angles[0].offset_sec == 0.0   # reference
        assert mc.angles[0].is_reference is True
        assert mc.angles[1].offset_sec == 2.0    # 7 - 5 = 2s later

    def test_three_angles(self):
        mc = sync_by_markers(
            ["/a.mp4", "/b.mp4", "/c.mp4"],
            [10.0, 8.0, 12.0],
        )
        assert mc.angles[0].offset_sec == 0.0   # reference
        assert mc.angles[1].offset_sec == -2.0   # starts 2s earlier
        assert mc.angles[2].offset_sec == 2.0    # starts 2s later
        assert mc.sync_method == "marker"

    def test_mismatched_lengths(self):
        mc = sync_by_markers(["/a.mp4"], [1.0, 2.0])
        assert len(mc.angles) == 0

    def test_empty(self):
        mc = sync_by_markers([], [])
        assert len(mc.angles) == 0


# ─── MulticamClip serialization ───


class TestMulticamClipSerialization:
    def test_to_dict(self):
        mc = MulticamClip(
            multicam_id="test123",
            angles=[
                MulticamAngle(0, "/a.mp4", "CamA", 0.0, 10.0, 1.0, True),
                MulticamAngle(1, "/b.mp4", "CamB", 1.5, 10.0, 0.85, False),
            ],
            sync_method="waveform",
            reference_index=0,
            total_duration_sec=11.5,
        )
        d = mc.to_dict()
        assert d["multicam_id"] == "test123"
        assert len(d["angles"]) == 2
        assert d["angles"][0]["is_reference"] is True
        assert d["angles"][1]["offset_sec"] == 1.5
        assert d["sync_method"] == "waveform"


# ─── Multicam switch clip ───


class TestBuildMulticamSwitchClip:
    def _make_multicam(self) -> MulticamClip:
        return MulticamClip(
            multicam_id="mc_test",
            angles=[
                MulticamAngle(0, "/cam_a.mp4", "A", 0.0, 60.0, 1.0, True),
                MulticamAngle(1, "/cam_b.mp4", "B", 2.0, 60.0, 0.9, False),
            ],
        )

    def test_switch_to_reference(self):
        mc = self._make_multicam()
        clip = build_multicam_switch_clip(mc, 0, switch_time_sec=10.0, duration_sec=5.0)
        assert clip["source_path"] == "/cam_a.mp4"
        assert clip["start_sec"] == 10.0
        assert clip["duration_sec"] == 5.0
        assert clip["source_in"] == 10.0  # reference has 0 offset
        assert clip["angle_index"] == 0

    def test_switch_to_offset_angle(self):
        mc = self._make_multicam()
        clip = build_multicam_switch_clip(mc, 1, switch_time_sec=10.0, duration_sec=5.0)
        assert clip["source_path"] == "/cam_b.mp4"
        assert clip["source_in"] == 8.0  # 10.0 - 2.0 offset

    def test_invalid_angle(self):
        mc = self._make_multicam()
        with pytest.raises(ValueError):
            build_multicam_switch_clip(mc, 5, 10.0, 5.0)

    def test_switch_before_angle_start(self):
        """Switch at t=0 when angle has offset=5 → source_in clamped to 0."""
        mc = MulticamClip(
            multicam_id="mc",
            angles=[
                MulticamAngle(0, "/a.mp4", "A", 0.0, 60.0, 1.0, True),
                MulticamAngle(1, "/b.mp4", "B", 5.0, 60.0, 0.9, False),
            ],
        )
        clip = build_multicam_switch_clip(mc, 1, switch_time_sec=2.0, duration_sec=3.0)
        assert clip["source_in"] == 0.0  # clamped, can't go negative


# ─── Waveform sync (requires FFmpeg) ───


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
class TestSyncByWaveform:
    def _write_sine_wav(self, path: Path, freq: float, duration_sec: float,
                        offset_sec: float = 0.0, sample_rate: int = 16000) -> None:
        """Write WAV with sine tone, optionally prepended with silence."""
        silent_samples = int(sample_rate * offset_sec)
        tone_samples = int(sample_rate * duration_sec)
        total = silent_samples + tone_samples
        samples = []
        for i in range(total):
            if i < silent_samples:
                samples.append(0)
            else:
                t = (i - silent_samples) / sample_rate
                samples.append(int(16000 * math.sin(2 * math.pi * freq * t)))
        pcm = struct.pack(f"<{total}h", *[max(-32768, min(32767, s)) for s in samples])
        data_size = len(pcm)
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", 36 + data_size, b"WAVE",
            b"fmt ", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16,
            b"data", data_size,
        )
        path.write_bytes(header + pcm)

    def test_identical_files_structure(self, tmp_path: Path):
        """Two identical files → returns valid multicam structure."""
        f1 = tmp_path / "cam_a.wav"
        f2 = tmp_path / "cam_b.wav"
        self._write_sine_wav(f1, 440, 2.0)
        self._write_sine_wav(f2, 440, 2.0)

        mc = sync_by_waveform([str(f1), str(f2)])
        assert len(mc.angles) == 2
        assert mc.angles[0].is_reference is True
        assert mc.sync_method == "waveform"
        assert mc.multicam_id  # has UUID
        # Note: identical pure sine waves can correlate at any lag
        # Real-world audio has enough variation for precise sync

    def test_offset_detection(self, tmp_path: Path):
        """Cam B has 0.5s silence prepended → offset should be ~0.5s."""
        f1 = tmp_path / "cam_a.wav"
        f2 = tmp_path / "cam_b.wav"
        self._write_sine_wav(f1, 440, 2.0, offset_sec=0.0)
        self._write_sine_wav(f2, 440, 2.0, offset_sec=0.5)

        mc = sync_by_waveform([str(f1), str(f2)], max_lag_sec=5.0)
        # Offset should be approximately 0.5s (within 100ms tolerance)
        assert abs(mc.angles[1].offset_sec - 0.5) < 0.15
        assert mc.angles[1].sync_confidence > 0.3

    def test_three_angles(self, tmp_path: Path):
        """Three cameras, different offsets."""
        f1 = tmp_path / "a.wav"
        f2 = tmp_path / "b.wav"
        f3 = tmp_path / "c.wav"
        self._write_sine_wav(f1, 440, 2.0, offset_sec=0.0)
        self._write_sine_wav(f2, 440, 2.0, offset_sec=0.0)  # same as reference
        self._write_sine_wav(f3, 440, 2.0, offset_sec=1.0)   # 1s offset

        mc = sync_by_waveform([str(f1), str(f2), str(f3)], max_lag_sec=5.0)
        assert len(mc.angles) == 3
        assert mc.multicam_id  # should have UUID
        assert mc.sync_method == "waveform"


# ─── Timecode sync (mocked) ───


class TestSyncByTimecode:
    def test_no_timecodes(self):
        """Files without timecodes → zero offsets, zero confidence."""
        with patch("src.services.cut_multicam_sync._extract_timecode_from_file", return_value=None):
            with patch("src.services.cut_multicam_sync._probe_duration", return_value=10.0):
                mc = sync_by_timecode(["/a.mp4", "/b.mp4"])
        assert len(mc.angles) == 2
        assert all(a.sync_confidence == 0.0 for a in mc.angles)

    def test_with_timecodes(self):
        """Two files with different timecodes → correct offset."""
        def mock_tc(path):
            return "01:00:00:00" if "a" in path else "01:00:05:00"

        with patch("src.services.cut_multicam_sync._extract_timecode_from_file", side_effect=mock_tc):
            with patch("src.services.cut_multicam_sync._probe_duration", return_value=60.0):
                mc = sync_by_timecode(["/a.mp4", "/b.mp4"], fps=25.0)

        assert len(mc.angles) == 2
        # a starts at 01:00:00:00, b at 01:00:05:00 → b is 5s later
        assert mc.angles[0].offset_sec == 0.0  # reference (earliest)
        assert abs(mc.angles[1].offset_sec - 5.0) < 0.01
        assert mc.sync_method == "timecode"
