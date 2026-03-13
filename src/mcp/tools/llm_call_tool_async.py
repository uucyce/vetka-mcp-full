"""MCP Tool: mycelium_call_model — Native async LLM call for MYCELIUM.

Fork of llm_call_tool.py with native async execute().
Eliminates ThreadPoolExecutor + asyncio.run() hack that blocked VETKA event loop.

Key differences from llm_call_tool.py (sync version):
- Inherits BaseAsyncMCPTool (async execute)
- Direct `await call_model_v2()` — no ThreadPoolExecutor
- Direct `await _gather_inject_context()` — no asyncio.run() hack
- Chat emit via HTTP POST (no SocketIO access in MYCELIUM)
- Same security filters (SAFE_FUNCTION_CALLING_TOOLS allowlist)
- Same usage tracking (_track_usage_for_balance)

MARKER_129.2: Phase 129 — MYCELIUM async LLM tool

@status: active
@phase: 129
@depends: base_async_tool.py, src.elisya.provider_registry, src.utils.unified_key_manager
@used_by: mycelium_mcp_server.py, agent_pipeline.py (async_mode=True)
"""

from typing import Any, Dict, List, Optional
import logging
import asyncio
import random
import json
from pathlib import Path

from .base_async_tool import BaseAsyncMCPTool
from .llm_call_reflex import (
    extend_safe_tool_allowlist,
    filter_tool_calls,
    get_effective_allowed_tool_names,
    is_opted_in_write_tool,
    maybe_apply_reflex_to_direct_tools,
)

logger = logging.getLogger(__name__)

# MARKER_133.C33A: Provider Resilience — retry + fallback chain
RESILIENCE_MAX_RETRIES = 5
RESILIENCE_FALLBACK_CHAIN = ["polza", "openrouter", "ollama"]
RETRYABLE_ERRORS = ["429", "502", "503", "504", "timeout", "Timeout", "rate limit", "RateLimitError"]


async def resilient_llm_call(
    call_func,
    messages: List[Dict],
    model: str,
    provider_enum,
    source: Optional[str],
    tools: Optional[List],
    temperature: float,
    max_tokens: int,
    fallback_chain: Optional[List[str]] = None,
    max_retries: int = RESILIENCE_MAX_RETRIES,
) -> Dict[str, Any]:
    """MARKER_133.C33A: Exponential backoff + jitter + provider fallback.

    Wraps LLM calls with:
    1. Retry with exponential backoff (1s → 16s) + jitter (±20%)
    2. Max 5 retries per provider on 429/502/504/timeout
    3. Fallback chain: polza → openrouter → ollama
    4. Logging of each retry and provider switch
    """
    from src.elisya.provider_registry import Provider

    providers_to_try = fallback_chain or RESILIENCE_FALLBACK_CHAIN
    last_exc = None
    original_source = source

    for provider_name in providers_to_try:
        # Skip if we're already using a specific source and it's not this provider
        if original_source and original_source != provider_name:
            continue

        for attempt in range(max_retries):
            try:
                # Update provider enum for this attempt
                try:
                    current_provider = Provider(provider_name)
                except ValueError:
                    current_provider = provider_enum

                response = await call_func(
                    messages=messages,
                    model=model,
                    provider=current_provider,
                    source=provider_name,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response

            except Exception as e:
                last_exc = e
                err_str = str(e)

                # Check if error is retryable
                is_retryable = any(code in err_str for code in RETRYABLE_ERRORS)

                if is_retryable:
                    # Exponential backoff with jitter
                    base_wait = min(2 ** attempt, 16)
                    jitter = base_wait * random.uniform(-0.2, 0.2)
                    wait_time = base_wait + jitter

                    logger.warning(
                        f"[Resilience] {provider_name} attempt {attempt + 1}/{max_retries}: "
                        f"{err_str[:80]}. Retry in {wait_time:.1f}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    # Non-retryable error — break inner loop, try next provider
                    logger.error(f"[Resilience] {provider_name} non-retryable: {err_str[:120]}")
                    break

        # Provider exhausted
        logger.warning(f"[Resilience] Provider {provider_name} exhausted after {max_retries} retries, trying next")

        # After first provider fails, allow fallback to other providers
        if original_source:
            original_source = None

    raise last_exc or RuntimeError("All providers failed")

# MARKER_129.2_START: Security allowlists (same as llm_call_tool.py)
SAFE_FUNCTION_CALLING_TOOLS = extend_safe_tool_allowlist({
    "vetka_search_semantic",
    "vetka_read_file",
    "vetka_list_files",
    "vetka_get_tree",
    "vetka_search_files",
    "vetka_get_metrics",
    "vetka_get_knowledge_graph",
    "vetka_health",
    "vetka_get_media_window_debug",
    "vetka_get_pinned_files",
    "vetka_get_context_dag",
    "vetka_get_memory_summary",
    "vetka_get_user_preferences",
    "vetka_get_conversation_context",
    "vetka_read_group_messages",
    "vetka_get_chat_digest",
    "vetka_session_init",
    "vetka_session_status",
    "vetka_research",
    "vetka_review",
    "vetka_git_status",
    "vetka_run_tests",
    "vetka_list_artifacts",
    "vetka_workflow_status",
    "vetka_arc_suggest",
    "vetka_web_search",
    "vetka_library_docs",
})

WRITE_TOOLS_REQUIRING_APPROVAL = {
    "vetka_edit_file",
    "vetka_git_commit",
    "vetka_edit_artifact",
    "vetka_approve_artifact",
    "vetka_reject_artifact",
    "vetka_send_message",
    "vetka_camera_focus",
    "vetka_execute_workflow",
    "vetka_mycelium_pipeline",
    "vetka_implement",
    "vetka_call_model",
}


class LLMCallToolAsync(BaseAsyncMCPTool):
    """Async LLM call tool for MYCELIUM — native async, no ThreadPoolExecutor."""

    @property
    def name(self) -> str:
        return "mycelium_call_model"

    @property
    def description(self) -> str:
        return (
            "Call any LLM model through MYCELIUM (async). Supports Grok (x.ai), GPT (OpenAI), "
            "Claude (Anthropic), Gemini (Google), Ollama (local), and OpenRouter. "
            "Examples: grok-4, gpt-4o, claude-opus-4-5, gemini-2.0-flash, llama3.1:8b"
        )

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": (
                        "Model identifier. Examples:\n"
                        "- grok-4 (x.ai/Grok)\n"
                        "- gpt-4o, gpt-4-turbo (OpenAI)\n"
                        "- claude-opus-4-5, claude-sonnet-4-5 (Anthropic)\n"
                        "- gemini-2.0-flash, gemini-1.5-pro (Google)\n"
                        "- llama3.1:8b, deepseek-llm:7b (Ollama local)\n"
                        "- mistralai/mistral-7b (OpenRouter)"
                    )
                },
                "messages": {
                    "type": "array",
                    "description": (
                        "Chat messages in format [{\"role\": \"user\"|\"assistant\"|\"system\", \"content\": \"...\"}]. "
                        "At minimum, provide one user message."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string", "enum": ["user", "assistant", "system"]},
                            "content": {"type": "string"}
                        },
                        "required": ["role", "content"]
                    }
                },
                "temperature": {
                    "type": "number",
                    "description": "Sampling temperature (0.0-2.0, default: 0.7)",
                    "default": 0.7,
                    "minimum": 0.0,
                    "maximum": 2.0
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum tokens to generate (default: 4096)",
                    "default": 4096,
                    "minimum": 1
                },
                "tools": {
                    "type": "array",
                    "description": "Optional function calling tools (OpenAI format).",
                    "items": {"type": "object"}
                },
                "inject_context": {
                    "type": "object",
                    "description": "Auto-inject VETKA context into system prompt.",
                    "properties": {
                        "files": {"type": "array", "items": {"type": "string"}},
                        "session_id": {"type": "string"},
                        "include_prefs": {"type": "boolean", "default": False},
                        "include_cam": {"type": "boolean", "default": False},
                        "semantic_query": {"type": "string"},
                        "semantic_limit": {"type": "integer", "default": 5},
                        "compress": {"type": "boolean", "default": True},
                        "chat_id": {"type": "string"},
                        "chat_limit": {"type": "integer", "default": 10}
                    }
                },
                "model_source": {
                    "type": "string",
                    "description": "Source provider for routing (poe, polza, openrouter, etc.)",
                }
            },
            "required": ["model", "messages"]
        }

    # --- Helper methods (sync, no I/O) ---

    def _detect_provider(self, model: str, source: Optional[str] = None) -> str:
        """Detect provider from model name or explicit source."""
        from src.elisya.provider_registry import ProviderRegistry
        canonical_provider = ProviderRegistry.detect_provider(model, source=source)
        return canonical_provider.value

    def _normalize_model_name(self, model: str) -> str:
        """Normalize short model names to full versions."""
        aliases = {
            'grok': 'grok-4',
            'gpt': 'gpt-4o',
            'claude': 'claude-sonnet-4-5',
            'gemini': 'gemini-2.0-flash',
        }
        return aliases.get(model.lower(), model)

    # MARKER_166.FAVKEY.001: Auto-apply favorite key as preferred one-shot before MYCELIUM model call.
    def _apply_favorite_preferred_key(self, provider_name: str) -> None:
        """Load persisted favorites and set one-shot preferred key for provider if available."""
        try:
            normalized = str(provider_name or "").strip().lower()
            if not normalized:
                return
            if normalized == "google":
                normalized = "gemini"

            favorites_path = Path(__file__).resolve().parents[3] / "data" / "favorites.json"
            if not favorites_path.exists():
                return

            data = json.loads(favorites_path.read_text(encoding="utf-8"))
            keys = data.get("keys", [])
            if not isinstance(keys, list) or not keys:
                return

            favorite_masked = None
            for item in keys:
                if not isinstance(item, str) or ":" not in item:
                    continue
                prov, masked = item.split(":", 1)
                prov_norm = prov.strip().lower()
                if prov_norm == "google":
                    prov_norm = "gemini"
                if prov_norm == normalized and masked.strip():
                    favorite_masked = masked.strip()
                    break

            if not favorite_masked:
                return

            from src.utils.unified_key_manager import get_key_manager
            km = get_key_manager()
            km.set_preferred_key(normalized, favorite_masked)
            logger.info(f"[MYCELIUM_FAVORITE_KEY] Preferred key applied for {normalized}/{favorite_masked[:12]}...")
        except Exception as e:
            logger.debug(f"[MYCELIUM_FAVORITE_KEY] Failed to apply favorite key: {e}")

    def _track_usage_for_balance(self, provider: str, model: str, usage: Optional[Dict] = None):
        """Record usage to BalanceTracker after successful LLM call."""
        if not usage:
            return
        try:
            from src.services.balance_tracker import get_balance_tracker
            tracker = get_balance_tracker()

            tokens_in = (
                usage.get('prompt_tokens') or
                usage.get('input_tokens') or
                usage.get('promptTokenCount') or
                usage.get('prompt_eval_count') or
                0
            )
            tokens_out = (
                usage.get('completion_tokens') or
                usage.get('output_tokens') or
                usage.get('candidatesTokenCount') or
                usage.get('eval_count') or
                0
            )

            key_masked = self._get_current_key_masked(provider)
            tracker.record_usage(
                provider=provider or "unknown",
                key_masked=key_masked,
                model=model,
                tokens_in=tokens_in,
                tokens_out=tokens_out
            )
        except Exception as e:
            logger.debug(f"[MYCELIUM LLM] Usage tracking failed: {e}")

    def _get_current_key_masked(self, provider: str) -> str:
        """Get masked version of current active key for provider."""
        try:
            from src.utils.unified_key_manager import get_key_manager
            km = get_key_manager()
            key = km.get_key(provider) if provider else None
            if key and len(key) > 8:
                return f"{key[:4]}****{key[-4:]}"
            return "****"
        except Exception:
            return "****"

    # --- Context injection (async — already async in original) ---

    async def _gather_inject_context(self, inject_config: Dict[str, Any]) -> str:
        """Gather context from VETKA sources for injection.

        MARKER_135.FIX_ASYNC: Wrapped with global timeout (5s) to prevent blocking.
        Sync operations (Qdrant, Ollama embedding) run via run_in_executor.
        If any section hangs, it's skipped gracefully — pipeline continues.
        """
        import asyncio
        import concurrent.futures

        # MARKER_135.FIX_ASYNC: Global timeout for entire context gathering
        # Prevents pipeline from hanging on slow Ollama/Qdrant calls
        INJECT_TIMEOUT = 5.0  # seconds — if context takes longer, skip it

        try:
            return await asyncio.wait_for(
                self._gather_inject_context_inner(inject_config),
                timeout=INJECT_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.warning(f"[MYCELIUM INJECT] Context gathering timed out ({INJECT_TIMEOUT}s) — skipping")
            return ""
        except Exception as e:
            logger.warning(f"[MYCELIUM INJECT] Context gathering failed: {e}")
            return ""

    async def _gather_inject_context_inner(self, inject_config: Dict[str, Any]) -> str:
        """Inner context gathering — called within timeout wrapper."""
        context_parts = []

        # 1. Read files (fast, local I/O — no timeout needed)
        files = inject_config.get("files", [])
        if files:
            try:
                import os
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                for file_path in files[:10]:
                    full_path = os.path.join(project_root, file_path) if not file_path.startswith('/') else file_path
                    if os.path.exists(full_path):
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()[:8000]
                        context_parts.append(f"### File: {file_path}\n```\n{content}\n```")
                    else:
                        context_parts.append(f"### File: {file_path}\n(file not found)")
            except Exception as e:
                logger.warning(f"[MYCELIUM INJECT] File read error: {e}")

        # 2. Session state
        session_id = inject_config.get("session_id")
        if session_id:
            try:
                from src.mcp.state.mcp_state_manager import get_mcp_state_manager
                state_mgr = get_mcp_state_manager()
                state = await state_mgr.get_state(session_id)
                if state:
                    import json
                    context_parts.append(
                        f"### Session State: {session_id}\n```json\n"
                        f"{json.dumps(state, indent=2, ensure_ascii=False)[:2000]}\n```"
                    )
            except Exception as e:
                logger.warning(f"[MYCELIUM INJECT] Session state error: {e}")

        # 3. User preferences from Engram
        # MARKER_135.FIX_ASYNC: Wrapped in executor — Qdrant scroll() is sync
        if inject_config.get("include_prefs"):
            try:
                import asyncio
                loop = asyncio.get_event_loop()

                def _get_prefs_sync():
                    from src.memory.engram_user_memory import EngramUserMemory
                    from src.memory.qdrant_client import get_qdrant_client
                    qdrant = get_qdrant_client()
                    memory = EngramUserMemory(qdrant)
                    return memory.get_all_preferences("danila")

                prefs = await asyncio.wait_for(
                    loop.run_in_executor(None, _get_prefs_sync),
                    timeout=3.0
                )
                if prefs:
                    import json
                    context_parts.append(
                        f"### User Preferences\n```json\n"
                        f"{json.dumps(prefs, indent=2, ensure_ascii=False)[:1500]}\n```"
                    )
            except asyncio.TimeoutError:
                logger.warning("[MYCELIUM INJECT] Engram prefs timed out (3s)")
            except Exception as e:
                logger.warning(f"[MYCELIUM INJECT] Engram error: {e}")

        # 4. CAM active nodes
        if inject_config.get("include_cam"):
            try:
                from src.orchestration.cam_engine import get_cam_engine
                cam = get_cam_engine()
                if cam and hasattr(cam, 'get_active_nodes'):
                    nodes = cam.get_active_nodes(limit=5)
                    if nodes:
                        nodes_text = "\n".join(
                            [f"- {n.get('id', 'unknown')}: {n.get('content', '')[:200]}" for n in nodes]
                        )
                        context_parts.append(f"### CAM Active Context\n{nodes_text}")
            except Exception as e:
                logger.warning(f"[MYCELIUM INJECT] CAM error: {e}")

        # 5. Semantic search results
        # MARKER_135.FIX_ASYNC: Wrapped with per-section timeout — Ollama embedding can hang
        semantic_query = inject_config.get("semantic_query")
        if semantic_query:
            try:
                import asyncio
                from src.search.hybrid_search import get_hybrid_search
                search = get_hybrid_search()
                limit = inject_config.get("semantic_limit", 5)
                search_response = await asyncio.wait_for(
                    search.search(semantic_query, limit=limit),
                    timeout=3.0  # Ollama embedding + Qdrant search — 3s max
                )
                results = search_response.get("results", []) if isinstance(search_response, dict) else search_response
                if results:
                    search_text = []
                    for r in results[:limit]:
                        path = r.get("path", r.get("file_path", "unknown"))
                        score = r.get("score", 0)
                        snippet = r.get("content", "")[:300]
                        search_text.append(f"**{path}** (score: {score:.2f})\n{snippet}")
                    context_parts.append(
                        f"### Semantic Search: '{semantic_query}'\n" + "\n\n".join(search_text)
                    )
            except asyncio.TimeoutError:
                logger.warning(f"[MYCELIUM INJECT] Semantic search timed out (3s) for '{semantic_query[:30]}'")
            except Exception as e:
                logger.warning(f"[MYCELIUM INJECT] Semantic search error: {e}")

        # 6. Recent chat messages
        chat_id = inject_config.get("chat_id")
        if chat_id:
            try:
                from src.chat.chat_history_manager import get_chat_history_manager
                manager = get_chat_history_manager()
                max_msgs = inject_config.get("chat_limit", 10)
                digest = manager.get_chat_digest(chat_id, max_messages=max_msgs)
                recent = digest.get("recent_messages", [])
                if recent:
                    msg_lines = []
                    for m in recent[-max_msgs:]:
                        sender = m.get("sender_id", m.get("sender", "?"))
                        text = m.get("content", "")[:200]
                        ts = m.get("timestamp", "")[:19]
                        msg_lines.append(f"[{ts}] {sender}: {text}")
                    context_parts.append(f"### Recent Chat Messages\n" + "\n".join(msg_lines))
            except Exception as e:
                logger.warning(f"[MYCELIUM INJECT] Chat history error: {e}")

        # Combine
        if not context_parts:
            return ""

        full_context = "\n\n".join(context_parts)

        # 7. ELISION compression
        if inject_config.get("compress", True) and len(full_context) > 2000:
            try:
                from src.memory.elision import compress_context
                compressed = compress_context({"content": full_context})
                if compressed and len(compressed) < len(full_context):
                    full_context = compressed
                    logger.info(
                        f"[MYCELIUM INJECT] Compressed: {len(full_context)} chars "
                        f"(saved {100 - len(compressed) * 100 // len(full_context)}%)"
                    )
            except Exception as e:
                logger.warning(f"[MYCELIUM INJECT] Compression error: {e}")

        return f"<vetka_context>\n{full_context}\n</vetka_context>"

    # --- Main execute (THE KEY FIX — native async) ---

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute LLM call — native async, no ThreadPoolExecutor.

        This is the core fix for Phase 129:
        - Old: def execute() → ThreadPoolExecutor → asyncio.run() → blocks 60-300s
        - New: async def execute() → await call_model_v2() → non-blocking
        """
        model = self._normalize_model_name(arguments.get('model', ''))
        messages = list(arguments.get('messages', []))
        temperature = arguments.get('temperature', 0.7)
        max_tokens = arguments.get('max_tokens', 4096)
        tools = arguments.get('tools')
        inject_context = arguments.get('inject_context')
        model_source = arguments.get('model_source')
        allow_task_board_writes = bool(arguments.get("_allow_task_board_writes"))
        allow_edit_file_writes = bool(arguments.get("_allow_edit_file_writes"))
        effective_allowed_tools = get_effective_allowed_tool_names(
            SAFE_FUNCTION_CALLING_TOOLS,
            allow_edit_file_writes=allow_edit_file_writes,
        )

        # MARKER_129.2A: Security — filter tools by allowlist
        if tools:
            filtered_tools = []
            for tool_def in tools:
                tool_func_name = tool_def.get('function', {}).get('name', '') if isinstance(tool_def, dict) else ''
                if tool_func_name in effective_allowed_tools:
                    filtered_tools.append(tool_def)
                elif is_opted_in_write_tool(
                    tool_func_name,
                    allow_edit_file_writes=allow_edit_file_writes,
                ):
                    filtered_tools.append(tool_def)
                elif tool_func_name in WRITE_TOOLS_REQUIRING_APPROVAL:
                    logger.warning(f"[SECURITY] Blocked write tool '{tool_func_name}' from function calling")
                else:
                    logger.warning(f"[SECURITY] Blocked unknown tool '{tool_func_name}' — not in allowlist")
            tools = filtered_tools if filtered_tools else None

        # MARKER_129.2B: Context injection — direct await (no ThreadPoolExecutor!)
        if inject_context:
            try:
                injected_content = await self._gather_inject_context(inject_context)
                if injected_content:
                    has_system = any(m.get('role') == 'system' for m in messages)
                    if has_system:
                        for i, m in enumerate(messages):
                            if m.get('role') == 'system':
                                messages[i] = {
                                    'role': 'system',
                                    'content': m['content'] + '\n\n' + injected_content
                                }
                                break
                    else:
                        messages.insert(0, {
                            'role': 'system',
                            'content': injected_content
                        })
                    logger.info(f"[MYCELIUM INJECT] Added {len(injected_content)} chars to system prompt")
            except Exception as e:
                logger.warning(f"[MYCELIUM INJECT] Failed: {e}")

        # Reset expired rate-limit cooldowns
        try:
            from src.utils.unified_key_manager import get_key_manager
            km = get_key_manager()
            for provider_keys in km.keys.values():
                for record in provider_keys:
                    if record.rate_limited_at:
                        if record.cooldown_remaining() is None:
                            record.rate_limited_at = None
        except Exception:
            pass

        # Validate inputs
        if not model:
            return {'success': False, 'error': 'Model name is required', 'result': None}

        if not messages or not isinstance(messages, list):
            return {'success': False, 'error': 'Messages must be a non-empty array', 'result': None}

        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                return {'success': False, 'error': f'Message {i} must be an object with role and content', 'result': None}
            if 'role' not in msg or 'content' not in msg:
                return {'success': False, 'error': f'Message {i} missing role or content', 'result': None}

        try:
            # MARKER_129.2C: Direct async call — THE KEY FIX
            from src.elisya.provider_registry import call_model_v2, Provider

            provider_name = self._detect_provider(model, source=model_source)

            try:
                provider_enum = Provider(provider_name)
            except ValueError:
                logger.warning(f"Unknown provider '{provider_name}', using auto-detect")
                provider_enum = None

            # MARKER_166.FAVKEY.002: Auto-apply persisted favorite key before provider call.
            self._apply_favorite_preferred_key(provider_name)

            source_info = f" (source: {model_source})" if model_source else ""
            logger.info(f"[MYCELIUM LLM] Calling {model} via {provider_name}{source_info}")

            # MARKER_178.4.8: Universal REFLEX pre-hook for ALL LLM calls (async)
            messages, tools, _reflex_recs, reflex_meta = maybe_apply_reflex_to_direct_tools(
                arguments=arguments,
                messages=messages,
                tools=tools,
                provider_name=provider_name,
            )

            # MARKER_133.C33A: Use resilient wrapper with retry + fallback
            response = await resilient_llm_call(
                call_func=call_model_v2,
                messages=messages,
                model=model,
                provider_enum=provider_enum,
                source=model_source,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Normalize response
            if isinstance(response, dict):
                message_data = response.get("message", {})
                if not message_data and "content" in response:
                    # Some providers return flat dict
                    message_data = {"content": response["content"], "role": "assistant"}
            else:
                message_data = {"content": str(response), "role": "assistant"}

            content = message_data.get('content', '')
            tool_calls = message_data.get('tool_calls')

            result = {
                'content': content,
                'model': response.get('model', model) if isinstance(response, dict) else model,
                'provider': response.get('provider', provider_name) if isinstance(response, dict) else provider_name,
                'usage': response.get('usage') if isinstance(response, dict) else None,
            }

            # Security: filter response tool_calls
            if tool_calls:
                filtered_calls = filter_tool_calls(
                    tool_calls,
                    allowed_tool_names=effective_allowed_tools,
                    allow_task_board_writes=allow_task_board_writes,
                )
                dropped_calls = len(tool_calls) - len(filtered_calls)
                if dropped_calls:
                    logger.warning("[SECURITY] Filtered %d unsafe tool_call(s) from LLM response", dropped_calls)
                if filtered_calls:
                    result['tool_calls'] = filtered_calls
            if reflex_meta.get("enabled"):
                result["reflex"] = reflex_meta

            # Track usage
            self._track_usage_for_balance(provider_name, model, result.get('usage'))

            # MARKER_178.4.9: Universal REFLEX post-hook for ALL LLM calls (async)
            try:
                from src.services.reflex_integration import reflex_post_fc, _is_enabled
                if _is_enabled():
                    _tool_calls = result.get("tool_calls", [])
                    if _tool_calls:
                        _tool_execs = []
                        for tc in _tool_calls:
                            _fn = tc.get("function", {})
                            _tool_execs.append({
                                "name": _fn.get("name", "unknown"),
                                "success": True,
                                "result": {"content": "from_llm_response"}
                            })
                        _phase = arguments.get("_reflex_phase", "research")
                        _role = arguments.get("_reflex_role", "coder")
                        reflex_post_fc(_tool_execs, phase_type=_phase, agent_role=_role, subtask_id="llm_call")
            except Exception:
                pass

            return {
                'success': True,
                'result': result,
                'error': None
            }

        except ImportError as e:
            logger.error(f"[MYCELIUM LLM] Import error: {e}")
            return {'success': False, 'error': f'Failed to import provider registry: {str(e)}', 'result': None}
        except Exception as e:
            logger.error(f"[MYCELIUM LLM] Execution error: {e}")
            return {'success': False, 'error': f'LLM call failed: {str(e)}', 'result': None}
# MARKER_129.2_END
