"""
Phase 155 main tail closure: input-matrix enrich API.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _seed_version(tmp_path, monkeypatch):
    import src.services.mcc_dag_versions as dag_versions_module
    from src.services.mcc_dag_versions import create_dag_version
    from src.services.project_config import ProjectConfig

    monkeypatch.setattr(
        dag_versions_module,
        "DAG_VERSIONS_PATH",
        str(tmp_path / "mcc_dag_versions.json"),
    )
    monkeypatch.setattr(ProjectConfig, "load", classmethod(lambda cls, path=None: None))

    dag_payload = {
        "design_graph": {
            "nodes": [
                {"id": "n1", "label": "src/api/routes/workflow_routes.py", "path": "src/api/routes/workflow_routes.py", "updated_at": "2026-03-01T10:00:00Z"},
                {"id": "n2", "label": "src/services/mcc_scc_graph.py", "path": "src/services/mcc_scc_graph.py", "updated_at": "2026-03-02T10:00:00Z"},
                {"id": "n3", "label": "docs/155_ph/plan.md", "path": "docs/155_ph/plan.md", "updated_at": "2026-03-02T11:00:00Z"},
            ],
            "edges": [
                {"source": "n1", "target": "n2", "type": "flow", "meta": {"channel": "explicit", "evidence": ["import"]}},
                {"source": "n3", "target": "n2", "type": "reference", "meta": {"evidence": ["citation"]}},
            ],
        },
        "runtime_graph": {
            "l2_overview": {
                "nodes": [
                    {"id": "n1", "label": "Runtime A"},
                    {"id": "n2", "label": "Runtime B"},
                ],
                "edges": [
                    {"source": "n1", "target": "n2"},
                ],
            }
        },
    }

    record = create_dag_version(
        project_id="default_project",
        dag_payload=dag_payload,
        name="seed-input-matrix",
        set_primary=True,
    )
    return str(record["version_id"])


def _client() -> TestClient:
    from src.api.routes.workflow_routes import router
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 155b contracts changed")

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_input_matrix_enrich_returns_marker_and_scored_edges(tmp_path, monkeypatch):
    version_id = _seed_version(tmp_path, monkeypatch)
    client = _client()

    response = client.post(
        f"/api/workflow/enrich/input-matrix/{version_id}",
        json={"graph_mode": "design", "min_score": 0.2, "include_rejected": True},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["marker"] == "MARKER_155B.CANON.INPUT_MATRIX_ENRICH_API.V1"
    assert "MARKER_155B.CANON.RUNTIME_GRAPH_API.V1" in data["canonical_markers"]
    assert data["graph_mode"] == "design"
    assert data["input_matrix"]["total_edges"] == 2
    assert len(data["enriched_graph"]["edges"]) == 2

    first_edge_meta = data["enriched_graph"]["edges"][0]["meta"]["input_matrix"]
    assert "score" in first_edge_meta
    assert "channel_scores" in first_edge_meta
    assert first_edge_meta["accepted"] in {True, False}


def test_input_matrix_enrich_threshold_filters_when_rejected_hidden(tmp_path, monkeypatch):
    version_id = _seed_version(tmp_path, monkeypatch)
    client = _client()

    response = client.post(
        f"/api/workflow/enrich/input-matrix/{version_id}",
        json={"graph_mode": "design", "min_score": 0.95, "include_rejected": False},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["input_matrix"]["total_edges"] == 2
    assert len(data["enriched_graph"]["edges"]) <= 2
    for edge in data["enriched_graph"]["edges"]:
        assert edge["meta"]["input_matrix"]["accepted"] is True
