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


def test_cut_scene_graph_apply_adds_note_edge_and_persists_log(tmp_path: Path):
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
            "project_name": "Graph Demo",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]
    scene_job = client.post(
        "/api/cut/scene-assembly-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id},
    )
    _wait_for_job(client, scene_job.json()["job_id"])

    response = client.post(
        "/api/cut/scene-graph/apply",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "graph_id": "main",
            "author": "graph_tester",
            "ops": [
                {"op": "rename_node", "node_id": "scene_01", "label": "Opening Scene"},
                {
                    "op": "add_note",
                    "node_id": "note_director_01",
                    "label": "Director note",
                    "text": "Use tighter rhythm here",
                    "target_node_id": "scene_01",
                },
                {
                    "op": "add_edge",
                    "edge_id": "edge_scene_take_semantic",
                    "edge_type": "semantic_match",
                    "source": "scene_01",
                    "target": "take_node_0001",
                    "weight": 0.9,
                },
            ],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["schema_version"] == "cut_scene_graph_apply_v1"
    assert payload["scene_graph"]["revision"] == 2
    scene_node = next(node for node in payload["scene_graph"]["nodes"] if node["node_id"] == "scene_01")
    note_node = next(node for node in payload["scene_graph"]["nodes"] if node["node_id"] == "note_director_01")
    assert scene_node["label"] == "Opening Scene"
    assert note_node["node_type"] == "note"
    assert note_node["metadata"]["text"] == "Use tighter rhythm here"
    assert any(edge["edge_type"] == "semantic_match" for edge in payload["scene_graph"]["edges"])

    graph_path = sandbox_root / "cut_runtime" / "state" / "scene_graph.latest.json"
    persisted_graph = json.loads(graph_path.read_text(encoding="utf-8"))
    assert persisted_graph["revision"] == 2

    log_path = sandbox_root / "cut_runtime" / "state" / "scene_graph_edit_log.jsonl"
    assert log_path.exists()
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(events) == 1
    assert events[0]["author"] == "graph_tester"
    assert events[0]["op_count"] == 3


def test_cut_scene_graph_apply_returns_recoverable_error_for_unknown_node(tmp_path: Path):
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
            "project_name": "Graph Demo",
        },
    )
    project_id = bootstrap.json()["project"]["project_id"]
    scene_job = client.post(
        "/api/cut/scene-assembly-async",
        json={"sandbox_root": str(sandbox_root), "project_id": project_id},
    )
    _wait_for_job(client, scene_job.json()["job_id"])

    response = client.post(
        "/api/cut/scene-graph/apply",
        json={
            "sandbox_root": str(sandbox_root),
            "project_id": project_id,
            "ops": [{"op": "rename_node", "node_id": "missing_node", "label": "Bad"}],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["schema_version"] == "cut_scene_graph_apply_v1"
    assert payload["error"]["code"] == "scene_graph_patch_invalid"
