from __future__ import annotations

import os
import sys
import importlib.util
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
    monkeypatch.setattr(reg_module, "PROJECTS_DIR", os.path.join(tmp_path, "mcc_projects"))

    module_path = ROOT / "src" / "api" / "routes" / "mcc_routes.py"
    spec = importlib.util.spec_from_file_location("test_mcc_routes_module", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    router = module.router

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
    assert isinstance(data.get("updated_at"), str)
    names_by_id = {str(p.get("project_id")): str(p.get("display_name")) for p in data.get("projects", [])}
    assert names_by_id[id1] == "Project One"
    assert names_by_id[id2] == "Project Two"
    rows_by_id = {str(p.get("project_id")): p for p in data.get("projects", [])}
    assert rows_by_id[id1]["workspace_path"].endswith(id1)
    assert rows_by_id[id1]["context_scope_path"].endswith(id1)

    act = client.post("/api/mcc/projects/activate", json={"project_id": id1})
    assert act.status_code == 200
    assert act.json()["success"] is True
    assert act.json()["active_project_id"] == id1

    init = client.get("/api/mcc/init")
    assert init.status_code == 200
    init_payload = init.json()
    assert init_payload["has_project"] is True
    assert init_payload["active_project_id"] == id1
    assert isinstance(init_payload.get("updated_at"), str)
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

    # Force project context for this window without mutating global registry state.
    init = client.get(f"/api/mcc/init?project_id={id_a}")
    assert init.status_code == 200
    payload = init.json()
    assert payload["has_project"] is True
    assert payload["active_project_id"] == id_a
    assert payload["project_config"]["project_id"] == id_a

    listed = client.get("/api/mcc/projects/list").json()
    assert listed["active_project_id"] == id_b
    ids = {p["project_id"] for p in listed["projects"]}
    assert id_a in ids
    assert id_b in ids


def test_window_session_state_isolated_per_window(client: TestClient, tmp_path: Path) -> None:
    source = tmp_path / "isolated_state_proj"
    source.mkdir(parents=True, exist_ok=True)
    (source / "main.py").write_text("print('ok')\n", encoding="utf-8")

    project_id = client.post("/api/mcc/project/init", json=_init_payload(str(source))).json()["project_id"]

    save = client.post(
        "/api/mcc/state",
        json={
            "project_id": project_id,
            "window_session_id": "window_a",
            "level": "workflow",
            "roadmap_node_id": "core",
            "task_id": "tb_123",
            "history": ["roadmap", "tasks"],
        },
    )
    assert save.status_code == 200

    window_a = client.get(f"/api/mcc/state?project_id={project_id}&window_session_id=window_a")
    assert window_a.status_code == 200
    assert window_a.json()["level"] == "workflow"
    assert window_a.json()["task_id"] == "tb_123"

    window_b = client.get(f"/api/mcc/state?project_id={project_id}&window_session_id=window_b")
    assert window_b.status_code == 200
    assert window_b.json()["level"] == "roadmap"
    assert window_b.json()["task_id"] == ""


def test_project_scoped_roadmap_endpoint_returns_requested_project_graph(
    client: TestClient,
    tmp_path: Path,
) -> None:
    from src.services.roadmap_generator import RoadmapDAG, roadmap_path_for_project

    project_a = tmp_path / "project_a"
    project_b = tmp_path / "project_b"
    project_a.mkdir(parents=True, exist_ok=True)
    project_b.mkdir(parents=True, exist_ok=True)
    (project_a / "a.py").write_text("print('a')\n", encoding="utf-8")
    (project_b / "b.py").write_text("print('b')\n", encoding="utf-8")

    id_a = client.post("/api/mcc/project/init", json=_init_payload(str(project_a), project_name="Alpha")).json()["project_id"]
    id_b = client.post("/api/mcc/project/init", json=_init_payload(str(project_b), project_name="Beta")).json()["project_id"]

    dag_a = RoadmapDAG(project_id=id_a, nodes=[{"id": "alpha_core", "label": "Alpha Core"}], edges=[])
    dag_b = RoadmapDAG(project_id=id_b, nodes=[{"id": "beta_core", "label": "Beta Core"}], edges=[])
    assert dag_a.save(path=roadmap_path_for_project(id_a))
    assert dag_b.save(path=roadmap_path_for_project(id_b))

    res_a = client.get(f"/api/mcc/roadmap?project_id={id_a}")
    res_b = client.get(f"/api/mcc/roadmap?project_id={id_b}")

    assert res_a.status_code == 200
    assert res_b.status_code == 200
    assert [node["id"] for node in res_a.json()["nodes"]] == ["alpha_core"]
    assert [node["id"] for node in res_b.json()["nodes"]] == ["beta_core"]


def test_project_init_supports_oauth_agent_mode_without_playground_copy(
    client: TestClient,
    tmp_path: Path,
) -> None:
    source = tmp_path / "oauth_source"
    source.mkdir(parents=True, exist_ok=True)
    (source / "agent.py").write_text("print('oauth')\n", encoding="utf-8")

    created = client.post(
        "/api/mcc/project/init",
        json={
            "source_type": "local",
            "source_path": str(source),
            "execution_mode": "oauth_agent",
            "quota_gb": 5,
        },
    )
    assert created.status_code == 200
    data = created.json()
    assert data["success"] is True
    assert data["execution_mode"] == "oauth_agent"
    assert data["sandbox_path"] == ""

    init = client.get(f"/api/mcc/init?project_id={data['project_id']}")
    assert init.status_code == 200
    payload = init.json()
    assert payload["project_config"]["execution_mode"] == "oauth_agent"

    listed = client.get("/api/mcc/projects/list")
    assert listed.status_code == 200
    rows = listed.json().get("projects", [])
    row = next((p for p in rows if str(p.get("project_id")) == str(data["project_id"])), None)
    assert row is not None
    assert row.get("execution_mode") == "oauth_agent"
    assert row.get("workspace_path") == str(source)
    assert row.get("context_scope_path") == str(source)
    assert row.get("project_kind") == "user"


def test_registry_bootstrap_rehydrates_projects_from_snapshot_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    monkeypatch.setattr(reg_module, "PROJECTS_DIR", os.path.join(tmp_path, "mcc_projects"))

    project_root = tmp_path / "oauth_source"
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "main.py").write_text("print('ok')\n", encoding="utf-8")

    cfg = pc_module.ProjectConfig.create_new(
        "local",
        str(project_root),
        execution_mode="oauth_agent",
        project_name="OAuth Snapshot",
    )
    snapshot_path = Path(reg_module.PROJECTS_DIR) / cfg.project_id / "project_config.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    assert cfg.save(path=str(snapshot_path))

    listing = reg_module.list_projects()
    assert listing["count"] == 1
    row = listing["projects"][0]
    assert row["project_id"] == cfg.project_id
    assert row["display_name"] == "OAuth Snapshot"
    assert row["workspace_path"] == str(project_root)
    assert row["context_scope_path"] == str(project_root)


def test_fixture_projects_are_hidden_from_default_project_tabs(client: TestClient, tmp_path: Path) -> None:
    source = tmp_path / "fixture_repo"
    source.mkdir(parents=True, exist_ok=True)
    (source / "fixture.py").write_text("print('fixture')\n", encoding="utf-8")

    created = client.post(
        "/api/mcc/project/init",
        json={
            "source_type": "local",
            "source_path": str(source),
            "project_kind": "fixture",
            "quota_gb": 1,
            "project_name": "Playwright Fixture",
        },
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["success"] is True
    assert payload["project_kind"] == "fixture"

    visible = client.get("/api/mcc/projects/list")
    assert visible.status_code == 200
    visible_data = visible.json()
    assert visible_data["count"] == 0
    assert visible_data["hidden_count"] == 1

    hidden = client.get("/api/mcc/projects/list?include_hidden=1")
    assert hidden.status_code == 200
    hidden_data = hidden.json()
    assert hidden_data["count"] == 1
    row = hidden_data["projects"][0]
    assert row["project_kind"] == "fixture"
    assert row["tab_visibility"] == "hidden"

    init = client.get(f"/api/mcc/init?project_id={payload['project_id']}")
    assert init.status_code == 200
    init_payload = init.json()
    assert init_payload["active_project_id"] == payload["project_id"]
    assert init_payload["hidden_count"] == 0
    assert any(str(item.get("project_id")) == str(payload["project_id"]) for item in init_payload["projects"])
