"""
REFLEX REST API — Telemetry & Debug endpoints.

MARKER_172.P5.API

Provides observability into REFLEX tool selection:
- GET /api/reflex/stats      — tool usage stats, success rates, top tools
- GET /api/reflex/recommend   — debug: get recommendations for a task description
- GET /api/reflex/feedback    — raw feedback log stats
- GET /api/reflex/health      — REFLEX system health check

Part of VETKA OS:
  VETKA > REFLEX > Telemetry API (this file)

@status: active
@phase: 172.P5
@depends: reflex_scorer, reflex_feedback, reflex_registry
"""

import logging
import time
from typing import Dict, Any, List

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reflex", tags=["reflex"])


def _is_reflex_enabled() -> bool:
    """Check if REFLEX is enabled."""
    try:
        from src.services.reflex_scorer import REFLEX_ENABLED
        return REFLEX_ENABLED
    except ImportError:
        return False


# ─── P5.1: Stats endpoint ────────────────────────────────────────

@router.get("/stats")
async def reflex_stats() -> Dict[str, Any]:
    """MARKER_172.P5.1 — Tool usage statistics.

    Returns tool usage counts, success rates, top tools,
    and aggregated feedback scores.
    """
    if not _is_reflex_enabled():
        return {
            "enabled": False,
            "message": "REFLEX is disabled. Set REFLEX_ENABLED=1 to activate.",
        }

    try:
        from src.services.reflex_feedback import get_reflex_feedback
        from src.services.reflex_registry import get_reflex_registry

        fb = get_reflex_feedback()
        registry = get_reflex_registry()

        # Get feedback stats
        stats = fb.get_stats()

        # Get bulk scores for all phases
        scores_all = fb.get_scores_bulk("*")
        scores_research = fb.get_scores_bulk("research")
        scores_fix = fb.get_scores_bulk("fix")
        scores_build = fb.get_scores_bulk("build")

        # Registry info
        all_tools = registry.get_all_tools()

        return {
            "enabled": True,
            "registry": {
                "total_tools": len(all_tools),
                "active_tools": len([t for t in all_tools if t.active]),
                "namespaces": list(set(t.namespace for t in all_tools)),
            },
            "feedback": stats,
            "scores": {
                "all_phases": scores_all,
                "by_phase": {
                    "research": scores_research,
                    "fix": scores_fix,
                    "build": scores_build,
                },
            },
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error("[REFLEX API] Stats error: %s", e)
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "enabled": True},
        )


# ─── P5.2: Debug recommendations endpoint ────────────────────────

@router.get("/recommend")
async def reflex_recommend(
    task: str = Query(..., description="Task description to get recommendations for"),
    phase_type: str = Query("research", description="Pipeline phase: research, fix, build"),
    role: str = Query("coder", description="Agent role: coder, researcher, architect, verifier"),
    top_n: int = Query(5, description="Number of recommendations", ge=1, le=20),
) -> Dict[str, Any]:
    """MARKER_172.P5.2 — Debug: get tool recommendations for a task.

    Useful for testing REFLEX scoring without running a pipeline.
    """
    if not _is_reflex_enabled():
        return {
            "enabled": False,
            "message": "REFLEX is disabled. Set REFLEX_ENABLED=1 to activate.",
        }

    try:
        from src.services.reflex_scorer import ReflexContext, get_reflex_scorer
        from src.services.reflex_registry import get_reflex_registry
        from src.services.reflex_feedback import get_reflex_feedback

        t0 = time.time()

        # Build context
        ctx = ReflexContext(
            task_text=task,
            phase_type=phase_type,
            agent_role=role,
        )

        # Load feedback scores
        try:
            ctx.feedback_scores = get_reflex_feedback().get_scores_bulk(phase_type)
        except Exception:
            pass

        scorer = get_reflex_scorer()
        registry = get_reflex_registry()
        tools = registry.get_tools_for_role(role)

        scored = scorer.recommend(ctx, tools, top_n=top_n)
        duration_ms = round((time.time() - t0) * 1000, 1)

        recommendations = []
        for s in scored:
            # Get full signal breakdown
            tool_entry = registry.get_tool(s.tool_id)
            signals = scorer.score_signals(ctx, tool_entry) if tool_entry else {}

            recommendations.append({
                "tool_id": s.tool_id,
                "score": s.score,
                "reason": s.reason,
                "signals": signals,
            })

        return {
            "enabled": True,
            "task": task,
            "phase_type": phase_type,
            "role": role,
            "tools_evaluated": len(tools),
            "recommendations": recommendations,
            "duration_ms": duration_ms,
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error("[REFLEX API] Recommend error: %s", e)
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "enabled": True},
        )


# ─── P5.3 helper: Feedback summary ───────────────────────────────

@router.get("/feedback")
async def reflex_feedback_summary() -> Dict[str, Any]:
    """MARKER_172.P5.FEEDBACK — Raw feedback log statistics."""
    if not _is_reflex_enabled():
        return {"enabled": False}

    try:
        from src.services.reflex_feedback import get_reflex_feedback
        fb = get_reflex_feedback()

        return {
            "enabled": True,
            "entry_count": fb.entry_count,
            "stats": fb.get_stats(),
            "timestamp": time.time(),
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


# ─── Health check ─────────────────────────────────────────────────

@router.get("/health")
async def reflex_health() -> Dict[str, Any]:
    """REFLEX system health check."""
    health = {
        "enabled": _is_reflex_enabled(),
        "components": {},
    }

    # Check registry
    try:
        from src.services.reflex_registry import get_reflex_registry
        reg = get_reflex_registry()
        tools = reg.get_all_tools()
        health["components"]["registry"] = {
            "status": "ok",
            "tools": len(tools),
        }
    except Exception as e:
        health["components"]["registry"] = {"status": "error", "error": str(e)}

    # Check scorer
    try:
        from src.services.reflex_scorer import get_reflex_scorer
        scorer = get_reflex_scorer()
        health["components"]["scorer"] = {
            "status": "ok",
            "weights": scorer.weights if hasattr(scorer, 'weights') else "loaded",
        }
    except Exception as e:
        health["components"]["scorer"] = {"status": "error", "error": str(e)}

    # Check feedback
    try:
        from src.services.reflex_feedback import get_reflex_feedback
        fb = get_reflex_feedback()
        health["components"]["feedback"] = {
            "status": "ok",
            "entries": fb.entry_count,
        }
    except Exception as e:
        health["components"]["feedback"] = {"status": "error", "error": str(e)}

    return health
