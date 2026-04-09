"""
MARKER_BOTIO — Import sub-router.

Accepts uploaded NLE timeline files (Premiere XML, FCPXML, OTIO JSON, EDL)
and returns a CUT timeline structure ready for store hydration.

Endpoints:
  POST /import/otio        — upload any supported format, get timeline JSON
  POST /import/otio/apply  — upload + write directly to sandbox store
  GET  /import/formats     — list supported formats and their capabilities

@status: active
@phase: BOTIO
@task: tb_1774423967_1
@depends: cut_otio_import, cut_project_store
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from src.services.cut_otio_import import parse_otio_file, CutImportResult
from src.services.cut_project_store import CutProjectStore

logger = logging.getLogger("cut.routes.import")

import_router = APIRouter(tags=["CUT-Import"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _result_to_response(result: CutImportResult, *, include_timeline: bool = True) -> dict[str, Any]:
    resp: dict[str, Any] = {
        "success": True,
        "schema_version": "cut_import_result_v1",
        "source_format": result.source_format,
        "project_name": result.project_name,
        "sequence_name": result.sequence_name,
        "fps": result.fps,
        "duration_sec": result.duration_sec,
        "clip_count": result.clip_count,
        "lane_count": result.lane_count,
        "marker_count": len(result.markers),
        "warnings": result.warnings,
        "generated_at": _utc_now_iso(),
    }
    if include_timeline:
        resp["timeline_state"] = result.timeline_state
        resp["markers"] = result.markers
    return resp


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@import_router.get("/import/formats")
async def cut_import_formats() -> dict[str, Any]:
    """
    MARKER_BOTIO.1 — List supported import formats and their capabilities.
    """
    return {
        "success": True,
        "schema_version": "cut_import_formats_v1",
        "formats": [
            {
                "id": "otio_json",
                "extensions": [".otio", ".otio.json"],
                "name": "OpenTimelineIO JSON",
                "description": "VETKA CUT native OTIO JSON export format (Timeline.1 schema). "
                               "Preserves source_path, timeline positions, and metadata.",
                "capabilities": {
                    "clips": True,
                    "markers": False,
                    "transitions": False,
                    "multi_lane": True,
                    "source_paths": True,
                    "audio_tracks": True,
                },
            },
            {
                "id": "premiere_xml",
                "extensions": [".xml"],
                "name": "Premiere Pro XMEML v5",
                "description": "Adobe Premiere Pro XML interchange format. "
                               "Supports video/audio tracks, markers, and file references.",
                "capabilities": {
                    "clips": True,
                    "markers": True,
                    "transitions": False,
                    "multi_lane": True,
                    "source_paths": True,
                    "audio_tracks": True,
                },
            },
            {
                "id": "fcpxml",
                "extensions": [".fcpxml"],
                "name": "Final Cut Pro XML v1.x",
                "description": "FCPXML for Final Cut Pro / DaVinci Resolve. "
                               "Parses spine clips and clip markers.",
                "capabilities": {
                    "clips": True,
                    "markers": True,
                    "transitions": False,
                    "multi_lane": False,
                    "source_paths": True,
                    "audio_tracks": False,
                },
            },
            {
                "id": "edl",
                "extensions": [".edl"],
                "name": "CMX 3600 EDL",
                "description": "Edit Decision List (CMX 3600). Clips are parsed by reel name; "
                               "source paths are empty and require relinking after import.",
                "capabilities": {
                    "clips": True,
                    "markers": False,
                    "transitions": False,
                    "multi_lane": False,
                    "source_paths": False,
                    "audio_tracks": False,
                },
                "limitations": [
                    "Source file paths are not embedded in EDL — reel names only.",
                    "Use media relink after import to resolve source files.",
                ],
            },
        ],
        "generated_at": _utc_now_iso(),
    }


@import_router.post("/import/otio")
async def cut_import_otio(
    file: UploadFile = File(...),
    project_id: str = Form(default=""),
) -> dict[str, Any]:
    """
    MARKER_BOTIO.2 — Parse an uploaded NLE timeline file and return CUT timeline JSON.

    Accepts: .otio, .otio.json, .xml (Premiere XMEML), .fcpxml, .edl
    Returns: timeline_state (cut_timeline_state_v1) + markers list

    This endpoint does NOT write to any store — it returns the parsed data
    for the frontend to review and confirm before applying.

    Body (multipart/form-data):
      - file: timeline file
      - project_id: optional project ID to embed in the result
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    filename = file.filename or "unknown"
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(content) > 50 * 1024 * 1024:  # 50 MB safety cap
        raise HTTPException(status_code=413, detail="File too large. Maximum 50 MB.")

    try:
        result = parse_otio_file(
            file_path=filename,
            content=content,
            project_id=project_id or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("cut_import_otio: unexpected error parsing '%s'", filename)
        raise HTTPException(status_code=500, detail=f"Import failed: {exc}") from exc

    return _result_to_response(result, include_timeline=True)


class CutImportApplyRequest(BaseModel):
    sandbox_root: str
    project_id: str
    timeline_id: str = ""
    merge_mode: str = "replace"   # "replace" | "append_lanes"


@import_router.post("/import/otio/apply")
async def cut_import_otio_apply(
    file: UploadFile = File(...),
    sandbox_root: str = Form(...),
    project_id: str = Form(...),
    timeline_id: str = Form(default=""),
    merge_mode: str = Form(default="replace"),
) -> dict[str, Any]:
    """
    MARKER_BOTIO.3 — Parse uploaded timeline and write it directly to the sandbox store.

    This combines parse + save in one call.
    merge_mode:
      - "replace"      — overwrite the existing timeline (default)
      - "append_lanes" — append imported lanes to existing timeline

    Body (multipart/form-data):
      - file: timeline file
      - sandbox_root: absolute path to CUT sandbox
      - project_id: CUT project ID
      - timeline_id: target timeline ID (default: auto-generated)
      - merge_mode: "replace" | "append_lanes"
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")
    if not sandbox_root or not project_id:
        raise HTTPException(status_code=400, detail="sandbox_root and project_id are required.")

    filename = file.filename or "unknown"
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum 50 MB.")

    # Parse
    try:
        result = parse_otio_file(
            file_path=filename,
            content=content,
            project_id=project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("cut_import_otio_apply: parse error for '%s'", filename)
        raise HTTPException(status_code=500, detail=f"Import parse failed: {exc}") from exc

    # Load store
    try:
        store = CutProjectStore(sandbox_root)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid sandbox_root: {exc}") from exc

    # Determine target timeline_id
    target_id = str(timeline_id or "").strip() or result.timeline_state.get("timeline_id") or "main"
    result.timeline_state["timeline_id"] = target_id
    result.timeline_state["project_id"] = project_id

    # Merge modes
    if merge_mode == "append_lanes":
        existing = store.load_timeline_by_id(target_id) or store.load_timeline_state()
        if existing:
            existing_lanes: list[dict] = existing.get("lanes") or []
            imported_lanes: list[dict] = result.timeline_state.get("lanes") or []
            existing_ids = {str(l.get("lane_id") or "") for l in existing_lanes}
            # Suffix conflicting lane_ids
            for lane in imported_lanes:
                lid = str(lane.get("lane_id") or "")
                if lid in existing_ids:
                    suffix = f"_imp"
                    lane["lane_id"] = lid + suffix
                    for clip in lane.get("clips") or []:
                        clip["lane_id"] = lane["lane_id"]
            merged_lanes = existing_lanes + imported_lanes
            result.timeline_state["lanes"] = merged_lanes
            result.timeline_state["revision"] = int(existing.get("revision") or 0) + 1

    # Save timeline
    try:
        store.save_timeline_by_id(target_id, result.timeline_state)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Timeline validation failed: {exc}") from exc
    except Exception as exc:
        logger.exception("cut_import_otio_apply: save error")
        raise HTTPException(status_code=500, detail=f"Failed to save timeline: {exc}") from exc

    # Save markers to time_marker_bundle if any
    marker_save_error: str | None = None
    if result.markers:
        try:
            existing_bundle = store.load_time_marker_bundle() or {
                "schema_version": "cut_time_marker_bundle_v1",
                "project_id": project_id,
                "items": [],
            }
            existing_items: list[dict] = existing_bundle.get("items") or []
            # Stamp imported markers with status=active
            for mk in result.markers:
                mk["status"] = mk.get("status") or "active"
                mk["source"] = "import"
            existing_items.extend(result.markers)
            existing_bundle["items"] = existing_items
            store.save_time_marker_bundle(existing_bundle)
        except Exception as exc:
            marker_save_error = str(exc)
            logger.warning("cut_import_otio_apply: marker save failed: %s", exc)

    response = _result_to_response(result, include_timeline=True)
    response["applied"] = True
    response["target_timeline_id"] = target_id
    response["merge_mode"] = merge_mode
    if marker_save_error:
        response["warnings"] = result.warnings + [f"Marker save failed: {marker_save_error}"]

    return response
