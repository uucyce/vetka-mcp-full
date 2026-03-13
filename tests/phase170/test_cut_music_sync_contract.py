"""
MARKER_170.C10.MUSIC_SYNC_CONTRACT_TESTS
Tests for cut_music_sync_result_v1 contract: schema validation, store round-trip,
project-state surfacing.
"""
import json
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.cut_routes import router, _build_music_summary
from src.services.cut_project_store import CutProjectStore


def _valid_music_sync(project_id: str = "p1", music_path: str = "/track.m4a") -> dict:
    return {
        "schema_version": "cut_music_sync_result_v1",
        "project_id": project_id,
        "music_path": music_path,
        "tempo": {"bpm": 120.0, "confidence": 0.95, "time_signature": "4/4"},
        "downbeats": [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5],
        "phrases": [
            {
                "phrase_id": "ph_001",
                "start_sec": 0.0,
                "end_sec": 8.0,
                "energy": 0.3,
                "label": "intro",
            },
            {
                "phrase_id": "ph_002",
                "start_sec": 8.0,
                "end_sec": 24.0,
                "energy": 0.8,
                "label": "verse",
            },
        ],
        "cue_points": [
            {"cue_id": "cue_001", "time_sec": 0.0, "kind": "downbeat", "strength": 0.9},
            {"cue_id": "cue_002", "time_sec": 8.0, "kind": "phrase_start", "strength": 0.85},
            {"cue_id": "cue_003", "time_sec": 16.0, "kind": "drop", "strength": 1.0},
        ],
        "derived_from": "onset_detection_v1",
        "generated_at": "2026-03-13T12:00:00+00:00",
    }


# ─── Schema validation ───


def test_valid_payload_passes_validation(tmp_path: Path):
    store = CutProjectStore(str(tmp_path))
    payload = _valid_music_sync()
    assert store._validate_music_sync_result_payload(payload) is True


def test_missing_required_field_fails():
    store = CutProjectStore("/tmp/test")
    payload = _valid_music_sync()
    del payload["tempo"]
    assert store._validate_music_sync_result_payload(payload) is False


def test_wrong_schema_version_fails():
    store = CutProjectStore("/tmp/test")
    payload = _valid_music_sync()
    payload["schema_version"] = "cut_audio_sync_result_v1"
    assert store._validate_music_sync_result_payload(payload) is False


def test_invalid_tempo_fails():
    store = CutProjectStore("/tmp/test")
    payload = _valid_music_sync()
    payload["tempo"] = {"bpm": 120}  # missing confidence
    assert store._validate_music_sync_result_payload(payload) is False


def test_invalid_phrase_fails():
    store = CutProjectStore("/tmp/test")
    payload = _valid_music_sync()
    payload["phrases"] = [{"phrase_id": "ph_001"}]  # missing fields
    assert store._validate_music_sync_result_payload(payload) is False


def test_invalid_cue_point_fails():
    store = CutProjectStore("/tmp/test")
    payload = _valid_music_sync()
    payload["cue_points"] = [{"cue_id": "c1"}]  # missing fields
    assert store._validate_music_sync_result_payload(payload) is False


def test_empty_arrays_valid():
    store = CutProjectStore("/tmp/test")
    payload = _valid_music_sync()
    payload["downbeats"] = []
    payload["phrases"] = []
    payload["cue_points"] = []
    assert store._validate_music_sync_result_payload(payload) is True


# ─── Store round-trip ───


def test_save_and_load_round_trip(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    for d in ("config", "cut_runtime", "cut_storage", "core_mirror"):
        (sandbox / d).mkdir(parents=True)
    (sandbox / "config" / "cut_core_mirror_manifest.json").write_text("{}\n")

    store = CutProjectStore(str(sandbox))
    payload = _valid_music_sync()
    store.save_music_sync_result(payload)

    loaded = store.load_music_sync_result()
    assert loaded is not None
    assert loaded["schema_version"] == "cut_music_sync_result_v1"
    assert loaded["tempo"]["bpm"] == 120.0
    assert len(loaded["phrases"]) == 2
    assert len(loaded["cue_points"]) == 3
    assert loaded["downbeats"] == [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]


def test_save_invalid_payload_raises(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    for d in ("config", "cut_runtime", "cut_storage", "core_mirror"):
        (sandbox / d).mkdir(parents=True)
    (sandbox / "config" / "cut_core_mirror_manifest.json").write_text("{}\n")

    store = CutProjectStore(str(sandbox))
    bad = {"schema_version": "cut_music_sync_result_v1", "project_id": "p1"}
    with pytest.raises(ValueError, match="Invalid cut_music_sync_result_v1"):
        store.save_music_sync_result(bad)


def test_load_missing_returns_none(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    for d in ("config", "cut_runtime", "cut_storage", "core_mirror"):
        (sandbox / d).mkdir(parents=True)
    (sandbox / "config" / "cut_core_mirror_manifest.json").write_text("{}\n")

    store = CutProjectStore(str(sandbox))
    assert store.load_music_sync_result() is None


# ─── Music summary ───


def test_music_summary_from_valid_result():
    result = _valid_music_sync()
    summary = _build_music_summary(result)
    assert summary is not None
    assert summary["bpm"] == 120.0
    assert summary["bpm_confidence"] == 0.95
    assert summary["total_downbeats"] == 8
    assert summary["total_phrases"] == 2
    assert summary["total_cue_points"] == 3
    assert summary["high_energy_phrases"] == 1  # verse energy=0.8 >= 0.7
    assert summary["phrase_labels"] == ["intro", "verse"]
    assert summary["cue_kind_counts"]["downbeat"] == 1
    assert summary["cue_kind_counts"]["phrase_start"] == 1
    assert summary["cue_kind_counts"]["drop"] == 1


def test_music_summary_none_when_no_result():
    assert _build_music_summary(None) is None


# ─── Project-state integration ───


def test_project_state_includes_music_sync(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "cam_a.mp4").write_bytes(b"00")
    (source_dir / "track.m4a").write_bytes(b"00")

    sandbox = tmp_path / "sandbox"
    for d in ("config", "cut_runtime", "cut_storage", "core_mirror"):
        (sandbox / d).mkdir(parents=True)
    (sandbox / "config" / "cut_core_mirror_manifest.json").write_text("{}\n")

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox),
            "project_name": "Music Test",
        },
    )
    project_id = resp.json()["project"]["project_id"]
    job = client.post(
        "/api/cut/scene-assembly-async",
        json={"sandbox_root": str(sandbox), "project_id": project_id},
    )
    for _ in range(20):
        r = client.get(f"/api/cut/job/{job.json()['job_id']}")
        if r.json()["job"]["state"] in {"done", "error"}:
            break
        time.sleep(0.05)

    # Before saving: music_sync_ready should be False
    state1 = client.get(
        "/api/cut/project-state",
        params={"sandbox_root": str(sandbox), "project_id": project_id},
    ).json()
    assert state1["music_sync_ready"] is False
    assert state1["music_sync_result"] is None

    # Save music sync result
    store = CutProjectStore(str(sandbox))
    store.save_music_sync_result(_valid_music_sync(project_id, str(source_dir / "track.m4a")))

    # After saving: music_sync_ready should be True
    state2 = client.get(
        "/api/cut/project-state",
        params={"sandbox_root": str(sandbox), "project_id": project_id},
    ).json()
    assert state2["music_sync_ready"] is True
    assert state2["music_sync_result"]["tempo"]["bpm"] == 120.0
    assert len(state2["music_sync_result"]["cue_points"]) == 3
    # Music summary lane
    assert state2["music_summary"] is not None
    assert state2["music_summary"]["bpm"] == 120.0
    assert state2["music_summary"]["total_cue_points"] == 3
