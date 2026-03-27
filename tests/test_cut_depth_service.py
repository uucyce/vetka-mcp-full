"""
MARKER_DEPTH_SERVICE — Tests for CUT depth map generation service.

Tests: DepthMetadata, DepthResult, cache paths, FFmpeg luma generation,
generate_depth routing, build_depth_metadata, depth generate endpoint contract.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.services.cut_depth_service import (
    DEPTH_CACHE_DIR,
    DepthMetadata,
    DepthResult,
    build_depth_metadata,
    generate_depth,
    generate_depth_ffmpeg_luma,
    get_depth_cache_dir,
    get_depth_paths,
)


# ── DepthResult ──


class TestDepthResult:
    def test_default_values(self) -> None:
        r = DepthResult(source_path="/a.mp4")
        assert r.success is False
        assert r.skipped is False
        assert r.polarity == "white_near"

    def test_to_dict(self) -> None:
        r = DepthResult(source_path="/a.mp4", success=True, backend="ffmpeg-luma")
        d = r.to_dict()
        assert d["source_path"] == "/a.mp4"
        assert d["success"] is True
        assert d["backend"] == "ffmpeg-luma"


# ── DepthMetadata ──


class TestDepthMetadata:
    def test_default_source_is_none(self) -> None:
        m = DepthMetadata()
        assert m.source == "none"
        assert m.polarity == "white_near"

    def test_to_dict(self) -> None:
        m = DepthMetadata(source="auto", model="depth-pro", depth_path="/d.png")
        d = m.to_dict()
        assert d["source"] == "auto"
        assert d["model"] == "depth-pro"

    def test_from_dict(self) -> None:
        m = DepthMetadata.from_dict({
            "source": "sidecar",
            "depth_path": "/d.png",
            "model": "depth-anything-v2-small",
        })
        assert m.source == "sidecar"
        assert m.depth_path == "/d.png"

    def test_from_dict_defaults(self) -> None:
        m = DepthMetadata.from_dict({})
        assert m.source == "none"
        assert m.polarity == "white_near"


# ── Cache paths ──


class TestCachePaths:
    def test_cache_dir_is_beside_source(self) -> None:
        cache = get_depth_cache_dir("/media/videos/clip01.mp4")
        assert cache.parent.parent == Path("/media/videos")
        assert DEPTH_CACHE_DIR in str(cache)

    def test_cache_dir_uses_stem(self) -> None:
        cache = get_depth_cache_dir("/media/clip.mp4")
        assert "clip_" in cache.name

    def test_different_files_get_different_dirs(self) -> None:
        a = get_depth_cache_dir("/media/a.mp4")
        b = get_depth_cache_dir("/media/b.mp4")
        assert a != b

    def test_same_file_gets_same_dir(self) -> None:
        a = get_depth_cache_dir("/media/clip.mp4")
        b = get_depth_cache_dir("/media/clip.mp4")
        assert a == b

    def test_get_depth_paths(self) -> None:
        depth_p, preview_p = get_depth_paths("/media/clip.mp4")
        assert depth_p.name == "depth_map.png"
        assert preview_p.name == "depth_preview.png"
        assert depth_p.parent == preview_p.parent


# ── FFmpeg luma generation ──


class TestGenerateDepthFfmpegLuma:
    @patch("src.services.cut_depth_service.subprocess.run")
    def test_success_returns_depth_path(self, mock_run: MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "clip.mp4"
            src.touch()
            out_dir = Path(tmpdir) / "depth"

            # Simulate FFmpeg creating the output file
            def side_effect(*args, **kwargs):
                cmd = args[0]
                out_path = cmd[-1]
                Path(out_path).parent.mkdir(parents=True, exist_ok=True)
                Path(out_path).touch()
                return MagicMock(returncode=0, stderr=b"")
            mock_run.side_effect = side_effect

            result = generate_depth_ffmpeg_luma(str(src), out_dir)
            assert result.success is True
            assert result.backend == "ffmpeg-luma"
            assert "depth_map.png" in result.depth_path

    @patch("src.services.cut_depth_service.subprocess.run")
    def test_ffmpeg_failure_returns_error(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stderr=b"error msg")
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "clip.mp4"
            src.touch()
            result = generate_depth_ffmpeg_luma(str(src), Path(tmpdir) / "depth")
            assert result.success is False
            assert "error" in result.error.lower()


# ── generate_depth routing ──


class TestGenerateDepth:
    def test_nonexistent_source(self) -> None:
        result = generate_depth("/nonexistent/file.mp4")
        assert result.success is False
        assert result.error == "source_not_found"

    @patch("src.services.cut_depth_service.generate_depth_ffmpeg_luma")
    def test_ffmpeg_luma_backend(self, mock_gen: MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "clip.mp4"
            src.touch()
            mock_gen.return_value = DepthResult(source_path=str(src), success=True)
            result = generate_depth(str(src), backend="ffmpeg-luma")
            mock_gen.assert_called_once()
            assert result.success is True

    def test_cached_depth_returns_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "clip.mp4"
            src.touch()
            # Pre-create cached depth
            depth_p, _ = get_depth_paths(str(src))
            depth_p.parent.mkdir(parents=True, exist_ok=True)
            depth_p.touch()

            result = generate_depth(str(src), force=False)
            assert result.success is True
            assert result.skipped is True
            assert result.backend == "cached"

    def test_force_ignores_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "clip.mp4"
            src.touch()
            # Pre-create cached depth
            depth_p, _ = get_depth_paths(str(src))
            depth_p.parent.mkdir(parents=True, exist_ok=True)
            depth_p.touch()

            with patch("src.services.cut_depth_service.generate_depth_ai") as mock_ai:
                mock_ai.return_value = DepthResult(source_path=str(src), success=True, backend="ai")
                result = generate_depth(str(src), force=True)
                mock_ai.assert_called_once()


# ── build_depth_metadata ──


class TestBuildDepthMetadata:
    def test_successful_result(self) -> None:
        r = DepthResult(
            source_path="/a.mp4", success=True, backend="depth-pro",
            depth_path="/cache/depth.png", preview_path="/cache/preview.png",
        )
        meta = build_depth_metadata(r)
        assert meta.source == "auto"
        assert meta.model == "depth-pro"
        assert meta.depth_path == "/cache/depth.png"
        assert meta.generated_at != ""

    def test_failed_result(self) -> None:
        r = DepthResult(source_path="/a.mp4", success=False, error="failed")
        meta = build_depth_metadata(r)
        assert meta.source == "none"
        assert meta.depth_path == ""


# ── Endpoint contract (schema validation only) ──


class TestDepthEndpointContract:
    """Verify endpoint request/response models match the service contract."""

    def test_depth_result_serializable(self) -> None:
        r = DepthResult(source_path="/a.mp4", success=True, stats={"min": 0.1, "max": 0.9})
        d = r.to_dict()
        # Must be JSON-serializable
        json_str = json.dumps(d)
        assert "min" in json_str

    def test_depth_metadata_roundtrip(self) -> None:
        m = DepthMetadata(source="auto", model="depth-pro", depth_path="/d.png")
        d = m.to_dict()
        m2 = DepthMetadata.from_dict(d)
        assert m2.source == m.source
        assert m2.model == m.model
        assert m2.depth_path == m.depth_path
