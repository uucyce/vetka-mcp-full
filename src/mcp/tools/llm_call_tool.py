"""MCP Tool: vetka_call_model - Universal LLM call through VETKA infrastructure.

Calls any LLM model through VETKA's provider registry (Grok, GPT, Claude, Gemini, Ollama, OpenRouter).
Supports context injection from VETKA sources (files, session state, Engram preferences, CAM, semantic search).

Features:
- Multi-provider support via provider_registry.call_model_v2
- Context injection with ELISION compression (Phase 55.2)
- Streaming to VETKA "Molniya" group chat (Phase 90.4.0)
- Function calling for compatible models
- API key rotation with rate-limit cooldown handling (Phase 93.5)

Supported models:
- grok-4 (x.ai/Grok)
- gpt-4o, gpt-4-turbo (OpenAI)
- claude-opus-4-5, claude-sonnet-4-5 (Anthropic)
- gemini-2.0-flash, gemini-1.5-pro (Google)
- llama3.1:8b, deepseek-llm:7b (Ollama local)
- mistralai/mistral-7b (OpenRouter)

@status: active
@phase: 96
@depends: src/mcp/tools/base_tool.py, src/elisya/provider_registry.py, src/utils/unified_key_manager.py, src/memory (elision, engram_user_memory, qdrant_client), src/orchestration/cam_engine.py, src/search/hybrid_search.py, src/initialization/components_init.py (socketio)
@used_by: src/mcp/vetka_mcp_bridge.py
"""

from typing import Any, Dict, List, Optional
import logging
from .base_tool import BaseMCPTool

logger = logging.getLogger(__name__)

# MARKER_90.4.0_START: VETKA chat ID for call_model streaming
LIGHTNING_CHAT_ID = "5e2198c2-8b1a-45df-807f-5c73c5496aa8"  # "Молния" group
# MARKER_90.4.0_END


class LLMCallTool(BaseMCPTool):
    """LLM call tool - route to any provider through VETKA"""

    @property
    def name(self) -> str:
        return "vetka_call_model"

    @property
    def description(self) -> str:
        return (
            "Call any LLM model through VETKA infrastructure. Supports Grok (x.ai), GPT (OpenAI), "
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
                            "role": {
                                "type": "string",
                                "enum": ["user", "assistant", "system"]
                            },
                            "content": {
                                "type": "string"
                            }
                        },
                        "required": ["role", "content"]
                    }
                },
                "temperature": {
                    "type": "number",
                    "description": "Sampling temperature (0.0-2.0, default: 0.7). Higher = more creative.",
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
                    "description": "Optional function calling tools (OpenAI format). Only supported by some models.",
                    "items": {
                        "type": "object"
                    }
                },
                "inject_context": {
                    "type": "object",
                    "description": (
                        "Phase 55.2: Auto-inject VETKA context into system prompt. "
                        "VETKA will gather context from specified sources and prepend to messages. "
                        "This saves tokens - you don't need to pass file contents in messages."
                    ),
                    "properties": {
                        "files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "File paths to read and inject (e.g., ['src/main.py', 'README.md'])"
                        },
                        "session_id": {
                            "type": "string",
                            "description": "MCPStateManager session ID to load state from"
                        },
                        "include_prefs": {
                            "type": "boolean",
                            "description": "Include user preferences from Engram memory",
                            "default": False
                        },
                        "include_cam": {
                            "type": "boolean",
                            "description": "Include CAM (Context-Aware Memory) active nodes",
                            "default": False
                        },
                        "semantic_query": {
                            "type": "string",
                            "description": "Semantic search query to find relevant context"
                        },
                        "semantic_limit": {
                            "type": "integer",
                            "description": "Max results for semantic search (default: 5)",
                            "default": 5
                        },
                        "compress": {
                            "type": "boolean",
                            "description": "Apply ELISION compression to injected context",
                            "default": True
                        }
                    }
                }
            },
            "required": ["model", "messages"]
        }

    def _detect_provider(self, model: str) -> str:
        """
        Detect provider from model name.

        Phase 90.1.4.1: NOW USES CANONICAL detect_provider from provider_registry.

        # MARKER_90.1.4.1_START: Use canonical detect_provider
        Returns:
            Provider enum name: 'xai', 'openai', 'anthropic', 'google', 'ollama', 'openrouter'
        """
        from src.elisya.provider_registry import ProviderRegistry

        # Use canonical implementation
        canonical_provider = ProviderRegistry.detect_provider(model)

        # Return the enum value (string)
        return canonical_provider.value
        # MARKER_90.1.4.1_END

    def _normalize_model_name(self, model: str) -> str:
        """Normalize short model names to full versions"""
        aliases = {
            'grok': 'grok-4',
            'gpt': 'gpt-4o',
            'claude': 'claude-sonnet-4-5',
            'gemini': 'gemini-2.0-flash',
        }
        return aliases.get(model.lower(), model)

    # MARKER_90.4.0_START: Chat streaming methods
    def _emit_to_chat(self, sender_id: str, content: str, message_type: str = "chat"):
        """
        Emit message to VETKA "Молния" chat.

        Args:
            sender_id: Sender identifier (e.g., '@grok-4', '@user')
            content: Message content
            message_type: Type of message (chat, response, system)
        """
        try:
            from src.initialization.components_init import get_socketio
            from datetime import datetime
            import asyncio

            socketio = get_socketio()
            if not socketio:
                logger.debug("[LLM_CALL_TOOL] SocketIO not available, skipping chat emit")
                return

            # Prepare message data
            message_data = {
                'group_id': LIGHTNING_CHAT_ID,
                'sender_id': sender_id,
                'content': content,
                'message_type': message_type,
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'source': 'vetka_call_model',
                    'mcp_tool': True
                }
            }

            # Emit synchronously (socket.io will handle async internally)
            room = f'group_{LIGHTNING_CHAT_ID}'

            # Create a simple async wrapper to emit
            async def emit_async():
                await socketio.emit('group_message', message_data, room=room)

            # Run in event loop if available, otherwise skip
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule as a task
                    asyncio.create_task(emit_async())
                else:
                    # Run directly
                    asyncio.run(emit_async())
            except Exception as e:
                logger.debug(f"[LLM_CALL_TOOL] Could not emit to chat (no event loop): {e}")

        except Exception as e:
            logger.warning(f"[LLM_CALL_TOOL] Failed to emit to chat: {e}")

    def _emit_request_to_chat(self, model: str, messages: List[Dict], temperature: float, max_tokens: int):
        """Emit LLM request to VETKA chat"""
        # Get last user message for preview
        user_messages = [m for m in messages if m.get('role') == 'user']
        last_message = user_messages[-1]['content'] if user_messages else '(no user message)'

        # Truncate long messages
        preview = last_message[:200]
        if len(last_message) > 200:
            preview += "..."

        # Format request message
        content = f"**[MCP call_model]** {model}\n"
        content += f"Temperature: {temperature}, Max tokens: {max_tokens}\n"
        content += f"```\n{preview}\n```"

        self._emit_to_chat('@user', content, 'system')

    def _emit_response_to_chat(self, model: str, content: str, usage: Optional[Dict] = None):
        """Emit LLM response to VETKA chat"""
        # Format usage info if available
        usage_str = ""
        if usage:
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            total_tokens = usage.get('total_tokens', 0)
            usage_str = f"\n\n*Tokens: {prompt_tokens} → {completion_tokens} (total: {total_tokens})*"

        # Emit as response from the model
        response_content = content + usage_str
        self._emit_to_chat(f'@{model}', response_content, 'response')
    # MARKER_90.4.0_END

    # MARKER_55.2_START: Context injection for MCP
    async def _gather_inject_context(self, inject_config: Dict[str, Any]) -> str:
        """
        Phase 55.2: Gather context from VETKA sources for injection.

        Args:
            inject_config: Configuration dict with sources to gather from

        Returns:
            Formatted context string to prepend to system prompt
        """
        context_parts = []

        # 1. Read files
        files = inject_config.get("files", [])
        if files:
            try:
                import os
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                for file_path in files[:10]:  # Limit to 10 files
                    full_path = os.path.join(project_root, file_path) if not file_path.startswith('/') else file_path
                    if os.path.exists(full_path):
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()[:8000]  # Limit per file
                        context_parts.append(f"### File: {file_path}\n```\n{content}\n```")
                    else:
                        context_parts.append(f"### File: {file_path}\n(file not found)")
            except Exception as e:
                logger.warning(f"[INJECT_CONTEXT] File read error: {e}")

        # 2. Load session state from MCPStateManager
        session_id = inject_config.get("session_id")
        if session_id:
            try:
                from src.mcp.state.mcp_state_manager import get_mcp_state_manager
                state_mgr = get_mcp_state_manager()
                state = await state_mgr.get_state(session_id)
                if state:
                    import json
                    context_parts.append(f"### Session State: {session_id}\n```json\n{json.dumps(state, indent=2, ensure_ascii=False)[:2000]}\n```")
            except Exception as e:
                logger.warning(f"[INJECT_CONTEXT] Session state error: {e}")

        # 3. User preferences from Engram
        if inject_config.get("include_prefs"):
            try:
                from src.memory.engram_user_memory import EngramUserMemory
                from src.memory.qdrant_client import get_qdrant_client
                qdrant = get_qdrant_client()
                memory = EngramUserMemory(qdrant)
                prefs = memory.get_all_preferences("danila")  # Default user
                if prefs:
                    import json
                    context_parts.append(f"### User Preferences\n```json\n{json.dumps(prefs, indent=2, ensure_ascii=False)[:1500]}\n```")
            except Exception as e:
                logger.warning(f"[INJECT_CONTEXT] Engram error: {e}")

        # 4. CAM active nodes
        if inject_config.get("include_cam"):
            try:
                from src.orchestration.cam_engine import get_cam_engine
                cam = get_cam_engine()
                if cam and hasattr(cam, 'get_active_nodes'):
                    nodes = cam.get_active_nodes(limit=5)
                    if nodes:
                        nodes_text = "\n".join([f"- {n.get('id', 'unknown')}: {n.get('content', '')[:200]}" for n in nodes])
                        context_parts.append(f"### CAM Active Context\n{nodes_text}")
            except Exception as e:
                logger.warning(f"[INJECT_CONTEXT] CAM error: {e}")

        # 5. Semantic search results
        semantic_query = inject_config.get("semantic_query")
        if semantic_query:
            try:
                from src.search.hybrid_search import HybridSearch
                search = HybridSearch()
                limit = inject_config.get("semantic_limit", 5)
                results = await search.search(semantic_query, limit=limit)
                if results:
                    search_text = []
                    for r in results[:limit]:
                        path = r.get("path", r.get("file_path", "unknown"))
                        score = r.get("score", 0)
                        snippet = r.get("content", "")[:300]
                        search_text.append(f"**{path}** (score: {score:.2f})\n{snippet}")
                    context_parts.append(f"### Semantic Search: '{semantic_query}'\n" + "\n\n".join(search_text))
            except Exception as e:
                logger.warning(f"[INJECT_CONTEXT] Semantic search error: {e}")

        # Combine all context
        if not context_parts:
            return ""

        full_context = "\n\n".join(context_parts)

        # 6. Apply ELISION compression if requested
        if inject_config.get("compress", True) and len(full_context) > 2000:
            try:
                from src.memory.elision import compress_context
                compressed = compress_context({"content": full_context})
                if compressed and len(compressed) < len(full_context):
                    full_context = compressed
                    logger.info(f"[INJECT_CONTEXT] Compressed: {len(full_context)} chars (saved {100 - len(compressed)*100//len(full_context)}%)")
            except Exception as e:
                logger.warning(f"[INJECT_CONTEXT] Compression error: {e}")

        return f"<vetka_context>\n{full_context}\n</vetka_context>"
    # MARKER_55.2_END

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute LLM call through VETKA provider registry"""

        model = self._normalize_model_name(arguments.get('model', ''))
        messages = list(arguments.get('messages', []))  # Copy to avoid mutation
        temperature = arguments.get('temperature', 0.7)
        max_tokens = arguments.get('max_tokens', 4096)
        tools = arguments.get('tools')
        inject_context = arguments.get('inject_context')

        # MARKER_55.2_START: Process context injection
        if inject_context:
            try:
                import asyncio
                # Gather context from VETKA sources
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            self._gather_inject_context(inject_context)
                        )
                        injected_content = future.result()
                else:
                    injected_content = asyncio.run(self._gather_inject_context(inject_context))

                if injected_content:
                    # Prepend to system message or create one
                    has_system = any(m.get('role') == 'system' for m in messages)
                    if has_system:
                        # Append to existing system message
                        for i, m in enumerate(messages):
                            if m.get('role') == 'system':
                                messages[i] = {
                                    'role': 'system',
                                    'content': m['content'] + '\n\n' + injected_content
                                }
                                break
                    else:
                        # Insert new system message at the beginning
                        messages.insert(0, {
                            'role': 'system',
                            'content': injected_content
                        })
                    logger.info(f"[INJECT_CONTEXT] Added {len(injected_content)} chars to system prompt")
            except Exception as e:
                logger.warning(f"[INJECT_CONTEXT] Failed to inject context: {e}")
        # MARKER_55.2_END

        # MARKER_93.5_MCP_KEY_RESET: Reset expired rate-limit cooldowns
        # Phase 93.5: MCP runs in subprocess with singleton key manager
        # Old rate-limit marks might persist across multiple MCP calls
        # Reset any expired cooldowns to allow retry on previously-failed keys
        try:
            from src.utils.unified_key_manager import get_key_manager
            km = get_key_manager()
            for provider_keys in km.keys.values():
                for record in provider_keys:
                    if record.rate_limited_at:
                        # Check if cooldown has expired
                        if record.cooldown_remaining() is None:
                            # Cooldown expired, reset the rate_limited_at timestamp
                            record.rate_limited_at = None
                            logger.debug(f"[MCP_KEY_RESET] Key {record.mask()} cooldown expired, reset available")
        except Exception as e:
            logger.warning(f"[MCP_KEY_RESET] Failed to reset key cooldowns: {e}")

        # Validate inputs
        if not model:
            return {
                'success': False,
                'error': 'Model name is required',
                'result': None
            }

        if not messages or not isinstance(messages, list):
            return {
                'success': False,
                'error': 'Messages must be a non-empty array',
                'result': None
            }

        # Validate message format
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                return {
                    'success': False,
                    'error': f'Message {i} must be an object with role and content',
                    'result': None
                }
            if 'role' not in msg or 'content' not in msg:
                return {
                    'success': False,
                    'error': f'Message {i} missing role or content',
                    'result': None
                }

        try:
            # Import provider registry
            from src.elisya.provider_registry import call_model_v2, Provider
            from src.utils.unified_key_manager import get_key_manager, ProviderType
            import asyncio

            # Detect provider
            provider_name = self._detect_provider(model)

            # Convert provider string to enum
            try:
                provider_enum = Provider(provider_name)
            except ValueError:
                logger.warning(f"Unknown provider '{provider_name}', using auto-detect")
                provider_enum = None  # Let call_model_v2 auto-detect

            logger.info(f"[LLM_CALL_TOOL] Calling {model} via {provider_name}")

            # MARKER_93.5_MCP_DIAGNOSTIC: Log key availability before call
            # Phase 93.5: Debug MCP 429 errors by tracking which keys are used
            if provider_name == "openai":
                km = get_key_manager()
                openai_keys = km.keys.get(ProviderType.OPENAI, [])
                available_count = sum(1 for k in openai_keys if k.is_available())
                logger.info(f"[MCP_KEY_DEBUG] OpenAI: {available_count}/{len(openai_keys)} keys available")
                for i, key in enumerate(openai_keys):
                    cooldown_info = f", cooldown: {key.cooldown_remaining()}" if key.rate_limited_at else ""
                    logger.debug(f"[MCP_KEY_DEBUG]   Key {i}: {key.mask()} - available: {key.is_available()}{cooldown_info}")

            # MARKER_90.4.0_START: Emit request to VETKA chat
            self._emit_request_to_chat(model, messages, temperature, max_tokens)
            # MARKER_90.4.0_END

            # Call model asynchronously
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If event loop is already running, use run_in_executor
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        call_model_v2(
                            messages=messages,
                            model=model,
                            provider=provider_enum,
                            tools=tools,
                            temperature=temperature,
                            max_tokens=max_tokens
                        )
                    )
                    response = future.result()
            else:
                # No event loop running, create one
                response = asyncio.run(
                    call_model_v2(
                        messages=messages,
                        model=model,
                        provider=provider_enum,
                        tools=tools,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                )

            # Extract response content
            message_data = response.get('message', {})
            content = message_data.get('content', '')
            tool_calls = message_data.get('tool_calls')

            # Build result
            result = {
                'content': content,
                'model': response.get('model', model),
                'provider': response.get('provider', provider_name),
                'usage': response.get('usage'),
            }

            if tool_calls:
                result['tool_calls'] = tool_calls

            # MARKER_90.4.0_START: Emit response to VETKA chat
            self._emit_response_to_chat(model, content, result.get('usage'))
            # MARKER_90.4.0_END

            return {
                'success': True,
                'result': result,
                'error': None
            }

        except ImportError as e:
            logger.error(f"[LLM_CALL_TOOL] Import error: {e}")
            return {
                'success': False,
                'error': f'Failed to import provider registry: {str(e)}',
                'result': None
            }
        except Exception as e:
            logger.error(f"[LLM_CALL_TOOL] Execution error: {e}")
            return {
                'success': False,
                'error': f'LLM call failed: {str(e)}',
                'result': None
            }
