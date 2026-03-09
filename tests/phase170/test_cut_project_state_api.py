import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import cut_routes as cut_module
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


def _wait_for_job(client: TestClient, job_id: str) -> dict:
    for _ in range(20):
        status = client.get(f"/api/cut/job/{job_id}")
        job = status.json()["job"]
        if job["state"] in {"done", "error", "cancelled"}:
            return job
        time.sleep(0.05)
    raise AssertionError(f"job did not finish: {job_id}")


def test_cut_project_state_returns_project_bootstrap_timeline_and_graph(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "clip_a.mp4").write_bytes(b"00")
    (source_dir / "audio_a.wav").write_bytes(b"00")

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    bootstrap = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "State Demo",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    job_created = client.post(
        "/api/cut/scene-assembly-async",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
        },
    )
    job_id = job_created.json()["job_id"]

    _wait_for_job(client, job_id)

    response = client.get(
        "/api/cut/project-state",
        params={"sandbox_root": str(sandbox_root), "project_id": project_id},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["schema_version"] == "cut_project_state_v1"
    assert payload["project"]["project_id"] == project_id
    assert payload["bootstrap_state"]["project_id"] == project_id
    assert payload["bootstrap_state"]["last_job_id"] == job_id
    assert payload["timeline_state"]["schema_version"] == "cut_timeline_state_v1"
    assert payload["scene_graph"]["schema_version"] == "cut_scene_graph_v1"
    assert payload["runtime_ready"] is True
    assert payload["graph_ready"] is True
    assert payload["waveform_bundle"] is None
    assert payload["transcript_bundle"] is None
    assert payload["thumbnail_bundle"] is None
    assert payload["time_marker_bundle"] is None
    assert payload["waveform_ready"] is False
    assert payload["transcript_ready"] is False
    assert payload["thumbnail_ready"] is False
    assert payload["time_markers_ready"] is False
    assert len(payload["recent_jobs"]) == 1
    assert payload["recent_jobs"][0]["job_id"] == job_id
    assert payload["recent_jobs"][0]["job_type"] == "scene_assembly"
    assert payload["active_jobs"] == []


def test_cut_project_state_returns_worker_bundles_when_ready(tmp_path: Path, monkeypatch):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "clip_a.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    (source_dir / "audio_a.wav").write_bytes(b"RIFF....WAVEfmt ")

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    async def _fake_transcript_success(body, request):
        return {
            "success": True,
            "transcript_normalized_json": {
                "schema_version": "vetka_transcript_v1",
                "path": body.path,
                "modality": "audio",
                "language": "en",
                "duration_sec": 12.0,
                "source_engine": "mlx_whisper",
                "text": "hello",
                "segments": [{"start": 0.0, "end": 0.4, "text": "hello"}],
            },
            "degraded_mode": False,
            "degraded_reason": "",
        }

    monkeypatch.setattr(cut_module, "media_transcript_normalized", _fake_transcript_success)

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
            "project_name": "State Bundle Demo",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    waveform_job = client.post(
        "/api/cut/worker/waveform-build-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id, "bins": 32, "limit": 8},
    ).json()["job_id"]
    marker_response = client.post(
        "/api/cut/time-markers/apply",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "timeline_id": "main",
            "media_path": str(source_dir / "clip_a.mp4"),
            "kind": "favorite",
            "start_sec": 1.25,
            "end_sec": 2.1,
            "score": 0.95,
        },
    )
    assert marker_response.status_code == 200
    assert marker_response.json()["success"] is True
    transcript_job = client.post(
        "/api/cut/worker/transcript-normalize-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id, "limit": 4, "segments_limit": 32},
    ).json()["job_id"]
    thumbnail_job = client.post(
        "/api/cut/worker/thumbnail-build-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id, "limit": 4, "waveform_bins": 32, "preview_segments_limit": 16},
    ).json()["job_id"]

    _wait_for_job(client, waveform_job)
    _wait_for_job(client, transcript_job)
    _wait_for_job(client, thumbnail_job)

    response = client.get(
        "/api/cut/project-state",
        params={"sandbox_root": str(sandbox_root), "project_id": project_id},
    )
    payload = response.json()
    assert payload["success"] is True
    assert payload["waveform_bundle"]["schema_version"] == "cut_waveform_bundle_v1"
    assert payload["transcript_bundle"]["schema_version"] == "cut_transcript_bundle_v1"
    assert payload["thumbnail_bundle"]["schema_version"] == "cut_thumbnail_bundle_v1"
    assert payload["time_marker_bundle"]["schema_version"] == "cut_time_marker_bundle_v1"
    assert payload["waveform_ready"] is True
    assert payload["transcript_ready"] is True
    assert payload["thumbnail_ready"] is True
    assert payload["time_markers_ready"] is True
    assert len(payload["waveform_bundle"]["items"]) == 2
    assert len(payload["transcript_bundle"]["items"]) == 2
    assert len(payload["thumbnail_bundle"]["items"]) == 2
    assert len(payload["time_marker_bundle"]["items"]) == 1
    assert len(payload["recent_jobs"]) >= 2
    job_types = {job["job_type"] for job in payload["recent_jobs"]}
    assert "waveform_build" in job_types
    assert "transcript_normalize" in job_types
    assert "thumbnail_build" in job_types
    assert payload["active_jobs"] == []


def test_cut_project_state_returns_recoverable_error_for_missing_project(tmp_path: Path):
    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    response = client.get(
        "/api/cut/project-state",
        params={"sandbox_root": str(sandbox_root), "project_id": "missing_project"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["schema_version"] == "cut_project_state_v1"
    assert payload["error"]["code"] == "project_not_found"
    assert payload["error"]["recoverable"] is True
