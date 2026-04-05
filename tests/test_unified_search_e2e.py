# MARKER_137.S1_6_UNIFIED_SEARCH_E2E_TEST
import pytest

pytestmark = pytest.mark.stale(reason="Unified search — merge/filter logic changed")

import asyncio

from src.api.handlers import unified_search as us
from src.api.routes.unified_search_routes import UnifiedSearchRequest, unified_search_endpoint


def test_unified_search_merges_all_sources(monkeypatch):
    monkeypatch.setattr(us, "_file_search", lambda q, l: [{"source": "file", "title": "f", "snippet": "f", "score": 0.6, "url": "file://f"}])
    monkeypatch.setattr(us, "_semantic_search", lambda q, l: [{"source": "semantic", "title": "s", "snippet": "s", "score": 0.9, "url": "file://s"}])
    monkeypatch.setattr(us, "_web_search", lambda q, l: [{"source": "web", "title": "w", "snippet": "w", "score": 0.7, "url": "https://w"}])
    monkeypatch.setattr(us, "_social_search", lambda q, l: [{"source": "social", "title": "x", "snippet": "x", "score": 0.5, "url": "https://x"}])

    payload = us.run_unified_search("artifact", limit=10)

    assert payload["success"] is True
    assert payload["count"] == 4
    assert payload["results"][0]["source"] == "semantic"
    assert set(payload["by_source"].keys()) == {"file", "semantic", "web", "social"}


def test_unified_search_respects_sources_filter(monkeypatch):
    monkeypatch.setattr(us, "_file_search", lambda q, l: [{"source": "file", "title": "f", "snippet": "f", "score": 0.9, "url": "file://f"}])
    monkeypatch.setattr(us, "_semantic_search", lambda q, l: [{"source": "semantic", "title": "s", "snippet": "s", "score": 0.8, "url": "file://s"}])
    monkeypatch.setattr(us, "_web_search", lambda q, l: [{"source": "web", "title": "w", "snippet": "w", "score": 0.7, "url": "https://w"}])

    payload = us.run_unified_search("artifact", limit=10, sources=["web"])

    assert payload["success"] is True
    assert payload["count"] == 1
    assert payload["results"][0]["source"] == "web"


def test_unified_search_route_integration(monkeypatch):
    monkeypatch.setattr(us, "_file_search", lambda q, l: [{"source": "file", "title": "f", "snippet": "f", "score": 0.6, "url": "file://f"}])
    monkeypatch.setattr(us, "_semantic_search", lambda q, l: [{"source": "semantic", "title": "s", "snippet": "s", "score": 0.8, "url": "file://s"}])
    monkeypatch.setattr(us, "_web_search", lambda q, l: [{"source": "web", "title": "w", "snippet": "w", "score": 0.7, "url": "https://w"}])
    monkeypatch.setattr(us, "_social_search", lambda q, l: [])

    result = asyncio.run(
        unified_search_endpoint(
            UnifiedSearchRequest(query="pipeline", limit=5, sources=["file", "semantic", "web"])
        )
    )

    assert result["success"] is True
    assert result["count"] == 3
    assert result["sources"] == ["file", "semantic", "web"]
