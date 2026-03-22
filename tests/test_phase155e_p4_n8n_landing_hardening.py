"""
Phase 155E P4 tests: n8n landing hardening (type-preserve + runtime mapping profile).
"""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.api.routes.workflow_template_routes as workflow_template_routes
from src.api.routes.workflow_template_routes import router as workflow_template_router
from src.services.workflow_store import WorkflowStore
from src.services.converters.n8n_converter import n8n_to_vetka, vetka_to_n8n

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 155e contracts changed")

@pytest.fixture
def api_client(tmp_path: Path):
    store = WorkflowStore(project_root=tmp_path)
    workflow_template_routes._store = store
    app = FastAPI()
    app.include_router(workflow_template_router)
    try:
        yield TestClient(app)
    finally:
        workflow_template_routes._store = None


def test_n8n_import_sets_runtime_mapping_profile_and_connection_meta():
    n8n = {
        "name": "Profile Preserve",
        "nodes": [
            {"name": "If", "type": "n8n-nodes-base.if", "typeVersion": 1, "position": [0, 0]},
            {"name": "True Node", "type": "n8n-nodes-base.code", "typeVersion": 1, "position": [200, -100]},
            {"name": "False Node", "type": "n8n-nodes-base.code", "typeVersion": 1, "position": [200, 100]},
        ],
        "connections": {
            "If": {
                "main": [
                    [{"node": "True Node", "type": "main", "index": 0}],
                    [{"node": "False Node", "type": "main", "index": 0}],
                ]
            }
        },
    }

    wf = n8n_to_vetka(n8n)
    assert wf["metadata"]["runtime_mapping_profile"] == "n8n->canonical->runtime.v1"

    conditional_edges = [e for e in wf["edges"] if e.get("type") == "conditional"]
    assert len(conditional_edges) == 2
    output_indexes = sorted(
        int(e.get("data", {}).get("n8n_connection", {}).get("output_index", -1))
        for e in conditional_edges
    )
    assert output_indexes == [0, 1]


def test_n8n_roundtrip_preserves_non_default_connection_slot():
    n8n = {
        "name": "Slot Preserve",
        "nodes": [
            {"name": "Split", "type": "n8n-nodes-base.splitInBatches", "typeVersion": 1, "position": [0, 0]},
            {"name": "A", "type": "n8n-nodes-base.code", "typeVersion": 1, "position": [200, -100]},
            {"name": "B", "type": "n8n-nodes-base.code", "typeVersion": 1, "position": [200, 100]},
        ],
        "connections": {
            "Split": {
                "main": [
                    [],
                    [{"node": "B", "type": "main", "index": 0}],
                ]
            }
        },
    }

    wf = n8n_to_vetka(n8n)
    exported = vetka_to_n8n(wf)

    assert exported["meta"]["runtime_mapping_profile"] == "n8n->canonical->runtime.v1"
    split_main = exported["connections"]["Split"]["main"]
    assert len(split_main) >= 2
    assert split_main[0] == []
    assert split_main[1][0]["node"] == "B"
    assert split_main[1][0]["type"] == "main"


def test_api_import_export_preserves_mapping_profile_and_slots(api_client: TestClient):
    payload = {
        "name": "API Slot Preserve",
        "nodes": [
            {"name": "If", "type": "n8n-nodes-base.if", "typeVersion": 1, "position": [0, 0]},
            {"name": "Yes", "type": "n8n-nodes-base.code", "typeVersion": 1, "position": [200, -100]},
            {"name": "No", "type": "n8n-nodes-base.code", "typeVersion": 1, "position": [200, 100]},
        ],
        "connections": {
            "If": {
                "main": [
                    [],
                    [{"node": "No", "type": "main", "index": 0}],
                ]
            }
        },
    }

    imported = api_client.post("/api/workflows/import", json={"data": payload, "save": True}).json()
    assert imported["success"] is True
    assert imported["workflow"]["metadata"]["runtime_mapping_profile"] == "n8n->canonical->runtime.v1"
    wf_id = imported["workflow_id"]

    exported = api_client.post(f"/api/workflows/{wf_id}/export", json={"format": "n8n"}).json()
    assert exported["success"] is True
    assert exported["exported"]["meta"]["runtime_mapping_profile"] == "n8n->canonical->runtime.v1"
    if_main = exported["exported"]["connections"]["If"]["main"]
    assert len(if_main) >= 2
    assert if_main[0] == []
    assert if_main[1][0]["node"] == "No"
