"""
Memory tools for MCP server - get, store, search operations.

@status: active
@phase: 109
@depends: base_tool, memory.qdrant_client, memory.user_memory
@used_by: stdio_server
"""

from typing import Any, Dict, Optional
from .base_tool import BaseMCPTool


class MemoryGetTool(BaseMCPTool):
    """Get memory entries from VETKA memory system"""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from src.memory.qdrant_client import get_qdrant_client
                self._client = get_qdrant_client()
            except ImportError:
                pass
        return self._client

    @property
    def name(self) -> str:
        return "vetka_memory_get"

    @property
    def description(self) -> str:
        return "Get memory entries from VETKA long-term memory (Qdrant)"

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for memory"
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum results to return"
                },
                "collection": {
                    "type": "string",
                    "default": "VetkaUserMemories",
                    "description": "Memory collection to search"
                }
            },
            "required": ["query"]
        }

    def safe_execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self.execute(arguments)

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        client = self._get_client()
        if not client:
            return {
                "success": False,
                "error": "Memory system not available. Ensure Qdrant is running."
            }

        query = arguments.get("query", "")
        limit = arguments.get("limit", 10)
        collection = arguments.get("collection", "VetkaUserMemories")

        try:
            results = client.search_by_content(
                query=query,
                collection=collection,
                limit=limit
            )
            return {
                "success": True,
                "result": {
                    "query": query,
                    "count": len(results),
                    "results": results
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class MemoryStoreTool(BaseMCPTool):
    """Store new memory entry in VETKA memory system"""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from src.memory.qdrant_client import get_qdrant_client
                self._client = get_qdrant_client()
            except ImportError:
                pass
        return self._client

    @property
    def name(self) -> str:
        return "vetka_memory_store"

    @property
    def description(self) -> str:
        return "Store new memory entry in VETKA long-term memory"

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Memory content to store"
                },
                "metadata": {
                    "type": "object",
                    "description": "Optional metadata (tags, source, etc.)"
                },
                "collection": {
                    "type": "string",
                    "default": "VetkaUserMemories",
                    "description": "Target collection"
                }
            },
            "required": ["content"]
        }

    def safe_execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self.execute(arguments)

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        client = self._get_client()
        if not client:
            return {
                "success": False,
                "error": "Memory system not available. Ensure Qdrant is running."
            }

        content = arguments.get("content", "")
        metadata = arguments.get("metadata", {})
        collection = arguments.get("collection", "VetkaUserMemories")

        if not content:
            return {
                "success": False,
                "error": "Content is required"
            }

        try:
            from datetime import datetime
            import uuid

            point = {
                "id": str(uuid.uuid4()),
                "vector": client._generate_mock_embedding(content) if hasattr(client, '_generate_mock_embedding') else None,
                "payload": {
                    "content": content,
                    "timestamp": datetime.now().isoformat(),
                    **metadata
                }
            }

            if point["vector"] is None:
                return {
                    "success": False,
                    "error": "Embedding service not available. Install embedding model."
                }

            client.upsert_point(collection=collection, point=point)

            return {
                "success": True,
                "result": {
                    "stored": True,
                    "id": point["id"],
                    "collection": collection
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class MemorySearchTool(BaseMCPTool):
    """Semantic search in VETKA memory system"""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from src.memory.qdrant_client import get_qdrant_client
                self._client = get_qdrant_client()
            except ImportError:
                pass
        return self._client

    @property
    def name(self) -> str:
        return "vetka_memory_search"

    @property
    def description(self) -> str:
        return "Semantic search in VETKA memory with embeddings"

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Semantic search query"
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum results"
                },
                "min_score": {
                    "type": "number",
                    "default": 0.3,
                    "description": "Minimum relevance score (0.0-1.0)"
                }
            },
            "required": ["query"]
        }

    def safe_execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self.execute(arguments)

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        client = self._get_client()
        if not client:
            return {
                "success": False,
                "error": "Memory system not available"
            }

        query = arguments.get("query", "")
        limit = arguments.get("limit", 10)
        min_score = arguments.get("min_score", 0.3)

        try:
            results = client.search_by_content(
                query=query,
                collection="VetkaUserMemories",
                limit=limit
            )

            filtered = [r for r in results if r.get("score", 0) >= min_score]

            return {
                "success": True,
                "result": {
                    "query": query,
                    "total_found": len(results),
                    "returned": len(filtered),
                    "results": filtered
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }