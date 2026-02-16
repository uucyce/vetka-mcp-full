"""
VETKA Model Updater — On-demand LLM model profile fetching.

NO cron. NO polling. NO background loops.

Strategy: Lazy + event-driven.
- When a NEW model appears in pipeline (not seen before) → fetch its profile
- When pipeline starts → ensure all preset models have cached profiles
- Cache is persistent (3-day TTL in llm_model_registry.py) — no redundant fetches

MARKER_145.MODEL_UPDATER

@status: active
@phase: 145
@depends: asyncio, logging
@used_by: agent_pipeline._safe_phase (on-demand), preset loading
"""

import asyncio
import logging
from typing import Optional, Set

from src.elisya.llm_model_registry import get_llm_registry, ModelProfile

logger = logging.getLogger(__name__)

# Track which models we've already ensured this session (avoid redundant checks)
_ensured_models: Set[str] = set()


async def ensure_model_profile(model_id: str) -> Optional[ModelProfile]:
    """Ensure a model profile exists in the registry cache.

    Called on-demand when a model is first used in a pipeline phase.
    If the profile is already cached (in-memory or on disk), returns immediately.
    If the model is new, fetches from API and caches it.

    This replaces the old 6-hour cron loop with a zero-cost lazy approach:
    - First call for a model: ~200ms (API fetch if not in hardcoded defaults)
    - Subsequent calls: ~0ms (in-memory cache hit)

    Args:
        model_id: Model identifier (e.g., "qwen/qwen3-coder", "gpt-4o")

    Returns:
        ModelProfile if found/fetched, None on failure.
    """
    if not model_id:
        return None

    # Skip if already ensured this session
    if model_id in _ensured_models:
        return None  # Already checked — profile is in registry

    registry = get_llm_registry()
    try:
        profile = await registry.get_profile(model_id)
        _ensured_models.add(model_id)
        if profile:
            logger.debug("Model profile ensured: %s (source=%s, tps=%.1f)",
                         model_id, profile.source, profile.output_tokens_per_second)
        return profile
    except Exception as e:
        logger.warning("Failed to ensure model profile for %s: %s", model_id, e)
        _ensured_models.add(model_id)  # Don't retry failed models this session
        return None


async def ensure_preset_models(preset_roles: dict) -> int:
    """Ensure all models in a preset are cached. Called once when preset is applied.

    Args:
        preset_roles: Dict of role→model_id (e.g., {"coder": "qwen/qwen3-coder", ...})

    Returns:
        Number of models that were newly fetched (0 = all were cached).
    """
    if not preset_roles:
        return 0

    new_fetches = 0
    for role, model_id in preset_roles.items():
        if model_id and model_id not in _ensured_models:
            profile = await ensure_model_profile(model_id)
            if profile and profile.source not in ("hardcoded_defaults", "hardcoded_defaults_stripped"):
                new_fetches += 1  # Actually fetched from API, not just hardcoded
                logger.info("Fetched new model profile for preset role %s: %s", role, model_id)

    if new_fetches > 0:
        logger.info("Preset model profiles: %d newly fetched, %d already cached",
                     new_fetches, len(preset_roles) - new_fetches)

    return new_fetches


def reset_session_cache():
    """Reset the session-level ensured models set.

    Call this when the server restarts or when you want to force
    re-checking all models on next use.
    """
    count = len(_ensured_models)
    _ensured_models.clear()  # .clear() keeps same set reference (important for importers)
    if count > 0:
        logger.info("Model updater session cache reset (%d models cleared)", count)


# ---------------------------------------------------------------------------
# Backward-compatible API (for main.py lifespan hooks)
# ---------------------------------------------------------------------------

async def start_model_updater():
    """No-op. Kept for backward compatibility with main.py lifespan.

    Old behavior: started a 6-hour cron loop.
    New behavior: does nothing. Profiles are fetched on-demand.
    """
    logger.info("Model updater: on-demand mode (no background loop)")
    return None


async def stop_model_updater():
    """Reset session cache on shutdown. Kept for backward compatibility."""
    reset_session_cache()
    logger.info("Model updater: session cache cleared on shutdown")
