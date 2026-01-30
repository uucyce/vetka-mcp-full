"""
VETKA Mention Handler - @mention parsing and direct model routing.

Handles @mention parsing and direct model routing with dependency injection.
Extracted from user_message_handler.py lines 603-891 (288 lines).

@status: active
@phase: 96
@depends: agents.agentic_tools, handler_utils, message_utils, chat.chat_history_manager, orchestration.cam_event_handler
@used_by: di_container
"""

import asyncio
import time
from typing import Dict, Any, Optional, Protocol, Callable, List

# Parse @mentions
from src.agents.agentic_tools import parse_mentions

# Handler utilities (context, persistence, keys)
from src.api.handlers.handler_utils import (
    sync_get_rich_context,
    format_context_for_agent,
    save_chat_message,
    get_openrouter_key,
    rotate_openrouter_key,
)

# Context builders
from src.api.handlers.message_utils import (
    format_history_for_prompt,
    build_pinned_context,
    build_viewport_summary,
    build_json_context,
    build_model_prompt,
)

# Chat history
from src.chat.chat_history_manager import get_chat_history_manager

# CAM event emission
from src.orchestration.cam_event_handler import emit_cam_event

# Response detection
from src.utils.chat_utils import detect_response_type


class IMentionParser(Protocol):
    """Protocol for @mention parsing and handling."""

    def parse_mentions(self, text: str) -> Dict[str, Any]:
        """Parse @mentions from user text."""
        ...

    async def handle_mention_call(
        self,
        sid: str,
        data: dict,
        parsed: dict
    ) -> bool:
        """
        Handle direct model call triggered by @mention.

        Returns:
            True if mention was handled (early return from main flow)
            False if should continue to regular agent flow
        """
        ...


class MentionHandler:
    """
    Handles @mention parsing and direct model routing.

    Extracts clean separation of @mention logic from main message handler.
    Uses dependency injection for socket, context builders, and model clients.
    """

    def __init__(self, sio):
        """
        Initialize mention handler.

        Args:
            sio: Socket.IO server instance for emitting events
        """
        self.sio = sio

    def parse_mentions(self, text: str) -> Dict[str, Any]:
        """
        Parse @mentions from user text.

        Delegates to parse_mentions from agentic_tools.

        Returns:
            {
                'mentions': [{'alias': '@deepseek', 'target': 'deepseek/deepseek-chat', 'type': 'model'}],
                'clean_message': 'fix main.py',
                'mode': 'single',  # auto | single | team | agents
                'models': ['deepseek/deepseek-chat'],
                'agents': []
            }
        """
        return parse_mentions(text)

    async def handle_mention_call(
        self,
        sid: str,
        data: dict,
        parsed: dict
    ) -> bool:
        """
        Handle direct model call triggered by @mention.

        This is the core extraction from lines 609-890 of user_message_handler.py.
        Handles:
        - Single model @mentions (bypass agent chain)
        - Direct Ollama calls with tool support
        - Direct OpenRouter calls with retry/rotation
        - Response streaming to frontend
        - Chat history persistence

        Args:
            sid: Socket.IO session ID
            data: Original message data from frontend
            parsed: Parsed mention data from parse_mentions()

        Returns:
            True if mention was handled (early return from main flow)
            False if should continue to regular agent flow
        """
        # Extract data
        text = data.get('text', '')
        node_id = data.get('node_id')
        node_path = data.get('node_path')
        pinned_files = data.get('pinned_files', [])
        viewport_context = data.get('viewport_context', {})
        request_node_id = data.get('request_node_id', node_id)
        request_timestamp = data.get('request_timestamp', int(time.time() * 1000))

        clean_text = parsed['clean_message']

        # Log mentions
        if parsed['mentions']:
            print(f"[MENTIONS] Found: {[m['alias'] for m in parsed['mentions']]}")
            print(f"[MENTIONS] Mode: {parsed['mode']}, Clean text: {clean_text[:50]}...")

        # Check if specific model mentioned (NOT agent)
        if parsed['mode'] == 'single' and parsed['models']:
            model_to_use = parsed['models'][0]
            is_ollama = model_to_use.startswith('ollama:')

            print(f"[MENTIONS] Direct MODEL call: {model_to_use}")

            # Emit routing status
            routing_text = f"Routing to **{model_to_use}**..."
            await self.sio.emit('agent_message', {
                'agent': 'Hostess',
                'model': 'routing',
                'content': routing_text,
                'text': routing_text,
                'node_id': request_node_id,
                'node_path': node_path,
                'timestamp': request_timestamp,
                'response_type': 'status',
                'force_artifact': False
            }, to=sid)

            # ========================================
            # DIRECT MODEL CALL (bypass agents)
            # ========================================
            try:
                # Load chat history
                chat_history = get_chat_history_manager()
                chat_id = chat_history.get_or_create_chat(node_path)
                history_messages = chat_history.get_chat_messages(chat_id)
                history_context = format_history_for_prompt(history_messages, max_messages=10)

                print(f"[MENTION] @mention call: Loaded {len(history_messages)} history messages")

                # Get file context for the model
                rich_context = sync_get_rich_context(node_path)
                if rich_context.get('error'):
                    context_for_model = f"File: {node_path}\nStatus: {rich_context['error']}"
                else:
                    context_for_model = format_context_for_agent(rich_context, 'generic')

                # Build pinned files context with smart selection
                pinned_context = build_pinned_context(pinned_files, user_query=clean_text) if pinned_files else ""

                # Build viewport summary for spatial awareness
                viewport_summary = build_viewport_summary(viewport_context) if viewport_context else ""

                # Build JSON dependency context for AI agents
                # Pass session_id for cold start legend detection
                # Pass model_name for per-model legend tracking
                json_context = build_json_context(
                    pinned_files,
                    viewport_context,
                    session_id=sid,
                    model_name=model_to_use
                )

                # Save user message BEFORE model call
                # Pass pinned_files for group chat context
                save_chat_message(node_path, {
                    'role': 'user',
                    'text': text,  # Original text (with @mention)
                    'node_id': node_id
                }, pinned_files=pinned_files)

                # Build prompt with all context
                model_prompt = build_model_prompt(
                    clean_text,
                    context_for_model,
                    pinned_context,
                    history_context,
                    viewport_summary,
                    json_context
                )

                # Call the model directly
                response_text = None

                if is_ollama:
                    response_text = await self._call_ollama_model(
                        model_to_use,
                        model_prompt
                    )
                else:
                    response_text = await self._call_openrouter_model(
                        model_to_use,
                        model_prompt
                    )

                print(f"[MENTION] Got response: {len(response_text)} chars")

                # Emit the response
                agent_short_name = model_to_use.split('/')[-1].split(':')[-1]
                await self.sio.emit('agent_message', {
                    'agent': agent_short_name,
                    'model': model_to_use,
                    'content': response_text,
                    'text': response_text,
                    'node_id': request_node_id,
                    'node_path': node_path,
                    'timestamp': request_timestamp,
                    'response_type': detect_response_type(response_text),
                    'force_artifact': len(response_text) > 800
                }, to=sid)

                # Emit chat_response for chat panel
                await self.sio.emit('chat_response', {
                    'message': response_text,
                    'agent': agent_short_name,
                    'model': model_to_use,
                    'workflow_id': f"direct_{request_timestamp}"
                }, to=sid)

                # Save to chat history
                save_chat_message(node_path, {
                    'role': 'assistant',
                    'agent': model_to_use,
                    'text': response_text,
                    'node_id': node_id
                }, pinned_files=pinned_files)

                # Emit message_sent event for surprise calculation
                try:
                    chat_history = get_chat_history_manager()
                    chat_id = chat_history.get_or_create_chat(node_path)
                    await emit_cam_event("message_sent", {
                        "chat_id": chat_id,
                        "content": response_text,
                        "role": "assistant"
                    }, source="@mention_call")
                except Exception as cam_err:
                    print(f"[CAM] Message event error (non-critical): {cam_err}")

                print(f"[MENTION] Direct model call complete")
                return True  # Early return - skip agent chain!

            except Exception as e:
                print(f"[MENTION] Error calling model: {e}")
                error_msg = f"Error calling {model_to_use}: {str(e)[:200]}"
                await self.sio.emit('agent_message', {
                    'agent': 'System',
                    'model': 'error',
                    'content': error_msg,
                    'text': error_msg,
                    'node_id': request_node_id,
                    'node_path': node_path,
                    'timestamp': request_timestamp,
                    'response_type': 'error',
                    'force_artifact': False
                }, to=sid)

                # Also emit chat_response for error
                await self.sio.emit('chat_response', {
                    'message': error_msg,
                    'agent': 'System',
                    'model': 'error'
                }, to=sid)
                return True  # Still early return on error

        # No single model mention - continue to regular flow
        return False

    async def _call_ollama_model(self, model_to_use: str, model_prompt: str) -> str:
        """
        Call Ollama model directly with tool support.

        Args:
            model_to_use: Model name (e.g., 'ollama:qwen2:7b')
            model_prompt: Formatted prompt with all context

        Returns:
            Response text from model
        """
        # Ollama model (e.g., ollama:qwen2:7b)
        ollama_model = model_to_use.replace('ollama:', '')
        print(f"[MENTION] Calling Ollama: {ollama_model}")

        import ollama

        # Get tools for direct model calls
        from src.agents.tools import get_tools_for_agent
        from src.tools import SafeToolExecutor, ToolCall
        model_tools = get_tools_for_agent('Dev')  # Dev has most tools
        print(f"[MENTION] Tools available: {len(model_tools)}")

        # Build messages with tool guidance
        tool_system = """You have access to tools. Use them when appropriate:
- camera_focus: Move 3D camera to show user specific files/folders. USE THIS when asked to show/navigate/focus on something.
- search_semantic: Search codebase by meaning
- get_tree_context: Get file structure context

When user asks to "show", "focus", "navigate to" a file - USE camera_focus tool!"""

        messages_with_tools = [
            {'role': 'system', 'content': tool_system},
            {'role': 'user', 'content': model_prompt}
        ]

        # Run sync ollama call in executor
        loop = asyncio.get_event_loop()
        ollama_response = await loop.run_in_executor(
            None,
            lambda: ollama.chat(
                model=ollama_model,
                messages=messages_with_tools,
                tools=model_tools,
                stream=False
            )
        )

        # Handle tool calls from Ollama
        response_text = None
        if hasattr(ollama_response, 'message') and ollama_response.message.tool_calls:
            print(f"[MENTION] Tool calls received: {len(ollama_response.message.tool_calls)}")
            executor = SafeToolExecutor()
            tool_results = []

            for tc in ollama_response.message.tool_calls:
                func_name = tc.function.name
                func_args = tc.function.arguments
                print(f"[MENTION] Executing: {func_name}({func_args})")

                call = ToolCall(
                    tool_name=func_name,
                    arguments=func_args,
                    agent_type='Dev',
                    call_id=f"direct_{func_name}"
                )
                result = await executor.execute(call)

                tool_results.append({
                    'tool': func_name,
                    'args': func_args,
                    'success': result.success,
                    'result': result.result,
                    'error': result.error
                })
                print(f"[MENTION] Result: success={result.success}")

            # Build response with tool execution info
            if tool_results:
                tool_summary = "\n".join([
                    f"* {tr['tool']}({tr['args']}) -> {tr['result'].get('message', 'done') if tr['success'] else tr['error']}"
                    for tr in tool_results
                ])
                response_text = f"Executed tools:\n{tool_summary}"

                # If camera_focus was called, add friendly message
                camera_calls = [tr for tr in tool_results if tr['tool'] == 'camera_focus']
                if camera_calls:
                    target = camera_calls[0]['args'].get('target', 'unknown')
                    response_text = f"Camera focused on: **{target}**\n\nThe 3D view should now be showing this location."

        if response_text is None:
            # No tool calls, get text response
            if hasattr(ollama_response, 'message'):
                response_text = ollama_response.message.content or 'No response'
            else:
                response_text = ollama_response.get('message', {}).get('content', 'No response')

        return response_text

    async def _call_openrouter_model(self, model_to_use: str, model_prompt: str) -> str:
        """
        Call OpenRouter model with retry and key rotation.

        Args:
            model_to_use: Model name (e.g., 'anthropic/claude-3-haiku')
            model_prompt: Formatted prompt with all context

        Returns:
            Response text from model
        """
        import requests

        response_text = None
        max_retries = 3

        for attempt in range(max_retries):
            api_key = get_openrouter_key()
            print(f"[MENTION] Calling OpenRouter: {model_to_use} (attempt {attempt + 1}/{max_retries})")

            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'http://localhost:5001',
                'X-Title': 'VETKA'
            }
            payload = {
                'model': model_to_use,
                'messages': [{'role': 'user', 'content': model_prompt}],
                'max_tokens': 999999,  # Phase 92.4: Unlimited responses
                'temperature': 0.7
            }

            try:
                # Run sync request in executor
                loop = asyncio.get_event_loop()
                resp = await loop.run_in_executor(
                    None,
                    lambda: requests.post(
                        'https://openrouter.ai/api/v1/chat/completions',
                        headers=headers,
                        json=payload,
                        timeout=60
                    )
                )

                if resp.status_code == 200:
                    response_text = resp.json()['choices'][0]['message']['content']
                    break  # Success!

                elif resp.status_code in [401, 402]:
                    print(f"[MENTION] Key failed ({resp.status_code}), rotating...")
                    rotate_openrouter_key(mark_failed=True)
                    continue

                else:
                    print(f"[MENTION] OpenRouter error: {resp.status_code} - {resp.text[:200]}")
                    response_text = f"Error calling {model_to_use}: {resp.status_code}"
                    break

            except requests.exceptions.Timeout:
                print(f"[MENTION] Timeout, trying next key...")
                rotate_openrouter_key(mark_failed=False)
                continue

        if response_text is None:
            response_text = f"All API keys failed for {model_to_use}. Please check your OpenRouter account."

        return response_text
