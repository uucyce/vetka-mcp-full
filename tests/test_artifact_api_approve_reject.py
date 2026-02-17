# MARKER_136.ARTIFACT_APPROVE_REJECT_TEST
import asyncio
import json
from types import SimpleNamespace

import src.services.artifact_scanner as scanner
from src.api.handlers.artifact_routes import (
    list_artifacts_for_panel,
    approve_artifact_for_panel,
    reject_artifact_for_panel,
)
from src.api.routes.artifact_routes import (
    ArtifactDecisionRequest,
    SaveSearchResultRequest,
    approve_artifact_endpoint,
    reject_artifact_endpoint,
    save_search_result_endpoint,
)


def _patch_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(scanner, "ARTIFACTS_DIR", tmp_path / "data" / "artifacts")
    monkeypatch.setattr(scanner, "VETKA_OUT_DIR", tmp_path / "src" / "vetka_out")
    monkeypatch.setattr(scanner, "STAGING_FILE", tmp_path / "data" / "staging.json")


def test_list_artifacts_includes_vetka_out(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    scanner.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    scanner.VETKA_OUT_DIR.mkdir(parents=True, exist_ok=True)

    (scanner.ARTIFACTS_DIR / "a.py").write_text("print('a')", encoding="utf-8")
    (scanner.VETKA_OUT_DIR / "b.md").write_text("# b", encoding="utf-8")

    payload = list_artifacts_for_panel()
    assert payload["success"] is True
    names = {a["name"] for a in payload["artifacts"]}
    assert names == {"a.py", "b.md"}


def test_approve_and_reject_update_staging(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    scanner.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    scanner.STAGING_FILE.parent.mkdir(parents=True, exist_ok=True)

    filename = "feature.py"
    (scanner.ARTIFACTS_DIR / filename).write_text("print('ok')", encoding="utf-8")

    artifact_id = scanner._generate_artifact_id(filename)

    approved = approve_artifact_for_panel(artifact_id, "looks good")
    assert approved["success"] is True
    assert approved["status"] == "approved"

    data = json.loads(scanner.STAGING_FILE.read_text(encoding="utf-8"))
    assert data["artifacts"][approved["artifact_id"]]["status"] == "approved"

    rejected = reject_artifact_for_panel(artifact_id, "needs tests")
    assert rejected["success"] is True
    assert rejected["status"] == "rejected"

    data = json.loads(scanner.STAGING_FILE.read_text(encoding="utf-8"))
    assert data["artifacts"][rejected["artifact_id"]]["feedback"] == "needs tests"


def test_artifact_route_endpoints(monkeypatch):
    monkeypatch.setattr(
        "src.api.routes.artifact_routes.approve_artifact_for_panel",
        lambda artifact_id, reason: {"success": True, "artifact_id": artifact_id, "reason": reason, "status": "approved"},
    )
    monkeypatch.setattr(
        "src.api.routes.artifact_routes.reject_artifact_for_panel",
        lambda artifact_id, reason: {"success": True, "artifact_id": artifact_id, "reason": reason, "status": "rejected"},
    )

    ok = asyncio.run(approve_artifact_endpoint("artifact_abc", ArtifactDecisionRequest(reason="ok")))
    bad = asyncio.run(reject_artifact_endpoint("artifact_abc", ArtifactDecisionRequest(reason="bad")))

    assert ok["status"] == "approved"
    assert bad["status"] == "rejected"


def test_save_search_result_endpoint_indexes_when_qdrant_available(monkeypatch, tmp_path):
    saved = tmp_path / "saved.md"
    saved.write_text("# ok", encoding="utf-8")

    async def _save_search_result_artifact_mock(**kwargs):
        return {
            "success": True,
            "file_path": str(saved),
            "title": "Saved",
        }

    monkeypatch.setattr(
        "src.api.routes.artifact_routes.save_search_result_artifact",
        _save_search_result_artifact_mock,
    )

    class _Updater:
        def update_file(self, path):
            return True

    monkeypatch.setattr(
        "src.api.routes.artifact_routes.get_qdrant_updater",
        lambda **kwargs: _Updater(),
    )

    req = SaveSearchResultRequest(source="web", url="https://example.com")
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=SimpleNamespace(client=object()))))
    result = asyncio.run(save_search_result_endpoint(req, request))
    assert result["success"] is True
    assert result["indexed"] is True


def test_save_search_result_endpoint_marks_index_error_without_qdrant(monkeypatch, tmp_path):
    saved = tmp_path / "saved.md"
    saved.write_text("# ok", encoding="utf-8")

    async def _save_search_result_artifact_mock(**kwargs):
        return {
            "success": True,
            "file_path": str(saved),
            "title": "Saved",
        }

    monkeypatch.setattr(
        "src.api.routes.artifact_routes.save_search_result_artifact",
        _save_search_result_artifact_mock,
    )

    req = SaveSearchResultRequest(source="file", path="README.md")
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=None)))
    result = asyncio.run(save_search_result_endpoint(req, request))
    assert result["success"] is True
    assert result["indexed"] is False
    assert result["index_error"] == "qdrant_client_not_available"


def test_save_search_result_endpoint_returns_policy_block(monkeypatch, tmp_path):
    blocked = tmp_path / "blocked.exe"
    blocked.write_bytes(b"binary")

    async def _save_search_result_artifact_mock(**kwargs):
        return {
            "success": True,
            "file_path": str(blocked),
            "title": "Saved",
        }

    monkeypatch.setattr(
        "src.api.routes.artifact_routes.save_search_result_artifact",
        _save_search_result_artifact_mock,
    )

    req = SaveSearchResultRequest(source="file", path="README.md")
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(qdrant_manager=SimpleNamespace(client=object()))))
    result = asyncio.run(save_search_result_endpoint(req, request))
    assert result["success"] is True
    assert result["indexed"] is False
    assert result["index_error"] == "ingest_policy_blocked"
    assert result["index_policy"]["code"] in ("DENY_EXTENSION", "UNKNOWN_EXTENSION", "FILE_TOO_LARGE")
