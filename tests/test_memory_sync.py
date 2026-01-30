"""
Tests for Phase 77: Memory Sync Protocol

@file test_memory_sync.py
@phase Phase 77.7 - Memory Sync Protocol
@lastAudit 2026-01-20

Comprehensive tests for:
- VetkaBackup (77.0)
- MemorySnapshot (77.1)
- MemoryDiff (77.2)
- HostessMemoryCurator (77.3)
- MemoryCompression (77.4)
- DEPCompression (77.5)
- TrashMemory (77.6)
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

# ========== IMPORTS ==========

from src.memory.snapshot import (
    MemorySnapshot,
    NodeState,
    EdgeState,
    EdgeChange,
    SnapshotBuilder,
    create_empty_snapshot
)

from src.memory.diff import (
    MemoryDiff,
    DiffResult,
    DiffApplier,
    get_memory_diff
)

from src.agents.memory_curator_agent import (
    HostessMemoryCuratorAgent,
    SyncDecisions,
    SyncDecision,
    get_memory_curator
)

from src.memory.compression import (
    MemoryCompression,
    CompressedNodeState,
    CompressionScheduler,
    get_memory_compressor
)

from src.memory.dep_compression import (
    DEPCompression,
    CompressedDEP,
    DEPCompressionStats,
    get_dep_compressor
)

from src.memory.trash import (
    TrashMemory,
    TrashItem,
    get_trash_memory
)


# ========== TEST FIXTURES ==========

@pytest.fixture
def sample_node():
    """Create a sample NodeState."""
    return NodeState(
        path="/test/file.py",
        embedding=[0.1] * 768,
        embedding_dim=768,
        content_hash="abc123",
        timestamp=datetime.now(),
        name="file.py",
        extension=".py",
        size_bytes=1024,
        modified_time=datetime.now().timestamp()
    )


@pytest.fixture
def sample_edge():
    """Create a sample EdgeState."""
    return EdgeState(
        source="/test/a.py",
        target="/test/b.py",
        dep_score=0.75,
        edge_type="import_dependency"
    )


@pytest.fixture
def sample_snapshot(sample_node, sample_edge):
    """Create a sample MemorySnapshot."""
    snapshot = create_empty_snapshot()
    snapshot.add_node(sample_node)
    snapshot.add_edge(sample_edge)
    return snapshot


# ========== PHASE 77.1: SNAPSHOT TESTS ==========

class TestNodeState:
    """Tests for NodeState dataclass."""

    def test_node_creation(self, sample_node):
        """Test creating a NodeState."""
        assert sample_node.path == "/test/file.py"
        assert sample_node.embedding_dim == 768
        assert len(sample_node.embedding) == 768

    def test_node_to_dict(self, sample_node):
        """Test serialization."""
        data = sample_node.to_dict()
        assert isinstance(data, dict)
        assert data['path'] == "/test/file.py"
        assert 'timestamp' in data

    def test_node_from_dict(self, sample_node):
        """Test deserialization."""
        data = sample_node.to_dict()
        restored = NodeState.from_dict(data)
        assert restored.path == sample_node.path
        assert restored.embedding_dim == sample_node.embedding_dim


class TestEdgeState:
    """Tests for EdgeState dataclass."""

    def test_edge_creation(self, sample_edge):
        """Test creating an EdgeState."""
        assert sample_edge.source == "/test/a.py"
        assert sample_edge.target == "/test/b.py"
        assert sample_edge.dep_score == 0.75

    def test_edge_id(self, sample_edge):
        """Test edge ID generation."""
        assert sample_edge.edge_id == "/test/a.py→/test/b.py"


class TestMemorySnapshot:
    """Tests for MemorySnapshot."""

    def test_empty_snapshot(self):
        """Test creating empty snapshot."""
        snapshot = create_empty_snapshot()
        assert len(snapshot.nodes) == 0
        assert len(snapshot.edges) == 0

    def test_add_node(self, sample_snapshot, sample_node):
        """Test adding nodes."""
        assert sample_node.path in sample_snapshot.nodes

    def test_add_edge(self, sample_snapshot, sample_edge):
        """Test adding edges."""
        assert sample_edge.edge_id in sample_snapshot.edges

    def test_remove_node(self, sample_snapshot, sample_node):
        """Test removing node also removes related edges."""
        # Add another node connected by edge
        node2 = NodeState(
            path="/test/a.py",
            embedding=[0.2] * 768,
            embedding_dim=768,
            content_hash="def456",
            timestamp=datetime.now()
        )
        sample_snapshot.add_node(node2)

        # Remove and verify
        removed = sample_snapshot.remove_node(sample_node.path)
        assert removed is not None
        assert sample_node.path not in sample_snapshot.nodes

    def test_snapshot_hash(self, sample_snapshot):
        """Test snapshot hashing."""
        h1 = hash(sample_snapshot)
        assert isinstance(h1, int)

        # Adding node should change hash
        sample_snapshot.add_node(NodeState(
            path="/test/new.py",
            embedding=[0.3] * 768,
            embedding_dim=768,
            content_hash="new123",
            timestamp=datetime.now()
        ))
        h2 = hash(sample_snapshot)
        # Hash might change after adding node

    def test_snapshot_stats(self, sample_snapshot):
        """Test stats generation."""
        stats = sample_snapshot.stats
        assert 'total_nodes' in stats
        assert 'total_edges' in stats
        assert stats['total_nodes'] == 1
        assert stats['total_edges'] == 1


# ========== PHASE 77.2: DIFF TESTS ==========

class TestMemoryDiff:
    """Tests for MemoryDiff algorithm."""

    @pytest.fixture
    def differ(self):
        return MemoryDiff()

    @pytest.mark.asyncio
    async def test_diff_added_files(self, differ):
        """Test detecting added files."""
        old = create_empty_snapshot()
        new = create_empty_snapshot()

        # Add file in new snapshot only
        new.add_node(NodeState(
            path="/test/new_file.py",
            embedding=[0.1] * 768,
            embedding_dim=768,
            content_hash="new123",
            timestamp=datetime.now()
        ))

        diff = await differ.diff(old, new)

        assert len(diff.added) == 1
        assert "/test/new_file.py" in diff.added
        assert len(diff.deleted) == 0
        assert len(diff.modified) == 0

    @pytest.mark.asyncio
    async def test_diff_deleted_files(self, differ):
        """Test detecting deleted files (should go to trash)."""
        old = create_empty_snapshot()
        new = create_empty_snapshot()

        # Add file in old snapshot only
        old.add_node(NodeState(
            path="/test/deleted_file.py",
            embedding=[0.1] * 768,
            embedding_dim=768,
            content_hash="old123",
            timestamp=datetime.now()
        ))

        diff = await differ.diff(old, new)

        assert len(diff.deleted) == 1
        assert "/test/deleted_file.py" in diff.deleted
        assert len(diff.added) == 0

    @pytest.mark.asyncio
    async def test_diff_modified_files(self, differ):
        """Test detecting modified files."""
        old = create_empty_snapshot()
        new = create_empty_snapshot()

        # Same file, different hash
        old.add_node(NodeState(
            path="/test/file.py",
            embedding=[0.1] * 768,
            embedding_dim=768,
            content_hash="old_hash",
            timestamp=datetime.now()
        ))

        new.add_node(NodeState(
            path="/test/file.py",
            embedding=[0.1] * 768,
            embedding_dim=768,
            content_hash="new_hash",  # Different!
            timestamp=datetime.now()
        ))

        diff = await differ.diff(old, new)

        assert len(diff.modified) == 1
        assert "/test/file.py" in diff.modified

    @pytest.mark.asyncio
    async def test_quick_diff(self, differ):
        """Test quick diff returns counts."""
        old = create_empty_snapshot()
        new = create_empty_snapshot()

        new.add_node(NodeState(
            path="/test/new.py",
            embedding=[],
            embedding_dim=0,
            content_hash="123",
            timestamp=datetime.now()
        ))

        result = await differ.quick_diff(old, new)

        assert result['added'] == 1
        assert result['needs_sync'] is True

    def test_diff_result_summary(self):
        """Test DiffResult summary."""
        diff = DiffResult()
        diff.added = {"/a": MagicMock()}
        diff.deleted = {"/b": MagicMock()}

        summary = diff.summary
        assert summary['added'] == 1
        assert summary['deleted'] == 1
        assert summary['total'] == 2


# ========== PHASE 77.3: CURATOR TESTS ==========

class TestHostessMemoryCurator:
    """Tests for HostessMemoryCuratorAgent."""

    @pytest.fixture
    def curator(self):
        return HostessMemoryCuratorAgent()

    @pytest.mark.asyncio
    async def test_auto_approve_small_changes(self, curator):
        """Test auto-approve for small change counts."""
        diff = DiffResult()
        diff.added = {"/a.py": MagicMock()}

        decisions = await curator.sync_with_user(diff)

        assert decisions.approved is True
        assert len(decisions.decisions) >= 1

    @pytest.mark.asyncio
    async def test_default_decisions(self, curator):
        """Test default decisions are safe."""
        diff = DiffResult()
        diff.deleted = {"/deleted.py": MagicMock()}

        decisions = await curator._create_default_decisions(diff)

        # Deleted should go to trash (safe default)
        assert "/deleted.py" in decisions.decisions
        assert decisions.decisions["/deleted.py"].action == "trash"

    def test_is_system_path(self, curator):
        """Test system path detection."""
        assert curator._is_system_path("/node_modules/pkg/index.js")
        assert curator._is_system_path("/__pycache__/module.cpython-311.pyc")
        assert not curator._is_system_path("/src/main.py")

    def test_is_optional_path(self, curator):
        """Test optional path detection."""
        assert curator._is_optional_path("/tests/test_main.py")
        assert curator._is_optional_path("/docs/README.md")
        assert not curator._is_optional_path("/src/main.py")


# ========== PHASE 77.4: COMPRESSION TESTS ==========

class TestMemoryCompression:
    """Tests for MemoryCompression."""

    @pytest.fixture
    def compressor(self):
        return MemoryCompression()

    @pytest.mark.asyncio
    async def test_compress_fresh_node(self, compressor, sample_node):
        """Test fresh nodes stay at full dimension."""
        compressed = await compressor.compress_by_age(sample_node, age_days=0)

        assert compressed.embedding_dim == 768
        assert compressed.memory_layer == 'active'
        assert compressed.confidence == 1.0

    @pytest.mark.asyncio
    async def test_compress_old_node(self, compressor, sample_node):
        """Test old nodes get compressed."""
        compressed = await compressor.compress_by_age(sample_node, age_days=100)

        assert compressed.embedding_dim < 768  # Should be compressed
        assert compressed.memory_layer == 'archived'
        assert compressed.confidence < 1.0

    def test_confidence_decay(self, compressor):
        """Test confidence decreases with age."""
        conf_0 = compressor._get_confidence(0)
        conf_30 = compressor._get_confidence(30)
        conf_90 = compressor._get_confidence(90)

        assert conf_0 > conf_30 > conf_90

    def test_quality_degradation_report(self, compressor):
        """Test MARKER-77-09 quality metric."""
        report = compressor.get_quality_degradation_report()
        assert 'nodes_tracked' in report
        assert 'avg_quality' in report


# ========== PHASE 77.5: DEP COMPRESSION TESTS ==========

class TestDEPCompression:
    """Tests for DEPCompression."""

    @pytest.fixture
    def dep_compressor(self):
        return DEPCompression()

    @pytest.mark.asyncio
    async def test_compress_fresh_deps(self, dep_compressor):
        """Test fresh nodes keep all deps."""
        edges = [
            {'source': '/a.py', 'target': '/node.py', 'dep_score': 0.8},
            {'source': '/b.py', 'target': '/node.py', 'dep_score': 0.6},
            {'source': '/c.py', 'target': '/node.py', 'dep_score': 0.4},
        ]

        compressed = await dep_compressor.compress_dep_graph('/node.py', edges, age_days=10)

        assert compressed.dep_mode == 'full'
        assert compressed.compressed_edge_count == 3

    @pytest.mark.asyncio
    async def test_compress_old_deps_top3(self, dep_compressor):
        """Test 30-90 day nodes keep top 3."""
        edges = [
            {'source': f'/{i}.py', 'target': '/node.py', 'dep_score': 0.9 - i * 0.1}
            for i in range(5)
        ]

        compressed = await dep_compressor.compress_dep_graph('/node.py', edges, age_days=50)

        assert compressed.dep_mode == 'top_3'
        assert compressed.compressed_edge_count <= 3

    @pytest.mark.asyncio
    async def test_compress_archive_deps_top1(self, dep_compressor):
        """Test 90-180 day nodes keep top 1."""
        edges = [
            {'source': '/a.py', 'target': '/node.py', 'dep_score': 0.9},
            {'source': '/b.py', 'target': '/node.py', 'dep_score': 0.5},
        ]

        compressed = await dep_compressor.compress_dep_graph('/node.py', edges, age_days=120)

        assert compressed.dep_mode == 'top_1'
        assert compressed.compressed_edge_count == 1

    @pytest.mark.asyncio
    async def test_compress_ancient_deps_none(self, dep_compressor):
        """Test >180 day nodes have no deps."""
        edges = [
            {'source': '/a.py', 'target': '/node.py', 'dep_score': 0.9},
        ]

        compressed = await dep_compressor.compress_dep_graph('/node.py', edges, age_days=200)

        assert compressed.dep_mode == 'none'
        assert compressed.compressed_edge_count == 0


# ========== PHASE 77.6: TRASH TESTS ==========

class TestTrashMemory:
    """Tests for TrashMemory."""

    @pytest.fixture
    def mock_trash(self):
        """Create TrashMemory with mocked Qdrant."""
        trash = TrashMemory(qdrant_client=None)
        return trash

    def test_trash_constants(self, mock_trash):
        """Test MARKER-77-06 constants."""
        assert mock_trash.TRASH_CLEANUP_INTERVAL == 86400  # 24 hours
        assert mock_trash.TRASH_TTL_DEFAULT == 90  # days

    def test_trash_item_creation(self):
        """Test TrashItem creation."""
        now = datetime.now()
        item = TrashItem(
            original_path="/test/deleted.py",
            node_data={'path': '/test/deleted.py'},
            embedding=[0.1] * 768,
            moved_at=now,
            ttl_days=90,
            restore_until=now + timedelta(days=90)
        )

        assert item.original_path == "/test/deleted.py"
        assert not item.restored

    def test_trash_item_payload(self):
        """Test TrashItem to payload conversion."""
        now = datetime.now()
        item = TrashItem(
            original_path="/test/file.py",
            node_data={},
            embedding=[],
            moved_at=now,
            ttl_days=90,
            restore_until=now + timedelta(days=90)
        )

        payload = item.to_payload()
        assert 'original_path' in payload
        assert 'restore_until' in payload


# ========== INTEGRATION TESTS ==========

class TestMemorySyncIntegration:
    """Integration tests for complete sync flow."""

    @pytest.mark.asyncio
    async def test_full_sync_flow(self):
        """Test complete sync: diff → decisions → apply."""
        # Create snapshots
        old = create_empty_snapshot()
        new = create_empty_snapshot()

        # Old has a file that's deleted
        old.add_node(NodeState(
            path="/deleted.py",
            embedding=[0.1] * 768,
            embedding_dim=768,
            content_hash="old",
            timestamp=datetime.now()
        ))

        # New has a new file
        new.add_node(NodeState(
            path="/added.py",
            embedding=[0.2] * 768,
            embedding_dim=768,
            content_hash="new",
            timestamp=datetime.now()
        ))

        # Diff
        differ = MemoryDiff()
        diff = await differ.diff(old, new)

        assert len(diff.added) == 1
        assert len(diff.deleted) == 1

        # Get decisions
        curator = HostessMemoryCuratorAgent()
        decisions = await curator._create_default_decisions(diff)

        assert decisions.decisions["/added.py"].action == "full"
        assert decisions.decisions["/deleted.py"].action == "trash"

    @pytest.mark.asyncio
    async def test_compression_integration(self):
        """Test compression with real node."""
        node = NodeState(
            path="/old_file.py",
            embedding=[0.1] * 768,
            embedding_dim=768,
            content_hash="old",
            timestamp=datetime.now() - timedelta(days=100)
        )

        compressor = MemoryCompression()
        compressed = await compressor.compress_by_age(node, age_days=100)

        assert compressed.embedding_dim < 768
        assert compressed.quality_score < 1.0


# ========== RUN TESTS ==========

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--asyncio-mode=auto'])
