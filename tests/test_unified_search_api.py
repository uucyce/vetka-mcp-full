# MARKER_136.UNIFIED_SEARCH_BACKEND_TEST
import asyncio

from src.api.handlers import unified_search as us
from src.api.routes.unified_search_routes import (
    UnifiedSearchRequest,
    unified_search_endpoint,
)


def test_run_unified_search_aggregates_sources(monkeypatch):
    monkeypatch.setattr(us, "_file_search", lambda query, limit: [{"source": "file", "title": "a.py", "snippet": "hit", "score": 0.9, "url": "file://a.py"}])
    monkeypatch.setattr(us, "_semantic_search", lambda query, limit: [{"source": "semantic", "title": "b.py", "snippet": "sem", "score": 0.8, "url": "file://b.py"}])
    monkeypatch.setattr(us, "_web_search", lambda query, limit: [{"source": "web", "title": "doc", "snippet": "web", "score": 0.7, "url": "https://example.com"}])
    monkeypatch.setattr(us, "_social_search", lambda query, limit: [])

    payload = us.run_unified_search("auth flow", limit=10)

    assert payload["success"] is True
    assert payload["count"] == 3
    assert payload["results"][0]["source"] == "file"
    assert set(payload["by_source"].keys()) == {"file", "semantic", "web", "social"}


def test_run_unified_search_validates_query():
    payload = us.run_unified_search("x", limit=10)
    assert payload["success"] is False
    assert "Query too short" in payload["error"]


def test_unified_search_route_calls_handler(monkeypatch):
    monkeypatch.setattr(
        "src.api.routes.unified_search_routes.run_unified_search",
        lambda query, limit, sources: {
            "success": True,
            "query": query,
            "sources": sources,
            "results": [],
            "count": 0,
        },
    )

    response = asyncio.run(
        unified_search_endpoint(
            UnifiedSearchRequest(query="pipeline", limit=5, sources=["file", "web"])
        )
    )
    assert response["success"] is True
    assert response["query"] == "pipeline"
    assert response["sources"] == ["file", "web"]
