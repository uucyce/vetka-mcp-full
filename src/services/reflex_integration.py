"""
REFLEX Integration — Thin hooks for injection into pipeline & session.

MARKER_172.P4.INTEGRATION

Provides safe, feature-flag-guarded entry points that pipeline code calls.
Each function: check flag → build context → call scorer/feedback → return.
On ANY error: log warning, return empty/None. Never break the pipeline.

Injection Points:
  IP-1: reflex_pre_fc()    — before FC loop, log tool recommendations
  IP-3: reflex_post_fc()   — after FC loop, record feedback for used tools
  IP-4: reflex_for_role()  — before role execution, get recommendations
  IP-5: reflex_verifier()  — after verifier, close feedback loop
  IP-6: reflex_session()   — for session_init, broad recommendations

Part of VETKA OS:
  VETKA > REFLEX > Integration (this file)

@status: active
@phase: 172.P4
@depends: reflex_scorer, reflex_feedback, reflex_registry
@used_by: fc_loop.py (IP-1,3), agent_pipeline.py (IP-4,5), session_tools.py (IP-6)
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
) -> int:
    """MARKER_172.P4.IP5 — Close feedback loop after verification.

    Called by agent_pipeline after verifier returns.
    Links verifier outcome to all tools used in the subtask.

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
            logger.info("[REFLEX IP-5] Verifier %s → %d tools feedback for %s",
                        status, count, subtask_id)
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

def reflex_session(session_data: Dict[str, Any], phase_type: str = "research") -> List[Dict]:
    """MARKER_172.P4.IP6 — Get broad recommendations for session_init.

    Called by session_tools._execute_async() to include tool recommendations
    in the session init response.

    Returns:
        List of {tool_id, score, reason} dicts.
    """
    if not _is_enabled():
        return []

    try:
        from src.services.reflex_scorer import get_reflex_scorer
        scorer = get_reflex_scorer()
        scored = scorer.recommend_for_session(session_data, phase_type=phase_type, top_n=10)
        return [
            {"tool_id": s.tool_id, "score": s.score, "reason": s.reason}
            for s in scored
        ]

    except Exception as e:
        logger.debug("[REFLEX IP-6] Error (non-fatal): %s", e)
        return []
