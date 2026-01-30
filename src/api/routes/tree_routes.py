"""
VETKA Tree Routes - FastAPI Version

@file tree_routes.py
@status ACTIVE
@phase Phase 39.3
@lastAudit 2026-01-05

Tree/Knowledge Graph API routes.
Migrated from src/server/routes/tree_routes.py (Flask Blueprint)

Endpoints:
- GET /api/tree/data - Main tree data API with FAN layout
- POST /api/tree/clear-semantic-cache - Clear semantic DAG cache
- GET /api/tree/export/blender - Export to Blender format
- GET,POST /api/tree/knowledge-graph - Get Knowledge Graph structure
- POST /api/tree/clear-knowledge-cache - Clear Knowledge Graph cache
"""

import os
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List


router = APIRouter(prefix="/api/tree", tags=["tree"])


# Module-level cache for semantic DAG (computed once per session)
_semantic_cache = {
    'nodes': None,
    'edges': None,
    'positions': None,
    'stats': None
}

# Module-level cache for Knowledge Graph (computed once per session)
_knowledge_graph_cache = {
    'tags': None,
    'edges': None,
    'chain_edges': None,
    'positions': None,
    'knowledge_levels': None,
    'rrf_stats': None
}


# ============================================================
# PYDANTIC MODELS
# ============================================================

class KnowledgeGraphRequest(BaseModel):
    """Request for Knowledge Graph data."""
    force_refresh: Optional[bool] = False
    min_cluster_size: Optional[int] = 3
    similarity_threshold: Optional[float] = 0.7
    file_positions: Optional[Dict[str, Any]] = {}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _get_memory_manager(request: Request):
    """Get memory manager from app state or singleton."""
    memory = getattr(request.app.state, 'memory_manager', None)
    if not memory:
        from src.initialization.components_init import get_memory_manager
        memory = get_memory_manager()
    return memory


# ============================================================
# ROUTES
# ============================================================

@router.get("/data")
async def get_tree_data(
    mode: str = Query("directory", description="Layout mode: directory, semantic, or both"),
    request: Request = None
):
    """
    Phase 17.2: Multi-tree layout with directory/semantic blend.

    Query params:
    - mode: 'directory' (default), 'semantic', or 'both'

    Returns:
    - tree: {nodes, edges}
    - layouts: {directory: {...}, semantic: {...}} (when mode='both')
    - semantic_data: {nodes, edges, stats} (when mode='semantic' or 'both')
    """
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    from datetime import datetime
    import math

    try:
        memory = _get_memory_manager(request)
        qdrant = memory.qdrant if memory else None

        if not qdrant:
            return {
                'error': 'Qdrant not connected',
                'tree': {'nodes': [], 'edges': []}
            }

        # Import layout functions
        from src.layout.fan_layout import calculate_directory_fan_layout
        from src.layout.incremental import (
            detect_new_branches,
            incremental_layout_update,
            get_last_branch_count,
            set_last_branch_count,
        )
        from src.orchestration.cam_engine import calculate_surprise_metrics_for_tree

        # ═══════════════════════════════════════════════════════════════════
        # STEP 1: Get ALL scanned files from Qdrant
        # ═══════════════════════════════════════════════════════════════════
        all_files = []
        offset = None

        while True:
            results, offset = qdrant.scroll(
                collection_name='vetka_elisya',
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="type", match=MatchValue(value="scanned_file")),
                        FieldCondition(key="deleted", match=MatchValue(value=False))
                    ]
                ),
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            all_files.extend(results)
            if offset is None:
                break

        print(f"[API] Found {len(all_files)} files in Qdrant")

        if not all_files:
            return {'tree': {'nodes': [], 'edges': []}}

        # ═══════════════════════════════════════════════════════════════════
        # STEP 1.5: Mark deleted files (don't filter - show as ghost/transparent)
        # Phase 90.11: Keep deleted files but mark them for transparent rendering
        # ═══════════════════════════════════════════════════════════════════
        valid_files = []
        deleted_count = 0
        browser_count = 0
        for point in all_files:
            file_path = (point.payload or {}).get('path', '')
            # Phase 54.5: Keep browser:// virtual paths (from drag & drop)
            if file_path.startswith('browser://'):
                valid_files.append(point)
                browser_count += 1
            elif file_path:
                # Phase 90.11: Mark as deleted if file doesn't exist on disk
                if not os.path.exists(file_path):
                    point.payload['is_ghost'] = True  # Ghost file - render transparent
                    deleted_count += 1
                valid_files.append(point)

        if deleted_count > 0 or browser_count > 0:
            print(f"[API] Ghost files: {deleted_count}, browser files: {browser_count}, total: {len(valid_files)}")

        all_files = valid_files

        # ═══════════════════════════════════════════════════════════════════
        # STEP 2: Build folder hierarchy
        # ═══════════════════════════════════════════════════════════════════
        folders = {}
        files_by_folder = {}

        for point in all_files:
            p = point.payload or {}
            file_path = p.get('path', '')
            file_name = p.get('name', 'unknown')

            parent_folder = p.get('parent_folder', '')
            if not parent_folder and file_path:
                parent_folder = '/'.join(file_path.split('/')[:-1])
            if not parent_folder:
                parent_folder = 'root'

            if parent_folder not in files_by_folder:
                files_by_folder[parent_folder] = []
            files_by_folder[parent_folder].append({
                'id': str(point.id),
                'name': file_name,
                'path': file_path,
                'created_time': p.get('created_time', 0),
                'modified_time': p.get('modified_time', 0),
                'extension': p.get('extension', ''),
                'content': p.get('content', '')[:150] if p.get('content') else '',
                'is_ghost': p.get('is_ghost', False)  # Phase 90.11: Ghost files (deleted from disk)
            })

            # Phase 54.5: Handle browser:// paths specially
            if parent_folder.startswith('browser://'):
                # browser://folder_name -> ['browser:', 'folder_name']
                browser_parts = parent_folder.replace('browser://', '').split('/')
                browser_parts = [p for p in browser_parts if p]  # Remove empty parts

                # Create browser root folder if needed
                browser_root = 'browser://' + browser_parts[0] if browser_parts else 'browser://unknown'
                if browser_root not in folders:
                    folders[browser_root] = {
                        'path': browser_root,
                        'name': browser_parts[0] if browser_parts else 'unknown',
                        'parent_path': None,  # Browser folders are top-level
                        'depth': 1,
                        'children': []
                    }

                # Create nested browser folders
                for i in range(1, len(browser_parts)):
                    folder_path = 'browser://' + '/'.join(browser_parts[:i+1])
                    parent_path = 'browser://' + '/'.join(browser_parts[:i])

                    if folder_path not in folders:
                        folders[folder_path] = {
                            'path': folder_path,
                            'name': browser_parts[i],
                            'parent_path': parent_path,
                            'depth': i + 1,
                            'children': []
                        }

                    if parent_path in folders and folder_path not in folders[parent_path]['children']:
                        folders[parent_path]['children'].append(folder_path)
            else:
                # Original logic for regular file paths
                parts = parent_folder.split('/') if parent_folder != 'root' else ['root']
                for i in range(len(parts)):
                    folder_path = '/'.join(parts[:i+1]) if parts[0] != 'root' else 'root' if i == 0 else '/'.join(parts[:i+1])
                    parent_path = '/'.join(parts[:i]) if i > 0 else None

                    if folder_path and folder_path not in folders:
                        folders[folder_path] = {
                            'path': folder_path,
                            'name': parts[i] if parts[i] else 'root',
                            'parent_path': parent_path,
                            'depth': i,
                            'children': []
                        }

                    if parent_path and parent_path in folders and folder_path not in folders[parent_path]['children']:
                        folders[parent_path]['children'].append(folder_path)

        print(f"[API] Built {len(folders)} folders")

        # ═══════════════════════════════════════════════════════════════════
        # STEP 2.5: CAM SURPRISE METRICS
        # ═══════════════════════════════════════════════════════════════════
        cam_metrics = {}
        try:
            cam_metrics = calculate_surprise_metrics_for_tree(
                files_by_folder=files_by_folder,
                qdrant_client=qdrant,
                collection_name='vetka_elisya'
            )
            print(f"[CAM] Calculated surprise metrics for {len(cam_metrics)} files")
        except Exception as cam_err:
            print(f"[CAM] Warning: Could not calculate surprise metrics: {cam_err}")

        # ═══════════════════════════════════════════════════════════════════
        # STEP 3: FAN LAYOUT
        # ═══════════════════════════════════════════════════════════════════
        positions, root_folders, BRANCH_LENGTH, FAN_ANGLE, Y_PER_DEPTH = calculate_directory_fan_layout(
            folders=folders,
            files_by_folder=files_by_folder,
            all_files=[],
            socketio_instance=None  # No socketio in FastAPI context
        )

        # Incremental update
        new_branches, affected_nodes = detect_new_branches(
            folders, positions, get_last_branch_count()
        )

        if new_branches or affected_nodes:
            print(f"[PHASE 15] Detected changes: {len(new_branches)} new branches")
            incremental_layout_update(new_branches, affected_nodes, folders, positions, files_by_folder)
            set_last_branch_count(len(folders))
        else:
            set_last_branch_count(len(folders))

        # ═══════════════════════════════════════════════════════════════════
        # STEP 4: Build nodes list
        # ═══════════════════════════════════════════════════════════════════
        nodes = []
        edges = []

        root_id = "main_tree_root"
        nodes.append({
            'id': root_id,
            'type': 'root',
            'name': 'VETKA',
            'visual_hints': {
                'layout_hint': {'expected_x': 0, 'expected_y': 0, 'expected_z': 0},
                'color': '#8B4513'
            }
        })

        EXT_COLORS = {
            '.py': '#4A5A3A', '.js': '#5A5A3A', '.ts': '#3A4A6A',
            '.md': '#3A4A5A', '.json': '#5A4A3A', '.html': '#5A4A4A'
        }

        # Folder nodes
        for folder_path, folder in folders.items():
            folder_id = f"folder_{abs(hash(folder_path)) % 100000000}"
            pos = positions.get(folder_path, {'x': 0, 'y': 0})

            if folder['parent_path']:
                parent_id = f"folder_{abs(hash(folder['parent_path'])) % 100000000}"
            else:
                parent_id = root_id

            nodes.append({
                'id': folder_id,
                'type': 'branch',
                'name': folder['name'],
                'parent_id': parent_id,
                'metadata': {
                    'path': folder_path,
                    'depth': folder['depth'],
                    'file_count': len(files_by_folder.get(folder_path, []))
                },
                'visual_hints': {
                    'layout_hint': {
                        'expected_x': pos.get('x', 0),
                        'expected_y': pos.get('y', 0),
                        'expected_z': 0
                    },
                    'color': '#8B4513'
                }
            })

            edges.append({
                'from': parent_id,
                'to': folder_id,
                'semantics': 'contains'
            })

        # File nodes
        for folder_path, folder_files in files_by_folder.items():
            folder_id = f"folder_{abs(hash(folder_path)) % 100000000}"

            for file_data in folder_files:
                pos = positions.get(file_data['id'], {'x': 0, 'y': 0})
                ext = file_data.get('extension', '')
                color = EXT_COLORS.get(ext, '#3A3A4A')

                folder_depth = folders.get(folder_path, {}).get('depth', 0)
                file_depth = folder_depth + 1

                file_cam = cam_metrics.get(file_data['id'], {})

                # Phase 90.11: Ghost files get muted color
                is_ghost = file_data.get('is_ghost', False)
                ghost_color = '#2A2A2A' if is_ghost else color  # Darker for ghosts

                nodes.append({
                    'id': file_data['id'],
                    'type': 'leaf',
                    'name': file_data['name'],
                    'parent_id': folder_id,
                    'metadata': {
                        'path': file_data['path'],
                        'name': file_data['name'],
                        'extension': ext,
                        'depth': file_depth,
                        'created_time': file_data['created_time'],
                        'modified_time': file_data['modified_time'],
                        'content_preview': file_data.get('content', ''),
                        'qdrant_id': file_data['id'],
                        'is_ghost': is_ghost  # Phase 90.11: Deleted from disk
                    },
                    'visual_hints': {
                        'layout_hint': {
                            'expected_x': pos.get('x', 0),
                            'expected_y': pos.get('y', 0),
                            'expected_z': pos.get('z', 0)
                        },
                        'color': ghost_color,
                        'opacity': 0.3 if is_ghost else 1.0  # Phase 90.11: Transparent ghosts
                    },
                    'cam': {
                        'surprise_metric': file_cam.get('surprise_metric', 0.5),
                        'operation': file_cam.get('cam_operation', 'append')
                    }
                })

                edges.append({
                    'from': folder_id,
                    'to': file_data['id'],
                    'semantics': 'contains'
                })

        print(f"[API] Tree built: {len(nodes)} nodes, {len(edges)} edges")

        # ═══════════════════════════════════════════════════════════════════
        # STEP 5: Build response
        # ═══════════════════════════════════════════════════════════════════
        response = {
            'format': 'vetka-v1.4',
            'source': 'qdrant',
            'mode': mode,
            'tree': {
                'id': root_id,
                'name': 'VETKA',
                'nodes': nodes,
                'edges': edges,
                'metadata': {
                    'total_nodes': len(nodes),
                    'total_edges': len(edges),
                    # Accept both "leaf" and "file" types
                    'total_files': len([n for n in nodes if n['type'] in ['leaf', 'file']]),
                    'total_folders': len(folders)
                }
            }
        }

        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'error': str(e), 'tree': {'nodes': [], 'edges': []}}


@router.post("/clear-semantic-cache")
async def clear_semantic_cache():
    """Clear the semantic DAG cache to force recalculation."""
    global _semantic_cache
    _semantic_cache = {
        'nodes': None,
        'edges': None,
        'positions': None,
        'stats': None
    }
    print("[SEMANTIC] Cache cleared")
    return {'status': 'ok', 'message': 'Semantic cache cleared'}


@router.get("/export/blender")
async def export_blender(
    format: str = Query("json", description="Export format: json, glb, or obj"),
    mode: str = Query("directory", description="Layout mode: directory or semantic"),
    request: Request = None
):
    """
    Export current tree state to Blender-compatible format.

    Query params:
    - format: 'json' (default), 'glb', or 'obj'
    - mode: 'directory' (default) or 'semantic'
    """
    import tempfile
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    try:
        from src.export.blender_exporter import BlenderExporter

        memory = _get_memory_manager(request)
        qdrant = memory.qdrant if memory else None

        if not qdrant:
            raise HTTPException(status_code=500, detail="Qdrant not connected")

        exporter = BlenderExporter(output_format=format)

        # Fetch nodes from Qdrant
        all_files = []
        offset = None
        while True:
            results, offset = qdrant.scroll(
                collection_name='vetka_elisya',
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="type", match=MatchValue(value="scanned_file")),
                        FieldCondition(key="deleted", match=MatchValue(value=False))
                    ]
                ),
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            all_files.extend(results)
            if offset is None:
                break

        # Add root node
        exporter.add_node(
            node_id='main_tree_root',
            pos={'x': 0, 'y': 0, 'z': 0},
            node_type='root',
            label='VETKA'
        )

        # Add file nodes
        for point in all_files:
            p = point.payload or {}
            file_path = p.get('path', '')

            if not file_path or not os.path.exists(file_path):
                continue

            file_id = str(point.id)
            hash_val = abs(hash(file_id))

            exporter.add_node(
                node_id=file_id,
                pos={
                    'x': (hash_val % 1000) - 500,
                    'y': ((hash_val // 1000) % 1000) - 500,
                    'z': ((hash_val // 1000000) % 100) - 50
                },
                node_type='file',
                label=p.get('name', 'file')
            )

            exporter.add_edge(
                from_id='main_tree_root',
                to_id=file_id,
                edge_type='contains'
            )

        # Export to temp file
        ext = 'json' if format == 'json' else format
        fd, filepath = tempfile.mkstemp(suffix=f'.{ext}', prefix='vetka_export_')
        os.close(fd)

        if format == 'glb':
            success = exporter.export_glb(filepath)
            if not success:
                filepath = filepath.replace('.glb', '.json')
                exporter.export_json(filepath)
                format = 'json'
        elif format == 'obj':
            exporter.export_obj(filepath)
        else:
            exporter.export_json(filepath)

        print(f"[BlenderExport] Exported {len(exporter.nodes)} nodes to {filepath}")

        return FileResponse(
            path=filepath,
            filename=f'vetka-tree-{mode}.{format}',
            media_type='application/octet-stream'
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.api_route("/knowledge-graph", methods=["GET", "POST"])
async def get_knowledge_graph(
    request: Request,
    force_refresh: bool = Query(False, description="Force recalculation"),
    min_cluster_size: int = Query(3, description="Minimum files per cluster"),
    similarity_threshold: float = Query(0.7, description="Minimum similarity for edges")
):
    """
    Phase 17.1: Return Knowledge Graph structure for tag-based layout.

    Returns:
    - tags: {tag_id -> {id, name, files, color, position}}
    - edges: [{source, target, type, weight}, ...]
    - positions: {node_id -> {x, y, z, angle, type, knowledge_level, ...}}
    - knowledge_levels: {file_id -> float (0-1)}
    """
    global _knowledge_graph_cache

    try:
        # Parse POST body if present
        file_positions = {}
        if request.method == "POST":
            try:
                body = await request.json()
                force_refresh = body.get('force_refresh', force_refresh)
                min_cluster_size = body.get('min_cluster_size', min_cluster_size)
                similarity_threshold = body.get('similarity_threshold', similarity_threshold)
                file_positions = body.get('file_positions', {})
            except:
                pass

        # Return cached if available
        if not force_refresh and _knowledge_graph_cache['tags'] is not None:
            print("[KG] Returning cached Knowledge Graph")
            return {
                'status': 'ok',
                'source': 'cache',
                'tags': _knowledge_graph_cache['tags'],
                'edges': _knowledge_graph_cache['edges'],
                'chain_edges': _knowledge_graph_cache.get('chain_edges', []),
                'positions': _knowledge_graph_cache['positions'],
                'knowledge_levels': _knowledge_graph_cache['knowledge_levels'],
                'nodes': len(_knowledge_graph_cache['positions'] or {}),
                'rrf_stats': _knowledge_graph_cache.get('rrf_stats', {}),
                'statistics': {
                    'tags': len(_knowledge_graph_cache['tags'] or {}),
                    'edges': len(_knowledge_graph_cache['edges'] or []),
                    'chain_edges': len(_knowledge_graph_cache.get('chain_edges', [])),
                    'positions': len(_knowledge_graph_cache['positions'] or {})
                }
            }

        # Get Qdrant client
        memory = _get_memory_manager(request)
        qdrant = memory.qdrant if memory else None

        if not qdrant:
            return {
                'status': 'error',
                'error': 'Qdrant not connected',
                'tags': {},
                'edges': [],
                'chain_edges': [],
                'positions': {},
                'knowledge_levels': {}
            }

        print(f"[KG] Building Knowledge Graph...")

        # Build Knowledge Graph
        from src.layout.knowledge_layout import build_knowledge_graph_from_qdrant

        kg_data = build_knowledge_graph_from_qdrant(
            qdrant_client=qdrant,
            collection_name='vetka_elisya',
            min_cluster_size=min_cluster_size,
            similarity_threshold=similarity_threshold,
            file_directory_positions=file_positions
        )

        # Cache the result
        _knowledge_graph_cache['tags'] = kg_data['tags']
        _knowledge_graph_cache['edges'] = kg_data['edges']
        _knowledge_graph_cache['chain_edges'] = kg_data.get('chain_edges', [])
        _knowledge_graph_cache['positions'] = kg_data['positions']
        _knowledge_graph_cache['knowledge_levels'] = kg_data['knowledge_levels']
        _knowledge_graph_cache['rrf_stats'] = kg_data.get('rrf_stats', {})

        print(f"[KG] Knowledge Graph built: {len(kg_data['tags'])} tags, {len(kg_data['edges'])} edges")

        return {
            'status': 'ok',
            'source': 'computed',
            'tags': kg_data['tags'],
            'edges': kg_data['edges'],
            'chain_edges': kg_data.get('chain_edges', []),
            'positions': kg_data['positions'],
            'knowledge_levels': kg_data['knowledge_levels'],
            'nodes': len(kg_data['positions']),
            'rrf_stats': kg_data.get('rrf_stats', {}),
            'statistics': {
                'tags': len(kg_data['tags']),
                'edges': len(kg_data['edges']),
                'chain_edges': len(kg_data.get('chain_edges', [])),
                'positions': len(kg_data['positions'])
            }
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'status': 'error',
            'error': str(e),
            'tags': {},
            'edges': [],
            'chain_edges': [],
            'positions': {},
            'knowledge_levels': {}
        }


@router.post("/clear-knowledge-cache")
async def clear_knowledge_cache():
    """Clear the Knowledge Graph cache to force recalculation."""
    global _knowledge_graph_cache
    _knowledge_graph_cache = {
        'tags': None,
        'edges': None,
        'chain_edges': None,
        'positions': None,
        'knowledge_levels': None,
        'rrf_stats': None
    }
    print("[KG] Cache cleared")
    return {'status': 'ok', 'message': 'Knowledge Graph cache cleared'}
