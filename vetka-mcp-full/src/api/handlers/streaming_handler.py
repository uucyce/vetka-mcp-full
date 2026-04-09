"""
VETKA Streaming Handler - Token Streaming Logic

@file streaming_handler.py
@status ACTIVE
@phase Phase 64.2
@extracted_from user_message_handler.py
@lastAudit 2026-01-17

@calledBy:
  - src.api.handlers.user_message_handler (stream_response for single agent mode)
  - src.api.handlers.__init__ (re-export)

Handles streaming token responses from LLM models:
- Stream start/token/end events
- Token counting
- Full response accumulation

Dependencies:
- src.elisya.api_aggregator_v3.call_model_stream
"""

import uuid
from typing import Tuple


async def stream_response(
    sio,
    sid: str,
    prompt: str,
    agent_name: str,
    model_name: str,
    node_id: str,
    node_path: str
) -> Tuple[str, int]:
    """
    Stream tokens from model to client with metadata.

    Phase 46: Streaming support for better UX.

    Args:
        sio: Socket.IO server instance
        sid: Session ID
        prompt: Full prompt to send to model
        agent_name: Name of agent (PM, Dev, QA, etc.)
        model_name: Model identifier
        node_id: Node ID for context
        node_path: File path context

    Returns:
        Tuple of (full_response_text, token_count)

    Emits:
        - stream_start: {id, agent, model}
        - stream_token: {id, token}
        - stream_end: {id, full_message, metadata}
    """
    # Import here to avoid circular imports
    from src.elisya.api_aggregator_v3 import call_model_stream

    msg_id = str(uuid.uuid4())

    # Emit stream start
    await sio.emit('stream_start', {
        'id': msg_id,
        'agent': agent_name,
        'model': model_name
    }, to=sid)

    # Stream tokens
    full_response = ""
    token_count = 0

    async for token in call_model_stream(prompt, model_name):
        full_response += token
        token_count += 1

        # Emit each token
        await sio.emit('stream_token', {
            'id': msg_id,
            'token': token
        }, to=sid)

    # Emit stream end with metadata
    await sio.emit('stream_end', {
        'id': msg_id,
        'full_message': full_response,
        'metadata': {
            'tokens_output': token_count,
            'tokens_input': len(prompt.split()),
            'model': model_name,
            'agent': agent_name
        }
    }, to=sid)

    return full_response, token_count


# Export all utilities
__all__ = ['stream_response']
