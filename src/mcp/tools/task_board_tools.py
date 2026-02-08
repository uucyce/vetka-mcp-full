"""
Task Board MCP Tools — Phase 121

Three MCP tools for managing the Task Board:
1. vetka_task_board  — CRUD + list + summary
2. vetka_task_dispatch — dispatch tasks to pipeline
3. vetka_task_import — import from todo files

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
            "enum": ["add", "list", "get", "update", "remove", "summary"],
            "description": "Operation to perform"
        },
        # For "add":
        "title": {"type": "string", "description": "Task title (required for add)"},
        "description": {"type": "string", "description": "Detailed task description"},
        "priority": {"type": "number", "description": "1=critical, 2=high, 3=medium, 4=low, 5=someday"},
        "phase_type": {"type": "string", "enum": ["build", "fix", "research"], "description": "Task type"},
        "complexity": {"type": "string", "enum": ["low", "medium", "high"], "description": "Estimated complexity"},
        "preset": {"type": "string", "description": "Pipeline preset override"},
        "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for categorization"},
        "dependencies": {"type": "array", "items": {"type": "string"}, "description": "Task IDs that must complete first"},
        # For "get", "update", "remove":
        "task_id": {"type": "string", "description": "Task ID (required for get/update/remove)"},
        # For "update":
        "status": {"type": "string", "enum": ["pending", "queued", "running", "done", "failed", "cancelled"]},
        # For "list":
        "filter_status": {"type": "string", "description": "Filter by status (optional for list)"},
    },
    "required": ["action"]
}


def handle_task_board(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle vetka_task_board MCP tool calls.

    CRUD + list + summary operations on the task board.
    """
    from src.orchestration.task_board import get_task_board

    action = arguments.get("action")
    if not action:
        return {"success": False, "error": "action is required"}

    board = get_task_board()

    if action == "add":
        title = arguments.get("title")
        if not title:
            return {"success": False, "error": "title is required for add"}

        task_id = board.add_task(
            title=title,
            description=arguments.get("description", ""),
            priority=int(arguments.get("priority", 3)),
            phase_type=arguments.get("phase_type", "build"),
            complexity=arguments.get("complexity", "medium"),
            preset=arguments.get("preset"),
            tags=arguments.get("tags"),
            dependencies=arguments.get("dependencies"),
            source="mcp"
        )
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
                       "preset", "status", "tags", "dependencies"]:
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
