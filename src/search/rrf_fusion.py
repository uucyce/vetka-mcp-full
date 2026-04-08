"""
VETKA Phase 68: Reciprocal Rank Fusion

@file rrf_fusion.py
@status ACTIVE
@phase Phase 68
@description RRF fusion engine for combining results from multiple search backends
@usedBy hybrid_search.py
@lastAudit 2026-01-18

RRF Formula: score_RRF(d) = Σ w_i × 1/(k + rank_i(d))

Research basis:
- Microsoft GraphRAG 2025: k=60-80 optimal for hybrid search
- Lower k = more weight to top ranks
- Default weights: semantic 50%, keyword 30%, graph 20%
"""

import logging
from typing import List, Dict, Optional, Any, Tuple

logger = logging.getLogger("VETKA_RRF")


def extract_doc_id(result: Dict) -> Optional[str]:
    """
    Extract document ID from result dict.
    Supports multiple ID field formats from Qdrant/Weaviate.

    Args:
        result: Result dict from search backend

    Returns:
        Document ID string or None
    """
    # Try common ID fields in priority order
    for field in ('id', 'node_id', 'path', 'file_id', '_additional'):
        value = result.get(field)
        if value:
            # Handle Weaviate _additional.id format
            if field == '_additional' and isinstance(value, dict):
                return value.get('id')
            if isinstance(value, str):
                return value
    return None


def normalize_results(results: List[Dict], source: str) -> List[Dict]:
    """
    Normalize results from different backends to a common format.

    Args:
        results: Raw results from search backend
        source: Source identifier ('qdrant', 'weaviate', 'graph')

    Returns:
        List of normalized result dicts with 'id', 'score', 'source', and original data
    """
    normalized = []

    for result in results:
        doc_id = extract_doc_id(result)
        if not doc_id:
            continue

        # Extract score based on source
        if source == 'qdrant':
            score = result.get('score', 0.0)
        elif source == 'weaviate':
            # Weaviate returns score in _additional or directly
            additional = result.get('_additional', {})
            score = additional.get('score') or additional.get('certainty') or result.get('score', 0.0)
            # Convert distance to score if needed (1 - distance)
            if 'distance' in additional:
                score = max(0, 1.0 - additional['distance'])
        else:
            score = result.get('score', 0.0)

        # Phase 69.4: Preserve metadata fields for UI display
        normalized.append({
            'id': doc_id,
            'score': float(score) if score else 0.0,
            'source': source,
            'path': result.get('path', ''),
            'content': result.get('content', ''),
            'name': result.get('name', ''),
            'node_type': result.get('node_type', ''),
            'creator': result.get('creator', ''),
            'created_time': result.get('created_time', 0),
            'modified_time': result.get('modified_time', 0),
            'size': result.get('size') or result.get('size_bytes', 0),
            '_raw': result  # Keep original for debugging
        })

    return normalized


def weighted_rrf(
    results_lists: List[List[Dict]],
    weights: Optional[List[float]] = None,
    k: int = 60,
    top_n: int = 20
) -> List[Dict]:
    """
    Weighted Reciprocal Rank Fusion.

    Combines results from multiple search backends using RRF formula:
    score_RRF(d) = Σ w_i × 1/(k + rank_i(d))

    Args:
        results_lists: List of result lists from different backends
                      e.g., [semantic_results, keyword_results, graph_results]
        weights: Per-source weights (default: equal weights)
                e.g., [0.5, 0.3, 0.2]
        k: Smoothing constant (default 60)
           Lower k = more emphasis on top ranks
           Recommended: 60 for balanced, 30 for top-heavy
        top_n: Number of results to return

    Returns:
        Fused results sorted by RRF score, each with:
        - id: Document identifier
        - rrf_score: Combined RRF score
        - original_score: Score from best source
        - sources: List of sources that contained this result
        - path, content, etc: Original document data

    Example:
        >>> semantic = [{'id': 'a', 'score': 0.9}, {'id': 'b', 'score': 0.8}]
        >>> keyword = [{'id': 'b', 'score': 0.95}, {'id': 'c', 'score': 0.7}]
        >>> fused = weighted_rrf([semantic, keyword], weights=[0.6, 0.4])
        >>> # 'b' will score highest (appears in both lists)
    """
    if not results_lists:
        return []

    # Filter out empty lists
    results_lists = [r for r in results_lists if r]
    if not results_lists:
        return []

    # Default to equal weights
    if weights is None:
        weights = [1.0 / len(results_lists)] * len(results_lists)

    # Ensure weights match number of lists
    if len(weights) != len(results_lists):
        logger.warning(f"[RRF] Weight count mismatch: {len(weights)} weights for {len(results_lists)} lists")
        weights = [1.0 / len(results_lists)] * len(results_lists)

    # Accumulate RRF scores per document
    scores: Dict[str, float] = {}
    doc_data: Dict[str, Dict] = {}
    doc_sources: Dict[str, List[str]] = {}
    doc_ranks: Dict[str, Dict[str, int]] = {}  # doc_id -> {source: rank}

    for list_idx, (result_list, weight) in enumerate(zip(results_lists, weights)):
        source_name = f"source_{list_idx}"

        for rank, doc in enumerate(result_list, start=1):
            doc_id = doc.get('id') or extract_doc_id(doc)
            if not doc_id:
                continue

            # Initialize if first time seeing this document
            if doc_id not in scores:
                scores[doc_id] = 0.0
                doc_data[doc_id] = doc.copy()
                doc_sources[doc_id] = []
                doc_ranks[doc_id] = {}

            # RRF formula: weight / (k + rank)
            rrf_contribution = weight / (k + rank)
            scores[doc_id] += rrf_contribution

            # Track sources and ranks
            source = doc.get('source', source_name)
            if source not in doc_sources[doc_id]:
                doc_sources[doc_id].append(source)
            doc_ranks[doc_id][source] = rank

            # Keep the highest original score and best data
            current_score = doc.get('score', 0.0) or 0.0
            existing_score = doc_data[doc_id].get('original_score', 0.0) or 0.0
            if current_score > existing_score:
                doc_data[doc_id].update(doc)
                doc_data[doc_id]['original_score'] = current_score

    # Sort by RRF score descending
    ranked_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    # Build final results
    results = []
    for doc_id in ranked_ids[:top_n]:
        doc = doc_data[doc_id].copy()
        doc['id'] = doc_id
        doc['rrf_score'] = round(scores[doc_id], 6)
        doc['sources'] = doc_sources[doc_id]
        doc['ranks'] = doc_ranks[doc_id]

        # Clean up internal fields
        doc.pop('_raw', None)

        results.append(doc)

    # Log fusion stats
    total_input = sum(len(r) for r in results_lists)
    unique_docs = len(scores)
    multi_source = sum(1 for s in doc_sources.values() if len(s) > 1)

    logger.info(
        f"[RRF] Fused {total_input} results → {unique_docs} unique → {len(results)} returned "
        f"(k={k}, multi-source={multi_source})"
    )

    return results


def compute_rrf_explanation(result: Dict, query: str) -> str:
    """
    Generate human-readable explanation for why a result matched.

    Args:
        result: Result dict with rrf_score, sources, ranks, etc.
        query: Original search query

    Returns:
        Explanation string
    """
    explanations = []

    # Check multi-source boost
    sources = result.get('sources', [])
    if len(sources) > 1:
        explanations.append(f"Found in {len(sources)} search methods")

    # Check semantic similarity
    original_score = result.get('original_score', 0)
    if original_score:
        if original_score > 0.8:
            explanations.append("Very high semantic similarity")
        elif original_score > 0.6:
            explanations.append("High semantic similarity")
        elif original_score > 0.4:
            explanations.append("Moderate semantic similarity")

    # Check if query terms appear in path/name
    query_terms = query.lower().split()
    path = (result.get('path') or result.get('name') or '').lower()
    matching_terms = [t for t in query_terms if t in path]
    if matching_terms:
        explanations.append(f"Path contains: {', '.join(matching_terms)}")

    # Check rank positions
    ranks = result.get('ranks', {})
    top_ranks = [f"{src}:#{r}" for src, r in ranks.items() if r <= 5]
    if top_ranks:
        explanations.append(f"Top-5 in: {', '.join(top_ranks)}")

    return "; ".join(explanations) if explanations else "General relevance"
