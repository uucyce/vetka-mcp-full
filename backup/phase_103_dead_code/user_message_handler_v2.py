"""
VETKA User Message Handler V2 - Slim Orchestrator.

Main Socket.IO handler for user messages with clean architecture.
Replaces user_message_handler.py (1694 lines -> ~200 lines).

Architecture:
  user_message (SIO) -> DIContainer -> [ContextBuilder, ModelClient,
  MentionHandler, HostessRouter, AgentOrchestrator, ResponseManager]

Old handler: 1694 lines, 10+ responsibilities
New handler: ~200 lines, 1 responsibility (orchestration)

@status: dead
@phase: 103 (marked dead)
@reason: Never registered in __init__.py - user_message_handler.py still active
@depends: di_container, chat.chat_registry, orchestration.cam_event_handler, handler_utils, agents.hostess_agent
@used_by: NONE - was intended for main.py but switch never happened
"""

import time
import asyncio
from pathlib import Path

from src.chat.chat_registry import ChatRegistry, Message
from src.chat.chat_history_manager import get_chat_history_manager
from src.orchestration.cam_event_handler import emit_cam_event
from src.api.handlers.handler_utils import (
    get_agents,
    save_chat_message,
    HOSTESS_AVAILABLE,
)
from src.agents.hostess_agent import get_hostess

# MARKER_90.1.2_START: Hostess timeout wrapper
HOSTESS_TIMEOUT = 15  # seconds

async def call_hostess_with_timeout(hostess, text, context):
    """
    Run hostess.process() with timeout to prevent blocking.

    The sync hostess.process() call can block the entire event loop.
    This wrapper runs it in an executor with a timeout.

    Args:
        hostess: Hostess agent instance
        text: User message text
        context: Rich context dict

    Returns:
        Hostess decision dict or None on timeout
    """
    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: hostess.process(text, context=context)),
            timeout=HOSTESS_TIMEOUT
        )
        return result
    except asyncio.TimeoutError:
        print(f"[Hostess] ⚠️ Timeout after {HOSTESS_TIMEOUT}s")
        return None
# MARKER_90.1.2_END

# Optional Hostess context builder
def get_hostess_context_builder():
    """Get HostessContextBuilder for rich context (Phase 44)."""
    try:
        from src.orchestration.hostess_context_builder import get_hostess_context_builder as _get_builder
        return _get_builder()
    except Exception:
        return None


def register_user_message_handler(sio, app=None):
    """
    Register the SLIM user_message Socket.IO handler.

    This replaces the 1694-line God Object with a clean orchestrator
    that delegates to specialized modules.

    Args:
        sio: Socket.IO AsyncServer instance
        app: Optional Flask/Sanic app reference
    """

    # Initialize DI container
    from .di_container import get_container
    container = get_container(sio, app)

    @sio.on('user_message')
    async def handle_user_message(sid, data):
        """
        User message handler - SLIM VERSION.

        Flow:
        1. Parse input and normalize paths
        2. Direct model call? → ModelClient
        3. @mention? → MentionHandler
        4. Hostess routing → HostessRouter
        5. Agent chain → AgentOrchestrator
        6. Emit responses → ResponseManager
        7. Generate summary if multi-agent
        """

        # ========================================
        # STEP 1: PARSE INPUT
        # ========================================
        client_id = sid[:8]
        text = data.get('text', '').strip()
        node_id = data.get('node_id', 'root')
        raw_node_path = data.get('node_path', 'unknown')

        # Normalize path to prevent duplicate chats
        if raw_node_path not in ('unknown', 'root', ''):
            try:
                node_path = str(Path(raw_node_path).resolve())
            except Exception:
                node_path = raw_node_path
        else:
            node_path = raw_node_path

        # Extract optional parameters
        requested_model = data.get('model')
        pinned_files = data.get('pinned_files', [])
        viewport_context = data.get('viewport_context', None)

        # Request metadata
        request_node_id = node_id
        request_timestamp = time.time()

        print(f"\n[HANDLER_V2] User message from {client_id}: {text[:50]}... (node: {node_path})")

        if pinned_files:
            print(f"[HANDLER_V2] Pinned files: {len(pinned_files)} files")
        if viewport_context:
            print(f"[HANDLER_V2] Viewport: {viewport_context.get('total_pinned', 0)} pinned, {viewport_context.get('total_visible', 0)} visible")

        # Validate input
        if not text:
            await sio.emit('agent_error', {'error': 'Empty message'}, to=sid)
            return

        # Setup session chat manager
        chat_manager = ChatRegistry.get_manager(sid)
        if node_path and node_path not in ('unknown', 'root'):
            chat_manager.set_context(node_path)

        # Add user message to session history
        chat_manager.add_message(Message(
            role='user',
            content=text,
            node_path=node_path
        ))

        # ========================================
        # STEP 2: DIRECT MODEL CALL (Model Directory)
        # ========================================
        if requested_model:
            print(f"[HANDLER_V2] Direct model call: {requested_model}")

            # Emit routing status
            await sio.emit('agent_message', {
                'agent': 'Hostess',
                'model': 'routing',
                'content': f"Routing to **{requested_model}**...",
                'text': f"Routing to **{requested_model}**...",
                'node_id': request_node_id,
                'node_path': node_path,
                'timestamp': request_timestamp,
                'response_type': 'status',
                'force_artifact': False
            }, to=sid)

            # Build context
            context = await container.context_builder.build_context(
                node_path=node_path,
                text=text,
                pinned_files=pinned_files,
                viewport_context=viewport_context,
                session_id=sid,
                model_name=requested_model
            )

            # Save user message BEFORE model call
            save_chat_message(node_path, {
                'role': 'user',
                'text': text,
                'node_id': node_id
            }, pinned_files=pinned_files)

            # Call model
            result = await container.model_client.call_model(
                model_name=requested_model,
                prompt=context['model_prompt'],
                session_id=sid,
                node_id=node_id,
                node_path=node_path
            )

            # Save response
            if result['success']:
                save_chat_message(node_path, {
                    'role': 'assistant',
                    'agent': requested_model,
                    'text': result['response_text'],
                    'node_id': node_id
                }, pinned_files=pinned_files)

                # Emit CAM event
                try:
                    chat_history = get_chat_history_manager()
                    chat_id = chat_history.get_or_create_chat(node_path)
                    await emit_cam_event("message_sent", {
                        "chat_id": chat_id,
                        "content": result['response_text'],
                        "role": "assistant"
                    }, source="direct_model_call")
                except Exception as cam_err:
                    print(f"[CAM] Message event error (non-critical): {cam_err}")

            print(f"[HANDLER_V2] Direct model call complete")
            return  # Early return

        # ========================================
        # STEP 3: @MENTION HANDLING
        # ========================================
        parsed_mentions = container.mention_handler.parse_mentions(text)

        # Check if @mention should handle this (single model call)
        if parsed_mentions['mentions']:
            handled = await container.mention_handler.handle_mention_call(
                sid=sid,
                data={
                    'text': text,
                    'node_id': node_id,
                    'node_path': node_path,
                    'pinned_files': pinned_files,
                    'viewport_context': viewport_context,
                    'request_node_id': request_node_id,
                    'request_timestamp': request_timestamp
                },
                parsed=parsed_mentions
            )

            if handled:
                print(f"[HANDLER_V2] @mention handled, returning")
                return  # Early return

        # Save user message to chat history
        save_chat_message(node_path, {
            'role': 'user',
            'text': text,
            'node_id': node_id
        }, pinned_files=pinned_files)

        # Emit CAM event for user message
        try:
            chat_history = get_chat_history_manager()
            chat_id = chat_history.get_or_create_chat(node_path)
            await emit_cam_event("message_sent", {
                "chat_id": chat_id,
                "content": text,
                "role": "user"
            }, source="user_input")
        except Exception as cam_err:
            print(f"[CAM] Message event error (non-critical): {cam_err}")

        # ========================================
        # STEP 4: HOSTESS ROUTING
        # ========================================
        hostess_decision = None
        agents_to_call = ['PM', 'Dev', 'QA']  # Default: full chain
        single_mode = False

        # Check if user is responding to pending API key question
        is_pending_key = await container.hostess_router.handle_pending_key_response(
            sid=sid,
            text=text,
            context={
                'node_id': request_node_id,
                'node_path': node_path,
                'timestamp': request_timestamp
            }
        )

        if is_pending_key:
            print(f"[HANDLER_V2] Pending key response handled, returning")
            return  # Early return

        # Get Hostess decision
        if HOSTESS_AVAILABLE:
            try:
                hostess = get_hostess()

                # Build rich context for routing
                context_builder = get_hostess_context_builder()
                if context_builder:
                    rich_context = context_builder.build_context(
                        message=text,
                        file_path=node_path,
                        conversation_id=client_id,
                        node_id=node_id
                    )
                    print(f"[HANDLER_V2] Rich context: file={rich_context.get('has_file_context')}, semantic={rich_context.get('has_semantic_context')}")
                else:
                    rich_context = {"node_path": node_path, "client_id": client_id}

                # MARKER_90.1.2: Use timeout wrapper to prevent infinite thinking
                hostess_decision = await call_hostess_with_timeout(hostess, text, rich_context)

                if hostess_decision is None:
                    # MARKER_90.1.2_FIX: Hostess timeout - skip silently, don't interfere with chat
                    print(f"[HANDLER_V2] Hostess timeout, skipping silently")
                    pass  # Let normal flow continue without Hostess interference
                else:
                    print(f"[HANDLER_V2] Hostess decision: {hostess_decision['action']} (confidence: {hostess_decision['confidence']:.2f})")

                    # Process Hostess decision
                    agents_result = await container.hostess_router.process_hostess_decision(
                        sid=sid,
                        decision=hostess_decision,
                        context={
                            'node_id': request_node_id,
                            'node_path': node_path,
                            'timestamp': request_timestamp,
                            'text': text
                        }
                    )

                if agents_result is None:
                    print(f"[HANDLER_V2] Hostess handled directly, returning")
                    return  # Early return - Hostess handled it

                agents_to_call = agents_result
                single_mode = len(agents_to_call) == 1

            except Exception as e:
                print(f"[HANDLER_V2] Hostess error: {e}, continuing with default flow")

        # ========================================
        # STEP 5: @MENTION AGENT OVERRIDE
        # ========================================
        if parsed_mentions.get('mode') == 'agents' and parsed_mentions.get('agents'):
            mention_agents = parsed_mentions['agents']

            # Remove Hostess from list if mentioned
            if 'Hostess' in mention_agents:
                mention_agents = [a for a in mention_agents if a != 'Hostess']

            if mention_agents:
                agents_to_call = mention_agents
                single_mode = len(agents_to_call) == 1
                print(f"[HANDLER_V2] @mention override: {agents_to_call}")

        # ========================================
        # STEP 6: EXECUTE AGENT CHAIN
        # ========================================
        agents = get_agents()

        if not agents:
            print("[HANDLER_V2] No agents available, sending fallback")
            for agent_name in ['PM', 'Dev', 'QA']:
                fallback_text = f"[Fallback] I'm {agent_name}. Agents not initialized."
                await sio.emit('agent_message', {
                    'agent': agent_name,
                    'model': 'fallback',
                    'content': fallback_text,
                    'text': fallback_text,
                    'node_id': request_node_id,
                    'node_path': node_path,
                    'timestamp': request_timestamp,
                    'response_type': 'text',
                    'force_artifact': False
                }, to=sid)
            return

        # Get file context
        from src.api.handlers.handler_utils import sync_get_rich_context, format_context_for_agent
        rich_context = sync_get_rich_context(node_path)

        if rich_context.get('error'):
            context_for_llm = f"File: {node_path}\nStatus: {rich_context['error']}"
            file_available = False
        else:
            context_for_llm = format_context_for_agent(rich_context, 'generic')
            file_available = True

        # Execute agent chain
        orchestrator = container.create_orchestrator(sid)
        result = await orchestrator.execute_agent_chain(
            agents_to_call=agents_to_call,
            agents=agents,
            text=text,
            context_for_llm=context_for_llm,
            pinned_files=pinned_files,
            request_node_id=request_node_id,
            node_path=node_path,
            request_timestamp=request_timestamp,
            single_mode=single_mode
        )

        responses = result['responses']
        all_artifacts = result['all_artifacts']

        # ========================================
        # STEP 7: EMIT RESPONSES
        # ========================================
        response_manager = container.create_response_manager(sid)

        await response_manager.emit_responses(
            responses=responses,
            node_path=node_path,
            file_available=file_available,
            pinned_files=pinned_files
        )

        # ========================================
        # STEP 8: GENERATE SUMMARY
        # ========================================
        await response_manager.emit_summary(
            responses=responses,
            request_node_id=request_node_id,
            node_path=node_path,
            request_timestamp=request_timestamp,
            single_mode=single_mode
        )

        # ========================================
        # STEP 9: CAM EVENT FOR ARTIFACTS
        # ========================================
        if all_artifacts and len(all_artifacts) > 0:
            try:
                from src.orchestration.cam_event_handler import emit_artifact_event

                print(f"[CAM] Single agent produced {len(all_artifacts)} artifact(s), emitting events...")

                for artifact in all_artifacts:
                    artifact_path = artifact.get('filename', 'unknown')
                    artifact_content = artifact.get('code', '')
                    source_agent = artifact.get('agent', 'Dev')

                    await emit_artifact_event(
                        artifact_path=artifact_path,
                        artifact_content=artifact_content,
                        source_agent=source_agent
                    )

                print(f"[CAM] CAM events emitted")

            except Exception as cam_error:
                print(f"[CAM] CAM error (non-critical): {cam_error}")

        print(f"[HANDLER_V2] Processing complete\n")
