"""
Phase 80.10: Provider Registry Architecture
===========================================
Clean separation: Orchestrator selects provider. call_model only executes.

@file provider_registry.py
@status active
@phase 96
@depends os, asyncio, time, json, httpx, abc, enum, dataclasses, collections, logging
@used_by orchestrator_with_elisya.py, llm_call_tool.py, user_message_handler.py, chat_handler.py, open_router_bridge.py

Based on ChatGPT architectural recommendation:
- ProviderRegistry: singleton registry for all providers
- BaseProvider: abstract interface with supports_tools flag
- Provider implementations: OpenAI, Anthropic, Google, Ollama, OpenRouter, XAI
"""

import os
import asyncio
import time
import json
import httpx
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncGenerator
from enum import Enum
from dataclasses import dataclass
from collections import deque

import logging

logger = logging.getLogger(__name__)


# Phase 80.39: Custom exception for xai key exhaustion
class XaiKeysExhausted(Exception):
    """Raised when all xai keys return 403 - signals to use OpenRouter fallback"""

    pass


class Provider(Enum):
    """Supported providers"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"  # Note: config.json uses "gemini" key, APIKeyService maps google->gemini
    GEMINI = "gemini"  # Phase 80.41: Added for config.json compatibility
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    XAI = "xai"  # Phase 80.35: x.ai (Grok models)


@dataclass
class ProviderConfig:
    """Configuration for a provider"""

    api_key: Optional[str] = None
    base_url: Optional[str] = None
    default_model: Optional[str] = None


class BaseProvider(ABC):
    """
    Abstract base class for all LLM providers.
    Each provider implements its own call() method with native tool support.
    """

    def __init__(self, config: ProviderConfig):
        self.config = config

    @property
    @abstractmethod
    def supports_tools(self) -> bool:
        """Whether this provider supports native function calling"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging"""
        pass

    @abstractmethod
    async def call(
        self,
        messages: List[Dict[str, str]],
        model: str,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Call the LLM with given messages.

        Returns standardized response:
        {
            "message": {"content": str, "tool_calls": Optional[List]},
            "model": str,
            "provider": str,
            "usage": Optional[Dict]
        }
        """
        pass


class OpenAIProvider(BaseProvider):
    """OpenAI API provider (GPT models)"""

    @property
    def supports_tools(self) -> bool:
        return True

    @property
    def name(self) -> str:
        return "OpenAI"

    async def call(
        self,
        messages: List[Dict[str, str]],
        model: str,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Phase 93.4: Added auto-rotation on 401/402/403 errors with 24h cooldown.
        Phase 93.5: Added diagnostic logging for MCP 429 issues.
        """
        from src.utils.unified_key_manager import get_key_manager, ProviderType
        import httpx

        start_time = time.time()
        km = get_key_manager()

        # Get all OpenAI keys
        openai_keys = km.keys.get(ProviderType.OPENAI, [])
        available_keys = [k for k in openai_keys if k.is_available()]
        max_retries = len(available_keys)  # MARKER_94.1: Use all available keys

        # MARKER_93.5: Diagnostic logging for MCP 429 debugging
        print(f"[OPENAI] Key status before call: {len(openai_keys)} total, {len(available_keys)} available")
        for i, key in enumerate(openai_keys):
            cooldown = key.cooldown_remaining()
            cooldown_str = f", cooldown: {cooldown}" if cooldown else ""
            print(f"[OPENAI]   Key {i}: {key.mask()} - available: {key.is_available()}{cooldown_str}")

        if max_retries == 0:
            raise ValueError(f"No active OpenAI API keys available ({len(openai_keys)} total, all rate-limited)")

        # Clean model name (remove openai/ prefix if present)
        clean_model = model.replace("openai/", "")
        last_error = None

        for attempt in range(max_retries):
            # Get active key
            api_key = km.get_active_key(ProviderType.OPENAI)
            if not api_key:
                raise ValueError("OpenAI API key not found")

            print(f"[OPENAI] Calling {clean_model} (key: ****{api_key[-4:]}, attempt {attempt + 1}/{max_retries})")

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": clean_model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
            }

            if tools:
                # Convert to OpenAI tool format
                payload["tools"] = [
                    {"type": "function", "function": t} if "type" not in t else t
                    for t in tools
                ]

            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=payload,
                    )

                    # Phase 93.4: Handle auth/payment errors with key rotation + 24h cooldown
                    if response.status_code in (401, 402, 403, 429):
                        print(f"[OPENAI] Key failed ({response.status_code}), marking rate-limited (24h)...")
                        for record in openai_keys:
                            if record.key == api_key:
                                record.mark_rate_limited()
                                print(f"[OPENAI] Key {record.mask()} marked rate-limited")
                                break
                        last_error = f"Key error {response.status_code}"
                        continue

                    response.raise_for_status()
                    data = response.json()
                    break  # Success!

            except httpx.HTTPStatusError as e:
                if e.response.status_code in (401, 402, 403, 429):
                    print(f"[OPENAI] Key failed ({e.response.status_code}), rotating...")
                    for record in openai_keys:
                        if record.key == api_key:
                            record.mark_rate_limited()
                            break
                    last_error = e
                    continue
                raise
        else:
            raise ValueError(f"All OpenAI keys exhausted after {max_retries} attempts. Last error: {last_error}")

        duration = time.time() - start_time
        print(f"[OPENAI] ✅ Completed in {duration:.1f}s")

        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})

        return {
            "message": {
                "content": message.get("content", ""),
                "tool_calls": message.get("tool_calls"),
                "role": message.get("role", "assistant"),
            },
            "model": clean_model,
            "provider": "openai",
            "usage": data.get("usage"),
        }


class AnthropicProvider(BaseProvider):
    """Anthropic API provider (Claude models)"""

    @property
    def supports_tools(self) -> bool:
        return True

    @property
    def name(self) -> str:
        return "Anthropic"

    async def call(
        self,
        messages: List[Dict[str, str]],
        model: str,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Phase 93.4: Added auto-rotation on 401/402/403/429 errors with 24h cooldown.
        """
        from src.utils.unified_key_manager import get_key_manager, ProviderType
        import httpx

        start_time = time.time()
        km = get_key_manager()

        # Get all Anthropic keys
        anthropic_keys = km.keys.get(ProviderType.ANTHROPIC, [])
        max_retries = len([k for k in anthropic_keys if k.is_available()])  # MARKER_94.1: Use all keys

        if max_retries == 0:
            raise ValueError("No active Anthropic API keys available")

        # Clean model name
        clean_model = model.replace("anthropic/", "")
        last_error = None

        for attempt in range(max_retries):
            api_key = km.get_active_key(ProviderType.ANTHROPIC)
            if not api_key:
                raise ValueError("Anthropic API key not found")

            print(f"[ANTHROPIC] Calling {clean_model} (key: ****{api_key[-4:]}, attempt {attempt + 1}/{max_retries})")

            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            }

            # Convert messages format (Anthropic uses different format)
            system_content = ""
            anthropic_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_content = msg["content"]
                else:
                    anthropic_messages.append(
                        {"role": msg["role"], "content": msg["content"]}
                    )

            payload = {
                "model": clean_model,
                "max_tokens": kwargs.get("max_tokens", 4096),
                "messages": anthropic_messages,
            }

            if system_content:
                payload["system"] = system_content

            if tools:
                # Convert to Anthropic tool format
                payload["tools"] = [
                    {
                        "name": t.get("name"),
                        "description": t.get("description", ""),
                        "input_schema": t.get("parameters", t.get("input_schema", {})),
                    }
                    for t in tools
                ]

            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        "https://api.anthropic.com/v1/messages", headers=headers, json=payload
                    )

                    # Phase 93.4: Handle auth/rate errors with key rotation + 24h cooldown
                    if response.status_code in (401, 402, 403, 429):
                        print(f"[ANTHROPIC] Key failed ({response.status_code}), marking rate-limited (24h)...")
                        for record in anthropic_keys:
                            if record.key == api_key:
                                record.mark_rate_limited()
                                print(f"[ANTHROPIC] Key {record.mask()} marked rate-limited")
                                break
                        last_error = f"Key error {response.status_code}"
                        continue

                    response.raise_for_status()
                    data = response.json()
                    break  # Success!

            except httpx.HTTPStatusError as e:
                if e.response.status_code in (401, 402, 403, 429):
                    print(f"[ANTHROPIC] Key failed ({e.response.status_code}), rotating...")
                    for record in anthropic_keys:
                        if record.key == api_key:
                            record.mark_rate_limited()
                            break
                    last_error = e
                    continue
                raise
        else:
            raise ValueError(f"All Anthropic keys exhausted after {max_retries} attempts. Last error: {last_error}")

        duration = time.time() - start_time
        print(f"[ANTHROPIC] ✅ Completed in {duration:.1f}s")

        # Extract content from Anthropic response
        content_blocks = data.get("content", [])
        text_content = ""
        tool_calls = []

        for block in content_blocks:
            if block.get("type") == "text":
                text_content += block.get("text", "")
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    {
                        "id": block.get("id"),
                        "type": "function",
                        "function": {
                            "name": block.get("name"),
                            "arguments": json.dumps(block.get("input", {})),
                        },
                    }
                )

        return {
            "message": {
                "content": text_content,
                "tool_calls": tool_calls if tool_calls else None,
                "role": "assistant",
            },
            "model": clean_model,
            "provider": "anthropic",
            "usage": data.get("usage"),
        }


class GoogleProvider(BaseProvider):
    """Google Gemini API provider"""

    @property
    def supports_tools(self) -> bool:
        return True

    @property
    def name(self) -> str:
        return "Google"

    async def call(
        self,
        messages: List[Dict[str, str]],
        model: str,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Phase 93.4: Added auto-rotation on 401/403/429 errors with 24h cooldown.
        """
        from src.utils.unified_key_manager import get_key_manager, ProviderType
        import httpx

        start_time = time.time()
        km = get_key_manager()

        # Get all Gemini keys (stored as GEMINI in config)
        gemini_keys = km.keys.get(ProviderType.GEMINI, [])
        max_retries = len([k for k in gemini_keys if k.is_available()])  # MARKER_94.1: Use all keys

        if max_retries == 0:
            raise ValueError("No active Google/Gemini API keys available")

        # Clean model name
        clean_model = model.replace("google/", "")
        last_error = None

        for attempt in range(max_retries):
            api_key = km.get_active_key(ProviderType.GEMINI)
            if not api_key:
                raise ValueError("Google API key not found")

            print(f"[GOOGLE] Calling {clean_model} (key: ****{api_key[-4:]}, attempt {attempt + 1}/{max_retries})")

            # Convert messages to Gemini format
            gemini_contents = []
            system_instruction = None

            for msg in messages:
                if msg["role"] == "system":
                    system_instruction = msg["content"]
                else:
                    role = "user" if msg["role"] == "user" else "model"
                    gemini_contents.append(
                        {"role": role, "parts": [{"text": msg["content"]}]}
                    )

            payload = {
                "contents": gemini_contents,
                "generationConfig": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "maxOutputTokens": kwargs.get("max_tokens", 4096),
                },
            }

            if system_instruction:
                payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

            if tools:
                # Convert to Gemini tool format
                function_declarations = []
                for t in tools:
                    function_declarations.append(
                        {
                            "name": t.get("name"),
                            "description": t.get("description", ""),
                            "parameters": t.get("parameters", {}),
                        }
                    )
                payload["tools"] = [{"functionDeclarations": function_declarations}]

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={api_key}"

            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(url, json=payload)

                    # Phase 93.4: Handle auth/rate errors with key rotation + 24h cooldown
                    if response.status_code in (401, 403, 429):
                        print(f"[GOOGLE] Key failed ({response.status_code}), marking rate-limited (24h)...")
                        for record in gemini_keys:
                            if record.key == api_key:
                                record.mark_rate_limited()
                                print(f"[GOOGLE] Key {record.mask()} marked rate-limited")
                                break
                        last_error = f"Key error {response.status_code}"
                        continue

                    response.raise_for_status()
                    data = response.json()
                    break  # Success!

            except httpx.HTTPStatusError as e:
                if e.response.status_code in (401, 403, 429):
                    print(f"[GOOGLE] Key failed ({e.response.status_code}), rotating...")
                    for record in gemini_keys:
                        if record.key == api_key:
                            record.mark_rate_limited()
                            break
                    last_error = e
                    continue
                raise
        else:
            raise ValueError(f"All Google keys exhausted after {max_retries} attempts. Last error: {last_error}")

        duration = time.time() - start_time
        print(f"[GOOGLE] ✅ Completed in {duration:.1f}s")

        # Extract content
        candidates = data.get("candidates", [{}])
        content = candidates[0].get("content", {}) if candidates else {}
        parts = content.get("parts", [])

        text_content = ""
        tool_calls = []

        for part in parts:
            if "text" in part:
                text_content += part["text"]
            elif "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append(
                    {
                        "id": f"call_{len(tool_calls)}",
                        "type": "function",
                        "function": {
                            "name": fc.get("name"),
                            "arguments": json.dumps(fc.get("args", {})),
                        },
                    }
                )

        return {
            "message": {
                "content": text_content,
                "tool_calls": tool_calls if tool_calls else None,
                "role": "assistant",
            },
            "model": clean_model,
            "provider": "google",
            "usage": data.get("usageMetadata"),
        }


class OllamaProvider(BaseProvider):
    """Local Ollama provider"""

    # Phase 80.5: Models that do NOT support tool calling
    # These models will fail with "does not support tools (status code: 400)"
    MODELS_WITHOUT_TOOLS = {
        "deepseek-llm",  # Deepseek 7B lightweight
        "llama2",  # Legacy Llama 2
        "codellama",  # CodeLlama base
        "mistral",  # Mistral 7B base (newer versions support tools)
        "phi",  # Microsoft Phi models
        "gemma",  # Google Gemma base
        "orca-mini",  # Orca lightweight
        "vicuna",  # Vicuna base
    }

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.host = config.base_url or os.getenv(
            "OLLAMA_HOST", "http://localhost:11434"
        )
        self._available_models: List[str] = []
        self._default_model = "deepseek-llm:7b"
        self._health_checked = False

    @property
    def supports_tools(self) -> bool:
        return True  # Ollama supports tools

    @property
    def name(self) -> str:
        return "Ollama"

    def _check_health(self):
        """Check Ollama availability and get models"""
        if self._health_checked:
            return

        try:
            import requests

            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                self._available_models = [m["name"] for m in data.get("models", [])]
                if (
                    self._available_models
                    and self._default_model not in self._available_models
                ):
                    self._default_model = self._available_models[0]
                print(f"[OLLAMA] Health check: {len(self._available_models)} models")
        except Exception as e:
            print(f"[OLLAMA] Health check failed: {e}")

        self._health_checked = True

    def _model_supports_tools(self, model_name: str) -> bool:
        """
        Phase 80.5: Check if model supports tool calling.

        Args:
            model_name: Model identifier (e.g., 'deepseek-llm:7b')

        Returns:
            True if model supports tools, False otherwise
        """
        # Extract base model name (remove tag)
        base_name = model_name.split(":")[0].lower()

        # Check against blacklist
        for unsupported in self.MODELS_WITHOUT_TOOLS:
            if unsupported in base_name:
                return False

        return True

    async def call(
        self,
        messages: List[Dict[str, str]],
        model: str,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        import ollama

        start_time = time.time()
        self._check_health()

        # Clean model name
        clean_model = model.replace("ollama/", "")

        # Validate model exists
        if self._available_models and clean_model not in self._available_models:
            print(
                f"[OLLAMA] Model {clean_model} not found, using {self._default_model}"
            )
            clean_model = self._default_model

        # Phase 80.5: Check if model supports tools
        model_has_tools = self._model_supports_tools(clean_model)
        effective_tools = tools if (tools and model_has_tools) else None

        if tools and not model_has_tools:
            print(
                f"[OLLAMA] ⚠️  {clean_model} does not support tools - calling without tools"
            )

        print(
            f"[OLLAMA] Calling {clean_model} (tools: {len(effective_tools) if effective_tools else 0})"
        )

        params = {"model": clean_model, "messages": messages, "stream": False}

        if effective_tools:
            params["tools"] = effective_tools

        # Run sync ollama.chat in thread pool
        # MARKER_105_OLLAMA_TIMEOUT_FIX: Add timeout to prevent server hangs
        loop = asyncio.get_event_loop()
        OLLAMA_TIMEOUT = 60.0  # 60 second timeout for model inference

        try:
            response = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: ollama.chat(**params)),
                timeout=OLLAMA_TIMEOUT
            )
        except asyncio.TimeoutError:
            print(f"[OLLAMA] ⚠️ TIMEOUT after {OLLAMA_TIMEOUT}s - {clean_model} hung!")
            raise TimeoutError(f"Ollama {clean_model} did not respond within {OLLAMA_TIMEOUT}s")
        except Exception as e:
            # Phase 80.5: If tools error, retry without tools
            if "does not support tools" in str(e) and "tools" in params:
                print(
                    f"[OLLAMA] Tool error detected, retrying {clean_model} without tools"
                )
                del params["tools"]
                try:
                    response = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: ollama.chat(**params)),
                        timeout=OLLAMA_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    print(f"[OLLAMA] ⚠️ TIMEOUT on retry after {OLLAMA_TIMEOUT}s")
                    raise TimeoutError(f"Ollama {clean_model} retry timeout")
            else:
                raise

        duration = time.time() - start_time
        print(f"[OLLAMA] ✅ Completed in {duration:.1f}s")

        # Standardize response
        message = response.get("message", {})

        return {
            "message": {
                "content": message.get("content", ""),
                "tool_calls": message.get("tool_calls"),
                "role": message.get("role", "assistant"),
            },
            "model": clean_model,
            "provider": "ollama",
            "usage": None,
        }


class OpenRouterProvider(BaseProvider):
    """OpenRouter API provider (aggregator)"""

    @property
    def supports_tools(self) -> bool:
        return False  # OpenRouter has limited tool support

    @property
    def name(self) -> str:
        return "OpenRouter"

    async def call(
        self,
        messages: List[Dict[str, str]],
        model: str,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Phase 93.4: Added auto-rotation on 401/402/403 errors.
        Will retry with next key up to 3 times.
        """
        from src.utils.unified_key_manager import get_key_manager
        import httpx

        start_time = time.time()
        km = get_key_manager()
        max_retries = km.get_openrouter_keys_count()  # MARKER_94.1: Use all OR keys

        last_error = None

        for attempt in range(max_retries):
            # Get current key - FIX_95.5: rotate=True to actually use all keys
            api_key = km.get_openrouter_key(rotate=(attempt > 0))
            if not api_key:
                raise ValueError("OpenRouter API key not found")

            print(f"[OPENROUTER] Calling {model} (key: ****{api_key[-4:]}, attempt {attempt + 1}/{max_retries})")

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://vetka.ai",
                "X-Title": "VETKA",
            }

            # MARKER_93.6_MODEL_CLEANUP: Clean model name (remove openrouter/ prefix if present)
            # Phase 93.6: Fix 400 Bad Request in group chat - OpenRouter doesn't accept prefixed models
            clean_model = model.replace("openrouter/", "")

            payload = {
                "model": clean_model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
            }

            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=payload,
                    )

                    # Phase 100.1: Handle auth/payment/rate-limit errors with key rotation
                    if response.status_code in (401, 402, 403, 429):
                        print(f"[OPENROUTER] Key failed ({response.status_code}), rotating...")
                        # Use unified report_failure with auto_rotate
                        km.report_failure(api_key, mark_cooldown=(response.status_code != 429))
                        last_error = f"Key error {response.status_code}"
                        continue

                    response.raise_for_status()
                    data = response.json()
                    break  # Success!

            except httpx.HTTPStatusError as e:
                # Phase 100.1: Handle all key errors with unified rotation
                if e.response.status_code in (401, 402, 403, 429):
                    print(f"[OPENROUTER] Key failed ({e.response.status_code}), rotating...")
                    km.report_failure(api_key, mark_cooldown=(e.response.status_code != 429))
                    last_error = e
                    continue
                raise
        else:
            # All retries exhausted
            raise ValueError(f"All OpenRouter keys exhausted after {max_retries} attempts. Last error: {last_error}")

        duration = time.time() - start_time
        print(f"[OPENROUTER] ✅ Completed in {duration:.1f}s")

        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})

        return {
            "message": {
                "content": message.get("content", ""),
                "tool_calls": None,  # OpenRouter doesn't support tools well
                "role": message.get("role", "assistant"),
            },
            "model": model,
            "provider": "openrouter",
            "usage": data.get("usage"),
        }


class XaiProvider(BaseProvider):
    """Phase 80.35: x.ai API provider (Grok models) - OpenAI-compatible API"""

    @property
    def supports_tools(self) -> bool:
        return True  # x.ai supports function calling

    @property
    def name(self) -> str:
        return "x.ai"

    async def call(
        self,
        messages: List[Dict[str, str]],
        model: str,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        start_time = time.time()

        api_key = self.config.api_key
        if not api_key:
            from src.orchestration.services.api_key_service import APIKeyService

            api_key = APIKeyService().get_key("xai")

        if not api_key:
            raise ValueError("x.ai API key not found")

        # MARKER_94.1_FIX: Strip prefix for x.ai API
        # x.ai API expects "grok-4" not "x-ai/grok-4" or "xai/grok-4"
        clean_model = model.replace("x-ai/", "").replace("xai/", "")
        print(f"[XAI] Calling {clean_model} (from {model})")

        import httpx

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": clean_model,  # Use cleaned model name
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
        }

        # Add tools if provided and model supports them
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.x.ai/v1/chat/completions", headers=headers, json=payload
            )

            # Phase 80.39: Handle 403 with key rotation + OpenRouter fallback
            # Phase 80.40: Fixed bugs - use singleton and correct attribute name
            if response.status_code == 403:
                print(
                    f"[XAI] ⚠️ 403 Forbidden - 24h timestamp limit, trying rotation..."
                )
                from src.utils.unified_key_manager import get_key_manager, ProviderType

                key_manager = get_key_manager()  # Use singleton, not new instance

                # Mark current key as rate-limited (24h cooldown)
                for record in key_manager.keys.get(
                    ProviderType.XAI, []
                ):  # .keys not ._keys
                    if record.key == api_key:
                        record.mark_rate_limited()
                        print(f"[XAI] Key {record.mask()} marked as rate-limited (24h)")
                        break

                # Phase 100.1: Rotate to next key
                key_manager.rotate_to_next(ProviderType.XAI)
                print(f"[XAI] 🔄 Rotated to next key")

                # Try next key
                next_key = key_manager.get_active_key(ProviderType.XAI)
                if next_key and next_key != api_key:
                    print(f"[XAI] 🔄 Retrying with next key...")
                    headers["Authorization"] = f"Bearer {next_key}"
                    response = await client.post(
                        "https://api.x.ai/v1/chat/completions",
                        headers=headers,
                        json=payload,
                    )

                # Phase 80.39: If still 403, fallback to OpenRouter
                if response.status_code == 403:
                    print(
                        f"[XAI] ❌ All xai keys exhausted (403), falling back to OpenRouter..."
                    )
                    # Raise special exception to trigger OpenRouter fallback
                    raise XaiKeysExhausted(
                        f"All xai keys returned 403 - use OpenRouter for x-ai/{model}"
                    )

            response.raise_for_status()
            data = response.json()

        duration = time.time() - start_time
        print(f"[XAI] ✅ Completed in {duration:.1f}s")

        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})

        return {
            "message": {
                "content": message.get("content", ""),
                "tool_calls": message.get("tool_calls"),
                "role": message.get("role", "assistant"),
            },
            "model": model,
            "provider": "xai",
            "usage": data.get("usage"),
        }


class ProviderRegistry:
    """
    Singleton registry for all providers.
    Orchestrator selects provider. Registry only executes.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._providers: Dict[Provider, BaseProvider] = {}
        self._initialized = True

        # Auto-register default providers
        self._register_defaults()

    def _register_defaults(self):
        """Register default providers with empty configs (keys loaded on demand)"""
        google_provider = GoogleProvider(ProviderConfig())
        self.register(Provider.OPENAI, OpenAIProvider(ProviderConfig()))
        self.register(Provider.ANTHROPIC, AnthropicProvider(ProviderConfig()))
        self.register(Provider.GOOGLE, google_provider)
        self.register(
            Provider.GEMINI, google_provider
        )  # Phase 80.41: Alias for GOOGLE (same instance)
        self.register(Provider.OLLAMA, OllamaProvider(ProviderConfig()))
        self.register(Provider.OPENROUTER, OpenRouterProvider(ProviderConfig()))
        self.register(
            Provider.XAI, XaiProvider(ProviderConfig())
        )  # Phase 80.35: x.ai (Grok)
        print(f"[REGISTRY] Initialized with {len(self._providers)} providers")

    def register(self, provider_type: Provider, provider: BaseProvider):
        """Register a provider"""
        self._providers[provider_type] = provider

    def get(self, provider_type: Provider) -> Optional[BaseProvider]:
        """Get a provider by type"""
        return self._providers.get(provider_type)

    def get_by_name(self, name: str) -> Optional[BaseProvider]:
        """Get provider by string name"""
        try:
            provider_type = Provider(name.lower())
            return self.get(provider_type)
        except ValueError:
            return None

    def list_providers(self) -> List[str]:
        """List all registered providers"""
        return [p.value for p in self._providers.keys()]

    @staticmethod
    def detect_provider(model_name: str) -> Provider:
        """
        Detect provider from model name.
        This is a FALLBACK - orchestrator should pass provider explicitly.

        # MARKER_93.10_SIMPLE_ROUTING: No whitelist needed!
        # Phase 93.10: Route by prefix only. Simple, future-proof, no maintenance.
        # If model has "openai/" prefix or starts with "gpt-" -> OpenAI API
        # If model has "anthropic/" prefix or starts with "claude-" -> Anthropic API
        # etc.
        # If API returns 404 for unknown model - that's the API's problem, not routing.
        """
        # MARKER_94.5_PROVIDER_ROUTING: Provider detection logic
        # MARKER_94.8_BUG_ROUTING: CRITICAL FIX - x-ai/ prefix routing bug
        # The bug: x-ai/grok-4 was being routed to XAI direct API instead of OpenRouter
        # Root cause: The old logic treated x-ai/ prefix as "direct xAI API call"
        # Reality: x-ai/ prefix is OpenRouter's way of specifying xAI models
        # OpenRouter model IDs use format: provider/model-name
        # So x-ai/grok-4 means "xAI's grok-4 model via OpenRouter"
        # Direct xAI API models are just: grok-4 (without prefix)
        #
        # Fix strategy:
        # 1. If model starts with "provider/" format where provider is known -> OpenRouter
        # 2. If model is just "grok-4" or "grok-beta" (no prefix) -> XAI direct API
        # 3. Check for direct API format FIRST (no slash at all)
        # 4. Then check for provider-prefixed models (openrouter format)

        model_lower = model_name.lower()

        # Direct API models (NO provider prefix):
        # - grok-4, grok-beta (direct xAI API)
        # - gpt-4, gpt-3.5 (direct OpenAI API, rare but possible)
        # - claude-3 (direct Anthropic API)

        # Check if this is a direct xAI API call (no prefix, starts with grok)
        if model_lower.startswith("grok-") or model_lower == "grok":
            # MARKER_94.8_FIX: Direct xAI API (grok-4, grok-beta, etc. without x-ai/ prefix)
            return Provider.XAI

        # OpenAI: openai/*, gpt-*, o1*, chatgpt-*
        if (model_lower.startswith("openai/") or
            model_lower.startswith("gpt-") or
            model_lower.startswith("o1") or
            model_lower.startswith("chatgpt-")):
            return Provider.OPENAI
        # Anthropic: anthropic/*, claude-*
        elif model_lower.startswith("anthropic/") or model_lower.startswith("claude-"):
            return Provider.ANTHROPIC
        elif model_lower.startswith("google/") or model_lower.startswith("gemini"):
            return Provider.GOOGLE
        # MARKER_94.8_FIX: OpenRouter models with x-ai/ prefix (x-ai/grok-4)
        # These are OpenRouter's representation of xAI models, NOT direct xAI API calls
        elif model_lower.startswith("xai/") or model_lower.startswith("x-ai/"):
            # MARKER_94.8_OPENROUTER_XAI: Models like "x-ai/grok-4" or "xai/grok-4"
            # are OpenRouter models, not direct xAI API
            return Provider.OPENROUTER
        elif ":" in model_name or model_lower.startswith("ollama/"):
            return Provider.OLLAMA
        elif "/" in model_name:
            # Any other provider/model format -> OpenRouter
            return Provider.OPENROUTER
        else:
            return Provider.OLLAMA  # Default to local
        # MARKER_90.1.4.1_END


# Global registry instance - initialize immediately on import
_registry = ProviderRegistry()


def get_registry() -> ProviderRegistry:
    """Get the global registry instance"""
    return _registry


async def call_model_v2(
    messages: List[Dict[str, str]],
    model: str,
    provider: Optional[Provider] = None,
    tools: Optional[List[Dict]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Phase 80.10: New unified call_model with explicit provider.

    Key difference from old call_model:
    - Provider is a FIRST-CLASS parameter
    - No routing logic here - orchestrator decides provider
    - If provider not specified, auto-detect as fallback

    Args:
        messages: List of message dicts with role/content
        model: Model identifier
        provider: Provider enum (OPENAI, ANTHROPIC, etc.)
        tools: Optional list of tool schemas
        **kwargs: Additional params (temperature, max_tokens, etc.)

    Returns:
        Standardized response dict
    """
    registry = get_registry()

    # If provider not specified, auto-detect (fallback)
    if provider is None:
        provider = ProviderRegistry.detect_provider(model)

    # Get provider instance
    provider_instance = registry.get(provider)
    if not provider_instance:
        raise ValueError(
            f"Provider {provider.value} not registered (available: {registry.list_providers()})"
        )

    # Check tool support
    if tools and not provider_instance.supports_tools:
        print(f"[REGISTRY] Warning: {provider.value} doesn't support tools, ignoring")
        tools = None

    # Call provider with fallback to OpenRouter if direct API fails
    try:
        result = await provider_instance.call(messages, model, tools, **kwargs)
        # MARKER_93.11_SUCCESS: Update model status on success
        from src.elisya.model_router_v2 import update_model_status
        update_model_status(model, success=True)
        return result
    except XaiKeysExhausted as e:
        # Phase 80.39: All xai keys got 403, fallback to OpenRouter
        print(
            f"[REGISTRY] XAI keys exhausted (403), using OpenRouter fallback for {model}..."
        )
        openrouter_provider = registry.get(Provider.OPENROUTER)
        if openrouter_provider:
            # Convert model to OpenRouter format: grok-4 -> x-ai/grok-4
            # MARKER-PROVIDER-004-FIX: Remove double x-ai/xai/ prefix
            clean_model = model.replace("xai/", "").replace("x-ai/", "")
            openrouter_model = f"x-ai/{clean_model}"
            result = await openrouter_provider.call(
                messages, openrouter_model, tools, **kwargs
            )
            return result
        raise
    except ValueError as e:
        # API key not found - try OpenRouter as fallback for remote models
        if provider in (
            Provider.OPENAI,
            Provider.ANTHROPIC,
            Provider.GOOGLE,
            Provider.XAI,
        ):
            print(
                f"[REGISTRY] {provider.value} API key not found, trying OpenRouter fallback..."
            )
            openrouter_provider = registry.get(Provider.OPENROUTER)
            if openrouter_provider:
                try:
                    # MARKER-PROVIDER-006-FIX: Convert model for XAI fallback consistency
                    # Convert xai/grok-beta -> x-ai/grok-beta for OpenRouter
                    clean_model = model.replace("xai/", "").replace("x-ai/", "")
                    openrouter_model = (
                        f"x-ai/{clean_model}" if provider == Provider.XAI else model
                    )
                    result = await openrouter_provider.call(
                        messages, openrouter_model, None, **kwargs
                    )
                    return result
                except Exception as fallback_err:
                    print(f"[REGISTRY] OpenRouter fallback also failed: {fallback_err}")
        print(f"[REGISTRY] {provider.value} failed: {e}")
        raise
    except httpx.HTTPStatusError as e:
        # MARKER_93.11_ERROR: Update model status on HTTP error
        from src.elisya.model_router_v2 import update_model_status
        update_model_status(model, success=False, error_code=e.response.status_code)

        # MARKER_93.10_FALLBACK: HTTP errors (401/402/403/404/429) - fallback to OpenRouter
        # Phase 93.10: Added 404 - if direct API doesn't have model, try OpenRouter
        if provider in (
            Provider.OPENAI,
            Provider.ANTHROPIC,
            Provider.GOOGLE,
            Provider.XAI,
        ):
            print(
                f"[REGISTRY] {provider.value} HTTP error ({e.response.status_code}), trying OpenRouter fallback..."
            )
            openrouter_provider = registry.get(Provider.OPENROUTER)
            if openrouter_provider:
                try:
                    # MARKER_93.10: Convert model for OpenRouter - preserve provider prefix
                    # openai/gpt-5.2 -> openai/gpt-5.2 (OpenRouter understands this format)
                    # xai/grok-4 -> x-ai/grok-4 (OpenRouter uses x-ai/ not xai/)
                    if provider == Provider.XAI:
                        clean_model = model.replace("xai/", "").replace("x-ai/", "")
                        openrouter_model = f"x-ai/{clean_model}"
                    else:
                        openrouter_model = model  # Keep as-is for openai/, anthropic/, etc.

                    print(f"[REGISTRY] OpenRouter fallback: {model} -> {openrouter_model}")
                    result = await openrouter_provider.call(
                        messages, openrouter_model, None, **kwargs
                    )
                    return result
                except Exception as fallback_err:
                    print(f"[REGISTRY] OpenRouter fallback also failed: {fallback_err}")
        print(f"[REGISTRY] {provider.value} HTTP error: {e}")
        raise
    except Exception as e:
        # MARKER_93.11_ERROR: Update model status on general error
        from src.elisya.model_router_v2 import update_model_status
        update_model_status(model, success=False, error_code=500)
        print(f"[REGISTRY] {provider.value} failed: {e}")
        raise


# Convenience function for backwards compatibility
async def call_model_with_provider(
    prompt: str,
    model_name: str,
    provider: str,
    system_prompt: str = "You are a helpful assistant.",
    tools: Optional[List[Dict]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Backwards-compatible wrapper that accepts provider as string.
    Converts to new call_model_v2 format.
    """
    # Convert provider string to enum
    try:
        provider_enum = Provider(provider.lower())
    except ValueError:
        provider_enum = ProviderRegistry.detect_provider(model_name)

    # Build messages
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    return await call_model_v2(messages, model_name, provider_enum, tools, **kwargs)


# ============ STREAMING (Phase 93.2) ============


async def call_model_v2_stream(
    messages: List[Dict[str, str]],
    model: str,
    provider: Optional[Provider] = None,
    **kwargs,
) -> AsyncGenerator[str, None]:
    """
    Phase 93.2: Streaming version of call_model_v2.

    Supports:
    - Ollama (native streaming)
    - OpenRouter (SSE streaming)
    - Anti-loop detection (from Phase 90.2)
    - Timeout handling

    Args:
        messages: List of messages in OpenAI format
        model: Model identifier
        provider: Optional provider enum (auto-detected if None)
        **kwargs: Additional parameters (stream_timeout, temperature)

    Yields:
        Token strings as they arrive
    """
    from collections import deque
    import time as time_module
    import httpx

    registry = get_registry()

    # Auto-detect provider if not specified
    if provider is None:
        provider = ProviderRegistry.detect_provider(model)

    # MARKER_93.2_START: Anti-loop detection setup
    token_history = deque(maxlen=100)
    stream_start = time_module.time()
    max_duration = kwargs.get("stream_timeout", 300)  # 5 min default
    loop_threshold = 0.99  # Phase 100.1: Effectively DISABLED - user request (false positives on JSON/code)
    # MARKER_93.2_END

    print(f"[STREAM_V2] Starting stream: model={model}, provider={provider.value}")

    try:
        if provider == Provider.OLLAMA:
            # Ollama streaming
            async for token in _stream_ollama(messages, model, registry, **kwargs):
                # Apply anti-loop detection
                if time_module.time() - stream_start > max_duration:
                    print(f"[STREAM_V2] Timeout after {max_duration}s")
                    yield "\n\n[Stream stopped: timeout]"
                    break

                token_history.append(token)

                # Check for loops every 50 tokens
                if len(token_history) >= 50:
                    if _detect_loop(token_history, loop_threshold):
                        print(f"[STREAM_V2] Loop detected")
                        yield "\n\n[Stream stopped: repetition detected]"
                        break

                yield token

        elif provider == Provider.OPENROUTER:
            # OpenRouter SSE streaming
            async for token in _stream_openrouter(messages, model, registry, **kwargs):
                if time_module.time() - stream_start > max_duration:
                    print(f"[STREAM_V2] Timeout after {max_duration}s")
                    yield "\n\n[Stream stopped: timeout]"
                    break

                token_history.append(token)

                if len(token_history) >= 50:
                    if _detect_loop(token_history, loop_threshold):
                        print(f"[STREAM_V2] Loop detected")
                        yield "\n\n[Stream stopped: repetition detected]"
                        break

                yield token

        elif provider == Provider.XAI:
            # MARKER_94.1_FIX: Direct xAI streaming (not via OpenRouter)
            # x.ai API now supports streaming, use it directly
            clean_model = model.replace("xai/", "").replace("x-ai/", "")
            print(f"[STREAM_V2] XAI direct: {model} -> {clean_model}")

            async for token in _stream_xai_direct(messages, clean_model, **kwargs):
                if time_module.time() - stream_start > max_duration:
                    print(f"[STREAM_V2] Timeout after {max_duration}s")
                    yield "\n\n[Stream stopped: timeout]"
                    break

                token_history.append(token)

                if len(token_history) >= 50:
                    if _detect_loop(token_history, loop_threshold):
                        print(f"[STREAM_V2] Loop detected")
                        yield "\n\n[Stream stopped: repetition detected]"
                        break

                yield token

        elif provider == Provider.OPENAI:
            # MARKER_93.10: OpenAI streaming via OpenRouter
            # OpenRouter supports OpenAI models with streaming
            # Model format: openai/gpt-5.2 stays as openai/gpt-5.2
            print(f"[STREAM_V2] OpenAI via OpenRouter: {model}")

            async for token in _stream_openrouter(messages, model, registry, **kwargs):
                if time_module.time() - stream_start > max_duration:
                    print(f"[STREAM_V2] Timeout after {max_duration}s")
                    yield "\n\n[Stream stopped: timeout]"
                    break

                token_history.append(token)

                if len(token_history) >= 50:
                    if _detect_loop(token_history, loop_threshold):
                        print(f"[STREAM_V2] Loop detected")
                        yield "\n\n[Stream stopped: repetition detected]"
                        break

                yield token

        elif provider == Provider.ANTHROPIC:
            # MARKER_93.10: Anthropic streaming via OpenRouter
            print(f"[STREAM_V2] Anthropic via OpenRouter: {model}")

            async for token in _stream_openrouter(messages, model, registry, **kwargs):
                if time_module.time() - stream_start > max_duration:
                    print(f"[STREAM_V2] Timeout after {max_duration}s")
                    yield "\n\n[Stream stopped: timeout]"
                    break

                token_history.append(token)

                if len(token_history) >= 50:
                    if _detect_loop(token_history, loop_threshold):
                        print(f"[STREAM_V2] Loop detected")
                        yield "\n\n[Stream stopped: repetition detected]"
                        break

                yield token

        else:
            # Fallback: non-streaming call, yield result at once
            result = await call_model_v2(messages, model, provider, **kwargs)
            content = result.get("message", {}).get("content", "")
            yield content

    except Exception as e:
        print(f"[STREAM_V2 ERROR] {e}")
        yield f"\n[STREAM ERROR]: {str(e)}"


def _detect_loop(token_history: deque, threshold: float) -> bool:
    """
    MARKER_93.2: Detect repetitive patterns in token stream.

    Args:
        token_history: Recent tokens
        threshold: Overlap ratio to trigger detection

    Returns:
        True if loop detected
    """
    recent_text = "".join(list(token_history)[-50:])
    prior_text = "".join(list(token_history)[:-50])

    recent_words = set(recent_text.split())
    prior_words = set(prior_text.split())

    if prior_words:
        overlap = len(recent_words & prior_words) / max(len(recent_words), 1)
        return overlap > threshold

    return False


async def _stream_ollama(
    messages: List[Dict[str, str]],
    model: str,
    registry: "ProviderRegistry",
    **kwargs,
) -> AsyncGenerator[str, None]:
    """
    Phase 93.2: Ollama streaming implementation.
    """
    import ollama
    import asyncio

    provider_instance = registry.get(Provider.OLLAMA)
    if not provider_instance:
        yield "[ERROR] Ollama provider not available"
        return

    # Clean model name
    clean_model = model.replace("ollama/", "")

    # Run health check
    provider_instance._check_health()

    # Validate model
    if provider_instance._available_models and clean_model not in provider_instance._available_models:
        clean_model = provider_instance._default_model
        print(f"[STREAM_OLLAMA] Using fallback model: {clean_model}")

    print(f"[STREAM_OLLAMA] Starting stream: {clean_model}")

    params = {
        "model": clean_model,
        "messages": messages,
        "stream": True,
        "options": {"temperature": kwargs.get("temperature", 0.7)},
    }

    loop = asyncio.get_event_loop()

    try:
        # ollama.chat with stream=True returns generator
        def stream_sync():
            return ollama.chat(**params)

        response_gen = await loop.run_in_executor(None, stream_sync)

        for chunk in response_gen:
            if chunk and "message" in chunk:
                content = chunk["message"].get("content", "")
                if content:
                    yield content
            if chunk.get("done"):
                print(f"[STREAM_OLLAMA] Complete")
                break

    except Exception as e:
        print(f"[STREAM_OLLAMA ERROR] {e}")
        yield f"\n[STREAM ERROR]: {str(e)}"


# MARKER_94.1_XAI_STREAM: Direct x.ai streaming
async def _stream_xai_direct(
    messages: List[Dict[str, str]],
    model: str,  # Already cleaned: "grok-4" not "x-ai/grok-4"
    **kwargs,
) -> AsyncGenerator[str, None]:
    """
    Phase 94.1: Direct x.ai API streaming.
    x.ai uses OpenAI-compatible API with SSE streaming.
    """
    import httpx
    import json

    from src.orchestration.services.api_key_service import APIKeyService
    from src.utils.unified_key_manager import get_key_manager, ProviderType

    # Get xai key
    api_key = APIKeyService().get_key("xai")
    if not api_key:
        yield "[ERROR] No x.ai API key available"
        return

    print(f"[STREAM_XAI] Starting direct stream: {model}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": kwargs.get("temperature", 0.7),
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            async with client.stream(
                "POST",
                "https://api.x.ai/v1/chat/completions",
                json=payload,
                headers=headers,
            ) as response:
                # Handle 403 with key rotation
                if response.status_code == 403:
                    print(f"[STREAM_XAI] 403 Forbidden, trying key rotation...")
                    km = get_key_manager()
                    for record in km.keys.get(ProviderType.XAI, []):
                        if record.key == api_key:
                            record.mark_rate_limited()
                            print(f"[STREAM_XAI] Key marked rate-limited (24h)")
                            break

                    # Try next key
                    next_key = km.get_active_key(ProviderType.XAI)
                    if next_key and next_key != api_key:
                        print(f"[STREAM_XAI] Retrying with next key...")
                        headers["Authorization"] = f"Bearer {next_key}"
                        async with client.stream(
                            "POST",
                            "https://api.x.ai/v1/chat/completions",
                            json=payload,
                            headers=headers,
                        ) as retry_response:
                            if retry_response.status_code == 200:
                                async for line in retry_response.aiter_lines():
                                    if not line or not line.startswith("data: "):
                                        continue
                                    data_str = line[6:]
                                    if data_str == "[DONE]":
                                        return
                                    try:
                                        data = json.loads(data_str)
                                        content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                        if content:
                                            yield content
                                    except json.JSONDecodeError:
                                        continue
                                return

                    # All keys exhausted - fallback to OpenRouter
                    print(f"[STREAM_XAI] All keys exhausted, falling back to OpenRouter")
                    yield "[XAI keys exhausted, using OpenRouter fallback]\n"
                    # Note: Caller should handle OpenRouter fallback
                    return

                if response.status_code != 200:
                    error_text = await response.aread()
                    yield f"[ERROR] x.ai: {response.status_code} - {error_text.decode()}"
                    return

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    data_str = line[6:]  # Remove "data: " prefix
                    if data_str == "[DONE]":
                        print(f"[STREAM_XAI] Complete")
                        return

                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            print(f"[STREAM_XAI ERROR] {e}")
            yield f"\n[STREAM ERROR]: {str(e)}"


async def _stream_openrouter(
    messages: List[Dict[str, str]],
    model: str,
    registry: "ProviderRegistry",
    **kwargs,
) -> AsyncGenerator[str, None]:
    """
    Phase 93.2: OpenRouter SSE streaming implementation.
    Phase 93.4: Added auto-rotation on 401/402/403 errors.
    """
    import httpx
    import json

    from src.utils.unified_key_manager import get_key_manager
    km = get_key_manager()
    max_retries = km.get_openrouter_keys_count()  # MARKER_94.1: Use all OR keys

    for attempt in range(max_retries):
        # FIX_95.5: rotate=True to actually use all keys on retry
        api_key = km.get_openrouter_key(rotate=(attempt > 0))
        if not api_key:
            yield "[ERROR] No OpenRouter API key available"
            return

        print(f"[STREAM_OPENROUTER] Starting stream: {model} (key: ****{api_key[-4:]}, attempt {attempt + 1}/{max_retries})")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://vetka.ai",
            "X-Title": "VETKA AI",
            "Content-Type": "application/json",
        }

        # MARKER_93.6_STREAM_MODEL_CLEANUP: Clean model name for streaming
        # Phase 93.6: Fix 400 Bad Request - OpenRouter doesn't accept prefixed models
        clean_model = model.replace("openrouter/", "")

        payload = {
            "model": clean_model,
            "messages": messages,
            "stream": True,
            "temperature": kwargs.get("temperature", 0.7),
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                async with client.stream(
                    "POST",
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=payload,
                    headers=headers,
                ) as response:
                    # Phase 93.4: Handle auth/payment errors with key rotation + 24h cooldown
                    if response.status_code in (401, 402, 403):
                        print(f"[STREAM_OPENROUTER] Key failed ({response.status_code}), marking rate-limited (24h)...")
                        # MARKER_93.4_24H_COOLDOWN
                        from src.utils.unified_key_manager import ProviderType
                        for record in km.keys.get(ProviderType.OPENROUTER, []):
                            if record.key == api_key:
                                record.mark_rate_limited()
                                print(f"[STREAM_OPENROUTER] Key {record.mask()} marked rate-limited")
                                break
                        km.rotate_to_next()
                        continue  # Retry with next key

                    if response.status_code != 200:
                        error_text = await response.aread()
                        yield f"[ERROR] OpenRouter: {response.status_code} - {error_text.decode()}"
                        return

                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue

                        data_str = line[6:]  # Remove "data: " prefix
                        if data_str == "[DONE]":
                            print(f"[STREAM_OPENROUTER] Complete")
                            break

                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

                    # Success - exit retry loop
                    return

            except Exception as e:
                print(f"[STREAM_OPENROUTER ERROR] {e}")
                yield f"\n[STREAM ERROR]: {str(e)}"
                return

    # All retries exhausted
    yield f"[ERROR] All OpenRouter keys exhausted after {max_retries} attempts"
