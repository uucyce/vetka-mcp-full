import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.cut_routes import router


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


def test_cut_bootstrap_async_job_lifecycle(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "clip.mp4").write_bytes(b"00")

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)

    client = _make_client()
    created = client.post(
        "/api/cut/bootstrap-async",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Async Demo",
        },
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["success"] is True
    assert payload["schema_version"] == "cut_mcp_job_v1"
    job_id = str(payload["job_id"])
    assert job_id

    terminal = None
    for _ in range(20):
        status = client.get(f"/api/cut/bootstrap-job/{job_id}")
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
    assert terminal["result"]["project"]["schema_version"] == "cut_project_v1"


def test_cut_bootstrap_async_unknown_job_returns_404():
    client = _make_client()
    status = client.get("/api/cut/bootstrap-job/does-not-exist")
    assert status.status_code == 404
