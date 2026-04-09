# file: src/api/litellm_client.py

import os
import logging
from typing import Dict, Any, Optional
import litellm
from litellm import completion

# Configure logging
logger = logging.getLogger(__name__)

class LiteLLMClient:
    """Unified LiteLLM client for all model providers"""
    
    def __init__(self):
        """Initialize LiteLLM client with environment configuration"""
        # Set up LiteLLM with environment variables
        litellm.set_verbose = os.getenv("LITELLM_DEBUG", "false").lower() == "true"
        
        # Set up API keys from environment variables
        if os.getenv("OPENAI_API_KEY"):
            litellm.api_key = os.getenv("OPENAI_API_KEY")
            
        if os.getenv("ANTHROPIC_API_KEY"):
            litellm.api_key = os.getenv("ANTHROPIC_API_KEY")
            
        # Add any other provider keys as needed
        
    async def call_model(
        self, 
        model: str, 
        messages: list, 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Unified API call to any supported model through LiteLLM proxy
        
        Args:
            model: Model identifier (e.g., 'gpt-4', 'claude-2', 'llama2')
            messages: List of message dictionaries
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters for the model
            
        Returns:
            Dict containing the model response and metadata
        """
        try:
            logger.info(f"Calling model: {model} with {len(messages)} messages")
            
            # Prepare the request parameters
            request_params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                **kwargs
            }
            
            # Add max_tokens if specified
            if max_tokens:
                request_params["max_tokens"] = max_tokens
                
            # Make the API call through LiteLLM
            response = await completion(**request_params)
            
            # Extract relevant information from the response
            result = {
                "model": model,
                "choices": [
                    {
                        "message": choice.message.dict() if hasattr(choice.message, 'dict') else choice.message,
                        "finish_reason": choice.finish_reason
                    } 
                    for choice in response.choices
                ],
                "usage": response.usage.dict() if hasattr(response.usage, 'dict') else response.usage,
                "response_time": getattr(response, '_response_ms', None)
            }
            
            logger.info(f"Successfully received response from {model}")
            return result
            
        except Exception as e:
            logger.error(f"Error calling model {model}: {str(e)}")
            raise
            
# Global instance
litellm_client = LiteLLMClient()