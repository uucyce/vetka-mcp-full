import json
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import cut_routes as cut_module
from src.api.routes.cut_routes import router
from src.services.cut_mcp_job_store import get_cut_mcp_job_store


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _bootstrap_sandbox(root: Path) -> None:
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "cut_runtime").mkdir(parents=True, exist_ok=True)
    (root / "cut_storage").mkdir(parents=True, exist_ok=True)
    (root / "core_mirror").mkdir(parents=True, exist_ok=True)
    (root / "config" / "cut_core_mirror_manifest.json").write_text("{}\n", encoding="utf-8")


def _wait_for_job(client: TestClient, job_id: str) -> dict:
    for _ in range(20):
        response = client.get(f"/api/cut/job/{job_id}")
        job = response.json()["job"]
        if job["state"] in {"done", "error", "cancelled"}:
            return job
        time.sleep(0.05)
    raise AssertionError(f"job did not finish: {job_id}")


def _clear_jobs() -> None:
    get_cut_mcp_job_store().clear()


def test_cut_timecode_sync_worker_async_builds_persisted_result(tmp_path: Path):
    _clear_jobs()
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "cam_a_tc_01-00-00-00.mov").write_bytes(b"00")
    (source_dir / "cam_b_tc_01-00-00-12.mov").write_bytes(b"00")

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    bootstrap = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Timecode Sync Demo",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    created = client.post(
        "/api/cut/worker/timecode-sync-async",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "limit": 4,
            "fps": 25,
        },
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["success"] is True
    assert payload["schema_version"] == "cut_mcp_job_v1"

    job = _wait_for_job(client, str(payload["job_id"]))
    assert job["state"] == "done"
    assert job["job_type"] == "timecode_sync"
    assert job["result"]["success"] is True
    assert job["result"]["worker_task"]["schema_version"] == "cut_worker_task_v1"
    assert job["result"]["timecode_sync_result"]["schema_version"] == "cut_timecode_sync_result_v1"
    assert len(job["result"]["timecode_sync_result"]["items"]) == 1
    item = job["result"]["timecode_sync_result"]["items"][0]
    assert item["method"] == "timecode_v1"
    assert item["reference_timecode"] == "01:00:00:00"
    assert item["source_timecode"] == "01:00:00:12"
    assert abs(item["detected_offset_sec"] - 0.48) <= 0.001

    result_path = sandbox_root / "cut_runtime" / "state" / "timecode_sync_result.latest.json"
    assert result_path.exists()
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["schema_version"] == "cut_timecode_sync_result_v1"
    assert len(result["items"]) == 1


def test_cut_timecode_sync_worker_returns_recoverable_error_for_missing_project(tmp_path: Path):
    _clear_jobs()
    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    response = client.post(
        "/api/cut/worker/timecode-sync-async",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": "missing_project",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["schema_version"] == "cut_mcp_job_v1"
    assert payload["error"]["code"] == "project_not_found"


def test_cut_timecode_sync_worker_suppresses_duplicate_active_task(tmp_path: Path, monkeypatch):
    _clear_jobs()
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "cam_a_tc_01-00-00-00.mov").write_bytes(b"00")
    (source_dir / "cam_b_tc_01-00-00-12.mov").write_bytes(b"00")

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    bootstrap = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Timecode Sync Dup Demo",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    original = cut_module._extract_timecode_from_path

    def slow_extract(path: str, default_fps: int):
        time.sleep(0.25)
        return original(path, default_fps)

    monkeypatch.setattr(cut_module, "_extract_timecode_from_path", slow_extract)

    first = client.post(
        "/api/cut/worker/timecode-sync-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id, "limit": 4, "fps": 25},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/cut/worker/timecode-sync-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id, "limit": 4, "fps": 25},
    )
    assert second.status_code == 200
    payload = second.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "duplicate_job_active"
    assert payload["job"]["job_type"] == "timecode_sync"

    _wait_for_job(client, str(first.json()["job_id"]))
