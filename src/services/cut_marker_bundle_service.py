"""
MARKER_170.8.MARKER_BUNDLE_CONTRACT
Music-sync marker bundle creation service.

Merges energy_pause_v1 slice windows + audio_sync_v1 sync results
into TimeMarker items compatible with cut_time_marker_bundle_v1.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from src.services.cut_audio_intel_eval import SliceWindow, SyncResult


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def hybrid_merge_slices(
    windows: list[SliceWindow],
    *,
    overlap_threshold_sec: float = 0.15,
) -> list[dict[str, Any]]:
    """
    Merge overlapping/adjacent slice windows from different sources.
    Windows within overlap_threshold_sec are merged, keeping best confidence.
    """
    if not windows:
        return []

    # Sort by start time
    sorted_wins = sorted(windows, key=lambda w: w.start_sec)
    merged: list[dict[str, Any]] = []

    current = {
        "start_sec": sorted_wins[0].start_sec,
        "end_sec": sorted_wins[0].end_sec,
        "confidence": sorted_wins[0].confidence,
        "method": sorted_wins[0].method,
        "sources": [sorted_wins[0].method],
    }

    for win in sorted_wins[1:]:
        # Check overlap or adjacency
        if win.start_sec <= current["end_sec"] + overlap_threshold_sec:
            # Merge: extend end, keep best confidence
            current["end_sec"] = max(current["end_sec"], win.end_sec)
            current["confidence"] = max(current["confidence"], win.confidence)
            if win.method not in current["sources"]:
                current["sources"].append(win.method)
                current["method"] = "hybrid"
        else:
            merged.append(current)
            current = {
                "start_sec": win.start_sec,
                "end_sec": win.end_sec,
                "confidence": win.confidence,
                "method": win.method,
                "sources": [win.method],
            }

    merged.append(current)
    return merged


def create_marker_bundle_from_slices(
    project_id: str,
    timeline_id: str,
    track_id: str,
    media_path: str,
    slice_windows: list[SliceWindow],
    sync_result: SyncResult | None = None,
    slice_method: Literal["transcript_only", "energy_only", "hybrid_merge"] = "hybrid_merge",
) -> dict[str, Any]:
    """
    MARKER_170.8.MUSIC_SYNC_INTEGRATION
    Convert slice windows + sync result → cut_time_marker_bundle_v1 items.

    1. Merge overlapping windows (hybrid_merge)
    2. Apply sync offset to all marker times
    3. Create labeled markers in cut_time_marker_v1 format
    4. Include sync_status in bundle metadata
    """
    # Step 1: Merge overlapping windows
    merged = hybrid_merge_slices(slice_windows)

    # Step 2: Apply sync offset
    offset_sec = sync_result.detected_offset_sec if sync_result else 0.0
    for window in merged:
        window["start_sec"] = max(0.0, window["start_sec"] + offset_sec)
        window["end_sec"] = max(0.0, window["end_sec"] + offset_sec)

    # Step 3: Create markers in cut_time_marker_v1 format
    now = _utc_now_iso()
    items: list[dict[str, Any]] = []
    for i, window in enumerate(merged):
        source_method = window.get("method", "energy_pause_v1")
        # Determine source label
        if source_method == "hybrid":
            source_label = "hybrid"
        elif "transcript" in source_method:
            source_label = "transcript_pause"
        else:
            source_label = "energy_pause"

        marker = {
            "marker_id": f"{track_id}_music_{uuid4().hex[:8]}",
            "schema_version": "cut_time_marker_v1",
            "project_id": project_id,
            "timeline_id": timeline_id,
            "media_path": media_path,
            "kind": "music_sync",
            "start_sec": float(window["start_sec"]),
            "end_sec": float(window["end_sec"]),
            "anchor_sec": float(window["start_sec"]),
            "score": float(window.get("confidence", 0.8)),
            "label": f"Slice {i + 1}",
            "text": "",
            "author": "music_sync_engine",
            "context_slice": {
                "source": source_label,
                "confidence": float(window.get("confidence", 0.8)),
                "slice_method": slice_method,
                "sources": window.get("sources", [source_method]),
                "tags": ["music", "primary_track"],
            },
            "cam_payload": None,
            "chat_thread_id": None,
            "comment_thread_id": None,
            "source_engine": f"music_sync_{source_label}",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        items.append(marker)

    # Step 4: Build sync_status metadata
    sync_status: dict[str, Any] = {}
    if sync_result:
        sync_status = {
            "method": sync_result.method,
            "offset_sec": sync_result.detected_offset_sec,
            "confidence": sync_result.confidence,
            "peak_value": sync_result.peak_value,
            "notes": None if sync_result.confidence >= 0.7 else "Low sync confidence — may need manual adjustment",
        }

    # Build the bundle in cut_time_marker_bundle_v1 format
    bundle: dict[str, Any] = {
        "schema_version": "cut_time_marker_bundle_v1",
        "project_id": project_id,
        "timeline_id": timeline_id,
        "revision": 1,
        "items": items,
        "ranking_summary": _compute_music_marker_ranking(items),
        "music_sync_meta": {
            "sync_status": sync_status,
            "slice_method": slice_method,
            "source_track_id": track_id,
            "marker_count": len(items),
            "generated_at": now,
        },
        "generated_at": now,
    }
    return bundle


def _compute_music_marker_ranking(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute ranking summary for music markers."""
    if not items:
        return {
            "total_active": 0,
            "total_archived": 0,
            "by_kind": {},
            "avg_score": 0.0,
        }
    active = [i for i in items if i.get("status") != "archived"]
    archived = [i for i in items if i.get("status") == "archived"]
    scores = [float(i.get("score", 0)) for i in active]
    by_kind: dict[str, int] = {}
    for item in active:
        kind = str(item.get("kind", "unknown"))
        by_kind[kind] = by_kind.get(kind, 0) + 1
    return {
        "total_active": len(active),
        "total_archived": len(archived),
        "by_kind": by_kind,
        "avg_score": sum(scores) / len(scores) if scores else 0.0,
    }
