"""
MARKER_ZETA.F2: Smart Debrief — auto-task creation + memory routing from experience reports.

When agent submits experience report:
- lessons_learned (Q1 bugs) → auto-create [DEBRIEF-BUG] research tasks
- recommendations (Q3 ideas) → auto-create [DEBRIEF-IDEA] research tasks
- All answers → route to memory subsystems via regex triggers

Usage:
    from src.services.smart_debrief import process_smart_debrief
    process_smart_debrief(report)  # call after ExperienceReportStore.submit()
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ── Bug detection patterns ──────────────────────────────────

_BUG_PATTERNS = re.compile(
    r"сломан|broken|bug|баг|ошибк|error|fail|crash|не работает|doesn.t work|"
    r"workaround|хак|hack|костыл|kludge|мусор|garbage|stale|устарев|"
    r"неправильн|incorrect|wrong|кривой|should not|shouldn.t|"
    r"always returns|всегда возвращает|pollut|загрязн",
    re.IGNORECASE,
)

# ── Memory routing patterns (regex "mousetraps") ───────────

_TOOL_PATTERN = re.compile(
    r"\bvetka_\w+\b|\bRead\b|\bEdit\b|\bGrep\b|\bGlob\b|\bBash\b|\bWrite\b|"
    r"\bsession_init\b|\btask_board\b",
)

_USER_PATTERN = re.compile(
    r"\buser\b|\bпользовател\w*\b|\bюзер\w*\b|\bUI\b|\bUX\b",
    re.IGNORECASE,
)

_FILE_PATTERN = re.compile(
    r"[\w./]+\.(?:py|ts|tsx|js|jsx|yaml|json|md|css|html)\b",
)

_LEARNING_PATTERN = re.compile(
    r"\bпаттерн\w*\b|\bpattern\b|\bпринцип\w*\b|\bprinciple\b|"
    r"\balways\b|\bnever\b|\bлучше\b|\bхуже\b|\bэффективн\w*\b|"
    r"\bстандарт\w*\b|\bstandard\b|\brule\b|\bправил\w*\b|"
    r"\bрекоменд\w*\b|\brecommend\w*\b",
    re.IGNORECASE,
)


def _extract_summary(text: str, max_len: int = 60) -> str:
    """Extract first meaningful line as summary, truncated."""
    line = text.strip().split("\n")[0].strip()
    # Remove Q1:/Q2:/Q3: prefixes
    line = re.sub(r"^Q[123]:\s*", "", line)
    # Remove leading numbering
    line = re.sub(r"^\d+\.\s*", "", line)
    if len(line) > max_len:
        return line[:max_len - 3] + "..."
    return line


def _is_bug_report(text: str) -> bool:
    """Check if text describes a bug/problem."""
    return bool(_BUG_PATTERNS.search(text))


def _create_auto_tasks(report, task_board) -> list[str]:
    """Create research tasks from debrief answers. Returns list of created task IDs."""
    created = []

    # Q1: bugs from lessons_learned
    for lesson in report.lessons_learned:
        if _is_bug_report(lesson):
            try:
                task_id = task_board.add_task(
                    title=f"[DEBRIEF-BUG] {_extract_summary(lesson)}",
                    description=(
                        f"Обнаружено агентом {report.agent_callsign or 'unknown'} "
                        f"({report.domain or 'cross-cutting'}).\n\n{lesson}"
                    ),
                    phase_type="research",
                    priority=3,
                    tags=["debrief-auto", "architect-review"],
                    source="smart_debrief",
                )
                created.append(task_id)
                logger.info("[SmartDebrief] Created bug task: %s", task_id)
            except Exception as e:
                logger.debug("[SmartDebrief] Failed to create bug task: %s", e)

    # Q3: ideas from recommendations
    for rec in report.recommendations:
        if rec.strip():
            try:
                task_id = task_board.add_task(
                    title=f"[DEBRIEF-IDEA] {_extract_summary(rec)}",
                    description=(
                        f"Идея от агента {report.agent_callsign or 'unknown'}.\n\n{rec}"
                    ),
                    phase_type="research",
                    priority=4,
                    tags=["debrief-auto", "architect-review", "idea"],
                    source="smart_debrief",
                )
                created.append(task_id)
                logger.info("[SmartDebrief] Created idea task: %s", task_id)
            except Exception as e:
                logger.debug("[SmartDebrief] Failed to create idea task: %s", e)

    return created


def _route_to_memory(text: str, report) -> dict:
    """MARKER_195.21/F4: Route text to memory subsystems via regex triggers.

    Each subsystem call is isolated in try/except — never crashes the debrief.
    Returns dict of triggered subsystems for logging/testing.
    """
    triggered = {}

    # REFLEX/CORTEX: tool name mentions → record feedback
    tool_matches = _TOOL_PATTERN.findall(text)
    if tool_matches:
        tools_deduped = list(set(tool_matches))
        triggered["reflex_tools"] = tools_deduped
        is_negative = bool(_BUG_PATTERNS.search(text))
        try:
            from src.services.reflex_feedback import get_reflex_feedback
            fb = get_reflex_feedback()
            for tool_name in tools_deduped:
                fb.record(
                    tool_id=tool_name,
                    success=not is_negative,
                    useful=not is_negative,
                    phase_type=report.domain or "research",
                    agent_role="debrief",
                    execution_time_ms=0.0,
                    subtask_id="",
                    extra={"source": "smart_debrief", "text": text[:200]},
                )
            logger.debug("[SmartDebrief] REFLEX recorded %d tools (neg=%s)", len(tools_deduped), is_negative)
        except Exception as e:
            logger.debug("[SmartDebrief] REFLEX write failed (non-fatal): %s", e)

    # AURA: user/UX mentions → store insight
    if _USER_PATTERN.search(text):
        triggered["aura_ux"] = True
        try:
            from src.memory.aura_store import get_aura_store
            store = get_aura_store()
            cat = "viewport_patterns" if re.search(r"UI|UX|viewport|panel|layout", text, re.IGNORECASE) else "communication_style"
            store.set_preference(
                agent_type="default",
                user_id="default",
                category=cat,
                key="debrief_ux_insight",
                value=text[:500],
                confidence=0.3,
            )
            logger.debug("[SmartDebrief] AURA stored UX insight (cat=%s)", cat)
        except Exception as e:
            logger.debug("[SmartDebrief] AURA write failed (non-fatal): %s", e)

    # MGC: file path mentions → hot file marker
    file_matches = _FILE_PATTERN.findall(text)
    if file_matches:
        files_deduped = list(set(file_matches))
        triggered["mgc_files"] = files_deduped
        try:
            from src.memory.mgc_cache import get_mgc_cache
            mgc = get_mgc_cache()
            for fpath in files_deduped:
                mgc.set_sync(
                    key=f"debrief_hot:{fpath}",
                    value={"source": "smart_debrief", "text": text[:200], "agent": report.agent_callsign},
                    size_bytes=0,
                )
            logger.debug("[SmartDebrief] MGC marked %d hot files", len(files_deduped))
        except Exception as e:
            logger.debug("[SmartDebrief] MGC write failed (non-fatal): %s", e)

    # ENGRAM: pattern/principle mentions → L1 learning entry
    if _LEARNING_PATTERN.search(text):
        triggered["engram_learning"] = True
        try:
            from src.memory.engram_cache import get_engram_cache
            cache = get_engram_cache()
            cat = "architecture" if re.search(r"always|never|принцип|principle|rule|правил", text, re.IGNORECASE) else "pattern"
            cache.put(
                key=f"{report.agent_callsign or 'unknown'}::debrief::learning::{report.domain or 'research'}",
                value=text[:300],
                category=cat,
                source_learning_id=f"debrief:{report.session_id}",
                match_count=0,
            )
            logger.debug("[SmartDebrief] ENGRAM stored learning (cat=%s)", cat)
        except Exception as e:
            logger.debug("[SmartDebrief] ENGRAM write failed (non-fatal): %s", e)

    # CORTEX: fallback — everything goes to general feedback
    if not triggered:
        triggered["cortex_general"] = True
        try:
            from src.services.reflex_feedback import get_reflex_feedback
            fb = get_reflex_feedback()
            fb.record(
                tool_id="__general_debrief__",
                success=True,
                useful=True,
                phase_type=report.domain or "research",
                agent_role="debrief",
                extra={"source": "smart_debrief", "text": text[:200]},
            )
            logger.debug("[SmartDebrief] CORTEX general fallback recorded")
        except Exception as e:
            logger.debug("[SmartDebrief] CORTEX fallback write failed (non-fatal): %s", e)

    return triggered


def process_smart_debrief(report) -> dict:
    """
    Main entry point. Process experience report:
    1. Create auto-tasks from bugs (Q1) and ideas (Q3)
    2. Route all answers through memory triggers

    Args:
        report: ExperienceReport instance

    Returns:
        Dict with processing results (tasks_created, memory_routes)
    """
    results = {
        "tasks_created": [],
        "memory_routes": [],
    }

    # 1. Auto-create tasks
    try:
        from src.orchestration.task_board import TaskBoard
        board = TaskBoard()
        results["tasks_created"] = _create_auto_tasks(report, board)
    except Exception as e:
        logger.debug("[SmartDebrief] Task creation skipped: %s", e)

    # 2. Route all text through memory triggers
    all_texts = list(report.lessons_learned) + list(report.recommendations)
    for text in all_texts:
        if text.strip():
            route = _route_to_memory(text, report)
            results["memory_routes"].append({"text_preview": text[:80], "triggered": route})

    logger.info(
        "[SmartDebrief] Processed report from %s: %d tasks created, %d texts routed",
        report.agent_callsign or "unknown",
        len(results["tasks_created"]),
        len(results["memory_routes"]),
    )

    return results
