"""
VETKA Chat Handler - Direct Model Calls and @Mention Routing

@file chat_handler.py
@status ACTIVE
@phase Phase 64.3
@extracted_from user_message_handler.py
@lastAudit 2026-01-17

@calledBy:
  - src.api.handlers.user_message_handler (detect_provider, build_model_prompt, get_agent_short_name)
  - src.api.handlers.__init__ (re-export)

Handles direct model communication:
- Provider detection (Ollama, OpenRouter, Gemini, xAI, Deepseek, Groq)
- Unified prompt building
- Ollama local model calls
- OpenRouter API calls
- @mention routing to specific models/agents

This module provides helper functions that are used by the main
user_message_handler to handle direct chat scenarios.

Dependencies:
- ollama (external)
- httpx (external)
"""

import asyncio
import uuid
from typing import Dict, Any, Optional, Tuple
from enum import Enum


class ModelProvider(Enum):
    """Supported model providers."""

    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    GEMINI = "gemini"
    XAI = "xai"
    DEEPSEEK = "deepseek"
    GROQ = "groq"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    UNKNOWN = "unknown"


def detect_provider(model_name: str, source: Optional[str] = None) -> ModelProvider:
    """
    Detect which provider a model belongs to.

    Phase 90.1.4.1: NOW USES CANONICAL detect_provider from provider_registry.
    This is a WRAPPER that converts Provider enum to ModelProvider enum.

    # MARKER_90.1.4.1_START: Use canonical detect_provider
    """
    if not model_name:
        return ModelProvider.UNKNOWN

    # Use canonical implementation
    from src.elisya.provider_registry import ProviderRegistry, Provider

    canonical_provider = ProviderRegistry.detect_provider(model_name, source=source)

    # Map Provider enum to ModelProvider enum
    provider_map = {
        Provider.OPENAI: ModelProvider.OPENAI,
        Provider.ANTHROPIC: ModelProvider.ANTHROPIC,
        Provider.GOOGLE: ModelProvider.GEMINI,
        Provider.GEMINI: ModelProvider.GEMINI,
        Provider.OLLAMA: ModelProvider.OLLAMA,
        Provider.OPENROUTER: ModelProvider.OPENROUTER,
        Provider.XAI: ModelProvider.XAI,
    }

    result = provider_map.get(canonical_provider, ModelProvider.UNKNOWN)

    # Legacy check for deepseek/groq (not in canonical Provider enum yet)
    model_lower = model_name.lower()
    if model_lower.startswith("deepseek:") or "deepseek-api" in model_lower:
        return ModelProvider.DEEPSEEK
    if model_lower.startswith("groq:"):
        return ModelProvider.GROQ

    return result
    # MARKER_90.1.4.1_END


def is_local_ollama_model(model_name: str) -> bool:
    """
    Phase 60.4: Detect if this is a local Ollama model.

    DEPRECATED: Use detect_provider() instead for more accurate detection.

    Ollama models don't have '/' in name (e.g., qwen2:7b, llama3:8b)
    OpenRouter models have provider prefix (e.g., anthropic/claude-3, deepseek/deepseek-r1)

    Args:
        model_name: Model identifier string

    Returns:
        True if local Ollama model, False if OpenRouter/other
    """
    return detect_provider(model_name) == ModelProvider.OLLAMA


# [PHASE71-M3] Phase 71: Added viewport_summary parameter
# [PHASE73-4] Phase 73: Added json_context parameter
def build_model_prompt(
    text: str,
    context_for_model: str,
    pinned_context: str = "",
    history_context: str = "",
    viewport_summary: str = "",
    json_context: str = "",
    web_context_summary: str = "",
) -> str:
    """
    Build a standard prompt for direct model calls.

    Phase 71: Added viewport_summary for spatial awareness context.
    Phase 73: Added json_context for structured dependency/semantic context.

    Args:
        text: User's message text
        context_for_model: File/node context string
        pinned_context: Optional pinned files context
        history_context: Optional chat history context
        viewport_summary: Optional viewport spatial context (Phase 71)
        json_context: Optional JSON dependency context (Phase 73)

    Returns:
        Formatted prompt string
    """
    # MARKER_140.WEB_CTX_PROMPT: Prioritized live web summary section (without replacing viewport context)
    web_section = ""
    if web_context_summary:
        web_section = f"""## LIVE WEB CONTEXT (PRIMARY WHEN RELEVANT)
The user currently has a web page open in VETKA research window.
Use this context first for internet-related questions.

{web_context_summary}
"""

    # Phase 71: Build spatial context section if available
    spatial_section = ""
    if viewport_summary:
        spatial_section = f"""## 3D VIEWPORT CONTEXT
The user is viewing this codebase in a 3D visualization. Here's what they can see:

{viewport_summary}
"""

    # Phase 73: json_context is already formatted with header, just include if present
    json_section = json_context if json_context else ""

    return f"""You are a helpful AI assistant. Analyze the following context and answer the user's question.

{context_for_model}

{json_section}{pinned_context}{web_section}{spatial_section}{history_context}## CURRENT USER QUESTION
{text}

---

Provide a helpful, specific answer:"""


def build_web_context_summary(web_context: Optional[Dict[str, Any]]) -> str:
    """
    MARKER_140.WEB_CTX_SUMMARY: Compact web context summary for prompt injection.
    """
    if not web_context or not web_context.get("url"):
        return ""

    url = str(web_context.get("url", "")).strip()
    if not url:
        return ""

    title = str(web_context.get("title", "")).strip()
    source = str(web_context.get("source", "")).strip()
    captured_at = str(web_context.get("captured_at", "")).strip()
    summary = str(web_context.get("summary", "")).strip()

    # Guard token bloat: keep only concise live summary
    if len(summary) > 2500:
        summary = summary[:2500] + "\n...[truncated]"

    lines = [
        f"- URL: {url}",
    ]
    if title:
        lines.append(f"- Title: {title}")
    if source:
        lines.append(f"- Source: {source}")
    if captured_at:
        lines.append(f"- Captured: {captured_at}")

    if summary:
        lines.extend(["", "### Page Summary", summary])

    return "\n".join(lines)


async def call_ollama_model(
    model_name: str, prompt: str, with_tools: bool = False, tools: Optional[list] = None
) -> Tuple[str, Optional[list]]:
    """
    Call local Ollama model.

    Phase 80.5: Added tool support detection to avoid errors with lightweight models.

    Args:
        model_name: Ollama model identifier (e.g., qwen2:7b)
        prompt: Full prompt text
        with_tools: Whether to include tools in call
        tools: Optional list of tool definitions

    Returns:
        Tuple of (response_text, tool_calls or None)
    """
    import ollama

    loop = asyncio.get_event_loop()

    messages = [{"role": "user", "content": prompt}]

    # Phase 80.5: Models that don't support tools
    MODELS_WITHOUT_TOOLS = {
        "deepseek-llm",
        "llama2",
        "codellama",
        "mistral",
        "phi",
        "gemma",
        "orca-mini",
        "vicuna",
    }

    # Check if model supports tools
    base_model = model_name.split(":")[0].lower()
    model_supports_tools = not any(
        unsupported in base_model for unsupported in MODELS_WITHOUT_TOOLS
    )

    if with_tools and tools:
        if not model_supports_tools:
            print(
                f"[CHAT] ⚠️  {model_name} does not support tools - calling without tools"
            )
            with_tools = False
        else:
            # Add tool guidance to system message
            tool_system = """You have access to tools. Use them when appropriate:
- camera_focus: Move 3D camera to show user specific files/folders. USE THIS when asked to show/navigate/focus on something.
- search_semantic: Search codebase by meaning
- get_tree_context: Get file structure context

When user asks to "show", "focus", "navigate to" a file - USE camera_focus tool!"""

            messages = [
                {"role": "system", "content": tool_system},
                {"role": "user", "content": prompt},
            ]

            try:
                ollama_response = await loop.run_in_executor(
                    None,
                    lambda: ollama.chat(
                        model=model_name, messages=messages, tools=tools, stream=False
                    ),
                )
            except Exception as e:
                # Phase 80.5: If tools error, retry without tools
                if "does not support tools" in str(e):
                    print(
                        f"[CHAT] Tool error detected, retrying {model_name} without tools"
                    )
                    with_tools = False
                else:
                    raise
    # Call without tools (either not requested or model doesn't support)
    if not with_tools:

        def ollama_call():
            return ollama.chat(model=model_name, messages=messages, stream=False)

        ollama_response = await loop.run_in_executor(None, ollama_call)

    # Extract response text
    response_text = ""
    tool_calls = None

    if hasattr(ollama_response, "message"):
        response_text = ollama_response.message.content or ""
        if (
            hasattr(ollama_response.message, "tool_calls")
            and ollama_response.message.tool_calls
        ):
            tool_calls = ollama_response.message.tool_calls
    else:
        response_text = ollama_response.get("message", {}).get("content", "")

    return response_text, tool_calls


async def call_openrouter_model(
    model_name: str,
    prompt: str,
    api_key: str,
    max_tokens: int = 999999,
    temperature: float = 0.7,
    stream: bool = True,
) -> Tuple[str, int, Optional[str]]:
    """
    Call OpenRouter API model.

    Args:
        model_name: OpenRouter model identifier (e.g., anthropic/claude-3-haiku)
        prompt: Full prompt text
        api_key: OpenRouter API key
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature
        stream: Whether to use streaming (for compatibility check)

    Returns:
        Tuple of (response_text, token_count, error_message or None)
    """
    import httpx
    import json as json_module

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://vetka.app",
        "X-Title": "VETKA",
    }

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,  # Non-streaming for simple call
    }

    full_response = ""
    tokens_output = 0
    error_message = None

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
            )

            if resp.status_code == 429:
                error_message = f"Rate limited for model {model_name}"
            elif resp.status_code in [401, 402]:
                error_message = f"Auth error {resp.status_code}"
            elif resp.status_code == 200:
                resp_data = resp.json()
                full_response = (
                    resp_data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                tokens_output = resp_data.get("usage", {}).get(
                    "completion_tokens", len(full_response.split())
                )
            else:
                error_message = f"Error {resp.status_code}: {resp.text[:200]}"

    except Exception as e:
        error_message = str(e)

    return full_response, tokens_output, error_message


def get_agent_short_name(model_name: str) -> str:
    """
    Extract short agent name from model identifier.

    Args:
        model_name: Full model name (e.g., anthropic/claude-3-haiku or qwen2:7b)

    Returns:
        Short name for display (e.g., claude-3-haiku or qwen2)
    """
    # OpenRouter: provider/model -> model
    if "/" in model_name:
        return model_name.split("/")[-1]
    # Ollama: model:tag -> model
    if ":" in model_name:
        return model_name.split(":")[0]
    return model_name


async def emit_model_response(
    sio,
    sid: str,
    response_text: str,
    model_name: str,
    node_id: str,
    node_path: str,
    timestamp: float,
    response_type: str = "text",
) -> None:
    """
    Emit model response to client via both agent_message and chat_response events.

    Args:
        sio: Socket.IO server instance
        sid: Session ID
        response_text: Response content
        model_name: Model identifier
        node_id: Node ID for context
        node_path: File path context
        timestamp: Request timestamp
        response_type: Type of response (text, code, etc.)
    """
    agent_short_name = get_agent_short_name(model_name)
    force_artifact = len(response_text) > 800

    # Emit agent_message (for 3D panel)
    await sio.emit(
        "agent_message",
        {
            "agent": agent_short_name,
            "model": model_name,
            "content": response_text,
            "text": response_text,
            "node_id": node_id,
            "node_path": node_path,
            "timestamp": timestamp,
            "response_type": response_type,
            "force_artifact": force_artifact,
        },
        to=sid,
    )

    # Emit chat_response (for chat panel)
    await sio.emit(
        "chat_response",
        {
            "message": response_text,
            "agent": agent_short_name,
            "model": model_name,
            "workflow_id": f"direct_{timestamp}",
        },
        to=sid,
    )


async def emit_stream_wrapper(
    sio, sid: str, model_name: str, full_response: str, prompt: str
) -> None:
    """
    Emit stream start/end events for non-streaming responses.

    Used when we have a complete response but want to emit it
    in the streaming event format for client consistency.

    Args:
        sio: Socket.IO server instance
        sid: Session ID
        model_name: Model identifier
        full_response: Complete response text
        prompt: Original prompt (for input token count)
    """
    agent_short_name = get_agent_short_name(model_name)
    msg_id = str(uuid.uuid4())
    tokens_output = len(full_response.split())

    # Emit stream start
    await sio.emit(
        "stream_start",
        {"id": msg_id, "agent": agent_short_name, "model": model_name},
        to=sid,
    )

    # Emit stream end with full response
    await sio.emit(
        "stream_end",
        {
            "id": msg_id,
            "full_message": full_response,
            "metadata": {
                "tokens_output": tokens_output,
                "tokens_input": len(prompt.split()),
                "model": model_name,
                "agent": agent_short_name,
            },
        },
        to=sid,
    )


# Export all utilities
__all__ = [
    "ModelProvider",
    "detect_provider",
    "is_local_ollama_model",
    "build_model_prompt",
    "call_ollama_model",
    "call_openrouter_model",
    "get_agent_short_name",
    "emit_model_response",
    "emit_stream_wrapper",
]
