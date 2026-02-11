# MARKER_136.ARTIFACT_APPROVE_REJECT_TEST
import asyncio
import json

import src.services.artifact_scanner as scanner
from src.api.handlers.artifact_routes import (
    list_artifacts_for_panel,
    approve_artifact_for_panel,
    reject_artifact_for_panel,
)
from src.api.routes.artifact_routes import (
    ArtifactDecisionRequest,
    approve_artifact_endpoint,
    reject_artifact_endpoint,
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
