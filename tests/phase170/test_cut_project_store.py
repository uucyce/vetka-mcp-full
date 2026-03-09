import json
from pathlib import Path

from src.services.cut_project_store import CutProjectStore


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

    loaded_project = store.load_project()
    loaded_bootstrap = store.load_bootstrap_state()
    loaded_graph = store.load_scene_graph()
    loaded_markers = store.load_time_marker_bundle()
    assert loaded_project is not None
    assert loaded_project["project_id"] == project["project_id"]
    assert loaded_bootstrap is not None
    assert loaded_bootstrap["schema_version"] == "cut_bootstrap_state_v1"
    assert loaded_graph is not None
    assert loaded_graph["schema_version"] == "cut_scene_graph_v1"
    assert loaded_markers is not None
    assert loaded_markers["schema_version"] == "cut_time_marker_bundle_v1"


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
