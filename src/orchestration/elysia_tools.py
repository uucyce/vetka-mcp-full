"""
MARKER_198.P2.3: ELYSIA Evaluation — ARCHIVED + STUBBED for Signal 9.

History: Phase 75.2 used this file to route read_file/write_file/git_commit
via Weaviate Elysia @tool decorator. That was wrong use case — deterministic ops
don't benefit from LLM-driven decision trees. Zero callers since Phase 75.2.

See evaluation verdict: docs/198_ph_reflex/ELYSIA_EVALUATION_VERDICT.md

CURRENT PURPOSE: Stub for REFLEX Signal 9 — Weaviate embedding similarity scoring.
When a Weaviate ToolDescriptions collection is populated, query_tool_similarity()
will return {tool_id: similarity_score} for top-K tools matching a task description.
Signal weight: 0.08 (see reflex_scorer.py Signal 9 slot).

@file src/orchestration/elysia_tools.py
@status STUB_FOR_SIGNAL_9
@phase Phase 198 — REFLEX Signal 9
@depends weaviate-client (optional, graceful fallback to {})
@used_by src/services/reflex_scorer.py (Signal 9 slot, tb_1774337717_1)
@history docs/73_ph/THE_LEGENDARY_ELISYA_MISHAP.md
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Weaviate availability (graceful degradation) ──────────────────────────────

try:
    import weaviate  # noqa: F401
    WEAVIATE_AVAILABLE = True
    logger.info("[ElysiaSig9] weaviate-client available")
except ImportError:
    WEAVIATE_AVAILABLE = False
    logger.debug("[ElysiaSig9] weaviate-client not installed — Signal 9 returns 0.0")

# Kept for import safety in any code that checks ELYSIA_AVAILABLE
ELYSIA_AVAILABLE = False


# ── REFLEX Signal 9: Weaviate embedding similarity ────────────────────────────

def query_tool_similarity(task_description: str) -> dict[str, float]:
    """Query Weaviate ToolDescriptions collection for semantic tool similarity.

    Returns {tool_id: similarity_score} for top-K tools matching task_description.
    Returns {} (Signal 9 = 0.0 contribution) if:
      - weaviate-client not installed
      - Weaviate server unavailable
      - ToolDescriptions collection empty or missing

    Usage (reflex_scorer.py Signal 9 slot):
        similarities = query_tool_similarity(task.description)
        signal_9 = similarities.get(tool_id, 0.0)  # 0.0 if not in top-K

    Collection schema (to be created when activating Signal 9):
        class ToolDescriptions:
            tool_id: str       # e.g. "vetka_task_board"
            description: str   # natural language description of tool's purpose
            domain: str        # e.g. "harness", "cut", "memory"
    """
    if not WEAVIATE_AVAILABLE:
        return {}

    try:
        # STUB: uncomment and adapt when ToolDescriptions collection is populated
        # import weaviate
        # client = weaviate.connect_to_local()
        # collection = client.collections.get("ToolDescriptions")
        # response = collection.query.near_text(
        #     query=task_description,
        #     limit=10,
        #     return_metadata=weaviate.classes.query.MetadataQuery(score=True),
        # )
        # return {obj.properties["tool_id"]: obj.metadata.score
        #         for obj in response.objects}
        return {}  # stub returns empty → Signal 9 contributes 0.0 weight
    except Exception as exc:
        logger.debug("[ElysiaSig9] Weaviate query failed (non-fatal): %s", exc)
        return {}


def get_signal9_score(tool_id: str, task_description: str) -> float:
    """Convenience wrapper for reflex_scorer.py.

    Returns similarity score [0.0, 1.0] for a single tool against task description.
    Returns 0.0 on any error or when Weaviate unavailable.
    """
    try:
        scores = query_tool_similarity(task_description)
        return float(scores.get(tool_id, 0.0))
    except Exception:
        return 0.0
