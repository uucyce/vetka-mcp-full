"""
MARKER_B65 — Bootstrap & Timeline Builder sub-module.
Extracted from cut_routes.py to reduce file size and merge conflicts.

Contains: CutBootstrapRequest, _execute_cut_bootstrap, _build_initial_timeline_state,
_run_cut_bootstrap_job, and bootstrap helpers.

@status: active
@phase: B65
@task: tb_1774311141_1
"""
from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, Literal
from types import SimpleNamespace

from pydantic import BaseModel, Field

from src.services.cut_codec_probe import probe_file, probe_duration
from src.services.cut_project_store import (
    CutProjectStore,
    build_cut_bootstrap_profile,
    build_cut_fallback_questions,
    quick_scan_cut_source,
)
from src.services.cut_mcp_job_store import get_cut_mcp_job_store

logger = logging.getLogger("cut.bootstrap")


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class CutBootstrapRequest(BaseModel):
    source_path: str
    sandbox_root: str
    project_name: str = ""
    mode: Literal["create_or_open", "open_existing", "create_new"] = "create_or_open"
    quick_scan_limit: int = Field(default=5000, ge=1, le=200000)
    bootstrap_profile: str = "default"
    use_core_mirror: bool = True
    create_project_if_missing: bool = True
    timeline_id: str = "main"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bootstrap_error(
    code: str,
    message: str,
    *,
    degraded_reason: str,
    recoverable: bool = True,
    failed_files: list[str] | None = None,
) -> dict[str, Any]:
    # MARKER_B_DEGRADE: error_message + failed_files let frontend show
    # actionable notification instead of silently showing empty timeline.
    return {
        "success": False,
        "schema_version": "cut_bootstrap_v1",
        "error": {
            "code": code,
            "message": message,
            "recoverable": recoverable,
        },
        "error_message": message,          # top-level alias for frontend toast
        "failed_files": failed_files or [],  # paths that failed probe/import
        "degraded_mode": True,
        "degraded_reason": degraded_reason,
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


# ---------------------------------------------------------------------------
# Timeline Builder
# ---------------------------------------------------------------------------

def _build_initial_timeline_state(
    project: dict[str, Any], timeline_id: str, *, store: CutProjectStore | None = None,
) -> dict[str, Any]:
    source_path = str(project.get("source_path") or "").strip()
    scan = quick_scan_cut_source(source_path, limit=5000)
    source_root = source_path
    lanes: list[dict[str, Any]] = []

    # MARKER_189.2: Load media_index for real durations (from scan-matrix-async)
    media_index_files: dict[str, dict[str, Any]] = {}
    # MARKER_189.4: Load scan_matrix for scene segments + waveforms + thumbnails
    scan_matrix_items: dict[str, dict[str, Any]] = {}  # keyed by source_path
    if store is not None:
        mi = store.load_media_index()
        if mi and isinstance(mi.get("files"), dict):
            media_index_files = mi["files"]
        smr = store.load_scan_matrix_result()
        if smr and isinstance(smr.get("items"), list):
            for item in smr["items"]:
                sp = str(item.get("source_path", ""))
                if sp:
                    scan_matrix_items[sp] = item

    video_lane = {"lane_id": "video_main", "lane_type": "video_main", "clips": []}
    audio_lane = {"lane_id": "audio_sync", "lane_type": "audio_sync", "clips": []}
    # MARKER_B58: Sync with CUT_VIDEO_EXT / CUT_AUDIO_EXT from cut_project_store
    video_ext = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm", ".mxf", ".r3d", ".braw",
                 ".mts", ".m2ts", ".dnxhd", ".dnxhr", ".hevc", ".h264", ".h265"}
    audio_ext = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma", ".aiff", ".aif"}
    clip_counter = 0
    timeline_cursor = 0.0  # running position on timeline
    global_scene_counter = 0
    scene_ids_used: list[str] = []

    # MARKER_B63: .cutignore support — exclude directories from timeline scan
    _cutignore_patterns: set[str] = set()
    _cutignore_default = {"__pycache__", ".DS_Store", "node_modules", ".git"}
    _cutignore_path = os.path.join(source_root, ".cutignore") if os.path.isdir(source_root) else ""
    if _cutignore_path and os.path.isfile(_cutignore_path):
        try:
            with open(_cutignore_path, "r", encoding="utf-8") as _cif:
                for _line in _cif:
                    _line = _line.strip()
                    if _line and not _line.startswith("#"):
                        _cutignore_patterns.add(_line.rstrip("/"))
        except Exception:
            pass
    _cutignore_all = _cutignore_default | _cutignore_patterns

    # MARKER_B56-FIX: Recursive walk (was os.scandir — flat, missed subdirs)
    _all_media: list[str] = []
    if os.path.isdir(source_root):
        for dirpath, _dirs, files in os.walk(source_root):
            # MARKER_B63: Prune ignored directories in-place (prevents descent)
            _dirs[:] = [d for d in _dirs if d not in _cutignore_all]
            for fname in sorted(files, key=str.lower):
                ext_check = os.path.splitext(fname)[1].lower()
                if ext_check in video_ext or ext_check in audio_ext:
                    _all_media.append(os.path.join(dirpath, fname))
    elif os.path.isfile(source_root):
        # Single file passed as source_path
        ext_check = os.path.splitext(source_root)[1].lower()
        if ext_check in video_ext or ext_check in audio_ext:
            _all_media.append(source_root)

    for file_path in _all_media:
        path = SimpleNamespace(path=file_path, name=os.path.basename(file_path))
        ext = os.path.splitext(path.name)[1].lower()

        # MARKER_189.2: Resolve real duration from media_index → ffprobe fallback → 5.0
        mi_entry = media_index_files.get(path.path) or {}
        full_duration = float(mi_entry.get("duration_sec") or 0)
        if full_duration <= 0:
            full_duration = probe_duration(path.path)
        if full_duration <= 0:
            full_duration = 5.0  # ultimate fallback

        # MARKER_189.4: Use scanner segments to create per-segment clips
        sm_item = scan_matrix_items.get(path.path) or {}
        video_scan = sm_item.get("video_scan") or {}
        audio_scan = sm_item.get("audio_scan") or {}
        segments = video_scan.get("segments") or []
        thumbnail_paths = video_scan.get("thumbnail_paths") or []
        waveform_bins = audio_scan.get("waveform_bins") or []

        if ext in video_ext and len(segments) > 1:
            # Multi-segment video: create one clip per detected scene segment
            for seg_idx, seg in enumerate(segments):
                clip_counter += 1
                global_scene_counter += 1
                seg_start = float(seg.get("start_sec", 0))
                seg_end = float(seg.get("end_sec", 0))
                seg_dur = float(seg.get("duration_sec", 0)) or (seg_end - seg_start)
                if seg_dur <= 0:
                    continue
                scene_id = str(seg.get("segment_id", "")) or f"scene_{global_scene_counter:02d}"
                if scene_id not in scene_ids_used:
                    scene_ids_used.append(scene_id)
                thumb = ""
                if seg_idx < len(thumbnail_paths):
                    thumb = thumbnail_paths[seg_idx]
                clip = {
                    "clip_id": f"clip_{clip_counter:04d}",
                    "record_id": f"record_{clip_counter:04d}",
                    "scene_id": scene_id,
                    "take_id": f"take_{clip_counter:04d}",
                    "start_sec": round(timeline_cursor, 3),
                    "duration_sec": round(seg_dur, 3),
                    "source_path": path.path,
                    "source_in": round(seg_start, 3),
                    "source_out": round(seg_end, 3),
                    "sync": None,
                    "thumbnail_path": thumb,
                }
                timeline_cursor += seg_dur
                video_lane["clips"].append(clip)
        else:
            # Single-segment or audio-only: one clip per file
            clip_counter += 1
            global_scene_counter += 1
            scene_id = f"scene_{global_scene_counter:02d}"
            if scene_id not in scene_ids_used:
                scene_ids_used.append(scene_id)
            thumb = thumbnail_paths[0] if thumbnail_paths else ""
            clip = {
                "clip_id": f"clip_{clip_counter:04d}",
                "record_id": f"record_{clip_counter:04d}",
                "scene_id": scene_id,
                "take_id": f"take_{clip_counter:04d}",
                "start_sec": round(timeline_cursor, 3),
                "duration_sec": round(full_duration, 3),
                "source_path": path.path,
                "sync": None,
                "thumbnail_path": thumb,
            }
            if waveform_bins:
                clip["waveform_bins"] = waveform_bins
            timeline_cursor += full_duration
            if ext in video_ext:
                video_lane["clips"].append(clip)
            else:
                audio_lane["clips"].append(clip)

    if video_lane["clips"]:
        lanes.append(video_lane)
    if audio_lane["clips"]:
        lanes.append(audio_lane)

    # MARKER_B55: Auto-detect FPS from first video clip (like Premiere Pro)
    detected_fps = 25.0  # default fallback
    if video_lane["clips"]:
        first_clip_path = video_lane["clips"][0].get("source_path", "")
        if first_clip_path:
            try:
                probe_result = probe_file(first_clip_path)
                if probe_result.ok and probe_result.video_streams:
                    raw_fps = probe_result.video_streams[0].fps
                    if raw_fps > 0:
                        detected_fps = round(raw_fps, 3)
            except Exception:
                pass  # fallback to 25

    first_scene = scene_ids_used[0] if scene_ids_used else ""
    return {
        "schema_version": "cut_timeline_state_v1",
        "project_id": str(project.get("project_id") or ""),
        "timeline_id": str(timeline_id or "main"),
        "revision": 1,
        "fps": detected_fps,
        "lanes": lanes,
        "selection": {
            "clip_ids": [video_lane["clips"][0]["clip_id"]] if video_lane["clips"] else [],
            "scene_ids": [first_scene] if first_scene else [],
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


# ---------------------------------------------------------------------------
# Bootstrap Execution
# ---------------------------------------------------------------------------

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
    # MARKER_B69: Register as active singleton for PULSE/render endpoints
    CutProjectStore.set_current(store)
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

    # MARKER_B54-FIX + B58 + B60: Create/rebuild timeline with clips from scanned media
    existing_timeline = store.load_timeline_state()
    existing_clip_count = 0
    if existing_timeline:
        for _lane in existing_timeline.get("lanes", []):
            existing_clip_count += len(_lane.get("clips", []))

    if existing_timeline is None or existing_clip_count == 0:
        timeline_id = str(body.timeline_id or "main")
        initial_timeline = _build_initial_timeline_state(project, timeline_id, store=store)
        store.save_timeline_state(initial_timeline)
        logger.info("MARKER_B58: Timeline created/rebuilt with %d media files",
                     sum(len(l.get("clips", [])) for l in initial_timeline.get("lanes", [])))

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
        "auto_scan_job_id": None,
        # MARKER_B58: Include clip count for verification
        "timeline_clip_count": sum(
            len(l.get("clips", []))
            for l in (store.load_timeline_state() or {}).get("lanes", [])
        ),
        "missing_inputs": {
            "script_or_treatment": not bool(signals.get("has_script_or_treatment")),
            "montage_sheet": not bool(signals.get("has_montage_sheet")),
            "transcript_or_timecodes": not bool(signals.get("has_transcript_or_timecodes")),
        },
        "fallback_questions": fallback_questions,
        "phases": [
            {"id": "discover", "label": "Scope discovery", "status": "done", "progress": 0.33},
            {"id": "project", "label": "Project bootstrap", "status": "done", "progress": 0.66},
            {"id": "align", "label": "Timeline bootstrap", "status": "done", "progress": 1.0},
        ],
        "next_actions": [
            "open_cut_project",
            "poll_bootstrap_job",
            "start_scene_assembly",
        ],
        "degraded_mode": degraded_mode,
        "degraded_reason": degraded_reason,
        # MARKER_B_DEGRADE: error_message + failed_files for frontend notification
        "error_message": degraded_reason if degraded_mode else "",
        "failed_files": [],  # populated by scan phase when file probing fails
        # Extra fields for auto-scan orchestration (used by route handler)
        "_media_count": media_count,
        "_project_id": str(project.get("project_id") or ""),
        "_sandbox_root": sandbox_root,
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
