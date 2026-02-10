"""
VETKA Task API Routes - Universal Task Management

@file task_routes.py
@status ACTIVE
@phase Phase 131
@marker MARKER_131.C20C
@lastAudit 2026-02-10

Public API endpoints for Task Board management.
Replaces /api/debug/task-board/* with cleaner /api/tasks/* paths.

Endpoints:
- GET /api/tasks - List all tasks (with optional status filter)
- GET /api/tasks/{task_id} - Get single task details
- POST /api/tasks - Create new task
- PATCH /api/tasks/{task_id} - Update task
- DELETE /api/tasks/{task_id} - Remove task
- POST /api/tasks/dispatch - Dispatch next pending task (or specific task_id)
- POST /api/tasks/{task_id}/claim - Claim task for an agent
- POST /api/tasks/{task_id}/complete - Mark task as completed
- POST /api/tasks/{task_id}/cancel - Cancel a running/pending task
- GET /api/tasks/{task_id}/results - Get pipeline results for task
"""

from fastapi import APIRouter, Query
from typing import Dict, Any, Optional, List
import time
import logging

router = APIRouter(prefix="/api/tasks", tags=["tasks"])
logger = logging.getLogger("VETKA_TASK_API")


# ============================================================
# LIST / GET TASKS
# ============================================================

@router.get("")
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status: pending, running, done, failed"),
    limit: int = Query(100, description="Max tasks to return"),
) -> Dict[str, Any]:
    """Get all tasks with optional status filter."""
    from src.orchestration.task_board import get_task_board

    board = get_task_board()
    tasks = board.get_queue()

    # Filter by status if provided
    if status:
        tasks = [t for t in tasks if t.get("status") == status]

    # Apply limit
    tasks = tasks[:limit]

    summary = board.get_board_summary()

    return {
        "success": True,
        "tasks": tasks,
        "count": len(tasks),
        "summary": summary,
        "timestamp": time.time(),
    }


@router.get("/{task_id}")
async def get_task(task_id: str) -> Dict[str, Any]:
    """Get a single task by ID."""
    from src.orchestration.task_board import get_task_board

    board = get_task_board()
    task = board.tasks.get(task_id)

    if not task:
        return {"success": False, "error": f"Task {task_id} not found"}

    return {"success": True, "task": task}


# ============================================================
# CREATE / UPDATE / DELETE TASKS
# ============================================================

@router.post("")
async def create_task(body: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new task.

    Body params:
    - title: str (required)
    - description: str
    - priority: int (1-5, default 3)
    - phase_type: str (build/fix/research)
    - preset: str (dragon_silver, titan_core, etc.)
    - tags: list[str]
    """
    from src.orchestration.task_board import get_task_board

    title = body.get("title")
    if not title:
        return {"success": False, "error": "Title is required"}

    board = get_task_board()
    task_id = board.add_task(
        title=title,
        description=body.get("description", ""),
        priority=body.get("priority", 3),
        phase_type=body.get("phase_type", "build"),
        preset=body.get("preset"),
        tags=body.get("tags", []),
        source=body.get("source", "api"),
    )

    logger.info(f"[TaskAPI] Created task {task_id}: {title[:50]}")
    return {"success": True, "task_id": task_id}


@router.patch("/{task_id}")
async def update_task(task_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """Update a task's fields (priority, status, title, etc.)."""
    from src.orchestration.task_board import get_task_board

    board = get_task_board()

    # Filter allowed update fields
    allowed_fields = {"title", "description", "priority", "phase_type", "preset", "status", "tags"}
    updates = {k: v for k, v in body.items() if k in allowed_fields}

    if not updates:
        return {"success": False, "error": "No valid fields to update"}

    ok = board.update_task(task_id, **updates)
    return {"success": ok, "task_id": task_id}


@router.delete("/{task_id}")
async def delete_task(task_id: str) -> Dict[str, Any]:
    """Remove a task from the board."""
    from src.orchestration.task_board import get_task_board

    board = get_task_board()
    ok = board.remove_task(task_id)
    return {"success": ok, "task_id": task_id}


# ============================================================
# DISPATCH / CLAIM / COMPLETE / CANCEL
# ============================================================

@router.post("/dispatch")
async def dispatch_task(body: Dict[str, Any] = None) -> Dict[str, Any]:
    """Dispatch the highest-priority pending task (or specific task_id).

    Body params:
    - task_id: str (optional, dispatch specific task)
    - chat_id: str (optional, for progress streaming)
    - selected_key: {provider, key_masked} (optional)
    """
    from src.orchestration.task_board import get_task_board

    body = body or {}
    board = get_task_board()
    task_id = body.get("task_id")
    chat_id = body.get("chat_id")
    selected_key = body.get("selected_key")

    if task_id:
        result = await board.dispatch_task(task_id, chat_id=chat_id, selected_key=selected_key)
    else:
        result = await board.dispatch_next(chat_id=chat_id, selected_key=selected_key)

    return result


@router.post("/{task_id}/claim")
async def claim_task(task_id: str, body: Dict[str, Any] = None) -> Dict[str, Any]:
    """Claim a task for an agent to work on.

    Body params:
    - agent_name: str (required - opus, cursor, dragon, grok)
    - agent_type: str (optional - claude_code, cursor, mycelium, grok, human)
    """
    from src.orchestration.task_board import get_task_board

    body = body or {}
    agent_name = body.get("agent_name")
    agent_type = body.get("agent_type", "unknown")

    if not agent_name:
        return {"success": False, "error": "agent_name is required"}

    board = get_task_board()
    result = board.claim_task(task_id, agent_name, agent_type)
    return result


@router.post("/{task_id}/complete")
async def complete_task(task_id: str, body: Dict[str, Any] = None) -> Dict[str, Any]:
    """Mark a task as completed with optional commit info.

    Body params:
    - commit_hash: str (optional - git commit hash)
    - commit_message: str (optional - first line of commit message)
    """
    from src.orchestration.task_board import get_task_board

    body = body or {}
    commit_hash = body.get("commit_hash")
    commit_message = body.get("commit_message")

    board = get_task_board()
    result = board.complete_task(task_id, commit_hash, commit_message)
    return result


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, body: Dict[str, Any] = None) -> Dict[str, Any]:
    """Cancel a running or pending task.

    Body params:
    - reason: str (optional, default "Cancelled by user")
    """
    from src.orchestration.task_board import get_task_board

    body = body or {}
    reason = body.get("reason", "Cancelled by user")

    board = get_task_board()
    ok = board.cancel_task(task_id, reason)
    return {"success": ok, "task_id": task_id}


# ============================================================
# RESULTS
# ============================================================

@router.get("/{task_id}/results")
async def get_task_results(task_id: str) -> Dict[str, Any]:
    """Get pipeline results for a completed task.

    Returns subtasks with their code results for display.
    """
    import json
    from pathlib import Path
    from src.orchestration.task_board import get_task_board

    board = get_task_board()
    task = board.tasks.get(task_id)

    if not task:
        return {"success": False, "error": f"Task {task_id} not found"}

    pipeline_task_id = task.get("pipeline_task_id")
    if not pipeline_task_id:
        return {
            "success": True,
            "task_id": task_id,
            "pipeline_task_id": None,
            "status": task.get("status"),
            "subtasks": [],
            "message": "No pipeline results (task not dispatched or still pending)"
        }

    # Read pipeline_tasks.json
    pipeline_file = Path(__file__).parent.parent.parent.parent / "data" / "pipeline_tasks.json"
    if not pipeline_file.exists():
        return {"success": False, "error": "pipeline_tasks.json not found"}

    try:
        pipeline_data = json.loads(pipeline_file.read_text())
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON: {e}"}

    pipeline_task = pipeline_data.get(pipeline_task_id)
    if not pipeline_task:
        return {
            "success": True,
            "task_id": task_id,
            "pipeline_task_id": pipeline_task_id,
            "status": task.get("status"),
            "subtasks": [],
            "message": f"Pipeline task {pipeline_task_id} not found"
        }

    # Extract subtasks with results
    subtasks = []
    for s in pipeline_task.get("subtasks", []):
        subtasks.append({
            "description": s.get("description", "")[:200],
            "status": s.get("status", "unknown"),
            "result": s.get("result"),
            "marker": s.get("marker"),
            "needs_research": s.get("needs_research", False),
        })

    return {
        "success": True,
        "task_id": task_id,
        "pipeline_task_id": pipeline_task_id,
        "status": pipeline_task.get("status"),
        "phase_type": pipeline_task.get("phase_type"),
        "subtasks": subtasks,
        "results_summary": pipeline_task.get("results", {}),
    }


# ============================================================
# STATS / ACTIVE AGENTS
# ============================================================

@router.get("/active-agents")
async def get_active_agents() -> Dict[str, Any]:
    """Get list of agents with claimed/running tasks."""
    from src.orchestration.task_board import get_task_board

    board = get_task_board()
    agents = board.get_active_agents()
    return {"success": True, "agents": agents, "count": len(agents)}


# ============================================================
# MARKER_131.C20D: CURSOR TASK WORKFLOW (take → work → complete)
# ============================================================

@router.get("/claimable")
async def get_claimable_tasks(
    limit: int = Query(5, description="Max tasks to return"),
    phase_type: Optional[str] = Query(None, description="Filter by phase: build/fix/research"),
) -> Dict[str, Any]:
    """Get pending tasks ready for claiming by external agents (Cursor, etc).

    Returns simplified task list for quick review:
    - id, title, priority, phase_type, complexity
    - Sorted by priority (highest first)

    Use POST /api/tasks/take to claim the top task automatically.
    """
    from src.orchestration.task_board import get_task_board

    board = get_task_board()
    all_tasks = board.get_queue()

    # Filter to claimable statuses
    claimable = [t for t in all_tasks if t.get("status") in ("pending", "queued")]

    # Filter by phase_type if specified
    if phase_type:
        claimable = [t for t in claimable if t.get("phase_type") == phase_type]

    # Sort by priority (1=highest)
    claimable = sorted(claimable, key=lambda t: t.get("priority", 3))

    # Limit and simplify
    result_tasks = []
    for t in claimable[:limit]:
        result_tasks.append({
            "id": t.get("id"),
            "title": t.get("title"),
            "description": t.get("description", "")[:200],
            "priority": t.get("priority", 3),
            "phase_type": t.get("phase_type"),
            "complexity": t.get("complexity", "medium"),
            "tags": t.get("tags", []),
        })

    return {
        "success": True,
        "tasks": result_tasks,
        "count": len(result_tasks),
        "total_claimable": len(claimable),
        "tip": "POST /api/tasks/take with agent_name to claim the top task"
    }


@router.post("/take")
async def take_next_task(body: Dict[str, Any] = None) -> Dict[str, Any]:
    """Take (claim) the highest-priority pending task in one call.

    This is a convenience endpoint for the Cursor workflow:
    1. Finds the next pending task (respects priority, phase_type filter)
    2. Claims it for the specified agent
    3. Returns the task details to work on

    Body params:
    - agent_name: str (required - e.g., "cursor", "opus")
    - agent_type: str (optional, default "cursor")
    - phase_type: str (optional - filter to build/fix/research only)

    Returns:
    - task: The full task object you claimed
    - workflow: Instructions for completing the task
    """
    from src.orchestration.task_board import get_task_board

    body = body or {}
    agent_name = body.get("agent_name")
    agent_type = body.get("agent_type", "cursor")
    phase_type = body.get("phase_type")

    if not agent_name:
        return {"success": False, "error": "agent_name is required"}

    board = get_task_board()
    all_tasks = board.get_queue()

    # Filter to claimable statuses
    claimable = [t for t in all_tasks if t.get("status") in ("pending", "queued")]

    # Filter by phase_type if specified
    if phase_type:
        claimable = [t for t in claimable if t.get("phase_type") == phase_type]

    if not claimable:
        return {
            "success": False,
            "error": "No claimable tasks available",
            "tip": "All tasks are already claimed/running or the queue is empty"
        }

    # Sort by priority (1=highest) and take first
    claimable = sorted(claimable, key=lambda t: t.get("priority", 3))
    task_to_claim = claimable[0]
    task_id = task_to_claim.get("id")

    # Claim it
    claim_result = board.claim_task(task_id, agent_name, agent_type)

    if not claim_result.get("success"):
        return claim_result

    # Get the updated task
    task = board.get_task(task_id)

    logger.info(f"[TaskAPI] Agent '{agent_name}' took task {task_id}: {task.get('title', '')[:50]}")

    return {
        "success": True,
        "task_id": task_id,
        "task": task,
        "workflow": {
            "step1_claimed": f"Task claimed by {agent_name}",
            "step2_work": "Implement the task as described",
            "step3_complete": f"POST /api/tasks/{task_id}/complete with commit_hash and commit_message",
        }
    }
