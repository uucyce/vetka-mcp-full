# file: src/elisya/key_roaming_handler.py
"""
Phase 102.3: Key Roaming Logic Implementation
============================================
Implements key roaming logic in call_model() to rotate through multiple API keys 
when rate limited or unavailable before falling back.

This module provides a robust key rotation mechanism that:
1. Attempts API calls with available keys
2. Rotates keys on rate limiting or authentication errors
3. Implements exponential backoff for rate-limited keys
4. Falls back gracefully when all keys are exhausted
"""

import asyncio
import time
import logging
from typing import List, Optional, Dict, Any, Callable, Awaitable
from src.utils.unified_key_manager import get_key_manager, ProviderType
from src.elisya.provider_registry import Provider, BaseProvider

logger = logging.getLogger(__name__)

class KeyRoamingHandler:
    """Handles key roaming logic for API calls with automatic rotation"""
    
    def __init__(self, provider: Provider):
        self.provider = provider
        self.key_manager = get_key_manager()
        self.max_retries = 3
        self.base_delay = 1.0
    
    async def call_model_with_roaming(
        self,
        call_function: Callable[..., Awaitable[Dict[str, Any]]],
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute API call with key roaming logic.
        
        Args:
            call_function: The actual API call function to execute
            *args: Positional arguments for the API call
            **kwargs: Keyword arguments for the API call
            
        Returns:
            Dict containing the API response
            
        Raises:
            Exception: If all keys are exhausted or other unrecoverable errors occur
        """
        # Get all available keys for this provider
        provider_type = self._get_provider_type()
        all_keys = self.key_manager.keys.get(provider_type, [])
        available_keys = [k for k in all_keys if k.is_available()]
        
        if not available_keys:
            raise ValueError(f"No available keys for provider {self.provider}")
        
        # Try each key with exponential backoff
        for attempt in range(len(available_keys)):
            try:
                # Get current key
                current_key = self.key_manager.get_key(provider_type)
                if not current_key:
                    raise ValueError(f"No active key available for {self.provider}")
                
                # Set the API key in kwargs
                kwargs_with_key = {**kwargs, 'api_key': current_key.key}
                
                # Execute the API call
                result = await call_function(*args, **kwargs_with_key)
                return result
                
            except Exception as e:
                # Check if error indicates key exhaustion or rate limiting
                should_rotate = self._should_rotate_key(e)
                
                if should_rotate and attempt < len(available_keys) - 1:
                    # Rotate key and retry
                    logger.info(f"[{self.provider}] Rotating key after error: {str(e)}")
                    self._rotate_key(current_key, e)
                    # Exponential backoff before next attempt
                    delay = self.base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    # No more keys to try or non-retryable error
                    logger.error(f"[{self.provider}] All keys exhausted or unretryable error: {str(e)}")
                    raise
        
        raise Exception(f"[{self.provider}] Failed to complete call after trying all available keys")
    
    def _get_provider_type(self) -> ProviderType:
        """Map Provider enum to ProviderType for key manager"""
        mapping = {
            Provider.OPENAI: ProviderType.OPENAI,
            Provider.ANTHROPIC: ProviderType.ANTHROPIC,
            Provider.GOOGLE: ProviderType.GOOGLE,
            Provider.GEMINI: ProviderType.GOOGLE,
            Provider.OLLAMA: ProviderType.OLLAMA,
            Provider.OPENROUTER: ProviderType.OPENROUTER,
            Provider.XAI: ProviderType.XAI,
            Provider.POE: ProviderType.POE,
            Provider.POLZA: ProviderType.POLZA,
            Provider.MISTRAL: ProviderType.MISTRAL,
            Provider.PERPLEXITY: ProviderType.PERPLEXITY,
            Provider.NANOGPT: ProviderType.NANOGPT,
            Provider.TAVILY: ProviderType.TAVILY,
        }
        return mapping.get(self.provider, ProviderType.OPENAI)
    
    def _should_rotate_key(self, error: Exception) -> bool:
        """Determine if the error indicates we should rotate to another key"""
        # Check for common rate limiting or auth errors
        error_str = str(error).lower()
        
        # HTTP status codes that indicate key issues
        rate_limit_indicators = [
            '429',  # Too Many Requests
            '401',  # Unauthorized
            '403',  # Forbidden
            '402',  # Payment Required
            'rate limit',
            'quota exceeded',
            'access denied',
            'invalid api key',
            'authentication failed'
        ]
        
        return any(indicator in error_str for indicator in rate_limit_indicators)
    
    def _rotate_key(self, current_key: Any, error: Exception):
        """Rotate the current key based on the error type"""
        error_str = str(error).lower()
        
        # Determine if we should apply cooldown
        mark_cooldown = any(code in error_str for code in ['402', '429', 'quota', 'rate limit'])
        
        # Report failure to key manager
        self.key_manager.report_failure(
            current_key.key, 
            mark_cooldown=mark_cooldown, 
            auto_rotate=True
        )
        
        logger.info(f"[{self.provider}] Key {current_key.mask()} rotated due to: {str(error)}")

# Convenience function for backward compatibility
async def call_model_with_key_roaming(
    provider: Provider,
    call_function: Callable[..., Awaitable[Dict[str, Any]]],
    *args,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to call model with key roaming logic
    
    Args:
        provider: The provider enum
        call_function: The actual API call function to execute
        *args: Positional arguments for the API call
        **kwargs: Keyword arguments for the API call
        
    Returns:
        Dict containing the API response
    """
    handler = KeyRoamingHandler(provider)
    return await handler.call_model_with_roaming(call_function, *args, **kwargs)