import pytest
import json
import time
from pathlib import Path

pytestmark = pytest.mark.stale(reason="CUT API refactored — bootstrap/project_state contracts changed")

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


def test_cut_waveform_worker_async_builds_persisted_bundle(tmp_path: Path):
    _clear_jobs()
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "clip_a.mp4").write_bytes(bytes(range(64)) * 4)
    (source_dir / "audio_a.wav").write_bytes(bytes(reversed(range(64))) * 4)

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    bootstrap = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Wave Demo",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    created = client.post(
        "/api/cut/worker/waveform-build-async",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "bins": 32,
            "limit": 8,
        },
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["success"] is True
    assert payload["schema_version"] == "cut_mcp_job_v1"

    job = _wait_for_job(client, str(payload["job_id"]))
    assert job["state"] == "done"
    assert job["job_type"] == "waveform_build"
    assert job["result"]["success"] is True
    assert job["result"]["worker_task"]["schema_version"] == "cut_worker_task_v1"
    assert job["result"]["waveform_bundle"]["schema_version"] == "cut_waveform_bundle_v1"
    assert len(job["result"]["waveform_bundle"]["items"]) == 2

    bundle_path = sandbox_root / "cut_runtime" / "state" / "waveform_bundle.latest.json"
    assert bundle_path.exists()
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert bundle["schema_version"] == "cut_waveform_bundle_v1"
    assert len(bundle["items"]) == 2
    assert len(bundle["items"][0]["waveform_bins"]) == 32


def test_cut_waveform_worker_returns_recoverable_error_for_missing_project(tmp_path: Path):
    _clear_jobs()
    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    response = client.post(
        "/api/cut/worker/waveform-build-async",
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


def test_cut_waveform_worker_suppresses_duplicate_active_task(tmp_path: Path, monkeypatch):
    _clear_jobs()
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "clip_a.mp4").write_bytes(bytes(range(64)) * 8)

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    bootstrap = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Dup Demo",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    original = cut_module._build_waveform_proxy_from_bytes

    def slow_build(path: str, bins: int):
        time.sleep(0.25)
        return original(path, bins)

    monkeypatch.setattr(cut_module, "_build_waveform_proxy_from_bytes", slow_build)

    first = client.post(
        "/api/cut/worker/waveform-build-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id, "bins": 32, "limit": 8},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/cut/worker/waveform-build-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id, "bins": 32, "limit": 8},
    )
    assert second.status_code == 200
    payload = second.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "duplicate_job_active"
    assert payload["job"]["job_type"] == "waveform_build"

    _wait_for_job(client, str(first.json()["job_id"]))


def test_cut_worker_backpressure_blocks_third_active_background_job(tmp_path: Path, monkeypatch):
    _clear_jobs()
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "clip_a.mp4").write_bytes(bytes(range(64)) * 8)
    (source_dir / "audio_a.wav").write_bytes(bytes(reversed(range(64))) * 8)

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    bootstrap = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Backpressure Demo",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    original_waveform = cut_module._build_waveform_proxy_from_bytes
    original_timeline = cut_module._build_initial_timeline_state

    def slow_waveform(path: str, bins: int):
        time.sleep(0.25)
        return original_waveform(path, bins)

    def slow_timeline(project: dict, timeline_id: str):
        time.sleep(0.25)
        return original_timeline(project, timeline_id)

    monkeypatch.setattr(cut_module, "_build_waveform_proxy_from_bytes", slow_waveform)
    monkeypatch.setattr(cut_module, "_build_initial_timeline_state", slow_timeline)

    first = client.post(
        "/api/cut/worker/waveform-build-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id, "bins": 32, "limit": 8},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/cut/scene-assembly-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id, "timeline_id": "alt"},
    )
    assert second.status_code == 200
    assert second.json()["success"] is True

    third = client.post(
        "/api/cut/worker/waveform-build-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id, "bins": 32, "limit": 8},
    )
    assert third.status_code == 200
    payload = third.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "worker_backpressure_limit"

    _wait_for_job(client, str(first.json()["job_id"]))
    _wait_for_job(client, str(second.json()["job_id"]))
