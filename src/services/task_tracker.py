# MARKER_133.TRACKER: Automatic task lifecycle tracking
"""
Task Tracker — connects TaskBoard, Pipeline History, and Project Digest.

When a pipeline completes:
  1. TaskBoard marks done ✓ (already works)
  2. Pipeline history records stats ✓ (just added)
  3. THIS MODULE: Updates project_digest.json with latest achievements
  4. THIS MODULE: Emits event for DevPanel to refresh

Usage:
    from src.services.task_tracker import on_task_completed, on_cursor_task_completed

    # Called automatically by pipeline
    await on_task_completed(task_id, task_title, status, stats)

    # Called manually or via API for Cursor tasks
    await on_cursor_task_completed(marker, description, files_changed)
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("VETKA_TRACKER")

# MARKER_134.FIX_CWD: Use absolute path from __file__ to avoid CWD issues in MCP context
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DIGEST_FILE = _PROJECT_ROOT / "data" / "project_digest.json"
TRACKER_FILE = _PROJECT_ROOT / "data" / "task_tracker.json"


def _load_digest() -> dict:
    if DIGEST_FILE.exists():
        try:
            return json.loads(DIGEST_FILE.read_text())
        except Exception:
            pass
    return {"version": "1.0.0", "current_phase": {}, "summary": {}}


def _save_digest(digest: dict):
    digest["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
    digest["auto_updated"] = True
    DIGEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    DIGEST_FILE.write_text(json.dumps(digest, indent=2, default=str))


def _load_tracker() -> dict:
    if TRACKER_FILE.exists():
        try:
            return json.loads(TRACKER_FILE.read_text())
        except Exception:
            pass
    return {"completed": [], "in_progress": [], "phase": 133}


def _save_tracker(tracker: dict):
    TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_FILE.write_text(json.dumps(tracker, indent=2, default=str))


async def on_task_completed(
    task_id: str,
    task_title: str,
    status: str,
    stats: Optional[Dict[str, Any]] = None,
    source: str = "dragon",
):
    """Called when a pipeline task completes. Updates digest + tracker."""
    tracker = _load_tracker()

    entry = {
        "task_id": task_id,
        "title": task_title[:200],
        "status": status,
        "source": source,
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "stats": {
            "duration_s": stats.get("duration_s", 0) if stats else 0,
            "llm_calls": stats.get("llm_calls", 0) if stats else 0,
            "preset": stats.get("preset", "unknown") if stats else "unknown",
        }
    }
    tracker["completed"].append(entry)
    # Remove from in_progress if was there
    tracker["in_progress"] = [
        t for t in tracker["in_progress"]
        if t.get("task_id") != task_id
    ]
    # Keep last 100
    tracker["completed"] = tracker["completed"][-100:]
    _save_tracker(tracker)

    # Update digest
    _update_digest_with_task(task_title, status, source)

    logger.info(f"[Tracker] {source} task completed: {task_title[:60]} ({status})")


async def on_cursor_task_completed(
    marker: str,
    description: str,
    files_changed: Optional[List[str]] = None,
):
    """Called via API when Cursor completes a task. Updates digest."""
    tracker = _load_tracker()

    entry = {
        "task_id": marker,
        "title": description[:200],
        "status": "done",
        "source": "cursor",
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "files_changed": files_changed or [],
    }
    tracker["completed"].append(entry)
    tracker["completed"] = tracker["completed"][-100:]
    _save_tracker(tracker)

    _update_digest_with_task(f"[{marker}] {description}", "done", "cursor")

    logger.info(f"[Tracker] Cursor task completed: {marker} — {description[:60]}")


def on_task_started(task_id: str, task_title: str, source: str = "dragon"):
    """Track task start (non-async, can be called from sync context)."""
    tracker = _load_tracker()
    tracker["in_progress"].append({
        "task_id": task_id,
        "title": task_title[:200],
        "source": source,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })
    # Keep last 20 in progress
    tracker["in_progress"] = tracker["in_progress"][-20:]
    _save_tracker(tracker)


def _update_digest_with_task(title: str, status: str, source: str):
    """Update project_digest.json with latest achievement."""
    digest = _load_digest()

    # Update phase
    phase = digest.get("current_phase", {})
    phase_num = phase.get("number", 133)
    digest["current_phase"] = {
        "number": phase_num,
        "subphase": str(int(phase.get("subphase", "0")) + 1) if status == "done" else phase.get("subphase", "0"),
        "name": f"Phase {phase_num}: Active Development",
        "status": "IN_PROGRESS",
        "started": phase.get("started", time.strftime("%Y-%m-%d")),
    }

    # Add to achievements (prepend, keep 10)
    summary = digest.get("summary", {})
    achievements = summary.get("key_achievements", [])
    tag = f"[{source}]"
    new_achievement = f"{tag} {title[:80]}"
    achievements.insert(0, new_achievement)
    summary["key_achievements"] = achievements[:10]
    summary["headline"] = f"Phase {phase_num} active — {source}: {title[:50]}"
    digest["summary"] = summary

    _save_digest(digest)


def get_tracker_status() -> dict:
    """Get current tracker state for API/DevPanel."""
    tracker = _load_tracker()
    return {
        "phase": tracker.get("phase", 133),
        "in_progress": tracker.get("in_progress", []),
        "completed_count": len(tracker.get("completed", [])),
        "last_completed": tracker.get("completed", [])[-1] if tracker.get("completed") else None,
    }
