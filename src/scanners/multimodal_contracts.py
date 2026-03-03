"""
Multimodal extraction contracts for ingestion pipeline.

MARKER_153.IMPL.CONTRACTS_MULTIMODAL
MARKER_158.QDRANT.SCHEMA_MEDIA_CHUNKS_V1
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

MEDIA_CHUNKS_SCHEMA_VERSION = "media_chunks_v1"
EXTRACTION_VERSION = "phase158_media_chunks_v1"
TIMELINE_LANES = {"video_main", "audio_sync", "take_alt_y", "take_alt_z"}
DEGRADED_EXTRACTION_ROUTES = {
    "summary_fallback",
    "ocr_error",
    "ocr_empty",
    "stt_error",
    "stt_empty",
}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _default_timeline_lane(modality: str) -> str:
    normalized = str(modality or "").strip().lower()
    if normalized == "audio":
        return "audio_sync"
    if normalized == "video":
        return "video_main"
    return "video_main"


@dataclass
class OCRResult:
    text: str
    confidence: float
    boxes: List[Dict[str, Any]]
    source_path: str
    extractor: str
    timestamp_sec: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MediaChunk:
    start_sec: float
    end_sec: float
    text: str
    confidence: float = 0.0
    speaker: Optional[str] = None
    frame_ref: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def normalize_media_chunk(
    chunk: Dict[str, Any],
    *,
    chunk_index: int,
    parent_file_path: str,
    modality: str,
    extractor_id: str = "",
) -> Dict[str, Any]:
    """Normalize arbitrary chunk dict to canonical media_chunks_v1 schema."""
    start_sec = max(0.0, _to_float(chunk.get("start_sec", 0.0), 0.0))
    end_sec = max(0.0, _to_float(chunk.get("end_sec", 0.0), 0.0))
    if end_sec < start_sec:
        end_sec = start_sec
    text = str(chunk.get("text", "") or "")
    confidence = max(0.0, min(1.0, _to_float(chunk.get("confidence", 0.0), 0.0)))
    speaker = chunk.get("speaker")
    frame_ref = chunk.get("frame_ref")
    timeline_lane = str(chunk.get("timeline_lane", "") or "").strip().lower()
    if timeline_lane not in TIMELINE_LANES:
        timeline_lane = _default_timeline_lane(modality)
    lane_index = max(0, _to_int(chunk.get("lane_index", 0), 0))
    take_id = str(chunk.get("take_id", "") or "")
    sync_group_id = str(chunk.get("sync_group_id", parent_file_path) or parent_file_path)
    chunk_id = f"{parent_file_path}#chunk:{chunk_index}"
    return {
        "schema_version": MEDIA_CHUNKS_SCHEMA_VERSION,
        "chunk_id": chunk_id,
        "chunk_index": int(chunk_index),
        "parent_file_path": parent_file_path,
        "modality": modality,
        "start_sec": start_sec,
        "end_sec": end_sec,
        "duration_sec": max(0.0, end_sec - start_sec),
        "text": text,
        "confidence": confidence,
        "speaker": speaker,
        "frame_ref": frame_ref,
        "extractor_id": extractor_id,
        "timeline_lane": timeline_lane,
        "lane_index": lane_index,
        "take_id": take_id,
        "sync_group_id": sync_group_id,
    }


def normalize_media_chunks(
    media_chunks: List[Dict[str, Any]],
    *,
    parent_file_path: str,
    modality: str,
    extractor_id: str = "",
    limit: int = 128,
) -> List[Dict[str, Any]]:
    source = list((media_chunks or [])[:limit])
    source = sorted(
        source,
        key=lambda c: (
            max(0.0, _to_float(c.get("start_sec", 0.0), 0.0)),
            max(0.0, _to_float(c.get("end_sec", 0.0), 0.0)),
        ),
    )
    normalized: List[Dict[str, Any]] = []
    for idx, chunk in enumerate(source):
        normalized.append(
            normalize_media_chunk(
                chunk,
                chunk_index=idx,
                parent_file_path=parent_file_path,
                modality=modality,
                extractor_id=extractor_id,
            )
        )
    return normalized


def build_multimodal_payload(
    *,
    extension: str,
    mime_type: str,
    modality: str,
    ingest_mode: str,
    extractor_id: str,
    extraction_route: str,
    media_chunks_v1: List[Dict[str, Any]],
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    route = str(extraction_route or "").strip().lower()
    degraded_mode = route in DEGRADED_EXTRACTION_ROUTES
    payload = {
        "extension": extension,
        "mime_type": mime_type,
        "modality": modality,
        "ingest_mode": ingest_mode,
        "extractor_id": extractor_id,
        "extraction_route": extraction_route,
        "media_chunks": media_chunks_v1[:32],  # Backward compatibility lane
        "media_chunks_v1": media_chunks_v1,
        "media_chunks_schema": MEDIA_CHUNKS_SCHEMA_VERSION,
        "extraction_version": EXTRACTION_VERSION,
        "degraded_mode": degraded_mode,
        "degraded_reason": route if degraded_mode else "",
    }
    if extra:
        payload.update(extra)
    return payload
