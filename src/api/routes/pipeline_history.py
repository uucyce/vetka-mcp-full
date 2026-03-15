# MARKER_133.HISTORY: Pipeline run history storage and API
"""
Tracks pipeline execution history for observability.
GET /api/pipeline/history — returns last N pipeline runs with stats.
"""
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

# MARKER_134.FIX_CWD: Use absolute path from __file__ to avoid CWD issues in MCP context
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
HISTORY_FILE = _PROJECT_ROOT / "data" / "pipeline_history.json"


def _load_history() -> list:
    """Load pipeline history from disk."""
    if HISTORY_FILE.exists():
        try:
            data = json.loads(HISTORY_FILE.read_text())
            return data if isinstance(data, list) else []
        except Exception:
            return []
    return []


def _save_history(history: list):
    """Save pipeline history to disk. Keep last 500 entries."""
    history = history[-500:]  # Trim to 500
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, indent=2, default=str))


def append_run(
    task_id: str,
    task_title: str,
    preset: str,
    phase_type: str,
    phases_completed: list,
    total_duration_s: float,
    eval_score: Optional[float],
    status: str,
    llm_calls: int = 0,
    tokens_in: int = 0,
    tokens_out: int = 0,
    files_created: list = None,
    subtasks_completed: int = 0,
    subtasks_total: int = 0,
    # MARKER_182.5: New fields for timeline persistence + run tracking
    run_id: Optional[str] = None,
    session_id: Optional[str] = None,
    timeline_events: list = None,
):
    """Append a pipeline run record to history."""
    history = _load_history()
    record = {
        # MARKER_182.RUNID: Use provided run_id or generate one
        "run_id": run_id or f"run_{int(time.time())}_{task_id[-8:]}",
        "session_id": session_id,  # MARKER_182.SESSIONID
        "task_id": task_id,
        "task_title": task_title[:200],
        "preset": preset,
        "phase_type": phase_type,
        "phases_completed": phases_completed,
        "subtasks_completed": subtasks_completed,
        "subtasks_total": subtasks_total,
        "total_duration_s": round(total_duration_s, 1),
        "eval_score": eval_score,
        "status": status,
        "llm_calls": llm_calls,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "files_created": (files_created or [])[:20],
        # MARKER_182.5: Persist timeline events from pipeline
        "timeline_events": (timeline_events or [])[:200],  # Cap at 200 events
        "timestamp": time.time(),
        "timestamp_human": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    history.append(record)
    _save_history(history)
    return record


@router.get("/history")
async def get_pipeline_history(
    limit: int = Query(20, ge=1, le=200, description="Max entries to return"),
    status_filter: Optional[str] = Query(None, description="Filter by status: done, failed"),
    preset_filter: Optional[str] = Query(None, description="Filter by preset"),
):
    """Get pipeline execution history with optional filters."""
    history = _load_history()

    # Apply filters
    if status_filter:
        history = [r for r in history if r.get("status") == status_filter]
    if preset_filter:
        history = [r for r in history if r.get("preset") == preset_filter]

    # Return most recent first
    history = list(reversed(history[-limit:]))

    # Calculate summary stats
    total = len(history)
    success = sum(1 for r in history if r.get("status") == "done")
    avg_duration = (
        round(sum(r.get("total_duration_s", 0) for r in history) / total, 1)
        if total > 0
        else 0
    )
    total_tokens = sum(r.get("tokens_in", 0) + r.get("tokens_out", 0) for r in history)

    return {
        "success": True,
        "total": total,
        "summary": {
            "success_rate": round(success / total * 100, 1) if total > 0 else 0,
            "avg_duration_s": avg_duration,
            "total_tokens": total_tokens,
            "total_llm_calls": sum(r.get("llm_calls", 0) for r in history),
        },
        "runs": history,
    }


# MARKER_182.TIMELINE_API: Get timeline events for a specific run
@router.get("/history/{run_id}/timeline")
async def get_run_timeline(
    run_id: str,
    role: Optional[str] = Query(None, description="Filter by role: architect, scout, coder, verifier"),
):
    """Get timeline events for a specific pipeline run."""
    history = _load_history()

    # Find run by run_id
    run = None
    for r in history:
        if r.get("run_id") == run_id:
            run = r
            break

    if not run:
        return {"success": False, "error": f"Run {run_id} not found"}

    events = run.get("timeline_events", [])

    # Filter by role if specified
    # MARKER_183.11: Use `is not None` — Query(None) objects are truthy when called directly
    if role is not None:
        events = [e for e in events if e.get("role") == role]

    return {
        "success": True,
        "run_id": run_id,
        "task_id": run.get("task_id"),
        "session_id": run.get("session_id"),
        "total_events": len(events),
        "timeline_events": events,
    }


@router.get("/history/stats")
async def pipeline_stats():
    """Aggregated pipeline stats — for Stats tab in DevPanel."""
    history = _load_history()
    if not history:
        return {"success": True, "stats": {"total_runs": 0}}

    total = len(history)
    success = sum(1 for r in history if r.get("status") == "done")

    # Per-preset breakdown
    presets: Dict[str, Any] = {}
    for r in history:
        p = r.get("preset", "unknown")
        if p not in presets:
            presets[p] = {"runs": 0, "success": 0, "total_duration": 0, "tokens": 0}
        presets[p]["runs"] += 1
        if r.get("status") == "done":
            presets[p]["success"] += 1
        presets[p]["total_duration"] += r.get("total_duration_s", 0)
        presets[p]["tokens"] += r.get("tokens_in", 0) + r.get("tokens_out", 0)

    return {
        "success": True,
        "stats": {
            "total_runs": total,
            "success_rate": round(success / total * 100, 1),
            "avg_duration_s": round(sum(r.get("total_duration_s", 0) for r in history) / total, 1),
            "total_tokens_in": sum(r.get("tokens_in", 0) for r in history),
            "total_tokens_out": sum(r.get("tokens_out", 0) for r in history),
            "total_llm_calls": sum(r.get("llm_calls", 0) for r in history),
            "total_files_created": sum(len(r.get("files_created", [])) for r in history),
            "per_preset": presets,
        },
    }
