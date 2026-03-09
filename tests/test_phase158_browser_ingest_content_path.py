import asyncio
import base64
from types import SimpleNamespace

from src.api.routes import watcher_routes as routes
from src.scanners.extractor_registry import ExtractionResult


class _DummyUpdater:
    collection_name = "vetka_elisya"

    def _get_embedding(self, text):
        return [0.0] * 768


class _DummyWatcher:
    def add_browser_directory(self, root_name, files_count):
        return None


def _fake_request():
    app = SimpleNamespace(
        state=SimpleNamespace(
            qdrant_manager=SimpleNamespace(client=object()),
            socketio=None,
        )
    )
    return SimpleNamespace(app=app)


def test_add_from_browser_metadata_only_sets_degraded(monkeypatch):
    captured = {"metadata": None}

    class _TW:
        def write_file(self, file_path, content, embedding, metadata=None):
            captured["metadata"] = metadata or {}
            return {"qdrant": True, "weaviate": False, "changelog": True, "vetka_tree": True}

        def write_media_chunks(self, file_path, media_chunks, modality):
            return 0

    monkeypatch.setattr(routes, "get_qdrant_updater", lambda qdrant_client: _DummyUpdater())
    monkeypatch.setattr(routes, "get_watcher", lambda socketio=None, qdrant_client=None: _DummyWatcher())
    monkeypatch.setattr(
        "src.orchestration.triple_write_manager.get_triple_write_manager",
        lambda: _TW(),
    )

    req = routes.AddFromBrowserRequest(
        rootName="Footage",
        mode="metadata_only",
        files=[
            routes.BrowserFileInfo(
                name="A001.mp4",
                relativePath="Day1/A001.mp4",
                size=123456,
                type="video/mp4",
                lastModified=1700000000000,
                contentBase64=None,
            )
        ],
    )
    result = asyncio.run(routes.add_from_browser(req, _fake_request()))
    assert result["success"] is True
    assert result["indexed_count"] == 1
    assert captured["metadata"]["degraded_mode"] is True
    assert captured["metadata"]["extraction_route"] == "browser_metadata_only"
    assert captured["metadata"]["media_chunks_schema"] == "media_chunks_v1"


def test_add_from_browser_content_small_uses_extractor(monkeypatch):
    captured = {"metadata": None}

    class _TW:
        def write_file(self, file_path, content, embedding, metadata=None):
            captured["metadata"] = metadata or {}
            return {"qdrant": True, "weaviate": False, "changelog": True, "vetka_tree": True}

        def write_media_chunks(self, file_path, media_chunks, modality):
            return 0

    class _Registry:
        def extract_file(self, path, rel_path=None, max_text_chars=4000):
            return ExtractionResult(
                text="decoded text",
                media_chunks=[],
                metadata={"extraction_route": "text"},
                extractor_id="text_reader",
            )

    monkeypatch.setattr(routes, "get_qdrant_updater", lambda qdrant_client: _DummyUpdater())
    monkeypatch.setattr(routes, "get_watcher", lambda socketio=None, qdrant_client=None: _DummyWatcher())
    monkeypatch.setattr(routes, "get_media_extractor_registry", lambda: _Registry())
    monkeypatch.setattr(
        "src.orchestration.triple_write_manager.get_triple_write_manager",
        lambda: _TW(),
    )

    payload = base64.b64encode(b"hello browser text").decode("ascii")
    req = routes.AddFromBrowserRequest(
        rootName="Footage",
        mode="content_small",
        files=[
            routes.BrowserFileInfo(
                name="note.txt",
                relativePath="Docs/note.txt",
                size=17,
                type="text/plain",
                lastModified=1700000000000,
                contentBase64=payload,
            )
        ],
    )
    result = asyncio.run(routes.add_from_browser(req, _fake_request()))
    assert result["success"] is True
    assert result["indexed_count"] == 1
    assert captured["metadata"]["degraded_mode"] is False
    assert captured["metadata"]["extractor_id"].startswith("browser_inline:")
    assert captured["metadata"]["extraction_route"] == "text"
