# MARKER_136.UNIFIED_SEARCH_ROUTE
"""Routes for unified federated search."""

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from src.api.handlers.unified_search import run_unified_search


router = APIRouter(prefix="/api/search", tags=["unified-search"])


class UnifiedSearchRequest(BaseModel):
    query: str
    limit: int = 20
    sources: Optional[List[str]] = None


@router.post("/unified")
async def unified_search_endpoint(body: UnifiedSearchRequest):
    safe_limit = max(1, min(body.limit, 100))
    return run_unified_search(
        query=body.query,
        limit=safe_limit,
        sources=body.sources,
    )
