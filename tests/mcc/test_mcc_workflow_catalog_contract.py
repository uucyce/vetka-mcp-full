from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    import src.api.routes.mcc_routes as routes
    from src.api.routes.mcc_routes import router

    monkeypatch.setattr(
        routes,
        "_list_core_workflow_templates",
        lambda: [
            {
                "key": "ralph_loop",
                "id": "ralph_loop",
                "name": "Ralph Loop",
                "description": "Single-agent coding loop",
                "node_count": 4,
                "task_types": ["solo", "fix"],
                "complexity_range": [1, 5],
                "workflow_family": {"family": "ralph_loop", "version": "v1"},
            }
        ],
    )
    monkeypatch.setattr(
        routes,
        "_list_saved_workflow_templates",
        lambda: [
            {
                "id": "wf_saved_01",
                "name": "Saved Pipeline",
                "description": "User workflow",
                "node_count": 7,
                "edge_count": 6,
                "metadata": {"workflow_family": "custom_pipeline"},
            },
            {
                "id": "wf_n8n_01",
                "name": "Imported n8n Flow",
                "description": "Imported from n8n",
                "node_count": 5,
                "edge_count": 4,
                "metadata": {
                    "workflow_family": "n8n_ingest",
                    "imported_from": "n8n",
                    "workflow_bank": "n8n",
                },
            },
            {
                "id": "wf_comfy_01",
                "name": "Imported ComfyUI Graph",
                "description": "Imported from ComfyUI",
                "node_count": 9,
                "edge_count": 8,
                "metadata": {
                    "template_family": "comfy_image_gen",
                    "imported_from": "comfyui_graph",
                },
            },
            {
                "id": "wf_imported_01",
                "name": "Imported Generic Flow",
                "description": "Imported from custom source",
                "node_count": 3,
                "edge_count": 2,
                "metadata": {
                    "imported_from": "custom_json",
                },
            }
        ],
    )

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_mcc_workflow_catalog_exposes_expected_banks_and_normalized_rows(client: TestClient) -> None:
    """
    MARKER_167.STATS_WORKFLOW.CATALOG_API.V1
    MARKER_167.STATS_WORKFLOW.CATALOG_NORMALIZE.V1
    """
    resp = client.get("/api/mcc/workflow-catalog")
    assert resp.status_code == 200
    data = resp.json()

    assert data["success"] is True
    assert data["total_count"] == 5
    bank_keys = [row["key"] for row in data["banks"]]
    assert bank_keys == ["core", "saved", "n8n", "comfyui", "imported"]

    rows = data["workflows"]
    assert len(rows) == 5

    core = next(row for row in rows if row["bank"] == "core")
    assert core["id"] == "ralph_loop"
    assert core["title"] == "Ralph Loop"
    assert core["family"] == "ralph_loop"
    assert core["source"] == "core_library"
    assert core["compatibility_tags"] == ["fix", "solo"]
    assert core["metrics"]["node_count"] == 4

    saved = next(row for row in rows if row["bank"] == "saved")
    assert saved["id"] == "wf_saved_01"
    assert saved["title"] == "Saved Pipeline"
    assert saved["family"] == "custom_pipeline"
    assert saved["source"] == "saved_workflow_store"
    assert saved["compatibility_tags"] == []
    assert saved["metrics"]["node_count"] == 7
    assert saved["metrics"]["edge_count"] == 6

    n8n = next(row for row in rows if row["bank"] == "n8n")
    assert n8n["id"] == "wf_n8n_01"
    assert n8n["family"] == "n8n_ingest"

    comfy = next(row for row in rows if row["bank"] == "comfyui")
    assert comfy["id"] == "wf_comfy_01"
    assert comfy["family"] == "comfy_image_gen"

    imported = next(row for row in rows if row["bank"] == "imported")
    assert imported["id"] == "wf_imported_01"
    assert imported["family"] == "imported_workflow"


def test_mcc_workflow_catalog_keeps_external_banks_even_when_empty(client: TestClient) -> None:
    resp = client.get("/api/mcc/workflow-catalog")
    assert resp.status_code == 200
    data = resp.json()

    banks = {row["key"]: row for row in data["banks"]}
    assert banks["n8n"]["count"] == 1
    assert banks["comfyui"]["count"] == 1
    assert banks["imported"]["count"] == 1
    assert banks["n8n"]["available"] is True
    assert banks["comfyui"]["available"] is True
    assert banks["imported"]["available"] is True
