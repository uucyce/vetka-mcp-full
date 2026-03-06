from __future__ import annotations

import asyncio

from src.search.hybrid_search import HybridSearchService


def test_phase161_hybrid_adds_filename_source_for_lexical_query() -> None:
    service = HybridSearchService.__new__(HybridSearchService)
    service._initialized = True
    service._qdrant = object()
    service._weaviate = object()
    service._embedding_service = object()

    async def _semantic(query: str, limit: int, collection: str):  # noqa: ARG001
        return [{"id": "sem-1", "path": "/docs/sem.md", "name": "sem.md", "content": "", "score": 0.2, "source": "qdrant"}]

    async def _keyword(query: str, limit: int, collection: str):  # noqa: ARG001
        return [{"id": "kw-1", "path": "/docs/kw.md", "name": "kw.md", "content": "", "score": 0.2, "source": "weaviate"}]

    async def _filename(query: str, limit: int, collection: str):  # noqa: ARG001
        return [{"id": "fn-1", "path": "/docs/VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md", "name": "VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md", "content": "", "score": 1.0, "source": "qdrant_filename"}]

    service._semantic_search = _semantic
    service._keyword_search = _keyword
    service._filename_search = _filename
    service._jepa_reorder = lambda query, results, limit: results[:limit]  # noqa: ARG005
    service._init_backends = lambda: None

    result = asyncio.run(
        service.search(
            query="abbreviation",
            limit=10,
            mode="hybrid",
            collection="leaf",
            skip_cache=True,
        )
    )

    assert result["mode"] == "hybrid"
    assert "filename" in result["sources"]
    assert any("ABBREVIATIONS" in str(item.get("path", "")) for item in result["results"])

