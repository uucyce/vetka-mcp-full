from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class _FakeBoard:
    def __init__(self, task: dict | None = None, tasks: list[dict] | None = None) -> None:
        self.tasks = {}
        for row in list(tasks or []):
            task_id = str((row or {}).get("id") or "").strip()
            if task_id:
                self.tasks[task_id] = dict(row)
        if task:
            task_id = str(task.get("id") or "").strip()
            if task_id:
                self.tasks[task_id] = dict(task)

    def get_task(self, task_id: str):
        row = self.tasks.get(task_id)
        return dict(row) if row else None


class _FakeLLMRegistry:
    def __init__(self, profiles: dict[str, object]) -> None:
        self._profiles = profiles

    async def get_profile(self, model_id: str):
        if model_id not in self._profiles:
            raise AssertionError(f"unexpected model lookup: {model_id}")
        return self._profiles[model_id]


def _localguys_profiles() -> dict[str, object]:
    return {
        model_id: SimpleNamespace(
            model_id=model_id,
            context_length=32768,
            output_tokens_per_second=42.0,
            input_tokens_per_second=115.0,
            ttft_ms=650.0,
            provider="ollama",
            source="test_fixture",
        )
        for model_id in [
            "qwen3.5:latest",
            "qwen3:8b",
            "qwen2.5:7b",
            "qwen2.5:3b",
            "deepseek-r1:8b",
            "phi4-mini:latest",
            "qwen2.5vl:3b",
            "embeddinggemma:300m",
        ]
    }


def _install_localguys_client(
    *,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tasks: list[dict],
) -> TestClient:
    import src.api.routes.mcc_routes as routes
    from src.api.routes.mcc_routes import router
    from src.services.mcc_local_run_registry import LocalguysRunRegistry

    board = _FakeBoard(tasks=tasks)
    monkeypatch.setattr(routes, "_get_task_board_instance", lambda: board)
    monkeypatch.setattr("src.elisya.llm_model_registry.get_llm_registry", lambda: _FakeLLMRegistry(_localguys_profiles()))

    fake_models = {
        model_id: SimpleNamespace(
            id=model_id,
            provider="ollama",
            available=True,
            type=SimpleNamespace(value="local"),
            capabilities=[SimpleNamespace(value=value) for value in caps],
        )
        for model_id, caps in {
            "qwen3.5:latest": ["chat", "code"],
            "qwen3:8b": ["chat", "code"],
            "qwen2.5:7b": ["chat", "code"],
            "qwen2.5:3b": ["chat", "code"],
            "deepseek-r1:8b": ["chat", "reasoning"],
            "phi4-mini:latest": ["chat", "reasoning"],
            "qwen2.5vl:3b": ["chat", "vision"],
            "embeddinggemma:300m": ["embeddings"],
        }.items()
    }
    monkeypatch.setattr(
        "src.services.model_registry.get_model_registry",
        lambda: SimpleNamespace(_models=fake_models, _detect_capabilities=lambda model_id: []),
    )

    registry = LocalguysRunRegistry(
        registry_file=tmp_path / "localguys_runs.json",
        artifacts_root=tmp_path / "artifacts",
    )
    monkeypatch.setattr(routes, "_get_localguys_run_registry", lambda: registry)

    async def _fake_create_playground(*, task_description: str, preset: str, source_branch: str):
        playground_id = f"pg_{abs(hash((task_description, preset, source_branch))) % 100000}"
        worktree_path = tmp_path / "playgrounds" / playground_id
        worktree_path.mkdir(parents=True, exist_ok=True)
        return {
            "playground_id": playground_id,
            "branch_name": f"playground/{playground_id}",
            "worktree_path": str(worktree_path),
            "status": "active",
            "task_description": task_description,
            "preset": preset,
            "source_branch": source_branch,
        }

    monkeypatch.setattr(routes, "_create_localguys_playground", _fake_create_playground)

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    client._registry = registry  # type: ignore[attr-defined]
    return client


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    return _install_localguys_client(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        tasks=[
            {
            "id": "tb_local_1",
            "title": "Localguys narrow fix",
            "description": "Run local workflow in playground",
            "phase_type": "fix",
            "complexity": "medium",
            "preset": "dragon_silver",
            "team_profile": "dragon_silver",
            "workflow_id": "g3_localguys",
            "workflow_family": "g3_localguys",
            "workflow_selection_origin": "user-selected",
            }
        ],
    )


def _start_run(client: TestClient):
    resp = client.post("/api/mcc/tasks/tb_local_1/localguys-run")
    assert resp.status_code == 200
    return resp.json()["run"]


def test_localguys_run_start_creates_playground_binding_and_artifact_layout(client: TestClient) -> None:
    resp = client.post("/api/mcc/tasks/tb_local_1/localguys-run")
    assert resp.status_code == 200
    payload = resp.json()
    run = payload["run"]

    assert run["task_id"] == "tb_local_1"
    assert run["workflow_family"] == "g3_localguys"
    assert run["playground_id"].startswith("pg_")
    assert run["branch_name"] == f"playground/{run['playground_id']}"
    assert run["status"] == "queued"
    assert run["artifact_manifest"]["required"] == [
        "facts.json",
        "plan.json",
        "patch.diff",
        "test_output.txt",
        "review.json",
        "final_report.json",
    ]
    assert run["artifact_manifest"]["missing"] == run["artifact_manifest"]["required"]
    assert run["metrics"]["required_artifact_count"] == 6
    assert run["metrics"]["artifact_missing_count"] == 6
    assert run["metrics"]["artifact_present_count"] == 0
    assert run["metrics"]["run_status"] == "queued"
    assert Path(run["artifact_manifest"]["artifact_root_abs"]).is_dir()
    assert payload["runtime_guard"]["current_step"] == "recon"
    assert payload["runtime_guard"]["allowed_tools"] == ["context", "search", "artifacts", "stats"]
    assert payload["runtime_guard"]["write_opt_ins"]["task_board"] is False


def test_localguys_run_done_is_blocked_until_required_artifacts_exist(client: TestClient) -> None:
    run = _start_run(client)

    resp = client.patch(
        f"/api/mcc/localguys-runs/{run['run_id']}",
        json={"status": "done", "current_step": "finalize"},
    )
    assert resp.status_code == 400
    assert "required_artifact_missing" in resp.json()["detail"]


def test_localguys_artifact_write_and_finalize_passes_contract_validation(client: TestClient) -> None:
    run = _start_run(client)
    required = run["artifact_manifest"]["required"]

    for artifact_name in required:
        resp = client.put(
            f"/api/mcc/localguys-runs/{run['run_id']}/artifacts/{artifact_name}",
            json={"content": f"artifact::{artifact_name}"},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["success"] is True
        assert payload["artifact"]["name"] == artifact_name
        assert payload["artifact"]["exists"] is True

    resp = client.patch(
        f"/api/mcc/localguys-runs/{run['run_id']}",
        json={"status": "done", "current_step": "finalize", "active_role": "verifier"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["run"]["status"] == "done"
    assert data["run"]["artifact_manifest"]["missing"] == []
    assert data["run"]["metrics"]["artifact_missing_count"] == 0
    assert data["run"]["metrics"]["artifact_present_count"] == 6
    assert data["run"]["metrics"]["run_status"] == "done"


def test_localguys_run_lookup_by_task_returns_latest_run(client: TestClient) -> None:
    first_run = _start_run(client)
    second_run = _start_run(client)

    resp = client.get("/api/mcc/tasks/tb_local_1/localguys-run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["task_id"] == "tb_local_1"
    assert data["run"]["run_id"] == second_run["run_id"]
    assert data["run"]["run_id"] != first_run["run_id"]


def test_localguys_benchmark_summary_reports_status_and_metrics(client: TestClient) -> None:
    first_run = _start_run(client)
    second_run = _start_run(client)

    required = first_run["artifact_manifest"]["required"]
    for artifact_name in required:
        resp = client.put(
            f"/api/mcc/localguys-runs/{first_run['run_id']}/artifacts/{artifact_name}",
            json={"content": f"artifact::{artifact_name}"},
        )
        assert resp.status_code == 200

    resp = client.patch(
        f"/api/mcc/localguys-runs/{first_run['run_id']}",
        json={"status": "done", "current_step": "finalize", "active_role": "verifier"},
    )
    assert resp.status_code == 200

    resp = client.patch(
        f"/api/mcc/localguys-runs/{second_run['run_id']}",
        json={"status": "failed", "current_step": "verify", "failure_reason": "verifier_blocked"},
    )
    assert resp.status_code == 200

    resp = client.get("/api/mcc/localguys/benchmark-summary", params={"workflow_family": "g3_localguys"})
    assert resp.status_code == 200
    data = resp.json()
    summary = data["summary"]

    assert data["success"] is True
    assert summary["workflow_family"] == "g3_localguys"
    assert summary["count"] == 2
    assert summary["status_counts"] == {"failed": 1, "done": 1}
    assert summary["success_rate"] == 50.0
    assert summary["avg_required_artifact_count"] == 6.0
    assert len(summary["recent_runs"]) == 2


def test_localguys_run_metadata_surfaces_playbook_telemetry_and_summary(client: TestClient) -> None:
    run = _start_run(client)

    resp = client.patch(
        f"/api/mcc/localguys-runs/{run['run_id']}",
        json={
            "status": "running",
            "current_step": "verify",
            "active_role": "verifier",
            "metadata": {
                "recommended_tools": ["pytest", "rg", "pytest"],
                "filtered_tool_schemas": ["edit_file", "task_board"],
                "idle_turn_count": 2,
                "verification_passed": True,
                "verification_target": "targeted_tests",
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    telemetry = data["run"]["telemetry"]

    assert telemetry["recommended_tools"] == ["pytest", "rg"]
    assert telemetry["filtered_tool_schemas"] == ["edit_file", "task_board"]
    assert telemetry["idle_turn_count"] == 2
    assert telemetry["verification_passed"] is True
    assert telemetry["verification_target"] == "targeted_tests"
    assert data["run"]["metrics"]["recommended_tool_count"] == 2
    assert data["run"]["metrics"]["filtered_tool_schema_count"] == 2
    assert data["run"]["metrics"]["idle_turn_count"] == 2
    assert data["run"]["metrics"]["verification_passed"] is True

    summary_resp = client.get("/api/mcc/localguys/benchmark-summary", params={"workflow_family": "g3_localguys"})
    assert summary_resp.status_code == 200
    summary = summary_resp.json()["summary"]

    assert summary["count"] == 1
    assert summary["avg_idle_turn_count"] == 2.0
    assert summary["verification_pass_rate"] == 100.0
    assert summary["runs_with_recommended_tools"] == 1
    assert summary["runs_with_filtered_tool_schemas"] == 1


def test_localguys_run_rejects_tools_not_allowed_for_current_step(client: TestClient) -> None:
    run = _start_run(client)

    resp = client.patch(
        f"/api/mcc/localguys-runs/{run['run_id']}",
        json={
            "status": "running",
            "current_step": "recon",
            "metadata": {
                "used_tools": ["tasks"],
            },
        },
    )
    assert resp.status_code == 400
    assert "disallowed_tools_for_step:recon:tasks" == resp.json()["detail"]


def test_localguys_run_rejects_write_attempts_outside_contract(client: TestClient) -> None:
    run = _start_run(client)

    resp = client.patch(
        f"/api/mcc/localguys-runs/{run['run_id']}",
        json={
            "status": "running",
            "current_step": "execute",
            "metadata": {
                "write_attempts": ["task_board"],
            },
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "write_scope_not_allowed:task_board"


def test_localguys_run_tracks_turn_budget_and_runtime_guard(client: TestClient) -> None:
    run = _start_run(client)

    resp = client.patch(
        f"/api/mcc/localguys-runs/{run['run_id']}",
        json={
            "status": "running",
            "current_step": "execute",
            "metadata": {
                "turn_increment": 2,
                "used_tools": ["context", "tests"],
            },
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["run"]["metadata"]["turn_count"] == 2
    assert payload["runtime_guard"]["current_step"] == "execute"
    assert payload["runtime_guard"]["turn_count"] == 2
    assert payload["runtime_guard"]["remaining_turns"] == 11

    exceeded = client.patch(
        f"/api/mcc/localguys-runs/{run['run_id']}",
        json={
            "metadata": {
                "turn_increment": 20,
            },
        },
    )
    assert exceeded.status_code == 400
    assert exceeded.json()["detail"] == "max_turns_exceeded:22/13"


def test_localguys_run_start_returns_503_when_playground_creation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.api.routes.mcc_routes as routes
    from src.api.routes.mcc_routes import router
    from src.services.mcc_local_run_registry import LocalguysRunRegistry

    board = _FakeBoard(
        {
            "id": "tb_local_1",
            "title": "Localguys narrow fix",
            "description": "Run local workflow in playground",
            "workflow_id": "g3_localguys",
            "workflow_family": "g3_localguys",
        }
    )
    monkeypatch.setattr(routes, "_get_task_board_instance", lambda: board)
    registry = LocalguysRunRegistry(
        registry_file=tmp_path / "localguys_runs.json",
        artifacts_root=tmp_path / "artifacts",
    )
    monkeypatch.setattr(routes, "_get_localguys_run_registry", lambda: registry)
    async def _boom_create_playground(*, task_description: str, preset: str, source_branch: str):
        raise RuntimeError("boom")

    monkeypatch.setattr(routes, "_create_localguys_playground", _boom_create_playground)

    profiles = {
        model_id: SimpleNamespace(
            model_id=model_id,
            context_length=32768,
            output_tokens_per_second=42.0,
            input_tokens_per_second=115.0,
            ttft_ms=650.0,
            provider="ollama",
            source="test_fixture",
        )
        for model_id in [
            "qwen3.5:latest",
            "qwen3:8b",
            "qwen2.5:7b",
            "qwen2.5:3b",
            "deepseek-r1:8b",
            "phi4-mini:latest",
            "qwen2.5vl:3b",
            "embeddinggemma:300m",
        ]
    }
    monkeypatch.setattr("src.elisya.llm_model_registry.get_llm_registry", lambda: _FakeLLMRegistry(profiles))
    monkeypatch.setattr(
        "src.services.model_registry.get_model_registry",
        lambda: SimpleNamespace(_models={}, _detect_capabilities=lambda model_id: []),
    )

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.post("/api/mcc/tasks/tb_local_1/localguys-run")
    assert resp.status_code == 503
    assert "playground" in resp.json()["detail"].lower()


def test_localguys_replay_fixture_preserves_multitask_protocol_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _install_localguys_client(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        tasks=[
            {
                "id": "tb_1773261070_1",
                "title": "Phase 171 protocol closeout: guarded multitask closure with history and digest sync",
                "description": "Implement protocol-backed TaskBoard closure handshake, task history, lane metadata, close API, and closure protocol wiring.",
                "phase_type": "build",
                "status": "queued",
                "preset": "dragon_silver",
                "team_profile": "dragon_silver",
                "workflow_id": "g3_localguys",
                "workflow_family": "g3_localguys",
                "workflow_selection_origin": "user-selected",
                "project_id": "171_multitask_mcp",
                "project_lane": "171_multitask_mcp",
                "protocol_version": "multitask_mcp_v1",
                "closure_tests": [
                    "pytest -q tests/test_phase136_task_board_claim_complete.py tests/test_phase171_multitask_digest_contract.py"
                ],
                "tags": ["phase171", "multitask", "backend", "critical"],
            }
        ],
    )

    resp = client.post("/api/mcc/tasks/tb_1773261070_1/localguys-run")
    assert resp.status_code == 200
    run = resp.json()["run"]

    assert run["task_snapshot"]["project_id"] == "171_multitask_mcp"
    assert run["task_snapshot"]["project_lane"] == "171_multitask_mcp"
    assert run["task_snapshot"]["protocol_version"] == "multitask_mcp_v1"
    assert run["task_snapshot"]["closure_tests"] == [
        "pytest -q tests/test_phase136_task_board_claim_complete.py tests/test_phase171_multitask_digest_contract.py"
    ]
    assert "tb_1773261070_1" in run["artifact_manifest"]["artifact_root_abs"]


def test_localguys_live_queue_runtime_keeps_parallel_task_runs_isolated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _install_localguys_client(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        tasks=[
            {
                "id": "tb_1773251065_1",
                "title": "MARKER_176.1B: Roadmap→Task Bridge Backend",
                "description": "Add backend roadmap create-tasks bridge.",
                "phase_type": "build",
                "status": "queued",
                "preset": "dragon_bronze",
                "team_profile": "dragon_bronze",
                "workflow_id": "g3_localguys",
                "workflow_family": "g3_localguys",
                "workflow_selection_origin": "user-selected",
                "tags": ["phase176", "backend", "critical"],
            },
            {
                "id": "tb_1773251071_3",
                "title": "MARKER_176.3B: Apply/Reject Backend Handlers",
                "description": "Wire apply and reject handlers in MCC backend.",
                "phase_type": "build",
                "status": "queued",
                "preset": "dragon_bronze",
                "team_profile": "dragon_bronze",
                "workflow_id": "g3_localguys",
                "workflow_family": "g3_localguys",
                "workflow_selection_origin": "user-selected",
                "tags": ["phase176", "backend", "critical"],
            },
        ],
    )

    first = client.post("/api/mcc/tasks/tb_1773251065_1/localguys-run")
    second = client.post("/api/mcc/tasks/tb_1773251071_3/localguys-run")
    assert first.status_code == 200
    assert second.status_code == 200

    first_run = first.json()["run"]
    second_run = second.json()["run"]
    assert first_run["run_id"] != second_run["run_id"]
    assert first_run["artifact_manifest"]["artifact_root_abs"] != second_run["artifact_manifest"]["artifact_root_abs"]
    assert first_run["playground_id"] != second_run["playground_id"]

    first_latest = client.get("/api/mcc/tasks/tb_1773251065_1/localguys-run")
    second_latest = client.get("/api/mcc/tasks/tb_1773251071_3/localguys-run")
    assert first_latest.status_code == 200
    assert second_latest.status_code == 200
    assert first_latest.json()["run"]["run_id"] == first_run["run_id"]
    assert second_latest.json()["run"]["run_id"] == second_run["run_id"]


def test_localguys_benchmark_summary_merges_litert_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.api.routes.mcc_routes as routes
    from src.services.mcc_benchmark_store import MCCBenchmarkStore

    client = _install_localguys_client(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        tasks=[
            {
                "id": "tb_local_1",
                "title": "Localguys narrow fix",
                "description": "Run local workflow in playground",
                "phase_type": "fix",
                "preset": "dragon_silver",
                "team_profile": "dragon_silver",
                "workflow_id": "g3_localguys",
                "workflow_family": "g3_localguys",
                "workflow_selection_origin": "user-selected",
            }
        ],
    )
    benchmark_store = MCCBenchmarkStore(store_file=tmp_path / "mcc_benchmarks.json")
    monkeypatch.setattr(routes, "_get_mcc_benchmark_store", lambda: benchmark_store)

    run = _start_run(client)
    required = run["artifact_manifest"]["required"]
    for artifact_name in required:
        resp = client.put(
            f"/api/mcc/localguys-runs/{run['run_id']}/artifacts/{artifact_name}",
            json={"content": f"artifact::{artifact_name}"},
        )
        assert resp.status_code == 200
    resp = client.patch(
        f"/api/mcc/localguys-runs/{run['run_id']}",
        json={"status": "done", "current_step": "finalize", "active_role": "verifier"},
    )
    assert resp.status_code == 200

    litert_resp = client.post(
        "/api/mcc/benchmarks",
        json={
            "runtime_name": "litert",
            "workflow_family": "litert_benchmark",
            "task_id": "tb_1773275513_6",
            "run_status": "measured",
            "device_profile": "apple_silicon_m4",
            "accelerator": "gpu_metal",
            "cold_start_ms": 180,
            "avg_runtime_ms": 42,
            "runtime_ms": 42,
            "success_rate": 100.0,
            "notes": "smoke",
        },
    )
    assert litert_resp.status_code == 200
    assert litert_resp.json()["record"]["runtime_name"] == "litert"

    resp = client.get("/api/mcc/localguys/benchmark-summary", params={"limit": 10})
    assert resp.status_code == 200
    summary = resp.json()["summary"]

    assert summary["count"] == 2
    assert summary["runtime_counts"]["localguys"] == 1
    assert summary["runtime_counts"]["litert"] == 1
    assert summary["status_counts"]["done"] == 1
    assert summary["status_counts"]["measured"] == 1
    assert summary["success_rate"] == 100.0
    assert any(row.get("runtime_name") == "litert" for row in summary["recent_runs"])
