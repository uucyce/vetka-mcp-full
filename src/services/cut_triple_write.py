"""
MARKER_189.3 — CUT Triple Memory Write service.
Routes scanner output to:
  1. Qdrant media_chunks_v1 (vector upsert with editorial payload)
  2. JSON fallback (montage_sheet.json, media_index.json — always written)
Degraded-safe: JSON always written; Qdrant optional.
Closes Phase 153 findings F1-F3, F5-F6.

@status: active
@phase: 189
@depends: triple_write_manager, multimodal_contracts, scan_types, cut_project_store
@used_by: cut_routes (scan-matrix-async)
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

from src.scanners.scan_types import ScanResult, SceneSegment, TranscriptSegment

logger = logging.getLogger(__name__)

# ── Qdrant integration (lazy, degraded-safe) ──

_triple_write_mgr = None
_qdrant_available: bool | None = None


def _get_triple_write_manager() -> Any | None:
    """Lazy-load TripleWriteManager. Returns None if unavailable."""
    global _triple_write_mgr, _qdrant_available
    if _qdrant_available is False:
        return None
    if _triple_write_mgr is not None:
        return _triple_write_mgr
    try:
        from src.orchestration.triple_write_manager import get_triple_write_manager
        _triple_write_mgr = get_triple_write_manager()
        _qdrant_available = True
        return _triple_write_mgr
    except Exception as exc:
        logger.info("TripleWriteManager not available: %s", exc)
        _qdrant_available = False
        return None


# ── Timecode helpers ──

def _sec_to_timecode(sec: float, fps: int = 25) -> str:
    """Convert seconds to SMPTE timecode HH:MM:SS:FF."""
    if sec < 0:
        sec = 0.0
    total_frames = int(sec * fps)
    h = total_frames // (fps * 3600)
    remainder = total_frames % (fps * 3600)
    m = remainder // (fps * 60)
    remainder = remainder % (fps * 60)
    s = remainder // fps
    f = remainder % fps
    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"


# ── Montage sheet builder ──

def _build_montage_records(
    scan_results: list[dict[str, Any]],
    project_id: str,
    fps: int = 25,
) -> list[dict[str, Any]]:
    """Build vetka_montage_sheet_v1 records from scanner output.

    Each video segment becomes a montage sheet record.
    Transcript text is attached as dialogue_text.
    """
    records: list[dict[str, Any]] = []
    record_counter = 0

    for file_result in scan_results:
        source_path = str(file_result.get("source_path", ""))
        video_scan = file_result.get("video_scan") or {}
        audio_scan = file_result.get("audio_scan") or {}

        segments = video_scan.get("segments") or []
        transcript = audio_scan.get("transcript") or []
        metadata = video_scan.get("metadata") or audio_scan.get("metadata") or {}

        if not segments:
            # Audio-only file: create single record from transcript
            if transcript:
                record_counter += 1
                full_text = " ".join(t.get("text", "") for t in transcript).strip()
                duration = float(metadata.get("duration_sec") or 0)
                records.append({
                    "record_id": f"rec_{record_counter:04d}",
                    "scene_id": "scene_01",
                    "take_id": f"take_{record_counter:04d}",
                    "source_file": source_path,
                    "start_tc": "00:00:00:00",
                    "end_tc": _sec_to_timecode(duration, fps),
                    "duration_sec": round(duration, 3),
                    "dialogue_text": full_text[:2000],
                    "hero_entities": [],
                    "location_entities": [],
                    "action_tags": [],
                    "quality_flags": [],
                    "notes": "",
                })
            continue

        for seg in segments:
            record_counter += 1
            seg_start = float(seg.get("start_sec", 0))
            seg_end = float(seg.get("end_sec", 0))
            seg_dur = float(seg.get("duration_sec", 0)) or (seg_end - seg_start)

            # Collect transcript text that overlaps this segment
            dialogue_parts: list[str] = []
            for t in transcript:
                t_start = float(t.get("start_sec", 0))
                t_end = float(t.get("end_sec", 0))
                if t_end > seg_start and t_start < seg_end:
                    text = str(t.get("text", "")).strip()
                    if text:
                        dialogue_parts.append(text)

            records.append({
                "record_id": f"rec_{record_counter:04d}",
                "scene_id": seg.get("segment_id", f"scene_{record_counter:02d}"),
                "take_id": f"take_{record_counter:04d}",
                "source_file": source_path,
                "start_tc": _sec_to_timecode(seg_start, fps),
                "end_tc": _sec_to_timecode(seg_end, fps),
                "duration_sec": round(seg_dur, 3),
                "dialogue_text": " ".join(dialogue_parts)[:2000],
                "hero_entities": [],
                "location_entities": [],
                "action_tags": [],
                "quality_flags": [],
                "notes": "",
            })

    return records


# ── Qdrant media chunk builder ──

def _build_qdrant_chunks(
    scan_results: list[dict[str, Any]],
    project_id: str,
) -> list[dict[str, Any]]:
    """Build media_chunks_v1 dicts for Qdrant upsert from scanner output.

    Each video segment or transcript utterance becomes a chunk
    with text suitable for embedding.
    """
    chunks: list[dict[str, Any]] = []

    for file_result in scan_results:
        source_path = str(file_result.get("source_path", ""))
        video_scan = file_result.get("video_scan") or {}
        audio_scan = file_result.get("audio_scan") or {}
        metadata = video_scan.get("metadata") or audio_scan.get("metadata") or {}

        transcript = audio_scan.get("transcript") or []
        segments = video_scan.get("segments") or []

        # Transcript utterances → chunks (primary: text-based search)
        for i, utt in enumerate(transcript):
            text = str(utt.get("text", "")).strip()
            if len(text) < 3:
                continue
            chunks.append({
                "parent_file_path": source_path,
                "modality": "audio",
                "chunk_index": len(chunks),
                "start_sec": float(utt.get("start_sec", 0)),
                "end_sec": float(utt.get("end_sec", 0)),
                "text": text,
                "confidence": float(utt.get("confidence", 0)),
                "speaker": utt.get("speaker", ""),
                "project_id": project_id,
                "media_type": str(metadata.get("media_type", "video")),
                "extraction_method": "whisper_stt",
            })

        # Video segments → chunks (with segment description as text)
        for seg in segments:
            seg_id = seg.get("segment_id", "")
            start = float(seg.get("start_sec", 0))
            end = float(seg.get("end_sec", 0))
            dur = float(seg.get("duration_sec", 0))

            # Gather overlapping transcript for this segment
            seg_text_parts: list[str] = []
            for utt in transcript:
                u_start = float(utt.get("start_sec", 0))
                u_end = float(utt.get("end_sec", 0))
                if u_end > start and u_start < end:
                    t = str(utt.get("text", "")).strip()
                    if t:
                        seg_text_parts.append(t)

            # Build descriptive text for the segment
            fname = Path(source_path).stem
            desc = f"Video segment {seg_id} from {fname}"
            if seg_text_parts:
                desc += f": {' '.join(seg_text_parts)}"

            if len(desc) < 5:
                continue

            chunks.append({
                "parent_file_path": source_path,
                "modality": "video",
                "chunk_index": len(chunks),
                "start_sec": start,
                "end_sec": end,
                "text": desc[:2000],
                "confidence": float(seg.get("diff_score", 0)),
                "project_id": project_id,
                "scene_id": seg_id,
                "media_type": "video",
                "codec": str(metadata.get("codec", "")),
                "width": int(metadata.get("width") or 0),
                "height": int(metadata.get("height") or 0),
                "extraction_method": "video_scanner_v1",
            })

    return chunks


# ── Main triple write function ──

def cut_triple_write(
    scan_results: list[dict[str, Any]],
    *,
    project_id: str,
    sandbox_root: str,
    fps: int = 25,
) -> dict[str, Any]:
    """Write scanner results to triple memory stores.

    1. JSON fallback (always written):
       - montage_sheet.json (vetka_montage_sheet_v1)
       - media_index.json (already saved by scan-matrix-async)
    2. Qdrant media_chunks_v1 (degraded-safe):
       - Text embeddings for transcript + segment descriptions
       - Editorial payload (scene_id, timecodes, dialogue, entities)

    Returns status dict with per-store results.
    """
    from src.services.cut_project_store import CutProjectStore

    t0 = time.monotonic()
    result: dict[str, Any] = {
        "json_written": False,
        "qdrant_written": False,
        "qdrant_chunks_count": 0,
        "montage_records_count": 0,
        "degraded_mode": False,
        "degraded_reason": "",
        "elapsed_sec": 0.0,
    }

    store = CutProjectStore(sandbox_root)

    # ── Step 1: JSON fallback (ALWAYS written) ──
    try:
        montage_records = _build_montage_records(scan_results, project_id, fps)
        result["montage_records_count"] = len(montage_records)

        if montage_records:
            montage_sheet = {
                "schema_version": "vetka_montage_sheet_v1",
                "project": {
                    "project_id": project_id,
                    "project_name": project_id,
                    "fps": fps,
                },
                "records": montage_records,
            }
            # Save to sandbox runtime state
            montage_path = os.path.join(
                sandbox_root, "runtime_state", "montage_sheet.latest.json"
            )
            os.makedirs(os.path.dirname(montage_path), exist_ok=True)
            import json
            with open(montage_path, "w", encoding="utf-8") as f:
                json.dump(montage_sheet, f, ensure_ascii=False, indent=2)

        result["json_written"] = True
        logger.info(
            "CUT triple write JSON: %d montage records for %s",
            len(montage_records), project_id,
        )
    except Exception as exc:
        logger.error("CUT triple write JSON failed: %s", exc)
        result["degraded_mode"] = True
        result["degraded_reason"] = f"json_write_failed: {exc}"

    # ── Step 2: Qdrant media_chunks_v1 (degraded-safe) ──
    try:
        tw = _get_triple_write_manager()
        if tw is None:
            result["degraded_mode"] = True
            result["degraded_reason"] = result.get("degraded_reason") or "qdrant_unavailable"
            logger.info("CUT triple write: Qdrant unavailable, JSON-only mode")
        else:
            chunks = _build_qdrant_chunks(scan_results, project_id)
            if chunks:
                # Use TripleWriteManager's write_media_chunks for each file
                files_grouped: dict[str, list[dict[str, Any]]] = {}
                for chunk in chunks:
                    fp = chunk.get("parent_file_path", "")
                    files_grouped.setdefault(fp, []).append(chunk)

                total_upserted = 0
                for file_path, file_chunks in files_grouped.items():
                    modality = file_chunks[0].get("modality", "media") if file_chunks else "media"
                    count = tw.write_media_chunks(
                        file_path=file_path,
                        media_chunks=file_chunks,
                        modality=modality,
                    )
                    total_upserted += count

                result["qdrant_written"] = total_upserted > 0
                result["qdrant_chunks_count"] = total_upserted
                logger.info(
                    "CUT triple write Qdrant: %d chunks upserted for %s",
                    total_upserted, project_id,
                )
            else:
                logger.info("CUT triple write: no chunks to upsert (no text content)")
    except Exception as exc:
        logger.warning("CUT triple write Qdrant failed (degraded): %s", exc)
        result["degraded_mode"] = True
        result["degraded_reason"] = result.get("degraded_reason") or f"qdrant_write_failed: {exc}"

    result["elapsed_sec"] = round(time.monotonic() - t0, 3)
    return result
