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
    assert payload["scene_graph_view"]["schema_version"] == "cut_scene_graph_view_v1"
    scene_node = next(node for node in payload["scene_graph"]["nodes"] if node["node_type"] == "scene")
    view_scene_node = next(node for node in payload["scene_graph_view"]["nodes"] if node["node_type"] == "scene")
    view_take_node = next(node for node in payload["scene_graph_view"]["nodes"] if node["node_type"] == "take")
    assert scene_node["metadata"]["scene_index"] == 1
    assert scene_node["metadata"]["summary"]
    assert view_scene_node["visual_bucket"] == "primary_structural"
    assert view_scene_node["rank_hint"] == 1
    assert view_scene_node["selection_refs"]["scene_ids"] == ["scene_01"]
    assert view_scene_node["selection_refs"]["source_paths"]
    assert view_scene_node["render_hints"]["display_mode"] == "scene_card"
    assert view_take_node["node_id"] in payload["scene_graph_view"]["focus"]["focused_node_ids"]
    assert view_take_node["selection_refs"]["clip_ids"] == payload["timeline_state"]["selection"]["clip_ids"]
    assert view_take_node["render_hints"]["display_mode"] == "take_preview"
    assert "scene_01" in payload["scene_graph_view"]["focus"]["focused_node_ids"]
    assert payload["scene_graph_view"]["focus"]["selected_scene_ids"] == ["scene_01"]
    assert payload["scene_graph_view"]["focus"]["selected_clip_ids"] == payload["timeline_state"]["selection"]["clip_ids"]
    assert payload["scene_graph_view"]["focus"]["anchor_node_id"] in payload["scene_graph_view"]["focus"]["focused_node_ids"]
    assert payload["scene_graph_view"]["layout_hints"]["primary_rank_edge_types"] == ["follows", "contains"]
    assert payload["scene_graph_view"]["layout_hints"]["intelligence_edge_types"] == ["semantic_match"]
    selected_clip_id = payload["timeline_state"]["selection"]["clip_ids"][0]
    assert view_take_node["node_id"] in payload["scene_graph_view"]["crosslinks"]["by_clip_id"][selected_clip_id]
    assert "scene_01" in payload["scene_graph_view"]["crosslinks"]["by_scene_id"]
    assert view_scene_node["node_id"] in payload["scene_graph_view"]["structural_subgraph"]["node_ids"]
    assert payload["scene_graph_view"]["overlay_edges"] == []
    dag_projection = payload["scene_graph_view"]["dag_projection"]
    assert dag_projection["root_ids"]
    dag_scene_node = next(node for node in dag_projection["nodes"] if node["primaryNodeId"] == view_scene_node["node_id"])
    assert dag_scene_node["type"] == "roadmap_task"
    assert dag_scene_node["graphKind"] == "project_task"
    assert any(edge["type"] == "structural" for edge in dag_projection["edges"])
    inspector = payload["scene_graph_view"]["inspector"]
    assert inspector["primary_node_id"] in payload["scene_graph_view"]["focus"]["focused_node_ids"]
    assert inspector["focused_nodes"]
    assert any(node["node_id"] == view_scene_node["node_id"] for node in inspector["focused_nodes"])
    assert payload["runtime_ready"] is True
    assert payload["graph_ready"] is True
    assert payload["waveform_bundle"] is None
    assert payload["transcript_bundle"] is None
    assert payload["thumbnail_bundle"] is None
    assert payload["audio_sync_result"] is None
    assert payload["music_sync_result"] is None
    assert payload["music_cue_summary"] is None
    assert payload["slice_bundle"] is None
    assert payload["timecode_sync_result"] is None
    assert payload["sync_surface"]["schema_version"] == "cut_sync_surface_v1"
    assert payload["sync_surface"]["items"] == []
    assert payload["time_marker_bundle"] is None
    assert payload["montage_state"] is None
    assert payload["waveform_ready"] is False
    assert payload["transcript_ready"] is False
    assert payload["thumbnail_ready"] is False
    assert payload["audio_sync_ready"] is False
    assert payload["music_cues_ready"] is False
    assert payload["slice_ready"] is False
    assert payload["timecode_sync_ready"] is False
    assert payload["sync_surface_ready"] is False
    assert payload["time_markers_ready"] is False
    assert payload["montage_ready"] is False
    assert len(payload["recent_jobs"]) == 1
    assert payload["recent_jobs"][0]["job_id"] == job_id
    assert payload["recent_jobs"][0]["job_type"] == "scene_assembly"
    assert payload["active_jobs"] == []


def test_cut_project_state_returns_worker_bundles_when_ready(tmp_path: Path, monkeypatch):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "clip_a_tc_01-00-00-00.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    (source_dir / "audio_a_tc_01-00-00-12.wav").write_bytes(b"RIFF....WAVEfmt ")

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
            "media_path": str(source_dir / "clip_a_tc_01-00-00-00.mp4"),
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
    audio_sync_job = client.post(
        "/api/cut/worker/audio-sync-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id, "limit": 4, "sample_bytes": 2048, "method": "peaks+correlation"},
    ).json()["job_id"]
    timecode_sync_job = client.post(
        "/api/cut/worker/timecode-sync-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id, "limit": 4, "fps": 25},
    ).json()["job_id"]
    slice_job = client.post(
        "/api/cut/worker/pause-slice-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id, "limit": 4, "sample_bytes": 2048, "frame_ms": 20, "silence_threshold": 0.08},
    ).json()["job_id"]

    _wait_for_job(client, waveform_job)
    _wait_for_job(client, transcript_job)
    _wait_for_job(client, thumbnail_job)
    _wait_for_job(client, audio_sync_job)
    _wait_for_job(client, timecode_sync_job)
    _wait_for_job(client, slice_job)

    response = client.get(
        "/api/cut/project-state",
        params={"sandbox_root": str(sandbox_root), "project_id": project_id},
    )
    payload = response.json()
    assert payload["success"] is True
    assert payload["scene_graph_view"] is None
    assert payload["waveform_bundle"]["schema_version"] == "cut_waveform_bundle_v1"
    assert payload["transcript_bundle"]["schema_version"] == "cut_transcript_bundle_v1"
    assert payload["thumbnail_bundle"]["schema_version"] == "cut_thumbnail_bundle_v1"
    assert payload["audio_sync_result"]["schema_version"] == "cut_audio_sync_result_v1"
    assert payload["music_sync_result"] is None
    assert payload["slice_bundle"]["schema_version"] == "cut_slice_bundle_v1"
    assert payload["timecode_sync_result"]["schema_version"] == "cut_timecode_sync_result_v1"
    assert payload["sync_surface"]["schema_version"] == "cut_sync_surface_v1"
    assert payload["time_marker_bundle"]["schema_version"] == "cut_time_marker_bundle_v1"
    assert payload["montage_state"] is None
    assert payload["waveform_ready"] is True
    assert payload["transcript_ready"] is True
    assert payload["thumbnail_ready"] is True
    assert payload["audio_sync_ready"] is True
    assert payload["music_cues_ready"] is False
    assert payload["slice_ready"] is True
    assert payload["timecode_sync_ready"] is True
    assert payload["sync_surface_ready"] is True
    assert payload["time_markers_ready"] is True
    assert payload["montage_ready"] is False
    assert len(payload["waveform_bundle"]["items"]) == 2
    assert len(payload["transcript_bundle"]["items"]) == 2
    assert len(payload["thumbnail_bundle"]["items"]) == 2
    assert len(payload["audio_sync_result"]["items"]) >= 1
    assert len(payload["slice_bundle"]["items"]) >= 1
    assert len(payload["timecode_sync_result"]["items"]) >= 1
    assert len(payload["sync_surface"]["items"]) >= 1
    assert len(payload["time_marker_bundle"]["items"]) == 1
    assert len(payload["recent_jobs"]) >= 2
    assert payload["scene_graph_view"] is None
    job_types = {job["job_type"] for job in payload["recent_jobs"]}
    assert "waveform_build" in job_types
    assert "transcript_normalize" in job_types
    assert "thumbnail_build" in job_types
    assert "audio_sync" in job_types
    assert "pause_slice" in job_types
    assert "timecode_sync" in job_types
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


def test_cut_project_state_surfaces_berlin_fixture_profile_metadata(tmp_path: Path):
    source_dir = tmp_path / "berlin"
    (source_dir / "source_gh5").mkdir(parents=True)
    (source_dir / "source_gh5" / "take_01.mov").write_bytes(b"00")
    (source_dir / "250623_vanpticdanyana_berlin_Punch.m4a").write_bytes(b"00")

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    bootstrap = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Berlin State Demo",
            "bootstrap_profile": "berlin_fixture_v1",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    response = client.get(
        "/api/cut/project-state",
        params={"sandbox_root": str(sandbox_root), "project_id": project_id},
    )
    assert response.status_code == 200
    payload = response.json()
    profile = payload["bootstrap_state"]["profile"]
    assert payload["success"] is True
    assert payload["project"]["bootstrap_profile"] == "berlin_fixture_v1"
    assert profile["profile_name"] == "berlin_fixture_v1"
    assert profile["sandbox_hint"] == "codex54_cut_fixture_sandbox"
    assert profile["reserved_port"] == 3211
    assert profile["music_track"]["relative_path"] == "250623_vanpticdanyana_berlin_Punch.m4a"


def test_cut_project_state_surfaces_music_cue_summary(tmp_path: Path):
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
            "project_name": "Berlin Cue Demo",
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
                "confidence": 0.89,
            },
            "downbeats": [0.0, 1.94, 3.88, 5.82],
            "phrases": [
                {
                    "phrase_id": "phrase_intro",
                    "start_sec": 0.0,
                    "end_sec": 15.52,
                    "label": "Intro",
                    "energy": 0.61,
                }
            ],
            "cue_points": [
                {
                    "cue_id": "cue_drop_01",
                    "start_sec": 5.82,
                    "end_sec": 6.18,
                    "label": "Drop lead",
                    "cue_type": "drop",
                    "confidence": 0.94,
                    "energy": 0.88,
                },
                {
                    "cue_id": "cue_phrase_02",
                    "start_sec": 15.52,
                    "end_sec": 15.9,
                    "label": "Phrase turn",
                    "cue_type": "phrase_turn",
                    "confidence": 0.91,
                    "energy": 0.79,
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

    assert response.status_code == 200
    payload = response.json()
    summary = payload["music_cue_summary"]
    assert payload["success"] is True
    assert payload["music_sync_result"]["schema_version"] == "cut_music_sync_result_v1"
    assert payload["music_cues_ready"] is True
    assert summary["schema_version"] == "cut_music_cue_summary_v1"
    assert summary["track_label"] == "250623_vanpticdanyana_berlin_Punch.m4a"
    assert summary["cue_point_count"] == 2
    assert summary["phrase_count"] == 1
    assert summary["downbeat_count"] == 4
    assert summary["tempo_bpm"] == 124.0
    assert summary["top_cues"][0]["cue_id"] == "cue_drop_01"


def test_cut_project_state_surfaces_rhythm_surface(tmp_path: Path):
    source_dir = tmp_path / "berlin"
    source_dir.mkdir()
    punch = source_dir / "250623_vanpticdanyana_berlin_Punch.m4a"
    punch.write_bytes(b"00")
    (source_dir / "take_01.mov").write_bytes(b"00")

    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()

    bootstrap = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": "Berlin Rhythm Demo",
            "bootstrap_profile": "berlin_fixture_v1",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    store = cut_module.CutProjectStore(str(sandbox_root))
    store.save_timeline_state(
        {
            "schema_version": "cut_timeline_state_v1",
            "project_id": project_id,
            "timeline_id": "main",
            "revision": 2,
            "fps": 25,
            "lanes": [
                {
                    "lane_id": "video_main",
                    "lane_type": "video_main",
                    "clips": [
                        {"clip_id": "clip_01", "start_sec": 0.0, "duration_sec": 1.1, "source_path": str(source_dir / "take_01.mov")},
                        {"clip_id": "clip_02", "start_sec": 1.2, "duration_sec": 0.9, "source_path": str(source_dir / "take_01.mov")},
                        {"clip_id": "clip_03", "start_sec": 2.3, "duration_sec": 1.0, "source_path": str(source_dir / "take_01.mov")},
                        {"clip_id": "clip_04", "start_sec": 3.6, "duration_sec": 1.1, "source_path": str(source_dir / "take_01.mov")},
                    ],
                }
            ],
            "selection": {"clip_ids": [], "scene_ids": []},
            "view": {"zoom": 1.0, "scroll_sec": 0.0, "active_lane_id": "video_main"},
            "updated_at": "2026-03-13T00:00:00+00:00",
        }
    )
    store.save_music_sync_result(
        {
            "schema_version": "cut_music_sync_result_v1",
            "project_id": project_id,
            "revision": 1,
            "music_path": str(punch),
            "tempo": {
                "bpm": 124.0,
                "confidence": 0.89,
            },
            "downbeats": [0.0, 1.94, 3.88, 5.82, 7.76, 9.7, 11.64, 13.58],
            "phrases": [
                {
                    "phrase_id": "phrase_intro",
                    "start_sec": 0.0,
                    "end_sec": 7.76,
                    "label": "Intro",
                    "energy": 0.61,
                }
            ],
            "cue_points": [
                {
                    "cue_id": "cue_drop_01",
                    "start_sec": 5.82,
                    "end_sec": 6.18,
                    "label": "Drop lead",
                    "cue_type": "drop",
                    "confidence": 0.94,
                    "energy": 0.88,
                },
                {
                    "cue_id": "cue_phrase_02",
                    "start_sec": 7.76,
                    "end_sec": 8.12,
                    "label": "Phrase turn",
                    "cue_type": "phrase_turn",
                    "confidence": 0.9,
                    "energy": 0.77,
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

    assert response.status_code == 200
    payload = response.json()
    rhythm_surface = payload["rhythm_surface"]
    assert payload["success"] is True
    assert payload["rhythm_surface_ready"] is True
    assert rhythm_surface["schema_version"] == "cut_rhythm_surface_v1"
    assert rhythm_surface["music_path"] == str(punch)
    assert rhythm_surface["music_tempo_bpm"] == 124.0
    assert rhythm_surface["scene_target_bpm"] >= 72.0
    assert rhythm_surface["source_engine"] == "pulse_scene_proxy_v1"
    assert rhythm_surface["items"][0]["cue_type"] == "drop"
    assert rhythm_surface["items"][0]["recommendation"] == "accent_cut"


def test_cut_project_state_surfaces_montage_state(tmp_path: Path):
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
            "project_name": "Montage State Demo",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]

    store = cut_module.CutProjectStore(str(sandbox_root))
    store.save_montage_state(
        {
            "schema_version": "cut_montage_state_v1",
            "project_id": project_id,
            "revision": 2,
            "source_bundle_revisions": {
                "time_marker_bundle": 3,
                "music_sync_result": 1,
            },
            "accepted_decisions": [
                {
                    "decision_id": "decision_accept_01",
                    "source_family": "marker",
                    "cue_provenance_ids": ["marker_demo_01"],
                    "confidence": 0.91,
                    "score": 0.94,
                    "editorial_intent": "accent_cut",
                    "status": "accepted",
                    "timeline_id": "main",
                    "lane_id": "V1",
                    "anchor_sec": 1.5,
                    "start_sec": 1.25,
                    "end_sec": 2.1,
                    "source_bundle_id": "time_marker_bundle",
                    "source_bundle_revision": 3,
                    "created_at": "2026-03-13T00:00:00+00:00",
                    "updated_at": "2026-03-13T00:00:00+00:00",
                    "author": "tester",
                }
            ],
            "rejected_decisions": [
                {
                    "decision_id": "decision_reject_01",
                    "source_family": "music",
                    "cue_provenance_ids": ["cue_drop_01"],
                    "confidence": 0.52,
                    "score": 0.4,
                    "editorial_intent": "phrase_hold",
                    "status": "rejected",
                    "timeline_id": "main",
                    "lane_id": "V1",
                    "anchor_sec": 3.84,
                    "start_sec": 3.84,
                    "end_sec": 4.32,
                    "source_bundle_id": "music_sync_result",
                    "source_bundle_revision": 1,
                    "created_at": "2026-03-13T00:00:00+00:00",
                    "updated_at": "2026-03-13T00:00:00+00:00",
                    "author": "tester",
                }
            ],
            "updated_at": "2026-03-13T00:00:00+00:00",
            "updated_by": "tester",
        }
    )

    response = client.get(
        "/api/cut/project-state",
        params={"sandbox_root": str(sandbox_root), "project_id": project_id},
    )

    assert response.status_code == 200
    payload = response.json()
    montage_state = payload["montage_state"]
    assert payload["success"] is True
    assert payload["montage_ready"] is True
    assert montage_state["schema_version"] == "cut_montage_state_v1"
    assert montage_state["revision"] == 2
    assert montage_state["accepted_decisions"][0]["editorial_intent"] == "accent_cut"
    assert montage_state["rejected_decisions"][0]["status"] == "rejected"
