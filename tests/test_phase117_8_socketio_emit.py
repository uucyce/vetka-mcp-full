"""
Phase 117.8: SocketIO Direct Emit — Unblock VETKA during @dragon

MARKER_117.8: Tests for async SocketIO emit fix.

Root cause: _emit_progress() used sync httpx.Client(timeout=5.0) that BLOCKED
the async event loop for 5s per emit × 20 emits = 100s total freeze.
Also: solo chat_id → group endpoint = "Group not found" → always timeout.

Fix: SocketIO direct emit (sio.emit) for solo + httpx.AsyncClient for groups.
"""

import inspect
import re
import pytest
from pathlib import Path


PIPELINE_FILE = Path(__file__).parent.parent / "src" / "orchestration" / "agent_pipeline.py"
HANDLER_FILE = Path(__file__).parent.parent / "src" / "api" / "handlers" / "user_message_handler.py"


class TestPipelineSioSidParams:
    """MARKER_117.8A: AgentPipeline accepts sio and sid parameters."""

    def test_pipeline_accepts_sio_param(self):
        from src.orchestration.agent_pipeline import AgentPipeline
        sig = inspect.signature(AgentPipeline.__init__)
        assert "sio" in sig.parameters, "AgentPipeline.__init__ should accept 'sio' param"

    def test_pipeline_accepts_sid_param(self):
        from src.orchestration.agent_pipeline import AgentPipeline
        sig = inspect.signature(AgentPipeline.__init__)
        assert "sid" in sig.parameters, "AgentPipeline.__init__ should accept 'sid' param"

    def test_pipeline_stores_sio_sid(self):
        """Pipeline should store sio and sid as instance attributes."""
        source = PIPELINE_FILE.read_text()
        assert "self.sio = sio" in source
        assert "self.sid = sid" in source

    def test_dispatch_solo_passes_sio_sid(self):
        """_dispatch_solo_system_command should pass sio+sid to AgentPipeline."""
        source = HANDLER_FILE.read_text()
        assert "sio=sio, sid=sid" in source, (
            "AgentPipeline creation should include sio=sio, sid=sid"
        )


class TestEmitProgressAsync:
    """MARKER_117.8B: _emit_progress is async and uses SocketIO."""

    def test_emit_progress_is_coroutine(self):
        """_emit_progress should be async (coroutine function)."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline()
        assert inspect.iscoroutinefunction(pipeline._emit_progress), (
            "_emit_progress should be a coroutine function (async def)"
        )

    def test_no_sync_httpx_client_in_emit(self):
        """No sync httpx.Client in _emit_progress (should use AsyncClient)."""
        source = PIPELINE_FILE.read_text()
        # Find the _emit_progress method body
        match = re.search(r'async def _emit_progress\(self.*?\n(.*?)(?=\n    (?:async )?def |\nclass |\Z)', source, re.DOTALL)
        assert match, "_emit_progress method not found"
        emit_body = match.group(1)
        assert "httpx.Client(" not in emit_body, (
            "_emit_progress should NOT use sync httpx.Client (blocks event loop!)"
        )

    def test_sio_emit_in_source(self):
        """SocketIO direct emit should be present in _emit_progress."""
        source = PIPELINE_FILE.read_text()
        assert 'sio.emit("agent_message"' in source or "sio.emit('agent_message'" in source, (
            "_emit_progress should use sio.emit('agent_message', ...) for solo chat"
        )

    def test_async_client_for_groups(self):
        """HTTP fallback should use httpx.AsyncClient (not sync Client)."""
        source = PIPELINE_FILE.read_text()
        assert "httpx.AsyncClient(" in source, (
            "Group chat fallback should use httpx.AsyncClient (async, non-blocking)"
        )


class TestNoDefaultUUID:
    """MARKER_117.8C: No default Lightning UUID for chat_id."""

    def test_no_default_lightning_uuid(self):
        """chat_id should not have a default UUID that sends to wrong chat."""
        source = PIPELINE_FILE.read_text()
        assert "5e2198c2" not in source, (
            "Default Lightning UUID (5e2198c2-...) should be removed from chat_id init"
        )

    def test_chat_id_can_be_none(self):
        """AgentPipeline(chat_id=None) should work — sio/sid used instead."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline(chat_id=None)
        assert pipeline.chat_id is None, "chat_id should be None when not provided"


class TestAllEmitCallsAwait:
    """MARKER_117.8: All _emit_progress calls must have await."""

    def test_all_emit_progress_have_await(self):
        """Every self._emit_progress( call should be preceded by await."""
        source = PIPELINE_FILE.read_text()
        # Find all lines with self._emit_progress(
        lines = source.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if 'self._emit_progress(' in stripped and not stripped.startswith('#') and not stripped.startswith('"') and not stripped.startswith("'"):
                # Check that 'await' is before self._emit_progress
                assert 'await self._emit_progress(' in stripped or 'await self._emit_progress(' in line, (
                    f"Line {i+1}: self._emit_progress( without await: {stripped[:80]}"
                )

    def test_emit_to_chat_is_async(self):
        """_emit_to_chat should also be async."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline()
        assert inspect.iscoroutinefunction(pipeline._emit_to_chat), (
            "_emit_to_chat should be a coroutine function"
        )

    def test_emit_to_chat_has_sio_route(self):
        """_emit_to_chat should also support SocketIO direct emit."""
        source = PIPELINE_FILE.read_text()
        # Find _emit_to_chat method
        match = re.search(r'async def _emit_to_chat\(self.*?\n(.*?)(?=\n    (?:async )?def |\nclass |\Z)', source, re.DOTALL)
        assert match, "_emit_to_chat method not found"
        body = match.group(1)
        assert "self.sio" in body and "self.sid" in body, (
            "_emit_to_chat should check self.sio and self.sid for SocketIO route"
        )


class TestMarkers:
    """Verify MARKER_117.8 presence."""

    def test_marker_117_8a_in_pipeline(self):
        source = PIPELINE_FILE.read_text()
        assert "MARKER_117.8A" in source

    def test_marker_117_8b_in_pipeline(self):
        source = PIPELINE_FILE.read_text()
        assert "MARKER_117.8B" in source

    def test_marker_117_8c_in_pipeline(self):
        source = PIPELINE_FILE.read_text()
        assert "MARKER_117.8C" in source

    def test_marker_117_8a_in_handler(self):
        source = HANDLER_FILE.read_text()
        assert "MARKER_117.8A" in source
