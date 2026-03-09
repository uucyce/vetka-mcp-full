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


def _init_payload(source_path: str, project_name: str = "") -> dict:
    payload = {
        "source_type": "local",
        "source_path": source_path,
        "quota_gb": 5,
    }
    if project_name:
        payload["project_name"] = project_name
    return payload


def test_projects_registry_list_and_activate(client: TestClient, tmp_path: Path) -> None:
    p1 = tmp_path / "project_one"
    p2 = tmp_path / "project_two"
    p1.mkdir(parents=True, exist_ok=True)
    p2.mkdir(parents=True, exist_ok=True)
    (p1 / "a.py").write_text("print('a')\n", encoding="utf-8")
    (p2 / "b.py").write_text("print('b')\n", encoding="utf-8")

    r1 = client.post("/api/mcc/project/init", json=_init_payload(str(p1), project_name="Project One"))
    assert r1.status_code == 200
    assert r1.json()["success"] is True
    id1 = r1.json()["project_id"]

    r2 = client.post("/api/mcc/project/init", json=_init_payload(str(p2), project_name="Project Two"))
    assert r2.status_code == 200
    assert r2.json()["success"] is True
    id2 = r2.json()["project_id"]
    assert id1 != id2

    listed = client.get("/api/mcc/projects/list")
    assert listed.status_code == 200
    data = listed.json()
    assert data["success"] is True
    assert data["count"] == 2
    assert data["active_project_id"] == id2
    names_by_id = {str(p.get("project_id")): str(p.get("display_name")) for p in data.get("projects", [])}
    assert names_by_id[id1] == "Project One"
    assert names_by_id[id2] == "Project Two"

    act = client.post("/api/mcc/projects/activate", json={"project_id": id1})
    assert act.status_code == 200
    assert act.json()["success"] is True
    assert act.json()["active_project_id"] == id1

    init = client.get("/api/mcc/init")
    assert init.status_code == 200
    init_payload = init.json()
    assert init_payload["has_project"] is True
    assert init_payload["active_project_id"] == id1
    assert init_payload["project_config"]["project_id"] == id1


def test_init_accepts_project_id_override(client: TestClient, tmp_path: Path) -> None:
    pa = tmp_path / "project_a"
    pb = tmp_path / "project_b"
    pa.mkdir(parents=True, exist_ok=True)
    pb.mkdir(parents=True, exist_ok=True)
    (pa / "x.py").write_text("print('x')\n", encoding="utf-8")
    (pb / "y.py").write_text("print('y')\n", encoding="utf-8")

    id_a = client.post("/api/mcc/project/init", json=_init_payload(str(pa))).json()["project_id"]
    id_b = client.post("/api/mcc/project/init", json=_init_payload(str(pb))).json()["project_id"]

    # Force active context during init call.
    init = client.get(f"/api/mcc/init?project_id={id_a}")
    assert init.status_code == 200
    payload = init.json()
    assert payload["has_project"] is True
    assert payload["active_project_id"] == id_a
    assert payload["project_config"]["project_id"] == id_a

    listed = client.get("/api/mcc/projects/list").json()
    assert listed["active_project_id"] == id_a
    ids = {p["project_id"] for p in listed["projects"]}
    assert id_a in ids
    assert id_b in ids
