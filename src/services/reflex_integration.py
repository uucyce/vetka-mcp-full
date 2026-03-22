"""
REFLEX Integration — Thin hooks for injection into pipeline & session.

MARKER_172.P4.INTEGRATION + MARKER_173.P1.IP7

Provides safe, feature-flag-guarded entry points that pipeline code calls.
Each function: check flag → build context → call scorer/feedback → return.
On ANY error: log warning, return empty/None. Never break the pipeline.

Injection Points:
  IP-1: reflex_pre_fc()          — before FC loop, log tool recommendations
  IP-3: reflex_post_fc()         — after FC loop, record feedback for used tools
  IP-4: reflex_for_role()        — before role execution, get recommendations
  IP-5: reflex_verifier()        — after verifier, close feedback loop
  IP-6: reflex_session()         — for session_init, broad recommendations
  IP-7: reflex_filter_schemas()  — active schema filtering before FC loop

Part of VETKA OS:
  VETKA > REFLEX > Integration (this file)

@status: active
@phase: 173.P1+P2
@depends: reflex_scorer, reflex_feedback, reflex_registry, reflex_filter, reflex_preferences
@used_by: fc_loop.py (IP-1,3), agent_pipeline.py (IP-4,5,7), session_tools.py (IP-6)
"""

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _is_enabled() -> bool:
    """Check REFLEX feature flag. Imported lazily to respect runtime env changes."""
    try:
        from src.services.reflex_scorer import REFLEX_ENABLED
        return REFLEX_ENABLED
    except ImportError:
        return False


def _is_active() -> bool:
    """MARKER_173.P1.FLAG — Check if REFLEX active filtering is enabled.

    Requires BOTH REFLEX_ENABLED and REFLEX_ACTIVE to be True.
    """
    if not _is_enabled():
        return False
    try:
        from src.services.reflex_filter import REFLEX_ACTIVE
        return REFLEX_ACTIVE
    except ImportError:
        return False


def _apply_preferences(scored: list) -> list:
    """MARKER_173.P2.HELPER — Apply user preferences to scored recommendations.

    Pinned tools get score=1.0, banned tools are excluded.
    Returns modified scored list, re-sorted by score.
    """
    try:
        from src.services.reflex_preferences import get_reflex_preferences
        prefs = get_reflex_preferences().get()
        if not prefs.pinned_tools and not prefs.banned_tools:
            return scored

        # Exclude banned tools
        scored = [s for s in scored if s.tool_id not in prefs.banned_tools]

        # Boost pinned tools
        for s in scored:
            if s.tool_id in prefs.pinned_tools:
                s.score = 1.0
                s.reason = f"pinned, {s.reason}"

        # Re-sort
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored

    except Exception:
        return scored  # Preferences errors never block


# ─── IP-1: Pre-FC Loop (recommendations before coder runs) ──────

def reflex_pre_fc(
    subtask: Any,
    phase_type: str = "research",
    agent_role: str = "coder",
    model_context_length: int = 128000,
    model_output_tps: float = 50.0,
) -> List[Dict]:
    """MARKER_172.P4.IP1 — Get REFLEX recommendations before FC loop.

    Called by agent_pipeline before execute_fc_loop(). Returns tool
    recommendations for logging/context injection. Does NOT filter
    tool_schemas (yet — that's a future optimization).

    Returns:
        List of {tool_id, score, reason} dicts. Empty if disabled or error.
    """
    if not _is_enabled():
        return []

    try:
        from src.services.reflex_scorer import ReflexContext, get_reflex_scorer
        from src.services.reflex_registry import get_reflex_registry

        ctx = ReflexContext.from_subtask(
            subtask,
            model_context_length=model_context_length,
            model_output_tps=model_output_tps,
        )
        ctx.phase_type = phase_type
        ctx.agent_role = agent_role

        # Load feedback scores if available
        try:
            from src.services.reflex_feedback import get_reflex_feedback
            ctx.feedback_scores = get_reflex_feedback().get_scores_bulk(phase_type)
        except Exception:
            pass

        scorer = get_reflex_scorer()
        registry = get_reflex_registry()
        tools = registry.get_tools_for_role(agent_role)

        scored = scorer.recommend(ctx, tools, top_n=5)

        # MARKER_173.P2.IP1_UPDATE: Apply user preferences (pin/ban)
        scored = _apply_preferences(scored)

        result = [
            {"tool_id": s.tool_id, "score": s.score, "reason": s.reason}
            for s in scored
        ]

        if result:
            top_ids = ", ".join(r["tool_id"] for r in result[:3])
            logger.info("[REFLEX IP-1] Recommendations for %s/%s: %s",
                        phase_type, agent_role, top_ids)

        return result

    except Exception as e:
        logger.debug("[REFLEX IP-1] Error (non-fatal): %s", e)
        return []


# ─── IP-3: Post-FC Loop (record feedback for used tools) ────────

def reflex_post_fc(
    tool_executions: List[Dict],
    phase_type: str = "research",
    agent_role: str = "coder",
    subtask_id: str = "",
) -> int:
    """MARKER_172.P4.IP3 — Record feedback after FC loop execution.

    Called by agent_pipeline after execute_fc_loop() returns.
    Records each tool execution result to the feedback log.

    Args:
        tool_executions: List of {name, args, result} from FC loop
        phase_type: Current pipeline phase
        agent_role: Which agent ran
        subtask_id: Pipeline subtask identifier

    Returns:
        Number of feedback entries recorded.
    """
    if not _is_enabled():
        return 0

    try:
        from src.services.reflex_feedback import get_reflex_feedback
        fb = get_reflex_feedback()

        count = 0
        for te in tool_executions:
            tool_name = te.get("name", "")
            result = te.get("result", {})
            success = result.get("success", False)
            # Usefulness heuristic: has non-empty result content
            useful = success and bool(result.get("result"))

            fb.record(
                tool_id=tool_name,
                success=success,
                useful=useful,
                phase_type=phase_type,
                agent_role=agent_role,
                subtask_id=subtask_id,
            )
            count += 1

        if count > 0:
            logger.debug("[REFLEX IP-3] Recorded %d tool feedbacks for %s", count, subtask_id)
        return count

    except Exception as e:
        logger.debug("[REFLEX IP-3] Error (non-fatal): %s", e)
        return 0


# ─── IP-5: Verifier feedback (close the loop) ───────────────────

def reflex_verifier(
    subtask_id: str,
    tools_used: List[str],
    verifier_passed: bool,
    phase_type: str = "research",
    agent_role: str = "coder",
    # MARKER_182.REFLEX: Enhanced params for run/session tracking
    run_id: Optional[str] = None,
    session_id: Optional[str] = None,
    verifier_confidence: float = 0.0,
) -> int:
    """MARKER_172.P4.IP5 — Close feedback loop after verification.

    Called by agent_pipeline after verifier returns.
    Links verifier outcome to all tools used in the subtask.

    MARKER_182.REFLEX: Enhanced with run_id/session_id tracking.
    When ActionRegistry is available, also logs tool→action mappings.

    Returns:
        Number of feedback entries recorded.
    """
    if not _is_enabled():
        return 0

    try:
        from src.services.reflex_feedback import get_reflex_feedback
        fb = get_reflex_feedback()

        count = fb.record_outcome(
            subtask_id=subtask_id,
            tools_used=tools_used,
            verifier_passed=verifier_passed,
            phase_type=phase_type,
            agent_role=agent_role,
        )

        if count > 0:
            status = "PASS" if verifier_passed else "FAIL"
            logger.info("[REFLEX IP-5] Verifier %s → %d tools feedback for %s (run=%s, conf=%.2f)",
                        status, count, subtask_id, run_id or "?", verifier_confidence)

        # MARKER_182.REFLEX: Log to ActionRegistry if run_id provided
        if run_id:
            try:
                from src.orchestration.action_registry import ActionRegistry
                registry = ActionRegistry()
                registry.log_action(
                    run_id=run_id,
                    agent="reflex",
                    action="feedback",
                    file=f"IP-5/{subtask_id}",
                    result="success" if verifier_passed else "failed",
                    session_id=session_id,
                    metadata={
                        "tools_used": tools_used[:20],
                        "verifier_confidence": verifier_confidence,
                        "feedback_count": count,
                    },
                )
            except Exception:
                pass  # Non-fatal

        return count

    except Exception as e:
        logger.debug("[REFLEX IP-5] Error (non-fatal): %s", e)
        return 0


# ─── IP-4: Pipeline role recommendations ────────────────────────

def reflex_for_role(
    role: str,
    subtask: Any = None,
    phase_type: str = "research",
    model_context_length: int = 128000,
) -> List[Dict]:
    """MARKER_172.P4.IP4 — Get recommendations for a pipeline role.

    Called before each role execution (architect, researcher, coder, verifier).
    Stores result in subtask.context["reflex_tools"] if subtask provided.

    Returns:
        List of {tool_id, score} dicts.
    """
    if not _is_enabled():
        return []

    try:
        from src.services.reflex_scorer import ReflexContext, get_reflex_scorer
        from src.services.reflex_registry import get_reflex_registry

        ctx = ReflexContext(
            task_text=getattr(subtask, "description", "") if subtask else "",
            phase_type=phase_type,
            agent_role=role,
            model_context_length=model_context_length,
        )

        scorer = get_reflex_scorer()
        registry = get_reflex_registry()
        tools = registry.get_tools_for_role(role)
        scored = scorer.recommend(ctx, tools, top_n=5)

        result = [{"tool_id": s.tool_id, "score": s.score} for s in scored]

        # Store in subtask context if available
        if subtask and hasattr(subtask, "context") and isinstance(getattr(subtask, "context", None), dict):
            subtask.context["reflex_tools"] = [r["tool_id"] for r in result]

        return result

    except Exception as e:
        logger.debug("[REFLEX IP-4] Error (non-fatal): %s", e)
        return []


# ─── IP-6: Session Init recommendations ─────────────────────────

def reflex_session(
    session_data: Dict[str, Any],
    phase_type: str = "research",
    agent_type: str = "",
    current_task: Optional[Dict[str, Any]] = None,
) -> List[Dict]:
    """MARKER_172.P4.IP6 + MARKER_186.3 + MARKER_191.3 + MARKER_193.2 — Get task-aware recommendations for session_init.

    Called by session_tools._execute_async() to include tool recommendations
    in the session init response.

    MARKER_186.3: Now accepts agent_type for agent-aware scoring.
    MARKER_191.3: Now accepts current_task for task-aware semantic matching.
    MARKER_193.2: Guard filtering — blocked/warned tools annotated before return.

    Returns:
        List of {tool_id, score, reason} dicts (blocked tools excluded).
    """
    if not _is_enabled():
        return []

    try:
        from src.services.reflex_scorer import get_reflex_scorer
        scorer = get_reflex_scorer()
        scored = scorer.recommend_for_session(
            session_data,
            phase_type=phase_type,
            top_n=10,
            agent_type=agent_type,
            current_task=current_task,
        )

        # MARKER_173.P2.IP6_UPDATE: Apply user preferences (pin/ban)
        scored = _apply_preferences(scored)

        recs = [
            {"tool_id": s.tool_id, "score": s.score, "reason": s.reason}
            for s in scored
        ]

        # MARKER_193.2: Apply guard filtering — block/warn/demote dangerous tools
        try:
            from src.services.reflex_guard import get_feedback_guard, GuardContext
            guard = get_feedback_guard()
            ctx = GuardContext(
                agent_type=agent_type,
                phase_type=phase_type,
                project_id=session_data.get("project_id", ""),
            )
            recs = guard.filter_recommendations(recs, ctx)
        except Exception as e:
            logger.debug("[REFLEX IP-6] Guard filtering failed (non-fatal): %s", e)

        # MARKER_196.1: D2 → D3 wiring — populate EmotionContext.tool_freshness from ToolSourceWatch
        # MARKER_196.2: D1 → D3 wiring — populate EmotionContext.guard_warnings from ProtocolGuard
        try:
            from src.services.reflex_emotions import get_reflex_emotions, EmotionContext
            emo_engine = get_reflex_emotions()

            # --- 196.1: Freshness → Curiosity ---
            tool_freshness: Dict[str, float] = {}
            try:
                from src.services.tool_source_watch import get_tool_source_watch, FRESHNESS_WINDOW_HOURS
                watch = get_tool_source_watch()
                all_freshness = watch.get_all()
                for tid, entry in all_freshness.items():
                    if entry.is_recently_updated():
                        hours = entry.hours_since_update()
                        # Linear decay: 1.0 at update, 0.0 at 48h
                        score = max(0.0, 1.0 - hours / FRESHNESS_WINDOW_HOURS)
                        tool_freshness[tid] = round(score, 4)
                if tool_freshness:
                    logger.debug("[REFLEX IP-6] 196.1: %d fresh tools populated", len(tool_freshness))
            except Exception as e:
                logger.debug("[REFLEX IP-6] 196.1 freshness wiring failed (non-fatal): %s", e)

            # --- 196.2: Guard → Caution ---
            guard_warnings_list: list = []
            try:
                from src.services.protocol_guard import get_protocol_guard as _get_pg
                from src.services.session_tracker import get_session_tracker as _get_st
                _tracker = _get_st()
                _guard = _get_pg()
                _sid = session_data.get("session_id", "reflex_default")
                _session = _tracker.get_session(_sid)
                _pending = _guard.check_all_pending(_session)
                for v in _pending:
                    guard_warnings_list.append(v.rule_id)
                if guard_warnings_list:
                    logger.debug("[REFLEX IP-6] 196.2: %d guard warnings populated", len(guard_warnings_list))
            except Exception as e:
                logger.debug("[REFLEX IP-6] 196.2 guard wiring failed (non-fatal): %s", e)

            # Build a shared EmotionContext with wired data for session-level emotion compute
            emo_ctx = EmotionContext(
                agent_id=agent_type,
                phase_type=phase_type,
                tool_freshness=tool_freshness,
                guard_warnings=guard_warnings_list,
            )

            # Recompute emotions for each recommended tool with wired context
            for rec in recs:
                tid = rec.get("tool_id", "")
                if not tid or tid == "protocol_guard":
                    continue
                try:
                    # Set per-tool freshness_score from the tool_freshness dict
                    emo_ctx.freshness_score = tool_freshness.get(tid, 0.0)
                    state = emo_engine.compute_emotions(tid, emo_ctx)
                    rec["emotions"] = {
                        "curiosity": round(state.curiosity, 4),
                        "trust": round(state.trust, 4),
                        "caution": round(state.caution, 4),
                        "mood": state.mood_label,
                    }
                except Exception:
                    pass
        except Exception as e:
            logger.debug("[REFLEX IP-6] 196.1/196.2 emotion wiring failed (non-fatal): %s", e)

        # MARKER_195.7: Protocol violations as REFLEX warnings
        try:
            from src.services.protocol_guard import get_protocol_guard
            from src.services.session_tracker import get_session_tracker
            _pg_tracker = get_session_tracker()
            _pg_guard = get_protocol_guard()
            _pg_sid = session_data.get("session_id", "reflex_default")
            _pg_session = _pg_tracker.get_session(_pg_sid)
            _pg_pending = _pg_guard.check_all_pending(_pg_session)
            for _pg_v in _pg_pending:
                recs.append({
                    "tool_id": "protocol_guard",
                    "score": 0.0,
                    "reason": _pg_v.message,
                    "severity": _pg_v.severity,
                    "source": f"protocol:{_pg_v.rule_id}",
                    "warning": f"PROTOCOL: {_pg_v.message} → {_pg_v.suggestion}",
                })
        except Exception as e:
            logger.debug("[REFLEX IP-6] Protocol bridge failed (non-fatal): %s", e)

        return recs

    except Exception as e:
        logger.debug("[REFLEX IP-6] Error (non-fatal): %s", e)
        return []


# ─── IP-7: Active Tool Schema Filtering ──────────────────────────

def reflex_filter_schemas(
    tool_schemas: List[Dict],
    subtask: Any = None,
    phase_type: str = "research",
    agent_role: str = "coder",
    model_tier: str = "silver",
) -> List[Dict]:
    """MARKER_173.P1.IP7 — Filter tool_schemas before FC loop.

    Only active when BOTH REFLEX_ENABLED=1 AND REFLEX_ACTIVE=1.
    On error: returns original schemas unchanged (safe fallback).

    Args:
        tool_schemas: OpenAI-format tool schemas for FC loop
        subtask: Current pipeline subtask (for context building)
        phase_type: Current pipeline phase
        agent_role: Agent role executing
        model_tier: bronze/silver/gold (from preset)

    Returns:
        Filtered list of tool schemas. Same as input if filtering disabled.
    """
    if not _is_active():
        return tool_schemas

    try:
        from src.services.reflex_filter import filter_tool_schemas
        from src.services.reflex_scorer import ReflexContext

        # Build context for scoring
        if subtask is not None:
            ctx = ReflexContext.from_subtask(subtask)
        else:
            ctx = ReflexContext(
                task_text="",
                phase_type=phase_type,
                agent_role=agent_role,
            )
        ctx.phase_type = phase_type
        ctx.agent_role = agent_role

        # Load feedback scores for better filtering
        try:
            from src.services.reflex_feedback import get_reflex_feedback
            ctx.feedback_scores = get_reflex_feedback().get_scores_bulk(phase_type)
        except Exception:
            pass

        filtered = filter_tool_schemas(tool_schemas, context=ctx, model_tier=model_tier)

        if len(filtered) < len(tool_schemas):
            logger.info("[REFLEX IP-7] Filtered schemas: %d → %d (tier=%s)",
                        len(tool_schemas), len(filtered), model_tier)

        return filtered

    except Exception as e:
        logger.debug("[REFLEX IP-7] Error (non-fatal): %s", e)
        return tool_schemas  # Safety: return original on error
