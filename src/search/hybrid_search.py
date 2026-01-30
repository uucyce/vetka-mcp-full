"""
VETKA Phase 68: Hybrid Search Service

@file hybrid_search.py
@status ACTIVE
@phase Phase 68
@description Unified hybrid search combining Qdrant (semantic) + Weaviate (BM25) + RRF fusion
@usedBy semantic_routes.py (API endpoint)
@lastAudit 2026-01-18

Architecture:
1. Semantic search via Qdrant vector similarity
2. Keyword search via Weaviate BM25
3. RRF fusion to combine results
4. Configurable weights via environment variables

Fallback cascade:
- If Weaviate unavailable → pure semantic (Qdrant)
- If Qdrant unavailable → pure keyword (Weaviate BM25)
- If both unavailable → empty results with error
"""

import os
import time
import logging
import asyncio
from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor

from src.search.rrf_fusion import (
    weighted_rrf,
    normalize_results,
    compute_rrf_explanation,
)
from src.utils.embedding_service import get_embedding_service
from config.config import COLLECTIONS

logger = logging.getLogger("VETKA_HYBRID_SEARCH")

# Configurable via environment
SEMANTIC_WEIGHT = float(os.getenv("VETKA_SEMANTIC_WEIGHT", "0.5"))
KEYWORD_WEIGHT = float(os.getenv("VETKA_KEYWORD_WEIGHT", "0.3"))
GRAPH_WEIGHT = float(os.getenv("VETKA_GRAPH_WEIGHT", "0.2"))
RRF_K = int(os.getenv("VETKA_RRF_K", "60"))

# Cache configuration
HYBRID_CACHE_TTL = int(os.getenv("VETKA_HYBRID_CACHE_TTL", "300"))  # 5 minutes
_hybrid_search_cache: Dict[str, Any] = {}

# Thread pool for parallel searches
_executor = ThreadPoolExecutor(max_workers=3)


class HybridSearchService:
    """
    Unified hybrid search across all backends.

    Combines:
    - Qdrant: Semantic/vector search (primary)
    - Weaviate: BM25 keyword search + hybrid
    - RRF: Reciprocal Rank Fusion for combining results

    Usage:
        service = get_hybrid_search()
        results = await service.search("authentication flow", limit=20)
    """

    def __init__(self):
        """Initialize search service with lazy-loaded backends."""
        self._qdrant = None
        self._weaviate = None
        self._embedding_service = None
        self._initialized = False

    def _init_backends(self):
        """Lazy initialization of search backends."""
        if self._initialized:
            return

        # Import here to avoid circular imports
        try:
            from src.memory.qdrant_client import get_qdrant_client

            self._qdrant = get_qdrant_client()
            if self._qdrant and self._qdrant.health_check():
                logger.info("[HYBRID] Qdrant backend initialized")
            else:
                logger.warning("[HYBRID] Qdrant backend unavailable")
                self._qdrant = None
        except Exception as e:
            logger.warning(f"[HYBRID] Qdrant init failed: {e}")
            self._qdrant = None

        try:
            from src.memory.weaviate_helper import WeaviateHelper

            self._weaviate = WeaviateHelper()
            logger.info("[HYBRID] Weaviate backend initialized")
        except Exception as e:
            logger.warning(f"[HYBRID] Weaviate init failed: {e}")
            self._weaviate = None

        self._embedding_service = get_embedding_service()
        self._initialized = True

    @property
    def qdrant(self):
        self._init_backends()
        return self._qdrant

    @property
    def weaviate(self):
        self._init_backends()
        return self._weaviate

    @property
    def embedding_service(self):
        self._init_backends()
        return self._embedding_service

    async def search(
        self,
        query: str,
        limit: int = 100,
        mode: str = "hybrid",
        filters: Optional[Dict] = None,
        collection: str = "leaf",  # FIX_95.7: Changed default from tree to leaf (VetkaLeaf has file data)
        skip_cache: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute hybrid search with RRF fusion.

        Args:
            query: Search query string
            limit: Max results to return
            mode: Search mode - "semantic", "keyword", or "hybrid"
            filters: Optional filters (file_types, paths, etc.)
            collection: Collection to search (tree, leaf, shared)
            skip_cache: Skip cache lookup

        Returns:
            Dict with:
            - results: List of matched documents with rrf_score
            - count: Number of results
            - mode: Actual mode used
            - timing_ms: Search time in milliseconds
            - sources: Which backends were used
            - cache_hit: Whether result was from cache
        """
        start_time = time.time()
        filters = filters or {}

        # Check cache first
        cache_key = f"hybrid:{query}:{limit}:{mode}:{hash(str(filters))}"
        if not skip_cache and cache_key in _hybrid_search_cache:
            cached = _hybrid_search_cache[cache_key]
            age = time.time() - cached["timestamp"]
            if age < HYBRID_CACHE_TTL:
                logger.debug(f"[HYBRID] Cache hit for '{query}' (age: {age:.1f}s)")
                result = cached["result"].copy()
                result["cache_hit"] = True
                return result

        # Initialize backends
        self._init_backends()

        results_lists = []
        weights = []
        sources_used = []

        try:
            # Phase 68.2: Handle filename mode separately (no fusion needed)
            if mode == "filename":
                filename_results = await self._filename_search(query, limit, collection)
                elapsed_ms = (time.time() - start_time) * 1000

                # Normalize results
                for result in filename_results:
                    result["explanation"] = f"Filename match for '{query}'"
                    result["search_mode"] = "filename"

                response = {
                    "results": filename_results,
                    "count": len(filename_results),
                    "query": query,
                    "mode": "filename",
                    "requested_mode": mode,
                    "timing_ms": round(elapsed_ms, 2),
                    "sources": ["qdrant_filename"],
                    "cache_hit": False,
                    "config": {
                        "semantic_weight": SEMANTIC_WEIGHT,
                        "keyword_weight": KEYWORD_WEIGHT,
                        "rrf_k": RRF_K,
                    },
                }

                # Cache the result
                _hybrid_search_cache[cache_key] = {
                    "result": response,
                    "timestamp": time.time(),
                }

                logger.info(
                    f"[HYBRID] Filename search '{query}' → {len(filename_results)} results "
                    f"({elapsed_ms:.0f}ms)"
                )

                return response

            # Run searches in parallel using asyncio
            tasks = []

            # 1. Semantic search (Qdrant)
            if mode in ("semantic", "hybrid") and self.qdrant:
                tasks.append(
                    ("semantic", self._semantic_search(query, limit * 2, collection))
                )

            # 2. Keyword search (Weaviate BM25)
            if mode in ("keyword", "hybrid") and self.weaviate:
                tasks.append(
                    ("keyword", self._keyword_search(query, limit * 2, collection))
                )

            # Execute tasks
            if tasks:
                # Run in parallel
                task_results = await asyncio.gather(
                    *[t[1] for t in tasks], return_exceptions=True
                )

                for (task_name, _), result in zip(tasks, task_results):
                    if isinstance(result, Exception):
                        logger.warning(f"[HYBRID] {task_name} search failed: {result}")
                        continue

                    if result:
                        # Normalize results to common format
                        source = "qdrant" if task_name == "semantic" else "weaviate"
                        normalized = normalize_results(result, source)
                        if normalized:
                            results_lists.append(normalized)
                            sources_used.append(task_name)

                            # Set weight based on mode
                            if mode == "hybrid":
                                if task_name == "semantic":
                                    weights.append(SEMANTIC_WEIGHT)
                                elif task_name == "keyword":
                                    weights.append(KEYWORD_WEIGHT)
                            else:
                                weights.append(1.0)

            # 3. RRF Fusion if multiple sources
            if len(results_lists) > 1:
                fused = weighted_rrf(results_lists, weights, k=RRF_K, top_n=limit)
                actual_mode = "hybrid"
            elif len(results_lists) == 1:
                fused = results_lists[0][:limit]
                actual_mode = sources_used[0] if sources_used else mode
            else:
                fused = []
                # FIX_95.1_MODE_NONE: Preserve requested mode instead of "none"
                # This allows frontend to show correct mode even with 0 results
                actual_mode = mode  # Was: "none" - bug caused confusion in UI

            # Add explanations to results
            for result in fused:
                result["explanation"] = compute_rrf_explanation(result, query)
                result["search_mode"] = actual_mode

            # Calculate timing
            elapsed_ms = (time.time() - start_time) * 1000

            response = {
                "results": fused,
                "count": len(fused),
                "query": query,
                "mode": actual_mode,
                "requested_mode": mode,
                "timing_ms": round(elapsed_ms, 2),
                "sources": sources_used,
                "cache_hit": False,
                "config": {
                    "semantic_weight": SEMANTIC_WEIGHT,
                    "keyword_weight": KEYWORD_WEIGHT,
                    "rrf_k": RRF_K,
                },
            }

            # Cache the result
            _hybrid_search_cache[cache_key] = {
                "result": response,
                "timestamp": time.time(),
            }

            # Cleanup old cache entries (keep max 200)
            if len(_hybrid_search_cache) > 200:
                oldest = sorted(
                    _hybrid_search_cache.keys(),
                    key=lambda k: _hybrid_search_cache[k]["timestamp"],
                )[:100]
                for k in oldest:
                    del _hybrid_search_cache[k]
                logger.debug(
                    f"[HYBRID] Cache cleanup: removed {len(oldest)} old entries"
                )

            logger.info(
                f"[HYBRID] Search '{query}' → {len(fused)} results "
                f"({actual_mode}, {elapsed_ms:.0f}ms, sources={sources_used})"
            )

            return response

        except Exception as e:
            logger.error(f"[HYBRID] Search failed: {e}")
            elapsed_ms = (time.time() - start_time) * 1000

            return {
                "results": [],
                "count": 0,
                "query": query,
                "mode": "error",
                "requested_mode": mode,
                "timing_ms": round(elapsed_ms, 2),
                "sources": sources_used,
                "cache_hit": False,
                "error": str(e),
            }

    async def _semantic_search(
        self, query: str, limit: int, collection: str
    ) -> List[Dict]:
        """
        Qdrant vector similarity search.

        Args:
            query: Search query
            limit: Max results
            collection: Collection name

        Returns:
            List of results with score, path, content, etc.
        """
        if not self.qdrant:
            return []

        try:
            # Generate embedding for query
            embedding = self.embedding_service.get_embedding(query)
            if not embedding:
                logger.warning("[HYBRID] Failed to generate query embedding")
                return []

            # Search Qdrant
            results = self.qdrant.search_by_vector(
                query_vector=embedding,
                limit=limit,
                score_threshold=0.3,  # Lower threshold for broader results
            )

            # Phase 69.4: Extract and preserve metadata from Qdrant payload
            for r in results:
                r["source"] = "qdrant"
                # Ensure metadata fields are preserved (may be in _raw or directly in payload)
                if "created_time" not in r or not r.get("created_time"):
                    r["created_time"] = r.get("_raw", {}).get("created_time", 0)
                if "modified_time" not in r or not r.get("modified_time"):
                    r["modified_time"] = r.get("_raw", {}).get("modified_time", 0)
                if "size" not in r or not r.get("size"):
                    r["size"] = r.get("_raw", {}).get("size") or r.get("_raw", {}).get(
                        "size_bytes", 0
                    )

            return results

        except Exception as e:
            logger.debug(f"[HYBRID] Semantic search failed: {e}")
            return []

    async def _keyword_search(
        self, query: str, limit: int, collection: str
    ) -> List[Dict]:
        """
        Weaviate BM25 keyword search.

        Args:
            query: Search query
            limit: Max results
            collection: Collection name

        Returns:
            List of results with score, path, content, etc.
        """
        if not self.weaviate:
            logger.warning("[KEYWORD] Weaviate not available")
            return []

        try:
            col_name = COLLECTIONS.get(collection, collection)
            logger.debug(f"[KEYWORD] BM25 search in '{col_name}'")

            results = self.weaviate.bm25_search(
                collection=collection, query=query, limit=limit
            )

            if not results:
                logger.warning(
                    f"[KEYWORD] BM25 returned 0 results for '{query}'. "
                    f"Weaviate collection '{col_name}' may be empty - needs data sync from Qdrant."
                )
                return []

            # Normalize Weaviate results
            # FIX_95.11: Include 'name' field from file_name mapping
            normalized = []
            for r in results:
                additional = r.get("_additional", {})
                path = r.get("path", "")
                # Extract name from path if not provided
                name = r.get("name", r.get("file_name", ""))
                if not name and path:
                    name = path.split("/")[-1]
                normalized.append({
                    "id": additional.get("id", path),
                    "path": path,
                    "name": name,
                    "content": r.get("content", ""),
                    "creator": r.get("creator", ""),
                    "node_type": r.get("node_type", ""),
                    "score": additional.get("score", 0.0),
                    "source": "weaviate",
                })

            logger.info(f"[KEYWORD] Found {len(normalized)} results")
            return normalized

        except Exception as e:
            logger.error(f"[KEYWORD] BM25 search failed: {e}")
            return []

    async def _filename_search(
        self, query: str, limit: int, collection: str
    ) -> List[Dict]:
        """
        Phase 68.2: Filename search via Qdrant payload filter.

        Searches files by name using case-insensitive substring match.
        Does NOT use vector similarity - pure payload filtering.

        Args:
            query: Filename pattern to search (e.g., "3d", "config", "test")
            limit: Max results
            collection: Collection name for Qdrant search

        Returns:
            List of results matching the filename pattern
        """
        if not self.qdrant:
            return []

        try:
            # FIX_95.3: Pass collection to search_by_filename (was missing!)
            # Maps collection param to Qdrant collection name
            qdrant_collection = {
                "tree": "vetka_tree",
                "leaf": "vetka_elisya",  # VetkaLeaf stores are in vetka_elisya
                "shared": "vetka_shared",
            }.get(collection, "vetka_elisya")

            results = self.qdrant.search_by_filename(
                filename_pattern=query, limit=limit, collection=qdrant_collection
            )

            # Add source marker and normalize scores
            for i, r in enumerate(results):
                r["source"] = "qdrant_filename"
                # Score based on position (first = best match)
                r["score"] = 1.0 - (i / max(len(results), 1)) * 0.5

            logger.debug(f"[HYBRID] Filename search '{query}' → {len(results)} results")
            return results

        except Exception as e:
            logger.debug(f"[HYBRID] Filename search failed: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """
        Get search service statistics.

        Returns:
            Dict with cache stats, backend status, configuration
        """
        self._init_backends()

        return {
            "backends": {
                "qdrant": self._qdrant is not None and self._qdrant.health_check()
                if self._qdrant
                else False,
                "weaviate": self._weaviate is not None,
            },
            "cache": {
                "size": len(_hybrid_search_cache),
                "ttl_seconds": HYBRID_CACHE_TTL,
            },
            "config": {
                "semantic_weight": SEMANTIC_WEIGHT,
                "keyword_weight": KEYWORD_WEIGHT,
                "graph_weight": GRAPH_WEIGHT,
                "rrf_k": RRF_K,
            },
            "embedding_stats": self._embedding_service.get_stats()
            if self._embedding_service
            else {},
        }

    def clear_cache(self):
        """Clear the search cache."""
        global _hybrid_search_cache
        _hybrid_search_cache.clear()
        logger.info("[HYBRID] Cache cleared")


# Singleton instance
_hybrid_search_instance: Optional[HybridSearchService] = None


def get_hybrid_search() -> HybridSearchService:
    """
    Get or create the singleton hybrid search service.

    Returns:
        HybridSearchService instance
    """
    global _hybrid_search_instance
    if _hybrid_search_instance is None:
        _hybrid_search_instance = HybridSearchService()
    return _hybrid_search_instance
