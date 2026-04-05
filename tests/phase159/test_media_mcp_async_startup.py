import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.artifact_routes import router


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_phase159_media_startup_async_job_lifecycle(tmp_path: Path):
    media_dir = tmp_path / "media_scope"
    media_dir.mkdir(parents=True, exist_ok=True)
    (media_dir / "clip.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")

    client = _make_client()
    created = client.post(
        "/api/artifacts/media/startup-async",
        json={"scope_path": str(media_dir), "quick_scan_limit": 5000},
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["success"] is True
    assert payload["schema_version"] == "media_mcp_job_v1"
    job_id = str(payload["job_id"])
    assert job_id

    # Background task may complete quickly in test runtime; poll status deterministically.
    terminal = None
    for _ in range(10):
        status = client.get(f"/api/artifacts/media/startup-job/{job_id}")
        assert status.status_code == 200
        job = status.json()["job"]
        if job["state"] in {"done", "error"}:
            terminal = job
            break
        time.sleep(0.05)

    assert terminal is not None
    assert terminal["state"] == "done"
    assert float(terminal["progress"]) == 1.0
    assert terminal["result"]["success"] is True
    assert terminal["result"]["stats"]["media_files"] >= 1


def test_phase159_media_startup_async_unknown_job_returns_404():
    client = _make_client()
    status = client.get("/api/artifacts/media/startup-job/does-not-exist")
    assert status.status_code == 404

