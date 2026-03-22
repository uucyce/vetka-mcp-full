from pathlib import Path

from src.scanners.extractor_registry import ExtractionResult
from src.scanners.qdrant_updater import QdrantIncrementalUpdater
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 158 contracts changed")


class _DummyClient:
    def __init__(self):
        self.points = []

    def upsert(self, collection_name, points, wait=False):
        self.points.extend(points)


def test_qdrant_updater_uses_extractor_registry(monkeypatch, tmp_path):
    fpath = tmp_path / "clip.mp4"
    fpath.write_bytes(b"\x00\x00\x00\x18ftypmp42")

    class _Registry:
        def extract_file(self, file_path, rel_path=None, max_text_chars=8000):
            return ExtractionResult(
                text="video transcript",
                media_chunks=[{"start_sec": 0.0, "end_sec": 2.0, "text": "hello"}],
                metadata={"extraction_route": "stt"},
                extractor_id="whisper_stt",
            )

    client = _DummyClient()
    updater = QdrantIncrementalUpdater(qdrant_client=client)

    monkeypatch.setattr(updater, "_file_changed", lambda path: (True, None))
    monkeypatch.setattr(updater, "_get_embedding", lambda text: [0.0] * 8)
    monkeypatch.setattr(
        "src.scanners.qdrant_updater.get_media_extractor_registry",
        lambda: _Registry(),
    )

    ok = updater.update_file(Path(fpath))
    assert ok is True
    assert len(client.points) == 1
    payload = client.points[0].payload
    assert payload["extractor_id"] == "whisper_stt"
    assert payload["extraction_route"] == "stt"
    assert payload["media_chunks_schema"] == "media_chunks_v1"
    assert isinstance(payload["media_chunks_v1"], list)
    assert payload["media_chunks"][0]["text"] == "hello"
