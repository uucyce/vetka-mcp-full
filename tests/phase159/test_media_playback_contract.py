import asyncio
from pathlib import Path

from src.api.routes.files_routes import _normalize_media_mime, get_raw_file


def test_phase159_normalize_media_mime_for_m4a():
    out = _normalize_media_mime("/tmp/a.m4a", "audio/mp4a-latm")
    assert out == "audio/mp4"


def test_phase159_get_raw_file_uses_normalized_media_type(tmp_path):
    media = tmp_path / "voice.m4a"
    media.write_bytes(b"\x00\x00\x00\x18ftypM4A ")
    resp = asyncio.run(get_raw_file(path=str(media)))
    assert getattr(resp, "media_type", "") == "audio/mp4"


def test_phase159_playback_contract_raw_media_endpoint_serves_existing_file(tmp_path):
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"\x00\x00\x00\x18ftypmp42")
    resp = asyncio.run(get_raw_file(path=str(media)))
    assert Path(resp.path).exists()
    assert resp.media_type.startswith("video/")
