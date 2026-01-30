"""
VETKA Phase 68: Search Socket Handlers

@file search_handlers.py
@status ACTIVE
@phase Phase 68
@description Socket.IO handlers for real-time hybrid search
@usedBy UnifiedSearchBar (frontend)
@lastAudit 2026-01-18

Events:
- search_query: Client sends query, receives search_results or search_error
- search_results: Server returns fused results with relevance scores
- search_error: Server returns error details
"""

import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger("VETKA_SEARCH_HANDLER")


def register_search_handlers(sio, app=None):
    """
    Register search-related Socket.IO handlers.

    Args:
        sio: python-socketio AsyncServer instance
        app: FastAPI app for accessing app.state (optional)
    """

    @sio.on('search_query')
    async def handle_search_query(sid: str, data: Dict[str, Any]):
        """
        Handle real-time search query from frontend.

        Expected data:
        {
            "text": str,       # Search query
            "limit": int,      # Max results (default 10, max 50)
            "mode": str,       # "hybrid" | "semantic" | "keyword" (default hybrid)
            "filters": dict    # Optional filters (file_types, paths)
        }

        Emits:
        - search_results: {results, total, query, took_ms}
        - search_error: {error, query}
        """
        # Validate input
        if not isinstance(data, dict):
            await sio.emit('search_error', {
                'error': 'Invalid data format',
                'query': ''
            }, to=sid)
            return

        query = (data.get('text') or '').strip()
        # Phase 68.2: Remove hard limit cap, allow up to 200 results
        # Score threshold filtering will reduce irrelevant results
        limit = min(data.get('limit', 50), 200)  # Increased cap to 200
        mode = data.get('mode', 'hybrid')
        filters = data.get('filters', {})

        # FIX_96.3: Mode-aware score thresholds
        # Different search modes return scores in different ranges:
        # - semantic: cosine similarity 0.3-1.0
        # - hybrid/RRF: weighted rank fusion 0.001-0.033
        # - keyword/BM25: TF-IDF based, varies widely, often very small
        # - filename: position-based 0-1
        default_thresholds = {
            'semantic': 0.3,    # Cosine similarity - only high matches
            'hybrid': 0.001,    # RRF scores are tiny - allow most through
            'keyword': 0.0,     # BM25 scores vary - no threshold
            'filename': 0.0     # Filename match - no threshold
        }
        # FIX_96.3.1: Frontend sends min_score=0.3 as default for ALL modes (legacy)
        # Override with mode-aware threshold unless frontend explicitly sends different value
        frontend_min_score = data.get('min_score')
        if frontend_min_score is None or frontend_min_score == 0.3:
            # Use mode-aware default
            min_score = default_thresholds.get(mode, 0.001)
        else:
            # User explicitly set a custom threshold
            min_score = frontend_min_score

        # FIX_96.3 DEBUG: Log actual threshold being used
        logger.info(f"[SEARCH] Mode={mode}, min_score={min_score}")

        # Empty query - return empty results
        if not query:
            await sio.emit('search_results', {
                'results': [],
                'total': 0,
                'query': '',
                'took_ms': 0
            }, to=sid)
            return

        logger.info(f"[SEARCH] Query from {sid}: '{query}' (limit={limit}, mode={mode})")

        try:
            start = time.time()

            # Get HybridSearchService
            from src.search.hybrid_search import get_hybrid_search
            service = get_hybrid_search()

            # Execute search
            response = await service.search(
                query=query,
                limit=limit,
                mode=mode,
                filters=filters
            )

            took_ms = int((time.time() - start) * 1000)

            # Transform results to frontend format
            raw_results = response.get('results', [])
            formatted_results = []
            filtered_count = 0  # Track how many were filtered by score

            for r in raw_results:
                # Extract path for name and type detection
                path = r.get('path', '')
                name = path.split('/')[-1] if path else r.get('id', 'unknown')

                # Detect type from extension
                ext = name.split('.')[-1].lower() if '.' in name else ''
                doc_extensions = {'md', 'txt', 'rst', 'adoc', 'html', 'pdf'}
                code_extensions = {'py', 'js', 'ts', 'tsx', 'jsx', 'rs', 'go', 'java', 'c', 'cpp', 'h', 'hpp', 'cs', 'rb', 'php', 'swift', 'kt'}

                if ext in doc_extensions:
                    file_type = 'doc'
                elif ext in code_extensions:
                    file_type = 'code'
                else:
                    file_type = 'file'

                # FIX_95.12: RRF scores are in range 0.001-0.03 (formula: weight/(k+rank), k=60)
                # Don't normalize - use raw RRF score for threshold comparison
                score = r.get('rrf_score') or r.get('score') or 0
                relevance = score  # Keep raw score for accurate filtering

                # FIX_95.12: Filter by minimum score threshold (0.005 default for RRF)
                if relevance < min_score:
                    filtered_count += 1
                    if filtered_count <= 3:  # Log first 3 filtered for debugging
                        logger.debug(f"[SEARCH] Filtered: {path} (score={score:.6f} < min={min_score})")
                    continue

                # FIX_95.12: Scale RRF score (0.001-0.03) to display range (0-1)
                # Max theoretical RRF: 2 * (1/(60+1)) ≈ 0.033 for rank 1 in both sources
                display_relevance = min(relevance * 30, 1.0)  # Scale up for UI display

                formatted_results.append({
                    'id': r.get('id') or path,
                    'name': name,
                    'path': path,
                    'type': file_type,
                    'relevance': round(display_relevance, 3),
                    'raw_score': round(relevance, 6),  # Keep raw for debugging
                    'preview': (r.get('content') or '')[:150],  # First 150 chars
                    'source': r.get('source', response.get('mode', 'hybrid')),
                    # Phase 68.2: Date fields for sorting
                    'created_time': r.get('created_time', 0),
                    'modified_time': r.get('modified_time', 0),
                    # Phase 69.4: Size for display
                    'size': r.get('size') or r.get('size_bytes', 0)
                })

            # Emit results
            await sio.emit('search_results', {
                'results': formatted_results,
                'total': len(formatted_results),
                'total_raw': len(raw_results),  # Phase 68.2: Total before filtering
                'filtered': filtered_count,      # Phase 68.2: How many filtered by score
                'query': query,
                'took_ms': took_ms,
                'mode': response.get('mode', mode),
                'sources': response.get('sources', []),
                'min_score': min_score
            }, to=sid)

            logger.info(f"[SEARCH] Found {len(formatted_results)} results in {took_ms}ms (mode={response.get('mode')}, filtered={filtered_count})")

        except Exception as e:
            logger.error(f"[SEARCH] Error: {e}", exc_info=True)
            await sio.emit('search_error', {
                'error': str(e),
                'query': query
            }, to=sid)

    print("  [Handlers] search_handlers registered (search_query)")
