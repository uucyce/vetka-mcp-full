"""
VETKA Phase 104.7 - Stream Visibility Handler

MARKER_104_STREAM_HANDLER

Manages real-time streaming with visibility control.
Integrates with Socket.IO for event emission and ELISION for compression.

Socket.IO Event Types:
- pipeline_progress: Overall pipeline status updates
- subtask_start: When a subtask/agent begins work
- subtask_complete: When a subtask/agent finishes
- artifact_staged: New artifact staged for review
- stm_update: Short-term memory state changes
- research_trigger: Research/semantic search initiated

Visibility Levels:
- FULL: Complete data, no compression - for critical events
- SUMMARY: Compressed/summarized - default for most events
- SILENT: No emit - for internal/debug events

@file stream_handler.py
@status ACTIVE
@phase 104.7
@depends socketio, elision, typing, dataclasses
"""

import logging
import time
from collections import deque
from typing import Dict, Any, Optional, List, Callable, Deque
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# STREAM VISIBILITY LEVELS
# =============================================================================

class StreamLevel(Enum):
    """Visibility levels for stream events."""
    FULL = "full"        # Complete data, no compression
    SUMMARY = "summary"  # Compressed/summarized (default)
    SILENT = "silent"    # No emit, internal only


# =============================================================================
# STREAM EVENT TYPES
# =============================================================================

class StreamEventType(Enum):
    """Standard Socket.IO event types for VETKA streams."""
    # Pipeline events
    PIPELINE_PROGRESS = "pipeline_progress"
    WORKFLOW_STATUS = "workflow_status"
    WORKFLOW_RESULT = "workflow_result"

    # Subtask events
    SUBTASK_START = "subtask_start"
    SUBTASK_COMPLETE = "subtask_complete"
    SUBTASK_ERROR = "subtask_error"

    # Artifact events
    ARTIFACT_STAGED = "artifact_staged"
    ARTIFACT_APPLIED = "artifact_applied"
    ARTIFACT_REJECTED = "artifact_rejected"

    # Memory events
    STM_UPDATE = "stm_update"
    CAM_UPDATE = "cam_update"
    MEMORY_COMPRESSED = "memory_compressed"

    # Research events
    RESEARCH_TRIGGER = "research_trigger"
    SEMANTIC_SEARCH = "semantic_search"
    ARC_SUGGESTIONS = "arc_suggestions"

    # Group chat events
    GROUP_STREAM_START = "group_stream_start"
    GROUP_STREAM_END = "group_stream_end"
    GROUP_TYPING = "group_typing"
    # MARKER_156.VOICE.S1_STREAM_ENUMS: Voice-specific group events (contract scaffold).
    GROUP_VOICE_STREAM_START = "group_voice_stream_start"
    GROUP_VOICE_STREAM_CHUNK = "group_voice_stream_chunk"
    GROUP_VOICE_STREAM_END = "group_voice_stream_end"
    GROUP_VOICE_MESSAGE = "group_voice_message"

    # Approval events
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_RESPONSE = "approval_response"

    # LangGraph events
    LANGGRAPH_PROGRESS = "langgraph_progress"

    # MARKER_104_GROK_IMPROVEMENTS: Phase 104.8 - Added by Grok review
    # Voice/Jarvis events
    VOICE_TRANSCRIPT = "voice_transcript"       # STT partial/final transcription
    JARVIS_INTERRUPT = "jarvis_interrupt"       # User interrupt during voice
    JARVIS_PREDICTION = "jarvis_prediction"     # T9-like draft response

    # MARKER_104_ARTIFACT_EVENT: Phase 104.9 - Artifact approval workflow
    ARTIFACT_APPROVAL = "artifact_approval"     # Request user approval for artifact

    # Error/System events
    STREAM_ERROR = "stream_error"               # Generic stream error
    ROOM_JOINED = "room_joined"                 # User joined room
    ROOM_LEFT = "room_left"                     # User left room


# =============================================================================
# STREAM EVENT DATACLASS
# =============================================================================

@dataclass
class StreamEvent:
    """
    Structured stream event with visibility control.

    Attributes:
        event_type: Type of event (from StreamEventType or custom string)
        workflow_id: Associated workflow/session ID
        data: Event payload data
        visibility: Visibility level (FULL, SUMMARY, SILENT)
        priority: Higher = more important (affects UI ordering)
        compress: Whether to apply ELISION compression
        room: Socket.IO room to emit to (optional)
        metadata: Additional metadata for debugging
    """
    event_type: str
    workflow_id: str
    data: Dict[str, Any]
    visibility: StreamLevel = StreamLevel.SUMMARY
    priority: int = 0
    compress: bool = True
    room: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_emit(self) -> Dict[str, Any]:
        """
        Prepare event for Socket.IO emit.

        Returns:
            Dict formatted for Socket.IO emission
        """
        return {
            "type": self.event_type,
            "workflow_id": self.workflow_id,
            "data": self.data,
            "visibility": self.visibility.value,
            "priority": self.priority,
            "timestamp": self.timestamp,
            "metadata": self.metadata if self.metadata else None,
        }

    def to_buffer(self) -> Dict[str, Any]:
        """
        Prepare event for buffer storage (includes more detail).

        Returns:
            Dict with full event information
        """
        return {
            "type": self.event_type,
            "workflow_id": self.workflow_id,
            "data": self.data,
            "visibility": self.visibility.value,
            "priority": self.priority,
            "timestamp": self.timestamp,
            "room": self.room,
            "compressed": self.compress,
            "metadata": self.metadata,
        }


# =============================================================================
# STREAM MANAGER
# =============================================================================

@dataclass
class StreamConfig:
    """
    MARKER_104_GROK_IMPROVEMENTS: Configurable stream settings.

    Phase 104.8: Centralized configuration for compression thresholds.
    """
    string_compression_threshold: int = 200   # Compress strings longer than this
    list_truncate_threshold: int = 10         # Truncate lists longer than this
    summary_max_length: int = 500             # Max length for summary content
    enable_metrics: bool = True               # Track emit metrics


class StreamManager:
    """
    Manages stream visibility and emission.

    Provides centralized control over Socket.IO event emission with:
    - Visibility-based filtering (FULL, SUMMARY, SILENT)
    - ELISION compression for SUMMARY level
    - Event buffering for history/replay
    - Priority-based event handling
    - Room management and cleanup (Phase 104.8)
    - Configurable compression thresholds (Phase 104.8)

    Usage:
        manager = StreamManager(socketio, default_visibility="summary")
        await manager.emit("subtask_start", workflow_id, {"agent": "Dev"}, room=room)

        # Or use typed events:
        await manager.emit_subtask_start(workflow_id, "Dev", "gpt-4", room=room)
    """

    def __init__(
        self,
        socketio=None,
        default_visibility: str = "summary",
        max_buffer: int = 100,
        enable_compression: bool = True,
        config: Optional[StreamConfig] = None
    ):
        """
        Initialize StreamManager.

        Args:
            socketio: AsyncServer instance (optional, can be set later)
            default_visibility: Default visibility level ("full", "summary", "silent")
            max_buffer: Maximum events to keep in buffer
            enable_compression: Whether to enable ELISION compression
            config: Optional StreamConfig for custom thresholds (Phase 104.8)
        """
        self.socketio = socketio
        self.default_visibility = StreamLevel(default_visibility)
        # MARKER_104_BUFFER: Use deque for O(1) append/eviction instead of list with O(n) pop(0)
        self._buffer: Deque[StreamEvent] = deque(maxlen=max_buffer)
        self._max_buffer = max_buffer
        self._enable_compression = enable_compression
        self._config = config or StreamConfig()
        self._compression_threshold = self._config.string_compression_threshold
        self._listeners: Dict[str, List[Callable]] = {}

        # MARKER_104_GROK_IMPROVEMENTS: Room management (Phase 104.8)
        self._active_rooms: Dict[str, set] = {}  # room_id -> set of session_ids
        self._session_rooms: Dict[str, set] = {}  # session_id -> set of room_ids

        # MARKER_104_GROK_IMPROVEMENTS: Metrics tracking (Phase 104.8)
        self._metrics = {
            "total_emits": 0,
            "compressed_emits": 0,
            "silent_skipped": 0,
            "errors": 0,
            "bytes_saved": 0,
        }

        logger.info(f"[StreamManager] Initialized (visibility={default_visibility}, buffer={max_buffer})")

    def set_socketio(self, socketio) -> None:
        """Set the Socket.IO instance (for late binding)."""
        self.socketio = socketio
        logger.debug("[StreamManager] Socket.IO instance set")

    # =========================================================================
    # ROOM MANAGEMENT - MARKER_104_GROK_IMPROVEMENTS (Phase 104.8)
    # =========================================================================

    def join_room(self, session_id: str, room_id: str) -> None:
        """
        Track session joining a room.

        Args:
            session_id: Socket session ID
            room_id: Room to join
        """
        if room_id not in self._active_rooms:
            self._active_rooms[room_id] = set()
        self._active_rooms[room_id].add(session_id)

        if session_id not in self._session_rooms:
            self._session_rooms[session_id] = set()
        self._session_rooms[session_id].add(room_id)

        logger.debug(f"[StreamManager] Session {session_id[:8]}... joined room {room_id}")

    def leave_room(self, session_id: str, room_id: str) -> None:
        """
        Track session leaving a room.

        Args:
            session_id: Socket session ID
            room_id: Room to leave
        """
        if room_id in self._active_rooms:
            self._active_rooms[room_id].discard(session_id)
            if not self._active_rooms[room_id]:
                del self._active_rooms[room_id]

        if session_id in self._session_rooms:
            self._session_rooms[session_id].discard(room_id)
            if not self._session_rooms[session_id]:
                del self._session_rooms[session_id]

        logger.debug(f"[StreamManager] Session {session_id[:8]}... left room {room_id}")

    def cleanup_session(self, session_id: str) -> List[str]:
        """
        Cleanup all rooms for a disconnected session.

        Args:
            session_id: Socket session ID that disconnected

        Returns:
            List of room_ids the session was in
        """
        rooms = list(self._session_rooms.get(session_id, []))
        for room_id in rooms:
            self.leave_room(session_id, room_id)
        logger.info(f"[StreamManager] Cleaned up session {session_id[:8]}... from {len(rooms)} rooms")
        return rooms

    def get_room_sessions(self, room_id: str) -> set:
        """Get all sessions in a room."""
        return self._active_rooms.get(room_id, set()).copy()

    def get_session_rooms(self, session_id: str) -> set:
        """Get all rooms a session is in."""
        return self._session_rooms.get(session_id, set()).copy()

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get stream metrics for monitoring.

        Returns:
            Dict with emit counts, compression stats, errors
        """
        return {
            **self._metrics,
            "active_rooms": len(self._active_rooms),
            "active_sessions": len(self._session_rooms),
            "buffer_size": len(self._buffer),
        }

    async def emit(
        self,
        event_type: str,
        workflow_id: str,
        data: Dict[str, Any],
        room: Optional[str] = None,
        visibility: Optional[str] = None,
        compress: bool = True,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[StreamEvent]:
        """
        Emit event with visibility control.

        Args:
            event_type: Event type string (or StreamEventType enum value)
            workflow_id: Associated workflow ID
            data: Event payload
            room: Socket.IO room to emit to
            visibility: Override visibility level
            compress: Whether to compress data
            priority: Event priority (higher = more important)
            metadata: Additional metadata

        Returns:
            StreamEvent if emitted, None if silent
        """
        # Handle enum event types
        if isinstance(event_type, StreamEventType):
            event_type = event_type.value

        # Determine visibility level
        level = StreamLevel(visibility) if visibility else self.default_visibility

        # Silent events: log only, no emit
        if level == StreamLevel.SILENT:
            logger.debug(f"[Stream] Silent event: {event_type} (workflow={workflow_id})")
            if self._config.enable_metrics:
                self._metrics["silent_skipped"] += 1
            return None

        # Compress data if needed
        processed_data = data
        original_size = 0
        compressed_size = 0
        if compress and level == StreamLevel.SUMMARY and self._enable_compression:
            if self._config.enable_metrics:
                import json
                original_size = len(json.dumps(data, default=str))
            processed_data = self._compress_for_stream(data)
            if self._config.enable_metrics:
                compressed_size = len(json.dumps(processed_data, default=str))
                self._metrics["compressed_emits"] += 1
                self._metrics["bytes_saved"] += max(0, original_size - compressed_size)

        # Create event object
        event = StreamEvent(
            event_type=event_type,
            workflow_id=workflow_id,
            data=processed_data,
            visibility=level,
            priority=priority,
            compress=compress,
            room=room,
            metadata=metadata or {},
        )

        # Emit via Socket.IO
        if self.socketio and room:
            try:
                await self.socketio.emit(event_type, event.to_emit(), room=room)
                logger.debug(f"[Stream] Emitted {event_type} to room={room}")
                if self._config.enable_metrics:
                    self._metrics["total_emits"] += 1
            except Exception as e:
                logger.error(f"[Stream] Emit failed: {e}")
                if self._config.enable_metrics:
                    self._metrics["errors"] += 1
        elif self.socketio:
            # Broadcast if no room specified
            try:
                await self.socketio.emit(event_type, event.to_emit())
                logger.debug(f"[Stream] Broadcast {event_type}")
                if self._config.enable_metrics:
                    self._metrics["total_emits"] += 1
            except Exception as e:
                logger.error(f"[Stream] Broadcast failed: {e}")
                if self._config.enable_metrics:
                    self._metrics["errors"] += 1

        # Notify local listeners
        await self._notify_listeners(event)

        # Buffer for history - deque with maxlen handles eviction automatically (O(1))
        self._buffer.append(event)

        return event

    def _compress_for_stream(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compress data for SUMMARY visibility level.

        Uses ELISION compression for efficient token usage.
        MARKER_104_GROK_IMPROVEMENTS: Uses configurable thresholds (Phase 104.8).

        Args:
            data: Data dictionary to compress

        Returns:
            Compressed data dictionary
        """
        try:
            from src.memory.elision import get_elision_compressor
            compressor = get_elision_compressor()
        except ImportError:
            # Fallback: simple truncation
            compressor = None

        result = {}
        string_threshold = self._config.string_compression_threshold
        list_threshold = self._config.list_truncate_threshold
        max_summary = self._config.summary_max_length

        for key, value in data.items():
            if isinstance(value, str) and len(value) > string_threshold:
                if compressor:
                    # Use ELISION compression
                    compressed = compressor.compress(value, level=2)
                    result[key] = compressed.compressed
                    # Further truncate if still too long for summary
                    if len(result[key]) > max_summary:
                        result[key] = result[key][:max_summary] + "..."
                else:
                    # Fallback: truncate with ellipsis
                    result[key] = value[:string_threshold] + "..."
            elif isinstance(value, dict):
                result[key] = self._compress_for_stream(value)
            elif isinstance(value, list) and len(value) > list_threshold:
                # Truncate long lists (configurable threshold)
                result[key] = value[:list_threshold] + [f"... ({len(value) - list_threshold} more)"]
            else:
                result[key] = value

        return result

    # =========================================================================
    # TYPED EVENT EMITTERS - MARKER_104_STREAM_HANDLER
    # =========================================================================

    async def emit_pipeline_progress(
        self,
        workflow_id: str,
        stage: str,
        progress: float,
        message: str = "",
        room: Optional[str] = None
    ) -> Optional[StreamEvent]:
        """Emit pipeline progress update."""
        return await self.emit(
            StreamEventType.PIPELINE_PROGRESS,
            workflow_id,
            {
                "stage": stage,
                "progress": progress,
                "message": message,
            },
            room=room,
            visibility="full",  # Progress updates are important
            priority=5,
        )

    async def emit_subtask_start(
        self,
        workflow_id: str,
        agent: str,
        model: str,
        task_description: str = "",
        room: Optional[str] = None
    ) -> Optional[StreamEvent]:
        """Emit subtask/agent start event."""
        return await self.emit(
            StreamEventType.SUBTASK_START,
            workflow_id,
            {
                "agent": agent,
                "model": model,
                "description": task_description,
                "started_at": time.time(),
            },
            room=room,
            visibility="full",
            priority=3,
        )

    async def emit_subtask_complete(
        self,
        workflow_id: str,
        agent: str,
        output: str,
        duration: float,
        success: bool = True,
        room: Optional[str] = None
    ) -> Optional[StreamEvent]:
        """Emit subtask/agent completion event."""
        return await self.emit(
            StreamEventType.SUBTASK_COMPLETE,
            workflow_id,
            {
                "agent": agent,
                "output": output,
                "duration": duration,
                "success": success,
                "completed_at": time.time(),
            },
            room=room,
            visibility="summary",  # Output can be long, compress it
            compress=True,
            priority=3,
        )

    async def emit_artifact_staged(
        self,
        workflow_id: str,
        agent: str,
        artifact_count: int,
        task_ids: List[str],
        qa_score: float,
        room: Optional[str] = None
    ) -> Optional[StreamEvent]:
        """Emit artifact staging notification."""
        return await self.emit(
            StreamEventType.ARTIFACT_STAGED,
            workflow_id,
            {
                "agent": agent,
                "count": artifact_count,
                "task_ids": task_ids,
                "qa_score": qa_score,
            },
            room=room,
            visibility="full",  # Artifact events are important
            priority=4,
        )

    async def emit_stm_update(
        self,
        workflow_id: str,
        stm_state: Dict[str, Any],
        room: Optional[str] = None
    ) -> Optional[StreamEvent]:
        """Emit short-term memory state update."""
        return await self.emit(
            StreamEventType.STM_UPDATE,
            workflow_id,
            stm_state,
            room=room,
            visibility="summary",  # STM updates can be compressed
            compress=True,
            priority=1,
        )

    async def emit_research_trigger(
        self,
        workflow_id: str,
        query: str,
        sources: List[str],
        room: Optional[str] = None
    ) -> Optional[StreamEvent]:
        """Emit research/semantic search trigger."""
        return await self.emit(
            StreamEventType.RESEARCH_TRIGGER,
            workflow_id,
            {
                "query": query,
                "sources": sources,
                "triggered_at": time.time(),
            },
            room=room,
            visibility="summary",
            priority=2,
        )

    async def emit_workflow_status(
        self,
        workflow_id: str,
        step: str,
        status: str,
        extra: Optional[Dict[str, Any]] = None,
        room: Optional[str] = None
    ) -> Optional[StreamEvent]:
        """
        Emit workflow status (compatible with orchestrator _emit_status).

        This matches the existing pattern in orchestrator_with_elisya.py
        """
        data = {
            "step": step,
            "status": status,
            "timestamp": time.time(),
        }
        if extra:
            data.update(extra)

        return await self.emit(
            StreamEventType.WORKFLOW_STATUS,
            workflow_id,
            data,
            room=room,
            visibility="full",
            priority=5,
        )

    # =========================================================================
    # VOICE/JARVIS EVENTS - MARKER_104_GROK_IMPROVEMENTS (Phase 104.8)
    # =========================================================================

    async def emit_voice_transcript(
        self,
        workflow_id: str,
        transcript: str,
        is_final: bool = False,
        confidence: float = 1.0,
        room: Optional[str] = None
    ) -> Optional[StreamEvent]:
        """Emit voice transcription (partial or final)."""
        return await self.emit(
            StreamEventType.VOICE_TRANSCRIPT,
            workflow_id,
            {
                "transcript": transcript,
                "is_final": is_final,
                "confidence": confidence,
            },
            room=room,
            visibility="full",  # Voice transcripts are important
            priority=6,
        )

    async def emit_jarvis_interrupt(
        self,
        workflow_id: str,
        reason: str = "user_interrupt",
        room: Optional[str] = None
    ) -> Optional[StreamEvent]:
        """Emit Jarvis interrupt signal (user spoke during generation)."""
        return await self.emit(
            StreamEventType.JARVIS_INTERRUPT,
            workflow_id,
            {
                "reason": reason,
                "timestamp": time.time(),
            },
            room=room,
            visibility="full",
            priority=10,  # High priority - interrupts are urgent
        )

    async def emit_jarvis_prediction(
        self,
        workflow_id: str,
        partial_input: str,
        predicted_response: str,
        confidence: float = 0.0,
        room: Optional[str] = None
    ) -> Optional[StreamEvent]:
        """
        Emit Jarvis T9-like prediction (draft response based on first tokens).

        MARKER_104_JARVIS_T9: Phase 104.8 - Grok's prediction idea.
        """
        return await self.emit(
            StreamEventType.JARVIS_PREDICTION,
            workflow_id,
            {
                "partial_input": partial_input,
                "predicted_response": predicted_response,
                "confidence": confidence,
                "is_draft": True,
            },
            room=room,
            visibility="summary",  # Can be compressed
            compress=True,
            priority=4,
        )

    async def emit_stream_error(
        self,
        workflow_id: str,
        error: str,
        error_type: str = "generic",
        recoverable: bool = True,
        room: Optional[str] = None
    ) -> Optional[StreamEvent]:
        """Emit stream error event."""
        return await self.emit(
            StreamEventType.STREAM_ERROR,
            workflow_id,
            {
                "error": error,
                "error_type": error_type,
                "recoverable": recoverable,
                "timestamp": time.time(),
            },
            room=room,
            visibility="full",
            priority=8,
        )

    async def emit_room_joined(
        self,
        workflow_id: str,
        session_id: str,
        room_id: str,
        room: Optional[str] = None
    ) -> Optional[StreamEvent]:
        """Emit room join notification."""
        return await self.emit(
            StreamEventType.ROOM_JOINED,
            workflow_id,
            {
                "session_id": session_id[:8] + "...",  # Truncate for privacy
                "room_id": room_id,
            },
            room=room or room_id,
            visibility="full",
            priority=2,
        )

    async def emit_room_left(
        self,
        workflow_id: str,
        session_id: str,
        room_id: str,
        room: Optional[str] = None
    ) -> Optional[StreamEvent]:
        """Emit room leave notification."""
        return await self.emit(
            StreamEventType.ROOM_LEFT,
            workflow_id,
            {
                "session_id": session_id[:8] + "...",
                "room_id": room_id,
            },
            room=room or room_id,
            visibility="full",
            priority=2,
        )

    # =========================================================================
    # ARTIFACT APPROVAL - MARKER_104_ARTIFACT_EVENT (Phase 104.9)
    # =========================================================================

    async def emit_artifact_approval(
        self,
        workflow_id: str,
        path: str,
        name: str,
        size: int,
        level: str = "L1",  # L1=yes/no, L2=edit, L3=reject
        namespace: str = "/vetka"
    ) -> Optional[StreamEvent]:
        """
        Emit artifact approval request to UI.

        MARKER_104_ARTIFACT_EVENT: Phase 104.9 - Artifact approval workflow.

        Approval levels:
        - L1: Simple yes/no approval
        - L2: Allows editing before approval
        - L3: Reject with reason

        Args:
            workflow_id: Associated workflow ID
            path: File path for the artifact
            name: Artifact name/identifier
            size: Content length in bytes
            level: Approval level (L1, L2, L3)
            namespace: Socket.IO namespace (default /vetka)

        Returns:
            StreamEvent if emitted, None if silent
        """
        return await self.emit(
            StreamEventType.ARTIFACT_APPROVAL,
            workflow_id,
            {
                "path": path,
                "name": name,
                "size": size,
                "level": level,
                "workflow_id": workflow_id,
                "timestamp": time.time(),
            },
            room=namespace,
            visibility="full",  # Approval requests are important
            priority=7,  # High priority - requires user action
        )

    # =========================================================================
    # BUFFER AND HISTORY
    # =========================================================================

    def get_buffer(
        self,
        workflow_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get buffered events.

        Args:
            workflow_id: Filter by workflow ID
            event_type: Filter by event type
            limit: Maximum events to return

        Returns:
            List of event dictionaries
        """
        # Convert deque to list for filtering and slicing operations
        filtered: List[StreamEvent] = list(self._buffer)

        if workflow_id:
            filtered = [e for e in filtered if e.workflow_id == workflow_id]

        if event_type:
            if isinstance(event_type, StreamEventType):
                event_type = event_type.value
            filtered = [e for e in filtered if e.event_type == event_type]

        return [e.to_buffer() for e in filtered[-limit:]]

    def clear_buffer(self, workflow_id: Optional[str] = None) -> int:
        """
        Clear event buffer.

        Args:
            workflow_id: Only clear events for this workflow (optional)

        Returns:
            Number of events cleared
        """
        if workflow_id:
            original_len = len(self._buffer)
            # Filter deque by creating new one with retained events
            retained = deque(
                (e for e in self._buffer if e.workflow_id != workflow_id),
                maxlen=self._max_buffer
            )
            cleared_count = original_len - len(retained)
            self._buffer = retained
            return cleared_count
        else:
            count = len(self._buffer)
            self._buffer.clear()
            return count

    # =========================================================================
    # LISTENER REGISTRATION
    # =========================================================================

    def add_listener(self, event_type: str, callback: Callable) -> None:
        """
        Register a listener for an event type.

        Args:
            event_type: Event type to listen for
            callback: Async callback function(event: StreamEvent)
        """
        if isinstance(event_type, StreamEventType):
            event_type = event_type.value

        if event_type not in self._listeners:
            self._listeners[event_type] = []

        self._listeners[event_type].append(callback)
        logger.debug(f"[StreamManager] Added listener for {event_type}")

    def remove_listener(self, event_type: str, callback: Callable) -> bool:
        """
        Remove a listener for an event type.

        Returns:
            True if listener was found and removed
        """
        if isinstance(event_type, StreamEventType):
            event_type = event_type.value

        if event_type in self._listeners:
            try:
                self._listeners[event_type].remove(callback)
                return True
            except ValueError:
                return False
        return False

    async def _notify_listeners(self, event: StreamEvent) -> None:
        """Notify all registered listeners for an event."""
        listeners = self._listeners.get(event.event_type, [])
        for callback in listeners:
            try:
                if callable(callback):
                    result = callback(event)
                    if hasattr(result, '__await__'):
                        await result
            except Exception as e:
                logger.error(f"[StreamManager] Listener error for {event.event_type}: {e}")


# =============================================================================
# FACTORY AND SINGLETON
# =============================================================================

_stream_manager_instance: Optional[StreamManager] = None


def get_stream_manager(socketio=None) -> StreamManager:
    """
    Get or create singleton StreamManager instance.

    Args:
        socketio: Optional Socket.IO instance to set

    Returns:
        StreamManager instance
    """
    global _stream_manager_instance

    if _stream_manager_instance is None:
        _stream_manager_instance = StreamManager(socketio)
    elif socketio and _stream_manager_instance.socketio is None:
        _stream_manager_instance.set_socketio(socketio)

    return _stream_manager_instance


def create_stream_manager(socketio=None, **kwargs) -> StreamManager:
    """
    Create a new StreamManager instance (not singleton).

    Use this when you need a separate manager with different config.

    Args:
        socketio: Socket.IO instance
        **kwargs: Additional StreamManager constructor arguments

    Returns:
        New StreamManager instance
    """
    return StreamManager(socketio, **kwargs)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def emit_stream_event(
    event_type: str,
    workflow_id: str,
    data: Dict[str, Any],
    room: Optional[str] = None,
    visibility: str = "summary"
) -> Optional[StreamEvent]:
    """
    Convenience function to emit a stream event.

    Uses the singleton StreamManager.
    """
    manager = get_stream_manager()
    return await manager.emit(
        event_type,
        workflow_id,
        data,
        room=room,
        visibility=visibility
    )
