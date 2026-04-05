"""
MARKER_B5 — CUT Render Engine (re-export facade).

Split into domain modules for maintainability:
  - cut_codecs.py:          CODEC_MAP, log decode filters
  - cut_formats.py:         RESOLUTION_MAP, EXPORT_PRESETS, SOCIAL_PRESETS
  - cut_render_pipeline.py: RenderPlan, FilterGraphBuilder, render_timeline, etc.

This file re-exports all public symbols for backward compatibility.
Import from here or directly from the sub-modules.

@status: active
@phase: B5
@task: tb_1773981833_10
@depends: cut_codec_probe, cut_mcp_job_store, cut_project_store
"""
from __future__ import annotations

# --- Codec registry + log decode ---
from src.services.cut_codecs import (  # noqa: F401
    CODEC_MAP,
    _LOG_DECODE_FILTERS,
    compile_log_decode_filter,
    _compile_log_decode_filter,
)

# --- Export presets + resolution map ---
from src.services.cut_formats import (  # noqa: F401
    EXPORT_PRESETS,
    RESOLUTION_MAP,
    SOCIAL_PRESETS,
)

# --- Render pipeline (dataclasses, builders, orchestrator) ---
from src.services.cut_render_pipeline import (  # noqa: F401
    FilterGraphBuilder,
    RenderCancelled,
    RenderClip,
    RenderPlan,
    Transition,
    _build_atempo_chain,
    _build_concat_cmd,
    _build_filter_complex_cmd,
    _map_transition_type,
    build_ffmpeg_command,
    build_render_plan,
    export_audio_stems,
    generate_thumbnail,
    render_timeline,
)

__all__ = [
    # Codecs
    "CODEC_MAP",
    "_LOG_DECODE_FILTERS",
    "compile_log_decode_filter",
    "_compile_log_decode_filter",
    # Formats
    "EXPORT_PRESETS",
    "RESOLUTION_MAP",
    "SOCIAL_PRESETS",
    # Pipeline
    "FilterGraphBuilder",
    "RenderCancelled",
    "RenderClip",
    "RenderPlan",
    "Transition",
    "_build_atempo_chain",
    "_build_concat_cmd",
    "_build_filter_complex_cmd",
    "_map_transition_type",
    "build_ffmpeg_command",
    "build_render_plan",
    "export_audio_stems",
    "generate_thumbnail",
    "render_timeline",
]
