import pytest
from pathlib import Path

pytestmark = pytest.mark.stale(reason="CUT API refactored — bootstrap/project_state contracts changed")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import cut_routes as cut_module
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


def test_cut_music_sync_result_roundtrip(tmp_path: Path):
    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    store = CutProjectStore(str(sandbox_root))

    payload = {
        "schema_version": "cut_music_sync_result_v1",
        "project_id": "cut_demo",
        "revision": 1,
        "music_path": "/tmp/punch.m4a",
        "tempo": {
            "bpm": 124.0,
            "confidence": 0.91,
        },
        "downbeats": [0.0, 1.94, 3.88],
        "phrases": [
            {
                "phrase_id": "phrase_01",
                "start_sec": 0.0,
                "end_sec": 15.52,
                "label": "Intro",
                "energy": 0.62,
            }
        ],
        "cue_points": [
            {
                "cue_id": "cue_01",
                "start_sec": 5.82,
                "end_sec": 6.18,
                "label": "Drop lead",
                "cue_type": "drop",
                "confidence": 0.94,
                "energy": 0.88,
            }
        ],
        "derived_from": "music_sync_transient_v1",
        "generated_at": "2026-03-13T00:00:00+00:00",
    }

    store.save_music_sync_result(payload)
    loaded = store.load_music_sync_result()

    assert loaded is not None
    assert loaded["schema_version"] == "cut_music_sync_result_v1"
    assert loaded["tempo"]["bpm"] == 124.0
    assert loaded["cue_points"][0]["cue_id"] == "cue_01"


def test_cut_project_state_music_summary_prefers_music_contract(tmp_path: Path):
    source_dir = tmp_path / "berlin"
    source_dir.mkdir()
    punch = source_dir / "250623_vanpticdanyana_berlin_Punch.m4a"
    punch.write_bytes(b"00")

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    bootstrap = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Berlin Music Summary",
            "bootstrap_profile": "berlin_fixture_v1",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    store = cut_module.CutProjectStore(str(sandbox_root))
    store.save_music_sync_result(
        {
            "schema_version": "cut_music_sync_result_v1",
            "project_id": project_id,
            "revision": 1,
            "music_path": str(punch),
            "tempo": {
                "bpm": 124.0,
                "confidence": 0.9,
            },
            "downbeats": [0.0, 1.94, 3.88, 5.82],
            "phrases": [
                {
                    "phrase_id": "phrase_01",
                    "start_sec": 0.0,
                    "end_sec": 15.52,
                    "label": "Intro",
                    "energy": 0.62,
                },
                {
                    "phrase_id": "phrase_02",
                    "start_sec": 15.52,
                    "end_sec": 31.04,
                    "label": "Lift",
                    "energy": 0.85,
                },
            ],
            "cue_points": [
                {
                    "cue_id": "cue_01",
                    "start_sec": 5.82,
                    "end_sec": 6.18,
                    "label": "Drop lead",
                    "cue_type": "drop",
                    "confidence": 0.94,
                    "energy": 0.88,
                },
                {
                    "cue_id": "cue_02",
                    "start_sec": 15.52,
                    "end_sec": 15.9,
                    "label": "Phrase turn",
                    "cue_type": "phrase_turn",
                    "confidence": 0.91,
                    "energy": 0.8,
                },
            ],
            "derived_from": "music_sync_transient_v1",
            "generated_at": "2026-03-13T00:00:00+00:00",
        }
    )

    response = client.get(
        "/api/cut/project-state",
        params={"sandbox_root": str(sandbox_root), "project_id": project_id},
    )
    payload = response.json()
    summary = payload["music_cue_summary"]

    assert payload["music_cues_ready"] is True
    assert summary["track_label"] == "250623_vanpticdanyana_berlin_Punch.m4a"
    assert summary["cue_point_count"] == 2
    assert summary["phrase_count"] == 2
    assert summary["top_cues"][0]["cue_id"] == "cue_01"
