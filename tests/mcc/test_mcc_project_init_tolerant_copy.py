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


def test_project_init_tolerates_missing_file_during_copy(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    src_root = tmp_path / "src_project"
    sandbox_root = tmp_path / "sandbox_project"
    src_root.mkdir(parents=True, exist_ok=True)
    good = src_root / "good.txt"
    bad = src_root / "gone.txt"
    good.write_text("ok\n", encoding="utf-8")
    bad.write_text("temp\n", encoding="utf-8")

    import src.api.routes.mcc_routes as routes

    orig_copy2 = routes.shutil.copy2

    def flaky_copy2(src: str, dst: str):
        if src.endswith("gone.txt"):
            raise FileNotFoundError(src)
        return orig_copy2(src, dst)

    monkeypatch.setattr(routes.shutil, "copy2", flaky_copy2)

    resp = client.post(
        "/api/mcc/project/init",
        json={
            "source_type": "local",
            "source_path": str(src_root),
            "sandbox_path": str(sandbox_root),
            "quota_gb": 5,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert os.path.exists(sandbox_root / "good.txt")
