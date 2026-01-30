"""
KeyManager - chat-based API key management system.

DEPRECATED: Phase 57.12 - Use UnifiedKeyManager instead!
This module now re-exports from unified_key_manager.py for backwards compatibility.

@status: deprecated
@phase: 96
@depends: src.utils.unified_key_manager
@used_by: legacy imports (backwards compatibility)
"""

# Phase 57.12: Re-export everything from UnifiedKeyManager
from src.utils.unified_key_manager import (
    UnifiedKeyManager as KeyManager,
    get_key_manager,
    ProviderType,
    ProviderKey,
    APIKeyRecord,
    RATE_LIMIT_COOLDOWN,
)

# Keep old exports working
__all__ = [
    'KeyManager',
    'get_key_manager',
    'ProviderType',
    'ProviderKey',
    'APIKeyRecord',
    'RATE_LIMIT_COOLDOWN',
]
