"""
MARKER_198.P2.4: Post-failure memory trigger.

Registered as a bridge post-hook. When an MCP tool fails:
1. Query ENGRAM L1 danger entries matching the tool name
2. Query CORTEX feedback for failure rate of same tool
3. Return formatted workaround hint (or None if no data)

@status: active
@phase: 198.P2.4
@depends: src/mcp/bridge_hooks.py, src/memory/engram_cache.py, src/services/reflex_feedback.py
"""

import fnmatch
import logging
from typing import Any, Dict, Optional

from src.memory.engram_cache import get_engram_cache
from src.services.reflex_feedback import get_reflex_feedback

logger = logging.getLogger("VETKA_WORKAROUND")


async def failure_workaround_post_hook(
    tool_name: str,
    arguments: Dict[str, Any],
    result_text: str,
    session_id: str,
    error: Optional[Exception] = None,
) -> Optional[str]:
    """MARKER_198.P2.4: Post-failure memory trigger.

    Only fires on failures (error is not None, or result_text starts with "Error").
    Queries ENGRAM L1 dangers + CORTEX feedback. Returns workaround hint.
    """
    # Guard: only fire on failures
    if error is None:
        if not result_text or not any(
            result_text.startswith(p) for p in ("Error", "error:", "Failed")
        ):
            return None

    suggestions = []

    # 1. ENGRAM L1 — danger entries matching tool pattern
    try:
        cache = get_engram_cache()
        danger_entries = cache.get_danger_entries()
        matched = [
            e for e in danger_entries
            if fnmatch.fnmatch(tool_name, e.key)
            or e.key in tool_name
            or tool_name in e.key
        ]
        if matched:
            best = max(matched, key=lambda e: e.hit_count)
            # Parse "reason | context" format used by reflex_guard
            parts = best.value.split("|", 1)
            reason = parts[0].strip()
            if reason:
                suggestions.append(f"Known issue: {reason}")
                logger.debug(f"[P2.4] ENGRAM danger match for {tool_name}: {reason[:80]}")
    except Exception as e:
        logger.debug(f"[P2.4] ENGRAM query failed (non-fatal): {e}")

    # 2. CORTEX — failure rate for this tool
    try:
        fb = get_reflex_feedback()
        summary = fb.get_feedback_summary()
        per_tool = summary.get("per_tool", {})
        stats = per_tool.get(tool_name)
        if stats:
            count = stats.get("count", 0)
            rate = stats.get("success_rate", 1.0)
            if count >= 2 and rate < 0.5:
                suggestions.append(
                    f"CORTEX: {tool_name} has {rate:.0%} success rate "
                    f"over {count} calls. Consider alternative approach."
                )
                logger.debug(f"[P2.4] CORTEX low success for {tool_name}: {rate:.0%}")
    except Exception as e:
        logger.debug(f"[P2.4] CORTEX query failed (non-fatal): {e}")

    if suggestions:
        return "\n".join(suggestions)
    return None


def register_workaround_hook() -> None:
    """Register the failure workaround hook with the bridge."""
    try:
        from src.mcp.bridge_hooks import register_post_hook
        register_post_hook(failure_workaround_post_hook)
        logger.info("[P2.4] Failure workaround post-hook registered")
    except Exception as e:
        logger.warning(f"[P2.4] Failed to register workaround hook: {e}")
