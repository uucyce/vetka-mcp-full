# file: src/api/handlers/web_search_handler.py
# MARKER_102.2_START
"""
Web search API endpoint handler for Tavily integration.
Provides REST endpoint for web search functionality.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging

from src.mcp.tools.web_search_tool import WebSearchTool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


class WebSearchRequest(BaseModel):
    """Request model for web search endpoint."""
    query: str
    max_results: Optional[int] = 5
    search_depth: Optional[str] = "basic"


class WebSearchResult(BaseModel):
    """Individual search result."""
    title: str
    url: str
    content: str
    score: Optional[float] = None


class WebSearchResponse(BaseModel):
    """Response model for web search endpoint."""
    query: str
    results: List[WebSearchResult]
    total_results: int
    error: Optional[str] = None


@router.post("/web", response_model=WebSearchResponse)
async def web_search(request: WebSearchRequest) -> WebSearchResponse:
    """
    Perform web search using Tavily API.
    
    Args:
        request: WebSearchRequest with query and optional parameters
        
    Returns:
        WebSearchResponse with search results
        
    Raises:
        HTTPException: If search fails critically
    """
    try:
        logger.info(f"Web search request: query='{request.query}', max_results={request.max_results}")
        
        # Initialize web search tool
        search_tool = WebSearchTool()
        
        # Perform search
        raw_results = await search_tool.search(
            query=request.query,
            max_results=request.max_results,
            search_depth=request.search_depth
        )
        
        # Parse results
        results = []
        if raw_results and isinstance(raw_results, list):
            for item in raw_results:
                results.append(WebSearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                    score=item.get("score")
                ))
        
        logger.info(f"Web search completed: {len(results)} results")
        
        return WebSearchResponse(
            query=request.query,
            results=results,
            total_results=len(results),
            error=None
        )
        
    except Exception as e:
        logger.error(f"Web search error: {e}", exc_info=True)
        # Return graceful error response instead of raising
        return WebSearchResponse(
            query=request.query,
            results=[],
            total_results=0,
            error=str(e)
        )


def register_web_search_routes(app):
    """Register web search routes with the FastAPI application."""
    app.include_router(router)
    logger.info("Web search routes registered at /api/search/web")

# MARKER_102.2_END