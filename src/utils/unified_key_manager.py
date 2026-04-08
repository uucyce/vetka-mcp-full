"""VETKA Unified Key Manager Stubs.

This module provides stub implementations for API key management.
These stubs allow the MCP server to run without full key management.
"""

from enum import Enum
from typing import Optional, Dict


class ProviderType(Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    GEMINI = "gemini"
    LITELLM = "litellm"


class _KeyManagerStub:
    """Stub for key manager."""

    def __init__(self):
        self._keys: Dict[str, str] = {}

    def get_key(self, provider: ProviderType) -> Optional[str]:
        """Get API key for provider."""
        import os

        # Try environment variables
        env_map = {
            ProviderType.OPENAI: "OPENAI_API_KEY",
            ProviderType.ANTHROPIC: "ANTHROPIC_API_KEY",
            ProviderType.OLLAMA: "OLLAMA_API_KEY",
            ProviderType.GEMINI: "GEMINI_API_KEY",
        }
        env_var = env_map.get(provider)
        if env_var:
            return os.environ.get(env_var)
        return self._keys.get(provider.value)

    def set_key(self, provider: ProviderType, key: str) -> None:
        """Set API key for provider."""
        self._keys[provider.value] = key

    def has_key(self, provider: ProviderType) -> bool:
        """Check if key exists for provider."""
        return self.get_key(provider) is not None


_key_manager: Optional[_KeyManagerStub] = None


def get_key_manager() -> _KeyManagerStub:
    """Get or create key manager instance."""
    global _key_manager
    if _key_manager is None:
        _key_manager = _KeyManagerStub()
    return _key_manager
