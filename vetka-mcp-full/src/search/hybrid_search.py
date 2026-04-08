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
from src.search.file_search_service import search_files
from src.services.mcc_jepa_adapter import embed_texts_for_overlay

logger = logging.getLogger("VETKA_HYBRID_SEARCH")

# Configurable via environment
SEMANTIC_WEIGHT = float(os.getenv("VETKA_SEMANTIC_WEIGHT", "0.5"))
KEYWORD_WEIGHT = float(os.getenv("VETKA_KEYWORD_WEIGHT", "0.3"))
GRAPH_WEIGHT = float(os.getenv("VETKA_GRAPH_WEIGHT", "0.2"))
RRF_K = int(os.getenv("VETKA_RRF_K", "60"))
FILE_WEIGHT = float(os.getenv("VETKA_FILE_WEIGHT", "0.35"))
FILENAME_WEIGHT = float(os.getenv("VETKA_FILENAME_WEIGHT", "0.45"))
JEPA_REORDER_WEIGHT = float(os.getenv("VETKA_HYBRID_JEPA_REORDER_WEIGHT", "0.35"))
HYBRID_JEPA_ENABLED = os.getenv("VETKA_HYBRID_JEPA_ENABLED", "true").lower() == "true"
HYBRID_JEPA_INTENT_MIN_WORDS = max(4, int(os.getenv("VETKA_HYBRID_JEPA_INTENT_MIN_WORDS", "4")))

# Cache configuration
HYBRID_CACHE_TTL = int(os.getenv("VETKA_HYBRID_CACHE_TTL", "300"))  # 5 minutes
_hybrid_search_cache: Dict[str, Any] = {}

# Thread pool for parallel searches
_executor = ThreadPoolExecutor(max_workers=3)


def _is_descriptive_query(query: str) -> bool:
    q = (query or "").lower().strip()
    words = [w for w in q.split() if w]
    file_like = any(x in q for x in [".py", ".md", ".txt", "marker_", "/", "\\"])
    markers = ["не помню", "найди файл где", "документ", "где ", "про "]
    return (len(words) >= HYBRID_JEPA_INTENT_MIN_WORDS and not file_like) or any(m in q for m in markers)


def _is_explicit_file_finder_query(query: str) -> bool:
    q = (query or "").lower().strip()
    markers = [
        "найди файл",
        "какой файл",
        "где файл",
        "find file",
        "which file",
    ]
    return any(m in q for m in markers)


def _is_lexical_filename_query(query: str) -> bool:
    """
    Short lexical queries should include filename search source in vetka/hybrid path.
    Example: 'abbreviation', 'auth', 'router', 'marker_157'.
    """
    q = (query or "").strip().lower()
    if not q:
        return False
    words = [w for w in q.split() if w]
    if len(words) > 2:
        return False
    if len(q) < 3:
        return False
    # File-ish token patterns are strong filename intent signals.
    if any(ch in q for ch in ("_", "-", ".", "/")):
        return True
    return len(words) == 1


def _query_lexical_variants(query: str) -> List[str]:
    q = (query or "").strip().lower()
    if not q:
        return []
    variants = {q}
    if q.endswith("s") and len(q) > 3:
        variants.add(q[:-1])
    else:
        variants.add(f"{q}s")
    return [v for v in variants if v]


def _path_name_lexical_bonus(query: str, row: Dict[str, Any]) -> float:
    variants = _query_lexical_variants(query)
    if not variants:
        return 0.0
    path = str(row.get("path") or "").lower()
    name = str(row.get("name") or os.path.basename(path)).lower()
    best = 0.0
    for token in variants:
        if name == token:
            best = max(best, 0.2)
        elif name.startswith(token):
            best = max(best, 0.12)
        elif token in name:
            best = max(best, 0.08)
        elif token in path:
            best = max(best, 0.04)
    return best


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

    async def _file_search_local(self, query: str, limit: int, mode: str = "keyword") -> List[Dict]:
        try:
            res = await asyncio.to_thread(search_files, query=query, limit=limit, mode=mode)
            rows = []
            for it in (res or {}).get("results", []):
                rows.append(
                    {
                        "id": it.get("path") or it.get("title"),
                        "path": it.get("path") or it.get("title", ""),
                        "name": os.path.basename(it.get("path") or it.get("title", "")),
                        "content": it.get("snippet", ""),
                        "score": float(it.get("score", 0.0)),
                        "source": "file_local",
                    }
                )
            return rows
        except Exception as e:
            logger.debug(f"[HYBRID] local file search failed: {e}")
            return []

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0
        n = min(len(a), len(b))
        dot = sum(float(a[i]) * float(b[i]) for i in range(n))
        na = sum(float(a[i]) * float(a[i]) for i in range(n)) ** 0.5
        nb = sum(float(b[i]) * float(b[i]) for i in range(n)) ** 0.5
        if na <= 1e-12 or nb <= 1e-12:
            return 0.0
        return float(dot / (na * nb))

    def _jepa_reorder(self, query: str, results: List[Dict], limit: int) -> List[Dict]:
        if not HYBRID_JEPA_ENABLED or not results:
            return results[:limit]
        try:
            texts = [query]
            for r in results[: max(limit * 3, 30)]:
                txt = (r.get("path") or r.get("name") or "") + " " + (r.get("content") or "")
                texts.append(txt.strip())
            jr = embed_texts_for_overlay(texts=texts, target_dim=128)
            vectors = getattr(jr, "vectors", []) or []
            if len(vectors) != len(texts):
                return results[:limit]
            qv = vectors[0]
            rescored = []
            for idx, r in enumerate(results[: max(limit * 3, 30)], start=1):
                base = float(r.get("rrf_score") or r.get("score") or 0.0)
                js = max(0.0, self._cosine(qv, vectors[idx]))
                merged = base + (JEPA_REORDER_WEIGHT * js)
                rc = dict(r)
                rc["jepa_score"] = round(js, 6)
                rc["jepa_provider_mode"] = getattr(jr, "provider_mode", "")
                rc["jepa_reordered"] = True
                rc["score"] = merged
                rescored.append(rc)
            rescored.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)
            return rescored[:limit]
        except Exception as e:
            logger.debug(f"[HYBRID] JEPA reorder skipped: {e}")
            return results[:limit]

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
        query_intent = "descriptive" if _is_descriptive_query(query) else "name_like"

        # Check cache first
        cache_key = f"hybrid:{query}:{limit}:{mode}:{query_intent}:{hash(str(filters))}"
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
                if not filename_results:
                    # Keep vetka/FILE useful when dedicated filename list is temporarily sparse.
                    keyword_fallback = await self._keyword_search(query, limit * 3, collection)
                    if keyword_fallback:
                        variants = _query_lexical_variants(query)
                        filtered = []
                        for row in keyword_fallback:
                            hay = f"{row.get('name', '')} {row.get('path', '')}".lower()
                            if any(v in hay for v in variants):
                                nr = dict(row)
                                nr["source"] = "filename_fallback"
                                nr["score"] = max(float(nr.get("score", 0.0)), 0.55)
                                filtered.append(nr)
                        filename_results = filtered[:limit]
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

                # MARKER_130.C19C: Lowered to debug
                logger.debug(
                    f"[HYBRID] Filename search '{query}' → {len(filename_results)} results "
                    f"({elapsed_ms:.0f}ms)"
                )

                return response

            # Run searches in parallel using asyncio
            tasks = []
            normalized_by_source: Dict[str, List[Dict[str, Any]]] = {}

            # 1. Semantic search (Qdrant)
            if mode in ("semantic", "hybrid") and self.qdrant:
                tasks.append(
                    ("semantic", self._semantic_search(query, limit * 2, collection))
                )

            # 2. Keyword search (Weaviate BM25, Qdrant fallback)
            if mode in ("keyword", "hybrid") and (self.weaviate or self.qdrant):
                tasks.append(
                    ("keyword", self._keyword_search(query, limit * 2, collection))
                )

            # 2.1 Filename search source for lexical/name-like vetka queries.
            if mode in ("keyword", "hybrid") and self.qdrant and _is_lexical_filename_query(query):
                tasks.append(
                    ("filename", self._filename_search(query, limit * 2, collection))
                )

            # 3. Local file search source (especially useful for descriptive doc queries).
            if mode in ("keyword", "hybrid") and query_intent == "descriptive":
                tasks.append(
                    ("file", self._file_search_local(query, limit * 2, mode="keyword"))
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
                        source_map = {
                            "semantic": "qdrant",
                            "keyword": "weaviate",
                            "file": "file",
                            "filename": "filename",
                        }
                        source = source_map.get(task_name, task_name)
                        normalized = normalize_results(result, source)
                        if normalized:
                            normalized_by_source[task_name] = normalized
                            results_lists.append(normalized)
                            sources_used.append(task_name)

                        # Set weight based on mode
                        if mode == "hybrid":
                            if task_name == "semantic":
                                weights.append(SEMANTIC_WEIGHT)
                            elif task_name == "keyword":
                                weights.append(KEYWORD_WEIGHT)
                            elif task_name == "file":
                                weights.append(FILE_WEIGHT)
                            elif task_name == "filename":
                                weights.append(FILENAME_WEIGHT)
                        else:
                            weights.append(1.0)

            # Phase 157 runtime policy:
            # explicit "find file" intent should prioritize local file retrieval to avoid semantic noise.
            if (
                mode == "hybrid"
                and query_intent == "descriptive"
                and _is_explicit_file_finder_query(query)
                and normalized_by_source.get("file")
            ):
                fused = normalized_by_source["file"][:limit]
                actual_mode = "file"
                sources_used = ["file"]
            else:
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

            # For lexical queries, prioritize direct name/path hits in fused list.
            if mode in ("hybrid", "keyword") and _is_lexical_filename_query(query) and fused:
                boosted = []
                for row in fused:
                    nr = dict(row)
                    base = float(nr.get("rrf_score") or nr.get("score") or 0.0)
                    bonus = _path_name_lexical_bonus(query, nr)
                    if bonus > 0:
                        nr["lexical_bonus"] = round(bonus, 6)
                        nr["score"] = base + bonus
                        if "rrf_score" in nr:
                            nr["rrf_score"] = round(float(nr.get("rrf_score", 0.0)) + bonus, 6)
                    boosted.append(nr)
                boosted.sort(
                    key=lambda x: float(x.get("rrf_score") or x.get("score") or 0.0),
                    reverse=True,
                )
                fused = boosted[:limit]

            # Optional JEPA reorder for descriptive queries.
            if query_intent == "descriptive":
                fused = self._jepa_reorder(query, fused, limit=limit)

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
                "intent": query_intent,
                "jepa_reordered": bool(query_intent == "descriptive" and HYBRID_JEPA_ENABLED),
                "config": {
                    "semantic_weight": SEMANTIC_WEIGHT,
                    "keyword_weight": KEYWORD_WEIGHT,
                    "file_weight": FILE_WEIGHT,
                    "filename_weight": FILENAME_WEIGHT,
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

            # MARKER_130.C19C: Lowered to debug
            logger.debug(
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
        async def _qdrant_fallback() -> List[Dict]:
            if not self.qdrant:
                return []
            try:
                qdrant_collection = {
                    "tree": "vetka_tree",
                    "leaf": "vetka_elisya",
                    "shared": "vetka_shared",
                }.get(collection, "vetka_elisya")
                rows = self.qdrant.search_by_content(
                    query=query,
                    limit=limit,
                    collection=qdrant_collection,
                )
                for r in rows:
                    r["source"] = "qdrant_keyword"
                if rows:
                    logger.info(f"[KEYWORD] Qdrant content fallback returned {len(rows)} rows")
                return rows
            except Exception as e:
                logger.debug(f"[KEYWORD] Qdrant content fallback failed: {e}")
                return []

        if not self.weaviate:
            logger.warning("[KEYWORD] Weaviate not available, using Qdrant content fallback")
            return await _qdrant_fallback()

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
                return await _qdrant_fallback()

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

            # MARKER_130.C19C: Lowered to debug
            logger.debug(f"[KEYWORD] Found {len(normalized)} results")
            return normalized

        except Exception as e:
            logger.error(f"[KEYWORD] BM25 search failed: {e}")
            return await _qdrant_fallback()

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
