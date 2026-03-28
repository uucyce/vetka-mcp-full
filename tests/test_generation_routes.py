"""
MARKER_GEN-ROUTES — Tests for /api/cut/generate/* endpoints.

Validates the API contract used by GenerationControlPanel (Alpha's frontend):
  POST   /api/cut/generate/submit
  GET    /api/cut/generate/status/{job_id}
  POST   /api/cut/generate/cancel/{job_id}
  POST   /api/cut/generate/accept/{job_id}
  POST   /api/cut/generate/reject/{job_id}
  GET    /api/cut/generate/queue
  GET    /api/cut/generate/history
  GET    /api/cut/generate/providers
  POST   /api/cut/generate/test-connection
  POST   /api/cut/generate/estimate-cost
  GET    /api/cut/generate/budget
  POST   /api/cut/generate/budget/limits

@phase GENERATION_CONTROL
@task tb_1774689673_97753_1
"""
from __future__ import annotations

import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Path setup — ensure worktree src/ is importable
# ---------------------------------------------------------------------------
_ROOT = os.path.dirname(os.path.dirname(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


# ---------------------------------------------------------------------------
# Helpers — build a minimal GenerationService mock
# ---------------------------------------------------------------------------

def _make_service(
    *,
    job_status: dict | None = None,
    active_jobs: list | None = None,
    providers: list | None = None,
    cancel_ok: bool = True,
    accept_result: dict | None = None,
):
    """Return a mock GenerationService with sensible defaults."""
    svc = MagicMock()
    svc.get_job_status.return_value = job_status
    svc.get_active_jobs.return_value = active_jobs or []
    svc.list_providers.return_value = providers or [{"name": "runway"}, {"name": "kling"}]
    svc.cancel_job = AsyncMock(return_value=cancel_ok)
    svc.accept_job = AsyncMock(return_value=accept_result or {"output_url": "/result/out.mp4"})
    svc.submit_job = AsyncMock(return_value={"job_id": "test-job-123"})

    # budget mock
    svc.budget.can_spend.return_value = (True, "ok")
    svc.budget.record_spend.return_value = None
    svc.budget.get_summary.return_value = {
        "daily_spend_usd": 0.0,
        "daily_limit_usd": 10.0,
        "daily_remaining_usd": 10.0,
        "monthly_spend_usd": 0.0,
        "monthly_limit_usd": 200.0,
        "monthly_remaining_usd": 200.0,
        "alert_threshold": 0.8,
        "total_jobs": 0,
    }
    svc.budget.set_limits.return_value = None

    # provider mock for test-connection / estimate-cost
    mock_provider = MagicMock()
    mock_provider.test_connection = AsyncMock(return_value=True)
    mock_provider.estimate_cost = AsyncMock(return_value=0.05)
    svc.get_provider.return_value = mock_provider

    # _job_store for reject
    svc._job_store = MagicMock()
    svc._job_store.update.return_value = None

    return svc


# ---------------------------------------------------------------------------
# Import routes after path is set
# ---------------------------------------------------------------------------

from src.api.routes.cut_routes_generation import generation_router  # noqa: E402


# ---------------------------------------------------------------------------
# FastAPI TestClient
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """FastAPI test client with generation_router mounted."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(generation_router)
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_svc():
    """Ensure lazy singleton is reset between tests."""
    import src.api.routes.cut_routes_generation as mod
    original = mod._svc
    yield
    mod._svc = original


def _inject_svc(svc):
    """Inject a mock service into the module's lazy singleton."""
    import src.api.routes.cut_routes_generation as mod
    mod._svc = svc


# ===========================================================================
# POST /generate/submit
# ===========================================================================

class TestSubmit:
    def test_submit_returns_job_id(self, client):
        svc = _make_service()
        _inject_svc(svc)
        resp = client.post("/generate/submit", json={
            "provider_id": "runway",
            "prompt": "A sunset over the ocean",
            "params": {"duration": 5},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data

    def test_submit_requires_prompt(self, client):
        svc = _make_service()
        _inject_svc(svc)
        resp = client.post("/generate/submit", json={
            "provider_id": "runway",
            "prompt": "",  # too short (min_length=1)
        })
        assert resp.status_code == 422

    def test_submit_with_reference_frame(self, client):
        svc = _make_service()
        _inject_svc(svc)
        resp = client.post("/generate/submit", json={
            "provider_id": "flux",
            "prompt": "A portrait",
            "params": {},
            "reference_frame": "data:image/jpeg;base64,/9j/...",
        })
        assert resp.status_code == 200
        # reference_frame should be in params passed to submit_job
        call_args = svc.submit_job.call_args
        assert call_args is not None

    def test_submit_budget_exceeded_returns_402(self, client):
        svc = _make_service()
        svc.budget.can_spend.return_value = (False, "Daily limit exceeded")
        _inject_svc(svc)
        resp = client.post("/generate/submit", json={
            "provider_id": "runway",
            "prompt": "Long expensive video",
            "params": {"duration": 120},
        })
        assert resp.status_code == 402

    def test_submit_unknown_provider_returns_400(self, client):
        svc = _make_service()
        svc.get_provider.side_effect = KeyError("no_such_provider")
        svc.submit_job = AsyncMock(side_effect=KeyError("no_such_provider"))
        _inject_svc(svc)
        resp = client.post("/generate/submit", json={
            "provider_id": "no_such_provider",
            "prompt": "test",
        })
        assert resp.status_code == 400


# ===========================================================================
# GET /generate/status/{job_id}
# ===========================================================================

class TestStatus:
    def test_status_returns_job_fields(self, client):
        svc = _make_service(job_status={
            "job_id": "abc",
            "status": "generating",
            "progress": 0.4,
            "eta_sec": 8,
            "output_url": None,
        })
        _inject_svc(svc)
        resp = client.get("/generate/status/abc")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "generating"
        assert data["progress"] == pytest.approx(0.4)
        assert data["eta_sec"] == 8
        assert data["job_id"] == "abc"

    def test_status_404_if_job_missing(self, client):
        svc = _make_service(job_status=None)
        _inject_svc(svc)
        resp = client.get("/generate/status/nonexistent")
        assert resp.status_code == 404

    def test_status_completed_has_result_url(self, client):
        svc = _make_service(job_status={
            "job_id": "done-1",
            "status": "completed",
            "progress": 1.0,
            "eta_sec": 0,
            "output_url": "/api/cut/generate/result/done-1/output.mp4",
        })
        _inject_svc(svc)
        resp = client.get("/generate/status/done-1")
        assert resp.status_code == 200
        assert resp.json()["result_url"] is not None


# ===========================================================================
# POST /generate/cancel/{job_id}
# ===========================================================================

class TestCancel:
    def test_cancel_success(self, client):
        svc = _make_service(cancel_ok=True)
        _inject_svc(svc)
        resp = client.post("/generate/cancel/job-99")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_cancel_404_if_job_not_found(self, client):
        svc = _make_service(cancel_ok=False)
        _inject_svc(svc)
        resp = client.post("/generate/cancel/nonexistent")
        assert resp.status_code == 404


# ===========================================================================
# POST /generate/accept/{job_id}
# ===========================================================================

class TestAccept:
    def test_accept_success(self, client):
        svc = _make_service(
            job_status={"job_id": "j1", "status": "completed", "cost_usd": 0.05, "provider": "runway"},
            accept_result={"output_url": "/result/out.mp4"},
        )
        _inject_svc(svc)
        resp = client.post("/generate/accept/j1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["job_id"] == "j1"

    def test_accept_404_if_not_completed(self, client):
        svc = _make_service(job_status={"job_id": "j2", "status": "generating"})
        svc.accept_job = AsyncMock(side_effect=ValueError("not completed"))
        _inject_svc(svc)
        resp = client.post("/generate/accept/j2")
        assert resp.status_code == 404


# ===========================================================================
# POST /generate/reject/{job_id}
# ===========================================================================

class TestReject:
    def test_reject_completed_job(self, client):
        svc = _make_service(job_status={"job_id": "j3", "status": "completed"})
        _inject_svc(svc)
        resp = client.post("/generate/reject/j3")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        svc._job_store.update.assert_called_once_with("j3", status="rejected")

    def test_reject_404_if_missing(self, client):
        svc = _make_service(job_status=None)
        _inject_svc(svc)
        resp = client.post("/generate/reject/missing")
        assert resp.status_code == 404

    def test_reject_409_if_not_completed(self, client):
        svc = _make_service(job_status={"job_id": "j4", "status": "generating"})
        _inject_svc(svc)
        resp = client.post("/generate/reject/j4")
        assert resp.status_code == 409


# ===========================================================================
# GET /generate/queue
# ===========================================================================

class TestQueue:
    def test_queue_returns_active_jobs(self, client):
        jobs = [
            {"job_id": "a", "status": "queued"},
            {"job_id": "b", "status": "generating"},
        ]
        svc = _make_service(active_jobs=jobs)
        _inject_svc(svc)
        resp = client.get("/generate/queue")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert len(data["jobs"]) == 2

    def test_queue_empty(self, client):
        svc = _make_service(active_jobs=[])
        _inject_svc(svc)
        resp = client.get("/generate/queue")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0


# ===========================================================================
# GET /generate/history
# ===========================================================================

class TestHistory:
    def test_history_filters_terminal_jobs(self, client):
        all_jobs = [
            {"job_id": "x1", "status": "completed", "created_at": 1000},
            {"job_id": "x2", "status": "queued", "created_at": 900},
            {"job_id": "x3", "status": "failed", "created_at": 800},
            {"job_id": "x4", "status": "cancelled", "created_at": 700},
            {"job_id": "x5", "status": "accepted", "created_at": 600},
            {"job_id": "x6", "status": "rejected", "created_at": 500},
        ]
        svc = _make_service()
        svc._job_store.get_all.return_value = all_jobs
        _inject_svc(svc)
        resp = client.get("/generate/history")
        assert resp.status_code == 200
        data = resp.json()
        # Only terminal jobs: completed, failed, cancelled, accepted, rejected (5)
        assert data["count"] == 5
        returned_ids = {j["job_id"] for j in data["jobs"]}
        assert "x2" not in returned_ids  # queued is not history


# ===========================================================================
# GET /generate/providers
# ===========================================================================

class TestProviders:
    def test_providers_list(self, client):
        svc = _make_service(providers=[{"name": "runway"}, {"name": "kling"}, {"name": "flux"}])
        _inject_svc(svc)
        resp = client.get("/generate/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert "providers" in data
        assert len(data["providers"]) == 3


# ===========================================================================
# POST /generate/test-connection
# ===========================================================================

class TestConnection:
    def test_test_connection_success(self, client):
        svc = _make_service()
        _inject_svc(svc)
        resp = client.post("/generate/test-connection", json={"provider_id": "runway"})
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_test_connection_unknown_provider_returns_true(self, client):
        """Unknown provider falls back to mock success (per route logic)."""
        svc = _make_service()
        svc.get_provider.side_effect = KeyError("unknown")
        _inject_svc(svc)
        resp = client.post("/generate/test-connection", json={"provider_id": "unknown_provider"})
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_test_connection_failure_returns_false(self, client):
        svc = _make_service()
        svc.get_provider.return_value.test_connection = AsyncMock(side_effect=Exception("network error"))
        _inject_svc(svc)
        resp = client.post("/generate/test-connection", json={"provider_id": "runway"})
        assert resp.status_code == 200
        assert resp.json()["success"] is False


# ===========================================================================
# POST /generate/estimate-cost
# ===========================================================================

class TestEstimateCost:
    def test_estimate_cost_returns_usd(self, client):
        svc = _make_service()
        svc.get_provider.return_value.estimate_cost = AsyncMock(return_value=0.25)
        _inject_svc(svc)
        resp = client.post("/generate/estimate-cost", json={
            "provider_id": "runway",
            "prompt": "A 10 second clip",
            "params": {"duration": 10},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "estimated_usd" in data
        assert data["estimated_usd"] == pytest.approx(0.25, abs=0.001)

    def test_estimate_cost_unknown_provider_returns_zero(self, client):
        svc = _make_service()
        svc.get_provider.side_effect = KeyError("no_such")
        _inject_svc(svc)
        resp = client.post("/generate/estimate-cost", json={
            "provider_id": "no_such",
            "prompt": "test",
        })
        assert resp.status_code == 200
        assert resp.json()["estimated_usd"] == 0.0

    def test_estimate_cost_local_provider_returns_zero(self, client):
        svc = _make_service()
        svc.get_provider.return_value.estimate_cost = AsyncMock(return_value=0.0)
        _inject_svc(svc)
        resp = client.post("/generate/estimate-cost", json={
            "provider_id": "flux",
            "prompt": "local model",
            "params": {},
        })
        assert resp.status_code == 200
        assert resp.json()["estimated_usd"] == 0.0


# ===========================================================================
# GET /generate/budget
# ===========================================================================

class TestBudget:
    def test_budget_summary_keys(self, client):
        svc = _make_service()
        _inject_svc(svc)
        resp = client.get("/generate/budget")
        assert resp.status_code == 200
        data = resp.json()
        assert "daily_spend_usd" in data
        assert "daily_limit_usd" in data
        assert "monthly_spend_usd" in data
        assert "monthly_limit_usd" in data


# ===========================================================================
# POST /generate/budget/limits
# ===========================================================================

class TestBudgetLimits:
    def test_set_daily_limit(self, client):
        svc = _make_service()
        _inject_svc(svc)
        resp = client.post("/generate/budget/limits", json={"daily_limit": 25.0})
        assert resp.status_code == 200
        svc.budget.set_limits.assert_called_once_with(daily=25.0, monthly=None)

    def test_set_monthly_limit(self, client):
        svc = _make_service()
        _inject_svc(svc)
        resp = client.post("/generate/budget/limits", json={"monthly_limit": 500.0})
        assert resp.status_code == 200
        svc.budget.set_limits.assert_called_once_with(daily=None, monthly=500.0)

    def test_set_both_limits(self, client):
        svc = _make_service()
        _inject_svc(svc)
        resp = client.post("/generate/budget/limits", json={"daily_limit": 15.0, "monthly_limit": 300.0})
        assert resp.status_code == 200
        svc.budget.set_limits.assert_called_once_with(daily=15.0, monthly=300.0)
