"""
REFLEX Active Filter Engine — Tool Schema Filtering by Model Tier.

MARKER_173.P1.FILTER

Filters tool lists and FC tool_schemas based on:
- Model tier (Gold=all, Silver=top15, Bronze=top8)
- User preferences (pinned always included, banned always excluded)
- REFLEX scores (highest score tools survive)

Feature flag: REFLEX_ACTIVE (default: False)
Requires REFLEX_ENABLED to also be True.

Part of VETKA OS:
  VETKA > REFLEX > Filter Engine (this file)

@status: active
@phase: 173.P1
@depends: reflex_scorer, reflex_preferences, reflex_registry
"""

import logging
import os
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Feature flag for active filtering (separate from passive REFLEX_ENABLED)
REFLEX_ACTIVE = os.getenv("REFLEX_ACTIVE", "false").lower() in ("true", "1", "yes")

# ─── Tier Configuration ──────────────────────────────────────────

TIER_LIMITS: Dict[str, Optional[int]] = {
    "gold": None,     # No filtering — all tools pass through
    "silver": 15,     # Top 15 by score + always-include
    "bronze": 8,      # Top 8 by score + always-include
}

DEFAULT_ALWAYS_INCLUDE: Set[str] = {
    "vetka_read_file",
    "vetka_edit_file",
    "vetka_search_semantic",
}

PRESET_TO_TIER: Dict[str, str] = {
    "dragon_bronze": "bronze",
    "dragon_silver": "silver",
    "dragon_gold": "gold",
    "dragon_gold_gpt": "gold",
    "titan_lite": "bronze",
    "titan_core": "silver",
    "titan_prime": "gold",
}


# ─── Helpers ─────────────────────────────────────────────────────

def get_tool_id(tool: Any) -> str:
    """Extract tool_id from various tool representations.

    Supports:
    - ToolEntry objects (.tool_id attribute)
    - OpenAI-format schema dicts ({"function": {"name": "..."}})
    - Simple dicts with "tool_id" or "name" keys
    - Strings (returned as-is)
    """
    if hasattr(tool, "tool_id"):
        return tool.tool_id
    if isinstance(tool, dict):
        # OpenAI function calling format
        func = tool.get("function", {})
        if isinstance(func, dict) and "name" in func:
            return func["name"]
        # Simple dict formats
        return tool.get("tool_id", tool.get("name", str(tool)))
    return str(tool)


def resolve_model_tier(preset_name: str) -> str:
    """Map preset name to model tier (bronze/silver/gold).

    Unknown presets default to 'silver' (moderate filtering).
    """
    return PRESET_TO_TIER.get(preset_name, "silver")


# ─── Core Filter ─────────────────────────────────────────────────

def filter_tools(
    tools: List[Any],
    context: Any = None,
    model_tier: str = "silver",
    preferences: Any = None,
    always_include: Optional[Set[str]] = None,
) -> List[Any]:
    """MARKER_173.P1.CORE — Filter tools by tier, scores, and preferences.

    Args:
        tools: List of tools (ToolEntry, schema dict, or any with extractable ID)
        context: ReflexContext for scoring (optional — if None, uses position-based ordering)
        model_tier: "gold" (no filter), "silver" (top 15), "bronze" (top 8)
        preferences: ReflexPreferences object (optional — lazy-loaded if None)
        always_include: Tool IDs to always keep (merged with pinned tools)

    Returns:
        Filtered list of tools (same type as input).
    """
    if not tools:
        return tools

    # Check feature flags
    try:
        from src.services.reflex_scorer import REFLEX_ENABLED
        if not REFLEX_ENABLED or not REFLEX_ACTIVE:
            return tools
    except ImportError:
        return tools

    # Resolve always-include set
    keep_set = set(always_include) if always_include else set(DEFAULT_ALWAYS_INCLUDE)

    # Load preferences if not provided
    if preferences is None:
        try:
            from src.services.reflex_preferences import get_reflex_preferences
            preferences = get_reflex_preferences().get()
        except Exception:
            preferences = None

    # Add pinned tools to always-include
    if preferences and hasattr(preferences, "pinned_tools"):
        keep_set |= preferences.pinned_tools

    # Get banned tools
    banned: Set[str] = set()
    if preferences and hasattr(preferences, "banned_tools"):
        banned = preferences.banned_tools

    # Step 1: Remove banned tools
    tools_after_ban = []
    for tool in tools:
        tid = get_tool_id(tool)
        if tid not in banned:
            tools_after_ban.append(tool)

    # Step 2: Check tier limit
    limit = TIER_LIMITS.get(model_tier)
    if limit is None:
        # Gold tier: no top-N filtering, just ban filtering
        return tools_after_ban

    # Step 3: If already under limit, return as-is
    if len(tools_after_ban) <= limit:
        return tools_after_ban

    # Step 4: Separate always-include from remainder
    always_included = []
    remainder = []
    for tool in tools_after_ban:
        tid = get_tool_id(tool)
        if tid in keep_set:
            always_included.append(tool)
        else:
            remainder.append(tool)

    # Step 5: Score remainder (if context available)
    remaining_slots = max(0, limit - len(always_included))

    if remaining_slots == 0:
        return always_included

    if context is not None:
        try:
            from src.services.reflex_scorer import get_reflex_scorer
            scorer = get_reflex_scorer()
            scored_remainder = []
            for tool in remainder:
                score = scorer.score(tool, context)
                scored_remainder.append((score, tool))
            scored_remainder.sort(key=lambda x: x[0], reverse=True)
            top_remainder = [tool for _, tool in scored_remainder[:remaining_slots]]
        except Exception as e:
            logger.debug("[REFLEX Filter] Scoring error: %s — using position order", e)
            top_remainder = remainder[:remaining_slots]
    else:
        # No context: use position order (first N)
        top_remainder = remainder[:remaining_slots]

    return always_included + top_remainder


def filter_tool_schemas(
    schemas: List[Dict],
    context: Any = None,
    model_tier: str = "silver",
    preferences: Any = None,
    always_include: Optional[Set[str]] = None,
) -> List[Dict]:
    """MARKER_173.P1.SCHEMAS — Filter OpenAI-format tool schemas.

    Convenience wrapper around filter_tools for FC loop schemas.
    Input schemas are dicts with {"type": "function", "function": {"name": "...", ...}}.
    """
    return filter_tools(
        tools=schemas,
        context=context,
        model_tier=model_tier,
        preferences=preferences,
        always_include=always_include,
    )
