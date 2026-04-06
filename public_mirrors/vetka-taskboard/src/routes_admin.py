"""
Admin endpoints for Agent Gateway management.

Internal-only endpoints for managing registered agents:
list, suspend, activate, rotate keys, view audit log.

@license MIT
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from .auth import verify_agent_authorization
from .taskboard import get_task_board

router = APIRouter(prefix="/api/gateway/admin", tags=["gateway-admin"])


@router.get("/agents")
async def list_agents(
    status: Optional[str] = Query(None),
    agent: dict = Depends(verify_agent_authorization),
) -> Dict[str, Any]:
    """List all registered agents."""
    board = get_task_board()
    agents = board.list_agents()
    if status:
        agents = [a for a in agents if a.get("status") == status]
    return {"success": True, "agents": agents, "count": len(agents)}


@router.post("/agents/{agent_id}/suspend")
async def suspend_agent(
    agent_id: str,
    agent: dict = Depends(verify_agent_authorization),
) -> Dict[str, Any]:
    """Suspend an agent (prevent further API access)."""
    board = get_task_board()
    if not board.suspend_agent(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    board.log_audit(agent_id=agent["id"], action="suspend_agent", task_id=agent_id)
    return {"success": True, "agent_id": agent_id, "status": "suspended"}


@router.post("/agents/{agent_id}/activate")
async def activate_agent(
    agent_id: str,
    agent: dict = Depends(verify_agent_authorization),
) -> Dict[str, Any]:
    """Reactivate a suspended agent."""
    board = get_task_board()
    if not board.activate_agent(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    board.log_audit(agent_id=agent["id"], action="activate_agent", task_id=agent_id)
    return {"success": True, "agent_id": agent_id, "status": "active"}


@router.post("/agents/{agent_id}/rotate-key")
async def rotate_agent_key(
    agent_id: str,
    agent: dict = Depends(verify_agent_authorization),
) -> Dict[str, Any]:
    """Generate a new API key for an agent. Old key is invalidated."""
    board = get_task_board()
    new_key = board.rotate_agent_key(agent_id)
    if not new_key:
        raise HTTPException(status_code=404, detail="Agent not found")
    board.log_audit(agent_id=agent["id"], action="rotate_key", task_id=agent_id)
    return {
        "success": True,
        "agent_id": agent_id,
        "api_key": new_key,
        "message": "New API key generated. Old key is now invalid.",
    }


@router.get("/audit")
async def get_audit_log(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    agent_id: Optional[str] = Query(None),
    agent: dict = Depends(verify_agent_authorization),
) -> Dict[str, Any]:
    """View audit log entries (paginated)."""
    board = get_task_board()
    entries = board.get_audit_log(agent_id=agent_id, limit=limit, offset=offset)
    return {
        "success": True,
        "entries": entries,
        "count": len(entries),
        "offset": offset,
        "limit": limit,
    }
