"""
VETKA Phase 36.1 - Unified Embedding Service

@file embedding_service.py
@status ACTIVE
@phase Phase 36.1
@description Unified embedding service for all VETKA components
@usedBy memory_manager.py, cam_engine.py, semantic_tagger.py, embedding_pipeline.py, triple_write_manager.py
@lastAudit 2026-01-04
"""

from typing import Optional, List
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
        Generate embedding for text.
        Uses caching to avoid redundant API calls.

        Args:
            text: Input text to embed

        Returns:
            List of floats (embedding vector) or None on error
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
            result = ollama.embeddings(model=self.model, prompt=text)
            embedding = result.get("embedding")

            if embedding:
                # Cache it
                self._cache[cache_key] = embedding
                return embedding
            return None

        except Exception as e:
            logger.debug(f"Embedding generation failed: {e}")
            return None

    def get_embedding_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Batch embedding for multiple texts."""
        return [self.get_embedding(text) for text in texts]

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
