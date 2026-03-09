import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.cut_routes import router
from src.services.cut_project_store import CutProjectStore


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


def test_cut_bootstrap_creates_project_and_persists_state(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "clip.mp4").write_bytes(b"00")
    (source_dir / "script.md").write_text("Opening scene", encoding="utf-8")

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)

    client = _make_client()
    resp = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Demo Cut",
            "mode": "create_or_open",
            "quick_scan_limit": 5000,
            "use_core_mirror": True,
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"] is True
    assert payload["schema_version"] == "cut_bootstrap_v1"
    assert payload["project"]["schema_version"] == "cut_project_v1"
    assert payload["stats"]["media_files"] >= 1
    assert payload["missing_inputs"]["script_or_treatment"] is False

    project_path = sandbox_root / "config" / "cut_project.json"
    bootstrap_state_path = sandbox_root / "config" / "cut_bootstrap_state.json"
    assert project_path.exists()
    assert bootstrap_state_path.exists()

    project = json.loads(project_path.read_text(encoding="utf-8"))
    assert project["display_name"] == "Demo Cut"
    assert project["state"] == "ready"


def test_cut_bootstrap_reopens_existing_project_in_create_or_open_mode(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "clip.mov").write_bytes(b"00")

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)

    client = _make_client()
    first = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Demo Cut",
        },
    )
    first_payload = first.json()
    first_project_id = first_payload["project"]["project_id"]

    second = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Renamed But Reopen",
            "mode": "create_or_open",
        },
    )
    second_payload = second.json()
    assert second_payload["success"] is True
    assert second_payload["project"]["project_id"] == first_project_id

    store = CutProjectStore(str(sandbox_root))
    persisted = store.load_project()
    assert persisted is not None
    assert persisted["project_id"] == first_project_id


def test_cut_bootstrap_returns_recoverable_error_when_sandbox_missing(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "clip.mp4").write_bytes(b"00")

    client = _make_client()
    resp = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(tmp_path / 'missing_sandbox'),
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "sandbox_missing"
    assert payload["degraded_mode"] is True
