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

from fastapi import APIRouter, Query, Path as ApiPath
from typing import Optional, List, Dict, Any
from pathlib import Path as FilePath
from datetime import datetime
import json
import time
import logging

logger = logging.getLogger(__name__)
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
    task_id: str = ApiPath(..., description="Task board ID (e.g. tb_xxx)"),
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
        description="Metric to trend: success_rate, avg_duration, tokens_in, cost_estimate",
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
    chat_id: str = ApiPath(..., description="Chat UUID to lookup tasks for"),
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
            if (
                task.get("source_chat_id") == chat_id
                or task.get("source_group_id") == chat_id
            ):
                matching.append(
                    {
                        "id": tid,
                        "title": task.get("title", ""),
                        "status": task.get("status", ""),
                        "preset": task.get("preset", ""),
                        "source": task.get("source", ""),
                        "created_at": task.get("created_at", ""),
                    }
                )

        return {"success": True, "tasks": matching, "total": len(matching)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# MARKER_152.12D: Pipeline Context Summary
# ============================================================


@router.get("/context")
async def analytics_context():
    """Assembled pipeline context: pinned files + recent digest.

    Returns everything a pipeline needs for context injection.
    Used by: StatsDashboard context panel, pipeline pre-flight check.
    """
    import json
    from pathlib import Path as PathLib

    _PROJECT_ROOT = PathLib(__file__).resolve().parent.parent.parent.parent

    result = {"pinned_files": [], "digest_summary": "", "pinned_count": 0}

    # 1. Pinned files
    try:
        pinned_path = _PROJECT_ROOT / "data" / "pinned_files.json"
        if pinned_path.exists():
            pinned_data = json.loads(pinned_path.read_text())
            if isinstance(pinned_data, dict):
                for fp, meta in pinned_data.items():
                    result["pinned_files"].append(
                        {
                            "file_path": fp,
                            "reason": meta.get("reason", "")
                            if isinstance(meta, dict)
                            else "",
                            "timestamp": meta.get("timestamp", "")
                            if isinstance(meta, dict)
                            else "",
                        }
                    )
            elif isinstance(pinned_data, list):
                result["pinned_files"] = pinned_data[:20]
            result["pinned_count"] = len(result["pinned_files"])
    except Exception:
        pass

    # 2. Project digest headline
    try:
        digest_path = _PROJECT_ROOT / "data" / "project_digest.json"
        if digest_path.exists():
            digest = json.loads(digest_path.read_text())
            phase = digest.get("current_phase", "")
            status = digest.get("status", "")
            result["digest_summary"] = f"Phase {phase}: {status}" if phase else ""
    except Exception:
        pass

    return {"success": True, "data": result}


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
    MARKER_152.13: Enriched with per-node mini-stats (duration, success%, cost).
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
            "done": "#22c55e",
            "running": "#3b82f6",
            "pending": "#94a3b8",
            "failed": "#ef4444",
            "hold": "#f59e0b",
            "cancelled": "#6b7280",
        }

        # Apply limit (most recent first by created_at)
        sorted_tasks = sorted(
            tasks.items(),
            key=lambda x: x[1].get("created_at", ""),
            reverse=True,
        )[:limit]

        if status_filter:
            sorted_tasks = [
                (tid, t) for tid, t in sorted_tasks if t.get("status") == status_filter
            ]

        task_ids = {tid for tid, _ in sorted_tasks}

        # MARKER_152.13: Fetch mini-stats for all visible nodes
        from src.orchestration.pipeline_analytics import compute_dag_mini_stats

        mini_stats = compute_dag_mini_stats(task_ids=list(task_ids))

        for idx, (tid, task) in enumerate(sorted_tasks):
            status = task.get("status", "pending")
            node_data = {
                "label": task.get("title", tid)[:60],
                "status": status,
                "preset": task.get("preset", ""),
                "phase_type": task.get("phase_type", ""),
                "priority": task.get("priority", 3),
                "color": STATUS_COLORS.get(status, "#94a3b8"),
            }

            # MARKER_152.13: Merge mini-stats if available
            if tid in mini_stats:
                node_data["mini_stats"] = mini_stats[tid]

            nodes.append(
                {
                    "id": tid,
                    "type": "taskNode",
                    "position": {"x": (idx % 5) * 280, "y": (idx // 5) * 120},
                    "data": node_data,
                }
            )

            # Build edges from dependencies
            for dep in task.get("dependencies", []):
                if dep in task_ids:
                    edges.append(
                        {
                            "id": f"e-{dep}-{tid}",
                            "source": dep,
                            "target": tid,
                            "animated": status == "running",
                        }
                    )

        return {"success": True, "nodes": nodes, "edges": edges, "total": len(nodes)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# MARKER_155.STATS.ENDPOINTS: Agent Metrics Dashboard (Phase 155)
# ============================================================

from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Any, Optional


class AgentRunMetric(BaseModel):
    """Single agent run metric record."""

    run_id: str
    agent_id: str
    agent_type: str  # scout, researcher, architect, coder, verifier
    task_id: str
    pipeline_id: str
    start_time: str  # ISO format
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    quality_score: Optional[float] = None  # 0-100
    architect_remark: Optional[str] = None
    success: bool = False
    error_message: Optional[str] = None
    model_used: Optional[str] = None
    provider: Optional[str] = None
    tier: Optional[str] = None  # bronze, silver, gold


class AgentMetricsSummary(BaseModel):
    """Aggregated metrics for an agent type."""

    agent_type: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    avg_duration: float
    avg_quality: float
    total_tokens: int
    total_cost: float
    recent_remarks: List[str]


# In-memory storage for agent metrics (will persist to file)
_agent_metrics: List[Dict[str, Any]] = []
_metrics_file: Optional[FilePath] = None


def _get_metrics_file() -> FilePath:
    """Get path to agent metrics storage file."""
    global _metrics_file
    if _metrics_file is None:
        _PROJECT_ROOT = FilePath(__file__).resolve().parent.parent.parent.parent
        _metrics_file = _PROJECT_ROOT / "data" / "agent_metrics.json"
        _metrics_file.parent.mkdir(parents=True, exist_ok=True)
    return _metrics_file


def _load_agent_metrics() -> List[Dict[str, Any]]:
    """Load agent metrics from disk."""
    global _agent_metrics
    try:
        file_path = _get_metrics_file()
        if file_path.exists():
            data = json.loads(file_path.read_text())
            _agent_metrics = data.get("runs", [])
    except Exception as e:
        logger.warning(f"[AgentMetrics] Failed to load metrics: {e}")
    return _agent_metrics


def _save_agent_metrics():
    """Save agent metrics to disk."""
    try:
        file_path = _get_metrics_file()
        file_path.write_text(
            json.dumps(
                {"runs": _agent_metrics, "updated_at": datetime.now().isoformat()},
                indent=2,
            )
        )
    except Exception as e:
        logger.warning(f"[AgentMetrics] Failed to save metrics: {e}")


def record_agent_run(metric: AgentRunMetric):
    """Record a new agent run metric (called from pipeline)."""
    global _agent_metrics
    _agent_metrics.append(metric.dict())
    # Keep only last 1000 runs to prevent file bloat
    if len(_agent_metrics) > 1000:
        _agent_metrics = _agent_metrics[-1000:]
    _save_agent_metrics()


@router.get("/agents/summary")
async def get_agents_summary(
    period: str = Query("7d", description="Period: 1d, 7d, 30d, all"),
):
    """Get aggregated metrics for all agent types.

    MARKER_155.STATS.AGENTS_SUMMARY: Overall agent performance dashboard.
    """
    try:
        import json
        from pathlib import Path as PathLib

        # Load pipeline history for agent data
        _PROJECT_ROOT = PathLib(__file__).resolve().parent.parent.parent.parent
        _PIPELINE_HISTORY_FILE = _PROJECT_ROOT / "data" / "pipeline_history.json"

        runs = []
        if _PIPELINE_HISTORY_FILE.exists():
            data = json.loads(_PIPELINE_HISTORY_FILE.read_text())
            runs = data.get("runs", []) if isinstance(data, dict) else []

        # Parse period
        period_days = {"1d": 1, "7d": 7, "30d": 30, "all": 3650}.get(period, 7)
        cutoff_time = time.time() - (period_days * 24 * 60 * 60)

        # Filter recent runs
        recent_runs = [r for r in runs if r.get("timestamp", 0) > cutoff_time]

        # Aggregate by agent type
        agent_types = ["scout", "researcher", "architect", "coder", "verifier"]
        summary = {}

        for agent_type in agent_types:
            agent_runs = [
                r for r in recent_runs if agent_type in str(r.get("agent", "")).lower()
            ]

            if not agent_runs:
                summary[agent_type] = {
                    "agent_type": agent_type,
                    "total_runs": 0,
                    "successful_runs": 0,
                    "failed_runs": 0,
                    "avg_duration": 0.0,
                    "avg_quality": 0.0,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "recent_remarks": [],
                }
                continue

            successful = [r for r in agent_runs if r.get("success", False)]
            durations = [
                r.get("duration_seconds", 0)
                for r in agent_runs
                if r.get("duration_seconds")
            ]
            tokens = [r.get("total_tokens", 0) for r in agent_runs]
            costs = [r.get("cost_usd", 0) for r in agent_runs]

            summary[agent_type] = {
                "agent_type": agent_type,
                "total_runs": len(agent_runs),
                "successful_runs": len(successful),
                "failed_runs": len(agent_runs) - len(successful),
                "avg_duration": sum(durations) / len(durations) if durations else 0.0,
                "avg_quality": sum(r.get("quality_score", 0) for r in agent_runs)
                / len(agent_runs)
                if agent_runs
                else 0.0,
                "total_tokens": sum(tokens),
                "total_cost": sum(costs),
                "recent_remarks": [
                    r.get("architect_remark", "")
                    for r in agent_runs[-5:]
                    if r.get("architect_remark")
                ],
            }

        return {"success": True, "period": period, "agents": summary}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/agents/{agent_type}/runs")
async def get_agent_runs(
    agent_type: str = ApiPath(
        ..., description="Agent type: scout, researcher, architect, coder, verifier"
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get detailed run history for a specific agent type.

    MARKER_155.STATS.AGENT_RUNS: Individual run details with remarks.
    """
    try:
        import json
        from pathlib import Path as PathLib

        _PROJECT_ROOT = PathLib(__file__).resolve().parent.parent.parent.parent
        _PIPELINE_HISTORY_FILE = _PROJECT_ROOT / "data" / "pipeline_history.json"

        runs = []
        if _PIPELINE_HISTORY_FILE.exists():
            data = json.loads(_PIPELINE_HISTORY_FILE.read_text())
            runs = data.get("runs", []) if isinstance(data, dict) else []

        # Filter by agent type
        agent_runs = [r for r in runs if agent_type in str(r.get("agent", "")).lower()]

        # Sort by timestamp (newest first)
        agent_runs.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

        total = len(agent_runs)
        paginated = agent_runs[offset : offset + limit]

        return {
            "success": True,
            "agent_type": agent_type,
            "runs": paginated,
            "total": total,
            "offset": offset,
            "limit": limit,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/agents/{run_id}/remark")
async def add_architect_remark(
    run_id: str = ApiPath(..., description="Run ID to add remark to"),
    remark: str = Query(..., description="Architect's remark"),
    score: int = Query(..., ge=0, le=100, description="Quality score 0-100"),
):
    """Add architect's remark to a specific run.

    MARKER_155.STATS.REMARK: Quality feedback from architect.
    """
    try:
        import json
        from pathlib import Path as PathLib

        _PROJECT_ROOT = PathLib(__file__).resolve().parent.parent.parent.parent
        _PIPELINE_HISTORY_FILE = _PROJECT_ROOT / "data" / "pipeline_history.json"

        if not _PIPELINE_HISTORY_FILE.exists():
            return {"success": False, "error": "Pipeline history not found"}

        data = json.loads(_PIPELINE_HISTORY_FILE.read_text())
        runs = data.get("runs", []) if isinstance(data, dict) else []

        # Find and update run
        for run in runs:
            if run.get("run_id") == run_id or run.get("id") == run_id:
                run["architect_remark"] = remark
                run["quality_score"] = score
                run["remarked_at"] = datetime.now().isoformat()

                # Save back
                data["runs"] = runs
                _PIPELINE_HISTORY_FILE.write_text(json.dumps(data, indent=2))

                return {"success": True, "message": "Remark added", "run_id": run_id}

        return {"success": False, "error": f"Run not found: {run_id}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
