"""
Semantic search through VETKA knowledge base.

@status: active
@phase: 96
@depends: base_tool, singletons, semantic_tagger
@used_by: mcp_server, stdio_server
"""
from typing import Any, Dict, List
from .base_tool import BaseMCPTool


class SearchKnowledgeTool(BaseMCPTool):
    """Semantic search across VETKA knowledge base (files, notes, embeddings)"""

    def __init__(self):
        self._memory = None
        self._tagger = None

    def _get_memory(self):
        """Lazy load memory manager"""
        if self._memory is None:
            try:
                from src.initialization.singletons import get_memory_manager
                self._memory = get_memory_manager()
            except ImportError:
                pass
            except Exception:
                pass
        return self._memory

    def _get_tagger(self):
        """Lazy load semantic tagger"""
        if self._tagger is None:
            memory = self._get_memory()
            if memory and memory.qdrant:
                try:
                    from src.knowledge_graph.semantic_tagger import SemanticTagger
                    self._tagger = SemanticTagger(
                        qdrant_client=memory.qdrant,
                        collection='vetka_elisya'
                    )
                except ImportError:
                    pass
                except Exception:
                    pass
        return self._tagger

    @property
    def name(self) -> str:
        return "vetka_search_knowledge"

    @property
    def description(self) -> str:
        return "Semantic search across VETKA knowledge base using embeddings"

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query"
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum results (max 50)"
                },
                "min_score": {
                    "type": "number",
                    "default": 0.3,
                    "description": "Minimum relevance score (0.0-1.0)"
                },
                "file_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by file extensions (e.g. ['py', 'md'])"
                }
            },
            "required": ["query"]
        }

    def validate_arguments(self, args: Dict[str, Any]) -> str:
        query = args.get("query", "")
        if not query or len(query) < 2:
            return "Query must be at least 2 characters"
        limit = args.get("limit", 10)
        if not isinstance(limit, int) or limit < 1:
            return "Limit must be a positive integer"
        return None

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments["query"]
        limit = min(arguments.get("limit", 10), 50)
        min_score = arguments.get("min_score", 0.3)
        file_types = arguments.get("file_types", [])

        results: List[Dict] = []

        # Try semantic search via tagger
        tagger = self._get_tagger()
        if tagger:
            try:
                search_results = tagger.find_files_by_semantic_tag(
                    tag=query,
                    limit=limit * 2,  # Get extra to filter
                    min_score=min_score
                )

                for r in search_results:
                    score = r.get('score', 0)
                    if score < min_score:
                        continue

                    path = r.get('path', '')

                    # Filter by file types if specified
                    if file_types:
                        ext = path.split('.')[-1] if '.' in path else ''
                        if ext not in file_types:
                            continue

                    results.append({
                        "path": path,
                        "name": r.get('name', ''),
                        "score": round(score, 3),
                        "snippet": (r.get('content', '')[:300] + '...') if r.get('content') else None,
                        "extension": r.get('extension', '')
                    })

                    if len(results) >= limit:
                        break

            except Exception as e:
                # Fall through to return what we have
                pass

        # Return results (may be empty if no tagger available)
        return {
            "success": True,
            "result": {
                "query": query,
                "count": len(results),
                "results": results,
                "note": "Semantic search via Qdrant embeddings" if results else "No results or Qdrant not available"
            },
            "error": None
        }
