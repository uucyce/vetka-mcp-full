"""
Chat History Manager - Persistent storage for chat messages.

Features:
- Store/load chat history from JSON
- Create chats per file path with normalization
- Organize by updated_at timestamp
- Support for group chats with multiple files
- Search messages by content

@status: active
@phase: 96
@depends: json, pathlib, datetime, typing, uuid
@used_by: api.handlers.chat_handler, services.group_chat_manager
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid


class ChatHistoryManager:
    """Manages persistent chat history storage."""

    def __init__(self, history_file: str = "data/chat_history.json"):
        """Initialize ChatHistoryManager with file path."""
        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.history = self._load()

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

    def _save(self) -> None:
        """Save history to JSON file."""
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
        display_name: Optional[str] = None
    ) -> str:
        """
        Get existing chat for file or create new one.

        Phase 51.1 Fix: Normalize paths to prevent duplicate chats for same file.
        Phase 74: Extended schema with context_type, items, topic, display_name.

        Args:
            file_path: File path to associate with chat
            context_type: Type of context - "file", "folder", "group", or "topic"
            items: List of file paths for group chats
            topic: Topic name for topic-based chats (no file)
            display_name: Custom display name for the chat

        Returns:
            Chat UUID
        """
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
        chat_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        # Phase 74: Determine file_name based on context_type
        if normalized_path not in ('unknown', 'root', ''):
            file_name = Path(normalized_path).name
        else:
            file_name = normalized_path

        # Phase 74.10: Strip display_name to prevent trailing space issues
        clean_display_name = display_name.strip() if display_name else None

        self.history["chats"][chat_id] = {
            "id": chat_id,
            "file_path": normalized_path,
            "file_name": file_name,
            "display_name": clean_display_name,  # Phase 74: Custom name (Phase 74.10: stripped)
            "context_type": context_type,  # Phase 74: "file" | "folder" | "group" | "topic"
            "items": items or [],          # Phase 74: File paths for groups
            "topic": topic,                # Phase 74: Topic for file-less chats
            "pinned_file_ids": [],         # Phase 100.2: Persistent pinned files
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

    def get_all_chats(self) -> List[Dict[str, Any]]:
        """
        Get all chats sorted by updated_at (newest first).

        Returns:
            List of chat objects
        """
        chats = list(self.history["chats"].values())
        return sorted(chats, key=lambda x: x.get("updated_at", ""), reverse=True)

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
