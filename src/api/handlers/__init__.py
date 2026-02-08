"""
VETKA Socket.IO Handlers - FastAPI/ASGI Version

@file handlers/__init__.py
@status ACTIVE
@phase Phase 64.5 - God Object Split Complete
@lastAudit 2026-01-17

Socket.IO Handler Registration Module for python-socketio AsyncServer.
Migrated from src/server/handlers/ (Flask-SocketIO version).

Phase 64 Split Structure:
- message_utils.py: Pure utility functions (format, parse, build)
- streaming_handler.py: Token streaming logic
- chat_handler.py: Direct model calls, provider detection
- workflow_handler.py: Agent chain, summary, Hostess routing
- user_message_handler.py: Main handler (now uses above modules)

Key changes from Flask-SocketIO:
- emit() -> await sio.emit()
- request.sid -> sid parameter
- def handler() -> async def handler()
- broadcast=True -> omit 'to' parameter
"""

from socketio import AsyncServer

# Phase 64: Re-export extracted modules for backwards compatibility
from .message_utils import (
    format_history_for_prompt,
    load_pinned_file_content,
    build_pinned_context,
)

from .streaming_handler import stream_response

from .chat_handler import (
    ModelProvider,
    detect_provider,
    is_local_ollama_model,
    build_model_prompt,
    get_agent_short_name,
)

from .workflow_handler import (
    generate_simple_summary,
    parse_llm_summary,
    build_summary_prompt,
    determine_agents_to_call,
)

# Phase 104.7: Stream visibility handler
from .stream_handler import (
    StreamLevel,
    StreamEventType,
    StreamEvent,
    StreamManager,
    get_stream_manager,
    create_stream_manager,
    emit_stream_event,
)

# MARKER_123.0A: Phase 123.0 - ActivityHub for glow events
from src.services.activity_hub import get_activity_hub, ActivityHub


async def register_all_handlers(sio: AsyncServer, app=None):
    """
    Register all Socket.IO handlers with AsyncServer.

    Args:
        sio: python-socketio AsyncServer instance
        app: FastAPI app for accessing app.state (optional)
    """
    from .connection_handlers import register_connection_handlers
    from .approval_handlers import register_approval_handlers
    from .tree_handlers import register_tree_handlers
    from .chat_handlers import register_chat_handlers
    from .workflow_handlers import register_workflow_handlers
    from .reaction_handlers import register_reaction_handlers
    from .user_message_handler import register_user_message_handler
    from .group_message_handler import register_group_message_handler
    from .key_handlers import register_key_handlers  # Phase 57.9
    from .workflow_socket_handler import register_workflow_socket_handlers  # Phase 60.2
    from .voice_socket_handler import register_voice_socket_handlers  # Phase 60.5
    from .search_handlers import register_search_handlers  # Phase 68
    from .jarvis_handler import register_jarvis_handlers  # Phase 104 - Jarvis Voice
    from .approval_socket_handler import register_approval_socket_handlers  # Phase 104.4
    from .mcp_socket_handler import register_mcp_socket_handlers  # MARKER_106e_2: MCP socket handlers
    from .layout_socket_handler import register_layout_socket_handlers  # MARKER_110_BACKEND_CONFIG: Layout config handlers

    register_connection_handlers(sio, app)
    register_approval_handlers(sio, app)
    register_tree_handlers(sio, app)
    register_chat_handlers(sio, app)
    register_workflow_handlers(sio, app)
    register_reaction_handlers(sio, app)
    register_user_message_handler(sio, app)
    register_group_message_handler(sio, app)
    register_key_handlers(sio, app)  # Phase 57.9
    register_workflow_socket_handlers(sio, app)  # Phase 60.2
    register_voice_socket_handlers(sio, app)  # Phase 60.5
    register_search_handlers(sio, app)  # Phase 68
    register_jarvis_handlers(sio)  # Phase 104 - Jarvis Voice
    register_approval_socket_handlers(sio, app)  # Phase 104.4 - Approval Socket
    await register_mcp_socket_handlers(sio, app)  # MARKER_106e_2: MCP socket handlers
    register_layout_socket_handlers(sio, app)  # MARKER_110_BACKEND_CONFIG: Layout config handlers

    # MARKER_123.0A: Phase 123.0 - Initialize ActivityHub with Socket.IO
    hub = get_activity_hub()
    hub.set_socketio(sio)
    hub.start_decay_loop()
    print("  [Handlers] ✅ ActivityHub initialized with decay loop - MARKER_123.0A")

    print("  [Handlers] Socket.IO async handlers registered (Phase 104.7)")
    print("  [Handlers] ✅ group_message_handler registered (join_group, leave_group, group_message, group_typing)")
    print("  [Handlers] ✅ key_handlers registered (add_api_key, learn_key_type, get_key_status)")
    print("  [Handlers] ✅ workflow_socket_handler registered on /workflow namespace (Phase 60.2)")
    print("  [Handlers] ✅ voice_socket_handler registered with Realtime Pipeline (Phase 60.5.1)")
    print("  [Handlers]   - Legacy: voice_start, voice_audio, voice_stop, tts_request")
    print("  [Handlers]   - Realtime: voice_stream_start, voice_pcm, voice_utterance_end, voice_interrupt")
    print("  [Handlers] ✅ search_handlers registered (search_query) - Phase 68")
    print("  [Handlers] ✅ jarvis_handler registered (jarvis_listen_start/stop, jarvis_audio_chunk) - Phase 104")
    print("  [Handlers] ✅ approval_socket_handler registered (approval_response, get_approval_details) - Phase 104.4")
    print("  [Handlers] ✅ mcp_socket_handler registered on /mcp namespace - MARKER_106e_2")
    print("  [Handlers] ✅ layout_socket_handler registered (update_layout_config, get_layout_config) - MARKER_110_BACKEND_CONFIG")
    print("  [Handlers] ✅ stream_handler available (StreamManager, visibility control) - Phase 104.7")
