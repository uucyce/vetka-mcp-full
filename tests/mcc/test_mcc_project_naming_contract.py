from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    import src.services.project_config as pc_module

    monkeypatch.setattr(pc_module, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(pc_module, "CONFIG_PATH", os.path.join(tmp_path, "project_config.json"))
    monkeypatch.setattr(pc_module, "SESSION_STATE_PATH", os.path.join(tmp_path, "session_state.json"))

    import src.services.mcc_project_registry as reg_module

    monkeypatch.setattr(reg_module, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(reg_module, "CONFIG_PATH", os.path.join(tmp_path, "project_config.json"))
    monkeypatch.setattr(reg_module, "SESSION_STATE_PATH", os.path.join(tmp_path, "session_state.json"))
    monkeypatch.setattr(reg_module, "REGISTRY_PATH", os.path.join(tmp_path, "mcc_projects_registry.json"))
    monkeypatch.setattr(reg_module, "SESSIONS_DIR", os.path.join(tmp_path, "mcc_sessions"))

    from src.api.routes.mcc_routes import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_project_name_propagates_to_response_init_and_registry(client: TestClient, tmp_path: Path) -> None:
    source = tmp_path / "src_named"
    source.mkdir(parents=True, exist_ok=True)
    (source / "main.py").write_text("print('ok')\n", encoding="utf-8")

    sandbox = tmp_path / "playgrounds" / "my_named_workspace"
    created = client.post(
        "/api/mcc/project/init",
        json={
            "source_type": "local",
            "source_path": str(source),
            "sandbox_path": str(sandbox),
            "project_name": "Moon Garden",
            "quota_gb": 5,
        },
    )
    assert created.status_code == 200
    data = created.json()
    assert data["success"] is True
    assert data["project_name"] == "Moon Garden"
    project_id = str(data["project_id"])

    init = client.get("/api/mcc/init")
    assert init.status_code == 200
    init_payload = init.json()
    assert init_payload["has_project"] is True
    assert init_payload["project_config"]["project_id"] == project_id
    assert init_payload["project_config"]["display_name"] == "Moon Garden"

    listed = client.get("/api/mcc/projects/list")
    assert listed.status_code == 200
    rows = listed.json().get("projects", [])
    row = next((p for p in rows if str(p.get("project_id")) == project_id), None)
    assert row is not None
    assert row.get("display_name") == "Moon Garden"


def test_project_name_falls_back_to_workspace_basename_when_omitted(client: TestClient, tmp_path: Path) -> None:
    source = tmp_path / "src_unnamed"
    source.mkdir(parents=True, exist_ok=True)
    (source / "a.txt").write_text("x\n", encoding="utf-8")

    sandbox = tmp_path / "playgrounds" / "name_project"
    created = client.post(
        "/api/mcc/project/init",
        json={
            "source_type": "local",
            "source_path": str(source),
            "sandbox_path": str(sandbox),
            "quota_gb": 5,
        },
    )
    assert created.status_code == 200
    data = created.json()
    assert data["success"] is True
    assert data["project_name"] == "name_project"
