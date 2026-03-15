"""
VETKA Phase 99 - Short-Term Memory Buffer (STM)

Fast-access buffer for the most recent 5-10 interactions with automatic decay.
Integrates with HOPE for quick context and CAM for surprise events.

@file stm_buffer.py
@status active
@phase 99
@depends dataclasses, datetime, typing, collections, logging
@used_by langgraph_nodes.py, cam_engine.py, hope_enhancer.py, useStore.ts

MARKER-99-01: STM decay formula - weight *= (1 - decay_rate * (age_seconds / 60))
"""

import os
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class STMConfig:
    """Configuration for STM Buffer with env var overrides.

    MARKER_118.8_STM_CONFIG
    All defaults match current hardcoded values for backward compatibility.
    Override via VETKA_STM_* environment variables.
    """
    max_size: int = int(os.getenv("VETKA_STM_MAX_SIZE", "10"))
    decay_rate: float = float(os.getenv("VETKA_STM_DECAY_RATE", "0.1"))
    min_weight: float = float(os.getenv("VETKA_STM_MIN_WEIGHT", "0.1"))
    surprise_base_weight: float = float(os.getenv("VETKA_STM_SURPRISE_BASE", "1.0"))
    surprise_preserve_coeff: float = float(os.getenv("VETKA_STM_SURPRISE_PRESERVE", "0.3"))
    hope_weight: float = float(os.getenv("VETKA_STM_HOPE_WEIGHT", "1.2"))
    hope_truncate: int = int(os.getenv("VETKA_STM_HOPE_TRUNCATE", "500"))


@dataclass
class STMEntry:
    """
    Single entry in Short-Term Memory buffer.

    Attributes:
        content: The text content of this memory
        timestamp: When this entry was created
        source: Origin of the entry ('user', 'agent', 'system', 'hope', 'cam_surprise', 'pipeline')
        weight: Current weight (decays over time, boosted by surprise)
        surprise_score: CAM-detected novelty score (0.0-1.0)
        metadata: Optional additional data (workflow_id, group_id, etc.)
    """
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "system"  # 'user', 'agent', 'system', 'hope', 'cam_surprise', 'pipeline'
    weight: float = 1.0
    surprise_score: float = 0.0
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON/frontend."""
        return {
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "weight": self.weight,
            "surprise_score": self.surprise_score,
            "metadata": self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "STMEntry":
        """Deserialize from JSON."""
        return cls(
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data.get("source", "system"),
            weight=data.get("weight", 1.0),
            surprise_score=data.get("surprise_score", 0.0),
            metadata=data.get("metadata")
        )


class STMBuffer:
    """
    Short-Term Memory Buffer with automatic decay.

    Maintains the most recent N interactions with time-based weight decay.
    High-surprise items from CAM get boosted initial weights.

    Usage:
        stm = STMBuffer(max_size=10, decay_rate=0.1)
        stm.add(STMEntry(content="Hello", source="user"))
        context = stm.get_context(max_items=5)  # sorted by weight

    MARKER-99-01: Decay formula applies on each add() call
    """

    def __init__(
        self,
        max_size: int = None,
        decay_rate: float = None,
        min_weight: float = None,
        config: STMConfig = None
    ):
        """
        Initialize STM buffer.

        Args:
            max_size: Maximum entries to keep (oldest evicted on overflow)
            decay_rate: Weight decay per minute (0.1 = 10% per minute)
            min_weight: Minimum weight before entry is considered stale
            config: Optional STMConfig with env var overrides
        """
        cfg = config or STMConfig()
        self._config = cfg
        self.max_size = max_size if max_size is not None else cfg.max_size
        self.decay_rate = decay_rate if decay_rate is not None else cfg.decay_rate
        self.min_weight = min_weight if min_weight is not None else cfg.min_weight
        self._buffer: deque[STMEntry] = deque(maxlen=self.max_size)

        logger.debug(f"STMBuffer initialized: max_size={self.max_size}, decay_rate={self.decay_rate}")

    def add(self, entry: STMEntry) -> None:
        """
        Add entry to buffer, applying decay to existing items.

        Args:
            entry: STMEntry to add
        """
        self._apply_decay()
        self._buffer.append(entry)
        logger.debug(f"STM add: source={entry.source}, weight={entry.weight:.2f}")

    def add_message(
        self,
        content: str,
        source: str = "system",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Convenience method to add a simple message.

        Args:
            content: Text content
            source: Message source ('user', 'agent', 'system', 'hope')
            metadata: Optional metadata dict
        """
        entry = STMEntry(
            content=content,
            timestamp=datetime.now(),
            source=source,
            metadata=metadata
        )
        self.add(entry)

    def add_from_cam(self, content: str, surprise_score: float) -> None:
        """
        Add CAM surprise event with boosted weight.

        FIX_99.1: Surprise boosts initial weight for longer retention.

        Args:
            content: Content that triggered surprise
            surprise_score: CAM surprise metric (0.0-1.0)
        """
        entry = STMEntry(
            content=content,
            timestamp=datetime.now(),
            source="cam_surprise",
            weight=self._config.surprise_base_weight + surprise_score,
            surprise_score=surprise_score
        )
        self.add(entry)
        logger.info(f"STM surprise event: score={surprise_score:.2f}, boosted_weight={entry.weight:.2f}")

    def add_from_hope(self, summary: str, workflow_id: Optional[str] = None) -> None:
        """
        Add HOPE analysis summary to STM.

        Args:
            summary: HOPE analysis summary (truncated to 500 chars)
            workflow_id: Optional workflow identifier
        """
        entry = STMEntry(
            content=summary[:self._config.hope_truncate],
            timestamp=datetime.now(),
            source="hope",
            weight=self._config.hope_weight,
            metadata={"workflow_id": workflow_id} if workflow_id else None
        )
        self.add(entry)

    def get_context(self, max_items: int = 5) -> List[STMEntry]:
        """
        Get recent items sorted by weight (highest first).

        Args:
            max_items: Maximum entries to return

        Returns:
            List of STMEntry sorted by weight descending
        """
        if not self._buffer:
            return []

        # Apply decay before returning
        self._apply_decay()

        # Sort by weight, return top N
        sorted_entries = sorted(self._buffer, key=lambda x: x.weight, reverse=True)
        return sorted_entries[:max_items]

    def get_context_string(self, max_items: int = 5, separator: str = "\n") -> str:
        """
        Get context as a formatted string for prompt injection.

        Args:
            max_items: Maximum entries to include
            separator: String between entries

        Returns:
            Formatted string of recent context
        """
        entries = self.get_context(max_items)
        if not entries:
            return ""

        lines = []
        for entry in entries:
            prefix = f"[{entry.source}]" if entry.source != "system" else ""
            lines.append(f"{prefix} {entry.content}".strip())

        return separator.join(lines)

    def get_all(self) -> List[STMEntry]:
        """Get all entries without filtering."""
        self._apply_decay()
        return list(self._buffer)

    def get_entries_for_session(self, session_id: str) -> List[STMEntry]:
        """Get all entries with a specific session_id in metadata.

        MARKER_183.3: Enables querying STM by pipeline session.
        """
        return [
            e for e in self._buffer
            if e.metadata and e.metadata.get("session_id") == session_id
        ]

    def clear(self) -> None:
        """Clear all entries from buffer."""
        self._buffer.clear()
        logger.debug("STM buffer cleared")

    def _apply_decay(self) -> None:
        """
        Reduce weights of older items based on age.

        MARKER-99-01: Decay formula with adaptive surprise preservation
        base_decay = weight * (1 - decay_rate * (age_seconds / 60))

        FIX_99.2: Surprise items decay slower (0.3 soft coefficient)
        - surprise_score=0 → full decay (preservation=1.0)
        - surprise_score=1 → 30% slower decay (preservation=1.3)

        NOTE: Only applies decay when decay_factor < 1.0 to prevent weight inflation
        """
        now = datetime.now()
        for entry in self._buffer:
            age_seconds = (now - entry.timestamp).total_seconds()
            base_decay = self.decay_rate * (age_seconds / 60)

            # Only apply decay if there's actual decay to apply
            if base_decay <= 0:
                continue

            decay_factor = 1 - base_decay

            # FIX_99.2: Adaptive surprise preservation (soft coefficient 0.3)
            # High-surprise items decay 30% slower to maintain important context
            # This reduces the decay amount, not multiplies the weight
            coeff = self._config.surprise_preserve_coeff
            surprise_preservation = 1.0 + (entry.surprise_score * coeff)

            # Apply surprise preservation to reduce decay impact
            adjusted_decay = decay_factor + (1 - decay_factor) * (entry.surprise_score * coeff)
            adjusted_decay = max(0, min(1.0, adjusted_decay))  # Clamp to [0, 1]

            entry.weight = max(self.min_weight, entry.weight * adjusted_decay)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize entire buffer for state persistence."""
        return {
            "entries": [e.to_dict() for e in self._buffer],
            "max_size": self.max_size,
            "decay_rate": self.decay_rate,
            "min_weight": self.min_weight
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "STMBuffer":
        """Restore buffer from serialized state."""
        buffer = cls(
            max_size=data.get("max_size", 10),
            decay_rate=data.get("decay_rate", 0.1),
            min_weight=data.get("min_weight", 0.1)
        )
        for entry_data in data.get("entries", []):
            buffer._buffer.append(STMEntry.from_dict(entry_data))
        return buffer

    def __len__(self) -> int:
        return len(self._buffer)

    def __bool__(self) -> bool:
        return len(self._buffer) > 0

    def __repr__(self) -> str:
        return f"STMBuffer(size={len(self)}/{self.max_size}, decay_rate={self.decay_rate})"


# === Thread-safe singleton (MARKER_118.8_SINGLETON) ===
_stm_lock = threading.Lock()
_global_stm: Optional[STMBuffer] = None


def get_stm_buffer() -> STMBuffer:
    """Get or create global STM buffer instance (thread-safe)."""
    global _global_stm
    if _global_stm is None:
        with _stm_lock:
            if _global_stm is None:
                _global_stm = STMBuffer()
                logger.info("Global STM buffer initialized")
    return _global_stm


def reset_stm_buffer() -> None:
    """Reset global STM buffer (for testing)."""
    global _global_stm
    with _stm_lock:
        _global_stm = None
