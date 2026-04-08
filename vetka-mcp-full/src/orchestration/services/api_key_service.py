"""
API Key Management Service

Handles:
- API key loading from config.json
- Key rotation and management
- Key injection for LLM routing

@status: active
@phase: 96
@depends: src.utils.unified_key_manager
@used_by: src.orchestration.orchestrator_with_elisya, src.api.routes.health_routes
"""

import os
from typing import Optional, Dict, Any
from src.utils.unified_key_manager import UnifiedKeyManager as KeyManager, ProviderType


class APIKeyService:
    """Manages API keys with rotation and fallback."""

    def __init__(self):
        """Initialize the API key service."""
        self.key_manager = KeyManager()
        self._load_keys()

    def _load_keys(self, quiet: bool = False):
        """
        Load API keys from config.json into KeyManager.
        Phase 51.3: Removed env fallback, ONLY config.json.

        Args:
            quiet: If True, suppress log output (for repeated initializations)
        """
        # Load keys from config.json (NOT from environment!)
        loaded_count = self.key_manager.load_from_config()

        if not quiet:
            if loaded_count > 0:
                print(f"✅ KeyManager loaded from config.json:")
                print(f"   OpenRouter keys: {len(self.key_manager.keys[ProviderType.OPENROUTER])}")
                print(f"   Gemini keys: {len(self.key_manager.keys[ProviderType.GEMINI])}")
            else:
                print(f"⚠️  No API keys found in config.json")
                print(f"   Add keys via: http://localhost:8000/keys")

    def get_key(self, provider: str) -> Optional[str]:
        """
        Get active key for provider.

        Args:
            provider: Provider name (e.g., 'openrouter', 'gemini', 'ollama')

        Returns:
            API key string or None if not available
        """
        # Phase 80.38: Complete provider map with ALL supported providers
        # Phase 80.41: Added 'google' alias for 'gemini'
        provider_map = {
            'openrouter': ProviderType.OPENROUTER,
            'gemini': ProviderType.GEMINI,
            'google': ProviderType.GEMINI,     # Alias for gemini
            'ollama': ProviderType.OLLAMA,
            'nanogpt': ProviderType.NANOGPT,
            'xai': ProviderType.XAI,           # x.ai (Grok)
            'openai': ProviderType.OPENAI,     # OpenAI
            'anthropic': ProviderType.ANTHROPIC,  # Anthropic
            'tavily': ProviderType.TAVILY,     # Tavily search
        }

        provider_type = provider_map.get(provider.lower())
        if not provider_type:
            print(f"      ⚠️  Unknown provider: {provider}")
            return None

        key = self.key_manager.get_active_key(provider_type)

        if key:
            print(f"      🔑 Key injected for {provider}")
            return key
        else:
            print(f"      ⚠️  No active key for {provider}")
            return None

    def inject_key_to_env(self, provider: str, key: str) -> Dict[str, Optional[str]]:
        """
        Inject API key into environment variables.

        Args:
            provider: Provider name
            key: API key to inject

        Returns:
            Dict mapping env var names to their previous values (for restore)
        """
        saved_env = {}
        provider_upper = provider.upper()
        env_key_names = [
            f'{provider_upper}_API_KEY',
            f'{provider_upper.replace("-", "_")}_API_KEY',
        ]

        for env_key in env_key_names:
            saved_env[env_key] = os.environ.get(env_key)
            os.environ[env_key] = key

        print(f"      ✅ Key set in environment for {provider_upper}")
        return saved_env

    def restore_env(self, saved_env: Dict[str, Optional[str]]):
        """
        Restore environment variables to previous state.

        Args:
            saved_env: Dict from inject_key_to_env()
        """
        for env_key, value in saved_env.items():
            if value is not None:
                os.environ[env_key] = value
            else:
                os.environ.pop(env_key, None)

    def report_failure(self, provider: str, key: str):
        """
        Report key failure for rotation.

        Args:
            provider: Provider name
            key: Failed API key
        """
        self.key_manager.report_failure(key)

    def add_key(self, provider: str, key: str) -> Dict[str, Any]:
        """
        Add API key via chat command.
        Phase 57.12: Supports dynamic providers via UnifiedKeyManager.

        Args:
            provider: Provider name
            key: API key to add

        Returns:
            Dict with success status and message
        """
        # Phase 57.12: Use UnifiedKeyManager's dynamic provider support
        # No need for hardcoded map - manager handles any provider
        provider_lower = provider.lower()

        # Try to find in ProviderType enum first
        provider_key = None
        for pt in ProviderType:
            if pt.value == provider_lower:
                provider_key = pt
                break

        # If not in enum, use string key (dynamic provider)
        if provider_key is None:
            provider_key = provider_lower

        success = self.key_manager.add_key_direct(provider_key, key)

        if success:
            return {
                'success': True,
                'message': f'Key added for {provider}',
                'masked_key': self.key_manager.mask_key(key)
            }
        else:
            return {'success': False, 'error': 'Invalid key format'}

    def list_keys(self) -> Dict[str, Any]:
        """
        List all stored API keys (masked).

        Returns:
            Dict representation of KeyManager state
        """
        return self.key_manager.to_dict()

    def remove_key(self, provider: str, index: int) -> Dict[str, Any]:
        """
        Remove an API key by provider and index.
        Phase 57: Added for UI key management.

        Args:
            provider: Provider name (e.g., 'openrouter', 'gemini')
            index: Index of key to remove (0-based)

        Returns:
            Dict with success status
        """
        # Phase 80.38: Complete provider map with ALL supported providers
        # Phase 80.41: Added 'google' alias for 'gemini'
        provider_map = {
            'openrouter': ProviderType.OPENROUTER,
            'gemini': ProviderType.GEMINI,
            'google': ProviderType.GEMINI,     # Alias for gemini
            'ollama': ProviderType.OLLAMA,
            'nanogpt': ProviderType.NANOGPT,
            'xai': ProviderType.XAI,           # x.ai (Grok)
            'openai': ProviderType.OPENAI,     # OpenAI
            'anthropic': ProviderType.ANTHROPIC,  # Anthropic
            'tavily': ProviderType.TAVILY,     # Tavily search
        }

        provider_type = provider_map.get(provider.lower())
        if not provider_type:
            return {'success': False, 'error': f'Unknown provider: {provider}'}

        try:
            success = self.key_manager.remove_key_by_index(provider_type, index)
            if success:
                return {'success': True}
            else:
                return {'success': False, 'error': 'Key not found at index'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
