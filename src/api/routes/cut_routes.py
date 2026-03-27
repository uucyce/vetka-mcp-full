from __future__ import annotations

import asyncio
import base64
import json
import logging
import math
import mimetypes
import os
import re
import subprocess
import threading

logger = logging.getLogger("cut.routes")
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal
from uuid import uuid4

import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
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
from src.services.cut_codec_probe import probe_file, probe_duration
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

# MARKER_B41: Sub-routers extracted for modularity (reduce merge conflicts)
from src.api.routes.cut_routes_media import media_router
from src.api.routes.cut_routes_export import export_router
from src.api.routes.cut_routes_render import render_router
# MARKER_B_P2_HOTKEYS: Audio sub-router (scrubbing, level adjust, solo)
from src.api.routes.cut_routes_audio import audio_router

# MARKER_B65: Bootstrap sub-module extracted for modularity
from src.api.routes.cut_routes_bootstrap import (  # noqa: E402
    CutBootstrapRequest,
    _bootstrap_error,
    _build_initial_timeline_state,
    _execute_cut_bootstrap,
    _run_cut_bootstrap_job,
    _utc_now_iso,
    _infer_cut_media_modality,
)

router.include_router(media_router)
router.include_router(export_router)
router.include_router(render_router)
router.include_router(audio_router)  # MARKER_B_P2_HOTKEYS

# MARKER_BOTIO: Import sub-router — OTIO / Premiere XML / FCPXML / EDL import
from src.api.routes.cut_routes_import import import_router  # noqa: E402

router.include_router(import_router)

# MARKER_B70: PULSE sub-router extracted for modularity (26 endpoints, ~1300 lines)
from src.api.routes.cut_routes_pulse import pulse_router  # noqa: E402

router.include_router(pulse_router)

# MARKER_B70: Workers sub-router extracted for modularity (14 endpoints, ~3100 lines)
from src.api.routes.cut_routes_workers import (  # noqa: E402
    worker_router,
    _collect_project_jobs,
    _worker_job_error,
    _find_active_duplicate_job,
    _count_active_background_jobs_for_sandbox,
    _ACTIVE_JOB_STATES,
    _SANDBOX_BACKGROUND_LIMIT,
    _build_initial_scene_graph,  # MARKER_B74: moved to workers, re-imported for backward compat
    _infer_cut_asset_kind,       # MARKER_B74: moved to workers
)

router.include_router(worker_router)


# CutBootstrapRequest — moved to cut_routes_bootstrap.py (MARKER_B65)


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


# MARKER_B3: Sequence settings persistence
class CutSequenceSettingsRequest(BaseModel):
    sandbox_root: str
    project_id: str = ""
    framerate: float = Field(default=25, ge=1, le=120)
    timecode_format: str = "smpte"          # 'smpte' | 'milliseconds'
    drop_frame: bool = False
    start_timecode: str = "00:00:00:00"
    audio_sample_rate: int = Field(default=48000, ge=8000, le=192000)
    audio_bit_depth: int = Field(default=24, ge=8, le=64)
    resolution: str = "1080p"               # '4K' | '1080p' | '720p' | 'custom'
    width: int = Field(default=1920, ge=1, le=16384)
    height: int = Field(default=1080, ge=1, le=16384)
    color_space: str = "Rec.709"            # 'Rec.709' | 'Rec.2020' | 'DCI-P3'
    proxy_mode: str = "auto"                # 'full' | 'proxy' | 'auto'


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


class CutScanMatrixRequest(BaseModel):
    """MARKER_189.2 — Request model for scan-matrix-async."""
    sandbox_root: str
    project_id: str
    limit: int = Field(default=24, ge=1, le=128)
    waveform_bins: int = Field(default=120, ge=16, le=512)
    max_thumbs_per_file: int = Field(default=12, ge=1, le=48)
    run_stt: bool = True
    scene_threshold: float = Field(default=0.3, ge=0.05, le=0.95)
    scene_interval_sec: float = Field(default=1.0, ge=0.25, le=5.0)


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


# _bootstrap_error — moved to cut_routes_bootstrap.py (MARKER_B65)


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


# _utc_now_iso, _infer_cut_media_modality — moved to cut_routes_bootstrap.py (MARKER_B65)


# MARKER_B74: _infer_cut_asset_kind + _build_initial_scene_graph moved to cut_routes_workers.py
# Re-imported above for backward compat.


# _build_initial_timeline_state — moved to cut_routes_bootstrap.py (MARKER_B65)
# _build_initial_scene_graph — moved to cut_routes_workers.py (MARKER_B74)


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

        # MARKER_A2.1 — slip_clip: change source_in without moving clip on timeline
        # FCP7 slip = move content within fixed clip window (Ch.57)
        if op_type == "slip_clip":
            clip_id = str(op.get("clip_id") or "")
            source_in = float(op.get("source_in", 0.0))
            if source_in < 0:
                source_in = 0.0
            _, clip = _find_clip(state, clip_id)
            if clip is None:
                raise ValueError(f"clip not found: {clip_id}")
            clip["source_in"] = round(source_in, 4)
            applied_ops.append({"op": op_type, "clip_id": clip_id, "source_in": round(source_in, 4)})
            continue

        # MARKER_A2.2 — ripple_trim: trim edge + shift all subsequent clips in lane
        # FCP7 ripple trim = extend/shorten clip, everything after shifts (Ch.56)
        if op_type == "ripple_trim":
            clip_id = str(op.get("clip_id") or "")
            new_start = float(op.get("start_sec", -1))
            new_dur = float(op.get("duration_sec", -1))
            if new_dur <= 0:
                raise ValueError("duration_sec must be > 0")
            source_lane, clip = _find_clip(state, clip_id)
            if source_lane is None or clip is None:
                raise ValueError(f"clip not found: {clip_id}")
            old_start = float(clip.get("start_sec") or 0.0)
            old_dur = float(clip.get("duration_sec") or 0.0)
            old_end = old_start + old_dur
            # Apply new values
            if new_start >= 0:
                clip["start_sec"] = round(new_start, 4)
            else:
                new_start = old_start
            clip["duration_sec"] = round(new_dur, 4)
            new_end = new_start + new_dur
            # Delta = how much the clip's end moved
            delta = round(new_end - old_end, 4)
            # Shift all subsequent clips in same lane by delta
            if abs(delta) > 0.0001:
                for c in source_lane.get("clips", []):
                    if c is clip:
                        continue
                    c_start = float(c.get("start_sec") or 0.0)
                    if c_start >= old_end - 0.001:
                        c["start_sec"] = max(0.0, round(c_start + delta, 4))
            source_lane["clips"] = sorted(
                source_lane["clips"],
                key=lambda c: float(c.get("start_sec") or 0.0),
            )
            applied_ops.append({
                "op": op_type, "clip_id": clip_id,
                "lane_id": str(source_lane.get("lane_id") or ""),
                "start_sec": round(new_start, 4), "duration_sec": round(new_dur, 4),
                "delta_sec": delta,
            })
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

        # MARKER_UNDO-FIX: remove_clip — delete clip without closing gap (lift)
        if op_type == "remove_clip":
            clip_id = str(op.get("clip_id") or "")
            source_lane, clip = _find_clip(state, clip_id)
            if source_lane is None or clip is None:
                raise ValueError(f"clip not found: {clip_id}")
            lane_id = str(source_lane.get("lane_id") or "")
            source_lane["clips"] = [c for c in source_lane.get("clips", []) if str(c.get("clip_id") or "") != clip_id]
            applied_ops.append({"op": op_type, "clip_id": clip_id, "lane_id": lane_id})
            continue

        # MARKER_UNDO-FIX: replace_media — swap source_path on clip at playhead position
        if op_type == "replace_media":
            clip_id = str(op.get("clip_id") or "")
            source_path = str(op.get("source_path") or "")
            source_in = float(op.get("source_in", 0.0))
            if not source_path:
                raise ValueError("source_path is required for replace_media")
            _, clip = _find_clip(state, clip_id)
            if clip is None:
                raise ValueError(f"clip not found: {clip_id}")
            old_source = str(clip.get("source_path") or "")
            clip["source_path"] = source_path
            clip["source_in"] = round(max(0.0, source_in), 4)
            applied_ops.append({
                "op": op_type, "clip_id": clip_id,
                "source_path": source_path, "source_in": round(max(0.0, source_in), 4),
                "old_source_path": old_source,
            })
            continue

        # MARKER_UNDO-FIX: set_transition — add or remove transition_out on a clip
        if op_type == "set_transition":
            clip_id = str(op.get("clip_id") or "")
            _, clip = _find_clip(state, clip_id)
            if clip is None:
                raise ValueError(f"clip not found: {clip_id}")
            transition = op.get("transition")  # None = remove, dict = set
            old_transition = clip.get("transition_out")
            if transition is None:
                clip.pop("transition_out", None)
            else:
                clip["transition_out"] = {
                    "type": str(transition.get("type", "cross_dissolve")),
                    "duration_sec": float(transition.get("duration_sec", 1.0)),
                    "alignment": str(transition.get("alignment", "center")),
                }
            applied_ops.append({
                "op": op_type, "clip_id": clip_id,
                "transition": transition,
                "old_transition": old_transition,
            })
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

        # MARKER_B68: set_clip_color — persist color grading params for render pipeline
        if op_type == "set_clip_color":
            clip_id = str(op.get("clip_id") or "").strip()
            if not clip_id:
                continue
            _lane, clip = _find_clip(state, clip_id)
            if clip is None:
                continue
            # Write color grading fields onto clip dict
            color_fields = {
                "log_profile": str(op.get("log_profile") or "").strip() or None,
                "lut_path": str(op.get("lut_path") or "").strip() or None,
                "color_effects": op.get("color_effects") if isinstance(op.get("color_effects"), list) else None,
            }
            for key, val in color_fields.items():
                if val is not None:
                    clip[key] = val
                elif key in op:
                    # Explicitly set to empty = clear the field
                    clip.pop(key, None)
            applied_ops.append({"op": op_type, "clip_id": clip_id, **{k: v for k, v in color_fields.items() if v is not None}})
            continue

        # MARKER_B68: set_clip_meta — generic clip metadata update (rating, notes, shot_scale, etc.)
        if op_type == "set_clip_meta":
            clip_id = str(op.get("clip_id") or "").strip()
            if not clip_id:
                continue
            _lane, clip = _find_clip(state, clip_id)
            if clip is None:
                continue
            meta = op.get("meta") or {}
            if not isinstance(meta, dict):
                continue
            # Whitelist safe fields to prevent overwriting structural clip data
            _safe_meta_keys = {"rating", "notes", "label", "color_label", "shot_scale", "scene_id",
                               "log_profile", "lut_path", "camelot_key", "pulse_data", "tags"}
            for key, val in meta.items():
                if key in _safe_meta_keys:
                    clip[key] = val
            applied_ops.append({"op": op_type, "clip_id": clip_id, "keys": list(meta.keys())})
            continue

        # MARKER_B71: set_effects — set/replace effects list on a clip
        if op_type == "set_effects":
            clip_id = str(op.get("clip_id") or "").strip()
            if not clip_id:
                raise ValueError("clip_id is required for set_effects")
            _, clip = _find_clip(state, clip_id)
            if clip is None:
                raise ValueError(f"clip not found: {clip_id}")
            effects = op.get("effects")
            if effects is None:
                clip.pop("effects", None)
            else:
                if not isinstance(effects, list):
                    raise ValueError("effects must be a list")
                clip["effects"] = effects
            applied_ops.append({"op": op_type, "clip_id": clip_id, "effects": effects})
            continue

        # MARKER_PASTE_ATTR: set_prop — set arbitrary clip property (for paste attributes)
        if op_type == "set_prop":
            clip_id = str(op.get("clip_id") or "").strip()
            if not clip_id:
                raise ValueError("clip_id is required for set_prop")
            _lane, clip = _find_clip(state, clip_id)
            if clip is None:
                raise ValueError(f"clip not found: {clip_id}")
            key = str(op.get("key") or "").strip()
            if not key:
                raise ValueError("key is required for set_prop")
            # Whitelist pasteable properties — no structural fields (clip_id, start_sec, etc.)
            _paste_safe_keys = {
                "color_correction", "motion", "speed", "reverse", "maintain_pitch",
                "transition", "transition_out", "keyframes", "effects",
            }
            if key not in _paste_safe_keys:
                raise ValueError(f"set_prop: key '{key}' not in paste-safe whitelist")
            value = op.get("value")
            if value is None:
                clip.pop(key, None)
            else:
                clip[key] = value
            applied_ops.append({"op": op_type, "clip_id": clip_id, "key": key})
            continue

        # MARKER_B71: add_keyframe — append a keyframe to clip's keyframes list
        if op_type == "add_keyframe":
            clip_id = str(op.get("clip_id") or "").strip()
            if not clip_id:
                raise ValueError("clip_id is required for add_keyframe")
            prop = str(op.get("property") or "").strip()
            if not prop:
                raise ValueError("property is required for add_keyframe")
            time_sec = float(op.get("time_sec", -1))
            if time_sec < 0:
                raise ValueError("time_sec must be >= 0 for add_keyframe")
            value = op.get("value")
            _, clip = _find_clip(state, clip_id)
            if clip is None:
                raise ValueError(f"clip not found: {clip_id}")
            keyframes = clip.setdefault("keyframes", [])
            kf = {"property": prop, "time_sec": round(time_sec, 4), "value": value}
            if "easing" in op:
                kf["easing"] = str(op["easing"])
            keyframes.append(kf)
            keyframes.sort(key=lambda k: (str(k.get("property") or ""), float(k.get("time_sec") or 0.0)))
            applied_ops.append({"op": op_type, "clip_id": clip_id, "property": prop, "time_sec": round(time_sec, 4), "value": value})
            continue

        # MARKER_B71: remove_keyframe — remove keyframe by property+time
        if op_type == "remove_keyframe":
            clip_id = str(op.get("clip_id") or "").strip()
            if not clip_id:
                raise ValueError("clip_id is required for remove_keyframe")
            prop = str(op.get("property") or "").strip()
            if not prop:
                raise ValueError("property is required for remove_keyframe")
            time_sec = float(op.get("time_sec", -1))
            if time_sec < 0:
                raise ValueError("time_sec must be >= 0 for remove_keyframe")
            _, clip = _find_clip(state, clip_id)
            if clip is None:
                raise ValueError(f"clip not found: {clip_id}")
            keyframes = clip.get("keyframes", [])
            original_len = len(keyframes)
            clip["keyframes"] = [
                k for k in keyframes
                if not (str(k.get("property") or "") == prop and abs(float(k.get("time_sec") or 0.0) - time_sec) < 0.001)
            ]
            removed = original_len - len(clip["keyframes"])
            applied_ops.append({"op": op_type, "clip_id": clip_id, "property": prop, "time_sec": round(time_sec, 4), "removed": removed})
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

    # MARKER_B59: Auto-create timeline if missing or empty (safety net for pre-B54 projects)
    if timeline_state is None or sum(len(l.get("clips", [])) for l in timeline_state.get("lanes", [])) == 0:
        try:
            auto_timeline = _build_initial_timeline_state(project, "main", store=store)
            auto_clip_count = sum(len(l.get("clips", [])) for l in auto_timeline.get("lanes", []))
            if auto_clip_count > 0:
                store.save_timeline_state(auto_timeline)
                timeline_state = auto_timeline
                logger.info("MARKER_B59: Auto-created timeline with %d clips", auto_clip_count)
        except Exception as exc:
            logger.warning("MARKER_B59: Auto-create timeline failed: %s", exc)
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
        "sequence_settings": project.get("sequence_settings"),
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


@router.post("/sequence-settings")
async def cut_sequence_settings(body: CutSequenceSettingsRequest) -> dict[str, Any]:
    """
    MARKER_B3 — Persist sequence settings to project JSON.
    Frontend calls this when user changes any project setting.
    """
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None:
        return {"success": False, "error": "project_not_found"}

    seq = {
        "framerate": body.framerate,
        "timecode_format": body.timecode_format,
        "drop_frame": body.drop_frame,
        "start_timecode": body.start_timecode,
        "audio_sample_rate": body.audio_sample_rate,
        "audio_bit_depth": body.audio_bit_depth,
        "resolution": body.resolution,
        "width": body.width,
        "height": body.height,
        "color_space": body.color_space,
        "proxy_mode": body.proxy_mode,
    }
    project["sequence_settings"] = seq
    store.save_project(project)
    return {"success": True, "sequence_settings": seq}


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
    # MARKER_B1-CLEANUP: Use cut_codec_probe for structured probe + playback class
    if body.probe_ffprobe:
        probe_result = probe_file(path)
        playback_class = probe_result.playback_class or "unknown"
        ffprobe_payload = {"available": probe_result.available, "probe": probe_result.to_dict()}
        if probe_result.error:
            ffprobe_payload["error"] = probe_result.error
    else:
        ffprobe_payload = {"available": False, "error": "disabled"}
        # Fallback to extension-based classification
        if ext in NATIVE_VIDEO_EXT:
            playback_class = "native"
        elif ext in PROXY_RECOMMENDED_EXT:
            playback_class = "proxy_recommended"
        elif ext in TRANSCODE_REQUIRED_EXT:
            playback_class = "transcode_required"
        elif ext in AUDIO_EXT:
            playback_class = "native"
        else:
            playback_class = "unknown"
    return {
        "success": True,
        "schema_version": "cut_media_support_v2",
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



# MARKER_B41: Export routes moved to cut_routes_export.py (7 routes)

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


# ---------------------------------------------------------------------------
# MARKER_198.MULTI_TL: Multi-timeline CRUD API
# ---------------------------------------------------------------------------


class CutTimelineCreateRequest(BaseModel):
    sandbox_root: str
    project_id: str
    timeline_id: str
    label: str = ""
    clone_from: str | None = None
    fps: float = 25.0


@router.post("/timeline/create")
async def cut_timeline_create(body: CutTimelineCreateRequest) -> dict[str, Any]:
    """
    MARKER_198.MULTI_TL — Create a new timeline (optionally cloned from existing).
    """
    from datetime import datetime, timezone

    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return {"success": False, "error": "project_not_found"}

    # Check if timeline already exists
    existing = store.load_timeline_by_id(body.timeline_id)
    if existing is not None:
        return {"success": False, "error": "timeline_exists", "timeline_id": body.timeline_id}

    if body.clone_from:
        clone = store.clone_timeline(body.clone_from, body.timeline_id)
        if clone is None:
            return {"success": False, "error": "clone_source_not_found", "source_id": body.clone_from}
        return {
            "success": True,
            "timeline_id": body.timeline_id,
            "cloned_from": body.clone_from,
            "lane_count": len(clone.get("lanes", [])),
        }

    # Create empty timeline
    now = datetime.now(timezone.utc).isoformat()
    new_state = {
        "schema_version": "cut_timeline_state_v1",
        "project_id": body.project_id,
        "timeline_id": body.timeline_id,
        "revision": 0,
        "fps": body.fps,
        "lanes": [
            {"lane_id": "v1", "lane_type": "video_main", "clips": []},
            {"lane_id": "a1", "lane_type": "audio_sync", "clips": []},
        ],
        "selection": {"active_clip_id": None, "active_lane_id": None},
        "view": {"zoom": 60, "scroll_left": 0, "track_height": 56},
        "updated_at": now,
    }
    store.save_timeline_by_id(body.timeline_id, new_state)
    return {
        "success": True,
        "timeline_id": body.timeline_id,
        "created": True,
    }


@router.get("/timeline/{timeline_id}/state")
async def cut_timeline_get_state(
    timeline_id: str,
    sandbox_root: str,
    project_id: str,
) -> dict[str, Any]:
    """
    MARKER_198.MULTI_TL — Get full state for a specific timeline by ID.
    Returns lanes, markers, waveforms, duration.
    """
    store = CutProjectStore(sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(project_id):
        return {"success": False, "error": "project_not_found"}

    state = store.load_timeline_by_id(timeline_id)
    if state is None:
        # Fallback: try legacy single-timeline state
        legacy = store.load_timeline_state()
        if legacy and str(legacy.get("timeline_id", "main")) == timeline_id:
            state = legacy
        else:
            return {"success": False, "error": "timeline_not_found", "timeline_id": timeline_id}

    # Load supplementary data from project-level bundles
    waveform_bundle = store._load_json(store.paths.waveform_bundle_path) or {}
    marker_bundle = store._load_json(store.paths.time_marker_bundle_path) or {}

    # Compute duration from lanes
    duration = 0.0
    for lane in state.get("lanes", []):
        for clip in lane.get("clips", []):
            end = (clip.get("start_sec", 0) or 0) + (clip.get("duration_sec", 0) or 0)
            if end > duration:
                duration = end

    return {
        "success": True,
        "timeline_id": timeline_id,
        "state": state,
        "waveforms": waveform_bundle.get("items", []),
        "markers": [
            m for m in marker_bundle.get("markers", [])
            if m.get("timeline_id") in (timeline_id, None) or m.get("media_path")
        ],
        "duration": duration,
    }


@router.get("/timeline/list")
async def cut_timeline_list(
    sandbox_root: str,
    project_id: str,
) -> dict[str, Any]:
    """
    MARKER_198.MULTI_TL — List all timelines in the project.
    """
    store = CutProjectStore(sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(project_id):
        return {"success": False, "error": "project_not_found"}

    timelines = store.list_timelines()

    # Also include legacy main timeline if it exists and isn't in per-id dir
    legacy = store.load_timeline_state()
    if legacy:
        legacy_id = str(legacy.get("timeline_id", "main"))
        if not any(t["timeline_id"] == legacy_id for t in timelines):
            timelines.insert(0, {
                "timeline_id": legacy_id,
                "revision": legacy.get("revision", 0),
                "fps": legacy.get("fps", 25),
                "lane_count": len(legacy.get("lanes", [])),
                "updated_at": legacy.get("updated_at", ""),
                "legacy": True,
            })

    return {
        "success": True,
        "project_id": project_id,
        "timelines": timelines,
        "count": len(timelines),
    }


class CutTimelineDeleteRequest(BaseModel):
    sandbox_root: str
    project_id: str
    timeline_id: str


@router.delete("/timeline/{timeline_id}")
async def cut_timeline_delete(
    timeline_id: str,
    sandbox_root: str,
    project_id: str,
) -> dict[str, Any]:
    """
    MARKER_198.MULTI_TL — Delete a timeline by ID.
    """
    store = CutProjectStore(sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(project_id):
        return {"success": False, "error": "project_not_found"}

    deleted = store.delete_timeline(timeline_id)
    if not deleted:
        return {"success": False, "error": "timeline_not_found", "timeline_id": timeline_id}

    return {
        "success": True,
        "deleted": timeline_id,
    }


# ---------------------------------------------------------------------------
# Legacy timeline apply (pre-multi-timeline)
# ---------------------------------------------------------------------------


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
    """MARKER_173.6 + B2 — Proxy generation request."""
    sandbox_root: str
    project_id: str
    source_paths: list[str] = Field(default_factory=list, description="Media files to proxy. If empty, uses all clips from timeline.")
    resolution: str = Field(default="auto", description="Proxy resolution: auto, 720p, 480p, 360p. 'auto' probes each file and picks optimal spec.")
    force: bool = Field(default=False, description="Force regeneration even if proxy exists")


@router.post("/proxy/generate")
async def cut_proxy_generate(body: CutProxyGenerateRequest) -> dict[str, Any]:
    """
    MARKER_173.6 + B2 — Generate proxy files for timeline clips.

    Creates lightweight proxies for faster scrubbing.
    resolution="auto" probes each file via ProbeResult and picks optimal spec:
      - transcode_required / 4K heavy → 480p
      - proxy_recommended 1080p → 720p
      - native < 4K → skip (no proxy needed)
    Explicit modes: 720p, 480p, 360p apply same spec to all files.
    """
    from src.services.cut_proxy_worker import PROXY_480P, PROXY_360P

    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return {"success": False, "error": "project_not_found"}

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

    # MARKER_B2: Auto mode — probe each file, decide per-file spec
    if body.resolution == "auto":
        worker = ProxyWorker(body.sandbox_root, force=body.force)
        auto_results = worker.generate_auto(resolved)

        return {
            "success": True,
            "schema_version": "cut_proxy_generate_v2",
            "mode": "auto",
            "results": auto_results,
            "total": len(auto_results),
            "generated": sum(1 for r in auto_results if r.get("proxy_success") and not r.get("proxy_skipped")),
            "skipped": sum(1 for r in auto_results if not r.get("needs_proxy") or r.get("proxy_skipped")),
            "failed": sum(1 for r in auto_results if r.get("needs_proxy") and not r.get("proxy_success")),
            "resolution": "auto",
        }

    # Explicit resolution mode (720p / 480p / 360p)
    spec_map = {"720p": None, "480p": PROXY_480P, "360p": PROXY_360P}
    spec = spec_map.get(body.resolution)

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
        "schema_version": "cut_proxy_generate_v2",
        "mode": "explicit",
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


# ─── MARKER_CUT_1.2: Script parse endpoint ───

@router.post("/script/parse")
async def cut_script_parse(body: dict) -> dict:
    """
    Parse screenplay text into SceneChunks with chronological timing.

    Input: {"text": "INT. CAFE - DAY\n..."}
    Output: {"success": true, "chunks": [...], "total_duration_sec": N, "page_count": N}

    MVP: plain text only. Fountain/FDX/PDF/DOCX = Phase 2.
    """
    from src.services.screenplay_timing import parse_screenplay, get_total_duration, get_total_pages
    from dataclasses import asdict

    text = body.get("text", "")
    if not text or not text.strip():
        return {
            "success": True,
            "chunks": [],
            "total_duration_sec": 0.0,
            "page_count": 0.0,
        }

    chunks = parse_screenplay(text)
    return {
        "success": True,
        "chunks": [asdict(c) for c in chunks],
        "total_duration_sec": get_total_duration(chunks),
        "page_count": get_total_pages(chunks),
    }


# ─── MARKER_CUT_2.1: Apply script to project DAG ───

@router.post("/project/apply-script")
async def cut_apply_script_to_dag(body: dict) -> dict:
    """
    Parse screenplay text and create scene_chunk nodes in project DAG.

    Input: {"sandbox_root": "...", "project_id": "...", "text": "INT. CAFE..."}
    Output: {"success": true, "chunks_count": N, "dag_node_count": N, "dag_edge_count": N}
    """
    from src.services.screenplay_timing import parse_screenplay, get_total_duration, get_total_pages
    from src.services.cut_project_store import CutProjectStore
    from dataclasses import asdict

    sandbox_root = body.get("sandbox_root", "")
    project_id = body.get("project_id", "")
    text = body.get("text", "")

    if not sandbox_root or not project_id:
        return {"success": False, "error": "sandbox_root and project_id required"}

    if not text or not text.strip():
        return {"success": True, "chunks_count": 0, "dag_node_count": 0, "dag_edge_count": 0}

    chunks = parse_screenplay(text)
    store = CutProjectStore(sandbox_root=sandbox_root, project_id=project_id)
    graph = store.add_scene_chunks_to_dag(chunks)

    return {
        "success": True,
        "chunks_count": len(chunks),
        "chunks": [asdict(c) for c in chunks],
        "total_duration_sec": get_total_duration(chunks),
        "page_count": get_total_pages(chunks),
        "dag_node_count": len(graph.get("nodes", [])),
        "dag_edge_count": len(graph.get("edges", [])),
    }


# ---------------------------------------------------------------------------
# MARKER_B41: Render routes moved to cut_routes_render.py
# CutRenderMasterRequest, _emit_render_progress, _run_master_render_job,
# cut_render_master, cut_render_presets, CutRenderBatchRequest,
# _run_batch_render_job, cut_render_batch, CutSaveRequest, cut_save_project,
# cut_audio_loudness, cut_loudness_standards
# ---------------------------------------------------------------------------
# (Render code removed — now in cut_routes_render.py)
# MARKER_B72: Re-export _emit_render_progress for backward compat (tests import from here)
from src.api.routes.cut_routes_render import _emit_render_progress as _emit_render_progress  # noqa: F401
