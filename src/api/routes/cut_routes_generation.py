"""
MARKER_B98 — Generation Control API endpoints.
FastAPI routes for AI media generation pipeline: submit jobs, poll status,
cancel, accept results, manage budget limits, and list provider capabilities.

@status: active
@phase: B98
@task: tb_1774432033_1
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

generation_router = APIRouter(tags=["CUT-Generation"])

# ---------------------------------------------------------------------------
# Lazy singleton for GenerationService
# ---------------------------------------------------------------------------

_generation_service = None


def _get_service():
    global _generation_service
    if _generation_service is None:
        from src.services.cut_generation_service import GenerationService
        _generation_service = GenerationService()
    return _generation_service


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class GenerateSubmitRequest(BaseModel):
    provider: str
    prompt: str
    duration_sec: float = Field(default=5.0, gt=0)
    image_url: Optional[str] = None
    model: Optional[str] = None
    resolution: Optional[str] = "1280x768"


class GenerateCancelRequest(BaseModel):
    job_id: str


class GenerateAcceptRequest(BaseModel):
    job_id: str
    output_dir: Optional[str] = None


class BudgetLimitRequest(BaseModel):
    daily_limit: Optional[float] = None
    monthly_limit: Optional[float] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@generation_router.post("/generate/submit")
async def submit_generation(req: GenerateSubmitRequest) -> dict[str, Any]:
    """Submit a generation job. Returns 402 if over budget limit."""
    service = _get_service()

    params = {
        "provider": req.provider,
        "prompt": req.prompt,
        "duration_sec": req.duration_sec,
        "image_url": req.image_url,
        "model": req.model,
        "resolution": req.resolution,
    }

    # Budget guard — estimate cost before submitting
    try:
        provider = service.get_provider(req.provider)
        budget = service.budget
        cost = await provider.estimate_cost(params)
        allowed, reason = budget.can_spend(cost)
        if not allowed:
            raise HTTPException(status_code=402, detail=reason)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Budget pre-check failed, proceeding: %s", exc)

    try:
        job = await service.submit_job(req.provider, params)
        return job
    except Exception as exc:
        logger.exception("submit_job failed")
        raise HTTPException(status_code=500, detail=str(exc))


@generation_router.get("/generate/status/{job_id}")
async def get_generation_status(job_id: str) -> dict[str, Any]:
    """Return current status of a generation job."""
    service = _get_service()
    try:
        status = await service.get_job_status(job_id)
        if status is None:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        return status
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("get_job_status failed")
        raise HTTPException(status_code=500, detail=str(exc))


@generation_router.get("/generate/queue")
async def get_generation_queue() -> dict[str, Any]:
    """Return all active generation jobs."""
    service = _get_service()
    try:
        jobs = service.get_active_jobs()
        return {"jobs": jobs, "count": len(jobs)}
    except Exception as exc:
        logger.exception("list_active_jobs failed")
        raise HTTPException(status_code=500, detail=str(exc))


@generation_router.post("/generate/cancel")
async def cancel_generation(req: GenerateCancelRequest) -> dict[str, Any]:
    """Cancel a pending or running generation job."""
    service = _get_service()
    try:
        result = await service.cancel_job(req.job_id)
        return result
    except Exception as exc:
        logger.exception("cancel_job failed")
        raise HTTPException(status_code=500, detail=str(exc))


@generation_router.post("/generate/accept")
async def accept_generation(req: GenerateAcceptRequest) -> dict[str, Any]:
    """Accept a completed generation job — downloads result to output_dir."""
    service = _get_service()
    try:
        result = await service.accept_job(req.job_id)
        output_path = result.get("output_path", "")
        return {"job_id": req.job_id, "output_path": str(output_path)}
    except Exception as exc:
        logger.exception("accept_job failed")
        raise HTTPException(status_code=500, detail=str(exc))


@generation_router.get("/generate/providers")
async def list_providers() -> dict[str, Any]:
    """List available generation providers with their capabilities."""
    service = _get_service()
    try:
        providers = service.list_providers()
        return {"providers": providers}
    except Exception as exc:
        logger.exception("list_providers failed")
        raise HTTPException(status_code=500, detail=str(exc))


@generation_router.get("/generate/budget")
async def get_budget_summary() -> dict[str, Any]:
    """Return current budget usage summary (daily/monthly spend and limits)."""
    service = _get_service()
    try:
        summary = service.budget.get_summary()
        return summary
    except Exception as exc:
        logger.exception("get_budget_summary failed")
        raise HTTPException(status_code=500, detail=str(exc))


@generation_router.post("/generate/budget/limits")
async def update_budget_limits(req: BudgetLimitRequest) -> dict[str, Any]:
    """Update daily and/or monthly budget limits."""
    service = _get_service()
    try:
        service.budget.set_limits(
            daily_limit=req.daily_limit,
            monthly_limit=req.monthly_limit,
        )
        return service.budget.get_summary()
    except Exception as exc:
        logger.exception("update_budget_limits failed")
        raise HTTPException(status_code=500, detail=str(exc))


@generation_router.post("/generate/estimate")
async def estimate_generation_cost(req: GenerateSubmitRequest) -> dict[str, Any]:
    """Estimate cost for a generation job without submitting it."""
    service = _get_service()

    params = {
        "provider": req.provider,
        "prompt": req.prompt,
        "duration_sec": req.duration_sec,
        "image_url": req.image_url,
        "model": req.model,
        "resolution": req.resolution,
    }

    try:
        provider = service.get_provider(req.provider)
        cost = await provider.estimate_cost(params)
        budget = service.budget
        allowed, reason = budget.can_spend(cost)
        return {
            "estimated_cost": cost,
            "within_budget": allowed,
            "reason": reason if not allowed else None,
            "provider": req.provider,
        }
    except Exception as exc:
        logger.exception("estimate_cost failed")
        raise HTTPException(status_code=500, detail=str(exc))
