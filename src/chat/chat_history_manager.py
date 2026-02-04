"""
Chat History Manager - Persistent storage for chat messages.

Features:
- Store/load chat history from JSON
- Create chats per file path with normalization
- Organize by updated_at timestamp
- Support for group chats with multiple files
- Search messages by content

@status: active
@phase: 108
@depends: json, pathlib, datetime, typing, uuid
@used_by: api.handlers.chat_handler, services.group_chat_manager, mcp.tools.session_tools

MARKER_QDRANT_CHAT_INDEX: Phase 103.7 + Phase 108.2 - Chat message indexing
- Chat messages auto-persisted to Qdrant VetkaGroupChat collection
- Embeddings generated for semantic search via get_embedding()
- Both user and agent messages indexed with group_id, role, sender_id
- Chat digest API (get_chat_digest) provides lightweight context for MCP

MARKER_ARTIFACTS_STORAGE: Phase 104.9 - Artifact linking to chats
- Artifacts saved to artifacts/ directory (disk_artifact_service.py)
- Each artifact linked to source_message_id in Qdrant payload
- Chat history manager tracks artifact IDs in message metadata
- Enables trace back from artifact to generating conversation

MARKER_CHAT_STRUCTURE: Chat history data model
- Chat format: { id, file_path, file_name, created_at, updated_at, messages[] }
- Message format: { role, content, agent, model, node_id, metadata, id, timestamp }
- Groups format: { default: { name, roles: {PM, Dev, QA} } }
- Storage: data/chat_history.json with retention policy (90 days, max 1000 chats)
- Indexing: Chat messages auto-indexed to Qdrant VetkaGroupChat collection
- For 3D visualization: Each chat can be a node with messages as subnodes
  - Chat node type: 'chat' or 'group' (from treeNodes.ts)
  - Parent: file_path → links to file node
  - Children: message IDs or artifact node IDs
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import uuid
import logging
import threading  # MARKER_109_13: Lock for race condition prevention

logger = logging.getLogger(__name__)


class ChatHistoryManager:
    """Manages persistent chat history storage."""

    def __init__(self, history_file: str = "data/chat_history.json"):
        """Initialize ChatHistoryManager with file path."""
        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.history = self._load()
        # MARKER_109_13: Thread lock for race condition prevention in get_or_create_chat
        self._lock = threading.Lock()

    def _load(self) -> Dict[str, Any]:
        """Load history from JSON file or create new structure."""
        if self.history_file.exists():
            try:
                return json.loads(self.history_file.read_text(encoding='utf-8'))
            except Exception as e:
                print(f"[ChatHistory] Error loading history: {e}, creating new")
                return self._create_empty_history()
        return self._create_empty_history()

    def _create_empty_history(self) -> Dict[str, Any]:
        """Create empty history structure."""
        return {
            "chats": {},
            "groups": {
                "default": {
                    "name": "Default",
                    "roles": {
                        "PM": "qwen2.5:7b",
                        "Dev": "deepseek-coder:6.7b",
                        "QA": "llama3.1:8b"
                    }
                }
            }
        }

    def _enforce_retention_policy(self) -> None:
        """
        Trim old chats if limits exceeded. Call before save.

        Phase 107.3: Retention policy to prevent unbounded growth.
        - MAX_CHATS: Keep newest 1000 chats by updated_at
        - MAX_AGE_DAYS: Remove chats older than 90 days
        - MAX_FILE_SIZE_MB: Target file size (10MB) enforced via count/age limits
        """
        MAX_CHATS = 1000
        MAX_AGE_DAYS = 90

        chats = self.history.get("chats", {})
        original_count = len(chats)

        # 1. Check total count - keep newest MAX_CHATS by updated_at
        if len(chats) > MAX_CHATS:
            sorted_ids = sorted(
                chats.keys(),
                key=lambda x: chats[x].get("updated_at", ""),
                reverse=True
            )
            for old_id in sorted_ids[MAX_CHATS:]:
                del chats[old_id]
            logger.info(f"[Retention] Trimmed by count: {original_count} -> {len(chats)} chats")

        # 2. Check age - remove chats older than MAX_AGE_DAYS
        cutoff = datetime.now() - timedelta(days=MAX_AGE_DAYS)
        removed_by_age = 0
        for chat_id, chat in list(chats.items()):
            updated = chat.get("updated_at", "")
            if updated:
                try:
                    updated_dt = datetime.fromisoformat(updated.replace("Z", ""))
                    if updated_dt < cutoff:
                        del chats[chat_id]
                        removed_by_age += 1
                except Exception as e:
                    logger.warning(f"[Retention] Invalid timestamp for chat {chat_id}: {e}")

        if removed_by_age > 0:
            logger.info(f"[Retention] Removed {removed_by_age} chats older than {MAX_AGE_DAYS} days")

        # Log final stats
        if len(chats) < original_count:
            logger.info(f"[Retention] Total cleanup: {original_count} -> {len(chats)} chats")

    def _save(self) -> None:
        """Save history to JSON file."""
        # Phase 107.3: Enforce retention policy before save
        self._enforce_retention_policy()

        try:
            self.history_file.write_text(
                json.dumps(self.history, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
        except Exception as e:
            print(f"[ChatHistory] Error saving history: {e}")

    def get_or_create_chat(
        self,
        file_path: str,
        context_type: str = "file",
        items: Optional[List[str]] = None,
        topic: Optional[str] = None,
        display_name: Optional[str] = None,
        chat_id: Optional[str] = None,  # FIX_109.4: Accept client-provided chat_id
        group_id: Optional[str] = None  # MARKER_109_13: Stable key for group chats
    ) -> str:
        """
        Get existing chat for file or create new one.

        Phase 51.1 Fix: Normalize paths to prevent duplicate chats for same file.
        Phase 74: Extended schema with context_type, items, topic, display_name.
        MARKER_109_13: Use group_id as stable key for group chats (prevents duplicates).

        Args:
            file_path: File path to associate with chat
            context_type: Type of context - "file", "folder", "group", or "topic"
            items: List of file paths for group chats
            topic: Topic name for topic-based chats (no file)
            display_name: Custom display name for the chat

        Returns:
            Chat UUID
        """
        # MARKER_109_13: Use lock to prevent race condition (parallel requests creating duplicates)
        with self._lock:
            return self._get_or_create_chat_impl(
                file_path, context_type, items, topic, display_name, chat_id, group_id
            )

    def _get_or_create_chat_impl(
        self,
        file_path: str,
        context_type: str,
        items: Optional[List[str]],
        topic: Optional[str],
        display_name: Optional[str],
        chat_id: Optional[str],
        group_id: Optional[str]
    ) -> str:
        """Internal implementation (called with lock held)."""
        # MARKER_109_13: Priority 1 - Search by group_id for group chats (stable key!)
        if group_id and context_type == "group":
            for existing_id, chat in self.history["chats"].items():
                chat_metadata = chat.get("metadata", {})
                if chat_metadata.get("group_id") == group_id:
                    # Found existing chat for this group - reuse it!
                    print(f"[ChatHistory] MARKER_109_13: Reusing chat {existing_id[:8]} for group {group_id[:8]}")
                    return existing_id

        # Phase 51.1 Fix: Normalize incoming path
        if file_path and file_path not in ('unknown', 'root', ''):
            try:
                normalized_path = str(Path(file_path).resolve())
            except Exception:
                normalized_path = file_path
        else:
            normalized_path = file_path

        # Phase 74: Detect folder context type
        if normalized_path and normalized_path not in ('unknown', 'root', ''):
            try:
                if Path(normalized_path).is_dir():
                    context_type = "folder"
            except Exception:
                pass

        # Phase 74.1: Handle "null" context (unknown/root/'')
        is_null_context = normalized_path in ('unknown', 'root', '', None)

        if is_null_context:
            # Phase 74.9: If display_name provided, find chat by name first
            if display_name:
                # Phase 74.10: Normalize display_name with strip() to avoid trailing space mismatches
                search_name = display_name.strip() if display_name else None
                for chat_id, chat in self.history["chats"].items():
                    stored_name = chat.get("display_name")
                    # Phase 74.10: Strip stored name for comparison too
                    stored_name_normalized = stored_name.strip() if stored_name else None
                    if stored_name_normalized == search_name:
                        # Found chat with same name - reuse it
                        # Update context_type if needed
                        if chat.get("context_type") != context_type:
                            chat["context_type"] = context_type
                            self._save()
                        return chat_id

            # Phase 74.7: For null-context without name, match by context_type
            # Group chats should not reuse regular null-chats and vice versa
            null_chats = []
            for chat_id, chat in self.history["chats"].items():
                stored_path = chat.get("file_path", "")
                if stored_path in ('unknown', 'root', '', None):
                    # Only reuse if NOT renamed (no display_name)
                    if not chat.get("display_name"):
                        # Phase 74.7: Match context_type for groups
                        stored_type = chat.get("context_type", "file")
                        # Group chats only match with group chats
                        if context_type == "group":
                            if stored_type == "group":
                                null_chats.append((chat_id, chat.get("updated_at", "")))
                        else:
                            # Non-group only matches non-group
                            if stored_type != "group":
                                null_chats.append((chat_id, chat.get("updated_at", "")))

            if null_chats:
                # Return most recently updated unnamed null-chat
                null_chats.sort(key=lambda x: x[1], reverse=True)
                return null_chats[0][0]
            # No matching null-chat found - will create new one below
        else:
            # Check if chat exists for this file (only for real paths)
            for chat_id, chat in self.history["chats"].items():
                stored_path = chat.get("file_path", "")

                # Phase 51.1 Fix: Normalize stored path for comparison
                if stored_path and stored_path not in ('unknown', 'root', ''):
                    try:
                        stored_normalized = str(Path(stored_path).resolve())
                    except Exception:
                        stored_normalized = stored_path
                else:
                    # Skip null-context chats when searching
                    continue

                if stored_normalized == normalized_path:
                    # Phase 74: Update context_type if changed (e.g., folder detected)
                    if chat.get("context_type") != context_type:
                        chat["context_type"] = context_type
                        self._save()
                    return chat_id

        # Create new chat with normalized path
        # FIX_109.4: Use client-provided chat_id if available (unified ID system like groups)
        if chat_id and chat_id not in self.history["chats"]:
            # Use provided ID
            print(f"[ChatHistory] Using client-provided chat_id: {chat_id}")
        else:
            # Generate new ID
            chat_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        # Phase 74: Determine file_name based on context_type
        if normalized_path not in ('unknown', 'root', ''):
            file_name = Path(normalized_path).name
        else:
            file_name = normalized_path

        # Phase 74.10: Strip display_name to prevent trailing space issues
        clean_display_name = display_name.strip() if display_name else None

        # MARKER_109_13: Build metadata with group_id for stable lookup
        chat_metadata = {}
        if group_id:
            chat_metadata["group_id"] = group_id

        self.history["chats"][chat_id] = {
            "id": chat_id,
            "file_path": normalized_path,
            "file_name": file_name,
            "display_name": clean_display_name,  # Phase 74: Custom name (Phase 74.10: stripped)
            "context_type": context_type,  # Phase 74: "file" | "folder" | "group" | "topic"
            "items": items or [],          # Phase 74: File paths for groups
            "topic": topic,                # Phase 74: Topic for file-less chats
            "pinned_file_ids": [],         # Phase 100.2: Persistent pinned files
            "metadata": chat_metadata,     # MARKER_109_13: Stable keys (group_id, etc.)
            "created_at": now,
            "updated_at": now,
            "messages": []
        }

        self._save()
        print(f"[ChatHistory] Created new chat {chat_id} for {normalized_path} (type={context_type}, name='{clean_display_name}')")
        return chat_id

    def add_message(self, chat_id: str, message: Dict[str, Any]) -> bool:
        """
        Add message to chat history.

        Args:
            chat_id: Chat UUID
            message: Message dict with role, content, etc.

        Returns:
            True if successful
        """
        if chat_id not in self.history["chats"]:
            print(f"[ChatHistory] Chat {chat_id} not found")
            return False

        # Add message ID if not present
        if "id" not in message:
            message["id"] = str(uuid.uuid4())

        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.now().isoformat()

        self.history["chats"][chat_id]["messages"].append(message)
        self.history["chats"][chat_id]["updated_at"] = datetime.now().isoformat()

        self._save()
        return True

    def get_chat_messages(self, chat_id: str) -> List[Dict[str, Any]]:
        """
        Get all messages for a chat.

        Args:
            chat_id: Chat UUID

        Returns:
            List of messages
        """
        if chat_id not in self.history["chats"]:
            return []
        return self.history["chats"][chat_id].get("messages", [])

    def get_chat(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full chat object.

        Args:
            chat_id: Chat UUID

        Returns:
            Chat object or None
        """
        return self.history["chats"].get(chat_id)

    def get_all_chats(
        self,
        limit: int = 50,
        offset: int = 0,
        load_from_end: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get chats with pagination.

        Phase 107.3: Pagination support to prevent loading 4MB+ chat files.

        Args:
            limit: Max chats to return (default 50)
            offset: Skip first N chats (default 0)
            load_from_end: If True, return newest chats first (default True)

        Returns:
            List of chat dicts, sorted by updated_at desc
        """
        chats = list(self.history["chats"].values())
        sorted_chats = sorted(
            chats,
            key=lambda x: x.get("updated_at", ""),
            reverse=True  # Newest first
        )

        if load_from_end:
            # Return from end (newest)
            return sorted_chats[offset:offset + limit]
        else:
            # Return from beginning (oldest)
            return sorted_chats[-(offset + limit):-offset or None]

    def get_total_chats_count(self) -> int:
        """
        Return total number of chats.

        Phase 107.3: Needed for pagination metadata.

        Returns:
            Total count of chats
        """
        return len(self.history.get("chats", {}))

    def get_chats_for_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Get all chats for a specific file.

        Args:
            file_path: File path

        Returns:
            List of chat objects
        """
        chats = [
            chat for chat in self.history["chats"].values()
            if chat.get("file_path") == file_path
        ]
        return sorted(chats, key=lambda x: x.get("updated_at", ""), reverse=True)

    def delete_chat(self, chat_id: str) -> bool:
        """
        Delete a chat.

        Args:
            chat_id: Chat UUID

        Returns:
            True if successful
        """
        if chat_id in self.history["chats"]:
            del self.history["chats"][chat_id]
            self._save()
            return True
        return False

    def rename_chat(self, chat_id: str, new_name: str) -> bool:
        """
        Rename a chat (set display_name).

        Phase 74: Allow custom chat names independent of file_name.

        MARKER_EDIT_NAME_HANDLER: Backend handler in ChatHistoryManager.rename_chat()
        Status: WORKING - Updates display_name field and saves to JSON
        Issue: NONE - Handler is fully functional

        Args:
            chat_id: Chat UUID
            new_name: New display name for the chat

        Returns:
            True if successful
        """
        if chat_id in self.history["chats"]:
            self.history["chats"][chat_id]["display_name"] = new_name
            self.history["chats"][chat_id]["updated_at"] = datetime.now().isoformat()
            self._save()
            print(f"[ChatHistory] Renamed chat {chat_id} to '{new_name}'")
            return True
        return False

    def update_chat_items(self, chat_id: str, items: List[str]) -> bool:
        """
        Update items list for a group chat.

        Phase 74: Track pinned files associated with a chat.

        Args:
            chat_id: Chat UUID
            items: List of file paths (pinned files)

        Returns:
            True if successful
        """
        if chat_id in self.history["chats"]:
            chat = self.history["chats"][chat_id]
            existing_items = chat.get("items", [])

            # Only update if items changed
            if set(existing_items) != set(items):
                chat["items"] = items
                chat["context_type"] = "group" if len(items) > 1 else chat.get("context_type", "file")
                chat["updated_at"] = datetime.now().isoformat()
                self._save()
                print(f"[ChatHistory] Updated items for chat {chat_id}: {len(items)} files")
            return True
        return False

    def update_pinned_files(self, chat_id: str, pinned_file_ids: List[str]) -> bool:
        """
        Update pinned file IDs for a chat.

        Phase 100.2: Persistent pinned files across reload.
        Stores node IDs (not paths) for frontend Zustand compatibility.

        Args:
            chat_id: Chat UUID
            pinned_file_ids: List of node IDs (from Zustand pinnedFileIds)

        Returns:
            True if successful
        """
        if chat_id in self.history["chats"]:
            chat = self.history["chats"][chat_id]
            existing_pins = chat.get("pinned_file_ids", [])

            # Only update if pins changed
            if set(existing_pins) != set(pinned_file_ids):
                chat["pinned_file_ids"] = pinned_file_ids
                chat["updated_at"] = datetime.now().isoformat()
                self._save()
                print(f"[ChatHistory] Updated pinned files for chat {chat_id}: {len(pinned_file_ids)} files")
            return True
        return False

    def get_pinned_files(self, chat_id: str) -> List[str]:
        """
        Get pinned file IDs for a chat.

        Phase 100.2: Retrieve pinned files on chat load.

        Args:
            chat_id: Chat UUID

        Returns:
            List of pinned file node IDs
        """
        if chat_id in self.history["chats"]:
            return self.history["chats"][chat_id].get("pinned_file_ids", [])
        return []

    def search_messages(self, query: str, chat_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search messages by content.

        Args:
            query: Search query
            chat_id: Optional - search in specific chat only

        Returns:
            List of matching messages with chat context
        """
        results = []
        query_lower = query.lower()

        chats_to_search = {chat_id: self.history["chats"][chat_id]} if chat_id else self.history["chats"]

        for cid, chat in chats_to_search.items():
            for message in chat.get("messages", []):
                if query_lower in message.get("content", "").lower() or query_lower in message.get("text", "").lower():
                    results.append({
                        "chat_id": cid,
                        "chat_name": chat.get("file_name"),
                        "message": message
                    })

        return results

    def export_chat(self, chat_id: str) -> Optional[str]:
        """
        Export chat as JSON string.

        Args:
            chat_id: Chat UUID

        Returns:
            JSON string or None
        """
        chat = self.get_chat(chat_id)
        if not chat:
            return None
        return json.dumps(chat, indent=2, ensure_ascii=False)

    # MARKER_108_3: Chat digest for MCP context
    def get_chat_digest(self, chat_id: str, max_messages: int = 10) -> dict:
        """
        Get compressed chat context for MCP agents.

        Phase 108.3: Provides lightweight chat summary for MCP context injection.
        Returns recent messages, agent logs, and optional ELISION summary.

        Args:
            chat_id: Chat UUID
            max_messages: Max recent messages to include (default 10)

        Returns:
            Dict with chat_id, recent_messages, agent_logs, summary
        """
        chat = self.get_chat(chat_id)
        if not chat:
            return {
                "chat_id": chat_id,
                "error": "Chat not found",
                "recent_messages": [],
                "agent_logs": [],
                "summary": ""
            }

        # Get recent messages (last N)
        all_messages = chat.get("messages", [])
        recent_messages = all_messages[-max_messages:] if len(all_messages) > max_messages else all_messages

        # Extract agent logs (messages with role="agent" or role="system")
        agent_logs = [
            {
                "sender": msg.get("sender_id", msg.get("role", "unknown")),
                "content": msg.get("content", "")[:200],  # Truncate to 200 chars
                "timestamp": msg.get("timestamp", ""),
                "type": msg.get("message_type", "chat")
            }
            for msg in recent_messages
            if msg.get("role") in ["agent", "system"] or msg.get("sender_id", "").startswith("agent_")
        ]

        # Create basic summary
        total_messages = len(all_messages)
        user_messages = sum(1 for m in all_messages if m.get("role") == "user")
        assistant_messages = sum(1 for m in all_messages if m.get("role") == "assistant")

        summary = (
            f"Chat {chat.get('display_name', chat.get('file_name', 'Unknown'))} "
            f"({total_messages} messages: {user_messages} user, {assistant_messages} assistant)"
        )

        # Optional: Try to use ELISION compression for summary if available
        try:
            from src.memory.elision import compress_context
            compressed = compress_context({"messages": recent_messages})
            if compressed and isinstance(compressed, str):
                summary += f" | Compressed: {compressed[:150]}..."
        except Exception:
            # If ELISION unavailable, skip compression
            pass

        return {
            "chat_id": chat_id,
            "recent_messages": [
                {
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")[:500],  # Truncate for digest
                    "timestamp": msg.get("timestamp", ""),
                    "sender": msg.get("sender_id", msg.get("role", "unknown"))
                }
                for msg in recent_messages
            ],
            "agent_logs": agent_logs,
            "summary": summary,
            "context_type": chat.get("context_type", "file"),
            "file_path": chat.get("file_path", "unknown"),
            "total_messages": total_messages
        }


# Singleton instance
_manager: Optional[ChatHistoryManager] = None


def get_chat_history_manager(history_file: str = "data/chat_history.json") -> ChatHistoryManager:
    """
    Get or create ChatHistoryManager singleton.

    Args:
        history_file: Path to history JSON file

    Returns:
        ChatHistoryManager instance
    """
    global _manager
    if _manager is None:
        _manager = ChatHistoryManager(history_file)
    return _manager
