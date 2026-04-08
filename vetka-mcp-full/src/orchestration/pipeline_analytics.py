"""
MARKER_152.1: Pipeline Analytics Aggregator

Phase 152 — MCC Analytics Engine.
Reads from multiple data sources (TaskBoard, pipeline_history, feedback reports)
and computes time-series aggregates, per-agent efficiency, weak-link detection,
cost estimation, and per-task timelines.

Output format: JSON dicts compatible with Recharts data shape for frontend charts.

Data sources:
  - data/task_board.json (tasks with stats, agent_stats, result_status)
  - data/pipeline_history.json (append-only run log, max 500)
  - data/feedback/reports/*.json (per-task quality reports)

@status: ACTIVE
@phase: 152
@depends: task_board.py, pipeline_history.py
"""

import json
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger("VETKA_ANALYTICS")

# MARKER_152.1A: Data paths — absolute from __file__ to avoid CWD issues
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_TASK_BOARD_FILE = _PROJECT_ROOT / "data" / "task_board.json"
_PIPELINE_HISTORY_FILE = _PROJECT_ROOT / "data" / "pipeline_history.json"
_FEEDBACK_DIR = _PROJECT_ROOT / "data" / "feedback" / "reports"
_ANALYTICS_CACHE_FILE = _PROJECT_ROOT / "data" / "pipeline_analytics.json"

# MARKER_152.1B: Cost estimation per 1K tokens (approximate, USD)
# Based on typical Polza/provider pricing. Updated as needed.
MODEL_COST_PER_1K = {
    # Dragon Bronze
    "qwen/qwen3-30b-a3b": {"input": 0.0003, "output": 0.0006},
    "qwen/qwen3-coder-flash": {"input": 0.0002, "output": 0.0004},
    "xiaomi/mimo-v2-flash": {"input": 0.0001, "output": 0.0002},
    # Dragon Silver
    "moonshotai/kimi-k2.5": {"input": 0.0008, "output": 0.0016},
    "qwen/qwen3-coder": {"input": 0.0005, "output": 0.001},
    "z-ai/glm-4.7-flash": {"input": 0.0003, "output": 0.0006},
    # Dragon Gold
    "qwen/qwen3-235b-a22b": {"input": 0.002, "output": 0.004},
    # Shared (all tiers)
    "x-ai/grok-4.1-fast": {"input": 0.0004, "output": 0.0008},
    # GPT variant
    "openai/gpt-5.2": {"input": 0.01, "output": 0.03},
    # Research team
    "anthropic/claude-sonnet-4": {"input": 0.003, "output": 0.015},
    "anthropic/claude-haiku-4.5": {"input": 0.001, "output": 0.005},
    # Fallback
    "deepseek/deepseek-v3.2": {"input": 0.0003, "output": 0.0006},
}

# Default cost for unknown models
_DEFAULT_COST = {"input": 0.001, "output": 0.002}

# Preset → cost tier (approx cost multiplier for simple estimation)
PRESET_COST_TIER = {
    "dragon_bronze": 0.3,
    "dragon_silver": 1.0,
    "dragon_gold": 2.5,
    "dragon_gold_gpt": 5.0,
    "titan_lite": 2.0,
    "titan_core": 5.0,
    "titan_prime": 15.0,
    "polza_research": 4.0,
    "polza_mixed": 3.0,
    "xai_direct": 1.5,
}


# ============================================================
# Data Loading
# ============================================================

def _load_task_board() -> Dict[str, Any]:
    """Load task board data."""
    if not _TASK_BOARD_FILE.exists():
        return {}
    try:
        data = json.loads(_TASK_BOARD_FILE.read_text())
        return data.get("tasks", {}) if isinstance(data, dict) else {}
    except Exception as e:
        logger.error(f"Failed to load task board: {e}")
        return {}


def _load_pipeline_history() -> List[Dict]:
    """Load pipeline history records."""
    if not _PIPELINE_HISTORY_FILE.exists():
        return []
    try:
        data = json.loads(_PIPELINE_HISTORY_FILE.read_text())
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.error(f"Failed to load pipeline history: {e}")
        return []


def _load_feedback_reports() -> List[Dict]:
    """Load feedback reports from data/feedback/reports/."""
    reports = []
    if not _FEEDBACK_DIR.exists():
        return reports
    try:
        for f in sorted(_FEEDBACK_DIR.glob("*.json")):
            try:
                report = json.loads(f.read_text())
                if isinstance(report, dict):
                    reports.append(report)
            except Exception:
                continue
    except Exception as e:
        logger.error(f"Failed to load feedback reports: {e}")
    return reports


# ============================================================
# MARKER_152.1C: Time-Series Bucketing
# ============================================================

def _timestamp_to_bucket(ts: float, period: str) -> str:
    """Convert unix timestamp to bucket key.

    Args:
        ts: Unix timestamp
        period: 'hour', 'day', 'week'

    Returns:
        Bucket key string like '2026-02-10 14:00' or '2026-02-10'
    """
    dt = datetime.fromtimestamp(ts)
    if period == "hour":
        return dt.strftime("%Y-%m-%d %H:00")
    elif period == "day":
        return dt.strftime("%Y-%m-%d")
    elif period == "week":
        # ISO week start (Monday)
        week_start = dt - timedelta(days=dt.weekday())
        return week_start.strftime("%Y-%m-%d")
    return dt.strftime("%Y-%m-%d")


def compute_time_series(
    period: str = "day",
    limit_days: int = 30,
) -> List[Dict[str, Any]]:
    """Compute time-bucketed analytics for charts.

    MARKER_152.1C: Reads pipeline_history + task_board, buckets by hour/day/week.
    Returns Recharts-compatible data shape:
    [
        {"bucket": "2026-02-10", "runs": 5, "success": 4, "success_rate": 80,
         "tokens_in": 12000, "tokens_out": 5000, "avg_duration": 120.5,
         "cost_estimate": 0.05, "retries": 2},
        ...
    ]
    """
    history = _load_pipeline_history()
    tasks = _load_task_board()

    cutoff = time.time() - (limit_days * 86400)

    # Merge data: history has timestamps, tasks have agent_stats + adjusted_stats
    # Build lookup: task_id → task data
    task_lookup = {}
    for tid, task in tasks.items():
        if task.get("stats"):
            task_lookup[task.get("pipeline_task_id", tid)] = task

    buckets: Dict[str, Dict] = defaultdict(lambda: {
        "runs": 0,
        "success": 0,
        "failed": 0,
        "tokens_in": 0,
        "tokens_out": 0,
        "total_duration": 0.0,
        "retries": 0,
        "llm_calls": 0,
        "cost_estimate": 0.0,
    })

    for run in history:
        ts = run.get("timestamp", 0)
        if ts < cutoff:
            continue

        bucket_key = _timestamp_to_bucket(ts, period)
        b = buckets[bucket_key]
        b["runs"] += 1
        if run.get("status") == "done":
            b["success"] += 1
        else:
            b["failed"] += 1
        b["tokens_in"] += run.get("tokens_in", 0)
        b["tokens_out"] += run.get("tokens_out", 0)
        b["total_duration"] += run.get("total_duration_s", 0)
        b["llm_calls"] += run.get("llm_calls", 0)

        # Cost estimation
        preset = run.get("preset", "dragon_silver")
        tier = PRESET_COST_TIER.get(preset, 1.0)
        tokens_total = run.get("tokens_in", 0) + run.get("tokens_out", 0)
        b["cost_estimate"] += (tokens_total / 1000) * 0.001 * tier

        # Retries from task stats if available
        task = task_lookup.get(run.get("task_id", ""))
        if task and (task.get("stats") or {}).get("agent_stats"):
            for role_stats in task["stats"]["agent_stats"].values():
                b["retries"] += role_stats.get("retries", 0)

    # Sort and format for Recharts
    result = []
    for bucket_key in sorted(buckets.keys()):
        b = buckets[bucket_key]
        result.append({
            "bucket": bucket_key,
            "runs": b["runs"],
            "success": b["success"],
            "failed": b["failed"],
            "success_rate": round(b["success"] / b["runs"] * 100, 1) if b["runs"] > 0 else 0,
            "tokens_in": b["tokens_in"],
            "tokens_out": b["tokens_out"],
            "avg_duration": round(b["total_duration"] / b["runs"], 1) if b["runs"] > 0 else 0,
            "llm_calls": b["llm_calls"],
            "retries": b["retries"],
            "cost_estimate": round(b["cost_estimate"], 4),
        })

    return result


# ============================================================
# MARKER_152.1D: Per-Agent Aggregates
# ============================================================

def compute_agent_efficiency() -> List[Dict[str, Any]]:
    """Compute per-agent efficiency report across all tasks.

    Aggregates agent_stats from all done/failed tasks in task_board.
    Returns Recharts-compatible data:
    [
        {"role": "scout", "calls": 20, "tokens_in": 5000, "tokens_out": 2000,
         "duration_s": 60.0, "success_count": 18, "fail_count": 2,
         "retries": 0, "success_rate": 90.0, "avg_duration": 3.0,
         "tokens_per_call": 350, "efficiency_score": 0.85},
        ...
    ]
    """
    tasks = _load_task_board()

    role_agg: Dict[str, Dict] = defaultdict(lambda: {
        "calls": 0,
        "tokens_in": 0,
        "tokens_out": 0,
        "duration_s": 0.0,
        "success_count": 0,
        "fail_count": 0,
        "retries": 0,
    })

    for tid, task in tasks.items():
        if task.get("status") not in ("done", "failed"):
            continue
        stats = task.get("stats") or {}
        agent_stats = stats.get("agent_stats", {})

        for role_raw, values in agent_stats.items():
            role = role_raw.lower().strip()
            agg = role_agg[role]
            agg["calls"] += values.get("calls", 0)
            agg["tokens_in"] += values.get("tokens_in", 0)
            agg["tokens_out"] += values.get("tokens_out", 0)
            agg["duration_s"] += values.get("duration_s", 0)
            agg["success_count"] += values.get("success_count", 0)
            agg["fail_count"] += values.get("fail_count", 0)
            agg["retries"] += values.get("retries", 0)

    result = []
    for role in sorted(role_agg.keys()):
        agg = role_agg[role]
        total_attempts = agg["success_count"] + agg["fail_count"]
        success_rate = (agg["success_count"] / total_attempts * 100) if total_attempts > 0 else 0
        avg_duration = (agg["duration_s"] / agg["calls"]) if agg["calls"] > 0 else 0
        tokens_per_call = ((agg["tokens_in"] + agg["tokens_out"]) / agg["calls"]) if agg["calls"] > 0 else 0

        # Efficiency score: weighted blend of success rate + speed + token efficiency
        # Higher is better: 0.0-1.0
        speed_score = max(0, 1.0 - (avg_duration / 120))  # < 120s = good
        token_score = max(0, 1.0 - (tokens_per_call / 10000))  # < 10K tokens/call = good
        efficiency = round(
            0.5 * (success_rate / 100) + 0.3 * speed_score + 0.2 * token_score, 3
        )

        result.append({
            "role": role,
            "calls": agg["calls"],
            "tokens_in": agg["tokens_in"],
            "tokens_out": agg["tokens_out"],
            "duration_s": round(agg["duration_s"], 1),
            "success_count": agg["success_count"],
            "fail_count": agg["fail_count"],
            "retries": agg["retries"],
            "success_rate": round(success_rate, 1),
            "avg_duration": round(avg_duration, 1),
            "tokens_per_call": round(tokens_per_call),
            "efficiency_score": efficiency,
        })

    return result


# ============================================================
# MARKER_152.1E: Weak-Link Detection
# ============================================================

def detect_weak_links(threshold_success: float = 60.0, threshold_retries: int = 2) -> List[Dict]:
    """Identify bottleneck roles in the pipeline.

    A role is "weak" if:
    - success_rate < threshold_success (default 60%)
    - retries > threshold_retries (default 2)
    - avg_duration > 2x median duration

    Returns list of weak-link reports sorted by severity.
    """
    agents = compute_agent_efficiency()
    if not agents:
        return []

    durations = [a["avg_duration"] for a in agents if a["avg_duration"] > 0]
    median_duration = sorted(durations)[len(durations) // 2] if durations else 30.0

    weak_links = []
    for agent in agents:
        reasons = []
        severity = 0  # Higher = worse

        if agent["calls"] < 2:
            continue  # Not enough data

        if agent["success_rate"] < threshold_success:
            reasons.append(f"Low success rate: {agent['success_rate']}% (threshold: {threshold_success}%)")
            severity += 3

        if agent["retries"] > threshold_retries:
            reasons.append(f"High retry count: {agent['retries']} (threshold: {threshold_retries})")
            severity += 2

        if agent["avg_duration"] > 2 * median_duration and median_duration > 0:
            ratio = round(agent["avg_duration"] / median_duration, 1)
            reasons.append(f"Slow: {agent['avg_duration']}s ({ratio}x median)")
            severity += 1

        if reasons:
            weak_links.append({
                "role": agent["role"],
                "severity": severity,
                "reasons": reasons,
                "success_rate": agent["success_rate"],
                "retries": agent["retries"],
                "avg_duration": agent["avg_duration"],
                "efficiency_score": agent["efficiency_score"],
            })

    return sorted(weak_links, key=lambda x: -x["severity"])


# ============================================================
# MARKER_152.1F: Per-Task Drill-Down
# ============================================================

def get_task_analytics(task_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed analytics for a single task.

    Returns:
    {
        "task_id": "tb_xxx",
        "title": "...",
        "status": "done",
        "preset": "dragon_silver",
        "duration_s": 666.8,
        "agent_stats": {...},
        "adjusted_stats": {...},
        "token_distribution": [{"role": "coder", "tokens": 23000, "pct": 60}, ...],
        "timeline_events": [...],
        "cost_estimate": 0.05,
        "retries_total": 2,
        "verifier_confidence": 0.94,
    }
    """
    tasks = _load_task_board()
    task = tasks.get(task_id)
    if not task:
        return None

    stats = task.get("stats") or {}
    agent_stats = stats.get("agent_stats", {})

    # Token distribution (for pie chart)
    token_dist = []
    total_tokens = 0
    for role, values in agent_stats.items():
        tok = values.get("tokens_in", 0) + values.get("tokens_out", 0)
        total_tokens += tok
        token_dist.append({"role": role.lower(), "tokens": tok})

    for item in token_dist:
        item["pct"] = round(item["tokens"] / total_tokens * 100, 1) if total_tokens > 0 else 0
    token_dist.sort(key=lambda x: -x["tokens"])

    # Retries total
    retries = sum(v.get("retries", 0) for v in agent_stats.values())

    # Cost estimation
    preset = stats.get("preset", task.get("preset", "dragon_silver"))
    tier = PRESET_COST_TIER.get(preset, 1.0)
    cost = (total_tokens / 1000) * 0.001 * tier

    # Timeline events — prefer real timestamped events (152.4), fallback to approximate
    real_timeline = stats.get("timeline", [])
    if real_timeline:
        timeline = _normalize_real_timeline(real_timeline)
    else:
        timeline = _build_task_timeline(agent_stats, stats)

    # Adjusted stats
    adjusted = {}
    result_status = task.get("result_status")
    if stats:
        verifier_success = 1.0 if stats.get("success", False) else 0.0
        feedback_map = {"applied": 1.0, "rework": 0.5, "rejected": 0.0}
        user_success = feedback_map.get(result_status, verifier_success)
        adjusted_success = 0.7 * verifier_success + 0.3 * user_success
        adjusted = {
            "adjusted_success": round(adjusted_success, 3),
            "user_feedback": result_status,
            "has_user_feedback": result_status is not None,
        }

    return {
        "task_id": task_id,
        "title": task.get("title", ""),
        "description": task.get("description", ""),
        "status": task.get("status", ""),
        "preset": preset,
        "phase_type": stats.get("phase_type", task.get("phase_type", "")),
        "duration_s": stats.get("duration_s", 0),
        "llm_calls": stats.get("llm_calls", 0),
        "tokens_in": stats.get("tokens_in", 0),
        "tokens_out": stats.get("tokens_out", 0),
        "subtasks_total": stats.get("subtasks_total", 0),
        "subtasks_completed": stats.get("subtasks_completed", 0),
        "agent_stats": agent_stats,
        "adjusted_stats": adjusted,
        "token_distribution": token_dist,
        "timeline_events": timeline,
        "cost_estimate": round(cost, 4),
        "retries_total": retries,
        "verifier_confidence": stats.get("verifier_avg_confidence", 0),
        "created_at": task.get("created_at", ""),
        "completed_at": task.get("completed_at", ""),
        "source": task.get("source", ""),
        "source_chat_id": task.get("source_chat_id", ""),
    }


def _normalize_real_timeline(events: List[Dict]) -> List[Dict]:
    """Normalize real timestamped timeline events (152.4) for frontend.

    Real events have: {ts, role, event, detail, duration_s, subtask_idx}
    Frontend needs: events sorted by ts, with relative offsets from pipeline start.

    Returns list of events enriched with offset_s (seconds from first event).
    """
    if not events:
        return []

    # Sort by timestamp
    sorted_events = sorted(events, key=lambda e: e.get("ts", 0))
    t0 = sorted_events[0].get("ts", 0)

    result = []
    for ev in sorted_events:
        result.append({
            "ts": ev.get("ts", 0),
            "offset_s": round(ev.get("ts", 0) - t0, 2),
            "role": ev.get("role", ""),
            "event": ev.get("event", ""),
            "detail": ev.get("detail", ""),
            "duration_s": ev.get("duration_s", 0),
            "subtask_idx": ev.get("subtask_idx", -1),
        })

    return result


def _build_task_timeline(agent_stats: Dict, pipeline_stats: Dict) -> List[Dict]:
    """Build approximate timeline of agent events for Gantt chart.

    MARKER_152.1F: Uses agent_stats duration to reconstruct order.
    Actual timestamped events come in 152.4.

    Returns:
    [
        {"role": "scout", "action": "completed", "duration_s": 8.0,
         "tokens": 3500, "start_offset": 0, "end_offset": 8.0},
        ...
    ]
    """
    # Standard pipeline order
    ROLE_ORDER = ["scout", "architect", "researcher", "coder", "verifier"]

    timeline = []
    offset = 0.0

    for role in ROLE_ORDER:
        stats = agent_stats.get(role, {})
        if not stats or stats.get("calls", 0) == 0:
            continue

        duration = stats.get("duration_s", 0)
        tokens = stats.get("tokens_in", 0) + stats.get("tokens_out", 0)
        success = stats.get("success_count", 0)
        fail = stats.get("fail_count", 0)
        retries = stats.get("retries", 0)

        action = "completed"
        if fail > 0 and success == 0:
            action = "failed"
        elif retries > 0:
            action = "retried"

        timeline.append({
            "role": role,
            "action": action,
            "duration_s": round(duration, 1),
            "tokens": tokens,
            "calls": stats.get("calls", 0),
            "retries": retries,
            "start_offset": round(offset, 1),
            "end_offset": round(offset + duration, 1),
        })
        offset += duration

    return timeline


# ============================================================
# MARKER_152.13: DAG Mini-Stats per Task Node
# ============================================================

PRESET_COST_TIER_DAG = {
    "dragon_bronze": 0.5, "dragon_silver": 1.0, "dragon_gold": 2.5,
    "titan_lite": 0.3, "titan_core": 1.0, "titan_prime": 2.0,
}


def compute_dag_mini_stats(task_ids: Optional[List[str]] = None) -> Dict[str, Dict]:
    """Compute mini-stats for DAG node enrichment.

    MARKER_152.13: Per-node duration, success%, llm_calls, tokens, cost.
    Keeps it lightweight — only fields useful for DAG node tooltips/badges.

    Args:
        task_ids: Optional filter — only compute for these task IDs. None = all.

    Returns:
        {
            "tb_001": {
                "duration_s": 66.8,
                "success": true,
                "llm_calls": 12,
                "tokens_total": 23000,
                "cost_estimate": 0.023,
                "subtasks_done": 3,
                "subtasks_total": 3,
                "retries": 1,
                "verifier_confidence": 0.9,
            },
            ...
        }
    """
    tasks = _load_task_board()
    result = {}

    for tid, task in tasks.items():
        if task_ids is not None and tid not in task_ids:
            continue

        stats = task.get("stats") or {}
        if not stats:
            # No pipeline stats recorded — skip (pending/queued tasks)
            continue

        tokens_in = stats.get("tokens_in", 0)
        tokens_out = stats.get("tokens_out", 0)
        total_tokens = tokens_in + tokens_out

        preset = stats.get("preset", task.get("preset", "dragon_silver"))
        tier = PRESET_COST_TIER_DAG.get(preset, 1.0)
        cost = (total_tokens / 1000) * 0.001 * tier

        agent_stats = stats.get("agent_stats", {})
        retries = sum(v.get("retries", 0) for v in agent_stats.values())

        result[tid] = {
            "duration_s": round(stats.get("duration_s", 0), 1),
            "success": stats.get("success", False),
            "llm_calls": stats.get("llm_calls", 0),
            "tokens_total": total_tokens,
            "cost_estimate": round(cost, 4),
            "subtasks_done": stats.get("subtasks_completed", 0),
            "subtasks_total": stats.get("subtasks_total", 0),
            "retries": retries,
            "verifier_confidence": round(stats.get("verifier_avg_confidence", 0), 2),
        }

    return result


# ============================================================
# MARKER_152.1G: Summary Dashboard
# ============================================================

def compute_summary() -> Dict[str, Any]:
    """Compute overall summary for the stats dashboard top row.

    Returns:
    {
        "total_runs": 25,
        "success_rate": 80.0,
        "adjusted_success_avg": 75.0,
        "total_tokens": 500000,
        "total_cost_estimate": 1.25,
        "avg_duration_s": 180.5,
        "total_retries": 15,
        "total_llm_calls": 200,
        "tasks_by_status": {"done": 20, "failed": 5, ...},
        "tasks_by_preset": {"dragon_silver": 15, ...},
        "tasks_by_source": {"dragon_pipeline": 10, "heartbeat": 5, ...},
        "weak_links": [...],
        "time_series": [...],
        "agent_efficiency": [...],
    }
    """
    tasks = _load_task_board()
    history = _load_pipeline_history()

    # Task counts by status
    status_counts = defaultdict(int)
    preset_counts = defaultdict(int)
    source_counts = defaultdict(int)

    total_adjusted = 0.0
    adjusted_count = 0
    total_retries = 0
    total_tokens = 0
    total_cost = 0.0
    total_duration = 0.0
    total_llm_calls = 0
    done_tasks = 0

    for tid, task in tasks.items():
        status = task.get("status", "pending")
        status_counts[status] += 1

        if status in ("done", "failed"):
            preset = task.get("preset", (task.get("stats") or {}).get("preset", "unknown"))
            preset_counts[preset] += 1

            source = task.get("source", "unknown")
            source_counts[source] += 1

            stats = task.get("stats") or {}
            if stats:
                total_tokens += stats.get("tokens_in", 0) + stats.get("tokens_out", 0)
                total_duration += stats.get("duration_s", 0)
                total_llm_calls += stats.get("llm_calls", 0)

                # Cost
                p = stats.get("preset", preset)
                tier = PRESET_COST_TIER.get(p, 1.0)
                tok = stats.get("tokens_in", 0) + stats.get("tokens_out", 0)
                total_cost += (tok / 1000) * 0.001 * tier

                # Retries
                for role_stats in stats.get("agent_stats", {}).values():
                    total_retries += role_stats.get("retries", 0)

                # Adjusted success
                if task.get("result_status") is not None:
                    verifier_s = 1.0 if stats.get("success", False) else 0.0
                    fb_map = {"applied": 1.0, "rework": 0.5, "rejected": 0.0}
                    user_s = fb_map.get(task["result_status"], verifier_s)
                    total_adjusted += 0.7 * verifier_s + 0.3 * user_s
                    adjusted_count += 1

            if status == "done":
                done_tasks += 1

    completed = done_tasks + status_counts.get("failed", 0)
    success_rate = round(done_tasks / completed * 100, 1) if completed > 0 else 0
    avg_adjusted = round(total_adjusted / adjusted_count * 100, 1) if adjusted_count > 0 else 0
    avg_duration = round(total_duration / completed, 1) if completed > 0 else 0

    return {
        "total_runs": completed,
        "success_rate": success_rate,
        "adjusted_success_avg": avg_adjusted,
        "total_tokens": total_tokens,
        "total_cost_estimate": round(total_cost, 4),
        "avg_duration_s": avg_duration,
        "total_retries": total_retries,
        "total_llm_calls": total_llm_calls,
        "tasks_by_status": dict(status_counts),
        "tasks_by_preset": dict(preset_counts),
        "tasks_by_source": dict(source_counts),
        "weak_links": detect_weak_links(),
        "time_series": compute_time_series(period="day", limit_days=30),
        "agent_efficiency": compute_agent_efficiency(),
    }


# ============================================================
# MARKER_152.1H: Preset/Team Comparison
# ============================================================

def compute_team_comparison() -> List[Dict[str, Any]]:
    """Compare team presets (Bronze vs Silver vs Gold etc).

    Returns Recharts-compatible:
    [
        {"preset": "dragon_bronze", "runs": 10, "success_rate": 70.0,
         "avg_duration": 35.0, "avg_tokens": 5000, "cost_per_run": 0.002,
         "retries_per_run": 0.5},
        ...
    ]
    """
    tasks = _load_task_board()

    preset_data: Dict[str, Dict] = defaultdict(lambda: {
        "runs": 0,
        "success": 0,
        "total_duration": 0.0,
        "total_tokens": 0,
        "total_cost": 0.0,
        "total_retries": 0,
    })

    for tid, task in tasks.items():
        if task.get("status") not in ("done", "failed"):
            continue
        stats = task.get("stats") or {}
        preset = stats.get("preset", task.get("preset", "unknown"))

        d = preset_data[preset]
        d["runs"] += 1
        if task.get("status") == "done":
            d["success"] += 1

        d["total_duration"] += stats.get("duration_s", 0)
        tok = stats.get("tokens_in", 0) + stats.get("tokens_out", 0)
        d["total_tokens"] += tok

        tier = PRESET_COST_TIER.get(preset, 1.0)
        d["total_cost"] += (tok / 1000) * 0.001 * tier

        for role_stats in stats.get("agent_stats", {}).values():
            d["total_retries"] += role_stats.get("retries", 0)

    result = []
    for preset in sorted(preset_data.keys()):
        d = preset_data[preset]
        runs = d["runs"]
        if runs == 0:
            continue
        result.append({
            "preset": preset,
            "runs": runs,
            "success_rate": round(d["success"] / runs * 100, 1),
            "avg_duration": round(d["total_duration"] / runs, 1),
            "avg_tokens": round(d["total_tokens"] / runs),
            "cost_per_run": round(d["total_cost"] / runs, 4),
            "retries_per_run": round(d["total_retries"] / runs, 1),
        })

    return result


# ============================================================
# MARKER_152.1I: Trends (Time-Series with Custom Period)
# ============================================================

def compute_trends(
    period: str = "day",
    limit_days: int = 30,
    metric: str = "success_rate",
) -> Dict[str, Any]:
    """Compute trend data with direction indicator.

    Returns:
    {
        "metric": "success_rate",
        "period": "day",
        "trend": "up" | "down" | "stable",
        "current_value": 85.0,
        "previous_value": 75.0,
        "change_pct": 13.3,
        "data_points": [...]
    }
    """
    series = compute_time_series(period=period, limit_days=limit_days)

    if len(series) < 2:
        return {
            "metric": metric,
            "period": period,
            "trend": "stable",
            "current_value": series[-1].get(metric, 0) if series else 0,
            "previous_value": 0,
            "change_pct": 0,
            "data_points": series,
        }

    # Compare last bucket vs previous
    current = series[-1].get(metric, 0)
    previous = series[-2].get(metric, 0)

    if previous == 0:
        change = 100.0 if current > 0 else 0
    else:
        change = round((current - previous) / previous * 100, 1)

    if change > 5:
        trend = "up"
    elif change < -5:
        trend = "down"
    else:
        trend = "stable"

    return {
        "metric": metric,
        "period": period,
        "trend": trend,
        "current_value": current,
        "previous_value": previous,
        "change_pct": change,
        "data_points": series,
    }


# ============================================================
# MARKER_152.1J: Cost Estimation
# ============================================================

def compute_cost_report() -> Dict[str, Any]:
    """Compute cost estimation report.

    Returns:
    {
        "total_cost_estimate": 1.25,
        "cost_by_preset": [{"preset": "dragon_silver", "cost": 0.80, "runs": 15}, ...],
        "cost_by_role": [{"role": "coder", "cost": 0.60, "tokens": 300000}, ...],
        "cost_trend": [{"bucket": "2026-02-10", "cost": 0.05}, ...],
    }
    """
    tasks = _load_task_board()

    preset_cost: Dict[str, Dict] = defaultdict(lambda: {"cost": 0.0, "runs": 0, "tokens": 0})
    role_cost: Dict[str, Dict] = defaultdict(lambda: {"cost": 0.0, "tokens": 0})
    total_cost = 0.0

    for tid, task in tasks.items():
        if task.get("status") not in ("done", "failed"):
            continue
        stats = task.get("stats") or {}
        preset = stats.get("preset", task.get("preset", "unknown"))
        tier = PRESET_COST_TIER.get(preset, 1.0)

        tok = stats.get("tokens_in", 0) + stats.get("tokens_out", 0)
        cost = (tok / 1000) * 0.001 * tier
        total_cost += cost

        preset_cost[preset]["cost"] += cost
        preset_cost[preset]["runs"] += 1
        preset_cost[preset]["tokens"] += tok

        # Per-role costs (approximate — proportional to tokens)
        for role, values in stats.get("agent_stats", {}).items():
            role_tok = values.get("tokens_in", 0) + values.get("tokens_out", 0)
            role_c = (role_tok / 1000) * 0.001 * tier
            role_cost[role.lower()]["cost"] += role_c
            role_cost[role.lower()]["tokens"] += role_tok

    return {
        "total_cost_estimate": round(total_cost, 4),
        "cost_by_preset": sorted(
            [{"preset": p, **{k: round(v, 4) if isinstance(v, float) else v for k, v in d.items()}}
             for p, d in preset_cost.items()],
            key=lambda x: -x["cost"]
        ),
        "cost_by_role": sorted(
            [{"role": r, **{k: round(v, 4) if isinstance(v, float) else v for k, v in d.items()}}
             for r, d in role_cost.items()],
            key=lambda x: -x["cost"]
        ),
        "cost_trend": [
            {"bucket": pt["bucket"], "cost": pt["cost_estimate"]}
            for pt in compute_time_series(period="day", limit_days=30)
        ],
    }
