"""
Phase 93.1: LLMCore - Base class for all LLM interactions.

Shared logic for provider_registry.py and api_aggregator_v3.py.

Architecture (recommended by Grok-4 + Claude Sonnet):
- LLMCore: Base class with shared logic (routing, fallback, key management)
- UIHandler (api_aggregator): Streaming-specific, inherits LLMCore
- AgentHandler (provider_registry): Structured messages, inherits LLMCore

Key Features:
- Unified fallback chain: Direct API -> OpenRouter FREE -> OpenRouter PAID -> Ollama
- Provider detection from model name
- Key rotation with 24h cooldown
- XAI special handling (403 -> OpenRouter fallback)

@status: active
@phase: 96
@depends: logging, abc, typing, enum
@used_by: provider_registry, api_aggregator_v3
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, AsyncGenerator
from enum import Enum

logger = logging.getLogger(__name__)


class FallbackPriority(Enum):
    """
    Phase 93.1: Correct fallback priority order.
    Lower value = higher priority (try first).
    """
    DIRECT_API = 1      # Direct to provider API (OpenAI, Anthropic, xAI)
    OPENROUTER_FREE = 2 # OpenRouter with FREE keys
    OPENROUTER_PAID = 3 # OpenRouter with PAID keys
    OLLAMA_LOCAL = 4    # Local Ollama (last resort)


class LLMCore(ABC):
    """
    Base class for all LLM interactions.

    Subclasses:
    - AgentHandler: For MCP tools, orchestrator (structured messages, no streaming)
    - UIHandler: For browser UI (prompt strings, streaming)

    Shared functionality:
    - Provider detection from model name
    - Fallback chain management
    - Key rotation logic
    - Error handling (403, rate limits, etc.)
    """

    def __init__(self):
        self._key_manager = None
        self._api_key_service = None

    @property
    def key_manager(self):
        """Lazy load key manager to avoid circular imports."""
        if self._key_manager is None:
            from src.utils.unified_key_manager import get_key_manager
            self._key_manager = get_key_manager()
        return self._key_manager

    @property
    def api_key_service(self):
        """Lazy load API key service."""
        if self._api_key_service is None:
            from src.orchestration.services.api_key_service import APIKeyService
            self._api_key_service = APIKeyService()
        return self._api_key_service

    # ============================================================
    # PROVIDER DETECTION (shared logic)
    # ============================================================

    def detect_provider(self, model_name: str) -> str:
        """
        Detect provider from model name.

        MARKER_93.1_PROVIDER_DETECTION: Canonical detection logic.

        Args:
            model_name: Model identifier (e.g., 'gpt-4', 'xai/grok-4', 'deepseek-llm:7b')

        Returns:
            Provider string: 'openai', 'anthropic', 'google', 'xai', 'ollama', 'openrouter'
        """
        model_lower = model_name.lower()

        # OpenAI models
        if model_lower.startswith("openai/") or model_lower.startswith("gpt-"):
            return "openai"

        # Anthropic models
        if model_lower.startswith("anthropic/") or model_lower.startswith("claude-"):
            return "anthropic"

        # Google models
        if model_lower.startswith("google/") or model_lower.startswith("gemini"):
            return "google"

        # XAI/Grok models (Phase 90.1.4.1 patterns)
        if (model_lower.startswith("xai/") or
            model_lower.startswith("x-ai/") or
            model_lower.startswith("grok")):
            return "xai"

        # Ollama models (has colon for version)
        if ":" in model_name or model_lower.startswith("ollama/"):
            return "ollama"

        # OpenRouter (has slash but not a known provider)
        if "/" in model_name:
            return "openrouter"

        # Default to Ollama for local models
        return "ollama"

    # ============================================================
    # FALLBACK CHAIN (shared logic)
    # ============================================================

    def get_fallback_chain(self, model_name: str) -> List[Dict[str, Any]]:
        """
        Get fallback chain for a model.

        Phase 93.1: Correct order: Direct → FREE → PAID → Ollama

        Args:
            model_name: Model identifier

        Returns:
            List of fallback options with provider and model info
        """
        primary_provider = self.detect_provider(model_name)
        chain = []

        # Step 1: Direct API (if key available)
        if primary_provider in ('openai', 'anthropic', 'google', 'xai'):
            chain.append({
                'priority': FallbackPriority.DIRECT_API,
                'provider': primary_provider,
                'model': model_name,
                'description': f'Direct {primary_provider} API'
            })

        # Step 2: OpenRouter FREE (always available as fallback)
        openrouter_model = self._convert_to_openrouter_model(model_name, primary_provider)
        chain.append({
            'priority': FallbackPriority.OPENROUTER_FREE,
            'provider': 'openrouter',
            'model': openrouter_model,
            'use_free_key': True,
            'description': 'OpenRouter (FREE key)'
        })

        # Step 3: OpenRouter PAID
        chain.append({
            'priority': FallbackPriority.OPENROUTER_PAID,
            'provider': 'openrouter',
            'model': openrouter_model,
            'use_free_key': False,
            'description': 'OpenRouter (PAID key)'
        })

        # Step 4: Ollama local (last resort)
        ollama_model = self._get_ollama_fallback_model(model_name)
        if ollama_model:
            chain.append({
                'priority': FallbackPriority.OLLAMA_LOCAL,
                'provider': 'ollama',
                'model': ollama_model,
                'description': 'Ollama local fallback'
            })

        return chain

    def _convert_to_openrouter_model(self, model_name: str, provider: str) -> str:
        """
        Convert model name to OpenRouter format.

        MARKER-PROVIDER-004-FIX: Handle xai/ → x-ai/ conversion.
        """
        if provider == 'xai':
            # Remove any existing prefix and add correct x-ai/ prefix
            clean_model = model_name.replace('xai/', '').replace('x-ai/', '')
            return f'x-ai/{clean_model}'

        # Most models work as-is on OpenRouter
        return model_name

    def _get_ollama_fallback_model(self, model_name: str) -> Optional[str]:
        """
        Get Ollama fallback model for a given model.

        Maps cloud models to local equivalents.
        """
        # Mapping of cloud models to local Ollama equivalents
        CLOUD_TO_OLLAMA = {
            'deepseek/deepseek-chat': 'deepseek-llm:7b',
            'deepseek/deepseek-coder': 'deepseek-llm:7b',
            'meta-llama/llama-3.1-8b-instruct': 'llama3.1:8b',
            'anthropic/claude-3-haiku': 'qwen2:7b',
            'anthropic/claude-3.5-sonnet': 'qwen2:7b',
        }

        # Check direct mapping
        if model_name in CLOUD_TO_OLLAMA:
            return CLOUD_TO_OLLAMA[model_name]

        # Default Ollama model
        return 'deepseek-llm:7b'

    # ============================================================
    # KEY MANAGEMENT (shared logic)
    # ============================================================

    def get_key_for_provider(self, provider: str, use_free: bool = True) -> Optional[str]:
        """
        Get API key for a provider.

        Phase 93.1: FREE keys first by default.

        Args:
            provider: Provider name
            use_free: If True, prefer free keys (default). If False, use paid.

        Returns:
            API key or None
        """
        if provider == 'openrouter':
            return self.key_manager.get_openrouter_key()
        else:
            return self.api_key_service.get_key(provider)

    def handle_key_error(self, provider: str, error_code: int) -> bool:
        """
        Handle key-related errors (403, 401, 402).

        Args:
            provider: Provider that returned error
            error_code: HTTP error code

        Returns:
            True if should retry with next key, False if all keys exhausted
        """
        if error_code in (401, 402, 403):
            if provider == 'openrouter':
                self.key_manager.rotate_to_next()
                return self.key_manager.get_openrouter_keys_count() > 0
            elif provider == 'xai':
                # Mark key as rate-limited (24h cooldown)
                # This is handled in XaiProvider
                return False
        return False

    # ============================================================
    # MESSAGE FORMATTING (shared logic)
    # ============================================================

    def format_messages(
        self,
        prompt_or_messages: Union[str, List[Dict[str, str]]],
        system_prompt: str = "You are a helpful assistant."
    ) -> List[Dict[str, str]]:
        """
        Normalize input to messages format.

        Args:
            prompt_or_messages: Either a prompt string or messages list
            system_prompt: System prompt to use if input is a string

        Returns:
            Messages list in OpenAI format
        """
        if isinstance(prompt_or_messages, str):
            return [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_or_messages}
            ]
        return prompt_or_messages

    # ============================================================
    # ABSTRACT METHODS (to be implemented by subclasses)
    # ============================================================

    @abstractmethod
    async def invoke(
        self,
        messages: List[Dict[str, str]],
        model: str,
        tools: Optional[List[Dict]] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncGenerator[str, None]]:
        """
        Main entry point for LLM calls.

        Args:
            messages: Messages in OpenAI format
            model: Model identifier
            tools: Optional tool schemas for function calling
            stream: If True, return async generator of tokens
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            If stream=False: Response dict
            If stream=True: Async generator yielding tokens
        """
        pass

    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether this handler supports streaming."""
        pass


# ============================================================
# UTILITY FUNCTIONS (importable by both handlers)
# ============================================================

def create_error_response(error: str, model: str = "unknown") -> Dict[str, Any]:
    """Create standardized error response."""
    return {
        "message": {"content": f"[ERROR] {error}", "role": "assistant"},
        "model": model,
        "provider": "error",
        "error": True
    }


def extract_content(response: Dict[str, Any]) -> str:
    """Extract text content from response dict."""
    message = response.get("message", {})
    if isinstance(message, dict):
        return message.get("content", "")
    return str(message)
