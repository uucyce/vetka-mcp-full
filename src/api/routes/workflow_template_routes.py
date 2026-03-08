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


class WorkflowGenerateRequest(BaseModel):
    """MARKER_144.7: Request body for AI workflow generation."""
    description: str
    complexity_hint: Optional[str] = None  # "low", "medium", "high"
    preset: str = "dragon_silver"
    save: bool = False  # If true, auto-save the generated workflow


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


@router.post("/generate")
async def generate_workflow(request: WorkflowGenerateRequest):
    """
    MARKER_144.7: AI-powered workflow generation.

    Takes a natural language description → Architect AI generates a complete
    workflow (nodes + edges) → returns it for the DAG editor.

    If save=True, also saves the generated workflow to the store.
    Falls back to template generation when LLM is unavailable.
    """
    from src.services.workflow_architect import generate_workflow as gen_wf

    result = await gen_wf(
        description=request.description,
        preset=request.preset,
        complexity_hint=request.complexity_hint,
    )

    if not result.get("success"):
        return result

    # Optionally save the generated workflow
    if request.save and result.get("workflow"):
        store = get_store()
        wf_id = store.save(result["workflow"])
        result["saved"] = True
        result["workflow_id"] = wf_id

    return result


# ============================================================
# MARKER_144.8 + 144.9: Import/Export Endpoints
# ============================================================

class WorkflowImportRequest(BaseModel):
    """Request body for importing a workflow from external format."""
    data: Dict[str, Any]  # Raw JSON from n8n or ComfyUI
    format: Optional[str] = None  # "n8n", "comfyui", or None for auto-detect
    save: bool = True  # Save imported workflow to store


class WorkflowExportRequest(BaseModel):
    """Request body for exporting a workflow to external format."""
    format: str = "n8n"  # "n8n" or "comfyui"
    comfyui_format: str = "graph"  # For ComfyUI: "graph" or "api"


@router.post("/import")
async def import_workflow(request: WorkflowImportRequest):
    """
    MARKER_144.8/144.9: Import workflow from n8n or ComfyUI format.
    Auto-detects format if not specified.
    Returns VETKA workflow JSON.
    """
    from src.services.converters.n8n_converter import detect_n8n_format, n8n_to_vetka
    from src.services.converters.comfyui_converter import detect_comfyui_format, comfyui_to_vetka

    data = request.data
    fmt = request.format

    # Auto-detect format if not specified
    if not fmt:
        if detect_n8n_format(data):
            fmt = "n8n"
        elif detect_comfyui_format(data) != "none":
            fmt = "comfyui"
        else:
            return {"success": False, "error": "Unknown workflow format. Expected n8n or ComfyUI JSON."}

    try:
        if fmt == "n8n":
            workflow = n8n_to_vetka(data)
        elif fmt == "comfyui":
            workflow = comfyui_to_vetka(data)
        else:
            return {"success": False, "error": f"Unsupported format: {fmt}"}
    except Exception as e:
        return {"success": False, "error": f"Conversion failed: {str(e)}"}

    # Validate converted workflow
    store = get_store()
    validation = store.validate(workflow)

    metadata = workflow.setdefault("metadata", {})
    if isinstance(metadata, dict):
        metadata["workflow_bank"] = fmt if fmt in {"n8n", "comfyui"} else "imported"
        metadata["import_format"] = fmt or "imported"

    # Save if requested
    saved_id = None
    if request.save:
        saved_id = store.save(workflow)

    return {
        "success": True,
        "format_detected": fmt,
        "workflow": workflow,
        "workflow_id": saved_id,
        "saved": request.save and saved_id is not None,
        "validation": validation.to_dict(),
    }


@router.post("/{workflow_id}/export")
async def export_workflow(workflow_id: str, request: WorkflowExportRequest):
    """
    MARKER_144.8/144.9: Export workflow to n8n or ComfyUI format.
    Returns converted JSON ready for download.
    """
    from src.services.converters.n8n_converter import vetka_to_n8n
    from src.services.converters.comfyui_converter import vetka_to_comfyui

    store = get_store()
    workflow = store.load(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")

    try:
        if request.format == "n8n":
            exported = vetka_to_n8n(workflow)
        elif request.format == "comfyui":
            exported = vetka_to_comfyui(workflow, fmt=request.comfyui_format)
        else:
            return {"success": False, "error": f"Unsupported export format: {request.format}"}
    except Exception as e:
        return {"success": False, "error": f"Export failed: {str(e)}"}

    return {
        "success": True,
        "format": request.format,
        "workflow_name": workflow.get("name", "Untitled"),
        "exported": exported,
    }


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


# ============================================================
# MARKER_144.10: Workflow Execution Bridge
# ============================================================

class WorkflowExecuteRequest(BaseModel):
    """Request body for executing a workflow."""
    preset: str = "dragon_silver"
    dry_run: bool = False  # If true, return planned tasks without dispatching


@router.post("/{workflow_id}/execute")
async def execute_workflow(workflow_id: str, request: WorkflowExecuteRequest):
    """
    MARKER_144.10: Execute a workflow by converting nodes → TaskBoard tasks.

    1. Load workflow from store
    2. Validate (must pass)
    3. Convert nodes → task dicts via workflow_to_tasks()
    4. Add tasks to TaskBoard (respecting dependency order)
    5. Optionally dispatch first batch (root tasks with no dependencies)

    If dry_run=True, returns planned tasks without adding to board.
    """
    import logging
    logger = logging.getLogger(__name__)

    store = get_store()
    workflow = store.load(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")

    # Validate first
    validation = store.validate(workflow)
    if not validation.valid:
        return {
            "success": False,
            "error": "Workflow has validation errors",
            "validation": validation.to_dict(),
        }

    # Convert nodes to task dicts
    task_dicts = store.workflow_to_tasks(workflow, request.preset)

    if not task_dicts:
        return {
            "success": False,
            "error": "Workflow has no nodes to execute",
        }

    # Dry run — just return the planned tasks
    if request.dry_run:
        return {
            "success": True,
            "dry_run": True,
            "workflow_id": workflow_id,
            "workflow_name": workflow.get("name", "Untitled"),
            "planned_tasks": task_dicts,
            "count": len(task_dicts),
        }

    # Real execution — add tasks to TaskBoard
    try:
        from src.orchestration.task_board import get_task_board
        board = get_task_board()
    except ImportError:
        return {
            "success": False,
            "error": "TaskBoard not available",
        }

    # Add tasks in topological order (roots first)
    # node_id → actual task_id mapping for dependency resolution
    node_to_task_id: Dict[str, str] = {}
    created_task_ids: List[str] = []
    root_task_ids: List[str] = []

    for task_dict in task_dicts:
        node_id = task_dict.get("node_id", "")
        dep_node_ids = task_dict.get("dependency_node_ids", [])

        # Resolve dependencies to actual task IDs
        dependencies = []
        for dep_nid in dep_node_ids:
            if dep_nid in node_to_task_id:
                dependencies.append(node_to_task_id[dep_nid])

        # Add to board
        task_id = board.add_task(
            title=task_dict["title"],
            description=task_dict.get("description", ""),
            priority=task_dict.get("priority", 3),
            tags=task_dict.get("tags", []),
            dependencies=dependencies if dependencies else None,
            complexity=task_dict.get("complexity", 1),
        )

        node_to_task_id[node_id] = task_id
        created_task_ids.append(task_id)

        if not dep_node_ids:
            root_task_ids.append(task_id)

    # Dispatch root tasks (no dependencies)
    dispatched = []
    for root_id in root_task_ids[:3]:  # Dispatch up to 3 roots in parallel
        try:
            result = await board.dispatch_task(root_id)
            if result.get("success"):
                dispatched.append(root_id)
        except Exception as e:
            logger.warning(f"[Workflow Execute] Dispatch failed for {root_id}: {e}")

    logger.info(
        f"[Workflow Execute] {workflow.get('name')}: "
        f"{len(created_task_ids)} tasks created, {len(dispatched)} dispatched"
    )

    return {
        "success": True,
        "workflow_id": workflow_id,
        "workflow_name": workflow.get("name", "Untitled"),
        "tasks_created": created_task_ids,
        "tasks_dispatched": dispatched,
        "root_tasks": root_task_ids,
        "count": len(created_task_ids),
        "node_to_task_map": node_to_task_id,
    }
