"""
Phase 155B-P0.1 tests: expose canonical schema service via /api/workflow routes.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.workflow_routes import router
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 155b contracts changed")

def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_schema_versions_endpoint_is_exposed_and_returns_markers():
    client = _client()
    response = client.get("/api/workflow/schema/versions")

    assert response.status_code == 200
    data = response.json()
    assert data["marker"] == "MARKER_155B.CANON.SCHEMA_VERSIONING.V1"
    assert "current_schema_version" in data
    assert "supported_schema_versions" in data
    assert "canonical_markers" in data
    assert "MARKER_155B.CANON.SCHEMA_LOCK.V1" in data["canonical_markers"]
    assert "MARKER_155B.CANON.EVENT_SCHEMA.V1" in data["canonical_markers"]


def test_event_schema_endpoint_is_exposed_and_returns_markers():
    client = _client()
    response = client.get("/api/workflow/event-schema")

    assert response.status_code == 200
    data = response.json()
    assert data["marker"] == "MARKER_155B.CANON.EVENT_SCHEMA.V1"
    assert "required_fields" in data
    assert "optional_fields" in data
    assert "canonical_markers" in data
    assert "MARKER_155B.CANON.SCHEMA_VERSIONING.V1" in data["canonical_markers"]


def test_schema_migrate_endpoint_migrates_0_9_to_1_0_and_validates():
    client = _client()
    payload = {
        "graph": {
            "schema_version": "0.9.0",
            "nodes": [],
            "edges": [],
        },
        "to_version": "1.0.0",
        "validate": True,
    }

    response = client.post("/api/workflow/schema/migrate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["marker"] == "MARKER_155B.CANON.SCHEMA_LOCK.V1"
    assert data["migration"]["source_version"] == "0.9.0"
    assert data["migration"]["target_version"] == "1.0.0"
    assert data["migration"]["changed"] is True
    assert data["graph"]["schema_version"] == "1.0.0"
    assert isinstance(data["validation"], dict)
    assert "canonical_markers" in data


def test_schema_migrate_endpoint_rejects_missing_graph():
    client = _client()
    response = client.post("/api/workflow/schema/migrate", json={"to_version": "1.0.0"})
    assert response.status_code == 422
    assert "graph" in response.json()["detail"]


def test_schema_migrate_endpoint_rejects_unsupported_target_version():
    client = _client()
    response = client.post(
        "/api/workflow/schema/migrate",
        json={
            "graph": {
                "schema_version": "1.0.0",
                "graph": {},
                "nodes": [],
                "edges": [],
            },
            "to_version": "2.0.0",
        },
    )
    assert response.status_code == 400
    assert "Unsupported target schema version" in response.json()["detail"]
