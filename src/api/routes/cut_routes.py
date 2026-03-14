from __future__ import annotations

import asyncio
import json
import logging
import math
import mimetypes
import os
import re
import shutil
import subprocess
import threading

logger = logging.getLogger("cut.routes")
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.api.routes.artifact_routes import (
    MediaPreviewRequest,
    MediaTranscriptNormalizeRequest,
    media_preview,
    media_transcript_normalized,
)
from src.services.cut_audio_intel_eval import (
    build_energy_envelope,
    derive_pause_windows_from_silence,
    detect_offset_hybrid,
    detect_offset_via_correlation,
    detect_peak_offset,
)
from src.services.cut_marker_bundle_service import (
    create_marker_bundle_from_slices,
    hybrid_merge_slices,
)
from src.services.cut_mcp_job_store import get_cut_mcp_job_store
from src.services.cut_montage_ranker import MontageRanker, ScoredClip
from src.services.cut_proxy_worker import ProxyWorker, ProxyResult
from src.services.cut_scene_detector import (
    SceneBoundary,
    detect_scene_boundaries,
    group_clips_into_scenes,
)
from src.services.cut_timeline_events import CutTimelineEventEmitter
from src.services.cut_undo_redo import CutUndoRedoService, build_op_label
from src.services.pulse_cinema_matrix import get_cinema_matrix
from src.services.pulse_camelot_engine import get_camelot_engine
from src.services.pulse_conductor import (
    get_pulse_conductor,
    NarrativeBPM,
    VisualBPM,
    AudioBPM,
)
from src.services.pulse_script_analyzer import get_script_analyzer
from src.services.pulse_energy_critics import (
    compute_all_energies,
    compute_calibrated_energies,
    list_genre_profiles,
)
from src.services.pulse_timeline_bridge import get_pulse_timeline_bridge
from src.services.pulse_srt_bridge import (
    srt_to_narrative_bpm,
    srt_to_narrative_bpm_with_timing,
    parse_subtitles,
)
from src.services.converters.premiere_xml_converter import build_premiere_xml
from src.services.converters.fcpxml_converter import build_fcpxml
from src.services.pulse_story_space import (
    TrianglePosition,
    StorySpacePoint,
    compute_triangle_energies,
    chaos_index,
    scores_to_story_space,
    genre_to_triangle,
    interpolate_critic_weights,
    markers_to_story_space_points,
)
from src.services.cut_project_store import (
    CutProjectStore,
    build_cut_bootstrap_profile,
    build_cut_fallback_questions,
    quick_scan_cut_source,
)
from src.services.cut_scene_graph_taxonomy import (
    SCENE_GRAPH_EDGE_ALT_TAKE,
    SCENE_GRAPH_EDGE_CONTAINS,
    SCENE_GRAPH_EDGE_FOLLOWS,
    SCENE_GRAPH_EDGE_REFERENCES,
    SCENE_GRAPH_EDGE_SEMANTIC_MATCH,
    SCENE_GRAPH_EDGE_TYPE_SET,
    SCENE_GRAPH_NODE_ASSET,
    SCENE_GRAPH_NODE_NOTE,
    SCENE_GRAPH_NODE_SCENE,
    SCENE_GRAPH_NODE_TAKE,
)


router = APIRouter(prefix="/api/cut", tags=["CUT"])
_ACTIVE_JOB_STATES = {"queued", "running", "partial"}
_SANDBOX_BACKGROUND_LIMIT = 2


class CutBootstrapRequest(BaseModel):
    source_path: str
    sandbox_root: str
    project_name: str = ""
    mode: Literal["create_or_open", "open_existing", "create_new"] = "create_or_open"
    quick_scan_limit: int = Field(default=5000, ge=1, le=200000)
    bootstrap_profile: str = "default"
    use_core_mirror: bool = True
    create_project_if_missing: bool = True


class CutSceneAssemblyRequest(BaseModel):
    sandbox_root: str
    project_id: str
    timeline_id: str = "main"
    graph_id: str = "main"


class CutTimelinePatchRequest(BaseModel):
    sandbox_root: str
    project_id: str
    timeline_id: str = "main"
    author: str = "cut_mcp"
    ops: list[dict[str, Any]] = Field(default_factory=list, min_length=1)


class CutSceneGraphPatchRequest(BaseModel):
    sandbox_root: str
    project_id: str
    graph_id: str = "main"
    author: str = "cut_mcp"
    ops: list[dict[str, Any]] = Field(default_factory=list, min_length=1)


class CutTimeMarkerApplyRequest(BaseModel):
    sandbox_root: str
    project_id: str
    timeline_id: str = "main"
    author: str = "cut_mcp"
    op: Literal["create", "archive"] = "create"
    marker_id: str | None = None
    media_path: str = ""
    kind: Literal["favorite", "comment", "cam", "insight", "chat"] = "favorite"
    start_sec: float = Field(default=0.0, ge=0.0)
    end_sec: float = Field(default=1.0, ge=0.0)
    anchor_sec: float | None = Field(default=None, ge=0.0)
    score: float = Field(default=1.0, ge=0.0, le=1.0)
    label: str = ""
    text: str = ""
    context_slice: dict[str, Any] | None = None
    cam_payload: dict[str, Any] | None = None
    chat_thread_id: str | None = None
    comment_thread_id: str | None = None
    source_engine: str = "cut_mcp"


class PlayerLabMarkerImportItem(BaseModel):
    marker_id: str = ""
    media_path: str
    kind: Literal["favorite", "comment", "cam", "insight", "chat"] = "favorite"
    start_sec: float = Field(default=0.0, ge=0.0)
    end_sec: float = Field(default=0.0, ge=0.0)
    anchor_sec: float | None = Field(default=None, ge=0.0)
    score: float = Field(default=1.0, ge=0.0, le=1.0)
    label: str = ""
    text: str = ""
    author: str = "player_lab"
    context_slice: dict[str, Any] | None = None
    cam_payload: dict[str, Any] | None = None
    chat_thread_id: str | None = None
    comment_thread_id: str | None = None
    source_engine: str = "player_lab"
    status: str = "active"


class PlayerLabProvisionalEventImportItem(BaseModel):
    provisional_event_id: str = ""
    event_type: str = "vetka_logo_capture"
    media_path: str
    start_sec: float = Field(default=0.0, ge=0.0)
    end_sec: float = Field(default=0.0, ge=0.0)
    text: str = ""
    export_mode: str = "srt_comment"
    migration_status: str = "local_only"


class CutPlayerLabMarkerImportRequest(BaseModel):
    sandbox_root: str
    project_id: str
    timeline_id: str = "main"
    author: str = "player_lab_import"
    markers: list[PlayerLabMarkerImportItem] = Field(default_factory=list)
    provisional_events: list[PlayerLabProvisionalEventImportItem] = Field(default_factory=list)


class CutMediaSupportRequest(BaseModel):
    sandbox_root: str = ""
    source_path: str
    probe_ffprobe: bool = True


class CutExportRequest(BaseModel):
    sandbox_root: str
    project_id: str
    timeline_id: str = "main"
    sequence_name: str = "VETKA_Sequence"
    fps: int = Field(default=25, ge=1, le=120)
    include_archived_markers: bool = False


class CutBatchExportRequest(BaseModel):
    sandbox_root: str
    project_id: str
    timeline_id: str = "main"
    fps: int = Field(default=25, ge=1, le=120)
    sequence_name: str = "VETKA_Sequence"
    formats: list[Literal["premiere_xml", "fcpxml", "otio", "edl"]] = Field(default_factory=lambda: ["premiere_xml"])
    social_targets: list[Literal["youtube", "instagram_reels", "instagram_feed_1x1", "instagram_feed_4x5", "tiktok", "telegram", "vk", "x"]] = Field(default_factory=list)


class CutMarkerSrtExportRequest(BaseModel):
    sandbox_root: str
    project_id: str
    timeline_id: str = "main"
    include_archived: bool = False
    kinds: list[str] = Field(default_factory=list)


class CutMarkerSrtImportRequest(BaseModel):
    sandbox_root: str
    project_id: str
    timeline_id: str = "main"
    srt_content: str
    author: str = "player_lab_srt_import"
    default_media_path: str = ""
    mode: Literal["append", "replace"] = "append"



class CutMontagePromoteMarkerRequest(BaseModel):
    sandbox_root: str
    project_id: str
    marker_id: str
    author: str = "cut_mcp"
    decision_id: str = ""
    lane_id: str = "V1"
    decision_status: Literal["accepted", "rejected"] = "accepted"
    editorial_intent: str = ""


class CutWaveformBuildRequest(BaseModel):
    sandbox_root: str
    project_id: str
    bins: int = Field(default=64, ge=16, le=256)
    limit: int = Field(default=12, ge=1, le=64)


class CutTranscriptNormalizeRequest(BaseModel):
    sandbox_root: str
    project_id: str
    limit: int = Field(default=6, ge=1, le=32)
    segments_limit: int = Field(default=128, ge=1, le=1024)
    max_transcribe_sec: int | None = Field(default=180, ge=5, le=1200)


class CutThumbnailBuildRequest(BaseModel):
    sandbox_root: str
    project_id: str
    limit: int = Field(default=12, ge=1, le=32)
    waveform_bins: int = Field(default=48, ge=16, le=256)
    preview_segments_limit: int = Field(default=24, ge=1, le=128)


class CutAudioSyncRequest(BaseModel):
    sandbox_root: str
    project_id: str
    limit: int = Field(default=6, ge=2, le=16)
    sample_bytes: int = Field(default=8192, ge=1024, le=65536)
    method: Literal["peaks+correlation", "correlation", "peak_only"] = "peaks+correlation"


class CutPauseSliceRequest(BaseModel):
    sandbox_root: str
    project_id: str
    limit: int = Field(default=6, ge=1, le=16)
    sample_bytes: int = Field(default=8192, ge=1024, le=65536)
    frame_ms: int = Field(default=20, ge=10, le=100)
    silence_threshold: float = Field(default=0.08, gt=0.0, le=1.0)
    min_silence_ms: int = Field(default=250, ge=80, le=2000)
    keep_silence_ms: int = Field(default=80, ge=0, le=1000)


class CutTimecodeSyncRequest(BaseModel):
    sandbox_root: str
    project_id: str
    limit: int = Field(default=6, ge=2, le=16)
    fps: int = Field(default=25, ge=1, le=120)


class CutMusicSyncRequest(BaseModel):
    sandbox_root: str
    project_id: str
    music_path: str = ""
    bpm_hint: float | None = Field(default=None, ge=40.0, le=240.0)
    max_analysis_sec: int = Field(default=180, ge=10, le=1200)


class CutMusicSyncSliceConfig(BaseModel):
    method: Literal["transcript_only", "energy_only", "hybrid_merge"] = "hybrid_merge"
    use_sync: bool = True
    sync_method: Literal["peaks+correlation", "correlation", "peak_only"] = "peaks+correlation"
    frame_ms: int = Field(default=20, ge=10, le=100)
    silence_threshold: float = Field(default=0.08, gt=0.0, le=1.0)
    min_silence_ms: int = Field(default=250, ge=80, le=2000)
    keep_silence_ms: int = Field(default=80, ge=0, le=1000)
    sample_bytes: int = Field(default=8192, ge=1024, le=65536)


class CutApplyWithMarkersRequest(BaseModel):
    sandbox_root: str
    project_id: str
    timeline_id: str = "main"
    track_id: str = ""
    media_path: str = ""
    slice_config: CutMusicSyncSliceConfig = Field(default_factory=CutMusicSyncSliceConfig)


class CutSceneDetectApplyRequest(BaseModel):
    """MARKER_173.3 — Request model for scene-detect-and-apply."""
    sandbox_root: str
    project_id: str
    timeline_id: str = "main"
    source_paths: list[str] = Field(default_factory=list, description="Media files to run scene detection on. If empty, uses all clips from the timeline.")
    threshold: float = Field(default=0.3, ge=0.05, le=0.95, description="Histogram diff threshold for scene boundary detection (lower = more sensitive)")
    interval_sec: float = Field(default=1.0, ge=0.1, le=10.0, description="Sampling interval in seconds")
    max_duration_sec: float = Field(default=300.0, ge=10.0, le=3600.0, description="Max duration per file to analyse")
    lane_id: str = Field(default="scenes", description="Lane to create detected scene clips on")
    update_scene_graph: bool = Field(default=True, description="Also update the scene graph with detected scenes")


def _cut_state_error(code: str, message: str, *, recoverable: bool = True) -> dict[str, Any]:
    return {
        "success": False,
        "schema_version": "cut_project_state_v1",
        "error": {
            "code": code,
            "message": message,
            "recoverable": recoverable,
        },
    }


def _timeline_error(code: str, message: str, *, recoverable: bool = True) -> dict[str, Any]:
    return {
        "success": False,
        "schema_version": "cut_timeline_apply_v1",
        "error": {
            "code": code,
            "message": message,
            "recoverable": recoverable,
        },
    }


def _scene_graph_error(code: str, message: str, *, recoverable: bool = True) -> dict[str, Any]:
    return {
        "success": False,
        "schema_version": "cut_scene_graph_apply_v1",
        "error": {
            "code": code,
            "message": message,
            "recoverable": recoverable,
        },
    }


def _time_marker_error(code: str, message: str, *, recoverable: bool = True) -> dict[str, Any]:
    return {
        "success": False,
        "schema_version": "cut_time_marker_apply_v1",
        "marker": None,
        "marker_bundle": None,
        "edit_event": None,
        "error": {
            "code": code,
            "message": message,
            "recoverable": recoverable,
        },
    }


def _bootstrap_error(code: str, message: str, *, degraded_reason: str, recoverable: bool = True) -> dict[str, Any]:
    return {
        "success": False,
        "schema_version": "cut_bootstrap_v1",
        "error": {
            "code": code,
            "message": message,
            "recoverable": recoverable,
        },
        "degraded_mode": True,
        "degraded_reason": degraded_reason,
    }


def _worker_job_error(code: str, message: str, *, existing_job: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "success": False,
        "schema_version": "cut_mcp_job_v1",
        "error": {
            "code": code,
            "message": message,
            "recoverable": True,
        },
    }
    if existing_job is not None:
        payload["job"] = existing_job
        payload["job_id"] = str(existing_job.get("job_id") or "")
    return payload


def _montage_error(code: str, message: str, *, recoverable: bool = True) -> dict[str, Any]:
    return {
        "success": False,
        "schema_version": "cut_montage_state_v1",
        "decision": None,
        "montage_state": None,
        "error": {
            "code": code,
            "message": message,
            "recoverable": recoverable,
        },
    }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _infer_cut_media_modality(source_path: str) -> str:
    ext = os.path.splitext(str(source_path or ""))[1].lower()
    if ext in {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}:
        return "video"
    if ext in {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}:
        return "audio"
    return "unknown"


def _infer_cut_asset_kind(modality: str, lane_type: str) -> str:
    if modality in {"video", "audio"}:
        return modality
    if lane_type.startswith("video"):
        return "video"
    if lane_type.startswith("audio"):
        return "audio"
    return "media"


def _build_initial_timeline_state(project: dict[str, Any], timeline_id: str) -> dict[str, Any]:
    source_path = str(project.get("source_path") or "").strip()
    scan = quick_scan_cut_source(source_path, limit=5000)
    source_root = source_path
    lanes: list[dict[str, Any]] = []

    video_lane = {"lane_id": "video_main", "lane_type": "video_main", "clips": []}
    audio_lane = {"lane_id": "audio_sync", "lane_type": "audio_sync", "clips": []}
    video_ext = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}
    audio_ext = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
    clip_counter = 0

    if os.path.isdir(source_root):
        for path in sorted(os.scandir(source_root), key=lambda e: e.name.lower()):
            if not path.is_file():
                continue
            ext = os.path.splitext(path.name)[1].lower()
            if ext not in video_ext and ext not in audio_ext:
                continue
            clip_counter += 1
            clip = {
                "clip_id": f"clip_{clip_counter:04d}",
                "record_id": f"record_{clip_counter:04d}",
                "scene_id": "scene_01",
                "take_id": f"take_{clip_counter:04d}",
                "start_sec": float(max(0, clip_counter - 1)) * 5.0,
                "duration_sec": 5.0,
                "source_path": path.path,
                "sync": None,
            }
            if ext in video_ext:
                video_lane["clips"].append(clip)
            else:
                audio_lane["clips"].append(clip)

    if video_lane["clips"]:
        lanes.append(video_lane)
    if audio_lane["clips"]:
        lanes.append(audio_lane)

    return {
        "schema_version": "cut_timeline_state_v1",
        "project_id": str(project.get("project_id") or ""),
        "timeline_id": str(timeline_id or "main"),
        "revision": 1,
        "fps": 25,
        "lanes": lanes,
        "selection": {
            "clip_ids": [video_lane["clips"][0]["clip_id"]] if video_lane["clips"] else [],
            "scene_ids": ["scene_01"] if lanes else [],
        },
        "view": {
            "zoom": 1.0,
            "scroll_sec": 0.0,
            "active_lane_id": lanes[0]["lane_id"] if lanes else "",
        },
        "updated_at": _utc_now_iso(),
        "stats": scan["stats"],
        "sync_groups": [],
    }


def _build_initial_scene_graph(
    project: dict[str, Any], timeline_state: dict[str, Any], graph_id: str
) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    scenes: dict[str, dict[str, Any]] = {}
    scene_order: list[str] = []
    take_node_ids: dict[tuple[str, str], str] = {}
    take_index_by_scene: dict[str, int] = {}
    asset_counter = 0
    take_counter = 0

    for lane in timeline_state.get("lanes", []):
        lane_id = str(lane.get("lane_id") or "")
        lane_type = str(lane.get("lane_type") or "")
        for clip in lane.get("clips", []):
            scene_id = str(clip.get("scene_id") or "").strip() or "scene_01"
            take_id = str(clip.get("take_id") or "").strip() or "take_01"
            record_id = str(clip.get("record_id") or "").strip() or take_id
            source_path = str(clip.get("source_path") or "")
            clip_id = str(clip.get("clip_id") or "")
            duration_sec = float(clip.get("duration_sec") or 0.0)
            modality = _infer_cut_media_modality(source_path)
            if scene_id not in scenes:
                scene_order.append(scene_id)
                scene_label = scene_id.replace("_", " ").title()
                scene_node = {
                    "node_id": scene_id,
                    "node_type": SCENE_GRAPH_NODE_SCENE,
                    "label": scene_label,
                    "record_ref": None,
                    "metadata": {
                        "timeline_id": str(timeline_state.get("timeline_id") or "main"),
                        "timeline_lane": lane_id,
                        "scene_index": len(scene_order),
                        "summary": "",
                        "lane_ids": [lane_id],
                        "source_paths": [],
                        "take_count": 0,
                        "asset_count": 0,
                        "clip_count": 0,
                        "duration_sec": 0.0,
                    },
                }
                scenes[scene_id] = scene_node
                nodes.append(scene_node)
            take_key = (scene_id, take_id)
            if take_key not in take_node_ids:
                take_counter += 1
                take_index_by_scene[scene_id] = take_index_by_scene.get(scene_id, 0) + 1
                take_node_id = f"take_node_{take_counter:04d}"
                take_node_ids[take_key] = take_node_id
                nodes.append(
                    {
                        "node_id": take_node_id,
                        "node_type": SCENE_GRAPH_NODE_TAKE,
                        "label": take_id.replace("_", " ").title(),
                        "record_ref": record_id,
                        "metadata": {
                            "scene_id": scene_id,
                            "take_id": take_id,
                            "take_index": take_index_by_scene[scene_id],
                            "lane_id": lane_id,
                            "lane_type": lane_type,
                            "clip_id": clip_id,
                            "source_path": source_path,
                            "duration_sec": duration_sec,
                            "modality": modality,
                        },
                    }
                )
                edges.append(
                    {
                        "edge_id": f"edge_contains_{scene_id}_{take_counter:04d}",
                        "edge_type": SCENE_GRAPH_EDGE_CONTAINS,
                        "source": scene_id,
                        "target": take_node_id,
                        "weight": 1.0,
                    }
                )
                scene_meta = scenes[scene_id]["metadata"]
                scene_meta["take_count"] = int(scene_meta.get("take_count") or 0) + 1
            asset_counter += 1
            asset_node_id = f"asset_{asset_counter:04d}"
            asset_label = os.path.basename(source_path) or asset_node_id
            nodes.append(
                {
                    "node_id": asset_node_id,
                    "node_type": SCENE_GRAPH_NODE_ASSET,
                    "label": asset_label,
                    "record_ref": record_id,
                    "metadata": {
                        "scene_id": scene_id,
                        "take_id": take_id,
                        "clip_id": clip_id,
                        "source_path": source_path,
                        "start_sec": float(clip.get("start_sec") or 0.0),
                        "duration_sec": duration_sec,
                        "timeline_lane": lane_id,
                        "lane_type": lane_type,
                        "asset_kind": _infer_cut_asset_kind(modality, lane_type),
                        "modality": modality,
                    },
                }
            )
            edges.append(
                {
                    "edge_id": f"edge_references_{asset_counter:04d}",
                    "edge_type": SCENE_GRAPH_EDGE_REFERENCES,
                    "source": take_node_ids[take_key],
                    "target": asset_node_id,
                    "weight": 1.0,
                }
            )
            scene_meta = scenes[scene_id]["metadata"]
            scene_meta["asset_count"] = int(scene_meta.get("asset_count") or 0) + 1
            scene_meta["clip_count"] = int(scene_meta.get("clip_count") or 0) + 1
            scene_meta["duration_sec"] = round(float(scene_meta.get("duration_sec") or 0.0) + duration_sec, 4)
            if lane_id not in scene_meta["lane_ids"]:
                scene_meta["lane_ids"].append(lane_id)
            if source_path and source_path not in scene_meta["source_paths"]:
                scene_meta["source_paths"].append(source_path)

    for index in range(len(scene_order) - 1):
        edges.append(
            {
                "edge_id": f"edge_follows_{index + 1:04d}",
                "edge_type": SCENE_GRAPH_EDGE_FOLLOWS,
                "source": scene_order[index],
                "target": scene_order[index + 1],
                "weight": 1.0,
            }
        )

    for scene_id, scene_node in scenes.items():
        metadata = scene_node["metadata"]
        take_count = int(metadata.get("take_count") or 0)
        asset_count = int(metadata.get("asset_count") or 0)
        duration_sec = float(metadata.get("duration_sec") or 0.0)
        metadata["summary"] = f"{take_count} takes · {asset_count} assets · {duration_sec:.1f}s"
        metadata["source_paths"] = sorted(metadata.get("source_paths", []))

    return {
        "schema_version": "cut_scene_graph_v1",
        "project_id": str(project.get("project_id") or ""),
        "graph_id": str(graph_id or "main"),
        "revision": 1,
        "nodes": nodes,
        "edges": edges,
        "updated_at": _utc_now_iso(),
    }


def _build_scene_graph_view(
    scene_graph: dict[str, Any] | None,
    timeline_state: dict[str, Any] | None = None,
    thumbnail_bundle: dict[str, Any] | None = None,
    sync_surface: dict[str, Any] | None = None,
    time_marker_bundle: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if scene_graph is None:
        return None

    contains_parent_by_target: dict[str, str] = {}
    references_parent_by_target: dict[str, str] = {}
    take_node_ids_by_clip: dict[str, str] = {}
    scene_node_ids: set[str] = set()
    thumbnail_by_source: dict[str, dict[str, Any]] = {
        str(item.get("source_path") or ""): dict(item)
        for item in (thumbnail_bundle or {}).get("items", [])
        if str(item.get("source_path") or "").strip()
    }
    sync_by_source: dict[str, dict[str, Any]] = {
        str(item.get("source_path") or ""): dict(item)
        for item in (sync_surface or {}).get("items", [])
        if str(item.get("source_path") or "").strip()
    }
    markers_by_source: dict[str, int] = {}
    for marker in (time_marker_bundle or {}).get("items", []):
        media_path = str(marker.get("media_path") or "").strip()
        if media_path:
            markers_by_source[media_path] = markers_by_source.get(media_path, 0) + 1
    for edge in scene_graph.get("edges", []):
        if str(edge.get("edge_type") or "") == SCENE_GRAPH_EDGE_CONTAINS:
            contains_parent_by_target[str(edge.get("target") or "")] = str(edge.get("source") or "")
        if str(edge.get("edge_type") or "") == SCENE_GRAPH_EDGE_REFERENCES:
            references_parent_by_target[str(edge.get("target") or "")] = str(edge.get("source") or "")

    def _node_bucket(node_type: str) -> str:
        if node_type == SCENE_GRAPH_NODE_SCENE:
            return "primary_structural"
        if node_type == SCENE_GRAPH_NODE_TAKE:
            return "media_candidate"
        if node_type == SCENE_GRAPH_NODE_ASSET:
            return "support_media"
        if node_type == SCENE_GRAPH_NODE_NOTE:
            return "annotation"
        return "generic"

    def _append_crosslink(target: dict[str, list[str]], key: str, node_id: str) -> None:
        if not key:
            return
        bucket = target.setdefault(key, [])
        if node_id not in bucket:
            bucket.append(node_id)

    def _map_dag_node_type(node_type: str) -> str:
        if node_type == SCENE_GRAPH_NODE_SCENE:
            return "roadmap_task"
        if node_type == SCENE_GRAPH_NODE_TAKE:
            return "subtask"
        if node_type == SCENE_GRAPH_NODE_ASSET:
            return "proposal"
        if node_type == SCENE_GRAPH_NODE_NOTE:
            return "condition"
        return "task"

    def _map_dag_layer(node_type: str) -> int:
        if node_type == SCENE_GRAPH_NODE_SCENE:
            return 0
        if node_type == SCENE_GRAPH_NODE_TAKE:
            return 1
        if node_type == SCENE_GRAPH_NODE_ASSET:
            return 2
        if node_type == SCENE_GRAPH_NODE_NOTE:
            return 2
        return 3

    def _map_dag_edge_type(family: str) -> str:
        return "predicted" if family == "intelligence" else "structural"

    def _build_render_hints(
        *,
        node_type: str,
        metadata: dict[str, Any],
        selection_refs: dict[str, list[str]],
    ) -> dict[str, Any]:
        source_paths = selection_refs.get("source_paths", [])
        source_path = source_paths[0] if source_paths else ""
        thumbnail = thumbnail_by_source.get(source_path or "")
        sync_item = sync_by_source.get(source_path or "")
        modality = str(metadata.get("modality") or thumbnail.get("modality") if thumbnail else metadata.get("modality") or "").strip() or None
        duration = metadata.get("duration_sec")
        if not isinstance(duration, (int, float)) or isinstance(duration, bool):
            duration = thumbnail.get("duration_sec") if thumbnail else None
        if not isinstance(duration, (int, float)) or isinstance(duration, bool):
            duration = None
        poster_url = None
        if isinstance(thumbnail, dict):
            preview_assets = dict(thumbnail.get("preview_assets") or {})
            poster_url = str(preview_assets.get("poster_url") or "").strip() or None
        marker_count = sum(markers_by_source.get(path, 0) for path in source_paths)
        recommended_method = str(sync_item.get("recommended_method") or "").strip() if isinstance(sync_item, dict) else ""
        sync_badge = recommended_method or None
        if node_type == SCENE_GRAPH_NODE_SCENE:
            display_mode = "scene_card"
        elif node_type == SCENE_GRAPH_NODE_TAKE:
            display_mode = "take_preview"
        elif node_type == SCENE_GRAPH_NODE_ASSET:
            display_mode = "asset_preview"
        else:
            display_mode = "annotation_chip"
        return {
            "display_mode": display_mode,
            "poster_url": poster_url,
            "modality": modality,
            "duration_sec": round(float(duration), 4) if isinstance(duration, (int, float)) else None,
            "marker_count": int(marker_count),
            "sync_badge": sync_badge,
        }

    view_nodes: list[dict[str, Any]] = []
    dag_nodes: list[dict[str, Any]] = []
    crosslinks_by_clip_id: dict[str, list[str]] = {}
    crosslinks_by_scene_id: dict[str, list[str]] = {}
    crosslinks_by_source_path: dict[str, list[str]] = {}
    for node in scene_graph.get("nodes", []):
        node_id = str(node.get("node_id") or "")
        node_type = str(node.get("node_type") or "")
        metadata = dict(node.get("metadata") or {})
        if node_type == SCENE_GRAPH_NODE_SCENE:
            scene_node_ids.add(node_id)
        if node_type == SCENE_GRAPH_NODE_TAKE:
            clip_id = str(metadata.get("clip_id") or "").strip()
            if clip_id:
                take_node_ids_by_clip[clip_id] = node_id
        rank_hint = metadata.get("scene_index")
        if rank_hint is None:
            rank_hint = metadata.get("take_index")
        if not isinstance(rank_hint, int) or isinstance(rank_hint, bool):
            rank_hint = None
        parent_id = contains_parent_by_target.get(node_id) or references_parent_by_target.get(node_id)
        selection_refs = {
            "clip_ids": [],
            "scene_ids": [],
            "source_paths": [],
        }
        clip_id = str(metadata.get("clip_id") or "").strip()
        if clip_id:
            selection_refs["clip_ids"].append(clip_id)
            _append_crosslink(crosslinks_by_clip_id, clip_id, node_id)
        scene_id = str(metadata.get("scene_id") or "").strip()
        if not scene_id and node_type == SCENE_GRAPH_NODE_SCENE:
            scene_id = node_id
        if scene_id:
            selection_refs["scene_ids"].append(scene_id)
            _append_crosslink(crosslinks_by_scene_id, scene_id, node_id)
        for source_path in metadata.get("source_paths", []) if isinstance(metadata.get("source_paths"), list) else []:
            value = str(source_path).strip()
            if value and value not in selection_refs["source_paths"]:
                selection_refs["source_paths"].append(value)
                _append_crosslink(crosslinks_by_source_path, value, node_id)
        source_path = str(metadata.get("source_path") or "").strip()
        if source_path and source_path not in selection_refs["source_paths"]:
            selection_refs["source_paths"].append(source_path)
            _append_crosslink(crosslinks_by_source_path, source_path, node_id)
        render_hints = _build_render_hints(node_type=node_type, metadata=metadata, selection_refs=selection_refs)
        view_nodes.append(
            {
                "node_id": node_id,
                "node_type": node_type,
                "visual_bucket": _node_bucket(node_type),
                "label": str(node.get("label") or node_id),
                "parent_id": parent_id or None,
                "rank_hint": rank_hint,
                "selection_refs": selection_refs,
                "render_hints": render_hints,
                "metadata": metadata,
            }
        )
        dag_nodes.append(
            {
                "id": f"cut_graph:{node_id}",
                "type": _map_dag_node_type(node_type),
                "label": str(node.get("label") or node_id),
                "status": "done",
                "layer": _map_dag_layer(node_type),
                "parentId": f"cut_graph:{parent_id}" if parent_id else None,
                "taskId": str(scene_graph.get("graph_id") or "main"),
                "graphKind": "project_task",
                "primaryNodeId": node_id,
                "metadata": {
                    **metadata,
                    "scene_graph_node_type": node_type,
                    "visual_bucket": _node_bucket(node_type),
                    "render_hints": render_hints,
                },
            }
        )

    view_edges: list[dict[str, Any]] = []
    overlay_edges: list[dict[str, Any]] = []
    dag_edges: list[dict[str, Any]] = []
    for edge in scene_graph.get("edges", []):
        edge_type = str(edge.get("edge_type") or "")
        family = "intelligence" if edge_type == SCENE_GRAPH_EDGE_SEMANTIC_MATCH else "structural"
        view_edge = {
            "edge_id": str(edge.get("edge_id") or ""),
            "edge_type": edge_type,
            "family": family,
            "source": str(edge.get("source") or ""),
            "target": str(edge.get("target") or ""),
            "weight": float(edge.get("weight") or 0.0),
            "visible_by_default": family == "structural",
        }
        view_edges.append(view_edge)
        if family == "intelligence":
            overlay_edges.append(dict(view_edge))
        dag_edges.append(
            {
                "id": f"cut_graph:{view_edge['edge_id']}",
                "source": f"cut_graph:{view_edge['source']}",
                "target": f"cut_graph:{view_edge['target']}",
                "type": _map_dag_edge_type(family),
                "strength": float(view_edge["weight"]),
                "relationKind": edge_type,
            }
        )
        

    selection = dict((timeline_state or {}).get("selection") or {})
    selected_clip_ids = [str(value) for value in selection.get("clip_ids", []) if str(value).strip()]
    selected_scene_ids = [str(value) for value in selection.get("scene_ids", []) if str(value).strip()]
    focused_node_ids: list[str] = []
    for clip_id in selected_clip_ids:
        take_node_id = take_node_ids_by_clip.get(clip_id)
        if take_node_id and take_node_id not in focused_node_ids:
            focused_node_ids.append(take_node_id)
            parent_id = contains_parent_by_target.get(take_node_id)
            if parent_id and parent_id not in focused_node_ids:
                focused_node_ids.append(parent_id)
    for scene_id in selected_scene_ids:
        if scene_id in scene_node_ids and scene_id not in focused_node_ids:
            focused_node_ids.append(scene_id)
    anchor_node_id = focused_node_ids[0] if focused_node_ids else None
    nodes_by_id = {str(node.get("node_id") or ""): node for node in view_nodes}
    inspector_nodes: list[dict[str, Any]] = []
    for node_id in focused_node_ids:
        node = nodes_by_id.get(node_id)
        if not isinstance(node, dict):
            continue
        node_type = str(node.get("node_type") or "")
        metadata = dict(node.get("metadata") or {})
        selection_refs = dict(node.get("selection_refs") or {})
        summary = str(metadata.get("summary") or "").strip()
        if not summary:
            render_hints = dict(node.get("render_hints") or {})
            marker_count = int(render_hints.get("marker_count") or 0)
            duration_sec = render_hints.get("duration_sec")
            if node_type == SCENE_GRAPH_NODE_TAKE:
                summary = f"take · markers {marker_count}" + (f" · {duration_sec:.1f}s" if isinstance(duration_sec, (int, float)) else "")
            elif node_type == SCENE_GRAPH_NODE_ASSET:
                summary = f"asset · markers {marker_count}" + (f" · {duration_sec:.1f}s" if isinstance(duration_sec, (int, float)) else "")
            elif node_type == SCENE_GRAPH_NODE_NOTE:
                summary = str(metadata.get("text") or "note")
            else:
                summary = node_type
        inspector_nodes.append(
            {
                "node_id": node_id,
                "node_type": node_type,
                "label": str(node.get("label") or node_id),
                "summary": summary,
                "related_clip_ids": [str(v) for v in selection_refs.get("clip_ids", [])],
                "related_source_paths": [str(v) for v in selection_refs.get("source_paths", [])],
            }
        )

    return {
        "schema_version": "cut_scene_graph_view_v1",
        "graph_id": str(scene_graph.get("graph_id") or "main"),
        "nodes": view_nodes,
        "edges": view_edges,
        "focus": {
            "selected_clip_ids": selected_clip_ids,
            "selected_scene_ids": selected_scene_ids,
            "focused_node_ids": focused_node_ids,
            "anchor_node_id": anchor_node_id,
        },
        "layout_hints": {
            "structural_edge_types": [
                SCENE_GRAPH_EDGE_CONTAINS,
                SCENE_GRAPH_EDGE_FOLLOWS,
                SCENE_GRAPH_EDGE_ALT_TAKE,
                SCENE_GRAPH_EDGE_REFERENCES,
            ],
            "intelligence_edge_types": [SCENE_GRAPH_EDGE_SEMANTIC_MATCH],
            "primary_rank_edge_types": [
                SCENE_GRAPH_EDGE_FOLLOWS,
                SCENE_GRAPH_EDGE_CONTAINS,
            ],
        },
        "crosslinks": {
            "by_clip_id": crosslinks_by_clip_id,
            "by_scene_id": crosslinks_by_scene_id,
            "by_source_path": crosslinks_by_source_path,
        },
        "structural_subgraph": {
            "node_ids": [str(node.get("node_id") or "") for node in view_nodes],
            "edge_ids": [str(edge.get("edge_id") or "") for edge in view_edges if str(edge.get("family") or "") == "structural"],
        },
        "overlay_edges": overlay_edges,
        "dag_projection": {
            "nodes": dag_nodes,
            "edges": dag_edges,
            "root_ids": [f"cut_graph:{node_id}" for node_id in scene_node_ids],
        },
        "inspector": {
            "primary_node_id": anchor_node_id,
            "focused_nodes": inspector_nodes,
        },
        "generated_at": _utc_now_iso(),
    }


def _find_lane(timeline_state: dict[str, Any], lane_id: str) -> dict[str, Any] | None:
    for lane in timeline_state.get("lanes", []):
        if str(lane.get("lane_id") or "") == str(lane_id):
            return lane
    return None


def _find_clip(timeline_state: dict[str, Any], clip_id: str) -> tuple[dict[str, Any], dict[str, Any]] | tuple[None, None]:
    for lane in timeline_state.get("lanes", []):
        for clip in lane.get("clips", []):
            if str(clip.get("clip_id") or "") == str(clip_id):
                return lane, clip
    return None, None


def _apply_timeline_ops(timeline_state: dict[str, Any], ops: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    state = deepcopy(timeline_state)
    applied_ops: list[dict[str, Any]] = []

    for raw_op in ops:
        op = dict(raw_op or {})
        op_type = str(op.get("op") or "").strip()
        if op_type == "set_selection":
            selection = state.setdefault("selection", {})
            clip_ids = [str(value) for value in op.get("clip_ids", [])]
            scene_ids = [str(value) for value in op.get("scene_ids", [])]
            selection["clip_ids"] = clip_ids
            selection["scene_ids"] = scene_ids
            applied_ops.append({"op": op_type, "clip_ids": clip_ids, "scene_ids": scene_ids})
            continue

        if op_type == "set_view":
            view = state.setdefault("view", {})
            applied: dict[str, Any] = {"op": op_type}
            if "zoom" in op:
                zoom = float(op["zoom"])
                if zoom <= 0:
                    raise ValueError("zoom must be > 0")
                view["zoom"] = zoom
                applied["zoom"] = zoom
            if "scroll_sec" in op:
                scroll_sec = float(op["scroll_sec"])
                if scroll_sec < 0:
                    raise ValueError("scroll_sec must be >= 0")
                view["scroll_sec"] = scroll_sec
                applied["scroll_sec"] = scroll_sec
            if "active_lane_id" in op:
                active_lane_id = str(op["active_lane_id"])
                lane = _find_lane(state, active_lane_id)
                if lane is None:
                    raise ValueError(f"lane not found: {active_lane_id}")
                view["active_lane_id"] = active_lane_id
                applied["active_lane_id"] = active_lane_id
            applied_ops.append(applied)
            continue

        if op_type == "move_clip":
            clip_id = str(op.get("clip_id") or "")
            target_lane_id = str(op.get("lane_id") or "")
            start_sec = float(op.get("start_sec"))
            if start_sec < 0:
                raise ValueError("start_sec must be >= 0")
            source_lane, clip = _find_clip(state, clip_id)
            if source_lane is None or clip is None:
                raise ValueError(f"clip not found: {clip_id}")
            target_lane = _find_lane(state, target_lane_id)
            if target_lane is None:
                raise ValueError(f"lane not found: {target_lane_id}")
            source_lane["clips"] = [entry for entry in source_lane.get("clips", []) if str(entry.get("clip_id") or "") != clip_id]
            clip["start_sec"] = start_sec
            target_lane.setdefault("clips", []).append(clip)
            target_lane["clips"] = sorted(target_lane["clips"], key=lambda item: float(item.get("start_sec") or 0.0))
            applied_ops.append(
                {"op": op_type, "clip_id": clip_id, "lane_id": target_lane_id, "start_sec": start_sec}
            )
            continue

        if op_type == "trim_clip":
            clip_id = str(op.get("clip_id") or "")
            duration_sec = float(op.get("duration_sec"))
            if duration_sec <= 0:
                raise ValueError("duration_sec must be > 0")
            _, clip = _find_clip(state, clip_id)
            if clip is None:
                raise ValueError(f"clip not found: {clip_id}")
            clip["duration_sec"] = duration_sec
            applied: dict[str, Any] = {"op": op_type, "clip_id": clip_id, "duration_sec": duration_sec}
            if "start_sec" in op:
                start_sec = float(op["start_sec"])
                if start_sec < 0:
                    raise ValueError("start_sec must be >= 0")
                clip["start_sec"] = start_sec
                applied["start_sec"] = start_sec
            applied_ops.append(applied)
            continue

        if op_type == "apply_sync_offset":
            clip_id = str(op.get("clip_id") or "")
            offset_sec = float(op.get("offset_sec"))
            method = str(op.get("method") or "").strip() or "unknown"
            reference_path = str(op.get("reference_path") or "").strip()
            source = str(op.get("source") or "sync_surface")
            confidence = float(op.get("confidence", 0.0))
            _, clip = _find_clip(state, clip_id)
            if clip is None:
                raise ValueError(f"clip not found: {clip_id}")
            clip["start_sec"] = max(0.0, round(float(clip.get("start_sec") or 0.0) + offset_sec, 4))
            clip["sync"] = {
                "method": method,
                "offset_sec": offset_sec,
                "confidence": max(0.0, min(1.0, confidence)),
                "applied_at": _utc_now_iso(),
                "reference_path": reference_path,
                "source": source,
            }
            sync_groups = state.setdefault("sync_groups", [])
            source_path = str(clip.get("source_path") or "")
            existing = next((entry for entry in sync_groups if str(entry.get("source_path") or "") == source_path), None)
            entry = {
                "group_id": str(op.get("group_id") or f"sync_{uuid4().hex[:8]}"),
                "source_path": source_path,
                "reference_path": reference_path or source_path,
                "method": method,
                "offset_sec": offset_sec,
                "confidence": max(0.0, min(1.0, confidence)),
                "applied_at": _utc_now_iso(),
            }
            if existing is not None:
                existing.update(entry)
            else:
                sync_groups.append(entry)
            applied_ops.append(
                {
                    "op": op_type,
                    "clip_id": clip_id,
                    "offset_sec": offset_sec,
                    "method": method,
                    "reference_path": reference_path,
                    "source": source,
                }
            )
            continue

        # MARKER_173.2 — ripple_delete: remove clip, shift subsequent clips left
        if op_type == "ripple_delete":
            clip_id = str(op.get("clip_id") or "")
            source_lane, clip = _find_clip(state, clip_id)
            if source_lane is None or clip is None:
                raise ValueError(f"clip not found: {clip_id}")
            clip_start = float(clip.get("start_sec") or 0.0)
            clip_dur = float(clip.get("duration_sec") or 0.0)
            gap = clip_dur
            # Remove the clip
            source_lane["clips"] = [c for c in source_lane.get("clips", []) if str(c.get("clip_id") or "") != clip_id]
            # Shift all subsequent clips left by the gap
            for c in source_lane.get("clips", []):
                c_start = float(c.get("start_sec") or 0.0)
                if c_start > clip_start:
                    c["start_sec"] = max(0.0, round(c_start - gap, 4))
            source_lane["clips"] = sorted(source_lane["clips"], key=lambda c: float(c.get("start_sec") or 0.0))
            applied_ops.append({"op": op_type, "clip_id": clip_id, "lane_id": str(source_lane.get("lane_id") or ""), "gap_sec": gap})
            continue

        # MARKER_173.2 — insert_at: insert clip at timecode, push subsequent clips right
        if op_type == "insert_at":
            lane_id = str(op.get("lane_id") or "")
            start_sec = float(op.get("start_sec"))
            source_path = str(op.get("source_path") or "")
            duration_sec = float(op.get("duration_sec") or 0.0)
            clip_id = str(op.get("clip_id") or f"clip_{uuid4().hex[:8]}")
            if start_sec < 0:
                raise ValueError("start_sec must be >= 0")
            if duration_sec <= 0:
                raise ValueError("duration_sec must be > 0")
            target_lane = _find_lane(state, lane_id)
            if target_lane is None:
                raise ValueError(f"lane not found: {lane_id}")
            # Push subsequent clips right
            for c in target_lane.get("clips", []):
                c_start = float(c.get("start_sec") or 0.0)
                if c_start >= start_sec:
                    c["start_sec"] = round(c_start + duration_sec, 4)
            # Insert new clip
            new_clip = {
                "clip_id": clip_id,
                "source_path": source_path,
                "start_sec": start_sec,
                "duration_sec": duration_sec,
            }
            target_lane.setdefault("clips", []).append(new_clip)
            target_lane["clips"] = sorted(target_lane["clips"], key=lambda c: float(c.get("start_sec") or 0.0))
            applied_ops.append({
                "op": op_type, "clip_id": clip_id, "lane_id": lane_id,
                "start_sec": start_sec, "duration_sec": duration_sec, "source_path": source_path,
            })
            continue

        # MARKER_173.2 — overwrite_at: place clip at timecode, no shift
        if op_type == "overwrite_at":
            lane_id = str(op.get("lane_id") or "")
            start_sec = float(op.get("start_sec"))
            source_path = str(op.get("source_path") or "")
            duration_sec = float(op.get("duration_sec") or 0.0)
            clip_id = str(op.get("clip_id") or f"clip_{uuid4().hex[:8]}")
            if start_sec < 0:
                raise ValueError("start_sec must be >= 0")
            if duration_sec <= 0:
                raise ValueError("duration_sec must be > 0")
            target_lane = _find_lane(state, lane_id)
            if target_lane is None:
                raise ValueError(f"lane not found: {lane_id}")
            end_sec = start_sec + duration_sec
            # Remove any clips fully within the overwrite range
            target_lane["clips"] = [
                c for c in target_lane.get("clips", [])
                if not (float(c.get("start_sec") or 0.0) >= start_sec
                        and float(c.get("start_sec") or 0.0) + float(c.get("duration_sec") or 0.0) <= end_sec)
            ]
            new_clip = {
                "clip_id": clip_id,
                "source_path": source_path,
                "start_sec": start_sec,
                "duration_sec": duration_sec,
            }
            target_lane.setdefault("clips", []).append(new_clip)
            target_lane["clips"] = sorted(target_lane["clips"], key=lambda c: float(c.get("start_sec") or 0.0))
            applied_ops.append({
                "op": op_type, "clip_id": clip_id, "lane_id": lane_id,
                "start_sec": start_sec, "duration_sec": duration_sec, "source_path": source_path,
            })
            continue

        # MARKER_173.2 — split_at: split a clip at a given time into two clips
        if op_type == "split_at":
            clip_id = str(op.get("clip_id") or "")
            split_sec = float(op.get("split_sec"))
            source_lane, clip = _find_clip(state, clip_id)
            if source_lane is None or clip is None:
                raise ValueError(f"clip not found: {clip_id}")
            clip_start = float(clip.get("start_sec") or 0.0)
            clip_dur = float(clip.get("duration_sec") or 0.0)
            clip_end = clip_start + clip_dur
            if split_sec <= clip_start or split_sec >= clip_end:
                raise ValueError(
                    f"split_sec {split_sec} must be within clip range ({clip_start}, {clip_end})"
                )
            # Create two clips from one
            left_dur = round(split_sec - clip_start, 4)
            right_dur = round(clip_end - split_sec, 4)
            right_id = f"{clip_id}_R{uuid4().hex[:4]}"

            # Modify original clip to be the left half
            clip["duration_sec"] = left_dur

            # Create right half
            right_clip = {
                "clip_id": right_id,
                "source_path": str(clip.get("source_path") or ""),
                "start_sec": split_sec,
                "duration_sec": right_dur,
            }
            # Copy optional fields
            if "in_point_sec" in clip:
                in_point = float(clip.get("in_point_sec") or 0.0)
                clip_in = in_point
                right_clip["in_point_sec"] = round(in_point + left_dur, 4)
            if "sync" in clip:
                right_clip["sync"] = dict(clip["sync"])

            source_lane.setdefault("clips", []).append(right_clip)
            source_lane["clips"] = sorted(source_lane["clips"], key=lambda c: float(c.get("start_sec") or 0.0))
            applied_ops.append({
                "op": op_type, "clip_id": clip_id, "split_sec": split_sec,
                "left_id": clip_id, "right_id": right_id,
                "left_duration": left_dur, "right_duration": right_dur,
            })
            continue

        raise ValueError(f"unsupported timeline op: {op_type or '<empty>'}")

    state["revision"] = int(state.get("revision") or 0) + 1
    state["updated_at"] = _utc_now_iso()
    return state, applied_ops


def _find_scene_graph_node(scene_graph: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    for node in scene_graph.get("nodes", []):
        if str(node.get("node_id") or "") == str(node_id):
            return node
    return None


def _apply_scene_graph_ops(scene_graph: dict[str, Any], ops: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    graph = deepcopy(scene_graph)
    applied_ops: list[dict[str, Any]] = []

    for raw_op in ops:
        op = dict(raw_op or {})
        op_type = str(op.get("op") or "").strip()

        if op_type == "add_note":
            label = str(op.get("label") or "").strip()
            if not label:
                raise ValueError("label is required for add_note")
            note_id = str(op.get("node_id") or f"note_{uuid4().hex[:8]}")
            if _find_scene_graph_node(graph, note_id) is not None:
                raise ValueError(f"node already exists: {note_id}")
            metadata = dict(op.get("metadata") or {})
            text = str(op.get("text") or "").strip()
            if text:
                metadata["text"] = text
            target_node_id = str(op.get("target_node_id") or "").strip()
            note_node = {
                "node_id": note_id,
                "node_type": SCENE_GRAPH_NODE_NOTE,
                "label": label,
                "record_ref": None,
                "metadata": metadata,
            }
            graph.setdefault("nodes", []).append(note_node)
            applied: dict[str, Any] = {"op": op_type, "node_id": note_id, "label": label}
            if target_node_id:
                target_node = _find_scene_graph_node(graph, target_node_id)
                if target_node is None:
                    raise ValueError(f"target node not found: {target_node_id}")
                edge = {
                    "edge_id": f"edge_note_ref_{uuid4().hex[:8]}",
                    "edge_type": SCENE_GRAPH_EDGE_REFERENCES,
                    "source": note_id,
                    "target": target_node_id,
                    "weight": 1.0,
                }
                graph.setdefault("edges", []).append(edge)
                applied["target_node_id"] = target_node_id
                applied["edge_id"] = edge["edge_id"]
            applied_ops.append(applied)
            continue

        if op_type == "add_edge":
            edge_type = str(op.get("edge_type") or "").strip()
            if edge_type not in SCENE_GRAPH_EDGE_TYPE_SET:
                raise ValueError(f"unsupported edge_type: {edge_type or '<empty>'}")
            source = str(op.get("source") or "").strip()
            target = str(op.get("target") or "").strip()
            if not source or not target:
                raise ValueError("source and target are required for add_edge")
            if _find_scene_graph_node(graph, source) is None:
                raise ValueError(f"source node not found: {source}")
            if _find_scene_graph_node(graph, target) is None:
                raise ValueError(f"target node not found: {target}")
            weight = float(op.get("weight", 1.0))
            if weight < 0 or weight > 1:
                raise ValueError("weight must be between 0 and 1")
            edge = {
                "edge_id": str(op.get("edge_id") or f"edge_{uuid4().hex[:8]}"),
                "edge_type": edge_type,
                "source": source,
                "target": target,
                "weight": weight,
            }
            graph.setdefault("edges", []).append(edge)
            applied_ops.append({"op": op_type, **edge})
            continue

        if op_type == "rename_node":
            node_id = str(op.get("node_id") or "").strip()
            label = str(op.get("label") or "").strip()
            if not node_id or not label:
                raise ValueError("node_id and label are required for rename_node")
            node = _find_scene_graph_node(graph, node_id)
            if node is None:
                raise ValueError(f"node not found: {node_id}")
            node["label"] = label
            applied_ops.append({"op": op_type, "node_id": node_id, "label": label})
            continue

        raise ValueError(f"unsupported scene graph op: {op_type or '<empty>'}")

    graph["revision"] = int(graph.get("revision") or 0) + 1
    graph["updated_at"] = _utc_now_iso()
    return graph, applied_ops


def _discover_worker_media_files(source_root: str, limit: int) -> list[str]:
    media_ext = {
        ".mp4",
        ".mov",
        ".m4v",
        ".avi",
        ".mkv",
        ".webm",
        ".mp3",
        ".wav",
        ".m4a",
        ".aac",
        ".flac",
        ".ogg",
    }
    if not os.path.isdir(source_root):
        return []
    paths: list[str] = []
    for entry in sorted(os.scandir(source_root), key=lambda item: item.name.lower()):
        if not entry.is_file():
            continue
        if os.path.splitext(entry.name)[1].lower() not in media_ext:
            continue
        paths.append(entry.path)
        if len(paths) >= limit:
            break
    return paths


def _build_waveform_proxy_from_bytes(path: str, bins: int) -> tuple[list[float], bool, str]:
    try:
        with open(path, "rb") as f:
            data = f.read(8192)
    except Exception as exc:
        return ([0.0] * bins, True, f"read_failed:{str(exc)[:48]}")
    if not data:
        return ([0.0] * bins, True, "empty_file")
    chunk_size = max(1, len(data) // bins)
    values: list[float] = []
    for index in range(bins):
        chunk = data[index * chunk_size : (index + 1) * chunk_size]
        if not chunk:
            values.append(0.0)
            continue
        avg = sum(abs(byte - 128) for byte in chunk) / (len(chunk) * 128.0)
        values.append(round(max(0.0, min(1.0, avg)), 4))
    return (values, False, "")


def _build_signal_proxy_from_bytes(path: str, sample_bytes: int) -> tuple[list[float], bool, str]:
    try:
        with open(path, "rb") as f:
            data = f.read(sample_bytes)
    except Exception as exc:
        return ([], True, f"read_failed:{str(exc)[:48]}")
    if not data:
        return ([], True, "empty_file")
    signal = [round((byte - 128) / 128.0, 6) for byte in data]
    return (signal, False, "")


def _sidecar_timecode_info(path: str) -> tuple[str | None, int | None]:
    sidecar = f"{path}.timecode.json"
    if not os.path.isfile(sidecar):
        return (None, None)
    try:
        with open(sidecar, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        return (None, None)
    if not isinstance(payload, dict):
        return (None, None)
    value = str(payload.get("start_tc") or payload.get("timecode") or "").strip()
    fps = int(payload.get("fps") or 0) or None
    return (value or None, fps)


def _extract_timecode_from_path(path: str, default_fps: int) -> tuple[str | None, int]:
    sidecar_value, sidecar_fps = _sidecar_timecode_info(path)
    if sidecar_value:
        return sidecar_value, int(sidecar_fps or default_fps)
    name = os.path.basename(path)
    match = re.search(r"(?:tc|timecode)[_-]?(\d{2})[:._-](\d{2})[:._-](\d{2})[:._-](\d{2})", name, re.IGNORECASE)
    if not match:
        return None, int(default_fps)
    hh, mm, ss, ff = match.groups()
    return f"{hh}:{mm}:{ss}:{ff}", int(default_fps)


def _timecode_to_seconds(value: str, fps: int) -> float | None:
    parts = re.split(r"[:]", str(value or "").strip())
    if len(parts) != 4:
        return None
    try:
        hh, mm, ss, ff = [int(part) for part in parts]
    except ValueError:
        return None
    return (hh * 3600) + (mm * 60) + ss + (ff / max(1, fps))


def _pick_audio_sync_media_paths(source_root: str, limit: int) -> list[str]:
    candidates = _discover_worker_media_files(source_root, limit * 2)
    preferred_audio_ext = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}
    audio_paths = [path for path in candidates if os.path.splitext(path)[1].lower() in preferred_audio_ext]
    if len(audio_paths) >= 2:
        return audio_paths[:limit]
    return candidates[:limit]


def _pick_timecode_sync_media_paths(source_root: str, limit: int) -> list[str]:
    return _discover_worker_media_files(source_root, limit)


def _find_active_duplicate_job(
    *,
    job_type: str,
    project_id: str,
    sandbox_root: str,
) -> dict[str, Any] | None:
    store = get_cut_mcp_job_store()
    for job in store.list_jobs():
        if str(job.get("job_type") or "") != str(job_type):
            continue
        if str(job.get("state") or "") not in _ACTIVE_JOB_STATES:
            continue
        input_payload = job.get("input") or {}
        if str(input_payload.get("project_id") or "") != str(project_id):
            continue
        if str(input_payload.get("sandbox_root") or "") != str(sandbox_root):
            continue
        return job
    return None


def _count_active_background_jobs_for_sandbox(sandbox_root: str) -> int:
    store = get_cut_mcp_job_store()
    count = 0
    for job in store.list_jobs():
        if str(job.get("state") or "") not in _ACTIVE_JOB_STATES:
            continue
        if str(job.get("route_mode") or "") != "background":
            continue
        input_payload = job.get("input") or {}
        if str(input_payload.get("sandbox_root") or "") != str(sandbox_root):
            continue
        count += 1
    return count


def _collect_project_jobs(*, project_id: str, sandbox_root: str, limit: int = 8) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    jobs: list[dict[str, Any]] = []
    for job in get_cut_mcp_job_store().list_jobs():
        input_payload = job.get("input") or {}
        if str(input_payload.get("project_id") or "") != str(project_id):
            continue
        if str(input_payload.get("sandbox_root") or "") != str(sandbox_root):
            continue
        jobs.append(job)
    jobs = sorted(jobs, key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""), reverse=True)
    active_jobs = [job for job in jobs if str(job.get("state") or "") in _ACTIVE_JOB_STATES]
    return jobs[:limit], active_jobs


def _compute_time_marker_ranking_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    kind_counts = {kind: 0 for kind in ("favorite", "comment", "cam", "insight", "chat")}
    media_scores: dict[str, float] = {}
    active_count = 0
    for item in items:
        if str(item.get("status") or "active") != "active":
            continue
        active_count += 1
        kind = str(item.get("kind") or "")
        if kind in kind_counts:
            kind_counts[kind] += 1
        media_path = str(item.get("media_path") or "")
        media_scores[media_path] = float(media_scores.get(media_path, 0.0)) + float(item.get("score") or 0.0)
    top_media = [
        {"media_path": media_path, "score": round(score, 4)}
        for media_path, score in sorted(media_scores.items(), key=lambda item: (-item[1], item[0]))[:8]
    ]
    return {
        "total_markers": len(items),
        "active_markers": active_count,
        "kind_counts": kind_counts,
        "top_media": top_media,
    }


def _build_sync_surface(
    *,
    project_id: str,
    timecode_sync_result: dict[str, Any] | None,
    audio_sync_result: dict[str, Any] | None,
    meta_sync_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    by_source: dict[str, dict[str, Any]] = {}

    def _ensure_item(source_path: str, reference_path: str) -> dict[str, Any]:
        item = by_source.get(source_path)
        if item is None:
            item = {
                "item_id": f"sync_surface_{len(by_source) + 1:04d}",
                "source_path": source_path,
                "reference_path": reference_path,
                "timecode": None,
                "waveform": None,
                "meta_sync": None,
                "recommended_method": None,
                "recommended_offset_sec": 0.0,
                "confidence": 0.0,
            }
            by_source[source_path] = item
        return item

    for entry in (timecode_sync_result or {}).get("items", []):
        source_path = str(entry.get("source_path") or "")
        reference_path = str(entry.get("reference_path") or "")
        if not source_path:
            continue
        item = _ensure_item(source_path, reference_path)
        item["timecode"] = dict(entry)
        item["recommended_method"] = "timecode"
        item["recommended_offset_sec"] = float(entry.get("detected_offset_sec") or 0.0)
        item["confidence"] = float(entry.get("confidence") or 0.0)

    for entry in (audio_sync_result or {}).get("items", []):
        source_path = str(entry.get("source_path") or "")
        reference_path = str(entry.get("reference_path") or "")
        if not source_path:
            continue
        item = _ensure_item(source_path, reference_path)
        item["waveform"] = dict(entry)
        if item["timecode"] is None:
            item["recommended_method"] = "waveform"
            item["recommended_offset_sec"] = float(entry.get("detected_offset_sec") or 0.0)
            item["confidence"] = float(entry.get("confidence") or 0.0)

    for entry in (meta_sync_result or {}).get("items", []):
        source_path = str(entry.get("source_path") or "")
        reference_path = str(entry.get("reference_path") or "")
        if not source_path:
            continue
        item = _ensure_item(source_path, reference_path)
        item["meta_sync"] = dict(entry)
        if item["timecode"] is None and item["waveform"] is None:
            item["recommended_method"] = "meta_sync"
            item["recommended_offset_sec"] = float(entry.get("suggested_offset_sec") or 0.0)
            item["confidence"] = float(entry.get("confidence") or 0.0)

    return {
        "schema_version": "cut_sync_surface_v1",
        "project_id": str(project_id),
        "items": list(by_source.values()),
        "generated_at": _utc_now_iso(),
    }


def _build_music_cue_summary(
    *,
    bootstrap_state: dict[str, Any] | None,
    music_sync_result: dict[str, Any] | None,
) -> dict[str, Any] | None:
    profile = (bootstrap_state or {}).get("profile") if isinstance(bootstrap_state, dict) else None
    profile = profile if isinstance(profile, dict) else {}
    music_track = profile.get("music_track") if isinstance(profile.get("music_track"), dict) else {}
    music_path = str((music_sync_result or {}).get("music_path") or music_track.get("path") or "")
    if not music_path:
        return None

    cue_points = [cue for cue in (music_sync_result or {}).get("cue_points", []) if isinstance(cue, dict)]
    phrases = [phrase for phrase in (music_sync_result or {}).get("phrases", []) if isinstance(phrase, dict)]
    downbeats = [value for value in (music_sync_result or {}).get("downbeats", []) if isinstance(value, (int, float))]
    tempo = (music_sync_result or {}).get("tempo") if isinstance((music_sync_result or {}).get("tempo"), dict) else {}
    track_label = str(music_track.get("relative_path") or os.path.basename(music_path) or music_path)
    top_cues = [
        {
            "cue_id": str(cue.get("cue_id") or ""),
            "label": str(cue.get("label") or ""),
            "start_sec": float(cue.get("start_sec") or 0.0),
            "cue_type": str(cue.get("cue_type") or ""),
            "confidence": float(cue.get("confidence") or 0.0),
        }
        for cue in sorted(
            cue_points,
            key=lambda item: (-float(item.get("confidence") or 0.0), float(item.get("start_sec") or 0.0)),
        )[:3]
    ]
    return {
        "schema_version": "cut_music_cue_summary_v1",
        "track_label": track_label,
        "music_path": music_path,
        "primary_candidate": True,
        "cue_point_count": len(cue_points),
        "phrase_count": len(phrases),
        "downbeat_count": len(downbeats),
        "tempo_bpm": float(tempo.get("bpm") or 0.0) if tempo else None,
        "tempo_confidence": float(tempo.get("confidence") or 0.0) if tempo else None,
        "top_cues": top_cues,
    }


def _resolve_music_sync_path(
    *,
    store: CutProjectStore,
    project: dict[str, Any],
    requested_path: str,
) -> tuple[str, str]:
    source_root = str(project.get("source_path") or "")

    def _normalize_candidate(raw: str) -> str:
        value = str(raw or "").strip()
        if not value:
            return ""
        if not os.path.isabs(value):
            value = os.path.join(source_root, value)
        return os.path.realpath(os.path.abspath(value))

    bootstrap_state = store.load_bootstrap_state()
    profile = (bootstrap_state or {}).get("profile") if isinstance(bootstrap_state, dict) else None
    profile = profile if isinstance(profile, dict) else {}
    music_track = profile.get("music_track") if isinstance(profile.get("music_track"), dict) else {}

    candidates: list[tuple[int, str, str]] = []
    explicit_path = _normalize_candidate(requested_path)
    if explicit_path:
        candidates.append((10, explicit_path, "request_path"))
    profile_path = _normalize_candidate(str(music_track.get("path") or music_track.get("relative_path") or ""))
    if profile_path:
        candidates.append((9, profile_path, "bootstrap_profile"))

    for path in _pick_audio_sync_media_paths(source_root, 12):
        name = os.path.basename(path).lower()
        score = 3 if any(token in name for token in ("punch", "music", "song", "score", "ost")) else 1
        candidates.append((score, os.path.realpath(path), "source_autodiscovery"))

    for _, path, reason in sorted(candidates, key=lambda item: (-item[0], item[1])):
        if os.path.isfile(path):
            return path, reason
    return "", "music_track_missing"


def _build_music_peak_times_from_signal(
    signal: list[float],
    *,
    sample_rate: int,
    frame_ms: int = 20,
) -> tuple[list[float], list[float]]:
    envelope = build_energy_envelope(signal, sample_rate, frame_ms=frame_ms)
    if not envelope:
        return [], []
    mean_value = sum(envelope) / max(1, len(envelope))
    variance = sum((value - mean_value) ** 2 for value in envelope) / max(1, len(envelope))
    std_value = math.sqrt(max(0.0, variance))
    threshold = max(0.08, mean_value + std_value * 0.45)
    frame_sec = frame_ms / 1000.0
    min_gap_frames = max(1, int(0.24 / max(frame_sec, 1e-6)))

    peaks: list[float] = []
    last_peak_idx = -min_gap_frames
    for idx in range(1, len(envelope) - 1):
        current = float(envelope[idx])
        if current < threshold:
            continue
        if current < float(envelope[idx - 1]) or current < float(envelope[idx + 1]):
            continue
        if idx - last_peak_idx < min_gap_frames:
            continue
        peaks.append(round(idx * frame_sec, 4))
        last_peak_idx = idx

    if not peaks:
        ranked = sorted(envelope, reverse=True)[: min(8, len(envelope))]
        if ranked:
            fallback_threshold = ranked[-1]
            peaks = [
                round(idx * frame_sec, 4)
                for idx, value in enumerate(envelope)
                if value >= fallback_threshold
            ][:8]
    return peaks, envelope


def _normalize_tempo_candidate(raw_bpm: float, bpm_hint: float | None) -> float:
    bpm = float(raw_bpm or 0.0)
    if bpm <= 0.0:
        return 0.0
    while bpm < 60.0:
        bpm *= 2.0
    while bpm > 180.0:
        bpm /= 2.0
    if bpm_hint is not None and bpm_hint > 0.0:
        candidates = [bpm / 4.0, bpm / 2.0, bpm, bpm * 2.0, bpm * 4.0]
        valid = [value for value in candidates if 40.0 <= value <= 240.0]
        if valid:
            bpm = min(valid, key=lambda value: abs(value - float(bpm_hint)))
    return round(max(40.0, min(240.0, bpm)), 3)


def _estimate_bpm_from_peak_times(peak_times: list[float], bpm_hint: float | None) -> tuple[float, float]:
    intervals = [
        float(peak_times[idx + 1] - peak_times[idx])
        for idx in range(len(peak_times) - 1)
        if 0.18 <= float(peak_times[idx + 1] - peak_times[idx]) <= 1.5
    ]
    if not intervals:
        fallback_bpm = _normalize_tempo_candidate(float(bpm_hint or 120.0), bpm_hint)
        fallback_confidence = 0.52 if bpm_hint is not None else 0.24
        return fallback_bpm, round(fallback_confidence, 3)

    ordered = sorted(intervals)
    median_interval = ordered[len(ordered) // 2]
    bpm = _normalize_tempo_candidate(60.0 / max(median_interval, 1e-6), bpm_hint)
    mean_interval = sum(intervals) / len(intervals)
    variance = sum((value - mean_interval) ** 2 for value in intervals) / len(intervals)
    cv = math.sqrt(max(0.0, variance)) / max(mean_interval, 1e-6)
    regularity = max(0.0, min(1.0, 1.0 - cv))
    coverage = max(0.0, min(1.0, len(intervals) / 24.0))
    confidence = max(0.18, min(0.97, 0.55 * regularity + 0.45 * coverage))
    return bpm, round(confidence, 3)


def _build_music_phrases(anchors: list[float], duration_sec: float) -> list[dict[str, Any]]:
    if duration_sec <= 0.0:
        return []
    clean = [round(max(0.0, float(value)), 4) for value in anchors if isinstance(value, (int, float))]
    clean = sorted({value for value in clean if value < duration_sec})
    if not clean or clean[0] > 0.001:
        clean.insert(0, 0.0)
    if clean[-1] < duration_sec:
        clean.append(round(duration_sec, 4))
    labels = ["Intro", "Lift", "Drive", "Break", "Push", "Finale", "Outro"]
    phrases: list[dict[str, Any]] = []
    for index in range(len(clean) - 1):
        start_sec = float(clean[index])
        end_sec = float(clean[index + 1])
        if end_sec - start_sec < 0.12:
            continue
        phrases.append(
            {
                "phrase_id": f"phrase_{index + 1:02d}",
                "start_sec": round(start_sec, 4),
                "end_sec": round(end_sec, 4),
                "label": labels[index % len(labels)],
                "energy": round(min(0.98, 0.58 + (0.07 * (index % 5))), 3),
            }
        )
    return phrases


def _build_music_cues(
    *,
    downbeats: list[float],
    envelope: list[float],
    duration_sec: float,
    tempo_bpm: float,
) -> list[dict[str, Any]]:
    if duration_sec <= 0.0:
        return []

    def _energy_at(time_sec: float) -> float:
        if not envelope:
            return 0.6
        idx = int((time_sec / max(duration_sec, 1e-6)) * max(0, len(envelope) - 1))
        idx = max(0, min(len(envelope) - 1, idx))
        peak = max(envelope) or 1.0
        return max(0.0, min(1.0, float(envelope[idx]) / peak))

    beat_period = 60.0 / max(float(tempo_bpm or 120.0), 1.0)
    selected: list[tuple[int, float, str]] = []
    for beat_index, time_sec in enumerate(downbeats):
        cue_type = ""
        energy = _energy_at(time_sec)
        if beat_index == 0:
            cue_type = "intro"
        elif beat_index % 8 == 0:
            cue_type = "phrase_turn"
        elif energy >= 0.78:
            cue_type = "drop"
        elif beat_index % 4 == 0:
            cue_type = "accent"
        if cue_type:
            selected.append((beat_index, float(time_sec), cue_type))

    if len(selected) < 2:
        for beat_index, time_sec in enumerate(downbeats[1:], start=1):
            if len(selected) >= 3:
                break
            selected.append((beat_index, float(time_sec), "accent"))

    label_map = {
        "intro": "Intro anchor",
        "phrase_turn": "Phrase turn",
        "drop": "Drop lead",
        "accent": "Accent hit",
    }
    cues: list[dict[str, Any]] = []
    for cue_index, (beat_index, time_sec, cue_type) in enumerate(selected[:8], start=1):
        energy = _energy_at(time_sec)
        confidence = max(0.45, min(0.98, 0.45 + energy * 0.45))
        cues.append(
            {
                "cue_id": f"cue_{cue_index:02d}",
                "start_sec": round(time_sec, 4),
                "end_sec": round(min(duration_sec, time_sec + max(0.18, beat_period * 0.35)), 4),
                "label": label_map.get(cue_type, "Music cue"),
                "cue_type": cue_type,
                "confidence": round(confidence, 3),
                "energy": round(max(0.2, energy), 3),
            }
        )
    return cues


def _analyze_music_track_fallback(
    *,
    path: str,
    bpm_hint: float | None,
    max_analysis_sec: int,
) -> dict[str, Any]:
    sample_rate = 1000
    sample_bytes = max(4096, min(262144, int(max_analysis_sec) * sample_rate))
    signal, degraded_mode, degraded_reason = _build_signal_proxy_from_bytes(path, sample_bytes)
    if not signal:
        bpm = _normalize_tempo_candidate(float(bpm_hint or 120.0), bpm_hint)
        return {
            "tempo_bpm": bpm,
            "tempo_confidence": 0.12,
            "downbeats": [0.0],
            "phrases": _build_music_phrases([0.0], 1.0),
            "cue_points": [
                {
                    "cue_id": "cue_01",
                    "start_sec": 0.0,
                    "end_sec": 0.2,
                    "label": "Intro anchor",
                    "cue_type": "intro",
                    "confidence": 0.3,
                    "energy": 0.3,
                }
            ],
            "derived_from": "music_sync_proxy_v1",
            "degraded_mode": True,
            "degraded_reason": degraded_reason or "signal_proxy_unavailable",
        }

    duration_sec = max(0.2, len(signal) / sample_rate)
    peak_times, envelope = _build_music_peak_times_from_signal(signal, sample_rate=sample_rate)
    tempo_bpm, tempo_confidence = _estimate_bpm_from_peak_times(peak_times, bpm_hint)
    beat_period = 60.0 / max(tempo_bpm, 1.0)
    if len(peak_times) < 4:
        peak_times = [
            round(step * beat_period, 4)
            for step in range(max(4, int(duration_sec / max(beat_period, 1e-6)) + 1))
            if (step * beat_period) < duration_sec
        ]
    downbeats = [round(value, 4) for idx, value in enumerate(peak_times) if idx % 4 == 0]
    if not downbeats:
        downbeats = [0.0]
    phrase_anchors = [value for idx, value in enumerate(downbeats) if idx % 2 == 0]
    phrases = _build_music_phrases(phrase_anchors, duration_sec)
    cue_points = _build_music_cues(
        downbeats=downbeats,
        envelope=envelope,
        duration_sec=duration_sec,
        tempo_bpm=tempo_bpm,
    )
    return {
        "tempo_bpm": tempo_bpm,
        "tempo_confidence": tempo_confidence,
        "downbeats": downbeats,
        "phrases": phrases,
        "cue_points": cue_points,
        "derived_from": "music_sync_proxy_v1",
        "degraded_mode": bool(degraded_mode),
        "degraded_reason": degraded_reason,
    }


def _try_native_music_sync_analysis(
    *,
    path: str,
    bpm_hint: float | None,
    max_analysis_sec: int,
) -> dict[str, Any]:
    try:
        import librosa  # type: ignore
        import numpy as np  # type: ignore
    except Exception as exc:
        return {"ok": False, "reason": f"native_deps_unavailable:{exc.__class__.__name__}"}

    try:
        y, sr = librosa.load(str(path), sr=22050, mono=True, duration=max_analysis_sec)
        if y is None or len(y) < int(sr * 0.8):
            return {"ok": False, "reason": "audio_too_short"}
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        tempo, beat_frames = librosa.beat.beat_track(
            onset_envelope=onset_env,
            sr=sr,
            start_bpm=float(bpm_hint or 120.0),
        )
        beat_times = [round(float(value), 4) for value in librosa.frames_to_time(beat_frames, sr=sr)]
        tempo_raw = float(np.asarray(tempo).reshape(-1)[0]) if np.asarray(tempo).size > 0 else 0.0
        tempo_bpm, tempo_confidence = _estimate_bpm_from_peak_times(beat_times, bpm_hint)
        if tempo_raw > 0.0:
            tempo_bpm = _normalize_tempo_candidate(tempo_raw, bpm_hint)
            tempo_confidence = min(0.98, max(tempo_confidence, 0.74))
        duration_sec = float(len(y) / max(1, sr))
        peak = float(np.max(onset_env)) if np.asarray(onset_env).size else 1.0
        envelope = [
            max(0.0, min(1.0, round(float(value) / max(peak, 1e-6), 4)))
            for value in np.asarray(onset_env).reshape(-1).tolist()
        ]
        downbeats = [round(value, 4) for idx, value in enumerate(beat_times) if idx % 4 == 0] or ([0.0] if beat_times else [])
        phrase_anchors = [value for idx, value in enumerate(downbeats) if idx % 2 == 0]
        phrases = _build_music_phrases(phrase_anchors, duration_sec)
        cue_points = _build_music_cues(
            downbeats=downbeats or beat_times,
            envelope=envelope,
            duration_sec=duration_sec,
            tempo_bpm=tempo_bpm,
        )
        return {
            "ok": True,
            "tempo_bpm": tempo_bpm,
            "tempo_confidence": tempo_confidence,
            "downbeats": downbeats or [0.0],
            "phrases": phrases,
            "cue_points": cue_points,
            "derived_from": "music_sync_native_v1",
            "degraded_mode": False,
            "degraded_reason": "",
        }
    except Exception as exc:
        return {"ok": False, "reason": f"native_runtime_error:{exc.__class__.__name__}"}


def _lookup_pulse_manifest_entry(path: str) -> dict[str, Any] | None:
    manifest_path = Path(__file__).resolve().parents[4] / "pulse" / "data" / "processed" / "jepa_training_manifest.jsonl"
    if not manifest_path.is_file():
        return None
    target_path = os.path.realpath(path)
    target_name = os.path.basename(target_path)
    try:
        with manifest_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    payload = json.loads(line)
                except Exception:
                    continue
                if not isinstance(payload, dict):
                    continue
                manifest_file = os.path.realpath(str(payload.get("path") or ""))
                if manifest_file == target_path or os.path.basename(manifest_file) == target_name:
                    return payload
    except Exception:
        return None
    return None


def _analyze_music_track(
    *,
    path: str,
    bpm_hint: float | None,
    max_analysis_sec: int,
) -> dict[str, Any]:
    manifest_entry = _lookup_pulse_manifest_entry(path)
    manifest_bpm = float((manifest_entry or {}).get("bpm_ref") or 0.0)
    native = _try_native_music_sync_analysis(path=path, bpm_hint=bpm_hint, max_analysis_sec=max_analysis_sec)
    if native.get("ok") is True:
        native.pop("ok", None)
        if manifest_bpm > 0.0:
            native["tempo_bpm"] = round(manifest_bpm, 3)
            native["tempo_confidence"] = max(float(native.get("tempo_confidence") or 0.0), 0.94)
            native["derived_from"] = "pulse_manifest_v1+native_audio_v1"
        return native
    fallback = _analyze_music_track_fallback(path=path, bpm_hint=bpm_hint, max_analysis_sec=max_analysis_sec)
    reason = str(native.get("reason") or "")
    if reason:
        fallback["degraded_mode"] = True
        fallback["degraded_reason"] = reason
    if manifest_bpm > 0.0:
        fallback["tempo_bpm"] = round(manifest_bpm, 3)
        fallback["tempo_confidence"] = max(float(fallback.get("tempo_confidence") or 0.0), 0.96)
        fallback["derived_from"] = "pulse_manifest_v1"
    return fallback


def _estimate_scene_target_bpm_from_timeline(
    timeline_state: dict[str, Any] | None,
    *,
    music_tempo_bpm: float | None,
) -> dict[str, Any]:
    lanes = (timeline_state or {}).get("lanes") if isinstance((timeline_state or {}).get("lanes"), list) else []
    video_clips: list[dict[str, Any]] = []
    for lane in lanes:
        if not isinstance(lane, dict):
            continue
        lane_type = str(lane.get("lane_type") or "")
        if "audio" in lane_type:
            continue
        for clip in lane.get("clips", []):
            if isinstance(clip, dict):
                video_clips.append(clip)
    if not video_clips:
        fallback_bpm = round(max(72.0, min(168.0, float(music_tempo_bpm or 96.0))))
        return {
            "target_bpm": fallback_bpm,
            "rhythm_profile": "steady",
            "cut_density_per_min": 0.0,
            "source_engine": "pulse_scene_fallback_v1",
        }

    ordered = sorted(video_clips, key=lambda clip: float(clip.get("start_sec") or 0.0))
    durations: list[float] = []
    total_duration = 0.0
    for index, clip in enumerate(ordered):
        start_sec = float(clip.get("start_sec") or 0.0)
        end_value = clip.get("end_sec")
        if isinstance(end_value, (int, float)):
            end_sec = float(end_value)
        elif isinstance(clip.get("duration_sec"), (int, float)):
            end_sec = start_sec + float(clip.get("duration_sec") or 0.0)
        elif index + 1 < len(ordered):
            end_sec = float(ordered[index + 1].get("start_sec") or start_sec + 2.0)
        else:
            end_sec = start_sec + 2.5
        duration = max(0.1, end_sec - start_sec)
        durations.append(duration)
        total_duration = max(total_duration, end_sec)

    cut_count = max(0, len(ordered) - 1)
    cut_density_per_min = (cut_count / max(total_duration, 1e-6)) * 60.0
    mean_duration = sum(durations) / max(1, len(durations))
    variance = sum((value - mean_duration) ** 2 for value in durations) / max(1, len(durations))
    duration_cv = math.sqrt(max(0.0, variance)) / max(mean_duration, 1e-6)
    motion_volatility = max(0.0, min(1.0, duration_cv))
    if cut_density_per_min > 28.0:
        rhythm_profile = "aggressive"
    elif cut_density_per_min > 16.0:
        rhythm_profile = "dynamic"
    else:
        rhythm_profile = "steady"
    target_bpm = int(max(72, min(168, round(78 + cut_density_per_min * 1.6 + motion_volatility * 22.0))))
    return {
        "target_bpm": target_bpm,
        "rhythm_profile": rhythm_profile,
        "cut_density_per_min": round(cut_density_per_min, 2),
        "source_engine": "pulse_scene_proxy_v1",
    }


def _build_rhythm_surface(
    *,
    project_id: str,
    music_sync_result: dict[str, Any] | None,
    timeline_state: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(music_sync_result, dict):
        return None

    music_path = str(music_sync_result.get("music_path") or "")
    tempo = music_sync_result.get("tempo") if isinstance(music_sync_result.get("tempo"), dict) else {}
    music_tempo_bpm = float(tempo.get("bpm") or 0.0) if tempo else 0.0
    scene_binding = _estimate_scene_target_bpm_from_timeline(
        timeline_state,
        music_tempo_bpm=music_tempo_bpm or None,
    )
    target_bpm = float(scene_binding.get("target_bpm") or 0.0)
    bpm_delta = round(target_bpm - music_tempo_bpm, 3) if music_tempo_bpm > 0.0 and target_bpm > 0.0 else None
    cue_points = [cue for cue in music_sync_result.get("cue_points", []) if isinstance(cue, dict)]
    downbeats = [float(value) for value in music_sync_result.get("downbeats", []) if isinstance(value, (int, float))]

    items: list[dict[str, Any]] = []
    recommendation_map = {
        "drop": "accent_cut",
        "phrase_turn": "phrase_bridge",
        "accent": "micro_hit",
        "intro": "establish",
        "downbeat": "downbeat_lock",
    }
    for index, cue in enumerate(cue_points[:24], start=1):
        cue_type = str(cue.get("cue_type") or "accent")
        items.append(
            {
                "item_id": f"rhythm_{index:04d}",
                "start_sec": round(float(cue.get("start_sec") or 0.0), 4),
                "end_sec": round(float(cue.get("end_sec") or cue.get("start_sec") or 0.0), 4),
                "label": str(cue.get("label") or "Music cue"),
                "cue_type": cue_type,
                "confidence": round(float(cue.get("confidence") or 0.0), 3),
                "energy": round(float(cue.get("energy") or 0.0), 3),
                "target_bpm": target_bpm or None,
                "music_bpm": music_tempo_bpm or None,
                "bpm_delta": bpm_delta,
                "recommendation": recommendation_map.get(cue_type, "accent_cut"),
            }
        )
    if not items:
        for index, time_sec in enumerate(downbeats[:12], start=1):
            items.append(
                {
                    "item_id": f"rhythm_{index:04d}",
                    "start_sec": round(float(time_sec), 4),
                    "end_sec": round(float(time_sec), 4),
                    "label": f"Downbeat {index}",
                    "cue_type": "downbeat",
                    "confidence": 0.55,
                    "energy": 0.5,
                    "target_bpm": target_bpm or None,
                    "music_bpm": music_tempo_bpm or None,
                    "bpm_delta": bpm_delta,
                    "recommendation": "downbeat_lock",
                }
            )

    return {
        "schema_version": "cut_rhythm_surface_v1",
        "project_id": str(project_id),
        "music_path": music_path,
        "music_tempo_bpm": music_tempo_bpm or None,
        "scene_target_bpm": target_bpm or None,
        "bpm_delta": bpm_delta,
        "rhythm_profile": str(scene_binding.get("rhythm_profile") or "steady"),
        "cut_density_per_min": float(scene_binding.get("cut_density_per_min") or 0.0),
        "source_engine": str(scene_binding.get("source_engine") or "pulse_scene_fallback_v1"),
        "items": items,
        "generated_at": _utc_now_iso(),
    }


def _run_audio_sync_method(
    method: str,
    reference_signal: list[float],
    candidate_signal: list[float],
    sample_rate: int,
) -> Any:
    if method == "peak_only":
        return detect_peak_offset(reference_signal, candidate_signal, sample_rate)
    if method == "correlation":
        return detect_offset_via_correlation(reference_signal, candidate_signal, sample_rate)
    return detect_offset_hybrid(reference_signal, candidate_signal, sample_rate)


def _build_slice_windows_from_signal(
    signal: list[float],
    *,
    frame_ms: int,
    silence_threshold: float,
    min_silence_ms: int,
    keep_silence_ms: int,
) -> list[dict[str, Any]]:
    windows = derive_pause_windows_from_silence(
        signal,
        1000,
        frame_ms=frame_ms,
        silence_threshold=silence_threshold,
        min_silence_ms=min_silence_ms,
        keep_silence_ms=keep_silence_ms,
    )
    return [
        {
            "start_sec": float(window.start_sec),
            "end_sec": float(window.end_sec),
            "duration_sec": round(float(window.end_sec) - float(window.start_sec), 4),
            "confidence": float(window.confidence),
            "method": str(window.method),
        }
        for window in windows
    ]


def _build_time_marker(body: CutTimeMarkerApplyRequest, project_id: str, timeline_id: str) -> dict[str, Any]:
    if body.end_sec < body.start_sec:
        raise ValueError("end_sec must be >= start_sec")
    media_path = str(body.media_path or "").strip()
    if not media_path:
        raise ValueError("media_path is required for marker creation")
    anchor_sec = body.anchor_sec
    if anchor_sec is not None and (anchor_sec < body.start_sec or anchor_sec > body.end_sec):
        raise ValueError("anchor_sec must be inside [start_sec, end_sec]")
    now = _utc_now_iso()
    return {
        "marker_id": str(body.marker_id or f"marker_{uuid4().hex[:12]}"),
        "schema_version": "cut_time_marker_v1",
        "project_id": str(project_id),
        "timeline_id": str(timeline_id),
        "media_path": media_path,
        "kind": str(body.kind),
        "start_sec": float(body.start_sec),
        "end_sec": float(body.end_sec),
        "anchor_sec": anchor_sec,
        "score": float(body.score),
        "label": str(body.label or ""),
        "text": str(body.text or ""),
        "author": str(body.author or "cut_mcp"),
        "context_slice": deepcopy(body.context_slice) if body.context_slice is not None else None,
        "cam_payload": deepcopy(body.cam_payload) if body.cam_payload is not None else None,
        "chat_thread_id": body.chat_thread_id,
        "comment_thread_id": body.comment_thread_id,
        "source_engine": str(body.source_engine or "cut_mcp"),
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }


PRODUCTION_VIDEO_FORMATS = {
    "camera_codecs": ["H.264", "H.265/HEVC", "ProRes 422/4444", "DNxHD/DNxHR", "RED R3D", "BRAW"],
    "containers": ["MOV", "MP4", "MXF", "AVI", "MKV"],
    "audio": ["WAV", "AIFF", "MP3", "AAC", "FLAC", "M4A"],
    "images": ["JPEG", "PNG", "TIFF", "EXR", "DPX", "BMP"],
    "documents": ["MD", "TXT", "PDF", "SRT", "VTT"],
    "projects": ["FCP XML", "AAF", "EDL", "OTIO"],
    "resolutions": ["SD", "HD", "FHD", "2K", "4K", "6K", "8K"],
    "frame_rates": [23.976, 24, 25, 29.97, 30, 48, 50, 59.94, 60, 120],
}

NATIVE_VIDEO_EXT = {"mp4", "m4v", "webm", "ogg", "mov"}
PROXY_RECOMMENDED_EXT = {"mxf", "r3d", "braw", "avi", "mkv", "mts", "m2ts", "dpx", "exr"}


def _resolve_asset_path(path: str, sandbox_root: str = "") -> Path:
    p = Path(str(path or "").strip())
    if p.is_absolute():
        return p
    if sandbox_root:
        return (Path(sandbox_root) / p).resolve()
    return p.resolve()


def _probe_ffprobe_metadata(path: Path) -> dict[str, Any]:
    ffprobe_bin = shutil.which("ffprobe")
    if not ffprobe_bin:
        return {"available": False, "error": "ffprobe_not_found"}
    if not path.exists():
        return {"available": True, "error": "file_not_found"}
    try:
        proc = subprocess.run(
            [
                ffprobe_bin,
                "-v",
                "error",
                "-show_entries",
                "stream=index,codec_name,codec_type,width,height,avg_frame_rate,r_frame_rate,pix_fmt,channels,sample_rate:format=format_name,duration,bit_rate",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if proc.returncode != 0:
            return {"available": True, "error": f"ffprobe_failed: {proc.stderr.strip() or proc.returncode}"}
        payload = json.loads(proc.stdout or "{}")
        return {"available": True, "metadata": payload}
    except Exception as exc:
        return {"available": True, "error": f"ffprobe_exception: {exc}"}


def _collect_export_material(
    *,
    store: CutProjectStore,
    project_id: str,
    timeline_id: str,
    include_archived_markers: bool,
) -> dict[str, Any]:
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(project_id):
        raise HTTPException(status_code=404, detail="CUT project not found")

    timeline = store.load_timeline_state()
    if timeline is None:
        raise HTTPException(status_code=404, detail="CUT timeline state not found")
    resolved_timeline_id = str(timeline.get("timeline_id") or "main")
    if timeline_id and str(timeline_id) != resolved_timeline_id:
        raise HTTPException(status_code=404, detail="CUT timeline not found")

    clips: list[dict[str, Any]] = []
    duration_sec = 0.0
    for lane in timeline.get("lanes", []) or []:
        for clip in lane.get("clips", []) or []:
            start_sec = float(clip.get("start_sec") or 0.0)
            clip_duration = max(0.0, float(clip.get("duration_sec") or 0.0))
            end_sec = start_sec + clip_duration
            duration_sec = max(duration_sec, end_sec)
            clips.append(
                {
                    "clip_id": str(clip.get("clip_id") or ""),
                    "name": str(Path(str(clip.get("source_path") or "")).name or clip.get("clip_id") or "clip"),
                    "source_path": str(clip.get("source_path") or ""),
                    "lane_id": str(lane.get("lane_id") or ""),
                    "start_sec": start_sec,
                    "end_sec": end_sec,
                    "duration_sec": clip_duration,
                }
            )

    marker_bundle = store.load_time_marker_bundle() or {}
    raw_items = list(marker_bundle.get("items") or [])
    markers: list[dict[str, Any]] = []
    for item in raw_items:
        status = str(item.get("status") or "active")
        if status != "active" and not include_archived_markers:
            continue
        markers.append(
            {
                "marker_id": str(item.get("marker_id") or ""),
                "media_path": str(item.get("media_path") or ""),
                "time_sec": float(item.get("anchor_sec") if item.get("anchor_sec") is not None else item.get("start_sec") or 0.0),
                "start_sec": float(item.get("start_sec") or 0.0),
                "end_sec": float(item.get("end_sec") or item.get("start_sec") or 0.0),
                "kind": str(item.get("kind") or "comment"),
                "comment": str(item.get("text") or item.get("label") or ""),
                "color": str(item.get("kind") or "comment"),
                "comment_thread_id": str(item.get("comment_thread_id") or ""),
            }
        )

    return {
        "project": project,
        "timeline": timeline,
        "clips": clips,
        "markers": markers,
        "duration_sec": duration_sec,
    }


def _build_otio_export(project_name: str, sequence_name: str, clips: list[dict[str, Any]], fps: int) -> dict[str, Any]:
    track_children = []
    for clip in clips:
        start = float(clip.get("start_sec") or 0.0)
        dur = float(clip.get("duration_sec") or 0.0)
        track_children.append(
            {
                "OTIO_SCHEMA": "Clip.2",
                "name": str(clip.get("name") or "clip"),
                "source_range": {
                    "OTIO_SCHEMA": "TimeRange.1",
                    "start_time": {"OTIO_SCHEMA": "RationalTime.1", "value": 0, "rate": fps},
                    "duration": {"OTIO_SCHEMA": "RationalTime.1", "value": round(dur * fps), "rate": fps},
                },
                "metadata": {
                    "vetka": {
                        "source_path": str(clip.get("source_path") or ""),
                        "timeline_start_sec": start,
                    }
                },
            }
        )
    return {
        "OTIO_SCHEMA": "Timeline.1",
        "name": sequence_name,
        "metadata": {"project_name": project_name},
        "tracks": {
            "OTIO_SCHEMA": "Stack.1",
            "children": [
                {
                    "OTIO_SCHEMA": "Track.1",
                    "name": "V1",
                    "kind": "Video",
                    "children": track_children,
                }
            ],
        },
    }


def _build_edl_export(sequence_name: str, clips: list[dict[str, Any]], fps: int) -> str:
    def tc(sec: float) -> str:
        total_frames = max(0, int(round(sec * fps)))
        hh = total_frames // (fps * 3600)
        mm = (total_frames // (fps * 60)) % 60
        ss = (total_frames // fps) % 60
        ff = total_frames % fps
        return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"

    lines = [f"TITLE: {sequence_name}", "FCM: NON-DROP FRAME"]
    for idx, clip in enumerate(clips, start=1):
        start = float(clip.get("start_sec") or 0.0)
        end = float(clip.get("end_sec") or start)
        name = str(clip.get("name") or f"clip_{idx}")
        event = f"{idx:03d}  AX       V     C        00:00:00:00 {tc(end-start)} {tc(start)} {tc(end)}"
        lines.append(event)
        lines.append(f"* FROM CLIP NAME: {name}")
    return "\n".join(lines) + "\n"


def _srt_ts(sec: float) -> str:
    total_ms = max(0, int(round(sec * 1000)))
    hh = total_ms // 3_600_000
    mm = (total_ms // 60_000) % 60
    ss = (total_ms // 1_000) % 60
    ms = total_ms % 1_000
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


def _serialize_srt_marker(index: int, marker: dict[str, Any]) -> str:
    start_sec = float(marker.get("start_sec") or marker.get("time_sec") or 0.0)
    end_sec = max(start_sec, float(marker.get("end_sec") or start_sec + 1.0))
    meta = {
        "kind": str(marker.get("kind") or "comment"),
        "marker_id": str(marker.get("marker_id") or ""),
        "media_path": str(marker.get("media_path") or ""),
        "comment_thread_id": str(marker.get("comment_thread_id") or ""),
    }
    meta_text = json.dumps(meta, ensure_ascii=False, separators=(",", ":"))
    comment = str(marker.get("comment") or "")
    return f"{index}\n{_srt_ts(start_sec)} --> {_srt_ts(end_sec)}\n{{{meta_text}}} {comment}\n"


def _extract_marker_meta_from_srt(text: str) -> tuple[dict[str, Any], str]:
    line = str(text or "").strip()
    if not line.startswith("{"):
        return {}, line
    try:
        end = line.index("}")
        raw_meta = line[1:end]
        meta = json.loads(raw_meta)
        note = line[end + 1 :].strip()
        return (meta if isinstance(meta, dict) else {}), note
    except Exception:
        return {}, line


def _social_presets_manifest() -> dict[str, Any]:
    return {
        "youtube": {"aspect_ratio": "16:9", "recommended": {"codec": "H.264", "resolution": "1920x1080"}, "extras": ["chapters_from_markers", "thumbnail_from_favorite"]},
        "instagram_reels": {"aspect_ratio": "9:16", "recommended": {"codec": "H.264", "resolution": "1080x1920"}},
        "instagram_feed_1x1": {"aspect_ratio": "1:1", "recommended": {"codec": "H.264", "resolution": "1080x1080"}},
        "instagram_feed_4x5": {"aspect_ratio": "4:5", "recommended": {"codec": "H.264", "resolution": "1080x1350"}},
        "tiktok": {"aspect_ratio": "9:16", "recommended": {"codec": "H.264", "resolution": "1080x1920"}},
        "telegram": {"aspect_ratio": "16:9|9:16", "recommended": {"codec": "H.264", "resolution": "1280x720"}},
        "vk": {"aspect_ratio": "16:9", "recommended": {"codec": "H.264", "resolution": "1920x1080"}},
        "x": {"aspect_ratio": "16:9|1:1", "recommended": {"codec": "H.264", "resolution": "1280x720"}},
    }


def _player_lab_marker_to_apply_request(
    payload: PlayerLabMarkerImportItem | PlayerLabProvisionalEventImportItem,
    *,
    sandbox_root: str,
    project_id: str,
    timeline_id: str,
    author: str,
) -> CutTimeMarkerApplyRequest:
    if isinstance(payload, PlayerLabMarkerImportItem):
        end_sec = max(float(payload.end_sec), float(payload.start_sec))
        anchor_sec = payload.anchor_sec
        if anchor_sec is None:
            anchor_sec = round((float(payload.start_sec) + end_sec) / 2.0, 4)
        return CutTimeMarkerApplyRequest(
            sandbox_root=sandbox_root,
            project_id=project_id,
            timeline_id=timeline_id,
            author=str(payload.author or author or "player_lab_import"),
            op="create",
            marker_id=str(payload.marker_id or ""),
            media_path=str(payload.media_path or ""),
            kind=payload.kind,
            start_sec=float(payload.start_sec),
            end_sec=end_sec,
            anchor_sec=anchor_sec,
            score=float(payload.score),
            label=str(payload.label or ""),
            text=str(payload.text or ""),
            context_slice=deepcopy(payload.context_slice) if payload.context_slice is not None else None,
            cam_payload=deepcopy(payload.cam_payload) if payload.cam_payload is not None else None,
            chat_thread_id=payload.chat_thread_id,
            comment_thread_id=payload.comment_thread_id,
            source_engine=str(payload.source_engine or "player_lab"),
        )

    end_sec = max(float(payload.end_sec), float(payload.start_sec))
    anchor_sec = round((float(payload.start_sec) + end_sec) / 2.0, 4)
    return CutTimeMarkerApplyRequest(
        sandbox_root=sandbox_root,
        project_id=project_id,
        timeline_id=timeline_id,
        author=str(author or "player_lab_import"),
        op="create",
        marker_id=str(payload.provisional_event_id or ""),
        media_path=str(payload.media_path or ""),
        kind="comment",
        start_sec=float(payload.start_sec),
        end_sec=end_sec,
        anchor_sec=anchor_sec,
        score=0.55,
        label="Player Lab capture",
        text=str(payload.text or payload.event_type or "Player Lab provisional event"),
        context_slice={
            "mode": "player_lab_provisional_v1",
            "event_type": str(payload.event_type or ""),
            "export_mode": str(payload.export_mode or ""),
            "migration_status": str(payload.migration_status or ""),
        },
        source_engine="player_lab_provisional",
    )



def _default_editorial_intent_for_marker(marker: dict[str, Any]) -> str:
    kind = str(marker.get("kind") or "")
    return {
        "favorite": "accent_cut",
        "comment": "commentary_hold",
        "cam": "camera_emphasis",
        "insight": "insight_emphasis",
        "chat": "dialogue_anchor",
    }.get(kind, "accent_cut")


def _build_montage_decision_from_marker(
    marker: dict[str, Any],
    *,
    marker_bundle_revision: int,
    decision_id: str,
    lane_id: str,
    decision_status: str,
    author: str,
    editorial_intent: str,
) -> dict[str, Any]:
    start_sec = float(marker.get("start_sec") or 0.0)
    end_sec = float(marker.get("end_sec") or start_sec)
    anchor_sec = marker.get("anchor_sec")
    if anchor_sec is None:
        anchor_sec = round((start_sec + end_sec) / 2.0, 4)
    now = _utc_now_iso()
    return {
        "decision_id": decision_id,
        "source_family": "marker",
        "cue_provenance_ids": [str(marker.get("marker_id") or "")],
        "confidence": float(marker.get("score") or 0.0),
        "score": float(marker.get("score") or 0.0),
        "editorial_intent": editorial_intent or _default_editorial_intent_for_marker(marker),
        "status": decision_status,
        "timeline_id": str(marker.get("timeline_id") or "main"),
        "lane_id": str(lane_id or "V1"),
        "anchor_sec": float(anchor_sec),
        "start_sec": start_sec,
        "end_sec": end_sec,
        "source_bundle_id": "time_marker_bundle",
        "source_bundle_revision": int(marker_bundle_revision),
        "created_at": now,
        "updated_at": now,
        "author": str(author or "cut_mcp"),
    }


def _execute_cut_bootstrap(body: CutBootstrapRequest) -> dict[str, Any]:
    source_path = str(body.source_path or "").strip()
    sandbox_root = str(body.sandbox_root or "").strip()
    if not source_path or not os.path.isabs(source_path) or not os.path.exists(source_path):
        return _bootstrap_error(
            "source_path_invalid",
            "Source path must be an existing absolute path.",
            degraded_reason="source_path_invalid",
        )
    if not sandbox_root or not os.path.isabs(sandbox_root):
        return _bootstrap_error(
            "sandbox_root_invalid",
            "Sandbox root must be an absolute path.",
            degraded_reason="sandbox_root_invalid",
        )

    store = CutProjectStore(sandbox_root)
    layout = store.sandbox_layout_status()

    # MARKER_181.3: Auto-create sandbox layout when create_project_if_missing is set
    if body.create_project_if_missing and (not layout["sandbox_exists"] or layout["missing_dirs"]):
        os.makedirs(store.paths.config_dir, exist_ok=True)
        os.makedirs(store.paths.runtime_dir, exist_ok=True)
        os.makedirs(store.paths.storage_dir, exist_ok=True)
        os.makedirs(store.paths.core_mirror_root, exist_ok=True)
        layout = store.sandbox_layout_status()

    if not layout["sandbox_exists"]:
        return _bootstrap_error(
            "sandbox_missing",
            "Sandbox root does not exist.",
            degraded_reason="sandbox_missing",
        )

    if layout["missing_dirs"]:
        return _bootstrap_error(
            "sandbox_missing_layout",
            "Sandbox layout is incomplete. Run CUT sandbox bootstrap first.",
            degraded_reason="sandbox_missing_layout",
        )

    # MARKER_181.3: Downgrade to non-mirror mode if manifest missing during auto-create
    use_core_mirror = body.use_core_mirror
    if use_core_mirror and not layout["manifest_exists"]:
        if body.create_project_if_missing:
            use_core_mirror = False
        else:
            return _bootstrap_error(
                "core_mirror_manifest_missing",
                "CUT core mirror manifest is missing from sandbox config.",
                degraded_reason="core_mirror_manifest_missing",
            )

    mode, project = store.resolve_create_or_open(source_path)
    if body.mode == "open_existing":
        if project is None:
            return _bootstrap_error(
                "project_not_found",
                "No existing CUT project found for this source and sandbox.",
                degraded_reason="project_not_found",
            )
        bootstrap_mode = "open_existing"
    elif body.mode == "create_new":
        if not body.create_project_if_missing:
            return _bootstrap_error(
                "project_creation_disabled",
                "Project creation is disabled for this bootstrap request.",
                degraded_reason="project_creation_disabled",
            )
        project = None
        bootstrap_mode = "create_new"
    else:
        bootstrap_mode = "open_existing" if mode == "open" else "create_new"

    if project is None:
        if not body.create_project_if_missing:
            return _bootstrap_error(
                "project_missing",
                "CUT project is missing and creation is disabled.",
                degraded_reason="project_missing",
            )
        project = store.create_project(
            source_path=source_path,
            display_name=body.project_name,
            bootstrap_profile=body.bootstrap_profile,
            use_core_mirror=use_core_mirror,
        )

    scan = quick_scan_cut_source(source_path, limit=body.quick_scan_limit)
    stats = scan["stats"]
    signals = scan["signals"]
    fallback_questions = build_cut_fallback_questions(signals, stats)
    profile_payload = build_cut_bootstrap_profile(
        source_path,
        body.bootstrap_profile,
        limit=body.quick_scan_limit,
    )
    media_count = int(stats.get("media_files", 0) or 0)
    estimated_ready_sec = round(max(1.0, min(30.0, 1.2 + media_count * 0.08)), 1)

    degraded_mode = False
    degraded_reason = ""
    if use_core_mirror and not layout["core_mirror_exists"]:
        degraded_mode = True
        degraded_reason = "core_mirror_missing"

    project["state"] = "degraded" if degraded_mode else "ready"
    project["bootstrap_profile"] = str(body.bootstrap_profile or project.get("bootstrap_profile") or "default")
    store.save_project(project)
    store.save_bootstrap_state(
        {
            "schema_version": "cut_bootstrap_state_v1",
            "project_id": str(project.get("project_id") or ""),
            "last_bootstrap_mode": bootstrap_mode,
            "last_source_path": str(project.get("source_path") or source_path),
            "last_stats": stats,
            "last_degraded_reason": degraded_reason,
            "last_job_id": "",
            "updated_at": str(project.get("last_opened_at") or ""),
            "profile": profile_payload,
        }
    )

    return {
        "success": True,
        "schema_version": "cut_bootstrap_v1",
        "project": project,
        "bootstrap": {
            "mode": bootstrap_mode if body.mode != "create_or_open" else body.mode,
            "state": "degraded" if degraded_mode else "ready",
            "use_core_mirror": bool(use_core_mirror),
            "core_mirror_root": store.paths.core_mirror_root,
            "estimated_ready_sec": estimated_ready_sec,
            "profile": profile_payload,
        },
        "stats": stats,
        "missing_inputs": {
            "script_or_treatment": not bool(signals.get("has_script_or_treatment")),
            "montage_sheet": not bool(signals.get("has_montage_sheet")),
            "transcript_or_timecodes": not bool(signals.get("has_transcript_or_timecodes")),
        },
        "fallback_questions": fallback_questions,
        "phases": [
            {"id": "discover", "label": "Scope discovery", "status": "done", "progress": 0.33},
            {"id": "project", "label": "Project bootstrap", "status": "done", "progress": 0.66},
            {"id": "align", "label": "Timeline bootstrap", "status": "ready", "progress": 1.0},
        ],
        "next_actions": [
            "open_cut_project",
            "poll_bootstrap_job",
            "start_scene_assembly",
        ],
        "degraded_mode": degraded_mode,
        "degraded_reason": degraded_reason,
    }


def _run_cut_bootstrap_job(job_id: str, body: CutBootstrapRequest) -> None:
    store = get_cut_mcp_job_store()
    store.update_job(job_id, state="running", progress=0.15)
    try:
        result = _execute_cut_bootstrap(body)
        terminal_state = "done" if bool(result.get("success")) else "error"
        store.update_job(job_id, state=terminal_state, progress=1.0, result=result)
    except Exception as exc:
        store.update_job(
            job_id,
            state="error",
            progress=1.0,
            error={
                "code": "bootstrap_exception",
                "message": str(exc),
                "recoverable": False,
            },
        )


def _run_cut_scene_assembly_job(job_id: str, body: CutSceneAssemblyRequest) -> None:
    job_store = get_cut_mcp_job_store()
    job_store.update_job(job_id, state="running", progress=0.2)
    try:
        store = CutProjectStore(body.sandbox_root)
        project = store.load_project()
        if project is None or str(project.get("project_id") or "") != str(body.project_id):
            job_store.update_job(
                job_id,
                state="error",
                progress=1.0,
                error={
                    "code": "project_not_found",
                    "message": "CUT project not found for scene assembly.",
                    "recoverable": True,
                },
            )
            return
        timeline_state = _build_initial_timeline_state(project, body.timeline_id)
        scene_graph = _build_initial_scene_graph(project, timeline_state, body.graph_id)
        store.save_timeline_state(timeline_state)
        store.save_scene_graph(scene_graph)
        job_store.update_job(
            job_id,
            state="done",
            progress=1.0,
            result={
                "success": True,
                "project_id": str(project.get("project_id") or ""),
                "timeline_state": timeline_state,
                "scene_graph": scene_graph,
            },
        )
    except Exception as exc:
        job_store.update_job(
            job_id,
            state="error",
            progress=1.0,
            error={
                "code": "scene_assembly_exception",
                "message": str(exc),
                "recoverable": False,
            },
        )


def _run_cut_waveform_build_job(job_id: str, body: CutWaveformBuildRequest) -> None:
    job_store = get_cut_mcp_job_store()
    job_store.update_job(job_id, state="running", progress=0.1)
    try:
        store = CutProjectStore(body.sandbox_root)
        project = store.load_project()
        if project is None or str(project.get("project_id") or "") != str(body.project_id):
            job_store.update_job(
                job_id,
                state="error",
                progress=1.0,
                error={
                    "code": "project_not_found",
                    "message": "CUT project not found for waveform build.",
                    "recoverable": True,
                },
            )
            return

        source_root = str(project.get("source_path") or "")
        media_paths = _discover_worker_media_files(source_root, int(body.limit))
        bundle_prev = store.load_waveform_bundle()
        revision = int((bundle_prev or {}).get("revision") or 0) + 1
        items: list[dict[str, Any]] = []
        degraded_count = 0

        if not media_paths:
            bundle = {
                "schema_version": "cut_waveform_bundle_v1",
                "project_id": str(project.get("project_id") or ""),
                "revision": revision,
                "items": [],
                "generated_at": _utc_now_iso(),
            }
            store.save_waveform_bundle(bundle)
            job_store.update_job(
                job_id,
                state="done",
                progress=1.0,
                degraded_mode=True,
                degraded_reason="no_media_files",
                result={
                    "success": True,
                    "worker_task": {
                        "schema_version": "cut_worker_task_v1",
                        "task_id": job_id,
                        "project_id": str(project.get("project_id") or ""),
                        "task_type": "waveform_build",
                        "route_mode": "background",
                        "priority": "normal",
                        "status": "done",
                        "input": {"bins": int(body.bins), "limit": int(body.limit)},
                        "output_ref": store.paths.waveform_bundle_path,
                        "degraded_mode": True,
                        "degraded_reason": "no_media_files",
                        "created_at": _utc_now_iso(),
                        "updated_at": _utc_now_iso(),
                    },
                    "waveform_bundle": bundle,
                },
            )
            return

        total = len(media_paths)
        for index, media_path in enumerate(media_paths, start=1):
            current_job = job_store.get_job(job_id)
            if current_job and bool(current_job.get("cancel_requested")):
                job_store.update_job(job_id, state="cancelled", progress=1.0)
                return
            bins, degraded_mode, degraded_reason = _build_waveform_proxy_from_bytes(media_path, int(body.bins))
            if degraded_mode:
                degraded_count += 1
            items.append(
                {
                    "item_id": f"waveform_{index:04d}",
                    "source_path": media_path,
                    "waveform_bins": bins,
                    "degraded_mode": degraded_mode,
                    "degraded_reason": degraded_reason,
                }
            )
            progress = 0.1 + (0.8 * index / total)
            job_store.update_job(job_id, progress=progress)

        bundle = {
            "schema_version": "cut_waveform_bundle_v1",
            "project_id": str(project.get("project_id") or ""),
            "revision": revision,
            "items": items,
            "generated_at": _utc_now_iso(),
        }
        store.save_waveform_bundle(bundle)
        degraded_mode = degraded_count > 0
        degraded_reason = "partial_waveform_proxy" if degraded_mode else ""
        worker_task = {
            "schema_version": "cut_worker_task_v1",
            "task_id": job_id,
            "project_id": str(project.get("project_id") or ""),
            "task_type": "waveform_build",
            "route_mode": "background",
            "priority": "normal",
            "status": "done",
            "input": {"bins": int(body.bins), "limit": int(body.limit)},
            "output_ref": store.paths.waveform_bundle_path,
            "degraded_mode": degraded_mode,
            "degraded_reason": degraded_reason,
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }
        job_store.update_job(
            job_id,
            state="done",
            progress=1.0,
            degraded_mode=degraded_mode,
            degraded_reason=degraded_reason,
            result={
                "success": True,
                "worker_task": worker_task,
                "waveform_bundle": bundle,
            },
        )
    except Exception as exc:
        job_store.update_job(
            job_id,
            state="error",
            progress=1.0,
            error={
                "code": "waveform_build_exception",
                "message": str(exc),
                "recoverable": False,
            },
        )


def _run_cut_transcript_normalize_job(job_id: str, body: CutTranscriptNormalizeRequest) -> None:
    job_store = get_cut_mcp_job_store()
    job_store.update_job(job_id, state="running", progress=0.1)
    try:
        store = CutProjectStore(body.sandbox_root)
        project = store.load_project()
        if project is None or str(project.get("project_id") or "") != str(body.project_id):
            job_store.update_job(
                job_id,
                state="error",
                progress=1.0,
                error={
                    "code": "project_not_found",
                    "message": "CUT project not found for transcript normalize.",
                    "recoverable": True,
                },
            )
            return

        source_root = str(project.get("source_path") or "")
        media_paths = _discover_worker_media_files(source_root, int(body.limit))
        bundle_prev = store.load_transcript_bundle()
        revision = int((bundle_prev or {}).get("revision") or 0) + 1
        items: list[dict[str, Any]] = []
        degraded_count = 0

        if not media_paths:
            bundle = {
                "schema_version": "cut_transcript_bundle_v1",
                "project_id": str(project.get("project_id") or ""),
                "revision": revision,
                "items": [],
                "generated_at": _utc_now_iso(),
            }
            store.save_transcript_bundle(bundle)
            job_store.update_job(
                job_id,
                state="done",
                progress=1.0,
                degraded_mode=True,
                degraded_reason="no_media_files",
                result={
                    "success": True,
                    "worker_task": {
                        "schema_version": "cut_worker_task_v1",
                        "task_id": job_id,
                        "project_id": str(project.get("project_id") or ""),
                        "task_type": "transcript_normalize",
                        "route_mode": "background",
                        "priority": "normal",
                        "status": "done",
                        "input": {
                            "limit": int(body.limit),
                            "segments_limit": int(body.segments_limit),
                            "max_transcribe_sec": body.max_transcribe_sec,
                        },
                        "output_ref": store.paths.transcript_bundle_path,
                        "degraded_mode": True,
                        "degraded_reason": "no_media_files",
                        "created_at": _utc_now_iso(),
                        "updated_at": _utc_now_iso(),
                    },
                    "transcript_bundle": bundle,
                },
            )
            return

        total = len(media_paths)
        request_context = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=None)))
        for index, media_path in enumerate(media_paths, start=1):
            current_job = job_store.get_job(job_id)
            if current_job and bool(current_job.get("cancel_requested")):
                job_store.update_job(job_id, state="cancelled", progress=1.0)
                return

            try:
                response = asyncio.run(
                    media_transcript_normalized(
                        MediaTranscriptNormalizeRequest(
                            path=media_path,
                            max_transcribe_sec=body.max_transcribe_sec,
                            segments_limit=int(body.segments_limit),
                        ),
                        request_context,
                    )
                )
                transcript_json = dict(response.get("transcript_normalized_json") or {})
                degraded_mode = bool(response.get("degraded_mode"))
                degraded_reason = str(response.get("degraded_reason") or "")
            except Exception as exc:
                transcript_json = {
                    "schema_version": "vetka_transcript_v1",
                    "path": media_path,
                    "modality": "",
                    "language": "",
                    "duration_sec": 0.0,
                    "source_engine": "none",
                    "text": "",
                    "segments": [],
                }
                degraded_mode = True
                degraded_reason = f"transcript_normalize_failed:{str(exc)[:80]}"

            if degraded_mode:
                degraded_count += 1
            items.append(
                {
                    "item_id": f"transcript_{index:04d}",
                    "source_path": media_path,
                    "transcript_normalized_json": transcript_json,
                    "degraded_mode": degraded_mode,
                    "degraded_reason": degraded_reason,
                }
            )
            progress = 0.1 + (0.8 * index / total)
            job_store.update_job(job_id, progress=progress)

        bundle = {
            "schema_version": "cut_transcript_bundle_v1",
            "project_id": str(project.get("project_id") or ""),
            "revision": revision,
            "items": items,
            "generated_at": _utc_now_iso(),
        }
        store.save_transcript_bundle(bundle)
        degraded_mode = degraded_count > 0
        degraded_reason = "partial_transcript_normalize" if degraded_mode else ""
        worker_task = {
            "schema_version": "cut_worker_task_v1",
            "task_id": job_id,
            "project_id": str(project.get("project_id") or ""),
            "task_type": "transcript_normalize",
            "route_mode": "background",
            "priority": "normal",
            "status": "done",
            "input": {
                "limit": int(body.limit),
                "segments_limit": int(body.segments_limit),
                "max_transcribe_sec": body.max_transcribe_sec,
            },
            "output_ref": store.paths.transcript_bundle_path,
            "degraded_mode": degraded_mode,
            "degraded_reason": degraded_reason,
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }
        job_store.update_job(
            job_id,
            state="done",
            progress=1.0,
            degraded_mode=degraded_mode,
            degraded_reason=degraded_reason,
            result={
                "success": True,
                "worker_task": worker_task,
                "transcript_bundle": bundle,
            },
        )
    except Exception as exc:
        job_store.update_job(
            job_id,
            state="error",
            progress=1.0,
            error={
                "code": "transcript_normalize_exception",
                "message": str(exc),
                "recoverable": False,
            },
        )


def _run_cut_thumbnail_build_job(job_id: str, body: CutThumbnailBuildRequest) -> None:
    job_store = get_cut_mcp_job_store()
    job_store.update_job(job_id, state="running", progress=0.1)
    try:
        store = CutProjectStore(body.sandbox_root)
        project = store.load_project()
        if project is None or str(project.get("project_id") or "") != str(body.project_id):
            job_store.update_job(
                job_id,
                state="error",
                progress=1.0,
                error={
                    "code": "project_not_found",
                    "message": "CUT project not found for thumbnail build.",
                    "recoverable": True,
                },
            )
            return

        source_root = str(project.get("source_path") or "")
        media_paths = _discover_worker_media_files(source_root, int(body.limit))
        bundle_prev = store.load_thumbnail_bundle()
        revision = int((bundle_prev or {}).get("revision") or 0) + 1
        items: list[dict[str, Any]] = []
        degraded_count = 0

        if not media_paths:
            bundle = {
                "schema_version": "cut_thumbnail_bundle_v1",
                "project_id": str(project.get("project_id") or ""),
                "revision": revision,
                "items": [],
                "generated_at": _utc_now_iso(),
            }
            store.save_thumbnail_bundle(bundle)
            job_store.update_job(
                job_id,
                state="done",
                progress=1.0,
                degraded_mode=True,
                degraded_reason="no_media_files",
                result={
                    "success": True,
                    "worker_task": {
                        "schema_version": "cut_worker_task_v1",
                        "task_id": job_id,
                        "project_id": str(project.get("project_id") or ""),
                        "task_type": "thumbnail_build",
                        "route_mode": "background",
                        "priority": "normal",
                        "status": "done",
                        "input": {
                            "limit": int(body.limit),
                            "waveform_bins": int(body.waveform_bins),
                            "preview_segments_limit": int(body.preview_segments_limit),
                        },
                        "output_ref": store.paths.thumbnail_bundle_path,
                        "degraded_mode": True,
                        "degraded_reason": "no_media_files",
                        "created_at": _utc_now_iso(),
                        "updated_at": _utc_now_iso(),
                    },
                    "thumbnail_bundle": bundle,
                },
            )
            return

        total = len(media_paths)
        request_context = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=None)))
        for index, media_path in enumerate(media_paths, start=1):
            current_job = job_store.get_job(job_id)
            if current_job and bool(current_job.get("cancel_requested")):
                job_store.update_job(job_id, state="cancelled", progress=1.0)
                return
            try:
                preview_payload = asyncio.run(
                    media_preview(
                        MediaPreviewRequest(
                            path=media_path,
                            waveform_bins=int(body.waveform_bins),
                            preview_segments_limit=int(body.preview_segments_limit),
                        ),
                        request_context,
                    )
                )
                preview_assets = preview_payload.get("preview_assets") or {}
                playback = preview_payload.get("playback") or {}
                degraded_mode = bool(preview_payload.get("degraded_mode"))
                degraded_reason = str(preview_payload.get("degraded_reason") or "")
                item = {
                    "item_id": f"thumbnail_{index:04d}",
                    "source_path": media_path,
                    "modality": str(preview_payload.get("modality") or "video"),
                    "duration_sec": float(preview_payload.get("duration_sec") or 0.0),
                    "poster_url": str(preview_assets.get("poster_url") or ""),
                    "animated_preview_url_300ms": str(preview_assets.get("animated_preview_url_300ms") or ""),
                    "source_url": str(playback.get("source_url") or ""),
                    "degraded_mode": degraded_mode,
                    "degraded_reason": degraded_reason,
                }
            except Exception as exc:
                degraded_mode = True
                degraded_reason = f"thumbnail_build_failed:{str(exc)[:80]}"
                item = {
                    "item_id": f"thumbnail_{index:04d}",
                    "source_path": media_path,
                    "modality": "video" if os.path.splitext(media_path)[1].lower() in {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"} else "audio",
                    "duration_sec": 0.0,
                    "poster_url": "",
                    "animated_preview_url_300ms": "",
                    "source_url": "",
                    "degraded_mode": True,
                    "degraded_reason": degraded_reason,
                }
            if degraded_mode:
                degraded_count += 1
            items.append(item)
            progress = 0.1 + (0.8 * index / total)
            job_store.update_job(job_id, progress=progress)

        bundle = {
            "schema_version": "cut_thumbnail_bundle_v1",
            "project_id": str(project.get("project_id") or ""),
            "revision": revision,
            "items": items,
            "generated_at": _utc_now_iso(),
        }
        store.save_thumbnail_bundle(bundle)
        degraded_mode = degraded_count > 0
        degraded_reason = "partial_thumbnail_build" if degraded_mode else ""
        worker_task = {
            "schema_version": "cut_worker_task_v1",
            "task_id": job_id,
            "project_id": str(project.get("project_id") or ""),
            "task_type": "thumbnail_build",
            "route_mode": "background",
            "priority": "normal",
            "status": "done",
            "input": {
                "limit": int(body.limit),
                "waveform_bins": int(body.waveform_bins),
                "preview_segments_limit": int(body.preview_segments_limit),
            },
            "output_ref": store.paths.thumbnail_bundle_path,
            "degraded_mode": degraded_mode,
            "degraded_reason": degraded_reason,
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }
        job_store.update_job(
            job_id,
            state="done",
            progress=1.0,
            degraded_mode=degraded_mode,
            degraded_reason=degraded_reason,
            result={
                "success": True,
                "worker_task": worker_task,
                "thumbnail_bundle": bundle,
            },
        )
    except Exception as exc:
        job_store.update_job(
            job_id,
            state="error",
            progress=1.0,
            error={
                "code": "thumbnail_build_exception",
                "message": str(exc),
                "recoverable": False,
            },
        )


def _run_cut_audio_sync_job(job_id: str, body: CutAudioSyncRequest) -> None:
    job_store = get_cut_mcp_job_store()
    job_store.update_job(job_id, state="running", progress=0.1)
    try:
        store = CutProjectStore(body.sandbox_root)
        project = store.load_project()
        if project is None or str(project.get("project_id") or "") != str(body.project_id):
            job_store.update_job(
                job_id,
                state="error",
                progress=1.0,
                error={
                    "code": "project_not_found",
                    "message": "CUT project not found for audio sync build.",
                    "recoverable": True,
                },
            )
            return

        source_root = str(project.get("source_path") or "")
        media_paths = _pick_audio_sync_media_paths(source_root, int(body.limit))
        result_prev = store.load_audio_sync_result()
        revision = int((result_prev or {}).get("revision") or 0) + 1
        items: list[dict[str, Any]] = []
        degraded_count = 0

        if len(media_paths) < 2:
            result = {
                "schema_version": "cut_audio_sync_result_v1",
                "project_id": str(project.get("project_id") or ""),
                "revision": revision,
                "items": [],
                "generated_at": _utc_now_iso(),
            }
            store.save_audio_sync_result(result)
            job_store.update_job(
                job_id,
                state="done",
                progress=1.0,
                degraded_mode=True,
                degraded_reason="insufficient_media_files",
                result={
                    "success": True,
                    "worker_task": {
                        "schema_version": "cut_worker_task_v1",
                        "task_id": job_id,
                        "project_id": str(project.get("project_id") or ""),
                        "task_type": "audio_sync",
                        "route_mode": "background",
                        "priority": "normal",
                        "status": "done",
                        "input": {
                            "limit": int(body.limit),
                            "sample_bytes": int(body.sample_bytes),
                            "method": str(body.method),
                        },
                        "output_ref": store.paths.audio_sync_result_path,
                        "degraded_mode": True,
                        "degraded_reason": "insufficient_media_files",
                        "created_at": _utc_now_iso(),
                        "updated_at": _utc_now_iso(),
                    },
                    "audio_sync_result": result,
                },
            )
            return

        reference_path = media_paths[0]
        reference_signal, reference_degraded, reference_reason = _build_signal_proxy_from_bytes(
            reference_path, int(body.sample_bytes)
        )
        if reference_degraded:
            degraded_count += 1

        total = max(1, len(media_paths) - 1)
        for index, media_path in enumerate(media_paths[1:], start=1):
            current_job = job_store.get_job(job_id)
            if current_job and bool(current_job.get("cancel_requested")):
                job_store.update_job(job_id, state="cancelled", progress=1.0)
                return
            candidate_signal, degraded_mode, degraded_reason = _build_signal_proxy_from_bytes(
                media_path, int(body.sample_bytes)
            )
            if reference_degraded or degraded_mode or not reference_signal or not candidate_signal:
                degraded_mode = True
                degraded_reason = degraded_reason or reference_reason or "signal_proxy_unavailable"
                sync_result = detect_offset_hybrid([], [], 1000)
            else:
                sync_result = _run_audio_sync_method(str(body.method), reference_signal, candidate_signal, 1000)
            if degraded_mode:
                degraded_count += 1
            items.append(
                {
                    "item_id": f"audio_sync_{index:04d}",
                    "reference_path": reference_path,
                    "source_path": media_path,
                    "detected_offset_sec": float(sync_result.detected_offset_sec),
                    "confidence": float(sync_result.confidence),
                    "method": str(sync_result.method),
                    "refinement_steps": 2 if "correlation" in str(sync_result.method) else 1,
                    "peak_value": float(sync_result.peak_value),
                    "degraded_mode": degraded_mode,
                    "degraded_reason": degraded_reason,
                }
            )
            progress = 0.1 + (0.8 * index / total)
            job_store.update_job(job_id, progress=progress)

        result = {
            "schema_version": "cut_audio_sync_result_v1",
            "project_id": str(project.get("project_id") or ""),
            "revision": revision,
            "items": items,
            "generated_at": _utc_now_iso(),
        }
        store.save_audio_sync_result(result)
        degraded_mode = degraded_count > 0
        degraded_reason = "partial_audio_sync" if degraded_mode else ""
        worker_task = {
            "schema_version": "cut_worker_task_v1",
            "task_id": job_id,
            "project_id": str(project.get("project_id") or ""),
            "task_type": "audio_sync",
            "route_mode": "background",
            "priority": "normal",
            "status": "done",
            "input": {
                "limit": int(body.limit),
                "sample_bytes": int(body.sample_bytes),
                "method": str(body.method),
            },
            "output_ref": store.paths.audio_sync_result_path,
            "degraded_mode": degraded_mode,
            "degraded_reason": degraded_reason,
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }
        job_store.update_job(
            job_id,
            state="done",
            progress=1.0,
            degraded_mode=degraded_mode,
            degraded_reason=degraded_reason,
            result={
                "success": True,
                "worker_task": worker_task,
                "audio_sync_result": result,
            },
        )
    except Exception as exc:
        job_store.update_job(
            job_id,
            state="error",
            progress=1.0,
            error={
                "code": "audio_sync_exception",
                "message": str(exc),
                "recoverable": False,
            },
        )


def _run_cut_music_sync_job(job_id: str, body: CutMusicSyncRequest) -> None:
    job_store = get_cut_mcp_job_store()
    job_store.update_job(job_id, state="running", progress=0.1)
    try:
        store = CutProjectStore(body.sandbox_root)
        project = store.load_project()
        if project is None or str(project.get("project_id") or "") != str(body.project_id):
            job_store.update_job(
                job_id,
                state="error",
                progress=1.0,
                error={
                    "code": "project_not_found",
                    "message": "CUT project not found for music sync build.",
                    "recoverable": True,
                },
            )
            return

        music_path, path_resolution = _resolve_music_sync_path(
            store=store,
            project=project,
            requested_path=body.music_path,
        )
        if not music_path:
            job_store.update_job(
                job_id,
                state="error",
                progress=1.0,
                error={
                    "code": "music_path_not_found",
                    "message": "No music track found for CUT music sync build.",
                    "recoverable": True,
                },
            )
            return
        if not os.path.isfile(music_path):
            job_store.update_job(
                job_id,
                state="error",
                progress=1.0,
                error={
                    "code": "music_path_missing",
                    "message": f"CUT music sync source is missing: {music_path}",
                    "recoverable": True,
                },
            )
            return

        current_job = job_store.get_job(job_id)
        if current_job and bool(current_job.get("cancel_requested")):
            job_store.update_job(job_id, state="cancelled", progress=1.0)
            return

        result_prev = store.load_music_sync_result()
        revision = int((result_prev or {}).get("revision") or 0) + 1
        analysis = _analyze_music_track(
            path=music_path,
            bpm_hint=body.bpm_hint,
            max_analysis_sec=int(body.max_analysis_sec),
        )
        job_store.update_job(job_id, progress=0.85)

        music_sync_result = {
            "schema_version": "cut_music_sync_result_v1",
            "project_id": str(project.get("project_id") or ""),
            "revision": revision,
            "music_path": music_path,
            "tempo": {
                "bpm": float(analysis.get("tempo_bpm") or 0.0),
                "confidence": float(analysis.get("tempo_confidence") or 0.0),
            },
            "downbeats": [round(float(value), 4) for value in analysis.get("downbeats", [])],
            "phrases": list(analysis.get("phrases", [])),
            "cue_points": list(analysis.get("cue_points", [])),
            "derived_from": str(analysis.get("derived_from") or "music_sync_proxy_v1"),
            "generated_at": _utc_now_iso(),
        }
        store.save_music_sync_result(music_sync_result)

        degraded_mode = bool(analysis.get("degraded_mode"))
        degraded_reason_parts = [str(analysis.get("degraded_reason") or "").strip(), str(path_resolution or "").strip()]
        degraded_reason = ",".join([part for part in degraded_reason_parts if part])
        worker_task = {
            "schema_version": "cut_worker_task_v1",
            "task_id": job_id,
            "project_id": str(project.get("project_id") or ""),
            "task_type": "music_sync",
            "route_mode": "background",
            "priority": "normal",
            "status": "done",
            "input": {
                "music_path": music_path,
                "bpm_hint": body.bpm_hint,
                "max_analysis_sec": int(body.max_analysis_sec),
            },
            "output_ref": store.paths.music_sync_result_path,
            "degraded_mode": degraded_mode,
            "degraded_reason": degraded_reason,
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }
        job_store.update_job(
            job_id,
            state="done",
            progress=1.0,
            degraded_mode=degraded_mode,
            degraded_reason=degraded_reason,
            result={
                "success": True,
                "worker_task": worker_task,
                "music_sync_result": music_sync_result,
            },
        )
    except Exception as exc:
        job_store.update_job(
            job_id,
            state="error",
            progress=1.0,
            error={
                "code": "music_sync_exception",
                "message": str(exc),
                "recoverable": False,
            },
        )


def _run_cut_pause_slice_job(job_id: str, body: CutPauseSliceRequest) -> None:
    job_store = get_cut_mcp_job_store()
    job_store.update_job(job_id, state="running", progress=0.1)
    try:
        store = CutProjectStore(body.sandbox_root)
        project = store.load_project()
        if project is None or str(project.get("project_id") or "") != str(body.project_id):
            job_store.update_job(
                job_id,
                state="error",
                progress=1.0,
                error={
                    "code": "project_not_found",
                    "message": "CUT project not found for pause slice build.",
                    "recoverable": True,
                },
            )
            return

        source_root = str(project.get("source_path") or "")
        media_paths = _pick_audio_sync_media_paths(source_root, int(body.limit))
        bundle_prev = store.load_slice_bundle()
        revision = int((bundle_prev or {}).get("revision") or 0) + 1
        items: list[dict[str, Any]] = []
        degraded_count = 0

        if not media_paths:
            bundle = {
                "schema_version": "cut_slice_bundle_v1",
                "project_id": str(project.get("project_id") or ""),
                "revision": revision,
                "items": [],
                "generated_at": _utc_now_iso(),
            }
            store.save_slice_bundle(bundle)
            job_store.update_job(
                job_id,
                state="done",
                progress=1.0,
                degraded_mode=True,
                degraded_reason="no_media_files",
                result={
                    "success": True,
                    "worker_task": {
                        "schema_version": "cut_worker_task_v1",
                        "task_id": job_id,
                        "project_id": str(project.get("project_id") or ""),
                        "task_type": "pause_slice",
                        "route_mode": "background",
                        "priority": "normal",
                        "status": "done",
                        "input": {
                            "limit": int(body.limit),
                            "sample_bytes": int(body.sample_bytes),
                            "frame_ms": int(body.frame_ms),
                            "silence_threshold": float(body.silence_threshold),
                            "min_silence_ms": int(body.min_silence_ms),
                            "keep_silence_ms": int(body.keep_silence_ms),
                        },
                        "output_ref": store.paths.slice_bundle_path,
                        "degraded_mode": True,
                        "degraded_reason": "no_media_files",
                        "created_at": _utc_now_iso(),
                        "updated_at": _utc_now_iso(),
                    },
                    "slice_bundle": bundle,
                },
            )
            return

        total = len(media_paths)
        for index, media_path in enumerate(media_paths, start=1):
            current_job = job_store.get_job(job_id)
            if current_job and bool(current_job.get("cancel_requested")):
                job_store.update_job(job_id, state="cancelled", progress=1.0)
                return
            signal, degraded_mode, degraded_reason = _build_signal_proxy_from_bytes(media_path, int(body.sample_bytes))
            if signal:
                windows = _build_slice_windows_from_signal(
                    signal,
                    frame_ms=int(body.frame_ms),
                    silence_threshold=float(body.silence_threshold),
                    min_silence_ms=int(body.min_silence_ms),
                    keep_silence_ms=int(body.keep_silence_ms),
                )
            else:
                windows = []
                degraded_mode = True
                degraded_reason = degraded_reason or "signal_proxy_unavailable"
            if degraded_mode:
                degraded_count += 1
            items.append(
                {
                    "item_id": f"slice_{index:04d}",
                    "source_path": media_path,
                    "method": "energy_pause_v1",
                    "windows": windows,
                    "degraded_mode": degraded_mode,
                    "degraded_reason": degraded_reason,
                }
            )
            progress = 0.1 + (0.8 * index / total)
            job_store.update_job(job_id, progress=progress)

        bundle = {
            "schema_version": "cut_slice_bundle_v1",
            "project_id": str(project.get("project_id") or ""),
            "revision": revision,
            "items": items,
            "generated_at": _utc_now_iso(),
        }
        store.save_slice_bundle(bundle)
        degraded_mode = degraded_count > 0
        degraded_reason = "partial_pause_slice" if degraded_mode else ""
        worker_task = {
            "schema_version": "cut_worker_task_v1",
            "task_id": job_id,
            "project_id": str(project.get("project_id") or ""),
            "task_type": "pause_slice",
            "route_mode": "background",
            "priority": "normal",
            "status": "done",
            "input": {
                "limit": int(body.limit),
                "sample_bytes": int(body.sample_bytes),
                "frame_ms": int(body.frame_ms),
                "silence_threshold": float(body.silence_threshold),
                "min_silence_ms": int(body.min_silence_ms),
                "keep_silence_ms": int(body.keep_silence_ms),
            },
            "output_ref": store.paths.slice_bundle_path,
            "degraded_mode": degraded_mode,
            "degraded_reason": degraded_reason,
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }
        job_store.update_job(
            job_id,
            state="done",
            progress=1.0,
            degraded_mode=degraded_mode,
            degraded_reason=degraded_reason,
            result={
                "success": True,
                "worker_task": worker_task,
                "slice_bundle": bundle,
            },
        )
    except Exception as exc:
        job_store.update_job(
            job_id,
            state="error",
            progress=1.0,
            error={
                "code": "pause_slice_exception",
                "message": str(exc),
                "recoverable": False,
            },
        )


def _run_cut_timecode_sync_job(job_id: str, body: CutTimecodeSyncRequest) -> None:
    job_store = get_cut_mcp_job_store()
    job_store.update_job(job_id, state="running", progress=0.1)
    try:
        store = CutProjectStore(body.sandbox_root)
        project = store.load_project()
        if project is None or str(project.get("project_id") or "") != str(body.project_id):
            job_store.update_job(
                job_id,
                state="error",
                progress=1.0,
                error={
                    "code": "project_not_found",
                    "message": "CUT project not found for timecode sync build.",
                    "recoverable": True,
                },
            )
            return

        source_root = str(project.get("source_path") or "")
        media_paths = _pick_timecode_sync_media_paths(source_root, int(body.limit))
        result_prev = store.load_timecode_sync_result()
        revision = int((result_prev or {}).get("revision") or 0) + 1
        items: list[dict[str, Any]] = []
        degraded_count = 0

        if len(media_paths) < 2:
            result = {
                "schema_version": "cut_timecode_sync_result_v1",
                "project_id": str(project.get("project_id") or ""),
                "revision": revision,
                "items": [],
                "generated_at": _utc_now_iso(),
            }
            store.save_timecode_sync_result(result)
            job_store.update_job(
                job_id,
                state="done",
                progress=1.0,
                degraded_mode=True,
                degraded_reason="insufficient_media_files",
                result={
                    "success": True,
                    "worker_task": {
                        "schema_version": "cut_worker_task_v1",
                        "task_id": job_id,
                        "project_id": str(project.get("project_id") or ""),
                        "task_type": "timecode_sync",
                        "route_mode": "background",
                        "priority": "normal",
                        "status": "done",
                        "input": {"limit": int(body.limit), "fps": int(body.fps)},
                        "output_ref": store.paths.timecode_sync_result_path,
                        "degraded_mode": True,
                        "degraded_reason": "insufficient_media_files",
                        "created_at": _utc_now_iso(),
                        "updated_at": _utc_now_iso(),
                    },
                    "timecode_sync_result": result,
                },
            )
            return

        reference_path = media_paths[0]
        reference_tc, reference_fps = _extract_timecode_from_path(reference_path, int(body.fps))
        reference_sec = _timecode_to_seconds(str(reference_tc or ""), int(reference_fps))
        total = max(1, len(media_paths) - 1)

        for index, media_path in enumerate(media_paths[1:], start=1):
            current_job = job_store.get_job(job_id)
            if current_job and bool(current_job.get("cancel_requested")):
                job_store.update_job(job_id, state="cancelled", progress=1.0)
                return
            source_tc, source_fps = _extract_timecode_from_path(media_path, int(body.fps))
            source_sec = _timecode_to_seconds(str(source_tc or ""), int(source_fps))
            degraded_mode = reference_sec is None or source_sec is None
            degraded_reason = "" if not degraded_mode else "timecode_missing"
            detected_offset_sec = 0.0 if degraded_mode else round(float(source_sec) - float(reference_sec), 4)
            items.append(
                {
                    "item_id": f"timecode_sync_{index:04d}",
                    "reference_path": reference_path,
                    "source_path": media_path,
                    "reference_timecode": reference_tc or "",
                    "source_timecode": source_tc or "",
                    "fps": int(source_fps or reference_fps or body.fps),
                    "detected_offset_sec": detected_offset_sec,
                    "confidence": 0.99 if not degraded_mode else 0.0,
                    "method": "timecode_v1",
                    "degraded_mode": degraded_mode,
                    "degraded_reason": degraded_reason,
                }
            )
            if degraded_mode:
                degraded_count += 1
            progress = 0.1 + (0.8 * index / total)
            job_store.update_job(job_id, progress=progress)

        result = {
            "schema_version": "cut_timecode_sync_result_v1",
            "project_id": str(project.get("project_id") or ""),
            "revision": revision,
            "items": items,
            "generated_at": _utc_now_iso(),
        }
        store.save_timecode_sync_result(result)
        degraded_mode = degraded_count > 0
        degraded_reason = "partial_timecode_sync" if degraded_mode else ""
        worker_task = {
            "schema_version": "cut_worker_task_v1",
            "task_id": job_id,
            "project_id": str(project.get("project_id") or ""),
            "task_type": "timecode_sync",
            "route_mode": "background",
            "priority": "normal",
            "status": "done",
            "input": {"limit": int(body.limit), "fps": int(body.fps)},
            "output_ref": store.paths.timecode_sync_result_path,
            "degraded_mode": degraded_mode,
            "degraded_reason": degraded_reason,
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }
        job_store.update_job(
            job_id,
            state="done",
            progress=1.0,
            degraded_mode=degraded_mode,
            degraded_reason=degraded_reason,
            result={
                "success": True,
                "worker_task": worker_task,
                "timecode_sync_result": result,
            },
        )
    except Exception as exc:
        job_store.update_job(
            job_id,
            state="error",
            progress=1.0,
            error={
                "code": "timecode_sync_exception",
                "message": str(exc),
                "recoverable": False,
            },
        )


@router.post("/bootstrap")
async def cut_bootstrap(body: CutBootstrapRequest) -> dict[str, Any]:
    """
    MARKER_170.MCP.BOOTSTRAP.FLOW_V1
    MARKER_170.MCP.BOOTSTRAP.CONTRACT_V1
    """
    return _execute_cut_bootstrap(body)


@router.post("/bootstrap-async")
async def cut_bootstrap_async(body: CutBootstrapRequest) -> dict[str, Any]:
    """
    MARKER_170.MCP.BOOTSTRAP_ASYNC_V1
    """
    store = get_cut_mcp_job_store()
    job = store.create_job(
        "bootstrap",
        {
            "source_path": str(body.source_path or ""),
            "sandbox_root": str(body.sandbox_root or ""),
            "mode": str(body.mode),
            "bootstrap_profile": str(body.bootstrap_profile or "default"),
        },
    )
    thread = threading.Thread(target=_run_cut_bootstrap_job, args=(str(job["job_id"]), body), daemon=True)
    thread.start()
    return {
        "success": True,
        "schema_version": "cut_mcp_job_v1",
        "job_id": str(job["job_id"]),
        "job": job,
    }


@router.post("/scene-assembly-async")
async def cut_scene_assembly_async(body: CutSceneAssemblyRequest) -> dict[str, Any]:
    """
    MARKER_170.MCP.SCENE_ASSEMBLY_ASYNC_V1
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _bootstrap_error(
            "project_not_found",
            "No existing CUT project found for this source and sandbox.",
            degraded_reason="project_not_found",
        )
    if _count_active_background_jobs_for_sandbox(str(body.sandbox_root)) >= _SANDBOX_BACKGROUND_LIMIT:
        return _worker_job_error(
            "worker_backpressure_limit",
            "CUT worker queue is saturated for this sandbox. Wait for active jobs to finish.",
        )
    duplicate_job = _find_active_duplicate_job(
        job_type="scene_assembly",
        project_id=str(body.project_id),
        sandbox_root=str(body.sandbox_root),
    )
    if duplicate_job is not None:
        return _worker_job_error(
            "duplicate_job_active",
            "A scene assembly job is already active for this CUT project.",
            existing_job=duplicate_job,
        )
    job_store = get_cut_mcp_job_store()
    job = job_store.create_job(
        "scene_assembly",
        {
            "project_id": str(body.project_id),
            "sandbox_root": str(body.sandbox_root),
            "timeline_id": str(body.timeline_id or "main"),
        },
    )
    bootstrap_state = store.load_bootstrap_state()
    if bootstrap_state is not None:
        bootstrap_state["last_job_id"] = str(job["job_id"])
        bootstrap_state["updated_at"] = _utc_now_iso()
        store.save_bootstrap_state(bootstrap_state)
    thread = threading.Thread(target=_run_cut_scene_assembly_job, args=(str(job["job_id"]), body), daemon=True)
    thread.start()
    return {
        "success": True,
        "schema_version": "cut_mcp_job_v1",
        "job_id": str(job["job_id"]),
        "job": job,
    }


@router.post("/worker/waveform-build-async")
async def cut_waveform_build_async(body: CutWaveformBuildRequest) -> dict[str, Any]:
    """
    MARKER_170.WORKER.MEDIA_SUBMCP
    MARKER_170.WORKER.DEGRADED_SAFE
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _worker_job_error("project_not_found", "CUT project not found for waveform worker task.")
    if _count_active_background_jobs_for_sandbox(str(body.sandbox_root)) >= _SANDBOX_BACKGROUND_LIMIT:
        return _worker_job_error(
            "worker_backpressure_limit",
            "CUT worker queue is saturated for this sandbox. Wait for active jobs to finish.",
        )
    duplicate_job = _find_active_duplicate_job(
        job_type="waveform_build",
        project_id=str(body.project_id),
        sandbox_root=str(body.sandbox_root),
    )
    if duplicate_job is not None:
        return _worker_job_error(
            "duplicate_job_active",
            "A waveform build job is already active for this CUT project.",
            existing_job=duplicate_job,
        )
    job_store = get_cut_mcp_job_store()
    job = job_store.create_job(
        "waveform_build",
        {
            "project_id": str(body.project_id),
            "sandbox_root": str(body.sandbox_root),
            "bins": int(body.bins),
            "limit": int(body.limit),
            "task_type": "waveform_build",
        },
    )
    thread = threading.Thread(target=_run_cut_waveform_build_job, args=(str(job["job_id"]), body), daemon=True)
    thread.start()
    return {
        "success": True,
        "schema_version": "cut_mcp_job_v1",
        "job_id": str(job["job_id"]),
        "job": job,
    }


@router.post("/worker/transcript-normalize-async")
async def cut_transcript_normalize_async(body: CutTranscriptNormalizeRequest) -> dict[str, Any]:
    """
    MARKER_170.WORKER.MEDIA_SUBMCP
    MARKER_170.WORKER.TRANSCRIPT_NORMALIZE_V1
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _worker_job_error("project_not_found", "CUT project not found for transcript worker task.")
    if _count_active_background_jobs_for_sandbox(str(body.sandbox_root)) >= _SANDBOX_BACKGROUND_LIMIT:
        return _worker_job_error(
            "worker_backpressure_limit",
            "CUT worker queue is saturated for this sandbox. Wait for active jobs to finish.",
        )
    duplicate_job = _find_active_duplicate_job(
        job_type="transcript_normalize",
        project_id=str(body.project_id),
        sandbox_root=str(body.sandbox_root),
    )
    if duplicate_job is not None:
        return _worker_job_error(
            "duplicate_job_active",
            "A transcript normalize job is already active for this CUT project.",
            existing_job=duplicate_job,
        )
    job_store = get_cut_mcp_job_store()
    job = job_store.create_job(
        "transcript_normalize",
        {
            "project_id": str(body.project_id),
            "sandbox_root": str(body.sandbox_root),
            "limit": int(body.limit),
            "segments_limit": int(body.segments_limit),
            "max_transcribe_sec": body.max_transcribe_sec,
            "task_type": "transcript_normalize",
        },
    )
    thread = threading.Thread(target=_run_cut_transcript_normalize_job, args=(str(job["job_id"]), body), daemon=True)
    thread.start()
    return {
        "success": True,
        "schema_version": "cut_mcp_job_v1",
        "job_id": str(job["job_id"]),
        "job": job,
    }


@router.post("/worker/thumbnail-build-async")
async def cut_thumbnail_build_async(body: CutThumbnailBuildRequest) -> dict[str, Any]:
    """
    MARKER_170.WORKER.MEDIA_SUBMCP
    MARKER_170.UI.STORYBOARD_THUMBNAILS_V1
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _worker_job_error("project_not_found", "CUT project not found for thumbnail worker task.")
    if _count_active_background_jobs_for_sandbox(str(body.sandbox_root)) >= _SANDBOX_BACKGROUND_LIMIT:
        return _worker_job_error(
            "worker_backpressure_limit",
            "CUT worker queue is saturated for this sandbox. Wait for active jobs to finish.",
        )
    duplicate_job = _find_active_duplicate_job(
        job_type="thumbnail_build",
        project_id=str(body.project_id),
        sandbox_root=str(body.sandbox_root),
    )
    if duplicate_job is not None:
        return _worker_job_error(
            "duplicate_job_active",
            "A thumbnail build job is already active for this CUT project.",
            existing_job=duplicate_job,
        )
    job_store = get_cut_mcp_job_store()
    job = job_store.create_job(
        "thumbnail_build",
        {
            "project_id": str(body.project_id),
            "sandbox_root": str(body.sandbox_root),
            "limit": int(body.limit),
            "waveform_bins": int(body.waveform_bins),
            "preview_segments_limit": int(body.preview_segments_limit),
            "task_type": "thumbnail_build",
        },
    )
    thread = threading.Thread(target=_run_cut_thumbnail_build_job, args=(str(job["job_id"]), body), daemon=True)
    thread.start()
    return {
        "success": True,
        "schema_version": "cut_mcp_job_v1",
        "job_id": str(job["job_id"]),
        "job": job,
    }


@router.post("/worker/audio-sync-async")
async def cut_audio_sync_async(body: CutAudioSyncRequest) -> dict[str, Any]:
    """
    MARKER_170.WORKER.AUDIO_SYNC_V1
    MARKER_170.WORKER.AUDIO_SYNC_BAKEOFF
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _worker_job_error("project_not_found", "CUT project not found for audio sync worker task.")
    if _count_active_background_jobs_for_sandbox(str(body.sandbox_root)) >= _SANDBOX_BACKGROUND_LIMIT:
        return _worker_job_error(
            "worker_backpressure_limit",
            "CUT worker queue is saturated for this sandbox. Wait for active jobs to finish.",
        )
    duplicate_job = _find_active_duplicate_job(
        job_type="audio_sync",
        project_id=str(body.project_id),
        sandbox_root=str(body.sandbox_root),
    )
    if duplicate_job is not None:
        return _worker_job_error(
            "duplicate_job_active",
            "An audio sync job is already active for this CUT project.",
            existing_job=duplicate_job,
        )
    job_store = get_cut_mcp_job_store()
    job = job_store.create_job(
        "audio_sync",
        {
            "project_id": str(body.project_id),
            "sandbox_root": str(body.sandbox_root),
            "limit": int(body.limit),
            "sample_bytes": int(body.sample_bytes),
            "method": str(body.method),
            "task_type": "audio_sync",
        },
    )
    thread = threading.Thread(target=_run_cut_audio_sync_job, args=(str(job["job_id"]), body), daemon=True)
    thread.start()
    return {
        "success": True,
        "schema_version": "cut_mcp_job_v1",
        "job_id": str(job["job_id"]),
        "job": job,
    }


@router.post("/worker/music-sync-async")
async def cut_music_sync_async(body: CutMusicSyncRequest) -> dict[str, Any]:
    """
    MARKER_171.WORKER.MUSIC_SYNC_V1
    MARKER_171.WORKER.BEAT_TRACK_PROXY
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _worker_job_error("project_not_found", "CUT project not found for music sync worker task.")
    if _count_active_background_jobs_for_sandbox(str(body.sandbox_root)) >= _SANDBOX_BACKGROUND_LIMIT:
        return _worker_job_error(
            "worker_backpressure_limit",
            "CUT worker queue is saturated for this sandbox. Wait for active jobs to finish.",
        )
    duplicate_job = _find_active_duplicate_job(
        job_type="music_sync",
        project_id=str(body.project_id),
        sandbox_root=str(body.sandbox_root),
    )
    if duplicate_job is not None:
        return _worker_job_error(
            "duplicate_job_active",
            "A music sync job is already active for this CUT project.",
            existing_job=duplicate_job,
        )
    job_store = get_cut_mcp_job_store()
    job = job_store.create_job(
        "music_sync",
        {
            "project_id": str(body.project_id),
            "sandbox_root": str(body.sandbox_root),
            "music_path": str(body.music_path or ""),
            "bpm_hint": body.bpm_hint,
            "max_analysis_sec": int(body.max_analysis_sec),
            "task_type": "music_sync",
        },
    )
    thread = threading.Thread(target=_run_cut_music_sync_job, args=(str(job["job_id"]), body), daemon=True)
    thread.start()
    return {
        "success": True,
        "schema_version": "cut_mcp_job_v1",
        "job_id": str(job["job_id"]),
        "job": job,
    }


@router.post("/worker/pause-slice-async")
async def cut_pause_slice_async(body: CutPauseSliceRequest) -> dict[str, Any]:
    """
    MARKER_170.INTEL.SLICE_METHOD_BAKEOFF
    MARKER_170.INTEL.PAUSE_SLICE_V1
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _worker_job_error("project_not_found", "CUT project not found for pause slice worker task.")
    if _count_active_background_jobs_for_sandbox(str(body.sandbox_root)) >= _SANDBOX_BACKGROUND_LIMIT:
        return _worker_job_error(
            "worker_backpressure_limit",
            "CUT worker queue is saturated for this sandbox. Wait for active jobs to finish.",
        )
    duplicate_job = _find_active_duplicate_job(
        job_type="pause_slice",
        project_id=str(body.project_id),
        sandbox_root=str(body.sandbox_root),
    )
    if duplicate_job is not None:
        return _worker_job_error(
            "duplicate_job_active",
            "A pause slice job is already active for this CUT project.",
            existing_job=duplicate_job,
        )
    job_store = get_cut_mcp_job_store()
    job = job_store.create_job(
        "pause_slice",
        {
            "project_id": str(body.project_id),
            "sandbox_root": str(body.sandbox_root),
            "limit": int(body.limit),
            "sample_bytes": int(body.sample_bytes),
            "frame_ms": int(body.frame_ms),
            "silence_threshold": float(body.silence_threshold),
            "min_silence_ms": int(body.min_silence_ms),
            "keep_silence_ms": int(body.keep_silence_ms),
            "task_type": "pause_slice",
        },
    )
    thread = threading.Thread(target=_run_cut_pause_slice_job, args=(str(job["job_id"]), body), daemon=True)
    thread.start()
    return {
        "success": True,
        "schema_version": "cut_mcp_job_v1",
        "job_id": str(job["job_id"]),
        "job": job,
    }


@router.post("/worker/timecode-sync-async")
async def cut_timecode_sync_async(body: CutTimecodeSyncRequest) -> dict[str, Any]:
    """
    MARKER_170.WORKER.TIMECODE_SYNC_V1
    MARKER_170.CONTRACT.MULTI_SYNC_ALIGNMENT_V1
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _worker_job_error("project_not_found", "CUT project not found for timecode sync worker task.")
    if _count_active_background_jobs_for_sandbox(str(body.sandbox_root)) >= _SANDBOX_BACKGROUND_LIMIT:
        return _worker_job_error(
            "worker_backpressure_limit",
            "CUT worker queue is saturated for this sandbox. Wait for active jobs to finish.",
        )
    duplicate_job = _find_active_duplicate_job(
        job_type="timecode_sync",
        project_id=str(body.project_id),
        sandbox_root=str(body.sandbox_root),
    )
    if duplicate_job is not None:
        return _worker_job_error(
            "duplicate_job_active",
            "A timecode sync job is already active for this CUT project.",
            existing_job=duplicate_job,
        )
    job_store = get_cut_mcp_job_store()
    job = job_store.create_job(
        "timecode_sync",
        {
            "project_id": str(body.project_id),
            "sandbox_root": str(body.sandbox_root),
            "limit": int(body.limit),
            "fps": int(body.fps),
            "task_type": "timecode_sync",
        },
    )
    thread = threading.Thread(target=_run_cut_timecode_sync_job, args=(str(job["job_id"]), body), daemon=True)
    thread.start()
    return {
        "success": True,
        "schema_version": "cut_mcp_job_v1",
        "job_id": str(job["job_id"]),
        "job": job,
    }


@router.get("/job/{job_id}")
async def cut_job_status(job_id: str) -> dict[str, Any]:
    """
    MARKER_170.MCP.JOB_STATUS_V1
    """
    store = get_cut_mcp_job_store()
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"CUT job not found: {job_id}")
    return {"success": True, "job": job}


@router.post("/job/{job_id}/cancel")
async def cut_job_cancel(job_id: str) -> dict[str, Any]:
    """
    MARKER_170.WORKER.RETRY_CANCEL
    """
    store = get_cut_mcp_job_store()
    job = store.request_cancel(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"CUT job not found: {job_id}")
    return {"success": True, "schema_version": "cut_mcp_job_v1", "job_id": job_id, "job": job}


@router.get("/project-state")
async def cut_project_state(sandbox_root: str, project_id: str = "") -> dict[str, Any]:
    """
    MARKER_170.MCP.PROJECT_STATE_V1
    """
    store = CutProjectStore(sandbox_root)
    project = store.load_project()
    if project is None:
        return _cut_state_error("project_not_found", "CUT project state is missing for this sandbox.")
    if project_id and str(project.get("project_id") or "") != str(project_id):
        return _cut_state_error("project_not_found", "Requested CUT project does not match sandbox state.")
    bootstrap_state = store.load_bootstrap_state()
    timeline_state = store.load_timeline_state()
    scene_graph = store.load_scene_graph()
    waveform_bundle = store.load_waveform_bundle()
    transcript_bundle = store.load_transcript_bundle()
    thumbnail_bundle = store.load_thumbnail_bundle()
    audio_sync_result = store.load_audio_sync_result()
    music_sync_result = store.load_music_sync_result()
    slice_bundle = store.load_slice_bundle()
    timecode_sync_result = store.load_timecode_sync_result()
    time_marker_bundle = store.load_time_marker_bundle()
    montage_state = store.load_montage_state()
    sync_surface = _build_sync_surface(
        project_id=str(project.get("project_id") or ""),
        timecode_sync_result=timecode_sync_result,
        audio_sync_result=audio_sync_result,
        meta_sync_result=None,
    )
    scene_graph_view = _build_scene_graph_view(
        scene_graph,
        timeline_state,
        thumbnail_bundle=thumbnail_bundle,
        sync_surface=sync_surface,
        time_marker_bundle=time_marker_bundle,
    )
    recent_jobs, active_jobs = _collect_project_jobs(project_id=str(project.get("project_id") or ""), sandbox_root=str(sandbox_root))
    music_cue_summary = _build_music_cue_summary(
        bootstrap_state=bootstrap_state,
        music_sync_result=music_sync_result,
    )
    rhythm_surface = _build_rhythm_surface(
        project_id=str(project.get("project_id") or ""),
        music_sync_result=music_sync_result,
        timeline_state=timeline_state,
    )
    return {
        "success": True,
        "schema_version": "cut_project_state_v1",
        "project": project,
        "bootstrap_state": bootstrap_state,
        "timeline_state": timeline_state,
        "scene_graph": scene_graph,
        "scene_graph_view": scene_graph_view,
        "waveform_bundle": waveform_bundle,
        "transcript_bundle": transcript_bundle,
        "thumbnail_bundle": thumbnail_bundle,
        "audio_sync_result": audio_sync_result,
        "music_sync_result": music_sync_result,
        "music_cue_summary": music_cue_summary,
        "rhythm_surface": rhythm_surface,
        "slice_bundle": slice_bundle,
        "timecode_sync_result": timecode_sync_result,
        "sync_surface": sync_surface,
        "time_marker_bundle": time_marker_bundle,
        "montage_state": montage_state,
        "recent_jobs": recent_jobs,
        "active_jobs": active_jobs,
        "layout": store.sandbox_layout_status(),
        "runtime_ready": timeline_state is not None,
        "graph_ready": scene_graph is not None,
        "waveform_ready": waveform_bundle is not None,
        "transcript_ready": transcript_bundle is not None,
        "thumbnail_ready": thumbnail_bundle is not None,
        "audio_sync_ready": audio_sync_result is not None,
        "music_cues_ready": music_sync_result is not None,
        "rhythm_surface_ready": bool((rhythm_surface or {}).get("items")),
        "slice_ready": slice_bundle is not None,
        "timecode_sync_ready": timecode_sync_result is not None,
        "sync_surface_ready": bool(sync_surface.get("items")),
        "time_markers_ready": time_marker_bundle is not None,
        "montage_ready": montage_state is not None,
    }


@router.get("/time-markers")
async def cut_time_markers(sandbox_root: str, project_id: str = "", timeline_id: str = "") -> dict[str, Any]:
    """
    MARKER_170.MCP.TIME_MARKERS_V1
    """
    store = CutProjectStore(sandbox_root)
    project = store.load_project()
    if project is None:
        return _time_marker_error("project_not_found", "CUT project not found for time marker read.")
    if project_id and str(project.get("project_id") or "") != str(project_id):
        return _time_marker_error("project_not_found", "Requested CUT project does not match sandbox state.")
    marker_bundle = store.load_time_marker_bundle()
    if marker_bundle is None:
        timeline_state = store.load_timeline_state()
        resolved_timeline_id = str(timeline_id or (timeline_state or {}).get("timeline_id") or "main")
        marker_bundle = {
            "schema_version": "cut_time_marker_bundle_v1",
            "project_id": str(project.get("project_id") or ""),
            "timeline_id": resolved_timeline_id,
            "revision": 1,
            "items": [],
            "ranking_summary": _compute_time_marker_ranking_summary([]),
            "generated_at": _utc_now_iso(),
        }
    elif timeline_id and str(marker_bundle.get("timeline_id") or "") != str(timeline_id):
        return _time_marker_error("timeline_not_found", "Requested CUT timeline does not match stored time marker bundle.")
    return {
        "success": True,
        "schema_version": "cut_time_marker_apply_v1",
        "marker": None,
        "marker_bundle": marker_bundle,
        "edit_event": None,
        "error": None,
    }


@router.post("/time-markers/apply")
async def cut_time_marker_apply(body: CutTimeMarkerApplyRequest) -> dict[str, Any]:
    """
    MARKER_170.MCP.TIME_MARKERS_V1
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _time_marker_error("project_not_found", "CUT project not found for time marker apply.")
    timeline_state = store.load_timeline_state()
    resolved_timeline_id = str((timeline_state or {}).get("timeline_id") or body.timeline_id or "main")
    if timeline_state is not None and str(body.timeline_id or resolved_timeline_id) != str(resolved_timeline_id):
        return _time_marker_error("timeline_not_found", "Requested CUT timeline does not match stored timeline state.")

    marker_bundle = store.load_time_marker_bundle()
    if marker_bundle is None:
        marker_bundle = {
            "schema_version": "cut_time_marker_bundle_v1",
            "project_id": str(project.get("project_id") or ""),
            "timeline_id": resolved_timeline_id,
            "revision": 0,
            "items": [],
            "ranking_summary": _compute_time_marker_ranking_summary([]),
            "generated_at": _utc_now_iso(),
        }

    items = [deepcopy(item) for item in marker_bundle.get("items", [])]
    marker: dict[str, Any] | None = None
    op = str(body.op or "create")
    if op == "create":
        try:
            marker = _build_time_marker(body, str(project.get("project_id") or ""), resolved_timeline_id)
        except ValueError as exc:
            return _time_marker_error("time_marker_invalid", str(exc))
        items.append(marker)
    else:
        marker_id = str(body.marker_id or "").strip()
        if not marker_id:
            return _time_marker_error("time_marker_invalid", "marker_id is required for archive operation.")
        target = next((item for item in items if str(item.get("marker_id") or "") == marker_id), None)
        if target is None:
            return _time_marker_error("marker_not_found", f"Time marker not found: {marker_id}")
        target["status"] = "archived"
        target["updated_at"] = _utc_now_iso()
        marker = deepcopy(target)

    updated_bundle = {
        "schema_version": "cut_time_marker_bundle_v1",
        "project_id": str(project.get("project_id") or ""),
        "timeline_id": resolved_timeline_id,
        "revision": int(marker_bundle.get("revision") or 0) + 1,
        "items": items,
        "ranking_summary": _compute_time_marker_ranking_summary(items),
        "generated_at": _utc_now_iso(),
    }
    store.save_time_marker_bundle(updated_bundle)
    edit_event = {
        "event_id": f"time_marker_edit_{uuid4().hex[:12]}",
        "project_id": str(project.get("project_id") or ""),
        "timeline_id": resolved_timeline_id,
        "author": str(body.author or "cut_mcp"),
        "revision": int(updated_bundle.get("revision") or 0),
        "op": op,
        "marker_id": str((marker or {}).get("marker_id") or body.marker_id or ""),
        "kind": str((marker or {}).get("kind") or body.kind or ""),
        "created_at": _utc_now_iso(),
    }
    store.append_time_marker_edit_event(edit_event)
    return {
        "success": True,
        "schema_version": "cut_time_marker_apply_v1",
        "marker": marker,
        "marker_bundle": updated_bundle,
        "edit_event": edit_event,
        "error": None,
    }


@router.post("/markers/import-player-lab")
async def cut_import_player_lab_markers(body: CutPlayerLabMarkerImportRequest) -> dict[str, Any]:
    """
    MARKER_173.20.PLAYER_LAB_IMPORT_UI
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _time_marker_error("project_not_found", "CUT project not found for Player Lab marker import.")

    timeline_state = store.load_timeline_state()
    resolved_timeline_id = str((timeline_state or {}).get("timeline_id") or body.timeline_id or "main")
    if timeline_state is not None and str(body.timeline_id or resolved_timeline_id) != str(resolved_timeline_id):
        return _time_marker_error("timeline_not_found", "Requested CUT timeline does not match stored timeline state.")

    marker_bundle = store.load_time_marker_bundle()
    if marker_bundle is None:
        marker_bundle = {
            "schema_version": "cut_time_marker_bundle_v1",
            "project_id": str(project.get("project_id") or ""),
            "timeline_id": resolved_timeline_id,
            "revision": 0,
            "items": [],
            "ranking_summary": _compute_time_marker_ranking_summary([]),
            "generated_at": _utc_now_iso(),
        }

    items = [deepcopy(item) for item in marker_bundle.get("items", [])]
    existing_marker_ids = {
        str(item.get("marker_id") or "").strip()
        for item in items
        if str(item.get("marker_id") or "").strip()
    }
    imported_markers: list[dict[str, Any]] = []
    skipped_duplicates = 0

    for payload in [*body.markers, *body.provisional_events]:
        apply_request = _player_lab_marker_to_apply_request(
            payload,
            sandbox_root=body.sandbox_root,
            project_id=body.project_id,
            timeline_id=resolved_timeline_id,
            author=body.author,
        )
        marker_id = str(apply_request.marker_id or "").strip()
        if marker_id and marker_id in existing_marker_ids:
            skipped_duplicates += 1
            continue
        try:
            marker = _build_time_marker(apply_request, str(project.get("project_id") or ""), resolved_timeline_id)
        except ValueError as exc:
            return _time_marker_error("time_marker_invalid", str(exc))
        items.append(marker)
        imported_markers.append(marker)
        if marker_id:
            existing_marker_ids.add(marker_id)

    updated_bundle = {
        "schema_version": "cut_time_marker_bundle_v1",
        "project_id": str(project.get("project_id") or ""),
        "timeline_id": resolved_timeline_id,
        "revision": int(marker_bundle.get("revision") or 0) + (1 if imported_markers else 0),
        "items": items,
        "ranking_summary": _compute_time_marker_ranking_summary(items),
        "generated_at": _utc_now_iso(),
    }
    store.save_time_marker_bundle(updated_bundle)

    edit_event = None
    if imported_markers:
        edit_event = {
            "event_id": f"time_marker_import_{uuid4().hex[:12]}",
            "project_id": str(project.get("project_id") or ""),
            "timeline_id": resolved_timeline_id,
            "author": str(body.author or "player_lab_import"),
            "revision": int(updated_bundle.get("revision") or 0),
            "op": "import_player_lab",
            "marker_id": "",
            "kind": "batch",
            "created_at": _utc_now_iso(),
            "imported_count": len(imported_markers),
        }
        store.append_time_marker_edit_event(edit_event)

    kind_counts: dict[str, int] = {}
    for marker in imported_markers:
        kind = str(marker.get("kind") or "favorite")
        kind_counts[kind] = kind_counts.get(kind, 0) + 1

    return {
        "success": True,
        "schema_version": "cut_player_lab_marker_import_v1",
        "project_id": str(project.get("project_id") or ""),
        "timeline_id": resolved_timeline_id,
        "imported_count": len(imported_markers),
        "skipped_duplicates": skipped_duplicates,
        "kind_counts": kind_counts,
        "markers": imported_markers,
        "marker_bundle": updated_bundle,
        "edit_event": edit_event,
        "error": None,
    }


@router.post("/media/support")
async def cut_media_support(body: CutMediaSupportRequest) -> dict[str, Any]:
    path = _resolve_asset_path(body.source_path, body.sandbox_root)
    ext = path.suffix.lower().lstrip(".")
    mime_type, _ = mimetypes.guess_type(str(path))
    playback_class = "native" if ext in NATIVE_VIDEO_EXT else ("proxy_recommended" if ext in PROXY_RECOMMENDED_EXT else "unknown")
    ffprobe_payload = _probe_ffprobe_metadata(path) if body.probe_ffprobe else {"available": False, "error": "disabled"}
    return {
        "success": True,
        "schema_version": "cut_media_support_v1",
        "source_path": str(path),
        "exists": path.exists(),
        "mime_type": mime_type or "application/octet-stream",
        "extension": ext,
        "playback_class": playback_class,
        "production_formats": PRODUCTION_VIDEO_FORMATS,
        "ffprobe": ffprobe_payload,
    }


def _build_export_filename(sequence_name: str, fmt: str) -> str:
    safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "_", sequence_name).strip("._-") or "vetka_cut_export"
    ext_map = {"premiere_xml": ".xml", "fcpxml": ".fcpxml", "otio": ".otio.json", "edl": ".edl"}
    return f"{safe_name}{ext_map.get(fmt, '.txt')}"


def _write_export_artifact(store: CutProjectStore, fmt: str, sequence_name: str, content: str) -> str:
    export_dir = Path(store.paths.storage_dir) / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    out_path = export_dir / _build_export_filename(sequence_name, fmt)
    out_path.write_text(content, encoding="utf-8")
    return str(out_path)


def _run_export(body: CutExportRequest, fmt: str) -> dict[str, Any]:
    store = CutProjectStore(body.sandbox_root)
    material = _collect_export_material(
        store=store,
        project_id=body.project_id,
        timeline_id=body.timeline_id,
        include_archived_markers=body.include_archived_markers,
    )
    project = material["project"]
    clips = material["clips"]
    markers = material["markers"]
    sequence_name = str(body.sequence_name or "VETKA_Sequence")
    project_name = str(project.get("display_name") or project.get("project_name") or "VETKA_Project")

    if fmt == "premiere_xml":
        xml_content = build_premiere_xml(
            {
                "project_name": project_name,
                "sequence_name": sequence_name,
                "source_path": str(project.get("source_path") or ""),
                "fps": int(body.fps),
                "duration_sec": float(material["duration_sec"] or 0.0),
                "clips": clips,
                "markers": markers,
            }
        )
        export_path = _write_export_artifact(store, fmt, sequence_name, xml_content)
        return {"content": xml_content, "path": export_path}

    if fmt == "fcpxml":
        xml_content = build_fcpxml(
            {
                "project_name": project_name,
                "sequence_name": sequence_name,
                "source_path": str(project.get("source_path") or ""),
                "fps": int(body.fps),
                "duration_sec": float(material["duration_sec"] or 0.0),
                "clips": clips,
                "markers": markers,
            }
        )
        export_path = _write_export_artifact(store, fmt, sequence_name, xml_content)
        return {"content": xml_content, "path": export_path}

    if fmt == "otio":
        payload = _build_otio_export(project_name, sequence_name, clips, int(body.fps))
        content = json.dumps(payload, ensure_ascii=False, indent=2)
        export_path = _write_export_artifact(store, fmt, sequence_name, content)
        return {"content": content, "path": export_path}

    if fmt == "edl":
        content = _build_edl_export(sequence_name, clips, int(body.fps))
        export_path = _write_export_artifact(store, fmt, sequence_name, content)
        return {"content": content, "path": export_path}

    raise HTTPException(status_code=400, detail=f"Unsupported export format: {fmt}")


@router.post("/export/premiere-xml")
async def cut_export_premiere_xml(body: CutExportRequest) -> dict[str, Any]:
    if not body.sandbox_root or not body.project_id:
        raise HTTPException(status_code=400, detail="sandbox_root and project_id are required")
    result = _run_export(body, "premiere_xml")
    store = CutProjectStore(body.sandbox_root)
    material = _collect_export_material(
        store=store,
        project_id=body.project_id,
        timeline_id=body.timeline_id,
        include_archived_markers=body.include_archived_markers,
    )
    return {
        "success": True,
        "schema_version": "cut_export_result_v1",
        "format": "premiere_xml",
        "project_id": body.project_id,
        "clip_count": len(material["clips"]),
        "marker_count": len(material["markers"]),
        "xml_content": result["content"],
        "export_path": result["path"],
        "generated_at": _utc_now_iso(),
    }


@router.post("/export/fcpxml")
async def cut_export_fcpxml(body: CutExportRequest) -> dict[str, Any]:
    if not body.sandbox_root or not body.project_id:
        raise HTTPException(status_code=400, detail="sandbox_root and project_id are required")
    result = _run_export(body, "fcpxml")
    store = CutProjectStore(body.sandbox_root)
    material = _collect_export_material(
        store=store,
        project_id=body.project_id,
        timeline_id=body.timeline_id,
        include_archived_markers=body.include_archived_markers,
    )
    return {
        "success": True,
        "schema_version": "cut_export_result_v1",
        "format": "fcpxml",
        "project_id": body.project_id,
        "clip_count": len(material["clips"]),
        "marker_count": len(material["markers"]),
        "xml_content": result["content"],
        "export_path": result["path"],
        "generated_at": _utc_now_iso(),
    }


@router.post("/export/otio")
async def cut_export_otio(body: CutExportRequest) -> dict[str, Any]:
    result = _run_export(body, "otio")
    return {
        "success": True,
        "schema_version": "cut_export_result_v1",
        "format": "otio",
        "project_id": body.project_id,
        "otio_content": result["content"],
        "export_path": result["path"],
        "generated_at": _utc_now_iso(),
    }


@router.post("/export/edl")
async def cut_export_edl(body: CutExportRequest) -> dict[str, Any]:
    result = _run_export(body, "edl")
    return {
        "success": True,
        "schema_version": "cut_export_result_v1",
        "format": "edl",
        "project_id": body.project_id,
        "edl_content": result["content"],
        "export_path": result["path"],
        "generated_at": _utc_now_iso(),
    }


@router.get("/export/social-presets")
async def cut_export_social_presets() -> dict[str, Any]:
    return {
        "success": True,
        "schema_version": "cut_export_social_presets_v1",
        "presets": _social_presets_manifest(),
        "batch_supported": True,
    }


@router.post("/export/batch")
async def cut_export_batch(body: CutBatchExportRequest) -> dict[str, Any]:
    export_req = CutExportRequest(
        sandbox_root=body.sandbox_root,
        project_id=body.project_id,
        timeline_id=body.timeline_id,
        sequence_name=body.sequence_name,
        fps=body.fps,
    )
    results: dict[str, dict[str, Any]] = {}
    for fmt in body.formats:
        out = _run_export(export_req, fmt)
        results[fmt] = {"export_path": out["path"]}
    social_manifest = _social_presets_manifest()
    social_targets = {target: social_manifest[target] for target in body.social_targets if target in social_manifest}
    return {
        "success": True,
        "schema_version": "cut_export_batch_v1",
        "project_id": body.project_id,
        "exports": results,
        "social_targets": social_targets,
        "generated_at": _utc_now_iso(),
    }


@router.post("/markers/export-srt")
async def cut_export_markers_srt(body: CutMarkerSrtExportRequest) -> dict[str, Any]:
    store = CutProjectStore(body.sandbox_root)
    material = _collect_export_material(
        store=store,
        project_id=body.project_id,
        timeline_id=body.timeline_id,
        include_archived_markers=body.include_archived,
    )
    kinds = {str(kind).strip() for kind in body.kinds if str(kind).strip()}
    markers = [
        marker for marker in material["markers"]
        if not kinds or str(marker.get("kind") or "") in kinds
    ]
    srt_parts = [_serialize_srt_marker(index, marker) for index, marker in enumerate(markers, start=1)]
    srt_content = "\n".join(srt_parts).strip() + ("\n" if srt_parts else "")
    export_dir = Path(store.paths.storage_dir) / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    out_path = export_dir / _build_export_filename("vetka_markers", "edl")
    out_path = out_path.with_suffix(".srt")
    out_path.write_text(srt_content, encoding="utf-8")
    return {
        "success": True,
        "schema_version": "cut_marker_srt_v1",
        "project_id": body.project_id,
        "timeline_id": body.timeline_id,
        "marker_count": len(markers),
        "srt_content": srt_content,
        "export_path": str(out_path),
        "generated_at": _utc_now_iso(),
    }


@router.post("/markers/import-srt")
async def cut_import_markers_srt(body: CutMarkerSrtImportRequest) -> dict[str, Any]:
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _time_marker_error("project_not_found", "CUT project not found for SRT marker import.")

    marker_bundle = store.load_time_marker_bundle() or {
        "schema_version": "cut_time_marker_bundle_v1",
        "project_id": str(project.get("project_id") or ""),
        "timeline_id": str(body.timeline_id or "main"),
        "revision": 0,
        "items": [],
        "ranking_summary": _compute_time_marker_ranking_summary([]),
        "generated_at": _utc_now_iso(),
    }

    items = [] if body.mode == "replace" else [deepcopy(item) for item in marker_bundle.get("items", [])]
    imported: list[dict[str, Any]] = []
    blocks = parse_subtitles(str(body.srt_content or ""))
    for block in blocks:
        meta, note = _extract_marker_meta_from_srt(getattr(block, "text", ""))
        media_path = str(meta.get("media_path") or body.default_media_path or "")
        if not media_path:
            continue
        marker_kind = str(meta.get("kind") or "comment")
        if marker_kind not in {"favorite", "comment", "cam", "insight", "chat"}:
            marker_kind = "comment"
        req = CutTimeMarkerApplyRequest(
            sandbox_root=body.sandbox_root,
            project_id=body.project_id,
            timeline_id=body.timeline_id,
            author=body.author,
            op="create",
            marker_id=str(meta.get("marker_id") or ""),
            media_path=media_path,
            kind=marker_kind,
            start_sec=float(getattr(block, "start", 0.0)),
            end_sec=float(getattr(block, "end", 0.0)),
            anchor_sec=float(getattr(block, "start", 0.0)),
            score=float(meta.get("score") or 0.7),
            text=note,
            comment_thread_id=str(meta.get("comment_thread_id") or "") or None,
            source_engine="srt_import_v1",
        )
        try:
            marker = _build_time_marker(req, str(project.get("project_id") or ""), str(body.timeline_id or "main"))
        except ValueError:
            continue
        items.append(marker)
        imported.append(marker)

    updated_bundle = {
        "schema_version": "cut_time_marker_bundle_v1",
        "project_id": str(project.get("project_id") or ""),
        "timeline_id": str(body.timeline_id or "main"),
        "revision": int(marker_bundle.get("revision") or 0) + (1 if imported else 0),
        "items": items,
        "ranking_summary": _compute_time_marker_ranking_summary(items),
        "generated_at": _utc_now_iso(),
    }
    store.save_time_marker_bundle(updated_bundle)
    return {
        "success": True,
        "schema_version": "cut_marker_srt_import_v1",
        "project_id": body.project_id,
        "timeline_id": body.timeline_id,
        "imported_count": len(imported),
        "mode": body.mode,
        "marker_bundle": updated_bundle,
    }



@router.post("/montage/promote-marker")
async def cut_montage_promote_marker(body: CutMontagePromoteMarkerRequest) -> dict[str, Any]:
    """
    MARKER_171.MONTAGE_ENGINE.MARKER_PROMOTION_BRIDGE
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _montage_error("project_not_found", "CUT project not found for montage promotion.")

    marker_bundle = store.load_time_marker_bundle()
    if marker_bundle is None:
        return _montage_error("marker_bundle_missing", "CUT time marker bundle is missing for montage promotion.")

    marker_id = str(body.marker_id or "").strip()
    if not marker_id:
        return _montage_error("marker_invalid", "marker_id is required for montage promotion.")

    marker = next((item for item in marker_bundle.get("items", []) if str(item.get("marker_id") or "") == marker_id), None)
    if marker is None:
        return _montage_error("marker_not_found", f"Time marker not found: {marker_id}")

    decision_status = str(body.decision_status or "accepted")
    decision_id = str(body.decision_id or f"montage_{marker_id}").strip()
    if not decision_id:
        return _montage_error("decision_invalid", "decision_id could not be resolved for montage promotion.")

    montage_state = store.load_montage_state()
    if montage_state is None:
        montage_state = {
            "schema_version": "cut_montage_state_v1",
            "project_id": str(project.get("project_id") or ""),
            "revision": 0,
            "source_bundle_revisions": {},
            "accepted_decisions": [],
            "rejected_decisions": [],
            "updated_at": _utc_now_iso(),
            "updated_by": str(body.author or "cut_mcp"),
        }

    accepted_decisions = [
        deepcopy(item)
        for item in montage_state.get("accepted_decisions", [])
        if str(item.get("decision_id") or "") != decision_id
    ]
    rejected_decisions = [
        deepcopy(item)
        for item in montage_state.get("rejected_decisions", [])
        if str(item.get("decision_id") or "") != decision_id
    ]

    decision = _build_montage_decision_from_marker(
        deepcopy(marker),
        marker_bundle_revision=int(marker_bundle.get("revision") or 0),
        decision_id=decision_id,
        lane_id=str(body.lane_id or "V1"),
        decision_status=decision_status,
        author=str(body.author or "cut_mcp"),
        editorial_intent=str(body.editorial_intent or ""),
    )

    if decision_status == "accepted":
        accepted_decisions.append(decision)
    else:
        rejected_decisions.append(decision)

    source_bundle_revisions = dict(montage_state.get("source_bundle_revisions") or {})
    source_bundle_revisions["time_marker_bundle"] = int(marker_bundle.get("revision") or 0)

    updated_state = {
        "schema_version": "cut_montage_state_v1",
        "project_id": str(project.get("project_id") or ""),
        "revision": int(montage_state.get("revision") or 0) + 1,
        "source_bundle_revisions": source_bundle_revisions,
        "accepted_decisions": accepted_decisions,
        "rejected_decisions": rejected_decisions,
        "updated_at": _utc_now_iso(),
        "updated_by": str(body.author or "cut_mcp"),
    }
    store.save_montage_state(updated_state)

    edit_event = {
        "event_id": f"montage_promote_{uuid4().hex[:12]}",
        "project_id": str(project.get("project_id") or ""),
        "marker_id": marker_id,
        "decision_id": decision_id,
        "decision_status": decision_status,
        "author": str(body.author or "cut_mcp"),
        "revision": int(updated_state.get("revision") or 0),
        "created_at": _utc_now_iso(),
    }
    return {
        "success": True,
        "schema_version": "cut_montage_state_v1",
        "decision": decision,
        "montage_state": updated_state,
        "edit_event": edit_event,
        "error": None,
    }


@router.post("/timeline/apply-with-markers")
async def cut_timeline_apply_with_markers(body: CutApplyWithMarkersRequest) -> dict[str, Any]:
    """
    MARKER_170.8.MUSIC_SYNC_INTEGRATION
    Wire energy_pause_v1 + audio_sync_v1 → TimeMarkerBundle → store.
    Creates music-sync markers from slice windows and optional audio sync.
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _time_marker_error("project_not_found", "CUT project not found for music-sync markers.")

    timeline_state = store.load_timeline_state()
    resolved_timeline_id = str((timeline_state or {}).get("timeline_id") or body.timeline_id or "main")

    # Resolve media path — find audio/music tracks from timeline
    media_path = str(body.media_path or "").strip()
    track_id = str(body.track_id or "").strip()
    if not media_path:
        # Try to find a music track from timeline lanes
        if timeline_state:
            for lane in timeline_state.get("lanes", []):
                if lane.get("lane_type") == "audio_sync":
                    clips = lane.get("clips", [])
                    if clips:
                        media_path = str(clips[0].get("source_path", ""))
                        if not track_id:
                            track_id = str(clips[0].get("clip_id", ""))
                        break
    if not media_path:
        return _time_marker_error("media_not_found", "No media_path provided and no music track found in timeline.")
    if not track_id:
        track_id = f"track_{uuid4().hex[:8]}"

    # Step 1: Run pause-slice (energy_pause_v1) on the audio signal
    # Load audio signal from project store
    audio_signal = _load_audio_signal_for_media(store, media_path, body.slice_config.sample_bytes)
    if audio_signal is None:
        return _time_marker_error("audio_signal_unavailable", "Could not load audio signal for music track.")

    signal_data, sample_rate = audio_signal
    slice_windows = derive_pause_windows_from_silence(
        signal_data,
        sample_rate,
        frame_ms=body.slice_config.frame_ms,
        silence_threshold=body.slice_config.silence_threshold,
        min_silence_ms=body.slice_config.min_silence_ms,
        keep_silence_ms=body.slice_config.keep_silence_ms,
    )

    # Step 2: Run audio sync (optional)
    sync_result = None
    if body.slice_config.use_sync:
        ref_signal = _load_reference_audio_signal(store, body.slice_config.sample_bytes)
        if ref_signal is not None:
            ref_data, ref_rate = ref_signal
            method = body.slice_config.sync_method
            if method == "peaks+correlation":
                sync_result = detect_offset_hybrid(signal_data, ref_data, min(sample_rate, ref_rate))
            elif method == "correlation":
                sync_result = detect_offset_via_correlation(signal_data, ref_data, min(sample_rate, ref_rate))
            else:
                sync_result = detect_peak_offset(signal_data, ref_data, min(sample_rate, ref_rate))

    # Step 3: Create marker bundle
    marker_bundle = create_marker_bundle_from_slices(
        project_id=str(project.get("project_id") or body.project_id),
        timeline_id=resolved_timeline_id,
        track_id=track_id,
        media_path=media_path,
        slice_windows=slice_windows,
        sync_result=sync_result,
        slice_method=body.slice_config.method,
    )

    # Step 4: Merge into existing bundle or save as new
    existing_bundle = store.load_time_marker_bundle()
    if existing_bundle and existing_bundle.get("items"):
        # Append music markers to existing bundle
        all_items = list(existing_bundle.get("items", [])) + marker_bundle.get("items", [])
        existing_bundle["items"] = all_items
        existing_bundle["revision"] = int(existing_bundle.get("revision", 0)) + 1
        existing_bundle["music_sync_meta"] = marker_bundle.get("music_sync_meta")
        existing_bundle["generated_at"] = _utc_now_iso()
        store.save_time_marker_bundle(existing_bundle)
        final_bundle = existing_bundle
    else:
        store.save_time_marker_bundle(marker_bundle)
        final_bundle = marker_bundle

    # Edit event
    edit_event = {
        "event_id": f"music_sync_markers_{uuid4().hex[:12]}",
        "project_id": str(project.get("project_id") or ""),
        "timeline_id": resolved_timeline_id,
        "author": "music_sync_engine",
        "revision": int(final_bundle.get("revision", 0)),
        "op": "music_sync_create",
        "marker_count": len(marker_bundle.get("items", [])),
        "sync_method": sync_result.method if sync_result else None,
        "sync_confidence": sync_result.confidence if sync_result else None,
        "created_at": _utc_now_iso(),
    }
    store.append_time_marker_edit_event(edit_event)

    return {
        "success": True,
        "schema_version": "cut_time_marker_apply_v1",
        "timeline_applied": True,
        "marker_bundle": final_bundle,
        "music_sync_meta": marker_bundle.get("music_sync_meta"),
        "edit_event": edit_event,
        "error": None,
    }


def _load_audio_signal_for_media(
    store: CutProjectStore, media_path: str, sample_bytes: int
) -> tuple[list[float], int] | None:
    """Load audio signal proxy from a media file via project store."""
    import struct

    # Check if waveform data exists in project state
    project_state = store.load_project()
    if project_state is None:
        return None

    # Try to read raw audio bytes from the media file
    full_path = media_path
    if not os.path.isabs(full_path):
        source_path = str(project_state.get("source_path", ""))
        if source_path:
            full_path = os.path.join(source_path, media_path)

    if not os.path.exists(full_path):
        return None

    try:
        with open(full_path, "rb") as f:
            raw = f.read(sample_bytes)
        if len(raw) < 4:
            return None
        # Build 16-bit PCM signal proxy
        signal = []
        for i in range(0, len(raw) - 1, 2):
            val = struct.unpack_from("<h", raw, i)[0]
            signal.append(val / 32768.0)
        return signal, 1000  # Approximate sample rate for proxy
    except Exception:
        return None


def _load_reference_audio_signal(
    store: CutProjectStore, sample_bytes: int
) -> tuple[list[float], int] | None:
    """Load a reference audio signal for sync (first video clip audio)."""
    import struct

    timeline_state = store.load_timeline_state()
    if timeline_state is None:
        return None

    project = store.load_project()
    source_path = str((project or {}).get("source_path", ""))

    # Find first video lane clip as reference
    for lane in timeline_state.get("lanes", []):
        if lane.get("lane_type") in ("video", "camera"):
            clips = lane.get("clips", [])
            if clips:
                ref_path = str(clips[0].get("source_path", ""))
                if ref_path:
                    full_path = ref_path if os.path.isabs(ref_path) else os.path.join(source_path, ref_path)
                    if os.path.exists(full_path):
                        try:
                            with open(full_path, "rb") as f:
                                raw = f.read(sample_bytes)
                            if len(raw) < 4:
                                continue
                            signal = []
                            for i in range(0, len(raw) - 1, 2):
                                val = struct.unpack_from("<h", raw, i)[0]
                                signal.append(val / 32768.0)
                            return signal, 1000
                        except Exception:
                            continue
    return None


@router.post("/timeline/apply")
async def cut_timeline_apply(body: CutTimelinePatchRequest) -> dict[str, Any]:
    """
    MARKER_170.MCP.TIMELINE_APPLY_V1
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _timeline_error("project_not_found", "CUT project not found for timeline apply.")
    timeline_state = store.load_timeline_state()
    if timeline_state is None:
        return _timeline_error("timeline_not_ready", "CUT timeline state is missing. Run scene assembly first.")
    if str(timeline_state.get("timeline_id") or "") != str(body.timeline_id):
        return _timeline_error("timeline_not_found", "Requested CUT timeline does not match stored timeline state.")
    # MARKER_173.1 — snapshot for undo before mutation
    prev_state_snapshot = deepcopy(timeline_state)
    revision_before = int(timeline_state.get("revision") or 0)

    try:
        updated_state, applied_ops = _apply_timeline_ops(timeline_state, body.ops)
    except ValueError as exc:
        return _timeline_error("timeline_patch_invalid", str(exc))

    store.save_timeline_state(updated_state)

    # MARKER_173.1 — push to undo stack (skip non-undoable ops like set_selection/set_view)
    undoable_ops = [op for op in applied_ops if op.get("op") not in ("set_selection", "set_view")]
    undo_info = None
    if undoable_ops:
        try:
            undo_service = CutUndoRedoService(
                body.sandbox_root, str(body.project_id), str(body.timeline_id)
            )
            revision_after = int(updated_state.get("revision") or 0)
            undo_info = undo_service.push(
                label=build_op_label(undoable_ops),
                prev_state=prev_state_snapshot,
                applied_ops=undoable_ops,
                revision_before=revision_before,
                revision_after=revision_after,
            )
        except Exception as exc:
            # Undo push failure is non-fatal — edit still applied
            logger.warning("Undo push failed (non-fatal): %s", exc)

    edit_event = {
        "event_id": f"timeline_edit_{uuid4().hex[:12]}",
        "project_id": str(project.get("project_id") or ""),
        "timeline_id": str(updated_state.get("timeline_id") or body.timeline_id),
        "author": str(body.author or "cut_mcp"),
        "revision": int(updated_state.get("revision") or 0),
        "op_count": len(applied_ops),
        "ops": applied_ops,
        "created_at": _utc_now_iso(),
    }
    store.append_timeline_edit_event(edit_event)
    result = {
        "success": True,
        "schema_version": "cut_timeline_apply_v1",
        "timeline_state": updated_state,
        "applied_ops": applied_ops,
        "edit_event": edit_event,
    }
    if undo_info:
        result["undo_info"] = undo_info

    # MARKER_173.4 — emit real-time event
    try:
        _emitter = CutTimelineEventEmitter.get_instance()
        asyncio.ensure_future(_emitter.emit_edit(
            str(body.project_id), str(body.timeline_id),
            applied_ops, int(updated_state.get("revision") or 0),
            author=str(body.author or "cut_mcp"),
        ))
    except Exception:
        pass  # non-fatal

    return result


@router.post("/scene-graph/apply")
async def cut_scene_graph_apply(body: CutSceneGraphPatchRequest) -> dict[str, Any]:
    """
    MARKER_170.MCP.SCENE_GRAPH_APPLY_V1
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return _scene_graph_error("project_not_found", "CUT project not found for scene graph apply.")
    scene_graph = store.load_scene_graph()
    if scene_graph is None:
        return _scene_graph_error("scene_graph_not_ready", "CUT scene graph is missing. Run scene assembly first.")
    if str(scene_graph.get("graph_id") or "") != str(body.graph_id):
        return _scene_graph_error("graph_not_found", "Requested CUT scene graph does not match stored graph state.")
    try:
        updated_graph, applied_ops = _apply_scene_graph_ops(scene_graph, body.ops)
    except ValueError as exc:
        return _scene_graph_error("scene_graph_patch_invalid", str(exc))

    store.save_scene_graph(updated_graph)
    edit_event = {
        "event_id": f"scene_graph_edit_{uuid4().hex[:12]}",
        "project_id": str(project.get("project_id") or ""),
        "graph_id": str(updated_graph.get("graph_id") or body.graph_id),
        "author": str(body.author or "cut_mcp"),
        "revision": int(updated_graph.get("revision") or 0),
        "op_count": len(applied_ops),
        "ops": applied_ops,
        "created_at": _utc_now_iso(),
    }
    store.append_scene_graph_edit_event(edit_event)
    return {
        "success": True,
        "schema_version": "cut_scene_graph_apply_v1",
        "scene_graph": updated_graph,
        "applied_ops": applied_ops,
        "edit_event": edit_event,
    }


@router.get("/bootstrap-job/{job_id}")
async def cut_bootstrap_job_status(job_id: str) -> dict[str, Any]:
    """
    MARKER_170.MCP.BOOTSTRAP_JOB_STATUS_V1
    """
    return await cut_job_status(job_id)


# ── MARKER_173.1 Undo/Redo Endpoints ───────────────────────


class CutUndoRedoRequest(BaseModel):
    sandbox_root: str
    project_id: str
    timeline_id: str


@router.post("/undo")
async def cut_undo(body: CutUndoRedoRequest) -> dict[str, Any]:
    """
    MARKER_173.1.UNDO_ENDPOINT
    Undo the last timeline edit. Restores previous timeline state.
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return {"success": False, "error": "project_not_found"}

    undo_service = CutUndoRedoService(
        body.sandbox_root, str(body.project_id), str(body.timeline_id)
    )
    result = undo_service.undo()
    if result is None:
        return {"success": False, "error": "nothing_to_undo", "undo_depth": 0, "redo_depth": 0}

    # Restore the previous state
    restore_state = result["restore_state"]
    store.save_timeline_state(restore_state)

    # Log the undo as an edit event
    edit_event = {
        "event_id": f"undo_{uuid4().hex[:12]}",
        "project_id": str(body.project_id),
        "timeline_id": str(body.timeline_id),
        "author": "undo",
        "revision": int(restore_state.get("revision") or 0),
        "op_count": 0,
        "ops": [{"op": "undo", "undone_label": result["entry"]["label"]}],
        "created_at": _utc_now_iso(),
    }
    store.append_timeline_edit_event(edit_event)

    # MARKER_173.4 — emit real-time event
    try:
        _emitter = CutTimelineEventEmitter.get_instance()
        asyncio.ensure_future(_emitter.emit_undo(
            str(body.project_id), str(body.timeline_id),
            result["entry"]["label"], int(restore_state.get("revision") or 0),
            result["undo_depth"], result["redo_depth"],
        ))
    except Exception:
        pass

    return {
        "success": True,
        "schema_version": "cut_undo_v1",
        "undone_label": result["entry"]["label"],
        "timeline_state": restore_state,
        "undo_depth": result["undo_depth"],
        "redo_depth": result["redo_depth"],
        "edit_event": edit_event,
    }


@router.post("/redo")
async def cut_redo(body: CutUndoRedoRequest) -> dict[str, Any]:
    """
    MARKER_173.1.REDO_ENDPOINT
    Redo the last undone timeline edit. Re-applies ops.
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return {"success": False, "error": "project_not_found"}

    timeline_state = store.load_timeline_state()
    if timeline_state is None:
        return {"success": False, "error": "timeline_not_ready"}

    undo_service = CutUndoRedoService(
        body.sandbox_root, str(body.project_id), str(body.timeline_id)
    )
    result = undo_service.redo()
    if result is None:
        return {"success": False, "error": "nothing_to_redo", "undo_depth": 0, "redo_depth": 0}

    # Re-apply the ops
    try:
        updated_state, applied_ops = _apply_timeline_ops(timeline_state, result["reapply_ops"])
    except ValueError as exc:
        return {"success": False, "error": "redo_failed", "detail": str(exc)}

    store.save_timeline_state(updated_state)

    edit_event = {
        "event_id": f"redo_{uuid4().hex[:12]}",
        "project_id": str(body.project_id),
        "timeline_id": str(body.timeline_id),
        "author": "redo",
        "revision": int(updated_state.get("revision") or 0),
        "op_count": len(applied_ops),
        "ops": [{"op": "redo", "redone_label": result["entry"]["label"]}] + applied_ops,
        "created_at": _utc_now_iso(),
    }
    store.append_timeline_edit_event(edit_event)

    # MARKER_173.4 — emit real-time event
    try:
        _emitter = CutTimelineEventEmitter.get_instance()
        asyncio.ensure_future(_emitter.emit_redo(
            str(body.project_id), str(body.timeline_id),
            result["entry"]["label"], int(updated_state.get("revision") or 0),
            result["undo_depth"], result["redo_depth"],
        ))
    except Exception:
        pass

    return {
        "success": True,
        "schema_version": "cut_redo_v1",
        "redone_label": result["entry"]["label"],
        "timeline_state": updated_state,
        "applied_ops": applied_ops,
        "undo_depth": result["undo_depth"],
        "redo_depth": result["redo_depth"],
        "edit_event": edit_event,
    }


@router.get("/undo-stack")
async def cut_undo_stack(
    sandbox_root: str,
    project_id: str,
    timeline_id: str,
) -> dict[str, Any]:
    """
    MARKER_173.1.UNDO_STACK_ENDPOINT
    Get undo/redo stack metadata (depths, labels). No heavy state payloads.
    """
    undo_service = CutUndoRedoService(sandbox_root, project_id, timeline_id)
    return {
        "success": True,
        **undo_service.get_stack_info(),
    }


@router.post("/scene-detect-and-apply")
async def cut_scene_detect_and_apply(body: CutSceneDetectApplyRequest) -> dict[str, Any]:
    """
    MARKER_173.3 — Scene detection → timeline auto-apply.

    Runs histogram-based scene boundary detection on source media files,
    creates clips at detected boundary points on a dedicated lane,
    and optionally updates the scene graph with detected scenes.

    Returns detected boundaries, created clips, and updated scene graph.
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return {"success": False, "error": "project_not_found"}

    timeline_state = store.load_timeline_state()
    if timeline_state is None:
        return {"success": False, "error": "timeline_not_ready"}

    # ── Discover source media paths ──────────────────────────
    source_paths: list[str] = list(body.source_paths) if body.source_paths else []
    if not source_paths:
        # Collect all unique source_path values from existing clips
        seen: set[str] = set()
        for lane in timeline_state.get("lanes", []):
            for clip in lane.get("clips", []):
                sp = str(clip.get("source_path") or "").strip()
                if sp and sp not in seen:
                    source_paths.append(sp)
                    seen.add(sp)
    if not source_paths:
        return {"success": False, "error": "no_source_media", "detail": "No media files to analyse."}

    # Resolve relative paths against sandbox_root
    resolved_paths: list[str] = []
    for sp in source_paths:
        p = Path(sp)
        if not p.is_absolute():
            p = Path(body.sandbox_root) / sp
        resolved_paths.append(str(p))

    # ── Run scene detection on each source ───────────────────
    all_boundaries: list[dict[str, Any]] = []
    for media_path in resolved_paths:
        if not os.path.isfile(media_path):
            logger.warning("Scene detect: skipping missing file %s", media_path)
            continue
        boundaries = detect_scene_boundaries(
            media_path,
            interval_sec=body.interval_sec,
            threshold=body.threshold,
            max_duration_sec=body.max_duration_sec,
        )
        for b in boundaries:
            all_boundaries.append({
                "time_sec": b.time_sec,
                "diff_score": b.diff_score,
                "method": b.method,
                "source_path": media_path,
            })

    # Sort boundaries by time
    all_boundaries.sort(key=lambda b: b["time_sec"])

    # ── Create clips on the target lane ──────────────────────
    lane_id = body.lane_id or "scenes"
    target_lane: dict[str, Any] | None = None
    for lane in timeline_state.get("lanes", []):
        if str(lane.get("lane_id") or "") == lane_id:
            target_lane = lane
            break

    if target_lane is None:
        # Create the lane if it doesn't exist
        target_lane = {
            "lane_id": lane_id,
            "type": "scene_detect",
            "clips": [],
        }
        timeline_state.setdefault("lanes", []).append(target_lane)

    # Build clip segments from boundaries
    # Each source file gets its own set of scene clips
    created_clips: list[dict[str, Any]] = []
    scene_counter = 0
    for media_path in resolved_paths:
        if not os.path.isfile(media_path):
            continue
        # Get boundaries for this source file
        file_boundaries = [b for b in all_boundaries if b["source_path"] == media_path]
        boundary_times = [b["time_sec"] for b in file_boundaries]

        # Determine total duration from existing clips or probe
        total_dur = 0.0
        for lane in timeline_state.get("lanes", []):
            for clip in lane.get("clips", []):
                if str(clip.get("source_path") or "") == media_path or str(clip.get("source_path") or "").endswith(os.path.basename(media_path)):
                    clip_end = float(clip.get("start_sec") or 0) + float(clip.get("duration_sec") or 0)
                    total_dur = max(total_dur, clip_end)
        if total_dur <= 0:
            total_dur = body.max_duration_sec  # fallback

        # Create scene segments: [0, b1), [b1, b2), ... [bN, total)
        seg_starts = [0.0] + boundary_times
        seg_ends = boundary_times + [total_dur]

        for i in range(len(seg_starts)):
            scene_counter += 1
            seg_start = seg_starts[i]
            seg_end = seg_ends[i]
            seg_dur = round(seg_end - seg_start, 4)
            if seg_dur <= 0:
                continue
            clip_id = f"scene_{scene_counter:03d}"
            new_clip = {
                "clip_id": clip_id,
                "source_path": media_path,
                "start_sec": round(seg_start, 4),
                "duration_sec": seg_dur,
                "scene_id": f"scene_{scene_counter:02d}",
                "auto_detected": True,
            }
            target_lane["clips"].append(new_clip)
            created_clips.append(new_clip)

    # Sort clips on target lane by start_sec
    target_lane["clips"] = sorted(
        target_lane.get("clips", []),
        key=lambda c: float(c.get("start_sec") or 0),
    )

    # ── Update scene graph ───────────────────────────────────
    scene_graph_updates: list[dict[str, Any]] = []
    if body.update_scene_graph:
        scene_graph = store.load_scene_graph()
        if scene_graph is None:
            scene_graph = {
                "schema_version": "cut_scene_graph_v1",
                "project_id": str(body.project_id),
                "graph_id": "main",
                "nodes": [],
                "edges": [],
                "updated_at": _utc_now_iso(),
            }
        existing_node_ids = {
            str(n.get("node_id") or "") for n in scene_graph.get("nodes", [])
        }
        prev_scene_node_id: str | None = None
        for clip in created_clips:
            scene_id = str(clip.get("scene_id") or "")
            if scene_id and scene_id not in existing_node_ids:
                scene_node = {
                    "node_id": scene_id,
                    "node_type": SCENE_GRAPH_NODE_SCENE,
                    "label": scene_id.replace("_", " ").title(),
                    "record_ref": None,
                    "metadata": {
                        "timeline_id": str(body.timeline_id),
                        "lane_id": lane_id,
                        "clip_id": str(clip.get("clip_id") or ""),
                        "source_path": str(clip.get("source_path") or ""),
                        "start_sec": clip.get("start_sec", 0.0),
                        "duration_sec": clip.get("duration_sec", 0.0),
                        "auto_detected": True,
                    },
                }
                scene_graph["nodes"].append(scene_node)
                existing_node_ids.add(scene_id)
                scene_graph_updates.append({"added_node": scene_id})

                # Add "follows" edge from previous scene
                if prev_scene_node_id:
                    edge = {
                        "source": prev_scene_node_id,
                        "target": scene_id,
                        "edge_type": SCENE_GRAPH_EDGE_FOLLOWS,
                        "metadata": {"auto_detected": True},
                    }
                    scene_graph.setdefault("edges", []).append(edge)
                prev_scene_node_id = scene_id

        scene_graph["updated_at"] = _utc_now_iso()
        store.save_scene_graph(scene_graph)

    # ── Bump revision and save timeline ──────────────────────
    timeline_state["revision"] = int(timeline_state.get("revision") or 0) + 1
    timeline_state["updated_at"] = _utc_now_iso()
    store.save_timeline_state(timeline_state)

    # MARKER_173.4 — emit real-time event
    try:
        _emitter = CutTimelineEventEmitter.get_instance()
        asyncio.ensure_future(_emitter.emit_scene_detected(
            str(body.project_id), str(body.timeline_id),
            len(all_boundaries), len(created_clips), lane_id,
        ))
    except Exception:
        pass

    return {
        "success": True,
        "schema_version": "cut_scene_detect_v1",
        "boundaries": all_boundaries,
        "boundary_count": len(all_boundaries),
        "created_clips": created_clips,
        "clip_count": len(created_clips),
        "lane_id": lane_id,
        "scene_graph_updates": scene_graph_updates,
        "source_paths_analysed": [p for p in resolved_paths if os.path.isfile(p)],
        "threshold": body.threshold,
        "interval_sec": body.interval_sec,
    }


@router.get("/montage/suggestions")
async def cut_montage_suggestions(
    sandbox_root: str,
    project_id: str,
    timeline_id: str = "main",
    limit: int = 10,
    min_score: float = 0.05,
) -> dict[str, Any]:
    """
    MARKER_173.5 — Montage suggestion ranking.

    Returns scored clip suggestions from all sources (markers, decisions),
    ranked by weighted signal fusion (transcript conf × energy × sync × marker × intent × recency).
    Pure math — <5ms execution.
    """
    store = CutProjectStore(sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(project_id):
        return {"success": False, "error": "project_not_found"}

    # Load markers and decisions
    marker_bundle = store.load_time_marker_bundle()
    markers: list[dict[str, Any]] = []
    if marker_bundle and isinstance(marker_bundle, dict):
        markers = marker_bundle.get("markers", [])
    elif isinstance(marker_bundle, list):
        markers = marker_bundle

    montage_state = store.load_montage_state()
    decisions: list[dict[str, Any]] = []
    if montage_state and isinstance(montage_state, dict):
        decisions = montage_state.get("decisions", [])

    ranker = MontageRanker(min_score=min_score)
    scored_clips = ranker.rank_clips(markers, decisions, limit=limit)

    suggestions = []
    for clip in scored_clips:
        suggestions.append({
            "clip_id": clip.clip_id,
            "source_path": clip.source_path,
            "start_sec": clip.start_sec,
            "end_sec": clip.end_sec,
            "duration_sec": clip.duration_sec,
            "score": clip.score,
            "confidence": clip.confidence,
            "editorial_intent": clip.editorial_intent,
            "reasoning": clip.reasoning,
            "source_signals": clip.source_signals,
            "marker_id": clip.marker_id,
        })

    return {
        "success": True,
        "schema_version": "cut_montage_suggestions_v1",
        "suggestions": suggestions,
        "total": len(suggestions),
        "limit": limit,
        "min_score": min_score,
        "marker_count": len(markers),
        "decision_count": len(decisions),
    }


class CutProxyGenerateRequest(BaseModel):
    """MARKER_173.6 — Proxy generation request."""
    sandbox_root: str
    project_id: str
    source_paths: list[str] = Field(default_factory=list, description="Media files to proxy. If empty, uses all clips from timeline.")
    resolution: str = Field(default="720p", description="Proxy resolution: 720p, 480p, 360p")
    force: bool = Field(default=False, description="Force regeneration even if proxy exists")


@router.post("/proxy/generate")
async def cut_proxy_generate(body: CutProxyGenerateRequest) -> dict[str, Any]:
    """
    MARKER_173.6 — Generate proxy files for timeline clips.

    Creates lightweight 720p/480p/360p H.264 proxies for faster scrubbing.
    Skips if fresh proxy already exists. Stores in cut_runtime/proxies/.
    """
    from src.services.cut_proxy_worker import PROXY_480P, PROXY_360P

    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return {"success": False, "error": "project_not_found"}

    # Select resolution preset
    spec_map = {"720p": None, "480p": PROXY_480P, "360p": PROXY_360P}
    spec = spec_map.get(body.resolution)

    # Discover source paths
    source_paths = list(body.source_paths)
    if not source_paths:
        timeline_state = store.load_timeline_state()
        if timeline_state:
            seen: set[str] = set()
            for lane in timeline_state.get("lanes", []):
                for clip in lane.get("clips", []):
                    sp = str(clip.get("source_path") or "").strip()
                    if sp and sp not in seen:
                        source_paths.append(sp)
                        seen.add(sp)

    if not source_paths:
        return {"success": False, "error": "no_source_media"}

    # Resolve relative paths
    resolved: list[str] = []
    for sp in source_paths:
        p = Path(sp)
        if not p.is_absolute():
            p = Path(body.sandbox_root) / sp
        resolved.append(str(p))

    worker = ProxyWorker(body.sandbox_root, spec=spec, force=body.force)
    results = worker.generate_batch(resolved)

    proxy_results = []
    for r in results:
        proxy_results.append({
            "source_path": r.source_path,
            "proxy_path": r.proxy_path,
            "success": r.success,
            "skipped": r.skipped,
            "error": r.error,
            "duration_sec": r.duration_sec,
            "source_size_bytes": r.source_size_bytes,
            "proxy_size_bytes": r.proxy_size_bytes,
        })

    return {
        "success": True,
        "schema_version": "cut_proxy_generate_v1",
        "results": proxy_results,
        "total": len(proxy_results),
        "generated": sum(1 for r in results if r.success and not r.skipped),
        "skipped": sum(1 for r in results if r.skipped),
        "failed": sum(1 for r in results if not r.success),
        "resolution": body.resolution,
    }


@router.get("/proxy/list")
async def cut_proxy_list(sandbox_root: str, project_id: str) -> dict[str, Any]:
    """
    MARKER_173.6 — List generated proxy files.
    """
    store = CutProjectStore(sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(project_id):
        return {"success": False, "error": "project_not_found"}

    worker = ProxyWorker(sandbox_root)
    proxies = worker.list_proxies()
    return {
        "success": True,
        "schema_version": "cut_proxy_list_v1",
        "proxies": proxies,
        "total": len(proxies),
    }


@router.get("/proxy/path")
async def cut_proxy_path(sandbox_root: str, source_path: str) -> dict[str, Any]:
    """
    MARKER_173.6 — Get proxy path for a source file (if exists).
    """
    worker = ProxyWorker(sandbox_root)
    proxy = worker.get_proxy_path(source_path)
    if proxy:
        return {"success": True, "proxy_path": proxy, "exists": True}
    return {"success": True, "proxy_path": None, "exists": False}


# ===================================================================
# PULSE Conductor endpoints — Phase 179 Sprint 1
# MARKER_179.5_PULSE_ENDPOINTS
# ===================================================================


class CutPulseScoreSceneRequest(BaseModel):
    """Request to score a single scene via PULSE conductor."""
    scene_id: str = "sc_0"
    # Narrative signal (optional)
    script_text: str | None = None
    dramatic_function: str | None = None
    pendulum_position: float | None = None
    suggested_scale: str | None = None
    # Visual signal (optional)
    cuts_per_minute: float | None = None
    motion_intensity: float | None = None
    # Audio signal (optional)
    audio_bpm: float | None = None
    audio_key: str | None = None
    audio_camelot_key: str | None = None


class CutPulseScoreFilmRequest(BaseModel):
    """Request to score an entire film from script text."""
    script_text: str
    # Optional audio context for the whole film
    audio_bpm: float | None = None
    audio_key: str | None = None
    audio_camelot_key: str | None = None


class CutPulseCamelotPathRequest(BaseModel):
    """Request to analyze a Camelot key path."""
    keys: list[str]  # e.g. ["8A", "9A", "3B", "8A"]


class CutPulseCamelotSuggestRequest(BaseModel):
    """Request to suggest next Camelot key."""
    current_key: str
    target_pendulum: float = 0.0
    prefer_dramatic: bool = False


@router.get("/pulse/matrix")
async def cut_pulse_matrix() -> dict[str, Any]:
    """
    MARKER_179.5 — Get the full cinema matrix (Scale → Genre → Cinema Scene).
    """
    matrix = get_cinema_matrix()
    return {
        "success": True,
        "schema_version": "pulse_cinema_matrix_v1",
        "scales": matrix.to_dict_list(),
        "total": len(matrix.all_scales()),
    }


@router.get("/pulse/matrix/{scale_name}")
async def cut_pulse_matrix_by_scale(scale_name: str) -> dict[str, Any]:
    """
    MARKER_179.5 — Get a single row from the cinema matrix by scale name.
    """
    matrix = get_cinema_matrix()
    row = matrix.get_by_scale(scale_name)
    if not row:
        raise HTTPException(404, f"Scale '{scale_name}' not found in cinema matrix")
    return {
        "success": True,
        "scale": row.scale,
        "cinema_genre": row.cinema_genre,
        "cinema_scene_types": row.cinema_scene_types,
        "dramatic_function": row.dramatic_function,
        "pendulum_position": row.pendulum_position,
        "counterpoint_pair": row.counterpoint_pair,
        "energy_profile": row.energy_profile,
        "itten_colors": row.itten_colors,
        "music_genres": row.music_genres,
        "confidence": row.confidence,
        "camelot_region": row.camelot_region,
    }


@router.post("/pulse/score-scene")
async def cut_pulse_score_scene(req: CutPulseScoreSceneRequest) -> dict[str, Any]:
    """
    MARKER_179.5 — Score a single scene via PULSE conductor.

    Accepts narrative, visual, and/or audio signals.
    If script_text provided, runs script analyzer first.
    """
    conductor = get_pulse_conductor()

    # Build narrative signal
    narrative = None
    if req.script_text:
        analyzer = get_script_analyzer()
        narrative = analyzer.analyze_single(req.script_text, req.scene_id)
    elif req.dramatic_function or req.pendulum_position is not None:
        narrative = NarrativeBPM(
            scene_id=req.scene_id,
            dramatic_function=req.dramatic_function or "Unknown",
            pendulum_position=req.pendulum_position or 0.0,
            estimated_energy=0.5,
            suggested_scale=req.suggested_scale or "",
            confidence=0.7,
        )

    # Build visual signal
    visual = None
    if req.cuts_per_minute is not None or req.motion_intensity is not None:
        visual = VisualBPM(
            scene_id=req.scene_id,
            cuts_per_minute=req.cuts_per_minute or 0.0,
            motion_intensity=req.motion_intensity or 0.5,
            confidence=0.6,
        )

    # Build audio signal
    audio = None
    if req.audio_bpm is not None or req.audio_camelot_key:
        engine = get_camelot_engine()
        camelot = req.audio_camelot_key or ""
        if not camelot and req.audio_key:
            camelot = engine.key_from_musical(req.audio_key) or ""
        audio = AudioBPM(
            bpm=req.audio_bpm or 120.0,
            key=req.audio_key or "",
            camelot_key=camelot,
            confidence=0.8,
        )

    score = conductor.score_scene(req.scene_id, narrative, visual, audio)

    return {
        "success": True,
        "schema_version": "pulse_score_v1",
        "score": score.to_dict(),
    }


@router.post("/pulse/score-film")
async def cut_pulse_score_film(req: CutPulseScoreFilmRequest) -> dict[str, Any]:
    """
    MARKER_179.5 — Score an entire film from script text.

    Parses script into scenes, runs PULSE conductor on each,
    returns the full partiture with Camelot path analysis.
    """
    analyzer = get_script_analyzer()
    conductor = get_pulse_conductor()

    narrative_bpms = analyzer.analyze(req.script_text)

    # Build audio context if provided
    audio = None
    if req.audio_bpm is not None or req.audio_camelot_key:
        engine = get_camelot_engine()
        camelot = req.audio_camelot_key or ""
        if not camelot and req.audio_key:
            camelot = engine.key_from_musical(req.audio_key) or ""
        audio = AudioBPM(
            bpm=req.audio_bpm or 120.0,
            key=req.audio_key or "",
            camelot_key=camelot,
            confidence=0.8,
        )

    scenes = []
    for nbpm in narrative_bpms:
        scenes.append({
            "scene_id": nbpm.scene_id,
            "narrative": nbpm,
            "audio": audio,  # same audio context for whole film
        })

    partiture = conductor.score_film(scenes)

    return {
        "success": True,
        "schema_version": "pulse_partiture_v1",
        "partiture": partiture.to_dict(),
    }


@router.post("/pulse/analyze-script")
async def cut_pulse_analyze_script(
    script_text: str = "",
) -> dict[str, Any]:
    """
    MARKER_179.5 — Analyze script text and extract NarrativeBPM for each scene.

    Returns scene breakdown with dramatic functions, pendulum positions,
    and suggested scales.
    """
    if not script_text:
        raise HTTPException(400, "script_text is required")

    analyzer = get_script_analyzer()
    results = analyzer.analyze(script_text)

    return {
        "success": True,
        "schema_version": "pulse_narrative_v1",
        "scenes": [
            {
                "scene_id": r.scene_id,
                "dramatic_function": r.dramatic_function,
                "pendulum_position": r.pendulum_position,
                "estimated_energy": r.estimated_energy,
                "keywords": r.keywords,
                "suggested_scale": r.suggested_scale,
                "confidence": r.confidence,
            }
            for r in results
        ],
        "total_scenes": len(results),
    }


@router.post("/pulse/camelot/path")
async def cut_pulse_camelot_path(req: CutPulseCamelotPathRequest) -> dict[str, Any]:
    """
    MARKER_179.5 — Analyze a Camelot key path for harmonic smoothness.
    """
    engine = get_camelot_engine()
    try:
        path = engine.plan_path(req.keys)
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "success": True,
        "schema_version": "pulse_camelot_path_v1",
        "keys": path.keys,
        "total_distance": path.total_distance,
        "max_jump": path.max_jump,
        "smoothness": round(path.smoothness, 3),
        "transitions": [
            {
                "from": t.from_key,
                "to": t.to_key,
                "distance": t.distance,
                "quality": t.quality,
            }
            for t in path.transitions
        ],
    }


@router.get("/pulse/camelot/distance")
async def cut_pulse_camelot_distance(key_a: str, key_b: str) -> dict[str, Any]:
    """
    MARKER_179.5 — Get harmonic distance between two Camelot keys.
    """
    engine = get_camelot_engine()
    try:
        d = engine.distance(key_a, key_b)
        c = engine.compatibility(key_a, key_b)
        q = engine.transition_quality(key_a, key_b)
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "success": True,
        "key_a": key_a,
        "key_b": key_b,
        "distance": d,
        "compatibility": c,
        "quality": q,
    }


@router.get("/pulse/camelot/neighbors")
async def cut_pulse_camelot_neighbors(key: str) -> dict[str, Any]:
    """
    MARKER_179.5 — Get harmonically compatible neighbors for a key.
    """
    engine = get_camelot_engine()
    try:
        nbrs = engine.neighbors(key)
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "success": True,
        "key": key,
        "neighbors": nbrs,
        "musical_key": engine.musical_from_key(key),
    }


@router.post("/pulse/camelot/suggest-next")
async def cut_pulse_camelot_suggest_next(
    req: CutPulseCamelotSuggestRequest,
) -> dict[str, Any]:
    """
    MARKER_179.5 — Suggest next Camelot key based on target pendulum.
    """
    engine = get_camelot_engine()
    try:
        suggestions = engine.suggest_next(
            req.current_key,
            req.target_pendulum,
            prefer_dramatic=req.prefer_dramatic,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "success": True,
        "current_key": req.current_key,
        "target_pendulum": req.target_pendulum,
        "suggestions": [
            {"key": k, "score": s, "musical_key": engine.musical_from_key(k)}
            for k, s in suggestions
        ],
    }


# ---------------------------------------------------------------------------
# MARKER_179.6_ENERGY_CRITICS_ENDPOINT
# ---------------------------------------------------------------------------


class CutPulseEnergyCriticsRequest(BaseModel):
    """Request to compute energy critics for a film from script text."""
    script_text: str
    # Optional per-scene audio overrides
    audio_bpm: float | None = None
    audio_key: str | None = None
    audio_camelot_key: str | None = None


@router.post("/pulse/energy-critics")
async def cut_pulse_energy_critics(req: CutPulseEnergyCriticsRequest) -> dict[str, Any]:
    """
    MARKER_179.6 — Compute all 5 energy critics for a film.

    Takes script text, scores each scene via PULSE conductor,
    then runs all energy critics on the resulting PulseScore sequence.

    Returns individual critic energies + weighted total.
    Lower total = better overall montage compatibility.
    """
    if not req.script_text:
        raise HTTPException(400, "script_text is required")

    conductor = get_pulse_conductor()
    analyzer = get_script_analyzer()

    # Analyze script into scenes
    narrative_scenes = analyzer.analyze(req.script_text)

    # Score each scene
    scores = []
    for nbpm in narrative_scenes:
        # Build optional audio signal
        audio = None
        if req.audio_bpm is not None or req.audio_camelot_key:
            engine = get_camelot_engine()
            camelot = req.audio_camelot_key or ""
            if not camelot and req.audio_key:
                camelot = engine.key_from_musical(req.audio_key) or ""
            audio = AudioBPM(
                bpm=req.audio_bpm or 120.0,
                key=req.audio_key or "",
                camelot_key=camelot,
                confidence=0.6,
            )

        score = conductor.score_scene(
            scene_id=nbpm.scene_id,
            narrative=nbpm,
            audio=audio,
        )
        scores.append(score)

    # Compute energy critics
    energies = compute_all_energies(scores)

    return {
        "success": True,
        "schema_version": "pulse_energy_critics_v1",
        "energies": energies,
        "scene_count": len(scores),
        "interpretation": {
            "total_label": _energy_label(energies["total"]),
            "advice": _energy_advice(energies),
        },
    }


def _energy_label(total: float) -> str:
    """Human-readable label for total energy."""
    if total < 0.2:
        return "excellent_harmony"
    elif total < 0.35:
        return "good_balance"
    elif total < 0.5:
        return "moderate_tension"
    elif total < 0.7:
        return "high_tension"
    else:
        return "extreme_conflict"


def _energy_advice(energies: Dict[str, float]) -> list[str]:
    """Generate actionable advice based on individual critic values."""
    advice = []
    if energies.get("pendulum_balance", 0) > 0.6:
        advice.append("Pendulum is monotonous — consider adding scenes with opposite emotional charge")
    if energies.get("camelot_proximity", 0) > 0.5:
        advice.append("Key transitions are jarring — try inserting bridge scenes with adjacent Camelot keys")
    if energies.get("music_scene_sync", 0) > 0.5:
        advice.append("Music-scene alignment shows frequent counterpoint — verify it's intentional")
    if energies.get("script_visual_match", 0) > 0.5:
        advice.append("Visual pacing doesn't match script energy — check cut density and motion intensity")
    if energies.get("energy_contour", 0) > 0.5:
        advice.append("Energy contour is spiky — smooth transitions between high/low energy scenes")
    if not advice:
        advice.append("Montage rhythm looks healthy — energy distribution is balanced")
    return advice


# ---------------------------------------------------------------------------
# MARKER_179.10_PULSE_TIMELINE_BRIDGE
# ---------------------------------------------------------------------------


class CutPulseEnrichScriptRequest(BaseModel):
    """Enrich scene graph from script text."""
    timeline_id: str
    script_text: str


@router.post("/pulse/enrich-from-script/{timeline_id}")
async def cut_pulse_enrich_from_script(
    timeline_id: str,
    script_text: str = "",
) -> dict[str, Any]:
    """
    MARKER_179.10 — Analyze script and attach PULSE data to scene graph nodes.

    Matches script scenes to scene graph nodes by index.
    Returns enriched scene count and partiture summary.
    """
    if not script_text:
        raise HTTPException(400, "script_text is required")

    store = CutProjectStore.current()
    if not store:
        raise HTTPException(400, "No CUT project loaded")

    scene_graph = store.get_scene_graph(timeline_id)
    if not scene_graph:
        raise HTTPException(404, f"No scene graph for timeline {timeline_id}")

    bridge = get_pulse_timeline_bridge()
    enriched = bridge.enrich_from_script(scene_graph, script_text)

    # Save back
    store.set_scene_graph(timeline_id, enriched)

    # Compute partiture
    partiture = bridge.compute_partiture(enriched)

    return {
        "success": True,
        "schema_version": "pulse_enrich_v1",
        "enriched_scenes": partiture["scene_count"],
        "tonic_key": partiture["tonic_key"],
        "tonic_musical": partiture["tonic_musical"],
        "energy_critics": partiture["energy_critics"],
        "camelot_path": partiture["camelot_path"],
    }


@router.post("/pulse/enrich-from-timeline/{timeline_id}")
async def cut_pulse_enrich_from_timeline(timeline_id: str) -> dict[str, Any]:
    """
    MARKER_179.10 — Extract visual signals from timeline clips and enrich scene graph.

    Computes cuts_per_minute and motion_intensity from clip data.
    """
    store = CutProjectStore.current()
    if not store:
        raise HTTPException(400, "No CUT project loaded")

    scene_graph = store.get_scene_graph(timeline_id)
    timeline_state = store.get_timeline_state(timeline_id)
    if not scene_graph:
        raise HTTPException(404, f"No scene graph for timeline {timeline_id}")
    if not timeline_state:
        raise HTTPException(404, f"No timeline state for {timeline_id}")

    bridge = get_pulse_timeline_bridge()
    enriched = bridge.enrich_from_timeline(scene_graph, timeline_state)

    store.set_scene_graph(timeline_id, enriched)
    partiture = bridge.compute_partiture(enriched)

    return {
        "success": True,
        "schema_version": "pulse_enrich_v1",
        "enriched_scenes": partiture["scene_count"],
        "energy_critics": partiture["energy_critics"],
    }


@router.get("/pulse/partiture/{timeline_id}")
async def cut_pulse_partiture(timeline_id: str) -> dict[str, Any]:
    """
    MARKER_179.10 — Get full film partiture from enriched scene graph.

    Returns scores, camelot path, energy critics, tonic key.
    """
    store = CutProjectStore.current()
    if not store:
        raise HTTPException(400, "No CUT project loaded")

    scene_graph = store.get_scene_graph(timeline_id)
    if not scene_graph:
        raise HTTPException(404, f"No scene graph for timeline {timeline_id}")

    bridge = get_pulse_timeline_bridge()
    partiture = bridge.compute_partiture(scene_graph)

    return {
        "success": True,
        **partiture,
    }


@router.get("/pulse/scene-summary/{timeline_id}")
async def cut_pulse_scene_summary(timeline_id: str) -> dict[str, Any]:
    """
    MARKER_179.10 — Compact PULSE summary for all scenes.

    Returns per-scene camelot_key, pendulum, dramatic_function for frontend overlay.
    """
    store = CutProjectStore.current()
    if not store:
        raise HTTPException(400, "No CUT project loaded")

    scene_graph = store.get_scene_graph(timeline_id)
    if not scene_graph:
        raise HTTPException(404, f"No scene graph for timeline {timeline_id}")

    bridge = get_pulse_timeline_bridge()
    summary = bridge.get_scene_pulse_summary(scene_graph)

    return {
        "success": True,
        "schema_version": "pulse_scene_summary_v1",
        "scenes": summary,
        "total": len(summary),
    }


# ---------------------------------------------------------------------------
# MARKER_179.12_GENRE_CALIBRATION_ENDPOINTS
# ---------------------------------------------------------------------------


@router.get("/pulse/genre-profiles")
async def cut_pulse_genre_profiles() -> dict[str, Any]:
    """
    MARKER_179.12 — List all available genre calibration profiles.
    """
    return {
        "success": True,
        "profiles": list_genre_profiles(),
        "total": len(list_genre_profiles()),
    }


class CutPulseCalibratedRequest(BaseModel):
    """Request for genre-calibrated energy critics."""
    script_text: str
    genre: str = "drama"
    audio_bpm: float | None = None
    audio_key: str | None = None
    audio_camelot_key: str | None = None


@router.post("/pulse/energy-critics-calibrated")
async def cut_pulse_energy_critics_calibrated(
    req: CutPulseCalibratedRequest,
) -> dict[str, Any]:
    """
    MARKER_179.12 — Genre-aware energy critics with calibration.

    Same as /pulse/energy-critics but applies genre-specific multipliers.
    High raw scores that are normal for the genre get reduced.

    Validated on: Nights of Cabiria (art_house), Mad Max (action),
    Mulholland Drive (surreal) — Grok 179.0A research.
    """
    if not req.script_text:
        raise HTTPException(400, "script_text is required")

    conductor = get_pulse_conductor()
    analyzer = get_script_analyzer()

    narrative_scenes = analyzer.analyze(req.script_text)
    scores = []
    for nbpm in narrative_scenes:
        audio = None
        if req.audio_bpm is not None or req.audio_camelot_key:
            engine = get_camelot_engine()
            camelot = req.audio_camelot_key or ""
            if not camelot and req.audio_key:
                camelot = engine.key_from_musical(req.audio_key) or ""
            audio = AudioBPM(
                bpm=req.audio_bpm or 120.0,
                key=req.audio_key or "",
                camelot_key=camelot,
                confidence=0.6,
            )
        score = conductor.score_scene(
            scene_id=nbpm.scene_id,
            narrative=nbpm,
            audio=audio,
        )
        scores.append(score)

    result = compute_calibrated_energies(scores, genre=req.genre)

    return {
        "success": True,
        "schema_version": "pulse_energy_critics_calibrated_v1",
        "scene_count": len(scores),
        **result,
    }


# ---------------------------------------------------------------------------
# PULSE Triangle + StorySpace3D endpoints — Phase 179 Sprint 5
# MARKER_179.14_TRIANGLE_STORYSPACE_ENDPOINTS
# ---------------------------------------------------------------------------


class CutPulseTriangleEnergiesRequest(BaseModel):
    """Request for McKee Triangle-calibrated energy critics."""
    script_text: str
    arch: float | None = None
    mini: float | None = None
    anti: float | None = None
    genre: str | None = None


@router.post("/pulse/triangle-energies")
async def cut_pulse_triangle_energies(
    req: CutPulseTriangleEnergiesRequest,
) -> dict[str, Any]:
    """
    MARKER_179.14 — McKee Triangle-calibrated energy critics.

    Replaces discrete genre calibration with continuous barycentric interpolation.
    If arch/mini/anti provided, uses explicit triangle position.
    If genre provided, maps genre → triangle position.
    If neither, infers from scores' scales.
    """
    analyzer = get_script_analyzer()
    conductor = get_pulse_conductor()

    narrative_scenes = analyzer.analyze(req.script_text)
    scores = []
    for nbpm in narrative_scenes:
        score = conductor.score_scene(scene_id=nbpm.scene_id, narrative=nbpm)
        scores.append(score)

    if not scores:
        return {"success": False, "error": "No scenes detected in script"}

    # Determine triangle position
    triangle = None
    if req.arch is not None and req.mini is not None and req.anti is not None:
        triangle = TrianglePosition(arch=req.arch, mini=req.mini, anti=req.anti)
    elif req.genre:
        triangle = genre_to_triangle(req.genre)
    # else: inferred inside compute_triangle_energies

    result = compute_triangle_energies(scores, triangle=triangle)

    return {
        "success": True,
        "schema_version": "pulse_triangle_energies_v1",
        "scene_count": len(scores),
        **result,
    }


@router.get("/pulse/triangle-weights")
async def cut_pulse_triangle_weights(
    arch: float = 0.5,
    mini: float = 0.3,
    anti: float = 0.2,
) -> dict[str, Any]:
    """
    MARKER_179.14 — Preview interpolated critic weights for a triangle position.

    Pure computation, no script required. Useful for UI sliders.
    """
    triangle = TrianglePosition(arch=arch, mini=mini, anti=anti)
    weights = interpolate_critic_weights(triangle)

    return {
        "success": True,
        "schema_version": "pulse_triangle_weights_v1",
        "triangle": triangle.to_dict(),
        "dominant": triangle.dominant,
        "mckee_height": round(triangle.mckee_height, 3),
        "weights": weights,
    }


class CutPulseChaosIndexRequest(BaseModel):
    """Request for chaos index computation."""
    script_text: str


@router.post("/pulse/chaos-index")
async def cut_pulse_chaos_index(
    req: CutPulseChaosIndexRequest,
) -> dict[str, Any]:
    """
    MARKER_179.14 — Compute chaos index (6th energy critic).

    Measures unpredictability of transitions: key jumps, pendulum variance,
    energy direction reversals. High chaos = antiplot territory.
    """
    analyzer = get_script_analyzer()
    conductor = get_pulse_conductor()

    narrative_scenes = analyzer.analyze(req.script_text)
    scores = []
    for nbpm in narrative_scenes:
        score = conductor.score_scene(scene_id=nbpm.scene_id, narrative=nbpm)
        scores.append(score)

    if len(scores) < 3:
        return {
            "success": True,
            "schema_version": "pulse_chaos_index_v1",
            "chaos_index": 0.0,
            "scene_count": len(scores),
            "note": "Need at least 3 scenes to compute chaos index",
        }

    ci = chaos_index(scores)

    return {
        "success": True,
        "schema_version": "pulse_chaos_index_v1",
        "chaos_index": ci,
        "scene_count": len(scores),
        "interpretation": (
            "low_chaos" if ci < 0.3
            else "moderate_chaos" if ci < 0.6
            else "high_chaos"
        ),
    }


class CutPulseStorySpaceRequest(BaseModel):
    """Request for StorySpace3D point generation."""
    script_text: str


@router.post("/pulse/story-space")
async def cut_pulse_story_space(
    req: CutPulseStorySpaceRequest,
) -> dict[str, Any]:
    """
    MARKER_179.14 — Generate StorySpace3D points for frontend visualization.

    Each scene becomes a point in 3D space:
    - X/Y: Camelot wheel angle (horizontal plane)
    - Z: McKee triangle height (archplot=1, antiplot=0)
    - Color: pendulum position (-1..+1)
    - Size: energy level
    """
    analyzer = get_script_analyzer()
    conductor = get_pulse_conductor()

    narrative_scenes = analyzer.analyze(req.script_text)
    scores = []
    for nbpm in narrative_scenes:
        score = conductor.score_scene(scene_id=nbpm.scene_id, narrative=nbpm)
        scores.append(score)

    if not scores:
        return {"success": False, "error": "No scenes detected in script"}

    points = scores_to_story_space(scores)

    return {
        "success": True,
        "schema_version": "pulse_story_space_v1",
        "scene_count": len(points),
        "points": [p.to_dict() for p in points],
    }


@router.post("/pulse/story-space/{timeline_id}")
async def cut_pulse_story_space_from_timeline(
    timeline_id: str,
) -> dict[str, Any]:
    """
    MARKER_179.14 — Generate StorySpace3D points from existing timeline scene graph.

    Reads enriched scene graph (must be enriched first via /pulse/enrich-*),
    reconstructs PulseScores, and converts to StorySpacePoints.
    """
    store = CutProjectStore.get_instance()
    scene_graph = store.load_scene_graph(timeline_id)
    if not scene_graph:
        return {"success": False, "error": f"No scene graph for timeline {timeline_id}"}

    # Reconstruct PulseScores from enriched scene graph
    from src.services.pulse_conductor import PulseScore
    scene_nodes = [
        n for n in scene_graph.get("nodes", [])
        if n.get("node_type") == "scene"
    ]

    scores = []
    for node in scene_nodes:
        pd = node.get("metadata", {}).get("pulse_data", {})
        if pd:
            score = PulseScore(
                scene_id=node.get("node_id", ""),
                camelot_key=pd.get("camelot_key", "8B"),
                scale=pd.get("scale", "Ionian"),
                pendulum_position=pd.get("pendulum_position", 0.0),
                dramatic_function=pd.get("dramatic_function", ""),
                energy_profile=pd.get("energy_profile", ""),
                counterpoint_pair=pd.get("counterpoint_pair", ""),
                confidence=pd.get("confidence", 0.0),
                alignment=pd.get("alignment", "sync"),
                itten_colors=pd.get("itten_colors", []),
                music_genres=pd.get("music_genres", []),
            )
            scores.append(score)

    if not scores:
        return {"success": False, "error": "No enriched scenes found — run /pulse/enrich-* first"}

    points = scores_to_story_space(scores)

    return {
        "success": True,
        "schema_version": "pulse_story_space_v1",
        "timeline_id": timeline_id,
        "scene_count": len(points),
        "points": [p.to_dict() for p in points],
    }


# ---------------------------------------------------------------------------
# PULSE SRT → NarrativeBPM Bridge — Phase 179 Sprint 5
# MARKER_179.15_SRT_NARRATIVE_BRIDGE
# ---------------------------------------------------------------------------


class CutPulseSrtAnalyzeRequest(BaseModel):
    """Request to analyze SRT/VTT subtitle content."""
    srt_content: str
    gap_threshold_sec: float = 3.0
    max_scene_duration_sec: float = 120.0


@router.post("/pulse/srt-to-narrative")
async def cut_pulse_srt_to_narrative(
    req: CutPulseSrtAnalyzeRequest,
) -> dict[str, Any]:
    """
    MARKER_179.15 — Parse SRT/VTT subtitles → NarrativeBPM scenes.

    Groups subtitle blocks into scenes by timing gaps, then analyzes
    each scene for dramatic function, pendulum, and energy.
    Returns scenes with timing metadata for timeline alignment.
    """
    results = srt_to_narrative_bpm_with_timing(
        content=req.srt_content,
        gap_threshold_sec=req.gap_threshold_sec,
        max_scene_duration_sec=req.max_scene_duration_sec,
    )

    return {
        "success": True,
        "schema_version": "pulse_srt_narrative_v1",
        "scene_count": len(results),
        "scenes": results,
    }


@router.post("/pulse/srt-to-story-space")
async def cut_pulse_srt_to_story_space(
    req: CutPulseSrtAnalyzeRequest,
) -> dict[str, Any]:
    """
    MARKER_179.15 — SRT/VTT → full PULSE pipeline → StorySpace3D points.

    End-to-end: parse subtitles → NarrativeBPM → PulseScore → StorySpacePoint[].
    Ready for Three.js visualization.
    """
    conductor = get_pulse_conductor()

    narrative_scenes = srt_to_narrative_bpm(
        content=req.srt_content,
        gap_threshold_sec=req.gap_threshold_sec,
        max_scene_duration_sec=req.max_scene_duration_sec,
    )

    if not narrative_scenes:
        return {"success": False, "error": "No scenes detected in SRT content"}

    scores = []
    for nbpm in narrative_scenes:
        score = conductor.score_scene(scene_id=nbpm.scene_id, narrative=nbpm)
        scores.append(score)

    points = scores_to_story_space(scores)

    # Also compute chaos index for the whole sequence
    ci = chaos_index(scores) if len(scores) >= 3 else 0.0

    return {
        "success": True,
        "schema_version": "pulse_srt_story_space_v1",
        "scene_count": len(points),
        "chaos_index": ci,
        "points": [p.to_dict() for p in points],
    }


# ---------------------------------------------------------------------------
# PULSE Favorite Marker → StorySpacePoint — Phase 179 Sprint 5
# MARKER_179.20_MARKER_STORYSPACE
# ---------------------------------------------------------------------------


class CutPulseMarkerStorySpaceRequest(BaseModel):
    """Request to map markers to StorySpace3D points."""
    script_text: str
    sandbox_root: str
    kind_filter: str = "favorite"


@router.post("/pulse/markers-to-story-space")
async def cut_pulse_markers_to_story_space(
    req: CutPulseMarkerStorySpaceRequest,
) -> dict[str, Any]:
    """
    MARKER_179.20 — Map favorite markers to StorySpace3D points.

    1. Load marker bundle from project store
    2. Filter by kind (default: favorite)
    3. Score script via PULSE conductor
    4. Align each marker to nearest scene
    5. Return StorySpacePoints with marker metadata
    """
    # Load markers
    store = CutProjectStore(req.sandbox_root)
    marker_bundle = store.load_time_marker_bundle()
    if not marker_bundle:
        return {"success": False, "error": "No marker bundle found"}

    items = marker_bundle.get("items", [])
    filtered = [
        m for m in items
        if m.get("kind") == req.kind_filter
        and m.get("status", "active") != "archived"
    ]

    if not filtered:
        return {
            "success": True,
            "schema_version": "pulse_marker_story_space_v1",
            "marker_count": 0,
            "points": [],
            "note": f"No active '{req.kind_filter}' markers found",
        }

    # Score script
    analyzer = get_script_analyzer()
    conductor = get_pulse_conductor()

    narrative_scenes = analyzer.analyze(req.script_text)
    scores = []
    for nbpm in narrative_scenes:
        score = conductor.score_scene(scene_id=nbpm.scene_id, narrative=nbpm)
        scores.append(score)

    if not scores:
        return {"success": False, "error": "No scenes detected in script"}

    # Map markers to story space
    points = markers_to_story_space_points(filtered, scores)

    return {
        "success": True,
        "schema_version": "pulse_marker_story_space_v1",
        "marker_count": len(points),
        "scene_count": len(scores),
        "points": points,
    }


# ---------------------------------------------------------------------------
# MARKER_180.8 — BPM Markers endpoint
# Returns all 3 BPM sources as timestamped arrays + computed sync points
# Architecture doc §5.1, §5.2
# ---------------------------------------------------------------------------


class CutPulseBPMMarkersRequest(BaseModel):
    """Request for BPM markers — needs timeline context."""

    timeline_id: str = "main"
    sandbox_root: str = ""
    # Optional script text for script BPM calculation
    script_text: str = ""
    # Sync tolerance: how close beats must be to count as sync (seconds)
    sync_tolerance_sec: float = 0.083  # ±2 frames at 24fps


@router.post("/pulse/bpm-markers")
async def cut_pulse_bpm_markers(
    req: CutPulseBPMMarkersRequest,
) -> dict[str, Any]:
    """
    MARKER_180.8 — BPM markers for timeline track.

    Returns 3 BPM sources + computed sync points (orange dots):
    - audio_beats: from AudioBPM downbeats (green dots)
    - visual_cuts: from VisualBPM scene boundaries (blue dots)
    - script_events: from NarrativeBPM script analysis (white dots)
    - sync_points: where all 3 coincide within tolerance (orange dots)

    Architecture doc: VETKA_CUT_Interface_Architecture_v1.docx §5.1, §5.2
    """
    audio_beats: list[dict[str, Any]] = []
    visual_cuts: list[dict[str, Any]] = []
    script_events: list[dict[str, Any]] = []

    # --- Audio BPM: get from partiture/enriched scene graph ---
    store = CutProjectStore.get_instance()
    scene_graph = store.load_scene_graph(req.timeline_id) if store else None

    if scene_graph:
        scene_nodes = [
            n for n in scene_graph.get("nodes", [])
            if n.get("node_type") == "scene"
        ]
        for node in scene_nodes:
            pulse_data = node.get("metadata", {}).get("pulse_data", {})
            # Audio beats from downbeats
            if pulse_data.get("has_audio"):
                audio_bpm_val = pulse_data.get("audio_bpm", 120)
                start_sec = node.get("metadata", {}).get("start_sec", 0)
                end_sec = node.get("metadata", {}).get("end_sec", start_sec + 10)
                # Generate beat positions from BPM
                if audio_bpm_val > 0:
                    beat_interval = 60.0 / audio_bpm_val
                    t = start_sec
                    while t < end_sec:
                        audio_beats.append({
                            "sec": round(t, 3),
                            "bpm": round(audio_bpm_val, 1),
                            "source": "audio",
                        })
                        t += beat_interval

            # Visual cuts from scene boundaries
            if pulse_data.get("has_visual"):
                start_sec = node.get("metadata", {}).get("start_sec", 0)
                visual_cuts.append({
                    "sec": round(start_sec, 3),
                    "source": "visual",
                })

    # --- Script BPM: from script text analysis ---
    if req.script_text:
        analyzer = get_script_analyzer()
        narrative_scenes = analyzer.analyze(req.script_text)
        # Each scene transition is a script event
        # Script BPM = events per minute (§5.3)
        page_duration_sec = 60.0  # 1 page ≈ 60 seconds
        for i, nbpm in enumerate(narrative_scenes):
            event_sec = i * page_duration_sec / max(len(narrative_scenes), 1) * len(narrative_scenes)
            # Rough time: distribute evenly for now (SRT bridge gives real times)
            event_sec = i * page_duration_sec
            script_events.append({
                "sec": round(event_sec, 3),
                "type": nbpm.dramatic_function,
                "energy": round(nbpm.estimated_energy, 3),
                "scene_id": nbpm.scene_id,
                "source": "script",
            })
    elif scene_graph:
        # Fall back to scene boundaries as script events
        scene_nodes = [
            n for n in scene_graph.get("nodes", [])
            if n.get("node_type") == "scene"
        ]
        for node in scene_nodes:
            start_sec = node.get("metadata", {}).get("start_sec", 0)
            pulse_data = node.get("metadata", {}).get("pulse_data", {})
            script_events.append({
                "sec": round(start_sec, 3),
                "type": pulse_data.get("dramatic_function", "unknown"),
                "energy": round(pulse_data.get("energy", 0.5), 3),
                "scene_id": node.get("node_id", ""),
                "source": "script",
            })

    # --- Compute sync points (orange): where sources coincide ---
    sync_points: list[dict[str, Any]] = []
    tolerance = req.sync_tolerance_sec

    # Collect all timestamps
    audio_times = [b["sec"] for b in audio_beats]
    visual_times = [v["sec"] for v in visual_cuts]
    script_times = [s["sec"] for s in script_events]

    # For each audio beat, check if visual AND script are nearby
    for at in audio_times:
        has_visual = any(abs(vt - at) <= tolerance for vt in visual_times)
        has_script = any(abs(st - at) <= tolerance for st in script_times)
        if has_visual and has_script:
            sync_points.append({
                "sec": round(at, 3),
                "strength": 1.0,
                "sources": ["audio", "visual", "script"],
            })
        elif has_visual or has_script:
            # Partial sync — 2 of 3 sources
            sources = ["audio"]
            if has_visual:
                sources.append("visual")
            if has_script:
                sources.append("script")
            sync_points.append({
                "sec": round(at, 3),
                "strength": 0.67,
                "sources": sources,
            })

    # Also check visual×script pairs that have no audio
    for vt in visual_times:
        has_audio = any(abs(at - vt) <= tolerance for at in audio_times)
        if has_audio:
            continue  # already handled above
        has_script = any(abs(st - vt) <= tolerance for st in script_times)
        if has_script:
            sync_points.append({
                "sec": round(vt, 3),
                "strength": 0.67,
                "sources": ["visual", "script"],
            })

    # Deduplicate sync points within tolerance
    deduped_sync: list[dict[str, Any]] = []
    for sp in sorted(sync_points, key=lambda x: x["sec"]):
        if not deduped_sync or abs(sp["sec"] - deduped_sync[-1]["sec"]) > tolerance:
            deduped_sync.append(sp)
        elif sp["strength"] > deduped_sync[-1]["strength"]:
            deduped_sync[-1] = sp  # keep the stronger one

    return {
        "success": True,
        "schema_version": "pulse_bpm_markers_v1",
        "audio_beats": audio_beats,
        "audio_beat_count": len(audio_beats),
        "visual_cuts": visual_cuts,
        "visual_cut_count": len(visual_cuts),
        "script_events": script_events,
        "script_event_count": len(script_events),
        "sync_points": deduped_sync,
        "sync_point_count": len(deduped_sync),
        "sync_tolerance_sec": tolerance,
    }


# ---------------------------------------------------------------------------
# MARKER_180.13 — PULSE Auto-Montage endpoint
# Architecture doc §7: 3 modes, always new timeline, never overwrite
# ---------------------------------------------------------------------------


class CutPulseAutoMontageRequest(BaseModel):
    """Request for auto-montage."""

    mode: str = "favorites"  # "favorites" | "script" | "music"
    project_name: str = "project"
    version: int = 1
    sandbox_root: str = ""
    timeline_id: str = "main"
    # Mode-specific params
    script_text: str = ""  # for script mode
    order_by: str = "time"  # for favorites mode: "time" | "energy" | "script"
    # Music mode
    music_bpm: float = 120.0
    music_key: str = "8B"
    music_camelot_key: str = "8B"


@router.post("/pulse/auto-montage")
async def cut_pulse_auto_montage(
    req: CutPulseAutoMontageRequest,
) -> dict[str, Any]:
    """
    MARKER_180.13 — PULSE Auto-Montage: 3 modes, always creates new timeline.

    Modes:
    - favorites: Assembles from favorite markers in marker bundle
    - script: Matches script scenes to available materials
    - music: Matches materials to music track via Camelot/mood

    Architecture doc §7.1 SAFETY: "NEVER overwrite existing work."
    """
    from src.services.pulse_auto_montage import (
        FavoriteMarker,
        MaterialAsset,
        get_auto_montage,
    )
    from src.services.pulse_conductor import AudioBPM

    engine = get_auto_montage()

    if req.mode == "favorites":
        # Load markers from project store
        store = CutProjectStore.get_instance()
        marker_bundle = store.load_time_marker_bundle() if store else None

        markers: list[FavoriteMarker] = []
        if marker_bundle:
            for item in marker_bundle.get("items", []):
                if item.get("kind") == "favorite" and item.get("status", "active") != "archived":
                    markers.append(FavoriteMarker(
                        marker_id=item.get("marker_id", ""),
                        media_path=item.get("media_path", ""),
                        start_sec=item.get("start_sec", 0),
                        end_sec=item.get("end_sec", 0),
                        score=item.get("score", 1.0),
                        text=item.get("text", ""),
                    ))

        result = engine.assemble_favorites(
            markers=markers,
            project_name=req.project_name,
            version=req.version,
            order_by=req.order_by,
        )

    elif req.mode == "script":
        # Gather materials from scene graph
        store = CutProjectStore.get_instance()
        scene_graph = store.load_scene_graph(req.timeline_id) if store else None

        materials: list[MaterialAsset] = []
        if scene_graph:
            for node in scene_graph.get("nodes", []):
                if node.get("node_type") in ("clip", "take", "asset"):
                    meta = node.get("metadata", {})
                    pulse = meta.get("pulse_data", {})
                    materials.append(MaterialAsset(
                        asset_id=node.get("node_id", ""),
                        source_path=meta.get("source_path", ""),
                        duration_sec=meta.get("duration_sec", 30.0),
                        camelot_key=pulse.get("camelot_key", ""),
                        energy=pulse.get("energy", 0.5),
                        pendulum=pulse.get("pendulum_position", 0.0),
                        scene_id=meta.get("scene_id", ""),
                    ))

        result = engine.assemble_from_script(
            script_text=req.script_text,
            materials=materials,
            project_name=req.project_name,
            version=req.version,
        )

    elif req.mode == "music":
        # Build AudioBPM from request
        music = AudioBPM(
            bpm=req.music_bpm,
            key=req.music_key,
            camelot_key=req.music_camelot_key,
        )

        # Gather materials
        store = CutProjectStore.get_instance()
        scene_graph = store.load_scene_graph(req.timeline_id) if store else None

        materials_m: list[MaterialAsset] = []
        if scene_graph:
            for node in scene_graph.get("nodes", []):
                if node.get("node_type") in ("clip", "take", "asset"):
                    meta = node.get("metadata", {})
                    pulse = meta.get("pulse_data", {})
                    materials_m.append(MaterialAsset(
                        asset_id=node.get("node_id", ""),
                        source_path=meta.get("source_path", ""),
                        duration_sec=meta.get("duration_sec", 30.0),
                        camelot_key=pulse.get("camelot_key", ""),
                        energy=pulse.get("energy", 0.5),
                        pendulum=pulse.get("pendulum_position", 0.0),
                    ))

        result = engine.assemble_from_music(
            music_audio=music,
            materials=materials_m,
            project_name=req.project_name,
            version=req.version,
        )

    else:
        return {"success": False, "error": f"Unknown mode: {req.mode}. Use 'favorites', 'script', or 'music'."}

    return {
        "success": True,
        "schema_version": "pulse_auto_montage_v1",
        **result.to_dict(),
    }


# ---------------------------------------------------------------------------
# MARKER_180.17 — DAG Project endpoint
# Returns project asset DAG: nodes by cluster, edges by usage in script
# Architecture doc §2.2, §8
# ---------------------------------------------------------------------------

# Cluster types from Architecture doc §2.2
_DAG_CLUSTER_TYPES = {
    "character", "location", "take", "dub",
    "music", "sfx", "graphics", "other",
}


def _classify_asset_cluster(node: dict) -> str:
    """Classify a scene graph node into a DAG cluster type."""
    node_type = node.get("node_type", "")
    meta = node.get("metadata", {})
    tags = meta.get("tags", [])
    source_path = meta.get("source_path", "")
    label = node.get("label", "").lower()

    # By node_type
    if node_type in ("character", "person"):
        return "character"
    if node_type in ("location", "place", "scene"):
        return "location"
    if node_type in ("take", "clip"):
        return "take"
    if node_type in ("dub", "voiceover"):
        return "dub"

    # By file extension
    if source_path:
        ext = source_path.rsplit(".", 1)[-1].lower() if "." in source_path else ""
        if ext in ("mp3", "wav", "aac", "flac", "ogg"):
            if any(t in tags for t in ["sfx", "sound_effect", "foley"]):
                return "sfx"
            return "music"
        if ext in ("png", "jpg", "jpeg", "svg", "psd", "ai"):
            return "graphics"

    # By tags
    if any(t in tags for t in ["character", "person", "actor"]):
        return "character"
    if any(t in tags for t in ["location", "set", "place"]):
        return "location"
    if any(t in tags for t in ["music", "score", "soundtrack"]):
        return "music"
    if any(t in tags for t in ["sfx", "foley", "sound"]):
        return "sfx"
    if any(t in tags for t in ["graphic", "title", "overlay"]):
        return "graphics"

    return "other"


@router.get("/project/dag/{timeline_id}")
async def cut_project_dag(
    timeline_id: str = "main",
) -> dict[str, Any]:
    """
    MARKER_180.17 — DAG Project: asset graph organized by clusters.

    Returns nodes grouped by cluster type (Characters, Locations, Takes,
    Music, SFX, Graphics) with edges showing asset-to-scene connections.
    Nodes linked to the active script line glow blue (computed by frontend).

    Architecture doc §2.2: "Material organized by clusters"
    Architecture doc §8: "DAG as universal view mode"
    """
    store = CutProjectStore.get_instance()
    scene_graph = store.load_scene_graph(timeline_id) if store else None

    if not scene_graph:
        return {
            "success": True,
            "schema_version": "cut_project_dag_v1",
            "node_count": 0,
            "edge_count": 0,
            "clusters": {},
            "nodes": [],
            "edges": [],
        }

    raw_nodes = scene_graph.get("nodes", [])
    raw_edges = scene_graph.get("edges", [])

    # Build DAG nodes with cluster classification
    dag_nodes: list[dict] = []
    clusters: dict[str, list[str]] = {ct: [] for ct in _DAG_CLUSTER_TYPES}

    for node in raw_nodes:
        cluster = _classify_asset_cluster(node)
        node_id = node.get("node_id", "")
        meta = node.get("metadata", {})
        pulse_data = meta.get("pulse_data", {})

        dag_node = {
            "node_id": node_id,
            "label": node.get("label", node_id),
            "node_type": node.get("node_type", "unknown"),
            "cluster": cluster,
            "source_path": meta.get("source_path", ""),
            "duration_sec": meta.get("duration_sec"),
            "start_sec": meta.get("start_sec"),
            "end_sec": meta.get("end_sec"),
            "thumbnail_url": meta.get("poster_url", ""),
            # PULSE data for inspector
            "camelot_key": pulse_data.get("camelot_key", ""),
            "pendulum": pulse_data.get("pendulum_position", 0),
            "energy": pulse_data.get("energy", 0.5),
            "dramatic_function": pulse_data.get("dramatic_function", ""),
            # Linked scenes (for blue glow on active script line)
            "linked_scene_ids": meta.get("linked_scenes", []),
        }
        dag_nodes.append(dag_node)
        clusters[cluster].append(node_id)

    # Build edges (asset→scene, scene→scene, etc.)
    dag_edges: list[dict] = []
    for edge in raw_edges:
        dag_edges.append({
            "source": edge.get("source", ""),
            "target": edge.get("target", ""),
            "edge_type": edge.get("edge_type", "link"),
            "label": edge.get("label", ""),
        })

    # Remove empty clusters
    clusters = {k: v for k, v in clusters.items() if v}

    return {
        "success": True,
        "schema_version": "cut_project_dag_v1",
        "node_count": len(dag_nodes),
        "edge_count": len(dag_edges),
        "clusters": clusters,
        "cluster_summary": {k: len(v) for k, v in clusters.items()},
        "nodes": dag_nodes,
        "edges": dag_edges,
    }
