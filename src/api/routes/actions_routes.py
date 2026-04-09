# MARKER_183.5: Actions Search REST API
"""
Phase 183.5 — Actions Search REST API.

Endpoints:
  GET /api/actions/search — Semantic + filter search on ActionRegistry
  GET /api/actions/stats — ActionRegistry statistics
  GET /api/actions/run/{run_id} — All actions for a run
  GET /api/actions/session/{session_id} — All actions for a session

@status: ACTIVE
@phase: 183
@depends: src/orchestration/action_registry.py
"""

from fastapi import APIRouter, Query
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/actions", tags=["actions"])

# Lazy singleton — same registry as pipeline uses
_registry = None


def _get_registry():
    global _registry
    if _registry is None:
        from src.orchestration.action_registry import ActionRegistry
        _registry = ActionRegistry()
    return _registry


@router.get("/search")
async def search_actions(
    q: str = Query("", description="Semantic search query"),
    session_id: Optional[str] = Query(None, description="Filter by session_id"),
    run_id: Optional[str] = Query(None, description="Filter by run_id"),
    agent: Optional[str] = Query(None, description="Filter by agent (opus, cursor, dragon)"),
    action: Optional[str] = Query(None, description="Filter by action type (edit, read, create)"),
    file: Optional[str] = Query(None, description="Filter by file path (partial match)"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
):
    """Search actions via Qdrant semantic search or JSON fallback.

    Supports combined semantic query + exact filters.
    """
    registry = _get_registry()
    results = await registry.search_actions(
        query=q, limit=limit, session_id=session_id,
        run_id=run_id, agent=agent, action=action, file_path=file,
    )
    return {"results": results, "count": len(results)}


@router.get("/stats")
def get_stats():
    """ActionRegistry statistics."""
    registry = _get_registry()
    return registry.get_stats()


@router.get("/run/{run_id}")
def get_actions_for_run(run_id: str):
    """All actions for a specific pipeline run."""
    registry = _get_registry()
    actions = registry.get_actions_for_run(run_id)
    return {"run_id": run_id, "actions": actions, "count": len(actions)}


@router.get("/session/{session_id}")
def get_actions_for_session(session_id: str):
    """All actions for a specific session (heartbeat tick)."""
    registry = _get_registry()
    actions = registry.get_actions_for_session(session_id)
    return {"session_id": session_id, "actions": actions, "count": len(actions)}
