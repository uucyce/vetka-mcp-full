# file: src/mcp/tools/web_search_tool.py
# MARKER_102.3_START
"""
MARKER_119.7: Tavily web search tool for pipeline @researcher.

Pre-fetches web search results to inject into researcher's LLM context.
Graceful fallback: if Tavily unavailable, returns empty results (non-fatal).

@status: active
@phase: 119.7
@depends: base_tool, unified_key_manager, tavily-python
@used_by: agent_pipeline._research(), mcp_server
"""

import logging
from typing import Any, Dict

from .base_tool import BaseMCPTool

logger = logging.getLogger(__name__)


class WebSearchTool(BaseMCPTool):
    """Web search via Tavily API."""

    @property
    def name(self) -> str:
        return "vetka_web_search"

    @property
    def description(self) -> str:
        return "Search the web using Tavily API. Returns relevant snippets with titles, URLs, and content."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max results to return (1-10, default 3)"
                },
                "search_depth": {
                    "type": "string",
                    "description": "'basic' (fast) or 'advanced' (thorough). Default: basic"
                }
            },
            "required": ["query"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query", "")
        max_results = min(arguments.get("max_results", 3), 10)
        search_depth = arguments.get("search_depth", "basic")

        if not query:
            return {"success": False, "error": "Query is required", "result": None}

        # Get Tavily API key
        try:
            from src.utils.unified_key_manager import get_key_manager, ProviderType
            km = get_key_manager()
            api_key = km.get_key_with_rotation(ProviderType.TAVILY)
            if not api_key:
                logger.debug("[WebSearch] No Tavily API key available")
                return {"success": False, "error": "No Tavily API key configured", "result": None}
        except Exception as e:
            logger.debug(f"[WebSearch] Key manager error: {e}")
            return {"success": False, "error": f"Key manager error: {e}", "result": None}

        # Call Tavily
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=api_key)
            response = client.search(
                query=query,
                max_results=max_results,
                search_depth=search_depth
            )

            # Format results
            results = []
            for item in response.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", "")[:500],
                    "score": item.get("score", 0)
                })

            return {
                "success": True,
                "result": {
                    "query": query,
                    # Keep native Tavily shape (title/url/content/score) for unified_search adapter.
                    "results": results,
                    "answer": response.get("answer", "")
                }
            }

        except ImportError:
            logger.warning("[WebSearch] tavily-python not installed. Run: pip install tavily-python")
            return {"success": False, "error": "tavily-python not installed", "result": None}
        except Exception as e:
            logger.warning(f"[WebSearch] Tavily API error: {e}")
            return {"success": False, "error": str(e), "result": None}


def register_web_search_tool(tool_list: list):
    """Register web search tool with a tool registry list."""
    tool_list.append(WebSearchTool())
# MARKER_102.3_END
