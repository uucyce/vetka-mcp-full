# MARKER_138.S2_2_ENGRAM_BRIDGE_TEST
import pytest

pytestmark = pytest.mark.stale(reason="Jarvis ENGRAM bridge — context collection API changed")

import asyncio

from src.jarvis.engram_bridge import JarvisEngramBridge


class DummyEnricher:
    def _get_user_context(self, user_id, include_categories=None):  # noqa: ARG002
        return {"user_id": user_id, "communication_style": {"detail_level": 0.8}}


class DummyMemory:
    def get_preference(self, user_id, category, key):  # noqa: ARG002
        if category == "project_highlights" and key == "current_project":
            return "vetka"
        if category == "communication_style" and key == "detail_level":
            return 0.8
        return None


def test_build_context_collects_memory_snapshot():
    bridge = JarvisEngramBridge(enricher=DummyEnricher(), memory=DummyMemory())
    payload = asyncio.run(bridge.build_context(user_id="u1", request="help"))

    assert payload["user_id"] == "u1"
    assert payload["focus"] == "vetka"
    assert payload["detail_level"] == 0.8
    assert "context" in payload
