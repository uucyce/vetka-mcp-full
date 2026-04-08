"""
VETKA Phase 68: Hybrid Search Module

@file search/__init__.py
@status ACTIVE
@phase Phase 68
@description Hybrid search with RRF fusion (Qdrant + Weaviate)
@lastAudit 2026-01-18
"""

from .rrf_fusion import weighted_rrf, normalize_results
from .hybrid_search import HybridSearchService, get_hybrid_search

__all__ = [
    'weighted_rrf',
    'normalize_results',
    'HybridSearchService',
    'get_hybrid_search',
]
