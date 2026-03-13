"""
MARKER_173.4 — CUT Timeline Real-Time Event Service tests.

Tests:
- CutTimelineEventEmitter singleton
- Event emission methods (edit, undo, redo, scene_detected, state_changed)
- Fire-and-forget behavior (failures don't raise)
- Payload structure
- SocketIO + WS broadcaster integration
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.cut_timeline_events import CutTimelineEventEmitter


@pytest.fixture
def emitter():
    """Create a fresh emitter (bypass singleton for isolation)."""
    e = CutTimelineEventEmitter()
    return e


@pytest.fixture
def mock_sio():
    """Mock SocketIO AsyncServer."""
    sio = AsyncMock()
    return sio


@pytest.fixture
def mock_ws():
    """Mock MYCELIUM WebSocket broadcaster."""
    ws = AsyncMock()
    return ws


class TestSingleton:
    def test_get_instance_returns_same(self):
        # Reset singleton
        import src.services.cut_timeline_events as mod
        mod._instance = None
        a = CutTimelineEventEmitter.get_instance()
        b = CutTimelineEventEmitter.get_instance()
        assert a is b
        mod._instance = None  # cleanup


class TestEmitEdit:
    @pytest.mark.asyncio
    async def test_emit_edit_socketio(self, emitter, mock_sio):
        emitter.set_socketio(mock_sio)
        await emitter.emit_edit("proj_1", "tl_1", [{"op": "move_clip"}], 5)
        mock_sio.emit.assert_called_once()
        call_args = mock_sio.emit.call_args
        assert call_args[0][0] == "cut_timeline_event"
        payload = call_args[0][1]
        assert payload["event_type"] == "timeline_edited"
        assert payload["project_id"] == "proj_1"
        assert payload["timeline_id"] == "tl_1"
        assert payload["revision"] == 5
        assert payload["op_count"] == 1
        assert "move_clip" in payload["op_types"]
        assert "event_id" in payload
        assert "timestamp" in payload

    @pytest.mark.asyncio
    async def test_emit_edit_ws(self, emitter, mock_ws):
        emitter.set_ws_broadcaster(mock_ws)
        await emitter.emit_edit("proj_1", "tl_1", [{"op": "trim_clip"}, {"op": "move_clip"}], 3)
        mock_ws.broadcast.assert_called_once()
        payload = mock_ws.broadcast.call_args[0][0]
        assert payload["type"] == "cut_timeline_event"
        assert payload["op_count"] == 2
        assert set(payload["op_types"]) == {"trim_clip", "move_clip"}

    @pytest.mark.asyncio
    async def test_emit_edit_both_channels(self, emitter, mock_sio, mock_ws):
        emitter.set_socketio(mock_sio)
        emitter.set_ws_broadcaster(mock_ws)
        await emitter.emit_edit("proj_1", "tl_1", [{"op": "add_clip"}], 1)
        mock_sio.emit.assert_called_once()
        mock_ws.broadcast.assert_called_once()


class TestEmitUndo:
    @pytest.mark.asyncio
    async def test_emit_undo(self, emitter, mock_sio):
        emitter.set_socketio(mock_sio)
        await emitter.emit_undo("proj_1", "tl_1", "Move clip abc", 4, 3, 1)
        payload = mock_sio.emit.call_args[0][1]
        assert payload["event_type"] == "timeline_undo"
        assert payload["undone_label"] == "Move clip abc"
        assert payload["undo_depth"] == 3
        assert payload["redo_depth"] == 1


class TestEmitRedo:
    @pytest.mark.asyncio
    async def test_emit_redo(self, emitter, mock_sio):
        emitter.set_socketio(mock_sio)
        await emitter.emit_redo("proj_1", "tl_1", "Trim clip xyz", 6, 5, 0)
        payload = mock_sio.emit.call_args[0][1]
        assert payload["event_type"] == "timeline_redo"
        assert payload["redone_label"] == "Trim clip xyz"
        assert payload["undo_depth"] == 5
        assert payload["redo_depth"] == 0


class TestEmitSceneDetected:
    @pytest.mark.asyncio
    async def test_emit_scene_detected(self, emitter, mock_sio):
        emitter.set_socketio(mock_sio)
        await emitter.emit_scene_detected("proj_1", "tl_1", 5, 6, "scenes")
        payload = mock_sio.emit.call_args[0][1]
        assert payload["event_type"] == "timeline_scene_detected"
        assert payload["boundary_count"] == 5
        assert payload["clip_count"] == 6
        assert payload["lane_id"] == "scenes"


class TestEmitStateChanged:
    @pytest.mark.asyncio
    async def test_emit_state_changed(self, emitter, mock_sio):
        emitter.set_socketio(mock_sio)
        await emitter.emit_state_changed("proj_1", "tl_1", "imported", 1, details={"source": "xml"})
        payload = mock_sio.emit.call_args[0][1]
        assert payload["event_type"] == "timeline_state_changed"
        assert payload["action"] == "imported"
        assert payload["details"]["source"] == "xml"


class TestFireAndForget:
    @pytest.mark.asyncio
    async def test_socketio_failure_non_fatal(self, emitter):
        sio = AsyncMock()
        sio.emit.side_effect = Exception("connection lost")
        emitter.set_socketio(sio)
        # Should NOT raise
        await emitter.emit_edit("proj_1", "tl_1", [{"op": "move_clip"}], 1)

    @pytest.mark.asyncio
    async def test_ws_failure_non_fatal(self, emitter):
        ws = AsyncMock()
        ws.broadcast.side_effect = Exception("ws down")
        emitter.set_ws_broadcaster(ws)
        # Should NOT raise
        await emitter.emit_undo("proj_1", "tl_1", "test", 1, 0, 1)

    @pytest.mark.asyncio
    async def test_no_channels_no_error(self, emitter):
        # No socketio, no ws — should not raise
        await emitter.emit_edit("proj_1", "tl_1", [{"op": "x"}], 1)
        await emitter.emit_undo("proj_1", "tl_1", "y", 1, 0, 0)
        await emitter.emit_redo("proj_1", "tl_1", "z", 1, 0, 0)
        await emitter.emit_scene_detected("proj_1", "tl_1", 0, 0, "scenes")
        await emitter.emit_state_changed("proj_1", "tl_1", "test", 1)


class TestLazyResolve:
    @pytest.mark.asyncio
    async def test_lazy_resolve_socketio(self, emitter):
        """Verifies lazy resolve doesn't crash when module not available."""
        with patch("src.services.cut_timeline_events.CutTimelineEventEmitter._resolve_socketio", return_value=None):
            await emitter.emit_edit("proj_1", "tl_1", [{"op": "x"}], 1)

    @pytest.mark.asyncio
    async def test_lazy_resolve_ws(self, emitter):
        with patch("src.services.cut_timeline_events.CutTimelineEventEmitter._resolve_ws", return_value=None):
            await emitter.emit_edit("proj_1", "tl_1", [{"op": "x"}], 1)
