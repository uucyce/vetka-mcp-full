import json
from pathlib import Path

import pytest

from src.services.cut_project_store import CutProjectStore, build_cut_bootstrap_profile, build_cut_source_manifest


def _bootstrap_sandbox(root: Path) -> None:
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "cut_runtime").mkdir(parents=True, exist_ok=True)
    (root / "cut_storage").mkdir(parents=True, exist_ok=True)
    (root / "core_mirror").mkdir(parents=True, exist_ok=True)
    (root / "config" / "cut_core_mirror_manifest.json").write_text("{}\n", encoding="utf-8")


def test_cut_project_store_roundtrip_and_bootstrap_state(tmp_path: Path):
    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    store = CutProjectStore(str(sandbox_root))
    project = store.create_project(
        source_path=str(source_dir),
        display_name="Store Demo",
        bootstrap_profile="default",
        use_core_mirror=True,
    )
    store.save_project(project)
    store.save_bootstrap_state(
        {
            "schema_version": "cut_bootstrap_state_v1",
            "project_id": project["project_id"],
            "last_bootstrap_mode": "create_new",
            "last_source_path": str(source_dir),
            "last_stats": {"media_files": 0},
            "last_degraded_reason": "",
            "last_job_id": "",
            "updated_at": project["created_at"],
        }
    )
    store.save_scene_graph(
        {
            "schema_version": "cut_scene_graph_v1",
            "project_id": project["project_id"],
            "graph_id": "main",
            "revision": 1,
            "nodes": [
                {
                    "node_id": "scene_01",
                    "node_type": "scene",
                    "label": "Scene 01",
                    "record_ref": None,
                    "metadata": {},
                }
            ],
            "edges": [],
            "updated_at": project["created_at"],
        }
    )
    store.save_time_marker_bundle(
        {
            "schema_version": "cut_time_marker_bundle_v1",
            "project_id": project["project_id"],
            "timeline_id": "main",
            "revision": 1,
            "items": [
                {
                    "marker_id": "marker_demo_01",
                    "schema_version": "cut_time_marker_v1",
                    "project_id": project["project_id"],
                    "timeline_id": "main",
                    "media_path": str(source_dir / "clip_a.mp4"),
                    "kind": "favorite",
                    "start_sec": 1.0,
                    "end_sec": 2.0,
                    "anchor_sec": 1.5,
                    "score": 0.9,
                    "label": "",
                    "text": "",
                    "author": "tester",
                    "context_slice": None,
                    "cam_payload": None,
                    "chat_thread_id": None,
                    "comment_thread_id": None,
                    "source_engine": "cut_mcp",
                    "status": "active",
                    "created_at": project["created_at"],
                    "updated_at": project["created_at"],
                }
            ],
            "ranking_summary": {
                "total_markers": 1,
                "active_markers": 1,
                "kind_counts": {"favorite": 1, "comment": 0, "cam": 0, "insight": 0, "chat": 0},
                "top_media": [{"media_path": str(source_dir / "clip_a.mp4"), "score": 0.9}],
            },
            "generated_at": project["created_at"],
        }
    )
    store.save_audio_sync_result(
        {
            "schema_version": "cut_audio_sync_result_v1",
            "project_id": project["project_id"],
            "revision": 1,
            "items": [
                {
                    "item_id": "audio_sync_0001",
                    "reference_path": str(source_dir / "audio_a.wav"),
                    "source_path": str(source_dir / "audio_b.wav"),
                    "detected_offset_sec": 0.032,
                    "confidence": 0.91,
                    "method": "peaks+correlation_v1",
                    "refinement_steps": 2,
                    "peak_value": 0.94,
                    "degraded_mode": False,
                    "degraded_reason": "",
                }
            ],
            "generated_at": project["created_at"],
        }
    )
    store.save_slice_bundle(
        {
            "schema_version": "cut_slice_bundle_v1",
            "project_id": project["project_id"],
            "revision": 1,
            "items": [
                {
                    "item_id": "slice_0001",
                    "source_path": str(source_dir / "audio_a.wav"),
                    "method": "energy_pause_v1",
                    "windows": [
                        {
                            "start_sec": 0.0,
                            "end_sec": 1.12,
                            "duration_sec": 1.12,
                            "confidence": 0.82,
                            "method": "energy_pause_v1",
                        }
                    ],
                    "degraded_mode": False,
                    "degraded_reason": "",
                }
            ],
            "generated_at": project["created_at"],
        }
    )
    store.save_timecode_sync_result(
        {
            "schema_version": "cut_timecode_sync_result_v1",
            "project_id": project["project_id"],
            "revision": 1,
            "items": [
                {
                    "item_id": "timecode_sync_0001",
                    "reference_path": str(source_dir / "cam_a_tc_01-00-00-00.mov"),
                    "source_path": str(source_dir / "cam_b_tc_01-00-00-12.mov"),
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
            "generated_at": project["created_at"],
        }
    )

    loaded_project = store.load_project()
    loaded_bootstrap = store.load_bootstrap_state()
    loaded_graph = store.load_scene_graph()
    loaded_markers = store.load_time_marker_bundle()
    loaded_audio_sync = store.load_audio_sync_result()
    loaded_slice_bundle = store.load_slice_bundle()
    loaded_timecode_sync = store.load_timecode_sync_result()
    assert loaded_project is not None
    assert loaded_project["project_id"] == project["project_id"]
    assert loaded_bootstrap is not None
    assert loaded_bootstrap["schema_version"] == "cut_bootstrap_state_v1"
    assert loaded_graph is not None
    assert loaded_graph["schema_version"] == "cut_scene_graph_v1"
    assert loaded_markers is not None
    assert loaded_markers["schema_version"] == "cut_time_marker_bundle_v1"
    assert loaded_audio_sync is not None
    assert loaded_audio_sync["schema_version"] == "cut_audio_sync_result_v1"
    assert loaded_slice_bundle is not None
    assert loaded_slice_bundle["schema_version"] == "cut_slice_bundle_v1"
    assert loaded_timecode_sync is not None
    assert loaded_timecode_sync["schema_version"] == "cut_timecode_sync_result_v1"


def test_cut_project_store_resolve_create_or_open_distinguishes_source_path(tmp_path: Path):
    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    source_a = tmp_path / "source_a"
    source_b = tmp_path / "source_b"
    source_a.mkdir()
    source_b.mkdir()

    store = CutProjectStore(str(sandbox_root))
    project = store.create_project(
        source_path=str(source_a),
        display_name="Store Demo",
        bootstrap_profile="default",
        use_core_mirror=True,
    )
    store.save_project(project)

    mode_a, project_a = store.resolve_create_or_open(str(source_a))
    mode_b, project_b = store.resolve_create_or_open(str(source_b))
    assert mode_a == "open"
    assert project_a is not None
    assert mode_b == "create"
    assert project_b is None


def test_cut_project_store_ignores_invalid_schema_file(tmp_path: Path):
    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    (sandbox_root / "config" / "cut_project.json").write_text(
        json.dumps({"schema_version": "wrong_schema", "project_id": "bad"}),
        encoding="utf-8",
    )

    store = CutProjectStore(str(sandbox_root))
    assert store.load_project() is None


def test_cut_source_manifest_groups_berlin_like_assets(tmp_path: Path):
    source_dir = tmp_path / "berlin"
    (source_dir / "source_gh5").mkdir(parents=True)
    (source_dir / "video_gen").mkdir()
    (source_dir / "boards").mkdir()
    (source_dir / "prj").mkdir()
    (source_dir / "source_gh5" / "cam_a.mov").write_bytes(b"00")
    (source_dir / "video_gen" / "scene_01.mp4").write_bytes(b"00")
    (source_dir / "boards" / "frame_01.png").write_bytes(b"00")
    (source_dir / "prj" / "edit.prproj").write_text("demo", encoding="utf-8")
    (source_dir / "250623_vanpticdanyana_berlin_Punch.m4a").write_bytes(b"00")
    (source_dir / "ironwall_v2_scenario.md").write_text("scenario", encoding="utf-8")

    manifest = build_cut_source_manifest(str(source_dir))

    assert manifest["schema_version"] == "cut_source_manifest_v1"
    assert manifest["asset_totals"]["video"] == 2
    assert manifest["asset_totals"]["audio"] == 1
    assert manifest["asset_totals"]["image"] == 1
    assert manifest["asset_totals"]["document"] == 1
    assert manifest["asset_totals"]["project"] == 1
    assert manifest["primary_music_track"]["relative_path"] == "250623_vanpticdanyana_berlin_Punch.m4a"
    assert "ironwall_v2_scenario.md" in manifest["key_docs"]
    assert "prj/edit.prproj" in manifest["project_files"]
    bucket_names = {bucket["bucket"] for bucket in manifest["bucket_summaries"]}
    assert "source_gh5" in bucket_names
    assert "video_gen" in bucket_names
    assert "boards" in bucket_names


def test_cut_bootstrap_profile_berlin_fixture_adds_launch_metadata(tmp_path: Path):
    source_dir = tmp_path / "berlin"
    source_dir.mkdir()
    punch = source_dir / "250623_vanpticdanyana_berlin_Punch.m4a"
    punch.write_bytes(b"00")

    profile = build_cut_bootstrap_profile(str(source_dir), "berlin_fixture_v1")

    assert profile["profile_name"] == "berlin_fixture_v1"
    assert profile["sandbox_hint"] == "codex54_cut_fixture_sandbox"
    assert profile["reserved_port"] == 3211
    assert profile["music_track"]["path"] == str(punch)


def test_cut_project_store_rejects_scene_graph_with_unknown_node_type(tmp_path: Path):
    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    store = CutProjectStore(str(sandbox_root))

    with pytest.raises(ValueError, match="Invalid cut_scene_graph_v1 payload"):
        store.save_scene_graph(
            {
                "schema_version": "cut_scene_graph_v1",
                "project_id": "proj_demo",
                "graph_id": "main",
                "revision": 1,
                "nodes": [
                    {
                        "node_id": "scene_01",
                        "node_type": "mystery",
                        "label": "Scene 01",
                        "record_ref": None,
                        "metadata": {},
                    }
                ],
                "edges": [],
                "updated_at": "2026-03-12T12:00:00+00:00",
            }
        )


def test_cut_project_store_rejects_scene_graph_with_duplicate_node_id(tmp_path: Path):
    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    store = CutProjectStore(str(sandbox_root))

    with pytest.raises(ValueError, match="Invalid cut_scene_graph_v1 payload"):
        store.save_scene_graph(
            {
                "schema_version": "cut_scene_graph_v1",
                "project_id": "proj_demo",
                "graph_id": "main",
                "revision": 1,
                "nodes": [
                    {
                        "node_id": "scene_01",
                        "node_type": "scene",
                        "label": "Scene 01",
                        "record_ref": None,
                        "metadata": {},
                    },
                    {
                        "node_id": "scene_01",
                        "node_type": "note",
                        "label": "Duplicate",
                        "record_ref": None,
                        "metadata": {},
                    },
                ],
                "edges": [],
                "updated_at": "2026-03-12T12:00:00+00:00",
            }
        )


def test_cut_project_store_rejects_scene_graph_edge_pointing_to_missing_node(tmp_path: Path):
    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    store = CutProjectStore(str(sandbox_root))

    with pytest.raises(ValueError, match="Invalid cut_scene_graph_v1 payload"):
        store.save_scene_graph(
            {
                "schema_version": "cut_scene_graph_v1",
                "project_id": "proj_demo",
                "graph_id": "main",
                "revision": 1,
                "nodes": [
                    {
                        "node_id": "scene_01",
                        "node_type": "scene",
                        "label": "Scene 01",
                        "record_ref": None,
                        "metadata": {},
                    }
                ],
                "edges": [
                    {
                        "edge_id": "edge_ref_01",
                        "edge_type": "references",
                        "source": "scene_01",
                        "target": "missing_take",
                        "weight": 1.0,
                    }
                ],
                "updated_at": "2026-03-12T12:00:00+00:00",
            }
        )
