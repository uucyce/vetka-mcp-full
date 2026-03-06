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


def test_project_init_rejects_sandbox_inside_source(client: TestClient, tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir(parents=True, exist_ok=True)
    (source / "main.py").write_text("print('x')\n", encoding="utf-8")
    sandbox = source / "playground_inside_source"

    resp = client.post(
        "/api/mcc/project/init",
        json={
            "source_type": "local",
            "source_path": str(source),
            "sandbox_path": str(sandbox),
            "quota_gb": 5,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert any("sandbox_path must be isolated from source_path" in str(e) for e in data.get("errors", []))

