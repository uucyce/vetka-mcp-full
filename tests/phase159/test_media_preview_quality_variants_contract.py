from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_media_preview_exposes_scaled_playback_sources():
    src = _read("src/api/routes/artifact_routes.py")
    assert "def _ensure_video_playback_variants(target: Path) -> dict[str, str]:" in src
    assert "playback_{name}.mp4" in src
    assert "\"playback\": {" in src
    assert "\"sources_scale\": playback_sources_scale" in src
    assert "playback_sources_scale: dict[str, str] = {\"full\": _encode_raw_url(target)}" in src
