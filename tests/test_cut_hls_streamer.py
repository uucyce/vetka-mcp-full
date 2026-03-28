"""
MARKER_HLS_STREAM — Tests for HLS adaptive streaming service + endpoints.
@task: tb_1774424853_1
"""
from __future__ import annotations

import hashlib
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from src.services.cut_hls_streamer import (
    HLS_SEGMENT_SEC,
    JOB_EXPIRE_SEC,
    MAX_CONCURRENT_JOBS,
    HLSJob,
    HLSJobStatus,
    HLSStreamer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_source(tmp_path: Path, name: str = "test.mov") -> Path:
    """Create a fake source file with some bytes so stat() works."""
    p = tmp_path / name
    p.write_bytes(b"\x00" * 1024)
    return p


def _make_streamer(tmp_path: Path) -> HLSStreamer:
    """Return a fresh HLSStreamer with cache_base redirected to tmp_path."""
    HLSStreamer.reset()
    streamer = HLSStreamer.get_instance()
    streamer._cache_base = tmp_path / "hls_cache"
    streamer._cache_base.mkdir(parents=True, exist_ok=True)
    return streamer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_singleton():
    """Ensure singleton is reset before and after every test."""
    HLSStreamer.reset()
    yield
    HLSStreamer.reset()


@pytest.fixture
def streamer(tmp_path):
    return _make_streamer(tmp_path)


@pytest.fixture
def source_file(tmp_path):
    return _make_source(tmp_path)


@pytest.fixture
def app_client(tmp_path):
    """
    TestClient wired up to a minimal FastAPI app that includes the CUT media
    router under /api/cut so the HLS routes are reachable at their real paths.
    """
    if not HAS_FASTAPI:
        pytest.skip("fastapi not installed")

    from src.api.routes.cut_routes_media import media_router

    app = FastAPI()
    app.include_router(media_router, prefix="/api/cut")

    # Redirect the singleton's cache_base to tmp_path before each request
    HLSStreamer.reset()
    streamer = HLSStreamer.get_instance()
    streamer._cache_base = tmp_path / "hls_cache"
    streamer._cache_base.mkdir(parents=True, exist_ok=True)

    return TestClient(app, raise_server_exceptions=False)


# ===========================================================================
# 1. HLSStreamer — Singleton behaviour
# ===========================================================================

class TestSingleton:
    def test_get_instance_returns_same_object(self):
        a = HLSStreamer.get_instance()
        b = HLSStreamer.get_instance()
        assert a is b

    def test_reset_clears_singleton(self):
        a = HLSStreamer.get_instance()
        HLSStreamer.reset()
        b = HLSStreamer.get_instance()
        assert a is not b

    def test_reset_cancels_active_jobs(self, streamer, source_file):
        # Inject a fake active job
        job = HLSJob(
            job_id="fake_id",
            source_path=source_file,
            hls_dir=streamer._cache_base / "fake_id",
            playlist_path=streamer._cache_base / "fake_id" / "stream.m3u8",
            status=HLSJobStatus.TRANSCODING,
        )
        streamer._jobs["fake_id"] = job
        HLSStreamer.reset()
        assert job.status == HLSJobStatus.CANCELLED


# ===========================================================================
# 2. HLSStreamer._cache_key
# ===========================================================================

class TestCacheKey:
    def test_cache_key_is_16_hex_chars(self, source_file):
        key = HLSStreamer._cache_key(source_file)
        assert len(key) == 16
        int(key, 16)  # raises ValueError if not hex

    def test_cache_key_same_file_same_key(self, source_file):
        k1 = HLSStreamer._cache_key(source_file)
        k2 = HLSStreamer._cache_key(source_file)
        assert k1 == k2

    def test_cache_key_different_files_different_keys(self, tmp_path):
        f1 = _make_source(tmp_path, "a.mov")
        f2 = _make_source(tmp_path, "b.mov")
        assert HLSStreamer._cache_key(f1) != HLSStreamer._cache_key(f2)

    def test_cache_key_changes_when_file_modified(self, tmp_path):
        f = _make_source(tmp_path, "c.mov")
        k1 = HLSStreamer._cache_key(f)
        f.write_bytes(b"\x01" * 2048)
        k2 = HLSStreamer._cache_key(f)
        assert k1 != k2

    def test_cache_key_sha256_prefix(self, source_file):
        """Manually verify the hash prefix matches sha256 of the same raw string."""
        stat = source_file.stat()
        raw = f"hls:{source_file}:{stat.st_mtime_ns}:{stat.st_size}"
        expected = hashlib.sha256(raw.encode()).hexdigest()[:16]
        assert HLSStreamer._cache_key(source_file) == expected


# ===========================================================================
# 3. HLSJob dataclass
# ===========================================================================

class TestHLSJob:
    def _make_job(self, source_file, status=HLSJobStatus.STARTING):
        return HLSJob(
            job_id="test_job_id",
            source_path=source_file,
            hls_dir=source_file.parent / "hls",
            playlist_path=source_file.parent / "hls" / "stream.m3u8",
            status=status,
        )

    def test_is_active_for_starting(self, source_file):
        job = self._make_job(source_file, HLSJobStatus.STARTING)
        assert job.is_active is True

    def test_is_active_for_transcoding(self, source_file):
        job = self._make_job(source_file, HLSJobStatus.TRANSCODING)
        assert job.is_active is True

    def test_is_not_active_for_ready(self, source_file):
        job = self._make_job(source_file, HLSJobStatus.READY)
        assert job.is_active is False

    def test_is_not_active_for_error(self, source_file):
        job = self._make_job(source_file, HLSJobStatus.ERROR)
        assert job.is_active is False

    def test_is_not_active_for_cancelled(self, source_file):
        job = self._make_job(source_file, HLSJobStatus.CANCELLED)
        assert job.is_active is False

    def test_is_expired_false_when_active(self, source_file):
        job = self._make_job(source_file, HLSJobStatus.TRANSCODING)
        assert job.is_expired is False

    def test_is_expired_false_just_completed(self, source_file):
        job = self._make_job(source_file, HLSJobStatus.READY)
        job.completed_at = time.time()
        assert job.is_expired is False

    def test_is_expired_true_after_ttl(self, source_file):
        job = self._make_job(source_file, HLSJobStatus.READY)
        job.completed_at = time.time() - JOB_EXPIRE_SEC - 1
        assert job.is_expired is True

    def test_to_dict_keys(self, source_file):
        job = self._make_job(source_file)
        d = job.to_dict()
        for key in ("job_id", "source_path", "status", "error",
                    "segment_count", "created_at", "completed_at", "playlist_url"):
            assert key in d, f"missing key: {key}"

    def test_to_dict_playlist_url_contains_job_id(self, source_file):
        job = self._make_job(source_file)
        assert job.job_id in job.to_dict()["playlist_url"]

    def test_to_dict_status_is_string(self, source_file):
        job = self._make_job(source_file, HLSJobStatus.TRANSCODING)
        assert job.to_dict()["status"] == "transcoding"


# ===========================================================================
# 4. HLSStreamer.start_or_get
# ===========================================================================

class TestStartOrGet:
    def test_returns_hls_job(self, streamer, source_file):
        with patch("src.services.cut_hls_streamer.FFMPEG", "/usr/bin/ffmpeg"):
            with patch("subprocess.Popen") as mock_popen:
                proc = MagicMock()
                proc.communicate.return_value = (b"", b"")
                proc.returncode = 0
                mock_popen.return_value = proc
                job = streamer.start_or_get(source_file, ["-c:v", "copy"], ["-c:a", "copy"])
        assert isinstance(job, HLSJob)
        assert job.source_path == source_file

    def test_second_call_returns_same_job(self, streamer, source_file):
        with patch("src.services.cut_hls_streamer.FFMPEG", "/usr/bin/ffmpeg"):
            with patch("subprocess.Popen") as mock_popen:
                proc = MagicMock()
                proc.communicate.return_value = (b"", b"")
                proc.returncode = 0
                mock_popen.return_value = proc
                job1 = streamer.start_or_get(source_file, [], [])
                job2 = streamer.start_or_get(source_file, [], [])
        assert job1.job_id == job2.job_id

    def test_disk_cache_reuse_returns_ready(self, streamer, source_file):
        """If playlist already exists on disk, job is returned as READY immediately."""
        job_id = HLSStreamer._cache_key(source_file)
        hls_dir = streamer._cache_base / job_id
        hls_dir.mkdir(parents=True, exist_ok=True)
        playlist = hls_dir / "stream.m3u8"
        playlist.write_text("#EXTM3U\n#EXT-X-VERSION:3\n")

        job = streamer.start_or_get(source_file, [], [])
        assert job.status == HLSJobStatus.READY
        assert job.job_id == job_id

    def test_error_job_retries(self, streamer, source_file):
        """A job previously in ERROR state is removed and a new one started."""
        job_id = HLSStreamer._cache_key(source_file)
        bad_job = HLSJob(
            job_id=job_id,
            source_path=source_file,
            hls_dir=streamer._cache_base / job_id,
            playlist_path=streamer._cache_base / job_id / "stream.m3u8",
            status=HLSJobStatus.ERROR,
        )
        streamer._jobs[job_id] = bad_job

        with patch("src.services.cut_hls_streamer.FFMPEG", "/usr/bin/ffmpeg"):
            with patch("subprocess.Popen") as mock_popen:
                proc = MagicMock()
                proc.communicate.return_value = (b"", b"")
                proc.returncode = 0
                mock_popen.return_value = proc
                new_job = streamer.start_or_get(source_file, [], [])
        # The new job should not be the old error job
        assert new_job is not bad_job


# ===========================================================================
# 5. Concurrent job limit
# ===========================================================================

class TestConcurrentLimit:
    def test_exceeding_max_concurrent_returns_error_job(self, streamer, tmp_path):
        """Filling MAX_CONCURRENT_JOBS slots makes the next request return an error job."""
        for i in range(MAX_CONCURRENT_JOBS):
            fake_path = tmp_path / f"fake_{i}.mov"
            fake_path.write_bytes(b"\x00" * 128)
            fake_id = f"fakeid_{i:02d}"
            streamer._jobs[fake_id] = HLSJob(
                job_id=fake_id,
                source_path=fake_path,
                hls_dir=streamer._cache_base / fake_id,
                playlist_path=streamer._cache_base / fake_id / "stream.m3u8",
                status=HLSJobStatus.TRANSCODING,
            )

        extra = _make_source(tmp_path, "extra.mov")
        job = streamer.start_or_get(extra, [], [])
        assert job.status == HLSJobStatus.ERROR
        assert "Too many" in job.error


# ===========================================================================
# 6. HLSStreamer.get_job / cancel / cancel_all
# ===========================================================================

class TestJobControl:
    def test_get_job_returns_none_for_unknown(self, streamer):
        assert streamer.get_job("nonexistent_id") is None

    def test_get_job_returns_job_after_registration(self, streamer, source_file):
        job_id = HLSStreamer._cache_key(source_file)
        job = HLSJob(
            job_id=job_id,
            source_path=source_file,
            hls_dir=streamer._cache_base / job_id,
            playlist_path=streamer._cache_base / job_id / "stream.m3u8",
            status=HLSJobStatus.TRANSCODING,
        )
        streamer._jobs[job_id] = job
        assert streamer.get_job(job_id) is job

    def test_cancel_active_job_returns_true(self, streamer, source_file):
        job_id = HLSStreamer._cache_key(source_file)
        job = HLSJob(
            job_id=job_id,
            source_path=source_file,
            hls_dir=streamer._cache_base / job_id,
            playlist_path=streamer._cache_base / job_id / "stream.m3u8",
            status=HLSJobStatus.TRANSCODING,
        )
        streamer._jobs[job_id] = job
        result = streamer.cancel(job_id)
        assert result is True
        assert job.status == HLSJobStatus.CANCELLED

    def test_cancel_non_active_job_returns_false(self, streamer, source_file):
        job_id = HLSStreamer._cache_key(source_file)
        job = HLSJob(
            job_id=job_id,
            source_path=source_file,
            hls_dir=streamer._cache_base / job_id,
            playlist_path=streamer._cache_base / job_id / "stream.m3u8",
            status=HLSJobStatus.READY,
        )
        streamer._jobs[job_id] = job
        assert streamer.cancel(job_id) is False

    def test_cancel_unknown_job_returns_false(self, streamer):
        assert streamer.cancel("nonexistent") is False

    def test_cancel_terminates_process(self, streamer, source_file):
        job_id = HLSStreamer._cache_key(source_file)
        mock_proc = MagicMock()
        job = HLSJob(
            job_id=job_id,
            source_path=source_file,
            hls_dir=streamer._cache_base / job_id,
            playlist_path=streamer._cache_base / job_id / "stream.m3u8",
            status=HLSJobStatus.TRANSCODING,
            process=mock_proc,
        )
        streamer._jobs[job_id] = job
        streamer.cancel(job_id)
        mock_proc.terminate.assert_called_once()

    def test_cancel_all_cancels_active_jobs(self, streamer, tmp_path):
        jobs = []
        for i in range(3):
            fp = tmp_path / f"src_{i}.mov"
            fp.write_bytes(b"\x00" * 64)
            jid = f"jid_{i}"
            j = HLSJob(
                job_id=jid,
                source_path=fp,
                hls_dir=streamer._cache_base / jid,
                playlist_path=streamer._cache_base / jid / "stream.m3u8",
                status=HLSJobStatus.TRANSCODING,
            )
            streamer._jobs[jid] = j
            jobs.append(j)
        streamer.cancel_all()
        for j in jobs:
            assert j.status == HLSJobStatus.CANCELLED


# ===========================================================================
# 7. get_segment_path — security / normal paths
# ===========================================================================

class TestGetSegmentPath:
    def _register_job(self, streamer, source_file):
        job_id = HLSStreamer._cache_key(source_file)
        hls_dir = streamer._cache_base / job_id
        hls_dir.mkdir(parents=True, exist_ok=True)
        job = HLSJob(
            job_id=job_id,
            source_path=source_file,
            hls_dir=hls_dir,
            playlist_path=hls_dir / "stream.m3u8",
            status=HLSJobStatus.READY,
        )
        streamer._jobs[job_id] = job
        return job

    def test_returns_none_for_unknown_job(self, streamer):
        assert streamer.get_segment_path("no_such_job", "seg_0000.ts") is None

    def test_returns_none_for_missing_segment(self, streamer, source_file):
        job = self._register_job(streamer, source_file)
        assert streamer.get_segment_path(job.job_id, "seg_9999.ts") is None

    def test_returns_path_for_existing_segment(self, streamer, source_file):
        job = self._register_job(streamer, source_file)
        seg = job.hls_dir / "seg_0000.ts"
        seg.write_bytes(b"\x00" * 188)
        result = streamer.get_segment_path(job.job_id, "seg_0000.ts")
        assert result == seg

    def test_path_traversal_with_slash_blocked(self, streamer, source_file):
        job = self._register_job(streamer, source_file)
        assert streamer.get_segment_path(job.job_id, "../evil.ts") is None

    def test_path_traversal_with_backslash_blocked(self, streamer, source_file):
        job = self._register_job(streamer, source_file)
        assert streamer.get_segment_path(job.job_id, "seg\\..\\evil.ts") is None

    def test_path_traversal_dotdot_blocked(self, streamer, source_file):
        job = self._register_job(streamer, source_file)
        assert streamer.get_segment_path(job.job_id, "..") is None


# ===========================================================================
# 8. list_jobs
# ===========================================================================

class TestListJobs:
    def test_list_jobs_empty(self, streamer):
        assert streamer.list_jobs() == []

    def test_list_jobs_returns_dicts(self, streamer, source_file):
        job_id = HLSStreamer._cache_key(source_file)
        streamer._jobs[job_id] = HLSJob(
            job_id=job_id,
            source_path=source_file,
            hls_dir=streamer._cache_base / job_id,
            playlist_path=streamer._cache_base / job_id / "stream.m3u8",
            status=HLSJobStatus.READY,
            completed_at=time.time(),
        )
        jobs = streamer.list_jobs()
        assert len(jobs) == 1
        assert isinstance(jobs[0], dict)
        assert jobs[0]["job_id"] == job_id

    def test_list_jobs_expires_old(self, streamer, source_file):
        job_id = HLSStreamer._cache_key(source_file)
        streamer._jobs[job_id] = HLSJob(
            job_id=job_id,
            source_path=source_file,
            hls_dir=streamer._cache_base / job_id,
            playlist_path=streamer._cache_base / job_id / "stream.m3u8",
            status=HLSJobStatus.READY,
            completed_at=time.time() - JOB_EXPIRE_SEC - 10,
        )
        jobs = streamer.list_jobs()
        assert jobs == []


# ===========================================================================
# 9. Constants
# ===========================================================================

class TestConstants:
    def test_hls_segment_sec(self):
        assert HLS_SEGMENT_SEC == 2

    def test_max_concurrent_jobs(self):
        assert MAX_CONCURRENT_JOBS == 4

    def test_job_expire_sec(self):
        assert JOB_EXPIRE_SEC == 3600


# ===========================================================================
# 10. Route-level tests (TestClient)
# ===========================================================================

class TestHLSRoutes:
    def test_hls_status_unknown_job_returns_404(self, app_client):
        r = app_client.get("/api/cut/stream/hls/status/nonexistent_job_id")
        assert r.status_code == 404

    def test_hls_jobs_list_empty(self, app_client):
        r = app_client.get("/api/cut/stream/hls/jobs")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["jobs"] == []

    def test_hls_cancel_unknown_job_returns_404(self, app_client):
        r = app_client.delete("/api/cut/stream/hls/nonexistent_job")
        assert r.status_code == 404

    def test_hls_playlist_unknown_job_returns_404(self, app_client):
        r = app_client.get("/api/cut/stream/hls/playlist/nonexistent_job")
        assert r.status_code == 404

    def test_hls_segment_unknown_job_returns_404(self, app_client):
        r = app_client.get("/api/cut/stream/hls/segment/nojob/seg_0000.ts")
        assert r.status_code == 404

    def test_hls_start_missing_path_returns_400(self, app_client):
        r = app_client.get("/api/cut/stream/hls?source_path=")
        assert r.status_code in (400, 422)

    def test_hls_start_nonexistent_file_returns_404(self, app_client, tmp_path):
        r = app_client.get(
            "/api/cut/stream/hls",
            params={"source_path": str(tmp_path / "does_not_exist.mov")},
        )
        assert r.status_code == 404

    def test_hls_status_returns_job_dict(self, app_client, tmp_path):
        """Register a READY job directly and verify the status endpoint returns it."""
        streamer = HLSStreamer.get_instance()
        source = _make_source(tmp_path, "vid.mov")
        job_id = HLSStreamer._cache_key(source)
        hls_dir = streamer._cache_base / job_id
        hls_dir.mkdir(parents=True, exist_ok=True)
        streamer._jobs[job_id] = HLSJob(
            job_id=job_id,
            source_path=source,
            hls_dir=hls_dir,
            playlist_path=hls_dir / "stream.m3u8",
            status=HLSJobStatus.READY,
            completed_at=time.time(),
        )
        r = app_client.get(f"/api/cut/stream/hls/status/{job_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["job_id"] == job_id
        assert data["status"] == "ready"

    def test_hls_cancel_active_job_returns_200(self, app_client, tmp_path):
        """Register an active job and confirm DELETE cancels it."""
        streamer = HLSStreamer.get_instance()
        source = _make_source(tmp_path, "active.mov")
        job_id = HLSStreamer._cache_key(source)
        hls_dir = streamer._cache_base / job_id
        hls_dir.mkdir(parents=True, exist_ok=True)
        streamer._jobs[job_id] = HLSJob(
            job_id=job_id,
            source_path=source,
            hls_dir=hls_dir,
            playlist_path=hls_dir / "stream.m3u8",
            status=HLSJobStatus.TRANSCODING,
        )
        r = app_client.delete(f"/api/cut/stream/hls/{job_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["status"] == "cancelled"

    def test_hls_playlist_rewrite_segments(self, app_client, tmp_path):
        """
        Playlist endpoint must rewrite bare segment filenames to API URLs.
        seg_0000.ts  →  /api/cut/stream/hls/segment/{job_id}/seg_0000.ts
        """
        streamer = HLSStreamer.get_instance()
        source = _make_source(tmp_path, "prores.mov")
        job_id = HLSStreamer._cache_key(source)
        hls_dir = streamer._cache_base / job_id
        hls_dir.mkdir(parents=True, exist_ok=True)
        playlist = hls_dir / "stream.m3u8"
        playlist.write_text(
            "#EXTM3U\n"
            "#EXT-X-VERSION:3\n"
            "#EXT-X-TARGETDURATION:2\n"
            "#EXTINF:2.0,\n"
            "seg_0000.ts\n"
            "#EXTINF:2.0,\n"
            "seg_0001.ts\n"
            "#EXT-X-ENDLIST\n"
        )
        streamer._jobs[job_id] = HLSJob(
            job_id=job_id,
            source_path=source,
            hls_dir=hls_dir,
            playlist_path=playlist,
            status=HLSJobStatus.READY,
            completed_at=time.time(),
        )

        r = app_client.get(f"/api/cut/stream/hls/playlist/{job_id}")
        assert r.status_code == 200
        body = r.text
        assert "seg_0000.ts" not in body or f"segment/{job_id}/seg_0000.ts" in body
        assert f"/api/cut/stream/hls/segment/{job_id}/seg_0001.ts" in body

    def test_hls_playlist_not_ready_returns_202(self, app_client, tmp_path):
        """If the .m3u8 does not exist yet the endpoint returns 202 Accepted."""
        streamer = HLSStreamer.get_instance()
        source = _make_source(tmp_path, "slow.mov")
        job_id = HLSStreamer._cache_key(source)
        hls_dir = streamer._cache_base / job_id
        hls_dir.mkdir(parents=True, exist_ok=True)
        # playlist file intentionally NOT created
        streamer._jobs[job_id] = HLSJob(
            job_id=job_id,
            source_path=source,
            hls_dir=hls_dir,
            playlist_path=hls_dir / "stream.m3u8",
            status=HLSJobStatus.TRANSCODING,
        )
        r = app_client.get(f"/api/cut/stream/hls/playlist/{job_id}")
        assert r.status_code == 202

    def test_hls_segment_served_when_present(self, app_client, tmp_path):
        """GET /stream/hls/segment/{job_id}/{seg} returns 200 + correct content-type."""
        streamer = HLSStreamer.get_instance()
        source = _make_source(tmp_path, "seg_test.mov")
        job_id = HLSStreamer._cache_key(source)
        hls_dir = streamer._cache_base / job_id
        hls_dir.mkdir(parents=True, exist_ok=True)
        seg = hls_dir / "seg_0000.ts"
        seg.write_bytes(b"\x47" * 188 * 10)  # fake MPEG-TS sync bytes
        streamer._jobs[job_id] = HLSJob(
            job_id=job_id,
            source_path=source,
            hls_dir=hls_dir,
            playlist_path=hls_dir / "stream.m3u8",
            status=HLSJobStatus.READY,
            completed_at=time.time(),
        )
        r = app_client.get(f"/api/cut/stream/hls/segment/{job_id}/seg_0000.ts")
        assert r.status_code == 200
        assert "video/mp2t" in r.headers.get("content-type", "")

    def test_hls_jobs_list_with_active_job(self, app_client, tmp_path):
        """GET /stream/hls/jobs returns registered jobs."""
        streamer = HLSStreamer.get_instance()
        source = _make_source(tmp_path, "list_test.mov")
        job_id = HLSStreamer._cache_key(source)
        hls_dir = streamer._cache_base / job_id
        hls_dir.mkdir(parents=True, exist_ok=True)
        streamer._jobs[job_id] = HLSJob(
            job_id=job_id,
            source_path=source,
            hls_dir=hls_dir,
            playlist_path=hls_dir / "stream.m3u8",
            status=HLSJobStatus.TRANSCODING,
        )
        r = app_client.get("/api/cut/stream/hls/jobs")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert any(j["job_id"] == job_id for j in data["jobs"])
