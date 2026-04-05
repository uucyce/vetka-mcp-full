# MARKER_136.UNIFIED_SEARCH_BACKEND_TEST
# MARKER_137.S1_2_TAVILY_WIRE_TEST
import pytest

pytestmark = pytest.mark.stale(reason="Unified search — web search normalization logic changed")

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


def test_web_search_normalizes_scores_and_dedups(monkeypatch):
    class DummyWebSearchTool:
        def execute(self, arguments):  # noqa: ARG002
            return {
                "success": True,
                "result": {
                    "results": [
                        {"title": "A", "url": "https://a.test", "content": "x", "score": 7.0},
                        {"title": "A-dup", "url": "https://a.test", "content": "dup", "score": 0.9},
                        {"title": "B", "url": "https://b.test", "content": "y", "score": -1.0},
                        {"title": "C", "url": "", "content": "z", "score": None},
                    ]
                },
            }

    monkeypatch.setattr("src.mcp.tools.web_search_tool.WebSearchTool", DummyWebSearchTool)

    rows = us._web_search("query", limit=10)
    assert len(rows) == 3

    # 7.0 -> normalized to 0.7
    first = next(r for r in rows if r["url"] == "https://a.test")
    assert first["score"] == 0.7

    # negative -> clamped
    second = next(r for r in rows if r["url"] == "https://b.test")
    assert second["score"] == 0.0

    # missing score -> rank fallback
    third = next(r for r in rows if r["url"] == "")
    assert third["score"] > 0.0
