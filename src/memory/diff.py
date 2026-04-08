"""
VETKA Phase 77.2 - Memory Diff Algorithm
Compares two MemorySnapshots and generates transformation

@file diff.py
@status ACTIVE
@phase Phase 77.2 - Memory Sync Protocol
@calledBy MemorySyncEngine
@lastAudit 2026-01-20

Key principle: deleted ≠ immediately delete
Deleted files go to Trash Memory for user recovery option.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field

from .snapshot import MemorySnapshot, NodeState, EdgeState, EdgeChange

logger = logging.getLogger(__name__)


@dataclass
class DiffResult:
    """
    Result of comparing two MemorySnapshots.

    Contains all changes needed to transform old_snapshot → new_snapshot.
    Deleted nodes are NOT immediately deleted — they go to Trash.
    """
    # Node changes
    added: Dict[str, NodeState] = field(default_factory=dict)  # path → node
    modified: Dict[str, NodeState] = field(default_factory=dict)  # path → new state
    deleted: Dict[str, NodeState] = field(default_factory=dict)  # path → old state (→ Trash!)

    # Edge changes
    edges_added: List[EdgeChange] = field(default_factory=list)
    edges_modified: List[EdgeChange] = field(default_factory=list)
    edges_deleted: List[EdgeChange] = field(default_factory=list)

    # Summary
    old_snapshot_id: str = ""
    new_snapshot_id: str = ""
    computed_at: datetime = field(default_factory=datetime.now)

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return bool(
            self.added or
            self.modified or
            self.deleted or
            self.edges_added or
            self.edges_modified or
            self.edges_deleted
        )

    @property
    def total_changes(self) -> int:
        """Total number of changes."""
        return (
            len(self.added) +
            len(self.modified) +
            len(self.deleted) +
            len(self.edges_added) +
            len(self.edges_modified) +
            len(self.edges_deleted)
        )

    @property
    def summary(self) -> Dict[str, int]:
        """Get change summary."""
        return {
            'added': len(self.added),
            'modified': len(self.modified),
            'deleted': len(self.deleted),
            'edges_added': len(self.edges_added),
            'edges_modified': len(self.edges_modified),
            'edges_deleted': len(self.edges_deleted),
            'total': self.total_changes
        }

    def to_dict(self) -> dict:
        """Convert to serializable dict."""
        return {
            'added': {k: v.to_dict() for k, v in self.added.items()},
            'modified': {k: v.to_dict() for k, v in self.modified.items()},
            'deleted': {k: v.to_dict() for k, v in self.deleted.items()},
            'edges_added': [e.to_dict() for e in self.edges_added],
            'edges_modified': [e.to_dict() for e in self.edges_modified],
            'edges_deleted': [e.to_dict() for e in self.edges_deleted],
            'old_snapshot_id': self.old_snapshot_id,
            'new_snapshot_id': self.new_snapshot_id,
            'computed_at': self.computed_at.isoformat(),
            'summary': self.summary
        }


class MemoryDiff:
    """
    Compares two MemorySnapshots and calculates the diff.

    Usage:
        differ = MemoryDiff()
        diff = await differ.diff(old_snapshot, new_snapshot)

        # Apply changes
        for path, node in diff.added.items():
            await memory.add_node(node)

        for path, node in diff.deleted.items():
            await trash.move_to_trash(node)  # NOT delete!
    """

    def __init__(
        self,
        hash_check: bool = True,
        timestamp_check: bool = True,
        size_check: bool = True
    ):
        """
        Initialize diff calculator.

        Args:
            hash_check: Compare content hashes
            timestamp_check: Compare timestamps
            size_check: Compare file sizes

        All three checks combined reduce false positives.
        """
        self.hash_check = hash_check
        self.timestamp_check = timestamp_check
        self.size_check = size_check

    async def diff(
        self,
        old_snapshot: MemorySnapshot,
        new_snapshot: MemorySnapshot
    ) -> DiffResult:
        """
        Calculate diff between two snapshots.

        FS Snapshot (new) VS Memory Snapshot (old) → Diff

        Args:
            old_snapshot: Previous state (typically from Qdrant)
            new_snapshot: Current state (typically from filesystem)

        Returns:
            DiffResult with all changes

        Key principle:
            deleted ≠ delete immediately
            deleted → Trash Memory (soft delete)
            user/hostess decides: delete or keep
        """
        result = DiffResult(
            old_snapshot_id=old_snapshot.snapshot_id,
            new_snapshot_id=new_snapshot.snapshot_id,
            computed_at=datetime.now()
        )

        old_paths = set(old_snapshot.nodes.keys())
        new_paths = set(new_snapshot.nodes.keys())

        # 1. Files in new but not in old → ADDED
        added_paths = new_paths - old_paths
        for path in added_paths:
            result.added[path] = new_snapshot.nodes[path]

        # 2. Files in old but not in new → DELETED (→ Trash!)
        deleted_paths = old_paths - new_paths
        for path in deleted_paths:
            result.deleted[path] = old_snapshot.nodes[path]

        # 3. Files in both → check if MODIFIED
        common_paths = old_paths & new_paths
        for path in common_paths:
            old_node = old_snapshot.nodes[path]
            new_node = new_snapshot.nodes[path]

            if self._is_modified(old_node, new_node):
                result.modified[path] = new_node

        # 4. Edge changes
        result.edges_added, result.edges_modified, result.edges_deleted = \
            await self._diff_edges(old_snapshot, new_snapshot)

        logger.info(
            f"[MemoryDiff] Computed diff: "
            f"+{len(result.added)} ~{len(result.modified)} -{len(result.deleted)} nodes, "
            f"+{len(result.edges_added)} ~{len(result.edges_modified)} -{len(result.edges_deleted)} edges"
        )

        return result

    def _is_modified(self, old_node: NodeState, new_node: NodeState) -> bool:
        """
        Check if a node has been modified.

        Uses multiple checks to reduce false positives:
        - Content hash (primary)
        - Modification timestamp
        - File size

        Returns True if ANY check indicates modification.
        """
        modified = False

        # Hash check (most reliable)
        if self.hash_check:
            if old_node.content_hash and new_node.content_hash:
                if old_node.content_hash != new_node.content_hash:
                    modified = True

        # Timestamp check (quick but may have false positives)
        if self.timestamp_check and not modified:
            if old_node.modified_time and new_node.modified_time:
                # Allow 1 second tolerance for filesystem precision
                if abs(old_node.modified_time - new_node.modified_time) > 1.0:
                    modified = True

        # Size check (quick sanity check)
        if self.size_check and not modified:
            if old_node.size_bytes != new_node.size_bytes:
                modified = True

        return modified

    async def _diff_edges(
        self,
        old_snapshot: MemorySnapshot,
        new_snapshot: MemorySnapshot
    ) -> tuple:
        """
        Calculate edge changes.

        Returns:
            (added_edges, modified_edges, deleted_edges)
        """
        added = []
        modified = []
        deleted = []

        old_edges = {(e.source, e.target): e for e in old_snapshot.edges.values()}
        new_edges = {(e.source, e.target): e for e in new_snapshot.edges.values()}

        old_edge_keys = set(old_edges.keys())
        new_edge_keys = set(new_edges.keys())

        # Added edges
        for key in new_edge_keys - old_edge_keys:
            new_edge = new_edges[key]
            added.append(EdgeChange(
                source=key[0],
                target=key[1],
                old_score=None,
                new_score=new_edge.dep_score,
                change_type="added"
            ))

        # Deleted edges
        for key in old_edge_keys - new_edge_keys:
            old_edge = old_edges[key]
            deleted.append(EdgeChange(
                source=key[0],
                target=key[1],
                old_score=old_edge.dep_score,
                new_score=None,
                change_type="deleted"
            ))

        # Modified edges (score changed)
        for key in old_edge_keys & new_edge_keys:
            old_edge = old_edges[key]
            new_edge = new_edges[key]

            # Check if score changed significantly (> 0.01 difference)
            if abs(old_edge.dep_score - new_edge.dep_score) > 0.01:
                modified.append(EdgeChange(
                    source=key[0],
                    target=key[1],
                    old_score=old_edge.dep_score,
                    new_score=new_edge.dep_score,
                    change_type="modified"
                ))

        return added, modified, deleted

    async def quick_diff(
        self,
        old_snapshot: MemorySnapshot,
        new_snapshot: MemorySnapshot
    ) -> Dict[str, int]:
        """
        Quick diff that only returns counts (faster).

        Useful for checking if sync is needed before full diff.

        Returns:
            Dict with change counts
        """
        old_paths = set(old_snapshot.nodes.keys())
        new_paths = set(new_snapshot.nodes.keys())

        added_count = len(new_paths - old_paths)
        deleted_count = len(old_paths - new_paths)

        # Quick modified check (only hash comparison)
        modified_count = 0
        for path in old_paths & new_paths:
            old_hash = old_snapshot.file_hashes.get(path, '')
            new_hash = new_snapshot.file_hashes.get(path, '')
            if old_hash != new_hash:
                modified_count += 1

        return {
            'added': added_count,
            'modified': modified_count,
            'deleted': deleted_count,
            'total': added_count + modified_count + deleted_count,
            'needs_sync': (added_count + modified_count + deleted_count) > 0
        }


class DiffApplier:
    """
    Applies DiffResult to memory system.

    Handles:
    - Adding new nodes to Qdrant
    - Updating modified nodes
    - Moving deleted nodes to Trash (NOT immediate delete!)
    """

    def __init__(
        self,
        qdrant_client=None,
        trash_manager=None
    ):
        """
        Initialize diff applier.

        Args:
            qdrant_client: QdrantVetkaClient for memory operations
            trash_manager: TrashMemory for soft deletes
        """
        self.qdrant = qdrant_client
        self.trash = trash_manager

    async def apply(
        self,
        diff: DiffResult,
        auto_trash: bool = True
    ) -> Dict[str, int]:
        """
        Apply diff changes to memory.

        Args:
            diff: DiffResult from MemoryDiff
            auto_trash: If True, automatically move deleted to trash

        Returns:
            Dict with applied change counts
        """
        applied = {
            'added': 0,
            'modified': 0,
            'trashed': 0,
            'errors': 0
        }

        # Apply additions
        for path, node in diff.added.items():
            try:
                await self._add_node(node)
                applied['added'] += 1
            except Exception as e:
                logger.error(f"[DiffApplier] Error adding {path}: {e}")
                applied['errors'] += 1

        # Apply modifications
        for path, node in diff.modified.items():
            try:
                await self._update_node(node)
                applied['modified'] += 1
            except Exception as e:
                logger.error(f"[DiffApplier] Error updating {path}: {e}")
                applied['errors'] += 1

        # Move deleted to trash (NOT permanent delete!)
        if auto_trash:
            for path, node in diff.deleted.items():
                try:
                    await self._move_to_trash(node)
                    applied['trashed'] += 1
                except Exception as e:
                    logger.error(f"[DiffApplier] Error trashing {path}: {e}")
                    applied['errors'] += 1

        logger.info(
            f"[DiffApplier] Applied: +{applied['added']} ~{applied['modified']} "
            f"→trash:{applied['trashed']} errors:{applied['errors']}"
        )

        return applied

    async def _add_node(self, node: NodeState):
        """Add node to Qdrant."""
        if not self.qdrant:
            return

        # Implementation depends on QdrantVetkaClient interface
        # This is a placeholder for the actual implementation
        pass

    async def _update_node(self, node: NodeState):
        """Update node in Qdrant."""
        if not self.qdrant:
            return

        # Implementation depends on QdrantVetkaClient interface
        pass

    async def _move_to_trash(self, node: NodeState):
        """Move node to trash (soft delete)."""
        if not self.trash:
            return

        # Will be implemented in Phase 77.6
        pass


# ========== FACTORY FUNCTIONS ==========

def get_memory_diff(
    hash_check: bool = True,
    timestamp_check: bool = True,
    size_check: bool = True
) -> MemoryDiff:
    """Get a MemoryDiff instance."""
    return MemoryDiff(
        hash_check=hash_check,
        timestamp_check=timestamp_check,
        size_check=size_check
    )


def get_diff_applier(
    qdrant_client=None,
    trash_manager=None
) -> DiffApplier:
    """Get a DiffApplier instance."""
    return DiffApplier(
        qdrant_client=qdrant_client,
        trash_manager=trash_manager
    )
