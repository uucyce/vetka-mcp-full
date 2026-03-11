"""
MARKER_175.7.TASKBOARD.REST_API.V1
Generic TaskBoard API for multi-client integrations.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException, Query

from src.orchestration.taskboard_adapters import get_taskboard_adapter

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
    "feedback",
    "result_status",
}


def _resolve_adapter(adapter_name: Optional[str] = None):
    try:
        return get_taskboard_adapter(adapter_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/create")
async def create_task(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    title = str(body.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    adapter = _resolve_adapter(body.get("adapter"))
    payload = {key: value for key, value in body.items() if key in _CREATE_FIELDS}
    task = await adapter.create_task(payload)
    return {"success": True, "adapter": adapter.adapter_name, "task": task}


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
async def dispatch_task(body: Optional[Dict[str, Any]] = Body(default=None)) -> Dict[str, Any]:
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
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return {"success": True, "adapter": adapter.adapter_name, "task": task}


@router.get("/{task_id}")
async def get_task(task_id: str, adapter: Optional[str] = Query(None)) -> Dict[str, Any]:
    adapter_impl = _resolve_adapter(adapter)
    task = await adapter_impl.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return {"success": True, "adapter": adapter_impl.adapter_name, "task": task}
