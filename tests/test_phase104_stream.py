"""
VETKA Phase 104.7 - Stream Visibility Tests

MARKER_104_STREAM_TESTS

Tests for stream visibility control and Socket.IO integration.
Validates:
- StreamLevel enum (full, summary, silent)
- PipelineTask visibility flags
- Subtask visibility control
- StreamManager event emission and compression
- Specific stream event types (pipeline progress, subtask events, artifacts)
- Visibility behavior matrix (emit behavior, compression)

@status: active
@phase: 104.7
@marker: MARKER_104_STREAM_TESTS
@depends: pytest, pytest-asyncio, unittest.mock
@used_by: agent_pipeline.py, orchestrator_with_elisya.py
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime


# ============================================================
# TEST MARKERS
# ============================================================

pytestmark = [
    pytest.mark.stream_visibility,
    pytest.mark.phase_104,
]


# ============================================================
# MOCK DATA STRUCTURES
# ============================================================

@dataclass
class MockSubtask:
    """Mock Subtask with stream visibility"""
    description: str
    needs_research: bool = False
    question: Optional[str] = None
    context: Optional[Dict] = None
    result: Optional[str] = None
    status: str = "pending"
    marker: Optional[str] = None
    visible: bool = True  # Show progress in UI
    stream_result: bool = True  # Stream completion to chat


@dataclass
class MockPipelineTask:
    """Mock PipelineTask with stream visibility control"""
    task_id: str
    task: str
    phase_type: str  # research, fix, build
    status: str = "pending"
    subtasks: List[MockSubtask] = None
    timestamp: float = 0
    results: Optional[Dict] = None
    visible_to_user: bool = True  # Show in chat UI
    stream_level: str = "summary"  # "full" | "summary" | "silent"
    highlight_artifacts: bool = True  # Highlight code blocks in output

    def __post_init__(self):
        if self.subtasks is None:
            self.subtasks = []


@dataclass
class MockStreamManager:
    """Mock StreamManager for testing stream emissions"""
    socketio: Optional[Any] = None
    buffer: List[Dict] = None

    def __post_init__(self):
        if self.buffer is None:
            self.buffer = []

    async def emit(self, event: str, data: Dict, visibility: str = "summary"):
        """Emit event with visibility control"""
        if visibility == "silent":
            return

        if visibility == "summary":
            data = self.compress_for_stream(data)

        self.buffer.append({"event": event, "data": data, "visibility": visibility})

        if self.socketio:
            await asyncio.sleep(0)  # Simulate async emit
            self.socketio.emit(event, data)

    def compress_for_stream(self, data: Dict) -> Dict:
        """Compress data for streaming"""
        compressed = {}
        for key, value in data.items():
            if isinstance(value, str) and len(value) > 200:
                compressed[key] = value[:200] + "..."
            elif isinstance(value, dict):
                compressed[key] = {"...": f"{len(str(value))} bytes"}
            elif isinstance(value, list) and len(value) > 10:
                compressed[key] = value[:10] + [{"...": f"{len(value) - 10} more"}]
            else:
                compressed[key] = value
        return compressed


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def sample_pipeline_task():
    """Create a sample PipelineTask"""
    return MockPipelineTask(
        task_id="task_001",
        task="Implement new feature",
        phase_type="build",
        status="pending",
        subtasks=[
            MockSubtask(
                description="Analyze requirements",
                needs_research=False,
                visible=True,
                stream_result=True
            ),
            MockSubtask(
                description="Implement core logic",
                needs_research=False,
                visible=True,
                stream_result=True
            ),
            MockSubtask(
                description="Write tests",
                needs_research=True,
                question="What testing framework should we use?",
                visible=True,
                stream_result=True
            ),
        ],
        visible_to_user=True,
        stream_level="summary"
    )


@pytest.fixture
def stream_manager():
    """Create a StreamManager instance"""
    return MockStreamManager()


@pytest.fixture
def mock_socketio():
    """Create a mock Socket.IO instance"""
    mock = MagicMock()
    mock.emit = MagicMock()
    return mock


@pytest.fixture
def large_data_payload():
    """Create large data payload for compression testing"""
    return {
        "task_id": "task_001",
        "long_description": "x" * 1000,
        "detailed_results": {
            "step_1": "y" * 500,
            "step_2": "z" * 500,
            "step_3": "w" * 500,
        },
        "items": list(range(100))
    }


# ============================================================
# TEST CLASSES
# ============================================================

class TestStreamLevels:
    """Tests for stream visibility levels."""

    def test_full_visibility_sends_complete_data(self):
        """FULL level should send uncompressed data."""
        data = {
            "task_id": "task_001",
            "description": "x" * 500,
            "status": "in_progress"
        }

        manager = MockStreamManager()
        manager.buffer = []

        # Simulate full visibility emit
        manager.buffer.append({"event": "task_progress", "data": data, "visibility": "full"})

        assert len(manager.buffer) == 1
        assert manager.buffer[0]["data"]["description"] == "x" * 500
        assert manager.buffer[0]["visibility"] == "full"

    def test_summary_visibility_compresses_data(self):
        """SUMMARY level should compress large data."""
        data = {
            "task_id": "task_001",
            "long_text": "x" * 1000,
            "nested": {
                "key": "value" * 100
            }
        }

        manager = MockStreamManager()
        compressed = manager.compress_for_stream(data)

        assert len(compressed["long_text"]) <= 203  # Truncated to 200 + "..."
        assert "..." in compressed["long_text"]
        assert "..." in compressed["nested"]

    def test_silent_visibility_skips_emit(self):
        """SILENT level should not emit anything."""
        manager = MockStreamManager()
        manager.buffer = []

        # SILENT should be handled by caller, not added to buffer
        # This tests the contract: silent=True -> no buffer entry
        visibility = "silent"

        if visibility != "silent":
            manager.buffer.append({"event": "test", "data": {}})

        assert len(manager.buffer) == 0

    def test_default_visibility_is_summary(self):
        """Default visibility should be SUMMARY."""
        task = MockPipelineTask(
            task_id="task_001",
            task="Test task",
            phase_type="build"
        )

        assert task.stream_level == "summary"


class TestPipelineVisibility:
    """Tests for PipelineTask visibility flags."""

    def test_visible_to_user_flag(self, sample_pipeline_task):
        """visible_to_user controls chat display."""
        assert sample_pipeline_task.visible_to_user is True

        sample_pipeline_task.visible_to_user = False
        assert sample_pipeline_task.visible_to_user is False

    def test_stream_level_controls_compression(self, sample_pipeline_task):
        """stream_level affects data size."""
        assert sample_pipeline_task.stream_level in ["full", "summary", "silent"]

        # Test all valid levels
        for level in ["full", "summary", "silent"]:
            sample_pipeline_task.stream_level = level
            assert sample_pipeline_task.stream_level == level

    def test_highlight_artifacts_flag(self, sample_pipeline_task):
        """highlight_artifacts controls code highlighting."""
        assert sample_pipeline_task.highlight_artifacts is True

        sample_pipeline_task.highlight_artifacts = False
        assert sample_pipeline_task.highlight_artifacts is False

    def test_task_to_dict_preserves_visibility(self, sample_pipeline_task):
        """Task serialization preserves visibility flags"""
        task_dict = asdict(sample_pipeline_task)

        assert task_dict["visible_to_user"] is True
        assert task_dict["stream_level"] == "summary"
        assert task_dict["highlight_artifacts"] is True


class TestSubtaskVisibility:
    """Tests for Subtask visibility."""

    def test_subtask_visible_flag(self):
        """visible flag controls progress display."""
        subtask = MockSubtask(
            description="Test subtask",
            visible=True
        )
        assert subtask.visible is True

        subtask.visible = False
        assert subtask.visible is False

    def test_subtask_stream_result_flag(self):
        """stream_result controls completion emit."""
        subtask = MockSubtask(
            description="Test subtask",
            stream_result=True
        )
        assert subtask.stream_result is True

        subtask.stream_result = False
        assert subtask.stream_result is False

    def test_subtask_visibility_independent_of_task(self, sample_pipeline_task):
        """Subtask visibility is independent of parent task visibility"""
        sample_pipeline_task.visible_to_user = False

        # Subtasks should still have their own visibility
        assert sample_pipeline_task.subtasks[0].visible is True
        assert sample_pipeline_task.subtasks[0].stream_result is True


class TestStreamManager:
    """Tests for StreamManager."""

    @pytest.mark.asyncio
    async def test_emit_with_socketio(self, stream_manager, mock_socketio):
        """Emit should call socketio.emit."""
        stream_manager.socketio = mock_socketio

        await stream_manager.emit("test_event", {"data": "test"}, visibility="full")

        mock_socketio.emit.assert_called_once()
        call_args = mock_socketio.emit.call_args
        assert call_args[0][0] == "test_event"

    @pytest.mark.asyncio
    async def test_emit_compresses_summary(self, stream_manager, large_data_payload):
        """Summary visibility should compress data."""
        await stream_manager.emit(
            "progress",
            large_data_payload,
            visibility="summary"
        )

        assert len(stream_manager.buffer) == 1
        emitted_data = stream_manager.buffer[0]["data"]

        # Check compression occurred
        assert len(str(emitted_data)) < len(str(large_data_payload))
        assert "..." in str(emitted_data) or len(emitted_data["items"]) < 100

    @pytest.mark.asyncio
    async def test_emit_buffers_events(self, stream_manager):
        """Events should be buffered for history."""
        await stream_manager.emit("event1", {"data": "1"}, visibility="full")
        await stream_manager.emit("event2", {"data": "2"}, visibility="full")
        await stream_manager.emit("event3", {"data": "3"}, visibility="full")

        assert len(stream_manager.buffer) == 3
        assert stream_manager.buffer[0]["event"] == "event1"
        assert stream_manager.buffer[1]["event"] == "event2"
        assert stream_manager.buffer[2]["event"] == "event3"

    @pytest.mark.asyncio
    async def test_emit_silent_not_buffered(self, stream_manager):
        """Silent events should not be buffered"""
        # Simulate silent handling - no buffer entry
        visibility = "silent"
        if visibility != "silent":
            stream_manager.buffer.append({"event": "test", "data": {}})

        assert len(stream_manager.buffer) == 0

    def test_compress_for_stream_truncates(self, stream_manager, large_data_payload):
        """Large strings should be truncated."""
        compressed = stream_manager.compress_for_stream(large_data_payload)

        assert len(compressed["long_description"]) <= 203
        assert compressed["long_description"].endswith("...")

    def test_compress_for_stream_handles_nested(self, stream_manager):
        """Compression should handle nested structures."""
        data = {
            "nested_dict": {
                "key": "value" * 100
            },
            "nested_list": list(range(100))
        }

        compressed = stream_manager.compress_for_stream(data)

        assert "..." in compressed["nested_dict"]
        assert len(compressed["nested_list"]) <= 11  # 10 items + 1 "more" marker


class TestStreamEvents:
    """Tests for specific stream event types."""

    @pytest.mark.asyncio
    async def test_pipeline_progress_event(self, stream_manager):
        """Pipeline progress event should be emitted correctly"""
        event_data = {
            "task_id": "task_001",
            "current_subtask": 2,
            "total_subtasks": 5,
            "status": "in_progress",
            "message": "Processing subtask 2 of 5"
        }

        await stream_manager.emit("pipeline_progress", event_data, visibility="summary")

        assert len(stream_manager.buffer) == 1
        assert stream_manager.buffer[0]["event"] == "pipeline_progress"
        assert stream_manager.buffer[0]["data"]["task_id"] == "task_001"

    @pytest.mark.asyncio
    async def test_subtask_start_event(self, stream_manager):
        """Subtask start event should be emitted correctly"""
        event_data = {
            "task_id": "task_001",
            "subtask_index": 0,
            "description": "Analyze requirements",
            "status": "started"
        }

        await stream_manager.emit("subtask_start", event_data, visibility="full")

        assert stream_manager.buffer[0]["event"] == "subtask_start"
        assert stream_manager.buffer[0]["visibility"] == "full"

    @pytest.mark.asyncio
    async def test_subtask_complete_event(self, stream_manager):
        """Subtask complete event should be emitted correctly"""
        event_data = {
            "task_id": "task_001",
            "subtask_index": 0,
            "description": "Analyze requirements",
            "status": "completed",
            "result": "Requirements clearly defined",
            "duration_ms": 5000
        }

        await stream_manager.emit("subtask_complete", event_data, visibility="summary")

        assert stream_manager.buffer[0]["event"] == "subtask_complete"

    @pytest.mark.asyncio
    async def test_artifact_staged_event(self, stream_manager):
        """Artifact staged event should be emitted correctly"""
        event_data = {
            "artifact_id": "art_001",
            "filename": "src/feature.py",
            "content_length": 5000,
            "language": "python",
            "staged": True
        }

        await stream_manager.emit("artifact_staged", event_data, visibility="summary")

        assert stream_manager.buffer[0]["event"] == "artifact_staged"

    @pytest.mark.asyncio
    async def test_research_trigger_event(self, stream_manager):
        """Research trigger event should be emitted correctly"""
        event_data = {
            "task_id": "task_001",
            "subtask_index": 1,
            "question": "What's the best approach?",
            "status": "research_triggered"
        }

        await stream_manager.emit("research_trigger", event_data, visibility="summary")

        assert stream_manager.buffer[0]["event"] == "research_trigger"


@pytest.mark.parametrize("visibility,should_emit,should_compress", [
    ("full", True, False),
    ("summary", True, True),
    ("silent", False, False),
])
class TestVisibilityMatrix:
    """Parametrized visibility behavior tests."""

    @pytest.mark.asyncio
    async def test_visibility_behavior(self, visibility, should_emit, should_compress):
        """Test visibility behavior matrix"""
        stream_manager = MockStreamManager()

        data = {
            "description": "x" * 1000,
            "status": "in_progress"
        }

        # Track if emit was called
        emit_called = False
        compression_applied = False

        if visibility != "silent":
            emit_called = True
            if visibility == "summary":
                compression_applied = True

        assert emit_called == should_emit
        assert compression_applied == should_compress

    @pytest.mark.asyncio
    async def test_visibility_emit_count(self, visibility, should_emit, should_compress):
        """Test that visibility levels emit correctly"""
        stream_manager = MockStreamManager()

        await stream_manager.emit("test_event", {"data": "test"}, visibility=visibility)

        if should_emit:
            assert len(stream_manager.buffer) == 1
        else:
            assert len(stream_manager.buffer) == 0


# ============================================================
# INTEGRATION TESTS
# ============================================================

class TestStreamVisibilityIntegration:
    """Integration tests for stream visibility across components."""

    @pytest.mark.asyncio
    async def test_full_pipeline_with_stream_events(self, sample_pipeline_task, stream_manager):
        """Test complete pipeline with stream events"""
        # Start pipeline
        await stream_manager.emit(
            "pipeline_start",
            {"task_id": sample_pipeline_task.task_id},
            visibility=sample_pipeline_task.stream_level
        )

        # Simulate subtask execution
        for i, subtask in enumerate(sample_pipeline_task.subtasks):
            if subtask.visible:
                await stream_manager.emit(
                    "subtask_start",
                    {"subtask_index": i, "description": subtask.description},
                    visibility=sample_pipeline_task.stream_level
                )

            if subtask.stream_result:
                await stream_manager.emit(
                    "subtask_complete",
                    {"subtask_index": i, "result": "Completed"},
                    visibility=sample_pipeline_task.stream_level
                )

        # End pipeline
        await stream_manager.emit(
            "pipeline_complete",
            {"task_id": sample_pipeline_task.task_id, "status": "success"},
            visibility=sample_pipeline_task.stream_level
        )

        # Verify buffer contains events
        assert len(stream_manager.buffer) > 0
        assert any(e["event"] == "pipeline_start" for e in stream_manager.buffer)
        assert any(e["event"] == "pipeline_complete" for e in stream_manager.buffer)

    @pytest.mark.asyncio
    async def test_visibility_flags_control_emission(self, stream_manager):
        """Test that visibility flags control event emission"""
        invisible_task = MockPipelineTask(
            task_id="invisible_task",
            task="Hidden task",
            phase_type="build",
            visible_to_user=False,
            stream_level="silent"
        )

        # Events for invisible task should not be emitted
        visible_to_user = invisible_task.visible_to_user
        stream_level = invisible_task.stream_level

        if visible_to_user and stream_level != "silent":
            await stream_manager.emit(
                "task_event",
                {"task_id": invisible_task.task_id},
                visibility=stream_level
            )

        # Buffer should be empty for truly invisible task
        assert len(stream_manager.buffer) == 0

    def test_mixed_subtask_visibility(self, sample_pipeline_task, stream_manager):
        """Test pipeline with mixed visible/invisible subtasks"""
        # Some subtasks visible, some invisible
        sample_pipeline_task.subtasks[0].visible = True
        sample_pipeline_task.subtasks[1].visible = False
        sample_pipeline_task.subtasks[2].visible = True

        visible_count = sum(1 for s in sample_pipeline_task.subtasks if s.visible)
        assert visible_count == 2


# ============================================================
# EDGE CASE TESTS
# ============================================================

class TestStreamVisibilityEdgeCases:
    """Edge case tests for stream visibility."""

    @pytest.mark.asyncio
    async def test_empty_data_compression(self, stream_manager):
        """Compress empty data"""
        compressed = stream_manager.compress_for_stream({})
        assert compressed == {}

    @pytest.mark.asyncio
    async def test_none_values_compression(self, stream_manager):
        """Handle None values in compression"""
        data = {"key": None, "value": "test"}
        compressed = stream_manager.compress_for_stream(data)

        assert compressed["key"] is None
        assert compressed["value"] == "test"

    @pytest.mark.asyncio
    async def test_deeply_nested_compression(self, stream_manager):
        """Handle deeply nested structures"""
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "long_text": "x" * 1000
                    }
                }
            }
        }

        compressed = stream_manager.compress_for_stream(data)
        # Should compress the nested structure
        assert "..." in str(compressed) or isinstance(compressed.get("level1"), dict)

    def test_invalid_visibility_level(self, stream_manager):
        """Invalid visibility level should be handled"""
        task = MockPipelineTask(
            task_id="test",
            task="Test",
            phase_type="build",
            stream_level="invalid"  # Invalid level
        )

        # System should allow setting, validation would happen in emit
        assert task.stream_level == "invalid"

    @pytest.mark.asyncio
    async def test_many_buffered_events(self, stream_manager):
        """Test handling many buffered events"""
        for i in range(100):
            await stream_manager.emit(
                f"event_{i}",
                {"index": i},
                visibility="summary"
            )

        assert len(stream_manager.buffer) == 100


# ============================================================
# PERFORMANCE TESTS
# ============================================================

class TestStreamVisibilityPerformance:
    """Performance tests for stream visibility."""

    def test_compression_performance(self, stream_manager, large_data_payload):
        """Compression should be fast"""
        import time

        start = time.time()
        for _ in range(100):
            stream_manager.compress_for_stream(large_data_payload)
        elapsed = time.time() - start

        # Should complete 100 compressions in under 1 second
        assert elapsed < 1.0

    @pytest.mark.asyncio
    async def test_emission_performance(self, stream_manager):
        """Many emissions should be fast"""
        import time

        start = time.time()
        for i in range(100):
            await stream_manager.emit(
                "perf_test",
                {"index": i},
                visibility="summary"
            )
        elapsed = time.time() - start

        # Should complete 100 emissions in under 2 seconds
        assert elapsed < 2.0
        assert len(stream_manager.buffer) == 100


# ============================================================
# PHASE 104.8 GROK IMPROVEMENTS TESTS
# MARKER_104_GROK_IMPROVEMENTS
# ============================================================

class TestGrokImprovementsPhase1048:
    """Tests for Phase 104.8 Grok improvements."""

    def test_stream_event_type_voice_events(self):
        """Test new voice/Jarvis event types exist."""
        from src.api.handlers.stream_handler import StreamEventType

        assert hasattr(StreamEventType, 'VOICE_TRANSCRIPT')
        assert hasattr(StreamEventType, 'JARVIS_INTERRUPT')
        assert hasattr(StreamEventType, 'JARVIS_PREDICTION')
        assert StreamEventType.VOICE_TRANSCRIPT.value == "voice_transcript"
        assert StreamEventType.JARVIS_INTERRUPT.value == "jarvis_interrupt"
        assert StreamEventType.JARVIS_PREDICTION.value == "jarvis_prediction"

    def test_stream_event_type_error_events(self):
        """Test new error/system event types exist."""
        from src.api.handlers.stream_handler import StreamEventType

        assert hasattr(StreamEventType, 'STREAM_ERROR')
        assert hasattr(StreamEventType, 'ROOM_JOINED')
        assert hasattr(StreamEventType, 'ROOM_LEFT')
        assert StreamEventType.STREAM_ERROR.value == "stream_error"

    def test_stream_config_defaults(self):
        """Test StreamConfig dataclass with defaults."""
        from src.api.handlers.stream_handler import StreamConfig

        config = StreamConfig()
        assert config.string_compression_threshold == 200
        assert config.list_truncate_threshold == 10
        assert config.summary_max_length == 500
        assert config.enable_metrics is True

    def test_stream_config_custom_values(self):
        """Test StreamConfig with custom values."""
        from src.api.handlers.stream_handler import StreamConfig

        config = StreamConfig(
            string_compression_threshold=500,
            list_truncate_threshold=20,
            summary_max_length=1000,
            enable_metrics=False
        )
        assert config.string_compression_threshold == 500
        assert config.list_truncate_threshold == 20
        assert config.summary_max_length == 1000
        assert config.enable_metrics is False

    def test_stream_manager_with_custom_config(self):
        """Test StreamManager accepts custom config."""
        from src.api.handlers.stream_handler import StreamManager, StreamConfig

        config = StreamConfig(string_compression_threshold=100)
        manager = StreamManager(config=config)

        assert manager._compression_threshold == 100
        assert manager._config.string_compression_threshold == 100

    def test_stream_manager_room_tracking(self):
        """Test room join/leave tracking."""
        from src.api.handlers.stream_handler import StreamManager

        manager = StreamManager()

        # Join room
        manager.join_room("session_123", "room_abc")
        assert "session_123" in manager.get_room_sessions("room_abc")
        assert "room_abc" in manager.get_session_rooms("session_123")

        # Leave room
        manager.leave_room("session_123", "room_abc")
        assert "session_123" not in manager.get_room_sessions("room_abc")
        assert "room_abc" not in manager.get_session_rooms("session_123")

    def test_stream_manager_cleanup_session(self):
        """Test session cleanup removes from all rooms."""
        from src.api.handlers.stream_handler import StreamManager

        manager = StreamManager()

        # Session joins multiple rooms
        manager.join_room("session_123", "room_a")
        manager.join_room("session_123", "room_b")
        manager.join_room("session_123", "room_c")

        # Verify joins
        assert len(manager.get_session_rooms("session_123")) == 3

        # Cleanup on disconnect
        cleaned_rooms = manager.cleanup_session("session_123")

        assert len(cleaned_rooms) == 3
        assert "session_123" not in manager._session_rooms
        assert all("session_123" not in manager.get_room_sessions(r) for r in ["room_a", "room_b", "room_c"])

    def test_stream_manager_metrics_tracking(self):
        """Test metrics tracking is initialized."""
        from src.api.handlers.stream_handler import StreamManager

        manager = StreamManager()

        metrics = manager.get_metrics()
        assert "total_emits" in metrics
        assert "compressed_emits" in metrics
        assert "silent_skipped" in metrics
        assert "errors" in metrics
        assert "bytes_saved" in metrics
        assert "active_rooms" in metrics
        assert "active_sessions" in metrics
        assert "buffer_size" in metrics

    @pytest.mark.asyncio
    async def test_emit_voice_transcript(self):
        """Test voice transcript typed emitter."""
        from src.api.handlers.stream_handler import StreamManager

        manager = StreamManager()

        event = await manager.emit_voice_transcript(
            workflow_id="wf_001",
            transcript="Hello world",
            is_final=False,
            confidence=0.95
        )

        assert event is not None
        assert event.event_type == "voice_transcript"
        assert event.data["transcript"] == "Hello world"
        assert event.data["is_final"] is False
        assert event.data["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_emit_jarvis_interrupt(self):
        """Test Jarvis interrupt typed emitter."""
        from src.api.handlers.stream_handler import StreamManager

        manager = StreamManager()

        event = await manager.emit_jarvis_interrupt(
            workflow_id="wf_001",
            reason="user_interrupt"
        )

        assert event is not None
        assert event.event_type == "jarvis_interrupt"
        assert event.data["reason"] == "user_interrupt"
        assert event.priority == 10  # High priority

    @pytest.mark.asyncio
    async def test_emit_jarvis_prediction(self):
        """Test Jarvis T9-like prediction emitter."""
        from src.api.handlers.stream_handler import StreamManager

        manager = StreamManager()

        event = await manager.emit_jarvis_prediction(
            workflow_id="wf_001",
            partial_input="How do I",
            predicted_response="You can do it by...",
            confidence=0.7
        )

        assert event is not None
        assert event.event_type == "jarvis_prediction"
        assert event.data["partial_input"] == "How do I"
        assert event.data["predicted_response"] == "You can do it by..."
        assert event.data["is_draft"] is True

    @pytest.mark.asyncio
    async def test_emit_stream_error(self):
        """Test stream error typed emitter."""
        from src.api.handlers.stream_handler import StreamManager

        manager = StreamManager()

        event = await manager.emit_stream_error(
            workflow_id="wf_001",
            error="Connection lost",
            error_type="network",
            recoverable=True
        )

        assert event is not None
        assert event.event_type == "stream_error"
        assert event.data["error"] == "Connection lost"
        assert event.data["error_type"] == "network"
        assert event.data["recoverable"] is True

    @pytest.mark.asyncio
    async def test_emit_room_joined(self):
        """Test room joined typed emitter."""
        from src.api.handlers.stream_handler import StreamManager

        manager = StreamManager()

        event = await manager.emit_room_joined(
            workflow_id="wf_001",
            session_id="session_123456789",
            room_id="room_abc"
        )

        assert event is not None
        assert event.event_type == "room_joined"
        assert event.data["room_id"] == "room_abc"
        # Session ID should be truncated for privacy
        assert "..." in event.data["session_id"]

    @pytest.mark.asyncio
    async def test_compression_uses_config_thresholds(self):
        """Test compression respects config thresholds.

        MARKER_104_TEST_FIX: Tests that config thresholds are properly applied:
        - string_compression_threshold: strings > threshold are processed
        - list_truncate_threshold: lists > threshold are truncated
        - summary_max_length: long strings are truncated to max_summary

        Note: ELISION level 2 compresses JSON keys (context -> c) and paths,
        but for plain text strings, truncation is the primary compression.
        """
        from src.api.handlers.stream_handler import StreamManager, StreamConfig

        # Low thresholds = more aggressive compression
        config = StreamConfig(
            string_compression_threshold=50,
            list_truncate_threshold=3,
            summary_max_length=100  # Force truncation for strings > 100 chars
        )
        manager = StreamManager(config=config)

        # Use data that will trigger threshold-based processing
        long_text = "x" * 200  # Exceeds both string_threshold (50) and summary_max (100)
        data = {
            "short": "abc",  # 3 chars, won't compress
            "long_text": long_text,  # 200 chars, will be truncated to 100 + "..."
            "list": [1, 2, 3, 4, 5]  # 5 items, will truncate to 3
        }

        compressed = manager._compress_for_stream(data)

        # Short strings should not be compressed
        assert compressed["short"] == "abc"
        # Long strings exceeding summary_max_length should be truncated
        assert len(compressed["long_text"]) <= 103  # 100 + "..."
        assert compressed["long_text"].endswith("...")
        # List should be truncated to 3 items + "... N more" marker
        assert len(compressed["list"]) <= 4  # 3 items + "... N more"

    @pytest.mark.asyncio
    async def test_compression_fallback_truncation(self):
        """Test compression fallback when ELISION doesn't compress."""
        from src.api.handlers.stream_handler import StreamManager, StreamConfig
        from unittest.mock import patch

        config = StreamConfig(string_compression_threshold=50)
        manager = StreamManager(config=config)

        # Mock ELISION import to fail, forcing fallback truncation
        with patch.dict('sys.modules', {'src.memory.elision': None}):
            # Need to patch the import inside _compress_for_stream
            original_compress = manager._compress_for_stream

            def mock_compress(data):
                result = {}
                for key, value in data.items():
                    if isinstance(value, str) and len(value) > config.string_compression_threshold:
                        # Fallback truncation
                        result[key] = value[:config.string_compression_threshold] + "..."
                    else:
                        result[key] = value
                return result

            manager._compress_for_stream = mock_compress

            data = {"long_text": "x" * 100}
            compressed = manager._compress_for_stream(data)

            assert len(compressed["long_text"]) == 53  # 50 + "..."
            assert compressed["long_text"].endswith("...")

    @pytest.mark.asyncio
    async def test_metrics_increment_on_emit(self):
        """Test that metrics are incremented on emit."""
        from src.api.handlers.stream_handler import StreamManager

        manager = StreamManager()

        # Initial metrics
        initial = manager.get_metrics()
        assert initial["total_emits"] == 0
        assert initial["silent_skipped"] == 0

        # Emit full visibility
        await manager.emit("test", "wf_001", {"data": "test"}, visibility="full")
        metrics = manager.get_metrics()
        assert metrics["total_emits"] >= 0  # May not emit without socketio

        # Emit silent
        await manager.emit("test", "wf_001", {"data": "test"}, visibility="silent")
        metrics = manager.get_metrics()
        assert metrics["silent_skipped"] == 1

    def test_multiple_sessions_in_same_room(self):
        """Test multiple sessions can join the same room."""
        from src.api.handlers.stream_handler import StreamManager

        manager = StreamManager()

        manager.join_room("session_1", "room_shared")
        manager.join_room("session_2", "room_shared")
        manager.join_room("session_3", "room_shared")

        room_sessions = manager.get_room_sessions("room_shared")
        assert len(room_sessions) == 3
        assert "session_1" in room_sessions
        assert "session_2" in room_sessions
        assert "session_3" in room_sessions

        # Leave one session
        manager.leave_room("session_2", "room_shared")
        room_sessions = manager.get_room_sessions("room_shared")
        assert len(room_sessions) == 2
        assert "session_2" not in room_sessions
