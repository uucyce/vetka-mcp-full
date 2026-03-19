"""
VETKA Failure Feedback Loop — Memory integration for pipeline failures.

Connects pipeline failures to cognitive memory subsystems:
- STM: Boost weight so agent remembers failures vividly
- CAM: Inject surprise event for unexpected failures
- CORTEX: Record tool-level failure for REFLEX scoring
- ENGRAM L1: Rehearse related entries on recovery

Single entry point: record_failure_feedback() — call once per task failure.

@file failure_feedback.py
@status active
@phase 187.12 MARKER_187.12
@depends stm_buffer.py, cam_event_handler.py, reflex/feedback.py, engram_cache.py
@used_by task_board.py, agent_pipeline.py
"""

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Max 1 feedback loop per task per attempt (anti-spam)
_recent_failures: Dict[str, float] = {}
_COOLDOWN_SECONDS = 60


def record_failure_feedback(
    task_id: str,
    error_summary: str,
    *,
    failed_tools: Optional[List[str]] = None,
    tier_used: str = "",
    phase_type: str = "build",
    attempt: int = 1,
    severity: str = "major",
    subtask_context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Single entry point for pipeline failure → memory feedback.

    Call this once per task failure. It fans out to STM, CAM, CORTEX, ENGRAM.
    Anti-spam: max 1 call per task per 60 seconds.

    Args:
        task_id: Failed task ID
        error_summary: Human-readable failure description
        failed_tools: List of tool_ids that failed (for CORTEX)
        tier_used: Model tier that failed (bronze/silver/gold)
        phase_type: Task phase type (build/fix/research/test)
        attempt: Attempt number
        severity: critical/major/minor
        subtask_context: Additional context about what was being done

    Returns:
        Dict with results from each subsystem
    """
    # Anti-spam guard
    cooldown_key = f"{task_id}:{attempt}"
    now = time.time()
    if cooldown_key in _recent_failures:
        elapsed = now - _recent_failures[cooldown_key]
        if elapsed < _COOLDOWN_SECONDS:
            logger.debug(f"[FailureFeedback] Cooldown active for {cooldown_key}, skipping")
            return {"skipped": True, "reason": "cooldown"}
    _recent_failures[cooldown_key] = now

    results: Dict[str, Any] = {"task_id": task_id, "attempt": attempt}

    # 1. STM — Remember failure vividly (boosted weight)
    results["stm"] = _feed_stm(task_id, error_summary, severity, tier_used, subtask_context)

    # 2. CORTEX — Record tool-level failures for REFLEX scoring
    results["cortex"] = _feed_cortex(failed_tools or [], phase_type, task_id)

    # MARKER_193.5: Auto-promote to ENGRAM danger if threshold crossed
    results["auto_promote"] = _maybe_promote_to_danger(failed_tools or [], phase_type)

    # 3. ENGRAM L1 — Check for pair warnings
    results["engram"] = _check_engram_warnings(failed_tools or [])

    logger.info(
        f"[FailureFeedback] Task {task_id} attempt #{attempt}: "
        f"STM={results['stm'].get('status', 'skip')}, "
        f"CORTEX={results['cortex'].get('recorded', 0)} tools, "
        f"ENGRAM={results['engram'].get('warnings', 0)} warnings, "
        f"promoted={results['auto_promote'].get('promoted', 0)}"
    )

    return results


def record_recovery_feedback(
    task_id: str,
    recovered_context: str,
) -> Dict[str, Any]:
    """
    Called when a task succeeds after previous failure(s).

    Reinforces the failure memory via STM rehearsal so the agent
    remembers what went wrong and how it was fixed.
    """
    results: Dict[str, Any] = {"task_id": task_id}

    try:
        from src.memory.stm_buffer import get_stm_buffer
        stm = get_stm_buffer()
        # Rehearse failure entries to keep them fresh
        rehearsed = stm.rehearse(f"[FAILURE] Task {task_id}")
        results["rehearsed"] = rehearsed
        if rehearsed:
            logger.info(f"[FailureFeedback] Recovery rehearsal for {task_id}")
    except Exception as e:
        results["rehearsal_error"] = str(e)

    return results


# ============ Internal feeders ============


def _feed_stm(
    task_id: str, error_summary: str, severity: str,
    tier_used: str, subtask_context: Optional[str],
) -> Dict[str, Any]:
    """Add failure to STM with boosted weight."""
    try:
        from src.memory.stm_buffer import get_stm_buffer, STMEntry
        from datetime import datetime

        weight_boost = {"critical": 2.0, "major": 1.5, "minor": 1.2}.get(severity, 1.5)
        surprise = {"critical": 0.9, "major": 0.7, "minor": 0.4}.get(severity, 0.7)

        content = f"[FAILURE] Task {task_id}: {error_summary}"
        if subtask_context:
            content += f" | Context: {subtask_context}"

        entry = STMEntry(
            content=content[:500],
            timestamp=datetime.now(),
            source="pipeline_failure",
            weight=weight_boost,
            surprise_score=surprise,
            metadata={
                "task_id": task_id,
                "tier_used": tier_used,
                "severity": severity,
            },
        )

        stm = get_stm_buffer()
        stm.add(entry)
        return {"status": "ok", "weight": weight_boost, "surprise": surprise}
    except Exception as e:
        logger.debug(f"[FailureFeedback] STM feed failed: {e}")
        return {"status": "error", "error": str(e)}


def _feed_cortex(
    failed_tools: List[str], phase_type: str, task_id: str,
) -> Dict[str, Any]:
    """Record tool-level failures in CORTEX (REFLEX feedback)."""
    try:
        from src.reflex.feedback import get_reflex_feedback

        feedback = get_reflex_feedback()
        recorded = 0
        for tool_id in failed_tools:
            feedback.record(
                tool_id=tool_id,
                success=False,
                useful=False,
                phase_type=phase_type,
                subtask_id=task_id,
            )
            recorded += 1
        return {"recorded": recorded}
    except Exception as e:
        logger.debug(f"[FailureFeedback] CORTEX feed failed: {e}")
        return {"recorded": 0, "error": str(e)}


# MARKER_193.5: Thresholds for auto-promotion to ENGRAM danger
_PROMOTE_MIN_FAILURES = 3
_PROMOTE_MAX_SUCCESS_RATE = 0.2


def _maybe_promote_to_danger(
    failed_tools: List[str], phase_type: str,
) -> Dict[str, Any]:
    """MARKER_193.5: Auto-promote tools to ENGRAM L1 danger if failure threshold crossed.

    After CORTEX records failures, check if any tool crossed the threshold:
    - >= 3 total calls AND success_rate < 20%
    - No existing ENGRAM danger entry for this tool (avoid duplicates)

    Creates self-healing loop: fails → record → promote → guard blocks → agent learns.
    """
    promoted = 0
    checked = 0
    try:
        from src.reflex.feedback import get_reflex_feedback
        from src.memory.engram_cache import get_engram_cache

        fb = get_reflex_feedback()
        cache = get_engram_cache()
        summary = fb.get_feedback_summary()
        per_tool = summary.get("per_tool", {})

        for tool_id in failed_tools:
            stats = per_tool.get(tool_id)
            if not stats:
                continue
            checked += 1

            count = stats.get("count", 0)
            success_rate = stats.get("success_rate", 1.0)

            if count < _PROMOTE_MIN_FAILURES or success_rate >= _PROMOTE_MAX_SUCCESS_RATE:
                continue

            # Check for existing danger entry (avoid duplicates)
            existing = cache.get_all()
            already_danger = any(
                e.get("category") == "danger" and e.get("key") == tool_id
                for e in existing.values()
            )
            if already_danger:
                logger.debug(f"[FailureFeedback] {tool_id} already has ENGRAM danger entry, skipping")
                continue

            # Promote: create ENGRAM L1 danger entry
            reason = f"Auto-promoted: {success_rate:.0%} success over {count} calls"
            cache.put(
                key=tool_id,
                value=f"{reason} | {phase_type}",
                category="danger",
            )
            promoted += 1
            logger.info(
                f"[FailureFeedback] Auto-promoted {tool_id} to ENGRAM danger "
                f"({count} calls, {success_rate:.0%} success)"
            )

    except Exception as e:
        logger.debug(f"[FailureFeedback] Auto-promote check failed: {e}")
        return {"promoted": 0, "checked": checked, "error": str(e)}

    return {"promoted": promoted, "checked": checked}


def _check_engram_warnings(failed_tools: List[str]) -> Dict[str, Any]:
    """Check ENGRAM L1 for pair warnings on failed files."""
    try:
        from src.memory.engram_cache import get_engram_cache

        cache = get_engram_cache()
        warnings = []
        for tool_id in failed_tools:
            pair_warnings = cache.find_pair_warnings(tool_id)
            for w in pair_warnings:
                warnings.append({"key": w.key, "value": w.value})
        return {"warnings": len(warnings), "details": warnings[:5]}
    except Exception as e:
        logger.debug(f"[FailureFeedback] ENGRAM check failed: {e}")
        return {"warnings": 0, "error": str(e)}
