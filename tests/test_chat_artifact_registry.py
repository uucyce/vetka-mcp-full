import json
from pathlib import Path

from src.services.chat_artifact_registry import ChatArtifactRegistry


def test_registry_link_and_get(tmp_path):
    registry_file = tmp_path / "data" / "chat_artifacts.json"
    registry = ChatArtifactRegistry(registry_file=registry_file)

    changed = registry.link(
        chat_id="chat_1",
        message_id="msg_1",
        artifact={"artifact_id": "art_1", "file_path": "data/artifacts/a.md", "name": "a.md"},
    )
    assert changed is True

    links = registry.get_by_chat("chat_1")
    assert len(links) == 1
    assert links[0]["artifact_id"] == "art_1"
    assert links[0]["message_id"] == "msg_1"

    # Duplicate should be ignored
    changed_dup = registry.link(
        chat_id="chat_1",
        message_id="msg_1",
        artifact={"artifact_id": "art_1", "file_path": "data/artifacts/a.md", "name": "a.md"},
    )
    assert changed_dup is False
    assert len(registry.get_by_chat("chat_1")) == 1

    data = json.loads(Path(registry_file).read_text(encoding="utf-8"))
    assert "by_chat" in data
