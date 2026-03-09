import shutil
import subprocess
import time
from pathlib import Path

import pytest

from src.api.routes.artifact_routes import (
    MediaPreviewRequest,
    _ensure_video_preview_assets,
    media_preview,
)


def _require_ffmpeg_stack() -> None:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg/ffprobe not available")


def _mk_video(path: Path, codec: str = "libx264") -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=640x360:rate=24",
            "-t",
            "2",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            codec,
            "-an",
            "-y",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def test_phase159_fastplay_asset_generation_budget(tmp_path: Path):
    _require_ffmpeg_stack()
    video = tmp_path / "clip.mp4"
    _mk_video(video, "libx264")
    started = time.perf_counter()
    assets = _ensure_video_preview_assets(video, duration_sec=2.0)
    elapsed = time.perf_counter() - started
    assert elapsed < 8.0
    assert Path(assets["poster_path"]).exists()
    assert Path(assets["animated_path"]).exists()


def test_phase159_media_preview_returns_video_fastplay_payload(tmp_path: Path, monkeypatch):
    _require_ffmpeg_stack()
    video = tmp_path / "clip.mp4"
    _mk_video(video, "libx264")
    monkeypatch.setenv("VETKA_MEDIA_ENABLE_PREVIEW_DERIVATIVES", "1")
    monkeypatch.setenv("VETKA_MEDIA_ENABLE_PROXY_TRANSCODE", "1")

    req = type("Req", (), {"app": type("App", (), {"state": type("State", (), {})()})()})()
    payload = MediaPreviewRequest(path=str(video), waveform_bins=64, preview_segments_limit=16)
    import asyncio

    data = asyncio.run(media_preview(payload, req))
    assert data["success"] is True
    assert data["modality"] == "video"
    assert "playback" in data
    assert data["playback"]["source_url"].startswith("/api/files/raw?path=")
    assert "preview_assets" in data
    assert data["preview_assets"]["poster_url"].startswith("/api/files/raw?path=")
    assert data["preview_assets"]["animated_preview_url_300ms"].startswith("/api/files/raw?path=")


def test_phase159_media_preview_default_is_direct_with_preview_derivatives(tmp_path: Path, monkeypatch):
    _require_ffmpeg_stack()
    video = tmp_path / "clip.mp4"
    _mk_video(video, "libx264")
    monkeypatch.delenv("VETKA_MEDIA_ENABLE_PREVIEW_DERIVATIVES", raising=False)
    monkeypatch.delenv("VETKA_MEDIA_ENABLE_PROXY_TRANSCODE", raising=False)

    req = type("Req", (), {"app": type("App", (), {"state": type("State", (), {})()})()})()
    payload = MediaPreviewRequest(path=str(video), waveform_bins=64, preview_segments_limit=16)
    import asyncio

    data = asyncio.run(media_preview(payload, req))
    assert data["success"] is True
    assert data["playback"]["strategy"] == "direct"
    assert data["preview_assets"]["poster_url"].startswith("/api/files/raw?path=")
    assert data["preview_assets"]["animated_preview_url_300ms"].startswith("/api/files/raw?path=")
