"""
Handler Utilities - Phase 44.6.

Shared utilities for Socket.IO handlers including file context and chat persistence.

@status: active
@phase: 96
@depends: os, threading, chat_history_manager
@used_by: chat_handler.py, user_message_handler.py
"""

import os
import threading
from typing import Dict, Any, Optional


# ============================================================
# AVAILABILITY FLAGS
# ============================================================

HOSTESS_AVAILABLE = False  # Phase 80.41: Muted - будет работать в фоне
ROLE_PROMPTS_AVAILABLE = True


# ============================================================
# AGENT REGISTRY
# ============================================================

_agents_registry: Dict[str, Any] = {}


def get_agents() -> Dict[str, Any]:
    """
    Get agents registry. Returns initialized agents or empty dict.

    Agents are populated during startup by the initialization system.
    """
    global _agents_registry
    return _agents_registry


def set_agents(agents: Dict[str, Any]) -> None:
    """Set the agents registry. Called during initialization."""
    global _agents_registry
    _agents_registry = agents


# ============================================================
# FILE CONTEXT FUNCTIONS
# ============================================================


def sync_get_rich_context(node_path: str) -> Dict[str, Any]:
    """
    Get rich context for a file/node path.
    Returns file content and metadata for LLM context.

    Args:
        node_path: File path to read (absolute or relative)

    Returns:
        Dict with file_path, file_content, file_metadata, error
    """
    result = {
        "file_path": node_path,
        "file_content": "",
        "file_metadata": {"lines": 0, "size": 0},
        "error": None,
    }

    if not node_path or node_path in ["/", "root", "unknown", "/test"]:
        result["error"] = "No specific file selected"
        return result

    # Handle absolute and relative paths
    if os.path.isabs(node_path):
        filepath = node_path
    else:
        filepath = os.path.join(os.getcwd(), node_path.lstrip("/"))

    # Phase 74: Support both files and directories
    if not (os.path.isfile(filepath) or os.path.isdir(filepath)):
        result["error"] = f"Path not found: {filepath}"
        return result

    # Phase 74: Handle directory context
    if os.path.isdir(filepath):
        try:
            files_in_dir = []
            aggregated_content = []
            total_lines = 0
            total_size = 0

            # Collect readable files from directory
            for entry in sorted(os.listdir(filepath)):
                entry_path = os.path.join(filepath, entry)
                if os.path.isfile(entry_path):
                    files_in_dir.append(entry)
                    # Try to read text files
                    try:
                        with open(
                            entry_path, "r", encoding="utf-8", errors="ignore"
                        ) as f:
                            file_content = f.read()
                            lines = file_content.count("\n") + 1
                            size = len(file_content.encode("utf-8"))

                            # Only include if not too large (limit per file)
                            if size < 50000:  # 50KB limit per file
                                aggregated_content.append(
                                    f"--- {entry} ({lines} lines) ---\n{file_content}"
                                )
                                total_lines += lines
                                total_size += size
                    except Exception:
                        # Skip binary or unreadable files
                        pass

            result["file_content"] = (
                "\n\n".join(aggregated_content)
                if aggregated_content
                else f"Directory with {len(files_in_dir)} files"
            )
            result["file_metadata"] = {
                "lines": total_lines,
                "size": total_size,
                "is_directory": True,
                "file_count": len(files_in_dir),
                "files": files_in_dir[:20],  # Limit to first 20 files for metadata
            }
        except Exception as e:
            result["error"] = str(e)

        return result

    # Handle regular file
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        result["file_content"] = content
        result["file_metadata"] = {
            "lines": content.count("\n") + 1,
            "size": len(content.encode("utf-8")),
            "is_directory": False,
        }
    except Exception as e:
        result["error"] = str(e)

    return result


def format_context_for_agent(
    rich_context: Dict[str, Any], agent_type: str = "generic"
) -> str:
    """
    Format rich context into a string for LLM prompts.

    Args:
        rich_context: Dict from sync_get_rich_context()
        agent_type: Type of agent (affects formatting)

    Returns:
        Formatted string for LLM prompt
    """
    if rich_context.get("error"):
        return f"File context unavailable: {rich_context['error']}"

    content = rich_context.get("file_content", "")
    metadata = rich_context.get("file_metadata", {})
    file_path = rich_context.get("file_path", "unknown")

    if not content:
        return f"File: {file_path}\nNo content available."

    # Remove truncation - unlimited content
    # No character limits for unlimited responses

    return f"""FILE: {file_path}
LINES: {metadata.get("lines", "?")} | SIZE: {metadata.get("size", "?")} bytes

CONTENT:
```
{content}
```"""


# ============================================================
# CHAT PERSISTENCE (Phase 50)
# ============================================================


def save_chat_message(
    node_path: str,
    message: Dict[str, Any],
    pinned_files: Optional[list] = None,
    context_type: str = "file",
    chat_id: Optional[str] = None,
) -> None:
    """
    Save chat message to history.

    Phase 50: Implemented persistent chat storage via ChatHistoryManager.
    Phase 51.1 Fix: Normalize path to prevent duplicate chats.
    Phase 74: Added pinned_files support for group chats.

    Args:
        node_path: Associated file path
        message: Message dict with role, text, content, agent, etc.
        pinned_files: Optional list of pinned file dicts for group context
        context_type: Type of context - "file", "folder", "group", or "topic"
        chat_id: Optional stable chat UUID from frontend/session. When provided,
            message is written to this chat to prevent chat fragmentation.
    """
    try:
        from pathlib import Path
        from src.chat.chat_history_manager import get_chat_history_manager

        # Phase 51.1 Fix: Normalize path
        if node_path and node_path not in ("unknown", "root", ""):
            try:
                normalized_path = str(Path(node_path).resolve())
            except Exception:
                normalized_path = node_path
        else:
            normalized_path = node_path

        manager = get_chat_history_manager()

        # Phase 74: Extract items from pinned_files for group chats
        items = None
        if pinned_files and len(pinned_files) > 1:
            context_type = "group"
            items = [pf.get("path", pf.get("name", "")) for pf in pinned_files]

        # MARKER_137.1: If a stable chat_id is provided, always prefer it.
        # This prevents message writes from splitting across path/context-derived chats.
        target_chat_id = chat_id
        if target_chat_id:
            existing_chat = manager.get_chat(target_chat_id)
            if not existing_chat:
                # Backward-compatible fallback: create chat with provided ID.
                target_chat_id = manager.get_or_create_chat(
                    normalized_path,
                    context_type=context_type,
                    items=items,
                    chat_id=target_chat_id,
                )
        else:
            # Legacy behavior for callers that don't provide chat_id.
            target_chat_id = manager.get_or_create_chat(
                normalized_path, context_type=context_type, items=items
            )

        # Phase 74: Update items if chat exists but pinned files changed
        if items:
            manager.update_chat_items(target_chat_id, items)

        # Normalize message format (text -> content)
        # MARKER_CHAT_HISTORY_ATTRIBUTION: Save model and provider attribution - IMPLEMENTED
        msg_to_save = {
            "role": message.get("role", "user"),
            "content": message.get("content") or message.get("text"),
            "agent": message.get("agent"),
            "model": message.get("model"),
            "model_provider": message.get("model_provider"),  # Provider attribution for model disambiguation
            "model_source": message.get("model_source"),  # MARKER_115_BUG3: model_source persistence
            "node_id": message.get("node_id"),
            "metadata": message.get("metadata", {}),
        }

        # Save to history
        manager.add_message(target_chat_id, msg_to_save)
        print(
            f"[ChatHistory] Saved {msg_to_save['role']} message to {normalized_path} (type={context_type}, chat_id={target_chat_id})"
        )

    except Exception as e:
        print(f"[ChatHistory] Error saving message: {e}")
        # Don't fail the handler if chat history save fails
        pass


# ============================================================
# API KEY MANAGEMENT
# ============================================================

_current_key_index = 0
_openrouter_keys: list = []
_key_rotation_lock = threading.Lock()  # Fix: Protect against race conditions


def get_openrouter_key() -> str:
    """Get current OpenRouter API key from config.json."""
    global _openrouter_keys
    if not _openrouter_keys:
        # Phase 57: Use APIKeyService instead of os.environ
        try:
            from src.orchestration.services.api_key_service import APIKeyService

            service = APIKeyService()
            key = service.get_key("openrouter")
            if key:
                _openrouter_keys = [key]
        except Exception as e:
            print(f"[handler_utils] Failed to get key from config: {e}")

    if _openrouter_keys:
        return _openrouter_keys[_current_key_index % len(_openrouter_keys)]
    return ""


def rotate_openrouter_key(mark_failed: bool = False) -> None:
    """
    Rotate to next OpenRouter API key.

    Args:
        mark_failed: If True, mark current key as failed
    """
    global _current_key_index
    with _key_rotation_lock:  # Fix: Atomic operation to prevent race condition
        _current_key_index += 1
