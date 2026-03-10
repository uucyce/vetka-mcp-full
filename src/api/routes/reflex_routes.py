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


# ─── P2 Preferences API ──────────────────────────────────────────

@router.get("/preferences")
async def reflex_preferences() -> Dict[str, Any]:
    """MARKER_173.P2.API — Get current user preferences (pins/bans/weights)."""
    if not _is_reflex_enabled():
        return {"enabled": False, "message": "REFLEX is disabled."}

    try:
        from src.services.reflex_preferences import get_reflex_preferences
        store = get_reflex_preferences()
        prefs = store.get()
        return {
            "enabled": True,
            "preferences": prefs.to_dict(),
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error("[REFLEX API] Preferences error: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/pin")
async def reflex_pin(
    tool_id: str = Query(..., description="Tool ID to pin"),
) -> Dict[str, Any]:
    """MARKER_173.P2.PIN — Pin a tool (always include in recommendations)."""
    if not _is_reflex_enabled():
        return {"enabled": False, "message": "REFLEX is disabled."}

    try:
        from src.services.reflex_preferences import get_reflex_preferences
        store = get_reflex_preferences()
        store.pin_tool(tool_id)
        return {
            "enabled": True,
            "action": "pin",
            "tool_id": tool_id,
            "preferences": store.get().to_dict(),
        }
    except Exception as e:
        logger.error("[REFLEX API] Pin error: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/ban")
async def reflex_ban(
    tool_id: str = Query(..., description="Tool ID to ban"),
) -> Dict[str, Any]:
    """MARKER_173.P2.BAN — Ban a tool (always exclude from recommendations)."""
    if not _is_reflex_enabled():
        return {"enabled": False, "message": "REFLEX is disabled."}

    try:
        from src.services.reflex_preferences import get_reflex_preferences
        store = get_reflex_preferences()
        store.ban_tool(tool_id)
        return {
            "enabled": True,
            "action": "ban",
            "tool_id": tool_id,
            "preferences": store.get().to_dict(),
        }
    except Exception as e:
        logger.error("[REFLEX API] Ban error: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.delete("/preferences/{tool_id}")
async def reflex_remove_preference(tool_id: str) -> Dict[str, Any]:
    """MARKER_173.P2.DELETE — Remove all preferences for a specific tool."""
    if not _is_reflex_enabled():
        return {"enabled": False, "message": "REFLEX is disabled."}

    try:
        from src.services.reflex_preferences import get_reflex_preferences
        store = get_reflex_preferences()
        store.remove_preference(tool_id)
        return {
            "enabled": True,
            "action": "remove",
            "tool_id": tool_id,
            "preferences": store.get().to_dict(),
        }
    except Exception as e:
        logger.error("[REFLEX API] Remove preference error: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


# ─── P1 Filter Debug Endpoint ────────────────────────────────────

@router.get("/filter")
async def reflex_filter_debug(
    task: str = Query(..., description="Task description to test filtering"),
    phase_type: str = Query("research", description="Pipeline phase"),
    role: str = Query("coder", description="Agent role"),
    model_tier: str = Query("silver", description="Model tier: bronze, silver, gold"),
) -> Dict[str, Any]:
    """MARKER_173.P1.DEBUG — Debug: see what filter_tools would produce."""
    if not _is_reflex_enabled():
        return {"enabled": False, "message": "REFLEX is disabled."}

    try:
        from src.services.reflex_filter import filter_tools, REFLEX_ACTIVE
        from src.services.reflex_scorer import ReflexContext, get_reflex_scorer
        from src.services.reflex_registry import get_reflex_registry

        t0 = time.time()

        ctx = ReflexContext(
            task_text=task,
            phase_type=phase_type,
            agent_role=role,
        )

        # Load feedback scores
        try:
            from src.services.reflex_feedback import get_reflex_feedback
            ctx.feedback_scores = get_reflex_feedback().get_scores_bulk(phase_type)
        except Exception:
            pass

        registry = get_reflex_registry()
        all_tools = registry.get_tools_for_role(role)
        filtered = filter_tools(all_tools, context=ctx, model_tier=model_tier)

        duration_ms = round((time.time() - t0) * 1000, 1)

        return {
            "enabled": True,
            "active": REFLEX_ACTIVE,
            "task": task,
            "model_tier": model_tier,
            "total_tools": len(all_tools),
            "filtered_tools": len(filtered),
            "tools": [
                {"tool_id": getattr(t, "tool_id", str(t)),
                 "kind": getattr(t, "kind", "unknown")}
                for t in filtered
            ],
            "duration_ms": duration_ms,
        }

    except Exception as e:
        logger.error("[REFLEX API] Filter debug error: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


# ─── P3 Streaming API ──────────────────────────────────────────────

@router.get("/events")
async def reflex_events(
    n: int = Query(20, description="Number of recent events", ge=1, le=100),
    since: float = Query(0, description="Events after this Unix timestamp"),
    pipeline_id: str = Query("", description="Filter by pipeline/task ID"),
) -> Dict[str, Any]:
    """MARKER_173.P3.EVENTS — Get recent REFLEX streaming events.

    Supports three query modes:
    - Default: last N events
    - since=<ts>: events newer than timestamp (for polling)
    - pipeline_id=<id>: events for specific pipeline run
    """
    if not _is_reflex_enabled():
        return {"enabled": False, "message": "REFLEX is disabled."}

    try:
        from src.services.reflex_streaming import get_reflex_event_buffer

        buf = get_reflex_event_buffer()

        if pipeline_id:
            events = buf.get_by_pipeline(pipeline_id)
        elif since > 0:
            events = buf.get_since(since)
        else:
            events = buf.get_recent(n)

        return {
            "enabled": True,
            "events": events,
            "count": len(events),
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error("[REFLEX API] Events error: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/events/stats")
async def reflex_event_stats() -> Dict[str, Any]:
    """MARKER_173.P3.STATS — Get REFLEX event buffer statistics."""
    if not _is_reflex_enabled():
        return {"enabled": False, "message": "REFLEX is disabled."}

    try:
        from src.services.reflex_streaming import get_reflex_event_buffer

        buf = get_reflex_event_buffer()
        stats = buf.get_stats()

        return {
            "enabled": True,
            "buffer": stats,
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error("[REFLEX API] Event stats error: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


# ─── P4 Experiment API ─────────────────────────────────────────────

@router.get("/experiment")
async def reflex_experiment() -> Dict[str, Any]:
    """MARKER_173.P4.API — Get A/B experiment comparison results."""
    if not _is_reflex_enabled():
        return {"enabled": False, "message": "REFLEX is disabled."}

    try:
        from src.services.reflex_experiment import get_reflex_experiment, REFLEX_EXPERIMENT

        store = get_reflex_experiment()
        comparison = store.get_comparison()

        return {
            "enabled": True,
            "experiment_active": REFLEX_EXPERIMENT,
            "config": store.get_config().to_dict(),
            "comparison": comparison,
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error("[REFLEX API] Experiment error: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/experiment/metrics")
async def reflex_experiment_metrics(
    arm: str = Query("", description="Filter by arm: control or treatment"),
) -> Dict[str, Any]:
    """MARKER_173.P4.METRICS — Get raw experiment metrics."""
    if not _is_reflex_enabled():
        return {"enabled": False, "message": "REFLEX is disabled."}

    try:
        from src.services.reflex_experiment import get_reflex_experiment

        store = get_reflex_experiment()
        if arm:
            metrics = store.get_arm_metrics(arm)
        else:
            metrics = store.get_all_metrics()

        return {
            "enabled": True,
            "arm_filter": arm or "all",
            "metrics": metrics,
            "count": len(metrics),
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error("[REFLEX API] Experiment metrics error: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


# ─── P5 Decay & Model Profiles API ───────────────────────────────

@router.get("/decay")
async def reflex_decay_info(
    phase_type: str = Query("*", description="Phase type for decay preview"),
    success_rate: float = Query(-1.0, description="Tool success rate (-1 = none)"),
    age_days: float = Query(0.0, description="Age in days for weight preview"),
) -> Dict[str, Any]:
    """MARKER_173.P5.API — Decay configuration and weight preview.

    Shows phase-specific half-lives, success-weighted adjustments,
    and optional weight calculation for a specific age/phase/success combo.
    """
    if not _is_reflex_enabled():
        return {"enabled": False, "message": "REFLEX is disabled."}

    try:
        from src.services.reflex_decay import (
            ReflexDecayEngine, get_decay_summary, get_all_model_profiles,
        )

        summary = get_decay_summary()

        # Optional: compute specific weight
        preview = None
        if age_days > 0:
            engine = ReflexDecayEngine()
            sr = success_rate if success_rate >= 0 else None
            weight = engine.compute_weight(age_days, phase_type, sr)
            half_life = engine.get_half_life(phase_type, sr)
            preview = {
                "age_days": age_days,
                "phase_type": phase_type,
                "success_rate": sr,
                "half_life_days": half_life,
                "weight": round(weight, 6),
            }

        return {
            "enabled": True,
            "decay": summary,
            "preview": preview,
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error("[REFLEX API] Decay error: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/models")
async def reflex_model_profiles(
    model: str = Query("", description="Specific model name (empty = all)"),
) -> Dict[str, Any]:
    """MARKER_173.P5.MODELS — Model-specific scoring profiles.

    Returns FC reliability, max tools, and preference settings per model.
    """
    if not _is_reflex_enabled():
        return {"enabled": False, "message": "REFLEX is disabled."}

    try:
        from src.services.reflex_decay import (
            get_model_profile, get_all_model_profiles,
        )

        if model:
            profile = get_model_profile(model)
            return {
                "enabled": True,
                "model": model,
                "profile": profile.to_dict(),
                "timestamp": time.time(),
            }
        else:
            return {
                "enabled": True,
                "profiles": get_all_model_profiles(),
                "count": len(get_all_model_profiles()),
                "timestamp": time.time(),
            }

    except Exception as e:
        logger.error("[REFLEX API] Model profiles error: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})
