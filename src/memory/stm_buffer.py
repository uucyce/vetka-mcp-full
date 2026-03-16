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
MARKER_187.5: Exponential decay + rehearsal + adaptive maxlen (Phase 187)
"""

import math
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

    # MARKER_187.5: Adaptive maxlen from model context_length
    # Caller passes context_length from LLMModelRegistry.get_profile()
    # STM scales: small model (≤8k) → 6 entries, large (>32k) → 15
    stm_size_small: int = 6    # ≤8k context
    stm_size_medium: int = 10  # ≤32k context
    stm_size_large: int = 15   # >32k context


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
        config: STMConfig = None,
        model_context_length: int = 0,
    ):
        """
        Initialize STM buffer.

        Args:
            max_size: Maximum entries to keep (oldest evicted on overflow)
            decay_rate: Weight decay per minute (0.1 = 10% per minute)
            min_weight: Minimum weight before entry is considered stale
            config: Optional STMConfig with env var overrides
            model_context_length: MARKER_187.5 — from LLMModelRegistry for adaptive maxlen
        """
        cfg = config or STMConfig()
        self._config = cfg

        # MARKER_187.5: Adaptive maxlen from model context window
        # Caller gets context_length from LLMModelRegistry.get_profile()
        if max_size is not None:
            self.max_size = max_size
        elif model_context_length > 0:
            self.max_size = self._maxlen_from_context(model_context_length, cfg)
        else:
            self.max_size = cfg.max_size

        self.decay_rate = decay_rate if decay_rate is not None else cfg.decay_rate
        self.min_weight = min_weight if min_weight is not None else cfg.min_weight
        self._buffer: deque[STMEntry] = deque(maxlen=self.max_size)

        logger.debug(f"STMBuffer initialized: max_size={self.max_size}, decay_rate={self.decay_rate}, model_ctx={model_context_length}")

    @staticmethod
    def _maxlen_from_context(context_length: int, cfg: STMConfig) -> int:
        """MARKER_187.5: Derive STM buffer size from model context window.

        Small models (≤8k) can't fit much STM in prompt → fewer entries.
        Large models (>32k) have room → more entries for richer context.
        """
        if context_length <= 8192:
            return cfg.stm_size_small     # 6
        elif context_length <= 32768:
            return cfg.stm_size_medium    # 10
        return cfg.stm_size_large         # 15

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

    def rehearse(self, content_substring: str) -> bool:
        """MARKER_187.5: Rehearsal — reset timestamp on re-accessed entry.

        When an entry is accessed again, its age resets to 0, keeping it fresh.
        Returns True if a matching entry was found and rehearsed.
        """
        needle = content_substring.lower()
        for entry in self._buffer:
            if needle in entry.content.lower():
                entry.timestamp = datetime.now()
                logger.debug(f"STM rehearsal: refreshed entry (source={entry.source})")
                return True
        return False

    def _apply_decay(self) -> None:
        """
        Reduce weights of older items based on age.

        MARKER_187.5: Exponential decay replaces linear decay (Phase 187).
        Old: weight *= (1 - decay_rate * age_minutes)  → goes to 0 at 10 min
        New: weight *= exp(-decay_rate * age_minutes)   → gradual, never zero

        FIX_99.2: Surprise items decay slower (0.3 soft coefficient)
        - surprise_score=0 → full decay rate
        - surprise_score=1 → 30% slower decay (effective_rate *= 0.7)
        """
        now = datetime.now()
        for entry in self._buffer:
            age_minutes = (now - entry.timestamp).total_seconds() / 60.0

            if age_minutes <= 0:
                continue

            # FIX_99.2: Surprise preservation — reduce effective decay rate
            coeff = self._config.surprise_preserve_coeff
            effective_rate = self.decay_rate * (1.0 - entry.surprise_score * coeff)
            effective_rate = max(0.0, effective_rate)  # Clamp

            # MARKER_187.5: Exponential decay — gradual, never hits zero
            decay_factor = math.exp(-effective_rate * age_minutes)

            entry.weight = max(self.min_weight, entry.weight * decay_factor)

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


def get_stm_buffer(model_context_length: int = 0) -> STMBuffer:
    """Get or create global STM buffer instance (thread-safe).

    MARKER_187.5: Pass model_context_length on first call for adaptive maxlen.
    Subsequent calls ignore the parameter (singleton already created).
    Caller gets context_length from: await get_llm_registry().get_profile(model_id)
    """
    global _global_stm
    if _global_stm is None:
        with _stm_lock:
            if _global_stm is None:
                _global_stm = STMBuffer(model_context_length=model_context_length)
                logger.info(f"Global STM buffer initialized (max_size={_global_stm.max_size})")
    return _global_stm


def reset_stm_buffer() -> None:
    """Reset global STM buffer (for testing)."""
    global _global_stm
    with _stm_lock:
        _global_stm = None
