"""
MARKER_173.4 — CUT Timeline Real-Time Event Service.

Emits timeline state change events to connected clients via:
1. SocketIO (port 5001) — for activity feed / UI state
2. MYCELIUM WebSocket (port 8082) — for DevPanel real-time

Events are fire-and-forget: emission failures never block edits.

Event types:
- timeline_edited: clip move/trim/add/remove
- timeline_undo: undo operation performed
- timeline_redo: redo operation performed
- timeline_scene_detected: scene detection completed
- timeline_state_changed: generic state change

Usage:
    from src.services.cut_timeline_events import CutTimelineEventEmitter

    emitter = CutTimelineEventEmitter.get_instance()
    await emitter.emit_edit(project_id, timeline_id, ops, revision)
    await emitter.emit_undo(project_id, timeline_id, label, revision)
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger("cut.timeline_events")

_instance: CutTimelineEventEmitter | None = None


class CutTimelineEventEmitter:
    """
    Broadcasts CUT timeline state changes to all connected clients.

    Singleton pattern — use CutTimelineEventEmitter.get_instance().
    """

    def __init__(self) -> None:
        self._socketio: Any | None = None
        self._ws_broadcaster: Any | None = None

    @classmethod
    def get_instance(cls) -> CutTimelineEventEmitter:
        global _instance
        if _instance is None:
            _instance = cls()
        return _instance

    def set_socketio(self, sio: Any) -> None:
        """Set SocketIO instance for activity feed broadcasting."""
        self._socketio = sio

    def set_ws_broadcaster(self, broadcaster: Any) -> None:
        """Set MYCELIUM WebSocket broadcaster for DevPanel."""
        self._ws_broadcaster = broadcaster

    def _resolve_socketio(self) -> Any | None:
        """Lazily resolve SocketIO from group_message_handler."""
        if self._socketio is not None:
            return self._socketio
        try:
            from src.api.handlers.group_message_handler import get_socketio
            self._socketio = get_socketio()
        except Exception:
            pass
        return self._socketio

    def _resolve_ws(self) -> Any | None:
        """Lazily resolve MYCELIUM WebSocket broadcaster."""
        if self._ws_broadcaster is not None:
            return self._ws_broadcaster
        try:
            from src.mcp.mycelium_ws_server import get_ws_broadcaster
            self._ws_broadcaster = get_ws_broadcaster()
        except Exception:
            pass
        return self._ws_broadcaster

    async def _broadcast(self, event_type: str, payload: dict[str, Any]) -> None:
        """Fire-and-forget broadcast to both channels."""
        payload["event_type"] = event_type
        payload["event_id"] = f"cut_evt_{uuid4().hex[:12]}"
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()

        # SocketIO channel
        sio = self._resolve_socketio()
        if sio is not None:
            try:
                await sio.emit("cut_timeline_event", payload)
            except Exception as exc:
                logger.debug("SocketIO emit failed (non-fatal): %s", exc)

        # MYCELIUM WebSocket channel
        ws = self._resolve_ws()
        if ws is not None:
            try:
                ws_payload = {"type": "cut_timeline_event", **payload}
                if asyncio.iscoroutinefunction(getattr(ws, "broadcast", None)):
                    await ws.broadcast(ws_payload)
                elif hasattr(ws, "broadcast"):
                    ws.broadcast(ws_payload)
            except Exception as exc:
                logger.debug("MYCELIUM WS broadcast failed (non-fatal): %s", exc)

    # ── High-level event methods ─────────────────────────────

    async def emit_edit(
        self,
        project_id: str,
        timeline_id: str,
        ops: list[dict[str, Any]],
        revision: int,
        *,
        author: str = "user",
    ) -> None:
        """Emit timeline edit event (move, trim, add, remove, etc.)."""
        op_types = list({op.get("op", "unknown") for op in ops})
        await self._broadcast("timeline_edited", {
            "project_id": project_id,
            "timeline_id": timeline_id,
            "revision": revision,
            "op_count": len(ops),
            "op_types": op_types,
            "author": author,
        })

    async def emit_undo(
        self,
        project_id: str,
        timeline_id: str,
        label: str,
        revision: int,
        undo_depth: int,
        redo_depth: int,
    ) -> None:
        """Emit undo event."""
        await self._broadcast("timeline_undo", {
            "project_id": project_id,
            "timeline_id": timeline_id,
            "undone_label": label,
            "revision": revision,
            "undo_depth": undo_depth,
            "redo_depth": redo_depth,
        })

    async def emit_redo(
        self,
        project_id: str,
        timeline_id: str,
        label: str,
        revision: int,
        undo_depth: int,
        redo_depth: int,
    ) -> None:
        """Emit redo event."""
        await self._broadcast("timeline_redo", {
            "project_id": project_id,
            "timeline_id": timeline_id,
            "redone_label": label,
            "revision": revision,
            "undo_depth": undo_depth,
            "redo_depth": redo_depth,
        })

    async def emit_scene_detected(
        self,
        project_id: str,
        timeline_id: str,
        boundary_count: int,
        clip_count: int,
        lane_id: str,
    ) -> None:
        """Emit scene detection completion event."""
        await self._broadcast("timeline_scene_detected", {
            "project_id": project_id,
            "timeline_id": timeline_id,
            "boundary_count": boundary_count,
            "clip_count": clip_count,
            "lane_id": lane_id,
        })

    async def emit_state_changed(
        self,
        project_id: str,
        timeline_id: str,
        action: str,
        revision: int,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Emit generic state change event."""
        await self._broadcast("timeline_state_changed", {
            "project_id": project_id,
            "timeline_id": timeline_id,
            "action": action,
            "revision": revision,
            "details": details or {},
        })
