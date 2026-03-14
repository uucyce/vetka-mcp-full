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


def test_cut_thumbnail_worker_async_builds_persisted_bundle(tmp_path: Path, monkeypatch):
    _clear_jobs()
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "clip_a.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    (source_dir / "audio_a.wav").write_bytes(b"RIFF....WAVEfmt ")

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    async def _fake_media_preview(body, request):
        return {
            "success": True,
            "path": body.path,
            "modality": "video" if str(body.path).endswith(".mp4") else "audio",
            "duration_sec": 5.0,
            "preview_assets": {
                "poster_url": f"/api/files/raw?path={body.path}.poster.jpg",
                "animated_preview_url_300ms": f"/api/files/raw?path={body.path}.preview.webp",
            },
            "playback": {"source_url": f"/api/files/raw?path={body.path}"},
            "degraded_mode": False,
            "degraded_reason": "",
        }

    monkeypatch.setattr(cut_module, "media_preview", _fake_media_preview)

    bootstrap = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Thumb Demo",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    created = client.post(
        "/api/cut/worker/thumbnail-build-async",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "limit": 8,
            "waveform_bins": 32,
            "preview_segments_limit": 16,
        },
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["success"] is True
    assert payload["schema_version"] == "cut_mcp_job_v1"

    job = _wait_for_job(client, str(payload["job_id"]))
    assert job["state"] == "done"
    assert job["job_type"] == "thumbnail_build"
    assert job["result"]["success"] is True
    assert job["result"]["worker_task"]["schema_version"] == "cut_worker_task_v1"
    assert job["result"]["thumbnail_bundle"]["schema_version"] == "cut_thumbnail_bundle_v1"
    assert len(job["result"]["thumbnail_bundle"]["items"]) == 2

    bundle_path = sandbox_root / "cut_runtime" / "state" / "thumbnail_bundle.latest.json"
    assert bundle_path.exists()
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert bundle["schema_version"] == "cut_thumbnail_bundle_v1"
    assert len(bundle["items"]) == 2
    assert bundle["items"][0]["source_url"].startswith("/api/files/raw?path=")


def test_cut_thumbnail_worker_returns_recoverable_error_for_missing_project(tmp_path: Path):
    _clear_jobs()
    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    response = client.post(
        "/api/cut/worker/thumbnail-build-async",
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
