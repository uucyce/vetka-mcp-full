"""
MARKER_175.7.TASKBOARD.REST_API.V1
Generic TaskBoard API for multi-client integrations.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException, Query

from src.orchestration.taskboard_adapters import get_taskboard_adapter
from src.services.roadmap_task_sync import apply_task_profile_defaults
from src.services.mcc_project_registry import list_projects

router = APIRouter(prefix="/api/taskboard", tags=["taskboard"])

_CREATE_FIELDS = {
    "title",
    "description",
    "priority",
    "phase_type",
    "preset",
    "tags",
    "source",
    "created_by",
    "module",
    "primary_node_id",
    "affected_nodes",
    "workflow_id",
    "workflow_bank",
    "workflow_family",
    "workflow_selection_origin",
    "team_profile",
    "task_origin",
    "roadmap_id",
    "roadmap_node_id",
    "roadmap_lane",
    "roadmap_title",
    "ownership_scope",
    "allowed_paths",
    "owner_agent",
    "completion_contract",
    "verification_agent",
    "blocked_paths",
    "forbidden_scopes",
    "worktree_hint",
    "touch_policy",
    "overlap_risk",
    "depends_on_docs",
    "project_id",
    "project_lane",
    "parent_task_id",
    "architecture_docs",
    "recon_docs",
    "protocol_version",
    "require_closure_proof",
    "closure_tests",
    "closure_files",
    "allowed_tools",  # MARKER_201.TOOL_GUARD
}

_UPDATE_FIELDS = {
    "title",
    "description",
    "priority",
    "phase_type",
    "preset",
    "status",
    "tags",
    "module",
    "primary_node_id",
    "affected_nodes",
    "workflow_id",
    "workflow_bank",
    "workflow_family",
    "workflow_selection_origin",
    "team_profile",
    "task_origin",
    "roadmap_id",
    "roadmap_node_id",
    "roadmap_lane",
    "roadmap_title",
    "ownership_scope",
    "allowed_paths",
    "owner_agent",
    "completion_contract",
    "verification_agent",
    "blocked_paths",
    "forbidden_scopes",
    "worktree_hint",
    "touch_policy",
    "overlap_risk",
    "depends_on_docs",
    "project_id",
    "project_lane",
    "feedback",
    "result_status",
    "result_summary",
    "completed_at",
    "actor_agent",
}


def _resolve_adapter(adapter_name: Optional[str] = None):
    try:
        return get_taskboard_adapter(adapter_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _prepare_create_payload(body: Dict[str, Any]) -> Dict[str, Any]:
    payload = {key: value for key, value in body.items() if key in _CREATE_FIELDS}
    if body.get("profile") not in (None, ""):
        payload["profile"] = body.get("profile")
    try:
        return apply_task_profile_defaults(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# MARKER_189.5A: Check if project_id exists in registry
def _check_project_known(project_id: str) -> bool:
    """Return True if project_id is empty or exists in the registry."""
    if not project_id:
        return True
    result = list_projects(include_hidden=True)
    return any(
        str(p.get("project_id", "")) == project_id for p in result.get("projects", [])
    )


@router.post("/create")
async def create_task(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    title = str(body.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    adapter = _resolve_adapter(body.get("adapter"))
    payload = _prepare_create_payload(body)
    try:
        task = await adapter.create_task(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # MARKER_189.5A: Hint if project_id is unknown — let client prompt user to create it
    project_id = str(payload.get("project_id") or "").strip()
    project_known = _check_project_known(project_id)
    result: Dict[str, Any] = {
        "success": True,
        "adapter": adapter.adapter_name,
        "task": task,
    }
    if project_id and not project_known:
        result["project_unknown"] = True
        result["suggested_action"] = "create_project"
        result["suggested_project_id"] = project_id
    return result


@router.get("/list")
async def list_tasks(
    adapter: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> Dict[str, Any]:
    adapter_impl = _resolve_adapter(adapter)
    tasks = await adapter_impl.list_tasks({"status": status, "limit": limit})
    return {
        "success": True,
        "adapter": adapter_impl.adapter_name,
        "tasks": tasks,
        "count": len(tasks),
    }


@router.post("/dispatch")
async def dispatch_task(
    body: Optional[Dict[str, Any]] = Body(default=None),
) -> Dict[str, Any]:
    body = body or {}
    adapter = _resolve_adapter(body.get("adapter"))
    result = await adapter.dispatch_task(
        body.get("task_id"),
        chat_id=body.get("chat_id"),
        selected_key=body.get("selected_key"),
    )
    result = dict(result or {})
    result.setdefault("success", True)
    result["adapter"] = adapter.adapter_name
    return result


@router.patch("/{task_id}")
async def update_task(task_id: str, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    adapter = _resolve_adapter(body.get("adapter"))
    updates = {key: value for key, value in body.items() if key in _UPDATE_FIELDS}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    task = await adapter.update_task(task_id, updates)
    if task is None:
        board = getattr(adapter, "board", None)
        last_error = str(getattr(board, "_last_update_error", "") or "").strip()
        if last_error == "task_not_found":
            raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
        if last_error:
            raise HTTPException(status_code=409, detail=last_error)
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return {"success": True, "adapter": adapter.adapter_name, "task": task}


# MARKER_189.2A: Project list for auto-complete in task creation
@router.get("/projects")
async def list_registered_projects(
    include_hidden: bool = Query(False),
) -> Dict[str, Any]:
    """Return registered MCC projects for task→project binding autocomplete."""
    result = list_projects(include_hidden=include_hidden)
    return {
        "success": True,
        "projects": result.get("projects", []),
        "active_project_id": result.get("active_project_id", ""),
    }


# MARKER_201.LOCALGUYS: Fixed path routes MUST come before /{task_id} wildcard
# so FastAPI matches them before the parametric route.


@router.post("/claim")
async def claim_task(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Claim a task. Used by local models (Ollama) that have no MCP access.

    Body: task_id, agent_name, agent_type (claude_code|local_ollama|…)
    """
    from src.orchestration.task_board import get_task_board

    task_id = body.get("task_id")
    agent_name = body.get("agent_name")
    agent_type = body.get("agent_type", "unknown")

    if not task_id:
        raise HTTPException(status_code=400, detail="task_id is required")
    if not agent_name:
        raise HTTPException(status_code=400, detail="agent_name is required")

    board = get_task_board()
    result = board.claim_task(task_id, agent_name, agent_type)
    if not result.get("success") and result.get("tool_isolation_rejected"):
        raise HTTPException(
            status_code=403, detail=result.get("error", "tool isolation rejected")
        )
    return result


@router.post("/complete")
async def complete_task(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Complete a task. Used by local models (Ollama) that have no MCP access.

    Body: task_id, commit_hash, commit_message (opt), branch (opt), agent_name (opt)
    """
    from src.orchestration.task_board import get_task_board

    task_id = body.get("task_id")
    if not task_id:
        raise HTTPException(status_code=400, detail="task_id is required")

    board = get_task_board()
    result = board.complete_task(
        task_id,
        commit_hash=body.get("commit_hash"),
        commit_message=body.get("commit_message"),
        branch=body.get("branch"),
        closed_by=body.get("agent_name"),
    )
    return result


@router.get("/{task_id}")
async def get_task(
    task_id: str, adapter: Optional[str] = Query(None)
) -> Dict[str, Any]:
    adapter_impl = _resolve_adapter(adapter)
    task = await adapter_impl.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return {"success": True, "adapter": adapter_impl.adapter_name, "task": task}
