import json
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


def _wait_for_job(client: TestClient, job_id: str) -> dict:
    for _ in range(20):
        response = client.get(f"/api/cut/job/{job_id}")
        job = response.json()["job"]
        if job["state"] in {"done", "error"}:
            return job
        time.sleep(0.05)
    raise AssertionError(f"job did not finish: {job_id}")


def test_cut_timeline_apply_updates_revision_and_persists_edit_log(tmp_path: Path):
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
            "project_name": "Edit Demo",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]
    scene_job = client.post(
        "/api/cut/scene-assembly-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id},
    )
    _wait_for_job(client, scene_job.json()["job_id"])

    response = client.post(
        "/api/cut/timeline/apply",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "timeline_id": "main",
            "author": "test_agent",
            "ops": [
                {"op": "set_selection", "clip_ids": ["clip_0002"], "scene_ids": ["scene_01"]},
                {"op": "set_view", "zoom": 2.0, "scroll_sec": 4.5, "active_lane_id": "audio_sync"},
                {"op": "move_clip", "clip_id": "clip_0002", "lane_id": "audio_sync", "start_sec": 9.0},
                {"op": "trim_clip", "clip_id": "clip_0002", "duration_sec": 3.5, "start_sec": 9.5},
            ],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["schema_version"] == "cut_timeline_apply_v1"
    assert payload["timeline_state"]["revision"] == 2
    assert payload["timeline_state"]["selection"]["clip_ids"] == ["clip_0002"]
    assert payload["timeline_state"]["view"]["active_lane_id"] == "audio_sync"

    audio_lane = next(
        lane for lane in payload["timeline_state"]["lanes"] if lane["lane_id"] == "audio_sync"
    )
    moved_clip = next(clip for clip in audio_lane["clips"] if clip["clip_id"] == "clip_0002")
    assert moved_clip["start_sec"] == 9.5
    assert moved_clip["duration_sec"] == 3.5

    timeline_path = sandbox_root / "cut_runtime" / "state" / "timeline_state.latest.json"
    persisted_timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    assert persisted_timeline["revision"] == 2

    log_path = sandbox_root / "cut_runtime" / "state" / "timeline_edit_log.jsonl"
    assert log_path.exists()
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(events) == 1
    assert events[0]["author"] == "test_agent"
    assert events[0]["op_count"] == 4


def test_cut_timeline_apply_supports_sync_offset_op(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "clip_a_tc_01-00-00-00.mp4").write_bytes(b"00")
    (source_dir / "audio_a_tc_01-00-00-12.wav").write_bytes(b"00")

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    bootstrap = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Sync Edit Demo",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]
    scene_job = client.post(
        "/api/cut/scene-assembly-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id},
    )
    _wait_for_job(client, scene_job.json()["job_id"])

    response = client.post(
        "/api/cut/timeline/apply",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "timeline_id": "main",
            "author": "sync_agent",
            "ops": [
                {
                    "op": "apply_sync_offset",
                    "clip_id": "clip_0001",
                    "offset_sec": 0.48,
                    "method": "timecode",
                    "confidence": 0.99,
                    "reference_path": str(source_dir / "clip_a_tc_01-00-00-00.mp4"),
                    "source": "sync_surface",
                    "group_id": "sync_group_main",
                }
            ],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["timeline_state"]["revision"] == 2

    audio_lane = next(lane for lane in payload["timeline_state"]["lanes"] if lane["lane_id"] == "audio_sync")
    synced_clip = next(clip for clip in audio_lane["clips"] if clip["clip_id"] == "clip_0001")
    assert synced_clip["start_sec"] == 0.48
    assert synced_clip["sync"]["method"] == "timecode"
    assert synced_clip["sync"]["offset_sec"] == 0.48
    assert synced_clip["sync"]["confidence"] == 0.99

    assert payload["timeline_state"]["sync_groups"][0]["group_id"] == "sync_group_main"
    assert payload["timeline_state"]["sync_groups"][0]["method"] == "timecode"


def test_cut_timeline_apply_returns_recoverable_error_when_timeline_missing(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "clip_a.mp4").write_bytes(b"00")

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    bootstrap = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Edit Demo",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    # B65 now creates timeline_state during bootstrap.
    # Remove it to test the timeline_not_ready guard path.
    timeline_file = sandbox_root / "cut_runtime" / "state" / "timeline_state.latest.json"
    if timeline_file.exists():
        timeline_file.unlink()

    response = client.post(
        "/api/cut/timeline/apply",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "ops": [{"op": "set_selection", "clip_ids": ["clip_0001"]}],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["schema_version"] == "cut_timeline_apply_v1"
    assert payload["error"]["code"] == "timeline_not_ready"
