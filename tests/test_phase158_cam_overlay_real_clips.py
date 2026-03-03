import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.api.routes.artifact_routes import MediaCamOverlayRequest, media_cam_overlay


REAL_VIDEO_DIR = Path("/Users/danilagulin/work/teletape_temp/berlin/video_gen")
REAL_SCENARIO = Path("/Users/danilagulin/work/teletape_temp/berlin/ironwall_v4_grok.md")


@pytest.mark.integration
def test_cam_overlay_real_kling_clips_local_dataset():
    if not REAL_VIDEO_DIR.exists():
        pytest.skip(f"Missing real dataset dir: {REAL_VIDEO_DIR}")
    if not REAL_SCENARIO.exists():
        pytest.skip(f"Missing scenario file: {REAL_SCENARIO}")

    clips = sorted(REAL_VIDEO_DIR.glob("*.mp4"))
    if not clips:
        pytest.skip("No .mp4 files found in real dataset dir")

    sample = clips[:2]
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=None)))
    non_degraded = 0

    for clip in sample:
        result = asyncio.run(
            media_cam_overlay(
                MediaCamOverlayRequest(path=str(clip), bins=48, segments_limit=120),
                request,
            )
        )
        assert result["success"] is True
        assert len(result["cam_features"]["uniqueness_track"]) == 48
        assert len(result["cam_features"]["memorability_track"]) == 48
        assert isinstance(result["cam_features"]["top_moments"], list)
        assert result["playback_metadata"]["cam_bins"] == 48
        assert result["playback_metadata"]["segment_source"] in {
            "qdrant_media_chunks_v1",
            "ffmpeg_scene_detect",
            "none",
        }
        if not result.get("degraded_mode", True):
            non_degraded += 1

    assert non_degraded >= 1, "Expected at least one real clip to produce non-degraded CAM overlay"
