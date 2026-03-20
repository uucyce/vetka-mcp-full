"""
MARKER_B1 — Tests for cut_codec_probe.py.

Tests ProbeResult construction, color space inference, fps parsing,
and probe_file() with mocked ffprobe output.

@task: tb_1773981821_8
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.services.cut_codec_probe import (
    AudioStream,
    ProbeResult,
    VideoStream,
    _infer_bit_depth,
    _infer_color_space,
    _parse_fps,
    probe_duration,
    probe_file,
)


# ---------------------------------------------------------------------------
# Fixtures — mock ffprobe JSON output
# ---------------------------------------------------------------------------

MOCK_FFPROBE_H264 = {
    "streams": [
        {
            "index": 0,
            "codec_name": "h264",
            "codec_type": "video",
            "codec_tag_string": "avc1",
            "profile": "High",
            "width": 1920,
            "height": 1080,
            "r_frame_rate": "30000/1001",
            "avg_frame_rate": "30000/1001",
            "pix_fmt": "yuv420p",
            "color_primaries": "bt709",
            "color_transfer": "bt709",
            "color_space": "bt709",
        },
        {
            "index": 1,
            "codec_name": "aac",
            "codec_type": "audio",
            "sample_rate": "48000",
            "channels": 2,
            "bits_per_raw_sample": "0",
        },
    ],
    "format": {
        "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
        "duration": "120.500",
        "bit_rate": "8500000",
        "size": "128000000",
    },
}

MOCK_FFPROBE_PRORES = {
    "streams": [
        {
            "index": 0,
            "codec_name": "prores",
            "codec_type": "video",
            "profile": "422 HQ",
            "width": 3840,
            "height": 2160,
            "r_frame_rate": "24000/1001",
            "pix_fmt": "yuv422p10le",
            "color_primaries": "bt2020",
            "color_transfer": "arib-std-b67",
        },
        {
            "index": 1,
            "codec_name": "pcm_s24le",
            "codec_type": "audio",
            "sample_rate": "96000",
            "channels": 6,
        },
    ],
    "format": {
        "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
        "duration": "300.000",
        "bit_rate": "220000000",
        "size": "8250000000",
    },
}

MOCK_FFPROBE_AUDIO_ONLY = {
    "streams": [
        {
            "index": 0,
            "codec_name": "pcm_s16le",
            "codec_type": "audio",
            "sample_rate": "44100",
            "channels": 2,
        },
    ],
    "format": {
        "format_name": "wav",
        "duration": "60.000",
        "bit_rate": "1411200",
        "size": "10584000",
    },
}


def _mock_run_factory(payload: dict):
    """Create a mock subprocess.run that returns given JSON payload."""

    def _mock_run(cmd, **kwargs):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = json.dumps(payload)
        mock.stderr = ""
        return mock

    return _mock_run


# ---------------------------------------------------------------------------
# Unit tests — helper functions
# ---------------------------------------------------------------------------

class TestParsesFps:
    def test_ntsc_30(self):
        assert abs(_parse_fps("30000/1001") - 29.97) < 0.01

    def test_integer_25(self):
        assert _parse_fps("25/1") == 25.0

    def test_plain_float(self):
        assert _parse_fps("23.976") == 23.976

    def test_zero(self):
        assert _parse_fps("0/0") == 0.0

    def test_empty(self):
        assert _parse_fps("") == 0.0

    def test_24000_1001(self):
        assert abs(_parse_fps("24000/1001") - 23.976) < 0.01


class TestInferColorSpace:
    def test_bt709(self):
        assert _infer_color_space("bt709", "yuv420p") == "Rec.709"

    def test_bt2020(self):
        assert _infer_color_space("bt2020", "yuv420p10le") == "Rec.2020"

    def test_dci_p3(self):
        assert _infer_color_space("smpte432", "yuv444p10le") == "DCI-P3"

    def test_unknown_primaries_8bit(self):
        assert _infer_color_space("", "yuv420p") == "Rec.709"

    def test_unknown_primaries_10bit(self):
        result = _infer_color_space("", "yuv420p10le")
        assert "709" in result and "assumed" in result

    def test_explicit_unknown(self):
        assert _infer_color_space("unknown", "yuv420p") == "Rec.709"


class TestInferBitDepth:
    def test_yuv420p(self):
        assert _infer_bit_depth("yuv420p") == 8

    def test_yuv422p10le(self):
        assert _infer_bit_depth("yuv422p10le") == 10

    def test_yuv444p12le(self):
        assert _infer_bit_depth("yuv444p12le") == 12

    def test_unknown_with_10(self):
        assert _infer_bit_depth("some10bit") == 10

    def test_fallback_8(self):
        assert _infer_bit_depth("weird_format") == 8


# ---------------------------------------------------------------------------
# Unit tests — ProbeResult
# ---------------------------------------------------------------------------

class TestProbeResult:
    def test_ok_true(self):
        r = ProbeResult(available=True, exists=True, error="")
        assert r.ok is True

    def test_ok_false_no_ffprobe(self):
        r = ProbeResult(available=False)
        assert r.ok is False

    def test_ok_false_error(self):
        r = ProbeResult(available=True, exists=True, error="some error")
        assert r.ok is False

    def test_resolution_labels(self):
        assert ProbeResult(height=2160).resolution_label == "4K"
        assert ProbeResult(height=1080).resolution_label == "1080p"
        assert ProbeResult(height=720).resolution_label == "720p"
        assert ProbeResult(height=480).resolution_label == "SD"
        assert ProbeResult(height=4320).resolution_label == "8K"
        assert ProbeResult(height=0).resolution_label == "unknown"

    def test_to_dict_has_required_keys(self):
        r = ProbeResult(
            available=True, exists=True, path="/test.mp4",
            video_codec="h264", width=1920, height=1080,
        )
        d = r.to_dict()
        for key in ["path", "ok", "video_codec", "audio_codec", "width",
                     "height", "fps", "color_space", "bit_depth",
                     "resolution_label", "duration_sec", "bitrate_kbps"]:
            assert key in d, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# Integration tests — probe_file with mocked subprocess
# ---------------------------------------------------------------------------

class TestProbeFileH264:
    @patch("src.services.cut_codec_probe.shutil.which", return_value="/usr/bin/ffprobe")
    @patch("src.services.cut_codec_probe.subprocess.run", side_effect=_mock_run_factory(MOCK_FFPROBE_H264))
    def test_h264_basic(self, mock_run, mock_which, tmp_path):
        f = tmp_path / "test.mp4"
        f.write_bytes(b"\x00" * 100)
        r = probe_file(f)
        assert r.ok
        assert r.video_codec == "h264"
        assert r.width == 1920
        assert r.height == 1080
        assert abs(r.fps - 29.97) < 0.01
        assert r.audio_codec == "aac"
        assert r.channels == 2
        assert r.sample_rate == 48000
        assert r.color_space == "Rec.709"
        assert r.bit_depth == 8
        assert r.resolution_label == "1080p"
        assert r.duration_sec == 120.5
        assert r.bitrate_kbps == 8500
        assert r.container == "mov,mp4,m4a,3gp,3g2,mj2"

    @patch("src.services.cut_codec_probe.shutil.which", return_value="/usr/bin/ffprobe")
    @patch("src.services.cut_codec_probe.subprocess.run", side_effect=_mock_run_factory(MOCK_FFPROBE_H264))
    def test_to_dict_complete(self, mock_run, mock_which, tmp_path):
        f = tmp_path / "test.mp4"
        f.write_bytes(b"\x00" * 100)
        r = probe_file(f)
        d = r.to_dict()
        assert d["ok"] is True
        assert "video_stream" in d
        assert d["video_stream"]["profile"] == "High"
        assert d["audio_stream"]["codec"] == "aac"
        assert d["video_stream_count"] == 1
        assert d["audio_stream_count"] == 1


class TestProbeFileProRes:
    @patch("src.services.cut_codec_probe.shutil.which", return_value="/usr/bin/ffprobe")
    @patch("src.services.cut_codec_probe.subprocess.run", side_effect=_mock_run_factory(MOCK_FFPROBE_PRORES))
    def test_prores_4k(self, mock_run, mock_which, tmp_path):
        f = tmp_path / "test.mov"
        f.write_bytes(b"\x00" * 100)
        r = probe_file(f)
        assert r.ok
        assert r.video_codec == "prores"
        assert r.width == 3840
        assert r.height == 2160
        assert r.resolution_label == "4K"
        assert r.color_space == "Rec.2020"
        assert r.bit_depth == 10
        assert r.audio_codec == "pcm_s24le"
        assert r.audio.bit_depth == 24
        assert r.audio.channels == 6
        assert r.audio.sample_rate == 96000


class TestProbeFileAudioOnly:
    @patch("src.services.cut_codec_probe.shutil.which", return_value="/usr/bin/ffprobe")
    @patch("src.services.cut_codec_probe.subprocess.run", side_effect=_mock_run_factory(MOCK_FFPROBE_AUDIO_ONLY))
    def test_audio_only(self, mock_run, mock_which, tmp_path):
        f = tmp_path / "test.wav"
        f.write_bytes(b"\x00" * 100)
        r = probe_file(f)
        assert r.ok
        assert r.video is None
        assert r.video_codec == ""
        assert r.audio_codec == "pcm_s16le"
        assert r.audio.bit_depth == 16
        assert r.channels == 2
        assert r.sample_rate == 44100


class TestProbeFileErrors:
    def test_ffprobe_not_found(self, tmp_path):
        f = tmp_path / "test.mp4"
        f.write_bytes(b"\x00" * 100)
        with patch("src.services.cut_codec_probe.shutil.which", return_value=None):
            r = probe_file(f)
        assert not r.ok
        assert r.error == "ffprobe_not_found"
        assert r.available is False

    @patch("src.services.cut_codec_probe.shutil.which", return_value="/usr/bin/ffprobe")
    def test_file_not_found(self, mock_which):
        r = probe_file("/nonexistent/file.mp4")
        assert not r.ok
        assert r.error == "file_not_found"

    @patch("src.services.cut_codec_probe.shutil.which", return_value="/usr/bin/ffprobe")
    @patch("src.services.cut_codec_probe.subprocess.run", side_effect=TimeoutError)
    def test_timeout(self, mock_run, mock_which, tmp_path):
        f = tmp_path / "test.mp4"
        f.write_bytes(b"\x00" * 100)
        r = probe_file(f)
        assert not r.ok
        assert "timeout" in r.error.lower() or "error" in r.error.lower()

    @patch("src.services.cut_codec_probe.shutil.which", return_value="/usr/bin/ffprobe")
    def test_ffprobe_nonzero_exit(self, mock_which, tmp_path):
        f = tmp_path / "test.mp4"
        f.write_bytes(b"\x00" * 100)
        mock = MagicMock()
        mock.returncode = 1
        mock.stderr = "Invalid data found"
        mock.stdout = ""
        with patch("src.services.cut_codec_probe.subprocess.run", return_value=mock):
            r = probe_file(f)
        assert not r.ok
        assert "ffprobe_failed" in r.error


class TestProbeDuration:
    @patch("src.services.cut_codec_probe.shutil.which", return_value="/usr/bin/ffprobe")
    @patch("src.services.cut_codec_probe.subprocess.run", side_effect=_mock_run_factory(MOCK_FFPROBE_H264))
    def test_returns_duration(self, mock_run, mock_which, tmp_path):
        f = tmp_path / "test.mp4"
        f.write_bytes(b"\x00" * 100)
        assert probe_duration(f) == 120.5

    def test_returns_zero_on_failure(self):
        assert probe_duration("/nonexistent/file.mp4") == 0.0
