"""
VETKA Phase 36.1 - Unified Embedding Service

@file embedding_service.py
@status ACTIVE
@phase Phase 36.1 → 118.1
@description Unified embedding service for all VETKA components
@usedBy memory_manager.py, cam_engine.py, semantic_tagger.py, embedding_pipeline.py, triple_write_manager.py
@lastAudit 2026-02-07
"""

from typing import Optional, List
import asyncio
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Singleton embedding service.
    Centralizes all embedding generation to avoid duplication.
    """

    _instance = None
    _initialized = False

    def __new__(cls, model: str = "embeddinggemma:300m"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model: str = "embeddinggemma:300m"):
        if self._initialized:
            return
        self.model = model
        self._cache = {}  # Simple cache: hash(text) -> embedding
        self._cache_hits = 0
        self._cache_misses = 0
        self._initialized = True
        logger.info(f"EmbeddingService initialized with model: {model}")

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text (sync wrapper for backward compat).
        Uses caching to avoid redundant API calls.
        """
        if not text or not text.strip():
            return None

        # Check cache
        cache_key = hash(text) % 100000
        if cache_key in self._cache:
            self._cache_hits += 1
            return self._cache[cache_key]

        self._cache_misses += 1

        try:
            import ollama
            # MARKER_118.1: Keep sync version for callers that aren't async yet
            result = ollama.embeddings(model=self.model, prompt=text)
            embedding = result.get("embedding")

            if embedding:
                self._cache[cache_key] = embedding
                return embedding
            return None

        except Exception as e:
            logger.debug(f"Embedding generation failed: {e}")
            return None

    async def get_embedding_async(self, text: str) -> Optional[List[float]]:
        """
        MARKER_118.1: Async embedding — does NOT block event loop.
        Uses asyncio.to_thread to wrap sync ollama call.
        """
        if not text or not text.strip():
            return None

        # Check cache (cache lookup is instant, no need for async)
        cache_key = hash(text) % 100000
        if cache_key in self._cache:
            self._cache_hits += 1
            return self._cache[cache_key]

        self._cache_misses += 1

        try:
            import ollama
            # MARKER_118.1: Run sync ollama call in thread pool — non-blocking!
            result = await asyncio.to_thread(ollama.embeddings, model=self.model, prompt=text)
            embedding = result.get("embedding")

            if embedding:
                self._cache[cache_key] = embedding
                return embedding
            return None

        except Exception as e:
            logger.debug(f"Async embedding generation failed: {e}")
            return None

    def get_embedding_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Batch embedding (sync) for backward compat.
        Phase 111.18: Uses ollama.embed() with input list.
        """
        if not texts:
            return []

        valid_texts = []
        valid_indices = []
        results = [None] * len(texts)

        for i, text in enumerate(texts):
            if text and text.strip():
                cache_key = hash(text) % 100000
                if cache_key in self._cache:
                    self._cache_hits += 1
                    results[i] = self._cache[cache_key]
                else:
                    valid_texts.append(text)
                    valid_indices.append(i)

        if not valid_texts:
            return results

        self._cache_misses += len(valid_texts)

        try:
            import ollama
            # MARKER_118.1: Sync batch — kept for backward compat
            response = ollama.embed(model=self.model, input=valid_texts)
            embeddings = response.get("embeddings", [])

            for idx, emb in zip(valid_indices, embeddings):
                if emb:
                    results[idx] = emb
                    cache_key = hash(texts[idx]) % 100000
                    self._cache[cache_key] = emb

            logger.debug(f"Batch embedded {len(valid_texts)} texts in single call")
            return results

        except Exception as e:
            logger.warning(f"Batch embedding failed, falling back to individual: {e}")
            for idx in valid_indices:
                results[idx] = self.get_embedding(texts[idx])
            return results

    async def get_embedding_batch_async(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        MARKER_118.1: Async batch embedding — does NOT block event loop.
        Uses asyncio.to_thread to wrap sync ollama.embed() call.
        """
        if not texts:
            return []

        valid_texts = []
        valid_indices = []
        results = [None] * len(texts)

        for i, text in enumerate(texts):
            if text and text.strip():
                cache_key = hash(text) % 100000
                if cache_key in self._cache:
                    self._cache_hits += 1
                    results[i] = self._cache[cache_key]
                else:
                    valid_texts.append(text)
                    valid_indices.append(i)

        if not valid_texts:
            return results

        self._cache_misses += len(valid_texts)

        try:
            import ollama
            # MARKER_118.1: Run sync ollama.embed() in thread pool — non-blocking!
            response = await asyncio.to_thread(ollama.embed, model=self.model, input=valid_texts)
            embeddings = response.get("embeddings", [])

            for idx, emb in zip(valid_indices, embeddings):
                if emb:
                    results[idx] = emb
                    cache_key = hash(texts[idx]) % 100000
                    self._cache[cache_key] = emb

            logger.debug(f"Async batch embedded {len(valid_texts)} texts in single call")
            return results

        except Exception as e:
            logger.warning(f"Async batch embedding failed, falling back to individual: {e}")
            for idx in valid_indices:
                results[idx] = await self.get_embedding_async(texts[idx])
            return results

    def get_stats(self) -> dict:
        """Return cache statistics."""
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0
        return {
            "cache_size": len(self._cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": f"{hit_rate:.2%}"
        }

    def clear_cache(self):
        """Clear the embedding cache."""
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        logger.info("Embedding cache cleared")


# Global instance for easy import
_embedding_service = None


def get_embedding_service(model: str = "embeddinggemma:300m") -> EmbeddingService:
    """Get or create the singleton embedding service."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(model=model)
    return _embedding_service


def get_embedding(text: str) -> Optional[List[float]]:
    """Convenience function - get embedding using default service."""
    return get_embedding_service().get_embedding(text)


async def get_embedding_async(text: str) -> Optional[List[float]]:
    """MARKER_118.1: Async convenience function — non-blocking embedding."""
    return await get_embedding_service().get_embedding_async(text)
