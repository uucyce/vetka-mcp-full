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


def test_cut_pause_slice_worker_async_builds_persisted_bundle(tmp_path: Path):
    _clear_jobs()
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    signal = bytes([190] * 1000 + [128] * 400 + [205] * 1200)
    (source_dir / "audio_a.wav").write_bytes(signal)
    (source_dir / "audio_b.wav").write_bytes(signal)

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    bootstrap = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Pause Slice Demo",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    created = client.post(
        "/api/cut/worker/pause-slice-async",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "limit": 4,
            "sample_bytes": 4096,
            "frame_ms": 20,
            "silence_threshold": 0.08,
            "min_silence_ms": 250,
            "keep_silence_ms": 80,
        },
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["success"] is True
    assert payload["schema_version"] == "cut_mcp_job_v1"

    job = _wait_for_job(client, str(payload["job_id"]))
    assert job["state"] == "done"
    assert job["job_type"] == "pause_slice"
    assert job["result"]["success"] is True
    assert job["result"]["worker_task"]["schema_version"] == "cut_worker_task_v1"
    assert job["result"]["slice_bundle"]["schema_version"] == "cut_slice_bundle_v1"
    assert len(job["result"]["slice_bundle"]["items"]) == 2
    first_item = job["result"]["slice_bundle"]["items"][0]
    assert first_item["method"] == "energy_pause_v1"
    assert len(first_item["windows"]) >= 2

    bundle_path = sandbox_root / "cut_runtime" / "state" / "slice_bundle.latest.json"
    assert bundle_path.exists()
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert bundle["schema_version"] == "cut_slice_bundle_v1"
    assert len(bundle["items"]) == 2


def test_cut_pause_slice_worker_returns_recoverable_error_for_missing_project(tmp_path: Path):
    _clear_jobs()
    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    response = client.post(
        "/api/cut/worker/pause-slice-async",
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


def test_cut_pause_slice_worker_suppresses_duplicate_active_task(tmp_path: Path, monkeypatch):
    _clear_jobs()
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    signal = bytes([200] * 1000 + [128] * 300 + [210] * 1100)
    (source_dir / "audio_a.wav").write_bytes(signal)
    (source_dir / "audio_b.wav").write_bytes(signal)

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    bootstrap = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Pause Slice Dup Demo",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    original = cut_module._build_signal_proxy_from_bytes

    def slow_build(path: str, sample_bytes: int):
        time.sleep(0.25)
        return original(path, sample_bytes)

    monkeypatch.setattr(cut_module, "_build_signal_proxy_from_bytes", slow_build)

    first = client.post(
        "/api/cut/worker/pause-slice-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id, "limit": 4, "sample_bytes": 4096},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/cut/worker/pause-slice-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id, "limit": 4, "sample_bytes": 4096},
    )
    assert second.status_code == 200
    payload = second.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "duplicate_job_active"
    assert payload["job"]["job_type"] == "pause_slice"

    _wait_for_job(client, str(first.json()["job_id"]))
