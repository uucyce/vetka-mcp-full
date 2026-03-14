from __future__ import annotations

from src.memory.qdrant_client import QdrantVetkaClient


class _FakePoint:
    def __init__(self, pid: str, payload: dict):
        self.id = pid
        self.payload = payload


class _FakeQdrantClient:
    def __init__(self):
        self.calls = 0

    def scroll(self, **kwargs):
        self.calls += 1
        offset = kwargs.get("offset")
        scroll_filter = kwargs.get("scroll_filter")

        if scroll_filter is not None:
            if offset is None:
                return ([_FakePoint("p1", {"path": "/docs/other.md", "name": "other.md", "type": "scanned_file", "deleted": False})], "page2")
            return ([_FakePoint("p2", {"path": "/docs/VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md", "name": "VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md", "type": "scanned_file", "deleted": False})], None)

        return ([], None)


def test_phase161_qdrant_filename_search_paginates_beyond_first_scroll_page() -> None:
    client = QdrantVetkaClient.__new__(QdrantVetkaClient)
    client.client = _FakeQdrantClient()

    rows = client.search_by_filename("abbreviation", limit=20, collection="vetka_elisya")

    assert len(rows) == 1
    assert "ABBREVIATIONS" in rows[0]["path"]
    # Ensure pagination happened (first and second page).
    assert client.client.calls >= 2

