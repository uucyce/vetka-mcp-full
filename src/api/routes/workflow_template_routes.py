"""
MARKER_144.1B: Workflow Template API Routes.
CRUD endpoints for user-created workflow templates.

Prefix: /api/workflows (plural — distinct from /api/workflow which is orchestrator history)

@phase 144
@status active
"""

from fastapi import APIRouter, HTTPException
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.services.workflow_store import WorkflowStore


router = APIRouter(prefix="/api/workflows", tags=["Workflow Templates"])

# Singleton store instance
_store: Optional[WorkflowStore] = None


def get_store() -> WorkflowStore:
    """Get or create WorkflowStore singleton."""
    global _store
    if _store is None:
        _store = WorkflowStore()
    return _store


# ============================================================
# Pydantic Models
# ============================================================

class WorkflowNodeModel(BaseModel):
    """A node in a workflow template."""
    id: str
    type: str
    label: str
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})
    data: Dict[str, Any] = Field(default_factory=dict)


class WorkflowEdgeModel(BaseModel):
    """An edge in a workflow template."""
    id: str
    source: str
    target: str
    type: str = "structural"
    label: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class WorkflowCreateRequest(BaseModel):
    """Request body for creating/updating a workflow."""
    id: Optional[str] = None
    name: str = "Untitled Workflow"
    description: Optional[str] = None
    nodes: List[WorkflowNodeModel] = Field(default_factory=list)
    edges: List[WorkflowEdgeModel] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowValidateRequest(BaseModel):
    """Request body for validating a workflow without saving."""
    name: Optional[str] = "Validation Check"
    nodes: List[WorkflowNodeModel] = Field(default_factory=list)
    edges: List[WorkflowEdgeModel] = Field(default_factory=list)


# ============================================================
# Endpoints
# ============================================================

@router.get("")
async def list_workflows():
    """
    List all saved workflow templates (summaries only).
    Returns id, name, node/edge counts, metadata.
    """
    store = get_store()
    workflows = store.list_workflows()
    return {"success": True, "workflows": workflows, "count": len(workflows)}


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str):
    """
    Load a complete workflow template by ID.
    Returns full node/edge data.
    """
    store = get_store()
    workflow = store.load(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")
    return {"success": True, "workflow": workflow}


@router.post("")
async def create_workflow(request: WorkflowCreateRequest):
    """
    Create a new workflow template.
    Returns the assigned workflow ID.
    """
    store = get_store()
    workflow_dict = request.model_dump()

    # Convert Pydantic models to plain dicts
    workflow_dict["nodes"] = [n if isinstance(n, dict) else n for n in workflow_dict["nodes"]]
    workflow_dict["edges"] = [e if isinstance(e, dict) else e for e in workflow_dict["edges"]]

    wf_id = store.save(workflow_dict)
    return {"success": True, "id": wf_id, "message": f"Workflow '{request.name}' saved"}


@router.put("/{workflow_id}")
async def update_workflow(workflow_id: str, request: WorkflowCreateRequest):
    """
    Update an existing workflow template.
    """
    store = get_store()

    # Check exists
    existing = store.load(workflow_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")

    workflow_dict = request.model_dump()
    workflow_dict["id"] = workflow_id

    # Preserve original created_at
    if "metadata" in existing and "created_at" in existing["metadata"]:
        if "metadata" not in workflow_dict:
            workflow_dict["metadata"] = {}
        workflow_dict["metadata"]["created_at"] = existing["metadata"]["created_at"]

    store.save(workflow_dict)
    return {"success": True, "id": workflow_id, "message": f"Workflow '{request.name}' updated"}


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """
    Delete a workflow template.
    """
    store = get_store()
    deleted = store.delete(workflow_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")
    return {"success": True, "message": f"Workflow {workflow_id} deleted"}


@router.post("/validate")
async def validate_workflow(request: WorkflowValidateRequest):
    """
    Validate a workflow without saving.
    Returns validation errors and warnings.
    """
    store = get_store()
    workflow_dict = request.model_dump()
    result = store.validate(workflow_dict)
    return {"success": True, "validation": result.to_dict()}
