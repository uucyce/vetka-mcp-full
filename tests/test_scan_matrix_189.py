"""
MARKER_189.2 — Tests for VideoScanner, AudioScanner, and scan_types.
Runs without real media files (mock-based) + optional integration tests with ffmpeg.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.scanners.scan_types import (
    MediaMetadata,
    ScanResult,
    SceneSegment,
    SignalEdge,
    TranscriptSegment,
)


# ── scan_types tests ──


class TestMediaMetadata:
    def test_basic_fields(self):
        m = MediaMetadata(path="/tmp/test.mp4", duration_sec=10.5, codec="h264")
        assert m.path == "/tmp/test.mp4"
        assert m.duration_sec == 10.5
        assert m.media_type == ""  # default

    def test_defaults(self):
        m = MediaMetadata(path="/tmp/x.wav")
        assert m.width == 0
        assert m.fps == 0.0
        assert m.channels == 0


class TestSignalEdge:
    def test_basic(self):
        e = SignalEdge(
            source="a", target="b", channel="temporal",
            evidence=["gap=0.5s"], confidence=0.9, weight=0.8,
        )
        assert e.channel == "temporal"
        assert e.confidence == 0.9

    def test_defaults(self):
        e = SignalEdge(source="a", target="b", channel="semantic")
        assert e.evidence == []
        assert e.source_type == ""


class TestScanResult:
    def test_to_dict_minimal(self):
        r = ScanResult(scanner_type="video", source_path="/tmp/x.mp4")
        d = r.to_dict()
        assert d["scanner_type"] == "video"
        assert d["extraction_status"] == "pending"
        assert "segments" not in d  # empty list not serialized

    def test_to_dict_with_segments(self):
        r = ScanResult(
            scanner_type="video",
            source_path="/tmp/x.mp4",
            segments=[
                SceneSegment(segment_id="seg_001", start_sec=0.0, end_sec=5.0, duration_sec=5.0),
            ],
            extraction_status="complete",
        )
        d = r.to_dict()
        assert len(d["segments"]) == 1
        assert d["segments"][0]["segment_id"] == "seg_001"

    def test_to_dict_with_transcript(self):
        r = ScanResult(
            scanner_type="audio",
            source_path="/tmp/x.wav",
            transcript=[
                TranscriptSegment(start_sec=0.0, end_sec=2.0, text="hello"),
            ],
        )
        d = r.to_dict()
        assert d["transcript"][0]["text"] == "hello"

    def test_to_dict_with_edges(self):
        r = ScanResult(
            scanner_type="video",
            source_path="/tmp/x.mp4",
            edges=[
                SignalEdge(source="a", target="b", channel="temporal"),
            ],
        )
        d = r.to_dict()
        assert len(d["edges"]) == 1


# ── VideoScanner tests ──


class TestVideoScanner:
    def test_scan_file_not_found(self):
        from src.scanners.video_scanner import scan_video
        result = scan_video("/nonexistent/video.mp4")
        assert result.extraction_status == "error"
        assert result.extraction_error == "file_not_found"

    def test_scan_unsupported_extension(self):
        from src.scanners.video_scanner import scan_video
        with tempfile.NamedTemporaryFile(suffix=".txt") as f:
            result = scan_video(f.name)
            assert result.extraction_status == "error"
            assert "unsupported_extension" in result.extraction_error

    @patch("src.scanners.video_scanner._ffprobe_metadata")
    @patch("src.scanners.video_scanner.detect_scene_boundaries")
    @patch("src.scanners.video_scanner._extract_thumbnail_grid")
    def test_scan_with_mocked_ffprobe(self, mock_thumbs, mock_scene, mock_ffprobe):
        from src.scanners.video_scanner import scan_video
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"\x00" * 100)
            tmp_path = f.name
        try:
            mock_ffprobe.return_value = MediaMetadata(
                path=tmp_path,
                duration_sec=30.0,
                codec="h264",
                width=1920,
                height=1080,
                fps=25.0,
                media_type="video",
            )
            mock_scene.return_value = []
            mock_thumbs.return_value = []

            result = scan_video(tmp_path)
            assert result.extraction_status == "complete"
            assert result.metadata is not None
            assert result.metadata.duration_sec == 30.0
            assert len(result.segments) == 1  # single segment (no cuts)
            assert result.segments[0].duration_sec == 30.0
        finally:
            os.unlink(tmp_path)

    def test_boundaries_to_segments(self):
        from src.scanners.video_scanner import _boundaries_to_segments, SceneBoundary
        boundaries = [
            SceneBoundary(time_sec=10.0, diff_score=0.5),
            SceneBoundary(time_sec=25.0, diff_score=0.4),
        ]
        segments = _boundaries_to_segments(boundaries, 40.0, "/tmp/x.mp4")
        assert len(segments) == 3
        assert segments[0].start_sec == 0.0
        assert segments[0].end_sec == 10.0
        assert segments[1].start_sec == 10.0
        assert segments[1].end_sec == 25.0
        assert segments[2].start_sec == 25.0
        assert segments[2].end_sec == 40.0

    def test_build_structural_edges(self):
        from src.scanners.video_scanner import _build_structural_edges
        segments = [
            SceneSegment(segment_id="seg_001", start_sec=0.0, end_sec=10.0),
            SceneSegment(segment_id="seg_002", start_sec=10.0, end_sec=20.0),
            SceneSegment(segment_id="seg_003", start_sec=20.0, end_sec=30.0),
        ]
        edges = _build_structural_edges("/tmp/test.mp4", segments)
        assert len(edges) == 2
        assert edges[0].channel == "temporal"
        assert "test:seg_001" in edges[0].source
        assert "test:seg_002" in edges[0].target


# ── AudioScanner tests ──


class TestAudioScanner:
    def test_scan_file_not_found(self):
        from src.scanners.audio_scanner import scan_audio
        result = scan_audio("/nonexistent/audio.wav")
        assert result.extraction_status == "error"
        assert result.extraction_error == "file_not_found"

    def test_scan_unsupported_extension(self):
        from src.scanners.audio_scanner import scan_audio
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            result = scan_audio(f.name)
            assert result.extraction_status == "error"
            assert "unsupported_extension" in result.extraction_error

    @patch("src.scanners.audio_scanner.build_waveform_with_fallback")
    def test_scan_audio_waveform_only(self, mock_waveform):
        from src.scanners.audio_scanner import scan_audio
        mock_waveform.return_value = ([0.1, 0.5, 0.3], False, "")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"\x00" * 100)
            tmp_path = f.name
        try:
            result = scan_audio(tmp_path, waveform_bins=3, run_stt=False)
            assert result.extraction_status == "complete"
            assert result.waveform_bins == [0.1, 0.5, 0.3]
            assert result.waveform_degraded is False
            assert result.transcript == []
        finally:
            os.unlink(tmp_path)

    def test_build_audio_edges(self):
        from src.scanners.audio_scanner import _build_audio_edges
        transcript = [
            TranscriptSegment(start_sec=0.0, end_sec=2.0, text="hello", confidence=0.9),
            TranscriptSegment(start_sec=2.5, end_sec=5.0, text="world", confidence=0.8),
        ]
        edges = _build_audio_edges("/tmp/test.wav", transcript)
        assert len(edges) == 1
        assert edges[0].channel == "temporal"
        assert "0.5s" in edges[0].evidence[0]


# ── Integration: _probe_clip_duration ──


class TestProbeClipDuration:
    @patch("src.api.routes.cut_routes._probe_ffprobe_metadata")
    def test_probe_with_metadata(self, mock_probe):
        from src.api.routes.cut_routes import _probe_clip_duration
        mock_probe.return_value = {
            "available": True,
            "metadata": {"format": {"duration": "42.5"}},
        }
        assert _probe_clip_duration("/tmp/test.mp4") == 42.5

    @patch("src.api.routes.cut_routes._probe_ffprobe_metadata")
    def test_probe_failure(self, mock_probe):
        from src.api.routes.cut_routes import _probe_clip_duration
        mock_probe.return_value = {"available": False, "error": "not found"}
        assert _probe_clip_duration("/tmp/test.mp4") == 0.0


# ── 189.4: Enriched scene assembly ──


class TestEnrichedTimelineState:
    """Tests for _build_initial_timeline_state with scan matrix data."""

    def _make_project(self, source_path: str) -> dict[str, Any]:
        return {"project_id": "test", "source_path": source_path}

    def _make_store_mock(self, media_index: dict | None = None, scan_matrix: dict | None = None):
        store = MagicMock()
        store.load_media_index.return_value = media_index
        store.load_scan_matrix_result.return_value = scan_matrix
        return store

    @patch("src.api.routes.cut_routes.quick_scan_cut_source")
    def test_multi_segment_creates_multiple_clips(self, mock_scan):
        from src.api.routes.cut_routes import _build_initial_timeline_state
        mock_scan.return_value = {"stats": {}, "signals": {}}

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake video file
            video_path = os.path.join(tmpdir, "interview.mp4")
            with open(video_path, "wb") as f:
                f.write(b"\x00" * 100)

            media_index = {
                "files": {video_path: {"duration_sec": 30.0, "media_type": "video"}}
            }
            scan_matrix = {
                "items": [{
                    "source_path": video_path,
                    "video_scan": {
                        "segments": [
                            {"segment_id": "seg_001", "start_sec": 0.0, "end_sec": 10.0, "duration_sec": 10.0},
                            {"segment_id": "seg_002", "start_sec": 10.0, "end_sec": 20.0, "duration_sec": 10.0},
                            {"segment_id": "seg_003", "start_sec": 20.0, "end_sec": 30.0, "duration_sec": 10.0},
                        ],
                        "thumbnail_paths": ["/tmp/t1.jpg", "/tmp/t2.jpg", "/tmp/t3.jpg"],
                    },
                    "audio_scan": {"waveform_bins": [0.1, 0.2, 0.3]},
                }]
            }
            store = self._make_store_mock(media_index, scan_matrix)
            project = self._make_project(tmpdir)

            result = _build_initial_timeline_state(project, "main", store=store)

            video_clips = result["lanes"][0]["clips"]
            assert len(video_clips) == 3  # one per segment
            assert video_clips[0]["scene_id"] == "seg_001"
            assert video_clips[1]["scene_id"] == "seg_002"
            assert video_clips[2]["scene_id"] == "seg_003"
            # Real durations
            assert video_clips[0]["duration_sec"] == 10.0
            # Timeline cursor advances
            assert video_clips[1]["start_sec"] == 10.0
            assert video_clips[2]["start_sec"] == 20.0
            # Source in/out for sub-clips
            assert video_clips[0]["source_in"] == 0.0
            assert video_clips[0]["source_out"] == 10.0
            # Thumbnails attached
            assert video_clips[0]["thumbnail_path"] == "/tmp/t1.jpg"

    @patch("src.api.routes.cut_routes.quick_scan_cut_source")
    @patch("src.api.routes.cut_routes._probe_clip_duration")
    def test_no_scan_matrix_falls_back(self, mock_probe, mock_scan):
        from src.api.routes.cut_routes import _build_initial_timeline_state
        mock_scan.return_value = {"stats": {}, "signals": {}}
        mock_probe.return_value = 15.0

        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "clip.mp4")
            with open(video_path, "wb") as f:
                f.write(b"\x00" * 100)

            store = self._make_store_mock(None, None)
            project = self._make_project(tmpdir)

            result = _build_initial_timeline_state(project, "main", store=store)

            video_clips = result["lanes"][0]["clips"]
            assert len(video_clips) == 1
            assert video_clips[0]["duration_sec"] == 15.0
            assert video_clips[0]["scene_id"].startswith("scene_")


class TestEnrichedSceneGraph:
    """Tests for _build_initial_scene_graph with scanner edges."""

    def test_scanner_edges_injected(self):
        from src.api.routes.cut_routes import _build_initial_scene_graph

        project = {"project_id": "test"}
        timeline_state = {
            "timeline_id": "main",
            "lanes": [{
                "lane_id": "video_main",
                "lane_type": "video_main",
                "clips": [{
                    "clip_id": "clip_0001",
                    "record_id": "rec_0001",
                    "scene_id": "seg_001",
                    "take_id": "take_0001",
                    "start_sec": 0.0,
                    "duration_sec": 10.0,
                    "source_path": "/tmp/test.mp4",
                }],
            }],
        }
        store = MagicMock()
        store.load_scan_matrix_result.return_value = {
            "items": [{
                "source_path": "/tmp/test.mp4",
                "video_scan": {
                    "edges": [
                        {"source": "test:seg_001", "target": "test:seg_002",
                         "channel": "temporal", "confidence": 0.9,
                         "evidence": ["sequential"], "source_type": "video", "target_type": "video"},
                    ],
                },
                "audio_scan": {"edges": []},
            }]
        }

        graph = _build_initial_scene_graph(project, timeline_state, "main", store=store)

        scanner_edges = [e for e in graph["edges"] if e["edge_id"].startswith("edge_scanner_")]
        assert len(scanner_edges) == 1
        assert scanner_edges[0]["source"] == "test:seg_001"
        assert scanner_edges[0]["target"] == "test:seg_002"
        assert scanner_edges[0]["metadata"]["channel"] == "temporal"

    def test_no_store_no_crash(self):
        from src.api.routes.cut_routes import _build_initial_scene_graph

        project = {"project_id": "test"}
        timeline_state = {"timeline_id": "main", "lanes": []}

        graph = _build_initial_scene_graph(project, timeline_state, "main", store=None)
        assert graph["schema_version"] == "cut_scene_graph_v1"
        assert isinstance(graph["edges"], list)
