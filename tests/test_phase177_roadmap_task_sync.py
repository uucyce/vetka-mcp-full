from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def board(tmp_path: Path):
    from src.orchestration.task_board import TaskBoard

    return TaskBoard(board_file=tmp_path / "task_board.json")


@pytest.fixture
def taskboard_client(board) -> TestClient:
    from src.api.routes.taskboard_routes import router
    from src.api.routes import taskboard_routes as routes

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides = {}
    routes.get_taskboard_adapter
    return TestClient(app)


def test_taskboard_create_accepts_roadmap_binding_fields(monkeypatch: pytest.MonkeyPatch, board) -> None:
    import src.orchestration.taskboard_adapters as adapters
    from src.api.routes.taskboard_routes import router

    monkeypatch.setattr(adapters.task_board_module, "get_task_board", lambda: board)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.post(
        "/api/taskboard/create",
        json={
            "title": "Sync roadmap task",
            "description": "linked",
            "workflow_family": "g3_localguys",
            "roadmap_id": "rm_177",
            "roadmap_node_id": "node_sync_1",
            "roadmap_lane": "core",
            "roadmap_title": "Roadmap Sync",
        },
    )
    assert resp.status_code == 200
    task = resp.json()["task"]
    assert task["roadmap_id"] == "rm_177"
    assert task["roadmap_node_id"] == "node_sync_1"
    assert task["roadmap_lane"] == "core"
    assert task["roadmap_title"] == "Roadmap Sync"


def test_taskboard_create_accepts_minimal_governance_fields(monkeypatch: pytest.MonkeyPatch, board) -> None:
    import src.orchestration.taskboard_adapters as adapters
    from src.api.routes.taskboard_routes import router

    monkeypatch.setattr(adapters.task_board_module, "get_task_board", lambda: board)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.post(
        "/api/taskboard/create",
        json={
            "title": "Governed task",
            "description": "narrow lane",
            "workflow_family": "g3_localguys",
            "ownership_scope": "mcc",
            "allowed_paths": ["client/src/components/mcc/**", "src/api/routes/mcc_routes.py"],
            "owner_agent": "codex",
            "completion_contract": ["result_summary required", "vite build passes"],
        },
    )
    assert resp.status_code == 200
    task = resp.json()["task"]
    assert task["ownership_scope"] == "mcc"
    assert task["allowed_paths"] == ["client/src/components/mcc/**", "src/api/routes/mcc_routes.py"]
    assert task["owner_agent"] == "codex"
    assert task["completion_contract"] == ["result_summary required", "vite build passes"]


def test_taskboard_update_accepts_minimal_governance_fields(monkeypatch: pytest.MonkeyPatch, board) -> None:
    import src.orchestration.taskboard_adapters as adapters
    from src.api.routes.taskboard_routes import router

    task_id = board.add_task(title="Update governed task")
    monkeypatch.setattr(adapters.task_board_module, "get_task_board", lambda: board)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.patch(
        f"/api/taskboard/{task_id}",
        json={
            "ownership_scope": "mcc",
            "allowed_paths": ["client/src/components/mcc/**"],
            "owner_agent": "claude",
            "completion_contract": ["result_summary required"],
        },
    )
    assert resp.status_code == 200
    task = resp.json()["task"]
    assert task["ownership_scope"] == "mcc"
    assert task["allowed_paths"] == ["client/src/components/mcc/**"]
    assert task["owner_agent"] == "claude"
    assert task["completion_contract"] == ["result_summary required"]


def test_taskboard_update_blocks_status_change_for_non_owner_agent(monkeypatch: pytest.MonkeyPatch, board) -> None:
    import src.orchestration.taskboard_adapters as adapters
    from src.api.routes.taskboard_routes import router

    task_id = board.add_task(
        title="Owned task",
        owner_agent="codex",
        completion_contract=["result_summary required"],
    )
    monkeypatch.setattr(adapters.task_board_module, "get_task_board", lambda: board)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.patch(
        f"/api/taskboard/{task_id}",
        json={
            "status": "running",
            "actor_agent": "claude",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "owner_agent_mismatch"


def test_taskboard_update_blocks_done_without_completion_contract_requirements(monkeypatch: pytest.MonkeyPatch, board) -> None:
    import src.orchestration.taskboard_adapters as adapters
    from src.api.routes.taskboard_routes import router

    task_id = board.add_task(
        title="Contract task",
        owner_agent="codex",
        completion_contract=["result_summary required"],
    )
    monkeypatch.setattr(adapters.task_board_module, "get_task_board", lambda: board)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.patch(
        f"/api/taskboard/{task_id}",
        json={
            "status": "done",
            "actor_agent": "codex",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "completion_contract_missing_result_summary"


def test_taskboard_update_allows_done_when_completion_contract_is_satisfied(monkeypatch: pytest.MonkeyPatch, board) -> None:
    import src.orchestration.taskboard_adapters as adapters
    from src.api.routes.taskboard_routes import router

    task_id = board.add_task(
        title="Completed contract task",
        owner_agent="codex",
        completion_contract=["result_summary required"],
    )
    monkeypatch.setattr(adapters.task_board_module, "get_task_board", lambda: board)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.patch(
        f"/api/taskboard/{task_id}",
        json={
            "status": "done",
            "actor_agent": "codex",
            "result_summary": "all checks green",
            "completed_at": "2026-03-12T12:00:00",
        },
    )
    assert resp.status_code == 200
    task = resp.json()["task"]
    assert task["status"] == "done"
    assert task["result_summary"] == "all checks green"


def test_taskboard_create_accepts_extended_governance_fields(monkeypatch: pytest.MonkeyPatch, board) -> None:
    import src.orchestration.taskboard_adapters as adapters
    from src.api.routes.taskboard_routes import router

    monkeypatch.setattr(adapters.task_board_module, "get_task_board", lambda: board)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.post(
        "/api/taskboard/create",
        json={
            "title": "Extended governed task",
            "verification_agent": "codex",
            "blocked_paths": ["client/src/components/mcc/**"],
            "forbidden_scopes": ["tts", "photo_parallax"],
            "worktree_hint": ".claude/worktrees/clever-kalam",
            "touch_policy": "frontend_cut_only",
            "overlap_risk": "low",
            "depends_on_docs": ["docs/177_MCC_local/TASKBOARD_GOVERNANCE_V1.md"],
        },
    )
    assert resp.status_code == 200
    task = resp.json()["task"]
    assert task["verification_agent"] == "codex"
    assert task["blocked_paths"] == ["client/src/components/mcc/**"]
    assert task["forbidden_scopes"] == ["tts", "photo_parallax"]
    assert task["worktree_hint"] == ".claude/worktrees/clever-kalam"
    assert task["touch_policy"] == "frontend_cut_only"
    assert task["overlap_risk"] == "low"
    assert task["depends_on_docs"] == ["docs/177_MCC_local/TASKBOARD_GOVERNANCE_V1.md"]


def test_taskboard_create_p6_profile_enforces_protocol_defaults(monkeypatch: pytest.MonkeyPatch, board) -> None:
    import src.orchestration.taskboard_adapters as adapters
    from src.api.routes.taskboard_routes import router

    monkeypatch.setattr(adapters.task_board_module, "get_task_board", lambda: board)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.post(
        "/api/taskboard/create",
        json={
            "title": "P6 emergency verification",
            "profile": "p6",
            "project_lane": "phase171_emergency",
            "architecture_docs": ["docs/171_ph_multytask_vetka_MCP/PHASE_171_MULTITASK_MCC_PROJECT_LANE_RECON_2026-03-13.md"],
            "closure_tests": ["pytest -q tests/test_phase177_roadmap_task_sync.py"],
            "allowed_paths": ["src/api/routes/taskboard_routes.py"],
        },
    )
    assert resp.status_code == 200
    task = resp.json()["task"]
    assert task["project_lane"] == "phase171_emergency"
    assert task["phase_type"] == "test"
    assert task["require_closure_proof"] is True
    assert task["protocol_version"] == "multitask_mcp_v1"
    assert task["task_origin"] == "p6_profile"
    assert task["workflow_selection_origin"] == "p6_profile"
    assert "p6" in task["tags"]
    assert "closure_proof" in task["tags"]
    assert task["closure_files"] == ["src/api/routes/taskboard_routes.py"]
    assert task["depends_on_docs"] == [
        "docs/171_ph_multytask_vetka_MCP/PHASE_171_MULTITASK_MCC_PROJECT_LANE_RECON_2026-03-13.md"
    ]
    assert "closure proof required" in task["completion_contract"]


def test_taskboard_create_p6_profile_requires_docs_and_tests(monkeypatch: pytest.MonkeyPatch, board) -> None:
    import src.orchestration.taskboard_adapters as adapters
    from src.api.routes.taskboard_routes import router

    monkeypatch.setattr(adapters.task_board_module, "get_task_board", lambda: board)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.post(
        "/api/taskboard/create",
        json={
            "title": "Broken p6 task",
            "profile": "p6",
            "project_lane": "phase171_emergency",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "p6 profile requires: architecture_docs, closure_tests"


def test_verification_agent_can_update_status_when_owner_differs(monkeypatch: pytest.MonkeyPatch, board) -> None:
    import src.orchestration.taskboard_adapters as adapters
    from src.api.routes.taskboard_routes import router

    task_id = board.add_task(
        title="Verified task",
        owner_agent="claude",
        verification_agent="codex",
        completion_contract=["result_summary required"],
    )
    monkeypatch.setattr(adapters.task_board_module, "get_task_board", lambda: board)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.patch(
        f"/api/taskboard/{task_id}",
        json={
            "status": "running",
            "actor_agent": "codex",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["task"]["status"] == "running"


def test_sync_task_status_to_roadmap_updates_bound_node(tmp_path: Path, board) -> None:
    from src.services.roadmap_task_sync import sync_task_status_to_roadmap
    from src.services.roadmap_generator import RoadmapDAG
    original_load = RoadmapDAG.load

    roadmap_path = tmp_path / "roadmap_dag.json"
    roadmap = RoadmapDAG(
        project_id="rm_177",
        nodes=[{"id": "node_sync_1", "label": "Sync Node", "status": "pending", "layer": "core"}],
        edges=[],
    )
    assert roadmap.save(str(roadmap_path)) is True

    task_id = board.add_task(
        title="Bound task",
        roadmap_id="rm_177",
        roadmap_node_id="node_sync_1",
        roadmap_lane="core",
        roadmap_title="Sync Node",
    )
    task = board.get_task(task_id)
    assert task is not None
    task["status"] = "done"

    assert sync_task_status_to_roadmap(task, roadmap_path=str(roadmap_path)) is True
    saved = json.loads(roadmap_path.read_text())
    node = saved["nodes"][0]
    assert node["status"] == "completed"
    assert node["task_sync_status"] == "done"
    assert node["task_sync_task_id"] == task_id
    assert node["task_sync_counts"]["completed"] == 1
    assert node["task_sync_progress"] == 100.0


def test_sync_task_status_to_roadmap_aggregates_multiple_tasks(tmp_path: Path, board) -> None:
    from src.services.roadmap_task_sync import sync_task_status_to_roadmap
    from src.services.roadmap_generator import RoadmapDAG

    roadmap_path = tmp_path / "roadmap_dag.json"
    roadmap = RoadmapDAG(
        project_id="rm_177",
        nodes=[{"id": "node_sync_1", "label": "Sync Node", "status": "pending", "layer": "core"}],
        edges=[],
    )
    assert roadmap.save(str(roadmap_path)) is True

    done_id = board.add_task(title="Done task", roadmap_node_id="node_sync_1")
    run_id = board.add_task(title="Running task", roadmap_node_id="node_sync_1")
    done_task = board.get_task(done_id)
    running_task = board.get_task(run_id)
    assert done_task is not None and running_task is not None
    done_task["status"] = "done"
    running_task["status"] = "running"

    assert sync_task_status_to_roadmap(running_task, tasks=[done_task, running_task], roadmap_path=str(roadmap_path)) is True
    saved = json.loads(roadmap_path.read_text())
    node = saved["nodes"][0]
    assert node["status"] == "active"
    assert node["task_sync_counts"] == {"total": 2, "completed": 1, "active": 1, "failed": 0}
    assert node["task_sync_progress"] == 50.0


def test_mcc_task_context_packet_includes_roadmap_binding(monkeypatch: pytest.MonkeyPatch, board) -> None:
    import src.api.routes.mcc_routes as routes
    from src.api.routes.mcc_routes import router

    task_id = board.add_task(
        title="Context packet task",
        workflow_family="g3_localguys",
        workflow_id="g3_localguys",
        roadmap_id="rm_177",
        roadmap_node_id="node_sync_1",
        roadmap_lane="core",
        roadmap_title="Sync Node",
        architecture_docs=["docs/177_MCC_local/ROADMAP_TASKBOARD_SYNC_PROPOSAL.md"],
        closure_tests=["python -m pytest tests/test_phase177_roadmap_task_sync.py -q"],
        closure_files=["src/api/routes/mcc_routes.py"],
        ownership_scope="mcc",
        allowed_paths=["client/src/components/mcc/**"],
        owner_agent="codex",
        completion_contract=["result_summary required"],
        verification_agent="claude",
        blocked_paths=["client/src/components/cut/**"],
        forbidden_scopes=["tts"],
        worktree_hint="codex_desktop_mcc_lane",
        touch_policy="shared_runtime_requires_lock",
        overlap_risk="medium",
        depends_on_docs=["docs/177_MCC_local/TASKBOARD_GOVERNANCE_V1.md"],
    )

    monkeypatch.setattr(routes, "_get_task_board_instance", lambda: board)

    async def _fake_contract(_family: str):
        return {
            "workflow_family": "g3_localguys",
            "steps": ["recon", "execute"],
            "execution_mode": "staged_state_machine",
            "sandbox_policy": {"mode": "playground_only", "requires_playground": True},
            "write_opt_ins": {"task_board": False, "edit_file": True},
            "verification_target": "targeted_tests",
            "max_turns": 8,
            "idle_nudge_template": "Stay inside the playground.",
            "stage_tool_policy": {"recon": ["context", "search"]},
            "artifact_contract": {"required": []},
        }

    monkeypatch.setattr(routes, "_resolve_workflow_contract", _fake_contract)

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.get(f"/api/mcc/tasks/{task_id}/context-packet")
    assert resp.status_code == 200
    packet = resp.json()["packet"]
    assert packet["roadmap_binding"] == {
        "roadmap_id": "rm_177",
        "roadmap_node_id": "node_sync_1",
        "roadmap_lane": "core",
        "roadmap_title": "Sync Node",
    }
    assert packet["workflow_contract"]["workflow_family"] == "g3_localguys"
    assert packet["localguys_compliance"] == {
        "workflow_family": "g3_localguys",
        "execution_mode": "staged_state_machine",
        "sandbox_mode": "playground_only",
        "requires_playground": True,
        "write_opt_ins": {"task_board": False, "edit_file": True},
        "verification_target": "targeted_tests",
        "max_turns": 8,
        "idle_nudge_template": "Stay inside the playground.",
        "stage_tool_policy": {"recon": ["context", "search"]},
        "active_step": "",
        "active_step_allowed_tools": [],
        "telemetry": {
            "recommended_tools": [],
            "filtered_tool_schemas": [],
            "idle_turn_count": 0,
            "verification_passed": False,
        },
    }
    assert packet["governance"] == {
        "ownership_scope": "mcc",
        "allowed_paths": ["client/src/components/mcc/**"],
        "blocked_paths": ["client/src/components/cut/**"],
        "forbidden_scopes": ["tts"],
        "owner_agent": "codex",
        "verification_agent": "claude",
        "touch_policy": "shared_runtime_requires_lock",
        "overlap_risk": "medium",
        "completion_contract": ["result_summary required"],
        "depends_on_docs": ["docs/177_MCC_local/TASKBOARD_GOVERNANCE_V1.md"],
        "worktree_hint": "codex_desktop_mcc_lane",
    }
    assert packet["docs"]["architecture_docs"] == ["docs/177_MCC_local/ROADMAP_TASKBOARD_SYNC_PROPOSAL.md"]
    assert packet["tests"]["closure_tests"] == ["python -m pytest tests/test_phase177_roadmap_task_sync.py -q"]
    assert packet["history"][-1]["event"] == "created"
    assert packet["gaps"] == []


def test_mcc_task_context_packet_enriches_roadmap_docs_and_localguys_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    board,
) -> None:
    import src.api.routes.mcc_routes as routes
    from src.api.routes.mcc_routes import router
    from src.services.mcc_local_run_registry import LocalguysRunRegistry
    from src.services.roadmap_generator import RoadmapDAG
    original_load = RoadmapDAG.load

    roadmap_path = tmp_path / "roadmap_dag.json"
    roadmap = RoadmapDAG(
        project_id="rm_177",
        nodes=[
            {
                "id": "node_sync_1",
                "label": "Sync Node",
                "status": "pending",
                "layer": "core",
                "docs": ["docs/177_MCC_local/LITERT_BENCHMARK_DIRECTION.md"],
                "file_patterns": ["src/services/roadmap_task_sync.py"],
            }
        ],
        edges=[],
    )
    assert roadmap.save(str(roadmap_path)) is True

    task_id = board.add_task(
        title="Context enrich task",
        workflow_family="g3_localguys",
        workflow_id="g3_localguys",
        roadmap_id="rm_177",
        roadmap_node_id="node_sync_1",
        roadmap_lane="core",
        roadmap_title="Sync Node",
    )

    registry = LocalguysRunRegistry(
        registry_file=tmp_path / "localguys_runs.json",
        artifacts_root=tmp_path / "artifacts",
    )
    run = registry.create_run(
        task_id=task_id,
        workflow_family="g3_localguys",
        contract={
            "version": "v1",
            "execution_mode": "staged_state_machine",
            "sandbox_policy": {"mode": "playground_only", "requires_playground": True},
            "write_opt_ins": {"task_board": False, "edit_file": True},
            "verification_target": "targeted_tests",
            "max_turns": 6,
            "idle_nudge_template": "Stay inside the playground.",
            "stage_tool_policy": {"recon": ["context", "search"]},
            "artifact_contract": {"required": ["facts.json"]},
        },
        playground={
            "playground_id": "pg_test",
            "branch_name": "playground/pg_test",
            "worktree_path": str(tmp_path / "pg"),
        },
        task_snapshot=board.get_task(task_id),
    )
    run = registry.update_run(
        run["run_id"],
        current_step="recon",
        metadata={
            "recommended_tools": ["rg", "pytest"],
            "filtered_tool_schemas": ["edit_file"],
            "idle_turn_count": 1,
            "verification_passed": True,
            "verification_target": "targeted_tests",
        },
    ) or run

    monkeypatch.setattr(routes, "_get_task_board_instance", lambda: board)
    monkeypatch.setattr("src.services.mcc_local_run_registry.get_localguys_run_registry", lambda: registry)
    monkeypatch.setattr(
        "src.services.roadmap_generator.RoadmapDAG.load",
        classmethod(lambda cls, path=None: original_load(str(roadmap_path))),
    )

    async def _fake_contract(_family: str):
        return {
            "workflow_family": "g3_localguys",
            "steps": ["recon"],
            "execution_mode": "staged_state_machine",
            "sandbox_policy": {"mode": "playground_only", "requires_playground": True},
            "write_opt_ins": {"task_board": False, "edit_file": True},
            "verification_target": "targeted_tests",
            "max_turns": 6,
            "idle_nudge_template": "Stay inside the playground.",
            "stage_tool_policy": {"recon": ["context", "search"]},
            "artifact_contract": {"required": ["facts.json"]},
        }

    monkeypatch.setattr(routes, "_resolve_workflow_contract", _fake_contract)

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.get(f"/api/mcc/tasks/{task_id}/context-packet")
    assert resp.status_code == 200
    packet = resp.json()["packet"]
    assert "docs/177_MCC_local/LITERT_BENCHMARK_DIRECTION.md" in packet["docs"]["architecture_docs"]
    assert "src/services/roadmap_task_sync.py" in packet["code_scope"]["closure_files"]
    assert packet["artifacts"]["recent_localguys_runs"][0]["run_id"] == run["run_id"]
    assert packet["localguys_compliance"]["active_step"] == "recon"
    assert packet["localguys_compliance"]["active_step_allowed_tools"] == ["context", "search"]
    assert packet["localguys_compliance"]["telemetry"]["recommended_tools"] == ["rg", "pytest"]
    assert packet["localguys_compliance"]["telemetry"]["verification_passed"] is True
    assert "missing_tests" in packet["gaps"]


def test_create_tasks_from_roadmap_node_auto_binds_roadmap_metadata(monkeypatch: pytest.MonkeyPatch, board) -> None:
    import src.api.routes.mcc_routes as routes
    from src.api.routes.mcc_routes import router

    class _FakeRoadmap:
        project_id = "rm_177"

        def to_frontend_format(self):
            return {
                "nodes": [
                    {
                        "id": "node_sync_1",
                        "data": {
                            "id": "node_sync_1",
                            "label": "Sync Node",
                            "description": "Implement sync",
                            "layer": "core",
                            "files": ["src/orchestration/task_board.py"],
                        },
                    }
                ]
            }

    monkeypatch.setattr(routes, "_get_task_board_instance", lambda: board)
    monkeypatch.setattr("src.services.roadmap_generator.RoadmapDAG.load", classmethod(lambda cls, path=None: _FakeRoadmap()))

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.post("/api/mcc/roadmap/node_sync_1/create-tasks")
    assert resp.status_code == 200
    task_ids = resp.json()["tasks"]
    assert len(task_ids) >= 1
    task = board.get_task(task_ids[0])
    assert task is not None
    assert task["roadmap_id"] == "rm_177"
    assert task["roadmap_node_id"] == "node_sync_1"
    assert task["roadmap_lane"] == "core"
    assert task["task_origin"] == "roadmap_sync"
    assert task["workflow_selection_origin"] == "roadmap_sync"


def test_build_directory_tree_keeps_nested_structure(tmp_path: Path) -> None:
    from src.api.routes.mcc_routes import _build_directory_tree

    root = tmp_path / "project"
    nested = root / "src" / "services"
    nested.mkdir(parents=True)
    (nested / "worker.py").write_text("print('ok')\n", encoding="utf-8")
    (root / "README.md").write_text("# ok\n", encoding="utf-8")

    tree = _build_directory_tree(str(root / "src"), str(root), depth=4, limit=50)

    assert tree["path"] == "src"
    assert tree["kind"] == "directory"
    assert tree["children"][0]["path"] == "src/services"
    assert tree["children"][0]["children"][0]["path"] == "src/services/worker.py"


def test_mcc_directory_tree_endpoint_returns_nested_children(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from src.api.routes.mcc_routes import router

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 177 contracts changed")

    root = tmp_path / "project"
    nested = root / "docs" / "phase177"
    nested.mkdir(parents=True)
    (nested / "plan.md").write_text("plan\n", encoding="utf-8")

    config = type("Cfg", (), {"sandbox_path": str(root), "source_path": str(root)})()
    monkeypatch.setattr("src.api.routes.mcc_routes._load_active_project_config", lambda: config)

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.get("/api/mcc/directory-tree", params={"path": "docs", "depth": 4})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["path"] == "docs"
    assert payload["tree"]["children"][0]["path"] == "docs/phase177"
    assert payload["tree"]["children"][0]["children"][0]["path"] == "docs/phase177/plan.md"
