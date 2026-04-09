"""
VETKA Knowledge Routes - FastAPI Version

@file knowledge_routes.py
@status ACTIVE
@phase Phase 39.5
@lastAudit 2026-01-05

Knowledge Graph, ARC, Branch, Vetka API routes.
Migrated from src/server/routes/knowledge_routes.py (Flask Blueprint)

Endpoints:
- POST /api/knowledge-graph/build - Build Knowledge Graph from embeddings
- GET /api/knowledge-graph/for-tag - Build KG for files with a tag
- POST /api/arc/suggest - Generate ARC suggestions
- GET /api/arc/status - Get ARC Solver status
- POST /api/qdrant/deduplicate - Remove duplicate Qdrant entries
- POST /api/branch/create - Create branch from selection
- POST /api/branch/context - Get context for a branch
- POST /api/vetka/create - Create VETKA tree with KG positioning
- GET /api/messages/counts - Get message counts for nodes

Changes from Flask version:
- Blueprint -> APIRouter
- request.get_json() -> Pydantic BaseModel
- request.args.get() -> Query()
- current_app.config -> request.app.state
- return jsonify({}) -> return {}
- def -> async def
"""

import os
import time
import json
import hashlib
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List


router = APIRouter(prefix="/api", tags=["knowledge"])

# Project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ============================================================
# PYDANTIC MODELS
# ============================================================

class KGBuildRequest(BaseModel):
    """Request to build knowledge graph."""
    file_ids: Optional[List[str]] = []
    collection: Optional[str] = "vetka_elisya"


class ARCSuggestRequest(BaseModel):
    """Request for ARC suggestions."""
    workflow_id: str
    graph_data: Optional[Dict[str, Any]] = None
    task_context: Optional[str] = ""
    num_candidates: Optional[int] = 10
    min_score: Optional[float] = 0.5


class BranchCreateRequest(BaseModel):
    """Request to create branch."""
    name: Optional[str] = "New Branch"
    files: List[Dict[str, Any]]
    source: Optional[str] = "manual"


class BranchContextRequest(BaseModel):
    """Request for branch context."""
    path: str
    depth: Optional[int] = 2
    include_content: Optional[bool] = False


class VetkaCreateRequest(BaseModel):
    """Request to create VETKA tree."""
    name: Optional[str] = "New VETKA"
    files: Optional[List[Dict[str, Any]]] = []
    tag: Optional[str] = ""
    parent_tree_id: Optional[str] = "root"
    x_offset: Optional[int] = 500
    source: Optional[str] = "manual"


class ClearHistoryRequest(BaseModel):
    """Request to clear history."""
    path: str


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _get_knowledge_components(request: Request) -> dict:
    """Get knowledge-related components from app state (DI pattern)."""
    flask_config = getattr(request.app.state, 'flask_config', {})
    return {
        'get_memory_manager': flask_config.get('get_memory_manager'),
        'get_orchestrator': flask_config.get('get_orchestrator'),
        'CHAT_HISTORY_DIR': flask_config.get('CHAT_HISTORY_DIR'),
    }


# ============================================================
# KNOWLEDGE GRAPH ENDPOINTS
# ============================================================

@router.post("/knowledge-graph/build")
async def build_knowledge_graph(req: KGBuildRequest, request: Request):
    """
    Build Knowledge Graph from Qdrant embeddings.

    Uses UMAP for positioning and HDBSCAN for clustering.
    """
    try:
        from src.knowledge_graph import VETKAKnowledgeGraphBuilder, VETKAPositionCalculator

        # Initialize builders
        builder = VETKAKnowledgeGraphBuilder(
            qdrant_host="localhost",
            qdrant_port=6333
        )
        calculator = VETKAPositionCalculator()

        # Build graph
        if req.file_ids:
            graph = builder.build_graph_for_files(req.file_ids, collection=req.collection)
        else:
            graph = builder.build_graph_for_files([], collection=req.collection)

        # Calculate positions and export
        result = calculator.export_with_positions(graph)

        return {
            'success': True,
            'graph': result
        }

    except ImportError as e:
        return {
            'error': f'Missing dependency: {e}. Install with: pip install umap-learn hdbscan networkx',
            'graph': {'nodes': [], 'edges': [], 'clusters': []}
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-graph/for-tag")
async def knowledge_graph_for_tag(
    tag: str = Query(..., description="Semantic tag"),
    collection: str = Query("vetka_elisya", description="Collection name"),
    request: Request = None
):
    """
    Build Knowledge Graph for files with a specific tag.
    """
    try:
        from src.knowledge_graph import VETKAKnowledgeGraphBuilder, VETKAPositionCalculator

        builder = VETKAKnowledgeGraphBuilder(
            qdrant_host="localhost",
            qdrant_port=6333
        )
        calculator = VETKAPositionCalculator()

        graph = builder.build_graph_for_tag(tag, collection=collection)
        result = calculator.export_with_positions(graph)

        return {
            'success': True,
            'tag': tag,
            'graph': result
        }

    except ImportError as e:
        return {
            'error': f'Missing dependency: {e}',
            'graph': {'nodes': [], 'edges': [], 'clusters': []}
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ARC SOLVER ENDPOINTS
# ============================================================

@router.post("/arc/suggest")
async def arc_suggest(req: ARCSuggestRequest, request: Request):
    """
    Generate ARC suggestions for a workflow graph.
    """
    try:
        components = _get_knowledge_components(request)
        get_orchestrator = components['get_orchestrator']

        if not get_orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not available")

        orchestrator = get_orchestrator()
        if not hasattr(orchestrator, 'arc_solver') or orchestrator.arc_solver is None:
            raise HTTPException(status_code=503, detail="ARC Solver not available")

        # Get graph_data
        graph_data = req.graph_data
        if not graph_data:
            # Try to build from workflow result
            history = orchestrator.get_workflow_history(100)
            workflow_result = None

            for item in history.get('local_history', []):
                if item.get('workflow_id') == req.workflow_id:
                    workflow_result = item
                    break

            if workflow_result:
                graph_data = orchestrator._build_graph_from_workflow(workflow_result)
            else:
                raise HTTPException(status_code=404, detail="Workflow not found and no graph_data provided")

        # Generate suggestions
        result = orchestrator.arc_solver.suggest_connections(
            workflow_id=req.workflow_id,
            graph_data=graph_data,
            task_context=req.task_context,
            num_candidates=req.num_candidates,
            min_score=req.min_score
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"  [ARC] Suggestion error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/arc/status")
async def arc_status(request: Request):
    """
    Get ARC Solver agent status and statistics.
    """
    try:
        components = _get_knowledge_components(request)
        get_orchestrator = components['get_orchestrator']

        if not get_orchestrator:
            return {
                'available': False,
                'error': 'Orchestrator not available'
            }

        orchestrator = get_orchestrator()

        if not hasattr(orchestrator, 'arc_solver') or orchestrator.arc_solver is None:
            return {
                'available': False,
                'error': 'ARC Solver not initialized'
            }

        stats = orchestrator.arc_solver.get_stats()

        return {
            'available': True,
            'stats': stats
        }

    except Exception as e:
        print(f"  [ARC] Status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# QDRANT DEDUPLICATION
# ============================================================

@router.post("/qdrant/deduplicate")
async def deduplicate_qdrant(request: Request):
    """
    Remove duplicate entries from Qdrant, keeping only the latest for each file path.
    """
    try:
        components = _get_knowledge_components(request)
        get_memory_manager = components['get_memory_manager']

        if not get_memory_manager:
            return {'error': 'Memory manager not available', 'deleted': 0}

        memory = get_memory_manager()
        qdrant = memory.qdrant if memory else None

        if not qdrant:
            return {'error': 'Qdrant not connected', 'deleted': 0}

        # Fetch all points
        result = qdrant.scroll(
            collection_name="vetka_elisya",
            limit=10000,
            with_payload=True,
            with_vectors=False
        )
        points = result[0] if result else []

        # Group by file path
        by_path = {}
        for point in points:
            path = point.payload.get('path', '')
            if path:
                if path not in by_path:
                    by_path[path] = []
                by_path[path].append(point)

        # Find duplicates (keep newest)
        to_delete = []
        for path, path_points in by_path.items():
            if len(path_points) > 1:
                sorted_points = sorted(
                    path_points,
                    key=lambda p: p.payload.get('modified_time', 0) or p.payload.get('timestamp', 0),
                    reverse=True
                )
                for point in sorted_points[1:]:
                    to_delete.append(point.id)

        if to_delete:
            from qdrant_client.models import PointIdsList
            qdrant.delete(
                collection_name="vetka_elisya",
                points_selector=PointIdsList(points=to_delete)
            )
            print(f"  [Dedupe] Deleted {len(to_delete)} duplicate entries")

        return {
            'success': True,
            'deleted': len(to_delete),
            'total_unique': len(by_path),
            'message': f'Removed {len(to_delete)} duplicates, {len(by_path)} unique files remain'
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# BRANCH CREATION
# ============================================================

@router.post("/branch/create")
async def create_branch_from_selection(req: BranchCreateRequest, request: Request):
    """
    Create a new branch from selected files (e.g., search results).
    """
    try:
        components = _get_knowledge_components(request)
        get_memory_manager = components['get_memory_manager']

        if not req.files:
            raise HTTPException(status_code=400, detail="No files provided")

        if not get_memory_manager:
            raise HTTPException(status_code=503, detail="Memory manager not available")

        memory = get_memory_manager()
        if not memory or not memory.qdrant:
            raise HTTPException(status_code=503, detail="Qdrant not available")

        from qdrant_client.models import PointStruct

        # Generate branch ID
        branch_id = f"branch_{hashlib.md5(req.name.encode()).hexdigest()[:8]}_{int(time.time())}"

        # Create branch metadata
        branch_metadata = {
            'type': 'user_branch',
            'source': req.source,
            'branch_name': req.name,
            'file_count': len(req.files),
            'file_paths': [f.get('path', '') for f in req.files[:20]],
            'timestamp': time.time(),
            'created_by': 'user'
        }

        # Generate embedding for branch
        try:
            import ollama
            branch_text = f"Branch: {req.name}\nFiles: {', '.join([f.get('name', '') for f in req.files[:10]])}"
            response = ollama.embeddings(model='embeddinggemma:300m', prompt=branch_text)
            branch_embedding = response.get('embedding', [])

            if branch_embedding:
                point_id = abs(hash(branch_id)) % (2**63)
                point = PointStruct(
                    id=point_id,
                    vector=branch_embedding,
                    payload=branch_metadata
                )

                memory.qdrant.upsert(
                    collection_name='vetka_elisya',
                    points=[point]
                )

                print(f"  [Branch] Created '{req.name}' with {len(req.files)} files (ID: {branch_id})")
        except Exception as e:
            print(f"  [Branch] Warning: Could not create embedding: {e}")

        return {
            'success': True,
            'branch_id': branch_id,
            'name': req.name,
            'file_count': len(req.files)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"  [Branch] Error creating branch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# BRANCH CONTEXT
# ============================================================

@router.post("/branch/context")
async def get_branch_context(req: BranchContextRequest, request: Request):
    """
    Get context for entire branch (folder).
    """
    try:
        branch_path = req.path.strip()
        max_depth = min(req.depth, 5)
        include_content = req.include_content

        # Security: prevent directory traversal
        if '..' in branch_path:
            raise HTTPException(status_code=400, detail="Invalid path")

        # Build full path
        full_path = os.path.join(PROJECT_ROOT, branch_path) if branch_path else PROJECT_ROOT

        if not os.path.isdir(full_path):
            raise HTTPException(status_code=404, detail="Not a directory")

        # Collect files
        files = []
        total_lines = 0
        total_size = 0
        file_types = {}

        # Patterns to skip
        skip_dirs = {'.git', 'node_modules', '__pycache__', 'venv', '.venv',
                     '.idea', '.vscode', 'dist', 'build', '.mypy_cache', '.pytest_cache'}
        skip_exts = {'.pyc', '.pyo', '.so', '.dylib', '.dll', '.exe', '.bin'}

        for root, dirs, filenames in os.walk(full_path):
            rel_root = os.path.relpath(root, full_path)
            current_depth = 0 if rel_root == '.' else rel_root.count(os.sep) + 1

            if current_depth > max_depth:
                dirs.clear()
                continue

            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in skip_dirs]

            for fname in filenames:
                if fname.startswith('.'):
                    continue

                ext = os.path.splitext(fname)[1].lower()
                if ext in skip_exts:
                    continue

                fpath = os.path.join(root, fname)
                rel_path = os.path.relpath(fpath, PROJECT_ROOT)

                try:
                    stat = os.stat(fpath)
                    file_info = {
                        'path': rel_path,
                        'name': fname,
                        'size': stat.st_size,
                        'ext': ext.lstrip('.').lower() if ext else 'unknown',
                        'mtime': stat.st_mtime
                    }

                    file_types[file_info['ext']] = file_types.get(file_info['ext'], 0) + 1

                    if include_content and stat.st_size < 30000 and ext in {'.py', '.js', '.ts', '.md', '.txt', '.json', '.yaml', '.yml', '.css', '.html'}:
                        try:
                            with open(fpath, 'r', encoding='utf-8') as f:
                                content = f.read()
                                file_info['content'] = content[:5000]
                                file_info['lines'] = content.count('\n') + 1
                                total_lines += file_info['lines']
                        except:
                            pass

                    total_size += stat.st_size
                    files.append(file_info)

                except Exception:
                    continue

        # Sort by modification time (newest first)
        files.sort(key=lambda x: x.get('mtime', 0), reverse=True)

        # Build context summary
        context = {
            'branch_path': branch_path or '.',
            'branch_name': os.path.basename(branch_path) if branch_path else 'root',
            'full_path': full_path,
            'total_files': len(files),
            'total_size': total_size,
            'total_size_human': f'{total_size / 1024:.1f} KB' if total_size < 1024*1024 else f'{total_size / (1024*1024):.1f} MB',
            'total_lines': total_lines,
            'file_types': file_types,
            'max_depth_scanned': max_depth,
            'structure_preview': [f['path'] for f in files[:30]]
        }

        return {
            'success': True,
            'context': context,
            'files': files[:100]
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# VETKA CREATE
# ============================================================

@router.post("/vetka/create")
async def create_vetka_tree(req: VetkaCreateRequest, request: Request):
    """
    Create a new VETKA tree using Knowledge Graph positioning.

    Phase 16: Full integration with SemanticTagger and PositionCalculator.
    """
    try:
        from src.knowledge_graph import VETKAKnowledgeGraphBuilder, VETKAPositionCalculator
        from src.knowledge_graph.semantic_tagger import SemanticTagger

        components = _get_knowledge_components(request)
        get_memory_manager = components['get_memory_manager']

        print(f"  [VETKA] Creating Knowledge Graph tree: {req.name}")
        print(f"  [VETKA] Input files: {len(req.files)}, tag: '{req.tag}'")

        files = list(req.files) if req.files else []

        if not files and not req.tag:
            raise HTTPException(status_code=400, detail="Provide files or semantic tag")

        if not get_memory_manager:
            raise HTTPException(status_code=503, detail="Memory manager not available")

        memory = get_memory_manager()
        if not memory or not memory.qdrant:
            raise HTTPException(status_code=503, detail="Qdrant not available")

        # 1. If tag provided, expand selection with semantic search
        if req.tag:
            tagger = SemanticTagger(
                qdrant_client=memory.qdrant,
                collection='vetka_elisya'
            )
            semantic_files = tagger.find_files_by_semantic_tag(req.tag, limit=50)

            existing_paths = {f.get('path', '') for f in files}
            for sf in semantic_files:
                if sf['path'] not in existing_paths:
                    files.append({
                        'qdrant_id': sf['id'],
                        'name': sf['name'],
                        'path': sf['path'],
                        'extension': sf['extension'],
                        'content': sf['content'],
                        'embedding': sf['embedding'],
                        'created_time': sf.get('created_time', 0),
                        'modified_time': sf.get('modified_time', 0)
                    })

            print(f"  [VETKA] After semantic expansion: {len(files)} files")

        if not files:
            raise HTTPException(status_code=400, detail="No files found")

        # 2. Fetch embeddings for files that don't have them
        files_with_embeddings = []
        for f in files:
            file_data = dict(f)

            if not file_data.get('embedding'):
                fid = file_data.get('qdrant_id') or file_data.get('id')
                if fid:
                    try:
                        point_id = int(fid)
                        points = memory.qdrant.retrieve(
                            collection_name='vetka_elisya',
                            ids=[point_id],
                            with_vectors=True,
                            with_payload=True
                        )
                        if points and points[0].vector:
                            file_data['embedding'] = points[0].vector
                            if not file_data.get('created_time') and points[0].payload:
                                file_data['created_time'] = points[0].payload.get('created_time', 0)
                                file_data['modified_time'] = points[0].payload.get('modified_time', 0)
                    except (ValueError, TypeError):
                        pass
                    except Exception as e:
                        print(f"  [VETKA] Warning: Could not fetch embedding for {fid}: {e}")

            files_with_embeddings.append(file_data)

        # 3. Build Knowledge Graph
        builder = VETKAKnowledgeGraphBuilder(
            qdrant_host="localhost",
            qdrant_port=6333
        )

        graph = builder._build_graph_from_file_data(files_with_embeddings)
        print(f"  [VETKA] Graph built: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")

        # 4. Calculate semantic positions
        calculator = VETKAPositionCalculator(
            n_neighbors=15,
            min_dist=0.1,
            min_cluster_size=3
        )

        kg_data = calculator.export_with_positions(graph)

        # 5. Generate tree structure
        tree_id = f"vetka_{hashlib.md5(req.name.encode()).hexdigest()[:8]}_{int(time.time())}"

        root_metadata = {
            'type': 'vetka_root',
            'source': req.source,
            'tree_id': tree_id,
            'tree_name': req.name,
            'parent_tree_id': req.parent_tree_id,
            'x_offset': req.x_offset,
            'file_count': len(kg_data['nodes']),
            'cluster_count': len(kg_data['clusters']),
            'tag': req.tag,
            'timestamp': time.time(),
            'created_by': 'user'
        }

        tree_nodes = [{
            'id': tree_id,
            'type': 'root',
            'name': req.name,
            'visual_hints': {
                'layout_hint': {'expected_x': 0, 'expected_y': 0, 'expected_z': 0}
            },
            'metadata': root_metadata
        }]

        tree_edges = []

        # 6. Add KG nodes with calculated positions
        for node in kg_data['nodes']:
            tree_nodes.append({
                'id': node['id'],
                'type': 'leaf',
                'name': node['name'],
                'parent_id': tree_id,
                'visual_hints': {
                    'layout_hint': {
                        'expected_x': node['x'],
                        'expected_y': node['y'],
                        'expected_z': node['z']
                    },
                    'color': node['color']
                },
                'metadata': {
                    'path': node['path'],
                    'name': node['name'],
                    'cluster': node['cluster'],
                    'created_time': node.get('created_time', 0),
                    'modified_time': node.get('modified_time', 0),
                    'y_time': node.get('y_time', node['y']),
                    'y_semantic': node.get('y_semantic', node['y']),
                    'preview': node.get('preview', ''),
                    'qdrant_id': node['id']
                }
            })

            tree_edges.append({
                'source': tree_id,
                'target': node['id'],
                'type': 'contains'
            })

        # 7. Add KG semantic edges
        for edge in kg_data['edges']:
            tree_edges.append({
                'source': edge['source'],
                'target': edge['target'],
                'type': edge['type'],
                'weight': edge['weight'],
                'color': edge['color']
            })

        print(f"  [VETKA] Tree created: {len(tree_nodes)} nodes, {len(tree_edges)} edges")
        print(f"  [VETKA] Clusters: {len(kg_data['clusters'])}")

        return {
            'success': True,
            'tree_id': tree_id,
            'name': req.name,
            'file_count': len(kg_data['nodes']),
            'cluster_count': len(kg_data['clusters']),
            'x_offset': req.x_offset,
            'tag': req.tag,
            'tree_data': {
                'id': tree_id,
                'name': req.name,
                'nodes': tree_nodes,
                'edges': tree_edges,
                'clusters': kg_data['clusters']
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"  [VETKA] Error creating KG tree: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# MESSAGE COUNTS
# ============================================================

@router.get("/messages/counts")
async def get_message_counts(request: Request):
    """
    Get message counts for all nodes (files/branches).

    Returns total and unread counts per node.
    """
    try:
        components = _get_knowledge_components(request)
        CHAT_HISTORY_DIR = components['CHAT_HISTORY_DIR']

        counts = {}

        if not CHAT_HISTORY_DIR or not CHAT_HISTORY_DIR.exists():
            return {'success': True, 'counts': {}}

        for chat_file in CHAT_HISTORY_DIR.glob('*.json'):
            try:
                with open(chat_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)

                if not history or not isinstance(history, list):
                    continue

                node_path = None
                for msg in history:
                    node_path = msg.get('node_path') or msg.get('path')
                    if node_path:
                        break

                if not node_path:
                    for msg in history:
                        if 'node_id' in msg:
                            node_path = f"node_{msg['node_id']}"
                            break

                if not node_path:
                    continue

                total = len(history)
                unread = sum(
                    1 for msg in history
                    if msg.get('agent') and msg.get('role') != 'user' and not msg.get('read', False)
                )

                counts[node_path] = {
                    'total': total,
                    'unread': unread
                }

                # Aggregate to parent branches
                parts = node_path.split('/')
                for i in range(1, len(parts)):
                    branch = '/'.join(parts[:i])
                    if branch not in counts:
                        counts[branch] = {'total': 0, 'unread': 0}
                    counts[branch]['total'] += total
                    counts[branch]['unread'] += unread

            except Exception:
                continue

        return {
            'success': True,
            'counts': counts
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
