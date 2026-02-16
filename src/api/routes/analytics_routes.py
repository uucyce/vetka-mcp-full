# MARKER_152.2: Analytics REST API
"""
Phase 152 — Pipeline Analytics REST API.
Exposes analytics data for the MCC Stats Dashboard.

Endpoints:
  GET /api/analytics/summary — Overall dashboard data (cards + charts)
  GET /api/analytics/task/{task_id} — Per-task drill-down
  GET /api/analytics/agents — Per-agent efficiency report
  GET /api/analytics/trends — Time-bucketed trend data
  GET /api/analytics/cost — Cost estimation report
  GET /api/analytics/teams — Team/preset comparison
  GET /api/analytics/tasks-by-chat/{chat_id} — Reverse lookup by chat (152.3)
  GET /api/analytics/dag/tasks — Task DAG nodes + edges (152.9)

@status: ACTIVE
@phase: 152
@depends: src/orchestration/pipeline_analytics.py
"""

from fastapi import APIRouter, Query, Path
from typing import Optional

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# ============================================================
# MARKER_152.2A: Dashboard Summary
# ============================================================

@router.get("/summary")
async def analytics_summary():
    """Overall stats dashboard data — summary cards + time-series + agent efficiency.

    Returns everything the Stats Dashboard top row needs.
    Used by: PipelineStats expanded mode, Stats Dashboard fullscreen tab (152.5).
    """
    from src.orchestration.pipeline_analytics import compute_summary
    return {"success": True, "data": compute_summary()}


# ============================================================
# MARKER_152.2B: Per-Task Drill-Down
# ============================================================

@router.get("/task/{task_id}")
async def analytics_task(
    task_id: str = Path(..., description="Task board ID (e.g. tb_xxx)")
):
    """Per-task analytics drill-down — timeline, token distribution, agent stats.

    Used by: Task Drill-Down Modal (152.6).
    """
    from src.orchestration.pipeline_analytics import get_task_analytics
    result = get_task_analytics(task_id)
    if result is None:
        return {"success": False, "error": f"Task not found: {task_id}"}
    return {"success": True, "data": result}


# ============================================================
# MARKER_152.2C: Per-Agent Efficiency
# ============================================================

@router.get("/agents")
async def analytics_agents():
    """Per-agent efficiency report — calls, tokens, duration, success rate, retries.

    Used by: Per-agent cards in Stats Dashboard, weak-link highlighting.
    """
    from src.orchestration.pipeline_analytics import (
        compute_agent_efficiency,
        detect_weak_links,
    )
    return {
        "success": True,
        "agents": compute_agent_efficiency(),
        "weak_links": detect_weak_links(),
    }


# ============================================================
# MARKER_152.2D: Time-Series Trends
# ============================================================

@router.get("/trends")
async def analytics_trends(
    period: str = Query("day", description="Bucket period: hour, day, week"),
    limit_days: int = Query(30, ge=1, le=365, description="Lookback window in days"),
    metric: str = Query(
        "success_rate",
        description="Metric to trend: success_rate, avg_duration, tokens_in, cost_estimate"
    ),
):
    """Time-bucketed trend data with direction indicator.

    Used by: Stats Dashboard middle row (success rate trend, token consumption).
    """
    from src.orchestration.pipeline_analytics import compute_trends
    return {
        "success": True,
        "data": compute_trends(period=period, limit_days=limit_days, metric=metric),
    }


# ============================================================
# MARKER_152.2E: Cost Report
# ============================================================

@router.get("/cost")
async def analytics_cost():
    """Cost estimation report — by preset, by role, over time.

    Used by: Stats Dashboard cost section, team comparison.
    """
    from src.orchestration.pipeline_analytics import compute_cost_report
    return {"success": True, "data": compute_cost_report()}


# ============================================================
# MARKER_152.2F: Team Comparison
# ============================================================

@router.get("/teams")
async def analytics_teams():
    """Team/preset comparison — success rate, duration, tokens, cost per team.

    Used by: Stats Dashboard bottom-right team comparison grouped BarChart.
    """
    from src.orchestration.pipeline_analytics import compute_team_comparison
    return {"success": True, "teams": compute_team_comparison()}


# ============================================================
# MARKER_152.3A: Tasks by Chat ID (Provenance Reverse Lookup)
# ============================================================

@router.get("/tasks-by-chat/{chat_id}")
async def analytics_tasks_by_chat(
    chat_id: str = Path(..., description="Chat UUID to lookup tasks for")
):
    """Reverse lookup: find all tasks created from a specific VETKA chat.

    MARKER_152.3: Task provenance — traces tasks back to originating chat.
    """
    import json
    from pathlib import Path as PathLib
    _PROJECT_ROOT = PathLib(__file__).resolve().parent.parent.parent.parent
    _TASK_BOARD_FILE = _PROJECT_ROOT / "data" / "task_board.json"

    try:
        if not _TASK_BOARD_FILE.exists():
            return {"success": True, "tasks": [], "total": 0}

        data = json.loads(_TASK_BOARD_FILE.read_text())
        tasks = data.get("tasks", {}) if isinstance(data, dict) else {}

        matching = []
        for tid, task in tasks.items():
            if (task.get("source_chat_id") == chat_id or
                    task.get("source_group_id") == chat_id):
                matching.append({
                    "id": tid,
                    "title": task.get("title", ""),
                    "status": task.get("status", ""),
                    "preset": task.get("preset", ""),
                    "source": task.get("source", ""),
                    "created_at": task.get("created_at", ""),
                })

        return {"success": True, "tasks": matching, "total": len(matching)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# MARKER_152.9A: Task DAG — Nodes + Edges for ReactFlow
# ============================================================

@router.get("/dag/tasks")
async def analytics_dag_tasks(
    limit: int = Query(50, ge=1, le=200, description="Max tasks to include"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
):
    """Task DAG nodes + edges for ReactFlow visualization.

    Converts TaskBoard dependencies into ReactFlow-compatible nodes/edges.
    Used by: Task DAG panel in MCC (152.9).
    """
    import json
    from pathlib import Path as PathLib
    _PROJECT_ROOT = PathLib(__file__).resolve().parent.parent.parent.parent
    _TASK_BOARD_FILE = _PROJECT_ROOT / "data" / "task_board.json"

    try:
        if not _TASK_BOARD_FILE.exists():
            return {"success": True, "nodes": [], "edges": []}

        data = json.loads(_TASK_BOARD_FILE.read_text())
        tasks = data.get("tasks", {}) if isinstance(data, dict) else {}

        nodes = []
        edges = []
        STATUS_COLORS = {
            "done": "#22c55e", "running": "#3b82f6", "pending": "#94a3b8",
            "failed": "#ef4444", "hold": "#f59e0b", "cancelled": "#6b7280",
        }

        # Apply limit (most recent first by created_at)
        sorted_tasks = sorted(
            tasks.items(),
            key=lambda x: x[1].get("created_at", ""),
            reverse=True,
        )[:limit]

        if status_filter:
            sorted_tasks = [(tid, t) for tid, t in sorted_tasks if t.get("status") == status_filter]

        task_ids = {tid for tid, _ in sorted_tasks}

        for idx, (tid, task) in enumerate(sorted_tasks):
            status = task.get("status", "pending")
            nodes.append({
                "id": tid,
                "type": "taskNode",
                "position": {"x": (idx % 5) * 280, "y": (idx // 5) * 120},
                "data": {
                    "label": task.get("title", tid)[:60],
                    "status": status,
                    "preset": task.get("preset", ""),
                    "phase_type": task.get("phase_type", ""),
                    "priority": task.get("priority", 3),
                    "color": STATUS_COLORS.get(status, "#94a3b8"),
                },
            })

            # Build edges from dependencies
            for dep in task.get("dependencies", []):
                if dep in task_ids:
                    edges.append({
                        "id": f"e-{dep}-{tid}",
                        "source": dep,
                        "target": tid,
                        "animated": status == "running",
                    })

        return {"success": True, "nodes": nodes, "edges": edges, "total": len(nodes)}
    except Exception as e:
        return {"success": False, "error": str(e)}
