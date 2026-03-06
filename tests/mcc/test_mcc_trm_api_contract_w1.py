from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    import src.api.routes.mcc_routes as routes
    from src.api.routes.mcc_routes import router

    monkeypatch.setattr(
        routes,
        "_load_active_project_config",
        lambda: SimpleNamespace(
            source_path=str(tmp_path),
            sandbox_path=str(tmp_path),
            project_id="trm_contract_project",
        ),
    )

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_build_design_contract_exposes_trm_meta_without_behavior_change(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    MARKER_161.TRM.API.BUILD_DESIGN_INPUT.V1
    MARKER_161.TRM.CONFIG.CONTRACT.V1
    """
    import src.services.mcc_architect_builder as builder

    monkeypatch.setattr(
        builder,
        "build_design_dag",
        lambda *args, **kwargs: {
            "design_graph": {"nodes": [], "edges": []},
            "markers": ["MARKER_TEST_BASELINE"],
        },
    )

    resp = client.post(
        "/api/mcc/graph/build-design",
        json={
            "scope_path": str(Path.cwd()),
            "max_nodes": 120,
            "trm_profile": "light",
            "trm_policy": {
                "enabled": True,
                "profile": "balanced",
                "max_refine_steps": 9999,
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["graph_source"] == "baseline"
    assert data["trm_meta"]["status"] == "disabled"
    assert data["trm_meta"]["applied"] is False
    assert data["trm_meta"]["profile"] == "balanced"
    assert data["trm_meta"]["policy"]["max_refine_steps"] == 64


def test_build_design_from_array_contract_exposes_trm_meta(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    MARKER_161.TRM.API.BUILD_FROM_ARRAY_INPUT.V1
    MARKER_161.TRM.CONFIG.CONTRACT.V1
    """
    import src.services.mcc_architect_builder as builder

    monkeypatch.setattr(
        builder,
        "build_design_dag_from_arrays",
        lambda *args, **kwargs: {
            "design_graph": {"nodes": [{"id": "n1"}], "edges": []},
            "markers": ["MARKER_TEST_ARRAY_BASELINE"],
        },
    )

    resp = client.post(
        "/api/mcc/graph/build-design/from-array",
        json={
            "scope_name": "arr",
            "records": [{"id": "n1", "path": "src", "kind": "dir"}],
            "trm_profile": "wrong_profile",
            "trm_policy": {"enabled": True},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["graph_source"] == "baseline"
    assert data["trm_meta"]["status"] == "disabled"
    assert data["trm_meta"]["profile"] == "off"
    assert data["trm_meta"]["policy"]["enabled"] is False

