"""
VETKA Secure API Key Manager.

DEPRECATED: Use UnifiedKeyManager instead!
Phase 57.12: This module now re-exports from unified_key_manager.py.
All imports continue to work, but use the unified manager internally.

@status: deprecated
@phase: 96
@depends: unified_key_manager
@used_by: legacy imports (prefer unified_key_manager)
"""

# Phase 57.12: Re-export everything from UnifiedKeyManager
from src.utils.unified_key_manager import (
    UnifiedKeyManager as SecureKeyManager,
    get_key_manager,
    ProviderType,
    APIKeyRecord,
)

# Keep old exports working
__all__ = ['SecureKeyManager', 'get_key_manager']
