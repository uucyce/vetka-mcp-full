"""
VETKA Chat Module.

Context-aware chat system for tree-integrated messaging.
Supports agent delegation, threading, and baton passing.

@status: active
@phase: 96
@depends: chat_manager
@used_by: api.handlers, orchestration
"""

from .chat_manager import ChatManager

__all__ = ["ChatManager"]
