from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class _FakeBoard:
    def __init__(self, task: dict | None = None) -> None:
        self.task = dict(task or {})
        self.updates: list[tuple[str, dict]] = []

    def get_task(self, task_id: str):
        if self.task.get("id") != task_id:
            return None
        return dict(self.task)

    def update_task(self, task_id: str, **updates):
        if self.task.get("id") != task_id:
            return False
        self.task.update(updates)
        self.updates.append((task_id, dict(updates)))
        return True


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    import src.api.routes.mcc_routes as routes
    from src.api.routes.mcc_routes import router

    board = _FakeBoard(
        {
            "id": "tb_1",
            "title": "Fix heartbeat tests",
            "description": "Stabilize daemon tests and runtime workflow",
            "phase_type": "fix",
            "complexity": "medium",
            "preset": "dragon_silver",
            "team_profile": "dragon_silver",
        }
    )

    monkeypatch.setattr(routes, "_get_task_board_instance", lambda: board)

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    client._fake_board = board  # type: ignore[attr-defined]
    return client


def test_task_workflow_binding_persists_explicit_fields_and_syncs_legacy_workflow_id(client: TestClient) -> None:
    """
    MARKER_167.STATS_WORKFLOW.TASK_BINDING.V1
    """
    resp = client.put(
        "/api/mcc/tasks/tb_1/workflow-binding",
        json={
            "workflow_bank": "core",
            "workflow_id": "ralph_loop",
            "workflow_family": "ralph_loop",
            "team_profile": "ralph_solo",
            "selection_origin": "user-selected",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["binding"]["workflow_id"] == "ralph_loop"
    assert data["binding"]["workflow_bank"] == "core"
    assert data["binding"]["workflow_family"] == "ralph_loop"
    assert data["binding"]["team_profile"] == "ralph_solo"
    assert data["binding"]["selection_origin"] == "user-selected"

    board = client._fake_board  # type: ignore[attr-defined]
    assert board.task["workflow_id"] == "ralph_loop"
    assert board.task["workflow_bank"] == "core"
    assert board.task["workflow_family"] == "ralph_loop"
    assert board.task["workflow_selection_origin"] == "user-selected"


def test_task_workflow_restore_prefers_explicit_binding_over_legacy_and_heuristic(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    MARKER_167.STATS_WORKFLOW.RESTORE_ORDER.V1
    """
    board = client._fake_board  # type: ignore[attr-defined]
    board.task.update(
        {
            "workflow_id": "quick_fix",
            "workflow_bank": "core",
            "workflow_family": "ralph_loop",
            "workflow_selection_origin": "user-selected",
            "team_profile": "ralph_solo",
        }
    )

    import src.api.routes.mcc_routes as routes

    monkeypatch.setattr(
        routes,
        "_select_heuristic_workflow_binding",
        lambda task: {
            "workflow_bank": "core",
            "workflow_id": "bmad_default",
            "workflow_family": "bmad_default",
            "team_profile": "dragon_silver",
            "selection_origin": "heuristic",
        },
    )

    resp = client.get("/api/mcc/tasks/tb_1/workflow-binding")
    assert resp.status_code == 200
    binding = resp.json()["binding"]
    assert binding["workflow_id"] == "quick_fix"
    assert binding["workflow_family"] == "ralph_loop"
    assert binding["selection_origin"] == "user-selected"
    assert binding["team_profile"] == "ralph_solo"


def test_task_workflow_restore_uses_heuristic_when_no_binding_exists(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    board = client._fake_board  # type: ignore[attr-defined]
    board.task.pop("workflow_id", None)
    board.task.pop("workflow_bank", None)
    board.task.pop("workflow_family", None)
    board.task.pop("workflow_selection_origin", None)

    import src.api.routes.mcc_routes as routes

    monkeypatch.setattr(
        routes,
        "_select_heuristic_workflow_binding",
        lambda task: {
            "workflow_bank": "core",
            "workflow_id": "g3_critic_coder",
            "workflow_family": "g3_critic_coder",
            "team_profile": "dragon_silver",
            "selection_origin": "heuristic",
        },
    )

    resp = client.get("/api/mcc/tasks/tb_1/workflow-binding")
    assert resp.status_code == 200
    binding = resp.json()["binding"]
    assert binding["workflow_id"] == "g3_critic_coder"
    assert binding["selection_origin"] == "heuristic"
