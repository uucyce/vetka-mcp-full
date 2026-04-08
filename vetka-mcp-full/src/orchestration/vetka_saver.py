"""
VETKA LangGraph Checkpointer
Persists workflow state to triple-write memory system

@file vetka_saver.py
@status ACTIVE
@phase Phase 60.1 - LangGraph Foundation
@calledBy langgraph_builder.py
@lastAudit 2026-01-10

VETKASaver implements LangGraph's BaseCheckpointSaver interface,
allowing workflow state to be persisted across:
- ChangeLog (JSON file - authoritative source)
- Qdrant (vector search - graceful failure)
- Weaviate (graph relationships - graceful failure)

Design Principles:
- ChangeLog is SOURCE OF TRUTH (always succeeds)
- Qdrant/Weaviate failures are graceful (workflow continues)
- Checkpoints enable workflow recovery and debugging
"""

import json
import logging
from typing import Optional, Dict, Any, Iterator, Tuple
from datetime import datetime

from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple
from langgraph.checkpoint.base import ChannelVersions

from src.orchestration.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


class VETKASaver(BaseCheckpointSaver):
    """
    Custom LangGraph Checkpointer using VETKA's triple-write memory.

    Saves workflow state to:
    - ChangeLog (JSON file - primary, always succeeds)
    - Qdrant (vector search - secondary, graceful failure)
    - Weaviate (graph DB - secondary, graceful failure)

    This enables:
    - Workflow recovery from any checkpoint
    - Debugging workflow execution history
    - Semantic search over past workflows
    """

    def __init__(self, memory_manager: MemoryManager):
        """
        Initialize checkpointer with memory manager.

        Args:
            memory_manager: VETKA MemoryManager instance with triple-write
        """
        super().__init__()
        self.memory = memory_manager
        logger.info("[VETKASaver] Initialized with triple-write memory")

    def put(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions
    ) -> Dict[str, Any]:
        """
        Save checkpoint to VETKA memory system.

        Args:
            config: Contains thread_id (workflow_id)
            checkpoint: LangGraph checkpoint data
            metadata: Checkpoint metadata (source, step, writes)
            new_versions: Channel version information

        Returns:
            Updated config with checkpoint info
        """
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = f"{thread_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # Prepare data for storage
        # Handle metadata as dict or CheckpointMetadata object
        if isinstance(metadata, dict):
            meta_source = metadata.get("source", "unknown")
            meta_step = metadata.get("step", 0)
            meta_writes = metadata.get("writes", {})
        elif metadata:
            meta_source = metadata.source if hasattr(metadata, 'source') else "unknown"
            meta_step = metadata.step if hasattr(metadata, 'step') else 0
            meta_writes = metadata.writes if hasattr(metadata, 'writes') else {}
        else:
            meta_source = "unknown"
            meta_step = 0
            meta_writes = {}

        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "thread_id": thread_id,
            "checkpoint": self._serialize_checkpoint(checkpoint),
            "metadata": {
                "source": meta_source,
                "step": meta_step,
                "writes": meta_writes,
            },
            "new_versions": dict(new_versions) if new_versions else {},
            "timestamp": datetime.now().isoformat(),
            "type": "langgraph_checkpoint",
            "speaker": "system"
        }

        # Triple-write to memory system
        try:
            # Use MemoryManager's triple_write (handles all three backends)
            entry_id = self.memory.triple_write(checkpoint_data)
            logger.debug(f"[VETKASaver] ✅ Checkpoint saved: {checkpoint_id}")

        except Exception as e:
            logger.error(f"[VETKASaver] ❌ Checkpoint save failed: {e}")
            # Don't raise - LangGraph can continue without checkpoints
            # The ChangeLog write in triple_write is critical and will raise if it fails

        return {
            **config,
            "configurable": {
                **config["configurable"],
                "checkpoint_id": checkpoint_id
            }
        }

    def put_writes(
        self,
        config: Dict[str, Any],
        writes: list,
        task_id: str
    ) -> None:
        """
        Store intermediate writes from a node.

        Args:
            config: Configuration with thread_id
            writes: List of (channel, value) tuples
            task_id: Task identifier
        """
        thread_id = config["configurable"]["thread_id"]

        write_data = {
            "type": "langgraph_write",
            "thread_id": thread_id,
            "task_id": task_id,
            "writes": [
                {"channel": channel, "value": self._serialize_value(value)}
                for channel, value in writes
            ],
            "timestamp": datetime.now().isoformat(),
            "speaker": "system"
        }

        try:
            self.memory.triple_write(write_data)
            logger.debug(f"[VETKASaver] Writes stored for task: {task_id}")
        except Exception as e:
            logger.warning(f"[VETKASaver] Failed to store writes: {e}")

    def get_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """
        Retrieve checkpoint tuple from VETKA memory system.

        Args:
            config: Contains thread_id and optionally checkpoint_id

        Returns:
            CheckpointTuple if found, None otherwise
        """
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = config["configurable"].get("checkpoint_id")

        try:
            # Get from ChangeLog (authoritative source)
            checkpoint_data = self._get_checkpoint_from_changelog(thread_id, checkpoint_id)

            if checkpoint_data:
                checkpoint = self._deserialize_checkpoint(checkpoint_data["checkpoint"])

                return CheckpointTuple(
                    config=config,
                    checkpoint=checkpoint,
                    metadata=CheckpointMetadata(
                        source=checkpoint_data.get("metadata", {}).get("source", "unknown"),
                        step=checkpoint_data.get("metadata", {}).get("step", 0),
                        writes=checkpoint_data.get("metadata", {}).get("writes", {}),
                        parents={}
                    ),
                    parent_config=None,
                    pending_writes=[]
                )

            return None

        except Exception as e:
            logger.error(f"[VETKASaver] ❌ Checkpoint get failed: {e}")
            return None

    def list(
        self,
        config: Optional[Dict[str, Any]],
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> Iterator[CheckpointTuple]:
        """
        List checkpoints for a thread.

        Args:
            config: Configuration with thread_id
            filter: Optional filter criteria
            before: Optional cursor for pagination
            limit: Maximum number of checkpoints to return

        Yields:
            CheckpointTuple for each matching checkpoint
        """
        if config is None:
            return

        thread_id = config["configurable"]["thread_id"]

        try:
            checkpoints = self._list_checkpoints_from_changelog(
                thread_id,
                limit=limit or 100
            )

            for cp_data in checkpoints:
                checkpoint = self._deserialize_checkpoint(cp_data["checkpoint"])

                yield CheckpointTuple(
                    config={
                        **config,
                        "configurable": {
                            **config["configurable"],
                            "checkpoint_id": cp_data["checkpoint_id"]
                        }
                    },
                    checkpoint=checkpoint,
                    metadata=CheckpointMetadata(
                        source=cp_data.get("metadata", {}).get("source", "unknown"),
                        step=cp_data.get("metadata", {}).get("step", 0),
                        writes=cp_data.get("metadata", {}).get("writes", {}),
                        parents={}
                    ),
                    parent_config=None,
                    pending_writes=[]
                )

        except Exception as e:
            logger.error(f"[VETKASaver] ❌ Checkpoint list failed: {e}")

    # ===========================
    # ASYNC METHODS (Required by LangGraph async streaming)
    # ===========================

    async def aget_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """
        Async version of get_tuple for LangGraph async operations.

        Wraps synchronous get_tuple for async compatibility.
        """
        return self.get_tuple(config)

    async def aput(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions
    ) -> Dict[str, Any]:
        """
        Async version of put for LangGraph async operations.

        Wraps synchronous put for async compatibility.
        """
        return self.put(config, checkpoint, metadata, new_versions)

    async def aput_writes(
        self,
        config: Dict[str, Any],
        writes: list,
        task_id: str
    ) -> None:
        """
        Async version of put_writes for LangGraph async operations.

        Wraps synchronous put_writes for async compatibility.
        """
        return self.put_writes(config, writes, task_id)

    async def alist(
        self,
        config: Optional[Dict[str, Any]],
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ):
        """
        Async version of list for LangGraph async operations.

        Wraps synchronous list generator as async generator.
        """
        for checkpoint in self.list(config, filter=filter, before=before, limit=limit):
            yield checkpoint

    # ===========================
    # PRIVATE METHODS
    # ===========================

    def _get_checkpoint_from_changelog(
        self,
        thread_id: str,
        checkpoint_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Get checkpoint from ChangeLog.

        Args:
            thread_id: Workflow ID
            checkpoint_id: Specific checkpoint ID (optional)

        Returns:
            Checkpoint data dict or None
        """
        from pathlib import Path

        changelog_path = Path(self.memory.changelog_path)
        if not changelog_path.exists():
            return None

        latest = None
        target_id = checkpoint_id

        with open(changelog_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line)

                    # Check if it's a checkpoint for our thread
                    if entry.get("type") != "langgraph_checkpoint":
                        continue
                    if entry.get("thread_id") != thread_id:
                        continue

                    # If looking for specific checkpoint
                    if target_id and entry.get("checkpoint_id") == target_id:
                        return entry

                    # Otherwise track latest
                    latest = entry

                except json.JSONDecodeError:
                    continue

        # Return latest if no specific ID was requested
        return latest if not target_id else None

    def _list_checkpoints_from_changelog(
        self,
        thread_id: str,
        limit: int = 100
    ) -> list:
        """
        List all checkpoints for a thread from ChangeLog.

        Args:
            thread_id: Workflow ID
            limit: Maximum number to return

        Returns:
            List of checkpoint data dicts (most recent first)
        """
        from pathlib import Path

        changelog_path = Path(self.memory.changelog_path)
        if not changelog_path.exists():
            return []

        checkpoints = []

        with open(changelog_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line)

                    if entry.get("type") != "langgraph_checkpoint":
                        continue
                    if entry.get("thread_id") != thread_id:
                        continue

                    checkpoints.append(entry)

                except json.JSONDecodeError:
                    continue

        # Return most recent first, limited
        return list(reversed(checkpoints))[:limit]

    def _serialize_checkpoint(self, checkpoint: Checkpoint) -> str:
        """
        Serialize checkpoint to JSON string.

        Args:
            checkpoint: LangGraph Checkpoint dict

        Returns:
            JSON string representation
        """
        # Convert to dict, handling special types
        checkpoint_dict = {
            "v": checkpoint.get("v", 1),
            "ts": checkpoint.get("ts", datetime.now().isoformat()),
            "id": checkpoint.get("id", ""),
            "channel_values": self._serialize_values(checkpoint.get("channel_values", {})),
            "channel_versions": checkpoint.get("channel_versions", {}),
            "versions_seen": checkpoint.get("versions_seen", {})
        }
        return json.dumps(checkpoint_dict, default=str)

    def _deserialize_checkpoint(self, checkpoint_str: str) -> Checkpoint:
        """
        Deserialize checkpoint from JSON string.

        Args:
            checkpoint_str: JSON string from storage

        Returns:
            Checkpoint dict
        """
        checkpoint_dict = json.loads(checkpoint_str)
        checkpoint_dict["channel_values"] = self._deserialize_values(
            checkpoint_dict.get("channel_values", {})
        )
        return checkpoint_dict

    def _serialize_values(self, values: Dict) -> Dict:
        """
        Serialize state values, handling special types.

        Args:
            values: State channel values

        Returns:
            JSON-serializable dict
        """
        serialized = {}

        for key, value in values.items():
            try:
                if hasattr(value, 'to_dict'):
                    serialized[key] = value.to_dict()
                elif hasattr(value, '__dict__'):
                    serialized[key] = value.__dict__
                elif isinstance(value, (list, dict, str, int, float, bool, type(None))):
                    serialized[key] = value
                else:
                    # Try JSON serialization, fallback to string
                    try:
                        json.dumps(value)
                        serialized[key] = value
                    except (TypeError, ValueError):
                        serialized[key] = str(value)
            except Exception as e:
                logger.warning(f"[VETKASaver] Could not serialize {key}: {e}")
                serialized[key] = str(value)

        return serialized

    def _deserialize_values(self, values: Dict) -> Dict:
        """
        Deserialize state values.

        Note: Complex types (like BaseMessage) need reconstruction.
        For now, returns as-is; can add type reconstruction later.

        Args:
            values: Serialized values dict

        Returns:
            Deserialized values (may need further processing)
        """
        # Messages need special handling
        if "messages" in values and isinstance(values["messages"], list):
            from langchain_core.messages import HumanMessage, AIMessage

            reconstructed = []
            for msg in values["messages"]:
                if isinstance(msg, dict):
                    msg_type = msg.get("type", "human")
                    content = msg.get("content", "")
                    name = msg.get("name")

                    if msg_type == "human":
                        reconstructed.append(HumanMessage(content=content))
                    else:
                        reconstructed.append(AIMessage(content=content, name=name))
                else:
                    reconstructed.append(msg)

            values["messages"] = reconstructed

        return values

    def _serialize_value(self, value: Any) -> Any:
        """
        Serialize a single value.

        Args:
            value: Value to serialize

        Returns:
            JSON-serializable value
        """
        if hasattr(value, 'to_dict'):
            return value.to_dict()
        elif hasattr(value, '__dict__'):
            return value.__dict__
        else:
            try:
                json.dumps(value)
                return value
            except (TypeError, ValueError):
                return str(value)
