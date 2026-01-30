"""
Tests for workflow event types and emitter
Phase 60.2: Socket.IO Real-time Streaming

@file test_workflow_events.py
@status ACTIVE
@phase Phase 60.2
"""

import pytest
from datetime import datetime

from src.orchestration.event_types import (
    WorkflowEventType,
    BaseEvent,
    WorkflowStartedEvent,
    WorkflowCompletedEvent,
    NodeStartedEvent,
    NodeCompletedEvent,
    NodeErrorEvent,
    NodeProgressEvent,
    ScoreComputedEvent,
    RetryDecisionEvent,
    LearnerAnalyzingEvent,
    LearnerSuggestionEvent,
    ArtifactCreatedEvent,
    CheckpointSavedEvent,
    WorkflowEventEmitter
)


class TestEventTypes:
    """Test event dataclasses"""

    def test_base_event_has_timestamp(self):
        """Base event should auto-generate timestamp"""
        event = NodeStartedEvent(workflow_id="test-123", node="hostess")
        assert event.timestamp is not None
        # Check timestamp is valid ISO format
        datetime.fromisoformat(event.timestamp)

    def test_node_started_event(self):
        """Test NodeStartedEvent creation and serialization"""
        event = NodeStartedEvent(
            workflow_id="test-123",
            node="hostess",
            input_preview="Hello world",
            retry_attempt=0
        )

        assert event.workflow_id == "test-123"
        assert event.node == "hostess"
        assert event.input_preview == "Hello world"
        assert event.retry_attempt == 0

        data = event.to_dict()
        assert 'workflow_id' in data
        assert 'node' in data
        assert 'timestamp' in data
        assert data['node'] == 'hostess'

    def test_node_completed_event(self):
        """Test NodeCompletedEvent with all fields"""
        event = NodeCompletedEvent(
            workflow_id="test-123",
            node="architect",
            duration_ms=1500,
            output_preview="Task decomposition complete",
            next_node="pm",
            artifacts_created=3
        )

        assert event.duration_ms == 1500
        assert event.next_node == "pm"
        assert event.artifacts_created == 3

        data = event.to_dict()
        assert data['duration_ms'] == 1500

    def test_node_error_event(self):
        """Test NodeErrorEvent"""
        event = NodeErrorEvent(
            workflow_id="test-123",
            node="dev_qa_parallel",
            error_message="API timeout",
            error_type="TimeoutError",
            recoverable=True
        )

        assert event.error_message == "API timeout"
        assert event.error_type == "TimeoutError"
        assert event.recoverable is True

    def test_score_computed_event_pass(self):
        """Test ScoreComputedEvent when score passes threshold"""
        event = ScoreComputedEvent(
            workflow_id="test-123",
            score=0.82,
            threshold=0.75
        )

        assert event.passed is True
        assert event.score == 0.82

    def test_score_computed_event_fail(self):
        """Test ScoreComputedEvent when score fails threshold"""
        event = ScoreComputedEvent(
            workflow_id="test-123",
            score=0.65,
            threshold=0.75
        )

        assert event.passed is False

    def test_retry_decision_event_will_retry(self):
        """Test RetryDecisionEvent when retry is needed"""
        event = RetryDecisionEvent(
            workflow_id="test-123",
            will_retry=True,
            retry_count=1,
            max_retries=3
        )

        assert event.will_retry is True
        assert "attempt 2/3" in event.reason

    def test_retry_decision_event_passed(self):
        """Test RetryDecisionEvent when passed (no retry)"""
        event = RetryDecisionEvent(
            workflow_id="test-123",
            will_retry=False,
            retry_count=0,
            max_retries=3
        )

        assert event.will_retry is False
        assert "passed" in event.reason.lower()

    def test_retry_decision_event_max_retries(self):
        """Test RetryDecisionEvent when max retries reached"""
        event = RetryDecisionEvent(
            workflow_id="test-123",
            will_retry=False,
            retry_count=3,
            max_retries=3
        )

        assert "max retries" in event.reason.lower()

    def test_learner_suggestion_event(self):
        """Test LearnerSuggestionEvent"""
        event = LearnerSuggestionEvent(
            workflow_id="test-123",
            failure_category="incomplete_implementation",
            suggestion_preview="Add error handling for edge cases",
            confidence=0.85,
            similar_failures_found=3
        )

        assert event.failure_category == "incomplete_implementation"
        assert event.confidence == 0.85

    def test_workflow_completed_event(self):
        """Test WorkflowCompletedEvent"""
        event = WorkflowCompletedEvent(
            workflow_id="test-123",
            final_score=0.88,
            total_retries=1,
            duration_ms=45000,
            artifacts_count=5,
            status="success"
        )

        data = event.to_dict()
        assert data['final_score'] == 0.88
        assert data['total_retries'] == 1
        assert data['duration_ms'] == 45000
        assert data['status'] == "success"

    def test_artifact_created_event(self):
        """Test ArtifactCreatedEvent"""
        event = ArtifactCreatedEvent(
            workflow_id="test-123",
            artifact_id="art-456",
            artifact_type="code",
            artifact_name="calculator.py",
            size_bytes=2048,
            created_by="dev"
        )

        assert event.artifact_type == "code"
        assert event.size_bytes == 2048

    def test_checkpoint_saved_event(self):
        """Test CheckpointSavedEvent with backends"""
        event = CheckpointSavedEvent(
            workflow_id="test-123",
            checkpoint_id="cp-789",
            state_size_bytes=4096,
            backends=['changelog', 'qdrant']
        )

        assert 'changelog' in event.backends
        assert event.state_size_bytes == 4096


class TestEventEmitter:
    """Test WorkflowEventEmitter"""

    def test_emitter_without_socketio(self):
        """Emitter should not fail without socketio"""
        emitter = WorkflowEventEmitter(sio=None)

        event = NodeStartedEvent(
            workflow_id="test",
            node="hostess"
        )

        # Should not raise
        emitter.emit_sync(event)
        assert emitter.enabled is False

    def test_emitter_enabled_with_socketio(self):
        """Emitter should be enabled with socketio"""
        # Mock socketio
        class MockSocketIO:
            async def emit(self, *args, **kwargs):
                pass

        emitter = WorkflowEventEmitter(sio=MockSocketIO())
        assert emitter.enabled is True

    def test_event_type_mapping(self):
        """Test event class to type string mapping"""
        emitter = WorkflowEventEmitter()

        # Test various events
        test_cases = [
            (NodeStartedEvent(workflow_id="t", node="h"), "node_started"),
            (NodeCompletedEvent(workflow_id="t", node="h"), "node_completed"),
            (ScoreComputedEvent(workflow_id="t", score=0.8), "score_computed"),
            (RetryDecisionEvent(workflow_id="t", will_retry=True, retry_count=1), "retry_decision"),
            (LearnerSuggestionEvent(workflow_id="t", failure_category="x", suggestion_preview="y"), "learner_suggestion"),
            (WorkflowStartedEvent(workflow_id="t"), "workflow_started"),
            (WorkflowCompletedEvent(workflow_id="t"), "workflow_completed"),
        ]

        for event, expected_type in test_cases:
            event_type = emitter._get_event_type(event)
            assert event_type == expected_type, f"Expected {expected_type}, got {event_type}"


class TestWorkflowEventTypes:
    """Test WorkflowEventType enum"""

    def test_all_event_types_defined(self):
        """All expected event types should be defined"""
        expected_types = [
            'workflow_started',
            'workflow_completed',
            'workflow_error',
            'node_started',
            'node_progress',
            'node_completed',
            'node_error',
            'score_computed',
            'retry_decision',
            'learner_analyzing',
            'learner_suggestion',
            'artifact_created',
            'checkpoint_saved',
        ]

        actual_types = [e.value for e in WorkflowEventType]

        for expected in expected_types:
            assert expected in actual_types, f"Missing event type: {expected}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
