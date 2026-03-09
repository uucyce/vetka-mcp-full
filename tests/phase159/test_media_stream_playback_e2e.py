import json
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.files_routes import router as files_router


def _require_ffmpeg_stack() -> None:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg/ffprobe not available")


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def _probe(path: Path) -> dict:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(out.stdout or "{}")


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(files_router)
    return TestClient(app)


def test_phase159_raw_audio_stream_is_decodable(tmp_path: Path, client: TestClient):
    _require_ffmpeg_stack()
    src = tmp_path / "tone.m4a"
    _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-y",
            str(src),
        ]
    )

    resp = client.get("/api/files/raw", params={"path": str(src)})
    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("audio/mp4")

    served = tmp_path / "served_audio.m4a"
    served.write_bytes(resp.content)
    meta = _probe(served)
    duration = float(meta.get("format", {}).get("duration", 0.0) or 0.0)
    assert duration > 1.5


def test_phase159_raw_video_stream_is_decodable(tmp_path: Path, client: TestClient):
    _require_ffmpeg_stack()
    src = tmp_path / "clip.mp4"
    _run(
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
            "libx264",
            "-y",
            str(src),
        ]
    )

    resp = client.get("/api/files/raw", params={"path": str(src)})
    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("video/mp4")

    served = tmp_path / "served_video.mp4"
    served.write_bytes(resp.content)
    meta = _probe(served)
    duration = float(meta.get("format", {}).get("duration", 0.0) or 0.0)
    streams = meta.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    assert duration > 1.5
    assert int(video.get("width", 0) or 0) == 640
    assert int(video.get("height", 0) or 0) == 360

