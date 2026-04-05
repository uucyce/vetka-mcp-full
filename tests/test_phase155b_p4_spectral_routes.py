"""
Phase 155B-P4 tests: spectral layout QA + spectral anomaly diagnostics APIs.
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
                {"id": "n4", "label": "Design D"},
            ],
            "edges": [
                {"source": "n1", "target": "n2"},
                {"source": "n2", "target": "n3"},
                {"source": "n3", "target": "n4"},
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
        name="seed-spectral",
        set_primary=True,
    )
    return str(record["version_id"])


def _client() -> TestClient:
    from src.api.routes.workflow_routes import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_spectral_layout_qa_endpoint_returns_metrics_and_thresholds(tmp_path, monkeypatch):
    version_id = _seed_version(tmp_path, monkeypatch)
    client = _client()

    response = client.get(f"/api/workflow/spectral-layout-qa/{version_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["marker"] == "MARKER_155B.CANON.SPECTRAL_LAYOUT_QA.V1"
    assert "MARKER_155B.CANON.SPECTRAL_ANOMALY.V1" in data["canonical_markers"]

    report = data["spectral_layout_qa"]
    assert report["status"] in {"ok", "warn", "fail"}
    assert isinstance(report["score"], float)
    assert report["metrics"]["node_count"] == 4
    assert report["metrics"]["component_count"] >= 1
    assert "max_orphan_ratio" in report["thresholds"]


def test_spectral_anomaly_endpoint_returns_laplacian_signature(tmp_path, monkeypatch):
    version_id = _seed_version(tmp_path, monkeypatch)
    client = _client()

    response = client.get(f"/api/workflow/spectral-anomaly/{version_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["marker"] == "MARKER_155B.CANON.SPECTRAL_ANOMALY.V1"
    report = data["spectral_anomaly"]
    assert report["status"] in {"ok", "warn", "fail"}
    assert "lambda2" in report["spectral"]
    assert "eigengap" in report["spectral"]
    assert report["topology"]["node_count"] == 4
    assert isinstance(report["anomaly_count"], int)
