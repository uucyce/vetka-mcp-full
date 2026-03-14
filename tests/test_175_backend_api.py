import asyncio
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def board(tmp_path, monkeypatch):
    import src.orchestration.task_board as task_board_module

    board = task_board_module.TaskBoard(board_file=tmp_path / "task_board.json")
    monkeypatch.setattr(task_board_module, "get_task_board", lambda: board)
    return board


@pytest.fixture
def client(board):
    from src.api.routes.chat_routes import router as chat_router
    from src.api.routes.mcc_routes import router as mcc_router
    from src.api.routes.taskboard_routes import router as taskboard_router

    app = FastAPI()
    app.include_router(mcc_router)
    app.include_router(chat_router)
    app.include_router(taskboard_router)
    return TestClient(app)


def _seed_task(board, **overrides):
    task_id = board.add_task(
        title=overrides.pop("title", "Phase 175 backend task"),
        description=overrides.pop("description", "Wire backend contracts"),
        priority=overrides.pop("priority", 3),
        phase_type=overrides.pop("phase_type", "build"),
        preset=overrides.pop("preset", "dragon_silver"),
        tags=overrides.pop("tags", ["phase175"]),
    )
    if overrides:
        assert board.update_task(task_id, **overrides)
    return task_id


def test_mcc_patch_task_updates_fields(client, board):
    task_id = _seed_task(board)

    response = client.patch(
        f"/api/mcc/tasks/{task_id}",
        json={
            "title": "Updated task",
            "description": "Updated description",
            "preset": "dragon_gold",
            "phase_type": "test",
            "priority": 1,
            "tags": ["phase175", "edited"],
            "project_lane": "mcc_test_lane",
            "architecture_docs": ["docs/177_MCC_local/MCC_CODE_CONTEXT_INSPECTION_ARCHITECTURE.md"],
            "closure_tests": ["pytest -q tests/test_175_backend_api.py"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["task"]["id"] == task_id
    assert data["task"]["title"] == "Updated task"
    assert data["task"]["preset"] == "dragon_gold"
    assert data["task"]["phase_type"] == "test"
    assert data["task"]["priority"] == 1
    assert data["task"]["tags"] == ["phase175", "edited"]
    assert data["task"]["project_lane"] == "mcc_test_lane"
    assert data["task"]["require_closure_proof"] is True
    assert data["task"]["closure_tests"] == ["pytest -q tests/test_175_backend_api.py"]


def test_mcc_patch_task_rejects_unknown_fields(client, board):
    task_id = _seed_task(board)

    response = client.patch(
        f"/api/mcc/tasks/{task_id}",
        json={"unknown_field": "nope"},
    )

    assert response.status_code == 400
    assert "No valid fields" in response.json()["detail"]


def test_mcc_patch_task_returns_404_for_missing_task(client):
    response = client.patch("/api/mcc/tasks/tb_missing", json={"preset": "dragon_gold"})

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_mcc_create_attached_task_derives_lane_docs_and_scope(client, monkeypatch):
    import src.services.roadmap_generator as roadmap_mod

    class _FakeRoadmap:
        project_id = "rm_171"
        nodes = [
            {
                "id": "cut_montage_engine",
                "label": "CUT Montage Engine",
                "layer": "feature",
                "docs": ["docs/171_ph_CUT_MONTAGE_ENGINE/PHASE_171_MONTAGE.md"],
                "file_patterns": ["src/montage/state.py"],
            }
        ]

        @classmethod
        def load(cls):
            return cls()

    monkeypatch.setattr(roadmap_mod, "RoadmapDAG", _FakeRoadmap)

    response = client.post(
        "/api/mcc/tasks/create-attached",
        json={
            "preset": "dragon_silver",
            "node_id": "node_montage_state",
            "node_label": "Montage State",
            "node_path": "src/montage/state.py",
            "node_graph_kind": "project_file",
            "roadmap_node_id": "cut_montage_engine",
        },
    )

    assert response.status_code == 200
    task = response.json()["task"]
    assert task["primary_node_id"] == "node_montage_state"
    assert task["project_lane"] == "cut_montage_engine"
    assert task["roadmap_node_id"] == "cut_montage_engine"
    assert task["roadmap_id"] == "rm_171"
    assert task["architecture_docs"] == ["docs/171_ph_CUT_MONTAGE_ENGINE/PHASE_171_MONTAGE.md"]
    assert "src/montage/state.py" in task["closure_files"]
    assert task["task_origin"] == "mcc_attached"


def test_mcc_attach_node_updates_task_binding(client, board, monkeypatch):
    import src.services.roadmap_generator as roadmap_mod

    task_id = _seed_task(board, title="Attach me")

    class _FakeRoadmap:
        project_id = "rm_171"
        nodes = [
            {
                "id": "cut_fixture",
                "label": "CUT Fixture",
                "layer": "test",
                "docs": ["docs/171_ph_CUT_FIXTURE/PHASE_171_FIXTURE.md"],
                "file_patterns": ["tests/test_fixture.py"],
            }
        ]

        @classmethod
        def load(cls):
            return cls()

    monkeypatch.setattr(roadmap_mod, "RoadmapDAG", _FakeRoadmap)

    response = client.post(
        f"/api/mcc/tasks/{task_id}/attach-node",
        json={
            "node_id": "node_fixture",
            "node_label": "Fixture Tests",
            "node_path": "tests/test_fixture.py",
            "node_graph_kind": "project_file",
            "roadmap_node_id": "cut_fixture",
        },
    )

    assert response.status_code == 200
    task = response.json()["task"]
    assert task["primary_node_id"] == "node_fixture"
    assert task["project_lane"] == "cut_fixture"
    assert task["roadmap_lane"] == "test"
    assert "docs/171_ph_CUT_FIXTURE/PHASE_171_FIXTURE.md" in task["architecture_docs"]
    assert "tests/test_fixture.py" in task["closure_files"]


def test_mcc_feedback_redo_sets_pending_and_feedback(client, board):
    task_id = _seed_task(board, status="done")

    response = client.post(
        f"/api/mcc/tasks/{task_id}/feedback",
        json={"feedback": "Please retry with better diagnostics", "action": "redo"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["task"]["status"] == "pending"
    assert data["task"]["result_status"] == 0.5
    assert data["task"]["feedback"] == "Please retry with better diagnostics"


def test_mcc_feedback_approve_sets_result_status_one(client, board):
    task_id = _seed_task(board, status="done")

    response = client.post(
        f"/api/mcc/tasks/{task_id}/feedback",
        json={"feedback": "Ship it", "action": "approve"},
    )

    assert response.status_code == 200
    assert response.json()["task"]["result_status"] == 1.0
    assert response.json()["task"]["status"] == "done"


def test_mcc_feedback_reject_sets_result_status_zero(client, board):
    task_id = _seed_task(board, status="done")

    response = client.post(
        f"/api/mcc/tasks/{task_id}/feedback",
        json={"feedback": "This did not solve it", "action": "reject"},
    )

    assert response.status_code == 200
    assert response.json()["task"]["result_status"] == 0.0
    assert response.json()["task"]["feedback"] == "This did not solve it"


def test_chat_quick_returns_reply_from_model(client, monkeypatch):
    import src.elisya.provider_registry as provider_mod

    async def fake_call_model_v2(**kwargs):
        assert kwargs["model"] == "grok-fast-4.1"
        assert kwargs["source"] == "polza"
        assert kwargs["max_tokens"] == 500
        return {"message": {"role": "assistant", "content": "Quick answer"}}

    monkeypatch.setattr(provider_mod, "call_model_v2", fake_call_model_v2)

    response = client.post(
        "/api/chat/quick",
        json={"message": "What should I do next?", "role": "architect", "context": {"nav_level": "roadmap"}},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["reply"] == "Quick answer"
    assert data["response"] == "Quick answer"
    assert data["model"] == "grok-fast-4.1"


def test_chat_quick_empty_message_returns_400(client):
    response = client.post("/api/chat/quick", json={"message": "   ", "context": {}})

    assert response.status_code == 400
    assert "message" in response.json()["detail"]


def test_chat_quick_model_failure_returns_fallback(client, monkeypatch):
    import src.elisya.provider_registry as provider_mod

    async def fake_call_model_v2(**kwargs):
        raise RuntimeError("provider offline")

    monkeypatch.setattr(provider_mod, "call_model_v2", fake_call_model_v2)

    response = client.post(
        "/api/chat/quick",
        json={"message": "hello", "role": "architect", "context": {}},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "fallback"
    assert data["reply"] == "Backend model unavailable"
    assert data["response"] == "Backend model unavailable"


def test_taskboard_update_task_persists_changes_to_json(tmp_path):
    from src.orchestration.task_board import TaskBoard

    board_file = tmp_path / "task_board.json"
    board = TaskBoard(board_file=board_file)
    task_id = _seed_task(board)

    assert board.update_task(
        task_id,
        title="Persisted title",
        feedback="Persist this feedback",
        result_status=1.0,
    )

    raw = json.loads(board_file.read_text())
    stored = raw["tasks"][task_id]
    assert stored["title"] == "Persisted title"
    assert stored["feedback"] == "Persist this feedback"
    assert stored["result_status"] == 1.0


def test_generic_rest_adapter_create_task_creates_task_in_board(board):
    from src.orchestration.taskboard_adapters import GenericRESTAdapter

    adapter = GenericRESTAdapter(board)
    result = asyncio.run(
        adapter.create_task(
            {
                "title": "Adapter create",
                "description": "Created via generic adapter",
                "preset": "dragon_gold",
            }
        )
    )

    assert result["title"] == "Adapter create"
    assert board.get_task(result["id"]) is not None


def test_generic_rest_adapter_dispatch_task_delegates_to_board(board, monkeypatch):
    from src.orchestration.taskboard_adapters import GenericRESTAdapter

    task_id = _seed_task(board)

    async def fake_dispatch(task_id_arg, **kwargs):
        assert task_id_arg == task_id
        return {"success": True, "task_id": task_id_arg, "status": "queued"}

    monkeypatch.setattr(board, "dispatch_task", fake_dispatch)

    adapter = GenericRESTAdapter(board)
    result = asyncio.run(adapter.dispatch_task(task_id))

    assert result["success"] is True
    assert result["task_id"] == task_id


def test_claude_adapter_wraps_existing_taskboard(board):
    from src.orchestration.taskboard_adapters import ClaudeMCPAdapter

    adapter = ClaudeMCPAdapter(board)
    result = asyncio.run(adapter.create_task({"title": "Claude path", "description": "wrap existing board"}))

    assert result["title"] == "Claude path"
    assert board.get_task(result["id"]) is not None
    assert adapter.adapter_name == "claude"


def test_taskboard_create_endpoint_creates_task(client, board):
    response = client.post(
        "/api/taskboard/create",
        json={"title": "REST create", "description": "from endpoint", "adapter": "generic"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["task"]["title"] == "REST create"
    assert board.get_task(data["task"]["id"]) is not None


def test_taskboard_list_endpoint_returns_all_tasks(client, board):
    _seed_task(board, title="First")
    _seed_task(board, title="Second")

    response = client.get("/api/taskboard/list")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["count"] == 2
    assert {task["title"] for task in data["tasks"]} == {"First", "Second"}


def test_taskboard_patch_endpoint_updates_task(client, board):
    task_id = _seed_task(board)

    response = client.patch(
        f"/api/taskboard/{task_id}",
        json={"description": "patched through generic api", "adapter": "generic"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["task"]["description"] == "patched through generic api"


def test_taskboard_route_selects_requested_adapter(client, monkeypatch):
    import src.api.routes.taskboard_routes as route_mod

    captured = {}

    class FakeAdapter:
        adapter_name = "claude"

        async def create_task(self, data):
            return {"id": "tb_fake", "title": data["title"], "status": "pending"}

    def fake_get_adapter(adapter_name, board=None):
        captured["adapter_name"] = adapter_name
        return FakeAdapter()

    monkeypatch.setattr(route_mod, "get_taskboard_adapter", fake_get_adapter)

    response = client.post(
        "/api/taskboard/create",
        json={"title": "Adapter selected", "adapter": "claude"},
    )

    assert response.status_code == 200
    assert captured["adapter_name"] == "claude"
    assert response.json()["adapter"] == "claude"
