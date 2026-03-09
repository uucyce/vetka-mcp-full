"""
Phase 155B-P1 tests: workflow graph source APIs (runtime/design/predict/drift).
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
                {"id": "n1", "label": "Design A"},
                {"id": "n2", "label": "Design B"},
                {"id": "n3", "label": "Design C"},
            ],
            "edges": [
                {"source": "n1", "target": "n2"},
                {"source": "n2", "target": "n3"},
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
        "predictive_overlay": {
            "predicted_edges": [
                {"source": "n2", "target": "n3", "confidence": 0.81},
            ],
            "stats": {"predicted_edges": 1, "enabled": True},
        },
        "verifier": {"decision": "warn"},
    }

    record = create_dag_version(
        project_id="default_project",
        dag_payload=dag_payload,
        name="seed-version",
        set_primary=True,
    )
    return str(record["version_id"])


def _client() -> TestClient:
    from src.api.routes.workflow_routes import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_runtime_graph_endpoint_returns_version_backed_graph(tmp_path, monkeypatch):
    version_id = _seed_version(tmp_path, monkeypatch)
    client = _client()

    response = client.get(f"/api/workflow/runtime-graph/{version_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["marker"] == "MARKER_155B.CANON.RUNTIME_GRAPH_API.V1"
    assert data["graph_source"] == "version"
    assert data["task_id"] == version_id
    assert data["stats"]["node_count"] == 2
    assert data["stats"]["edge_count"] == 1


def test_design_graph_latest_uses_primary_version(tmp_path, monkeypatch):
    _seed_version(tmp_path, monkeypatch)
    client = _client()

    response = client.get("/api/workflow/design-graph/latest")
    assert response.status_code == 200
    data = response.json()

    assert data["marker"] == "MARKER_155B.CANON.DESIGN_GRAPH_API.V1"
    assert data["graph_source"] == "version"
    assert data["stats"]["node_count"] == 3
    assert data["stats"]["edge_count"] == 2
    assert "MARKER_155B.CANON.DRIFT_REPORT_API.V1" in data["canonical_markers"]


def test_predict_graph_endpoint_returns_overlay_edges_and_nodes(tmp_path, monkeypatch):
    version_id = _seed_version(tmp_path, monkeypatch)
    client = _client()

    response = client.get(f"/api/workflow/predict-graph/{version_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["marker"] == "MARKER_155B.CANON.PREDICT_GRAPH_API.V1"
    assert data["graph_source"] == "version"
    assert len(data["predict_graph"]["edges"]) == 1
    assert data["predict_graph"]["edges"][0]["source"] == "n2"
    assert data["predict_graph"]["edges"][0]["target"] == "n3"
    assert len(data["predict_graph"]["nodes"]) == 2


def test_drift_report_endpoint_returns_metrics_and_delta(tmp_path, monkeypatch):
    version_id = _seed_version(tmp_path, monkeypatch)
    client = _client()

    response = client.get(f"/api/workflow/drift-report/{version_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["marker"] == "MARKER_155B.CANON.DRIFT_REPORT_API.V1"
    report = data["drift_report"]
    assert report["status"] == "warn"
    assert report["counts"]["design_nodes"] == 3
    assert report["counts"]["runtime_nodes"] == 2
    assert report["counts"]["shared_nodes"] == 2
    assert report["counts"]["design_edges"] == 2
    assert report["counts"]["runtime_edges"] == 1
    assert {"source": "n2", "target": "n3"} in report["delta"]["missing_runtime_edges"]
