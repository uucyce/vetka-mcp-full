"""
Chat Registry - Per-session chat management.

Prevents race conditions and message mixing between users.
Features:
- SessionChatManager: Per-session, per-node message storage
- ChatRegistry: Global registry mapping session_id to manager
- Thread isolation: Each node has its own message thread
- Clean disconnect handling

@status: active
@phase: 96
@depends: typing, dataclasses, datetime
@used_by: api.handlers.chat_handler, services.group_chat_manager
"""

from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    """Single chat message."""
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    agent: Optional[str] = None
    node_path: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'agent': self.agent,
            'node_path': self.node_path
        }


class SessionChatManager:
    """Per-session chat manager with per-node threads."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: Dict[str, List[Message]] = {}  # node_path → messages
        self.active_node: Optional[str] = None
        self.created_at = datetime.now()
        print(f"[ChatRegistry] Created manager for session {session_id[:8]}...")

    def set_context(self, node_path: str) -> List[Message]:
        """
        Switch to node context, return its messages.

        Args:
            node_path: Node path to switch to

        Returns:
            List of messages for the node
        """
        old_node = self.active_node
        self.active_node = node_path

        if old_node != node_path:
            print(f"[Chat] Session {self.session_id[:8]}: Context switch {old_node} → {node_path}")

        return self.get_messages(node_path)

    def get_messages(self, node_path: str = None) -> List[Message]:
        """
        Get messages for node (or active node).

        Args:
            node_path: Optional node path (defaults to active_node)

        Returns:
            List of messages
        """
        path = node_path or self.active_node
        if not path:
            return []
        return self.messages.get(path, [])

    def add_message(self, message: Message, node_path: str = None):
        """
        Add message to node thread.

        Args:
            message: Message to add
            node_path: Optional node path (defaults to active_node)
        """
        path = node_path or self.active_node
        if not path:
            path = 'unknown'

        # Set node_path on message if not set
        if message.node_path is None:
            message.node_path = path

        if path not in self.messages:
            self.messages[path] = []

        self.messages[path].append(message)

    def clear_node(self, node_path: str):
        """
        Clear messages for specific node.

        Args:
            node_path: Node path to clear
        """
        if node_path in self.messages:
            print(f"[Chat] Session {self.session_id[:8]}: Cleared {len(self.messages[node_path])} messages for {node_path}")
            self.messages[node_path] = []

    def get_node_count(self) -> int:
        """Get number of nodes with messages."""
        return len(self.messages)

    def get_total_messages(self) -> int:
        """Get total message count across all nodes."""
        return sum(len(msgs) for msgs in self.messages.values())


class ChatRegistry:
    """Registry of per-session chat managers."""

    _managers: Dict[str, SessionChatManager] = {}

    @classmethod
    def get_manager(cls, session_id: str) -> SessionChatManager:
        """
        Get or create manager for session.

        Args:
            session_id: Socket.IO session ID

        Returns:
            SessionChatManager instance
        """
        if session_id not in cls._managers:
            cls._managers[session_id] = SessionChatManager(session_id)
        return cls._managers[session_id]

    @classmethod
    def remove_manager(cls, session_id: str) -> bool:
        """
        Remove manager on disconnect.

        Args:
            session_id: Socket.IO session ID

        Returns:
            True if manager was removed
        """
        if session_id in cls._managers:
            manager = cls._managers[session_id]
            print(f"[ChatRegistry] Removing manager for session {session_id[:8]} " +
                  f"({manager.get_node_count()} nodes, {manager.get_total_messages()} messages)")
            del cls._managers[session_id]
            return True
        return False

    @classmethod
    def get_active_sessions(cls) -> int:
        """
        Get count of active sessions.

        Returns:
            Number of active sessions
        """
        return len(cls._managers)

    @classmethod
    def get_stats(cls) -> dict:
        """
        Get registry statistics.

        Returns:
            Dict with registry stats
        """
        total_nodes = sum(m.get_node_count() for m in cls._managers.values())
        total_messages = sum(m.get_total_messages() for m in cls._managers.values())

        return {
            'active_sessions': len(cls._managers),
            'total_nodes': total_nodes,
            'total_messages': total_messages
        }
