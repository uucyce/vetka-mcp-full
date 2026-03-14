from __future__ import annotations

from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "localguys.py"

spec = importlib.util.spec_from_file_location("localguys_script", SCRIPT_PATH)
localguys = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
spec.loader.exec_module(localguys)


class _FakeHttp:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict | None]] = []
        self.run_polls: dict[str, int] = {}

    def __call__(self, method: str, url: str, payload: dict | None):
        self.calls.append((method, url, payload))
        if url.endswith("/localguys/operator-methods"):
            return {
                "success": True,
                "methods": [
                    {
                        "workflow_family": "g3_localguys",
                        "source_family": "g3_critic_coder",
                        "method": "g3",
                        "command_template": "localguys run g3 --task {task_id}",
                        "roles": ["coder", "verifier"],
                        "steps": ["recon", "plan", "execute", "verify", "review", "finalize"],
                    },
                    {
                        "workflow_family": "dragons_localguys",
                        "source_family": "dragons",
                        "method": "dragons",
                        "command_template": "localguys run dragons --task {task_id}",
                        "roles": ["scout", "architect", "coder", "verifier"],
                        "steps": ["recon", "plan", "execute", "verify", "review", "finalize"],
                    },
                ],
            }
        if method == "POST" and (url.endswith("/tasks/tb_177/localguys-run") or url.endswith("/tasks/tb_178/localguys-run")):
            assert payload is not None
            task_id = "tb_178" if url.endswith("/tasks/tb_178/localguys-run") else "tb_177"
            run_id = "lg_run_demo_178" if task_id == "tb_178" else "lg_run_demo"
            return {
                "success": True,
                "contract": {
                    "artifact_contract": {
                        "required": [
                            "facts.json",
                            "plan.json",
                            "patch.diff",
                            "test_output.txt",
                            "review.json",
                            "final_report.json",
                        ]
                    }
                },
                "run": {
                    "run_id": run_id,
                    "task_id": task_id,
                    "workflow_family": payload["workflow_family"],
                    "status": "queued",
                    "current_step": "recon",
                    "playground_id": f"pg_{task_id}",
                    "branch_name": f"lg/{task_id}",
                    "worktree_path": f"/tmp/{task_id}",
                    "created_at": "2026-03-12T12:00:00Z",
                    "updated_at": "2026-03-12T12:00:02Z",
                    "artifact_manifest": {
                        "base_path": f"artifacts/mcc_local/{task_id}/{run_id}",
                        "missing": ["facts.json", "plan.json", "patch.diff", "test_output.txt", "review.json", "final_report.json"],
                    },
                },
            }
        if method == "GET" and url.endswith("/tasks/tb_177/localguys-run"):
            return {
                "success": True,
                "run": {
                    "run_id": "lg_run_demo",
                    "task_id": "tb_177",
                    "workflow_family": "g3_localguys",
                    "status": "done",
                },
            }
        if method == "PATCH" and url.endswith("/localguys-runs/lg_run_demo"):
            return {
                "success": True,
                "run": {
                    "run_id": "lg_run_demo",
                    "task_id": "tb_177",
                    "workflow_family": "g3_localguys",
                    "status": payload.get("status", "running") if payload else "running",
                    "current_step": payload.get("current_step", "execute") if payload else "execute",
                    "metadata": dict((payload or {}).get("metadata") or {}),
                },
                "runtime_guard": {
                    "current_step": payload.get("current_step", "execute") if payload else "execute",
                    "allowed_tools": ["context", "tests"],
                    "write_opt_ins": {
                        "task_board": False,
                        "edit_file": True,
                        "playground_artifacts": True,
                        "main_tree_write": False,
                    },
                    "verification_target": "targeted_tests",
                },
            }
        if "/localguys-runs/" in url:
            run_id = url.rsplit("/", 1)[-1]
            polls = self.run_polls.get(run_id, 0)
            self.run_polls[run_id] = polls + 1
            done = polls >= 1
            return {
                "success": True,
                "run": {
                    "run_id": run_id,
                    "task_id": "tb_177",
                    "workflow_family": "g3_localguys",
                    "status": "done" if done else "running",
                    "current_step": "finalize" if done else "execute",
                    "playground_id": "pg_demo",
                    "branch_name": "lg/tb_177",
                    "worktree_path": "/tmp/pg_demo",
                    "created_at": "2026-03-12T12:00:00Z",
                    "updated_at": "2026-03-12T12:00:04Z" if done else "2026-03-12T12:00:03Z",
                    "artifact_manifest": {
                        "base_path": "artifacts/mcc_local/tb_177/lg_run_demo",
                        "missing": [] if done else ["review.json"],
                    },
                },
            }
        raise AssertionError(f"unexpected call: {method} {url}")


def test_fetch_operator_methods_returns_catalog_rows() -> None:
    fake_http = _FakeHttp()
    rows = localguys.fetch_operator_methods("http://127.0.0.1:5001", http_json=fake_http)

    assert [row["method"] for row in rows] == ["g3", "dragons"]
    assert fake_http.calls[0][1] == "http://127.0.0.1:5001/api/mcc/localguys/operator-methods"


def test_start_localguys_run_resolves_method_to_family_and_returns_metrics() -> None:
    fake_http = _FakeHttp()
    result = localguys.start_localguys_run(
        "g3",
        task_id="tb_177",
        base_url="http://127.0.0.1:5001",
        project_id="proj_local",
        preset="dragon_silver",
        http_json=fake_http,
    )

    assert result["workflow_family"] == "g3_localguys"
    assert result["method"] == "g3"
    assert result["source_family"] == "g3_critic_coder"
    assert result["playground_id"] == "pg_tb_177"
    assert result["metrics"]["required_artifact_count"] == 6
    assert result["metrics"]["artifact_missing_count"] == 6
    assert result["metrics"]["run_status"] == "queued"
    assert result["metrics"]["runtime_ms"] == 2000
    assert fake_http.calls[1][2] == {
        "workflow_family": "g3_localguys",
        "source_branch": "main",
        "project_id": "proj_local",
        "preset": "dragon_silver",
    }


def test_start_localguys_run_accepts_direct_workflow_family() -> None:
    fake_http = _FakeHttp()
    result = localguys.start_localguys_run(
        "dragons_localguys",
        task_id="tb_177",
        base_url="http://127.0.0.1:5001/api/mcc",
        http_json=fake_http,
    )

    assert result["workflow_family"] == "dragons_localguys"
    assert result["method"] == "dragons"


def test_wait_for_localguys_run_polls_until_terminal_state(monkeypatch) -> None:
    fake_http = _FakeHttp()
    monkeypatch.setattr(localguys.time, "sleep", lambda _: None)

    result = localguys.start_localguys_run(
        "g3",
        task_id="tb_177",
        base_url="http://127.0.0.1:5001",
        wait=True,
        poll_interval_sec=0.01,
        timeout_sec=1.0,
        http_json=fake_http,
    )

    assert result["status"] == "done"
    assert result["metrics"]["artifact_missing_count"] == 0
    assert result["metrics"]["runtime_ms"] == 4000


def test_get_localguys_run_supports_latest_by_task() -> None:
    fake_http = _FakeHttp()
    run = localguys.get_localguys_run(base_url="http://127.0.0.1:5001", task_id="tb_177", http_json=fake_http)
    assert run["run_id"] == "lg_run_demo"
    assert run["status"] == "done"


def test_benchmark_localguys_runs_returns_stable_metrics_schema(monkeypatch) -> None:
    fake_http = _FakeHttp()
    monkeypatch.setattr(localguys.time, "sleep", lambda _: None)

    result = localguys.benchmark_localguys_runs(
        "g3",
        task_ids=["tb_177", "tb_178"],
        base_url="http://127.0.0.1:5001",
        wait=False,
        http_json=fake_http,
    )

    assert result["success"] is True
    assert result["task_count"] == 2
    assert result["workflow_family"] == "g3_localguys"
    assert result["metrics"]["status_counts"] == {"queued": 2}
    assert "avg_latency_ms" in result["metrics"]
    assert result["metrics"]["avg_artifact_missing_count"] == 6.0


def test_start_localguys_run_rejects_unknown_method() -> None:
    fake_http = _FakeHttp()
    try:
        localguys.start_localguys_run("unknown_mode", task_id="tb_177", http_json=fake_http)
    except ValueError as exc:
        assert "Unsupported localguys method" in str(exc)
    else:
        raise AssertionError("expected ValueError for unsupported method")


def test_signal_localguys_run_sends_lifecycle_metadata_and_returns_runtime_guard() -> None:
    fake_http = _FakeHttp()
    result = localguys.signal_localguys_run(
        run_id="lg_run_demo",
        base_url="http://127.0.0.1:5001",
        status="running",
        current_step="execute",
        active_role="coder",
        used_tools=["context", "tests"],
        write_attempts=["edit_file"],
        turn_increment=1,
        recommended_tools=["pytest"],
        filtered_tool_schemas=["task_board"],
        verification_passed=True,
        verification_target="targeted_tests",
        http_json=fake_http,
    )

    assert result["success"] is True
    assert result["run"]["metadata"]["used_tools"] == ["context", "tests"]
    assert result["run"]["metadata"]["write_attempts"] == ["edit_file"]
    assert result["run"]["metadata"]["turn_increment"] == 1
    assert result["runtime_guard"]["allowed_tools"] == ["context", "tests"]
    assert fake_http.calls[-1] == (
        "PATCH",
        "http://127.0.0.1:5001/api/mcc/localguys-runs/lg_run_demo",
        {
            "status": "running",
            "current_step": "execute",
            "active_role": "coder",
            "metadata": {
                "used_tools": ["context", "tests"],
                "write_attempts": ["edit_file"],
                "turn_increment": 1,
                "recommended_tools": ["pytest"],
                "filtered_tool_schemas": ["task_board"],
                "verification_passed": True,
                "verification_target": "targeted_tests",
            },
        },
    )
