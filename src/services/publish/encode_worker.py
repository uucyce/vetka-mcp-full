"""
MARKER_B96 — FFmpeg Encode Worker: Cross-Platform Social Publish.

Implements codec presets, platform constraints and a concurrent job
manager for encoding timeline exports to platform-specific deliverables
(YouTube, Instagram Reels, TikTok, X/Twitter, Telegram, ProRes, H.265).

Architecture:
- CODEC_PRESETS   — 7 named presets with codec/bitrate/resolution/fps config
- PLATFORM_CONSTRAINTS — per-platform file-size/duration/aspect limits
- build_ffmpeg_cmd()  — constructs the ffmpeg argv list for a preset
- run_encode_job()    — runs FFmpeg as subprocess, parses progress, returns result dict
- EncodeJobManager   — ThreadPoolExecutor(max_workers=3), submit/status/cancel

FFmpeg command template per preset:
  ffmpeg -y -i <input> [crop_filter] -c:v <codec> [preset/crf/bitrate flags]
         -r <fps> -vf scale=<WxH> -c:a aac -b:a <audio_bitrate>
         [-t <duration_clamp>] <output>

Progress is parsed from FFmpeg stderr lines matching:
  time=HH:MM:SS.ss

Requirements:
  - FFmpeg must be in PATH (or set FFMPEG_BIN env var)
  - Python 3.9+

Usage:
    from src.services.publish.encode_worker import EncodeJobManager

    mgr = EncodeJobManager()
    future = mgr.submit(
        job_id="job_001",
        input_path="/media/timeline_export.mp4",
        output_dir="/exports",
        preset_name="yt_h264_1080",
        on_progress=lambda pct: print(f"Progress: {pct:.1f}%"),
    )
    result = future.result()
    # result = {"success": True, "output_path": "...", "duration": 42.3, "file_size": 81920000}

@status: active
@phase: 198
@task: tb_publish_encode_worker
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("cut.publish.encode_worker")

# ── FFmpeg binary ──────────────────────────────────────────────────────────────

FFMPEG_BIN: str = os.environ.get("FFMPEG_BIN", "ffmpeg")

# ── Codec presets ──────────────────────────────────────────────────────────────

CODEC_PRESETS: Dict[str, Dict] = {
    # YouTube — H.264, 1920x1080, 30 fps, 8 Mbps video, 192k audio, unlimited duration
    "yt_h264_1080": {
        "codec": "libx264",
        "video_bitrate": "8M",
        "audio_bitrate": "192k",
        "resolution": "1920x1080",
        "fps": 30,
        "extra_flags": ["-preset", "slow", "-profile:v", "high", "-level", "4.0"],
        "max_duration_sec": None,
    },
    # Instagram Reels — H.264, 1080x1920 (9:16), 30 fps, 5 Mbps, 128k audio, 90 s max
    "ig_h264_reels": {
        "codec": "libx264",
        "video_bitrate": "5M",
        "audio_bitrate": "128k",
        "resolution": "1080x1920",
        "fps": 30,
        "extra_flags": ["-preset", "medium", "-profile:v", "high", "-level", "4.0"],
        "max_duration_sec": 90,
    },
    # TikTok — H.264, 1080x1920, 30 fps, 5 Mbps, 128k audio, 600 s max
    "tt_h264": {
        "codec": "libx264",
        "video_bitrate": "5M",
        "audio_bitrate": "128k",
        "resolution": "1080x1920",
        "fps": 30,
        "extra_flags": ["-preset", "medium", "-profile:v", "high", "-level", "4.0"],
        "max_duration_sec": 600,
    },
    # X / Twitter — H.264, 1920x1080, 30 fps, 5 Mbps, 128k audio, 140 s max
    "x_h264_1080": {
        "codec": "libx264",
        "video_bitrate": "5M",
        "audio_bitrate": "128k",
        "resolution": "1920x1080",
        "fps": 30,
        "extra_flags": ["-preset", "medium", "-profile:v", "high", "-level", "4.0"],
        "max_duration_sec": 140,
    },
    # Telegram — H.264, 1920x1080, 30 fps, 4 Mbps, 128k audio, no strict duration limit (2 GB file cap)
    "tg_h264": {
        "codec": "libx264",
        "video_bitrate": "4M",
        "audio_bitrate": "128k",
        "resolution": "1920x1080",
        "fps": 30,
        "extra_flags": ["-preset", "medium", "-profile:v", "high", "-level", "4.0"],
        "max_duration_sec": None,
    },
    # File export — Apple ProRes 422 (profile 2), PCM 24-bit, 1920x1080, native fps
    "file_prores422": {
        "codec": "prores_ks",
        "video_bitrate": None,          # ProRes is VBR — no target bitrate
        "audio_bitrate": None,          # PCM — no bitrate target
        "resolution": "1920x1080",
        "fps": None,                    # preserve source fps
        "extra_flags": ["-profile:v", "2", "-vendor", "apl0", "-pix_fmt", "yuv422p10le"],
        "max_duration_sec": None,
    },
    # File export — H.265 CRF 22, 1920x1080, native fps, AAC 192k
    "file_h265": {
        "codec": "libx265",
        "video_bitrate": None,          # CRF mode
        "audio_bitrate": "192k",
        "resolution": "1920x1080",
        "fps": None,                    # preserve source fps
        "extra_flags": ["-crf", "22", "-preset", "slow", "-tag:v", "hvc1"],
        "max_duration_sec": None,
    },
}

# ── Platform constraints ───────────────────────────────────────────────────────

PLATFORM_CONSTRAINTS: Dict[str, Dict] = {
    "youtube": {
        "max_file_size_bytes": None,            # effectively no limit (128 GB for verified accounts)
        "max_duration_sec": 43200,              # 12 hours
        "required_aspect_ratios": ["16:9"],
        "max_resolution": "3840x2160",          # 4K supported
    },
    "instagram": {
        "max_file_size_bytes": 4 * 1024 ** 3,  # 4 GB
        "max_duration_sec": 90,                 # Reels 90 s
        "required_aspect_ratios": ["9:16", "1:1", "4:5"],
        "max_resolution": "1080x1920",
    },
    "tiktok": {
        "max_file_size_bytes": 4 * 1024 ** 3,  # 4 GB for TikTok Studio
        "max_duration_sec": 600,                # 10 min
        "required_aspect_ratios": ["9:16", "1:1", "16:9"],
        "max_resolution": "1080x1920",
    },
    "x": {
        "max_file_size_bytes": 512 * 1024 ** 2,  # 512 MB
        "max_duration_sec": 140,
        "required_aspect_ratios": ["16:9", "1:1"],
        "max_resolution": "1920x1200",
    },
    "telegram": {
        "max_file_size_bytes": 2 * 1024 ** 3,  # 2 GB
        "max_duration_sec": None,
        "required_aspect_ratios": [],           # no strict aspect requirement
        "max_resolution": "1920x1080",
    },
    "file": {
        "max_file_size_bytes": None,
        "max_duration_sec": None,
        "required_aspect_ratios": [],
        "max_resolution": None,
    },
}

# ── Command builder ────────────────────────────────────────────────────────────

def build_ffmpeg_cmd(
    input_path: str,
    output_path: str,
    preset_name: str,
    reframe: Optional[Dict] = None,
    duration_clamp: Optional[float] = None,
) -> List[str]:
    """Build an FFmpeg argv list for the given preset.

    Args:
        input_path:     Absolute path to the source media file.
        output_path:    Absolute path for the encoded output file.
        preset_name:    Key from CODEC_PRESETS (e.g. 'yt_h264_1080').
        reframe:        Optional dict with reframe parameters.
                        Supported keys:
                          mode          — 'center' (only supported value)
                          target_aspect — '9:16'
                        When provided, inserts crop filter:
                          crop=ih*9/16:ih:(iw-ih*9/16)/2:0
        duration_clamp: Optional clip duration in seconds.  Adds -t flag.

    Returns:
        List[str] — complete ffmpeg argv starting with the ffmpeg binary.

    Raises:
        KeyError: if preset_name is not found in CODEC_PRESETS.
    """
    preset = CODEC_PRESETS[preset_name]  # raises KeyError on bad name

    cmd: List[str] = [FFMPEG_BIN, "-y", "-i", input_path]

    # ── Duration clamp (input-side -t is more reliable for exact cuts) ──
    if duration_clamp is not None:
        cmd += ["-t", str(duration_clamp)]

    # ── Video filter chain ──────────────────────────────────────────────
    vf_filters: List[str] = []

    if reframe is not None:
        mode = reframe.get("mode", "center")
        target_aspect = reframe.get("target_aspect", "9:16")
        if mode == "center" and target_aspect == "9:16":
            # Crop the centre 9:16 slice from a landscape (or any) frame
            vf_filters.append("crop=ih*9/16:ih:(iw-ih*9/16)/2:0")
        else:
            logger.warning(
                "build_ffmpeg_cmd: unsupported reframe mode=%s aspect=%s — skipping crop",
                mode,
                target_aspect,
            )

    resolution = preset.get("resolution")
    if resolution:
        vf_filters.append(f"scale={resolution}")

    if vf_filters:
        cmd += ["-vf", ",".join(vf_filters)]

    # ── Video codec ─────────────────────────────────────────────────────
    cmd += ["-c:v", preset["codec"]]

    # Extra codec flags (preset/profile/crf/etc.)
    extra_flags: List[str] = preset.get("extra_flags") or []
    cmd += extra_flags

    # Video bitrate (not used for ProRes / H.265 CRF modes)
    video_bitrate = preset.get("video_bitrate")
    if video_bitrate:
        cmd += ["-b:v", video_bitrate]

    # Frame rate
    fps = preset.get("fps")
    if fps is not None:
        cmd += ["-r", str(fps)]

    # ── Audio codec ─────────────────────────────────────────────────────
    codec = preset["codec"]
    if codec == "prores_ks":
        # ProRes uses PCM 24-bit audio
        cmd += ["-c:a", "pcm_s24le"]
    else:
        cmd += ["-c:a", "aac"]
        audio_bitrate = preset.get("audio_bitrate")
        if audio_bitrate:
            cmd += ["-b:a", audio_bitrate]

    # ── Output ──────────────────────────────────────────────────────────
    cmd.append(output_path)

    return cmd


# ── Progress parser helpers ────────────────────────────────────────────────────

_TIME_PATTERN = re.compile(r"time=(\d+):(\d+):(\d+)\.(\d+)")


def _parse_ffmpeg_time(line: str) -> Optional[float]:
    """Return elapsed seconds parsed from an FFmpeg progress line, or None."""
    m = _TIME_PATTERN.search(line)
    if not m:
        return None
    hours, minutes, seconds, centiseconds = (int(x) for x in m.groups())
    return hours * 3600 + minutes * 60 + seconds + centiseconds / 100.0


def _probe_duration(input_path: str) -> Optional[float]:
    """Use ffprobe to get stream duration in seconds. Returns None on failure."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                input_path,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        value = result.stdout.strip()
        if value and value != "N/A":
            return float(value)
    except Exception as exc:
        logger.debug("_probe_duration failed for %s: %s", input_path, exc)
    return None


# ── Core encode runner ─────────────────────────────────────────────────────────

def run_encode_job(
    job_id: str,
    input_path: str,
    output_dir: str,
    preset_name: str,
    reframe: Optional[Dict] = None,
    on_progress: Optional[Callable[[float], None]] = None,
    _process_registry: Optional[Dict] = None,
) -> Dict:
    """Run a single FFmpeg encode job synchronously.

    Designed to be called from a thread (e.g. via ThreadPoolExecutor).

    Args:
        job_id:            Unique job identifier (used for output filename prefix).
        input_path:        Absolute path to source media.
        output_dir:        Directory where the encoded file will be written.
        preset_name:       Key from CODEC_PRESETS.
        reframe:           Optional reframe dict (passed to build_ffmpeg_cmd).
        on_progress:       Optional callback ``fn(percent: float)`` called
                           periodically with 0–100 progress estimate.
        _process_registry: Optional dict for subprocess handle registration
                           (used by EncodeJobManager for cancel support).

    Returns:
        dict with keys:
          success      (bool)
          output_path  (str | None)
          duration     (float)  — wall-clock encode duration in seconds
          file_size    (int)    — output file size in bytes, or 0
          error        (str | None)
    """
    preset = CODEC_PRESETS.get(preset_name)
    if preset is None:
        return {
            "success": False,
            "output_path": None,
            "duration": 0.0,
            "file_size": 0,
            "error": f"Unknown preset: {preset_name!r}",
        }

    # Determine output extension
    codec = preset["codec"]
    ext_map = {
        "prores_ks": ".mov",
        "libx265": ".mp4",
        "libx264": ".mp4",
    }
    ext = ext_map.get(codec, ".mp4")

    output_path = str(Path(output_dir) / f"{job_id}_{preset_name}{ext}")

    # Respect preset's own max_duration_sec as a clamp if no explicit clamp given
    duration_clamp = preset.get("max_duration_sec")  # may be None

    cmd = build_ffmpeg_cmd(
        input_path=input_path,
        output_path=output_path,
        preset_name=preset_name,
        reframe=reframe,
        duration_clamp=duration_clamp,
    )

    logger.info("run_encode_job[%s]: %s", job_id, " ".join(cmd))

    # Probe source duration for progress calculation
    total_seconds = _probe_duration(input_path)
    if total_seconds and duration_clamp:
        total_seconds = min(total_seconds, duration_clamp)

    start_time = time.monotonic()
    error_output: List[str] = []

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        if _process_registry is not None:
            _process_registry[job_id] = proc

        for line in proc.stdout:  # type: ignore[union-attr]
            line = line.rstrip()
            if line:
                error_output.append(line)

            elapsed = _parse_ffmpeg_time(line)
            if elapsed is not None and on_progress is not None:
                if total_seconds and total_seconds > 0:
                    pct = min(elapsed / total_seconds * 100.0, 99.9)
                else:
                    pct = 0.0
                try:
                    on_progress(pct)
                except Exception:
                    pass

        proc.wait()
        wall_duration = time.monotonic() - start_time

        if _process_registry is not None:
            _process_registry.pop(job_id, None)

        if proc.returncode != 0:
            tail = "\n".join(error_output[-20:])
            logger.error("run_encode_job[%s] failed (rc=%d):\n%s", job_id, proc.returncode, tail)
            return {
                "success": False,
                "output_path": None,
                "duration": wall_duration,
                "file_size": 0,
                "error": f"FFmpeg exited with code {proc.returncode}. Last output:\n{tail}",
            }

        file_size = 0
        out_p = Path(output_path)
        if out_p.exists():
            file_size = out_p.stat().st_size

        if on_progress is not None:
            try:
                on_progress(100.0)
            except Exception:
                pass

        logger.info(
            "run_encode_job[%s] done in %.1fs, output=%s (%d bytes)",
            job_id, wall_duration, output_path, file_size,
        )
        return {
            "success": True,
            "output_path": output_path,
            "duration": wall_duration,
            "file_size": file_size,
            "error": None,
        }

    except Exception as exc:
        wall_duration = time.monotonic() - start_time
        logger.exception("run_encode_job[%s] raised: %s", job_id, exc)
        if _process_registry is not None:
            _process_registry.pop(job_id, None)
        return {
            "success": False,
            "output_path": None,
            "duration": wall_duration,
            "file_size": 0,
            "error": str(exc),
        }


# ── EncodeJobManager ───────────────────────────────────────────────────────────

class EncodeJobManager:
    """Concurrent encode job manager backed by a ThreadPoolExecutor.

    Manages up to ``max_workers`` simultaneous FFmpeg processes.
    Tracks job state (pending / running / done / cancelled / failed) and
    exposes per-job progress, output path, and error information.

    Usage:
        mgr = EncodeJobManager()
        future = mgr.submit("job_1", "/in/clip.mp4", "/out", "ig_h264_reels")
        print(mgr.get_status("job_1"))
        result = future.result()

    Thread safety:
        All public methods are thread-safe via internal lock.
    """

    def __init__(self, max_workers: int = 3) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="encode")
        self._lock = Lock()
        # job_id → status dict
        self._jobs: Dict[str, Dict] = {}
        # job_id → active subprocess handle (for cancel)
        self._processes: Dict[str, subprocess.Popen] = {}
        # job_id → Future
        self._futures: Dict[str, Future] = {}

    # ── Public API ─────────────────────────────────────────────────────

    def submit(
        self,
        job_id: str,
        input_path: str,
        output_dir: str,
        preset_name: str,
        reframe: Optional[Dict] = None,
        on_progress: Optional[Callable[[float], None]] = None,
    ) -> Future:
        """Submit an encode job to the thread pool.

        Args:
            job_id:       Unique job ID.  Must not already be active.
            input_path:   Source media file path.
            output_dir:   Directory for output file.
            preset_name:  Key from CODEC_PRESETS.
            reframe:      Optional reframe dict (see build_ffmpeg_cmd).
            on_progress:  Optional progress callback fn(percent: float).

        Returns:
            concurrent.futures.Future — resolves to the result dict from
            run_encode_job().
        """
        with self._lock:
            if job_id in self._jobs:
                existing = self._jobs[job_id]
                if existing["status"] in ("pending", "running"):
                    raise ValueError(f"Job {job_id!r} is already active (status={existing['status']})")

            self._jobs[job_id] = {
                "status": "pending",
                "progress": 0.0,
                "output_path": None,
                "error": None,
            }

        def _progress_wrapper(pct: float) -> None:
            with self._lock:
                if job_id in self._jobs:
                    self._jobs[job_id]["progress"] = pct
            if on_progress:
                on_progress(pct)

        def _run() -> Dict:
            with self._lock:
                if job_id in self._jobs:
                    self._jobs[job_id]["status"] = "running"

            result = run_encode_job(
                job_id=job_id,
                input_path=input_path,
                output_dir=output_dir,
                preset_name=preset_name,
                reframe=reframe,
                on_progress=_progress_wrapper,
                _process_registry=self._processes,
            )

            with self._lock:
                if job_id in self._jobs:
                    status = "done" if result["success"] else "failed"
                    self._jobs[job_id].update(
                        status=status,
                        progress=100.0 if result["success"] else self._jobs[job_id]["progress"],
                        output_path=result["output_path"],
                        error=result["error"],
                    )
                self._futures.pop(job_id, None)

            return result

        future = self._executor.submit(_run)
        with self._lock:
            self._futures[job_id] = future

        return future

    def get_status(self, job_id: str) -> Optional[Dict]:
        """Return status dict for a job, or None if job_id is unknown.

        Returned dict keys:
          status      — 'pending' | 'running' | 'done' | 'failed' | 'cancelled'
          progress    — float 0–100
          output_path — str | None
          error       — str | None
        """
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def cancel(self, job_id: str) -> bool:
        """Attempt to cancel a pending or running job.

        For pending jobs, cancels the Future.
        For running jobs, sends SIGTERM to the FFmpeg subprocess.

        Returns:
            True if a cancel was attempted, False if job not found.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False

            # Try to cancel a pending future (only works if not started yet)
            future = self._futures.get(job_id)
            if future is not None:
                future.cancel()

            # Kill subprocess if running
            proc = self._processes.get(job_id)
            if proc is not None:
                try:
                    proc.terminate()
                except Exception as exc:
                    logger.warning("cancel[%s]: terminate failed: %s", job_id, exc)
                self._processes.pop(job_id, None)

            job["status"] = "cancelled"
            job["error"] = "Cancelled by user"

        return True

    def get_all_statuses(self) -> Dict[str, Dict]:
        """Return a snapshot of all job statuses keyed by job_id."""
        with self._lock:
            return {jid: dict(jdata) for jid, jdata in self._jobs.items()}

    def shutdown(self, wait: bool = True) -> None:
        """Shut down the thread pool, optionally waiting for active jobs."""
        self._executor.shutdown(wait=wait)
