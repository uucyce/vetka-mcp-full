# === PHASE 104.9: PERSISTENCE SERVICE ===
"""
Chat event persistence service with Redis caching and disk fallback.

MARKER_104_CHAT_SAVE

@status: active
@phase: 104.9
@depends: asyncio, json, os, datetime, logging, redis (optional)
@used_by: src.api.handlers, src.orchestration

Features:
- Async save_chat_history() for workflow event persistence
- Redis-first caching with 300s TTL for fast retrieval
- Automatic fallback to disk (data/chat_history/{workflow_id}.json)
- Directory auto-creation for new workflow paths
"""

import asyncio
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Any, Dict

logger = logging.getLogger(__name__)

# Redis availability check (same pattern as model_router_v2.py)
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


# Redis connection singleton
_redis_client: Optional[Any] = None
_redis_connection_attempted: bool = False


def _get_redis_client() -> Optional[Any]:
    """
    Get or create Redis client singleton.

    MARKER_104_CHAT_SAVE: Lazy Redis connection with graceful failure.

    Returns:
        Redis client or None if unavailable
    """
    global _redis_client, _redis_connection_attempted

    if not REDIS_AVAILABLE:
        return None

    if _redis_client is not None:
        return _redis_client

    if _redis_connection_attempted:
        # Already tried and failed - don't retry
        return None

    _redis_connection_attempted = True

    try:
        # Default Redis connection (localhost:6379)
        client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0)),
            decode_responses=True,
            socket_timeout=2.0,  # Fast timeout for responsiveness
            socket_connect_timeout=2.0
        )
        # Test connection
        client.ping()
        _redis_client = client
        logger.info("[PERSISTENCE] Redis connection established")
        return _redis_client
    except Exception as e:
        logger.warning(f"[PERSISTENCE] Redis unavailable, using disk fallback: {e}")
        return None


async def save_chat_history(
    workflow_id: str,
    events: list,
    sid: str = None
) -> bool:
    """
    Save chat history events for a workflow.

    MARKER_104_CHAT_SAVE

    Persistence strategy:
    1. Try Redis first with 300s TTL for fast retrieval
    2. Always save to disk as permanent storage

    Args:
        workflow_id: Unique workflow identifier (e.g., from agent pipeline)
        events: List of chat events/messages to persist
        sid: Optional socket ID for session tracking

    Returns:
        True if save succeeded (either Redis or disk), False on complete failure
    """
    if not workflow_id:
        logger.warning("[PERSISTENCE] Cannot save: workflow_id is empty")
        return False

    if not events:
        logger.debug(f"[PERSISTENCE] No events to save for workflow {workflow_id}")
        return True  # Empty events is not a failure

    # Build data structure
    data: Dict[str, Any] = {
        "workflow_id": workflow_id,
        "events": events,
        "sid": sid,
        "timestamp": datetime.now().isoformat()
    }

    redis_success = False
    disk_success = False

    # Step 1: Try Redis first (non-blocking)
    redis_client = _get_redis_client()
    if redis_client:
        try:
            redis_key = f"chat:{workflow_id}"
            json_data = json.dumps(data, ensure_ascii=False, default=str)
            # setex: SET with EXpiration (TTL 300 seconds = 5 minutes)
            redis_client.setex(redis_key, 300, json_data)
            redis_success = True
            logger.debug(f"[PERSISTENCE] Redis cached: {redis_key} (TTL 300s)")
        except Exception as e:
            logger.warning(f"[PERSISTENCE] Redis save failed for {workflow_id}: {e}")

    # Step 2: Always save to disk (permanent storage)
    disk_path = Path(f"data/chat_history/{workflow_id}.json")

    try:
        # Create directory if not exists
        # MARKER_104_CHAT_SAVE: Directory auto-creation
        os.makedirs(os.path.dirname(disk_path), exist_ok=True)

        # Write atomically (temp file + rename)
        temp_path = disk_path.with_suffix('.tmp')

        # Run file I/O in executor to avoid blocking event loop
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            _write_json_file,
            temp_path,
            disk_path,
            data
        )

        disk_success = True
        logger.info(f"[PERSISTENCE] Chat saved: {workflow_id}")

    except Exception as e:
        logger.error(f"[PERSISTENCE] Disk save failed for {workflow_id}: {e}")

    return redis_success or disk_success


def _write_json_file(temp_path: Path, final_path: Path, data: dict) -> None:
    """
    Write JSON file atomically (sync helper for executor).

    MARKER_104_CHAT_SAVE: Atomic write with temp file pattern.

    Args:
        temp_path: Temporary file path
        final_path: Final destination path
        data: Data dict to serialize
    """
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    # Atomic rename (POSIX compliant)
    temp_path.replace(final_path)


async def load_chat_history(workflow_id: str) -> Optional[Dict[str, Any]]:
    """
    Load chat history for a workflow.

    MARKER_104_CHAT_SAVE

    Load strategy:
    1. Try Redis first (fast cache)
    2. Fallback to disk if not in cache

    Args:
        workflow_id: Unique workflow identifier

    Returns:
        Chat history dict or None if not found
    """
    if not workflow_id:
        return None

    # Step 1: Try Redis first
    redis_client = _get_redis_client()
    if redis_client:
        try:
            redis_key = f"chat:{workflow_id}"
            cached = redis_client.get(redis_key)
            if cached:
                logger.debug(f"[PERSISTENCE] Redis hit: {redis_key}")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"[PERSISTENCE] Redis load failed for {workflow_id}: {e}")

    # Step 2: Try disk
    disk_path = Path(f"data/chat_history/{workflow_id}.json")

    if disk_path.exists():
        try:
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(
                None,
                _read_json_file,
                disk_path
            )
            logger.debug(f"[PERSISTENCE] Disk load: {workflow_id}")
            return data
        except Exception as e:
            logger.error(f"[PERSISTENCE] Disk load failed for {workflow_id}: {e}")

    return None


def _read_json_file(path: Path) -> dict:
    """
    Read JSON file (sync helper for executor).

    Args:
        path: File path to read

    Returns:
        Parsed JSON dict
    """
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


async def delete_chat_history(workflow_id: str) -> bool:
    """
    Delete chat history for a workflow.

    MARKER_104_CHAT_SAVE

    Args:
        workflow_id: Unique workflow identifier

    Returns:
        True if deleted from at least one location
    """
    if not workflow_id:
        return False

    deleted = False

    # Delete from Redis
    redis_client = _get_redis_client()
    if redis_client:
        try:
            redis_key = f"chat:{workflow_id}"
            redis_client.delete(redis_key)
            deleted = True
        except Exception as e:
            logger.warning(f"[PERSISTENCE] Redis delete failed for {workflow_id}: {e}")

    # Delete from disk
    disk_path = Path(f"data/chat_history/{workflow_id}.json")
    if disk_path.exists():
        try:
            disk_path.unlink()
            deleted = True
            logger.info(f"[PERSISTENCE] Deleted chat history: {workflow_id}")
        except Exception as e:
            logger.error(f"[PERSISTENCE] Disk delete failed for {workflow_id}: {e}")

    return deleted


# Convenience exports
__all__ = [
    'save_chat_history',
    'load_chat_history',
    'delete_chat_history',
    'REDIS_AVAILABLE'
]
