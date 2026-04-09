"""
Direct API Calls Module.
Phase 95.1: Extracted from api_gateway.py for modular architecture.

Direct API calls for OpenAI/Anthropic/Google models with native tool support.
Bypasses Ollama for direct provider communication.

@status: active
@phase: 96
@depends: os, json, httpx, typing
@used_by: api_aggregator_v3, provider_registry
"""

import os
import json
import httpx
from typing import Dict, List, Optional


async def call_openai_direct(
    messages: List[Dict], model_name: str, tools: Optional[List[Dict]] = None
) -> Dict:
    """
    Call OpenAI API directly with tool support.
    Phase 80.9: Bypass Ollama for OpenAI models.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        # Try to get from config
        try:
            from src.orchestration.services.api_key_service import get_api_key_service

            key_service = get_api_key_service()
            api_key = key_service.get_key("openai")
        except:
            pass

    if not api_key:
        raise ValueError("No OpenAI API key found")

    # Extract model name without provider prefix
    model = model_name.replace("openai/", "")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {"model": model, "messages": messages}

    if tools:
        # Convert tools to OpenAI format
        payload["tools"] = [{"type": "function", "function": t} for t in tools]

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
        )

        if response.status_code >= 400:
            raise Exception(
                f"OpenAI API error: {response.status_code} - {response.text}"
            )

        data = response.json()

        # Return in format compatible with rest of system
        if "choices" in data and data["choices"]:
            choice = data["choices"][0]
            return {
                "message": {
                    "content": choice.get("message", {}).get("content", ""),
                    "tool_calls": choice.get("message", {}).get("tool_calls", []),
                }
            }

        return {"message": {"content": ""}}


async def call_anthropic_direct(
    messages: List[Dict], model_name: str, tools: Optional[List[Dict]] = None
) -> Dict:
    """
    Call Anthropic API directly with tool support.
    Phase 80.9: Bypass Ollama for Claude models.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        try:
            from src.orchestration.services.api_key_service import get_api_key_service

            key_service = get_api_key_service()
            api_key = key_service.get_key("anthropic")
        except:
            pass

    if not api_key:
        raise ValueError("No Anthropic API key found")

    # Extract model name without provider prefix
    model = model_name.replace("anthropic/", "")

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }

    # Convert messages to Anthropic format
    system_msg = ""
    anthropic_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_msg = msg["content"]
        else:
            anthropic_messages.append(msg)

    payload = {"model": model, "messages": anthropic_messages}

    if system_msg:
        payload["system"] = system_msg

    if tools:
        # Convert tools to Anthropic format
        payload["tools"] = [
            {
                "name": t.get("name"),
                "description": t.get("description", ""),
                "input_schema": t.get("parameters", {}),
            }
            for t in tools
        ]

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages", headers=headers, json=payload
        )

        if response.status_code >= 400:
            raise Exception(
                f"Anthropic API error: {response.status_code} - {response.text}"
            )

        data = response.json()

        # Extract content from Anthropic response
        content = ""
        tool_calls = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    {
                        "id": block.get("id"),
                        "function": {
                            "name": block.get("name"),
                            "arguments": json.dumps(block.get("input", {})),
                        },
                    }
                )

        return {"message": {"content": content, "tool_calls": tool_calls}}


async def call_google_direct(
    messages: List[Dict], model_name: str, tools: Optional[List[Dict]] = None
) -> Dict:
    """
    Call Google Gemini API directly with tool support.
    Phase 80.9: Bypass Ollama for Gemini models.
    """
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        try:
            from src.orchestration.services.api_key_service import get_api_key_service

            key_service = get_api_key_service()
            api_key = key_service.get_key("google") or key_service.get_key("gemini")
        except:
            pass

    if not api_key:
        raise ValueError("No Google/Gemini API key found")

    # Extract model name without provider prefix
    model = model_name.replace("google/", "").replace("gemini/", "")
    if not model.startswith("gemini"):
        model = f"gemini-{model}"

    # Convert messages to Gemini format
    contents = []
    system_instruction = None

    for msg in messages:
        if msg["role"] == "system":
            system_instruction = msg["content"]
        elif msg["role"] == "user":
            contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
        elif msg["role"] == "assistant":
            contents.append({"role": "model", "parts": [{"text": msg["content"]}]})

    payload = {"contents": contents}

    if system_instruction:
        payload["system_instruction"] = {"parts": [{"text": system_instruction}]}

    if tools:
        # Convert tools to Gemini format
        function_declarations = [
            {
                "name": t.get("name"),
                "description": t.get("description", ""),
                "parameters": t.get("parameters", {}),
            }
            for t in tools
        ]
        payload["tools"] = [{"function_declarations": function_declarations}]

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, json=payload)

        if response.status_code >= 400:
            raise Exception(
                f"Google API error: {response.status_code} - {response.text}"
            )

        data = response.json()

        # Extract content from Gemini response
        content = ""
        tool_calls = []

        candidates = data.get("candidates", [])
        if candidates:
            for part in candidates[0].get("content", {}).get("parts", []):
                if "text" in part:
                    content += part["text"]
                elif "functionCall" in part:
                    fc = part["functionCall"]
                    tool_calls.append(
                        {
                            "id": f"call_{len(tool_calls)}",
                            "function": {
                                "name": fc.get("name"),
                                "arguments": json.dumps(fc.get("args", {})),
                            },
                        }
                    )

        return {"message": {"content": content, "tool_calls": tool_calls}}
