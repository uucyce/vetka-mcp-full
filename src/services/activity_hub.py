"""
Activity Hub Service - Phase 123.0

Central hub for all activity events in VETKA.
Tracks heat scores, emits glow events, manages decay.

MARKER_123.0A: ActivityHub singleton
MARKER_123.0B: Heat score decay loop

Extends activity_emitter.py with stateful tracking.

@file activity_hub.py
@status ACTIVE
@phase Phase 123.0
@created 2026-02-08

Usage:
    from src.services.activity_hub import get_activity_hub

    hub = get_activity_hub()
    await hub.emit_glow(
        node_id="/path/to/file.py",
        intensity=0.8,
        reason="watchdog:modified"
    )
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any, Set
from dataclasses import dataclass, field
from socketio import AsyncServer

from src.services.activity_emitter import emit_activity_update

logger = logging.getLogger(__name__)


# =============================================================================
# MARKER_123.0A: ActivityHub Singleton
# =============================================================================

@dataclass
class GlowState:
    """State for a glowing node."""
    intensity: float           # 0.0 - 1.0
    reason: str                # Why it's glowing
    color: str = "#7ab3d4"     # Default: Scanner Panel blue
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    decay_rate: float = 0.98   # Per second (0.98^60 ≈ 0.30 after 1 min)


class ActivityHub:
    """
    Central hub for activity tracking and glow events.

    MARKER_123.0A: Singleton pattern for global access.

    Features:
    - Tracks heat_scores per node (file/folder path)
    - Emits glow events via Socket.IO
    - Background decay task reduces scores over time
    - Integrates with existing activity_emitter.py
    """

    _instance: Optional['ActivityHub'] = None
    _initialized: bool = False

    def __new__(cls) -> 'ActivityHub':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Prevent re-initialization
        if ActivityHub._initialized:
            return
        ActivityHub._initialized = True

        # State
        self.heat_scores: Dict[str, GlowState] = {}
        self.sio: Optional[AsyncServer] = None
        self._decay_task: Optional[asyncio.Task] = None
        self._running: bool = False

        # Config
        self.decay_interval_seconds: float = 30.0
        self.min_intensity_threshold: float = 0.01
        self.max_glowing_nodes: int = 100  # Prevent memory bloat

        logger.info("[ActivityHub] Initialized (singleton)")

    def set_socketio(self, sio: AsyncServer) -> None:
        """Set Socket.IO instance for event emission."""
        self.sio = sio
        logger.info("[ActivityHub] Socket.IO connected")

    # =========================================================================
    # Core API
    # =========================================================================

    async def emit_glow(
        self,
        node_id: str,
        intensity: float,
        reason: str,
        color: str = "#7ab3d4",
        propagate_to_parent: bool = True
    ) -> bool:
        """
        Emit activity glow for a node.

        Args:
            node_id: File or folder path
            intensity: Glow intensity (0.0 - 1.0)
            reason: Why glowing (e.g., "watchdog:modified", "pipeline:coder")
            color: Hex color (default: Scanner Panel blue)
            propagate_to_parent: Also glow parent folders (with reduced intensity)

        Returns:
            True if emitted successfully
        """
        try:
            # Clamp intensity
            intensity = max(0.0, min(1.0, intensity))

            # Update or create glow state
            if node_id in self.heat_scores:
                state = self.heat_scores[node_id]
                state.intensity = max(state.intensity, intensity)
                state.reason = reason
                state.updated_at = datetime.now(timezone.utc)
            else:
                self.heat_scores[node_id] = GlowState(
                    intensity=intensity,
                    reason=reason,
                    color=color
                )

            # Enforce max limit (LRU eviction)
            self._enforce_max_limit()

            # Emit Socket.IO event
            if self.sio:
                await self.sio.emit('activity_glow', {
                    'node_id': node_id,
                    'intensity': intensity,
                    'reason': reason,
                    'color': color,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })

            # Also emit to activity feed
            await emit_activity_update(
                socketio=self.sio,
                activity_type="glow",
                title=f"Activity: {self._short_path(node_id)}",
                description=reason,
                metadata={
                    "node_id": node_id,
                    "intensity": intensity,
                    "color": color
                }
            )

            # Propagate to parent folders
            if propagate_to_parent:
                await self._propagate_to_parents(node_id, intensity, reason, color)

            logger.debug(f"[ActivityHub] Glow: {node_id} ({intensity:.2f}) - {reason}")
            return True

        except Exception as e:
            logger.error(f"[ActivityHub] Error emitting glow: {e}")
            return False

    async def _propagate_to_parents(
        self,
        node_id: str,
        intensity: float,
        reason: str,
        color: str,
        max_depth: int = 3
    ) -> None:
        """Propagate glow up to parent folders with decay."""
        import os
        current = node_id
        depth = 0

        while depth < max_depth:
            parent = os.path.dirname(current)
            if not parent or parent == current:
                break

            # Reduce intensity for each level
            parent_intensity = intensity * (0.5 ** (depth + 1))
            if parent_intensity < self.min_intensity_threshold:
                break

            # Update parent (don't propagate further)
            if parent not in self.heat_scores:
                self.heat_scores[parent] = GlowState(
                    intensity=parent_intensity,
                    reason=f"child:{reason}",
                    color=color
                )
            else:
                state = self.heat_scores[parent]
                state.intensity = max(state.intensity, parent_intensity)

            current = parent
            depth += 1

    def emit_glow_sync(
        self,
        node_id: str,
        intensity: float,
        reason: str,
        color: str = "#7ab3d4"
    ) -> None:
        """
        MARKER_123.1A: Sync-safe glow emission for use from sync contexts (e.g., FileWatcher).

        Updates heat score immediately, schedules async emit via event loop.
        """
        import asyncio

        # Clamp intensity
        intensity = max(0.0, min(1.0, intensity))

        # Update state immediately (thread-safe via GIL)
        if node_id in self.heat_scores:
            state = self.heat_scores[node_id]
            state.intensity = max(state.intensity, intensity)
            state.reason = reason
            state.updated_at = datetime.now(timezone.utc)
        else:
            self.heat_scores[node_id] = GlowState(
                intensity=intensity,
                reason=reason,
                color=color
            )

        # Enforce max limit
        self._enforce_max_limit()

        # Schedule async emit if event loop is running
        if self.sio:
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._async_emit_glow(node_id, intensity, reason, color))
            except RuntimeError:
                # No running loop - try to run in new loop (for background threads)
                try:
                    asyncio.run(self._async_emit_glow(node_id, intensity, reason, color))
                except Exception as e:
                    logger.debug(f"[ActivityHub] Sync emit failed (no loop): {e}")

        logger.debug(f"[ActivityHub] Glow (sync): {node_id} ({intensity:.2f}) - {reason}")

    async def _async_emit_glow(
        self,
        node_id: str,
        intensity: float,
        reason: str,
        color: str
    ) -> None:
        """Helper for async emit from sync context."""
        if self.sio:
            await self.sio.emit('activity_glow', {
                'node_id': node_id,
                'intensity': intensity,
                'reason': reason,
                'color': color,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

    def get_heat_score(self, node_id: str) -> float:
        """Get current heat score for a node (with lazy decay)."""
        state = self.heat_scores.get(node_id)
        if not state:
            return 0.0
        return self._calculate_decayed_intensity(state)

    def get_all_heat_scores(self) -> Dict[str, float]:
        """Get all current heat scores (with lazy decay)."""
        self.cleanup_expired()  # Clean up on batch access
        return {
            node_id: self._calculate_decayed_intensity(state)
            for node_id, state in self.heat_scores.items()
        }

    def get_glowing_nodes(self) -> Dict[str, Dict[str, Any]]:
        """Get all glowing nodes with full state (with lazy decay)."""
        self.cleanup_expired()  # Clean up expired nodes
        result = {}
        for node_id, state in self.heat_scores.items():
            intensity = self._calculate_decayed_intensity(state)
            if intensity >= self.min_intensity_threshold:
                result[node_id] = {
                    'intensity': intensity,
                    'reason': state.reason,
                    'color': state.color,
                    'updated_at': state.updated_at.isoformat()
                }
        return result

    # =========================================================================
    # MARKER_123.0B: Lazy Decay (on-access, no background loop!)
    # =========================================================================

    def _calculate_decayed_intensity(self, state: GlowState) -> float:
        """
        Calculate current intensity with time-based decay.

        No background loop needed — decay is calculated on access.
        Formula: intensity * (decay_rate ^ seconds_elapsed)
        """
        now = datetime.now(timezone.utc)
        elapsed_seconds = (now - state.updated_at).total_seconds()

        # Decay every second (decay_rate per second)
        # 0.95^30 ≈ 0.21 after 30 seconds
        decayed = state.intensity * (state.decay_rate ** elapsed_seconds)

        return decayed if decayed >= self.min_intensity_threshold else 0.0

    def cleanup_expired(self) -> int:
        """
        Remove expired nodes. Call this periodically or on get_glowing_nodes().

        Returns number of removed nodes.
        """
        expired = [
            node_id for node_id, state in self.heat_scores.items()
            if self._calculate_decayed_intensity(state) < self.min_intensity_threshold
        ]

        for node_id in expired:
            del self.heat_scores[node_id]

        return len(expired)

    # Legacy methods for backwards compatibility (no-op now)
    def start_decay_loop(self) -> None:
        """No-op. Decay is now lazy (calculated on access)."""
        logger.info("[ActivityHub] Using lazy decay (no background loop)")

    def stop_decay_loop(self) -> None:
        """No-op. No background loop to stop."""
        pass

    # =========================================================================
    # Helpers
    # =========================================================================

    def _enforce_max_limit(self) -> None:
        """Remove oldest entries if over max limit (LRU)."""
        if len(self.heat_scores) <= self.max_glowing_nodes:
            return

        # Sort by updated_at, remove oldest
        sorted_nodes = sorted(
            self.heat_scores.items(),
            key=lambda x: x[1].updated_at
        )

        to_remove = len(self.heat_scores) - self.max_glowing_nodes
        for node_id, _ in sorted_nodes[:to_remove]:
            del self.heat_scores[node_id]

        logger.debug(f"[ActivityHub] LRU eviction: removed {to_remove} nodes")

    def _short_path(self, path: str, max_parts: int = 2) -> str:
        """Shorten path for display."""
        parts = path.split('/')
        if len(parts) <= max_parts:
            return path
        return '/'.join(['...'] + parts[-max_parts:])

    def get_stats(self) -> Dict[str, Any]:
        """Get hub statistics."""
        return {
            'total_nodes': len(self.heat_scores),
            'max_nodes': self.max_glowing_nodes,
            'decay_interval': self.decay_interval_seconds,
            'running': self._running,
            'top_5': sorted(
                [(k, v.intensity) for k, v in self.heat_scores.items()],
                key=lambda x: -x[1]
            )[:5]
        }


# =============================================================================
# Module-level Singleton Access
# =============================================================================

_hub: Optional[ActivityHub] = None


def get_activity_hub() -> ActivityHub:
    """Get or create the global ActivityHub instance."""
    global _hub
    if _hub is None:
        _hub = ActivityHub()
    return _hub


def reset_activity_hub() -> None:
    """Reset global ActivityHub (for testing)."""
    global _hub
    if _hub:
        _hub.stop_decay_loop()
    _hub = None
    ActivityHub._instance = None
    ActivityHub._initialized = False
