# MARKER_136.ARTIFACT_API_ROUTE
# MARKER_141.ARTIFACT_CONTENT: Added content reading endpoint
"""REST routes for artifacts panel (list + approve/reject + content)."""

from pathlib import Path
import base64
import mimetypes
import hashlib
import os
import subprocess
import json
import math
import wave
import re
import tempfile
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.api.handlers.artifact_routes import (
    list_artifacts_for_panel,
    approve_artifact_for_panel,
    reject_artifact_for_panel,
    save_search_result_artifact,
    save_webpage_artifact,
)
from src.scanners.qdrant_updater import get_qdrant_updater
from src.scanners.mime_policy import validate_ingest_target
from src.scanners.extractor_registry import get_media_extractor_registry
from src.services.artifact_scanner import set_artifact_favorite


router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


async def _try_index_saved_artifact(result: dict, request: Request) -> dict:
    """
    Best-effort index bridge for saved artifacts.
    Keeps API response stable and only augments with index status fields.
    """
    try:
        if not result.get("success") or not result.get("file_path"):
            return result
        target_path = Path(str(result["file_path"]))
        if not target_path.exists() or not target_path.is_file():
            result["indexed"] = False
            result["index_error"] = "saved_artifact_not_found"
            return result
        allowed, policy = validate_ingest_target(str(target_path), int(target_path.stat().st_size))
        if not allowed:
            result["indexed"] = False
            result["index_error"] = "ingest_policy_blocked"
            result["index_policy"] = {
                "code": policy.get("code"),
                "message": policy.get("message"),
                "extension": policy.get("extension"),
                "category": policy.get("category"),
                "mime_type": policy.get("mime_type"),
            }
            return result
        qdrant_manager = getattr(request.app.state, "qdrant_manager", None)
        qdrant_client = getattr(qdrant_manager, "client", None) if qdrant_manager else None
        if not qdrant_client:
            result["indexed"] = False
            result["index_error"] = "qdrant_client_not_available"
            return result
        updater = get_qdrant_updater(qdrant_client=qdrant_client, enable_triple_write=True)
        indexed = updater.update_file(target_path)
        result["indexed"] = bool(indexed)
        if indexed:
            try:
                from src.memory.qdrant_batch_manager import get_batch_manager

                extraction = get_media_extractor_registry().extract_file(
                    target_path,
                    rel_path=str(target_path),
                    max_text_chars=5000,
                )
                content = extraction.text[:5000]
                if not content:
                    digest = hashlib.sha256(target_path.read_bytes()).hexdigest()
                    content = f"[Artifact summary] path={target_path} sha256={digest[:16]}"

                ext = target_path.suffix.lower()
                if ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".svg"}:
                    artifact_type = "image"
                elif ext in {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}:
                    artifact_type = "audio"
                elif ext in {".mp4", ".mov", ".mkv", ".avi", ".webm"}:
                    artifact_type = "video"
                elif ext == ".pdf":
                    artifact_type = "document_pdf"
                else:
                    artifact_type = "text"

                batch_mgr = get_batch_manager()
                artifact_id = str(result.get("artifact_id") or result.get("id") or result.get("name") or target_path.name)
                workflow_id = str(result.get("workflow_id") or "artifact_api")
                await batch_mgr.queue_artifact(
                    artifact_id=artifact_id,
                    name=target_path.name,
                    content=content,
                    artifact_type=artifact_type,
                    workflow_id=workflow_id,
                    filepath=str(target_path),
                )
                # Ensure artifact lane is persisted even if background loop isn't started.
                await batch_mgr.force_flush()
                result["artifact_batch_queued"] = True
            except Exception as batch_err:
                result["artifact_batch_queued"] = False
                result["artifact_batch_error"] = str(batch_err)[:200]
    except Exception as idx_err:
        result["indexed"] = False
        result["index_error"] = str(idx_err)[:200]
    return result


class ArtifactDecisionRequest(BaseModel):
    reason: Optional[str] = None

class ArtifactFavoriteRequest(BaseModel):
    is_favorite: bool


class SaveWebpageRequest(BaseModel):
    url: str
    title: Optional[str] = None
    snippet: Optional[str] = None
    raw_html: Optional[str] = None
    raw_text: Optional[str] = None
    output_format: Optional[str] = None
    file_name: Optional[str] = None
    target_node_path: Optional[str] = None


class SaveSearchResultRequest(BaseModel):
    source: str
    path: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    snippet: Optional[str] = None
    output_format: Optional[str] = None
    file_name: Optional[str] = None
    target_node_path: Optional[str] = None


class MediaPreviewRequest(BaseModel):
    path: str = Field(..., description="Absolute or workspace-relative path to media file")
    waveform_bins: int = Field(default=120, ge=16, le=1024)
    preview_segments_limit: int = Field(default=64, ge=1, le=256)


class MediaWindowMetadataRequest(BaseModel):
    path: str = Field(..., description="Absolute or workspace-relative path to media file")


class MediaStartupRequest(BaseModel):
    scope_path: str = Field(default="", description="Folder path for media-mode startup analysis")
    quick_scan_limit: int = Field(default=5000, ge=100, le=50000)


class MediaSemanticLinksRequest(BaseModel):
    path: str = Field(..., description="Current media path")
    query_text: str = Field(default="", description="Segment text for semantic retrieval")
    start_sec: float = Field(default=0.0)
    end_sec: float = Field(default=0.0)
    limit: int = Field(default=12, ge=1, le=64)
    include_same_file: bool = Field(default=True)


class MediaRhythmAssistRequest(BaseModel):
    path: str = Field(..., description="Current media path")
    bins: int = Field(default=120, ge=24, le=1024)
    segments_limit: int = Field(default=256, ge=1, le=1024)


class MediaCamOverlayRequest(BaseModel):
    path: str = Field(..., description="Current media path")
    bins: int = Field(default=120, ge=24, le=1024)
    segments_limit: int = Field(default=256, ge=1, le=1024)


class MediaTranscriptNormalizeRequest(BaseModel):
    path: str = Field(..., description="Current media path")
    max_transcribe_sec: Optional[int] = Field(default=None, ge=5, le=1200)
    clip_for_testing_only: bool = Field(default=False, description="Enable duration clipping for tests only")
    segments_limit: int = Field(default=256, ge=1, le=4096)


class MediaExportPremiereXMLRequest(BaseModel):
    path: str = Field(..., description="Current media path")
    sequence_name: str = Field(default="VETKA_Sequence")
    fps: float = Field(default=30.0, ge=1.0, le=120.0)
    max_transcribe_sec: Optional[int] = Field(default=None, ge=5, le=1200)
    clip_for_testing_only: bool = Field(default=False)
    segments_limit: int = Field(default=1024, ge=1, le=4096)


class MediaExportFCPXMLRequest(BaseModel):
    path: str = Field(..., description="Current media path")
    sequence_name: str = Field(default="VETKA_Sequence")
    fps: float = Field(default=30.0, ge=1.0, le=120.0)
    max_transcribe_sec: Optional[int] = Field(default=None, ge=5, le=1200)
    clip_for_testing_only: bool = Field(default=False)
    segments_limit: int = Field(default=1024, ge=1, le=4096)


@router.get("")
async def get_artifacts():
    return list_artifacts_for_panel()


@router.post("/{artifact_id}/approve")
async def approve_artifact_endpoint(artifact_id: str, body: ArtifactDecisionRequest):
    return approve_artifact_for_panel(
        artifact_id=artifact_id,
        reason=body.reason or "Approved via API",
    )


@router.post("/{artifact_id}/reject")
async def reject_artifact_endpoint(artifact_id: str, body: ArtifactDecisionRequest):
    return reject_artifact_for_panel(
        artifact_id=artifact_id,
        reason=body.reason or "Rejected via API",
    )


@router.put("/{artifact_id}/favorite")
async def favorite_artifact_endpoint(artifact_id: str, body: ArtifactFavoriteRequest, request: Request):
    result = set_artifact_favorite(
        artifact_id=artifact_id,
        is_favorite=body.is_favorite,
    )
    if not result.get("success"):
        return result

    # MARKER_137.6F: Optional CAM memory sync for favorited artifacts.
    try:
        flask_config = getattr(request.app.state, "flask_config", {}) if request and request.app else {}
        if bool(flask_config.get("ELISYA_ENABLED", False)) and body.is_favorite:
            from src.orchestration.cam_event_handler import emit_cam_event
            await emit_cam_event(
                "artifact_created",
                {
                    "path": f"artifact_favorites/{artifact_id}",
                    "content": f"Favorite artifact: {artifact_id}",
                    "source_agent": "artifact_routes",
                },
                source="artifact_routes",
            )
    except Exception:
        pass

    # MARKER_137.6F: ENGRAM user preference sync (non-critical).
    try:
        from src.memory.engram_user_memory import get_engram_user_memory

        engram = get_engram_user_memory()
        user_id = (
            request.headers.get("x-user-id")
            or request.headers.get("x-session-user")
            or request.headers.get("x-session-id")
            or "danila"
        ).strip() or "danila"

        highlights = engram.get_preference(user_id, "project_highlights", "highlights")
        if not isinstance(highlights, dict):
            highlights = {}

        favorites = highlights.get("favorite_artifacts", [])
        if not isinstance(favorites, list):
            favorites = []

        if body.is_favorite:
            if artifact_id not in favorites:
                favorites.append(artifact_id)
        else:
            favorites = [aid for aid in favorites if aid != artifact_id]

        highlights["favorite_artifacts"] = favorites[-500:]
        engram.set_preference(
            user_id,
            "project_highlights",
            "highlights",
            highlights,
            confidence=0.85 if body.is_favorite else 0.72,
        )
    except Exception:
        pass

    return result


@router.post("/save-webpage")
async def save_webpage_endpoint(body: SaveWebpageRequest, request: Request):
    result = await save_webpage_artifact(
        url=body.url,
        title=body.title or "",
        snippet=body.snippet or "",
        raw_html=body.raw_html or "",
        raw_text=body.raw_text or "",
        output_format=body.output_format or "md",
        file_name=body.file_name or "",
        target_node_path=body.target_node_path or "",
    )
    # MARKER_153.IMPL.G16_WEB_SAVE_INDEX_BRIDGE
    return await _try_index_saved_artifact(result, request)


@router.post("/save-search-result")
async def save_search_result_endpoint(body: SaveSearchResultRequest, request: Request):
    result = await save_search_result_artifact(
        source=body.source,
        path=body.path or "",
        url=body.url or "",
        title=body.title or "",
        snippet=body.snippet or "",
        output_format=body.output_format or "md",
        file_name=body.file_name or "",
        target_node_path=body.target_node_path or "",
    )
    # MARKER_153.IMPL.G16_SEARCH_SAVE_INDEX_BRIDGE
    return await _try_index_saved_artifact(result, request)


def _probe_media_duration(path: Path) -> float:
    """Best-effort duration probing via ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if res.returncode == 0 and res.stdout:
            payload = json.loads(res.stdout)
            duration = float((payload.get("format", {}) or {}).get("duration", 0.0) or 0.0)
            if duration > 0:
                return duration
    except Exception:
        pass
    return 0.0


def _encode_raw_url(path: Path) -> str:
    return f"/api/files/raw?path={quote(str(path), safe='')}"


def _compute_waveform_bins_via_ffmpeg(path: Path, bins: int) -> tuple[list[float], int]:
    """Best-effort waveform extraction for non-WAV media."""
    try:
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "s16le",
            "-",
        ]
        res = subprocess.run(cmd, capture_output=True, timeout=30)
        if res.returncode != 0 or not res.stdout:
            return [], 0
        import struct

        frame_count = len(res.stdout) // 2
        if frame_count <= 0:
            return [], 0
        vals = struct.unpack("<" + "h" * frame_count, res.stdout[: frame_count * 2])
        samples = [abs(v / 32767.0) for v in vals]
        chunk_size = max(1, math.ceil(len(samples) / bins))
        out: list[float] = []
        for i in range(0, len(samples), chunk_size):
            chunk = samples[i : i + chunk_size]
            if chunk:
                out.append(min(1.0, max(0.0, max(chunk))))
        return out[:bins], 16000
    except Exception:
        return [], 0


def _media_cache_root() -> Path:
    return (Path(__file__).parent.parent.parent.parent / ".media_cache").resolve()


def _ensure_video_preview_assets(target: Path, duration_sec: float) -> dict:
    """
    Generate poster + animated 300ms preview only (no playback transcode).
    """
    cache_root = _media_cache_root()
    cache_root.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(f"{target}:{target.stat().st_mtime_ns}".encode("utf-8")).hexdigest()[:16]
    out_dir = cache_root / key
    out_dir.mkdir(parents=True, exist_ok=True)
    poster = out_dir / "poster.jpg"
    animated = out_dir / "preview_300ms.webp"

    if not poster.exists():
        # pick near-first frame but avoid pure black first frame
        t = min(max(0.08, duration_sec * 0.03), max(0.08, duration_sec - 0.05)) if duration_sec > 0 else 0.08
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{t:.3f}",
                "-i",
                str(target),
                "-frames:v",
                "1",
                "-vf",
                "scale=640:-1:flags=lanczos",
                str(poster),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    if not animated.exists():
        # 300ms animated preview
        t = min(max(0.08, duration_sec * 0.03), max(0.08, duration_sec - 0.35)) if duration_sec > 0 else 0.08
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{t:.3f}",
                "-t",
                "0.3",
                "-i",
                str(target),
                "-vf",
                "fps=12,scale=320:-1:flags=lanczos",
                "-loop",
                "0",
                str(animated),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

    return {
        "poster_path": str(poster) if poster.exists() else "",
        "animated_path": str(animated) if animated.exists() else "",
    }


def _probe_video_dimensions(path: Path) -> tuple[int, int]:
    """Best-effort video width/height via ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "json",
            str(path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if res.returncode != 0 or not res.stdout:
            return 0, 0
        payload = json.loads(res.stdout) or {}
        streams = payload.get("streams") or []
        if not streams:
            return 0, 0
        st = streams[0] or {}
        return int(st.get("width") or 0), int(st.get("height") or 0)
    except Exception:
        return 0, 0


def _format_aspect_ratio(width: int, height: int) -> str | None:
    if width <= 0 or height <= 0:
        return None
    try:
        divisor = math.gcd(int(width), int(height))
        if divisor <= 0:
            return None
        return f"{int(width // divisor)}:{int(height // divisor)}"
    except Exception:
        return None


def _ensure_video_playback_variants(target: Path) -> dict[str, str]:
    """
    Build cached playback variants for real decode/load reduction by scale.
    Returns absolute file paths by scale key: full/half/quarter/eighth/sixteenth.
    """
    variants: dict[str, str] = {"full": str(target)}
    src_w, src_h = _probe_video_dimensions(target)
    if src_w <= 0 or src_h <= 0:
        return variants

    cache_root = _media_cache_root()
    cache_root.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(f"{target}:{target.stat().st_mtime_ns}:playback".encode("utf-8")).hexdigest()[:16]
    out_dir = cache_root / key
    out_dir.mkdir(parents=True, exist_ok=True)

    scale_profiles = [
        ("half", 2, 2),
        ("quarter", 4, 320),
        ("eighth", 8, 320),
        ("sixteenth", 16, 320),
    ]
    for name, divisor, min_width in scale_profiles:
        scaled_w = max(2, (src_w // divisor // 2) * 2)
        if scaled_w < min_width:
            continue
        out_file = out_dir / f"playback_{name}.mp4"
        if not out_file.exists():
            scale_filter = f"scale='trunc(iw/{divisor}/2)*2:trunc(ih/{divisor}/2)*2:flags=neighbor'"
            cmd_h264 = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(target),
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-vf",
                scale_filter,
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "34",
                "-c:a",
                "aac",
                "-b:a",
                "96k",
                "-movflags",
                "+faststart",
                str(out_file),
            ]
            res = subprocess.run(cmd_h264, check=False, capture_output=True, text=True, timeout=90)
            if res.returncode != 0 and not out_file.exists():
                cmd_mpeg4 = [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(target),
                    "-map",
                    "0:v:0",
                    "-map",
                    "0:a?",
                    "-vf",
                    scale_filter,
                    "-c:v",
                    "mpeg4",
                    "-q:v",
                    "12",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "96k",
                    "-movflags",
                    "+faststart",
                    str(out_file),
                ]
                subprocess.run(cmd_mpeg4, check=False, capture_output=True, text=True, timeout=90)
        if out_file.exists():
            variants[name] = str(out_file)
    return variants


def _compute_waveform_bins_for_wav(path: Path, bins: int) -> tuple[list[float], int]:
    """Compute normalized waveform bins for WAV files."""
    try:
        with wave.open(str(path), "rb") as wav:
            n_channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            n_frames = wav.getnframes()
            if n_frames <= 0:
                return [], sample_rate
            raw = wav.readframes(n_frames)
            if sample_width not in (1, 2, 4):
                return [], sample_rate
            if sample_width == 1:
                max_amp = 127.0
                samples = [abs((b - 128) / max_amp) for b in raw]
            elif sample_width == 2:
                import struct
                count = len(raw) // 2
                vals = struct.unpack("<" + "h" * count, raw[: count * 2])
                max_amp = 32767.0
                samples = [abs(v / max_amp) for v in vals]
            else:
                import struct
                count = len(raw) // 4
                vals = struct.unpack("<" + "i" * count, raw[: count * 4])
                max_amp = float(2**31 - 1)
                samples = [abs(v / max_amp) for v in vals]

            # Downmix channels by taking every n_channels-th sample average.
            if n_channels > 1 and samples:
                mono = []
                for i in range(0, len(samples), n_channels):
                    window = samples[i : i + n_channels]
                    if window:
                        mono.append(sum(window) / len(window))
                samples = mono

            if not samples:
                return [], sample_rate

            chunk_size = max(1, math.ceil(len(samples) / bins))
            out = []
            for i in range(0, len(samples), chunk_size):
                chunk = samples[i : i + chunk_size]
                if not chunk:
                    continue
                out.append(min(1.0, max(0.0, max(chunk))))
            return out[:bins], sample_rate
    except Exception:
        return [], 0


def _resolve_media_path(raw_path: str) -> Path:
    p = Path(raw_path)
    if p.is_absolute():
        return p
    project_root = Path(__file__).parent.parent.parent.parent
    return (project_root / p).resolve()


def _default_lane_for_modality(modality: str) -> str:
    m = str(modality or "").strip().lower()
    if m == "audio":
        return "audio_sync"
    if m == "video":
        return "video_main"
    return "video_main"


def _enrich_segments_with_lanes(segments: list[dict], modality: str) -> list[dict]:
    lane_ends: dict[str, float] = {}
    out: list[dict] = []
    for idx, seg in enumerate(segments):
        start_sec = float(seg.get("start_sec", 0.0) or 0.0)
        end_sec = float(seg.get("end_sec", start_sec) or start_sec)
        lane = str(seg.get("timeline_lane", "") or "").strip().lower()
        if lane not in {"video_main", "audio_sync", "take_alt_y", "take_alt_z"}:
            lane = _default_lane_for_modality(modality)
        lane_index = int(seg.get("lane_index", 0) or 0)
        if lane in {"video_main", "audio_sync"} and start_sec < float(lane_ends.get(lane, -1.0)):
            lane = "take_alt_y"
            lane_index = max(1, lane_index)
        lane_ends[lane] = max(float(lane_ends.get(lane, -1.0)), end_sec)
        enriched = dict(seg)
        enriched["timeline_lane"] = lane
        enriched["lane_index"] = lane_index
        enriched["take_id"] = str(seg.get("take_id", "") or f"{lane}:{idx}")
        enriched["sync_group_id"] = str(seg.get("sync_group_id", "") or "default_sync")
        out.append(enriched)
    return out


def _load_media_segments_from_qdrant(
    request: Request,
    target: Path,
    *,
    limit: int,
) -> list[dict]:
    segments: list[dict] = []
    qdrant_manager = getattr(request.app.state, "qdrant_manager", None)
    qdrant_client = getattr(qdrant_manager, "client", None) if qdrant_manager else None
    if not qdrant_client:
        return segments
    from src.scanners.qdrant_updater import get_qdrant_updater

    updater = get_qdrant_updater(qdrant_client=qdrant_client, enable_triple_write=True)
    point_id = updater._get_point_id(str(target))
    results = qdrant_client.retrieve(
        collection_name=updater.collection_name,
        ids=[point_id],
        with_payload=True,
        with_vectors=False,
    )
    if not results:
        return segments
    payload = results[0].payload or {}
    chunks = payload.get("media_chunks_v1") or payload.get("media_chunks") or []
    for chunk in chunks[:limit]:
        segments.append(
            {
                "start_sec": float(chunk.get("start_sec", 0.0) or 0.0),
                "end_sec": float(chunk.get("end_sec", 0.0) or 0.0),
                "duration_sec": float(chunk.get("duration_sec", 0.0) or 0.0),
                "text": str(chunk.get("text", "") or ""),
                "confidence": float(chunk.get("confidence", 0.0) or 0.0),
                "chunk_id": str(chunk.get("chunk_id", "") or ""),
                "timeline_lane": str(chunk.get("timeline_lane", "") or ""),
                "lane_index": int(chunk.get("lane_index", 0) or 0),
                "take_id": str(chunk.get("take_id", "") or ""),
                "sync_group_id": str(chunk.get("sync_group_id", "") or ""),
            }
        )
    return segments


def _build_waveform_proxy_from_segments(duration_sec: float, segments: list[dict], bins: int) -> list[float]:
    if duration_sec <= 0 or bins <= 0:
        return []
    track = [0.0 for _ in range(bins)]
    for seg in segments:
        start = max(0.0, float(seg.get("start_sec", 0.0) or 0.0))
        end = max(start, float(seg.get("end_sec", start) or start))
        conf = float(seg.get("confidence", 0.4) or 0.4)
        a = int((start / duration_sec) * bins)
        b = int((end / duration_sec) * bins)
        if b < a:
            b = a
        for i in range(max(0, a), min(bins, b + 1)):
            track[i] = min(1.0, max(track[i], max(0.2, min(1.0, conf))))
    if not any(track):
        return track
    m = max(track)
    if m > 0:
        track = [min(1.0, v / m) for v in track]
    return track


def _extract_scene_segments_with_ffmpeg(target: Path, duration_sec: float, limit: int = 256) -> list[dict]:
    """
    Best-effort scene-cut extraction from real video via ffmpeg showinfo.
    Returns coarse timeline segments suitable for CAM/rhythm proxy features.
    """
    if duration_sec <= 0.0:
        return []
    try:
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(target),
            "-vf",
            "select='gt(scene,0.30)',showinfo",
            "-an",
            "-f",
            "null",
            "-",
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        stderr = str(proc.stderr or "")
    except Exception:
        return []

    cut_points: list[float] = [0.0]
    for m in re.finditer(r"pts_time:([0-9]+(?:\.[0-9]+)?)", stderr):
        t = float(m.group(1))
        if 0.0 < t < duration_sec:
            cut_points.append(t)
    cut_points.append(duration_sec)
    cut_points = sorted(set(round(t, 3) for t in cut_points))
    if len(cut_points) < 2:
        return []

    segments: list[dict] = []
    for i in range(len(cut_points) - 1):
        if len(segments) >= max(1, int(limit)):
            break
        s = float(cut_points[i])
        e = float(cut_points[i + 1])
        if e <= s:
            continue
        # Shorter segments are considered more unique/memorable candidates.
        duration = max(0.001, e - s)
        conf = max(0.2, min(1.0, 1.0 / max(0.45, duration)))
        segments.append(
            {
                "start_sec": s,
                "end_sec": e,
                "duration_sec": duration,
                "text": f"scene_{i+1}",
                "confidence": conf,
                "chunk_id": f"{target}#scene_cut:{i}",
                "timeline_lane": "video_main",
                "lane_index": 0,
                "take_id": f"scene_cut:{i}",
                "sync_group_id": "scene_detect",
            }
        )
    return segments


def _compute_rhythm_assist(duration_sec: float, segments: list[dict], energy_track: list[float]) -> dict:
    if duration_sec <= 0:
        return {
            "cut_density_per_sec": 0.0,
            "cut_density_per_min": 0.0,
            "motion_volatility": 0.0,
            "phase_markers": [],
            "recommended_shot_sec": 2.5,
            "music_binding": {
                "target_bpm": 90,
                "rhythm_profile": "steady",
            },
        }

    ordered = sorted(segments, key=lambda s: float(s.get("start_sec", 0.0) or 0.0))
    cut_count = 0
    prev_end: Optional[float] = None
    for seg in ordered:
        start = float(seg.get("start_sec", 0.0) or 0.0)
        if prev_end is not None and abs(start - prev_end) <= 0.25:
            cut_count += 1
        prev_end = float(seg.get("end_sec", start) or start)
    cut_density_per_sec = float(cut_count) / max(duration_sec, 1e-6)
    cut_density_per_min = cut_density_per_sec * 60.0

    durations = [
        max(0.0, float(s.get("end_sec", 0.0) or 0.0) - float(s.get("start_sec", 0.0) or 0.0))
        for s in ordered
    ]
    durations = [d for d in durations if d > 1e-4]
    if len(durations) >= 2:
        mean = sum(durations) / len(durations)
        var = sum((d - mean) ** 2 for d in durations) / len(durations)
        duration_cv = (var ** 0.5) / max(mean, 1e-6)
    else:
        duration_cv = 0.0

    if len(energy_track) >= 2:
        diffs = [abs(energy_track[i] - energy_track[i - 1]) for i in range(1, len(energy_track))]
        energy_flux = sum(diffs) / len(diffs)
    else:
        energy_flux = 0.0

    motion_volatility = max(0.0, min(1.0, 0.65 * min(1.0, duration_cv) + 0.35 * min(1.0, energy_flux * 3.0)))

    phase_markers: list[dict] = []
    if energy_track:
        avg_energy = sum(energy_track) / max(1, len(energy_track))
        threshold = min(0.95, max(0.25, avg_energy + 0.12))
        for idx, amp in enumerate(energy_track):
            if amp >= threshold:
                t = (idx / max(1, len(energy_track) - 1)) * duration_sec
                phase_markers.append({"time_sec": round(t, 3), "kind": "energy_peak", "strength": round(float(amp), 3)})
    for seg in ordered[:32]:
        phase_markers.append(
            {
                "time_sec": round(float(seg.get("start_sec", 0.0) or 0.0), 3),
                "kind": "segment_start",
                "strength": round(float(seg.get("confidence", 0.4) or 0.4), 3),
            }
        )
    phase_markers = sorted(phase_markers, key=lambda x: (x["time_sec"], x["kind"]))[:64]

    if cut_density_per_min > 28:
        rhythm_profile = "aggressive"
        recommended_shot_sec = 1.4
    elif cut_density_per_min > 16:
        rhythm_profile = "dynamic"
        recommended_shot_sec = 2.1
    else:
        rhythm_profile = "steady"
        recommended_shot_sec = 3.2

    target_bpm = int(max(72, min(168, round(78 + cut_density_per_min * 1.6 + motion_volatility * 22))))
    return {
        "cut_density_per_sec": round(cut_density_per_sec, 4),
        "cut_density_per_min": round(cut_density_per_min, 2),
        "motion_volatility": round(motion_volatility, 3),
        "phase_markers": phase_markers,
        "recommended_shot_sec": round(recommended_shot_sec, 2),
        "music_binding": {
            "target_bpm": target_bpm,
            "rhythm_profile": rhythm_profile,
        },
    }


def _compute_cam_overlay(duration_sec: float, segments: list[dict], bins: int) -> dict:
    if duration_sec <= 0 or bins <= 0:
        return {
            "uniqueness_track": [],
            "memorability_track": [],
            "top_moments": [],
        }
    uniqueness = [0.0 for _ in range(bins)]
    memorability = [0.0 for _ in range(bins)]
    for seg in segments:
        start = max(0.0, float(seg.get("start_sec", 0.0) or 0.0))
        end = max(start, float(seg.get("end_sec", start) or start))
        duration = max(0.0, end - start)
        conf = max(0.0, min(1.0, float(seg.get("confidence", 0.0) or 0.0)))
        text = str(seg.get("text", "") or "")
        lexical = min(1.0, len(set(re.findall(r"[A-Za-zА-Яа-яЁё0-9_]+", text.lower()))) / 12.0)
        motion_proxy = min(1.0, 1.0 / max(0.3, duration))
        uniq = max(0.0, min(1.0, 0.55 * lexical + 0.45 * motion_proxy))
        memo = max(0.0, min(1.0, 0.6 * conf + 0.4 * uniq))
        a = int((start / duration_sec) * bins)
        b = int((end / duration_sec) * bins)
        if b < a:
            b = a
        for i in range(max(0, a), min(bins, b + 1)):
            uniqueness[i] = max(uniqueness[i], uniq)
            memorability[i] = max(memorability[i], memo)

    top_moments: list[dict] = []
    for idx, score in sorted(enumerate(memorability), key=lambda x: x[1], reverse=True)[:8]:
        if score <= 0:
            continue
        time_sec = (idx / max(1, bins - 1)) * duration_sec
        top_moments.append(
            {
                "time_sec": round(time_sec, 3),
                "uniqueness": round(float(uniqueness[idx]), 3),
                "memorability": round(float(score), 3),
                "kind": "memorability_peak",
            }
        )
    return {
        "uniqueness_track": [round(float(v), 4) for v in uniqueness],
        "memorability_track": [round(float(v), 4) for v in memorability],
        "top_moments": sorted(top_moments, key=lambda x: x["time_sec"]),
    }


def _normalize_stt_segments(segments: list[dict], *, limit: int = 256) -> list[dict]:
    out: list[dict] = []
    for idx, seg in enumerate((segments or [])[:limit]):
        start = max(0.0, float(seg.get("start", seg.get("start_sec", 0.0)) or 0.0))
        end = max(start, float(seg.get("end", seg.get("end_sec", start)) or start))
        text = str(seg.get("text", "") or "").strip()
        conf = float(seg.get("confidence", 0.0) or 0.0)
        if not conf:
            conf = float(seg.get("avg_logprob", 0.0) or 0.0) + 1.0
        conf = max(0.0, min(1.0, conf))
        out.append(
            {
                "id": f"seg:{idx}",
                "start_sec": round(start, 3),
                "end_sec": round(end, 3),
                "duration_sec": round(max(0.0, end - start), 3),
                "text": text,
                "confidence": round(conf, 4),
                "speaker": str(seg.get("speaker", "") or ""),
                "source": "whisper",
            }
        )
    return out


def _transcribe_media_whisper(
    target: Path,
    *,
    duration_sec: float,
    max_transcribe_sec: Optional[int] = None,
    clip_for_testing_only: bool = False,
) -> dict:
    """
    Best-effort Whisper transcription with optional duration clipping.
    Returns {text, segments, language, source_engine, clipped}.
    """
    input_path = str(target)
    clipped = False
    tmp_file: Optional[str] = None
    try:
        if clip_for_testing_only and max_transcribe_sec and duration_sec > float(max_transcribe_sec):
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_file = tmp.name
            clip_cmd = [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(target),
                "-t",
                str(int(max_transcribe_sec)),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                tmp_file,
            ]
            subprocess.run(clip_cmd, check=True, capture_output=True, text=True, timeout=45)
            input_path = tmp_file
            clipped = True

        from src.voice.stt_engine import WhisperSTT

        stt = WhisperSTT(model_name="base")
        tr = stt.transcribe(input_path)
        return {
            "text": str(tr.get("text", "") or "").strip(),
            "segments": tr.get("segments", []) or [],
            "language": str(tr.get("language", "") or ""),
            "source_engine": "mlx_whisper",
            "clipped": clipped,
        }
    finally:
        if tmp_file:
            try:
                Path(tmp_file).unlink(missing_ok=True)
            except Exception:
                pass


def _tokenize_for_semantics(text: str) -> set[str]:
    return {
        t
        for t in re.findall(r"[A-Za-zА-Яа-яЁё0-9_]+", str(text or "").lower())
        if len(t) >= 3
    }


def _hero_tokens(text: str) -> set[str]:
    # Simple proper-name heuristic (Latin/Cyrillic title-case words)
    return {
        t.lower()
        for t in re.findall(r"\b([A-ZА-ЯЁ][a-zа-яё]{2,})\b", str(text or ""))
    }


def _infer_relation_type(query_text: str, candidate_text: str) -> str:
    q_hero = _hero_tokens(query_text)
    c_hero = _hero_tokens(candidate_text)
    if q_hero & c_hero:
        return "hero"

    q_tokens = _tokenize_for_semantics(query_text)
    c_tokens = _tokenize_for_semantics(candidate_text)
    common = q_tokens & c_tokens
    if not common:
        return "theme"

    location_markers = {
        "room", "street", "city", "office", "house", "forest", "beach",
        "location", "lobby", "kitchen", "car", "park",
        "локация", "улица", "город", "дом", "комната", "лес", "парк", "машина",
    }
    action_markers = {
        "run", "walk", "jump", "fight", "move", "open", "close", "enter", "exit",
        "say", "talk", "look", "turn",
        "идет", "бежит", "прыжок", "движение", "входит", "выходит", "смотрит", "говорит",
    }
    if common & location_markers:
        return "location"
    if common & action_markers:
        return "action"
    return "theme"


def _quick_media_scan(scope_path: Path, quick_scan_limit: int) -> dict:
    media_exts = {
        ".wav",
        ".mp3",
        ".m4a",
        ".aac",
        ".flac",
        ".ogg",
        ".mp4",
        ".mov",
        ".mkv",
        ".avi",
        ".webm",
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
        ".gif",
        ".tiff",
        ".pdf",
    }
    counts = {
        "total_files_scanned": 0,
        "media_files": 0,
        "audio_files": 0,
        "video_files": 0,
        "image_files": 0,
        "document_files": 0,
    }
    scanned = 0
    for root, _, files in os.walk(scope_path):
        for name in files:
            scanned += 1
            if scanned > quick_scan_limit:
                return {**counts, "truncated": True}
            counts["total_files_scanned"] += 1
            ext = Path(name).suffix.lower()
            if ext not in media_exts:
                continue
            counts["media_files"] += 1
            if ext in {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}:
                counts["audio_files"] += 1
            elif ext in {".mp4", ".mov", ".mkv", ".avi", ".webm"}:
                counts["video_files"] += 1
            elif ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"}:
                counts["image_files"] += 1
            elif ext == ".pdf":
                counts["document_files"] += 1
    return {**counts, "truncated": False}


def _collect_fallback_signals(scope_path: Path, quick_scan_limit: int) -> dict:
    script_exts = {".fdx", ".fountain", ".txt", ".md", ".docx", ".pdf"}
    transcript_exts = {".srt", ".vtt", ".json", ".xml", ".txt", ".md"}
    sheet_exts = {".xlsx", ".xls", ".csv", ".tsv", ".json", ".xml", ".md", ".txt"}

    signals = {
        "has_script_or_treatment": False,
        "has_montage_sheet": False,
        "has_transcript_or_timecodes": False,
    }

    scanned = 0
    for root, _, files in os.walk(scope_path):
        for name in files:
            scanned += 1
            if scanned > quick_scan_limit:
                return signals
            lower_name = name.lower()
            ext = Path(name).suffix.lower()

            if (not signals["has_script_or_treatment"]) and ext in script_exts:
                if any(token in lower_name for token in ("script", "scenario", "treatment", "скрипт", "сценар", "тритмент")):
                    signals["has_script_or_treatment"] = True

            if (not signals["has_montage_sheet"]) and ext in sheet_exts:
                if any(token in lower_name for token in ("montage", "edit", "sheet", "лист", "монтаж", "edl", "fcpxml", "premiere", "xml")):
                    signals["has_montage_sheet"] = True

            if (not signals["has_transcript_or_timecodes"]) and ext in transcript_exts:
                if any(token in lower_name for token in ("transcript", "subtitle", "captions", "timecode", "whisper", "srt", "vtt", "xml", "json", "таймкод", "транскриб")):
                    signals["has_transcript_or_timecodes"] = True

            if all(signals.values()):
                return signals

    return signals


def _build_fallback_questions(signals: dict, stats: dict) -> list[dict]:
    media_files = int(stats.get("media_files", 0) or 0)
    video_files = int(stats.get("video_files", 0) or 0)
    audio_files = int(stats.get("audio_files", 0) or 0)

    questions: list[dict] = []
    if not signals.get("has_script_or_treatment", False):
        questions.append(
            {
                "id": "missing_script",
                "priority": 1,
                "question": "No script/treatment found. Should Jarvis draft scene outline from footage metadata and filenames?",
                "prefill": "Jarvis, build initial scene outline from available media metadata and naming patterns.",
            }
        )
    if not signals.get("has_montage_sheet", False):
        questions.append(
            {
                "id": "missing_montage_sheet",
                "priority": 2,
                "question": "No montage sheet detected. Do we generate a draft montage sheet profile (scene/take/timecode/notes)?",
                "prefill": "Jarvis, generate draft montage sheet schema and start filling it from detected media segments.",
            }
        )
    if not signals.get("has_transcript_or_timecodes", False) and (audio_files > 0 or video_files > 0):
        questions.append(
            {
                "id": "missing_transcript_timecodes",
                "priority": 1,
                "question": "No transcript/timecodes detected. Start Whisper pass for audio/video and build timecoded JSON/XML?",
                "prefill": "Jarvis, run transcript+timecode pipeline for audio/video and save normalized JSON/XML output.",
            }
        )
    if media_files > 0 and video_files == 0 and audio_files > 0:
        questions.append(
            {
                "id": "audio_only_scope",
                "priority": 3,
                "question": "Scope appears audio-only. Build rhythm-first scene grouping for future video match?",
                "prefill": "Jarvis, prepare rhythm/genre grouping from audio as pre-edit structure for scene assembly.",
            }
        )
    return questions


@router.post("/media/startup")
async def media_startup(body: MediaStartupRequest):
    """
    MARKER_158.RUNTIME.MEDIA_MCP_SPLIT
    P5.2 startup orchestration contract for Media Edit Mode.
    """
    raw_scope = str(body.scope_path or "").strip()
    target = _resolve_media_path(raw_scope) if raw_scope else Path.cwd()
    if not target.exists() or not target.is_dir():
        target = Path.cwd()
        degraded = True
        degraded_reason = "scope_not_found_fallback_to_cwd"
    else:
        degraded = False
        degraded_reason = ""

    stats = _quick_media_scan(target, body.quick_scan_limit)
    signals = _collect_fallback_signals(target, body.quick_scan_limit)
    fallback_questions = _build_fallback_questions(signals, stats)
    media_count = int(stats.get("media_files", 0) or 0)
    eta_sec = round(max(1.0, min(30.0, 1.2 + media_count * 0.08)), 1)

    phases = [
        {"id": "discover", "label": "Scope discovery", "status": "done", "progress": 0.34},
        {"id": "index", "label": "Metadata index warmup", "status": "done", "progress": 0.68},
        {"id": "align", "label": "Timeline alignment prep", "status": "ready", "progress": 1.0},
    ]

    return {
        "success": True,
        "scope_path": str(target),
        "degraded_mode": degraded,
        "degraded_reason": degraded_reason,
        "estimated_ready_sec": eta_sec,
        "stats": stats,
        "missing_inputs": {
            "script_or_treatment": not bool(signals.get("has_script_or_treatment")),
            "montage_sheet": not bool(signals.get("has_montage_sheet")),
            "transcript_or_timecodes": not bool(signals.get("has_transcript_or_timecodes")),
        },
        "fallback_questions": fallback_questions,
        "phases": phases,
        "next_actions": [
            "open_media_preview",
            "fetch_media_chunks_v1",
            "start_scene_assembly",
        ],
    }


@router.post("/media/preview")
async def media_preview(body: MediaPreviewRequest, request: Request):
    """
    P5 media preview API: waveform bins + timeline segments + duration metadata.
    """
    target = _resolve_media_path(body.path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"Media file not found: {body.path}")

    mime_type, _ = mimetypes.guess_type(str(target))
    mime_type = mime_type or "application/octet-stream"
    is_audio = mime_type.startswith("audio/")
    is_video = mime_type.startswith("video/")
    if not (is_audio or is_video):
        raise HTTPException(status_code=400, detail=f"Unsupported media type: {mime_type}")
    modality = "video" if is_video else "audio"
    width_px, height_px = _probe_video_dimensions(target) if is_video else (0, 0)
    aspect_ratio = _format_aspect_ratio(width_px, height_px) if is_video else None

    duration_sec = _probe_media_duration(target)
    waveform_bins: list[float] = []
    sample_rate = 0
    degraded_reason = ""
    if target.suffix.lower() == ".wav":
        waveform_bins, sample_rate = _compute_waveform_bins_for_wav(target, body.waveform_bins)
    else:
        waveform_bins, sample_rate = _compute_waveform_bins_via_ffmpeg(target, body.waveform_bins)
    if not waveform_bins:
        waveform_bins = _build_waveform_proxy_from_segments(float(duration_sec or 0.0), [], int(body.waveform_bins))
        degraded_reason = "waveform_unavailable_fallback_proxy"

    # Try to retrieve stored media chunks for timeline.
    media_segments: list[dict] = []
    try:
        media_segments = _load_media_segments_from_qdrant(
            request,
            target,
            limit=body.preview_segments_limit,
        )
    except Exception:
        pass

    media_segments = _enrich_segments_with_lanes(media_segments, modality)
    if not waveform_bins and media_segments:
        waveform_bins = _build_waveform_proxy_from_segments(float(duration_sec or 0.0), media_segments, int(body.waveform_bins))

    preview_assets = {"poster_url": "", "animated_preview_url_300ms": ""}
    playback_sources_scale: dict[str, str] = {"full": _encode_raw_url(target)}
    if is_video:
        assets = _ensure_video_preview_assets(target, float(duration_sec or 0.0))
        if assets.get("poster_path"):
            preview_assets["poster_url"] = _encode_raw_url(Path(assets["poster_path"]))
        if assets.get("animated_path"):
            preview_assets["animated_preview_url_300ms"] = _encode_raw_url(Path(assets["animated_path"]))
        variants = _ensure_video_playback_variants(target)
        playback_sources_scale = {
            key: _encode_raw_url(Path(path))
            for key, path in variants.items()
            if path and Path(path).exists()
        }

    return {
        "success": True,
        "path": str(target),
        "mime_type": mime_type,
        "modality": modality,
        "size_bytes": os.path.getsize(target),
        "duration_sec": float(duration_sec or 0.0),
        "waveform_bins": waveform_bins,
        "waveform_sample_rate": sample_rate,
        "timeline_segments": media_segments,
        "preview": {
            "aspect_ratio": aspect_ratio,
            "recommended_zoom": 1.0,
            "width_px": int(width_px or 0),
            "height_px": int(height_px or 0),
        },
        "playback": {
            "source_url": _encode_raw_url(target),
            "strategy": "direct",
            "requires_proxy": False,
            "sources_scale": playback_sources_scale,
        },
        "preview_assets": preview_assets,
        "playback_metadata": {
            "modality": modality,
            "duration_sec": float(duration_sec or 0.0),
            "has_waveform": bool(waveform_bins),
            "has_timeline_segments": bool(media_segments),
            "timeline_segments_count": len(media_segments),
        },
        "degraded_mode": bool(degraded_reason),
        "degraded_reason": degraded_reason,
    }


@router.post("/media/window-metadata")
async def media_window_metadata(body: MediaWindowMetadataRequest):
    """Lightweight real media metadata for detached window initial sizing."""
    target = _resolve_media_path(body.path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"Media file not found: {body.path}")

    mime_type, _ = mimetypes.guess_type(str(target))
    mime_type = mime_type or "application/octet-stream"
    is_audio = mime_type.startswith("audio/")
    is_video = mime_type.startswith("video/")
    if not (is_audio or is_video):
        raise HTTPException(status_code=400, detail=f"Unsupported media type: {mime_type}")

    width_px, height_px = _probe_video_dimensions(target) if is_video else (0, 0)
    return {
        "success": True,
        "path": str(target),
        "mime_type": mime_type,
        "modality": "video" if is_video else "audio",
        "width_px": int(width_px or 0),
        "height_px": int(height_px or 0),
        "aspect_ratio": _format_aspect_ratio(width_px, height_px) if is_video else None,
    }


@router.post("/media/semantic-links")
async def media_semantic_links(body: MediaSemanticLinksRequest):
    """
    P5.5 semantic links for media segments (hero/action/location/theme).
    """
    target = _resolve_media_path(body.path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"Media file not found: {body.path}")

    query = str(body.query_text or "").strip()
    if len(query) < 2:
        return {
            "success": True,
            "path": str(target),
            "query_text": query,
            "links": [],
            "playback_metadata": {
                "query_text": query,
                "links_count": 0,
            },
            "degraded_mode": True,
            "degraded_reason": "empty_query_text",
        }

    try:
        from src.orchestration.triple_write_manager import get_triple_write_manager

        tw = get_triple_write_manager()
        candidates = tw.search_media_chunks(
            query=query,
            limit=max(4, int(body.limit) * 4),
            modality=None,
            parent_file_path=None,
        )
    except Exception:
        candidates = []

    links: list[dict] = []
    path_norm = str(target)
    for item in candidates:
        parent_path = str(item.get("parent_file_path", "") or "")
        if not parent_path:
            continue
        if not body.include_same_file and parent_path == path_norm:
            continue
        # Skip near-identical source segment
        start_sec = float(item.get("start_sec", 0.0) or 0.0)
        end_sec = float(item.get("end_sec", 0.0) or 0.0)
        if parent_path == path_norm and abs(start_sec - float(body.start_sec or 0.0)) < 0.15 and abs(end_sec - float(body.end_sec or 0.0)) < 0.15:
            continue
        cand_text = str(item.get("text", "") or "")
        relation_type = _infer_relation_type(query, cand_text)
        links.append(
            {
                "relation_type": relation_type,
                "score": float(item.get("score", 0.0) or 0.0),
                "parent_file_path": parent_path,
                "start_sec": start_sec,
                "end_sec": end_sec,
                "text": cand_text[:320],
                "timeline_lane": str(item.get("timeline_lane", "") or ""),
                "take_id": str(item.get("take_id", "") or ""),
                "sync_group_id": str(item.get("sync_group_id", "") or ""),
            }
        )

    links = sorted(links, key=lambda x: (x.get("relation_type", "theme"), -float(x.get("score", 0.0))))[: int(body.limit)]
    return {
        "success": True,
        "path": path_norm,
        "query_text": query,
        "links": links,
        "playback_metadata": {
            "query_text": query,
            "links_count": len(links),
        },
        "degraded_mode": len(candidates) == 0,
        "degraded_reason": "no_candidates" if len(candidates) == 0 else "",
    }


@router.post("/media/rhythm-assist")
async def media_rhythm_assist(body: MediaRhythmAssistRequest, request: Request):
    """
    P5.6 rhythm/music assist:
    - cut density
    - motion volatility estimate
    - phase markers
    - pulse bridge status
    """
    target = _resolve_media_path(body.path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"Media file not found: {body.path}")

    mime_type, _ = mimetypes.guess_type(str(target))
    mime_type = mime_type or "application/octet-stream"
    is_audio = mime_type.startswith("audio/")
    is_video = mime_type.startswith("video/")
    if not (is_audio or is_video):
        raise HTTPException(status_code=400, detail=f"Unsupported media type: {mime_type}")
    modality = "video" if is_video else "audio"

    duration_sec = float(_probe_media_duration(target) or 0.0)
    segments = []
    try:
        segments = _load_media_segments_from_qdrant(
            request,
            target,
            limit=body.segments_limit,
        )
    except Exception:
        segments = []
    segments = _enrich_segments_with_lanes(segments, modality)

    waveform_bins: list[float] = []
    if target.suffix.lower() == ".wav":
        waveform_bins, _ = _compute_waveform_bins_for_wav(target, body.bins)
    if not waveform_bins:
        waveform_bins = _build_waveform_proxy_from_segments(duration_sec, segments, body.bins)

    rhythm = _compute_rhythm_assist(duration_sec, segments, waveform_bins)

    pulse_root = Path(__file__).parent.parent.parent.parent / "pulse"
    pulse_available = pulse_root.exists() and pulse_root.is_dir()
    pulse_bridge = {
        "available": pulse_available,
        "mode": "heuristic_proxy_v1",
        "degraded_reason": "" if pulse_available else "pulse_repo_unavailable",
    }
    recommendations = [
        f"Target BPM ≈ {rhythm['music_binding']['target_bpm']} ({rhythm['music_binding']['rhythm_profile']})",
        f"Suggested base shot length: {rhythm['recommended_shot_sec']:.2f}s",
        "Prioritize high-energy phase markers for cut points.",
    ]

    return {
        "success": True,
        "path": str(target),
        "modality": modality,
        "duration_sec": duration_sec,
        "rhythm_features": {
            "cut_density": {
                "per_sec": rhythm["cut_density_per_sec"],
                "per_min": rhythm["cut_density_per_min"],
            },
            "motion_volatility": rhythm["motion_volatility"],
            "phase_markers": rhythm["phase_markers"],
        },
        "music_binding": rhythm["music_binding"],
        "recommended_shot_sec": rhythm["recommended_shot_sec"],
        "energy_track": waveform_bins,
        "pulse_bridge": pulse_bridge,
        "recommendations": recommendations,
        "playback_metadata": {
            "modality": modality,
            "duration_sec": duration_sec,
            "target_bpm": rhythm["music_binding"]["target_bpm"],
            "phase_markers_count": len(rhythm["phase_markers"]),
        },
        "degraded_mode": len(segments) == 0,
        "degraded_reason": "no_media_segments_v1" if len(segments) == 0 else "",
    }


@router.post("/media/cam-overlay")
async def media_cam_overlay(body: MediaCamOverlayRequest, request: Request):
    """
    T5 CAM overlay contract:
    - frame uniqueness track (heuristic proxy)
    - memorability track (heuristic proxy)
    - top moments list
    """
    target = _resolve_media_path(body.path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"Media file not found: {body.path}")

    mime_type, _ = mimetypes.guess_type(str(target))
    mime_type = mime_type or "application/octet-stream"
    is_audio = mime_type.startswith("audio/")
    is_video = mime_type.startswith("video/")
    if not (is_audio or is_video):
        raise HTTPException(status_code=400, detail=f"Unsupported media type: {mime_type}")
    modality = "video" if is_video else "audio"

    duration_sec = float(_probe_media_duration(target) or 0.0)
    segments = []
    segment_source = "qdrant_media_chunks_v1"
    try:
        segments = _load_media_segments_from_qdrant(
            request,
            target,
            limit=body.segments_limit,
        )
    except Exception:
        segments = []
    if not segments and is_video:
        segments = _extract_scene_segments_with_ffmpeg(
            target,
            duration_sec=duration_sec,
            limit=body.segments_limit,
        )
        if segments:
            segment_source = "ffmpeg_scene_detect"
        else:
            segment_source = "none"
    segments = _enrich_segments_with_lanes(segments, modality)

    cam = _compute_cam_overlay(duration_sec, segments, body.bins)
    try:
        from src.orchestration.cam_engine import VETKACAMEngine  # noqa: F401
        cam_available = True
    except Exception:
        cam_available = False

    return {
        "success": True,
        "path": str(target),
        "modality": modality,
        "duration_sec": duration_sec,
        "cam_features": cam,
        "cam_bridge": {
            "available": cam_available,
            "mode": "heuristic_proxy_v1",
            "degraded_reason": "" if cam_available else "cam_engine_unavailable",
        },
        "playback_metadata": {
            "modality": modality,
            "duration_sec": duration_sec,
            "cam_bins": int(body.bins),
            "top_moments_count": len(cam.get("top_moments", [])),
            "segment_source": segment_source,
        },
        "degraded_mode": len(segments) == 0,
        "degraded_reason": "no_media_segments_v1" if len(segments) == 0 else "",
    }


@router.post("/media/transcript-normalized")
async def media_transcript_normalized(body: MediaTranscriptNormalizeRequest, request: Request):
    """
    P6.1 Whisper transcript -> normalized JSON contract.
    """
    target = _resolve_media_path(body.path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"Media file not found: {body.path}")

    mime_type, _ = mimetypes.guess_type(str(target))
    mime_type = mime_type or "application/octet-stream"
    is_audio = mime_type.startswith("audio/")
    is_video = mime_type.startswith("video/")
    if not (is_audio or is_video):
        raise HTTPException(status_code=400, detail=f"Unsupported media type: {mime_type}")
    modality = "video" if is_video else "audio"

    duration_sec = float(_probe_media_duration(target) or 0.0)
    transcript_text = ""
    transcript_segments: list[dict] = []
    language = ""
    source_engine = "none"
    degraded_reason = ""
    clipped = False

    try:
        tr = _transcribe_media_whisper(
            target,
            duration_sec=duration_sec,
            max_transcribe_sec=int(body.max_transcribe_sec) if body.max_transcribe_sec else None,
            clip_for_testing_only=bool(body.clip_for_testing_only),
        )
        transcript_text = str(tr.get("text", "") or "")
        transcript_segments = _normalize_stt_segments(
            tr.get("segments", []) or [],
            limit=body.segments_limit,
        )
        language = str(tr.get("language", "") or "")
        source_engine = str(tr.get("source_engine", "mlx_whisper") or "mlx_whisper")
        clipped = bool(tr.get("clipped", False))
        if not transcript_text and not transcript_segments:
            degraded_reason = "stt_empty"
    except Exception as err:
        degraded_reason = f"stt_unavailable:{str(err)[:80]}"

    normalized = {
        "schema_version": "vetka_transcript_v1",
        "path": str(target),
        "modality": modality,
        "language": language,
        "duration_sec": duration_sec,
        "source_engine": source_engine,
        "text": transcript_text,
        "segments": transcript_segments,
    }

    return {
        "success": True,
        "path": str(target),
        "modality": modality,
        "mime_type": mime_type,
        "duration_sec": duration_sec,
        "transcript_normalized_json": normalized,
        "playback_metadata": {
            "modality": modality,
            "duration_sec": duration_sec,
            "segments_count": len(transcript_segments),
            "clipped": clipped,
            "max_transcribe_sec": int(body.max_transcribe_sec) if body.max_transcribe_sec else None,
            "clip_for_testing_only": bool(body.clip_for_testing_only),
        },
        "degraded_mode": bool(degraded_reason),
        "degraded_reason": degraded_reason,
    }


@router.post("/media/export/premiere-xml")
async def media_export_premiere_xml(body: MediaExportPremiereXMLRequest, request: Request):
    """
    P6.2 JSON -> Premiere XML export (XMEML v5 lane).
    """
    target = _resolve_media_path(body.path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"Media file not found: {body.path}")

    mime_type, _ = mimetypes.guess_type(str(target))
    mime_type = mime_type or "application/octet-stream"
    if not (mime_type.startswith("audio/") or mime_type.startswith("video/")):
        raise HTTPException(status_code=400, detail=f"Unsupported media type: {mime_type}")

    tx = await media_transcript_normalized(
        MediaTranscriptNormalizeRequest(
            path=str(target),
            max_transcribe_sec=body.max_transcribe_sec,
            clip_for_testing_only=body.clip_for_testing_only,
            segments_limit=body.segments_limit,
        ),
        request,
    )
    from src.services.premiere_adapter import PremiereExportRequest, get_premiere_adapter

    adapter = get_premiere_adapter("xml_interchange")
    artifact = adapter.export_from_transcript(
        PremiereExportRequest(
            source_path=str(target),
            transcript_normalized_json=tx.get("transcript_normalized_json") or {},
            sequence_name=str(body.sequence_name or "VETKA_Sequence"),
            fps=float(body.fps),
            lane="premiere_xml",
        )
    )
    return {
        "success": True,
        "format": "premiere_xml",
        "xml_root": "xmeml",
        "xml_content": artifact.xml_text,
        "source_path": str(target),
        "sequence_name": str(body.sequence_name or "VETKA_Sequence"),
        "fps": float(body.fps),
        "degraded_mode": bool(tx.get("degraded_mode", False)),
        "degraded_reason": str(tx.get("degraded_reason", "") or ""),
        "transcript_segments_count": int(
            len((tx.get("transcript_normalized_json") or {}).get("segments") or [])
        ),
    }


@router.post("/media/export/fcpxml")
async def media_export_fcpxml(body: MediaExportFCPXMLRequest, request: Request):
    """
    P6.3 JSON -> FCPXML export (secondary lane).
    """
    target = _resolve_media_path(body.path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"Media file not found: {body.path}")

    mime_type, _ = mimetypes.guess_type(str(target))
    mime_type = mime_type or "application/octet-stream"
    if not (mime_type.startswith("audio/") or mime_type.startswith("video/")):
        raise HTTPException(status_code=400, detail=f"Unsupported media type: {mime_type}")

    tx = await media_transcript_normalized(
        MediaTranscriptNormalizeRequest(
            path=str(target),
            max_transcribe_sec=body.max_transcribe_sec,
            clip_for_testing_only=body.clip_for_testing_only,
            segments_limit=body.segments_limit,
        ),
        request,
    )
    from src.services.premiere_adapter import PremiereExportRequest, get_premiere_adapter

    adapter = get_premiere_adapter("xml_interchange")
    artifact = adapter.export_from_transcript(
        PremiereExportRequest(
            source_path=str(target),
            transcript_normalized_json=tx.get("transcript_normalized_json") or {},
            sequence_name=str(body.sequence_name or "VETKA_Sequence"),
            fps=float(body.fps),
            lane="fcpxml",
        )
    )
    return {
        "success": True,
        "format": "fcpxml",
        "xml_root": "fcpxml",
        "xml_content": artifact.xml_text,
        "source_path": str(target),
        "sequence_name": str(body.sequence_name or "VETKA_Sequence"),
        "fps": float(body.fps),
        "degraded_mode": bool(tx.get("degraded_mode", False)),
        "degraded_reason": str(tx.get("degraded_reason", "") or ""),
        "transcript_segments_count": int(
            len((tx.get("transcript_normalized_json") or {}).get("segments") or [])
        ),
    }
# MARKER_141.ARTIFACT_CONTENT: Read artifact content by ID
# The artifact_id is URL-encoded, may contain slashes from file paths
@router.get("/{artifact_id:path}/content")
async def get_artifact_content(artifact_id: str):
    """
    Read the content of a panel artifact by its ID.

    The artifact scanner stores file_path in metadata. We look up
    the artifact to find its path, then read the file content.
    """
    # First find the artifact in the panel list
    result = list_artifacts_for_panel()
    artifacts = result.get("artifacts", [])

    target = None
    for art in artifacts:
        if art.get("id") == artifact_id or art.get("name") == artifact_id:
            target = art
            break

    if not target:
        raise HTTPException(status_code=404, detail=f"Artifact '{artifact_id}' not found")

    file_path = target.get("file_path", "")
    if not file_path:
        return {
            "success": True,
            "artifact_id": artifact_id,
            "content": "(no file path associated with this artifact)",
            "truncated": False,
        }

    # Resolve the file path
    p = Path(file_path)
    if not p.is_absolute():
        # Relative to project root
        project_root = Path(__file__).parent.parent.parent.parent
        p = project_root / file_path

    if not p.exists():
        return {
            "success": True,
            "artifact_id": artifact_id,
            "content": f"(file not found: {file_path})",
            "truncated": False,
        }

    try:
        max_size = 10000  # 10KB limit for UI display
        mime_type, _ = mimetypes.guess_type(str(p))
        mime_type = mime_type or "application/octet-stream"

        if mime_type.startswith("text/") or p.suffix.lower() in {".md", ".txt", ".json", ".yaml", ".yml", ".py", ".js", ".ts", ".tsx"}:
            content = p.read_text(encoding="utf-8", errors="replace")
            truncated = len(content) > max_size
            if truncated:
                content = content[:max_size]
            return {
                "success": True,
                "artifact_id": artifact_id,
                "file_path": str(p),
                "content": content,
                "encoding": "utf-8",
                "mimeType": mime_type,
                "size": p.stat().st_size,
                "truncated": truncated,
            }

        raw = p.read_bytes()
        truncated = len(raw) > max_size
        if truncated:
            raw = raw[:max_size]
        return {
            "success": True,
            "artifact_id": artifact_id,
            "file_path": str(p),
            "content": base64.b64encode(raw).decode("ascii"),
            "encoding": "base64",
            "mimeType": mime_type,
            "size": p.stat().st_size,
            "truncated": truncated,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "artifact_id": artifact_id,
        }
