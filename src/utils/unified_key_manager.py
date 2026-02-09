"""
VETKA UnifiedKeyManager - Phase 111.9.

Single source of truth for all API key management.
Combines features from SecureKeyManager and KeyManager.

Phase 111.9 (2025-02-04): Universal key rotation for ALL providers
- Added get_key_with_rotation() for any provider
- Added rotate_provider_key() universal rotation
- report_failure() now auto-rotates for any provider
- Backwards compatible with OpenRouter-specific methods

@status: active
@phase: 111.9
@depends: dataclasses, pathlib, json
@used_by: model_router_v2.py, api_key_service.py, voice providers, provider_registry.py
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Any, Union
from datetime import datetime, timedelta
from pathlib import Path
import json
import re
import logging
import threading  # FIX_110.2: Added for thread-safe singleton

logger = logging.getLogger(__name__)

# Config file paths
CONFIG_FILE = Path(__file__).parent.parent.parent / "data" / "config.json"
LEARNED_PATTERNS_FILE = Path(__file__).parent.parent.parent / "data" / "learned_key_patterns.json"

# Cooldown duration for rate-limited keys (24 hours)
RATE_LIMIT_COOLDOWN = timedelta(hours=24)


class ProviderType(Enum):
    """
    Core API key providers (statically defined).
    Dynamic providers use string keys directly.

    Phase 112: Added POLZA, POE, MISTRAL for multi-source model support.
    Phase 111.9: Synced with provider_registry.Provider - keep in sync!

    NOTE: This enum must match provider_registry.Provider values.
    """
    # === Core providers ===
    OPENROUTER = "openrouter"
    GEMINI = "gemini"
    GOOGLE = "google"  # Phase 111.9: Sync with provider_registry
    OLLAMA = "ollama"
    XAI = "xai"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    # === Multi-source aggregators ===
    POLZA = "polza"
    POE = "poe"
    MISTRAL = "mistral"
    PERPLEXITY = "perplexity"
    NANOGPT = "nanogpt"
    TAVILY = "tavily"


# Type alias for provider (can be enum OR string for dynamic providers)
ProviderKey = Union[ProviderType, str]


@dataclass
class APIKeyRecord:
    """Record for a stored API key with cooldown support."""
    provider: ProviderKey
    key: str
    alias: str = ""
    added_at: datetime = field(default_factory=datetime.now)
    last_rotated: Optional[datetime] = None
    active: bool = True
    # Rate limit tracking
    rate_limited_at: Optional[datetime] = None
    failure_count: int = 0
    success_count: int = 0
    last_used: Optional[datetime] = None
    # MARKER_117_BALANCE: Balance tracking fields
    balance: Optional[float] = None
    balance_limit: Optional[float] = None
    balance_updated_at: Optional[datetime] = None

    def mask(self) -> str:
        """Return masked version of key for logging."""
        if not self.key or len(self.key) < 8:
            return '****'
        return f"{self.key[:4]}****{self.key[-4:]}"

    def is_available(self) -> bool:
        """Check if key is available (not in cooldown)."""
        if not self.active:
            return False
        if self.rate_limited_at:
            cooldown_end = self.rate_limited_at + RATE_LIMIT_COOLDOWN
            if datetime.now() < cooldown_end:
                return False
            # Cooldown expired, reset
            self.rate_limited_at = None
        return True

    def mark_rate_limited(self):
        """Mark key as rate-limited (starts 24h cooldown)."""
        self.rate_limited_at = datetime.now()
        self.failure_count += 1
        logger.info(f"[UnifiedKeyManager] Key {self.mask()} marked rate-limited until {self.rate_limited_at + RATE_LIMIT_COOLDOWN}")

    def mark_success(self):
        """Record successful use of key."""
        self.success_count += 1
        self.last_used = datetime.now()
        if self.failure_count > 0:
            self.failure_count = 0

    def cooldown_remaining(self) -> Optional[timedelta]:
        """Get remaining cooldown time, or None if not in cooldown."""
        if not self.rate_limited_at:
            return None
        cooldown_end = self.rate_limited_at + RATE_LIMIT_COOLDOWN
        remaining = cooldown_end - datetime.now()
        return remaining if remaining.total_seconds() > 0 else None

    def get_status(self) -> Dict[str, Any]:
        """Get key status for display."""
        cooldown = self.cooldown_remaining()
        # MARKER_117_BALANCE: Include balance info in status
        balance_percent = None
        if self.balance is not None and self.balance_limit is not None and self.balance_limit > 0:
            balance_percent = round((self.balance / self.balance_limit) * 100, 1)

        return {
            'masked': self.mask(),
            'alias': self.alias,
            'active': self.active,
            'available': self.is_available(),
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'cooldown_hours': round(cooldown.total_seconds() / 3600, 1) if cooldown else None,
            'balance': self.balance,
            'balance_limit': self.balance_limit,
            'balance_percent': balance_percent
        }


class UnifiedKeyManager:
    """
    Unified API Key Manager - Phase 57.12

    Features from SecureKeyManager:
    - OpenRouter rotation with paid key priority
    - get_openrouter_key() with explicit rotation control
    - reset_to_paid() and rotate_to_next() methods

    Features from KeyManager:
    - 24h cooldown on 402/rate limit
    - Dynamic provider support
    - Chat command processing
    - Learned pattern validation
    """

    COMMAND_PATTERNS = {
        "add_key": r"add\s+key[:\s]+(.+?)\s+for\s+(\w+)",
        "show_keys": r"show\s+keys",
        "rotate_keys": r"rotate\s+keys(?:\s+for\s+(\w+))?",
        "show_status": r"show\s+status",
        "validate_keys": r"validate\s+keys"
    }

    def __init__(self):
        """Initialize UnifiedKeyManager."""
        # Provider key storage
        self.keys: Dict[ProviderKey, List[APIKeyRecord]] = {
            ProviderType.OPENROUTER: [],
            ProviderType.GEMINI: [],
            ProviderType.OLLAMA: [],
            ProviderType.NANOGPT: [],
            ProviderType.TAVILY: [],
            ProviderType.XAI: [],
            ProviderType.OPENAI: [],
            ProviderType.ANTHROPIC: [],
            # Phase 112: New aggregator providers
            ProviderType.POLZA: [],
            ProviderType.POE: [],
            ProviderType.MISTRAL: [],
            ProviderType.PERPLEXITY: [],  # Phase 113
        }

        # Phase 111.9: Universal rotation state for ALL providers
        # Dict[ProviderKey, int] - current index for each provider
        self._current_indices: Dict[ProviderKey, int] = {}

        # Backwards compatibility alias
        self._current_openrouter_index = 0

        # Command history
        self.command_history: List[Dict[str, Any]] = []

        # Validation rules
        self.validation_rules: Dict[ProviderKey, Any] = {
            ProviderType.OPENROUTER: self._validate_openrouter_key,
            ProviderType.GEMINI: self._validate_gemini_key,
            ProviderType.OLLAMA: self._validate_ollama_key,
            ProviderType.NANOGPT: self._validate_nanogpt_key,
            ProviderType.TAVILY: self._validate_tavily_key,
            ProviderType.XAI: self._validate_xai_key,
            ProviderType.OPENAI: self._validate_openai_key,
            ProviderType.ANTHROPIC: self._validate_anthropic_key,
            # Phase 112: New aggregator providers
            ProviderType.POLZA: self._validate_polza_key,
            ProviderType.POE: self._validate_poe_key,
            ProviderType.MISTRAL: self._validate_mistral_key,
            ProviderType.PERPLEXITY: self._validate_perplexity_key,  # Phase 113
        }

        # Learned patterns for dynamic providers
        self._learned_patterns: Dict[str, Dict] = {}
        self._load_learned_patterns()

        # MARKER_126.9F: Preferred key for specific provider (one-shot use)
        # Dict[provider_name, key_masked] -> temporary preference from UI
        self._preferred_keys: Dict[str, str] = {}

        # Load keys from config
        self._load_from_config()

    # ============================================================
    # UNIVERSAL KEY ROTATION (Phase 111.9)
    # ============================================================

    def get_key_with_rotation(self, provider: ProviderKey, rotate: bool = False) -> Optional[str]:
        """
        Phase 111.9: Universal key rotation for ANY provider.

        Works with: OpenRouter, Poe, Polza, Mistral, XAI, etc.
        If provider has multiple keys, rotates between them on failure.

        MARKER_126.9F: Now checks for preferred key first (from UI selection).

        Args:
            provider: Provider enum or string
            rotate: If True, rotate to next key BEFORE returning

        Returns:
            API key string or None if no keys available
        """
        # MARKER_126.9F: Check for UI-selected preferred key first
        preferred = self.get_preferred_key(provider)
        if preferred:
            return preferred

        self._ensure_provider_initialized(provider)
        provider_keys = self.keys.get(provider, [])

        if not provider_keys:
            return None

        # Get available keys (skip rate-limited)
        available_keys = [r for r in provider_keys if r.is_available()]
        if not available_keys:
            provider_name = self._get_provider_name(provider)
            logger.warning(f"[UnifiedKeyManager] All {provider_name} keys in cooldown!")
            return None

        # Get current index for this provider (default 0)
        current_idx = self._current_indices.get(provider, 0)

        # Rotate first if requested
        if rotate:
            current_idx = (current_idx + 1) % len(available_keys)
            self._current_indices[provider] = current_idx
            provider_name = self._get_provider_name(provider)
            logger.info(f"[UnifiedKeyManager] Rotated {provider_name} to key index {current_idx}")

        # Ensure index is within bounds
        idx = current_idx % len(available_keys)
        return available_keys[idx].key

    def rotate_provider_key(self, provider: ProviderKey) -> None:
        """
        Phase 111.9: Explicitly rotate to next key for ANY provider.
        Call this when current key fails (402, 401, timeout).
        """
        self._ensure_provider_initialized(provider)
        provider_keys = self.keys.get(provider, [])
        available_keys = [r for r in provider_keys if r.is_available()]

        if available_keys:
            old_index = self._current_indices.get(provider, 0)
            new_index = (old_index + 1) % len(available_keys)
            self._current_indices[provider] = new_index
            provider_name = self._get_provider_name(provider)
            logger.info(f"[UnifiedKeyManager] Rotated {provider_name} key: {old_index} -> {new_index}")

    def reset_provider_index(self, provider: ProviderKey) -> None:
        """
        Phase 111.9: Reset provider to first key (index 0).
        Call at start of new conversation to use preferred keys first.
        """
        current = self._current_indices.get(provider, 0)
        if current != 0:
            provider_name = self._get_provider_name(provider)
            logger.info(f"[UnifiedKeyManager] Reset {provider_name} to index 0 (was {current})")
            self._current_indices[provider] = 0

    def get_provider_keys_count(self, provider: ProviderKey) -> int:
        """Get total number of available keys for any provider."""
        self._ensure_provider_initialized(provider)
        provider_keys = self.keys.get(provider, [])
        return len([r for r in provider_keys if r.is_available()])

    # ============================================================
    # MARKER_126.9F: PREFERRED KEY SELECTION (from UI)
    # ============================================================

    def set_preferred_key(self, provider: str, key_masked: str) -> bool:
        """
        MARKER_126.9F: Set a preferred key for the next LLM call.

        When set, get_key_with_rotation() will return this specific key
        instead of the normal rotation. Preference is cleared after use.

        Args:
            provider: Provider name (e.g., "polza", "openrouter")
            key_masked: Masked key ID (e.g., "sk-or-****abcd")

        Returns:
            True if key found and preference set
        """
        provider_lower = provider.lower()
        self._preferred_keys[provider_lower] = key_masked
        logger.info(f"[UnifiedKeyManager] Preferred key set: {provider_lower}/{key_masked[:12]}...")
        return True

    def clear_preferred_key(self, provider: Optional[str] = None) -> None:
        """
        MARKER_126.9F: Clear preferred key preference.

        Args:
            provider: If given, clear only for that provider. Otherwise clear all.
        """
        if provider:
            self._preferred_keys.pop(provider.lower(), None)
        else:
            self._preferred_keys.clear()

    def get_preferred_key(self, provider: ProviderKey) -> Optional[str]:
        """
        MARKER_126.9F: Get preferred key if set, clear after use.

        Returns the actual API key if preference is set and key exists.
        Clears the preference after returning (one-shot use).
        """
        provider_name = self._get_provider_name(provider).lower()

        preferred_masked = self._preferred_keys.get(provider_name)
        if not preferred_masked:
            return None

        # Find the actual key by masked ID
        provider_keys = self.keys.get(provider, [])
        for record in provider_keys:
            if record.mask() == preferred_masked and record.is_available():
                # Clear preference (one-shot)
                self._preferred_keys.pop(provider_name, None)
                logger.info(f"[UnifiedKeyManager] Using preferred key: {provider_name}/{preferred_masked[:12]}...")
                return record.key

        # Key not found or not available - clear anyway
        self._preferred_keys.pop(provider_name, None)
        logger.warning(f"[UnifiedKeyManager] Preferred key not found/available: {provider_name}/{preferred_masked}")
        return None

    # ============================================================
    # OPENROUTER ROTATION (backwards compatibility)
    # ============================================================

    def get_openrouter_key(self, index: Optional[int] = None, rotate: bool = False) -> Optional[str]:
        """
        Get OpenRouter key with rotation control.
        Phase 111.9: Now delegates to universal get_key_with_rotation().
        """
        if index is not None:
            # Specific index requested
            available_keys = [r for r in self.keys.get(ProviderType.OPENROUTER, []) if r.is_available()]
            if 0 <= index < len(available_keys):
                return available_keys[index].key
            return None

        # Delegate to universal rotation
        key = self.get_key_with_rotation(ProviderType.OPENROUTER, rotate=rotate)

        # Keep backwards compat index in sync
        self._current_openrouter_index = self._current_indices.get(ProviderType.OPENROUTER, 0)

        return key

    def rotate_to_next(self) -> None:
        """
        Explicitly rotate to next OpenRouter key.
        Phase 111.9: Now delegates to universal rotate_provider_key().
        """
        self.rotate_provider_key(ProviderType.OPENROUTER)
        # Keep backwards compat index in sync
        self._current_openrouter_index = self._current_indices.get(ProviderType.OPENROUTER, 0)

    def reset_to_free(self) -> None:
        """
        Phase 93.1: Reset to free key (index 0).
        Phase 111.9: Now delegates to universal reset_provider_index().
        """
        self.reset_provider_index(ProviderType.OPENROUTER)
        self._current_openrouter_index = 0

    # Alias for backwards compatibility
    def reset_to_paid(self) -> None:
        """Deprecated: Use reset_to_free() instead. Kept for backwards compatibility."""
        self.reset_to_free()

    def get_openrouter_keys_count(self) -> int:
        """Get total number of available OpenRouter keys."""
        return self.get_provider_keys_count(ProviderType.OPENROUTER)

    # ============================================================
    # KEY ACCESS (combined)
    # ============================================================

    def get_key(self, provider: str) -> Optional[str]:
        """
        Get active key for any provider with rotation support.

        Phase 111.9: Now uses universal rotation for ALL providers.
        If provider has multiple keys, returns current key in rotation.

        Args:
            provider: Provider name (e.g., 'anthropic', 'gemini', 'openrouter', 'poe', 'polza')

        Returns:
            API key or None
        """
        provider_key = self._get_provider_key(provider)
        # Phase 111.9: Use universal rotation for ALL providers
        return self.get_key_with_rotation(provider_key, rotate=False)

    def get_key_with_record(self, provider: ProviderKey) -> Optional[APIKeyRecord]:
        """Get first available key record for provider."""
        self._ensure_provider_initialized(provider)
        for record in self.keys.get(provider, []):
            if record.is_available():
                return record
        return None

    def get_active_key(self, provider: ProviderKey) -> Optional[str]:
        """
        Get first available key for provider (backwards compatibility).
        Skips rate-limited keys (24h cooldown).
        """
        # For OpenRouter, use rotation logic
        if provider == ProviderType.OPENROUTER:
            return self.get_openrouter_key()

        self._ensure_provider_initialized(provider)
        for record in self.keys.get(provider, []):
            if record.is_available():
                return record.key

        logger.debug(f"[UnifiedKeyManager] No active key for provider: {provider}")
        return None

    # ============================================================
    # COOLDOWN MANAGEMENT (from KeyManager)
    # ============================================================

    def report_failure(self, key: str, mark_cooldown: bool = True, auto_rotate: bool = True):
        """
        Report key failure and optionally rotate to next key.

        Phase 111.9: Auto-rotation now works for ALL providers, not just OpenRouter.

        Args:
            key: The failed API key
            mark_cooldown: If True, start 24h cooldown
            auto_rotate: If True, automatically rotate to next key
        """
        for provider, provider_keys in self.keys.items():
            for record in provider_keys:
                if record.key == key:
                    if mark_cooldown:
                        record.mark_rate_limited()
                    else:
                        record.failure_count += 1

                    # Phase 111.9: Auto-rotate on failure for ANY provider with multiple keys
                    if auto_rotate:
                        available_count = len([r for r in provider_keys if r.is_available()])
                        if available_count > 1:  # Only rotate if there are other keys
                            old_idx = self._current_indices.get(provider, 0)
                            self.rotate_provider_key(provider)
                            new_idx = self._current_indices.get(provider, 0)
                            provider_name = self._get_provider_name(provider)
                            logger.info(f"[UnifiedKeyManager] Auto-rotated {provider_name} key: {old_idx} -> {new_idx}")

                            # Keep backwards compat for OpenRouter
                            if provider == ProviderType.OPENROUTER:
                                self._current_openrouter_index = new_idx
                    return

    def report_success(self, key: str):
        """Report successful key use."""
        for provider_keys in self.keys.values():
            for record in provider_keys:
                if record.key == key:
                    record.mark_success()
                    return

    def get_keys_status(self, provider: ProviderKey) -> List[Dict[str, Any]]:
        """Get status of all keys for a provider."""
        self._ensure_provider_initialized(provider)
        return [record.get_status() for record in self.keys.get(provider, [])]

    # ============================================================
    # BALANCE CHECKING (Phase 117)
    # ============================================================

    # MARKER_126.3A: OpenRouter balance parser with free-tier detection
    def _parse_openrouter_balance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse OpenRouter /api/v1/auth/key response correctly.

        Free-tier keys have:
          - limit: null (no spending limit)
          - limit_remaining: 9999.xx (max credit, NOT real money)
          - is_free_tier: true

        Paid keys have:
          - limit: 50.0 (actual spending cap)
          - limit_remaining: 35.42 (remaining within cap)
        """
        d = data.get('data', {})

        limit = d.get('limit')
        limit_remaining = d.get('limit_remaining', 0)
        usage = d.get('usage', 0)
        is_free_tier = d.get('is_free_tier', limit is None)

        if is_free_tier:
            return {
                'balance': 0.0,
                'limit': 0.0,
                'used': usage,
                'is_free_tier': True,
                'exhausted': usage > 0
            }
        else:
            return {
                'balance': limit_remaining,
                'limit': limit or 0,
                'used': usage,
                'is_free_tier': False,
                'exhausted': limit_remaining <= 0
            }

    # MARKER_117_BALANCE + MARKER_126.3B: Async balance fetcher with free-tier fix
    async def fetch_provider_balance(self, provider: str) -> Optional[Dict[str, Any]]:
        """Fetch balance from provider API. Returns {balance, limit, used} or None."""
        import httpx

        BALANCE_ENDPOINTS = {
            'openrouter': {
                'url': 'https://openrouter.ai/api/v1/auth/key',
                'auth': 'Bearer',
                'parse': self._parse_openrouter_balance  # MARKER_126.3B: Use fixed parser
            },
            'polza': {
                'url': 'https://api.polza.ai/api/v1/account/balance',
                'auth': 'Bearer',
                'parse': lambda data: {
                    'balance': data.get('balance', 0),
                    'limit': data.get('limit', 0),
                    'used': data.get('used', 0),
                    'is_free_tier': False,
                    'exhausted': data.get('balance', 0) <= 0
                }
            }
        }

        endpoint = BALANCE_ENDPOINTS.get(provider)
        if not endpoint:
            return None

        # Get active key for this provider
        key = self.get_key(provider)
        if not key:
            return None

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                headers = {'Authorization': f'{endpoint["auth"]} {key}'}
                resp = await client.get(endpoint['url'], headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    parsed = endpoint['parse'](data)
                    # Update record
                    provider_key = self._get_provider_key(provider)
                    for record in self.keys.get(provider_key, []):
                        if record.key == key:
                            record.balance = parsed.get('balance')
                            record.balance_limit = parsed.get('limit')
                            record.balance_updated_at = datetime.now()
                            break

                    # MARKER_126.3C: Update BalanceTracker with remote balance
                    try:
                        from src.services.balance_tracker import get_balance_tracker
                        tracker = get_balance_tracker()
                        key_masked = f"{key[:4]}****{key[-4:]}" if len(key) > 8 else "****"
                        tracker.update_balance(
                            provider=provider,
                            key_masked=key_masked,
                            balance=parsed.get('balance', 0),
                            limit=parsed.get('limit'),
                            is_free_tier=parsed.get('is_free_tier', False),
                            exhausted=parsed.get('exhausted', False)
                        )
                    except Exception as e:
                        logger.debug(f"[MARKER_126.3C] Tracker update failed: {e}")

                    return parsed
                elif resp.status_code in (401, 403):
                    return {'error': 'unauthorized', 'status': resp.status_code}
                else:
                    return {'error': f'HTTP {resp.status_code}', 'status': resp.status_code}
        except Exception as e:
            logger.warning(f"[MARKER_117_BALANCE] Balance check failed for {provider}: {e}")
            return {'error': str(e)}

    async def get_full_provider_status(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """Get unified status: local state + remote balance."""
        providers_to_check = [provider] if provider else list(self.keys.keys())
        result = {}
        for p in providers_to_check:
            p_name = p.value if hasattr(p, 'value') else str(p)
            local_status = self.get_keys_status(p)
            remote_balance = await self.fetch_provider_balance(p_name)
            result[p_name] = {
                'keys': local_status,
                'balance': remote_balance,
                'provider': p_name
            }
        return result

    # ============================================================
    # VALIDATION RULES
    # ============================================================

    def _validate_openrouter_key(self, key: str) -> bool:
        return key.startswith("sk-or-") and len(key) > 20

    def _validate_gemini_key(self, key: str) -> bool:
        return len(key) > 30 and key.replace("-", "").replace("_", "").isalnum()

    def _validate_ollama_key(self, key: str) -> bool:
        return len(key) > 0

    def _validate_nanogpt_key(self, key: str) -> bool:
        return key.startswith("sk-nano-") and len(key) > 40

    def _validate_tavily_key(self, key: str) -> bool:
        return (key.startswith("tvly-dev-") or key.startswith("tvly-")) and len(key) > 20

    def _validate_xai_key(self, key: str) -> bool:
        return key.startswith("xai-") and len(key) > 50

    def _validate_openai_key(self, key: str) -> bool:
        # Phase 57.12: Support sk-proj- keys (new format, ~164 chars)
        if key.startswith("sk-proj-") and len(key) > 80:
            return True
        # Legacy format
        return key.startswith("sk-") and len(key) > 40

    def _validate_anthropic_key(self, key: str) -> bool:
        return key.startswith("sk-ant-") and len(key) > 40

    # Phase 112: New aggregator validators
    def _validate_polza_key(self, key: str) -> bool:
        """Polza AI keys start with 'pza_' prefix."""
        return key.startswith("pza_") and len(key) > 20

    def _validate_poe_key(self, key: str) -> bool:
        """
        Poe API keys validation.

        Phase 113: Stricter validation based on observed patterns.
        Poe keys are alphanumeric with hyphens, typically 35-50 chars.
        Example: kwodYaOPh6Oix7rI-XJMVDigFvkFdrDv420N5TauLqo
        """
        if len(key) < 35 or len(key) > 50:
            return False
        # Must start with letter
        if not key[0].isalpha():
            return False
        # Allow alphanumeric, hyphens, underscores
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        return all(c in allowed for c in key)

    def _validate_mistral_key(self, key: str) -> bool:
        """Mistral AI keys - alphanumeric, 32+ chars."""
        return len(key) >= 32 and key.replace("-", "").replace("_", "").isalnum()

    def _validate_perplexity_key(self, key: str) -> bool:
        """
        Perplexity AI keys validation.

        Phase 113: Perplexity keys have 'pa-' prefix (NOT 'pplx-').
        Example: pa-eT5WN...JZIQ (44-54 chars total)
        """
        if not key.startswith("pa-"):
            return False
        if len(key) < 44 or len(key) > 54:
            return False
        return True

    def _validate_dynamic_key(self, key: str, provider: str) -> bool:
        """Validate key using learned pattern or basic check."""
        pattern = self._learned_patterns.get(provider)
        if pattern:
            prefix = pattern.get('prefix')
            if prefix and not key.startswith(prefix):
                return False
            length_min = pattern.get('length_min', 10)
            length_max = pattern.get('length_max', 200)
            if not (length_min <= len(key) <= length_max):
                return False
            return True
        return len(key) >= 10

    # ============================================================
    # DYNAMIC PROVIDER SUPPORT
    # ============================================================

    def _load_learned_patterns(self):
        """Load learned key patterns for dynamic validation."""
        if LEARNED_PATTERNS_FILE.exists():
            try:
                with open(LEARNED_PATTERNS_FILE, 'r', encoding='utf-8') as f:
                    self._learned_patterns = json.load(f)
                logger.info(f"[UnifiedKeyManager] Loaded {len(self._learned_patterns)} learned patterns")
            except Exception as e:
                logger.error(f"[UnifiedKeyManager] Failed to load learned patterns: {e}")
                self._learned_patterns = {}

    def _get_provider_key(self, provider_name: str) -> ProviderKey:
        """Convert provider name to ProviderKey (enum or string)."""
        provider_lower = provider_name.lower().strip()
        for pt in ProviderType:
            if pt.value == provider_lower:
                return pt
        return provider_lower

    def _ensure_provider_initialized(self, provider: ProviderKey):
        """Ensure provider exists in keys dict."""
        if provider not in self.keys:
            self.keys[provider] = []
            logger.info(f"[UnifiedKeyManager] Initialized dynamic provider: {provider}")

    def _get_provider_name(self, provider: ProviderKey) -> str:
        """Get string name for any provider type."""
        if isinstance(provider, ProviderType):
            return provider.value
        return str(provider)

    # ============================================================
    # KEY MANAGEMENT
    # ============================================================

    def add_key(self, provider: ProviderKey, key: str, alias: str = "") -> bool:
        """Add a key for a provider."""
        self._ensure_provider_initialized(provider)

        # Validate
        if provider in self.validation_rules:
            if not self.validation_rules[provider](key):
                return False
        else:
            provider_name = self._get_provider_name(provider)
            if not self._validate_dynamic_key(key, provider_name):
                return False

        record = APIKeyRecord(provider=provider, key=key, alias=alias)
        self.keys[provider].append(record)
        self.save_to_config()
        return True

    # Alias for backwards compatibility
    add_key_direct = add_key

    def remove_key_by_index(self, provider: ProviderKey, index: int) -> bool:
        """Remove key at specified index."""
        self._ensure_provider_initialized(provider)
        keys_list = self.keys.get(provider, [])
        if 0 <= index < len(keys_list):
            removed = keys_list.pop(index)
            self.save_to_config()
            logger.info(f"[UnifiedKeyManager] Removed key {removed.mask()} for {self._get_provider_name(provider)}")
            return True
        return False

    def add_openrouter_key(self, key: str, is_paid: bool = False) -> Dict[str, Any]:
        """
        Add OpenRouter key with paid/free distinction.
        Phase 93.1: FREE keys get priority (lower index), PAID keys go last.
        """
        if not self._validate_openrouter_key(key):
            return {"success": False, "message": "Invalid OpenRouter key format"}

        record = APIKeyRecord(
            provider=ProviderType.OPENROUTER,
            key=key,
            alias='paid' if is_paid else f'free_{len(self.keys[ProviderType.OPENROUTER])}'
        )

        # Phase 93.1: FREE keys insert at beginning (high priority), PAID keys append at end
        if is_paid:
            self.keys[ProviderType.OPENROUTER].append(record)  # PAID goes last
        else:
            self.keys[ProviderType.OPENROUTER].insert(0, record)  # FREE goes first

        self.save_to_config()
        return {
            "success": True,
            "message": f"OpenRouter key added {'(paid)' if is_paid else '(free)'}",
            "masked_key": record.mask()
        }

    # ============================================================
    # CONFIG PERSISTENCE
    # ============================================================

    def load_from_config(self) -> int:
        """
        Public method for loading keys from config.
        Returns number of keys loaded (for backwards compatibility).
        """
        # Clear existing keys first
        for provider in self.keys:
            self.keys[provider] = []

        self._load_from_config()
        return sum(len(records) for records in self.keys.values())

    def _load_from_config(self):
        """Load all keys from config.json."""
        if not CONFIG_FILE.exists():
            logger.warning(f"[UnifiedKeyManager] Config file not found: {CONFIG_FILE}")
            return

        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)

            api_keys = config.get('api_keys', {})
            loaded_count = 0

            for provider_name, keys_data in api_keys.items():
                if keys_data is None:
                    continue

                provider = self._get_provider_key(provider_name)
                self._ensure_provider_initialized(provider)

                validator = self.validation_rules.get(provider)
                if not validator:
                    validator = lambda k, p=provider_name: self._validate_dynamic_key(k, p)

                loaded_count += self._load_provider_keys(provider, keys_data, provider_name, validator)

            logger.info(f"[UnifiedKeyManager] Loaded {loaded_count} keys from config")

            # Log summary
            openrouter_count = len(self.keys.get(ProviderType.OPENROUTER, []))
            logger.info(f"   OpenRouter: {openrouter_count} keys")
            logger.info(f"   Gemini: {len(self.keys.get(ProviderType.GEMINI, []))} keys")
            logger.info(f"   OpenAI: {len(self.keys.get(ProviderType.OPENAI, []))} keys")

        except Exception as e:
            logger.error(f"[UnifiedKeyManager] Error loading config: {e}")

    def _load_provider_keys(self, provider: ProviderKey, keys_data: Any, provider_name: str, validator) -> int:
        """Load keys for a single provider."""
        loaded = 0

        # Format 1: String (single key)
        if isinstance(keys_data, str) and keys_data:
            if validator(keys_data):
                record = APIKeyRecord(provider=provider, key=keys_data)
                self.keys[provider].append(record)
                loaded += 1

        # Format 2: Array of keys
        elif isinstance(keys_data, list):
            for i, key in enumerate(keys_data):
                if key and validator(key):
                    record = APIKeyRecord(provider=provider, key=key, alias=f'{provider_name}_{i + 1}')
                    self.keys[provider].append(record)
                    loaded += 1

        # Format 3: Dict (OpenRouter style: {paid: key, free: [keys]})
        # Phase 93.1: Load FREE keys FIRST (index 0+), PAID key LAST
        # Priority order: FREE → PAID (save money, use free quotas first)
        elif isinstance(keys_data, dict):
            # Load FREE keys first (they get lower indices = higher priority)
            for i, key in enumerate(keys_data.get('free', [])):
                if key and validator(key):
                    record = APIKeyRecord(provider=provider, key=key, alias=f'free_{i + 1}')
                    self.keys[provider].append(record)
                    loaded += 1

            # Load PAID key last (it gets highest index = lowest priority)
            if paid_key := keys_data.get('paid'):
                if validator(paid_key):
                    record = APIKeyRecord(provider=provider, key=paid_key, alias='paid')
                    self.keys[provider].append(record)
                    loaded += 1

        return loaded

    def save_to_config(self) -> bool:
        """Save all keys to config.json."""
        try:
            config = {}
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            if 'api_keys' not in config:
                config['api_keys'] = {}

            for provider, records in self.keys.items():
                provider_name = self._get_provider_name(provider)
                active_keys = [r.key for r in records if r.active]

                if not active_keys:
                    continue

                if provider_name == 'openrouter':
                    # Phase 93.1: FREE keys are at indices 0..n-1, PAID key is at index -1 (last)
                    # When saving, we need to identify which is paid by alias
                    paid_key = None
                    free_keys = []
                    for r in records:
                        if r.active:
                            if r.alias == 'paid':
                                paid_key = r.key
                            else:
                                free_keys.append(r.key)
                    config['api_keys']['openrouter'] = {
                        'paid': paid_key,
                        'free': free_keys
                    }
                else:
                    if len(active_keys) == 1:
                        config['api_keys'][provider_name] = active_keys[0]
                    else:
                        config['api_keys'][provider_name] = active_keys

            config['updated_at'] = datetime.now().isoformat()

            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            logger.error(f"[UnifiedKeyManager] Error saving to config: {e}")
            return False

    # ============================================================
    # UTILITY METHODS
    # ============================================================

    def mask_key(self, key: str) -> str:
        """Mask an API key for display."""
        if len(key) < 20:
            return "***"
        return f"{key[:10]}***{key[-4:]}"

    def validate_keys(self) -> Dict[str, bool]:
        """Check if keys exist for all providers. Phase 112: Extended with new providers."""
        return {
            'openrouter': len([r for r in self.keys.get(ProviderType.OPENROUTER, []) if r.is_available()]) > 0,
            'gemini': len([r for r in self.keys.get(ProviderType.GEMINI, []) if r.is_available()]) > 0,
            'anthropic': len([r for r in self.keys.get(ProviderType.ANTHROPIC, []) if r.is_available()]) > 0,
            'openai': len([r for r in self.keys.get(ProviderType.OPENAI, []) if r.is_available()]) > 0,
            # Phase 112: New aggregator providers
            'xai': len([r for r in self.keys.get(ProviderType.XAI, []) if r.is_available()]) > 0,
            'polza': len([r for r in self.keys.get(ProviderType.POLZA, []) if r.is_available()]) > 0,
            'poe': len([r for r in self.keys.get(ProviderType.POE, []) if r.is_available()]) > 0,
            'mistral': len([r for r in self.keys.get(ProviderType.MISTRAL, []) if r.is_available()]) > 0,
            'nanogpt': len([r for r in self.keys.get(ProviderType.NANOGPT, []) if r.is_available()]) > 0,
            'perplexity': len([r for r in self.keys.get(ProviderType.PERPLEXITY, []) if r.is_available()]) > 0,  # Phase 113
        }

    def get_stats(self) -> Dict:
        """Get manager statistics."""
        total_keys = sum(len(records) for records in self.keys.values())
        available_keys = sum(
            len([r for r in records if r.is_available()])
            for records in self.keys.values()
        )

        return {
            'total_keys': total_keys,
            'available_keys': available_keys,
            'openrouter_keys': len(self.keys.get(ProviderType.OPENROUTER, [])),
            'current_openrouter_index': self._current_openrouter_index,
            'providers_available': self.validate_keys(),
            'config_file': str(CONFIG_FILE),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize manager state."""
        return {
            "keys": {
                self._get_provider_name(provider): [
                    record.get_status()
                    for record in records
                ]
                for provider, records in self.keys.items()
            },
            "stats": self.get_stats()
        }

    # ============================================================
    # CHAT COMMANDS (from KeyManager)
    # ============================================================

    def process_command(self, command: str) -> Dict[str, Any]:
        """Process chat command and return result."""
        command_lower = command.lower().strip()

        if re.search(self.COMMAND_PATTERNS["add_key"], command_lower):
            return self._handle_add_key(command)
        elif re.search(self.COMMAND_PATTERNS["show_keys"], command_lower):
            return self._handle_show_keys()
        elif re.search(self.COMMAND_PATTERNS["show_status"], command_lower):
            return self._handle_show_status()
        else:
            return {"success": False, "message": f"Unknown command: {command}"}

    def _handle_add_key(self, command: str) -> Dict[str, Any]:
        pattern = r"add\s+key[:\s]+([^\s]+)\s+for\s+(\w+)"
        match = re.search(pattern, command, re.IGNORECASE)

        if not match:
            return {"success": False, "message": "Invalid format. Use: 'add key YOUR_KEY for PROVIDER'"}

        key, provider_name = match.groups()
        provider = self._get_provider_key(provider_name)

        if self.add_key(provider, key):
            return {"success": True, "message": f"Key added for {provider_name}"}
        else:
            return {"success": False, "message": f"Invalid key format for {provider_name}"}

    def _handle_show_keys(self) -> Dict[str, Any]:
        keys_list = []
        for provider, records in self.keys.items():
            for record in records:
                keys_list.append({
                    "provider": self._get_provider_name(provider),
                    "masked": record.mask(),
                    "status": "available" if record.is_available() else "cooldown",
                    "alias": record.alias
                })

        return {"success": True, "message": f"Found {len(keys_list)} keys", "keys": keys_list}

    def _handle_show_status(self) -> Dict[str, Any]:
        return {"success": True, "stats": self.get_stats()}


# ============================================================
# SINGLETON
# ============================================================

_unified_manager: Optional[UnifiedKeyManager] = None
_singleton_lock = threading.Lock()  # FIX_110.2: Thread-safe singleton


def get_key_manager() -> UnifiedKeyManager:
    """
    Get global UnifiedKeyManager instance (singleton).

    This is the ONLY key manager you need!
    Thread-safe via Lock (FIX_110.2).
    """
    global _unified_manager
    # Double-checked locking pattern for performance
    if _unified_manager is None:
        with _singleton_lock:
            if _unified_manager is None:
                _unified_manager = UnifiedKeyManager()
    return _unified_manager


def reset_key_manager() -> None:
    """Reset singleton (for testing)."""
    global _unified_manager
    with _singleton_lock:
        _unified_manager = None


# ============================================================
# BACKWARDS COMPATIBILITY EXPORTS
# ============================================================

# These allow existing code to work without changes
SecureKeyManager = UnifiedKeyManager  # Alias
KeyManager = UnifiedKeyManager  # Alias

__all__ = [
    'UnifiedKeyManager',
    'get_key_manager',
    'reset_key_manager',
    'ProviderType',
    'APIKeyRecord',
    'ProviderKey',
    'RATE_LIMIT_COOLDOWN',
    # Backwards compatibility
    'SecureKeyManager',
    'KeyManager',
]
