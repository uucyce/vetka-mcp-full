import json
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import cut_routes as cut_module
from src.api.routes.cut_routes import router
from src.api.routes.cut_routes_workers import worker_router
from src.services.cut_mcp_job_store import get_cut_mcp_job_store


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.include_router(worker_router, prefix="/api/cut/worker")
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


def _bootstrap_async_and_wait(client: TestClient, source_dir: Path, sandbox_root: Path, project_name: str = "Test Project") -> str:
    """MARKER_QA.BOOTSTRAP_ASYNC_V2 — Migrate sync bootstrap tests to async pattern.

    Old pattern (removed): POST /api/cut/bootstrap → returns project immediately
    New pattern (async): POST /api/cut/worker/bootstrap-async → returns job_id, poll until done

    Returns: project_id from completed bootstrap job.
    """
    # Step 1: Start async bootstrap job
    bootstrap_resp = client.post(
        "/api/cut/worker/bootstrap-async",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": project_name,
        },
    )
    assert bootstrap_resp.status_code == 200, f"Bootstrap failed: {bootstrap_resp.text}"
    job_id = bootstrap_resp.json()["job_id"]

    # Step 2: Poll until job completes
    job = _wait_for_job(client, str(job_id))
    assert job["state"] == "done", f"Bootstrap job failed: {job}"

    # Step 3: Extract project_id from job result
    assert job["result"]["success"] is True, f"Bootstrap result failed: {job['result']}"
    project_id = job["result"]["project"]["project_id"]
    return str(project_id)


def test_cut_audio_sync_worker_async_builds_persisted_result(tmp_path: Path):
    _clear_jobs()
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    reference = bytes([128] * 32 + [250] * 12 + [128] * 24 + [40] * 10 + [128] * 32)
    shifted = bytes([128] * 24) + reference
    (source_dir / "cam_a.wav").write_bytes(reference)
    (source_dir / "rec_b.wav").write_bytes(shifted)

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    # MARKER_QA.BOOTSTRAP_ASYNC_V2: Migrated from sync /api/cut/bootstrap to async pattern
    project_id = _bootstrap_async_and_wait(client, source_dir, sandbox_root, "Audio Sync Demo")

    created = client.post(
        "/api/cut/worker/audio-sync-async",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "limit": 4,
            "sample_bytes": 4096,
            "method": "peaks+correlation",
        },
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["success"] is True
    assert payload["schema_version"] == "cut_mcp_job_v1"

    job = _wait_for_job(client, str(payload["job_id"]))
    assert job["state"] == "done"
    assert job["job_type"] == "audio_sync"
    assert job["result"]["success"] is True
    assert job["result"]["worker_task"]["schema_version"] == "cut_worker_task_v1"
    assert job["result"]["audio_sync_result"]["schema_version"] == "cut_audio_sync_result_v1"
    assert len(job["result"]["audio_sync_result"]["items"]) == 1
    item = job["result"]["audio_sync_result"]["items"][0]
    assert item["method"] in {"peaks+correlation_v1", "correlation_v1", "peak_only_v1"}
    assert abs(item["detected_offset_sec"] - 0.024) <= 0.01

    result_path = sandbox_root / "cut_runtime" / "state" / "audio_sync_result.latest.json"
    assert result_path.exists()
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["schema_version"] == "cut_audio_sync_result_v1"
    assert len(result["items"]) == 1


def test_cut_audio_sync_worker_returns_recoverable_error_for_missing_project(tmp_path: Path):
    _clear_jobs()
    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    response = client.post(
        "/api/cut/worker/audio-sync-async",
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


def test_cut_audio_sync_worker_suppresses_duplicate_active_task(tmp_path: Path, monkeypatch):
    _clear_jobs()
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    signal = bytes([128] * 16 + [220] * 16 + [128] * 32)
    (source_dir / "cam_a.wav").write_bytes(signal)
    (source_dir / "rec_b.wav").write_bytes(bytes([128] * 12) + signal)

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    # MARKER_QA.BOOTSTRAP_ASYNC_V2: Migrated from sync /api/cut/bootstrap to async pattern
    project_id = _bootstrap_async_and_wait(client, source_dir, sandbox_root, "Audio Sync Dup Demo")

    original = cut_module._build_signal_proxy_from_bytes

    def slow_build(path: str, sample_bytes: int):
        time.sleep(0.25)
        return original(path, sample_bytes)

    monkeypatch.setattr(cut_module, "_build_signal_proxy_from_bytes", slow_build)

    first = client.post(
        "/api/cut/worker/audio-sync-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id, "limit": 4, "sample_bytes": 2048},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/cut/worker/audio-sync-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id, "limit": 4, "sample_bytes": 2048},
    )
    assert second.status_code == 200
    payload = second.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "duplicate_job_active"
    assert payload["job"]["job_type"] == "audio_sync"

    _wait_for_job(client, str(first.json()["job_id"]))
