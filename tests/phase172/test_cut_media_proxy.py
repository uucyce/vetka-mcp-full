"""
MARKER_172.1.MEDIA_PROXY_TESTS
Tests for GET /api/cut/media-proxy: MIME detection, path security, range requests.
"""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.cut_routes import router, _resolve_mime, _is_safe_subpath


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# ─── MIME detection ───


def test_mime_video_mp4():
    assert _resolve_mime("/foo/bar.mp4") == "video/mp4"


def test_mime_audio_wav():
    assert _resolve_mime("/foo/audio.wav") == "audio/wav"


def test_mime_audio_m4a():
    assert _resolve_mime("/track.m4a") == "audio/mp4"


def test_mime_image_jpg():
    assert _resolve_mime("/thumb.jpg") == "image/jpeg"


def test_mime_unknown():
    assert _resolve_mime("/file.xyz") == "application/octet-stream"


def test_mime_case_insensitive():
    assert _resolve_mime("/VIDEO.MP4") == "video/mp4"


# ─── Path safety ───


def test_safe_subpath(tmp_path: Path):
    child = tmp_path / "sub" / "file.mp4"
    child.parent.mkdir(parents=True)
    child.touch()
    assert _is_safe_subpath(str(tmp_path), str(child)) is True


def test_traversal_rejected(tmp_path: Path):
    outside = tmp_path / ".." / "etc" / "passwd"
    assert _is_safe_subpath(str(tmp_path), str(outside)) is False


def test_symlink_escape_rejected(tmp_path: Path):
    target = Path("/tmp/outside_target")
    if not target.exists():
        target.mkdir(parents=True, exist_ok=True)
    link = tmp_path / "escape"
    try:
        link.symlink_to(target)
        assert _is_safe_subpath(str(tmp_path), str(link / "file.mp4")) is False
    finally:
        if link.is_symlink():
            link.unlink()


# ─── Full file serving ───


def test_serve_mp4_file(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    media = sandbox / "clip.mp4"
    media.write_bytes(b"\x00\x00\x00\x1c" + b"ftyp" + b"\x00" * 20)

    client = _make_client()
    resp = client.get(
        "/api/cut/media-proxy",
        params={"sandbox_root": str(sandbox), "path": str(media)},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "video/mp4"
    assert resp.headers["accept-ranges"] == "bytes"
    assert "access-control-allow-origin" in resp.headers
    assert len(resp.content) == 28


def test_serve_wav_file(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    audio = sandbox / "sound.wav"
    audio.write_bytes(b"RIFF" + b"\x00" * 40)

    client = _make_client()
    resp = client.get(
        "/api/cut/media-proxy",
        params={"sandbox_root": str(sandbox), "path": str(audio)},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/wav"


def test_serve_relative_path(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    media = sandbox / "clip.mp4"
    media.write_bytes(b"\x00" * 10)

    client = _make_client()
    resp = client.get(
        "/api/cut/media-proxy",
        params={"sandbox_root": str(sandbox), "path": "clip.mp4"},
    )
    assert resp.status_code == 200


# ─── Range requests ───


def test_range_request_partial_content(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    media = sandbox / "big.mp4"
    media.write_bytes(bytes(range(256)))

    client = _make_client()
    resp = client.get(
        "/api/cut/media-proxy",
        params={"sandbox_root": str(sandbox), "path": str(media)},
        headers={"Range": "bytes=0-9"},
    )
    assert resp.status_code == 206
    assert resp.headers["content-range"] == "bytes 0-9/256"
    assert len(resp.content) == 10
    assert resp.content == bytes(range(10))


def test_range_request_open_end(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    media = sandbox / "clip.mp4"
    media.write_bytes(bytes(range(100)))

    client = _make_client()
    resp = client.get(
        "/api/cut/media-proxy",
        params={"sandbox_root": str(sandbox), "path": str(media)},
        headers={"Range": "bytes=50-"},
    )
    assert resp.status_code == 206
    assert len(resp.content) == 50
    assert resp.headers["content-range"] == "bytes 50-99/100"


def test_range_request_beyond_file_size(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    media = sandbox / "small.mp4"
    media.write_bytes(b"\x00" * 10)

    client = _make_client()
    resp = client.get(
        "/api/cut/media-proxy",
        params={"sandbox_root": str(sandbox), "path": str(media)},
        headers={"Range": "bytes=100-200"},
    )
    assert resp.status_code == 416


# ─── Error cases ───


def test_file_not_found(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()

    client = _make_client()
    resp = client.get(
        "/api/cut/media-proxy",
        params={"sandbox_root": str(sandbox), "path": str(sandbox / "nonexistent.mp4")},
    )
    assert resp.status_code == 404


def test_path_traversal_blocked(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()

    client = _make_client()
    resp = client.get(
        "/api/cut/media-proxy",
        params={"sandbox_root": str(sandbox), "path": str(sandbox / ".." / ".." / "etc" / "passwd")},
    )
    assert resp.status_code == 403


def test_missing_params():
    client = _make_client()
    resp = client.get("/api/cut/media-proxy", params={"sandbox_root": "", "path": ""})
    assert resp.status_code == 400


def test_cors_headers_present(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    media = sandbox / "test.mp4"
    media.write_bytes(b"\x00" * 4)

    client = _make_client()
    resp = client.get(
        "/api/cut/media-proxy",
        params={"sandbox_root": str(sandbox), "path": str(media)},
    )
    assert resp.headers["access-control-allow-origin"] == "*"
    assert "Range" in resp.headers["access-control-allow-headers"]
    assert "Content-Range" in resp.headers["access-control-expose-headers"]
