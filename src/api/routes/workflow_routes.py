"""
VETKA Workflow Routes - FastAPI Version

@file workflow_routes.py
@status ACTIVE
@phase Phase 39.6
@lastAudit 2026-01-05

Workflow history and stats API routes.
Migrated from src/server/routes/workflow_routes.py (Flask Blueprint)

Endpoints:
- GET /api/workflow/history - Get workflow history
- GET /api/workflow/stats - Get workflow statistics
- GET /api/workflow/{workflow_id} - Get specific workflow details

Changes from Flask version:
- Blueprint -> APIRouter
- request.args.get() -> Query()
- return jsonify({}) -> return {}
- def -> async def
"""

from fastapi import APIRouter, HTTPException, Request, Query


router = APIRouter(prefix="/api/workflow", tags=["workflow"])


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _get_orchestrator(request: Request):
    """Get orchestrator from app state."""
    flask_config = getattr(request.app.state, 'flask_config', {})
    get_orchestrator = flask_config.get('get_orchestrator')

    if not get_orchestrator:
        # Fallback to singleton
        try:
            from src.initialization.singletons import get_orchestrator as _get_orch
            return _get_orch()
        except Exception:
            return None

    return get_orchestrator()


# ============================================================
# ROUTES
# ============================================================

@router.get("/history")
async def get_workflow_history(
    limit: int = Query(10, description="Max history items"),
    request: Request = None
):
    """
    Get workflow history.

    Returns recent workflow executions with their results.
    """
    orchestrator = _get_orchestrator(request)

    if not orchestrator:
        return {'local_history': [], 'weaviate_history': [], 'note': 'Orchestrator not available'}

    try:
        history = orchestrator.get_workflow_history(limit)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_workflow_stats(request: Request):
    """
    Get workflow statistics.

    Returns aggregated agent statistics.
    """
    orchestrator = _get_orchestrator(request)

    if not orchestrator:
        return {'agents': {}, 'total_workflows': 0, 'note': 'Orchestrator not available'}

    try:
        stats = orchestrator.get_agent_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workflow_id}")
async def get_workflow_details(workflow_id: str, request: Request):
    """
    Get specific workflow details.

    Returns full workflow data including agent results.
    """
    orchestrator = _get_orchestrator(request)

    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")

    try:
        history = orchestrator.get_workflow_history(100)

        # Search in local history
        for item in history.get('local_history', []):
            if item.get('workflow_id') == workflow_id:
                return item

        # Search in Weaviate history
        for item in history.get('weaviate_history', []):
            if item.get('workflow_id') == workflow_id:
                return item

        raise HTTPException(status_code=404, detail="Workflow not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
