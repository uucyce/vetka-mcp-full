# file: src/orchestration/model_fallback_handler.py

import yaml
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

# MARKER_102_3_START
class ModelFallbackHandler:
    """
    Handles fallback cascade for AI model providers.
    If Ollama/Hostess call fails or returns unavailable, 
    proceeds to try other provider keys in sequence as defined 
    in litellm_config.yaml fallback_order.
    """
    
    def __init__(self, config_path: str = "cnfg/litellm_config.yaml"):
        self.config_path = config_path
        self.fallback_order: List[str] = []
        self.provider_configs: Dict[str, Any] = {}
        self._load_config()
        
    def _load_config(self) -> None:
        """Load LiteLLM configuration and fallback order."""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                    self.fallback_order = config.get('fallback_order', [])
                    self.provider_configs = config.get('providers', {})
            else:
                logging.warning(f"Config file not found: {self.config_path}")
                # Default fallback order if config doesn't exist
                self.fallback_order = ['ollama', 'openai', 'anthropic', 'cohere']
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            self.fallback_order = ['ollama', 'openai', 'anthropic', 'cohere']
    
    def get_fallback_providers(self, failed_provider: str) -> List[str]:
        """
        Get list of fallback providers after the failed one.
        
        Args:
            failed_provider: The provider that failed
            
        Returns:
            List of provider keys in fallback order
        """
        if failed_provider in self.fallback_order:
            failed_index = self.fallback_order.index(failed_provider)
            return self.fallback_order[failed_index + 1:]
        return self.fallback_order[:]
    
    def attempt_fallback_cascade(self, initial_provider: str, attempt_func, *args, **kwargs) -> Optional[Any]:
        """
        Attempt to call providers in fallback order until one succeeds.
        
        Args:
            initial_provider: The provider to try first
            attempt_func: Function to call with provider as first argument
            *args: Additional arguments for attempt_func
            **kwargs: Additional keyword arguments for attempt_func
            
        Returns:
            Result from first successful provider, or None if all fail
        """
        providers_to_try = [initial_provider] + self.get_fallback_providers(initial_provider)
        
        for provider in providers_to_try:
            try:
                logging.info(f"Attempting provider: {provider}")
                result = attempt_func(provider, *args, **kwargs)
                
                # Check if result indicates unavailability
                if self._is_provider_unavailable(result):
                    logging.warning(f"Provider {provider} unavailable, trying next fallback")
                    continue
                    
                logging.info(f"Successfully got result from provider: {provider}")
                return result
            except Exception as e:
                logging.warning(f"Provider {provider} failed with error: {e}")
                continue
                
        logging.error("All providers in fallback chain failed")
        return None
    
    def _is_provider_unavailable(self, result: Any) -> bool:
        """
        Check if provider response indicates unavailability.
        
        Args:
            result: Provider response
            
        Returns:
            True if provider is unavailable, False otherwise
        """
        if result is None:
            return True
            
        # Check for common unavailability indicators
        if isinstance(result, dict):
            status = result.get('status', '').lower()
            if status in ['unavailable', 'error', 'failed']:
                return True
                
            # Check for specific error messages
            error_msg = str(result.get('error', '')).lower()
            unavailable_indicators = [
                'unavailable', 'timeout', 'quota', 'limit', 
                'access denied', 'not found', 'invalid key'
            ]
            for indicator in unavailable_indicators:
                if indicator in error_msg:
                    return True
                    
        return False

# MARKER_102_3_END