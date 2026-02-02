"""
Activity Feed Integration Examples - Phase 108.4 Step 5

Examples showing how to integrate activity broadcasting into existing services.

@file activity_feed_integration.py
@status EXAMPLE
@phase Phase 108.4 Step 5
"""

from typing import Optional
from socketio import AsyncServer
from src.services.activity_emitter import (
    emit_chat_activity,
    emit_mcp_activity,
    emit_artifact_activity,
    emit_git_activity,
    emit_activity_update
)


# ============================================================
# EXAMPLE 1: Integrating with ChatHistoryManager
# ============================================================

async def on_message_added(
    socketio: AsyncServer,
    chat_id: str,
    chat_name: str,
    message: dict
):
    """
    Called when a new message is added to a chat.
    Emit activity update for real-time feed.
    """
    await emit_chat_activity(
        socketio=socketio,
        chat_id=chat_id,
        chat_name=chat_name,
        sender=message.get("role", "user"),
        content=message.get("content", ""),
        message_id=message.get("id")
    )


# Integration location: src/chat/chat_history_manager.py
# Add to ChatHistoryManager.add_message() method:
"""
def add_message(self, chat_id: str, message: dict) -> bool:
    # ... existing code ...

    # Emit activity update
    if hasattr(self, 'socketio') and self.socketio:
        asyncio.create_task(on_message_added(
            self.socketio,
            chat_id,
            chat.get('display_name') or chat.get('file_name', 'Unknown'),
            message
        ))

    return True
"""


# ============================================================
# EXAMPLE 2: Integrating with MCP Server
# ============================================================

async def on_mcp_tool_called(
    socketio: AsyncServer,
    tool_name: str,
    client_id: str,
    success: bool,
    duration_ms: Optional[float] = None
):
    """
    Called after MCP tool execution completes.
    Emit activity update for real-time feed.
    """
    await emit_mcp_activity(
        socketio=socketio,
        tool_name=tool_name,
        client_id=client_id,
        success=success,
        duration_ms=duration_ms
    )


# Integration location: src/mcp/mcp_server.py
# Add to MCPServer.handle_tool_call() method:
"""
async def handle_tool_call(self, tool_name: str, args: dict, agent_id: str):
    start_time = time.time()

    try:
        # ... execute tool ...
        success = True
    except Exception as e:
        success = False
    finally:
        duration_ms = (time.time() - start_time) * 1000

        # Emit activity update
        asyncio.create_task(on_mcp_tool_called(
            self.socketio,
            tool_name,
            agent_id,
            success,
            duration_ms
        ))
"""


# ============================================================
# EXAMPLE 3: Integrating with Artifact Approval Service
# ============================================================

async def on_artifact_approved(
    socketio: AsyncServer,
    artifact_id: str,
    artifact_name: Optional[str] = None
):
    """
    Called when an artifact is approved.
    Emit activity update for real-time feed.
    """
    await emit_artifact_activity(
        socketio=socketio,
        artifact_id=artifact_id,
        status="approved",
        artifact_name=artifact_name
    )


async def on_artifact_rejected(
    socketio: AsyncServer,
    artifact_id: str,
    artifact_name: Optional[str] = None
):
    """
    Called when an artifact is rejected.
    Emit activity update for real-time feed.
    """
    await emit_artifact_activity(
        socketio=socketio,
        artifact_id=artifact_id,
        status="rejected",
        artifact_name=artifact_name
    )


async def on_artifact_staged(
    socketio: AsyncServer,
    artifact_id: str,
    artifact_name: Optional[str] = None
):
    """
    Called when an artifact is staged.
    Emit activity update for real-time feed.
    """
    await emit_artifact_activity(
        socketio=socketio,
        artifact_id=artifact_id,
        status="staged",
        artifact_name=artifact_name
    )


# Integration location: src/services/approval_service.py
# Add to ApprovalService methods:
"""
def approve(self, request_id: str, reason: str) -> bool:
    # ... existing code ...

    if success and self.socketio:
        asyncio.create_task(on_artifact_approved(
            self.socketio,
            artifact_id,
            artifact_name
        ))

    return success

def reject(self, request_id: str, reason: str) -> bool:
    # ... existing code ...

    if success and self.socketio:
        asyncio.create_task(on_artifact_rejected(
            self.socketio,
            artifact_id,
            artifact_name
        ))

    return success
"""


# ============================================================
# EXAMPLE 4: Integrating with Git Operations
# ============================================================

async def on_git_commit(
    socketio: AsyncServer,
    commit_hash: str,
    author: str,
    subject: str,
    timestamp: str
):
    """
    Called after a git commit is created.
    Emit activity update for real-time feed.
    """
    await emit_git_activity(
        socketio=socketio,
        commit_hash=commit_hash,
        author=author,
        subject=subject,
        timestamp=timestamp
    )


# Integration location: Any git wrapper/service
# Add after git commit:
"""
def commit_changes(self, message: str, author: str):
    # Run git commit
    result = subprocess.run(['git', 'commit', '-m', message], ...)

    if result.returncode == 0:
        # Get commit hash
        commit_hash = subprocess.run(['git', 'rev-parse', 'HEAD'], ...)

        # Emit activity update
        if self.socketio:
            asyncio.create_task(on_git_commit(
                self.socketio,
                commit_hash.strip(),
                author,
                message,
                datetime.now(timezone.utc).isoformat()
            ))
"""


# ============================================================
# EXAMPLE 5: Custom Activity Types
# ============================================================

async def emit_custom_activity(
    socketio: AsyncServer,
    activity_type: str,
    title: str,
    description: str,
    **kwargs
):
    """
    Emit a custom activity with arbitrary metadata.

    Usage:
        await emit_custom_activity(
            socketio=sio,
            activity_type="workflow",
            title="Workflow completed",
            description="PM -> Dev -> QA pipeline finished",
            workflow_id="wf_123",
            duration_seconds=45,
            status="success"
        )
    """
    await emit_activity_update(
        socketio=socketio,
        activity_type=activity_type,
        title=title,
        description=description,
        metadata=kwargs
    )


# ============================================================
# EXAMPLE 6: Batching Activities (Advanced)
# ============================================================

class ActivityBatcher:
    """
    Batch multiple activities and emit them together.
    Useful for high-frequency events (e.g., file watcher).
    """

    def __init__(self, socketio: AsyncServer, batch_size: int = 10):
        self.socketio = socketio
        self.batch_size = batch_size
        self.activities = []

    async def add_activity(
        self,
        activity_type: str,
        title: str,
        description: str,
        metadata: dict
    ):
        """Add activity to batch."""
        self.activities.append({
            "type": activity_type,
            "title": title,
            "description": description,
            "metadata": metadata
        })

        # Emit batch if full
        if len(self.activities) >= self.batch_size:
            await self.flush()

    async def flush(self):
        """Emit all batched activities."""
        if not self.activities:
            return

        for activity in self.activities:
            await emit_activity_update(
                socketio=self.socketio,
                activity_type=activity["type"],
                title=activity["title"],
                description=activity["description"],
                metadata=activity["metadata"]
            )

        self.activities.clear()


# Usage:
"""
batcher = ActivityBatcher(socketio=sio, batch_size=10)

# Add activities
await batcher.add_activity("file_change", "File modified", "src/main.py", {...})
await batcher.add_activity("file_change", "File modified", "src/utils.py", {...})
# ... more activities ...

# Force flush remaining activities
await batcher.flush()
"""
