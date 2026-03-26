"""
YouTube fetch service — yt-dlp wrapper for VETKA CUT source acquisition.

Provides oEmbed metadata, full yt-dlp metadata, video download with progress
callbacks, segment-based partial downloads, and a thread-pool job manager.

@status: active
@phase: B97
@task: tb_1774431996_1
"""

from __future__ import annotations

import json
import logging
import os
import re
import signal
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

QUALITY_FORMAT_MAP: Dict[str, str] = {
    "best": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    "1080p": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]",
    "720p": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]",
    "480p": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]",
    "audio-only": "bestaudio[ext=m4a]/bestaudio",
}

YTDLP_BIN: str = os.environ.get("YTDLP_BIN", "yt-dlp")

# Matches lines like: [download]  47.3% of ~  123.45MiB
_PROGRESS_RE = re.compile(
    r"\[download\]\s+(\d+(?:\.\d+)?)%\s+of\s+~?\s*[\d.]+\s*\w+",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def fetch_oembed(url: str) -> dict:
    """Fetch YouTube oEmbed JSON for *url*.

    Returns a dict with at least: title, author_name, thumbnail_url, html.
    Uses only stdlib (urllib). Timeout: 10 s.

    Raises urllib.error.URLError / ValueError on failure.
    """
    endpoint = "https://www.youtube.com/oembed"
    params = urllib.parse.urlencode({"url": url, "format": "json"})
    full_url = f"{endpoint}?{params}"

    req = urllib.request.Request(
        full_url,
        headers={"User-Agent": "VETKA-CUT/1.0 (yt-oembed)"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = resp.read()

    data: dict = json.loads(raw)
    return {
        "title": data.get("title", ""),
        "author_name": data.get("author_name", ""),
        "thumbnail_url": data.get("thumbnail_url", ""),
        "html": data.get("html", ""),
        **data,
    }


def fetch_metadata(url: str) -> dict:
    """Run ``yt-dlp --dump-json --no-download`` and return parsed metadata.

    Returned dict keys: id, title, description, channel, duration,
    thumbnail, upload_date, view_count, formats.

    *formats* is a list of dicts with: format_id, ext, height, filesize.

    Raises RuntimeError if yt-dlp exits non-zero.
    """
    cmd = [
        YTDLP_BIN,
        "--dump-json",
        "--no-download",
        url,
    ]
    logger.debug("fetch_metadata cmd=%s", cmd)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"yt-dlp --dump-json failed (rc={result.returncode}): {result.stderr.strip()}"
        )

    raw: dict = json.loads(result.stdout)

    formats = [
        {
            "format_id": f.get("format_id", ""),
            "ext": f.get("ext", ""),
            "height": f.get("height"),
            "filesize": f.get("filesize") or f.get("filesize_approx"),
        }
        for f in raw.get("formats", [])
    ]

    return {
        "id": raw.get("id", ""),
        "title": raw.get("title", ""),
        "description": raw.get("description", ""),
        "channel": raw.get("channel") or raw.get("uploader", ""),
        "duration": raw.get("duration"),
        "thumbnail": raw.get("thumbnail", ""),
        "upload_date": raw.get("upload_date", ""),
        "view_count": raw.get("view_count"),
        "formats": formats,
    }


def download_video(
    url: str,
    output_dir: str,
    quality: str = "best",
    segments: Optional[List[Dict]] = None,
    on_progress: Optional[Callable[[float], None]] = None,
) -> dict:
    """Download *url* to *output_dir* using yt-dlp.

    Parameters
    ----------
    url:
        YouTube (or any yt-dlp-supported) video URL.
    output_dir:
        Directory where the file will be saved.
    quality:
        One of the keys in ``QUALITY_FORMAT_MAP`` (default ``"best"``).
    segments:
        Optional list of ``{"in_time": str, "out_time": str}`` dicts.
        Each segment maps to ``--download-sections "*{in_time}-{out_time}"``.
    on_progress:
        Callable receiving a ``float`` percent (0.0–100.0) as yt-dlp
        reports progress on stderr.

    Returns
    -------
    dict
        ``{success, output_path, title, duration, file_size, error}``
    """
    fmt = QUALITY_FORMAT_MAP.get(quality, QUALITY_FORMAT_MAP["best"])
    output_template = os.path.join(output_dir, "%(title)s.%(ext)s")

    cmd: List[str] = [
        YTDLP_BIN,
        "-f", fmt,
        "-o", output_template,
        "--merge-output-format", "mp4",
        "--newline",          # one progress line per stderr line
    ]

    if segments:
        for seg in segments:
            in_t = seg.get("in_time", "0")
            out_t = seg.get("out_time", "inf")
            cmd += ["--download-sections", f"*{in_t}-{out_t}"]

    cmd.append(url)
    logger.debug("download_video cmd=%s", cmd)

    output_path: Optional[str] = None
    title: Optional[str] = None
    duration: Optional[float] = None
    file_size: Optional[int] = None
    error: Optional[str] = None

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Parse stderr for progress; stdout for merge/destination lines
        assert proc.stderr is not None
        for line in proc.stderr:
            line = line.rstrip()
            if not line:
                continue
            logger.debug("yt-dlp: %s", line)

            # Progress extraction
            if on_progress:
                m = _PROGRESS_RE.search(line)
                if m:
                    try:
                        on_progress(float(m.group(1)))
                    except Exception:
                        pass

            # Destination file detection
            if line.startswith("[Merger]") or "Destination:" in line:
                parts = line.split("Destination:", 1)
                if len(parts) == 2:
                    candidate = parts[1].strip()
                    if candidate:
                        output_path = candidate

        proc.wait()
        if proc.returncode != 0:
            stderr_tail = ""
            if proc.stderr:
                stderr_tail = proc.stderr.read()
            error = f"yt-dlp exited with code {proc.returncode}. {stderr_tail}".strip()
        else:
            # Try to stat the output file for size
            if output_path and os.path.isfile(output_path):
                file_size = os.path.getsize(output_path)
            # Attempt to read duration via a quick probe (best-effort)
            if output_path:
                try:
                    probe_cmd = [
                        "ffprobe", "-v", "quiet",
                        "-print_format", "json",
                        "-show_format",
                        output_path,
                    ]
                    probe_result = subprocess.run(
                        probe_cmd, capture_output=True, text=True, timeout=15
                    )
                    if probe_result.returncode == 0:
                        probe_data = json.loads(probe_result.stdout)
                        duration = float(
                            probe_data.get("format", {}).get("duration", 0) or 0
                        )
                        title = probe_data.get("format", {}).get("tags", {}).get("title")
                except Exception:
                    pass

    except Exception as exc:
        error = str(exc)
        logger.exception("download_video exception for url=%s", url)

    success = error is None and output_path is not None

    return {
        "success": success,
        "output_path": output_path,
        "title": title,
        "duration": duration,
        "file_size": file_size,
        "error": error,
    }


def cancel_download(process: subprocess.Popen) -> None:
    """Send SIGTERM to a running yt-dlp *process*.

    On Windows, falls back to ``process.terminate()``.
    """
    try:
        os.kill(process.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass
    except AttributeError:
        # Windows — signal.SIGTERM may not exist as a kill target
        process.terminate()


# ---------------------------------------------------------------------------
# YouTubeFetchManager
# ---------------------------------------------------------------------------


class YouTubeFetchManager:
    """Thread-pool manager for YouTube download jobs.

    Uses a ``ThreadPoolExecutor`` with ``max_workers=2`` so at most two
    downloads run concurrently (mirrors pre-transcode worker design in B73).

    Usage::

        mgr = YouTubeFetchManager()
        mgr.submit("job-1", url, "/tmp/out", quality="720p",
                   on_progress=lambda p: print(p))
        status = mgr.get_status("job-1")
        mgr.cancel("job-1")
    """

    def __init__(self) -> None:
        self._executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=2)
        # job_id -> {"future": Future, "process": Optional[Popen], "status": dict}
        self._jobs: Dict[str, Dict] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(
        self,
        job_id: str,
        url: str,
        output_dir: str,
        quality: str = "best",
        segments: Optional[List[Dict]] = None,
        on_progress: Optional[Callable[[float], None]] = None,
    ) -> None:
        """Queue a download job identified by *job_id*.

        If *job_id* already exists and is still running, this is a no-op.
        """
        if job_id in self._jobs:
            existing = self._jobs[job_id]
            future: Future = existing["future"]
            if not future.done():
                logger.warning("YouTubeFetchManager: job %s already running", job_id)
                return

        self._jobs[job_id] = {
            "future": None,
            "process": None,
            "status": {
                "job_id": job_id,
                "url": url,
                "state": "pending",
                "percent": 0.0,
                "result": None,
                "error": None,
            },
        }

        def _wrapped_progress(percent: float) -> None:
            self._jobs[job_id]["status"]["percent"] = percent
            if on_progress:
                on_progress(percent)

        future = self._executor.submit(
            self._run_job,
            job_id,
            url,
            output_dir,
            quality,
            segments,
            _wrapped_progress,
        )
        self._jobs[job_id]["future"] = future

    def get_status(self, job_id: str) -> dict:
        """Return status dict for *job_id*, or ``{"error": "not found"}``."""
        if job_id not in self._jobs:
            return {"error": f"job {job_id!r} not found"}
        return dict(self._jobs[job_id]["status"])

    def cancel(self, job_id: str) -> None:
        """Cancel *job_id*: terminate its yt-dlp process if running."""
        if job_id not in self._jobs:
            logger.warning("YouTubeFetchManager.cancel: unknown job %s", job_id)
            return

        job = self._jobs[job_id]
        future: Optional[Future] = job.get("future")
        proc: Optional[subprocess.Popen] = job.get("process")

        # Cancel if not yet started
        if future and not future.done():
            future.cancel()

        # Kill the subprocess if it is running
        if proc is not None:
            cancel_download(proc)

        job["status"]["state"] = "cancelled"

    def shutdown(self, wait: bool = True) -> None:
        """Shut down the thread pool executor."""
        self._executor.shutdown(wait=wait)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_job(
        self,
        job_id: str,
        url: str,
        output_dir: str,
        quality: str,
        segments: Optional[List[Dict]],
        on_progress: Callable[[float], None],
    ) -> dict:
        """Execute inside the thread pool; updates job status dict."""
        status = self._jobs[job_id]["status"]
        status["state"] = "running"

        # Monkey-patch Popen creation so we can store the process reference
        # for cancellation. We wrap download_video via a thin shim.
        _original_popen = subprocess.Popen
        _self = self

        class _TrackingPopen(_original_popen):  # type: ignore[valid-type]
            def __init__(inner_self, *args, **kwargs):  # noqa: N805
                super().__init__(*args, **kwargs)
                _self._jobs[job_id]["process"] = inner_self

        subprocess.Popen = _TrackingPopen  # type: ignore[misc]
        try:
            result = download_video(
                url=url,
                output_dir=output_dir,
                quality=quality,
                segments=segments,
                on_progress=on_progress,
            )
        finally:
            subprocess.Popen = _original_popen  # type: ignore[misc]
            self._jobs[job_id]["process"] = None

        status["state"] = "done" if result["success"] else "error"
        status["result"] = result
        status["error"] = result.get("error")
        return result
