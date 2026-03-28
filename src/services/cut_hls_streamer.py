"""
MARKER_HLS_STREAM — HLS adaptive streaming for non-browser-native codecs.

Background FFmpeg HLS transcode: ProRes/DNxHD/RAW → .m3u8 + .ts segments.
Browser starts playback after first 2-second chunk instead of waiting for
full sync transcode (up to 10min on large files).

Flow:
  1. /cut/stream/hls?source_path=... — start or resume HLS transcode
  2. FFmpeg outputs .m3u8 playlist + .ts chunks in background thread
  3. Browser fetches .m3u8, then pulls .ts segments as they appear
  4. On completion, also write final .mp4 for future direct-serve cache hits

@status: active
@phase: HLS_STREAM
@task: tb_1774424853_1
@depends: ffmpeg (system binary)
@used_by: cut_routes_media.py (/cut/stream/hls/*)
"""
from __future__ import annotations

import enum
import hashlib
import logging
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

FFMPEG = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")

# Segment duration in seconds — low for fast first-frame
HLS_SEGMENT_SEC = 2
# Maximum concurrent transcode jobs
MAX_CONCURRENT_JOBS = 4
# Auto-expire completed jobs after N seconds (1 hour)
JOB_EXPIRE_SEC = 3600


class HLSJobStatus(str, enum.Enum):
    STARTING = "starting"
    TRANSCODING = "transcoding"
    READY = "ready"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class HLSJob:
    """One background HLS transcode job."""
    job_id: str
    source_path: Path
    hls_dir: Path
    playlist_path: Path        # .m3u8
    status: HLSJobStatus = HLSJobStatus.STARTING
    error: str = ""
    process: subprocess.Popen | None = field(default=None, repr=False)
    thread: threading.Thread | None = field(default=None, repr=False)
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    # Transcode args (from _needs_browser_transcode decision)
    v_args: list[str] = field(default_factory=list)
    a_args: list[str] = field(default_factory=list)
    # Progress tracking
    segment_count: int = 0

    @property
    def is_active(self) -> bool:
        return self.status in (HLSJobStatus.STARTING, HLSJobStatus.TRANSCODING)

    @property
    def is_expired(self) -> bool:
        if self.completed_at is None:
            return False
        return (time.time() - self.completed_at) > JOB_EXPIRE_SEC

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "source_path": str(self.source_path),
            "status": self.status.value,
            "error": self.error,
            "segment_count": self.segment_count,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "playlist_url": f"/api/cut/stream/hls/playlist/{self.job_id}",
        }


class HLSStreamer:
    """
    Manages background HLS transcode jobs.

    Singleton — one per server process. Jobs are keyed by cache_key
    (sha256 of source_path + mtime + size) so re-requests for the same
    file reuse the same job.
    """

    _instance: HLSStreamer | None = None

    def __init__(self) -> None:
        self._jobs: dict[str, HLSJob] = {}
        self._lock = threading.Lock()
        self._cache_base = Path.home() / ".cut_cache" / "hls_stream"
        self._cache_base.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_instance(cls) -> HLSStreamer:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton — for tests only."""
        if cls._instance is not None:
            cls._instance.cancel_all()
        cls._instance = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_or_get(
        self,
        source_path: Path,
        v_args: list[str],
        a_args: list[str],
    ) -> HLSJob:
        """
        Start HLS transcode for source_path, or return existing job.

        Args:
            source_path: Absolute path to source media file.
            v_args: FFmpeg video codec args (e.g. ["-c:v", "libx264", ...]).
            a_args: FFmpeg audio codec args (e.g. ["-c:a", "aac", ...]).

        Returns:
            HLSJob with status and playlist URL.
        """
        job_id = self._cache_key(source_path)

        with self._lock:
            # Reuse existing active or completed job
            if job_id in self._jobs:
                job = self._jobs[job_id]
                if job.is_active or job.status == HLSJobStatus.READY:
                    return job
                # Error/cancelled — remove and retry
                self._cleanup_job(job_id)

            # Check concurrent limit
            active = sum(1 for j in self._jobs.values() if j.is_active)
            if active >= MAX_CONCURRENT_JOBS:
                # Return a synthetic "busy" error job
                return HLSJob(
                    job_id=job_id,
                    source_path=source_path,
                    hls_dir=self._job_dir(job_id),
                    playlist_path=self._job_dir(job_id) / "stream.m3u8",
                    status=HLSJobStatus.ERROR,
                    error=f"Too many concurrent transcodes ({MAX_CONCURRENT_JOBS})",
                )

            # Check if HLS segments already cached on disk
            hls_dir = self._job_dir(job_id)
            playlist = hls_dir / "stream.m3u8"
            if playlist.exists() and playlist.stat().st_size > 0:
                job = HLSJob(
                    job_id=job_id,
                    source_path=source_path,
                    hls_dir=hls_dir,
                    playlist_path=playlist,
                    status=HLSJobStatus.READY,
                    completed_at=time.time(),
                )
                self._jobs[job_id] = job
                return job

            # Create new job
            hls_dir.mkdir(parents=True, exist_ok=True)
            job = HLSJob(
                job_id=job_id,
                source_path=source_path,
                hls_dir=hls_dir,
                playlist_path=playlist,
                v_args=list(v_args),
                a_args=list(a_args),
            )
            self._jobs[job_id] = job

        # Start background transcode (outside lock)
        thread = threading.Thread(
            target=self._run_transcode,
            args=(job,),
            daemon=True,
            name=f"hls-{job_id[:8]}",
        )
        job.thread = thread
        thread.start()

        return job

    def get_job(self, job_id: str) -> HLSJob | None:
        """Get job by ID."""
        with self._lock:
            return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        """Cancel a running transcode job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or not job.is_active:
                return False
            job.status = HLSJobStatus.CANCELLED
            if job.process:
                try:
                    job.process.terminate()
                except OSError:
                    pass
            return True

    def cancel_all(self) -> None:
        """Cancel all active jobs — for shutdown."""
        with self._lock:
            for job in self._jobs.values():
                if job.is_active:
                    job.status = HLSJobStatus.CANCELLED
                    if job.process:
                        try:
                            job.process.terminate()
                        except OSError:
                            pass

    def list_jobs(self) -> list[dict[str, Any]]:
        """List all jobs as dicts."""
        with self._lock:
            self._expire_old_jobs()
            return [j.to_dict() for j in self._jobs.values()]

    def get_segment_path(self, job_id: str, segment_name: str) -> Path | None:
        """Get path to a .ts segment file, if it exists."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
        # Validate segment name to prevent path traversal
        if "/" in segment_name or "\\" in segment_name or ".." in segment_name:
            return None
        seg_path = job.hls_dir / segment_name
        if seg_path.exists() and seg_path.is_file():
            return seg_path
        return None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_transcode(self, job: HLSJob) -> None:
        """Background thread: run FFmpeg HLS transcode."""
        if not FFMPEG:
            job.status = HLSJobStatus.ERROR
            job.error = "ffmpeg not found"
            job.completed_at = time.time()
            return

        segment_pattern = str(job.hls_dir / "seg_%04d.ts")

        cmd = [
            FFMPEG, "-y",
            "-i", str(job.source_path),
            *job.v_args,
            *job.a_args,
            "-f", "hls",
            "-hls_time", str(HLS_SEGMENT_SEC),
            "-hls_list_size", "0",           # Keep all segments in playlist
            "-hls_segment_filename", segment_pattern,
            "-hls_flags", "append_list",     # Append to playlist as segments finish
            "-hls_playlist_type", "event",   # Signal: playlist grows, never shrinks
            str(job.playlist_path),
        ]

        logger.info("HLS transcode start: %s → %s", job.source_path, job.hls_dir)

        try:
            job.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            job.status = HLSJobStatus.TRANSCODING

            # Wait for completion
            _, stderr = job.process.communicate(timeout=600)

            if job.status == HLSJobStatus.CANCELLED:
                return

            if job.process.returncode != 0:
                job.status = HLSJobStatus.ERROR
                err_text = stderr.decode("utf-8", errors="replace")[-500:]
                job.error = f"FFmpeg exit {job.process.returncode}: {err_text}"
                logger.error("HLS transcode failed: %s — %s", job.job_id, job.error)
            else:
                job.status = HLSJobStatus.READY
                # Count segments
                job.segment_count = len(list(job.hls_dir.glob("seg_*.ts")))
                logger.info(
                    "HLS transcode done: %s — %d segments",
                    job.job_id, job.segment_count,
                )

        except subprocess.TimeoutExpired:
            job.status = HLSJobStatus.ERROR
            job.error = "Transcode timeout (600s)"
            if job.process:
                job.process.kill()
        except Exception as exc:
            job.status = HLSJobStatus.ERROR
            job.error = str(exc)
        finally:
            job.completed_at = time.time()
            job.process = None

    def _job_dir(self, job_id: str) -> Path:
        return self._cache_base / job_id

    def _cleanup_job(self, job_id: str) -> None:
        """Remove job from registry. Does NOT delete disk files (cache reuse)."""
        self._jobs.pop(job_id, None)

    def _expire_old_jobs(self) -> None:
        """Remove expired completed jobs from registry."""
        expired = [jid for jid, j in self._jobs.items() if j.is_expired]
        for jid in expired:
            self._jobs.pop(jid, None)

    @staticmethod
    def _cache_key(source_path: Path) -> str:
        """Stable cache key from file path + mtime + size."""
        stat = source_path.stat()
        raw = f"hls:{source_path}:{stat.st_mtime_ns}:{stat.st_size}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
