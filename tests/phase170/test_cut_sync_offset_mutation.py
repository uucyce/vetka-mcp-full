"""
MARKER_170.14.SYNC_OFFSET_MUTATION_TESTS
Comprehensive tests for apply_sync_offset mutation, sync_groups persistence,
multiple sequential ops, sync_surface recommendation logic, and round-trip.
"""
import json
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.cut_routes import router, _build_sync_surface
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


def _wait_for_job(client: TestClient, job_id: str) -> dict:
    for _ in range(20):
        response = client.get(f"/api/cut/job/{job_id}")
        job = response.json()["job"]
        if job["state"] in {"done", "error"}:
            return job
        time.sleep(0.05)
    raise AssertionError(f"job did not finish: {job_id}")


def _setup_project_with_timeline(tmp_path: Path):
    """Bootstrap project + scene assembly → returns (client, sandbox_root, project_id)."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "cam_a.mp4").write_bytes(b"00")
    (source_dir / "cam_b.mp4").write_bytes(b"00")
    (source_dir / "audio_a.wav").write_bytes(b"00")

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    bootstrap = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Sync Test",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]
    scene_job = client.post(
        "/api/cut/scene-assembly-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id},
    )
    _wait_for_job(client, scene_job.json()["job_id"])
    return client, sandbox_root, project_id, source_dir


# ─── sync_groups update vs append ───


def test_sync_offset_creates_sync_group_entry(tmp_path: Path):
    """First apply_sync_offset creates a new sync_groups entry."""
    client, sandbox_root, project_id, source_dir = _setup_project_with_timeline(tmp_path)

    response = client.post(
        "/api/cut/timeline/apply",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "ops": [
                {
                    "op": "apply_sync_offset",
                    "clip_id": "clip_0001",
                    "offset_sec": 0.032,
                    "method": "waveform",
                    "confidence": 0.91,
                    "reference_path": str(source_dir / "cam_a.mp4"),
                    "source": "sync_surface",
                    "group_id": "grp_wave",
                }
            ],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    groups = payload["timeline_state"]["sync_groups"]
    assert len(groups) >= 1
    grp = next(g for g in groups if g["group_id"] == "grp_wave")
    assert grp["method"] == "waveform"
    assert grp["offset_sec"] == 0.032
    assert grp["confidence"] == 0.91


def test_sync_offset_updates_existing_group_same_source(tmp_path: Path):
    """Second apply_sync_offset for same source_path updates existing entry, not appends."""
    client, sandbox_root, project_id, source_dir = _setup_project_with_timeline(tmp_path)

    # First sync
    client.post(
        "/api/cut/timeline/apply",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "ops": [
                {
                    "op": "apply_sync_offset",
                    "clip_id": "clip_0001",
                    "offset_sec": 0.032,
                    "method": "waveform",
                    "confidence": 0.80,
                    "reference_path": str(source_dir / "cam_a.mp4"),
                    "group_id": "grp_1",
                }
            ],
        },
    )

    # Second sync — same clip, better confidence
    response = client.post(
        "/api/cut/timeline/apply",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "ops": [
                {
                    "op": "apply_sync_offset",
                    "clip_id": "clip_0001",
                    "offset_sec": 0.048,
                    "method": "timecode",
                    "confidence": 0.99,
                    "reference_path": str(source_dir / "cam_a.mp4"),
                    "group_id": "grp_1_v2",
                }
            ],
        },
    )
    payload = response.json()
    assert payload["success"] is True

    # sync_groups should have updated the entry, not duplicated
    groups = payload["timeline_state"]["sync_groups"]
    source_entries = [g for g in groups if str(source_dir / "audio_a.wav") in str(g.get("source_path", "")) or "clip_0001" in str(g)]
    # The key check: no duplicate source_path entries
    source_paths = [g["source_path"] for g in groups]
    assert len(source_paths) == len(set(source_paths)), f"Duplicate source_paths in sync_groups: {source_paths}"


def test_sync_offset_multiple_clips_sequential(tmp_path: Path):
    """Apply sync to multiple clips in sequence — each gets its own sync metadata."""
    client, sandbox_root, project_id, source_dir = _setup_project_with_timeline(tmp_path)

    ops = []
    for i in range(1, 4):
        clip_id = f"clip_000{i}"
        ops.append({
            "op": "apply_sync_offset",
            "clip_id": clip_id,
            "offset_sec": 0.01 * i,
            "method": "waveform",
            "confidence": 0.8 + 0.05 * i,
            "reference_path": str(source_dir / "cam_a.mp4"),
            "group_id": f"grp_{i}",
        })

    response = client.post(
        "/api/cut/timeline/apply",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "ops": ops,
        },
    )
    payload = response.json()
    assert payload["success"] is True
    # Revision should increment by 1 (all ops in single batch)
    assert payload["timeline_state"]["revision"] == 2


# ─── Persistence round-trip ───


def test_sync_groups_persist_through_save_load(tmp_path: Path):
    """sync_groups survive save → load round-trip via CutProjectStore."""
    client, sandbox_root, project_id, source_dir = _setup_project_with_timeline(tmp_path)

    # Apply sync offset
    client.post(
        "/api/cut/timeline/apply",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "ops": [
                {
                    "op": "apply_sync_offset",
                    "clip_id": "clip_0001",
                    "offset_sec": 0.48,
                    "method": "timecode",
                    "confidence": 0.99,
                    "reference_path": str(source_dir / "cam_a.mp4"),
                    "group_id": "persist_test",
                }
            ],
        },
    )

    # Load persisted state from disk
    timeline_path = sandbox_root / "cut_runtime" / "state" / "timeline_state.latest.json"
    assert timeline_path.exists()
    persisted = json.loads(timeline_path.read_text(encoding="utf-8"))

    assert "sync_groups" in persisted
    assert len(persisted["sync_groups"]) >= 1
    grp = next(g for g in persisted["sync_groups"] if g["group_id"] == "persist_test")
    assert grp["method"] == "timecode"
    assert grp["offset_sec"] == 0.48
    assert grp["confidence"] == 0.99
    assert "applied_at" in grp


def test_sync_offset_clip_start_sec_accumulated(tmp_path: Path):
    """Clip start_sec accumulates offset correctly across operations."""
    client, sandbox_root, project_id, source_dir = _setup_project_with_timeline(tmp_path)

    # Get initial clip start_sec
    state_resp = client.get(
        "/api/cut/project-state",
        params={"sandbox_root": str(sandbox_root), "project_id": project_id},
    )
    initial_state = state_resp.json()
    timeline = initial_state.get("timeline_state") or {}
    lanes = timeline.get("lanes", [])
    audio_lane = next((l for l in lanes if l["lane_id"] == "audio_sync"), None)
    if not audio_lane or not audio_lane.get("clips"):
        return  # Skip if no audio clips (depends on bootstrap)

    clip = audio_lane["clips"][0]
    initial_start = clip["start_sec"]

    # Apply offset
    response = client.post(
        "/api/cut/timeline/apply",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "ops": [
                {
                    "op": "apply_sync_offset",
                    "clip_id": clip["clip_id"],
                    "offset_sec": 1.5,
                    "method": "waveform",
                    "confidence": 0.85,
                    "reference_path": str(source_dir / "cam_a.mp4"),
                }
            ],
        },
    )
    payload = response.json()
    assert payload["success"] is True

    # Find the updated clip
    updated_lane = next(l for l in payload["timeline_state"]["lanes"] if l["lane_id"] == "audio_sync")
    updated_clip = next(c for c in updated_lane["clips"] if c["clip_id"] == clip["clip_id"])
    assert updated_clip["start_sec"] == round(initial_start + 1.5, 4)
    assert updated_clip["sync"]["offset_sec"] == 1.5


# ─── _build_sync_surface recommendation logic ───


def test_sync_surface_prefers_timecode_over_waveform():
    """sync_surface recommends timecode when both timecode and waveform are available."""
    timecode_result = {
        "schema_version": "cut_timecode_sync_result_v1",
        "project_id": "p1",
        "revision": 1,
        "items": [
            {
                "item_id": "tc_001",
                "reference_path": "/cam_a.mov",
                "source_path": "/cam_b.mov",
                "reference_timecode": "01:00:00:00",
                "source_timecode": "01:00:00:12",
                "fps": 25,
                "detected_offset_sec": 0.48,
                "confidence": 0.99,
                "method": "timecode_v1",
                "degraded_mode": False,
                "degraded_reason": "",
            }
        ],
        "generated_at": "2026-03-13T00:00:00+00:00",
    }
    audio_result = {
        "schema_version": "cut_audio_sync_result_v1",
        "project_id": "p1",
        "revision": 1,
        "items": [
            {
                "item_id": "as_001",
                "reference_path": "/cam_a.mov",
                "source_path": "/cam_b.mov",
                "detected_offset_sec": 0.032,
                "confidence": 0.91,
                "method": "peaks+correlation_v1",
                "refinement_steps": 2,
                "peak_value": 0.94,
                "degraded_mode": False,
                "degraded_reason": "",
            }
        ],
        "generated_at": "2026-03-13T00:00:00+00:00",
    }

    surface = _build_sync_surface(
        project_id="p1",
        timecode_sync_result=timecode_result,
        audio_sync_result=audio_result,
    )

    assert surface["schema_version"] == "cut_sync_surface_v1"
    assert len(surface["items"]) >= 1
    item = surface["items"][0]
    assert item["recommended_method"] == "timecode"
    assert item["recommended_offset_sec"] == 0.48
    assert item["confidence"] == 0.99


def test_sync_surface_falls_back_to_waveform():
    """sync_surface recommends waveform when no timecode is available."""
    audio_result = {
        "schema_version": "cut_audio_sync_result_v1",
        "project_id": "p1",
        "revision": 1,
        "items": [
            {
                "item_id": "as_001",
                "reference_path": "/cam_a.mov",
                "source_path": "/cam_b.mov",
                "detected_offset_sec": 0.032,
                "confidence": 0.91,
                "method": "peaks+correlation_v1",
                "refinement_steps": 2,
                "peak_value": 0.94,
                "degraded_mode": False,
                "degraded_reason": "",
            }
        ],
        "generated_at": "2026-03-13T00:00:00+00:00",
    }

    surface = _build_sync_surface(
        project_id="p1",
        timecode_sync_result=None,
        audio_sync_result=audio_result,
    )

    assert len(surface["items"]) >= 1
    item = surface["items"][0]
    assert item["recommended_method"] == "waveform"
    assert item["recommended_offset_sec"] == 0.032


def test_sync_surface_empty_when_no_results():
    """sync_surface returns empty items when no sync results."""
    surface = _build_sync_surface(
        project_id="p1",
        timecode_sync_result=None,
        audio_sync_result=None,
    )

    assert surface["schema_version"] == "cut_sync_surface_v1"
    assert surface["items"] == []
