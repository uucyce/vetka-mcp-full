import asyncio

import pytest
from fastapi import HTTPException

from src.api.routes import triple_write_routes as routes


def test_search_media_chunks_rejects_short_query():
    req = routes.MediaChunksSearchRequest(query="a")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(routes.search_media_chunks(req))
    assert exc.value.status_code == 400


def test_search_media_chunks_returns_items(monkeypatch):
    class _TW:
        def search_media_chunks(self, query, limit=20, modality=None, parent_file_path=None):
            assert query == "speaker intro"
            assert limit == 3
            assert modality == "audio"
            return [
                {
                    "score": 0.91,
                    "parent_file_path": "data/a.wav",
                    "chunk_index": 0,
                    "start_sec": 0.0,
                    "end_sec": 3.5,
                    "text": "hello world",
                    "modality": "audio",
                }
            ]

    monkeypatch.setattr(
        "src.orchestration.triple_write_manager.get_triple_write_manager",
        lambda: _TW(),
    )

    req = routes.MediaChunksSearchRequest(query="speaker intro", limit=3, modality="audio")
    result = asyncio.run(routes.search_media_chunks(req))
    assert result["success"] is True
    assert result["count"] == 1
    assert result["items"][0]["modality"] == "audio"


def test_triple_write_reindex_uses_resolved_fpath(monkeypatch, tmp_path):
    class _TW:
        qdrant_client = None
        weaviate_client = None

        def get_embedding(self, text):
            return [0.0] * 768

        def write_file(self, file_path, content, embedding, metadata=None):
            return {"weaviate": False, "qdrant": True, "changelog": True, "vetka_tree": True}

    test_dir = tmp_path / "src"
    test_dir.mkdir(parents=True, exist_ok=True)
    (test_dir / "note.md").write_text("# hello\ncontent", encoding="utf-8")

    monkeypatch.setattr(routes, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(
        "src.orchestration.triple_write_manager.get_triple_write_manager",
        lambda: _TW(),
    )

    req = routes.ReindexRequest(path="src", limit=10, multimodal=False)
    result = asyncio.run(routes.triple_write_reindex(req))
    assert result["success"] is True
    assert result["indexed"] == 1
    assert result["errors"] == 0
