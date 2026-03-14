from __future__ import annotations

import pytest

from src.search.hybrid_search import HybridSearchService


@pytest.mark.asyncio
async def test_hybrid_descriptive_explicit_file_request_prefers_file_source(monkeypatch):
    svc = HybridSearchService()

    # Prevent real backend init and force both sources to be "available"
    def _fake_init():
        svc._initialized = True
        svc._qdrant = object()
        svc._weaviate = object()
        svc._embedding_service = None

    monkeypatch.setattr(svc, "_init_backends", _fake_init)

    async def _semantic(*args, **kwargs):
        return [
            {
                "id": "sem-1",
                "path": "/tmp/__init__.py",
                "content": "semantic noise",
                "score": 0.99,
                "source": "qdrant",
            }
        ]

    async def _keyword(*args, **kwargs):
        return []

    async def _file(*args, **kwargs):
        return [
            {
                "id": "file-1",
                "path": "/repo/docs/VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md",
                "content": "doc",
                "score": 0.6,
                "source": "file_local",
            },
            {
                "id": "file-2",
                "path": "/repo/docs/MARKER_157_ABBREVIATIONS_RUNTIME_MAP_2026-03-01.md",
                "content": "doc",
                "score": 0.5,
                "source": "file_local",
            },
        ]

    monkeypatch.setattr(svc, "_semantic_search", _semantic)
    monkeypatch.setattr(svc, "_keyword_search", _keyword)
    monkeypatch.setattr(svc, "_file_search_local", _file)

    out = await svc.search(
        query="Найди файл где все абревиатуры с памятью связано",
        limit=10,
        mode="hybrid",
        skip_cache=True,
    )

    assert out["mode"] == "file"
    assert out["sources"] == ["file"]
    assert out["results"]
    assert out["results"][0]["path"].endswith("VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md")
