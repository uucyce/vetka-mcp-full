# MARKER_133.TRACKER_API: Task lifecycle tracking endpoints
"""
API for task tracking — used by Cursor, Dragon, and DevPanel.

Endpoints:
  POST /api/tracker/cursor-done — Cursor marks task as completed
  POST /api/tracker/started — Mark task as started (any source)
  GET  /api/tracker/status — Current tracker state for DevPanel
  GET  /api/tracker/digest — Current project digest summary
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Body

router = APIRouter(prefix="/api/tracker", tags=["tracker"])


@router.post("/cursor-done")
async def cursor_task_done(body: Dict[str, Any] = Body(...)):
    """
    Cursor calls this when it completes a task.
    Body: {"marker": "C33E", "description": "Heartbeat persist to disk", "files_changed": ["src/..."]}
    """
    from src.services.task_tracker import on_cursor_task_completed
    marker = body.get("marker", "unknown")
    description = body.get("description", "")
    files_changed = body.get("files_changed", [])
    await on_cursor_task_completed(marker, description, files_changed)
    return {"success": True, "marker": marker, "tracked": True}


@router.post("/started")
async def task_started(body: Dict[str, Any] = Body(...)):
    """
    Mark a task as started. Any source (cursor, dragon, opus).
    Body: {"task_id": "C34A", "title": "Tauri multi-window", "source": "cursor"}
    """
    from src.services.task_tracker import on_task_started
    on_task_started(
        task_id=body.get("task_id", "unknown"),
        task_title=body.get("title", ""),
        source=body.get("source", "unknown"),
    )
    return {"success": True}


@router.get("/status")
async def tracker_status():
    """Get current task tracker state — in_progress, completed count, last task."""
    from src.services.task_tracker import get_tracker_status
    return {"success": True, **get_tracker_status()}


@router.get("/digest")
async def get_digest():
    """Get current project_digest.json summary."""
    digest_file = Path("data/project_digest.json")
    if digest_file.exists():
        data = json.loads(digest_file.read_text())
        return {
            "success": True,
            "phase": data.get("current_phase", {}),
            "headline": data.get("summary", {}).get("headline", ""),
            "achievements": data.get("summary", {}).get("key_achievements", [])[:5],
            "pending": data.get("summary", {}).get("pending_items", []),
        }
    return {"success": True, "phase": {}, "headline": "No digest"}


@router.post("/digest/update-phase")
async def update_phase(body: Dict[str, Any] = Body(...)):
    """
    Manually advance phase number.
    Body: {"phase": 134, "name": "Mycelium Command Center"}
    """
    digest_file = Path("data/project_digest.json")
    if digest_file.exists():
        data = json.loads(digest_file.read_text())
    else:
        data = {"version": "1.0.0"}

    data["current_phase"] = {
        "number": body.get("phase", 133),
        "subphase": "0",
        "name": body.get("name", f"Phase {body.get('phase', 133)}"),
        "status": "IN_PROGRESS",
    }
    digest_file.write_text(json.dumps(data, indent=2, default=str))
    return {"success": True, "phase": data["current_phase"]}
