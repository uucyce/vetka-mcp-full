"""
MARKER_189.7: Tests for MCC TaskBoard ↔ Project Integration (Phase 189).

Covers:
- /api/taskboard/projects endpoint (189.2A)
- project_id in _UPDATE_FIELDS — PATCH support (189.4A)
- project_unknown hint on task create (189.5A)
- _check_project_known logic (189.5A)
"""
from __future__ import annotations

import os
import sys
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Set up isolated taskboard + registry for testing."""
    # Isolate task board storage
    tb_file = tmp_path / "task_board.json"
    tb_file.write_text("[]", encoding="utf-8")
    import src.orchestration.task_board as tb_module
    monkeypatch.setattr(tb_module, "TASK_BOARD_FILE", tb_file)
    monkeypatch.setattr(tb_module, "TASK_BOARD_DB", tmp_path / "task_board.db")
    monkeypatch.setattr(tb_module, "PROJECT_ROOT", tmp_path)

    # Isolate project registry
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

    # Reset singleton task board
    tb_module._board_instance = None

    from src.api.routes.taskboard_routes import router
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _seed_registry(tmp_path: Path, projects: list[dict]) -> None:
    """Write a test registry with given projects."""
    registry = {
        "schema_version": 1,
        "active_project_id": projects[0]["project_id"] if projects else "",
        "projects": projects,
    }
    reg_path = tmp_path / "mcc_projects_registry.json"
    reg_path.write_text(json.dumps(registry), encoding="utf-8")


# ────────────────────────────────────────────────────────────────
# 189.2A: /api/taskboard/projects endpoint
# ────────────────────────────────────────────────────────────────


def test_projects_endpoint_empty(client: TestClient) -> None:
    """Projects endpoint returns empty list when no registry exists."""
    res = client.get("/api/taskboard/projects")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert isinstance(data["projects"], list)


def test_projects_endpoint_with_registry(client: TestClient, tmp_path: Path) -> None:
    """Projects endpoint returns registered projects."""
    _seed_registry(tmp_path, [
        {"project_id": "proj_alpha", "display_name": "Alpha", "project_kind": "user", "tab_visibility": "visible"},
        {"project_id": "proj_beta", "display_name": "Beta", "project_kind": "user", "tab_visibility": "visible"},
    ])
    res = client.get("/api/taskboard/projects")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["active_project_id"] == "proj_alpha"
    ids = [p["project_id"] for p in data["projects"]]
    assert "proj_alpha" in ids
    assert "proj_beta" in ids


# ────────────────────────────────────────────────────────────────
# 189.4A: PATCH project_id on existing task
# ────────────────────────────────────────────────────────────────


def test_patch_project_id(client: TestClient) -> None:
    """PATCH /api/taskboard/{id} can update project_id."""
    # Create task without project_id
    create_res = client.post("/api/taskboard/create", json={"title": "Test task"})
    assert create_res.status_code == 200
    task_id = create_res.json()["task"]["id"]

    # PATCH with project_id
    patch_res = client.patch(f"/api/taskboard/{task_id}", json={"project_id": "my_project"})
    assert patch_res.status_code == 200
    assert patch_res.json()["task"]["project_id"] == "my_project"


def test_patch_project_lane(client: TestClient) -> None:
    """PATCH /api/taskboard/{id} can update project_lane."""
    create_res = client.post("/api/taskboard/create", json={"title": "Lane task"})
    assert create_res.status_code == 200
    task_id = create_res.json()["task"]["id"]

    patch_res = client.patch(f"/api/taskboard/{task_id}", json={"project_lane": "MCC"})
    assert patch_res.status_code == 200
    assert patch_res.json()["task"]["project_lane"] == "MCC"


# ────────────────────────────────────────────────────────────────
# 189.5A: project_unknown hint on task create
# ────────────────────────────────────────────────────────────────


def test_create_task_known_project_no_hint(client: TestClient, tmp_path: Path) -> None:
    """Creating a task with a known project_id should NOT return project_unknown."""
    _seed_registry(tmp_path, [
        {"project_id": "known_proj", "display_name": "Known", "project_kind": "user", "tab_visibility": "visible"},
    ])
    res = client.post("/api/taskboard/create", json={
        "title": "Task in known project",
        "project_id": "known_proj",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "project_unknown" not in data


def test_create_task_unknown_project_returns_hint(client: TestClient, tmp_path: Path) -> None:
    """Creating a task with an unknown project_id should return project_unknown hint."""
    _seed_registry(tmp_path, [
        {"project_id": "existing_proj", "display_name": "Existing", "project_kind": "user", "tab_visibility": "visible"},
    ])
    res = client.post("/api/taskboard/create", json={
        "title": "Task in unknown project",
        "project_id": "nonexistent_proj",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["project_unknown"] is True
    assert data["suggested_action"] == "create_project"
    assert data["suggested_project_id"] == "nonexistent_proj"


def test_create_task_no_project_no_hint(client: TestClient) -> None:
    """Creating a task without project_id should NOT return project_unknown."""
    res = client.post("/api/taskboard/create", json={"title": "No project task"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "project_unknown" not in data


# ────────────────────────────────────────────────────────────────
# 189.1: project_id stored in task
# ────────────────────────────────────────────────────────────────


def test_create_task_with_project_id_stored(client: TestClient) -> None:
    """project_id passed at creation is stored and returned in GET."""
    res = client.post("/api/taskboard/create", json={
        "title": "Stored project task",
        "project_id": "vetka",
        "project_lane": "MCC",
    })
    assert res.status_code == 200
    task_id = res.json()["task"]["id"]

    get_res = client.get(f"/api/taskboard/{task_id}")
    assert get_res.status_code == 200
    task = get_res.json()["task"]
    assert task["project_id"] == "vetka"
    assert task["project_lane"] == "MCC"
