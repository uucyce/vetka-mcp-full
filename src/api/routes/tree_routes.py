"""
VETKA Tree Routes - FastAPI Version

@file tree_routes.py
@status ACTIVE
@phase Phase 108.3
@lastAudit 2026-02-02

Tree/Knowledge Graph API routes.
Migrated from src/server/routes/tree_routes.py (Flask Blueprint)

Endpoints:
- GET /api/tree/data - Main tree data API with FAN layout + chat nodes + artifact nodes
- POST /api/tree/clear-semantic-cache - Clear semantic DAG cache
- GET /api/tree/export/blender - Export to Blender format
- GET,POST /api/tree/knowledge-graph - Get Knowledge Graph structure
- POST /api/tree/clear-knowledge-cache - Clear Knowledge Graph cache

Phase History:
- Phase 108.3: Added artifact scanning from data/artifacts/
- Phase 108.2: Added chat node visualization
- Phase 39.3: FastAPI migration
"""

import os
import json
import hashlib
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


router = APIRouter(prefix="/api/tree", tags=["tree"])
NODE_FAVORITES_FILE = Path("data/node_favorites.json")


def _load_node_favorites() -> Dict[str, Any]:
    if not NODE_FAVORITES_FILE.exists():
        return {"favorites": {}, "updated_at": ""}
    try:
        data = json.loads(NODE_FAVORITES_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"favorites": {}, "updated_at": ""}
        favorites = data.get("favorites", {})
        if not isinstance(favorites, dict):
            favorites = {}
        return {"favorites": favorites, "updated_at": data.get("updated_at", "")}
    except Exception:
        return {"favorites": {}, "updated_at": ""}


def _save_node_favorites(data: Dict[str, Any]) -> bool:
    try:
        NODE_FAVORITES_FILE.parent.mkdir(parents=True, exist_ok=True)
        NODE_FAVORITES_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    except Exception:
        return False


def _stable_folder_node_id(folder_path: str) -> str:
    digest = hashlib.md5((folder_path or "").encode("utf-8")).hexdigest()[:8]
    return f"folder_{digest}"


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


class NodeFavoriteRequest(BaseModel):
    path: str
    is_favorite: bool


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


# MARKER_108_CHAT_VIZ_API: Phase 108.2 - Chat nodes in tree API - Helper functions
def extract_participants(chat: Dict[str, Any]) -> List[str]:
    """
    Extract participant list from chat messages (@mentions).

    Args:
        chat: Chat object with messages

    Returns:
        List of unique participant identifiers
    """
    participants = set()
    messages = chat.get("messages", [])

    for msg in messages:
        # Extract from sender_id field
        sender = msg.get("sender_id")
        if sender:
            participants.add(sender)

        # Extract from role field as fallback
        role = msg.get("role")
        if role and role not in ["user", "assistant", "system"]:
            participants.add(role)

        # Extract @mentions from content
        content = msg.get("content", "")
        import re
        mentions = re.findall(r'@(\w+)', content)
        participants.update(mentions)

    return list(participants)


def calculate_decay(updated_at_str: Optional[str]) -> float:
    """
    Calculate decay factor based on time since last activity.

    Args:
        updated_at_str: ISO format timestamp string

    Returns:
        Float 0.0-1.0, where 1.0 = recent, 0.0 = old (1 week+)
    """
    if not updated_at_str:
        return 0.0

    try:
        updated_at = datetime.fromisoformat(updated_at_str.replace("Z", ""))
        now = datetime.now()
        hours_since = (now - updated_at).total_seconds() / 3600

        # Decay over 168 hours (1 week)
        decay = max(0.0, 1.0 - (hours_since / 168.0))
        return decay
    except Exception as e:
        print(f"[CHAT_VIZ] Error calculating decay: {e}")
        return 0.5  # Default to middle value


# ============================================================
# ROUTES
# ============================================================

@router.get("/data")
async def get_tree_data(
    mode: str = Query("directory", description="Layout mode: directory, semantic, or both"),
    source: str = Query("vetka_elisya", description="Qdrant collection: vetka_elisya or vetka_tree"),
    chat_filter: str = Query("active", description="Chat node filter: active, favorite, all"),
    request: Request = None
):
    """
    Phase 17.2: Multi-tree layout with directory/semantic blend.

    Query params:
    - mode: 'directory' (default), 'semantic', or 'both'
    - source: 'vetka_elisya' (default) or 'vetka_tree' (Phase 101 hierarchical)

    Returns:
    - tree: {nodes, edges}
    - layouts: {directory: {...}, semantic: {...}} (when mode='both')
    - semantic_data: {nodes, edges, stats} (when mode='semantic' or 'both')

    MARKER_CHAT_3D_INTEGRATION: Adding chat nodes to tree visualization

    FUTURE IMPLEMENTATION PLAN:
    1. Extend return format:
       {
         "tree": { "nodes": [...file nodes...], "edges": [...] },
         "chat_nodes": { "id": ChatNode, ... },  ← ADD THIS
         "chat_edges": [ { "source": "file_id", "target": "chat_id" }, ... ]  ← ADD THIS
       }

    2. Data sources for chat nodes:
       - Query ChatHistoryManager for recent chats by file_path
       - OR query Qdrant VetkaGroupChat collection filtered by file_path
       - Include: id, name, participants, lastActivity, messageCount, artifacts[]

    3. Position strategy:
       - File position: from existing layout calculation
       - Chat position: offset from file (e.g., position.x + 8, position.y - 5)
       - Use chat's lastActivity for temporal sorting

    4. Edge creation:
       - Type: 'chat' edge (distinct from 'contains' edges)
       - Color (frontend): '#4a9eff' (blue) instead of gray
       - Source: file node id
       - Target: chat node id

    5. Frontend integration (useTreeData.ts):
       - Convert chat_nodes to TreeNode[] with type='chat'
       - Convert chat_edges to TreeEdge[] with type='chat'
       - Merge into existing nodes/edges
       - FileCard already supports type='chat' (from treeNodes.ts)
       - TreeEdges already supports edge coloring for chat edges

    6. Node rendering (FileCard.tsx):
       - For type='chat': show participants list instead of file content
       - For type='artifact': show artifact type badge and status
       - Both use same LOD system as files

    7. Interaction:
       - Click chat node → opens ChatPanel with that chat
       - Shift+click → pins chat node (shows in context)
       - Can drag chat nodes to reorganize conversations
    """
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    from datetime import datetime
    import math

    # MARKER_101.8_START: Source collection selection
    collection_name = "VetkaTree" if source == "vetka_tree" else "vetka_elisya"
    # MARKER_101.8_END

    try:
        memory = _get_memory_manager(request)
        qdrant = memory.qdrant if memory else None

        if not qdrant:
            return {
                'error': 'Qdrant not connected',
                'tree': {'nodes': [], 'edges': []}
            }

        # Import layout functions
        # MARKER_111_TREE_LAYOUT: Use classic tree layout instead of fan layout
        from src.layout.fan_layout import calculate_tree_layout, calculate_directory_fan_layout
        from src.layout.incremental import (
            detect_new_branches,
            incremental_layout_update,
            get_last_branch_count,
            set_last_branch_count,
        )
        from src.orchestration.cam_engine import calculate_surprise_metrics_for_tree

        node_favorites = _load_node_favorites().get("favorites", {})

        # ═══════════════════════════════════════════════════════════════════
        # STEP 1: Get ALL scanned files from Qdrant
        # ═══════════════════════════════════════════════════════════════════
        all_files = []
        offset = None

        while True:
            results, offset = qdrant.scroll(
                collection_name=collection_name,  # MARKER_101.8: Use selected source
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

        print(f"[API] Found {len(all_files)} files in {collection_name}")

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

        def _to_epoch_seconds(value: Any) -> float:
            """Best-effort conversion for mixed timestamp payloads."""
            if value is None:
                return 0.0
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                raw = value.strip()
                if not raw:
                    return 0.0
                # Numeric string
                try:
                    return float(raw)
                except Exception:
                    pass
                # ISO datetime string
                try:
                    return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
                except Exception:
                    return 0.0
            return 0.0

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
            created_time_raw = (
                p.get('created_time')
                or p.get('modified_time')
                or p.get('updated_at')
            )
            modified_time_raw = p.get('modified_time') or p.get('updated_at') or created_time_raw
            created_time = _to_epoch_seconds(created_time_raw)
            modified_time = _to_epoch_seconds(modified_time_raw)
            files_by_folder[parent_folder].append({
                'id': str(point.id),
                'name': file_name,
                'path': file_path,
                'created_time': created_time,
                'modified_time': modified_time,
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
        # STEP 2.6: CALCULATE FOLDER CREATED_TIME (Phase 111)
        # Folder time = minimum created_time of all files inside
        # ═══════════════════════════════════════════════════════════════════
        for folder_path, folder_files in files_by_folder.items():
            if folder_path in folders and folder_files:
                min_time = min(f.get('created_time', 0) for f in folder_files)
                folders[folder_path]['created_time'] = min_time

        # Propagate created_time up the tree (parent = min of children times)
        def propagate_folder_times(folder_path):
            folder = folders.get(folder_path)
            if not folder:
                return float('inf')
            # Get min time from direct files
            min_time = folder.get('created_time', float('inf'))
            # Get min time from children
            for child_path in folder.get('children', []):
                child_time = propagate_folder_times(child_path)
                min_time = min(min_time, child_time)
            folder['created_time'] = min_time if min_time != float('inf') else 0
            return min_time

        # Find root folders and propagate
        root_folder_paths = [p for p, f in folders.items() if not f.get('parent_path')]
        for root_path in root_folder_paths:
            propagate_folder_times(root_path)

        print(f"[API] Calculated created_time for {len(folders)} folders")

        # ═══════════════════════════════════════════════════════════════════
        # STEP 2.7: RECALCULATE DEPTH RELATIVE TO ROOT (Phase 111 FIX)
        # The original depth was based on absolute path position, not tree depth
        # ═══════════════════════════════════════════════════════════════════
        def recalculate_depth(folder_path, current_depth):
            """Recursively set correct depth from root (root=0, children=1, etc.)"""
            if folder_path in folders:
                folders[folder_path]['depth'] = current_depth
                for child_path in folders[folder_path].get('children', []):
                    recalculate_depth(child_path, current_depth + 1)

        for root_path in root_folder_paths:
            recalculate_depth(root_path, 0)  # Root folders are depth 0

        print(f"[API] Recalculated depth for {len(folders)} folders (root=0)")

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
        # STEP 3: TREE LAYOUT (Phase 111 - Classic inverted DAG)
        # ═══════════════════════════════════════════════════════════════════
        # MARKER_111_TREE_LAYOUT: Use classic tree layout for proper hierarchy
        # Children are positioned ABOVE parents, centered horizontally
        positions, root_folders, BRANCH_LENGTH, FAN_ANGLE, Y_PER_DEPTH = calculate_tree_layout(
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
                'layout_hint': {'expected_x': 0, 'expected_y': -80, 'expected_z': 0},
                'color': '#8B4513'
            }
        })

        EXT_COLORS = {
            '.py': '#4A5A3A', '.js': '#5A5A3A', '.ts': '#3A4A6A',
            '.md': '#3A4A5A', '.json': '#5A4A3A', '.html': '#5A4A4A'
        }

        # Folder nodes
        for folder_path, folder in folders.items():
            folder_id = _stable_folder_node_id(folder_path)
            pos = positions.get(folder_path, {'x': 0, 'y': 0})

            if folder['parent_path']:
                parent_id = _stable_folder_node_id(folder['parent_path'])
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
                    'file_count': len(files_by_folder.get(folder_path, [])),
                    'is_favorite': bool(node_favorites.get(folder_path, False)),
                },
                'visual_hints': {
                    'layout_hint': {
                        'expected_x': pos.get('x', 0),
                        'expected_y': pos.get('y', 0),
                        'expected_z': pos.get('z', 0)
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
            folder_id = _stable_folder_node_id(folder_path)

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
                        'is_ghost': is_ghost,  # Phase 90.11: Deleted from disk
                        'is_favorite': bool(node_favorites.get(file_data['path'], False)),
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
        # STEP 4.5: Build chat nodes and edges
        # MARKER_108_CHAT_VIZ_API: Phase 108.2 - Chat nodes in tree API
        # MARKER_108_3_TIMELINE_Y: Phase 108.3 - Temporal Y-axis ordering
        # ═══════════════════════════════════════════════════════════════════
        chat_nodes = []
        chat_edges = []

        try:
            from src.chat.chat_history_manager import get_chat_history_manager
            from src.layout.knowledge_layout import calculate_chat_positions

            chat_manager = get_chat_history_manager()
            all_chats = chat_manager.get_all_chats(limit=300, load_from_end=True)

            filter_mode = (chat_filter or "active").strip().lower()
            now_dt = datetime.now()

            def _is_active_chat(chat: Dict[str, Any]) -> bool:
                if bool(chat.get("is_favorite", False)):
                    return True
                msg_count = len(chat.get("messages", []) or [])
                if msg_count >= 10:
                    return True
                updated_raw = str(chat.get("updated_at", "") or "")
                if not updated_raw:
                    return False
                try:
                    updated = datetime.fromisoformat(updated_raw.replace("Z", "+00:00"))
                except Exception:
                    return False
                age_sec = abs((now_dt - updated.replace(tzinfo=None)).total_seconds())
                return age_sec <= (7 * 24 * 3600)

            if filter_mode == "favorite":
                all_chats = [c for c in all_chats if bool(c.get("is_favorite", False))]
            elif filter_mode == "all":
                pass
            else:
                all_chats = [c for c in all_chats if _is_active_chat(c)]

            # Create a mapping from file_path to file node id
            file_path_to_node_id = {}
            for node in nodes:
                if node.get('type') in ['leaf', 'file']:
                    node_path = node.get('metadata', {}).get('path')
                    if node_path:
                        file_path_to_node_id[node_path] = node['id']

            # MARKER_108_3_TIMELINE_Y: Build file_positions dict from existing tree nodes
            file_positions = {}
            for node in nodes:
                if node.get('visual_hints', {}).get('layout_hint'):
                    pos = node['visual_hints']['layout_hint']
                    file_positions[node['id']] = {
                        'x': pos.get('expected_x', 0),
                        'y': pos.get('expected_y', 0),
                        'z': pos.get('expected_z', 0)
                    }

            # MARKER_108_3_TIMELINE_Y: Prepare chats for temporal positioning
            chats_to_position = []
            for chat in all_chats:
                # Skip chats with no messages
                message_count = len(chat.get("messages", []))
                if message_count == 0:
                    continue

                chat_id = chat.get("id")
                file_path = chat.get("file_path", "")
                updated_at = chat.get("updated_at")

                # Find associated file node id (if exists)
                associated_file_id = None
                if file_path and file_path not in ('unknown', 'root', ''):
                    associated_file_id = file_path_to_node_id.get(file_path)

                # Parse timestamp for temporal ordering
                last_activity = updated_at
                if isinstance(last_activity, str):
                    last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))

                chats_to_position.append({
                    'id': f"chat_{chat_id}",
                    'parentId': associated_file_id,
                    'lastActivity': last_activity,
                    'chat_data': chat  # Store original chat data
                })

            # MARKER_108_3_TIMELINE_Y: Calculate positions with temporal ordering
            # Y-axis range based on existing tree layout
            y_positions = [pos['y'] for pos in file_positions.values() if 'y' in pos]
            y_min = min(y_positions) if y_positions else 0
            y_max = max(y_positions) if y_positions else 500

            positioned_chats = calculate_chat_positions(
                chats=chats_to_position,
                file_positions=file_positions,
                y_min=y_min,
                y_max=y_max
            )

            # MARKER_108_3_TIMELINE_Y: Build chat nodes using calculated positions
            for positioned_chat in positioned_chats:
                chat = positioned_chat.get('chat_data', {})
                chat_id = chat.get("id")
                file_path = chat.get("file_path", "")
                updated_at = chat.get("updated_at")
                message_count = len(chat.get("messages", []))

                # Get calculated position
                pos = positioned_chat.get('position', {})
                chat_x = pos.get('x', 0)
                chat_y = pos.get('y', 0)
                chat_z = pos.get('z', 0)
                decay_factor = pos.get('decay_factor', 0.5)

                # Find associated file node id (if exists)
                associated_file_id = None
                if file_path and file_path not in ('unknown', 'root', ''):
                    associated_file_id = file_path_to_node_id.get(file_path)

                # Extract participants from messages
                participants = extract_participants(chat)

                # Determine chat name
                chat_name = chat.get("display_name") or chat.get("file_name") or f"Chat #{chat_id[:8]}"

                # Create chat node
                chat_node = {
                    "id": f"chat_{chat_id}",
                    "type": "chat",
                    "name": chat_name,
                    "parent_id": associated_file_id if associated_file_id else None,
                    "metadata": {
                        "chat_id": chat_id,
                        "file_path": file_path,
                        "last_activity": updated_at,
                        "message_count": message_count,
                        "participants": participants,
                        "decay_factor": decay_factor,
                        "context_type": chat.get("context_type", "file"),
                        "display_name": chat.get("display_name")
                    },
                    "visual_hints": {
                        "layout_hint": {
                            "expected_x": chat_x,
                            "expected_y": chat_y,
                            "expected_z": chat_z
                        },
                        "color": "#4a9eff",  # Blue for chat nodes
                        "opacity": 0.7 + (decay_factor * 0.3)  # More opaque for recent chats
                    }
                }

                chat_nodes.append(chat_node)

                # Create edge from file to chat (if file exists)
                if associated_file_id:
                    chat_edge = {
                        "from": associated_file_id,
                        "to": f"chat_{chat_id}",
                        "semantics": "chat",
                        "metadata": {
                            "type": "chat",
                            "color": "#4a9eff",
                            "opacity": 0.3
                        }
                    }
                    chat_edges.append(chat_edge)

            print(f"[CHAT_VIZ] Built {len(chat_nodes)} chat nodes, {len(chat_edges)} chat edges")
            print(f"[CHAT_VIZ] Temporal Y-axis ordering applied (y_min={y_min:.1f}, y_max={y_max:.1f})")

        except Exception as chat_err:
            print(f"[CHAT_VIZ] Warning: Could not build chat nodes: {chat_err}")
            import traceback
            traceback.print_exc()

        # ═══════════════════════════════════════════════════════════════════
        # STEP 4.7: Build artifact nodes and edges
        # MARKER_108_3_ARTIFACT_SCAN: Phase 108.3 - Artifact nodes in tree API
        # ═══════════════════════════════════════════════════════════════════
        artifact_nodes = []
        artifact_edges = []

        try:
            from src.services.artifact_scanner import (
                scan_artifacts,
                build_artifact_edges,
                update_artifact_positions,
                build_media_chunk_nodes_and_edges,
            )

            # Scan artifacts directory
            artifact_nodes = scan_artifacts()

            # Update artifact positions based on parent chat positions
            update_artifact_positions(artifact_nodes, chat_nodes)

            # Build edges from chats to artifacts
            artifact_edges = build_artifact_edges(artifact_nodes, chat_nodes)

            # MARKER_153.IMPL.G12_MEDIA_CHUNK_GRAPH:
            # Extend artifact graph with timestamped media chunk nodes/edges from Qdrant.
            chunk_nodes, chunk_edges = build_media_chunk_nodes_and_edges(artifact_nodes)
            if chunk_nodes:
                artifact_nodes.extend(chunk_nodes)
            if chunk_edges:
                artifact_edges.extend(chunk_edges)

            print(f"[ARTIFACT_SCAN] Built {len(artifact_nodes)} artifact nodes, {len(artifact_edges)} artifact edges")

        except Exception as artifact_err:
            print(f"[ARTIFACT_SCAN] Warning: Could not build artifact nodes: {artifact_err}")
            import traceback
            traceback.print_exc()

        # ═══════════════════════════════════════════════════════════════════
        # STEP 4.5: Inject Heat Scores for Label Visibility (Phase 119.2)
        # MARKER_119.2F — Heat injection into tree nodes
        # ═══════════════════════════════════════════════════════════════════
        try:
            from src.scanners.file_watcher import get_watcher
            watcher = get_watcher()
            heat_scores = watcher.adaptive_scanner.get_all_heat_scores()

            # Inject heatScore into each node based on its directory
            for node in nodes:
                node_path = node.get('metadata', {}).get('path', '')
                if node_path:
                    # For files: use parent directory heat
                    # For folders: use folder path heat
                    if node.get('type') in ['leaf', 'file']:
                        dir_path = os.path.dirname(node_path)
                    else:
                        dir_path = node_path

                    # Get heat score (0.0-1.0)
                    node['heatScore'] = heat_scores.get(dir_path, 0.0)

                    # MARKER_137.6C: Favorites keep persistent visual glow.
                    if bool(node.get('metadata', {}).get('is_favorite', False)):
                        node['heatScore'] = max(float(node.get('heatScore', 0.0)), 0.95)

            heat_count = sum(1 for n in nodes if n.get('heatScore', 0) > 0)
            if heat_count > 0:
                print(f"[HEAT] Phase 119.2: Injected heat scores into {heat_count} nodes")

        except Exception as heat_err:
            print(f"[HEAT] Warning: Could not inject heat scores: {heat_err}")

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
            },
            # MARKER_108_CHAT_VIZ_API: Add chat nodes and edges to response
            'chat_nodes': chat_nodes,
            'chat_edges': chat_edges,
            # MARKER_108_3_ARTIFACT_SCAN: Add artifact nodes and edges to response
            'artifact_nodes': artifact_nodes,
            'artifact_edges': artifact_edges
        }

        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'error': str(e), 'tree': {'nodes': [], 'edges': []}}


@router.get("/favorites")
async def get_node_favorites():
    data = _load_node_favorites()
    favorites = data.get("favorites", {})
    return {
        "success": True,
        "favorites": favorites,
        "count": len([v for v in favorites.values() if v]),
    }


@router.put("/favorite")
async def set_node_favorite(body: NodeFavoriteRequest, request: Request):
    path = (body.path or "").strip()
    if not path:
        raise HTTPException(status_code=400, detail="path is required")

    data = _load_node_favorites()
    favorites = data.setdefault("favorites", {})
    favorites[path] = bool(body.is_favorite)
    data["updated_at"] = datetime.now().isoformat()

    if not _save_node_favorites(data):
        raise HTTPException(status_code=500, detail="Failed to persist node favorites")

    # MARKER_137.6F: Optional CAM sync for favorited nodes.
    try:
        flask_config = getattr(request.app.state, "flask_config", {}) if request and request.app else {}
        if bool(flask_config.get("ELISYA_ENABLED", False)) and body.is_favorite:
            from src.orchestration.cam_event_handler import emit_cam_event
            await emit_cam_event(
                "file_uploaded",
                {
                    "path": path,
                    "content": f"Favorite node path: {path}",
                },
                source="tree_routes",
            )
    except Exception:
        pass

    # MARKER_137.6F: ENGRAM user preference sync (non-critical).
    try:
        from src.memory.engram_user_memory import get_engram_user_memory

        engram = get_engram_user_memory()
        user_id = (
            request.headers.get("x-user-id")
            or request.headers.get("x-session-user")
            or request.headers.get("x-session-id")
            or "danila"
        ).strip() or "danila"

        highlights = engram.get_preference(user_id, "project_highlights", "highlights")
        if not isinstance(highlights, dict):
            highlights = {}

        favorites = highlights.get("favorite_nodes", [])
        if not isinstance(favorites, list):
            favorites = []

        if body.is_favorite:
            if path not in favorites:
                favorites.append(path)
        else:
            favorites = [p for p in favorites if p != path]

        highlights["favorite_nodes"] = favorites[-2000:]
        engram.set_preference(
            user_id,
            "project_highlights",
            "highlights",
            highlights,
            confidence=0.82 if body.is_favorite else 0.7,
        )
    except Exception:
        pass

    return {"success": True, "path": path, "is_favorite": bool(body.is_favorite)}


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
