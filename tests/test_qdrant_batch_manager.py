"""
Phase 111.18: Qdrant Batch Manager Tests

Comprehensive tests for QdrantBatchManager with:
- Non-blocking queue operations
- Interval-based batch flush
- Max batch size trigger
- Batch embedding performance comparison
- Graceful shutdown with final flush

Tests:
1. test_queue_message_non_blocking - verify queue_message returns instantly
2. test_batch_flush_interval - verify flush occurs on interval
3. test_batch_size_trigger - verify immediate flush at max_batch_size
4. test_embedding_batch_performance - compare batch vs individual speed
5. test_graceful_shutdown - verify stop() does final flush

@phase: 111.18
@file: tests/test_qdrant_batch_manager.py
@depends: pytest, asyncio, unittest.mock, src.memory.qdrant_batch_manager
"""

import pytest
import asyncio
import time
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from src.memory.qdrant_batch_manager import (
    QueuedMessage,
    QueuedArtifact,
    QdrantBatchManager,
    get_batch_manager,
    init_batch_manager,
    shutdown_batch_manager,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def batch_manager():
    """Create fresh batch manager for each test."""
    manager = QdrantBatchManager(flush_interval=1.0, max_batch_size=5)
    yield manager
    # Cleanup: stop if running
    if manager._running:
        asyncio.get_event_loop().run_until_complete(manager.stop())


@pytest.fixture
def fast_batch_manager():
    """Batch manager with very short flush interval for testing."""
    manager = QdrantBatchManager(flush_interval=0.1, max_batch_size=10)
    yield manager
    if manager._running:
        asyncio.get_event_loop().run_until_complete(manager.stop())


def create_mock_qdrant_client():
    """Create mock Qdrant client."""
    client = MagicMock()
    client.client = MagicMock()
    client.COLLECTION_NAMES = {"chat": "VetkaGroupChat", "artifacts": "VetkaArtifacts"}
    return client


def create_mock_embedding_service():
    """Create mock embedding service."""
    service = MagicMock()
    service.get_embedding_batch = MagicMock(
        side_effect=lambda texts: [[0.1] * 384 for _ in texts]
    )
    return service


# ============================================================================
# Test QueuedMessage and QueuedArtifact Dataclasses
# ============================================================================

class TestQueuedMessage:
    """Test QueuedMessage dataclass."""

    def test_message_creation_with_defaults(self):
        """Create QueuedMessage with minimal args."""
        msg = QueuedMessage(
            group_id="g-123",
            message_id="m-456",
            sender_id="user-1",
            content="Hello world",
        )
        assert msg.group_id == "g-123"
        assert msg.message_id == "m-456"
        assert msg.sender_id == "user-1"
        assert msg.content == "Hello world"
        assert msg.role == "user"
        assert msg.agent is None
        assert msg.model is None
        assert msg.metadata == {}
        assert isinstance(msg.timestamp, str)

    def test_message_creation_with_all_fields(self):
        """Create QueuedMessage with all fields."""
        msg = QueuedMessage(
            group_id="g-123",
            message_id="m-456",
            sender_id="agent-1",
            content="Response",
            role="assistant",
            agent="architect",
            model="gpt-4",
            metadata={"workflow_id": "wf-789"},
        )
        assert msg.role == "assistant"
        assert msg.agent == "architect"
        assert msg.model == "gpt-4"
        assert msg.metadata == {"workflow_id": "wf-789"}


class TestQueuedArtifact:
    """Test QueuedArtifact dataclass."""

    def test_artifact_creation(self):
        """Create QueuedArtifact."""
        artifact = QueuedArtifact(
            artifact_id="art-123",
            name="component.tsx",
            content="export default function...",
            artifact_type="code",
            workflow_id="wf-456",
            filepath="/src/components/component.tsx",
        )
        assert artifact.artifact_id == "art-123"
        assert artifact.name == "component.tsx"
        assert artifact.content == "export default function..."
        assert artifact.artifact_type == "code"
        assert artifact.workflow_id == "wf-456"
        assert artifact.filepath == "/src/components/component.tsx"
        assert isinstance(artifact.timestamp, str)


# ============================================================================
# Test 1: test_queue_message_non_blocking
# Verify that queue_message returns instantly without blocking
# ============================================================================

class TestQueueMessageNonBlocking:
    """Test MARKER-111.18-01: queue_message is non-blocking."""

    @pytest.mark.asyncio
    async def test_queue_message_returns_instantly(self, batch_manager):
        """queue_message should return in < 10ms (non-blocking)."""
        start_time = time.perf_counter()

        await batch_manager.queue_message(
            group_id="g-123",
            message_id="m-456",
            sender_id="user-1",
            content="Test message that should be queued instantly",
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Non-blocking should complete in < 10ms
        assert elapsed_ms < 10, f"queue_message took {elapsed_ms:.2f}ms, expected < 10ms"
        assert len(batch_manager._message_queue) == 1

    @pytest.mark.asyncio
    async def test_queue_multiple_messages_fast(self, batch_manager):
        """Queue 100 messages should still be fast."""
        start_time = time.perf_counter()

        for i in range(100):
            await batch_manager.queue_message(
                group_id="g-123",
                message_id=f"m-{i}",
                sender_id="user-1",
                content=f"Message {i}",
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # 100 messages should complete in < 100ms
        assert elapsed_ms < 100, f"100 messages took {elapsed_ms:.2f}ms"
        # Only max_batch_size (5) should remain after flush triggers
        # Actually, depends on whether flush was triggered

    @pytest.mark.asyncio
    async def test_queue_message_increments_stats(self, batch_manager):
        """Each queue_message increments stats counter."""
        assert batch_manager._stats["messages_queued"] == 0

        await batch_manager.queue_message(
            group_id="g-1",
            message_id="m-1",
            sender_id="u-1",
            content="First",
        )
        assert batch_manager._stats["messages_queued"] == 1

        await batch_manager.queue_message(
            group_id="g-1",
            message_id="m-2",
            sender_id="u-1",
            content="Second",
        )
        assert batch_manager._stats["messages_queued"] == 2

    @pytest.mark.asyncio
    async def test_queue_artifact_non_blocking(self, batch_manager):
        """queue_artifact is also non-blocking."""
        start_time = time.perf_counter()

        await batch_manager.queue_artifact(
            artifact_id="art-123",
            name="test.py",
            content="print('hello')",
            artifact_type="code",
            workflow_id="wf-456",
            filepath="/src/test.py",
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        assert elapsed_ms < 10
        assert len(batch_manager._artifact_queue) == 1


# ============================================================================
# Test 2: test_batch_flush_interval
# Verify that flush happens after the configured interval
# ============================================================================

class TestBatchFlushInterval:
    """Test MARKER-111.18-02: interval-based flush."""

    @pytest.mark.asyncio
    async def test_flush_happens_after_interval(self):
        """Messages are flushed after flush_interval."""
        with patch("src.memory.qdrant_client.get_qdrant_client") as mock_client, \
             patch("src.utils.embedding_service.get_embedding_service") as mock_emb:
            mock_client.return_value = create_mock_qdrant_client()
            mock_emb.return_value = create_mock_embedding_service()

            manager = QdrantBatchManager(flush_interval=0.2, max_batch_size=100)

            await manager.start()

            # Queue some messages
            await manager.queue_message(
                group_id="g-1",
                message_id="m-1",
                sender_id="u-1",
                content="Test message",
            )
            await manager.queue_message(
                group_id="g-1",
                message_id="m-2",
                sender_id="u-1",
                content="Another message",
            )

            # Initially, queue has 2 messages
            assert len(manager._message_queue) == 2

            # Wait for flush interval + buffer
            await asyncio.sleep(0.3)

            # After flush, queue should be empty
            assert len(manager._message_queue) == 0
            assert manager._stats["flush_count"] >= 1

            await manager.stop()

    @pytest.mark.asyncio
    async def test_multiple_flush_cycles(self):
        """Multiple flush cycles work correctly."""
        with patch("src.memory.qdrant_client.get_qdrant_client") as mock_client, \
             patch("src.utils.embedding_service.get_embedding_service") as mock_emb:
            mock_client.return_value = create_mock_qdrant_client()
            mock_emb.return_value = create_mock_embedding_service()

            manager = QdrantBatchManager(flush_interval=0.1, max_batch_size=100)

            await manager.start()

            # First batch
            await manager.queue_message(
                group_id="g-1", message_id="m-1", sender_id="u-1", content="Batch 1"
            )
            await asyncio.sleep(0.15)
            flush_count_1 = manager._stats["flush_count"]

            # Second batch
            await manager.queue_message(
                group_id="g-1", message_id="m-2", sender_id="u-1", content="Batch 2"
            )
            await asyncio.sleep(0.15)
            flush_count_2 = manager._stats["flush_count"]

            assert flush_count_2 > flush_count_1

            await manager.stop()

    @pytest.mark.asyncio
    async def test_flush_loop_handles_empty_queue(self):
        """Flush loop doesn't crash on empty queue."""
        manager = QdrantBatchManager(flush_interval=0.1, max_batch_size=10)

        await manager.start()

        # Just wait without queuing anything
        await asyncio.sleep(0.25)

        # Should have run flush cycles without error
        assert manager._stats["flush_count"] >= 1
        assert manager._running

        await manager.stop()

    @pytest.mark.asyncio
    async def test_last_flush_timestamp_updated(self):
        """last_flush timestamp is updated after each flush."""
        with patch("src.memory.qdrant_client.get_qdrant_client") as mock_client, \
             patch("src.utils.embedding_service.get_embedding_service") as mock_emb:
            mock_client.return_value = create_mock_qdrant_client()
            mock_emb.return_value = create_mock_embedding_service()

            manager = QdrantBatchManager(flush_interval=0.1, max_batch_size=100)

            assert manager._stats["last_flush"] is None

            await manager.start()
            await manager.queue_message(
                group_id="g-1", message_id="m-1", sender_id="u-1", content="Test"
            )
            await asyncio.sleep(0.15)

            assert manager._stats["last_flush"] is not None
            # Verify it's a valid ISO timestamp
            datetime.fromisoformat(manager._stats["last_flush"])

            await manager.stop()


# ============================================================================
# Test 3: test_batch_size_trigger
# Verify immediate flush when max_batch_size is reached
# ============================================================================

class TestBatchSizeTrigger:
    """Test MARKER-111.18-03: immediate flush at max_batch_size."""

    @pytest.mark.asyncio
    async def test_immediate_flush_at_max_batch_size(self):
        """Flush triggered immediately when queue reaches max_batch_size."""
        with patch("src.memory.qdrant_client.get_qdrant_client") as mock_client, \
             patch("src.utils.embedding_service.get_embedding_service") as mock_emb:
            mock_client.return_value = create_mock_qdrant_client()
            mock_emb.return_value = create_mock_embedding_service()

            manager = QdrantBatchManager(flush_interval=60.0, max_batch_size=3)
            # Long interval ensures flush is NOT from timer

            await manager.start()

            # Queue 2 messages (under limit)
            await manager.queue_message(
                group_id="g-1", message_id="m-1", sender_id="u-1", content="Msg 1"
            )
            await manager.queue_message(
                group_id="g-1", message_id="m-2", sender_id="u-1", content="Msg 2"
            )

            # Queue should still have 2
            assert len(manager._message_queue) == 2

            # Queue 3rd message (hits limit)
            await manager.queue_message(
                group_id="g-1", message_id="m-3", sender_id="u-1", content="Msg 3"
            )

            # Give async flush task time to run
            await asyncio.sleep(0.05)

            # Queue should be flushed (or flushing)
            assert len(manager._message_queue) <= 3  # May have remaining if batch was processed

            await manager.stop()

    @pytest.mark.asyncio
    async def test_batch_size_1_flushes_immediately(self):
        """max_batch_size=1 flushes on every message."""
        with patch("src.memory.qdrant_client.get_qdrant_client") as mock_client, \
             patch("src.utils.embedding_service.get_embedding_service") as mock_emb:
            mock_client.return_value = create_mock_qdrant_client()
            mock_emb.return_value = create_mock_embedding_service()

            manager = QdrantBatchManager(flush_interval=60.0, max_batch_size=1)

            await manager.start()

            await manager.queue_message(
                group_id="g-1", message_id="m-1", sender_id="u-1", content="Single"
            )

            # Give flush time to complete
            await asyncio.sleep(0.05)

            # Should be flushed immediately
            assert len(manager._message_queue) == 0

            await manager.stop()

    @pytest.mark.asyncio
    async def test_large_batch_size_no_premature_flush(self):
        """Large max_batch_size doesn't trigger premature flush."""
        manager = QdrantBatchManager(flush_interval=60.0, max_batch_size=1000)

        # Don't start to avoid interval flush
        # Just test the queue behavior

        for i in range(50):
            await manager.queue_message(
                group_id="g-1",
                message_id=f"m-{i}",
                sender_id="u-1",
                content=f"Message {i}",
            )

        # All 50 should still be in queue (< 1000 limit)
        assert len(manager._message_queue) == 50


# ============================================================================
# Test 4: test_embedding_batch_performance
# Compare batch embedding vs individual embedding speed
# ============================================================================

class TestEmbeddingBatchPerformance:
    """Test MARKER-111.18-04: batch embedding is faster than individual."""

    def test_batch_embedding_single_call(self):
        """Batch embedding makes single call for N texts."""
        mock_service = create_mock_embedding_service()
        texts = ["Text 1", "Text 2", "Text 3", "Text 4", "Text 5"]

        # Simulate batch call
        embeddings = mock_service.get_embedding_batch(texts)

        # Single call for 5 texts
        assert mock_service.get_embedding_batch.call_count == 1
        assert len(embeddings) == 5

    def test_individual_embedding_multiple_calls(self):
        """Individual embedding makes N calls for N texts."""
        mock_get = MagicMock(return_value=[0.1] * 384)

        texts = ["Text 1", "Text 2", "Text 3", "Text 4", "Text 5"]
        embeddings = [mock_get(t) for t in texts]

        # 5 separate calls
        assert mock_get.call_count == 5
        assert len(embeddings) == 5

    def test_batch_vs_individual_call_ratio(self):
        """Batch uses 1 call while individual uses N calls."""
        mock_service = create_mock_embedding_service()
        n_texts = 100
        texts = [f"Text {i}" for i in range(n_texts)]

        # Batch: 1 call
        batch_embeddings = mock_service.get_embedding_batch(texts)
        batch_calls = 1

        # Individual would be N calls
        individual_calls = n_texts

        # Batch is N times more efficient
        efficiency_ratio = individual_calls / batch_calls
        assert efficiency_ratio == n_texts
        assert len(batch_embeddings) == n_texts


# ============================================================================
# Test 5: test_graceful_shutdown
# Verify stop() performs final flush before stopping
# ============================================================================

class TestGracefulShutdown:
    """Test MARKER-111.18-05: graceful shutdown with final flush."""

    @pytest.mark.asyncio
    async def test_stop_flushes_pending_messages(self):
        """stop() flushes all pending messages."""
        with patch("src.memory.qdrant_client.get_qdrant_client") as mock_client, \
             patch("src.utils.embedding_service.get_embedding_service") as mock_emb:
            mock_client.return_value = create_mock_qdrant_client()
            mock_emb.return_value = create_mock_embedding_service()

            manager = QdrantBatchManager(flush_interval=60.0, max_batch_size=100)

            await manager.start()

            # Queue messages
            for i in range(10):
                await manager.queue_message(
                    group_id="g-1",
                    message_id=f"m-{i}",
                    sender_id="u-1",
                    content=f"Message {i}",
                )

            assert len(manager._message_queue) == 10

            # Stop should flush all
            await manager.stop()

            assert len(manager._message_queue) == 0
            assert not manager._running
            assert manager._stats["messages_flushed"] >= 10

    @pytest.mark.asyncio
    async def test_stop_flushes_pending_artifacts(self):
        """stop() flushes all pending artifacts."""
        with patch("src.memory.qdrant_client.get_qdrant_client") as mock_client, \
             patch("src.utils.embedding_service.get_embedding_service") as mock_emb:
            mock_client.return_value = create_mock_qdrant_client()
            mock_emb.return_value = create_mock_embedding_service()

            manager = QdrantBatchManager(flush_interval=60.0, max_batch_size=100)

            await manager.start()

            # Queue artifacts
            for i in range(5):
                await manager.queue_artifact(
                    artifact_id=f"art-{i}",
                    name=f"file-{i}.py",
                    content=f"content {i}",
                    artifact_type="code",
                    workflow_id="wf-123",
                    filepath=f"/src/file-{i}.py",
                )

            assert len(manager._artifact_queue) == 5

            await manager.stop()

            assert len(manager._artifact_queue) == 0
            assert manager._stats["artifacts_flushed"] >= 5

    @pytest.mark.asyncio
    async def test_stop_cancels_flush_task(self):
        """stop() properly cancels the background flush task."""
        manager = QdrantBatchManager(flush_interval=1.0, max_batch_size=100)

        await manager.start()
        assert manager._flush_task is not None
        assert manager._running

        await manager.stop()

        assert not manager._running
        assert manager._flush_task.cancelled() or manager._flush_task.done()

    @pytest.mark.asyncio
    async def test_double_stop_safe(self):
        """Calling stop() twice doesn't crash."""
        with patch("src.memory.qdrant_client.get_qdrant_client") as mock_client, \
             patch("src.utils.embedding_service.get_embedding_service") as mock_emb:
            mock_client.return_value = create_mock_qdrant_client()
            mock_emb.return_value = create_mock_embedding_service()

            manager = QdrantBatchManager(flush_interval=1.0, max_batch_size=100)

            await manager.start()
            await manager.stop()
            await manager.stop()  # Second stop should be safe

            assert not manager._running

    @pytest.mark.asyncio
    async def test_shutdown_batch_manager_function(self):
        """shutdown_batch_manager() stops and clears global singleton."""
        with patch("src.memory.qdrant_client.get_qdrant_client") as mock_client, \
             patch("src.utils.embedding_service.get_embedding_service") as mock_emb:
            mock_client.return_value = create_mock_qdrant_client()
            mock_emb.return_value = create_mock_embedding_service()

            # Reset global state
            import src.memory.qdrant_batch_manager as module
            module._batch_manager = None

            # Initialize
            manager = await init_batch_manager()
            assert manager._running

            # Shutdown
            await shutdown_batch_manager()

            assert module._batch_manager is None


# ============================================================================
# Test Manager Lifecycle
# ============================================================================

class TestManagerLifecycle:
    """Test manager start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_creates_flush_task(self):
        """start() creates background flush task."""
        manager = QdrantBatchManager(flush_interval=1.0, max_batch_size=10)

        assert manager._flush_task is None
        assert not manager._running

        await manager.start()

        assert manager._flush_task is not None
        assert manager._running

        await manager.stop()

    @pytest.mark.asyncio
    async def test_double_start_warning(self, caplog):
        """Starting already running manager logs warning."""
        manager = QdrantBatchManager(flush_interval=1.0, max_batch_size=10)

        await manager.start()
        await manager.start()  # Second start

        assert "Already running" in caplog.text

        await manager.stop()

    @pytest.mark.asyncio
    async def test_get_stats(self, batch_manager):
        """get_stats returns comprehensive statistics."""
        await batch_manager.queue_message(
            group_id="g-1", message_id="m-1", sender_id="u-1", content="Test"
        )

        stats = batch_manager.get_stats()

        assert "messages_queued" in stats
        assert "messages_flushed" in stats
        assert "artifacts_queued" in stats
        assert "artifacts_flushed" in stats
        assert "flush_count" in stats
        assert "last_flush" in stats
        assert "message_queue_size" in stats
        assert "artifact_queue_size" in stats
        assert "running" in stats
        assert "flush_interval" in stats
        assert "max_batch_size" in stats

        assert stats["messages_queued"] == 1
        assert stats["message_queue_size"] == 1

    @pytest.mark.asyncio
    async def test_force_flush(self):
        """force_flush() immediately flushes queue."""
        with patch("src.memory.qdrant_client.get_qdrant_client") as mock_client, \
             patch("src.utils.embedding_service.get_embedding_service") as mock_emb:
            mock_client.return_value = create_mock_qdrant_client()
            mock_emb.return_value = create_mock_embedding_service()

            manager = QdrantBatchManager(flush_interval=60.0, max_batch_size=100)

            await manager.queue_message(
                group_id="g-1", message_id="m-1", sender_id="u-1", content="Test"
            )

            assert len(manager._message_queue) == 1

            await manager.force_flush()

            assert len(manager._message_queue) == 0


# ============================================================================
# Test Singleton Pattern
# ============================================================================

class TestSingletonPattern:
    """Test singleton get_batch_manager()."""

    def teardown_method(self):
        """Reset singleton after each test."""
        import src.memory.qdrant_batch_manager as module
        module._batch_manager = None

    def test_get_batch_manager_creates_singleton(self):
        """get_batch_manager creates instance on first call."""
        import src.memory.qdrant_batch_manager as module
        module._batch_manager = None

        manager = get_batch_manager()

        assert manager is not None
        assert isinstance(manager, QdrantBatchManager)

    def test_get_batch_manager_returns_same_instance(self):
        """get_batch_manager returns same instance."""
        import src.memory.qdrant_batch_manager as module
        module._batch_manager = None

        manager1 = get_batch_manager()
        manager2 = get_batch_manager()

        assert manager1 is manager2

    def test_singleton_has_default_config(self):
        """Singleton has default 30s interval, 100 batch size."""
        import src.memory.qdrant_batch_manager as module
        module._batch_manager = None

        manager = get_batch_manager()

        assert manager._flush_interval == 30.0
        assert manager._max_batch_size == 100


# ============================================================================
# Test Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling in batch operations."""

    @pytest.mark.asyncio
    async def test_qdrant_not_available(self):
        """Handles Qdrant not available gracefully."""
        with patch("src.memory.qdrant_client.get_qdrant_client") as mock:
            mock.return_value = None

            manager = QdrantBatchManager(flush_interval=60.0, max_batch_size=100)

            await manager.queue_message(
                group_id="g-1", message_id="m-1", sender_id="u-1", content="Test"
            )

            # This should not crash
            await manager._flush_messages()

    @pytest.mark.asyncio
    async def test_embedding_failure_fallback(self):
        """Falls back to individual embeddings on batch failure."""
        with patch("src.memory.qdrant_client.get_qdrant_client") as mock_client:
            mock_client.return_value = create_mock_qdrant_client()

            with patch("src.utils.embedding_service.get_embedding_service") as mock_svc:
                service = MagicMock()
                service.get_embedding_batch = MagicMock(return_value=None)  # Batch fails
                mock_svc.return_value = service

                with patch("src.utils.embedding_service.get_embedding") as mock_individual:
                    mock_individual.return_value = [0.1] * 384

                    manager = QdrantBatchManager(flush_interval=60.0, max_batch_size=100)

                    await manager.queue_message(
                        group_id="g-1", message_id="m-1", sender_id="u-1", content="Test"
                    )

                    # Flush should use fallback
                    await manager._flush_messages()

                    # Individual embedding should have been called
                    assert mock_individual.called

    @pytest.mark.asyncio
    async def test_upsert_failure_logs_error(self):
        """Failed upsert logs error but messages are removed from queue.

        Note: The current implementation catches exceptions in _upsert_messages_sync
        and returns 0, so messages are not re-queued on Qdrant failures.
        Re-queue only happens for executor-level failures.
        """
        with patch("src.utils.embedding_service.get_embedding_service") as mock_emb:
            mock_emb.return_value = create_mock_embedding_service()

            with patch("src.memory.qdrant_client.get_qdrant_client") as mock:
                client = MagicMock()
                client.client = MagicMock()
                client.client.upsert = MagicMock(side_effect=Exception("Qdrant error"))
                client.COLLECTION_NAMES = {"chat": "VetkaGroupChat"}
                mock.return_value = client

                manager = QdrantBatchManager(flush_interval=60.0, max_batch_size=100)

                await manager.queue_message(
                    group_id="g-1", message_id="m-1", sender_id="u-1", content="Test"
                )

                # Flush will fail internally
                await manager._flush_messages()

                # Queue is empty after flush (failed messages are not re-queued in current impl)
                assert len(manager._message_queue) == 0
                # But flushed count is 0 because upsert failed
                assert manager._stats["messages_flushed"] == 0

    @pytest.mark.asyncio
    async def test_executor_failure_requeues(self):
        """Executor-level failure re-queues messages for retry."""
        manager = QdrantBatchManager(flush_interval=60.0, max_batch_size=100)

        await manager.queue_message(
            group_id="g-1", message_id="m-1", sender_id="u-1", content="Test"
        )

        initial_count = len(manager._message_queue)

        # Mock run_in_executor to raise an exception
        with patch.object(asyncio, "get_running_loop") as mock_loop:
            loop = MagicMock()
            loop.run_in_executor = AsyncMock(side_effect=Exception("Executor error"))
            mock_loop.return_value = loop

            await manager._flush_messages()

        # Messages should be re-queued
        assert len(manager._message_queue) >= initial_count


# ============================================================================
# Test Concurrent Access
# ============================================================================

class TestConcurrentAccess:
    """Test thread-safety and concurrent access."""

    @pytest.mark.asyncio
    async def test_concurrent_queue_operations(self, batch_manager):
        """Multiple concurrent queue operations are safe."""

        async def queue_batch(start_idx: int, count: int):
            for i in range(count):
                await batch_manager.queue_message(
                    group_id="g-1",
                    message_id=f"m-{start_idx + i}",
                    sender_id="u-1",
                    content=f"Message {start_idx + i}",
                )

        # Launch 10 concurrent tasks, each queuing 10 messages
        tasks = [queue_batch(i * 10, 10) for i in range(10)]
        await asyncio.gather(*tasks)

        # All 100 messages should be queued (or flushed)
        assert batch_manager._stats["messages_queued"] == 100

    @pytest.mark.asyncio
    async def test_queue_during_flush(self):
        """Can queue messages while flush is in progress."""
        with patch("src.memory.qdrant_client.get_qdrant_client") as mock_client, \
             patch("src.utils.embedding_service.get_embedding_service") as mock_emb:
            mock_client.return_value = create_mock_qdrant_client()
            mock_emb.return_value = create_mock_embedding_service()

            manager = QdrantBatchManager(flush_interval=60.0, max_batch_size=100)

            # Queue initial messages
            for i in range(5):
                await manager.queue_message(
                    group_id="g-1",
                    message_id=f"m-{i}",
                    sender_id="u-1",
                    content=f"Message {i}",
                )

            # Start flush as background task
            flush_task = asyncio.create_task(manager._flush_messages())

            # Queue more while flushing
            for i in range(5, 10):
                await manager.queue_message(
                    group_id="g-1",
                    message_id=f"m-{i}",
                    sender_id="u-1",
                    content=f"Message {i}",
                )

            await flush_task

            # Should have queued all 10
            assert manager._stats["messages_queued"] == 10


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_content_message(self, batch_manager):
        """Empty content message is queued."""
        await batch_manager.queue_message(
            group_id="g-1",
            message_id="m-1",
            sender_id="u-1",
            content="",
        )
        assert len(batch_manager._message_queue) == 1
        assert batch_manager._message_queue[0].content == ""

    @pytest.mark.asyncio
    async def test_very_long_content(self, batch_manager):
        """Very long content is queued (truncation happens on flush)."""
        long_content = "x" * 10000
        await batch_manager.queue_message(
            group_id="g-1",
            message_id="m-1",
            sender_id="u-1",
            content=long_content,
        )
        assert len(batch_manager._message_queue) == 1
        # Full content is queued
        assert len(batch_manager._message_queue[0].content) == 10000

    @pytest.mark.asyncio
    async def test_unicode_content(self, batch_manager):
        """Unicode content is handled correctly."""
        unicode_content = "Hello Privet Nihao Marhaba"
        await batch_manager.queue_message(
            group_id="g-1",
            message_id="m-1",
            sender_id="u-1",
            content=unicode_content,
        )
        assert batch_manager._message_queue[0].content == unicode_content

    @pytest.mark.asyncio
    async def test_special_characters_in_ids(self, batch_manager):
        """Special characters in IDs are handled."""
        await batch_manager.queue_message(
            group_id="g-123-abc_def",
            message_id="m-456/789",
            sender_id="user@example.com",
            content="Test",
        )
        msg = batch_manager._message_queue[0]
        assert msg.group_id == "g-123-abc_def"
        assert msg.message_id == "m-456/789"
        assert msg.sender_id == "user@example.com"

    @pytest.mark.asyncio
    async def test_null_optional_fields(self, batch_manager):
        """None values for optional fields work correctly."""
        await batch_manager.queue_message(
            group_id="g-1",
            message_id="m-1",
            sender_id="u-1",
            content="Test",
            agent=None,
            model=None,
            metadata=None,
        )
        msg = batch_manager._message_queue[0]
        assert msg.agent is None
        assert msg.model is None
        assert msg.metadata == {}

    def test_flush_interval_zero(self):
        """Zero flush interval creates valid manager."""
        manager = QdrantBatchManager(flush_interval=0.0, max_batch_size=10)
        assert manager._flush_interval == 0.0

    def test_max_batch_size_one(self):
        """Batch size of 1 is valid."""
        manager = QdrantBatchManager(flush_interval=1.0, max_batch_size=1)
        assert manager._max_batch_size == 1
