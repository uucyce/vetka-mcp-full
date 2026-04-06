"""
MARKER_CIRCULAR_FIX — Shared Pydantic request models for CUT routes.

Extracted from cut_routes.py to break circular import:
  cut_routes.py → cut_routes_workers.py → cut_routes.py

Both modules now import shared models from here.

@status: active
@phase: B70
@task: tb_1775486068_68814_15
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Worker Job Request Models (used by cut_routes.py + cut_routes_workers.py)
# ---------------------------------------------------------------------------

class CutSceneAssemblyRequest(BaseModel):
    sandbox_root: str
    project_id: str
    timeline_id: str = "main"
    graph_id: str = "main"


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
