from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    import src.services.project_config as pc_module
    import src.services.mcc_project_registry as reg_module

    monkeypatch.setattr(pc_module, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(pc_module, "CONFIG_PATH", os.path.join(tmp_path, "project_config.json"))
    monkeypatch.setattr(pc_module, "SESSION_STATE_PATH", os.path.join(tmp_path, "session_state.json"))

    monkeypatch.setattr(reg_module, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(reg_module, "CONFIG_PATH", os.path.join(tmp_path, "project_config.json"))
    monkeypatch.setattr(reg_module, "SESSION_STATE_PATH", os.path.join(tmp_path, "session_state.json"))
    monkeypatch.setattr(reg_module, "REGISTRY_PATH", os.path.join(tmp_path, "mcc_projects_registry.json"))
    monkeypatch.setattr(reg_module, "SESSIONS_DIR", os.path.join(tmp_path, "mcc_sessions"))

    from src.api.routes.mcc_routes import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_project_init_rejects_workspace_overlapping_existing_project(client: TestClient, tmp_path: Path) -> None:
    source_a = tmp_path / "source_a"
    source_a.mkdir(parents=True, exist_ok=True)
    (source_a / "a.py").write_text("print('a')\n", encoding="utf-8")
    sandbox_a = tmp_path / "workspace_a"

    first = client.post(
        "/api/mcc/project/init",
        json={
            "source_type": "local",
            "source_path": str(source_a),
            "sandbox_path": str(sandbox_a),
            "project_name": "Alpha",
            "quota_gb": 5,
        },
    )
    assert first.status_code == 200
    assert first.json()["success"] is True

    source_b = tmp_path / "source_b"
    source_b.mkdir(parents=True, exist_ok=True)
    (source_b / "b.py").write_text("print('b')\n", encoding="utf-8")
    nested_sandbox = sandbox_a / "nested_workspace"

    second = client.post(
        "/api/mcc/project/init",
        json={
            "source_type": "local",
            "source_path": str(source_b),
            "sandbox_path": str(nested_sandbox),
            "project_name": "Beta",
            "quota_gb": 5,
        },
    )
    assert second.status_code == 200
    payload = second.json()
    assert payload["success"] is False
    assert any("isolated from existing projects" in str(e) for e in payload.get("errors", []))

