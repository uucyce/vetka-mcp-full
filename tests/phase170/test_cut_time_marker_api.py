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


def test_cut_time_marker_apply_creates_bundle_and_supports_archive(tmp_path: Path):
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
            "project_name": "Marker Demo",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    create_response = client.post(
        "/api/cut/time-markers/apply",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "timeline_id": "main",
            "author": "tester",
            "op": "create",
            "media_path": str(media_path),
            "kind": "favorite",
            "start_sec": 10.0,
            "end_sec": 11.0,
            "anchor_sec": 10.4,
            "score": 0.9,
            "text": "strong beat",
            "context_slice": {"mode": "window", "start_sec": 9.5, "end_sec": 11.5},
        },
    )
    assert create_response.status_code == 200
    create_payload = create_response.json()
    assert create_payload["success"] is True
    assert create_payload["schema_version"] == "cut_time_marker_apply_v1"
    assert create_payload["marker"]["kind"] == "favorite"
    assert create_payload["marker_bundle"]["schema_version"] == "cut_time_marker_bundle_v1"
    assert create_payload["marker_bundle"]["revision"] == 1
    assert create_payload["marker_bundle"]["ranking_summary"]["kind_counts"]["favorite"] == 1
    marker_id = create_payload["marker"]["marker_id"]

    read_response = client.get(
        "/api/cut/time-markers",
        params={"sandbox_root": str(sandbox_root), "project_id": project_id, "timeline_id": "main"},
    )
    assert read_response.status_code == 200
    read_payload = read_response.json()
    assert read_payload["success"] is True
    assert len(read_payload["marker_bundle"]["items"]) == 1
    assert read_payload["marker_bundle"]["items"][0]["marker_id"] == marker_id

    archive_response = client.post(
        "/api/cut/time-markers/apply",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "timeline_id": "main",
            "author": "tester",
            "op": "archive",
            "marker_id": marker_id,
        },
    )
    assert archive_response.status_code == 200
    archive_payload = archive_response.json()
    assert archive_payload["success"] is True
    assert archive_payload["marker"]["status"] == "archived"
    assert archive_payload["marker_bundle"]["revision"] == 2
    assert archive_payload["marker_bundle"]["ranking_summary"]["active_markers"] == 0


def test_cut_time_marker_apply_returns_recoverable_error_for_invalid_marker(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    bootstrap = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Marker Demo",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    response = client.post(
        "/api/cut/time-markers/apply",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "timeline_id": "main",
            "op": "create",
            "media_path": "",
            "kind": "favorite",
            "start_sec": 3.0,
            "end_sec": 2.0,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["schema_version"] == "cut_time_marker_apply_v1"
    assert payload["error"]["code"] == "time_marker_invalid"
    assert payload["error"]["recoverable"] is True


def test_cut_montage_promote_marker_creates_accepted_decision(tmp_path: Path):
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
            "project_name": "Montage Demo",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    marker_response = client.post(
        "/api/cut/time-markers/apply",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "timeline_id": "main",
            "author": "tester",
            "op": "create",
            "media_path": str(media_path),
            "kind": "favorite",
            "start_sec": 10.0,
            "end_sec": 11.0,
            "score": 0.9,
        },
    )
    marker_id = marker_response.json()["marker"]["marker_id"]

    promote_response = client.post(
        "/api/cut/montage/promote-marker",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "marker_id": marker_id,
            "author": "tester",
            "lane_id": "V1",
            "decision_status": "accepted",
            "editorial_intent": "accent_cut",
        },
    )

    assert promote_response.status_code == 200
    payload = promote_response.json()
    assert payload["success"] is True
    assert payload["schema_version"] == "cut_montage_state_v1"
    assert payload["decision"]["status"] == "accepted"
    assert payload["decision"]["cue_provenance_ids"] == [marker_id]
    assert payload["decision"]["source_bundle_id"] == "time_marker_bundle"
    assert payload["montage_state"]["revision"] == 1
    assert payload["montage_state"]["accepted_decisions"][0]["editorial_intent"] == "accent_cut"
    assert payload["montage_state"]["source_bundle_revisions"]["time_marker_bundle"] == 1

    state_response = client.get(
        "/api/cut/project-state",
        params={"sandbox_root": str(sandbox_root), "project_id": project_id},
    )
    state_payload = state_response.json()
    assert state_payload["montage_ready"] is True
    assert state_payload["montage_state"]["accepted_decisions"][0]["decision_id"] == payload["decision"]["decision_id"]


def test_cut_montage_promote_marker_can_move_decision_to_rejected(tmp_path: Path):
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
            "project_name": "Montage Demo",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    marker_response = client.post(
        "/api/cut/time-markers/apply",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "timeline_id": "main",
            "author": "tester",
            "op": "create",
            "media_path": str(media_path),
            "kind": "comment",
            "start_sec": 4.0,
            "end_sec": 5.0,
            "score": 0.6,
        },
    )
    marker_id = marker_response.json()["marker"]["marker_id"]

    decision_id = "decision_marker_01"
    first = client.post(
        "/api/cut/montage/promote-marker",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "marker_id": marker_id,
            "author": "tester",
            "decision_id": decision_id,
            "decision_status": "accepted",
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/api/cut/montage/promote-marker",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "marker_id": marker_id,
            "author": "tester",
            "decision_id": decision_id,
            "decision_status": "rejected",
            "editorial_intent": "commentary_hold",
        },
    )
    payload = second.json()
    assert second.status_code == 200
    assert payload["success"] is True
    assert payload["montage_state"]["revision"] == 2
    assert payload["montage_state"]["accepted_decisions"] == []
    assert payload["montage_state"]["rejected_decisions"][0]["decision_id"] == decision_id
    assert payload["montage_state"]["rejected_decisions"][0]["status"] == "rejected"
