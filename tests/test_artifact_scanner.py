# MARKER_136.TEST_ARTIFACT_SCANNER
import json

import src.services.artifact_scanner as scanner


def _patch_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(scanner, "ARTIFACTS_DIR", tmp_path / "data" / "artifacts")
    monkeypatch.setattr(scanner, "VETKA_OUT_DIR", tmp_path / "src" / "vetka_out")
    monkeypatch.setattr(scanner, "STAGING_FILE", tmp_path / "data" / "staging.json")
    class _DummyRegistry:
        def __init__(self):
            self.links = []

        def link(self, chat_id, message_id, artifact):
            self.links.append((chat_id, message_id, artifact))
            return True

    monkeypatch.setattr(scanner, "get_chat_artifact_registry", lambda: _DummyRegistry())


def test_scan_artifacts_returns_empty_if_dir_missing(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    artifacts = scanner.scan_artifacts()
    assert artifacts == []


def test_scan_artifacts_reads_files_and_staging_links(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    scanner.ARTIFACTS_DIR.mkdir(parents=True)
    scanner.STAGING_FILE.parent.mkdir(parents=True, exist_ok=True)

    (scanner.ARTIFACTS_DIR / "dev_patch.py").write_text("print('ok')", encoding="utf-8")
    (scanner.ARTIFACTS_DIR / "qa_report.md").write_text("# report", encoding="utf-8")
    (scanner.ARTIFACTS_DIR / ".hidden").write_text("ignore", encoding="utf-8")

    scanner.STAGING_FILE.write_text(
        json.dumps(
            {
                "artifacts": {
                    "a1": {
                        "filename": "dev_patch.py",
                        "source_chat_id": "chat123",
                        "source_message_id": "msg1",
                        "status": "done",
                        "is_favorite": True,
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    artifacts = scanner.scan_artifacts()
    names = {a["name"] for a in artifacts}
    assert names == {"dev_patch.py", "qa_report.md"}

    dev = next(a for a in artifacts if a["name"] == "dev_patch.py")
    assert dev["metadata"]["artifact_type"] == "code"
    assert dev["metadata"]["language"] == "python"
    assert dev["parent_id"] == "chat_chat123"
    assert dev["metadata"]["source_message_id"] == "msg1"
    assert dev["metadata"]["is_favorite"] is True
    assert dev["visual_hints"]["color"] == scanner.ARTIFACT_COLORS["code"]


def test_build_artifact_edges_connects_only_existing_parents():
    artifacts = [
        {"id": "artifact_1", "parent_id": "chat_a", "visual_hints": {"color": "#10b981"}},
        {"id": "artifact_2", "parent_id": "chat_missing", "visual_hints": {"color": "#3b82f6"}},
        {"id": "artifact_3", "parent_id": None, "visual_hints": {"color": "#3b82f6"}},
    ]
    chat_nodes = [{"id": "chat_a"}, {"id": "chat_b"}]

    edges = scanner.build_artifact_edges(artifacts, chat_nodes)
    assert len(edges) == 1
    assert edges[0]["from"] == "chat_a"
    assert edges[0]["to"] == "artifact_1"
    assert edges[0]["semantics"] == "artifact"


def test_update_artifact_positions_offsets_from_parent():
    artifacts = [
        {
            "id": "artifact_1",
            "parent_id": "chat_a",
            "visual_hints": {"layout_hint": {"expected_x": 0, "expected_y": 0, "expected_z": 0}},
        },
        {
            "id": "artifact_2",
            "parent_id": "chat_a",
            "visual_hints": {"layout_hint": {"expected_x": 0, "expected_y": 0, "expected_z": 0}},
        },
    ]
    chats = [
        {
            "id": "chat_a",
            "visual_hints": {"layout_hint": {"expected_x": 10, "expected_y": 20, "expected_z": 5}},
        }
    ]

    scanner.update_artifact_positions(artifacts, chats)

    first = artifacts[0]["visual_hints"]["layout_hint"]
    second = artifacts[1]["visual_hints"]["layout_hint"]
    assert first["expected_x"] == 13
    assert first["expected_y"] == 18
    assert first["expected_z"] == 5
    assert second["expected_x"] == 15
    assert second["expected_y"] == 18


def test_set_artifact_favorite_persists_flag(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    scanner.ARTIFACTS_DIR.mkdir(parents=True)
    scanner.STAGING_FILE.parent.mkdir(parents=True, exist_ok=True)

    (scanner.ARTIFACTS_DIR / "fav_note.md").write_text("hello", encoding="utf-8")
    artifact_id = scanner._generate_artifact_id("fav_note.md")

    result = scanner.set_artifact_favorite(artifact_id, True)
    assert result["success"] is True
    assert result["is_favorite"] is True

    data = json.loads(scanner.STAGING_FILE.read_text(encoding="utf-8"))
    key = result["artifact_id"]
    assert data["artifacts"][key]["is_favorite"] is True
