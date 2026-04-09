"""
VETKA Context Builders - DRY Context Building Logic.

Consolidates repeated context building code into single source of truth.
Builds LLM context from file context, chat history, pinned files,
viewport spatial data, and JSON dependency graphs.

@status: active
@phase: 96
@depends: message_utils, handler_utils, chat_handler, chat.chat_history_manager
@used_by: di_container, models.model_client
"""

from typing import Dict, Any, List, Optional
from ..message_utils import (
    format_history_for_prompt,
    build_pinned_context,
    build_viewport_summary,
    build_json_context
)
from ..handler_utils import sync_get_rich_context, format_context_for_agent
from ..chat_handler import build_model_prompt
from src.chat.chat_history_manager import get_chat_history_manager


class ContextBuilder:
    """
    Builds complete LLM context from multiple sources.

    This class implements the IContextProvider interface and consolidates
    the repeated context building logic from user_message_handler.py.
    """

    def __init__(self):
        """Initialize context builder."""
        self.chat_history_manager = get_chat_history_manager()

    async def build_context(
        self,
        node_path: str,
        text: str,
        pinned_files: List[Dict[str, Any]],
        viewport_context: Optional[Dict[str, Any]],
        session_id: str,
        model_name: str,
        max_history: int = 10
    ) -> Dict[str, Any]:
        """
        Build complete context for LLM call.

        This method consolidates the logic from lines 254-291, 399-436, 638-675
        of user_message_handler.py.

        Args:
            node_path: File path being discussed
            text: User message text
            pinned_files: List of pinned file contexts
            viewport_context: 3D viewport spatial data
            session_id: Socket.IO session ID
            model_name: Model being called (for legend tracking)
            max_history: Maximum history messages to include

        Returns:
            Dictionary with all context components:
            {
                'chat_id': str,
                'history_messages': List[Dict],
                'history_context': str,
                'file_context': str,
                'pinned_context': str,
                'viewport_summary': str,
                'json_context': str,
                'model_prompt': str
            }
        """

        # Load chat history
        chat_id = self.chat_history_manager.get_or_create_chat(node_path)
        history_messages = self.chat_history_manager.get_chat_messages(chat_id)
        history_context = format_history_for_prompt(history_messages, max_messages=max_history)

        print(f"[CONTEXT_BUILDER] Loaded {len(history_messages)} history messages for {node_path}")

        # Get file context via Elisya
        rich_context = sync_get_rich_context(node_path)
        if rich_context.get('error'):
            context_for_model = f"File: {node_path}\nStatus: {rich_context['error']}"
        else:
            context_for_model = format_context_for_agent(rich_context, 'generic')

        # Build pinned files context with smart selection
        pinned_context = build_pinned_context(pinned_files, user_query=text) if pinned_files else ""

        # Build viewport summary for spatial awareness
        viewport_summary = build_viewport_summary(viewport_context) if viewport_context else ""

        # Build JSON dependency context for AI agents
        # Phase 73.6: Pass session_id for cold start legend detection
        # Phase 73.6.2: Pass model_name for per-model legend tracking
        json_context = build_json_context(pinned_files, viewport_context, session_id=session_id, model_name=model_name)

        # Build final model prompt
        model_prompt = build_model_prompt(
            text,
            context_for_model,
            pinned_context,
            history_context,
            viewport_summary,
            json_context
        )

        return {
            'chat_id': chat_id,
            'history_messages': history_messages,
            'history_context': history_context,
            'file_context': context_for_model,
            'pinned_context': pinned_context,
            'viewport_summary': viewport_summary,
            'json_context': json_context,
            'model_prompt': model_prompt
        }

    def build_context_sync(
        self,
        node_path: str,
        text: str,
        pinned_files: List[Dict[str, Any]],
        viewport_context: Optional[Dict[str, Any]],
        session_id: str,
        model_name: str,
        max_history: int = 10
    ) -> Dict[str, Any]:
        """
        Synchronous version of build_context for use in non-async contexts.

        This is needed because the original code uses sync calls in some places.
        Eventually this should be refactored to async everywhere.
        """
        # Load chat history
        chat_id = self.chat_history_manager.get_or_create_chat(node_path)
        history_messages = self.chat_history_manager.get_chat_messages(chat_id)
        history_context = format_history_for_prompt(history_messages, max_messages=max_history)

        print(f"[CONTEXT_BUILDER] Loaded {len(history_messages)} history messages for {node_path}")

        # Get file context via Elisya
        rich_context = sync_get_rich_context(node_path)
        if rich_context.get('error'):
            context_for_model = f"File: {node_path}\nStatus: {rich_context['error']}"
        else:
            context_for_model = format_context_for_agent(rich_context, 'generic')

        # Build pinned files context with smart selection
        pinned_context = build_pinned_context(pinned_files, user_query=text) if pinned_files else ""

        # Build viewport summary for spatial awareness
        viewport_summary = build_viewport_summary(viewport_context) if viewport_context else ""

        # Build JSON dependency context for AI agents
        json_context = build_json_context(pinned_files, viewport_context, session_id=session_id, model_name=model_name)

        # Build final model prompt
        model_prompt = build_model_prompt(
            text,
            context_for_model,
            pinned_context,
            history_context,
            viewport_summary,
            json_context
        )

        return {
            'chat_id': chat_id,
            'history_messages': history_messages,
            'history_context': history_context,
            'file_context': context_for_model,
            'pinned_context': pinned_context,
            'viewport_summary': viewport_summary,
            'json_context': json_context,
            'model_prompt': model_prompt
        }


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_context_builder_instance = None


def get_context_builder() -> ContextBuilder:
    """
    Get singleton ContextBuilder instance.

    This follows the pattern from src/initialization/components_init.py
    for thread-safe singleton initialization.
    """
    global _context_builder_instance
    if _context_builder_instance is None:
        _context_builder_instance = ContextBuilder()
    return _context_builder_instance
