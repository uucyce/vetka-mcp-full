"""
Activity Emitter Service - Phase 108.4 Step 5

Helper service for emitting activity_update events to Socket.IO clients.
Used by other services to broadcast real-time activity feed updates.

@file activity_emitter.py
@status ACTIVE
@phase Phase 108.4 Step 5
@created 2026-02-02

MARKER_108_5_ACTIVITY_FEED: Real-time activity broadcasting

Usage:
    from src.services.activity_emitter import emit_activity_update

    # Emit a chat activity
    await emit_activity_update(
        socketio=sio,
        activity_type="chat",
        title="New message in Dev Chat",
        description="User sent a message",
        metadata={"chat_id": "abc123", "sender": "user"}
    )
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from socketio import AsyncServer

logger = logging.getLogger(__name__)


async def emit_activity_update(
    socketio: AsyncServer,
    activity_type: str,
    title: str,
    description: str,
    metadata: Optional[Dict[str, Any]] = None,
    activity_id: Optional[str] = None,
    timestamp: Optional[str] = None
) -> bool:
    """
    Emit activity_update Socket.IO event for real-time feed updates.

    MARKER_108_5_ACTIVITY_FEED: Real-time activity broadcasting

    Args:
        socketio: Socket.IO AsyncServer instance
        activity_type: Activity type ('chat', 'mcp', 'artifact', 'commit')
        title: Activity title (short, descriptive)
        description: Activity description (brief details)
        metadata: Additional metadata dict (optional)
        activity_id: Activity ID (auto-generated if not provided)
        timestamp: ISO 8601 timestamp (auto-generated if not provided)

    Returns:
        True if event was emitted successfully, False otherwise

    Example:
        await emit_activity_update(
            socketio=sio,
            activity_type="artifact",
            title="Artifact approved: feature_x.py",
            description="Dev approved artifact for integration",
            metadata={"artifact_id": "art_123", "status": "approved"}
        )
    """
    try:
        if not socketio:
            logger.warning("[ActivityEmitter] Socket.IO instance not provided")
            return False

        # Auto-generate timestamp if not provided
        if not timestamp:
            timestamp = datetime.now(timezone.utc).isoformat()

        # Auto-generate activity ID if not provided
        if not activity_id:
            activity_id = f"{activity_type}_{int(datetime.now().timestamp() * 1000)}"

        # Build activity payload
        activity_data = {
            "id": activity_id,
            "type": activity_type,
            "timestamp": timestamp,
            "title": title,
            "description": description,
            "metadata": metadata or {}
        }

        # Emit event to all connected clients
        await socketio.emit('activity_update', activity_data)

        logger.info(f"[ActivityEmitter] Emitted: {activity_type} - {title}")
        return True

    except Exception as e:
        logger.error(f"[ActivityEmitter] Error emitting activity: {e}")
        return False


def emit_chat_activity(
    socketio: AsyncServer,
    chat_id: str,
    chat_name: str,
    sender: str,
    content: str,
    message_id: Optional[str] = None
):
    """
    Helper to emit chat message activity.

    Args:
        socketio: Socket.IO AsyncServer instance
        chat_id: Chat UUID
        chat_name: Chat display name
        sender: Message sender (user, assistant, agent)
        content: Message content (will be truncated)
        message_id: Message ID (optional)
    """
    # Truncate long content
    description = content[:100] + "..." if len(content) > 100 else content

    return emit_activity_update(
        socketio=socketio,
        activity_type="chat",
        title=f"Message in {chat_name}",
        description=description,
        metadata={
            "chat_id": chat_id,
            "sender": sender,
            "message_id": message_id
        }
    )


def emit_mcp_activity(
    socketio: AsyncServer,
    tool_name: str,
    client_id: str,
    success: bool,
    duration_ms: Optional[float] = None
):
    """
    Helper to emit MCP tool call activity.

    Args:
        socketio: Socket.IO AsyncServer instance
        tool_name: MCP tool name
        client_id: Client ID
        success: Whether tool call succeeded
        duration_ms: Execution duration in milliseconds (optional)
    """
    status_emoji = "✅" if success else "❌"
    title = f"{status_emoji} MCP: {tool_name}"

    return emit_activity_update(
        socketio=socketio,
        activity_type="mcp",
        title=title,
        description=f"Client: {client_id}",
        metadata={
            "tool": tool_name,
            "client_id": client_id,
            "success": success,
            "duration_ms": duration_ms
        }
    )


def emit_artifact_activity(
    socketio: AsyncServer,
    artifact_id: str,
    status: str,
    artifact_name: Optional[str] = None
):
    """
    Helper to emit artifact activity.

    Args:
        socketio: Socket.IO AsyncServer instance
        artifact_id: Artifact ID
        status: Artifact status (staged, approved, rejected, saved)
        artifact_name: Artifact file name (optional)
    """
    title = f"Artifact: {artifact_name or artifact_id}"

    return emit_activity_update(
        socketio=socketio,
        activity_type="artifact",
        title=title,
        description=f"Status: {status}",
        metadata={
            "artifact_id": artifact_id,
            "status": status,
            "artifact_name": artifact_name
        }
    )


def emit_git_activity(
    socketio: AsyncServer,
    commit_hash: str,
    author: str,
    subject: str,
    timestamp: Optional[str] = None
):
    """
    Helper to emit git commit activity.

    Args:
        socketio: Socket.IO AsyncServer instance
        commit_hash: Git commit hash
        author: Commit author
        subject: Commit subject/message
        timestamp: Commit timestamp (optional)
    """
    return emit_activity_update(
        socketio=socketio,
        activity_type="commit",
        title=subject[:100],
        description=f"By {author}",
        metadata={
            "commit_hash": commit_hash,
            "short_hash": commit_hash[:8],
            "author": author,
            "subject": subject
        },
        timestamp=timestamp
    )
