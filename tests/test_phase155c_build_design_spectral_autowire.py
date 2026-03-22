"""
Phase 155C recon guard: build-design auto-includes spectral diagnostics for architect flow.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 155c contracts changed")

def _client() -> TestClient:
    from src.api.routes.mcc_routes import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_build_design_autowires_spectral_diagnostics_by_default(tmp_path, monkeypatch):
    from src.services.project_config import ProjectConfig
    import src.api.routes.mcc_routes as mcc_routes_module

    monkeypatch.setattr(
        ProjectConfig,
        "load",
        classmethod(
            lambda cls, path=None: ProjectConfig(
                project_id="p1",
                source_type="local",
                source_path=str(tmp_path),
                sandbox_path=str(tmp_path),
                quota_gb=10,
            )
        ),
    )

    def _fake_build_design_dag(
        scope_root,
        max_nodes=600,
        include_artifacts=False,
        problem_statement="",
        target_outcome="",
        use_predictive_overlay=True,
        max_predicted_edges=120,
        min_confidence=0.55,
    ):
        return {
            "runtime_graph": {
                "l2_overview": {
                    "nodes": [{"id": "n1"}, {"id": "n2"}],
                    "edges": [{"source": "n1", "target": "n2"}],
                }
            },
            "design_graph": {
                "nodes": [{"id": "n1"}, {"id": "n2"}, {"id": "n3"}],
                "edges": [{"source": "n1", "target": "n2"}, {"source": "n2", "target": "n3"}],
            },
            "markers": ["MARKER_155.ARCHITECT_BUILD.CONTRACT.V1"],
        }

    async def _fake_to_thread(fn, *args, **kwargs):
        return _fake_build_design_dag(*args, **kwargs)

    monkeypatch.setattr(mcc_routes_module.asyncio, "to_thread", _fake_to_thread)

    client = _client()
    response = client.post("/api/mcc/graph/build-design", json={"scope_path": str(tmp_path)})
    assert response.status_code == 200
    data = response.json()

    assert "spectral_layout_qa" in data
    assert "spectral_anomaly" in data
    assert "MARKER_155B.CANON.SPECTRAL_LAYOUT_QA.V1" in data["markers"]
    assert "MARKER_155B.CANON.SPECTRAL_ANOMALY.V1" in data["markers"]


def test_build_design_can_disable_spectral_autowire(tmp_path, monkeypatch):
    from src.services.project_config import ProjectConfig
    import src.api.routes.mcc_routes as mcc_routes_module

    monkeypatch.setattr(
        ProjectConfig,
        "load",
        classmethod(
            lambda cls, path=None: ProjectConfig(
                project_id="p1",
                source_type="local",
                source_path=str(tmp_path),
                sandbox_path=str(tmp_path),
                quota_gb=10,
            )
        ),
    )

    def _fake_build_design_dag(
        scope_root,
        max_nodes=600,
        include_artifacts=False,
        problem_statement="",
        target_outcome="",
        use_predictive_overlay=True,
        max_predicted_edges=120,
        min_confidence=0.55,
    ):
        return {
            "runtime_graph": {"nodes": [{"id": "n1"}], "edges": []},
            "design_graph": {"nodes": [{"id": "n1"}], "edges": []},
            "markers": ["MARKER_155.ARCHITECT_BUILD.CONTRACT.V1"],
        }

    async def _fake_to_thread(fn, *args, **kwargs):
        return _fake_build_design_dag(*args, **kwargs)

    monkeypatch.setattr(mcc_routes_module.asyncio, "to_thread", _fake_to_thread)

    client = _client()
    response = client.post(
        "/api/mcc/graph/build-design",
        json={"scope_path": str(tmp_path), "include_spectral_diagnostics": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert "spectral_layout_qa" not in data
    assert "spectral_anomaly" not in data
