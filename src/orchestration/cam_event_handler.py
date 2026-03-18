"""
Phase 51.3: Event-Driven CAM Handler

Unified entry point for all CAM (Context-Aware Memory) operations.
Reacts to events: artifact_created, file_uploaded, message_sent, workflow_completed

@file cam_event_handler.py
@status ACTIVE
@phase Phase 51.3
@lastUpdate 2026-01-07

Architecture:
    Event Source (agent/workflow/user)
        ↓
    emit_cam_event()
        ↓
    CAMEventHandler.handle_event()
        ↓
    Specific handler (_handle_artifact, _handle_workflow_complete, etc.)
        ↓
    CAM Engine operations
        ↓
    Return result
"""

import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum


class CAMEventType(Enum):
    """Types of events that trigger CAM operations."""
    ARTIFACT_CREATED = "artifact_created"
    FILE_UPLOADED = "file_uploaded"
    MESSAGE_SENT = "message_sent"
    CHAT_FAVORITED = "chat_favorited"
    WORKFLOW_COMPLETED = "workflow_completed"
    PERIODIC_MAINTENANCE = "periodic_maintenance"
    PIPELINE_FAILED = "pipeline_failed"  # MARKER_187.12: Failure feedback loop


@dataclass
class CAMEvent:
    """
    CAM event data structure.

    Attributes:
        event_type: Type of event
        payload: Event-specific data
        source: Where the event came from (agent name, "user", "workflow", etc.)
        timestamp: When event was created (auto-set)
    """
    event_type: CAMEventType
    payload: Dict[str, Any]
    source: str
    timestamp: float = field(default_factory=time.time)


class CAMEventHandler:
    """
    Centralized CAM event processing.

    Handles all CAM operations in a uniform way, removing code duplication
    across handlers and providing a single point of control for CAM behavior.
    """

    def __init__(self, cam_engine=None, memory_manager=None):
        """
        Initialize CAM event handler.

        Args:
            cam_engine: VETKACAMEngine instance (optional, will lazy-load)
            memory_manager: MemoryManager instance (optional, will lazy-load)
        """
        self._cam_engine = cam_engine
        self._memory_manager = memory_manager
        self._event_queue: List[CAMEvent] = []
        self._stats = {
            'events_processed': 0,
            'artifacts_processed': 0,
            'maintenance_runs': 0,
            'errors': 0
        }

    def _ensure_cam_engine(self):
        """Lazy-load CAM engine if not provided."""
        if self._cam_engine is None:
            try:
                from src.orchestration.cam_engine import VETKACAMEngine
                from src.orchestration.memory_manager import get_memory_manager

                self._memory_manager = get_memory_manager()
                self._cam_engine = VETKACAMEngine(memory_manager=self._memory_manager)
                print("[CAM] Engine lazy-loaded successfully")
            except Exception as e:
                print(f"[CAM] Failed to lazy-load engine: {e}")
                raise

    async def handle_event(self, event: CAMEvent) -> Dict[str, Any]:
        """
        Main entry point for all CAM events.

        Args:
            event: CAMEvent to process

        Returns:
            Result dict with status and event-specific data
        """
        print(f"[CAM_EVENT] {event.event_type.value} from {event.source}")

        try:
            self._ensure_cam_engine()

            if event.event_type == CAMEventType.ARTIFACT_CREATED:
                result = await self._handle_artifact(event.payload)
            elif event.event_type == CAMEventType.FILE_UPLOADED:
                result = await self._handle_file_upload(event.payload)
            elif event.event_type == CAMEventType.MESSAGE_SENT:
                result = await self._handle_message(event.payload)
            elif event.event_type == CAMEventType.CHAT_FAVORITED:
                result = await self._handle_chat_favorited(event.payload)
            elif event.event_type == CAMEventType.WORKFLOW_COMPLETED:
                result = await self._handle_workflow_complete(event.payload)
            elif event.event_type == CAMEventType.PERIODIC_MAINTENANCE:
                result = await self._run_maintenance()
            elif event.event_type == CAMEventType.PIPELINE_FAILED:
                result = await self._handle_pipeline_failure(event.payload)
            else:
                print(f"[CAM_EVENT] Unknown event type: {event.event_type}")
                return {"status": "unknown_event", "event_type": str(event.event_type)}

            self._stats['events_processed'] += 1
            return result

        except Exception as e:
            print(f"[CAM_EVENT] Error handling {event.event_type.value}: {e}")
            self._stats['errors'] += 1
            return {"status": "error", "error": str(e)}

    async def _handle_artifact(self, payload: Dict) -> Dict:
        """
        Handle artifact_created event.

        Args:
            payload: {path: str, content: str, source_agent: str}

        Returns:
            {status: str, artifact: str, operation: str, metadata: dict}
        """
        artifact_path = payload.get('path', 'unknown')
        artifact_content = payload.get('content', '')
        source_agent = payload.get('source_agent', 'unknown')

        # Prepare metadata for CAM engine
        metadata = {
            'content': artifact_content,
            'type': 'code',  # Could be inferred from file extension
            'source_agent': source_agent,
            'name': artifact_path.split('/')[-1] if '/' in artifact_path else artifact_path
        }

        # Use handle_new_artifact (correct CAM Engine API)
        cam_result = await self._cam_engine.handle_new_artifact(
            artifact_path=artifact_path,
            metadata=metadata
        )

        # Extract surprise from CAM operation result
        # Note: CAMOperation has similarity, not surprise directly
        # surprise = 1 - similarity
        similarity = getattr(cam_result, 'similarity', 0.5)
        surprise = 1.0 - similarity if similarity > 0 else 0.5

        operation_type = getattr(cam_result, 'operation_type', 'unknown')

        print(f"[CAM_EVENT] Artifact '{artifact_path}': operation={operation_type}, similarity={similarity:.2f}")

        self._stats['artifacts_processed'] += 1

        return {
            "status": "processed",
            "artifact": artifact_path,
            "operation": operation_type,
            "similarity": similarity,
            "surprise": surprise
        }

    async def _handle_file_upload(self, payload: Dict) -> Dict:
        """
        Handle file_uploaded event.

        Args:
            payload: {path: str, content: str}

        Returns:
            Result dict
        """
        # Similar to artifact, but from user upload
        return await self._handle_artifact(payload)

    async def _handle_message(self, payload: Dict) -> Dict:
        """
        Phase 51.4: Handle message_sent event.
        Promote high-surprise messages to long-term memory.

        Args:
            payload: {content: str, chat_id: str, role: str}

        Returns:
            {status: str, surprise: float, promoted: bool}
        """
        content = payload.get('content', '')
        chat_id = payload.get('chat_id', '')
        role = payload.get('role', 'user')

        # Skip empty or very short messages
        if len(content) < 20:
            return {"status": "skipped", "reason": "too_short", "chat_id": chat_id}

        # Skip system messages
        if role == 'system':
            return {"status": "skipped", "reason": "system_message", "chat_id": chat_id}

        try:
            # Get embedding for this message
            message_embedding = await self._get_embedding_async(content)

            # Get recent history embeddings for comparison
            recent_embeddings = await self._get_recent_history_embeddings(chat_id, limit=10)

            # Calculate surprise (novelty)
            if recent_embeddings and len(recent_embeddings) > 0:
                surprise = self._calculate_message_surprise(message_embedding, recent_embeddings)
            else:
                surprise = 0.5  # Default for first message

            print(f"[CAM_EVENT] Message surprise: {surprise:.2f} (threshold: 0.7)")

            # Promote if high surprise
            NOVEL_THRESHOLD = 0.7
            if surprise > NOVEL_THRESHOLD:
                await self._promote_message_to_long_term(payload, message_embedding, surprise)
                print(f"[CAM_EVENT] ✅ Message promoted to long-term memory")
                return {"status": "promoted", "surprise": surprise, "chat_id": chat_id}

            return {"status": "kept_short_term", "surprise": surprise, "chat_id": chat_id}

        except Exception as e:
            print(f"[CAM_EVENT] Message handling error: {e}")
            return {"status": "error", "error": str(e), "chat_id": chat_id}

    async def _handle_workflow_complete(self, payload: Dict) -> Dict:
        """
        Handle workflow_completed event - run maintenance.

        Args:
            payload: {workflow_id: str, artifacts: List}

        Returns:
            {status: str, pruned: int, merged: int}
        """
        workflow_id = payload.get('workflow_id', 'unknown')

        print(f"[CAM_EVENT] Workflow {workflow_id} completed, running maintenance...")

        return await self._run_maintenance()

    async def _handle_pipeline_failure(self, payload: Dict) -> Dict:
        """
        MARKER_187.12: Handle pipeline_failed event — feed failure into memory.

        Calls failure_feedback.record_failure_feedback() which fans out to
        STM (boosted weight), CORTEX (tool failure), and ENGRAM (pair warnings).

        Args:
            payload: {task_id, error, failed_tools, tier_used, severity, ...}
        """
        from src.memory.failure_feedback import record_failure_feedback

        task_id = payload.get("task_id", "unknown")
        error = payload.get("error", "unknown failure")

        result = record_failure_feedback(
            task_id=task_id,
            error_summary=error,
            failed_tools=payload.get("failed_tools"),
            tier_used=payload.get("tier_used", ""),
            phase_type=payload.get("phase_type", "build"),
            attempt=payload.get("attempt", 1),
            severity=payload.get("severity", "major"),
            subtask_context=payload.get("subtask_context"),
        )

        print(f"[CAM_EVENT] Pipeline failure feedback for {task_id}: {result.get('stm', {}).get('status', 'skip')}")
        return {"status": "failure_recorded", "task_id": task_id, "feedback": result}

    async def _handle_chat_favorited(self, payload: Dict) -> Dict:
        """
        Handle chat_favorited event.

        MARKER_137.3: Promote favorited chats as high-priority memory anchors.

        Args:
            payload: {chat_id: str, is_favorite: bool}

        Returns:
            Result dict with sync status
        """
        chat_id = str(payload.get("chat_id", "")).strip()
        is_favorite = bool(payload.get("is_favorite", False))

        if not chat_id:
            return {"status": "skipped", "reason": "missing_chat_id"}

        if not is_favorite:
            # Unfavorite is intentionally lightweight for now.
            return {"status": "demoted", "chat_id": chat_id}

        metadata = {
            "type": "chat_favorite",
            "chat_id": chat_id,
            "is_favorite": True,
            "promoted_at": time.time(),
            "content": f"Favorite chat anchor: {chat_id}",
        }

        artifact_path = f"chat_favorites/{chat_id}"
        await self._cam_engine.handle_new_artifact(
            artifact_path=artifact_path,
            metadata=metadata
        )

        return {"status": "promoted", "chat_id": chat_id}

    async def _run_maintenance(self) -> Dict:
        """
        Run periodic maintenance (prune + merge).

        Returns:
            {status: str, pruned: int, merged: int}
        """
        print("[CAM_EVENT] 🔍 Running periodic maintenance...")

        pruned = await self._cam_engine.prune_low_entropy(threshold=0.2)
        merged = await self._cam_engine.merge_similar_subtrees(threshold=0.92)

        pruned_count = len(pruned or [])
        merged_count = len(merged or [])

        if pruned_count > 0:
            print(f"[CAM_EVENT] 🌱 Pruned {pruned_count} low-entropy nodes")
        else:
            print("[CAM_EVENT] ✓ No low-entropy nodes to prune")

        if merged_count > 0:
            print(f"[CAM_EVENT] 🔗 Merged {merged_count} similar subtrees")
        else:
            print("[CAM_EVENT] ✓ No similar subtrees to merge")

        self._stats['maintenance_runs'] += 1

        return {
            "status": "completed",
            "pruned": pruned_count,
            "merged": merged_count
        }

    # ============ PHASE 51.4: Message Surprise Helpers ============

    async def _get_embedding_async(self, text: str) -> List[float]:
        """
        Get embedding for text using memory manager.

        Args:
            text: Text to embed

        Returns:
            768-dimensional embedding vector
        """
        if self._memory_manager:
            # Use memory manager's embedding service
            embedding = self._memory_manager._get_embedding(text)
            if embedding:
                return embedding

        # Fallback: use simple hash-based pseudo-embedding
        import hashlib
        hash_bytes = hashlib.sha256(text.encode()).digest()
        # Create 768-dim pseudo-embedding from hash
        pseudo_emb = []
        for i in range(0, min(len(hash_bytes), 768)):
            pseudo_emb.append(hash_bytes[i] / 255.0)
        # Pad to 768 if needed
        while len(pseudo_emb) < 768:
            pseudo_emb.append(0.0)
        return pseudo_emb

    async def _get_recent_history_embeddings(
        self,
        chat_id: str,
        limit: int = 10
    ) -> List[List[float]]:
        """
        Get embeddings of recent messages in this chat.

        Args:
            chat_id: Chat identifier
            limit: Number of recent messages

        Returns:
            List of embedding vectors
        """
        # TODO: Implement via ChatHistoryManager + embedding cache
        # For now, return empty (will default to surprise=0.5)
        return []

    def _calculate_message_surprise(
        self,
        new_embedding: List[float],
        history_embeddings: List[List[float]]
    ) -> float:
        """
        Calculate surprise as distance from centroid of history.

        Args:
            new_embedding: Embedding of new message
            history_embeddings: Embeddings of recent messages

        Returns:
            Surprise score [0.0, 1.0] (higher = more novel)
        """
        import numpy as np

        new_vec = np.array(new_embedding)
        history_matrix = np.array(history_embeddings)

        # Centroid of history
        centroid = np.mean(history_matrix, axis=0)

        # Cosine similarity
        dot_product = np.dot(new_vec, centroid)
        norm_new = np.linalg.norm(new_vec)
        norm_centroid = np.linalg.norm(centroid)

        if norm_new == 0 or norm_centroid == 0:
            return 0.5  # Default if norms are zero

        similarity = dot_product / (norm_new * norm_centroid)
        surprise = 1.0 - similarity  # Higher distance = more surprise

        # Clamp to [0, 1]
        return max(0.0, min(1.0, surprise))

    async def _promote_message_to_long_term(
        self,
        payload: Dict,
        embedding: List[float],
        surprise: float
    ):
        """
        Promote high-surprise message to long-term CAM memory.

        Args:
            payload: Message payload
            embedding: Message embedding
            surprise: Surprise score
        """
        metadata = {
            'content': payload.get('content', ''),
            'chat_id': payload.get('chat_id', ''),
            'role': payload.get('role', 'user'),
            'surprise': surprise,
            'promoted_at': time.time(),
            'type': 'chat_insight',
            'embedding': embedding
        }

        # Store in CAM via handle_new_artifact
        artifact_path = f"chat_insights/{payload.get('chat_id', 'unknown')}/{int(time.time())}"

        await self._cam_engine.handle_new_artifact(
            artifact_path=artifact_path,
            metadata=metadata
        )

    def get_stats(self) -> Dict[str, int]:
        """Get CAM event handler statistics."""
        return self._stats.copy()


# ============ SINGLETON INSTANCE ============

_cam_event_handler: Optional[CAMEventHandler] = None


def get_cam_event_handler() -> CAMEventHandler:
    """
    Get singleton CAM event handler instance.

    Returns:
        CAMEventHandler instance
    """
    global _cam_event_handler

    if _cam_event_handler is None:
        print("[CAM_EVENT] Initializing singleton handler...")
        _cam_event_handler = CAMEventHandler()

    return _cam_event_handler


# ============ CONVENIENCE FUNCTIONS ============

async def emit_cam_event(
    event_type: str,
    payload: Dict[str, Any],
    source: str = "system"
) -> Dict[str, Any]:
    """
    Emit a CAM event from anywhere in the codebase.

    Usage:
        await emit_cam_event("artifact_created", {
            "path": "user.py",
            "content": "def validate()...",
            "source_agent": "Dev"
        }, source="dev_agent")

    Args:
        event_type: One of CAMEventType values as string
        payload: Event-specific data
        source: Event source identifier

    Returns:
        Result dict from event handler
    """
    handler = get_cam_event_handler()

    event = CAMEvent(
        event_type=CAMEventType(event_type),
        payload=payload,
        source=source
    )

    return await handler.handle_event(event)


async def emit_artifact_event(artifact_path: str, artifact_content: str, source_agent: str = "unknown") -> Dict:
    """
    Convenience: Emit artifact_created event.

    Args:
        artifact_path: Path to artifact file
        artifact_content: File content
        source_agent: Which agent created it

    Returns:
        Event result
    """
    return await emit_cam_event(
        "artifact_created",
        {
            "path": artifact_path,
            "content": artifact_content,
            "source_agent": source_agent
        },
        source=source_agent
    )


async def emit_workflow_complete_event(workflow_id: str, artifacts: List[Dict] = None) -> Dict:
    """
    Convenience: Emit workflow_completed event.

    Args:
        workflow_id: Workflow identifier
        artifacts: List of artifacts created (optional)

    Returns:
        Event result
    """
    return await emit_cam_event(
        "workflow_completed",
        {
            "workflow_id": workflow_id,
            "artifacts": artifacts or []
        },
        source="orchestrator"
    )


# ============ STATS ============

def get_cam_stats() -> Dict[str, int]:
    """Get CAM event handler statistics."""
    handler = get_cam_event_handler()
    return handler.get_stats()
