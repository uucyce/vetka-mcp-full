"""
Activity Emitter Service - Phase 108.4 Step 5 + Phase 109.1

Helper service for emitting activity_update events to Socket.IO clients.
Used by other services to broadcast real-time activity feed updates.

@file activity_emitter.py
@status ACTIVE
@phase Phase 108.4 Step 5, Phase 109.1
@created 2026-02-02
@updated 2026-02-04

MARKER_108_5_ACTIVITY_FEED: Real-time activity broadcasting
MARKER_109_4_REALTIME_CONTEXT: Dynamic context DAG updates for Jarvis super-agent

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


# =============================================================================
# MARKER_109_4_REALTIME_CONTEXT: Phase 109.1 - Dynamic Context Updates
# =============================================================================

async def emit_context_update(
    socketio: AsyncServer,
    session_id: str,
    context_type: str,
    change_type: str = "updated",
    summary: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    room: Optional[str] = None
) -> bool:
    """
    Emit context_update Socket.IO event for real-time DAG updates.

    MARKER_109_4_REALTIME_CONTEXT: Dynamic context injection for Jarvis super-agent.

    Used to notify agents when context layers change:
    - viewport: Camera/zoom changed, files entered/left view
    - pins: File pinned/unpinned
    - chat: New message in linked chat
    - cam: CAM activation changed
    - prefs: User preferences updated

    Args:
        socketio: Socket.IO AsyncServer instance
        session_id: MCP session ID to scope update
        context_type: Layer type ('viewport', 'pins', 'chat', 'cam', 'prefs')
        change_type: Change type ('created', 'updated', 'deleted')
        summary: One-line summary for quick parsing (e.g., "[→ viewport] zoom changed to 2")
        metadata: Additional layer-specific data
        room: Optional room to target (default: mcp_{session_id})

    Returns:
        True if event emitted, False on error

    Example:
        await emit_context_update(
            socketio=sio,
            session_id="abc123",
            context_type="viewport",
            change_type="updated",
            summary="[→ viewport] 15 new files visible, zoom ~3",
            metadata={"visible_count": 218, "zoom": 3}
        )
    """
    try:
        if not socketio:
            logger.warning("[ContextEmitter] Socket.IO instance not provided")
            return False

        timestamp = datetime.now(timezone.utc).isoformat()

        # Build context update payload
        context_data = {
            "session_id": session_id,
            "context_type": context_type,
            "change_type": change_type,
            "timestamp": timestamp,
            "summary": summary or f"[→ {context_type}] {change_type}",
            "metadata": metadata or {},
            # Hyperlink for agent to expand this layer
            "hyperlink": _get_context_hyperlink(context_type)
        }

        # Target specific session room or broadcast
        target_room = room or f"mcp_{session_id}"

        # Emit to room (scoped to session) or broadcast
        if room:
            await socketio.emit('context_update', context_data, room=target_room)
        else:
            # Broadcast to all (for global updates)
            await socketio.emit('context_update', context_data)

        logger.info(f"[ContextEmitter] Emitted: {context_type} {change_type} for session {session_id[:8]}")
        return True

    except Exception as e:
        logger.error(f"[ContextEmitter] Error emitting context update: {e}")
        return False


def _get_context_hyperlink(context_type: str) -> str:
    """Map context type to MCP tool for expansion."""
    hyperlinks = {
        "viewport": "vetka_get_viewport_detail",
        "pins": "vetka_get_pinned_files",
        "chat": "vetka_get_chat_digest",
        "cam": "vetka_get_memory_summary",
        "prefs": "vetka_get_user_preferences"
    }
    return hyperlinks.get(context_type, f"vetka_get_{context_type}")


async def emit_viewport_change(
    socketio: AsyncServer,
    session_id: str,
    visible_count: int,
    zoom_level: float,
    focus_path: Optional[str] = None
) -> bool:
    """
    Helper to emit viewport context change.

    MARKER_109_4_REALTIME_CONTEXT

    Args:
        socketio: Socket.IO instance
        session_id: MCP session ID
        visible_count: Number of visible files
        zoom_level: Current zoom level
        focus_path: Current focus path (optional)
    """
    zoom_desc = "overview" if zoom_level <= 2 else "medium" if zoom_level <= 5 else "close-up"
    summary = f"[→ viewport] {visible_count} nodes ({zoom_desc})"
    if focus_path:
        summary += f", focus: {focus_path}"

    return await emit_context_update(
        socketio=socketio,
        session_id=session_id,
        context_type="viewport",
        change_type="updated",
        summary=summary,
        metadata={
            "visible_count": visible_count,
            "zoom_level": zoom_level,
            "zoom_description": zoom_desc,
            "focus_path": focus_path
        }
    )


async def emit_pin_change(
    socketio: AsyncServer,
    session_id: str,
    action: str,
    file_path: str,
    total_pins: int
) -> bool:
    """
    Helper to emit pin context change.

    MARKER_109_4_REALTIME_CONTEXT

    Args:
        socketio: Socket.IO instance
        session_id: MCP session ID
        action: 'pinned' or 'unpinned'
        file_path: File path that changed
        total_pins: Total pinned count after change
    """
    file_name = file_path.split("/")[-1]
    summary = f"[→ pins] {file_name} {action}, total: {total_pins}"

    return await emit_context_update(
        socketio=socketio,
        session_id=session_id,
        context_type="pins",
        change_type="created" if action == "pinned" else "deleted",
        summary=summary,
        metadata={
            "action": action,
            "file_path": file_path,
            "file_name": file_name,
            "total_pins": total_pins
        }
    )


async def emit_chat_context_change(
    socketio: AsyncServer,
    session_id: str,
    chat_id: str,
    message_count: int,
    last_message_preview: str
) -> bool:
    """
    Helper to emit chat context change.

    MARKER_109_4_REALTIME_CONTEXT

    Args:
        socketio: Socket.IO instance
        session_id: MCP session ID
        chat_id: Chat ID that changed
        message_count: Total message count
        last_message_preview: Preview of last message
    """
    preview = last_message_preview[:50] + "..." if len(last_message_preview) > 50 else last_message_preview
    summary = f"[→ chats] Chat#{chat_id[:8]} ({message_count} msgs, last: '{preview}')"

    return await emit_context_update(
        socketio=socketio,
        session_id=session_id,
        context_type="chat",
        change_type="updated",
        summary=summary,
        metadata={
            "chat_id": chat_id,
            "message_count": message_count,
            "last_message_preview": preview
        }
    )
