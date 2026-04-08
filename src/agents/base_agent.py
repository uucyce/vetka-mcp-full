"""
BaseAgent - Foundation class for VETKA agent hierarchy.

Provides LLM calling capabilities with automatic provider selection.
Supports OpenRouter, Gemini, and Ollama fallback.

@file base_agent.py
@status: active
@phase: 96
@depends: httpx, src.orchestration.services.api_key_service.APIKeyService
@used_by: src/agents/vetka_pm.py, src/agents/vetka_dev.py,
          src/agents/vetka_qa.py, src/agents/vetka_architect.py
"""

import httpx
import json
import time
from typing import Optional

# Phase 57: Import APIKeyService for config.json-based key management
from src.orchestration.services.api_key_service import APIKeyService

# Singleton instance for key management
_api_key_service = None


def _get_api_key_service() -> APIKeyService:
    """Get or create singleton APIKeyService instance."""
    global _api_key_service
    if _api_key_service is None:
        _api_key_service = APIKeyService()
    return _api_key_service


class BaseAgent:
    def __init__(self, role: str, token_budget: Optional[int] = None):
        self.role = role
        self.name = role
        # token_budget removed - unlimited responses
        self.ollama_base_url = "http://localhost:11434"
        self.model = "ollama/llama3.2:1b"  # Fast model
        self.key_index = 0
        self.tokens_used = 0

    def _get_best_provider(self) -> dict:
        """
        Select best provider based on available API keys.
        Priority: OpenRouter (multiple models) → Gemini → Ollama (fallback)

        Phase 57: Now uses APIKeyService (config.json) instead of os.environ.
        """
        key_service = _get_api_key_service()

        # Check for OpenRouter key from config.json
        openrouter_key = key_service.get_key("openrouter")
        if openrouter_key:
            print(f"[INFO] {self.name}: Using OpenRouter (from config.json)")
            return {
                "provider": "openrouter",
                "model": "deepseek/deepseek-chat",  # Default OpenRouter model
                "api_key": openrouter_key,
                "base_url": "https://openrouter.ai/api/v1",
            }

        # Check for Gemini key from config.json
        gemini_key = key_service.get_key("gemini")
        if gemini_key:
            print(f"[INFO] {self.name}: Using Gemini (from config.json)")
            return {
                "provider": "gemini",
                "model": "gemini-2.0-flash",
                "api_key": gemini_key,
                "base_url": "https://generativelanguage.googleapis.com/v1beta/models",
            }

        # Fallback to Ollama (local, learning-enabled)
        print(
            f"[WARN] {self.name}: No API keys found in config.json, using Ollama (local)"
        )
        return {
            "provider": "ollama",
            "model": "mistral",
            "api_key": None,
            "base_url": "http://localhost:11434",
        }

    def call_llm(
        self, prompt: str, context: str = "", max_tokens: Optional[int] = None
    ) -> str:
        """
        Call LLM using best available provider.
        Automatically routes to OpenRouter/Gemini if keys available,
        falls back to Ollama for local learning.
        """

        full_prompt = f"{context}\n\n{prompt}" if context else prompt

        # max_tokens removed - unlimited responses

        start_time = time.time()

        # Get best provider
        provider_info = self._get_best_provider()
        provider = provider_info["provider"]
        model = provider_info["model"]
        api_key = provider_info["api_key"]

        try:
            if provider == "openrouter":
                # Use OpenRouter API
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }

                response = httpx.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": f"You are {self.role}."},
                            {"role": "user", "content": full_prompt},
                        ],
                        "max_tokens": max_tokens,
                    },
                    timeout=60,
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    tokens = data.get("usage", {}).get(
                        "completion_tokens", len(content.split())
                    )
                    self.tokens_used = tokens
                    elapsed = time.time() - start_time

                    print(
                        f"[AGENT] {self.name:12} | provider=OpenRouter | model={model[:20]:20} | budget={max_tokens:4} | used={tokens:4} | time={elapsed:.2f}s"
                    )
                    return content
                else:
                    print(
                        f"[WARN] {self.role}: OpenRouter error {response.status_code}, falling back to Ollama"
                    )
                    return self._call_ollama(full_prompt, max_tokens or 0)

            elif provider == "gemini":
                # Use Gemini API
                response = httpx.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    params={"key": api_key},
                    json={
                        "contents": [{"parts": [{"text": full_prompt}]}],
                        "generationConfig": {
                            # maxOutputTokens removed - unlimited
                        },
                    },
                    timeout=60,
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data["candidates"][0]["content"]["parts"][0]["text"]
                    tokens = len(content.split())
                    self.tokens_used = tokens
                    elapsed = time.time() - start_time

                    print(
                        f"[AGENT] {self.name:12} | provider=Gemini | model={model:20} | budget={max_tokens:4} | used={tokens:4} | time={elapsed:.2f}s"
                    )
                    return content
                else:
                    print(
                        f"[WARN] {self.role}: Gemini error {response.status_code}, falling back to Ollama"
                    )
                    return self._call_ollama(full_prompt, max_tokens or 0)

            else:
                # Ollama (local, learning)
                return self._call_ollama(full_prompt, max_tokens or 0)

        except Exception as e:
            print(f"[ERROR] {self.role}: LLM error: {e}, falling back to Ollama")
            return self._call_ollama(full_prompt, max_tokens)

    def _call_ollama(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Call local Ollama (learning model)"""
        start_time = time.time()

        try:
            client = httpx.Client(base_url="http://localhost:11434", timeout=120)
            model_name = self.model.replace("ollama/", "")

            resp = client.post(
                "/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    # max_tokens removed - unlimited responses
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                response = data.get("response", "")

                eval_count = data.get("eval_count", len(response.split()))
                self.tokens_used = eval_count
                elapsed = time.time() - start_time

                print(
                    f"[AGENT] {self.name:12} | provider=Ollama (LOCAL) | model={model_name:20} | budget={max_tokens:4} | used={eval_count:4} | time={elapsed:.2f}s"
                )

                return response
            else:
                print(f"[ERROR] {self.role}: Ollama HTTP {resp.status_code}")
                return ""

        except Exception as e:
            print(f"[ERROR] {self.role}: Ollama error: {e}")
            return ""

    def handle_task(
        self, task: str, context: str = "", max_tokens: Optional[int] = None
    ) -> str:
        """Execute task with token budget"""
        prompt = f"You are {self.role}.\nTask: {task}"
        return self.call_llm(prompt, context, max_tokens)  # unlimited

    def get_token_usage(self):
        """Return token usage statistics"""
        return {
            "role": self.role,
            "budget": "unlimited",
            "used": self.tokens_used,
            "remaining": "unlimited",
        }
