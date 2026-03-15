"""MARKER_181.10: Tests for chunked embedding pipeline.

Tests TextChunker + EmbeddingService.get_embedding_chunked() + QdrantUpdater integration.
Verifies that NO data is lost — all file content is embedded via chunk + mean pool.

@phase: 181.10
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# ============================================================
# TextChunker unit tests
# ============================================================

class TestTextChunker:
    """Tests for src/utils/text_chunker.py"""

    def test_import(self):
        from src.utils.text_chunker import chunk_text
        assert callable(chunk_text)

    def test_empty_text(self):
        from src.utils.text_chunker import chunk_text
        assert chunk_text("") == []
        assert chunk_text("   ") == []
        assert chunk_text(None) == []

    def test_short_text_no_chunking(self):
        from src.utils.text_chunker import chunk_text
        chunks = chunk_text("Hello world", max_chars=3000)
        assert len(chunks) == 1
        assert chunks[0] == "Hello world"

    def test_text_at_limit_no_chunking(self):
        from src.utils.text_chunker import chunk_text
        text = "a" * 3000
        chunks = chunk_text(text, max_chars=3000)
        assert len(chunks) == 1

    def test_long_text_creates_multiple_chunks(self):
        from src.utils.text_chunker import chunk_text
        text = "Word " * 2000  # ~10000 chars
        chunks = chunk_text(text, max_chars=3000, overlap=500)
        assert len(chunks) > 1, "Long text must produce multiple chunks"

    def test_all_chunks_within_limit(self):
        from src.utils.text_chunker import chunk_text
        text = "Word " * 2000
        chunks = chunk_text(text, max_chars=3000, overlap=500)
        for i, chunk in enumerate(chunks):
            # Allow slight overshoot from overlap merging
            assert len(chunk) <= 3500, f"Chunk {i} is {len(chunk)} chars (limit 3000+500 overlap)"

    def test_no_data_loss(self):
        """All words from original text must appear in at least one chunk."""
        from src.utils.text_chunker import chunk_text
        words = [f"unique_word_{i}" for i in range(200)]
        text = " ".join(words)
        chunks = chunk_text(text, max_chars=500, overlap=100)
        all_chunk_text = " ".join(chunks)
        for word in words:
            assert word in all_chunk_text, f"Word '{word}' lost during chunking"

    def test_paragraph_aware_splitting(self):
        from src.utils.text_chunker import chunk_text
        paragraphs = [f"Paragraph {i}. " * 30 for i in range(5)]
        text = "\n\n".join(paragraphs)
        chunks = chunk_text(text, max_chars=1000, overlap=200)
        assert len(chunks) >= 2

    def test_sentence_splitting_for_long_paragraphs(self):
        from src.utils.text_chunker import chunk_text
        # One giant paragraph with many sentences
        text = "This is a sentence. " * 500
        chunks = chunk_text(text, max_chars=1000, overlap=200)
        assert len(chunks) > 1

    def test_overlap_provides_context(self):
        """Consecutive chunks should share some text (overlap)."""
        from src.utils.text_chunker import chunk_text
        text = "Word " * 2000
        chunks = chunk_text(text, max_chars=1000, overlap=200)
        if len(chunks) >= 2:
            # End of chunk 0 should appear at start of chunk 1
            tail_0 = chunks[0][-100:]  # last 100 chars of chunk 0
            # At least some overlap should exist
            assert any(
                word in chunks[1][:300]
                for word in tail_0.split()
                if len(word) > 3
            ), "No overlap detected between consecutive chunks"

    def test_real_csv_file(self):
        """Test with actual CSV file that was failing before."""
        from src.utils.text_chunker import chunk_text
        csv_path = Path(__file__).parent.parent / "docs/besedii_google_drive_docs/PULSE-JEPA/pulse_cinema_matrix.csv"
        if csv_path.exists():
            content = csv_path.read_text()
            chunks = chunk_text(content, max_chars=3000)
            assert len(chunks) >= 1
            total_chars = sum(len(c) for c in chunks)
            # Total chunk content should be >= original (overlap adds extra)
            assert total_chars >= len(content) * 0.8, "Too much data lost in chunking"

    def test_real_markdown_file(self):
        """Test with actual markdown file that was failing before."""
        from src.utils.text_chunker import chunk_text
        md_path = Path(__file__).parent.parent / "docs/besedii_google_drive_docs/PULSE-JEPA/PULSE_McKee_Triangle_Calibration_v0.2.md"
        if md_path.exists():
            content = md_path.read_text()
            chunks = chunk_text(content, max_chars=3000)
            assert len(chunks) >= 2, f"14KB markdown should produce >=2 chunks, got {len(chunks)}"


# ============================================================
# EmbeddingService.get_embedding_chunked tests (mocked Ollama)
# ============================================================

class TestChunkedEmbeddingMocked:
    """Tests for get_embedding_chunked with mocked Ollama calls."""

    def teardown_method(self):
        """Reset singleton after each mocked test to prevent pollution."""
        import src.utils.embedding_service as es
        es._embedding_service = None

    def _make_fake_embedding(self, dim=768):
        """Generate a fake embedding vector."""
        import random
        return [random.random() for _ in range(dim)]

    def test_short_text_uses_fast_path(self):
        from src.utils.embedding_service import EmbeddingService
        svc = EmbeddingService(model="test")
        fake_emb = self._make_fake_embedding()

        with patch.object(svc, 'get_embedding', return_value=fake_emb) as mock:
            result = svc.get_embedding_chunked("short text", max_chars=3000)
            mock.assert_called_once_with("short text")
            assert result == fake_emb

    def test_long_text_uses_chunking(self):
        from src.utils.embedding_service import EmbeddingService
        svc = EmbeddingService(model="mock_model")
        fake_emb = self._make_fake_embedding()

        with patch.object(svc, 'get_embedding_batch', return_value=[fake_emb, fake_emb]) as mock:
            long_text = "word " * 2000  # 10KB
            result = svc.get_embedding_chunked(long_text, max_chars=3000)
            mock.assert_called_once()
            assert result is not None
            assert len(result) == 768

    def test_mean_pooling_averages_vectors(self):
        from src.utils.embedding_service import EmbeddingService
        svc = EmbeddingService(model="mock_model")

        emb1 = [1.0, 0.0, 0.0]
        emb2 = [0.0, 1.0, 0.0]
        emb3 = [0.0, 0.0, 1.0]

        with patch.object(svc, 'get_embedding_batch', return_value=[emb1, emb2, emb3]):
            long_text = "word " * 2000
            result = svc.get_embedding_chunked(long_text, max_chars=500)
            assert result is not None
            # Mean of [1,0,0], [0,1,0], [0,0,1] = [0.333, 0.333, 0.333]
            for val in result:
                assert abs(val - 1/3) < 0.01, f"Mean pooling incorrect: {result}"

    def test_empty_text_returns_none(self):
        from src.utils.embedding_service import EmbeddingService
        svc = EmbeddingService(model="test")
        assert svc.get_embedding_chunked("") is None
        assert svc.get_embedding_chunked("   ") is None

    def test_all_chunks_fail_returns_none(self):
        from src.utils.embedding_service import EmbeddingService
        svc = EmbeddingService(model="mock_model")

        with patch.object(svc, 'get_embedding_batch', return_value=[None, None]):
            long_text = "word " * 2000
            result = svc.get_embedding_chunked(long_text, max_chars=3000)
            assert result is None

    def test_partial_chunk_failure_still_works(self):
        from src.utils.embedding_service import EmbeddingService
        svc = EmbeddingService(model="mock_model")

        emb1 = [1.0, 2.0, 3.0]
        # Second chunk fails
        with patch.object(svc, 'get_embedding_batch', return_value=[emb1, None]):
            long_text = "word " * 2000
            result = svc.get_embedding_chunked(long_text, max_chars=3000)
            assert result is not None
            assert result == [1.0, 2.0, 3.0], "Single valid chunk should be the result"

    def test_convenience_function(self):
        from src.utils.embedding_service import get_embedding_chunked
        assert callable(get_embedding_chunked)


# ============================================================
# QdrantUpdater integration tests (mocked embedding)
# ============================================================

class TestQdrantUpdaterChunkedIntegration:
    """Verify QdrantUpdater._get_embedding uses chunked embedding."""

    def test_get_embedding_calls_chunked(self):
        """_get_embedding should use get_embedding_chunked, not get_embedding."""
        from src.scanners.qdrant_updater import QdrantIncrementalUpdater
        updater = QdrantIncrementalUpdater()

        fake_emb = [0.1] * 768
        with patch('src.utils.embedding_service.get_embedding_chunked', return_value=fake_emb) as mock:
            result = updater._get_embedding("test text")
            mock.assert_called_once_with("test text")
            assert result == fake_emb

    def test_embedding_fn_takes_priority(self):
        """If embedding_fn is set, it should be used instead of chunked."""
        from src.scanners.qdrant_updater import QdrantIncrementalUpdater

        custom_fn = MagicMock(return_value=[0.5] * 768)
        updater = QdrantIncrementalUpdater(embedding_fn=custom_fn)

        result = updater._get_embedding("test text")
        custom_fn.assert_called_once_with("test text")
        assert result == [0.5] * 768

    def test_no_truncation_in_update_file_embed_text(self):
        """update_file should NOT truncate content before embedding."""
        import inspect
        from src.scanners.qdrant_updater import QdrantIncrementalUpdater
        source = inspect.getsource(QdrantIncrementalUpdater.update_file)
        assert "[:8000]" not in source, "Content should NOT be truncated to 8000"
        assert "[:3800]" not in source, "Content should NOT be truncated to 3800"


# ============================================================
# Live Ollama tests (skip if Ollama not running)
# ============================================================

def _ollama_available():
    try:
        import ollama
        ollama.embeddings(model="embeddinggemma:300m", prompt="test")
        return True
    except Exception:
        return False


# NOTE: Live tests must run separately from mocked tests due to ollama httpx client state.
# Run with: pytest tests/test_phase181_chunked_embedding.py -k "Live"
@pytest.mark.skipif(not _ollama_available(), reason="Ollama not running or model not available")
class TestChunkedEmbeddingLive:
    """Live tests with actual Ollama — run only when Ollama is available."""

    def _fresh_service(self):
        """Create a fresh EmbeddingService with real model (not singleton)."""
        from src.utils.embedding_service import EmbeddingService
        return EmbeddingService(model="embeddinggemma:300m")

    def test_short_text_embeds(self):
        svc = self._fresh_service()
        result = svc.get_embedding_chunked("Hello world")
        assert result is not None
        assert len(result) == 768

    def test_long_text_embeds(self):
        """Text >4000 chars that FAILED before chunking should now work."""
        svc = self._fresh_service()
        long_text = "This is a test sentence with multiple words. " * 200  # ~9000 chars
        result = svc.get_embedding_chunked(long_text)
        assert result is not None, "Long text embedding should succeed with chunking"
        assert len(result) == 768

    def test_real_csv_embeds(self):
        """The actual CSV file that was failing."""
        svc = self._fresh_service()
        csv_path = Path(__file__).parent.parent / "docs/besedii_google_drive_docs/PULSE-JEPA/pulse_cinema_matrix.csv"
        if csv_path.exists():
            content = csv_path.read_text()
            embed_text = f"File: {csv_path.name}\n\n{content}"
            result = svc.get_embedding_chunked(embed_text)
            assert result is not None, f"CSV embedding failed for {len(content)} char file"
            assert len(result) == 768

    def test_real_markdown_embeds(self):
        """The actual markdown file that was failing."""
        svc = self._fresh_service()
        md_path = Path(__file__).parent.parent / "docs/besedii_google_drive_docs/PULSE-JEPA/PULSE_McKee_Triangle_Calibration_v0.2.md"
        if md_path.exists():
            content = md_path.read_text()
            embed_text = f"File: {md_path.name}\n\n{content}"
            result = svc.get_embedding_chunked(embed_text)
            assert result is not None, f"Markdown embedding failed for {len(content)} char file"
            assert len(result) == 768
