"""
VETKA Semantic Routes - FastAPI Version

@file semantic_routes.py
@status ACTIVE
@phase Phase 68
@lastAudit 2026-01-18

Semantic search and tagging API routes.
Migrated from src/server/routes/semantic_routes.py (Flask Blueprint)

Endpoints:
- GET /api/semantic-tags/search - Search files by semantic tag
- GET /api/semantic-tags/available - Get available semantic tags
- GET /api/file/{file_id}/auto-tags - Get auto-assigned tags for file
- GET /api/search/semantic - Universal semantic search
- POST /api/search/weaviate - Weaviate hybrid search with Qdrant fallback
- GET /api/search/hybrid - Phase 68: Hybrid search with RRF fusion

Changes from Flask version:
- Blueprint -> APIRouter
- request.get_json() -> Pydantic BaseModel
- request.args.get() -> Query()
- current_app.config -> request.app.state
- return jsonify({}) -> return {}
- def -> async def
"""

import os
import time
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


router = APIRouter(prefix="/api", tags=["semantic"])


# ============================================================
# MODULE-LEVEL CACHE (Phase 19)
# ============================================================

_semantic_search_cache: Dict[str, Any] = {}
_SEMANTIC_SEARCH_CACHE_TTL = 300  # 5 minutes


# ============================================================
# PYDANTIC MODELS
# ============================================================


class WeaviateSearchRequest(BaseModel):
    """Request for Weaviate hybrid search."""

    query: str
    limit: Optional[int] = 100
    filters: Optional[Dict[str, Any]] = {}


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def _get_semantic_components(request: Request) -> dict:
    """Get semantic-related components from app state (DI pattern)."""
    # Use FastAPI app.state directly instead of flask_config
    memory_manager = getattr(request.app.state, "memory_manager", None)
    return {
        "get_memory_manager": lambda: memory_manager,
    }


# ============================================================
# ROUTES
# ============================================================


@router.get("/semantic-tags/search")
async def semantic_tag_search(
    tag: str = Query(..., description="Semantic tag to search"),
    limit: int = Query(100, description="Max results"),
    min_score: float = Query(0.35, description="Minimum similarity score"),
    request: Request = None,
):
    """
    Search files by semantic tag using embeddings.

    Phase 16: Dynamic semantic search without stored tags.
    Uses embedding similarity to find files matching the semantic concept.
    """
    from src.knowledge_graph.semantic_tagger import SemanticTagger

    components = _get_semantic_components(request)
    get_memory_manager = components["get_memory_manager"]

    if not tag:
        raise HTTPException(status_code=400, detail="Tag parameter required")

    try:
        if not get_memory_manager:
            raise HTTPException(status_code=503, detail="Memory manager not available")

        memory = get_memory_manager()
        if not memory or not memory.qdrant:
            raise HTTPException(status_code=503, detail="Qdrant not available")

        tagger = SemanticTagger(qdrant_client=memory.qdrant, collection="vetka_elisya")

        files = tagger.find_files_by_semantic_tag(tag, limit=limit, min_score=min_score)

        return {
            "success": True,
            "tag": tag,
            "count": len(files),
            "files": [
                {
                    "id": f["id"],
                    "name": f["name"],
                    "path": f["path"],
                    "score": round(f["score"], 3),
                    "extension": f["extension"],
                }
                for f in files
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/semantic-tags/available")
async def get_available_tags():
    """
    Get list of predefined semantic tags.

    Phase 16: Returns all available semantic anchors.
    """
    from src.knowledge_graph.semantic_tagger import SemanticTagger

    # Create temporary tagger to get tags (no client needed for this)
    tagger = SemanticTagger(qdrant_client=None, collection="")

    tags_with_info = []
    for tag in tagger.get_available_tags():
        info = tagger.get_tag_description(tag)
        if info:
            tags_with_info.append(info)

    return {
        "tags": tagger.get_available_tags(),
        "tag_details": tags_with_info,
        "description": "Predefined semantic anchors for file categorization",
    }


@router.get("/file/{file_id}/auto-tags")
async def get_file_auto_tags(file_id: str, request: Request):
    """
    Get automatically assigned semantic tags for a file.

    Phase 16: Computes tag affinity from file embedding.
    """
    from src.knowledge_graph.semantic_tagger import SemanticTagger
    import numpy as np

    components = _get_semantic_components(request)
    get_memory_manager = components["get_memory_manager"]

    try:
        if not get_memory_manager:
            raise HTTPException(status_code=503, detail="Memory manager not available")

        memory = get_memory_manager()
        if not memory or not memory.qdrant:
            raise HTTPException(status_code=503, detail="Qdrant not available")

        # Get file embedding from Qdrant
        try:
            point_id = int(file_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid file ID")

        points = memory.qdrant.retrieve(
            collection_name="vetka_elisya",
            ids=[point_id],
            with_vectors=True,
            with_payload=True,
        )

        if not points:
            raise HTTPException(status_code=404, detail="File not found")

        point = points[0]
        embedding = point.vector

        if not embedding:
            raise HTTPException(status_code=400, detail="File has no embedding")

        tagger = SemanticTagger(qdrant_client=memory.qdrant, collection="vetka_elisya")

        tags = tagger.auto_tag_file(np.array(embedding))

        return {
            "file_id": file_id,
            "name": point.payload.get("name", "unknown"),
            "path": point.payload.get("path", ""),
            "tags": tags,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/semantic")
async def semantic_search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(100, description="Max results"),
    request: Request = None,
):
    """
    Phase 17: Universal semantic search.
    Phase 19: Added caching with TTL.

    Replaces text-based search with embedding similarity.
    Treats the query as a semantic anchor and finds similar files.
    """
    from src.knowledge_graph.semantic_tagger import SemanticTagger

    components = _get_semantic_components(request)
    get_memory_manager = components["get_memory_manager"]

    query = q.strip()

    if not query:
        raise HTTPException(status_code=400, detail="Query required")

    if len(query) < 2:
        raise HTTPException(status_code=400, detail="Query too short")

    # Phase 19: Check cache first
    cache_key = f"semantic:{query}:{limit}"
    if cache_key in _semantic_search_cache:
        cached = _semantic_search_cache[cache_key]
        age = time.time() - cached["timestamp"]
        if age < _SEMANTIC_SEARCH_CACHE_TTL:
            print(f"  [Semantic] CACHE HIT: '{query}' (age: {age:.1f}s)")
            result = cached["result"].copy()
            result["cache_hit"] = True
            return result
        else:
            print(f"  [Semantic] CACHE EXPIRED: '{query}' (age: {age:.1f}s)")
            del _semantic_search_cache[cache_key]
    else:
        print(f"  [Semantic] CACHE MISS: '{query}'")

    try:
        if not get_memory_manager:
            raise HTTPException(status_code=503, detail="Memory manager not available")

        memory = get_memory_manager()
        if not memory or not memory.qdrant:
            raise HTTPException(status_code=503, detail="Qdrant not available")

        # Use SemanticTagger for search (treats query as custom tag)
        tagger = SemanticTagger(qdrant_client=memory.qdrant, collection="vetka_elisya")

        # Search by embedding similarity
        # Lower threshold (0.30) for broader search results
        files = tagger.find_files_by_semantic_tag(
            tag=query,  # Query becomes the semantic anchor
            limit=limit,
            min_score=0.30,
        )

        result = {
            "success": True,
            "query": query,
            "count": len(files),
            "cache_hit": False,
            "files": [
                {
                    "id": f["id"],
                    "name": f["name"],
                    "path": f["path"],
                    "score": round(f["score"], 3),
                    "extension": f["extension"],
                    "created_time": f.get("created_time", 0),
                    "modified_time": f.get("modified_time", 0),
                }
                for f in files
            ],
        }

        # Phase 19: Cache the result
        _semantic_search_cache[cache_key] = {"result": result, "timestamp": time.time()}
        print(
            f"  [Semantic] CACHE SET: '{query}' (total cached: {len(_semantic_search_cache)})"
        )

        # Cleanup old entries (keep max 100)
        if len(_semantic_search_cache) > 100:
            oldest = sorted(
                _semantic_search_cache.keys(),
                key=lambda k: _semantic_search_cache[k]["timestamp"],
            )[:50]
            for k in oldest:
                del _semantic_search_cache[k]
            print(f"  [Semantic] CACHE CLEANUP: removed {len(oldest)} old entries")

        return result

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/weaviate")
async def weaviate_search(req: WeaviateSearchRequest, request: Request):
    """
    Phase 17-O: Semantic search via Weaviate.

    Uses hybrid search (keyword + vector) for best results.
    Falls back to Qdrant semantic search if Weaviate unavailable.
    """
    import requests as http_req

    components = _get_semantic_components(request)
    get_memory_manager = components["get_memory_manager"]

    try:
        query = req.query.strip()
        limit = min(req.limit, 200)  # Max 200

        if not query or len(query) < 2:
            raise HTTPException(status_code=400, detail="Query too short")

        results = []
        source = "weaviate"

        # Try Weaviate first
        try:
            weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")

            # Check Weaviate health
            health_resp = http_req.get(
                f"{weaviate_url}/v1/.well-known/ready", timeout=2
            )

            if health_resp.status_code == 200:
                # Build GraphQL query for hybrid search
                graphql_query = {
                    "query": f'''{{
                        Get {{
                            VetkaLeaf(
                                hybrid: {{query: "{query.replace('"', '\\"')}", alpha: 0.7}}
                                limit: {limit}
                            ) {{
                                file_path
                                file_name
                                content
                                file_type
                                depth
                                _additional {{ id distance certainty }}
                            }}
                        }}
                    }}'''
                }

                gql_resp = http_req.post(
                    f"{weaviate_url}/v1/graphql",
                    json=graphql_query,
                    headers={"Content-Type": "application/json"},
                    timeout=10,
                )

                if gql_resp.status_code == 200:
                    gql_data = gql_resp.json()
                    items = gql_data.get("data", {}).get("Get", {}).get("VetkaLeaf", [])

                    for item in items:
                        additional = item.get("_additional", {})
                        results.append(
                            {
                                "id": additional.get("id", ""),
                                "path": item.get("file_path", ""),
                                "name": item.get("file_name", ""),
                                "type": item.get("file_type", ""),
                                "depth": item.get("depth", 0),
                                "distance": additional.get("distance", 0),
                                "certainty": additional.get("certainty", 0),
                                "snippet": (item.get("content", "")[:200] + "...")
                                if item.get("content")
                                else "",
                                "source": "weaviate",
                            }
                        )

        except Exception as weaviate_err:
            print(
                f"  [Semantic] Weaviate unavailable: {weaviate_err}, falling back to Qdrant"
            )
            source = "qdrant"

        # Fallback to Qdrant semantic search
        if not results:
            source = "qdrant"
            try:
                if get_memory_manager:
                    memory = get_memory_manager()
                    if memory and memory.qdrant:
                        from src.knowledge_graph.semantic_tagger import SemanticTagger

                        tagger = SemanticTagger(
                            qdrant_client=memory.qdrant, collection="vetka_elisya"
                        )

                        files = tagger.find_files_by_semantic_tag(
                            tag=query, limit=limit, min_score=0.30
                        )

                        for f in files:
                            results.append(
                                {
                                    "id": f["id"],
                                    "path": f["path"],
                                    "name": f["name"],
                                    "type": f.get("extension", ""),
                                    "depth": 0,
                                    "distance": 1
                                    - f["score"],  # Convert score to distance
                                    "certainty": f["score"],
                                    "snippet": "",
                                    "source": "qdrant",
                                }
                            )

            except Exception as qdrant_err:
                print(f"  [Semantic] Qdrant fallback failed: {qdrant_err}")

        return {
            "success": True,
            "results": results,
            "total": len(results),
            "query": query,
            "source": source,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# PHASE 68: HYBRID SEARCH WITH RRF FUSION
# ============================================================


@router.get("/search/hybrid")
async def hybrid_search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(100, ge=1, le=1000, description="Max results (1-1000)"),
    mode: str = Query("hybrid", description="Search mode: semantic | keyword | hybrid"),
    file_types: Optional[str] = Query(
        None, description="Comma-separated file types filter: py,md,js"
    ),
    collection: str = Query(
        "leaf",  # FIX_95.7: Changed default from tree to leaf (VetkaLeaf has file data)
        description="Collection to search: tree, leaf, shared"
    ),
    skip_cache: bool = Query(False, description="Skip cache and force fresh search"),
):
    """
    Phase 68: Hybrid search with RRF (Reciprocal Rank Fusion).

    Combines multiple search backends with configurable weights:
    - Qdrant semantic search (default 50%)
    - Weaviate BM25 keyword search (default 30%)
    - Graph relations (default 20%, future)

    RRF formula: score_RRF(d) = Σ w_i × 1/(k + rank_i(d))

    Args:
        q: Search query string
        limit: Maximum results to return (1-100)
        mode: Search mode
            - "semantic": Pure vector similarity (Qdrant only)
            - "keyword": Pure BM25 text search (Weaviate only)
            - "hybrid": Combined with RRF fusion (default)
        file_types: Optional comma-separated file type filter (e.g., "py,md,js")
        collection: Which collection to search (tree, leaf, shared)
        skip_cache: If true, bypasses cache for fresh results

    Returns:
        JSON with:
        - results: List of matched documents with rrf_score, explanation
        - count: Number of results
        - mode: Actual mode used (may differ if backend unavailable)
        - timing_ms: Search latency
        - sources: Which backends contributed
        - config: RRF weights and k constant

    Example:
        GET /api/search/hybrid?q=authentication%20flow&limit=20&mode=hybrid

    Configuration (env vars):
        - VETKA_SEMANTIC_WEIGHT: Semantic search weight (default: 0.5)
        - VETKA_KEYWORD_WEIGHT: Keyword search weight (default: 0.3)
        - VETKA_RRF_K: RRF smoothing constant (default: 60)
        - VETKA_HYBRID_CACHE_TTL: Cache TTL in seconds (default: 300)
    """
    from src.search.hybrid_search import get_hybrid_search

    query = q.strip()

    # Validate query
    if not query:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")

    if len(query) < 2:
        raise HTTPException(
            status_code=400, detail="Query too short (min 2 characters)"
        )

    # Validate mode
    valid_modes = ("semantic", "keyword", "hybrid")
    if mode not in valid_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode '{mode}'. Must be one of: {', '.join(valid_modes)}",
        )

    # Parse file types filter
    filters = {}
    if file_types:
        filters["file_types"] = [
            ft.strip().lower() for ft in file_types.split(",") if ft.strip()
        ]

    try:
        search_service = get_hybrid_search()

        result = await search_service.search(
            query=query,
            limit=limit,
            mode=mode,
            filters=filters,
            collection=collection,
            skip_cache=skip_cache,
        )

        return {"success": True, **result}

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Hybrid search failed: {str(e)}")


@router.get("/search/hybrid/stats")
async def hybrid_search_stats():
    """
    Phase 68: Get hybrid search service statistics.

    Returns backend status, cache stats, and configuration.
    """
    from src.search.hybrid_search import get_hybrid_search

    try:
        search_service = get_hybrid_search()
        stats = search_service.get_stats()

        return {"success": True, "stats": stats}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# ============================================================
# PHASE 69: RESCAN ENDPOINT
# ============================================================


@router.post("/scanner/rescan")
async def trigger_rescan(
    path: Optional[str] = Query(
        None, description="Path to scan (defaults to current working directory)"
    ),
    request: Request = None,
):
    """
    Phase 69: Trigger full reindex with cleanup.
    Phase 83: Fixed to respect path parameter for targeted scanning.
              Added stop flag support for graceful interruption.

    DELETE old data, then scan fresh.
    Emits socket events for progress tracking.

    Args:
        path: Optional directory path to scan (REQUIRED for targeted scan)
              If not specified, scans current working directory

    Returns:
        JSON with indexed count, deleted count, and path
    """
    from pathlib import Path

    try:
        from src.scanners.qdrant_updater import get_qdrant_updater
        from src.scanners.local_scanner import LocalScanner
        from src.memory.qdrant_client import get_qdrant_client

        # Get socket.io for progress events
        socketio = getattr(request.app.state, "socketio", None) if request else None

        # Get Qdrant client from singleton
        qdrant_client = get_qdrant_client()
        if not qdrant_client:
            raise HTTPException(status_code=503, detail="Qdrant not available")

        # Get raw client for updater
        raw_client = qdrant_client.client if hasattr(qdrant_client, "client") else None
        if not raw_client:
            raise HTTPException(
                status_code=503, detail="Qdrant raw client not available"
            )

        updater = get_qdrant_updater(qdrant_client=raw_client)

        # Phase 83: Reset stop flag before starting new scan
        updater.reset_stop()

        # Phase 83: Properly use the path parameter for targeted scanning
        if path:
            scan_path = Path(path).expanduser().resolve()
            print(f"[Scanner] Targeted scan requested for: {scan_path}")
        else:
            scan_path = Path.cwd()
            print(f"[Scanner] Full scan requested (no path specified): {scan_path}")

        if not scan_path.exists():
            raise HTTPException(status_code=404, detail=f"Path not found: {scan_path}")

        if not scan_path.is_dir():
            raise HTTPException(
                status_code=400, detail=f"Path is not a directory: {scan_path}"
            )

        # 1. Cleanup old entries (synchronous method)
        deleted = updater.cleanup_deleted(older_than_hours=0)

        # 2. Scan and reindex ONLY the specified path
        scanner = LocalScanner(str(scan_path))

        # Phase 69: Emit scan_started event
        if socketio:
            await socketio.emit(
                "scan_started", {"path": str(scan_path), "status": "scanning"}
            )

        indexed = 0
        skipped = 0
        total_scanned = 0
        stopped = False

        for scanned_file in scanner.scan():
            # Phase 83: Check stop flag at each iteration
            if updater.is_stop_requested():
                print(
                    f"[Scanner] Stop requested - halting scan at {total_scanned} files"
                )
                stopped = True
                break

            total_scanned += 1

            # Convert ScannedFile to Path for updater
            file_path = Path(scanned_file.path)
            result = updater.update_file(file_path)
            if result:
                indexed += 1
            else:
                skipped += 1

            # Phase 69: Emit progress every 10 files
            if socketio and total_scanned % 10 == 0:
                await socketio.emit(
                    "scan_progress",
                    {
                        "current": total_scanned,
                        "indexed": indexed,
                        "file": scanned_file.name,
                        "path": str(scan_path),
                    },
                )

        stats = updater.get_stats()
        scanner_stats = scanner.get_stats()

        # Phase 83: Determine status based on whether stopped
        status = "stopped" if stopped else "completed"

        # Phase 69/83: Emit appropriate event
        if socketio:
            event_name = "scan_stopped" if stopped else "scan_complete"
            await socketio.emit(
                event_name,
                {
                    "indexed": indexed,
                    "skipped": skipped,
                    "total": total_scanned,
                    "deleted": deleted,
                    "path": str(scan_path),
                    "stopped": stopped,
                },
            )

        return {
            "success": True,
            "status": status,
            "indexed": indexed,
            "skipped": skipped,
            "deleted": deleted,
            "total_scanned": total_scanned,
            "errors": stats.get("error_count", 0),
            "path": str(scan_path),
            "stopped": stopped,
            "scanner_stats": scanner_stats,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Rescan failed: {str(e)}")


# ============================================================
# PHASE 83: SCANNER STOP ENDPOINT
# ============================================================


@router.post("/scanner/stop")
async def stop_scanner(request: Request = None):
    """
    Phase 83: Stop a running scan gracefully.

    Sets the stop flag on the QdrantIncrementalUpdater singleton.
    The running scan will exit at the next checkpoint (after current file).

    Returns:
        JSON with stop request status
    """
    try:
        from src.scanners.qdrant_updater import get_qdrant_updater
        from src.memory.qdrant_client import get_qdrant_client

        # Get socket.io for stop event
        socketio = getattr(request.app.state, "socketio", None) if request else None

        # Get Qdrant client from singleton
        qdrant_client = get_qdrant_client()
        raw_client = None
        if qdrant_client:
            raw_client = (
                qdrant_client.client if hasattr(qdrant_client, "client") else None
            )

        # Get updater singleton (may exist even without active client)
        updater = get_qdrant_updater(qdrant_client=raw_client)

        # Request stop
        updater.request_stop()

        # Emit stop requested event
        if socketio:
            await socketio.emit(
                "scan_stop_requested",
                {
                    "status": "stop_requested",
                    "message": "Stop signal sent - scan will halt at next checkpoint",
                },
            )

        stats = updater.get_stats()

        return {
            "success": True,
            "status": "stop_requested",
            "message": "Stop signal sent - scan will halt at next checkpoint",
            "current_stats": stats,
        }

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to stop scanner: {str(e)}")


@router.get("/scanner/status")
async def get_scanner_status(request: Request = None):
    """
    Phase 83: Get current scanner status.

    Returns the current state of the scanner including whether
    a stop has been requested.

    Returns:
        JSON with scanner status and stats
    """
    try:
        from src.scanners.qdrant_updater import get_qdrant_updater
        from src.memory.qdrant_client import get_qdrant_client

        # Get Qdrant client from singleton
        qdrant_client = get_qdrant_client()
        raw_client = None
        if qdrant_client:
            raw_client = (
                qdrant_client.client if hasattr(qdrant_client, "client") else None
            )

        # Get updater singleton
        updater = get_qdrant_updater(qdrant_client=raw_client)
        stats = updater.get_stats()

        return {
            "success": True,
            "stop_requested": updater.is_stop_requested(),
            "stats": stats,
        }

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Failed to get scanner status: {str(e)}"
        )


# ============================================================
# PHASE 84: CLEAR ALL SCANS ENDPOINT
# ============================================================


@router.delete("/scanner/clear-all")
async def clear_all_scans(request: Request = None):
    """
    Phase 84 + FIX_96.4: Delete all points from Qdrant AND Weaviate.

    This permanently removes all indexed files from BOTH vector stores:
    - Qdrant vetka_elisya collection
    - Weaviate VetkaLeaf class

    Note: Chat history (JSON) is preserved - only scan data is cleared.
    Use with caution - requires re-scanning to rebuild the index.

    Returns:
        JSON with count of deleted points and status for both stores
    """
    import requests as http_requests  # Avoid name collision with Request parameter

    try:
        from src.memory.qdrant_client import get_qdrant_client

        # Get socket.io for event notification
        socketio = getattr(request.app.state, "socketio", None) if request else None

        # === 1. CLEAR QDRANT ===
        qdrant_cleared = False
        qdrant_count = 0

        qdrant_client = get_qdrant_client()
        if qdrant_client and qdrant_client.client:
            raw_client = qdrant_client.client
            collection_name = "vetka_elisya"

            # Get current point count before deletion
            try:
                collection_info = raw_client.get_collection(collection_name)
                qdrant_count = collection_info.points_count
            except Exception:
                qdrant_count = 0

            if qdrant_count > 0:
                try:
                    from qdrant_client.models import VectorParams, Distance

                    # Get current vector config
                    vector_size = collection_info.config.params.vectors.size
                    distance = collection_info.config.params.vectors.distance

                    # Recreate collection (deletes all points)
                    raw_client.recreate_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(size=vector_size, distance=distance),
                    )
                    qdrant_cleared = True
                    print(f"[Scanner] ✅ Cleared {qdrant_count} points from Qdrant {collection_name}")
                except Exception as e:
                    print(f"[Scanner] ❌ Qdrant clear error: {e}")
            else:
                qdrant_cleared = True  # Already empty
                print(f"[Scanner] Qdrant {collection_name} already empty")

        # === 2. CLEAR WEAVIATE (FIX_96.4) ===
        # MARKER_CLEANUP_001: Now clearing VetkaLeaf class
        weaviate_cleared = False
        weaviate_count = 0

        try:
            weaviate_url = "http://localhost:8080"

            # First get count of objects
            try:
                count_resp = http_requests.get(
                    f"{weaviate_url}/v1/objects?class=VetkaLeaf&limit=1",
                    timeout=5
                )
                if count_resp.status_code == 200:
                    # Get total by fetching with high limit
                    all_resp = http_requests.get(
                        f"{weaviate_url}/v1/objects?class=VetkaLeaf&limit=10000",
                        timeout=10
                    )
                    if all_resp.status_code == 200:
                        weaviate_count = len(all_resp.json().get("objects", []))
            except Exception:
                pass

            # Delete entire VetkaLeaf class (fastest approach)
            # It will be auto-recreated by TripleWriteManager on next write
            resp = http_requests.delete(
                f"{weaviate_url}/v1/schema/VetkaLeaf",
                timeout=10
            )

            if resp.status_code in (200, 204):
                weaviate_cleared = True
                print(f"[Scanner] ✅ Cleared {weaviate_count} objects from Weaviate VetkaLeaf")
            elif resp.status_code == 404:
                weaviate_cleared = True  # Class doesn't exist, that's fine
                print(f"[Scanner] Weaviate VetkaLeaf class not found (already clean)")
            else:
                print(f"[Scanner] ❌ Weaviate clear failed: {resp.status_code} {resp.text}")

        except Exception as e:
            print(f"[Scanner] ❌ Weaviate cleanup error: {e}")

        # === 3. EMIT SOCKET EVENT ===
        if socketio:
            await socketio.emit(
                "scan_cleared",
                {
                    "collection": "vetka_elisya",
                    "deleted_count": qdrant_count,
                    "qdrant_cleared": qdrant_cleared,
                    "weaviate_cleared": weaviate_cleared,
                    "weaviate_count": weaviate_count,
                    "status": "cleared" if (qdrant_cleared and weaviate_cleared) else "partial",
                },
            )

        # === 4. RETURN RESULT ===
        total_deleted = qdrant_count + weaviate_count
        both_success = qdrant_cleared and weaviate_cleared

        return {
            "success": both_success,
            "message": f"Cleared {qdrant_count} from Qdrant, {weaviate_count} from Weaviate",
            "deleted_count": total_deleted,
            "qdrant_cleared": qdrant_cleared,
            "qdrant_count": qdrant_count,
            "weaviate_cleared": weaviate_cleared,
            "weaviate_count": weaviate_count,
            "chat_preserved": True,  # JSON chat history is NOT touched
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to clear scans: {str(e)}")
