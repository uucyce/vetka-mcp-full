"""
VETKA LangGraph Event Types for Socket.IO Streaming.

Phase 60.2: Real-time workflow visibility.

@status: active
@phase: 96
@depends: dataclasses, enum
@used_by: src.orchestration.langgraph_nodes, src.api.handlers
"""

from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class WorkflowEventType(str, Enum):
    """All possible workflow events"""

    # Lifecycle
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_ERROR = "workflow_error"

    # Node events
    NODE_STARTED = "node_started"
    NODE_PROGRESS = "node_progress"
    NODE_COMPLETED = "node_completed"
    NODE_ERROR = "node_error"

    # Evaluation (Phase 29)
    SCORE_COMPUTED = "score_computed"
    RETRY_DECISION = "retry_decision"

    # Learning (Phase 29)
    LEARNER_ANALYZING = "learner_analyzing"
    LEARNER_SUGGESTION = "learner_suggestion"

    # Artifacts
    ARTIFACT_CREATED = "artifact_created"

    # Checkpointing
    CHECKPOINT_SAVED = "checkpoint_saved"


@dataclass
class BaseEvent:
    """Base class for all events"""
    workflow_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WorkflowStartedEvent(BaseEvent):
    """Emitted when workflow begins"""
    context_preview: str = ""
    total_nodes: int = 7


@dataclass
class WorkflowCompletedEvent(BaseEvent):
    """Emitted when workflow completes"""
    final_score: float = 0.0
    total_retries: int = 0
    duration_ms: int = 0
    artifacts_count: int = 0
    status: str = "success"  # success, failed, max_retries


@dataclass
class NodeStartedEvent(BaseEvent):
    """Emitted when a node starts execution"""
    node: str = ""  # hostess, architect, pm, dev_qa_parallel, eval, learner, approval
    input_preview: str = ""
    retry_attempt: int = 0


@dataclass
class NodeProgressEvent(BaseEvent):
    """Emitted during node execution (for long-running nodes)"""
    node: str = ""
    progress_percent: int = 0
    status_message: str = ""


@dataclass
class NodeCompletedEvent(BaseEvent):
    """Emitted when a node completes"""
    node: str = ""
    duration_ms: int = 0
    output_preview: str = ""
    next_node: str = ""
    artifacts_created: int = 0


@dataclass
class NodeErrorEvent(BaseEvent):
    """Emitted when a node fails"""
    node: str = ""
    error_message: str = ""
    error_type: str = "unknown"
    recoverable: bool = True


@dataclass
class ScoreComputedEvent(BaseEvent):
    """Emitted when EvalAgent computes score (Phase 29)"""
    score: float = 0.0
    threshold: float = 0.75
    passed: bool = False
    feedback_preview: str = ""
    criteria_scores: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        self.passed = self.score >= self.threshold


@dataclass
class RetryDecisionEvent(BaseEvent):
    """Emitted when retry decision is made (Phase 29)"""
    will_retry: bool = False
    retry_count: int = 0
    max_retries: int = 3
    reason: str = ""

    def __post_init__(self):
        if not self.reason:
            if self.will_retry:
                self.reason = f"Score below threshold, attempt {self.retry_count + 1}/{self.max_retries}"
            else:
                self.reason = "Score passed threshold" if self.retry_count == 0 else "Max retries reached"


@dataclass
class LearnerAnalyzingEvent(BaseEvent):
    """Emitted when LearnerAgent starts analysis"""
    failure_category: str = ""
    analyzing_what: str = ""


@dataclass
class LearnerSuggestionEvent(BaseEvent):
    """Emitted when LearnerAgent provides suggestion"""
    failure_category: str = ""
    suggestion_preview: str = ""
    confidence: float = 0.0
    similar_failures_found: int = 0


@dataclass
class ArtifactCreatedEvent(BaseEvent):
    """Emitted when an artifact is created"""
    artifact_id: str = ""
    artifact_type: str = ""  # code, document, test, etc.
    artifact_name: str = ""
    size_bytes: int = 0
    created_by: str = ""  # which agent


@dataclass
class CheckpointSavedEvent(BaseEvent):
    """Emitted when checkpoint is saved"""
    checkpoint_id: str = ""
    state_size_bytes: int = 0
    backends: List[str] = field(default_factory=lambda: ['changelog'])


# ===========================
# EVENT EMITTER HELPER
# ===========================

class WorkflowEventEmitter:
    """
    Helper class to emit events via Socket.IO.
    Used by LangGraph nodes to broadcast progress.

    Supports python-socketio AsyncServer (not Flask-SocketIO).
    """

    def __init__(self, sio=None, namespace: str = '/workflow'):
        """
        Initialize event emitter.

        Args:
            sio: python-socketio AsyncServer instance
            namespace: Socket.IO namespace for workflow events
        """
        self.sio = sio
        self.namespace = namespace
        self.enabled = sio is not None

    async def emit(self, event: BaseEvent):
        """Emit event to all clients in workflow room"""
        if not self.enabled:
            return

        event_type = self._get_event_type(event)
        event_data = event.to_dict()

        try:
            # python-socketio uses 'to' parameter for room targeting
            await self.sio.emit(
                event_type,
                event_data,
                namespace=self.namespace,
                to=event.workflow_id  # Room = workflow_id for targeted delivery
            )
        except Exception as e:
            print(f"[EventEmitter] Failed to emit {event_type}: {e}")

    def emit_sync(self, event: BaseEvent):
        """
        Synchronous emit for non-async contexts.
        Note: This will schedule the emit but not wait for it.
        """
        if not self.enabled:
            return

        import asyncio

        event_type = self._get_event_type(event)
        event_data = event.to_dict()

        try:
            # Try to get running loop and schedule
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.sio.emit(
                    event_type,
                    event_data,
                    namespace=self.namespace,
                    to=event.workflow_id
                ))
            else:
                # Fallback: run in new loop
                loop.run_until_complete(self.sio.emit(
                    event_type,
                    event_data,
                    namespace=self.namespace,
                    to=event.workflow_id
                ))
        except Exception as e:
            print(f"[EventEmitter] Failed to emit {event_type}: {e}")

    def _get_event_type(self, event: BaseEvent) -> str:
        """Map event class to event type string"""
        mapping = {
            WorkflowStartedEvent: WorkflowEventType.WORKFLOW_STARTED,
            WorkflowCompletedEvent: WorkflowEventType.WORKFLOW_COMPLETED,
            NodeStartedEvent: WorkflowEventType.NODE_STARTED,
            NodeProgressEvent: WorkflowEventType.NODE_PROGRESS,
            NodeCompletedEvent: WorkflowEventType.NODE_COMPLETED,
            NodeErrorEvent: WorkflowEventType.NODE_ERROR,
            ScoreComputedEvent: WorkflowEventType.SCORE_COMPUTED,
            RetryDecisionEvent: WorkflowEventType.RETRY_DECISION,
            LearnerAnalyzingEvent: WorkflowEventType.LEARNER_ANALYZING,
            LearnerSuggestionEvent: WorkflowEventType.LEARNER_SUGGESTION,
            ArtifactCreatedEvent: WorkflowEventType.ARTIFACT_CREATED,
            CheckpointSavedEvent: WorkflowEventType.CHECKPOINT_SAVED,
        }
        return mapping.get(type(event), WorkflowEventType.NODE_PROGRESS).value
