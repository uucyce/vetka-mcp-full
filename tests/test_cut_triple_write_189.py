"""
MARKER_189.3 — Tests for CUT Triple Memory Write service.
Tests JSON fallback (always written) and Qdrant integration (mocked).
"""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src.services.cut_triple_write import (
    _build_montage_records,
    _build_qdrant_chunks,
    _sec_to_timecode,
    cut_triple_write,
)


# ── Timecode conversion ──


class TestSecToTimecode:
    def test_zero(self):
        assert _sec_to_timecode(0.0) == "00:00:00:00"

    def test_one_second(self):
        assert _sec_to_timecode(1.0, fps=25) == "00:00:01:00"

    def test_fractional(self):
        # 1.5 sec at 25fps = 37 frames = 1sec 12frames
        assert _sec_to_timecode(1.5, fps=25) == "00:00:01:12"

    def test_one_minute(self):
        assert _sec_to_timecode(60.0) == "00:01:00:00"

    def test_one_hour(self):
        assert _sec_to_timecode(3600.0) == "01:00:00:00"

    def test_negative_clamps(self):
        assert _sec_to_timecode(-5.0) == "00:00:00:00"


# ── Montage sheet builder ──


class TestBuildMontageRecords:
    def test_empty_input(self):
        records = _build_montage_records([], "test_project")
        assert records == []

    def test_video_segments_only(self):
        scan_results = [
            {
                "source_path": "/tmp/test.mp4",
                "video_scan": {
                    "metadata": {"duration_sec": 30.0},
                    "segments": [
                        {"segment_id": "seg_001", "start_sec": 0.0, "end_sec": 15.0, "duration_sec": 15.0},
                        {"segment_id": "seg_002", "start_sec": 15.0, "end_sec": 30.0, "duration_sec": 15.0},
                    ],
                },
                "audio_scan": {"transcript": []},
            }
        ]
        records = _build_montage_records(scan_results, "proj1")
        assert len(records) == 2
        assert records[0]["record_id"] == "rec_0001"
        assert records[0]["scene_id"] == "seg_001"
        assert records[0]["source_file"] == "/tmp/test.mp4"
        assert records[0]["start_tc"] == "00:00:00:00"
        assert records[0]["duration_sec"] == 15.0
        assert records[1]["scene_id"] == "seg_002"

    def test_with_transcript_overlap(self):
        scan_results = [
            {
                "source_path": "/tmp/test.mp4",
                "video_scan": {
                    "metadata": {"duration_sec": 10.0},
                    "segments": [
                        {"segment_id": "seg_001", "start_sec": 0.0, "end_sec": 10.0, "duration_sec": 10.0},
                    ],
                },
                "audio_scan": {
                    "transcript": [
                        {"start_sec": 1.0, "end_sec": 3.0, "text": "Hello world"},
                        {"start_sec": 5.0, "end_sec": 7.0, "text": "Goodbye"},
                    ],
                },
            }
        ]
        records = _build_montage_records(scan_results, "proj1")
        assert len(records) == 1
        assert "Hello world" in records[0]["dialogue_text"]
        assert "Goodbye" in records[0]["dialogue_text"]

    def test_audio_only_file(self):
        scan_results = [
            {
                "source_path": "/tmp/interview.wav",
                "video_scan": None,
                "audio_scan": {
                    "metadata": {"duration_sec": 60.0},
                    "transcript": [
                        {"start_sec": 0.0, "end_sec": 5.0, "text": "Testing audio"},
                    ],
                },
            }
        ]
        records = _build_montage_records(scan_results, "proj1")
        assert len(records) == 1
        assert records[0]["dialogue_text"] == "Testing audio"
        assert records[0]["duration_sec"] == 60.0

    def test_required_fields_present(self):
        scan_results = [
            {
                "source_path": "/tmp/x.mp4",
                "video_scan": {
                    "metadata": {"duration_sec": 5.0},
                    "segments": [
                        {"segment_id": "seg_001", "start_sec": 0.0, "end_sec": 5.0, "duration_sec": 5.0},
                    ],
                },
                "audio_scan": {"transcript": []},
            }
        ]
        records = _build_montage_records(scan_results, "proj1")
        rec = records[0]
        # All required fields per vetka_montage_sheet_v1 schema
        assert "record_id" in rec
        assert "scene_id" in rec
        assert "take_id" in rec
        assert "source_file" in rec
        assert "start_tc" in rec
        assert "end_tc" in rec
        assert "duration_sec" in rec


# ── Qdrant chunk builder ──


class TestBuildQdrantChunks:
    def test_empty_input(self):
        chunks = _build_qdrant_chunks([], "proj1")
        assert chunks == []

    def test_transcript_chunks(self):
        scan_results = [
            {
                "source_path": "/tmp/test.mp4",
                "video_scan": {"metadata": {"media_type": "video"}, "segments": []},
                "audio_scan": {
                    "metadata": {"media_type": "video"},
                    "transcript": [
                        {"start_sec": 0.0, "end_sec": 3.0, "text": "Hello world", "confidence": 0.9},
                        {"start_sec": 3.0, "end_sec": 6.0, "text": "Test", "confidence": 0.8},
                    ],
                },
            }
        ]
        chunks = _build_qdrant_chunks(scan_results, "proj1")
        # 2 transcript chunks (both have text >= 3 chars)
        audio_chunks = [c for c in chunks if c["modality"] == "audio"]
        assert len(audio_chunks) == 2
        assert audio_chunks[0]["text"] == "Hello world"
        assert audio_chunks[0]["extraction_method"] == "whisper_stt"

    def test_video_segment_chunks(self):
        scan_results = [
            {
                "source_path": "/tmp/test.mp4",
                "video_scan": {
                    "metadata": {"media_type": "video", "codec": "h264", "width": 1920, "height": 1080},
                    "segments": [
                        {"segment_id": "seg_001", "start_sec": 0.0, "end_sec": 10.0, "duration_sec": 10.0},
                    ],
                },
                "audio_scan": {"transcript": [], "metadata": {}},
            }
        ]
        chunks = _build_qdrant_chunks(scan_results, "proj1")
        video_chunks = [c for c in chunks if c["modality"] == "video"]
        assert len(video_chunks) == 1
        assert "seg_001" in video_chunks[0]["text"]
        assert video_chunks[0]["scene_id"] == "seg_001"
        assert video_chunks[0]["extraction_method"] == "video_scanner_v1"

    def test_short_text_filtered(self):
        """Chunks with text < 3 chars should be filtered out."""
        scan_results = [
            {
                "source_path": "/tmp/test.mp4",
                "video_scan": {"metadata": {}, "segments": []},
                "audio_scan": {
                    "metadata": {},
                    "transcript": [
                        {"start_sec": 0.0, "end_sec": 1.0, "text": "ok"},  # too short
                        {"start_sec": 1.0, "end_sec": 2.0, "text": ""},    # empty
                    ],
                },
            }
        ]
        chunks = _build_qdrant_chunks(scan_results, "proj1")
        assert len(chunks) == 0


# ── Integration: cut_triple_write ──


class TestCutTripleWrite:
    @patch("src.services.cut_triple_write._get_triple_write_manager")
    def test_json_only_mode(self, mock_tw):
        """When Qdrant is unavailable, JSON should still be written."""
        mock_tw.return_value = None  # Qdrant unavailable

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create sandbox layout
            runtime_dir = os.path.join(tmpdir, "runtime_state")
            config_dir = os.path.join(tmpdir, "config")
            storage_dir = os.path.join(tmpdir, "storage")
            os.makedirs(runtime_dir)
            os.makedirs(config_dir)
            os.makedirs(storage_dir)

            scan_results = [
                {
                    "source_path": "/tmp/test.mp4",
                    "video_scan": {
                        "metadata": {"duration_sec": 10.0},
                        "segments": [
                            {"segment_id": "seg_001", "start_sec": 0.0, "end_sec": 10.0, "duration_sec": 10.0},
                        ],
                    },
                    "audio_scan": {
                        "transcript": [
                            {"start_sec": 0.0, "end_sec": 5.0, "text": "Hello"},
                        ],
                    },
                }
            ]

            result = cut_triple_write(
                scan_results,
                project_id="test_proj",
                sandbox_root=tmpdir,
            )

            assert result["json_written"] is True
            assert result["qdrant_written"] is False
            assert result["degraded_mode"] is True
            assert result["montage_records_count"] == 1

            # Verify montage sheet was written
            montage_path = os.path.join(runtime_dir, "montage_sheet.latest.json")
            assert os.path.isfile(montage_path)
            with open(montage_path) as f:
                sheet = json.load(f)
            assert sheet["schema_version"] == "vetka_montage_sheet_v1"
            assert len(sheet["records"]) == 1

    @patch("src.services.cut_triple_write._get_triple_write_manager")
    def test_with_qdrant(self, mock_tw_getter):
        """When Qdrant is available, both JSON and Qdrant should be written."""
        mock_tw = MagicMock()
        mock_tw.write_media_chunks.return_value = 3  # 3 chunks upserted
        mock_tw_getter.return_value = mock_tw

        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_dir = os.path.join(tmpdir, "runtime_state")
            config_dir = os.path.join(tmpdir, "config")
            storage_dir = os.path.join(tmpdir, "storage")
            os.makedirs(runtime_dir)
            os.makedirs(config_dir)
            os.makedirs(storage_dir)

            scan_results = [
                {
                    "source_path": "/tmp/test.mp4",
                    "video_scan": {
                        "metadata": {"duration_sec": 10.0, "codec": "h264"},
                        "segments": [
                            {"segment_id": "seg_001", "start_sec": 0.0, "end_sec": 10.0, "duration_sec": 10.0},
                        ],
                    },
                    "audio_scan": {
                        "metadata": {"media_type": "video"},
                        "transcript": [
                            {"start_sec": 0.0, "end_sec": 5.0, "text": "Hello world", "confidence": 0.9},
                        ],
                    },
                }
            ]

            result = cut_triple_write(
                scan_results,
                project_id="test_proj",
                sandbox_root=tmpdir,
            )

            assert result["json_written"] is True
            assert result["qdrant_written"] is True
            assert result["qdrant_chunks_count"] == 3
            assert result["degraded_mode"] is False
            mock_tw.write_media_chunks.assert_called_once()

    @patch("src.services.cut_triple_write._get_triple_write_manager")
    def test_empty_scan_results(self, mock_tw):
        """Empty scan results should produce no records and no chunks."""
        mock_tw.return_value = None

        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_dir = os.path.join(tmpdir, "runtime_state")
            config_dir = os.path.join(tmpdir, "config")
            storage_dir = os.path.join(tmpdir, "storage")
            os.makedirs(runtime_dir)
            os.makedirs(config_dir)
            os.makedirs(storage_dir)

            result = cut_triple_write(
                [],
                project_id="empty_proj",
                sandbox_root=tmpdir,
            )

            assert result["json_written"] is True
            assert result["montage_records_count"] == 0
