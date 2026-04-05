"""
MARKER_GEN-ROUTES — /api/cut/generate/* endpoints for GenerationControlPanel.

Mirrors FCP7 Deck Control (Ch.50-51) — submit/poll/cancel/accept lifecycle.
Compatible with useGenerationControlStore state machine (Alpha, tb_1774432024_1).

Request/response contracts match Alpha's frontend exactly:
  POST   /generate/submit              {provider_id, prompt, params, reference_frame?}
  GET    /generate/status/{job_id}     → {job_id, status, progress, eta_sec?, result_url?}
  POST   /generate/cancel/{job_id}     → {success}
  POST   /generate/accept/{job_id}     → {success, job_id, result_url?}
  POST   /generate/reject/{job_id}     → {success}
  GET    /generate/queue               → {jobs, count}
  GET    /generate/history             → {jobs, count}
  GET    /generate/providers           → {providers}
  POST   /generate/test-connection     {provider_id} → {success}
  POST   /generate/estimate-cost       {provider_id, prompt, params} → {estimated_usd}
  GET    /generate/budget              → budget summary
  POST   /generate/budget/limits       {daily_limit?, monthly_limit?}

@phase GENERATION_CONTROL
@task tb_1774689673_97753_1
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

generation_router = APIRouter(tags=["CUT-Generation"])

# ---------------------------------------------------------------------------
# Lazy singleton — avoids import-time errors if deps missing
# ---------------------------------------------------------------------------

_svc = None


def _get_service():
    global _svc
    if _svc is None:
        from src.services.cut_generation_service import GenerationService
        _svc = GenerationService()
    return _svc


# ---------------------------------------------------------------------------
# Pydantic models — matching Alpha's frontend exactly
# ---------------------------------------------------------------------------

class SubmitRequest(BaseModel):
    """Matches GenerationTransportBar.tsx submit body."""
    provider_id: str
    prompt: str = Field(..., min_length=1, max_length=4000)
    params: dict = Field(default_factory=dict)
    reference_frame: Optional[str] = None   # base64 JPEG data URL


class TestConnectionRequest(BaseModel):
    """Matches GenerationControlPanel.tsx test-connection body."""
    provider_id: str


class EstimateCostRequest(BaseModel):
    """Matches GenerationPromptInput.tsx estimate-cost body."""
    provider_id: str
    prompt: str = ""
    params: dict = Field(default_factory=dict)


class BudgetLimitRequest(BaseModel):
    daily_limit: Optional[float] = None
    monthly_limit: Optional[float] = None


# ---------------------------------------------------------------------------
# POST /generate/submit
# ---------------------------------------------------------------------------

@generation_router.post("/generate/submit")
async def submit_generation(req: SubmitRequest) -> dict[str, Any]:
    """
    Submit a generation job.
    Returns {job_id} immediately — client polls /status/{job_id}.
    Returns 402 if over budget.
    """
    svc = _get_service()

    # Map frontend {provider_id, prompt, params} → service submit format
    provider_name = req.provider_id
    params = dict(req.params)
    params["prompt"] = req.prompt
    if req.reference_frame:
        params["reference_frame"] = req.reference_frame

    # Budget guard
    try:
        provider = svc.get_provider(provider_name)
        estimated = await provider.estimate_cost(params)
        allowed, reason = svc.budget.can_spend(estimated)
        if not allowed:
            raise HTTPException(status_code=402, detail=reason)
    except HTTPException:
        raise
    except KeyError:
        # Unknown provider — proceed with mock (no cost guard needed)
        pass
    except Exception as exc:
        logger.warning("Budget pre-check skipped: %s", exc)

    try:
        job = await svc.submit_job(provider_name, params)
        return {"job_id": job["job_id"]}
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_name!r}")
    except Exception as exc:
        logger.exception("submit_job failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /generate/status/{job_id}
# ---------------------------------------------------------------------------

@generation_router.get("/generate/status/{job_id}")
async def get_generation_status(job_id: str) -> dict[str, Any]:
    """
    Poll job status. Called every 2s by useGenerationControlStore.
    Returns: {status, progress, eta_sec?, result_url?}
    """
    svc = _get_service()
    job = svc.get_job_status(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return {
        "job_id": job.get("job_id", job_id),
        "status": job.get("status", "generating"),
        "progress": float(job.get("progress", 0)),
        "eta_sec": job.get("eta_sec"),
        "result_url": job.get("output_url") or job.get("result_url"),
    }


# ---------------------------------------------------------------------------
# POST /generate/cancel/{job_id}
# ---------------------------------------------------------------------------

@generation_router.post("/generate/cancel/{job_id}")
async def cancel_generation(job_id: str) -> dict[str, Any]:
    """Cancel a queued or generating job (K key in transport bar)."""
    svc = _get_service()
    ok = await svc.cancel_job(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found or already finished")
    return {"success": True, "job_id": job_id}


# ---------------------------------------------------------------------------
# POST /generate/accept/{job_id}
# ---------------------------------------------------------------------------

@generation_router.post("/generate/accept/{job_id}")
async def accept_generation(job_id: str) -> dict[str, Any]:
    """
    Accept result → records spend, marks accepted.
    Frontend: ACCEPTED → IMPORTING → IDLE.
    """
    svc = _get_service()
    try:
        updated = await svc.accept_job(job_id)
        # Record spend in budget
        job = svc.get_job_status(job_id)
        if job:
            cost = job.get("cost_usd", 0.0)
            if cost:
                svc.budget.record_spend(cost, job.get("provider", ""), job_id)
        return {
            "success": True,
            "job_id": job_id,
            "result_url": (updated or {}).get("output_url"),
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("accept_job failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# POST /generate/reject/{job_id}
# ---------------------------------------------------------------------------

@generation_router.post("/generate/reject/{job_id}")
async def reject_generation(job_id: str) -> dict[str, Any]:
    """
    Reject result — store transitions back to CONFIGURING (prompt preserved).
    Uses job_store.update directly since service has no reject method.
    """
    svc = _get_service()
    job = svc.get_job_status(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    if job.get("status") != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot reject job in state {job.get('status')!r}",
        )
    svc._job_store.update(job_id, status="rejected")
    logger.info("Generation job %s rejected", job_id)
    return {"success": True, "job_id": job_id}


# ---------------------------------------------------------------------------
# GET /generate/queue
# ---------------------------------------------------------------------------

@generation_router.get("/generate/queue")
async def get_generation_queue() -> dict[str, Any]:
    """List active (queued + generating) jobs."""
    svc = _get_service()
    jobs = svc.get_active_jobs()
    return {"jobs": jobs, "count": len(jobs)}


# ---------------------------------------------------------------------------
# GET /generate/history
# ---------------------------------------------------------------------------

@generation_router.get("/generate/history")
async def get_generation_history() -> dict[str, Any]:
    """List completed/accepted/rejected/failed/cancelled jobs."""
    svc = _get_service()
    terminal = {"completed", "accepted", "rejected", "failed", "cancelled"}
    all_jobs = svc._job_store.get_all()
    history = [j for j in all_jobs if j.get("status") in terminal]
    history.sort(key=lambda j: j.get("created_at", 0), reverse=True)
    return {"jobs": history, "count": len(history)}


# ---------------------------------------------------------------------------
# GET /generate/providers
# ---------------------------------------------------------------------------

@generation_router.get("/generate/providers")
async def list_generation_providers() -> dict[str, Any]:
    """List available providers. Used by ProviderSelector."""
    svc = _get_service()
    try:
        providers = svc.list_providers()
        return {"providers": providers}
    except Exception as exc:
        logger.exception("list_providers failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# POST /generate/test-connection
# ---------------------------------------------------------------------------

@generation_router.post("/generate/test-connection")
async def test_connection(req: TestConnectionRequest) -> dict[str, Any]:
    """
    Test provider connectivity / API key.
    Called by GenerationControlPanel on CONNECTING state entry.
    Returns {success: bool}.
    """
    svc = _get_service()
    try:
        provider = svc.get_provider(req.provider_id)
        ok = await provider.test_connection()
        return {"success": ok}
    except KeyError:
        # Provider not configured — return success for local/mock providers
        logger.info("Provider %r not in registry, returning mock success", req.provider_id)
        return {"success": True}
    except Exception as exc:
        logger.warning("test_connection failed for %s: %s", req.provider_id, exc)
        return {"success": False}


# ---------------------------------------------------------------------------
# POST /generate/estimate-cost
# ---------------------------------------------------------------------------

@generation_router.post("/generate/estimate-cost")
async def estimate_generation_cost(req: EstimateCostRequest) -> dict[str, Any]:
    """
    Live cost estimate — called debounced 500ms from GenerationPromptInput.
    Returns {estimated_usd}.
    """
    svc = _get_service()
    try:
        provider = svc.get_provider(req.provider_id)
        params = dict(req.params)
        params["prompt"] = req.prompt
        cost = await provider.estimate_cost(params)
        return {"estimated_usd": round(float(cost), 4)}
    except KeyError:
        return {"estimated_usd": 0.0}
    except Exception as exc:
        logger.warning("estimate_cost failed: %s", exc)
        return {"estimated_usd": 0.0}


# ---------------------------------------------------------------------------
# GET /generate/budget
# ---------------------------------------------------------------------------

@generation_router.get("/generate/budget")
async def get_budget_summary() -> dict[str, Any]:
    """Current spend tracking for BudgetSection in ProviderSettings."""
    svc = _get_service()
    try:
        return svc.budget.get_summary()
    except Exception as exc:
        logger.exception("get_budget_summary failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# POST /generate/budget/limits
# ---------------------------------------------------------------------------

@generation_router.post("/generate/budget/limits")
async def update_budget_limits(req: BudgetLimitRequest) -> dict[str, Any]:
    """Update daily/monthly budget limits."""
    svc = _get_service()
    try:
        svc.budget.set_limits(daily=req.daily_limit, monthly=req.monthly_limit)
        return svc.budget.get_summary()
    except Exception as exc:
        logger.exception("update_budget_limits failed")
        raise HTTPException(status_code=500, detail=str(exc))
