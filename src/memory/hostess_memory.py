"""
PHASE 56.5: Hostess Memory Module.

Manages Hostess interactions with decay visualization for 3D tree.

@status: active
@phase: 96
@depends: asyncio, dataclasses
@used_by: hostess_agent.py, chat_handler.py
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class InteractionRecord:
    """Single interaction record with decay tracking."""

    file_id: str
    query: str
    response: str
    timestamp: float
    count: int = 1
    decay_factor: float = 1.0


class HostessMemory:
    """Hostess memory system with automatic decay."""

    def __init__(self, user_id: str, qdrant_client=None):
        """Initialize hostess memory for a user."""
        self.user_id = user_id
        self.interaction_tree: Dict[str, InteractionRecord] = {}
        self.qdrant_client = qdrant_client
        self._decay_task: Optional[asyncio.Task] = None
        logger.info(f"[HostessMemory] Initialized for user {user_id}")

    async def start(self):
        """Start periodic decay task."""
        self._decay_task = asyncio.create_task(self._periodic_decay())
        logger.info(f"[HostessMemory] Decay task started for {self.user_id}")

    async def stop(self):
        """Stop decay task."""
        if self._decay_task:
            self._decay_task.cancel()
            try:
                await self._decay_task
            except asyncio.CancelledError:
                pass
            logger.info(f"[HostessMemory] Decay task stopped for {self.user_id}")

    async def _periodic_decay(self):
        """Decay interaction weights every hour."""
        while True:
            try:
                await asyncio.sleep(3600)  # 1 hour
                now = datetime.now()
                to_prune = []

                for file_id, record in self.interaction_tree.items():
                    age_days = (now - datetime.fromtimestamp(record.timestamp)).days
                    record.decay_factor = max(0.1, 1.0 - (age_days * 0.05))

                    if record.decay_factor < 0.15:
                        to_prune.append(file_id)

                for file_id in to_prune:
                    del self.interaction_tree[file_id]
                    logger.debug(f"[HostessMemory] Pruned {file_id} for {self.user_id}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[HostessMemory] Decay error: {e}")

    def record_interaction(self, file_id: str, query: str, response: str):
        """Record a new interaction with the hostess."""
        if file_id in self.interaction_tree:
            record = self.interaction_tree[file_id]
            record.count += 1
            record.timestamp = time.time()
            record.decay_factor = min(1.0, record.decay_factor + 0.1)
        else:
            self.interaction_tree[file_id] = InteractionRecord(
                file_id=file_id,
                query=query,
                response=response,
                timestamp=time.time(),
            )

        logger.debug(
            f"[HostessMemory] Recorded interaction for {file_id} ({self.interaction_tree[file_id].count}x)"
        )

    def get_recent_context(self, limit: int = 5) -> str:
        """Get recent interactions for context injection."""
        sorted_records = sorted(
            self.interaction_tree.items(),
            key=lambda x: x[1].timestamp,
            reverse=True,
        )[:limit]

        context_lines = []
        for file_id, record in sorted_records:
            preview = record.response[:150]
            context_lines.append(f"File {file_id} ({record.count}x): {preview}...")

        return "\n".join(context_lines) if context_lines else ""

    def get_visual_tree_data(self) -> Dict:
        """Export for frontend visualization."""
        nodes = [
            {
                "id": file_id,
                "label": f"{file_id.split('/')[-1]} ({record.count}x)",
                "size": min(10, record.count * 2),
                "opacity": record.decay_factor,
            }
            for file_id, record in self.interaction_tree.items()
        ]

        return {"nodes": nodes}

    def clear(self):
        """Clear all interactions."""
        self.interaction_tree.clear()
        logger.info(f"[HostessMemory] Cleared all interactions for {self.user_id}")

    @property
    def stats(self) -> Dict:
        """Get memory statistics."""
        return {
            "total_interactions": len(self.interaction_tree),
            "total_visits": sum(r.count for r in self.interaction_tree.values()),
            "avg_decay": (
                sum(r.decay_factor for r in self.interaction_tree.values())
                / len(self.interaction_tree)
                if self.interaction_tree
                else 0
            ),
        }
