"""
DEPRECATED: This module has been renamed to aura_store.py (Phase 187.6).

All imports are re-exported from aura_store for backwards compatibility.
Remove this shim once all external consumers are migrated.
"""

from .aura_store import (  # noqa: F401
    AuraStore as EngramUserMemory,
    get_aura_store as get_engram_user_memory,
    aura_lookup as engram_lookup,
    AuraStore,
    get_aura_store,
    aura_lookup,
)
