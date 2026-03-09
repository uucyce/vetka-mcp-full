from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.cut_routes import router
from src.services.cut_mcp_job_store import get_cut_mcp_job_store


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_cut_job_cancel_marks_job_cancelled_when_still_queued():
    store = get_cut_mcp_job_store()
    job = store.create_job("timeline_init", {"project_id": "cut_demo"})
    client = _make_client()

    response = client.post(f"/api/cut/job/{job['job_id']}/cancel")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["schema_version"] == "cut_mcp_job_v1"
    assert payload["job"]["cancel_requested"] is True
    assert payload["job"]["state"] == "cancelled"
    assert payload["job"]["retry_count"] == 0
    assert payload["job"]["route_mode"] == "background"


def test_cut_job_cancel_unknown_job_returns_404():
    client = _make_client()

    response = client.post("/api/cut/job/does-not-exist/cancel")
    assert response.status_code == 404
