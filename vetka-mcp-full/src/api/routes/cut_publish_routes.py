"""
MARKER_B96 — Publish sub-router.
FastAPI routes for social/platform publish pipeline: prepare encode jobs,
poll status, cancel, list presets and platform constraints.

@status: active
@phase: B96
@task: tb_1774432016_1
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

publish_router = APIRouter(tags=["CUT-Publish"])

# ---------------------------------------------------------------------------
# Platform presets — codec params per delivery target
# ---------------------------------------------------------------------------

PLATFORM_PRESETS: dict[str, dict[str, Any]] = {
    "youtube_1080p": {
        "label": "YouTube 1080p",
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "vcodec": "h264",
        "crf": 18,
        "acodec": "aac",
        "audio_bitrate": "192k",
        "container": "mp4",
    },
    "youtube_4k": {
        "label": "YouTube 4K",
        "width": 3840,
        "height": 2160,
        "fps": 30,
        "vcodec": "h264",
        "crf": 16,
        "acodec": "aac",
        "audio_bitrate": "256k",
        "container": "mp4",
    },
    "instagram_reels": {
        "label": "Instagram Reels (9:16)",
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "vcodec": "h264",
        "crf": 20,
        "acodec": "aac",
        "audio_bitrate": "128k",
        "container": "mp4",
    },
    "instagram_feed": {
        "label": "Instagram Feed (1:1)",
        "width": 1080,
        "height": 1080,
        "fps": 30,
        "vcodec": "h264",
        "crf": 20,
        "acodec": "aac",
        "audio_bitrate": "128k",
        "container": "mp4",
    },
    "tiktok": {
        "label": "TikTok (9:16)",
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "vcodec": "h264",
        "crf": 20,
        "acodec": "aac",
        "audio_bitrate": "128k",
        "container": "mp4",
    },
    "twitter": {
        "label": "Twitter / X",
        "width": 1280,
        "height": 720,
        "fps": 30,
        "vcodec": "h264",
        "crf": 22,
        "acodec": "aac",
        "audio_bitrate": "128k",
        "container": "mp4",
    },
    "vimeo_1080p": {
        "label": "Vimeo 1080p",
        "width": 1920,
        "height": 1080,
        "fps": 25,
        "vcodec": "h264",
        "crf": 16,
        "acodec": "aac",
        "audio_bitrate": "320k",
        "container": "mp4",
    },
    "prores_master": {
        "label": "ProRes Master (archival)",
        "width": 1920,
        "height": 1080,
        "fps": 25,
        "vcodec": "prores_ks",
        "profile": "3",
        "acodec": "pcm_s16le",
        "audio_bitrate": None,
        "container": "mov",
    },
}

# Map route-level platform keys → worker CODEC_PRESETS keys
_PRESET_MAP: dict[str, str] = {
    "youtube_1080p": "yt_h264_1080",
    "youtube_4k": "yt_h264_1080",  # uses same preset, worker scales
    "instagram_reels": "ig_h264_reels",
    "instagram_feed": "ig_h264_reels",
    "tiktok": "tt_h264",
    "twitter": "x_h264_1080",
    "vimeo_1080p": "yt_h264_1080",
    "prores_master": "file_prores422",
}

PLATFORM_CONSTRAINTS: dict[str, dict[str, Any]] = {
    "youtube": {
        "max_file_size_gb": 256,
        "max_duration_hours": 12,
        "allowed_containers": ["mp4", "mov", "avi"],
        "recommended_codec": "h264",
        "max_fps": 60,
        "notes": "H.264 or H.265, AAC audio",
    },
    "instagram": {
        "max_file_size_gb": 1,
        "max_duration_seconds": 3600,
        "allowed_containers": ["mp4"],
        "recommended_codec": "h264",
        "max_fps": 60,
        "notes": "MP4 required, H.264 + AAC",
    },
    "tiktok": {
        "max_file_size_gb": 2,
        "max_duration_minutes": 10,
        "allowed_containers": ["mp4"],
        "recommended_codec": "h264",
        "max_fps": 60,
        "notes": "MP4 required, 9:16 aspect preferred",
    },
    "twitter": {
        "max_file_size_mb": 512,
        "max_duration_seconds": 140,
        "allowed_containers": ["mp4", "mov"],
        "recommended_codec": "h264",
        "max_fps": 60,
        "notes": "Max 512 MB, 2 min 20 sec limit",
    },
    "vimeo": {
        "max_file_size_gb": 5,
        "max_duration_hours": 24,
        "allowed_containers": ["mp4", "mov"],
        "recommended_codec": "h264",
        "max_fps": 60,
        "notes": "Accepts ProRes for Vimeo Review links",
    },
}

# ---------------------------------------------------------------------------
# Singleton accessor for EncodeJobManager
# ---------------------------------------------------------------------------

_encode_manager: Any = None


def _get_encode_manager() -> Any:
    """Return the module-level EncodeJobManager singleton, creating on first call."""
    global _encode_manager
    if _encode_manager is None:
        try:
            from src.services.publish.encode_worker import EncodeJobManager  # type: ignore[import]
            _encode_manager = EncodeJobManager()
            logger.info("EncodeJobManager singleton initialised")
        except ImportError as exc:
            logger.error("publish.encode_worker not available: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="Encode worker service not available — run `pip install vetka-publish` or check src/services/publish/",
            ) from exc
    return _encode_manager


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------


class PublishPrepareRequest(BaseModel):
    """Request to prepare platform encode jobs for a source media file."""

    source_path: str = Field(description="Absolute path to the source media file")
    platforms: list[str] = Field(
        description="List of platform preset keys (e.g. ['youtube_1080p', 'instagram_reels'])"
    )
    reframe_mode: Literal["center", "none"] = Field(
        default="center",
        description="'center' — auto-reframe to platform aspect ratio; 'none' — letterbox/pillarbox",
    )
    output_dir: str | None = Field(
        default=None,
        description="Directory to write encoded files. Defaults to system temp/cut_publish_output/",
    )


class PublishStatusRequest(BaseModel):
    """Request to poll status for a list of encode job IDs."""

    job_ids: list[str] = Field(description="List of job IDs returned from /publish/prepare")


class PublishCancelRequest(BaseModel):
    """Request to cancel a running encode job."""

    job_id: str = Field(description="Job ID to cancel")


# ---------------------------------------------------------------------------
# Route: POST /publish/prepare
# ---------------------------------------------------------------------------


@publish_router.post("/publish/prepare")
async def publish_prepare(req: PublishPrepareRequest) -> dict[str, Any]:
    """
    Prepare platform encode jobs for a source media file.

    For each requested platform, resolves the codec preset and enqueues an
    encode job via EncodeJobManager.  Returns the list of created jobs with
    their IDs so the client can poll /publish/status.

    Returns:
        {"success": true, "jobs": [{"job_id": str, "platform": str, "preset": str}]}
    """
    source = Path(req.source_path)
    if not source.exists():
        raise HTTPException(status_code=400, detail=f"source_path not found: {req.source_path}")

    # Resolve output directory
    output_dir = Path(req.output_dir) if req.output_dir else Path(tempfile.gettempdir()) / "cut_publish_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Validate requested platforms
    unknown = [p for p in req.platforms if p not in PLATFORM_PRESETS]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown platform presets: {unknown}. Available: {sorted(PLATFORM_PRESETS.keys())}",
        )

    manager = _get_encode_manager()
    created_jobs: list[dict[str, str]] = []

    import uuid
    for platform_key in req.platforms:
        job_id = f"pub_{platform_key}_{uuid.uuid4().hex[:8]}"
        reframe = {"mode": "center", "target_aspect": "9:16"} if req.reframe_mode == "center" else None
        worker_preset = _PRESET_MAP.get(platform_key, platform_key)
        try:
            manager.submit(
                job_id=job_id,
                input_path=str(source),
                output_dir=str(output_dir),
                preset_name=worker_preset,
                reframe=reframe,
            )
            created_jobs.append({"job_id": job_id, "platform": platform_key, "preset": platform_key})
            logger.info("Publish job created: job_id=%s platform=%s", job_id, platform_key)
        except Exception as exc:
            logger.error("Failed to create encode job for platform %s: %s", platform_key, exc)
            raise HTTPException(
                status_code=500, detail=f"Failed to create encode job for platform '{platform_key}': {exc}"
            ) from exc

    return {"success": True, "jobs": created_jobs}


# ---------------------------------------------------------------------------
# Route: GET /publish/status
# ---------------------------------------------------------------------------


@publish_router.get("/publish/status")
async def publish_status(
    job_ids: str = Query(description="Comma-separated list of job IDs to poll"),
) -> dict[str, Any]:
    """
    Poll the status of one or more encode jobs.

    Query param:
        job_ids — comma-separated job ID strings

    Returns:
        {"jobs": [{"job_id", "platform", "status", "progress", "output_path", "error"}]}
    """
    ids = [j.strip() for j in job_ids.split(",") if j.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="job_ids query param is required and must not be empty")

    manager = _get_encode_manager()
    results: list[dict[str, Any]] = []

    for job_id in ids:
        try:
            info = manager.get_status(job_id)
            results.append(
                {
                    "job_id": job_id,
                    "platform": info.get("platform", ""),
                    "status": info.get("status", "unknown"),
                    "progress": info.get("progress", 0.0),
                    "output_path": info.get("output_path", ""),
                    "error": info.get("error", None),
                }
            )
        except KeyError:
            results.append(
                {
                    "job_id": job_id,
                    "platform": "",
                    "status": "not_found",
                    "progress": 0.0,
                    "output_path": "",
                    "error": f"Job '{job_id}' not found",
                }
            )
        except Exception as exc:
            logger.error("Error fetching status for job %s: %s", job_id, exc)
            results.append(
                {
                    "job_id": job_id,
                    "platform": "",
                    "status": "error",
                    "progress": 0.0,
                    "output_path": "",
                    "error": str(exc),
                }
            )

    return {"jobs": results}


# ---------------------------------------------------------------------------
# Route: POST /publish/cancel
# ---------------------------------------------------------------------------


@publish_router.post("/publish/cancel")
async def publish_cancel(req: PublishCancelRequest) -> dict[str, Any]:
    """
    Cancel a running encode job.

    Returns:
        {"success": bool, "job_id": str, "message": str}
    """
    manager = _get_encode_manager()
    try:
        cancelled = manager.cancel(req.job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Job '{req.job_id}' not found")
    except Exception as exc:
        logger.error("Cancel failed for job %s: %s", req.job_id, exc)
        raise HTTPException(status_code=500, detail=f"Cancel failed: {exc}") from exc

    if cancelled:
        logger.info("Publish job cancelled: job_id=%s", req.job_id)
        return {"success": True, "job_id": req.job_id, "message": "Job cancelled successfully"}
    return {"success": False, "job_id": req.job_id, "message": "Job could not be cancelled (already finished or not running)"}


# ---------------------------------------------------------------------------
# Route: GET /publish/presets
# ---------------------------------------------------------------------------


@publish_router.get("/publish/presets")
async def publish_presets() -> dict[str, Any]:
    """
    List all available codec presets with their encode parameters.

    Returns:
        {"presets": {preset_key: {label, width, height, fps, vcodec, crf, acodec, ...}}}
    """
    return {"presets": PLATFORM_PRESETS}


# ---------------------------------------------------------------------------
# Route: GET /publish/constraints
# ---------------------------------------------------------------------------


@publish_router.get("/publish/constraints")
async def publish_constraints() -> dict[str, Any]:
    """
    List platform delivery constraints (file size, duration, container limits).

    Returns:
        {"constraints": {platform: {max_file_size_*, max_duration_*, allowed_containers, notes}}}
    """
    return {"constraints": PLATFORM_CONSTRAINTS}
