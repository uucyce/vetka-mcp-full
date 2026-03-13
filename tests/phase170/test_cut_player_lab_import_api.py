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


def test_cut_import_player_lab_markers_imports_markers_and_provisional_events(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    media_path = source_dir / "clip_a.mp4"
    media_path.write_bytes(b"00")

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    bootstrap = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Player Lab Import Demo",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    response = client.post(
        "/api/cut/markers/import-player-lab",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "timeline_id": "main",
            "markers": [
                {
                    "marker_id": "player_marker_001",
                    "media_path": str(media_path),
                    "kind": "favorite",
                    "start_sec": 3.0,
                    "end_sec": 4.0,
                    "score": 0.85,
                    "label": "Starred moment",
                    "text": "nice beat",
                    "source_engine": "player_lab",
                }
            ],
            "provisional_events": [
                {
                    "provisional_event_id": "prov_001",
                    "media_path": str(media_path),
                    "start_sec": 6.0,
                    "end_sec": 6.8,
                    "text": "Moment registered locally.",
                    "event_type": "vetka_logo_capture",
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["schema_version"] == "cut_player_lab_marker_import_v1"
    assert payload["imported_count"] == 2
    assert payload["skipped_duplicates"] == 0
    assert payload["kind_counts"] == {"favorite": 1, "comment": 1}
    assert payload["marker_bundle"]["revision"] == 1

    read_response = client.get(
        "/api/cut/time-markers",
        params={"sandbox_root": str(sandbox_root), "project_id": project_id, "timeline_id": "main"},
    )
    items = read_response.json()["marker_bundle"]["items"]
    assert len(items) == 2
    assert {item["marker_id"] for item in items} == {"player_marker_001", "prov_001"}


def test_cut_import_player_lab_markers_skips_duplicate_marker_ids(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    media_path = source_dir / "clip_a.mp4"
    media_path.write_bytes(b"00")

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    bootstrap = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Player Lab Import Duplicate Demo",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    body = {
        "sandbox_root": str(sandbox_root),
        "project_id": project_id,
        "timeline_id": "main",
        "markers": [
            {
                "marker_id": "player_marker_dup",
                "media_path": str(media_path),
                "kind": "favorite",
                "start_sec": 1.0,
                "end_sec": 1.4,
            }
        ],
    }
    first = client.post("/api/cut/markers/import-player-lab", json=body)
    second = client.post("/api/cut/markers/import-player-lab", json=body)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["imported_count"] == 1
    assert second.json()["imported_count"] == 0
    assert second.json()["skipped_duplicates"] == 1
