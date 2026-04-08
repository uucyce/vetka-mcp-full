"""
REFLEX Streaming — Structured Event Emission Layer.

MARKER_173.P3.STREAMING

Provides typed REFLEX events for real-time observability across
all VETKA ecosystems (DevPanel WS, MCC, Chat, future Jarvis).

Event types:
  reflex:recommendation — IP-1: before FC, what REFLEX suggests
  reflex:outcome        — IP-3: after FC, what model chose vs recommended
  reflex:verifier       — IP-5: verifier verdict → score update
  reflex:filter         — IP-7: schema filtering applied
  reflex:fallback       — IP-7: filter fallback triggered

Architecture:
  ReflexEvent      — typed dataclass for each event
  ReflexEventBuffer — ring buffer (last N events, default 100)
  ReflexEventEmitter — builds & broadcasts events via WS + SocketIO

Part of VETKA OS:
  VETKA > REFLEX > Streaming (this file)

@status: active
@phase: 173.P3
@depends: agent_pipeline (emit infrastructure)
@used_by: agent_pipeline.py (IP-1,3,5,7), reflex_routes.py (event history)
"""

import logging
import time
import threading
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)


# ─── Event Types ──────────────────────────────────────────────────

class ReflexEventType(str, Enum):
    """MARKER_173.P3.TYPES — All REFLEX event types."""
    RECOMMENDATION = "reflex:recommendation"
    OUTCOME = "reflex:outcome"
    VERIFIER = "reflex:verifier"
    FILTER = "reflex:filter"
    FALLBACK = "reflex:fallback"


# ─── Event Dataclass ──────────────────────────────────────────────

@dataclass
class ReflexEvent:
    """MARKER_173.P3.EVENT — Typed REFLEX event payload.

    All events share a common envelope; data varies by event_type.
    """
    event_type: str               # ReflexEventType value
    pipeline_id: str = ""         # Pipeline/task identifier
    subtask_idx: int = 0          # Subtask index (1-based)
    subtask_marker: str = ""      # e.g. "step_3"
    phase_type: str = ""          # research, fix, build
    model_tier: str = ""          # bronze, silver, gold
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for WS/SSE emission."""
        return {
            "event": self.event_type,
            "pipeline_id": self.pipeline_id,
            "subtask_idx": self.subtask_idx,
            "subtask_marker": self.subtask_marker,
            "phase_type": self.phase_type,
            "model_tier": self.model_tier,
            "data": self.data,
            "timestamp": self.timestamp,
        }


# ─── Ring Buffer ──────────────────────────────────────────────────

class ReflexEventBuffer:
    """MARKER_173.P3.BUFFER — Thread-safe ring buffer for recent events.

    Stores last N events (default 100) for polling endpoints.
    Oldest events are evicted when buffer is full.
    """

    def __init__(self, max_size: int = 100):
        self._buffer: List[ReflexEvent] = []
        self._max_size = max_size
        self._lock = threading.Lock()
        self._sequence = 0  # Monotonic counter for ordering

    def push(self, event: ReflexEvent) -> int:
        """Add event, evict oldest if full. Returns sequence number."""
        with self._lock:
            self._sequence += 1
            if len(self._buffer) >= self._max_size:
                self._buffer.pop(0)
            self._buffer.append(event)
            return self._sequence

    def get_recent(self, n: int = 20) -> List[Dict[str, Any]]:
        """Return last N events as dicts."""
        with self._lock:
            events = self._buffer[-n:] if n < len(self._buffer) else list(self._buffer)
            return [e.to_dict() for e in events]

    def get_since(self, since_ts: float) -> List[Dict[str, Any]]:
        """Return events newer than timestamp."""
        with self._lock:
            return [e.to_dict() for e in self._buffer if e.timestamp > since_ts]

    def get_by_pipeline(self, pipeline_id: str) -> List[Dict[str, Any]]:
        """Return all events for a specific pipeline run."""
        with self._lock:
            return [e.to_dict() for e in self._buffer if e.pipeline_id == pipeline_id]

    def get_stats(self) -> Dict[str, Any]:
        """Return buffer statistics."""
        with self._lock:
            if not self._buffer:
                return {
                    "total_events": 0,
                    "buffer_size": 0,
                    "max_size": self._max_size,
                    "sequence": self._sequence,
                }
            type_counts: Dict[str, int] = {}
            for e in self._buffer:
                type_counts[e.event_type] = type_counts.get(e.event_type, 0) + 1
            return {
                "total_events": self._sequence,
                "buffer_size": len(self._buffer),
                "max_size": self._max_size,
                "sequence": self._sequence,
                "oldest_ts": self._buffer[0].timestamp,
                "newest_ts": self._buffer[-1].timestamp,
                "by_type": type_counts,
            }

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._buffer)

    def clear(self):
        with self._lock:
            self._buffer.clear()
            self._sequence = 0


# ─── Event Emitter ────────────────────────────────────────────────

class ReflexEventEmitter:
    """MARKER_173.P3.EMITTER — Builds & broadcasts typed REFLEX events.

    Two emission channels:
      1. WebSocket broadcaster (DevPanel) — structured JSON
      2. Ring buffer (REST polling) — stored for /api/reflex/events

    Usage in agent_pipeline:
        emitter = ReflexEventEmitter(ws_broadcaster=self._ws_broadcaster)
        emitter.emit_recommendation(pipeline_id, subtask_idx, ...)
    """

    def __init__(self, ws_broadcaster=None, buffer: Optional[ReflexEventBuffer] = None):
        self._ws = ws_broadcaster
        self._buffer = buffer or _get_global_buffer()

    async def _broadcast(self, event: ReflexEvent):
        """Broadcast event via WS and store in buffer."""
        # 1. Store in ring buffer (always)
        seq = self._buffer.push(event)

        # 2. Broadcast via WebSocket (if available)
        if self._ws:
            try:
                payload = event.to_dict()
                payload["_seq"] = seq
                await self._ws.broadcast({
                    "type": "reflex_event",
                    **payload,
                })
            except Exception as e:
                logger.debug("[REFLEX Stream] WS broadcast error (non-fatal): %s", e)

    async def emit_recommendation(
        self,
        pipeline_id: str,
        subtask_idx: int,
        subtask_marker: str,
        phase_type: str,
        model_tier: str,
        recommendations: List[Dict[str, Any]],
    ):
        """MARKER_173.P3.IP1 — Emit recommendation event (before FC)."""
        event = ReflexEvent(
            event_type=ReflexEventType.RECOMMENDATION,
            pipeline_id=pipeline_id,
            subtask_idx=subtask_idx,
            subtask_marker=subtask_marker,
            phase_type=phase_type,
            model_tier=model_tier,
            data={
                "recommended": [
                    {"tool_id": r.get("tool_id", ""), "score": r.get("score", 0), "reason": r.get("reason", "")}
                    for r in recommendations[:10]
                ],
                "count": len(recommendations),
            },
        )
        await self._broadcast(event)

    async def emit_outcome(
        self,
        pipeline_id: str,
        subtask_idx: int,
        subtask_marker: str,
        phase_type: str,
        model_tier: str,
        recommended_ids: List[str],
        used_ids: List[str],
        feedback_count: int,
    ):
        """MARKER_173.P3.IP3 — Emit outcome event (after FC)."""
        recommended_set = set(recommended_ids)
        used_set = set(used_ids)
        matched = recommended_set & used_set
        match_rate = len(matched) / len(recommended_set) if recommended_set else 0.0

        event = ReflexEvent(
            event_type=ReflexEventType.OUTCOME,
            pipeline_id=pipeline_id,
            subtask_idx=subtask_idx,
            subtask_marker=subtask_marker,
            phase_type=phase_type,
            model_tier=model_tier,
            data={
                "recommended": list(recommended_set),
                "used": list(used_set),
                "matched": list(matched),
                "match_rate": round(match_rate, 3),
                "feedback_count": feedback_count,
            },
        )
        await self._broadcast(event)

    async def emit_verifier(
        self,
        pipeline_id: str,
        subtask_idx: int,
        subtask_marker: str,
        phase_type: str,
        tools_used: List[str],
        verifier_passed: bool,
        feedback_count: int,
    ):
        """MARKER_173.P3.IP5 — Emit verifier event."""
        event = ReflexEvent(
            event_type=ReflexEventType.VERIFIER,
            pipeline_id=pipeline_id,
            subtask_idx=subtask_idx,
            subtask_marker=subtask_marker,
            phase_type=phase_type,
            data={
                "tools_used": tools_used[:20],
                "verifier_passed": verifier_passed,
                "feedback_count": feedback_count,
            },
        )
        await self._broadcast(event)

    async def emit_filter(
        self,
        pipeline_id: str,
        subtask_idx: int,
        subtask_marker: str,
        phase_type: str,
        model_tier: str,
        original_count: int,
        filtered_count: int,
    ):
        """MARKER_173.P3.IP7 — Emit filter event."""
        tokens_saved_estimate = (original_count - filtered_count) * 120  # ~120 tokens per schema avg

        event = ReflexEvent(
            event_type=ReflexEventType.FILTER,
            pipeline_id=pipeline_id,
            subtask_idx=subtask_idx,
            subtask_marker=subtask_marker,
            phase_type=phase_type,
            model_tier=model_tier,
            data={
                "original_count": original_count,
                "filtered_count": filtered_count,
                "removed": original_count - filtered_count,
                "tokens_saved_estimate": tokens_saved_estimate,
            },
        )
        await self._broadcast(event)

    async def emit_fallback(
        self,
        pipeline_id: str,
        subtask_idx: int,
        subtask_marker: str,
        phase_type: str,
        model_tier: str,
        reason: str,
    ):
        """MARKER_173.P3.FALLBACK — Emit filter fallback event."""
        event = ReflexEvent(
            event_type=ReflexEventType.FALLBACK,
            pipeline_id=pipeline_id,
            subtask_idx=subtask_idx,
            subtask_marker=subtask_marker,
            phase_type=phase_type,
            model_tier=model_tier,
            data={
                "reason": reason[:200],
            },
        )
        await self._broadcast(event)


# ─── Global Singleton ─────────────────────────────────────────────

_global_buffer: Optional[ReflexEventBuffer] = None
_global_lock = threading.Lock()


def _get_global_buffer() -> ReflexEventBuffer:
    """Lazy singleton for global event buffer."""
    global _global_buffer
    if _global_buffer is None:
        with _global_lock:
            if _global_buffer is None:
                _global_buffer = ReflexEventBuffer(max_size=100)
    return _global_buffer


def get_reflex_event_buffer() -> ReflexEventBuffer:
    """Public accessor for the global event buffer.

    Used by reflex_routes.py for event history endpoints.
    """
    return _get_global_buffer()


def reset_reflex_event_buffer():
    """Reset global buffer (for testing)."""
    global _global_buffer
    with _global_lock:
        _global_buffer = None
