"""
Tool 1: vetka_search
Semantic search through VETKA knowledge base using Weaviate/Qdrant embeddings.

@status: active
@phase: 96
@depends: base_tool, singletons, semantic_tagger
@used_by: mcp_server, stdio_server
"""

from typing import Any, Dict
from .base_tool import BaseMCPTool


class SearchTool(BaseMCPTool):
    """Semantic search tool for VETKA knowledge base"""
    
    def __init__(self):
        self._memory_manager = None
    
    @property
    def name(self) -> str:
        return "vetka_search"
    
    @property
    def description(self) -> str:
        return "Search VETKA knowledge base using semantic search (embeddings). Returns relevant files and content."
    
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g., 'authentication middleware', 'error handling')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 10, max: 50)",
                    "default": 10
                },
                "min_score": {
                    "type": "number",
                    "description": "Minimum similarity score (0.0-1.0, default: 0.3)",
                    "default": 0.3
                }
            },
            "required": ["query"]
        }
    
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute semantic search"""
        query = arguments.get('query', '')
        limit = min(arguments.get('limit', 10), 50)  # Cap at 50
        min_score = arguments.get('min_score', 0.3)
        
        if not query or len(query) < 2:
            return {
                'success': False,
                'error': 'Query too short (min 2 characters)',
                'result': None
            }
        
        try:
            # Get memory manager (lazy import to avoid circular dependencies)
            from src.initialization.singletons import get_memory_manager
            memory = get_memory_manager()
            
            if not memory or not memory.qdrant:
                return {
                    'success': False,
                    'error': 'Qdrant vector database not connected',
                    'result': None
                }
            
            # Use SemanticTagger for semantic search
            from src.knowledge_graph.semantic_tagger import SemanticTagger
            
            tagger = SemanticTagger(
                qdrant_client=memory.qdrant,
                collection='vetka_elisya'
            )
            
            # Search by semantic tag (treats query as semantic anchor)
            files = tagger.find_files_by_semantic_tag(
                tag=query,
                limit=limit,
                min_score=min_score
            )
            
            # Format results
            results = []
            for f in files:
                results.append({
                    'id': f.get('id'),
                    'name': f.get('name', 'unknown'),
                    'path': f.get('path', ''),
                    'extension': f.get('extension', ''),
                    'score': round(f.get('score', 0), 3),
                    'snippet': (f.get('content', '')[:200] + '...') if f.get('content') else ''
                })
            
            return {
                'success': True,
                'result': {
                    'query': query,
                    'count': len(results),
                    'files': results
                },
                'error': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Search failed: {str(e)}',
                'result': None
            }
