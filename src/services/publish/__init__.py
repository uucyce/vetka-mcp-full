"""
MARKER_B96 — Cross-Platform Publish Service package.

@status: active
@phase: 198
@task: tb_publish_encode_worker

Exports the encode worker surface for use by API routes and UI panels.
"""

from src.services.publish.encode_worker import (
    CODEC_PRESETS,
    PLATFORM_CONSTRAINTS,
    build_ffmpeg_cmd,
    run_encode_job,
    EncodeJobManager,
)

__all__ = [
    "CODEC_PRESETS",
    "PLATFORM_CONSTRAINTS",
    "build_ffmpeg_cmd",
    "run_encode_job",
    "EncodeJobManager",
]
