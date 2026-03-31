"""
MARKER_196.GW1.4: Agent Gateway API routes.

Public REST API for external agents (Gemini, Claude, GPT) to interact
with VETKA TaskBoard: register, claim tasks, submit results.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request

from src.api.middleware.auth import get_client_ip, verify_agent_authorization
from src.orchestration.task_board import get_task_board

router = APIRouter(prefix="/api/gateway", tags=["gateway"])


# ── Health ────────────────────────────────────────────────────────────


@router.get("/health")
async def gateway_health() -> Dict[str, Any]:
    """Public health check — no auth required."""
    return {"status": "ok", "service": "agent-gateway"}


# ── Agent Registration ───────────────────────────────────────────────


@router.post("/agents/register")
async def register_agent(
    body: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """Register a new external agent.

    Body:
        name: str (required) — human-readable agent name
        agent_type: str (required) — e.g. 'gemini', 'claude', 'gpt', 'custom'
        capabilities: list (optional) — e.g. ['python', 'typescript']
        model_tier: str (optional) — 'bronze', 'silver', 'gold'

    Returns agent info + API key (shown ONCE).
    """
    name = str(body.get("name") or "").strip()
    agent_type = str(body.get("agent_type") or "").strip()

    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if not agent_type:
        raise HTTPException(status_code=400, detail="agent_type is required")

    board = get_task_board()
    result = board.register_agent(
        name=name,
        agent_type=agent_type,
        capabilities=body.get("capabilities"),
        model_tier=body.get("model_tier"),
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500, detail=result.get("error", "registration failed")
        )

    agent = result["agent"]
    board.log_audit(
        agent_id=agent["id"],
        action="register",
        request_body=f"name={name}, type={agent_type}",
        response_status=200,
    )

    return {
        "success": True,
        "message": "Agent registered. Save your API key — it will not be shown again.",
        "agent": agent,
        "api_key": result["api_key"],
    }


@router.get("/agents/me")
async def get_my_agent(
    agent: dict = Depends(verify_agent_authorization),
) -> Dict[str, Any]:
    """Get current authenticated agent info."""
    return {"success": True, "agent": agent}


@router.post("/agents/{agent_id}/heartbeat")
async def agent_heartbeat(
    agent_id: str,
    agent: dict = Depends(verify_agent_authorization),
) -> Dict[str, Any]:
    """Prove liveness. Updates last_heartbeat timestamp."""
    if agent["id"] != agent_id:
        raise HTTPException(status_code=403, detail="Cannot heartbeat another agent")

    board = get_task_board()
    result = board.heartbeat_agent(agent_id)
    return result


# ── Task Operations ──────────────────────────────────────────────────


@router.get("/tasks")
async def list_gateway_tasks(
    status: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    agent: dict = Depends(verify_agent_authorization),
) -> Dict[str, Any]:
    """List available tasks.

    External agents can only see: id, title, description, priority,
    phase_type, tags, project_id — no internal fields.
    """
    board = get_task_board()
    tasks = board.list_tasks(status=status)

    # Filter by project_id if specified
    if project_id:
        tasks = [t for t in tasks if t.get("project_id") == project_id]

    # Only show claimable tasks (pending) or agent's own tasks
    my_id = agent["id"]
    visible = []
    for t in tasks:
        if t.get("status") == "pending":
            visible.append(t)
        elif t.get("assigned_to") == my_id:
            visible.append(t)

    # Strip internal fields
    safe_tasks = []
    for t in visible[:limit]:
        safe_tasks.append(
            {
                "id": t.get("id"),
                "title": t.get("title"),
                "description": t.get("description"),
                "priority": t.get("priority"),
                "phase_type": t.get("phase_type"),
                "tags": t.get("tags"),
                "project_id": t.get("project_id"),
                "status": t.get("status"),
                "complexity": t.get("complexity"),
            }
        )

    return {"success": True, "tasks": safe_tasks, "count": len(safe_tasks)}


@router.get("/tasks/{task_id}")
async def get_gateway_task(
    task_id: str,
    agent: dict = Depends(verify_agent_authorization),
) -> Dict[str, Any]:
    """Get single task details."""
    board = get_task_board()
    task = board.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    # Strip internal fields
    safe_task = {
        "id": task.get("id"),
        "title": task.get("title"),
        "description": task.get("description"),
        "priority": task.get("priority"),
        "phase_type": task.get("phase_type"),
        "tags": task.get("tags"),
        "project_id": task.get("project_id"),
        "status": task.get("status"),
        "complexity": task.get("complexity"),
        "allowed_paths": task.get("allowed_paths"),
        "completion_contract": task.get("completion_contract"),
        "architecture_docs": task.get("architecture_docs"),
        "recon_docs": task.get("recon_docs"),
        "implementation_hints": task.get("implementation_hints"),
    }

    board.log_audit(
        agent_id=agent["id"],
        action="get_task",
        task_id=task_id,
        response_status=200,
    )

    return {"success": True, "task": safe_task}


@router.post("/tasks/{task_id}/claim")
async def claim_gateway_task(
    task_id: str,
    agent: dict = Depends(verify_agent_authorization),
) -> Dict[str, Any]:
    """Claim a task for the authenticated agent."""
    board = get_task_board()
    result = board.claim_task(
        task_id,
        agent_name=agent["name"],
        agent_type=agent["agent_type"],
    )

    if not result.get("success"):
        board.log_audit(
            agent_id=agent["id"],
            action="claim_failed",
            task_id=task_id,
            response_status=400,
        )
        raise HTTPException(status_code=400, detail=result.get("error", "claim failed"))

    board.log_audit(
        agent_id=agent["id"],
        action="claim",
        task_id=task_id,
        response_status=200,
    )

    return result


@router.post("/tasks/{task_id}/complete")
async def complete_gateway_task(
    task_id: str,
    body: Dict[str, Any] = Body(...),
    agent: dict = Depends(verify_agent_authorization),
    request: Request = None,
) -> Dict[str, Any]:
    """Submit task completion.

    Body:
        commit_hash: str (required)
        commit_message: str (optional)
        branch: str (optional)
    """
    commit_hash = body.get("commit_hash")
    if not commit_hash:
        raise HTTPException(status_code=400, detail="commit_hash is required")

    board = get_task_board()
    result = board.complete_task(
        task_id,
        commit_hash=commit_hash,
        commit_message=body.get("commit_message"),
        branch=body.get("branch"),
        closed_by=agent["name"],
    )

    board.log_audit(
        agent_id=agent["id"],
        action="complete",
        task_id=task_id,
        request_body=f"commit_hash={commit_hash[:12]}...",
        response_status=200 if result.get("success") else 400,
        ip_address=get_client_ip(request) if request else None,
    )

    return result


@router.get("/my-tasks")
async def get_my_tasks(
    agent: dict = Depends(verify_agent_authorization),
) -> Dict[str, Any]:
    """Get tasks claimed by the authenticated agent."""
    board = get_task_board()
    tasks = board.list_tasks()
    my_tasks = [
        {
            "id": t.get("id"),
            "title": t.get("title"),
            "status": t.get("status"),
            "priority": t.get("priority"),
            "phase_type": t.get("phase_type"),
            "project_id": t.get("project_id"),
        }
        for t in tasks
        if t.get("assigned_to") == agent["id"]
    ]

    return {"success": True, "tasks": my_tasks, "count": len(my_tasks)}


# ── SSE Stream ───────────────────────────────────────────────────────


@router.get("/stream")
async def stream_events(
    request: Request,
    agent_id: Optional[str] = Query(None),
    task_id: Optional[str] = Query(None),
    agent: dict = Depends(verify_agent_authorization),
):
    """SSE stream for real-time task updates. Requires valid agent API key."""
    from src.services.gateway_sse import sse_stream as _sse_handler

    return await _sse_handler(
        request, agent_id=agent_id or agent.get("id"), task_id=task_id
    )
