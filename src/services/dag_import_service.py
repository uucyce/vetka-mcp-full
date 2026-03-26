"""
MARKER_SOURCE_ACQUIRE: DAG import service — creates media nodes from acquire jobs.
Writes AcquireSourceMeta to DAG for provenance tracking.

@status: shell
@phase: 198
@task: tb_1774431988_1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class AcquireSourceMeta:
    """Provenance metadata attached to DAG media nodes created via Source Acquire."""
    source_type: str  # 'youtube' | 'ai_generated_local' | 'ai_generated_remote' | 'local_import'
    original_url: Optional[str] = None
    prompt: Optional[str] = None
    generation_params: Optional[dict] = None
    remote_provider: Optional[str] = None  # 'runway' | 'sora' | 'kling'
    youtube_video_id: Optional[str] = None
    youtube_segment_in: Optional[float] = None
    youtube_segment_out: Optional[float] = None
    acquire_job_id: str = ""
    acquired_at: float = field(default_factory=time.time)


def create_media_node_from_job(
    project_id: str,
    file_path: str,
    label: str,
    source_meta: AcquireSourceMeta,
    duration_sec: float = 0.0,
    media_type: str = "video",
) -> dict:
    """Create a DAG media node dict from an acquire job result.

    Returns a node dict ready for insertion into the project DAG.
    The actual DAG write is handled by the caller (cut_project_store or timeline ops).

    Args:
        project_id: Project identifier.
        file_path: Absolute path to the acquired media file.
        label: Human-readable label for the node.
        source_meta: Provenance metadata from the acquire pipeline.
        duration_sec: Media duration in seconds (0 if unknown).
        media_type: 'video', 'audio', or 'image'.

    Returns:
        Dict with node_id, type, label, file_path, duration, and acquire_meta.
    """
    node_id = f"media_{uuid.uuid4().hex[:12]}"
    return {
        "node_id": node_id,
        "project_id": project_id,
        "type": media_type,
        "label": label,
        "file_path": file_path,
        "duration_sec": duration_sec,
        "acquire_meta": asdict(source_meta),
        "created_at": time.time(),
    }
