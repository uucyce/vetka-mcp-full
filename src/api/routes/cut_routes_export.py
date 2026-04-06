"""
MARKER_B41 — Export sub-router.
Extracted from cut_routes.py: editorial exports (Premiere, FCPXML, OTIO, EDL),
SRT marker export/import, social presets, batch export, montage promotion.

@status: active
@phase: B41
@task: tb_1774243018_2
"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.services.converters.premiere_xml_converter import build_premiere_xml
from src.services.converters.fcpxml_converter import build_fcpxml
from src.services.cut_project_store import CutProjectStore
from src.services.pulse_srt_bridge import parse_subtitles

export_router = APIRouter(tags=["CUT-Export"])


# ---------------------------------------------------------------------------
# Shared helpers (moved from cut_routes.py)
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
            clips.append({
                "clip_id": str(clip.get("clip_id") or ""),
                "name": str(Path(str(clip.get("source_path") or "")).name or clip.get("clip_id") or "clip"),
                "source_path": str(clip.get("source_path") or ""),
                "lane_id": str(lane.get("lane_id") or ""),
                "start_sec": start_sec, "end_sec": end_sec, "duration_sec": clip_duration,
            })

    marker_bundle = store.load_time_marker_bundle() or {}
    raw_items = list(marker_bundle.get("items") or [])
    markers: list[dict[str, Any]] = []
    for item in raw_items:
        status = str(item.get("status") or "active")
        if status != "active" and not include_archived_markers:
            continue
        markers.append({
            "marker_id": str(item.get("marker_id") or ""),
            "media_path": str(item.get("media_path") or ""),
            "time_sec": float(item.get("anchor_sec") if item.get("anchor_sec") is not None else item.get("start_sec") or 0.0),
            "start_sec": float(item.get("start_sec") or 0.0),
            "end_sec": float(item.get("end_sec") or item.get("start_sec") or 0.0),
            "kind": str(item.get("kind") or "comment"),
            "comment": str(item.get("text") or item.get("label") or ""),
            "color": str(item.get("kind") or "comment"),
            "comment_thread_id": str(item.get("comment_thread_id") or ""),
        })

    return {"project": project, "timeline": timeline, "clips": clips, "markers": markers, "duration_sec": duration_sec}


def _build_otio_export(project_name: str, sequence_name: str, clips: list[dict[str, Any]], fps: int) -> dict[str, Any]:
    track_children = []
    for clip in clips:
        start = float(clip.get("start_sec") or 0.0)
        dur = float(clip.get("duration_sec") or 0.0)
        track_children.append({
            "OTIO_SCHEMA": "Clip.2",
            "name": str(clip.get("name") or "clip"),
            "source_range": {
                "OTIO_SCHEMA": "TimeRange.1",
                "start_time": {"OTIO_SCHEMA": "RationalTime.1", "value": 0, "rate": fps},
                "duration": {"OTIO_SCHEMA": "RationalTime.1", "value": round(dur * fps), "rate": fps},
            },
            "metadata": {"vetka": {"source_path": str(clip.get("source_path") or ""), "timeline_start_sec": start}},
        })
    return {
        "OTIO_SCHEMA": "Timeline.1", "name": sequence_name,
        "metadata": {"project_name": project_name},
        "tracks": {
            "OTIO_SCHEMA": "Stack.1",
            "children": [{"OTIO_SCHEMA": "Track.1", "name": "V1", "kind": "Video", "children": track_children}],
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
    # MARKER_PLAYER_LAB_SRT: support simple [N] / [FAV] tags from VETKA Videoplayer Lab
    line = str(text or "").strip()
    upper = line.upper()
    if upper.startswith("[N]"):
        return {"kind": "negative", "score": 0.3}, line[3:].strip()
    if upper.startswith("[FAV]"):
        return {"kind": "favorite", "score": 1.0}, line[5:].strip()
    if not line.startswith("{"):
        return {}, line
    try:
        meta, end_idx = json.JSONDecoder().raw_decode(line)
        note = line[end_idx:].strip()
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


def _build_export_filename(sequence_name: str, fmt: str) -> str:
    safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "_", sequence_name).strip("._-") or "vetka_cut_export"
    ext_map = {"premiere_xml": ".xml", "fcpxml": ".fcpxml", "otio": ".otio.json", "edl": ".edl", "aaf": ".aaf.json"}
    return f"{safe_name}{ext_map.get(fmt, '.txt')}"


def _write_export_artifact(store: CutProjectStore, fmt: str, sequence_name: str, content: str) -> str:
    export_dir = Path(store.paths.storage_dir) / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    out_path = export_dir / _build_export_filename(sequence_name, fmt)
    out_path.write_text(content, encoding="utf-8")
    return str(out_path)


def _run_export(body: "CutExportRequest", fmt: str) -> dict[str, Any]:
    store = CutProjectStore(body.sandbox_root)
    material = _collect_export_material(
        store=store, project_id=body.project_id,
        timeline_id=body.timeline_id, include_archived_markers=body.include_archived_markers,
    )
    project = material["project"]
    clips = material["clips"]
    markers = material["markers"]
    sequence_name = str(body.sequence_name or "VETKA_Sequence")
    project_name = str(project.get("display_name") or project.get("project_name") or "VETKA_Project")

    if fmt == "premiere_xml":
        xml_content = build_premiere_xml({
            "project_name": project_name, "sequence_name": sequence_name,
            "source_path": str(project.get("source_path") or ""),
            "fps": int(body.fps), "duration_sec": float(material["duration_sec"] or 0.0),
            "clips": clips, "markers": markers,
        })
        export_path = _write_export_artifact(store, fmt, sequence_name, xml_content)
        return {"content": xml_content, "path": export_path}

    if fmt == "fcpxml":
        xml_content = build_fcpxml({
            "project_name": project_name, "sequence_name": sequence_name,
            "source_path": str(project.get("source_path") or ""),
            "fps": int(body.fps), "duration_sec": float(material["duration_sec"] or 0.0),
            "clips": clips, "markers": markers,
        })
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


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------


class CutExportRequest(BaseModel):
    sandbox_root: str
    project_id: str
    timeline_id: str = "main"
    sequence_name: str = "VETKA_Sequence"
    fps: int = 25
    include_archived_markers: bool = False


class CutBatchExportRequest(BaseModel):
    sandbox_root: str
    project_id: str
    timeline_id: str = "main"
    sequence_name: str = "VETKA_Sequence"
    fps: int = 25
    formats: list[str] = Field(default_factory=lambda: ["premiere_xml"])
    social_targets: list[str] = Field(default_factory=list)
    include_archived_markers: bool = False


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
    srt_content: str = ""
    default_media_path: str = ""
    author: str = "cut_mcp"
    mode: str = "append"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@export_router.post("/export/premiere-xml")
async def cut_export_premiere_xml(body: CutExportRequest) -> dict[str, Any]:
    if not body.sandbox_root or not body.project_id:
        raise HTTPException(status_code=400, detail="sandbox_root and project_id are required")
    result = _run_export(body, "premiere_xml")
    store = CutProjectStore(body.sandbox_root)
    material = _collect_export_material(
        store=store, project_id=body.project_id, timeline_id=body.timeline_id,
        include_archived_markers=body.include_archived_markers,
    )
    return {
        "success": True, "schema_version": "cut_export_result_v1", "format": "premiere_xml",
        "project_id": body.project_id, "clip_count": len(material["clips"]),
        "marker_count": len(material["markers"]), "xml_content": result["content"],
        "export_path": result["path"], "generated_at": _utc_now_iso(),
    }


@export_router.post("/export/fcpxml")
async def cut_export_fcpxml(body: CutExportRequest) -> dict[str, Any]:
    if not body.sandbox_root or not body.project_id:
        raise HTTPException(status_code=400, detail="sandbox_root and project_id are required")
    result = _run_export(body, "fcpxml")
    store = CutProjectStore(body.sandbox_root)
    material = _collect_export_material(
        store=store, project_id=body.project_id, timeline_id=body.timeline_id,
        include_archived_markers=body.include_archived_markers,
    )
    return {
        "success": True, "schema_version": "cut_export_result_v1", "format": "fcpxml",
        "project_id": body.project_id, "clip_count": len(material["clips"]),
        "marker_count": len(material["markers"]), "xml_content": result["content"],
        "export_path": result["path"], "generated_at": _utc_now_iso(),
    }


@export_router.post("/export/otio")
async def cut_export_otio(body: CutExportRequest) -> dict[str, Any]:
    result = _run_export(body, "otio")
    return {
        "success": True, "schema_version": "cut_export_result_v1", "format": "otio",
        "project_id": body.project_id, "otio_content": result["content"],
        "export_path": result["path"], "generated_at": _utc_now_iso(),
    }


@export_router.post("/export/edl")
async def cut_export_edl(body: CutExportRequest) -> dict[str, Any]:
    result = _run_export(body, "edl")
    return {
        "success": True, "schema_version": "cut_export_result_v1", "format": "edl",
        "project_id": body.project_id, "edl_content": result["content"],
        "export_path": result["path"], "generated_at": _utc_now_iso(),
    }


@export_router.get("/export/social-presets")
async def cut_export_social_presets() -> dict[str, Any]:
    return {"success": True, "schema_version": "cut_export_social_presets_v1", "presets": _social_presets_manifest(), "batch_supported": True}


@export_router.post("/export/batch")
async def cut_export_batch(body: CutBatchExportRequest) -> dict[str, Any]:
    export_req = CutExportRequest(
        sandbox_root=body.sandbox_root, project_id=body.project_id,
        timeline_id=body.timeline_id, sequence_name=body.sequence_name, fps=body.fps,
    )
    results: dict[str, dict[str, Any]] = {}
    for fmt in body.formats:
        out = _run_export(export_req, fmt)
        results[fmt] = {"export_path": out["path"]}
    social_manifest = _social_presets_manifest()
    social_targets = {target: social_manifest[target] for target in body.social_targets if target in social_manifest}
    return {
        "success": True, "schema_version": "cut_export_batch_v1", "project_id": body.project_id,
        "exports": results, "social_targets": social_targets, "generated_at": _utc_now_iso(),
    }


@export_router.post("/markers/export-srt")
async def cut_export_markers_srt(body: CutMarkerSrtExportRequest) -> dict[str, Any]:
    store = CutProjectStore(body.sandbox_root)
    material = _collect_export_material(
        store=store, project_id=body.project_id, timeline_id=body.timeline_id,
        include_archived_markers=body.include_archived,
    )
    kinds = {str(kind).strip() for kind in body.kinds if str(kind).strip()}
    markers = [m for m in material["markers"] if not kinds or str(m.get("kind") or "") in kinds]
    srt_parts = [_serialize_srt_marker(index, marker) for index, marker in enumerate(markers, start=1)]
    srt_content = "\n".join(srt_parts).strip() + ("\n" if srt_parts else "")
    export_dir = Path(store.paths.storage_dir) / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    out_path = export_dir / _build_export_filename("vetka_markers", "edl")
    out_path = out_path.with_suffix(".srt")
    out_path.write_text(srt_content, encoding="utf-8")
    return {
        "success": True, "schema_version": "cut_marker_srt_v1",
        "project_id": body.project_id, "timeline_id": body.timeline_id,
        "marker_count": len(markers), "srt_content": srt_content,
        "export_path": str(out_path), "generated_at": _utc_now_iso(),
    }


# ---------------------------------------------------------------------------
# MARKER_B49: AAF Export — Advanced Authoring Format for Pro Tools roundtrip
# ---------------------------------------------------------------------------


def _build_aaf_export(
    project_name: str,
    sequence_name: str,
    clips: list[dict[str, Any]],
    fps: int,
    duration_sec: float,
) -> dict[str, Any]:
    """Build AAF-compatible JSON structure.

    AAF (Advanced Authoring Format) is used for Premiere↔Pro Tools roundtrip.
    This generates a structured representation that can be serialized to actual
    AAF binary via pyaaf2 (if installed) or used as interchange JSON.

    Structure: CompositionMob → TimelineMobSlot → Sequence → SourceClip[]
    Each SourceClip references a MasterMob → SourceMob with file descriptor.
    """
    from uuid import uuid4

    source_mobs = []
    master_mobs = []
    source_clips = []

    for i, clip in enumerate(clips):
        clip_name = str(clip.get("name") or f"clip_{i+1}")
        source_path = str(clip.get("source_path") or "")
        start = float(clip.get("start_sec") or 0.0)
        dur = float(clip.get("duration_sec") or 0.0)
        lane_id = str(clip.get("lane_id") or "V1")

        mob_id = str(uuid4())
        master_id = str(uuid4())

        # SourceMob: points to physical file
        source_mobs.append({
            "mob_id": mob_id,
            "name": clip_name,
            "file_path": source_path,
            "descriptor": {
                "type": "FileDescriptor",
                "media_kind": "video" if lane_id.startswith("V") or lane_id.startswith("v") else "sound",
                "sample_rate": fps,
                "length": int(dur * fps),
            },
        })

        # MasterMob: editorial reference
        master_mobs.append({
            "mob_id": master_id,
            "name": clip_name,
            "source_mob_id": mob_id,
            "slot": {
                "slot_id": 1,
                "edit_rate": fps,
                "origin": 0,
            },
        })

        # SourceClip in composition
        source_clips.append({
            "master_mob_id": master_id,
            "slot_id": 1,
            "start_time": int(start * fps),
            "length": int(dur * fps),
            "name": clip_name,
            "track": lane_id,
        })

    return {
        "aaf_schema": "vetka_aaf_interchange_v1",
        "header": {
            "project_name": project_name,
            "edit_rate": fps,
            "duration_frames": int(duration_sec * fps),
        },
        "composition_mob": {
            "name": sequence_name,
            "mob_id": str(uuid4()),
            "slots": [
                {
                    "slot_id": 1,
                    "track_name": "V1",
                    "media_kind": "video",
                    "edit_rate": fps,
                    "sequence": {
                        "components": [
                            sc for sc in source_clips
                            if sc["track"].startswith("V") or sc["track"].startswith("v")
                        ],
                    },
                },
                {
                    "slot_id": 2,
                    "track_name": "A1",
                    "media_kind": "sound",
                    "edit_rate": fps,
                    "sequence": {
                        "components": [
                            sc for sc in source_clips
                            if sc["track"].startswith("A") or sc["track"].startswith("a")
                        ],
                    },
                },
            ],
        },
        "master_mobs": master_mobs,
        "source_mobs": source_mobs,
    }


@export_router.post("/export/aaf")
async def cut_export_aaf(body: CutExportRequest) -> dict[str, Any]:
    """
    MARKER_B49 — Export timeline as AAF interchange format.
    Returns JSON representation of AAF structure (CompositionMob + SourceMobs).
    Can be consumed by pyaaf2 for binary AAF generation, or used directly
    for Pro Tools / Premiere roundtrip via VETKA import.
    """
    if not body.sandbox_root or not body.project_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="sandbox_root and project_id required")

    material = _collect_export_material(
        store=CutProjectStore(body.sandbox_root),
        project_id=body.project_id,
        timeline_id=body.timeline_id,
        include_archived_markers=body.include_archived_markers,
    )

    project = material["project"]
    project_name = str(project.get("display_name") or project.get("project_name") or "VETKA_Project")
    sequence_name = str(body.sequence_name or "VETKA_Sequence")

    aaf_data = _build_aaf_export(
        project_name, sequence_name, material["clips"],
        int(body.fps), material["duration_sec"],
    )

    # Write to file
    content = json.dumps(aaf_data, ensure_ascii=False, indent=2)
    export_path = _write_export_artifact(
        CutProjectStore(body.sandbox_root), "aaf", sequence_name, content,
    )

    return {
        "success": True,
        "schema_version": "cut_export_result_v1",
        "format": "aaf",
        "project_id": body.project_id,
        "clip_count": len(material["clips"]),
        "aaf_content": aaf_data,
        "export_path": export_path,
        "generated_at": _utc_now_iso(),
    }
