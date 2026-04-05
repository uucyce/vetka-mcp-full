"""
MARKER_173.6 — Clip Proxy Generation Worker tests.

Tests:
- ProxyWorker file hashing and path generation
- Freshness detection (skip if proxy newer than source)
- Force regeneration flag
- FFmpeg error handling (mocked)
- Batch generation
- Proxy listing and cleanup
- API endpoints: /proxy/generate, /proxy/list, /proxy/path
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.cut_proxy_worker import (
    ProxyWorker,
    ProxyResult,
    ProxySpec,
    PROXY_720P,
    PROXY_480P,
    _human_size,
)


class TestProxySpec:
    def test_default_720p(self):
        s = PROXY_720P
        assert s.width == 1280
        assert s.height == 720
        assert s.codec == "libx264"

    def test_480p(self):
        s = PROXY_480P
        assert s.width == 854
        assert s.height == 480


class TestHumanSize:
    def test_bytes(self):
        assert _human_size(512) == "512B"

    def test_kilobytes(self):
        assert "KB" in _human_size(2048)

    def test_megabytes(self):
        assert "MB" in _human_size(5 * 1024 * 1024)

    def test_gigabytes(self):
        assert "GB" in _human_size(2 * 1024 * 1024 * 1024)


class TestProxyWorkerPaths:
    def test_content_hash_deterministic(self, tmp_path):
        source = tmp_path / "test.mp4"
        source.write_bytes(b"fake video data")
        worker = ProxyWorker(str(tmp_path))
        h1 = worker._content_hash(str(source))
        h2 = worker._content_hash(str(source))
        assert h1 == h2
        assert len(h1) == 16

    def test_content_hash_different_files(self, tmp_path):
        a = tmp_path / "a.mp4"
        b = tmp_path / "b.mp4"
        a.write_bytes(b"aaa")
        b.write_bytes(b"bbb")
        worker = ProxyWorker(str(tmp_path))
        assert worker._content_hash(str(a)) != worker._content_hash(str(b))

    def test_proxy_path_format(self, tmp_path):
        source = tmp_path / "my_video.mp4"
        source.write_bytes(b"data")
        worker = ProxyWorker(str(tmp_path))
        path = worker._proxy_path_for(str(source))
        assert "_proxy_720p" in path.name
        assert path.suffix == ".mp4"
        assert "proxies" in str(path)


class TestProxyFreshness:
    def test_no_proxy_not_fresh(self, tmp_path):
        source = tmp_path / "video.mp4"
        source.write_bytes(b"data")
        worker = ProxyWorker(str(tmp_path))
        proxy_path = worker._proxy_path_for(str(source))
        assert not worker._is_proxy_fresh(str(source), proxy_path)

    def test_existing_proxy_is_fresh(self, tmp_path):
        source = tmp_path / "video.mp4"
        source.write_bytes(b"data")
        worker = ProxyWorker(str(tmp_path))
        proxy_path = worker._proxy_path_for(str(source))
        proxy_path.parent.mkdir(parents=True, exist_ok=True)
        # Create proxy newer than source
        time.sleep(0.01)
        proxy_path.write_bytes(b"proxy data")
        assert worker._is_proxy_fresh(str(source), proxy_path)

    def test_force_overrides_fresh(self, tmp_path):
        source = tmp_path / "video.mp4"
        source.write_bytes(b"data")
        worker = ProxyWorker(str(tmp_path), force=True)
        proxy_path = worker._proxy_path_for(str(source))
        proxy_path.parent.mkdir(parents=True, exist_ok=True)
        time.sleep(0.01)
        proxy_path.write_bytes(b"proxy data")
        assert not worker._is_proxy_fresh(str(source), proxy_path)


class TestProxyGenerate:
    @patch("src.services.cut_proxy_worker.HAS_FFMPEG", False)
    def test_no_ffmpeg(self, tmp_path):
        source = tmp_path / "video.mp4"
        source.write_bytes(b"data")
        worker = ProxyWorker(str(tmp_path))
        result = worker.generate(str(source))
        assert not result.success
        assert "ffmpeg_not_available" in result.error

    def test_source_not_found(self, tmp_path):
        worker = ProxyWorker(str(tmp_path))
        result = worker.generate("/nonexistent/video.mp4")
        assert not result.success
        assert "source_not_found" in result.error

    def test_skip_fresh_proxy(self, tmp_path):
        source = tmp_path / "video.mp4"
        source.write_bytes(b"data")
        worker = ProxyWorker(str(tmp_path))
        proxy_path = worker._proxy_path_for(str(source))
        proxy_path.parent.mkdir(parents=True, exist_ok=True)
        time.sleep(0.01)
        proxy_path.write_bytes(b"proxy data")

        result = worker.generate(str(source))
        assert result.success
        assert result.skipped

    @patch("src.services.cut_proxy_worker.HAS_FFMPEG", True)
    @patch("src.services.cut_proxy_worker.subprocess.run")
    def test_ffmpeg_success(self, mock_run, tmp_path):
        source = tmp_path / "video.mp4"
        source.write_bytes(b"x" * 1000)
        worker = ProxyWorker(str(tmp_path))

        # Mock ffmpeg: create the tmp file then simulate success
        def fake_run(cmd, **kwargs):
            # Find the output path (last arg)
            out = cmd[-1]
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            Path(out).write_bytes(b"proxy content")
            return MagicMock(returncode=0, stderr=b"")

        mock_run.side_effect = fake_run
        result = worker.generate(str(source))
        assert result.success
        assert not result.skipped
        assert result.proxy_size_bytes > 0

    @patch("src.services.cut_proxy_worker.HAS_FFMPEG", True)
    @patch("src.services.cut_proxy_worker.subprocess.run")
    def test_ffmpeg_failure(self, mock_run, tmp_path):
        source = tmp_path / "video.mp4"
        source.write_bytes(b"data")
        worker = ProxyWorker(str(tmp_path))

        mock_run.return_value = MagicMock(returncode=1, stderr=b"Invalid data found")
        result = worker.generate(str(source))
        assert not result.success
        assert "ffmpeg_error" in result.error


class TestProxyBatch:
    def test_batch_empty(self, tmp_path):
        worker = ProxyWorker(str(tmp_path))
        results = worker.generate_batch([])
        assert results == []

    def test_batch_with_progress(self, tmp_path):
        source = tmp_path / "a.mp4"
        source.write_bytes(b"data")
        worker = ProxyWorker(str(tmp_path))
        # Create fresh proxy
        proxy_path = worker._proxy_path_for(str(source))
        proxy_path.parent.mkdir(parents=True, exist_ok=True)
        time.sleep(0.01)
        proxy_path.write_bytes(b"proxy")

        progress_calls = []
        worker.generate_batch(
            [str(source)],
            on_progress=lambda i, t, r: progress_calls.append((i, t, r.success)),
        )
        assert len(progress_calls) == 1
        assert progress_calls[0] == (0, 1, True)


class TestProxyList:
    def test_list_empty(self, tmp_path):
        worker = ProxyWorker(str(tmp_path))
        assert worker.list_proxies() == []

    def test_list_with_files(self, tmp_path):
        worker = ProxyWorker(str(tmp_path))
        proxy_dir = worker.proxy_dir
        proxy_dir.mkdir(parents=True)
        (proxy_dir / "a_proxy_720p.mp4").write_bytes(b"data1")
        (proxy_dir / "b_proxy_720p.mp4").write_bytes(b"data2")
        proxies = worker.list_proxies()
        assert len(proxies) == 2


class TestProxyCleanup:
    def test_cleanup_stale(self, tmp_path):
        worker = ProxyWorker(str(tmp_path))

        # Create source + proxy
        source = tmp_path / "keep.mp4"
        source.write_bytes(b"keep_data")
        proxy_keep = worker._proxy_path_for(str(source))
        proxy_keep.parent.mkdir(parents=True, exist_ok=True)
        proxy_keep.write_bytes(b"proxy_keep")

        # Create orphan proxy (hash doesn't match any valid source)
        orphan = worker.proxy_dir / "orphan_deadbeef12345678_proxy_720p.mp4"
        orphan.write_bytes(b"orphan_data")

        removed = worker.cleanup_stale([str(source)])
        assert removed == 1
        assert proxy_keep.is_file()
        assert not orphan.is_file()


class TestGetProxyPath:
    def test_no_proxy(self, tmp_path):
        worker = ProxyWorker(str(tmp_path))
        assert worker.get_proxy_path("/fake/video.mp4") is None

    def test_existing_proxy(self, tmp_path):
        source = tmp_path / "video.mp4"
        source.write_bytes(b"data")
        worker = ProxyWorker(str(tmp_path))
        proxy_path = worker._proxy_path_for(str(source))
        proxy_path.parent.mkdir(parents=True, exist_ok=True)
        proxy_path.write_bytes(b"proxy")
        result = worker.get_proxy_path(str(source))
        assert result is not None
        assert "proxy_720p" in result


class TestProxyEndpoints:
    def _get_client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.api.routes.cut_routes import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @patch("src.api.routes.cut_routes.CutProjectStore")
    @patch("src.api.routes.cut_routes.ProxyWorker")
    def test_generate_endpoint(self, MockWorker, MockStore):
        instance = MagicMock()
        instance.load_project.return_value = {"project_id": "proj_1"}
        instance.load_timeline_state.return_value = None
        MockStore.return_value = instance

        worker_inst = MagicMock()
        worker_inst.generate_batch.return_value = [
            ProxyResult(source_path="/a.mp4", proxy_path="/proxy/a.mp4", success=True, skipped=False),
        ]
        MockWorker.return_value = worker_inst

        client = self._get_client()
        resp = client.post("/api/cut/proxy/generate", json={
            "sandbox_root": "/tmp/test",
            "project_id": "proj_1",
            "source_paths": ["/a.mp4"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["generated"] == 1

    @patch("src.api.routes.cut_routes.CutProjectStore")
    def test_generate_project_not_found(self, MockStore):
        instance = MagicMock()
        instance.load_project.return_value = None
        MockStore.return_value = instance

        client = self._get_client()
        resp = client.post("/api/cut/proxy/generate", json={
            "sandbox_root": "/tmp/test",
            "project_id": "proj_1",
        })
        data = resp.json()
        assert data["success"] is False

    @patch("src.api.routes.cut_routes.CutProjectStore")
    @patch("src.api.routes.cut_routes.ProxyWorker")
    def test_list_endpoint(self, MockWorker, MockStore):
        instance = MagicMock()
        instance.load_project.return_value = {"project_id": "proj_1"}
        MockStore.return_value = instance

        worker_inst = MagicMock()
        worker_inst.list_proxies.return_value = [
            {"filename": "a_proxy.mp4", "path": "/proxy/a.mp4", "size_bytes": 1024, "mtime": 1000},
        ]
        MockWorker.return_value = worker_inst

        client = self._get_client()
        resp = client.get("/api/cut/proxy/list", params={
            "sandbox_root": "/tmp/test",
            "project_id": "proj_1",
        })
        data = resp.json()
        assert data["success"] is True
        assert data["total"] == 1

    @patch("src.api.routes.cut_routes.ProxyWorker")
    def test_path_endpoint_exists(self, MockWorker):
        worker_inst = MagicMock()
        worker_inst.get_proxy_path.return_value = "/proxy/video_proxy.mp4"
        MockWorker.return_value = worker_inst

        client = self._get_client()
        resp = client.get("/api/cut/proxy/path", params={
            "sandbox_root": "/tmp/test",
            "source_path": "/media/video.mp4",
        })
        data = resp.json()
        assert data["success"] is True
        assert data["exists"] is True

    @patch("src.api.routes.cut_routes.ProxyWorker")
    def test_path_endpoint_not_exists(self, MockWorker):
        worker_inst = MagicMock()
        worker_inst.get_proxy_path.return_value = None
        MockWorker.return_value = worker_inst

        client = self._get_client()
        resp = client.get("/api/cut/proxy/path", params={
            "sandbox_root": "/tmp/test",
            "source_path": "/media/video.mp4",
        })
        data = resp.json()
        assert data["exists"] is False
