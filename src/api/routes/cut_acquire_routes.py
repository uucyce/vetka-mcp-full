"""
MARKER_B97 — Source Acquire sub-router.
FastAPI routes for YouTube fetch pipeline: metadata fetch, download job management,
status polling, cancellation, and SSE progress streaming.

@status: active
@phase: B97
@task: tb_1774431996_1
"""
from __future__ import annotations

import asyncio
import json
import logging
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

logger = logging.getLogger(__name__)

acquire_router = APIRouter(tags=["CUT-Acquire"])

# ---------------------------------------------------------------------------
# Default output directory
# ---------------------------------------------------------------------------

_DEFAULT_OUTPUT_DIR = str(Path(tempfile.gettempdir()) / "cut_youtube_downloads")

# ---------------------------------------------------------------------------
# YouTubeFetchManager — inline singleton implementation
# ---------------------------------------------------------------------------


class YouTubeFetchManager:
    """Manages async yt-dlp download jobs with status tracking."""

    def __init__(self) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Metadata helpers
    # ------------------------------------------------------------------

    async def fetch_metadata(self, url: str) -> Dict[str, Any]:
        """Fetch oEmbed + yt-dlp metadata for *url*."""
        oembed: Dict[str, Any] = {}
        ytdlp: Dict[str, Any] = {}

        # --- oEmbed ---
        try:
            oembed = await self._fetch_oembed(url)
        except Exception as exc:
            logger.warning("oEmbed fetch failed for %s: %s", url, exc)

        # --- yt-dlp dump-json ---
        try:
            ytdlp = await self._fetch_ytdlp_meta(url)
        except Exception as exc:
            logger.warning("yt-dlp metadata fetch failed for %s: %s", url, exc)

        return {"oembed": oembed, "ytdlp": ytdlp}

    async def _fetch_oembed(self, url: str) -> Dict[str, Any]:
        oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
        proc = await asyncio.create_subprocess_exec(
            "curl", "-s", oembed_url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0 and stdout:
            return json.loads(stdout.decode())
        return {}

    async def _fetch_ytdlp_meta(self, url: str) -> Dict[str, Any]:
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp", "--dump-json", "--no-download", url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0 and stdout:
            return json.loads(stdout.decode())
        return {"error": stderr.decode().strip()}

    # ------------------------------------------------------------------
    # Download job management
    # ------------------------------------------------------------------

    def start_download(
        self,
        url: str,
        output_dir: str,
        quality: str,
        segments: Optional[List[Dict[str, float]]],
    ) -> str:
        """Enqueue a download job and return its *job_id*."""
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {
            "job_id": job_id,
            "url": url,
            "output_dir": output_dir,
            "quality": quality,
            "segments": segments or [],
            "status": "queued",
            "progress": 0.0,
            "output_path": None,
            "error": None,
        }
        asyncio.ensure_future(self._run_download(job_id))
        return job_id

    async def _run_download(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return

        job["status"] = "downloading"
        output_dir = Path(job["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        quality = job["quality"]
        url = job["url"]

        # Build yt-dlp format selector
        format_map = {
            "best": "bestvideo+bestaudio/best",
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "audio-only": "bestaudio/best",
        }
        fmt = format_map.get(quality, "bestvideo+bestaudio/best")

        cmd = [
            "yt-dlp",
            "-f", fmt,
            "--merge-output-format", "mp4",
            "--newline",
            "-o", str(output_dir / "%(title)s.%(ext)s"),
            url,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            output_lines: List[str] = []
            assert proc.stdout is not None
            async for raw in proc.stdout:
                line = raw.decode(errors="replace").strip()
                output_lines.append(line)
                # Parse [download] XX.X% lines
                if line.startswith("[download]") and "%" in line:
                    try:
                        pct_str = line.split("%")[0].split()[-1]
                        job["progress"] = float(pct_str)
                    except (ValueError, IndexError):
                        pass
                # Detect destination path
                if "Destination:" in line or "Merging formats into" in line:
                    parts = line.split('"') if '"' in line else line.split("into ")
                    if len(parts) >= 2:
                        job["output_path"] = parts[-1].strip().strip('"')

            await proc.wait()

            if self._jobs.get(job_id, {}).get("status") == "cancelled":
                return

            if proc.returncode == 0:
                job["status"] = "done"
                job["progress"] = 100.0
            else:
                job["status"] = "error"
                job["error"] = "\n".join(output_lines[-5:])

        except Exception as exc:
            job["status"] = "error"
            job["error"] = str(exc)

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._jobs.get(job_id)

    def get_statuses(self, job_ids: List[str]) -> Dict[str, Any]:
        return {jid: self._jobs.get(jid) for jid in job_ids}

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job:
            return False
        if job["status"] in ("done", "error", "cancelled"):
            return False
        job["status"] = "cancelled"
        return True


# ---------------------------------------------------------------------------
# Module-level singleton accessor (lazy init — same pattern as publish routes)
# ---------------------------------------------------------------------------

_fetch_manager: Optional[YouTubeFetchManager] = None


def _get_fetch_manager() -> YouTubeFetchManager:
    """Return the module-level YouTubeFetchManager singleton, creating on first call."""
    global _fetch_manager
    if _fetch_manager is None:
        _fetch_manager = YouTubeFetchManager()
        logger.info("YouTubeFetchManager singleton initialised")
    return _fetch_manager


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class YouTubeMetadataRequest(BaseModel):
    """Request oEmbed + yt-dlp metadata for a YouTube URL."""

    url: str = Field(description="YouTube video URL")


class YouTubeDownloadRequest(BaseModel):
    """Request to start a YouTube download job."""

    url: str = Field(description="YouTube video URL")
    output_dir: Optional[str] = Field(
        default=None,
        description=(
            "Directory to save downloaded files. "
            f"Defaults to {_DEFAULT_OUTPUT_DIR}/"
        ),
    )
    quality: Literal["best", "1080p", "720p", "480p", "audio-only"] = Field(
        default="best",
        description="Download quality preset",
    )
    segments: Optional[List[Dict[str, float]]] = Field(
        default=None,
        description=(
            "Optional list of segments to extract after download. "
            "Each dict must have 'in_time' (float, seconds) and 'out_time' (float, seconds)."
        ),
    )


class AcquireCancelRequest(BaseModel):
    """Request to cancel an in-flight download job."""

    job_id: str = Field(description="Job ID returned by the download endpoint")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@acquire_router.post("/acquire/youtube/metadata")
async def youtube_metadata(request: YouTubeMetadataRequest) -> Dict[str, Any]:
    """Fetch combined oEmbed + yt-dlp metadata for a YouTube URL.

    Returns a dict with keys ``oembed`` and ``ytdlp``.
    """
    manager = _get_fetch_manager()
    try:
        return await manager.fetch_metadata(request.url)
    except Exception as exc:
        logger.error("Metadata fetch error for %s: %s", request.url, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@acquire_router.post("/acquire/youtube/download")
async def youtube_download(request: YouTubeDownloadRequest) -> Dict[str, str]:
    """Start a yt-dlp download job.

    Returns ``{"job_id": "<uuid>"}`` immediately; poll
    ``GET /acquire/youtube/status?job_ids=<id>`` or stream
    ``GET /acquire/events/<id>`` for progress.
    """
    manager = _get_fetch_manager()
    output_dir = request.output_dir or _DEFAULT_OUTPUT_DIR
    try:
        job_id = manager.start_download(
            url=request.url,
            output_dir=output_dir,
            quality=request.quality,
            segments=request.segments,
        )
        return {"job_id": job_id}
    except Exception as exc:
        logger.error("Download start error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@acquire_router.get("/acquire/youtube/status")
async def youtube_status(
    job_ids: str = Query(
        description="Comma-separated list of job IDs to query",
    ),
) -> Dict[str, Any]:
    """Return the current status of one or more download jobs.

    Pass ``job_ids`` as a comma-separated query parameter,
    e.g. ``?job_ids=abc,def``.
    """
    manager = _get_fetch_manager()
    ids = [jid.strip() for jid in job_ids.split(",") if jid.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="job_ids query param is required")
    return manager.get_statuses(ids)


@acquire_router.post("/acquire/youtube/cancel")
async def youtube_cancel(request: AcquireCancelRequest) -> Dict[str, Any]:
    """Cancel an in-flight download job.

    Returns ``{"cancelled": true}`` if the job was found and cancelled,
    or raises 404 / 409 otherwise.
    """
    manager = _get_fetch_manager()
    job = manager.get_status(request.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {request.job_id!r} not found")
    ok = manager.cancel(request.job_id)
    if not ok:
        status = job.get("status", "unknown")
        raise HTTPException(
            status_code=409,
            detail=f"Job {request.job_id!r} cannot be cancelled (status={status!r})",
        )
    return {"cancelled": True, "job_id": request.job_id}


@acquire_router.get("/acquire/events/{job_id}")
async def acquire_events(job_id: str) -> StreamingResponse:
    """Server-Sent Events stream for a download job.

    Emits a ``data:`` line every 500 ms with the JSON-serialised job status.
    Terminates automatically when status reaches ``done``, ``error``, or
    ``cancelled``.  Sends an ``event: error`` frame if the job is not found.
    """
    manager = _get_fetch_manager()

    async def event_generator(job_id: str):  # type: ignore[return]
        while True:
            status = manager.get_status(job_id)
            if not status:
                yield f"event: error\ndata: job not found\n\n"
                break
            yield f"data: {json.dumps(status)}\n\n"
            if status.get("status") in ("done", "error", "cancelled"):
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(job_id), media_type="text/event-stream")
