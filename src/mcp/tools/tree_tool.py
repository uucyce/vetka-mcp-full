"""
Tools 2 & 3: vetka_get_tree and vetka_get_node
Tree structure navigation and node details.

@status: active
@phase: 96
@depends: base_tool, singletons, qdrant_client
@used_by: mcp_server, stdio_server
"""

from typing import Any, Dict
from .base_tool import BaseMCPTool


class GetTreeTool(BaseMCPTool):
    """Get VETKA tree structure (folders and files)"""
    
    @property
    def name(self) -> str:
        return "vetka_get_tree"
    
    @property
    def description(self) -> str:
        return "Get VETKA folder and file hierarchy (tree structure) with optional depth limit."
    
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Root path to start tree from (default: '/')",
                    "default": "/"
                },
                "depth": {
                    "type": "integer",
                    "description": "Maximum depth to include (1-5, default: 3)",
                    "default": 3
                }
            },
            "required": []
        }
    
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get tree structure"""
        path = arguments.get('path', '/').strip('/')
        depth = min(max(arguments.get('depth', 3), 1), 5)  # Clamp to 1-5
        
        try:
            from src.initialization.singletons import get_memory_manager
            memory = get_memory_manager()
            
            if not memory or not memory.qdrant:
                return {
                    'success': False,
                    'error': 'Qdrant not connected',
                    'result': None
                }
            
            # Fetch from Qdrant
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            all_points = []
            offset = None
            
            while True:
                results, offset = memory.qdrant.scroll(
                    collection_name='vetka_elisya',
                    scroll_filter=Filter(
                        must=[FieldCondition(key="type", match=MatchValue(value="scanned_file"))]
                    ),
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )
                all_points.extend(results)
                if offset is None:
                    break
            
            # Build tree structure
            nodes = []
            edges = []
            
            # Root node
            nodes.append({
                'id': 'root',
                'type': 'root',
                'name': 'VETKA',
                'path': '/',
                'depth': 0
            })
            
            # Add folder nodes (inferred from file paths)
            folders_seen = set()
            
            for point in all_points:
                payload = point.payload or {}
                file_path = payload.get('path', '')
                
                if not file_path:
                    continue
                
                # Extract folder path
                parts = file_path.split('/')
                current_path = ''
                
                for i, part in enumerate(parts[:-1]):  # All but last (filename)
                    if not part:
                        continue
                    
                    current_path = (current_path + '/' + part).lstrip('/')
                    depth_level = current_path.count('/') + 1
                    
                    if depth_level > depth:
                        break
                    
                    if current_path not in folders_seen:
                        folders_seen.add(current_path)
                        folder_id = f"folder_{hash(current_path) % 1000000}"
                        
                        nodes.append({
                            'id': folder_id,
                            'type': 'branch',
                            'name': part,
                            'path': current_path,
                            'depth': depth_level
                        })
                        
                        # Edge to parent
                        if depth_level == 1:
                            parent_id = 'root'
                        else:
                            parent_path = '/'.join(current_path.split('/')[:-1])
                            parent_id = f"folder_{hash(parent_path) % 1000000}"
                        
                        edges.append({
                            'from': parent_id,
                            'to': folder_id,
                            'type': 'contains'
                        })
            
            # Add file nodes (only to specified depth)
            for point in all_points:
                payload = point.payload or {}
                file_path = payload.get('path', '')
                
                if not file_path:
                    continue
                
                # Check depth
                parts = file_path.split('/')
                file_depth = len([p for p in parts if p]) - 1
                
                if file_depth > depth:
                    continue
                
                # Get parent folder
                parent_parts = parts[:-1]
                parent_path = '/'.join([p for p in parent_parts if p])
                
                if parent_path:
                    parent_id = f"folder_{hash(parent_path) % 1000000}"
                else:
                    parent_id = 'root'
                
                # Add file node
                file_id = str(point.id)
                nodes.append({
                    'id': file_id,
                    'type': 'leaf',
                    'name': payload.get('name', 'file'),
                    'path': file_path,
                    'depth': file_depth,
                    'extension': payload.get('extension', '')
                })
                
                # Edge to parent
                edges.append({
                    'from': parent_id,
                    'to': file_id,
                    'type': 'contains'
                })
            
            return {
                'success': True,
                'result': {
                    'path': path,
                    'depth': depth,
                    'nodes': nodes,
                    'edges': edges,
                    'total_nodes': len(nodes),
                    'total_edges': len(edges)
                },
                'error': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Tree fetch failed: {str(e)}',
                'result': None
            }


class GetNodeTool(BaseMCPTool):
    """Get details about a specific node (file or folder)"""
    
    @property
    def name(self) -> str:
        return "vetka_get_node"
    
    @property
    def description(self) -> str:
        return "Get detailed information about a specific file or folder node in VETKA."
    
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the node (file or folder)"
                }
            },
            "required": ["path"]
        }
    
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get node details"""
        node_path = arguments.get('path', '').strip('/')
        
        if not node_path:
            return {
                'success': False,
                'error': 'Path required',
                'result': None
            }
        
        try:
            from src.initialization.singletons import get_memory_manager
            memory = get_memory_manager()
            
            if not memory or not memory.qdrant:
                return {
                    'success': False,
                    'error': 'Qdrant not connected',
                    'result': None
                }
            
            # Search for node by path
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            results, _ = memory.qdrant.scroll(
                collection_name='vetka_elisya',
                scroll_filter=Filter(
                    must=[FieldCondition(key="path", match=MatchValue(value=node_path))]
                ),
                limit=1,
                with_payload=True,
                with_vectors=False
            )
            
            if not results:
                return {
                    'success': False,
                    'error': f'Node not found: {node_path}',
                    'result': None
                }
            
            point = results[0]
            payload = point.payload or {}
            
            # Build node details
            node_details = {
                'id': str(point.id),
                'path': payload.get('path', ''),
                'name': payload.get('name', 'unknown'),
                'type': 'file',
                'extension': payload.get('extension', ''),
                'size_bytes': payload.get('size_bytes', 0),
                'created_time': payload.get('created_time', 0),
                'modified_time': payload.get('modified_time', 0),
                'content_preview': (payload.get('content', '')[:500] + '...') if payload.get('content') else '',
                'lines': payload.get('lines', 0),
                'depth': payload.get('depth', 0)
            }
            
            return {
                'success': True,
                'result': node_details,
                'error': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Node fetch failed: {str(e)}',
                'result': None
            }
