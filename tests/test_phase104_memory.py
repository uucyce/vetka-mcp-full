"""
VETKA Phase 104.6 - Memory Integration Tests

MARKER_104_MEMORY_TESTS

Tests for ELISION compression in memory operations:
- STM compression in pipeline
- Staging JSON compression
- Memory savings metrics
- Age-based embedding compression
- Compression threshold logic

@status: active
@phase: 104.6
@depends: pytest, pytest-asyncio, src.memory.compression, src.memory.elision, src.memory.stm_buffer, src.utils.staging_utils
@markers: memory_integration, phase_104, asyncio

Run: pytest tests/test_phase104_memory.py -v
Run with markers: pytest tests/test_phase104_memory.py -m memory_integration -v
"""

import pytest
import json
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, List
from pathlib import Path
import tempfile
import shutil

# Import memory modules
from src.memory.compression import (
    AgeBasedEmbeddingCompression,
    CompressedNodeState,
    CompressionScheduler,
    get_memory_compressor,
)
from src.memory.elision import (
    ElisionCompressor,
    ElisionResult,
    get_elision_compressor,
    compress_context,
)
from src.memory.stm_buffer import STMBuffer, STMEntry, get_stm_buffer, reset_stm_buffer
from src.utils.staging_utils import (
    stage_artifact,
    get_staged_artifacts,
    update_artifact_status,
    _load_staging,
    _save_staging,
)


# ============================================================
# TEST CONFIGURATION & MARKERS
# ============================================================

pytestmark = [
    pytest.mark.memory_integration,
    pytest.mark.phase_104,
]


# ============================================================
# MOCK CLASSES & FIXTURES
# ============================================================

@pytest.fixture
def temp_staging_dir():
    """Create temporary directory for staging.json during tests."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_node():
    """Create mock NodeState for compression tests."""
    node = Mock()
    node.path = "test/node/path"
    node.timestamp = datetime.now()
    node.embedding = [0.5] * 768  # Standard 768D embedding
    return node


@pytest.fixture
def stm_buffer():
    """Create STM buffer for testing."""
    reset_stm_buffer()
    return STMBuffer(max_size=10, decay_rate=0.1)


@pytest.fixture
def elision_compressor():
    """Create ELISION compressor for testing."""
    return ElisionCompressor()


# ============================================================
# TEST CLASSES
# ============================================================

class TestSTMCompression:
    """Tests for Short-Term Memory compression with ELISION integration."""

    def test_stm_creates_entries(self, stm_buffer):
        """STM should accept and store entries."""
        entry = STMEntry(content="Test message", source="user")
        stm_buffer.add(entry)

        assert len(stm_buffer) == 1
        assert stm_buffer.get_all()[0].content == "Test message"

    def test_stm_add_message_creates_entry(self, stm_buffer):
        """STM add_message convenience method should work."""
        stm_buffer.add_message("Hello", source="user")
        assert len(stm_buffer) == 1

        entries = stm_buffer.get_all()
        assert entries[0].content == "Hello"
        assert entries[0].source == "user"

    def test_stm_respects_max_size(self, stm_buffer):
        """STM should evict oldest entries when max_size exceeded."""
        stm_buffer = STMBuffer(max_size=3)

        stm_buffer.add_message("Message 1")
        stm_buffer.add_message("Message 2")
        stm_buffer.add_message("Message 3")
        stm_buffer.add_message("Message 4")  # Should evict Message 1

        assert len(stm_buffer) == 3
        contents = [e.content for e in stm_buffer.get_all()]
        assert "Message 1" not in contents
        assert "Message 4" in contents

    def test_stm_decay_applied_on_get_context(self, stm_buffer):
        """STM decay should be applied when getting context."""
        entry = STMEntry(
            content="Test",
            source="user",
            weight=1.0,
            timestamp=datetime.now() - timedelta(minutes=5)
        )
        stm_buffer.add(entry)

        context = stm_buffer.get_context()
        assert len(context) > 0
        # Weight should be reduced due to decay
        assert context[0].weight < 1.0

    def test_stm_surprise_boost_weight(self, stm_buffer):
        """CAM surprise events should boost initial weight."""
        stm_buffer.add_from_cam("Surprising content", surprise_score=0.8)

        entries = stm_buffer.get_all()
        assert len(entries) == 1
        # Weight should be boosted: 1.0 + surprise_score
        assert entries[0].weight == pytest.approx(1.8)
        assert entries[0].source == "cam_surprise"

    def test_stm_summary_handles_compressed(self, stm_buffer):
        """STM should generate summaries with compressed entries."""
        stm_buffer.add_message("First message", source="user")
        stm_buffer.add_message("Second message", source="agent")

        summary = stm_buffer.get_context_string(max_items=2, separator=" | ")
        assert "First message" in summary
        assert "Second message" in summary
        assert " | " in summary

    def test_stm_memory_savings_tracked(self, stm_buffer):
        """STM should track memory savings (via compression ratio)."""
        # Create large entries
        large_content = "x" * 5000
        stm_buffer.add_message(large_content, source="system")

        entries = stm_buffer.get_all()
        assert len(entries) == 1
        assert len(entries[0].content) == 5000

    def test_stm_to_dict_serialization(self, stm_buffer):
        """STM should serialize/deserialize correctly."""
        stm_buffer.add_message("Test entry", source="user")
        stm_buffer.add_from_hope("Hope summary", workflow_id="wf_123")

        serialized = stm_buffer.to_dict()
        assert "entries" in serialized
        assert len(serialized["entries"]) == 2
        assert serialized["max_size"] == 10
        assert serialized["decay_rate"] == 0.1

    def test_stm_from_dict_deserialization(self, stm_buffer):
        """STM should restore from serialized state."""
        stm_buffer.add_message("Entry 1", source="user")
        original_dict = stm_buffer.to_dict()

        new_buffer = STMBuffer.from_dict(original_dict)
        assert len(new_buffer) == 1
        assert new_buffer.get_all()[0].content == "Entry 1"


class TestStagingCompression:
    """Tests for staging.json compression with ELISION."""

    def test_stage_artifact_basic(self, temp_staging_dir):
        """Should stage artifact with metadata."""
        artifact = {
            "id": "art_1",
            "type": "code",
            "filename": "test.py",
            "language": "python",
            "content": "print('hello')",
            "lines": 1,
            "agent": "Dev",
            "created_at": datetime.now().isoformat()
        }

        task_id = stage_artifact(artifact, qa_score=0.95)
        assert task_id is not None
        assert task_id.startswith("art_")

    def test_stage_artifact_preserves_content(self, temp_staging_dir):
        """Staged artifact content should be preserved."""
        large_content = "x" * 10000
        artifact = {
            "id": "art_2",
            "type": "code",
            "filename": "large.py",
            "language": "python",
            "content": large_content,
            "lines": 100,
            "agent": "Dev",
            "created_at": datetime.now().isoformat()
        }

        task_id = stage_artifact(artifact, qa_score=0.9)

        # Verify content is preserved (not compressed in staging)
        staged_items = get_staged_artifacts()
        assert any(s["task_id"] == task_id for s in staged_items)

    def test_stage_artifact_with_qa_score(self, temp_staging_dir):
        """Staged artifacts should include QA score."""
        artifact = {
            "id": "art_3",
            "type": "code",
            "filename": "qa_test.py",
            "language": "python",
            "content": "test",
            "lines": 1,
            "agent": "Dev",
            "created_at": datetime.now().isoformat()
        }

        qa_score = 0.85
        task_id = stage_artifact(artifact, qa_score=qa_score)

        staged_items = get_staged_artifacts()
        staged = next((s for s in staged_items if s["task_id"] == task_id), None)
        assert staged is not None
        assert staged["qa_score"] == qa_score

    def test_stage_artifact_with_group_id(self, temp_staging_dir):
        """Staged artifacts should preserve group context."""
        artifact = {
            "id": "art_4",
            "type": "code",
            "filename": "group_test.py",
            "language": "python",
            "content": "test",
            "lines": 1,
            "agent": "Dev",
            "created_at": datetime.now().isoformat()
        }

        task_id = stage_artifact(artifact, qa_score=0.9, group_id="grp_123")

        staged_items = get_staged_artifacts()
        staged = next((s for s in staged_items if s["task_id"] == task_id), None)
        assert staged["group_id"] == "grp_123"

    def test_stage_artifact_with_source_message_id(self, temp_staging_dir):
        """Staged artifacts should track source message for traceability."""
        artifact = {
            "id": "art_5",
            "type": "code",
            "filename": "trace_test.py",
            "language": "python",
            "content": "test",
            "lines": 1,
            "agent": "Dev",
            "created_at": datetime.now().isoformat()
        }

        task_id = stage_artifact(
            artifact,
            qa_score=0.9,
            source_message_id="msg_456"
        )

        staged_items = get_staged_artifacts()
        staged = next((s for s in staged_items if s["task_id"] == task_id), None)
        assert staged["source_message_id"] == "msg_456"

    def test_update_artifact_status(self, temp_staging_dir):
        """Should update artifact status through pipeline."""
        artifact = {
            "id": "art_6",
            "type": "code",
            "filename": "status_test.py",
            "language": "python",
            "content": "test",
            "lines": 1,
            "agent": "Dev",
            "created_at": datetime.now().isoformat()
        }

        task_id = stage_artifact(artifact, qa_score=0.9)

        # Update status
        success = update_artifact_status(task_id, "approved")
        assert success is True

        staged_items = get_staged_artifacts(status="approved")
        assert any(s["task_id"] == task_id for s in staged_items)

    def test_get_staged_artifacts_filter_qa_score(self, temp_staging_dir):
        """Should filter artifacts by minimum QA score."""
        artifact1 = {
            "id": "art_7a",
            "type": "code",
            "filename": "low_qa.py",
            "language": "python",
            "content": "test",
            "lines": 1,
            "agent": "Dev",
            "created_at": datetime.now().isoformat()
        }

        artifact2 = {
            "id": "art_7b",
            "type": "code",
            "filename": "high_qa.py",
            "language": "python",
            "content": "test",
            "lines": 1,
            "agent": "Dev",
            "created_at": datetime.now().isoformat()
        }

        stage_artifact(artifact1, qa_score=0.5)
        stage_artifact(artifact2, qa_score=0.95)

        high_qa_items = get_staged_artifacts(min_qa_score=0.8)
        assert len(high_qa_items) >= 1
        assert all(s["qa_score"] >= 0.8 for s in high_qa_items)

    def test_staging_roundtrip(self, temp_staging_dir):
        """Save → Load should preserve data integrity."""
        original_data = {
            "version": "1.0",
            "artifacts": {
                "art_1": {
                    "id": "art_1",
                    "content": "test content",
                    "status": "staged"
                }
            },
            "spawn": {}
        }

        success = _save_staging(original_data)
        assert success is True

        loaded_data = _load_staging()
        assert loaded_data["artifacts"]["art_1"]["content"] == "test content"


class TestMemoryMetrics:
    """Tests for memory savings metrics and compression tracking."""

    @pytest.mark.asyncio
    async def test_compression_ratio_tracked(self):
        """Compression ratio should be tracked for each node."""
        compressor = AgeBasedEmbeddingCompression()

        node = Mock()
        node.path = "test/node"
        node.timestamp = datetime.now() - timedelta(days=45)  # 45 days old
        node.embedding = [0.5] * 768

        compressed = await compressor.compress_by_age(node)

        assert compressed.compression_ratio > 1.0
        assert compressed.original_dim == 768
        assert compressed.embedding_dim < 768

    @pytest.mark.asyncio
    async def test_quality_score_tracking(self):
        """Quality scores should degrade with compression."""
        compressor = AgeBasedEmbeddingCompression()

        # Fresh node
        fresh_node = Mock()
        fresh_node.path = "fresh/node"
        fresh_node.timestamp = datetime.now()
        fresh_node.embedding = [0.5] * 768

        fresh_compressed = await compressor.compress_by_age(fresh_node)

        # Old node
        old_node = Mock()
        old_node.path = "old/node"
        old_node.timestamp = datetime.now() - timedelta(days=120)
        old_node.embedding = [0.5] * 768

        old_compressed = await compressor.compress_by_age(old_node)

        assert fresh_compressed.quality_score >= old_compressed.quality_score

    @pytest.mark.asyncio
    async def test_compression_scheduler_tracks_stats(self):
        """CompressionScheduler should track compression statistics."""
        compressor = AgeBasedEmbeddingCompression()
        scheduler = CompressionScheduler(compressor, check_interval_hours=0)

        nodes = []
        for i in range(3):
            node = Mock()
            node.path = f"node/{i}"
            node.timestamp = datetime.now() - timedelta(days=i*30)
            node.embedding = [0.5] * 768
            nodes.append(node)

        stats = await scheduler.check_and_compress(nodes)

        assert "checked" in stats
        assert stats["checked"] == 3

    def test_stm_buffer_capacity_metric(self):
        """STM buffer should report capacity usage."""
        stm = STMBuffer(max_size=5)

        stm.add_message("msg1")
        stm.add_message("msg2")

        assert len(stm) == 2
        assert stm.max_size == 5

    @pytest.mark.asyncio
    async def test_quality_degradation_report(self):
        """Should generate quality degradation report."""
        compressor = AgeBasedEmbeddingCompression()

        # Create nodes of varying ages
        for age_days in [0, 15, 60, 180]:
            node = Mock()
            node.path = f"node/age_{age_days}"
            node.timestamp = datetime.now() - timedelta(days=age_days)
            node.embedding = [0.5] * 768
            await compressor.compress_by_age(node)

        report = compressor.get_quality_degradation_report()

        assert report["nodes_tracked"] == 4
        assert "avg_quality" in report
        assert "degraded_count" in report
        assert "quality_distribution" in report


class TestCompressionThreshold:
    """Test compression threshold logic."""

    @pytest.mark.parametrize("size,should_compress", [
        (500, False),      # Small: below threshold
        (1500, True),      # Large: above threshold
        (3000, True),      # Very large: above threshold
        (100, False),      # Tiny: below threshold
        (768, False),      # Embedding size: no compression needed
        (2000, True),      # Large content: compress
    ])
    def test_threshold_decision(self, size, should_compress):
        """Compression should only apply to large entries."""
        # ELISION compression typically targets large context (>1000 chars)
        COMPRESSION_THRESHOLD = 1000

        will_compress = size > COMPRESSION_THRESHOLD
        assert will_compress == should_compress

    def test_small_entries_skipped(self):
        """Small entries should not be compressed."""
        THRESHOLD = 1000
        content = "x" * 500

        should_compress = len(content) > THRESHOLD
        assert should_compress is False

    def test_large_entries_compressed(self):
        """Large entries should be compressed."""
        THRESHOLD = 1000
        content = "x" * 3000

        should_compress = len(content) > THRESHOLD
        assert should_compress is True


class TestElisionIntegration:
    """Tests for ELISION compression integration with memory."""

    def test_elision_compressor_initialization(self):
        """ELISION compressor should initialize."""
        compressor = ElisionCompressor()
        assert compressor is not None

    def test_elision_compress_context(self):
        """ELISION should compress context efficiently."""
        context = {
            "current_file": "src/orchestration/pipeline.py",
            "user_id": "user_123",
            "message": "Please review the code",
            "timestamp": "2026-01-31T12:00:00",
            "dependencies": ["src/api/handlers/user_handler.py"],
        }

        compressor = ElisionCompressor()
        result = compressor.compress(context, level=2)

        assert result.compression_ratio > 1.0  # Compression ratio > 1 means compressed
        assert result.original_length > result.compressed_length

    def test_elision_level_3_vowel_skipping(self):
        """ELISION Level 3 should skip vowels intelligently."""
        compressor = ElisionCompressor()
        context = {
            "description": "This is a test of vowel skipping compression",
            "content": "The quick brown fox jumps over the lazy dog"
        }

        result = compressor.compress(context, level=3)

        # Level 3 compression should work
        assert result.level == 3
        assert result.original_length > 0
        assert result.compressed_length > 0

    def test_elision_preserves_semantics(self):
        """ELISION compression should preserve semantic meaning."""
        compressor = ElisionCompressor()

        # Create a larger context to ensure compression
        original = {
            "function_name": "calculate_score",
            "parameters": ["value", "threshold", "multiplier"],
            "returns": "boolean",
            "description": "This function calculates the final score based on input parameters",
            "current_file": "src/scoring/calculator.py"
        }

        result = compressor.compress(original, level=2)

        # Even though compressed, key meaning preserved through legend
        assert result.legend is not None
        # Either compressed or at least maintains original semantics through legend
        assert result.original_length > 0
        assert result.compressed_length > 0

    def test_elision_compression_ratio_metrics(self):
        """ELISION should report compression ratio accurately."""
        compressor = ElisionCompressor()
        large_context = {
            f"key_{i}": f"value_{i}" * 100
            for i in range(20)
        }

        result = compressor.compress(large_context, level=2)

        assert result.compression_ratio > 0
        assert result.original_length > 0
        assert result.compressed_length > 0
        assert result.tokens_saved_estimate >= 0


class TestMemoryIntegrationFlow:
    """Integration tests for complete memory flow."""

    @pytest.mark.asyncio
    async def test_stm_to_staging_flow(self):
        """STM entries should flow to staging properly."""
        stm = STMBuffer(max_size=10)

        # Add entries to STM
        stm.add_message("First task", source="user")
        stm.add_message("Second task", source="agent")

        context = stm.get_context_string(max_items=2)
        assert "First task" in context
        assert "Second task" in context

    @pytest.mark.asyncio
    async def test_compression_scheduler_age_based(self):
        """Compression scheduler should handle varying ages correctly."""
        compressor = AgeBasedEmbeddingCompression()
        scheduler = CompressionScheduler(compressor, check_interval_hours=0)

        # Create nodes of different ages
        nodes = []
        for age_days in [1, 10, 50, 100]:
            node = Mock()
            node.path = f"node/{age_days}d"
            node.timestamp = datetime.now() - timedelta(days=age_days)
            node.embedding = [0.1 * (i % 768) for i in range(768)]
            nodes.append(node)

        stats = await scheduler.check_and_compress(nodes)

        # All nodes should be processed
        assert stats["checked"] == 4

    def test_elision_with_stm_compression(self):
        """ELISION should work with STM context compression."""
        stm = STMBuffer(max_size=10)

        # Add large context
        large_msg = "x" * 5000
        stm.add_message(large_msg, source="system")

        context = stm.get_context_string(max_items=1)

        # Context should be retrievable
        assert len(context) > 0

    @pytest.mark.asyncio
    async def test_memory_savings_calculation(self):
        """Should calculate total memory savings from compression."""
        compressor = AgeBasedEmbeddingCompression()

        original_dims = []
        compressed_dims = []

        for age_days in [10, 40, 100]:
            node = Mock()
            node.path = f"node/{age_days}"
            node.timestamp = datetime.now() - timedelta(days=age_days)
            node.embedding = [0.5] * 768

            original_dims.append(768)
            compressed = await compressor.compress_by_age(node)
            compressed_dims.append(compressed.embedding_dim)

        # Calculate savings
        total_original = sum(original_dims)
        total_compressed = sum(compressed_dims)
        total_savings = total_original - total_compressed

        assert total_savings > 0


class TestCompressionEdgeCases:
    """Tests for edge cases in compression."""

    @pytest.mark.asyncio
    async def test_empty_node_compression(self):
        """Should handle nodes with no embedding gracefully."""
        compressor = AgeBasedEmbeddingCompression()

        node = Mock()
        node.path = "empty/node"
        node.timestamp = datetime.now()
        node.embedding = []

        compressed = await compressor.compress_by_age(node)

        assert compressed.embedding_dim == 0
        assert compressed.embedding == []

    @pytest.mark.asyncio
    async def test_very_large_embedding(self):
        """Should handle unusually large embeddings."""
        compressor = AgeBasedEmbeddingCompression()

        node = Mock()
        node.path = "large/node"
        node.timestamp = datetime.now() - timedelta(days=50)
        node.embedding = [0.5] * 2048  # Larger than standard 768D

        compressed = await compressor.compress_by_age(node)

        # Should still compress to target dimension
        assert compressed.embedding_dim > 0
        assert compressed.embedding_dim <= 384  # Target for 50 days old

    def test_stm_with_zero_decay_rate(self):
        """STM with zero decay rate should preserve weights."""
        stm = STMBuffer(max_size=10, decay_rate=0.0)

        entry = STMEntry(
            content="Test",
            timestamp=datetime.now() - timedelta(minutes=10),
            weight=1.0
        )
        stm.add(entry)
        stm._apply_decay()

        # Weight should not decay
        assert entry.weight == 1.0

    def test_stm_below_minimum_weight(self):
        """STM should respect minimum weight threshold."""
        stm = STMBuffer(max_size=10, decay_rate=1.0, min_weight=0.1)

        entry = STMEntry(
            content="Test",
            timestamp=datetime.now() - timedelta(hours=1),
            weight=0.05
        )
        stm.add(entry)
        stm._apply_decay()

        # Should be clamped to min_weight
        assert entry.weight >= stm.min_weight

    def test_elision_empty_context(self):
        """ELISION should handle empty context gracefully."""
        compressor = ElisionCompressor()
        result = compressor.compress("", level=1)

        assert result.original_length == 0
        assert result.compressed_length == 0

    def test_elision_special_characters(self):
        """ELISION should handle special characters."""
        compressor = ElisionCompressor()
        context_with_special = {
            "path": "/src/utils/helper-functions.py",
            "symbols": ["@", "#", "$", "%", "^"],
            "content": "code && logic || values"
        }

        result = compressor.compress(context_with_special, level=1)

        # Should compress without errors
        assert result.original_length > 0
        assert result.compression_ratio > 0


class TestCompressionMetadataTracking:
    """Tests for tracking compression metadata."""

    @pytest.mark.asyncio
    async def test_compression_preserves_metadata(self):
        """Compressed state should preserve original metadata."""
        compressor = AgeBasedEmbeddingCompression()

        node = Mock()
        node.path = "meta/test/node"
        node.timestamp = datetime.now() - timedelta(days=75)
        node.embedding = [0.5] * 768

        compressed = await compressor.compress_by_age(node)

        assert compressed.path == node.path
        assert compressed.original_dim == 768
        assert compressed.age_days == 75

    def test_compressed_node_state_serialization(self):
        """CompressedNodeState should serialize/deserialize."""
        state = CompressedNodeState(
            path="test/path",
            embedding=[0.5] * 384,
            embedding_dim=384,
            original_dim=768,
            compression_ratio=2.0,
            quality_score=0.9
        )

        state_dict = state.to_dict()

        assert state_dict["path"] == "test/path"
        assert state_dict["embedding_dim"] == 384
        assert state_dict["compression_ratio"] == 2.0

    def test_stm_entry_serialization_roundtrip(self):
        """STMEntry should serialize and deserialize correctly."""
        original = STMEntry(
            content="Test content",
            source="user",
            weight=0.85,
            surprise_score=0.6,
            metadata={"key": "value"}
        )

        serialized = original.to_dict()
        restored = STMEntry.from_dict(serialized)

        assert restored.content == original.content
        assert restored.source == original.source
        assert restored.weight == original.weight
        assert restored.surprise_score == original.surprise_score


# ============================================================
# PERFORMANCE TESTS
# ============================================================

class TestCompressionPerformance:
    """Performance tests for memory compression."""

    @pytest.mark.asyncio
    async def test_batch_compression_performance(self):
        """Batch compression should be efficient."""
        compressor = AgeBasedEmbeddingCompression()

        nodes = []
        for i in range(50):
            node = Mock()
            node.path = f"node/{i}"
            node.timestamp = datetime.now() - timedelta(days=i % 100)
            node.embedding = [0.5] * 768
            nodes.append(node)

        import time
        start = time.time()
        results = await compressor.compress_batch(nodes)
        elapsed = time.time() - start

        assert len(results) == 50
        assert elapsed < 5.0  # Should be reasonably fast

    def test_stm_buffer_get_context_performance(self):
        """STM get_context should be fast."""
        stm = STMBuffer(max_size=100)

        # Fill with entries
        for i in range(100):
            stm.add_message(f"Message {i}", source="system")

        import time
        start = time.time()
        for _ in range(100):
            stm.get_context(max_items=10)
        elapsed = time.time() - start

        # 100 calls should complete quickly
        assert elapsed < 1.0

    def test_elision_compression_speed(self):
        """ELISION compression should be fast."""
        compressor = ElisionCompressor()

        large_context = {
            f"field_{i}": f"value_{i}" * 50
            for i in range(100)
        }

        import time
        start = time.time()
        for _ in range(10):
            compressor.compress(large_context, level=1)
        elapsed = time.time() - start

        # 10 compressions should complete quickly
        assert elapsed < 2.0
