"""
MARKER_170.15.SYNC_HINT_ENRICHMENT_TESTS
Tests for _enrich_timeline_with_sync_hints: sync_hint on clips, sync_summary on lanes.
"""
from src.api.routes.cut_routes import _enrich_timeline_with_sync_hints


def _make_clip(clip_id: str, source_path: str, sync: dict | None = None) -> dict:
    clip = {
        "clip_id": clip_id,
        "source_path": source_path,
        "start_sec": 0.0,
        "duration_sec": 10.0,
    }
    if sync is not None:
        clip["sync"] = sync
    return clip


def _make_lane(lane_id: str, clips: list[dict]) -> dict:
    return {"lane_id": lane_id, "lane_type": "video", "clips": clips}


def _make_surface(items: list[dict]) -> dict:
    return {"schema_version": "cut_sync_surface_v1", "items": items}


def _make_surface_item(
    source_path: str,
    method: str = "timecode",
    offset: float = 0.5,
    confidence: float = 0.95,
    reference: str = "/ref.mp4",
) -> dict:
    return {
        "item_id": "sync_surface_0001",
        "source_path": source_path,
        "reference_path": reference,
        "recommended_method": method,
        "recommended_offset_sec": offset,
        "confidence": confidence,
    }


# ─── sync_hint embedding ───


def test_clip_gets_sync_hint_from_surface():
    """Clip with matching sync_surface item gets sync_hint embedded."""
    clip = _make_clip("c1", "/cam_b.mp4")
    lane = _make_lane("video", [clip])
    state = {"lanes": [lane], "sync_groups": []}
    surface = _make_surface([_make_surface_item("/cam_b.mp4", "timecode", 0.48, 0.99)])

    _enrich_timeline_with_sync_hints(state, surface)

    assert "sync_hint" in clip
    assert clip["sync_hint"]["recommended_method"] == "timecode"
    assert clip["sync_hint"]["recommended_offset_sec"] == 0.48
    assert clip["sync_hint"]["confidence"] == 0.99
    assert clip["sync_hint"]["already_applied"] is False


def test_clip_without_surface_match_has_no_hint():
    """Clip with no sync_surface match has no sync_hint."""
    clip = _make_clip("c1", "/cam_c.mp4")
    lane = _make_lane("video", [clip])
    state = {"lanes": [lane], "sync_groups": []}
    surface = _make_surface([_make_surface_item("/cam_b.mp4")])

    _enrich_timeline_with_sync_hints(state, surface)

    assert "sync_hint" not in clip


def test_already_synced_clip_hint_marks_applied():
    """Clip already synced still gets hint but already_applied=True."""
    clip = _make_clip(
        "c1",
        "/cam_b.mp4",
        sync={"method": "waveform", "offset_sec": 0.03, "confidence": 0.91},
    )
    lane = _make_lane("video", [clip])
    state = {"lanes": [lane], "sync_groups": []}
    surface = _make_surface([_make_surface_item("/cam_b.mp4", "timecode", 0.48, 0.99)])

    _enrich_timeline_with_sync_hints(state, surface)

    assert clip["sync_hint"]["already_applied"] is True


def test_stale_sync_hint_removed_when_surface_drops_item():
    """If sync_surface no longer has an item, old sync_hint is removed."""
    clip = _make_clip("c1", "/cam_b.mp4")
    clip["sync_hint"] = {"recommended_method": "waveform", "recommended_offset_sec": 0.03}
    lane = _make_lane("video", [clip])
    state = {"lanes": [lane], "sync_groups": []}
    surface = _make_surface([])  # empty surface

    _enrich_timeline_with_sync_hints(state, surface)

    assert "sync_hint" not in clip


# ─── sync_summary on lanes ───


def test_lane_sync_summary_counts():
    """Lane gets correct sync_summary with synced/unsynced/pending counts."""
    synced_clip = _make_clip(
        "c1",
        "/cam_a.mp4",
        sync={"method": "timecode", "offset_sec": 0.48, "confidence": 0.99},
    )
    unsynced_clip = _make_clip("c2", "/cam_b.mp4")
    lane = _make_lane("video", [synced_clip, unsynced_clip])
    state = {"lanes": [lane], "sync_groups": []}
    surface = _make_surface([_make_surface_item("/cam_b.mp4", "waveform", 0.03, 0.91)])

    _enrich_timeline_with_sync_hints(state, surface)

    summary = lane["sync_summary"]
    assert summary["total_clips"] == 2
    assert summary["synced"] == 1
    assert summary["unsynced"] == 1
    assert summary["pending_hints"] == 1
    assert "timecode" in summary["methods_used"]


def test_empty_lane_sync_summary():
    """Empty lane gets zeroed sync_summary."""
    lane = _make_lane("audio", [])
    state = {"lanes": [lane], "sync_groups": []}
    surface = _make_surface([])

    _enrich_timeline_with_sync_hints(state, surface)

    summary = lane["sync_summary"]
    assert summary["total_clips"] == 0
    assert summary["synced"] == 0
    assert summary["pending_hints"] == 0


def test_multiple_lanes_each_get_summary():
    """Each lane gets independent sync_summary."""
    clip_v = _make_clip("c1", "/cam_a.mp4")
    clip_a = _make_clip("c2", "/audio.wav")
    lane_v = _make_lane("video", [clip_v])
    lane_a = _make_lane("audio_sync", [clip_a])
    state = {"lanes": [lane_v, lane_a], "sync_groups": []}
    surface = _make_surface([
        _make_surface_item("/cam_a.mp4", "timecode", 0.48, 0.99),
        _make_surface_item("/audio.wav", "waveform", 0.03, 0.85),
    ])

    _enrich_timeline_with_sync_hints(state, surface)

    assert lane_v["sync_summary"]["pending_hints"] == 1
    assert lane_a["sync_summary"]["pending_hints"] == 1


def test_none_timeline_state_is_safe():
    """Passing None timeline_state does not raise."""
    surface = _make_surface([_make_surface_item("/cam_a.mp4")])
    _enrich_timeline_with_sync_hints(None, surface)  # should not raise


def test_enrichment_through_project_state_api(tmp_path):
    """Integration: project-state returns clips with sync_hint when sync results exist."""
    import json
    import time
    from pathlib import Path
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from src.api.routes.cut_routes import router
    from src.services.cut_project_store import CutProjectStore

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "cam_a.mp4").write_bytes(b"00")
    (source_dir / "cam_b.mp4").write_bytes(b"00")
    (source_dir / "audio_a.wav").write_bytes(b"00")

    sandbox_root = tmp_path / "sandbox"
    (sandbox_root / "config").mkdir(parents=True)
    (sandbox_root / "cut_runtime").mkdir(parents=True)
    (sandbox_root / "cut_storage").mkdir(parents=True)
    (sandbox_root / "core_mirror").mkdir(parents=True)
    (sandbox_root / "config" / "cut_core_mirror_manifest.json").write_text("{}\n")

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    bootstrap = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Hint Test",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]
    scene_job = client.post(
        "/api/cut/scene-assembly-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id},
    )
    for _ in range(20):
        resp = client.get(f"/api/cut/job/{scene_job.json()['job_id']}")
        if resp.json()["job"]["state"] in {"done", "error"}:
            break
        time.sleep(0.05)

    # Save a fake audio_sync_result so sync_surface has items
    store = CutProjectStore(str(sandbox_root))
    audio_sync = {
        "schema_version": "cut_audio_sync_result_v1",
        "project_id": project_id,
        "revision": 1,
        "items": [
            {
                "item_id": "as_001",
                "reference_path": str(source_dir / "cam_a.mp4"),
                "source_path": str(source_dir / "cam_b.mp4"),
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
    store.save_audio_sync_result(audio_sync)

    # Fetch project-state — should have enriched clips
    state_resp = client.get(
        "/api/cut/project-state",
        params={"sandbox_root": str(sandbox_root), "project_id": project_id},
    )
    payload = state_resp.json()
    assert payload["success"] is True
    assert payload["sync_surface_ready"] is True

    # Find clips that match the sync surface source_path
    timeline = payload.get("timeline_state") or {}
    all_clips = [c for lane in timeline.get("lanes", []) for c in lane.get("clips", [])]
    hinted = [c for c in all_clips if c.get("sync_hint")]
    assert len(hinted) >= 1, f"Expected at least 1 clip with sync_hint, got {len(hinted)}"
    assert hinted[0]["sync_hint"]["recommended_method"] == "waveform"

    # Check lane sync_summary exists
    for lane in timeline.get("lanes", []):
        assert "sync_summary" in lane, f"Lane {lane['lane_id']} missing sync_summary"
