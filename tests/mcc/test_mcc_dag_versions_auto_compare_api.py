from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _payload() -> dict:
    return {
        "source_kind": "array",
        "scope_name": "api_array_scope",
        "persist_versions": True,
        "set_primary_best": False,
        "variants": [
            {"name": "api_baseline", "max_nodes": 140, "use_predictive_overlay": False, "trm_profile": "off"},
            {
                "name": "api_trm_light",
                "max_nodes": 200,
                "use_predictive_overlay": False,
                "trm_profile": "light",
                "trm_policy": {"enabled": True, "seed": 3},
            },
        ],
        "records": [
            {"id": "src", "path": "src", "kind": "dir"},
            {"id": "svc", "path": "src/service.py", "kind": "file"},
            {"id": "api", "path": "src/api.py", "kind": "file"},
        ],
        "relations": [
            {"source": "svc", "target": "api", "weight": 0.9},
        ],
    }


@pytest.fixture
def client(tmp_path: str, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    import src.services.project_config as pc_module
    from src.services import mcc_dag_versions as dag_versions_module
    from src.api.routes.mcc_routes import router

    # Isolate project/session config to test temp directory.
    monkeypatch.setattr(pc_module, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(pc_module, "CONFIG_PATH", os.path.join(tmp_path, "project_config.json"))
    monkeypatch.setattr(pc_module, "SESSION_STATE_PATH", os.path.join(tmp_path, "session_state.json"))
    # Isolate DAG versions JSON.
    monkeypatch.setattr(
        dag_versions_module,
        "DAG_VERSIONS_PATH",
        os.path.join(tmp_path, "mcc_dag_versions.json"),
    )

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_auto_compare_api_creates_ranked_variants_and_versions(client: TestClient) -> None:
    resp = client.post("/api/mcc/dag-versions/auto-compare", json=_payload())
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["count"] == 2
    assert len(data["variants"]) == 2
    assert data["best"]["name"] in {"api_baseline", "api_trm_light"}
    assert data["variants"][0]["scorecard"]["score"] >= data["variants"][1]["scorecard"]["score"]
    assert "MARKER_161.TRM.VERSION_META.V1" in data["markers"]

    # Ensure persisted variants are visible through list endpoint.
    listed = client.get("/api/mcc/dag-versions/list")
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["success"] is True
    assert payload["count"] >= 2
    assert "graph_source" in payload["versions"][0]
    assert "trm_status" in payload["versions"][0]
    assert "trm_profile" in payload["versions"][0]


def test_auto_compare_api_rejects_empty_variants(client: TestClient) -> None:
    bad = _payload()
    bad["variants"] = []
    resp = client.post("/api/mcc/dag-versions/auto-compare", json=bad)
    assert resp.status_code == 400
    assert "variants array is empty" in resp.text
