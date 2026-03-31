"""
MARKER_196.GW3.1: Admin endpoints for Agent Gateway management.

Internal-only endpoints for managing registered agents:
list, suspend, activate, rotate keys, view audit log.
"""

import hashlib
import secrets
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from src.api.middleware.auth import verify_agent_authorization
from src.orchestration.task_board import get_task_board

router = APIRouter(prefix="/api/gateway/admin", tags=["gateway-admin"])


def _verify_admin():
    """Internal admin guard — requires valid API key."""
    # For MVP: reuse the same auth middleware.
    # In production, add a separate admin-only check.
    return verify_agent_authorization


@router.get("/agents")
async def list_agents(
    status: Optional[str] = Query(None),
    agent: dict = Depends(_verify_admin()),
) -> Dict[str, Any]:
    """List all registered agents."""
    board = get_task_board()
    agents = board.list_agents(status=status)
    return {"success": True, "agents": agents, "count": len(agents)}


@router.post("/agents/{agent_id}/suspend")
async def suspend_agent(
    agent_id: str,
    agent: dict = Depends(_verify_admin()),
) -> Dict[str, Any]:
    """Suspend an agent (prevent further API access)."""
    board = get_task_board()
    db = board.db
    row = db.execute(
        "SELECT id, status FROM agents WHERE id = ?", (agent_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    db.execute("UPDATE agents SET status = 'suspended' WHERE id = ?", (agent_id,))
    db.commit()
    board.log_audit(agent_id=agent["id"], action="suspend_agent", task_id=agent_id)
    return {"success": True, "agent_id": agent_id, "status": "suspended"}


@router.post("/agents/{agent_id}/activate")
async def activate_agent(
    agent_id: str,
    agent: dict = Depends(_verify_admin()),
) -> Dict[str, Any]:
    """Reactivate a suspended agent."""
    board = get_task_board()
    db = board.db
    row = db.execute(
        "SELECT id, status FROM agents WHERE id = ?", (agent_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    db.execute("UPDATE agents SET status = 'active' WHERE id = ?", (agent_id,))
    db.commit()
    board.log_audit(agent_id=agent["id"], action="activate_agent", task_id=agent_id)
    return {"success": True, "agent_id": agent_id, "status": "active"}


@router.post("/agents/{agent_id}/rotate-key")
async def rotate_agent_key(
    agent_id: str,
    agent: dict = Depends(_verify_admin()),
) -> Dict[str, Any]:
    """Generate a new API key for an agent. Old key is invalidated."""
    board = get_task_board()
    db = board.db
    row = db.execute("SELECT id FROM agents WHERE id = ?", (agent_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")

    new_key = f"vetka_{secrets.token_urlsafe(32)}"
    new_hash = hashlib.sha256(new_key.encode()).hexdigest()
    db.execute("UPDATE agents SET api_key_hash = ? WHERE id = ?", (new_hash, agent_id))
    db.commit()
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
    action: Optional[str] = Query(None),
    agent: dict = Depends(_verify_admin()),
) -> Dict[str, Any]:
    """View audit log entries (paginated)."""
    board = get_task_board()
    db = board.db

    where_parts = []
    params = []
    if agent_id:
        where_parts.append("agent_id = ?")
        params.append(agent_id)
    if action:
        where_parts.append("action = ?")
        params.append(action)

    where_clause = "WHERE " + " AND ".join(where_parts) if where_parts else ""

    rows = db.execute(
        f"SELECT * FROM audit_log {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [limit, offset],
    ).fetchall()

    total = db.execute(
        f"SELECT COUNT(*) FROM audit_log {where_clause}", params
    ).fetchone()[0]

    return {
        "success": True,
        "entries": [dict(r) for r in rows],
        "count": len(rows),
        "total": total,
        "offset": offset,
        "limit": limit,
    }
