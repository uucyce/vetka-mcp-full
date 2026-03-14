import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.api.routes.artifact_routes import (
    MediaCamOverlayRequest,
    MediaPreviewRequest,
    MediaStartupRequest,
    MediaTranscriptNormalizeRequest,
    media_cam_overlay,
    media_preview,
    media_startup,
    media_transcript_normalized,
)
from src.scanners.extractor_registry import MediaExtractorRegistry


REAL_BERLIN_ROOT = Path("/Users/danilagulin/work/teletape_temp/berlin")
REAL_VIDEO_DIR = REAL_BERLIN_ROOT / "video_gen"
REAL_SCENARIO = REAL_BERLIN_ROOT / "ironwall_v4_grok.md"
REAL_AUDIO = Path("/Users/danilagulin/work/teletape_temp/albom/250623_vanpticdanyana_berlin_Punch.m4a")


def _req_no_qdrant():
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=None)))


@pytest.mark.integration
def test_real_media_startup_detects_script_and_media():
    if not REAL_BERLIN_ROOT.exists():
        pytest.skip(f"Missing root: {REAL_BERLIN_ROOT}")
    if not REAL_SCENARIO.exists():
        pytest.skip(f"Missing scenario: {REAL_SCENARIO}")

    result = asyncio.run(
        media_startup(
            MediaStartupRequest(
                scope_path=str(REAL_BERLIN_ROOT),
                quick_scan_limit=400,
            )
        )
    )
    assert result["success"] is True
    assert result["missing_inputs"]["script_or_treatment"] is False
    assert result["stats"]["media_files"] > 0


@pytest.mark.integration
def test_real_video_preview_and_cam_overlay():
    if not REAL_VIDEO_DIR.exists():
        pytest.skip(f"Missing video dir: {REAL_VIDEO_DIR}")
    clips = sorted(REAL_VIDEO_DIR.glob("*.mp4"))
    if not clips:
        pytest.skip("No mp4 clips found")
    clip = clips[0]
    req = _req_no_qdrant()

    preview = asyncio.run(
        media_preview(
            MediaPreviewRequest(path=str(clip), waveform_bins=32, preview_segments_limit=32),
            req,
        )
    )
    assert preview["success"] is True
    assert preview["modality"] == "video"
    assert preview["duration_sec"] > 0

    cam = asyncio.run(
        media_cam_overlay(
            MediaCamOverlayRequest(path=str(clip), bins=48, segments_limit=120),
            req,
        )
    )
    assert cam["success"] is True
    assert len(cam["cam_features"]["uniqueness_track"]) == 48
    assert len(cam["cam_features"]["memorability_track"]) == 48
    assert cam["playback_metadata"]["segment_source"] in {"qdrant_media_chunks_v1", "ffmpeg_scene_detect", "none"}


@pytest.mark.integration
def test_real_audio_preview_contract():
    if not REAL_AUDIO.exists():
        pytest.skip(f"Missing audio: {REAL_AUDIO}")
    req = _req_no_qdrant()
    result = asyncio.run(
        media_preview(
            MediaPreviewRequest(path=str(REAL_AUDIO), waveform_bins=40, preview_segments_limit=16),
            req,
        )
    )
    assert result["success"] is True
    assert result["modality"] == "audio"
    assert result["duration_sec"] > 0


@pytest.mark.integration
def test_real_audio_transcript_normalized_contract():
    if not REAL_AUDIO.exists():
        pytest.skip(f"Missing audio: {REAL_AUDIO}")
    req = _req_no_qdrant()
    result = asyncio.run(
        media_transcript_normalized(
            MediaTranscriptNormalizeRequest(
                path=str(REAL_AUDIO),
                max_transcribe_sec=45,
                clip_for_testing_only=True,
                segments_limit=128,
            ),
            req,
        )
    )
    assert result["success"] is True
    tx = result["transcript_normalized_json"]
    assert tx["schema_version"] == "vetka_transcript_v1"
    assert tx["modality"] == "audio"
    assert "segments" in tx and isinstance(tx["segments"], list)
    assert result["playback_metadata"]["max_transcribe_sec"] == 45
    assert result["playback_metadata"]["clip_for_testing_only"] is True


@pytest.mark.integration
def test_real_photo_extractor_route():
    if not REAL_BERLIN_ROOT.exists():
        pytest.skip(f"Missing root: {REAL_BERLIN_ROOT}")
    images = sorted(REAL_BERLIN_ROOT.rglob("*.png"))
    if not images:
        pytest.skip("No png images found")
    img = images[0]

    registry = MediaExtractorRegistry()
    result = registry.extract_file(img, rel_path=str(img), max_text_chars=600)
    assert result.extractor_id == "ocr_processor"
    assert result.metadata.get("extraction_route") in {"ocr", "ocr_empty", "ocr_error"}
    assert isinstance(result.text, str)
