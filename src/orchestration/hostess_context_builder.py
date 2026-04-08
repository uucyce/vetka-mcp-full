"""
@file hostess_context_builder.py
@status ACTIVE
@phase Phase 44

Builds rich context for HOSTESS agent routing decisions.
Integrates Elisya middleware for semantic context.
"""

import os
from typing import Dict, Any, Optional, List
from src.utils.structured_logger import logger


class HostessContextBuilder:
    """
    Builds rich context for HOSTESS to make better routing decisions.

    Context includes:
    - File content (if selected)
    - Related files (semantic similarity)
    - Recent conversation history
    - Knowledge graph context
    - User preferences
    """

    def __init__(self, memory_manager=None, elisya_middleware=None):
        """
        Initialize HostessContextBuilder.

        Args:
            memory_manager: MemoryManager instance for history
            elisya_middleware: ElisyaMiddleware for semantic context
        """
        self.memory_manager = memory_manager
        self.elisya_middleware = elisya_middleware

    def build_context(
        self,
        message: str,
        file_path: Optional[str] = None,
        conversation_id: Optional[str] = None,
        node_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Build rich context for HOSTESS routing (synchronous version).

        Args:
            message: User message
            file_path: Currently selected file (if any)
            conversation_id: Current conversation ID
            node_id: Current node ID in tree

        Returns:
            Rich context dict with all available information
        """
        context = {
            "message": message,
            "file_path": file_path,
            "node_path": file_path,  # Alias for compatibility
            "conversation_id": conversation_id,
            "node_id": node_id,
            "has_file_context": False,
            "has_semantic_context": False,
            "has_history_context": False,
        }

        # 1. Get file content if file selected
        if file_path:
            file_context = self._get_file_context(file_path)
            if file_context:
                context["file_content"] = file_context.get("content", "")[:2000]
                context["file_type"] = file_context.get("type", "unknown")
                context["file_metadata"] = file_context.get("metadata", {})
                context["has_file_context"] = True
                logger.debug(f"File context loaded: {file_path}")

        # 2. Get semantic context from Elisya (if available)
        if self.elisya_middleware:
            try:
                semantic_context = self._get_elisya_context(message, file_path)
                context["related_files"] = semantic_context.get("related_files", [])
                context["semantic_tags"] = semantic_context.get("tags", [])
                context["knowledge_snippets"] = semantic_context.get("snippets", [])
                context["has_semantic_context"] = True
                logger.debug("Elisya semantic context loaded")
            except Exception as e:
                logger.warning(f"Elisya context failed: {e}")

        # 3. Get conversation history (Phase 51.1: Use ChatHistoryManager)
        try:
            from pathlib import Path
            from src.chat.chat_history_manager import get_chat_history_manager

            # Phase 51.1: Normalize path
            if file_path and file_path not in ('unknown', 'root', ''):
                try:
                    normalized_path = str(Path(file_path).resolve())
                except Exception:
                    normalized_path = file_path
            else:
                normalized_path = file_path

            chat_manager = get_chat_history_manager()
            chat_id = chat_manager.get_or_create_chat(normalized_path)
            history = chat_manager.get_chat_messages(chat_id)

            context["recent_messages"] = history[-5:]  # Last 5 messages
            context["has_history_context"] = len(history) > 0
            logger.debug(f"[PHASE_51.1] History loaded: {len(history)} messages for {normalized_path}")
        except Exception as e:
            logger.warning(f"History load failed: {e}")
            context["recent_messages"] = []
            context["has_history_context"] = False

        # 4. Build summary for HOSTESS prompt
        context["context_summary"] = self._build_summary(context)

        return context

    async def build_context_async(
        self,
        message: str,
        file_path: Optional[str] = None,
        conversation_id: Optional[str] = None,
        node_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Build rich context for HOSTESS routing (async version).
        Wraps sync version for compatibility.
        """
        return self.build_context(
            message=message,
            file_path=file_path,
            conversation_id=conversation_id,
            node_id=node_id,
            **kwargs
        )

    def _get_file_context(self, file_path: str) -> Optional[Dict]:
        """Get file content and metadata."""
        try:
            # Handle relative paths
            if not os.path.isabs(file_path):
                # Try relative to project root
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                full_path = os.path.join(project_root, file_path)
            else:
                full_path = file_path

            if not os.path.exists(full_path):
                logger.debug(f"File not found: {full_path}")
                return None

            # Don't read very large files
            file_size = os.path.getsize(full_path)
            if file_size > 100000:  # 100KB limit
                return {
                    "content": f"[File too large: {file_size} bytes]",
                    "type": os.path.splitext(file_path)[1],
                    "metadata": {
                        "size": file_size,
                        "name": os.path.basename(file_path),
                        "truncated": True
                    }
                }

            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            return {
                "content": content,
                "type": os.path.splitext(file_path)[1],
                "metadata": {
                    "size": file_size,
                    "name": os.path.basename(file_path),
                    "lines": content.count('\n') + 1
                }
            }
        except Exception as e:
            logger.error(f"File read error for {file_path}: {e}")
            return None

    def _get_elisya_context(self, message: str, file_path: Optional[str]) -> Dict:
        """Get semantic context from Elisya middleware."""
        if not self.elisya_middleware:
            return {}

        try:
            # Call Elisya's get_context method
            if hasattr(self.elisya_middleware, 'get_rich_context'):
                return self.elisya_middleware.get_rich_context(
                    query=message,
                    file_path=file_path
                )
            elif hasattr(self.elisya_middleware, 'get_context'):
                return self.elisya_middleware.get_context(file_path)
            else:
                return {}
        except Exception as e:
            logger.error(f"Elisya context error: {e}")
            return {}

    def _get_conversation_history(self, conversation_id: str) -> List[Dict]:
        """Get recent conversation history."""
        if not self.memory_manager:
            return []

        try:
            if hasattr(self.memory_manager, 'get_conversation_history'):
                return self.memory_manager.get_conversation_history(conversation_id)
            elif hasattr(self.memory_manager, 'get_history'):
                return self.memory_manager.get_history(conversation_id)
            return []
        except Exception as e:
            logger.error(f"History error: {e}")
            return []

    def _build_summary(self, context: Dict) -> str:
        """Build text summary for HOSTESS prompt enhancement."""
        parts = []

        if context.get("has_file_context"):
            file_path = context.get("file_path", "unknown")
            file_type = context.get("file_type", "")
            metadata = context.get("file_metadata", {})
            lines = metadata.get("lines", "?")
            parts.append(f"User is viewing file: {file_path} ({file_type}, {lines} lines)")

        if context.get("has_semantic_context"):
            related = context.get("related_files", [])[:3]
            if related:
                parts.append(f"Related files: {', '.join(related)}")

            tags = context.get("semantic_tags", [])[:5]
            if tags:
                parts.append(f"Topics: {', '.join(tags)}")

        if context.get("has_history_context"):
            history_count = len(context.get("recent_messages", []))
            parts.append(f"Conversation has {history_count} previous messages")

        if not parts:
            return "No additional context available."

        return "\n".join(parts)


# Global singleton instance
_context_builder_instance: Optional[HostessContextBuilder] = None


def get_hostess_context_builder(
    memory_manager=None,
    elisya_middleware=None,
    force_new: bool = False
) -> HostessContextBuilder:
    """
    Get or create HostessContextBuilder singleton.

    Args:
        memory_manager: Optional MemoryManager instance
        elisya_middleware: Optional ElisyaMiddleware instance
        force_new: If True, create new instance even if exists

    Returns:
        HostessContextBuilder instance
    """
    global _context_builder_instance

    if _context_builder_instance is None or force_new:
        _context_builder_instance = HostessContextBuilder(
            memory_manager=memory_manager,
            elisya_middleware=elisya_middleware
        )

    return _context_builder_instance


def create_hostess_context_builder(app_state) -> HostessContextBuilder:
    """
    Create HostessContextBuilder with dependencies from app state.

    Args:
        app_state: FastAPI app.state with components

    Returns:
        HostessContextBuilder instance
    """
    memory_manager = getattr(app_state, 'memory_manager', None)
    elisya_middleware = getattr(app_state, 'elisya_middleware', None)

    return get_hostess_context_builder(
        memory_manager=memory_manager,
        elisya_middleware=elisya_middleware
    )
