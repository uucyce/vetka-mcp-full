"""
Tests for REFLEX Streaming — Phase 173.P3

MARKER_173.P3.TESTS

Tests event schema, ring buffer, emitter, and REST endpoints.

T3.1  — ReflexEvent to_dict schema
T3.2  — ReflexEventType enum values
T3.3  — Buffer push and get_recent
T3.4  — Buffer eviction at max_size
T3.5  — Buffer get_since timestamp filter
T3.6  — Buffer get_by_pipeline filter
T3.7  — Buffer get_stats counters
T3.8  — Buffer clear resets
T3.9  — Buffer thread safety
T3.10 — Emitter emit_recommendation
T3.11 — Emitter emit_outcome match rate
T3.12 — Emitter emit_verifier
T3.13 — Emitter emit_filter tokens estimate
T3.14 — Emitter emit_fallback
T3.15 — Emitter broadcasts via WS
T3.16 — Singleton get/reset buffer
T3.17 — REST: GET /api/reflex/events
T3.18 — REST: GET /api/reflex/events/stats
T3.19 — REST: events disabled when REFLEX off
T3.20 — Pipeline _get_reflex_emitter lazy init
"""

import asyncio
import sys
import time
import pytest
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ─── T3.1-T3.2: Event Schema ─────────────────────────────────────

class TestEventSchema:
    """T3.1-T3.2: ReflexEvent and ReflexEventType."""

    def test_event_to_dict(self):
        from src.services.reflex_streaming import ReflexEvent, ReflexEventType
        event = ReflexEvent(
            event_type=ReflexEventType.RECOMMENDATION,
            pipeline_id="task_abc",
            subtask_idx=2,
            subtask_marker="step_2",
            phase_type="fix",
            model_tier="silver",
            data={"recommended": [{"tool_id": "vetka_read_file", "score": 0.9}]},
        )
        d = event.to_dict()
        assert d["event"] == "reflex:recommendation"
        assert d["pipeline_id"] == "task_abc"
        assert d["subtask_idx"] == 2
        assert d["subtask_marker"] == "step_2"
        assert d["phase_type"] == "fix"
        assert d["model_tier"] == "silver"
        assert "timestamp" in d
        assert d["data"]["recommended"][0]["tool_id"] == "vetka_read_file"

    def test_event_types(self):
        from src.services.reflex_streaming import ReflexEventType
        assert ReflexEventType.RECOMMENDATION == "reflex:recommendation"
        assert ReflexEventType.OUTCOME == "reflex:outcome"
        assert ReflexEventType.VERIFIER == "reflex:verifier"
        assert ReflexEventType.FILTER == "reflex:filter"
        assert ReflexEventType.FALLBACK == "reflex:fallback"
        # 5 event types
        assert len(ReflexEventType) == 5

    def test_event_default_timestamp(self):
        from src.services.reflex_streaming import ReflexEvent
        t0 = time.time()
        event = ReflexEvent(event_type="test")
        assert event.timestamp >= t0
        assert event.timestamp <= time.time()


# ─── T3.3-T3.9: Ring Buffer ──────────────────────────────────────

class TestEventBuffer:
    """T3.3-T3.9: ReflexEventBuffer operations."""

    def test_push_and_get_recent(self):
        from src.services.reflex_streaming import ReflexEventBuffer, ReflexEvent
        buf = ReflexEventBuffer(max_size=10)
        for i in range(5):
            buf.push(ReflexEvent(event_type=f"test_{i}", pipeline_id="p1"))
        recent = buf.get_recent(3)
        assert len(recent) == 3
        assert recent[-1]["event"] == "test_4"

    def test_eviction_at_max_size(self):
        from src.services.reflex_streaming import ReflexEventBuffer, ReflexEvent
        buf = ReflexEventBuffer(max_size=5)
        for i in range(10):
            buf.push(ReflexEvent(event_type=f"evt_{i}"))
        assert buf.size == 5
        recent = buf.get_recent(10)
        assert len(recent) == 5
        # Oldest should be evt_5 (first 5 evicted)
        assert recent[0]["event"] == "evt_5"
        assert recent[-1]["event"] == "evt_9"

    def test_get_since(self):
        from src.services.reflex_streaming import ReflexEventBuffer, ReflexEvent
        buf = ReflexEventBuffer(max_size=20)
        # Push old events
        for i in range(3):
            buf.push(ReflexEvent(event_type=f"old_{i}", timestamp=1000.0 + i))
        # Push new events
        cutoff = time.time()
        for i in range(3):
            buf.push(ReflexEvent(event_type=f"new_{i}"))
        result = buf.get_since(cutoff - 0.001)  # Slight margin
        assert len(result) == 3
        assert all(e["event"].startswith("new_") for e in result)

    def test_get_by_pipeline(self):
        from src.services.reflex_streaming import ReflexEventBuffer, ReflexEvent
        buf = ReflexEventBuffer(max_size=20)
        buf.push(ReflexEvent(event_type="a", pipeline_id="pipe_1"))
        buf.push(ReflexEvent(event_type="b", pipeline_id="pipe_2"))
        buf.push(ReflexEvent(event_type="c", pipeline_id="pipe_1"))
        buf.push(ReflexEvent(event_type="d", pipeline_id="pipe_3"))
        result = buf.get_by_pipeline("pipe_1")
        assert len(result) == 2
        assert all(e["pipeline_id"] == "pipe_1" for e in result)

    def test_get_stats(self):
        from src.services.reflex_streaming import ReflexEventBuffer, ReflexEvent, ReflexEventType
        buf = ReflexEventBuffer(max_size=50)
        buf.push(ReflexEvent(event_type=ReflexEventType.RECOMMENDATION))
        buf.push(ReflexEvent(event_type=ReflexEventType.RECOMMENDATION))
        buf.push(ReflexEvent(event_type=ReflexEventType.OUTCOME))
        stats = buf.get_stats()
        assert stats["total_events"] == 3
        assert stats["buffer_size"] == 3
        assert stats["max_size"] == 50
        assert stats["sequence"] == 3
        assert stats["by_type"]["reflex:recommendation"] == 2
        assert stats["by_type"]["reflex:outcome"] == 1

    def test_empty_stats(self):
        from src.services.reflex_streaming import ReflexEventBuffer
        buf = ReflexEventBuffer()
        stats = buf.get_stats()
        assert stats["total_events"] == 0
        assert stats["buffer_size"] == 0

    def test_clear(self):
        from src.services.reflex_streaming import ReflexEventBuffer, ReflexEvent
        buf = ReflexEventBuffer(max_size=10)
        buf.push(ReflexEvent(event_type="test"))
        buf.push(ReflexEvent(event_type="test"))
        assert buf.size == 2
        buf.clear()
        assert buf.size == 0
        stats = buf.get_stats()
        assert stats["total_events"] == 0
        assert stats["sequence"] == 0

    def test_thread_safety(self):
        from src.services.reflex_streaming import ReflexEventBuffer, ReflexEvent
        buf = ReflexEventBuffer(max_size=1000)
        errors = []

        def writer(thread_id):
            try:
                for i in range(100):
                    buf.push(ReflexEvent(event_type=f"t{thread_id}_{i}", pipeline_id=f"t{thread_id}"))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert buf.size == 500  # 5 threads x 100 events


# ─── T3.10-T3.15: Emitter ────────────────────────────────────────

class TestEventEmitter:
    """T3.10-T3.15: ReflexEventEmitter."""

    @pytest.mark.asyncio
    async def test_emit_recommendation(self):
        from src.services.reflex_streaming import ReflexEventEmitter, ReflexEventBuffer
        buf = ReflexEventBuffer(max_size=10)
        emitter = ReflexEventEmitter(buffer=buf)
        await emitter.emit_recommendation(
            pipeline_id="pipe_1",
            subtask_idx=1,
            subtask_marker="step_1",
            phase_type="research",
            model_tier="silver",
            recommendations=[
                {"tool_id": "vetka_read_file", "score": 0.9, "reason": "reading"},
                {"tool_id": "vetka_search_semantic", "score": 0.7, "reason": "search"},
            ],
        )
        events = buf.get_recent(1)
        assert len(events) == 1
        e = events[0]
        assert e["event"] == "reflex:recommendation"
        assert e["pipeline_id"] == "pipe_1"
        assert e["data"]["count"] == 2
        assert e["data"]["recommended"][0]["tool_id"] == "vetka_read_file"

    @pytest.mark.asyncio
    async def test_emit_outcome_match_rate(self):
        from src.services.reflex_streaming import ReflexEventEmitter, ReflexEventBuffer
        buf = ReflexEventBuffer(max_size=10)
        emitter = ReflexEventEmitter(buffer=buf)
        await emitter.emit_outcome(
            pipeline_id="pipe_1",
            subtask_idx=1,
            subtask_marker="step_1",
            phase_type="fix",
            model_tier="silver",
            recommended_ids=["tool_a", "tool_b", "tool_c", "tool_d"],
            used_ids=["tool_a", "tool_c", "tool_e"],
            feedback_count=3,
        )
        events = buf.get_recent(1)
        e = events[0]
        assert e["event"] == "reflex:outcome"
        assert e["data"]["match_rate"] == 0.5  # 2 matched out of 4 recommended
        assert set(e["data"]["matched"]) == {"tool_a", "tool_c"}
        assert e["data"]["feedback_count"] == 3

    @pytest.mark.asyncio
    async def test_emit_verifier(self):
        from src.services.reflex_streaming import ReflexEventEmitter, ReflexEventBuffer
        buf = ReflexEventBuffer(max_size=10)
        emitter = ReflexEventEmitter(buffer=buf)
        await emitter.emit_verifier(
            pipeline_id="pipe_1",
            subtask_idx=2,
            subtask_marker="step_2",
            phase_type="build",
            tools_used=["vetka_edit_file", "vetka_read_file"],
            verifier_passed=True,
            feedback_count=2,
        )
        events = buf.get_recent(1)
        e = events[0]
        assert e["event"] == "reflex:verifier"
        assert e["data"]["verifier_passed"] is True
        assert len(e["data"]["tools_used"]) == 2

    @pytest.mark.asyncio
    async def test_emit_filter_tokens_estimate(self):
        from src.services.reflex_streaming import ReflexEventEmitter, ReflexEventBuffer
        buf = ReflexEventBuffer(max_size=10)
        emitter = ReflexEventEmitter(buffer=buf)
        await emitter.emit_filter(
            pipeline_id="pipe_1",
            subtask_idx=3,
            subtask_marker="step_3",
            phase_type="fix",
            model_tier="bronze",
            original_count=45,
            filtered_count=8,
        )
        events = buf.get_recent(1)
        e = events[0]
        assert e["event"] == "reflex:filter"
        assert e["data"]["original_count"] == 45
        assert e["data"]["filtered_count"] == 8
        assert e["data"]["removed"] == 37
        # ~120 tokens per schema avg
        assert e["data"]["tokens_saved_estimate"] == 37 * 120

    @pytest.mark.asyncio
    async def test_emit_fallback(self):
        from src.services.reflex_streaming import ReflexEventEmitter, ReflexEventBuffer
        buf = ReflexEventBuffer(max_size=10)
        emitter = ReflexEventEmitter(buffer=buf)
        await emitter.emit_fallback(
            pipeline_id="pipe_1",
            subtask_idx=1,
            subtask_marker="step_1",
            phase_type="fix",
            model_tier="bronze",
            reason="No tool called — retrying with full schemas",
        )
        events = buf.get_recent(1)
        e = events[0]
        assert e["event"] == "reflex:fallback"
        assert "retrying" in e["data"]["reason"]

    @pytest.mark.asyncio
    async def test_emitter_broadcasts_via_ws(self):
        from src.services.reflex_streaming import ReflexEventEmitter, ReflexEventBuffer
        buf = ReflexEventBuffer(max_size=10)
        ws_mock = AsyncMock()
        emitter = ReflexEventEmitter(ws_broadcaster=ws_mock, buffer=buf)
        await emitter.emit_recommendation(
            pipeline_id="pipe_1",
            subtask_idx=1,
            subtask_marker="step_1",
            phase_type="research",
            model_tier="silver",
            recommendations=[{"tool_id": "tool_a", "score": 0.8, "reason": "test"}],
        )
        # WS broadcaster should have been called
        ws_mock.broadcast.assert_called_once()
        call_args = ws_mock.broadcast.call_args[0][0]
        assert call_args["type"] == "reflex_event"
        assert call_args["event"] == "reflex:recommendation"
        assert "_seq" in call_args


# ─── T3.16: Singleton ────────────────────────────────────────────

class TestBufferSingleton:
    """T3.16: Global buffer singleton."""

    def test_get_returns_same(self):
        from src.services.reflex_streaming import get_reflex_event_buffer, reset_reflex_event_buffer
        reset_reflex_event_buffer()
        b1 = get_reflex_event_buffer()
        b2 = get_reflex_event_buffer()
        assert b1 is b2
        reset_reflex_event_buffer()

    def test_reset_clears(self):
        from src.services.reflex_streaming import get_reflex_event_buffer, reset_reflex_event_buffer
        reset_reflex_event_buffer()
        b1 = get_reflex_event_buffer()
        reset_reflex_event_buffer()
        b2 = get_reflex_event_buffer()
        assert b1 is not b2
        reset_reflex_event_buffer()


# ─── T3.17-T3.19: REST Endpoints ─────────────────────────────────

class TestStreamingEndpoints:
    """T3.17-T3.19: REST API for streaming events."""

    @pytest.mark.asyncio
    async def test_get_events(self):
        from src.api.routes.reflex_routes import reflex_events
        from src.services.reflex_streaming import ReflexEventBuffer, ReflexEvent, ReflexEventType

        mock_buf = ReflexEventBuffer(max_size=50)
        mock_buf.push(ReflexEvent(event_type=ReflexEventType.RECOMMENDATION, pipeline_id="p1"))
        mock_buf.push(ReflexEvent(event_type=ReflexEventType.OUTCOME, pipeline_id="p1"))

        with patch("src.api.routes.reflex_routes._is_reflex_enabled", return_value=True), \
             patch("src.services.reflex_streaming.get_reflex_event_buffer", return_value=mock_buf):
            result = await reflex_events(n=10, since=0, pipeline_id="")

        assert result["enabled"] is True
        assert result["count"] == 2
        assert len(result["events"]) == 2

    @pytest.mark.asyncio
    async def test_get_events_by_pipeline(self):
        from src.api.routes.reflex_routes import reflex_events
        from src.services.reflex_streaming import ReflexEventBuffer, ReflexEvent

        mock_buf = ReflexEventBuffer(max_size=50)
        mock_buf.push(ReflexEvent(event_type="test", pipeline_id="pipe_A"))
        mock_buf.push(ReflexEvent(event_type="test", pipeline_id="pipe_B"))
        mock_buf.push(ReflexEvent(event_type="test", pipeline_id="pipe_A"))

        with patch("src.api.routes.reflex_routes._is_reflex_enabled", return_value=True), \
             patch("src.services.reflex_streaming.get_reflex_event_buffer", return_value=mock_buf):
            result = await reflex_events(n=20, since=0, pipeline_id="pipe_A")

        assert result["count"] == 2
        assert all(e["pipeline_id"] == "pipe_A" for e in result["events"])

    @pytest.mark.asyncio
    async def test_get_event_stats(self):
        from src.api.routes.reflex_routes import reflex_event_stats
        from src.services.reflex_streaming import ReflexEventBuffer, ReflexEvent, ReflexEventType

        mock_buf = ReflexEventBuffer(max_size=50)
        mock_buf.push(ReflexEvent(event_type=ReflexEventType.FILTER))
        mock_buf.push(ReflexEvent(event_type=ReflexEventType.FILTER))
        mock_buf.push(ReflexEvent(event_type=ReflexEventType.RECOMMENDATION))

        with patch("src.api.routes.reflex_routes._is_reflex_enabled", return_value=True), \
             patch("src.services.reflex_streaming.get_reflex_event_buffer", return_value=mock_buf):
            result = await reflex_event_stats()

        assert result["enabled"] is True
        assert result["buffer"]["buffer_size"] == 3
        assert result["buffer"]["by_type"]["reflex:filter"] == 2

    @pytest.mark.asyncio
    async def test_events_disabled(self):
        from src.api.routes.reflex_routes import reflex_events
        with patch("src.api.routes.reflex_routes._is_reflex_enabled", return_value=False):
            result = await reflex_events(n=10, since=0, pipeline_id="")
        assert result["enabled"] is False


# ─── T3.20: Pipeline integration ─────────────────────────────────

class TestPipelineEmitterIntegration:
    """T3.20: Pipeline _get_reflex_emitter lazy init."""

    def test_get_reflex_emitter_lazy_init(self):
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline.__new__(AgentPipeline)
        pipeline._reflex_emitter = None
        # First call should create emitter
        emitter = pipeline._get_reflex_emitter()
        assert emitter is not None
        # Second call should return same instance
        emitter2 = pipeline._get_reflex_emitter()
        assert emitter is emitter2
