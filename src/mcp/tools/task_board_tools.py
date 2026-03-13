"""
Task Board MCP Tools — Phase 121

Three MCP tools for managing the Task Board:
1. vetka_task_board  — CRUD + list + summary
2. vetka_task_dispatch — dispatch tasks to pipeline
3. vetka_task_import — import from todo files

TODO MARKER_126.11C: Add fourth tool:
4. vetka_task_claim — claim/release tasks for external agents
   - action: "claim" | "release" | "my_tasks"
   - Enables Claude Code, Grok, etc. to claim tasks without Mycelium

@status: active
@phase: 121
@depends: src/orchestration/task_board.py
"""

import logging
from typing import Dict, Any

logger = logging.getLogger("VETKA_MCP")


# ==========================================
# Tool 1: vetka_task_board (CRUD + list)
# ==========================================

TASK_BOARD_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            # MARKER_130.C16B: Added claim, complete, active_agents actions
            "enum": ["add", "list", "get", "update", "remove", "summary", "claim", "complete", "active_agents"],
            "description": "Operation to perform"
        },
        # For "add":
        "title": {"type": "string", "description": "Task title (required for add)"},
        "description": {"type": "string", "description": "Detailed task description"},
        "profile": {"type": "string", "enum": ["p6"], "description": "Task intake profile with protocol defaults"},
        "priority": {"type": "number", "description": "1=critical, 2=high, 3=medium, 4=low, 5=someday"},
        "phase_type": {"type": "string", "enum": ["build", "fix", "research", "test"], "description": "Task type"},
        "complexity": {"type": "string", "enum": ["low", "medium", "high"], "description": "Estimated complexity"},
        "preset": {"type": "string", "description": "Pipeline preset override"},
        "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for categorization"},
        "dependencies": {"type": "array", "items": {"type": "string"}, "description": "Task IDs that must complete first"},
        "project_id": {"type": "string", "description": "Logical project ID for lane-aware multitask routing"},
        "project_lane": {"type": "string", "description": "Specific multitask lane/MCC tab identifier"},
        "architecture_docs": {"type": "array", "items": {"type": "string"}, "description": "Architecture docs linked to the task"},
        "recon_docs": {"type": "array", "items": {"type": "string"}, "description": "Recon docs linked to the task"},
        "closure_tests": {"type": "array", "items": {"type": "string"}, "description": "Commands required for closure proof"},
        "closure_files": {"type": "array", "items": {"type": "string"}, "description": "Files allowed for scoped auto-commit"},
        # MARKER_130.C16B: Agent assignment fields
        "assigned_to": {"type": "string", "description": "Agent name: opus, cursor, dragon, grok"},
        "agent_type": {"type": "string", "description": "Agent type: claude_code, cursor, mycelium, grok, human"},
        # For "get", "update", "remove", "claim", "complete":
        "task_id": {"type": "string", "description": "Task ID (required for get/update/remove/claim/complete)"},
        # For "update":
        "status": {"type": "string", "enum": ["pending", "queued", "claimed", "running", "done", "failed", "cancelled"]},
        # For "list":
        "filter_status": {"type": "string", "description": "Filter by status (optional for list)"},
        # For "complete":
        "commit_hash": {"type": "string", "description": "Git commit hash (for complete)"},
        "commit_message": {"type": "string", "description": "Commit message (for complete)"},
    },
    "required": ["action"]
}


def handle_task_board(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle vetka_task_board MCP tool calls.

    CRUD + list + summary operations on the task board.
    """
    from src.orchestration.task_board import get_task_board
    from src.services.roadmap_task_sync import apply_task_profile_defaults

    action = arguments.get("action")
    if not action:
        return {"success": False, "error": "action is required"}

    board = get_task_board()

    if action == "add":
        title = arguments.get("title")
        if not title:
            return {"success": False, "error": "title is required for add"}
        payload = dict(arguments)
        payload["source"] = "mcp"
        try:
            payload = apply_task_profile_defaults(payload)
        except ValueError as exc:
            return {"success": False, "error": str(exc)}
        try:
            task_id = board.add_task(
                title=title,
                description=payload.get("description", ""),
                priority=int(payload.get("priority", 3)),
                phase_type=payload.get("phase_type", "build"),
                complexity=payload.get("complexity", "medium"),
                preset=payload.get("preset"),
                tags=payload.get("tags"),
                dependencies=payload.get("dependencies"),
                source=payload.get("source", "mcp"),
                project_id=payload.get("project_id"),
                project_lane=payload.get("project_lane"),
                architecture_docs=payload.get("architecture_docs"),
                recon_docs=payload.get("recon_docs"),
                protocol_version=payload.get("protocol_version"),
                require_closure_proof=bool(payload.get("require_closure_proof")),
                closure_tests=payload.get("closure_tests"),
                closure_files=payload.get("closure_files"),
                task_origin=payload.get("task_origin"),
                workflow_selection_origin=payload.get("workflow_selection_origin"),
                completion_contract=payload.get("completion_contract"),
                depends_on_docs=payload.get("depends_on_docs"),
            )
        except ValueError as exc:
            return {"success": False, "error": str(exc)}
        return {"success": True, "task_id": task_id, "message": f"Task '{title}' added"}

    elif action == "list":
        filter_status = arguments.get("filter_status")
        tasks = board.get_queue(status=filter_status)
        return {
            "success": True,
            "count": len(tasks),
            "tasks": [
                {
                    "id": t["id"],
                    "title": t["title"],
                    "priority": t["priority"],
                    "status": t["status"],
                    "phase_type": t["phase_type"],
                    "complexity": t["complexity"],
                    "source": t.get("source", ""),
                    "assigned_tier": t.get("assigned_tier")
                }
                for t in tasks[:20]  # Limit to 20 for readability
            ]
        }

    elif action == "get":
        task_id = arguments.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required for get"}
        task = board.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        return {"success": True, "task": task}

    elif action == "update":
        task_id = arguments.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required for update"}

        # Collect updatable fields
        updates = {}
        for field in ["title", "description", "priority", "phase_type", "complexity",
                       "preset", "status", "tags", "dependencies", "project_id",
                       "project_lane", "architecture_docs", "recon_docs",
                       "closure_tests", "closure_files"]:
            if field in arguments and arguments[field] is not None:
                updates[field] = arguments[field]

        if not updates:
            return {"success": False, "error": "No fields to update"}

        ok = board.update_task(task_id, **updates)
        return {"success": ok, "updated_fields": list(updates.keys())}

    elif action == "remove":
        task_id = arguments.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required for remove"}
        ok = board.remove_task(task_id)
        return {"success": ok, "message": f"Task {task_id} removed" if ok else f"Task {task_id} not found"}

    elif action == "summary":
        summary = board.get_board_summary()
        return {"success": True, **summary}

    # MARKER_130.C16B: claim action
    elif action == "claim":
        task_id = arguments.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required for claim"}
        agent_name = arguments.get("assigned_to", "unknown")
        agent_type = arguments.get("agent_type", "unknown")
        result = board.claim_task(task_id, agent_name, agent_type)
        return result

    # MARKER_130.C16B: complete action
    elif action == "complete":
        task_id = arguments.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required for complete"}
        commit_hash = arguments.get("commit_hash")
        commit_message = arguments.get("commit_message")
        result = board.complete_task(task_id, commit_hash, commit_message)
        return result

    # MARKER_130.C16B: active_agents action
    elif action == "active_agents":
        agents = board.get_active_agents()
        return {"success": True, "agents": agents, "count": len(agents)}

    else:
        return {"success": False, "error": f"Unknown action: {action}"}


# ==========================================
# Tool 2: vetka_task_dispatch
# ==========================================

TASK_DISPATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "task_id": {
            "type": "string",
            "description": "Task ID to dispatch. If omitted, dispatches highest-priority task."
        },
        "chat_id": {
            "type": "string",
            "description": "Chat ID for progress streaming (optional)"
        }
    }
}


async def handle_task_dispatch(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle vetka_task_dispatch MCP tool calls.

    Dispatches a task (or next available) to the Mycelium pipeline.
    """
    from src.orchestration.task_board import get_task_board

    board = get_task_board()
    task_id = arguments.get("task_id")
    chat_id = arguments.get("chat_id")

    if task_id:
        result = await board.dispatch_task(task_id, chat_id=chat_id)
    else:
        result = await board.dispatch_next(chat_id=chat_id)

    return result


# ==========================================
# Tool 3: vetka_task_import
# ==========================================

TASK_IMPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "file_path": {
            "type": "string",
            "description": "Path to todo file to import"
        },
        "source_tag": {
            "type": "string",
            "description": "Source tag for imported tasks (e.g., 'dragon_todo', 'titan_todo')"
        }
    },
    "required": ["file_path"]
}


def handle_task_import(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle vetka_task_import MCP tool calls.

    Imports tasks from a todo text file into the task board.
    """
    from src.orchestration.task_board import get_task_board

    file_path = arguments.get("file_path")
    if not file_path:
        return {"success": False, "error": "file_path is required"}

    source_tag = arguments.get("source_tag", "imported")
    board = get_task_board()
    count = board.import_from_todo(file_path, source_tag)

    return {
        "success": count > 0,
        "imported_count": count,
        "file": file_path,
        "source_tag": source_tag,
        "total_tasks": len(board.tasks)
    }
