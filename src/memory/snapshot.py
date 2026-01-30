"""
VETKA Phase 77.1 - Memory Snapshot
Unified representation for memory sync operations

@file snapshot.py
@status ACTIVE
@phase Phase 77.1 - Memory Sync Protocol
@calledBy MemoryDiff, MemorySyncEngine
@lastAudit 2026-01-20

Core dataclasses for representing VETKA memory state at a point in time.
Used for diff calculation and sync operations.
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Literal
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class NodeState:
    """
    State of a single knowledge node in VETKA memory.

    Represents a file/document with its embedding and metadata.
    Tracks memory layer (active/archived/trash) and confidence.
    """
    path: str
    embedding: List[float]  # 768D by default, can be compressed
    embedding_dim: int = 768
    content_hash: str = ""
    import_depth: int = 0  # Distance from root in dependency graph
    confidence: float = 1.0  # Decay factor based on age/relevance
    timestamp: datetime = field(default_factory=datetime.now)
    memory_layer: Literal["active", "archived", "trash"] = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Additional tracking
    name: str = ""
    extension: str = ""
    size_bytes: int = 0
    modified_time: float = 0.0
    created_time: float = 0.0

    def __post_init__(self):
        """Ensure timestamp is datetime."""
        if isinstance(self.timestamp, str):
            try:
                self.timestamp = datetime.fromisoformat(self.timestamp)
            except ValueError:
                self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dict."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NodeState':
        """Create from dict."""
        return cls(**data)

    @classmethod
    def from_scanned_file(cls, scanned_file, embedding: List[float]) -> 'NodeState':
        """
        Create NodeState from LocalScanner's ScannedFile.

        Args:
            scanned_file: ScannedFile from local_scanner.py
            embedding: 768D vector from embedding model

        Returns:
            NodeState instance
        """
        return cls(
            path=scanned_file.path,
            embedding=embedding,
            embedding_dim=len(embedding),
            content_hash=scanned_file.content_hash,
            timestamp=datetime.fromtimestamp(scanned_file.modified_time),
            name=scanned_file.name,
            extension=scanned_file.extension,
            size_bytes=scanned_file.size_bytes,
            modified_time=scanned_file.modified_time,
            created_time=scanned_file.created_time,
            metadata={
                'parent_folder': scanned_file.parent_folder,
                'depth': scanned_file.depth
            }
        )


@dataclass
class EdgeState:
    """
    State of a dependency edge between two nodes.

    Represents import/reference relationships with DEP score.
    """
    source: str  # Source node path (the dependency)
    target: str  # Target node path (depends on source)
    dep_score: float  # 0-1 from DEP formula
    edge_type: str = "import_dependency"  # import_dependency, semantic, reference
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EdgeState':
        """Create from dict."""
        return cls(**data)

    @property
    def edge_id(self) -> str:
        """Unique identifier for this edge."""
        return f"{self.source}→{self.target}"


@dataclass
class EdgeChange:
    """
    Represents a change in an edge during diff.
    """
    source: str
    target: str
    old_score: Optional[float]  # None if edge was added
    new_score: Optional[float]  # None if edge was deleted
    change_type: Literal["added", "modified", "deleted"] = "modified"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MemorySnapshot:
    """
    Complete snapshot of VETKA memory state at a point in time.

    Used for:
    - Diff calculation (old snapshot vs new snapshot)
    - Backup/restore operations
    - Memory sync with user confirmation

    Contains all nodes, edges, and metadata needed for
    incremental sync operations.
    """
    snapshot_id: str
    created_at: datetime
    source: Literal["filesystem", "web", "user", "memory"] = "memory"

    # Core data
    nodes: Dict[str, NodeState] = field(default_factory=dict)  # path → NodeState
    edges: Dict[str, EdgeState] = field(default_factory=dict)  # edge_id → EdgeState

    # Quick lookup hashes for diff
    file_hashes: Dict[str, str] = field(default_factory=dict)  # path → content_hash
    timestamps: Dict[str, float] = field(default_factory=dict)  # path → modified_time

    # Layout data for 3D tree (optional)
    layout_positions: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)

    # Computed once, cached
    _graph_hash: Optional[str] = field(default=None, repr=False)

    def __post_init__(self):
        """Ensure created_at is datetime."""
        if isinstance(self.created_at, str):
            try:
                self.created_at = datetime.fromisoformat(self.created_at)
            except ValueError:
                self.created_at = datetime.now()

    @property
    def dep_graph_hash(self) -> str:
        """
        Hash of the dependency graph structure.

        Used for quick comparison of graph topology.
        """
        if self._graph_hash is None:
            # Hash based on sorted edge keys and scores
            edge_data = sorted([
                (e.source, e.target, round(e.dep_score, 3))
                for e in self.edges.values()
            ])
            self._graph_hash = hashlib.md5(
                json.dumps(edge_data).encode()
            ).hexdigest()[:16]
        return self._graph_hash

    def __hash__(self) -> int:
        """
        Hash for quick state comparison.

        Based on node count, edge count, and graph hash.
        """
        state_str = json.dumps({
            'nodes': len(self.nodes),
            'edges': len(self.edges),
            'graph_hash': self.dep_graph_hash
        })
        return int(hashlib.sha256(state_str.encode()).hexdigest()[:16], 16)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dict."""
        return {
            'snapshot_id': self.snapshot_id,
            'created_at': self.created_at.isoformat(),
            'source': self.source,
            'nodes': {k: v.to_dict() for k, v in self.nodes.items()},
            'edges': {k: v.to_dict() for k, v in self.edges.items()},
            'file_hashes': self.file_hashes,
            'timestamps': self.timestamps,
            'layout_positions': self.layout_positions,
            'dep_graph_hash': self.dep_graph_hash
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemorySnapshot':
        """Create from dict."""
        snapshot = cls(
            snapshot_id=data['snapshot_id'],
            created_at=data['created_at'],
            source=data.get('source', 'memory'),
            file_hashes=data.get('file_hashes', {}),
            timestamps=data.get('timestamps', {}),
            layout_positions=data.get('layout_positions', {})
        )

        # Deserialize nodes
        for path, node_data in data.get('nodes', {}).items():
            snapshot.nodes[path] = NodeState.from_dict(node_data)

        # Deserialize edges
        for edge_id, edge_data in data.get('edges', {}).items():
            snapshot.edges[edge_id] = EdgeState.from_dict(edge_data)

        return snapshot

    def add_node(self, node: NodeState):
        """Add or update a node in the snapshot."""
        self.nodes[node.path] = node
        self.file_hashes[node.path] = node.content_hash
        self.timestamps[node.path] = node.modified_time
        # Invalidate graph hash cache
        self._graph_hash = None

    def remove_node(self, path: str) -> Optional[NodeState]:
        """Remove a node from the snapshot."""
        node = self.nodes.pop(path, None)
        self.file_hashes.pop(path, None)
        self.timestamps.pop(path, None)
        # Also remove related edges
        edges_to_remove = [
            eid for eid, edge in self.edges.items()
            if edge.source == path or edge.target == path
        ]
        for eid in edges_to_remove:
            del self.edges[eid]
        # Invalidate graph hash cache
        self._graph_hash = None
        return node

    def add_edge(self, edge: EdgeState):
        """Add or update an edge in the snapshot."""
        self.edges[edge.edge_id] = edge
        self._graph_hash = None

    def remove_edge(self, source: str, target: str) -> Optional[EdgeState]:
        """Remove an edge from the snapshot."""
        edge_id = f"{source}→{target}"
        edge = self.edges.pop(edge_id, None)
        self._graph_hash = None
        return edge

    def get_node_age_days(self, path: str) -> int:
        """Get age of a node in days."""
        node = self.nodes.get(path)
        if not node:
            return 0
        delta = datetime.now() - node.timestamp
        return delta.days

    def get_nodes_by_layer(self, layer: str) -> List[NodeState]:
        """Get all nodes in a memory layer."""
        return [n for n in self.nodes.values() if n.memory_layer == layer]

    def get_nodes_older_than(self, days: int) -> List[NodeState]:
        """Get nodes older than specified days."""
        cutoff = datetime.now()
        return [
            n for n in self.nodes.values()
            if (cutoff - n.timestamp).days > days
        ]

    @property
    def stats(self) -> Dict[str, Any]:
        """Get snapshot statistics."""
        layers = {'active': 0, 'archived': 0, 'trash': 0}
        for node in self.nodes.values():
            layers[node.memory_layer] = layers.get(node.memory_layer, 0) + 1

        return {
            'snapshot_id': self.snapshot_id,
            'total_nodes': len(self.nodes),
            'total_edges': len(self.edges),
            'layers': layers,
            'created_at': self.created_at.isoformat(),
            'graph_hash': self.dep_graph_hash
        }


class SnapshotBuilder:
    """
    Builder for creating MemorySnapshot from various sources.

    Usage:
        builder = SnapshotBuilder()
        snapshot = await builder.from_filesystem("/path/to/project")
        # or
        snapshot = await builder.from_qdrant(qdrant_client)
    """

    def __init__(self, embedding_model=None):
        """
        Initialize builder.

        Args:
            embedding_model: Model for generating embeddings (optional)
        """
        self.embedding_model = embedding_model

    async def from_filesystem(
        self,
        root_path: str,
        max_files: int = 10000
    ) -> MemorySnapshot:
        """
        Create snapshot from filesystem scan.

        Args:
            root_path: Directory to scan
            max_files: Maximum files to include

        Returns:
            MemorySnapshot of current filesystem state
        """
        import uuid
        from src.scanners.local_scanner import LocalScanner

        snapshot = MemorySnapshot(
            snapshot_id=str(uuid.uuid4())[:8],
            created_at=datetime.now(),
            source="filesystem"
        )

        scanner = LocalScanner(root_path, max_files=max_files)

        for scanned_file in scanner.scan():
            # Create node (embedding will be empty if no model)
            embedding = await self._get_embedding(scanned_file.content) if self.embedding_model else []

            node = NodeState(
                path=scanned_file.path,
                embedding=embedding,
                embedding_dim=len(embedding) if embedding else 0,
                content_hash=scanned_file.content_hash,
                timestamp=datetime.fromtimestamp(scanned_file.modified_time),
                name=scanned_file.name,
                extension=scanned_file.extension,
                size_bytes=scanned_file.size_bytes,
                modified_time=scanned_file.modified_time,
                created_time=scanned_file.created_time,
                metadata={
                    'parent_folder': scanned_file.parent_folder,
                    'depth': scanned_file.depth
                }
            )

            snapshot.add_node(node)

        logger.info(f"[SnapshotBuilder] Created snapshot from FS: {len(snapshot.nodes)} nodes")
        return snapshot

    async def from_qdrant(
        self,
        qdrant_client,
        collection: str = "vetka_elisya"
    ) -> MemorySnapshot:
        """
        Create snapshot from Qdrant collection.

        Args:
            qdrant_client: QdrantVetkaClient instance
            collection: Collection name to snapshot

        Returns:
            MemorySnapshot of current Qdrant state
        """
        import uuid

        snapshot = MemorySnapshot(
            snapshot_id=str(uuid.uuid4())[:8],
            created_at=datetime.now(),
            source="memory"
        )

        try:
            client = getattr(qdrant_client, 'client', qdrant_client)
            if not client:
                return snapshot

            # Scroll all points
            points, _ = client.scroll(
                collection_name=collection,
                limit=10000,
                with_payload=True,
                with_vectors=True
            )

            for point in points:
                payload = point.payload or {}
                path = payload.get('path', str(point.id))

                node = NodeState(
                    path=path,
                    embedding=point.vector if point.vector else [],
                    embedding_dim=len(point.vector) if point.vector else 0,
                    content_hash=payload.get('content_hash', ''),
                    timestamp=datetime.fromtimestamp(payload.get('modified_time', 0)) if payload.get('modified_time') else datetime.now(),
                    name=payload.get('name', ''),
                    extension=payload.get('extension', ''),
                    size_bytes=payload.get('size_bytes', 0),
                    modified_time=payload.get('modified_time', 0),
                    created_time=payload.get('created_time', 0),
                    metadata=payload.get('metadata', {})
                )

                snapshot.add_node(node)

            logger.info(f"[SnapshotBuilder] Created snapshot from Qdrant: {len(snapshot.nodes)} nodes")

        except Exception as e:
            logger.error(f"[SnapshotBuilder] Error creating snapshot from Qdrant: {e}")

        return snapshot

    async def _get_embedding(self, content: str) -> List[float]:
        """Get embedding for content."""
        if not self.embedding_model:
            return []

        try:
            # Assume embedding_model has an embed method
            return await self.embedding_model.embed(content)
        except Exception as e:
            logger.warning(f"[SnapshotBuilder] Embedding failed: {e}")
            return []


# ========== FACTORY FUNCTIONS ==========

def create_empty_snapshot(source: str = "memory") -> MemorySnapshot:
    """Create an empty snapshot."""
    import uuid
    return MemorySnapshot(
        snapshot_id=str(uuid.uuid4())[:8],
        created_at=datetime.now(),
        source=source
    )


def get_snapshot_builder(embedding_model=None) -> SnapshotBuilder:
    """Get a SnapshotBuilder instance."""
    return SnapshotBuilder(embedding_model=embedding_model)
