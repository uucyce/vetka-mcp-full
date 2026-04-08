"""
MARKER_119.8: Context7 library docs tool for pipeline @coder.

Pre-fetches up-to-date library documentation to inject into coder's LLM context.
Uses Context7 two-step API: resolve-library-id -> get-library-docs.
Graceful fallback: if Context7 unavailable, returns empty (non-fatal).

@status: active
@phase: 119.8
@depends: base_tool, httpx
@used_by: agent_pipeline._execute_subtask(), mcp_server
"""

import logging
from typing import Any, Dict

from .base_tool import BaseMCPTool

logger = logging.getLogger(__name__)

# Module-level cache for resolved library IDs
_LIBRARY_ID_CACHE: Dict[str, str] = {}

CONTEXT7_BASE_URL = "https://context7.com/api"


class LibraryDocsTool(BaseMCPTool):
    """Fetch up-to-date library documentation via Context7 API."""

    @property
    def name(self) -> str:
        return "vetka_library_docs"

    @property
    def description(self) -> str:
        return "Fetch up-to-date library documentation via Context7. Resolves library name to ID, then fetches relevant docs."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "library": {
                    "type": "string",
                    "description": "Library/package name (e.g., 'fastapi', 'react', 'numpy')"
                },
                "topic": {
                    "type": "string",
                    "description": "Specific topic to search docs for (e.g., 'websockets', 'routing')"
                },
                "tokens": {
                    "type": "integer",
                    "description": "Max tokens of documentation to return (default 3000)"
                }
            },
            "required": ["library"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        library = arguments.get("library", "").strip()
        topic = arguments.get("topic", "")
        tokens = min(arguments.get("tokens", 3000), 10000)

        if not library:
            return {"success": False, "error": "Library name is required", "result": None}

        try:
            import httpx
        except ImportError:
            logger.warning("[LibDocs] httpx not installed")
            return {"success": False, "error": "httpx not installed", "result": None}

        # Step 1: Resolve library ID (use cache if available)
        library_id = _LIBRARY_ID_CACHE.get(library)
        if not library_id:
            try:
                with httpx.Client(timeout=15.0) as client:
                    resp = client.get(
                        f"{CONTEXT7_BASE_URL}/v1/search",
                        params={"query": library}
                    )
                    resp.raise_for_status()
                    data = resp.json()

                results = data.get("results", [])
                if not results:
                    return {"success": False, "error": f"Library '{library}' not found on Context7", "result": None}

                # Pick best match: prefer exact name match, then highest trust score
                best = results[0]
                for r in results:
                    if r.get("name", "").lower() == library.lower():
                        best = r
                        break

                library_id = best.get("id", "")
                if not library_id:
                    return {"success": False, "error": "No library ID in Context7 response", "result": None}

                _LIBRARY_ID_CACHE[library] = library_id
                logger.debug(f"[LibDocs] Resolved '{library}' -> '{library_id}'")

            except httpx.TimeoutException:
                return {"success": False, "error": "Context7 resolve timeout", "result": None}
            except Exception as e:
                logger.debug(f"[LibDocs] Resolve error: {e}")
                return {"success": False, "error": f"Context7 resolve error: {e}", "result": None}

        # Step 2: Fetch library docs
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(
                    f"{CONTEXT7_BASE_URL}/v1/docs",
                    params={
                        "libraryId": library_id,
                        "topic": topic or library,
                        "tokens": tokens
                    }
                )
                resp.raise_for_status()
                data = resp.json()

            docs = data.get("content", "")
            if not docs:
                docs = data.get("docs", "")

            return {
                "success": True,
                "result": {
                    "library": library,
                    "library_id": library_id,
                    "topic": topic or library,
                    "docs": docs[:5000],
                    "tokens_used": len(docs.split()) if docs else 0
                }
            }

        except httpx.TimeoutException:
            return {"success": False, "error": "Context7 docs timeout", "result": None}
        except Exception as e:
            logger.debug(f"[LibDocs] Docs fetch error: {e}")
            return {"success": False, "error": f"Context7 docs error: {e}", "result": None}


def register_library_docs_tool(tool_list: list):
    """Register library docs tool with a tool registry list."""
    tool_list.append(LibraryDocsTool())
