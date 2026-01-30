"""
VETKA Chat Manager.

Context-aware chat system for tree-integrated messaging.
Features:
- Node context tracking (path, metadata)
- Agent delegation with @mentions
- Threading with reply_to
- Baton passing visualization
- Artifact tracking

@status: active
@phase: 96
@depends: datetime, typing, uuid
@used_by: chat.__init__, api.handlers
"""

from datetime import datetime
from typing import List, Dict, Optional
from uuid import uuid4


class ChatManager:
    """Manages chat messages integrated with VETKA tree nodes."""

    def __init__(self):
        self.messages: List[Dict] = []
        self.active_node_id: Optional[str] = None
        self.active_path: List[str] = ["Root"]
        self.active_metadata: Dict = {}

    def set_context(self, node_id: str, path: List[str], metadata: dict):
        """
        Set active node context for new messages.

        Args:
            node_id: Current node ID
            path: Breadcrumb path from root to node
            metadata: Node metadata (agent, entropy, eval_score, etc.)
        """
        self.active_node_id = node_id
        self.active_path = path
        self.active_metadata = metadata

    def add_message(
        self,
        agent: str,
        content: str,
        reply_to: Optional[str] = None,
        delegated_to: Optional[str] = None,
        artifacts: Optional[List[str]] = None,
        status: str = "done"
    ) -> Dict:
        """
        Add a new message to the chat.

        Args:
            agent: Agent type (PM, Dev, QA, ARC, Human, System)
            content: Message content
            reply_to: ID of message being replied to
            delegated_to: Agent being delegated to (baton pass)
            artifacts: List of created files/resources
            status: Message status (pending, in_progress, done, error)

        Returns:
            Created message dict
        """
        # Parse @mentions for delegation
        if delegated_to is None:
            import re
            mention = re.search(r'@(PM|Dev|QA|ARC)\b', content, re.IGNORECASE)
            if mention:
                delegated_to = mention.group(1)

        msg = {
            "id": f"msg_{uuid4().hex[:8]}",
            "node_id": self.active_node_id,
            "node_path": self.active_path.copy(),
            "agent": agent,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "reply_to": reply_to,
            "delegated_to": delegated_to,
            "status": status,
            "artifacts": artifacts or [],
            "metadata": {
                "entropy": self.active_metadata.get("entropy", 0),
                "eval_score": self.active_metadata.get("eval_score", 0),
            }
        }

        self.messages.append(msg)
        return msg

    def get_thread(self, node_id: str) -> List[Dict]:
        """
        Get all messages for a node and its children.

        Args:
            node_id: Node ID to get messages for

        Returns:
            List of messages related to the node
        """
        return [
            m for m in self.messages
            if m["node_id"] == node_id or node_id in (m.get("node_path") or [])
        ]

    def get_by_agent(self, agent: str) -> List[Dict]:
        """Get all messages from a specific agent."""
        return [m for m in self.messages if m["agent"] == agent]

    def get_delegations(self) -> List[Dict]:
        """Get all messages with delegations (baton passes)."""
        return [m for m in self.messages if m.get("delegated_to")]

    def get_replies(self, message_id: str) -> List[Dict]:
        """Get all replies to a specific message."""
        return [m for m in self.messages if m.get("reply_to") == message_id]

    def to_json(self) -> List[Dict]:
        """Export all messages as JSON-serializable list."""
        return self.messages.copy()

    def from_json(self, messages: List[Dict]):
        """Import messages from JSON list."""
        self.messages = messages.copy()

    def clear(self):
        """Clear all messages."""
        self.messages = []
