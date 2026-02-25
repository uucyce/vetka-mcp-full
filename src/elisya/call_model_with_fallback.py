# file: src/elisya/call_model_with_fallback.py
"""
Phase 102.2: Key Roaming Detection with Immediate Ollama Fallback
==================================================================
Implements enhanced call_model function with key roaming detection that 
immediately falls back to local Ollama endpoint when primary providers 
return unavailable status.
"""

import asyncio
import logging
import base64
import os
from typing import Dict, Any, Optional, Callable, Awaitable
from src.elisya.provider_registry import Provider
from src.elisya.key_roaming_handler import call_model_with_key_roaming
from src.elisya.api_aggregator_v3 import HOST_HAS_OLLAMA, OLLAMA_DEFAULT_MODEL
import ollama

logger = logging.getLogger(__name__)

async def call_model(
    provider: Provider,
    prompt: str,
    model: Optional[str] = None,
    images: Optional[list] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Enhanced call_model function with key roaming detection and immediate Ollama fallback.
    
    When primary model returns unavailable status after key roaming attempt,
    trigger immediate fallback to local Hostess (Ollama) endpoint before 
    attempting other providers.
    
    Args:
        provider: The API provider to use
        prompt: The prompt to send to the model
        model: Specific model to use (optional)
        images: List of images for multimodal models (optional)
        **kwargs: Additional parameters for the API call
        
    Returns:
        Dict containing the API response with keys: response, model, tokens, cost
    """
    # MARKER_102_2_START
    # First, try the primary provider with key roaming
    try:
        # Import the actual API call function for this provider
        call_function = _get_provider_call_function(provider)
        if not call_function:
            raise ValueError(f"No call function available for provider {provider}")
            
        # Execute with key roaming
        result = await call_model_with_key_roaming(
            provider,
            call_function,
            prompt=prompt,
            model=model,
            images=images,
            **kwargs
        )
        return result
        
    except Exception as primary_error:
        # Check if this is an "unavailable" status that indicates key roaming failed
        if _is_unavailable_status(primary_error):
            logger.info(f"[{provider}] Primary provider unavailable after key roaming, falling back to Ollama")
            
            # Immediately try Ollama as fallback before other providers
            ollama_result = await _try_ollama_fallback(prompt, model, images, **kwargs)
            if ollama_result:
                return ollama_result
        
        # If Ollama fallback failed or wasn't triggered, re-raise the original error
        # This will trigger the normal fallback chain in the calling function
        raise primary_error
    # MARKER_102_2_END

def _get_provider_call_function(provider: Provider) -> Optional[Callable[..., Awaitable[Dict[str, Any]]]]:
    """Get the actual API call function for a provider."""
    # This would import and return the specific call function for each provider
    # For example:
    if provider == Provider.OPENAI:
        try:
            from src.elisya.providers.openai_client import call_openai
            return call_openai
        except ImportError:
            return None
    elif provider == Provider.ANTHROPIC:
        try:
            from src.elisya.providers.anthropic_client import call_anthropic
            return call_anthropic
        except ImportError:
            return None
    elif provider == Provider.OPENROUTER:
        try:
            from src.elisya.providers.openrouter_client import call_openrouter
            return call_openrouter
        except ImportError:
            return None
    # Add other providers as needed
    
    return None

def _is_unavailable_status(error: Exception) -> bool:
    """
    Determine if the error indicates an unavailable status that should trigger
    immediate Ollama fallback.
    """
    error_str = str(error).lower()
    
    # Common indicators of unavailable status
    unavailable_indicators = [
        'unavailable',
        'rate limit',
        'quota exceeded',
        'service unavailable',
        'temporarily unavailable',
        '503',
        '504',
        'timeout',
        'connection refused',
        'no healthy upstream'
    ]
    
    return any(indicator in error_str for indicator in unavailable_indicators)

async def _try_ollama_fallback(
    prompt: str, 
    model: Optional[str] = None, 
    images: Optional[list] = None, 
    **kwargs
) -> Optional[Dict[str, Any]]:
    """
    Try to call the local Ollama endpoint as immediate fallback.
    
    Returns:
        Dict with response or None if Ollama is not available
    """
    # Check if Ollama is available
    if not HOST_HAS_OLLAMA:
        logger.warning("Ollama not available for fallback")
        return None
    
    try:
        # Use the default model if none specified
        ollama_model = model or OLLAMA_DEFAULT_MODEL
        
        # Prepare the content for Ollama
        content = prompt
        
        # Handle images if provided (for multimodal models)
        if images:
            # Ollama expects base64 encoded images
            image_data = []
            for image in images:
                if isinstance(image, str):
                    # If it's a file path, read and encode it
                    if os.path.exists(image):
                        with open(image, "rb") as f:
                            encoded = base64.b64encode(f.read()).decode('utf-8')
                            image_data.append(encoded)
                    # If it's already base64 data, use it as is
                    elif image.startswith('data:image'):
                        # Extract base64 data from data URL
                        if 'base64,' in image:
                            encoded = image.split('base64,')[1]
                            image_data.append(encoded)
                        else:
                            image_data.append(image)
                    else:
                        # Assume it's already base64 encoded
                        image_data.append(image)
            
            # Create message content with images
            content = [{"type": "text", "text": prompt}]
            for img_data in image_data:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img_data}"
                    }
                })
        
        # Prepare the messages for Ollama
        messages = [{"role": "user", "content": content}]
        
        # Prepare options from kwargs
        options = {}
        # Forward relevant parameters to Ollama
        if 'temperature' in kwargs:
            options['temperature'] = kwargs['temperature']
        if 'top_p' in kwargs:
            options['top_p'] = kwargs['top_p']
        if 'top_k' in kwargs:
            options['top_k'] = kwargs['top_k']
        if 'repeat_penalty' in kwargs:
            options['repeat_penalty'] = kwargs['repeat_penalty']
        if 'seed' in kwargs:
            options['seed'] = kwargs['seed']
        
        # Call Ollama with proper error handling
        try:
            response = ollama.chat(
                model=ollama_model,
                messages=messages,
                options=options if options else None
            )
        except Exception as ollama_error:
            logger.error(f"Ollama API call failed: {ollama_error}")
            return None
        
        # Format response to match expected structure
        return {
            "response": response["message"]["content"],
            "model": ollama_model,
            "tokens": response.get("prompt_eval_count", 0) + response.get("eval_count", 0),
            "cost": 0.0  # Ollama is free
        }
        
    except Exception as e:
        logger.error(f"Ollama fallback failed: {e}")
        return None