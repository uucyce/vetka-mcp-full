"""
Chat History Routes - Phase 50
API endpoints for managing chat history and conversation persistence.

@file chat_history_routes.py
@status ACTIVE
@phase Phase 50 - Chat History + Sidebar UI
@lastUpdate 2026-01-06

Endpoints:
- GET /api/chats - List all chats (for sidebar)
- GET /api/chats/{chat_id} - Get single chat with messages
- POST /api/chats/{chat_id}/messages - Add message to chat
- DELETE /api/chats/{chat_id} - Delete chat
- GET /api/chats/search - Search messages across chats
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from src.chat.chat_history_manager import get_chat_history_manager


router = APIRouter(prefix="/api", tags=["chat-history"])


# ============================================================
# PYDANTIC MODELS
# ============================================================

class MessageRequest(BaseModel):
    """Message to add to chat."""
    role: str  # 'user', 'assistant', 'agent'
    content: Optional[str] = None
    text: Optional[str] = None  # Backwards compatibility
    agent: Optional[str] = None
    model: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Chat object for responses."""
    id: str
    file_path: str
    file_name: str
    display_name: Optional[str] = None  # Phase 74: Custom chat name
    context_type: Optional[str] = None  # Phase 74: "file" | "folder" | "group" | "topic"
    items: Optional[List[str]] = None   # Phase 74: File paths for groups
    topic: Optional[str] = None         # Phase 74: Topic for file-less chats
    created_at: str
    updated_at: str
    message_count: Optional[int] = None


class MessageResponse(BaseModel):
    """Message object for responses."""
    id: str
    role: str
    content: Optional[str] = None
    agent: Optional[str] = None
    model: Optional[str] = None
    timestamp: str


# ============================================================
# API ENDPOINTS
# ============================================================

@router.get("/chats", response_model=Dict[str, List[ChatResponse]])
async def list_chats(request: Request):
    """
    Get all chats for sidebar.

    Returns:
        Dict with 'chats' list sorted by updated_at (newest first)
    """
    try:
        manager = get_chat_history_manager()
        all_chats = manager.get_all_chats()

        chat_responses = []
        for chat in all_chats:
            chat_responses.append(ChatResponse(
                id=chat["id"],
                file_path=chat["file_path"],
                file_name=chat["file_name"],
                display_name=chat.get("display_name"),       # Phase 74
                context_type=chat.get("context_type", "file"),  # Phase 74
                items=chat.get("items"),                     # Phase 74
                topic=chat.get("topic"),                     # Phase 74
                created_at=chat["created_at"],
                updated_at=chat["updated_at"],
                message_count=len(chat.get("messages", []))
            ))

        return {"chats": chat_responses}

    except Exception as e:
        print(f"[ChatHistory] Error listing chats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats/{chat_id}", response_model=Dict[str, Any])
async def get_chat(chat_id: str, request: Request):
    """
    Get single chat with all messages.

    Args:
        chat_id: Chat UUID

    Returns:
        Chat object with messages
    """
    try:
        manager = get_chat_history_manager()
        chat = manager.get_chat(chat_id)

        if not chat:
            raise HTTPException(status_code=404, detail=f"Chat {chat_id} not found")

        # Format messages
        # Phase 74 fix: Ensure content is never None (fallback to empty string)
        messages = []
        for msg in chat.get("messages", []):
            messages.append(MessageResponse(
                id=msg.get("id"),
                role=msg.get("role"),
                content=msg.get("content") or msg.get("text") or "",
                agent=msg.get("agent"),
                model=msg.get("model"),
                timestamp=msg.get("timestamp", "")
            ))

        return {
            "id": chat["id"],
            "file_path": chat["file_path"],
            "file_name": chat["file_name"],
            "display_name": chat.get("display_name"),           # Phase 74.3
            "context_type": chat.get("context_type", "file"),   # Phase 74.3
            "items": chat.get("items"),                         # Phase 74.3
            "topic": chat.get("topic"),                         # Phase 74.3
            "group_id": chat.get("group_id"),                   # Phase 80.5
            "pinned_file_ids": chat.get("pinned_file_ids", []), # Phase 100.2
            "created_at": chat["created_at"],
            "updated_at": chat["updated_at"],
            "messages": messages
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ChatHistory] Error getting chat {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chats/{chat_id}/messages")
async def add_message(chat_id: str, message: MessageRequest, request: Request):
    """
    Add message to chat.

    Args:
        chat_id: Chat UUID
        message: Message to add

    Returns:
        Success status
    """
    try:
        manager = get_chat_history_manager()

        msg_dict = {
            "role": message.role,
            "content": message.content or message.text,
            "agent": message.agent,
            "model": message.model,
            "metadata": message.metadata or {}
        }

        success = manager.add_message(chat_id, msg_dict)

        if not success:
            raise HTTPException(status_code=404, detail=f"Chat {chat_id} not found")

        return {"success": True, "message": "Message added"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ChatHistory] Error adding message to {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str, request: Request):
    """
    Delete a chat.

    Args:
        chat_id: Chat UUID

    Returns:
        Success status
    """
    try:
        manager = get_chat_history_manager()
        success = manager.delete_chat(chat_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Chat {chat_id} not found")

        return {"success": True, "message": f"Chat {chat_id} deleted"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ChatHistory] Error deleting chat {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RenameRequest(BaseModel):
    """Request to rename a chat."""
    display_name: str


@router.patch("/chats/{chat_id}")
async def rename_chat(chat_id: str, data: RenameRequest, request: Request):
    """
    Rename a chat (set display_name).

    Phase 74: Allow custom chat names independent of file_name.

    Args:
        chat_id: Chat UUID
        data: Request body with display_name

    Returns:
        Success status with new name
    """
    try:
        if not data.display_name or not data.display_name.strip():
            raise HTTPException(status_code=400, detail="display_name is required and cannot be empty")

        manager = get_chat_history_manager()
        success = manager.rename_chat(chat_id, data.display_name.strip())

        if not success:
            raise HTTPException(status_code=404, detail=f"Chat {chat_id} not found")

        return {
            "success": True,
            "chat_id": chat_id,
            "display_name": data.display_name.strip()
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ChatHistory] Error renaming chat {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class PinnedFilesRequest(BaseModel):
    """Request to update pinned files for a chat."""
    pinned_file_ids: List[str]


@router.put("/chats/{chat_id}/pinned")
async def update_pinned_files(chat_id: str, data: PinnedFilesRequest, request: Request):
    """
    Update pinned file IDs for a chat.

    Phase 100.2: Persistent pinned files across reload.

    Args:
        chat_id: Chat UUID
        data: Request body with pinned_file_ids list

    Returns:
        Success status with pinned count
    """
    try:
        manager = get_chat_history_manager()
        success = manager.update_pinned_files(chat_id, data.pinned_file_ids)

        if not success:
            raise HTTPException(status_code=404, detail=f"Chat {chat_id} not found")

        return {
            "success": True,
            "chat_id": chat_id,
            "pinned_count": len(data.pinned_file_ids)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ChatHistory] Error updating pinned files for {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats/{chat_id}/pinned")
async def get_pinned_files(chat_id: str, request: Request):
    """
    Get pinned file IDs for a chat.

    Phase 100.2: Retrieve pinned files on chat load.

    Args:
        chat_id: Chat UUID

    Returns:
        List of pinned file node IDs
    """
    try:
        manager = get_chat_history_manager()
        pinned_ids = manager.get_pinned_files(chat_id)

        return {
            "chat_id": chat_id,
            "pinned_file_ids": pinned_ids
        }

    except Exception as e:
        print(f"[ChatHistory] Error getting pinned files for {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats/file/{file_path:path}")
async def get_chats_for_file(file_path: str, request: Request):
    """
    Get all chats for a specific file.

    Args:
        file_path: File path (can contain slashes)

    Returns:
        List of chats for file
    """
    try:
        manager = get_chat_history_manager()
        chats = manager.get_chats_for_file(file_path)

        chat_responses = [
            ChatResponse(
                id=chat["id"],
                file_path=chat["file_path"],
                file_name=chat["file_name"],
                created_at=chat["created_at"],
                updated_at=chat["updated_at"],
                message_count=len(chat.get("messages", []))
            )
            for chat in chats
        ]

        return {"chats": chat_responses}

    except Exception as e:
        print(f"[ChatHistory] Error getting chats for file {file_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats/search/{query}")
async def search_chats(query: str, request: Request, chat_id: Optional[str] = None):
    """
    Search messages across chats.

    Args:
        query: Search query
        chat_id: Optional - search in specific chat only

    Returns:
        List of matching messages with context
    """
    try:
        manager = get_chat_history_manager()
        results = manager.search_messages(query, chat_id)

        return {
            "query": query,
            "count": len(results),
            "results": results
        }

    except Exception as e:
        print(f"[ChatHistory] Error searching for '{query}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CreateChatRequest(BaseModel):
    """Request to create a named chat (Phase 74.8)."""
    display_name: str
    context_type: str = "group"
    items: Optional[List[str]] = None
    topic: Optional[str] = None
    group_id: Optional[str] = None  # Phase 80.5: Link to GroupChatManager group


@router.post("/chats")
async def create_chat(data: CreateChatRequest, request: Request):
    """
    Create a new named chat.

    Phase 74.8: Allow creating chats with custom names (for group chats).

    Args:
        data: Request body with display_name, context_type, items, topic

    Returns:
        Created chat info with id
    """
    try:
        if not data.display_name or not data.display_name.strip():
            raise HTTPException(status_code=400, detail="display_name is required")

        manager = get_chat_history_manager()

        # Create chat with null path but with display_name
        chat_id = manager.get_or_create_chat(
            file_path="unknown",
            context_type=data.context_type,
            items=data.items,
            topic=data.topic,
            display_name=data.display_name.strip()
        )

        # If chat was reused (no display_name), set it now
        chat = manager.get_chat(chat_id)
        if not chat.get("display_name"):
            manager.rename_chat(chat_id, data.display_name.strip())
            # Also update context_type if needed
            if chat.get("context_type") != data.context_type:
                chat["context_type"] = data.context_type
                manager._save()

        # Phase 80.5: Store group_id for linking to GroupChatManager
        if data.group_id:
            chat["group_id"] = data.group_id
            manager._save()

        return {
            "success": True,
            "chat_id": chat_id,
            "display_name": data.display_name.strip(),
            "context_type": data.context_type,
            "group_id": data.group_id
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ChatHistory] Error creating chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats/{chat_id}/export")
async def export_chat(chat_id: str, request: Request):
    """
    Export chat as JSON.

    Args:
        chat_id: Chat UUID

    Returns:
        Chat as JSON string
    """
    try:
        manager = get_chat_history_manager()
        json_str = manager.export_chat(chat_id)

        if not json_str:
            raise HTTPException(status_code=404, detail=f"Chat {chat_id} not found")

        return {"json": json_str}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ChatHistory] Error exporting chat {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
