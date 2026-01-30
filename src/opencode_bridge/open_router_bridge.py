"""
OpenRouter Bridge for OpenCode UI.
Uses VETKA's existing key rotation logic.
Local-only, no real keys exposed.

@status: active
@phase: 96
@depends: src.utils.unified_key_manager, src.elisya.provider_registry, src.orchestration.services.api_key_service
@used_by: src.opencode_bridge.routes
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Import existing VETKA logic
from src.utils.unified_key_manager import get_key_manager, ProviderType
from src.elisya.provider_registry import ProviderRegistry, Provider, call_model_v2
from src.orchestration.services.api_key_service import APIKeyService


@dataclass
class BridgeStats:
    """Statistics for OpenCode UI"""

    total_keys: int = 0
    active_keys: int = 0
    rate_limited_keys: int = 0
    current_key_index: int = 0
    last_rotation: Optional[str] = None
    provider: str = "openrouter"


class OpenRouterBridge:
    """Bridge that wraps VETKA's OpenRouter multi-key logic"""

    def __init__(self):
        self.provider_type = ProviderType.OPENROUTER
        self.key_manager = get_key_manager()
        self.api_service = APIKeyService()
        self._load_keys()

    def _load_keys(self) -> None:
        """Load OpenRouter keys from config.json using existing logic"""
        try:
            # Get keys through existing manager
            openrouter_keys = self.key_manager.keys.get(self.provider_type, [])
            self.keys = [key for key in openrouter_keys if key.active]
            print(f"[Bridge] Loaded {len(self.keys)} OpenRouter keys")
        except Exception as e:
            print(f"[Bridge] Error loading keys: {e}")
            self.keys = []

    def get_available_keys(self) -> List[Dict[str, Any]]:
        """Get available keys for UI (masked)"""
        available = []
        for i, record in enumerate(self.keys):
            if record.is_available():
                available.append(
                    {
                        "id": f"openrouter_{i}",
                        "masked_key": record.mask(),
                        "status": "active",
                        "provider": "openrouter",
                        "alias": record.alias or f"key_{i}",
                    }
                )
        return available

    async def invoke(
        self, model_id: str, messages: List[Dict[str, Any]], **kwargs
    ) -> Dict[str, Any]:
        """Invoke model through bridge with automatic rotation"""
        try:
            # Use existing VETKA logic
            result = await call_model_v2(
                messages=messages,
                model=model_id,
                provider=Provider.OPENROUTER,
                tools=kwargs.get("tools"),
                temperature=kwargs.get("temperature", 0.7),
                # max_tokens removed - unlimited responses
            )

            # Log success (without key)
            print(f"[Bridge] Success: {model_id}")
            return {
                "success": True,
                "message": result.get("message", {}),
                "model": result.get("model", model_id),
                "provider": "openrouter",
                "usage": result.get("usage", {}),
            }

        except Exception as e:
            # Log error (without key)
            print(f"[Bridge] Error: {type(e).__name__}")
            return {"success": False, "error": str(e), "provider": "openrouter"}

    def get_stats(self) -> BridgeStats:
        """Get rotation statistics for UI"""
        stats = BridgeStats()
        stats.total_keys = len(self.keys)

        for i, record in enumerate(self.keys):
            if record.is_available():
                stats.active_keys += 1
            elif record.rate_limited_at:
                stats.rate_limited_keys += 1

        stats.current_key_index = self._get_current_key_index()
        stats.last_rotation = self._get_last_rotation_time()

        return stats

    def _get_current_key_index(self) -> int:
        """Determine current active key"""
        for i, record in enumerate(self.keys):
            if record.is_available():
                return i
        return 0

    def _get_last_rotation_time(self) -> Optional[str]:
        """Get time of last rotation"""
        for record in reversed(self.keys):
            if record.last_used:
                return record.last_used.isoformat()
        return None


# Singleton instance
_bridge_instance: Optional[OpenRouterBridge] = None


def get_openrouter_bridge() -> OpenRouterBridge:
    """Get singleton bridge instance"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = OpenRouterBridge()
    return _bridge_instance
