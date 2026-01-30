# === PHASE 55: FILE LOCK MANAGER ===
"""
File-level locking to prevent concurrent write conflicts.

Ensures only one agent can modify a file at a time with timeout support.

@status: active
@phase: 96
@depends: asyncio, dataclasses
@used_by: orchestrator_with_elisya.py, agents
"""

import asyncio
import os
import logging
from typing import Dict, Optional, Set
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FileLock:
    """Single file lock."""
    file_path: str
    agent_id: str
    acquired_at: datetime
    timeout_seconds: int = 30


class FileLockManager:
    """
    Manages file-level locks for concurrent agent access.

    Usage:
        lock_manager = get_file_lock_manager()

        if await lock_manager.acquire_lock('/path/file.py', 'agent_123'):
            try:
                # Write to file
                pass
            finally:
                await lock_manager.release_lock('/path/file.py', 'agent_123')
        else:
            # File is locked by another agent
            pass
    """

    def __init__(self):
        self._locks: Dict[str, FileLock] = {}
        self._lock = asyncio.Lock()  # Async-safe access

    async def acquire_lock(
        self,
        file_path: str,
        agent_id: str,
        timeout: int = 30
    ) -> bool:
        """
        Acquire lock on a file.

        Args:
            file_path: Path to the file
            agent_id: ID of the agent requesting lock
            timeout: Max seconds to hold lock (default: 30)

        Returns:
            True if lock acquired, False if file is locked
        """
        async with self._lock:
            # Normalize path for security
            file_path = os.path.abspath(os.path.normpath(file_path))

            # Check if already locked
            existing = self._locks.get(file_path)

            if existing:
                # Check if lock expired
                age = (datetime.now() - existing.acquired_at).total_seconds()
                if age > existing.timeout_seconds:
                    # ATOMIC: Replace expired lock immediately (no race condition)
                    self._locks[file_path] = FileLock(
                        file_path=file_path,
                        agent_id=agent_id,
                        acquired_at=datetime.now(),
                        timeout_seconds=timeout
                    )
                    logger.info(f"[FileLock] Expired lock replaced: {file_path} by {agent_id} (was {existing.agent_id})")
                    return True
                elif existing.agent_id == agent_id:
                    # Same agent already has lock (re-entrant) - refresh timestamp
                    existing.acquired_at = datetime.now()
                    logger.info(f"[FileLock] Re-entrant lock refreshed: {file_path} by {agent_id}")
                    return True
                else:
                    # Locked by another agent
                    logger.info(f"[FileLock] Blocked: {file_path} locked by {existing.agent_id}")
                    return False
            else:
                # No existing lock - create new one
                self._locks[file_path] = FileLock(
                    file_path=file_path,
                    agent_id=agent_id,
                    acquired_at=datetime.now(),
                    timeout_seconds=timeout
                )
                logger.info(f"[FileLock] Acquired: {file_path} by {agent_id}")
                return True

    async def release_lock(self, file_path: str, agent_id: str) -> bool:
        """
        Release lock on a file.

        Args:
            file_path: Path to the file
            agent_id: ID of the agent releasing lock

        Returns:
            True if released, False if not locked or wrong agent
        """
        async with self._lock:
            # Normalize path for security
            file_path = os.path.abspath(os.path.normpath(file_path))

            existing = self._locks.get(file_path)

            if not existing:
                logger.info(f"[FileLock] Release failed - not locked: {file_path}")
                return False

            if existing.agent_id != agent_id:
                logger.error(f"[FileLock] Release failed - wrong agent: {file_path} "
                      f"(locked by {existing.agent_id}, release by {agent_id})")
                return False

            del self._locks[file_path]
            logger.info(f"[FileLock] Released: {file_path} by {agent_id}")
            return True

    async def is_locked(self, file_path: str) -> bool:
        """Check if file is currently locked."""
        async with self._lock:
            # Normalize path for security
            file_path = os.path.abspath(os.path.normpath(file_path))

            existing = self._locks.get(file_path)
            if not existing:
                return False

            # Check expiration
            age = (datetime.now() - existing.acquired_at).total_seconds()
            if age > existing.timeout_seconds:
                del self._locks[file_path]
                return False

            return True

    async def get_lock_holder(self, file_path: str) -> Optional[str]:
        """Get agent ID holding the lock, or None."""
        async with self._lock:
            # Normalize path for security
            file_path = os.path.abspath(os.path.normpath(file_path))

            existing = self._locks.get(file_path)
            if existing:
                age = (datetime.now() - existing.acquired_at).total_seconds()
                if age <= existing.timeout_seconds:
                    return existing.agent_id
            return None

    async def get_all_locks(self) -> Dict[str, str]:
        """Get all active locks as {file_path: agent_id}."""
        async with self._lock:
            now = datetime.now()

            # First, collect expired paths (don't modify dict during iteration)
            expired = [
                path for path, lock in self._locks.items()
                if (now - lock.acquired_at).total_seconds() > lock.timeout_seconds
            ]

            # Then delete them
            for path in expired:
                del self._locks[path]

            # Return active locks
            return {path: lock.agent_id for path, lock in self._locks.items()}

    async def force_release_all(self, agent_id: str) -> int:
        """
        Force release all locks held by an agent.
        Used when agent crashes or times out.

        Returns:
            Number of locks released
        """
        async with self._lock:
            # Collect paths to release (don't modify dict during iteration)
            to_release = [
                path for path, lock in self._locks.items()
                if lock.agent_id == agent_id
            ]

            # Then delete them
            for path in to_release:
                del self._locks[path]

            if to_release:
                logger.info(f"[FileLock] Force released {len(to_release)} locks for {agent_id}")

            return len(to_release)


# Singleton instance
_file_lock_manager: Optional[FileLockManager] = None


def get_file_lock_manager() -> FileLockManager:
    """Get or create singleton FileLockManager."""
    global _file_lock_manager
    if _file_lock_manager is None:
        _file_lock_manager = FileLockManager()
    return _file_lock_manager
