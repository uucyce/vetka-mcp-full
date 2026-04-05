import json
import time
import wave
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
    for _ in range(100):
        response = client.get(f"/api/cut/job/{job_id}")
        job = response.json()["job"]
        if job["state"] in {"done", "error", "cancelled"}:
            return job
        time.sleep(0.05)
    raise AssertionError(f"job did not finish: {job_id}")


def _clear_jobs() -> None:
    get_cut_mcp_job_store().clear()


def _write_punch_track_wav(path: Path, *, sample_rate: int = 8000, bpm: float = 124.0, duration_sec: float = 6.0) -> None:
    frame_count = int(sample_rate * duration_sec)
    samples = [0 for _ in range(frame_count)]
    beat_interval = max(1, int(sample_rate * (60.0 / bpm)))
    for anchor in range(0, frame_count, beat_interval):
        for offset in range(int(sample_rate * 0.015)):
            idx = anchor + offset
            if idx >= frame_count:
                break
            samples[idx] = 24000 if offset % 2 == 0 else -24000
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"".join(int(sample).to_bytes(2, byteorder="little", signed=True) for sample in samples))


def test_cut_music_sync_worker_async_builds_persisted_result(tmp_path: Path):
    _clear_jobs()
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    punch_track = source_dir / "250623_vanpticdanyana_berlin_Punch.wav"
    _write_punch_track_wav(punch_track)

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    bootstrap = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Music Sync Demo",
            "bootstrap_profile": "berlin_fixture_v1",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    created = client.post(
        "/api/cut/worker/music-sync-async",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "music_path": str(punch_track),
            "bpm_hint": 124.0,
        },
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["success"] is True
    assert payload["schema_version"] == "cut_mcp_job_v1"

    job = _wait_for_job(client, str(payload["job_id"]))
    assert job["state"] == "done"
    assert job["job_type"] == "music_sync"
    assert job["result"]["success"] is True
    assert job["result"]["worker_task"]["schema_version"] == "cut_worker_task_v1"
    result = job["result"]["music_sync_result"]
    assert result["schema_version"] == "cut_music_sync_result_v1"
    assert result["music_path"] == str(punch_track)
    assert 110.0 <= result["tempo"]["bpm"] <= 140.0
    assert result["tempo"]["confidence"] > 0.0
    assert len(result["downbeats"]) >= 1
    assert len(result["cue_points"]) >= 1

    result_path = sandbox_root / "cut_runtime" / "state" / "music_sync_result.latest.json"
    assert result_path.exists()
    persisted = json.loads(result_path.read_text(encoding="utf-8"))
    assert persisted["schema_version"] == "cut_music_sync_result_v1"
    assert persisted["cue_points"][0]["cue_id"].startswith("cue_")


def test_cut_music_sync_worker_returns_recoverable_error_for_missing_project(tmp_path: Path):
    _clear_jobs()
    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    response = client.post(
        "/api/cut/worker/music-sync-async",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": "missing_project",
            "music_path": str(tmp_path / "missing.wav"),
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["schema_version"] == "cut_mcp_job_v1"
    assert payload["error"]["code"] == "project_not_found"


def test_cut_music_sync_worker_suppresses_duplicate_active_task(tmp_path: Path, monkeypatch):
    _clear_jobs()
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    punch_track = source_dir / "250623_vanpticdanyana_berlin_Punch.wav"
    _write_punch_track_wav(punch_track, duration_sec=8.0)

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    bootstrap = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Music Sync Dup Demo",
            "bootstrap_profile": "berlin_fixture_v1",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    original = cut_module._analyze_music_track

    def slow_analyze(*, path: str, bpm_hint: float | None, max_analysis_sec: int):
        time.sleep(0.25)
        return original(path=path, bpm_hint=bpm_hint, max_analysis_sec=max_analysis_sec)

    monkeypatch.setattr(cut_module, "_analyze_music_track", slow_analyze)

    first = client.post(
        "/api/cut/worker/music-sync-async",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "music_path": str(punch_track),
            "bpm_hint": 124.0,
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/api/cut/worker/music-sync-async",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "music_path": str(punch_track),
            "bpm_hint": 124.0,
        },
    )
    assert second.status_code == 200
    payload = second.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "duplicate_job_active"
    assert payload["job"]["job_type"] == "music_sync"

    _wait_for_job(client, str(first.json()["job_id"]))
