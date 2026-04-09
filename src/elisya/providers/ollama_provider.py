# file: src/elisya/providers/ollama_provider.py
"""
Phase 102.4: Ollama (Hostess) local model fallback implementation
==================================================================
This provider implements local model fallback using Ollama as the terminal option
in the fallback chain when all provider keys are exhausted.

@file ollama_provider.py
@status active
@phase 102.4
@depends httpx, json, asyncio, logging
@used_by provider_registry.py
"""

import httpx
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any
from src.elisya.provider_registry import BaseProvider, ProviderConfig

logger = logging.getLogger(__name__)


class OllamaProvider(BaseProvider):
    """Ollama local model provider for terminal fallback"""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        # Default to localhost:11434 if not specified
        self.base_url = config.base_url or "http://localhost:11434"
        self.client = httpx.AsyncClient(timeout=300.0)  # 5 minute timeout for local models

    @property
    def supports_tools(self) -> bool:
        # Ollama has limited tool support, returning False for safety
        return False

    @property
    def name(self) -> str:
        return "Ollama"

    async def call(
        self,
        messages: List[Dict[str, str]],
        model: str,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Call Ollama local model as terminal fallback option.
        
        Args:
            messages: List of message dictionaries
            model: Model name to use (e.g., 'llama3', 'mistral')
            tools: Tool definitions (not supported in this implementation)
            **kwargs: Additional parameters
            
        Returns:
            Standardized response dictionary
        """
        try:
            # Prepare the request payload
            payload = {
                "model": model or self.config.default_model or "llama3",
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "top_p": kwargs.get("top_p", 0.9),
                }
            }

            # Add any additional options from kwargs
            if "max_tokens" in kwargs:
                payload["options"]["num_predict"] = kwargs["max_tokens"]

            logger.info(f"[OLLAMA] Calling local model {payload['model']}")

            # Make the API call to Ollama
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            response.raise_for_status()
            result = response.json()

            # Extract the response content
            content = ""
            if "message" in result and "content" in result["message"]:
                content = result["message"]["content"]
            elif "response" in result:
                content = result["response"]

            # Return standardized response format
            return {
                "message": {
                    "content": content,
                    "tool_calls": None  # Tools not supported
                },
                "model": payload["model"],
                "provider": "ollama",
                "usage": {
                    "prompt_tokens": 0,  # Ollama doesn't always provide token counts
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"[OLLAMA] HTTP error {e.response.status_code}: {e.response.text}")
            raise Exception(f"Ollama API error: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"[OLLAMA] Request error: {str(e)}")
            raise Exception(f"Ollama request failed: {str(e)}")
        except Exception as e:
            logger.error(f"[OLLAMA] Unexpected error: {str(e)}")
            raise Exception(f"Ollama call failed: {str(e)}")

    async def list_models(self) -> List[str]:
        """
        List available models in Ollama.
        
        Returns:
            List of model names
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            logger.error(f"[OLLAMA] Failed to list models: {str(e)}")
            return []

    async def pull_model(self, model_name: str) -> bool:
        """
        Pull a model from Ollama library.
        
        Args:
            model_name: Name of the model to pull
            
        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {"name": model_name}
            response = await self.client.post(
                f"{self.base_url}/api/pull",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"[OLLAMA] Failed to pull model {model_name}: {str(e)}")
            return False