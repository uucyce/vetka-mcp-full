"""
VETKA Metrics Routes - FastAPI Version

@file metrics_routes.py
@status ACTIVE
@phase Phase 39.2
@lastAudit 2026-01-05

Metrics API routes.
Migrated from src/server/routes/metrics_routes.py (Flask Blueprint)

Changes from Flask version:
- Blueprint -> APIRouter
- current_app.config -> request.app.state
- return jsonify({}) -> return {}
- def -> async def
"""

from fastapi import APIRouter, HTTPException, Request


router = APIRouter(prefix="/api/metrics", tags=["metrics"])


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _get_metrics_components(request: Request) -> dict:
    """Get metrics components from app state."""
    return {
        'metrics_available': getattr(request.app.state, 'METRICS_AVAILABLE', False),
        'metrics_engine': getattr(request.app.state, 'metrics_engine', None),
        'model_router_available': getattr(request.app.state, 'MODEL_ROUTER_V2_AVAILABLE', False),
        'model_router': getattr(request.app.state, 'model_router', None),
        'feedback_loop_available': getattr(request.app.state, 'FEEDBACK_LOOP_V2_AVAILABLE', False),
        'feedback_loop': getattr(request.app.state, 'feedback_loop', None),
    }


# ============================================================
# ROUTES
# ============================================================

@router.get("/dashboard")
async def get_dashboard(request: Request):
    """
    Get complete metrics dashboard data.

    Returns aggregated metrics for the dashboard view.
    """
    components = _get_metrics_components(request)

    if not components['metrics_available'] or not components['metrics_engine']:
        raise HTTPException(status_code=503, detail="Metrics engine not available")

    try:
        return components['metrics_engine'].get_dashboard_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeline/{workflow_id}")
async def get_timeline(workflow_id: str, request: Request):
    """
    Get timeline for specific workflow.

    Args:
        workflow_id: The workflow ID to get timeline for
    """
    components = _get_metrics_components(request)

    if not components['metrics_available'] or not components['metrics_engine']:
        raise HTTPException(status_code=503, detail="Metrics engine not available")

    try:
        return components['metrics_engine'].get_timeline_data(workflow_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents")
async def get_agent_metrics(request: Request):
    """
    Get per-agent statistics.

    Returns metrics broken down by agent type (PM, Dev, QA, etc.).
    """
    components = _get_metrics_components(request)

    if not components['metrics_available'] or not components['metrics_engine']:
        raise HTTPException(status_code=503, detail="Metrics engine not available")

    try:
        return components['metrics_engine'].get_agent_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def get_model_metrics(request: Request):
    """
    Get model router statistics.

    Returns model usage statistics including calls, latency, and costs.
    """
    components = _get_metrics_components(request)

    if not components['model_router_available'] or not components['model_router']:
        raise HTTPException(status_code=503, detail="Model router not available")

    try:
        return components['model_router'].get_model_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers")
async def get_provider_metrics(request: Request):
    """
    Get provider health status.

    Returns health and availability info for each LLM provider.
    """
    components = _get_metrics_components(request)

    if not components['model_router_available'] or not components['model_router']:
        raise HTTPException(status_code=503, detail="Model router not available")

    try:
        return components['model_router'].get_provider_health()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback")
async def get_feedback_metrics(request: Request):
    """
    Get feedback loop statistics.

    Returns summary of user feedback and learning metrics.
    """
    components = _get_metrics_components(request)

    if not components['feedback_loop_available'] or not components['feedback_loop']:
        raise HTTPException(status_code=503, detail="Feedback loop not available")

    try:
        return components['feedback_loop'].get_feedback_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
