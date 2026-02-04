"""
Tests for VETKA Embedding Service Batch Operations

@file tests/test_embedding_batch.py
@status ACTIVE
@phase Phase 111.18
@description Tests for batch embedding functionality
@lastAudit 2026-02-04
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.embedding_service import EmbeddingService


@pytest.fixture
def fresh_embedding_service():
    """Create a fresh EmbeddingService instance for each test."""
    # Reset singleton state
    EmbeddingService._instance = None
    EmbeddingService._initialized = False
    service = EmbeddingService(model="test-model")
    yield service
    # Cleanup
    EmbeddingService._instance = None
    EmbeddingService._initialized = False


@pytest.fixture
def mock_embedding():
    """Return a mock embedding vector."""
    return [0.1, 0.2, 0.3, 0.4, 0.5]


class TestBatchSingleAPICall:
    """Test that batch makes a single API call for multiple texts."""

    def test_batch_single_api_call(self, fresh_embedding_service, mock_embedding):
        """Verify that get_embedding_batch makes exactly 1 API call for N texts."""
        texts = ["Hello world", "Test text", "Another example"]

        mock_response = {
            "embeddings": [mock_embedding, mock_embedding, mock_embedding]
        }

        with patch("ollama.embed") as mock_embed:
            mock_embed.return_value = mock_response

            results = fresh_embedding_service.get_embedding_batch(texts)

            # Should be called exactly once with all texts
            assert mock_embed.call_count == 1
            call_args = mock_embed.call_args
            assert call_args.kwargs["input"] == texts
            assert call_args.kwargs["model"] == "test-model"

            # All results should be populated
            assert len(results) == 3
            for result in results:
                assert result == mock_embedding

    def test_batch_10_texts_single_call(self, fresh_embedding_service, mock_embedding):
        """Verify batch with 10 texts still makes only 1 API call."""
        texts = [f"Text number {i}" for i in range(10)]

        mock_response = {
            "embeddings": [mock_embedding] * 10
        }

        with patch("ollama.embed") as mock_embed:
            mock_embed.return_value = mock_response

            results = fresh_embedding_service.get_embedding_batch(texts)

            assert mock_embed.call_count == 1
            assert len(results) == 10


class TestBatchCacheIntegration:
    """Test that cache works correctly in batch mode."""

    def test_batch_cache_integration(self, fresh_embedding_service, mock_embedding):
        """Verify that cached texts are not sent to API."""
        # Pre-populate cache with one text
        text_to_cache = "Cached text"
        cache_key = hash(text_to_cache) % 100000
        fresh_embedding_service._cache[cache_key] = [0.9, 0.8, 0.7]

        texts = ["New text 1", text_to_cache, "New text 2"]

        mock_response = {
            "embeddings": [mock_embedding, mock_embedding]  # Only 2 embeddings returned
        }

        with patch("ollama.embed") as mock_embed:
            mock_embed.return_value = mock_response

            results = fresh_embedding_service.get_embedding_batch(texts)

            # Only 2 texts should be sent to API (not the cached one)
            assert mock_embed.call_count == 1
            call_args = mock_embed.call_args
            assert call_args.kwargs["input"] == ["New text 1", "New text 2"]

            # Results should include cached embedding in correct position
            assert results[0] == mock_embedding  # New text 1
            assert results[1] == [0.9, 0.8, 0.7]  # Cached text
            assert results[2] == mock_embedding  # New text 2

    def test_batch_populates_cache(self, fresh_embedding_service, mock_embedding):
        """Verify that batch results are cached for future use."""
        texts = ["Text A", "Text B"]

        mock_response = {
            "embeddings": [[0.1, 0.2], [0.3, 0.4]]
        }

        with patch("ollama.embed") as mock_embed:
            mock_embed.return_value = mock_response

            fresh_embedding_service.get_embedding_batch(texts)

            # Verify cache was populated
            cache_key_a = hash("Text A") % 100000
            cache_key_b = hash("Text B") % 100000

            assert cache_key_a in fresh_embedding_service._cache
            assert cache_key_b in fresh_embedding_service._cache
            assert fresh_embedding_service._cache[cache_key_a] == [0.1, 0.2]
            assert fresh_embedding_service._cache[cache_key_b] == [0.3, 0.4]

    def test_batch_all_cached_no_api_call(self, fresh_embedding_service):
        """Verify no API call when all texts are cached."""
        texts = ["Cached 1", "Cached 2"]

        # Pre-populate cache
        for text in texts:
            cache_key = hash(text) % 100000
            fresh_embedding_service._cache[cache_key] = [0.5, 0.5]

        with patch("ollama.embed") as mock_embed:
            results = fresh_embedding_service.get_embedding_batch(texts)

            # No API call should be made
            assert mock_embed.call_count == 0

            # All results from cache
            assert results == [[0.5, 0.5], [0.5, 0.5]]


class TestBatchPreservesOrder:
    """Test that batch results maintain input order."""

    def test_batch_preserves_order(self, fresh_embedding_service):
        """Verify results are in same order as input texts."""
        texts = ["First", "Second", "Third", "Fourth"]

        # Return unique embeddings for each text
        mock_response = {
            "embeddings": [[1.0], [2.0], [3.0], [4.0]]
        }

        with patch("ollama.embed") as mock_embed:
            mock_embed.return_value = mock_response

            results = fresh_embedding_service.get_embedding_batch(texts)

            assert results[0] == [1.0]  # First
            assert results[1] == [2.0]  # Second
            assert results[2] == [3.0]  # Third
            assert results[3] == [4.0]  # Fourth

    def test_batch_preserves_order_with_mixed_cache(self, fresh_embedding_service):
        """Verify order is preserved when some texts are cached."""
        texts = ["A", "B", "C", "D", "E"]

        # Cache B and D
        fresh_embedding_service._cache[hash("B") % 100000] = [20.0]
        fresh_embedding_service._cache[hash("D") % 100000] = [40.0]

        # API returns for A, C, E
        mock_response = {
            "embeddings": [[10.0], [30.0], [50.0]]
        }

        with patch("ollama.embed") as mock_embed:
            mock_embed.return_value = mock_response

            results = fresh_embedding_service.get_embedding_batch(texts)

            assert results[0] == [10.0]  # A - from API
            assert results[1] == [20.0]  # B - from cache
            assert results[2] == [30.0]  # C - from API
            assert results[3] == [40.0]  # D - from cache
            assert results[4] == [50.0]  # E - from API


class TestBatchHandlesEmptyTexts:
    """Test handling of empty and whitespace-only texts."""

    def test_batch_handles_empty_texts(self, fresh_embedding_service, mock_embedding):
        """Verify empty texts return None and are not sent to API."""
        texts = ["Valid text", "", "Another valid", "   ", "Final text"]

        mock_response = {
            "embeddings": [mock_embedding, mock_embedding, mock_embedding]
        }

        with patch("ollama.embed") as mock_embed:
            mock_embed.return_value = mock_response

            results = fresh_embedding_service.get_embedding_batch(texts)

            # Only valid texts sent to API
            call_args = mock_embed.call_args
            assert call_args.kwargs["input"] == ["Valid text", "Another valid", "Final text"]

            # Empty/whitespace texts return None
            assert results[0] == mock_embedding  # Valid
            assert results[1] is None  # Empty
            assert results[2] == mock_embedding  # Valid
            assert results[3] is None  # Whitespace only
            assert results[4] == mock_embedding  # Valid

    def test_batch_all_empty_returns_nones(self, fresh_embedding_service):
        """Verify all empty texts returns list of Nones without API call."""
        texts = ["", "   ", None if False else "", "\t\n"]

        with patch("ollama.embed") as mock_embed:
            results = fresh_embedding_service.get_embedding_batch(texts)

            # No API call for all empty
            assert mock_embed.call_count == 0

            # All Nones
            assert results == [None, None, None, None]

    def test_batch_empty_list_returns_empty(self, fresh_embedding_service):
        """Verify empty input list returns empty output list."""
        with patch("ollama.embed") as mock_embed:
            results = fresh_embedding_service.get_embedding_batch([])

            assert mock_embed.call_count == 0
            assert results == []


class TestBatchFallbackOnError:
    """Test fallback to individual calls when batch API fails."""

    def test_batch_fallback_on_error(self, fresh_embedding_service, mock_embedding):
        """Verify fallback to individual calls when batch fails."""
        texts = ["Text 1", "Text 2", "Text 3"]

        with patch("ollama.embed") as mock_embed, \
             patch("ollama.embeddings") as mock_individual:

            # Batch API fails
            mock_embed.side_effect = Exception("Batch API not available")

            # Individual API works
            mock_individual.return_value = {"embedding": mock_embedding}

            results = fresh_embedding_service.get_embedding_batch(texts)

            # Batch was attempted
            assert mock_embed.call_count == 1

            # Fallback to individual calls
            assert mock_individual.call_count == 3

            # All results should be populated
            assert all(r == mock_embedding for r in results)

    def test_batch_fallback_uses_cache(self, fresh_embedding_service, mock_embedding):
        """Verify fallback respects cache when calling individually."""
        texts = ["Cached", "Not cached"]

        # Cache first text
        fresh_embedding_service._cache[hash("Cached") % 100000] = [0.1, 0.2]

        with patch("ollama.embed") as mock_embed, \
             patch("ollama.embeddings") as mock_individual:

            # Batch API fails
            mock_embed.side_effect = Exception("Batch error")

            # Individual API for non-cached
            mock_individual.return_value = {"embedding": mock_embedding}

            results = fresh_embedding_service.get_embedding_batch(texts)

            # Only non-cached text was sent to individual API
            # Note: "Cached" was already returned from cache before batch attempt
            # So only "Not cached" goes through individual fallback
            assert mock_individual.call_count == 1

            # Results correct
            assert results[0] == [0.1, 0.2]  # From cache
            assert results[1] == mock_embedding  # From individual fallback

    def test_batch_fallback_partial_failure(self, fresh_embedding_service):
        """Verify partial failures in individual fallback still return other results."""
        texts = ["Works", "Fails", "Also works"]

        with patch("ollama.embed") as mock_embed, \
             patch("ollama.embeddings") as mock_individual:

            mock_embed.side_effect = Exception("Batch error")

            # Simulate one individual call failing
            def individual_side_effect(model, prompt):
                if "Fails" in prompt:
                    raise Exception("Individual error")
                return {"embedding": [1.0, 2.0]}

            mock_individual.side_effect = individual_side_effect

            results = fresh_embedding_service.get_embedding_batch(texts)

            assert results[0] == [1.0, 2.0]  # Works
            assert results[1] is None  # Fails
            assert results[2] == [1.0, 2.0]  # Also works


class TestBatchCacheStats:
    """Test cache statistics in batch mode."""

    def test_batch_updates_cache_stats(self, fresh_embedding_service, mock_embedding):
        """Verify cache hit/miss counters are updated correctly in batch mode."""
        # Pre-cache one text
        fresh_embedding_service._cache[hash("Cached") % 100000] = [0.5]

        texts = ["Cached", "Not cached 1", "Not cached 2"]

        mock_response = {
            "embeddings": [[0.1], [0.2]]
        }

        with patch("ollama.embed") as mock_embed:
            mock_embed.return_value = mock_response

            fresh_embedding_service.get_embedding_batch(texts)

            stats = fresh_embedding_service.get_stats()

            assert stats["cache_hits"] == 1  # "Cached" was hit
            assert stats["cache_misses"] == 2  # 2 new texts
            assert stats["cache_size"] == 3  # 1 original + 2 new


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
