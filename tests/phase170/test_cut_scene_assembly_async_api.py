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
    (root / 'config').mkdir(parents=True, exist_ok=True)
    (root / 'cut_runtime').mkdir(parents=True, exist_ok=True)
    (root / 'cut_storage').mkdir(parents=True, exist_ok=True)
    (root / 'core_mirror').mkdir(parents=True, exist_ok=True)
    (root / 'config' / 'cut_core_mirror_manifest.json').write_text('{}\n', encoding='utf-8')


def test_cut_scene_assembly_async_creates_initial_timeline_state(tmp_path: Path):
    source_dir = tmp_path / 'source'
    source_dir.mkdir()
    (source_dir / 'clip_a.mp4').write_bytes(b'00')
    (source_dir / 'audio_a.wav').write_bytes(b'00')

    sandbox_root = tmp_path / 'sandbox'
    _bootstrap_sandbox(sandbox_root)

    client = _make_client()
    bootstrap = client.post(
        '/api/cut/bootstrap',
        json={
            'source_path': str(source_dir),
            'sandbox_root': str(sandbox_root),
            'project_name': 'Scene Demo',
        },
    )
    project_id = bootstrap.json()['project']['project_id']

    created = client.post(
        '/api/cut/scene-assembly-async',
        json={
            'sandbox_root': str(sandbox_root),
            'project_id': project_id,
            'timeline_id': 'main',
        },
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload['success'] is True
    job_id = str(payload['job_id'])

    terminal = None
    for _ in range(20):
        status = client.get(f'/api/cut/job/{job_id}')
        assert status.status_code == 200
        job = status.json()['job']
        if job['state'] in {'done', 'error'}:
            terminal = job
            break
        time.sleep(0.05)

    assert terminal is not None
    assert terminal['state'] == 'done'
    timeline_state = terminal['result']['timeline_state']
    scene_graph = terminal['result']['scene_graph']
    assert timeline_state['schema_version'] == 'cut_timeline_state_v1'
    assert scene_graph['schema_version'] == 'cut_scene_graph_v1'
    assert len(timeline_state['lanes']) >= 1
    assert len(scene_graph['nodes']) >= 3
    assert any(node['node_type'] == 'scene' for node in scene_graph['nodes'])
    assert any(edge['edge_type'] == 'contains' for edge in scene_graph['edges'])
    scene_node = next(node for node in scene_graph['nodes'] if node['node_type'] == 'scene')
    take_node = next(node for node in scene_graph['nodes'] if node['node_type'] == 'take')
    asset_node = next(node for node in scene_graph['nodes'] if node['node_type'] == 'asset')
    assert scene_node['metadata']['scene_index'] == 1
    assert scene_node['metadata']['take_count'] >= 1
    assert scene_node['metadata']['asset_count'] >= 1
    assert scene_node['metadata']['summary']
    assert take_node['metadata']['take_index'] == 1
    assert take_node['metadata']['source_path'].endswith(('.mp4', '.wav'))
    assert take_node['metadata']['modality'] in {'video', 'audio'}
    assert asset_node['metadata']['asset_kind'] in {'video', 'audio'}
    assert asset_node['metadata']['modality'] in {'video', 'audio'}

    persisted_path = sandbox_root / 'cut_runtime' / 'state' / 'timeline_state.latest.json'
    assert persisted_path.exists()
    persisted = json.loads(persisted_path.read_text(encoding='utf-8'))
    assert persisted['schema_version'] == 'cut_timeline_state_v1'

    graph_path = sandbox_root / 'cut_runtime' / 'state' / 'scene_graph.latest.json'
    assert graph_path.exists()
    persisted_graph = json.loads(graph_path.read_text(encoding='utf-8'))
    assert persisted_graph['schema_version'] == 'cut_scene_graph_v1'


def test_cut_scene_assembly_async_returns_recoverable_error_for_unknown_project(tmp_path: Path):
    sandbox_root = tmp_path / 'sandbox'
    _bootstrap_sandbox(sandbox_root)
    client = _make_client()
    resp = client.post(
        '/api/cut/scene-assembly-async',
        json={
            'sandbox_root': str(sandbox_root),
            'project_id': 'missing_project',
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload['success'] is False
    assert payload['error']['code'] == 'project_not_found'
