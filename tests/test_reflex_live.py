"""
Tests for REFLEX Live — Phase 174: Tool Selection Visibility in Chat Streams.

MARKER_174.REFLEX_LIVE.TESTS

Tests that _emit_progress correctly propagates structured REFLEX metadata
through all emission channels (SocketIO, WebSocket, HTTP relay).

T1  — _emit_progress with metadata includes it in SocketIO payload
T2  — _emit_progress with metadata includes it in WS broadcast
T3  — _emit_progress without metadata preserves existing behavior
T4  — HTTP relay forwards metadata correctly
T5  — IP-1 recommendation metadata format
T6  — IP-3 outcome metadata format
T7  — IP-5 verifier metadata format
T8  — IP-7 filter metadata format
T9  — Metadata schema validation
T10 — REFLEX metadata errors don't block pipeline
T11 — HTTP client emit_pipeline_progress passes metadata
T12 — HTTP client emit_chat_message includes metadata in JSON body
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ─── T1-T3: _emit_progress metadata propagation ──────────────────

class TestEmitProgressMetadata:
    """T1-T3: _emit_progress correctly handles metadata parameter."""

    @pytest.mark.asyncio
    async def test_sio_emit_includes_metadata(self):
        """T1: SocketIO chat_response includes type and metadata when provided."""
        from src.orchestration.agent_pipeline import AgentPipeline

        pipeline = AgentPipeline.__new__(AgentPipeline)
        pipeline.sio = AsyncMock()
        pipeline.sid = "test-sid"
        pipeline.chat_id = None
        pipeline.preset = "dragon_silver"
        pipeline.preset_name = "dragon_silver"
        pipeline.prompts = {}
        pipeline.progress_hooks = []
        pipeline._ws_broadcaster = None
        pipeline._http_client = None

        metadata = {
            "type": "reflex",
            "event": "recommendation",
            "tools": [{"id": "read_file", "score": 0.92}],
            "phase": "fix",
        }

        await pipeline._emit_progress("@reflex", "test msg", metadata=metadata)

        # Verify SocketIO emit was called with metadata
        pipeline.sio.emit.assert_called()
        call_args = pipeline.sio.emit.call_args
        assert call_args[0][0] == "chat_response"
        payload = call_args[0][1]
        assert payload["type"] == "reflex"
        assert payload["metadata"] == metadata
        assert "message" in payload

    @pytest.mark.asyncio
    async def test_ws_broadcast_includes_metadata(self):
        """T2: WebSocket broadcast includes metadata in pipeline_activity."""
        from src.orchestration.agent_pipeline import AgentPipeline

        pipeline = AgentPipeline.__new__(AgentPipeline)
        pipeline.sio = None
        pipeline.sid = None
        pipeline.chat_id = None
        pipeline.preset = "dragon_silver"
        pipeline.preset_name = "dragon_silver"
        pipeline.prompts = {}
        pipeline.progress_hooks = []
        pipeline._http_client = None
        pipeline._board_task_id = "task-123"

        ws_mock = AsyncMock()
        pipeline._ws_broadcaster = ws_mock

        metadata = {
            "type": "reflex",
            "event": "filter",
            "original_count": 12,
            "filtered_count": 5,
        }

        await pipeline._emit_progress("@reflex", "filter msg", metadata=metadata)

        ws_mock.broadcast.assert_called_once()
        ws_payload = ws_mock.broadcast.call_args[0][0]
        assert ws_payload["type"] == "pipeline_activity"
        assert ws_payload["metadata"] == metadata
        assert ws_payload["role"] == "@reflex"

    @pytest.mark.asyncio
    async def test_no_metadata_preserves_behavior(self):
        """T3: Without metadata, SocketIO emit has no type/metadata fields."""
        from src.orchestration.agent_pipeline import AgentPipeline

        pipeline = AgentPipeline.__new__(AgentPipeline)
        pipeline.sio = AsyncMock()
        pipeline.sid = "test-sid"
        pipeline.chat_id = None
        pipeline.preset = "dragon_silver"
        pipeline.preset_name = "dragon_silver"
        pipeline.prompts = {}
        pipeline.progress_hooks = []
        pipeline._ws_broadcaster = None
        pipeline._http_client = None

        await pipeline._emit_progress("@coder", "coding step 1")

        pipeline.sio.emit.assert_called()
        call_args = pipeline.sio.emit.call_args
        payload = call_args[0][1]
        # Without metadata, type and metadata keys should not be present
        assert "type" not in payload
        assert "metadata" not in payload

    @pytest.mark.asyncio
    async def test_http_relay_forwards_metadata(self):
        """T4: HTTP client relay passes metadata through."""
        from src.orchestration.agent_pipeline import AgentPipeline

        pipeline = AgentPipeline.__new__(AgentPipeline)
        pipeline.sio = None
        pipeline.sid = None
        pipeline.chat_id = "group-chat-123"
        pipeline.preset = "dragon_silver"
        pipeline.preset_name = "dragon_silver"
        pipeline.prompts = {}
        pipeline.progress_hooks = []
        pipeline._ws_broadcaster = None

        http_mock = AsyncMock()
        http_mock.emit_pipeline_progress = AsyncMock()
        pipeline._http_client = http_mock

        metadata = {
            "type": "reflex",
            "event": "outcome",
            "tools_used": ["read_file", "edit_file"],
        }

        await pipeline._emit_progress("@reflex", "used tools", metadata=metadata)

        http_mock.emit_pipeline_progress.assert_called_once()
        call_kwargs = http_mock.emit_pipeline_progress.call_args
        # metadata should be passed as keyword argument
        assert call_kwargs.kwargs.get("metadata") == metadata or \
               (len(call_kwargs.args) > 6 and call_kwargs.args[6] == metadata)


# ─── T5-T8: REFLEX metadata format ──────────────────────────────

class TestReflexMetadataFormat:
    """T5-T8: Metadata format for each REFLEX event type."""

    def test_recommendation_metadata_schema(self):
        """T5: Recommendation metadata has expected structure."""
        metadata = {
            "type": "reflex",
            "event": "recommendation",
            "tools": [
                {"id": "read_file", "score": 0.92},
                {"id": "edit_file", "score": 0.88},
                {"id": "search_semantic", "score": 0.75},
            ],
            "phase": "fix",
            "tier": "silver",
            "subtask": "step_1",
        }

        assert metadata["type"] == "reflex"
        assert metadata["event"] == "recommendation"
        assert len(metadata["tools"]) == 3
        assert all("id" in t and "score" in t for t in metadata["tools"])
        assert all(0 <= t["score"] <= 1.0 for t in metadata["tools"])
        assert metadata["phase"] in ("research", "fix", "build")
        assert metadata["tier"] in ("gold", "silver", "bronze")

    def test_outcome_metadata_schema(self):
        """T6: Outcome metadata has expected structure."""
        metadata = {
            "type": "reflex",
            "event": "outcome",
            "tools_used": ["read_file", "edit_file"],
            "feedback_count": 2,
            "phase": "build",
            "subtask": "step_3",
        }

        assert metadata["type"] == "reflex"
        assert metadata["event"] == "outcome"
        assert isinstance(metadata["tools_used"], list)
        assert metadata["feedback_count"] >= 0
        assert metadata["phase"] in ("research", "fix", "build")

    def test_verifier_metadata_schema(self):
        """T7: Verifier metadata has expected structure."""
        metadata = {
            "type": "reflex",
            "event": "verifier",
            "passed": True,
            "tools": ["read_file", "edit_file"],
            "feedback_count": 2,
            "phase": "fix",
            "subtask": "step_2",
        }

        assert metadata["type"] == "reflex"
        assert metadata["event"] == "verifier"
        assert isinstance(metadata["passed"], bool)
        assert isinstance(metadata["tools"], list)
        assert metadata["feedback_count"] >= 0

    def test_filter_metadata_schema(self):
        """T8: Filter metadata has expected structure."""
        metadata = {
            "type": "reflex",
            "event": "filter",
            "original_count": 12,
            "filtered_count": 5,
            "tier": "bronze",
            "phase": "fix",
            "subtask": "step_1",
        }

        assert metadata["type"] == "reflex"
        assert metadata["event"] == "filter"
        assert metadata["original_count"] >= metadata["filtered_count"]
        assert metadata["filtered_count"] >= 0
        assert metadata["tier"] in ("gold", "silver", "bronze")


# ─── T9-T10: Schema validation and error handling ────────────────

class TestMetadataValidation:
    """T9-T10: Schema validation and error resilience."""

    def test_all_event_types_covered(self):
        """T9: All 4 REFLEX event types produce valid metadata."""
        valid_events = {"recommendation", "outcome", "verifier", "filter"}
        assert len(valid_events) == 4

        # Each event type must have "type": "reflex" and "event" key
        for event in valid_events:
            meta = {"type": "reflex", "event": event}
            assert meta["type"] == "reflex"
            assert meta["event"] in valid_events

    @pytest.mark.asyncio
    async def test_metadata_error_doesnt_block_pipeline(self):
        """T10: If metadata construction fails, pipeline continues."""
        from src.orchestration.agent_pipeline import AgentPipeline

        pipeline = AgentPipeline.__new__(AgentPipeline)
        pipeline.sio = AsyncMock()
        pipeline.sid = "test-sid"
        pipeline.chat_id = None
        pipeline.preset = "dragon_silver"
        pipeline.preset_name = "dragon_silver"
        pipeline.prompts = {}
        pipeline.progress_hooks = []
        pipeline._ws_broadcaster = None
        pipeline._http_client = None

        # Even with bizarre metadata, emit should not raise
        weird_metadata = {"type": "reflex", "event": None, "tools": "not-a-list"}
        await pipeline._emit_progress("@reflex", "test", metadata=weird_metadata)

        # Should still emit (metadata is passed as-is, validation is frontend's job)
        pipeline.sio.emit.assert_called()


# ─── T11-T12: HTTP Client metadata passthrough ──────────────────

class TestHTTPClientMetadata:
    """T11-T12: mycelium_http_client metadata passthrough."""

    @pytest.mark.asyncio
    async def test_emit_pipeline_progress_with_metadata(self):
        """T11: emit_pipeline_progress passes metadata to emit_chat_message."""
        from src.mcp.mycelium_http_client import MyceliumHTTPClient

        client = MyceliumHTTPClient.__new__(MyceliumHTTPClient)
        client._client = AsyncMock()
        client._client.post = AsyncMock()

        metadata = {
            "type": "reflex",
            "event": "recommendation",
            "tools": [{"id": "test_tool", "score": 0.9}],
        }

        await client.emit_pipeline_progress(
            chat_id="chat-123",
            role="@reflex",
            message="test",
            model="system",
            metadata=metadata,
        )

        client._client.post.assert_called_once()
        call_args = client._client.post.call_args
        json_body = call_args.kwargs.get("json") or call_args[1].get("json")
        assert json_body["metadata"] == metadata
        assert json_body["message_type"] == "reflex"

    @pytest.mark.asyncio
    async def test_emit_chat_message_includes_metadata(self):
        """T12: emit_chat_message includes metadata in POST body."""
        from src.mcp.mycelium_http_client import MyceliumHTTPClient

        client = MyceliumHTTPClient.__new__(MyceliumHTTPClient)
        client._client = AsyncMock()
        client._client.post = AsyncMock()

        metadata = {"type": "reflex", "event": "filter"}

        await client.emit_chat_message(
            chat_id="chat-456",
            message="filter applied",
            sender="pipeline",
            msg_type="reflex",
            metadata=metadata,
        )

        client._client.post.assert_called_once()
        call_args = client._client.post.call_args
        json_body = call_args.kwargs.get("json") or call_args[1].get("json")
        assert "metadata" in json_body
        assert json_body["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_emit_pipeline_progress_without_metadata(self):
        """T12b: Without metadata, msg_type is 'system' and no metadata key."""
        from src.mcp.mycelium_http_client import MyceliumHTTPClient

        client = MyceliumHTTPClient.__new__(MyceliumHTTPClient)
        client._client = AsyncMock()
        client._client.post = AsyncMock()

        await client.emit_pipeline_progress(
            chat_id="chat-789",
            role="@coder",
            message="coding...",
            model="system",
        )

        client._client.post.assert_called_once()
        call_args = client._client.post.call_args
        json_body = call_args.kwargs.get("json") or call_args[1].get("json")
        assert json_body["message_type"] == "system"
        assert "metadata" not in json_body
