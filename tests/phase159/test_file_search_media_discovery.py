from pathlib import Path

from src.search.file_search_service import search_files


def test_phase159_file_search_falls_back_when_mdfind_misses(monkeypatch, tmp_path):
    media_dir = tmp_path / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    clip = media_dir / "d425-426f-be09-f2e1497a0e33.mp4"
    clip.write_bytes(b"\x00\x00\x00\x18ftypmp42")

    monkeypatch.setattr("src.search.file_search_service._detect_provider", lambda: "mdfind")
    monkeypatch.setattr("src.search.file_search_service._allowed_search_roots", lambda provider: [tmp_path])
    monkeypatch.setattr("src.search.file_search_service._name_search_mdfind", lambda root, query, limit: [])

    payload = search_files(query="d425-426f", mode="filename", limit=10)
    assert payload["success"] is True
    assert payload.get("intent") == "name_like"
    assert payload["count"] >= 1
    paths = [str(r.get("path", "")) for r in payload["results"]]
    assert str(clip) in paths


def test_phase159_file_search_supports_media_extension_hits(monkeypatch, tmp_path):
    media_dir = tmp_path / "video_gen"
    media_dir.mkdir(parents=True, exist_ok=True)
    clip = media_dir / "4c6596dd-8b34-4695-9a7e-a254add62fcb.mp4"
    clip.write_bytes(b"\x00\x00\x00\x18ftypmp42")

    monkeypatch.setattr("src.search.file_search_service._detect_provider", lambda: "walk")
    monkeypatch.setattr("src.search.file_search_service._allowed_search_roots", lambda provider: [tmp_path])

    payload = search_files(query="4c6596dd", mode="filename", limit=10)
    assert payload["success"] is True
    assert payload["count"] >= 1
    top = payload["results"][0]
    assert top["path"].endswith(".mp4")
