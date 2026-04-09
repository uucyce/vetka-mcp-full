"""
VETKA Tree Handlers - FastAPI/ASGI Version

@file tree_handlers.py
@status ACTIVE
@phase Phase 39.7
@lastAudit 2026-01-05

Tree/Branch Socket.IO handlers for python-socketio AsyncServer.
Migrated from src/server/handlers/tree_handlers.py (Flask-SocketIO)

Changes from Flask version:
- @socketio.on('event') -> @sio.on('event') async def handler()
- emit() -> await sio.emit()
- broadcast=True -> omit 'to' parameter
- def -> async def
"""

from datetime import datetime


def register_tree_handlers(sio, app=None):
    """Register tree/branch-related Socket.IO handlers."""

    # Lazy import for memory manager
    def get_memory_manager():
        from main import get_memory_manager as _get_memory_manager
        return _get_memory_manager()

    @sio.on('select_branch')
    async def handle_select_branch(sid, data):
        """
        Phase 17-P: Handle branch selection for agent context.
        """
        branch_path = data.get('path', '')
        branch_type = data.get('type', 'branch')

        print(f"[Branch] Selected: {branch_path} (type: {branch_type})")

        # Store in session/room context
        # This can be used by agents to get branch context
        await sio.emit('branch_selected', {
            'path': branch_path,
            'type': branch_type,
            'timestamp': datetime.now().isoformat()
        }, to=sid)

    @sio.on('fork_branch')
    async def handle_fork_branch(sid, data):
        """
        Phase 22: Handle node fork (detach from parent) in Knowledge Graph.

        When a user drags a node far enough from its parent, it "forks" and
        becomes an independent branch.

        Expected data:
        {
            'nodeId': 'file_id_or_tag_id',
            'oldParentId': 'parent_tag_id'
        }
        """
        node_id = data.get('nodeId')
        old_parent_id = data.get('oldParentId')

        print(f"[Fork] Node '{node_id}' detached from '{old_parent_id}'")

        # Broadcast to all clients
        await sio.emit('branch_forked', {
            'nodeId': node_id,
            'oldParentId': old_parent_id,
            'success': True,
            'timestamp': datetime.now().isoformat()
        })

        # Log for debugging
        print(f"[Fork] Fork event broadcast for node '{node_id}'")

    @sio.on('move_to_parent')
    async def handle_move_to_parent(sid, data):
        """
        Phase 22: Handle node move to new parent in Knowledge Graph.

        When a user drags a node close to another node, it "moves" and
        becomes a child of the new parent.

        Expected data:
        {
            'nodeId': 'file_id_or_tag_id',
            'oldParentId': 'old_parent_tag_id',
            'newParentId': 'new_parent_tag_id'
        }
        """
        node_id = data.get('nodeId')
        old_parent_id = data.get('oldParentId')
        new_parent_id = data.get('newParentId')

        print(f"[Move] Node '{node_id}': '{old_parent_id}' -> '{new_parent_id}'")

        # Broadcast to all clients
        await sio.emit('node_moved', {
            'nodeId': node_id,
            'oldParentId': old_parent_id,
            'newParentId': new_parent_id,
            'success': True,
            'timestamp': datetime.now().isoformat()
        })

        # Log for debugging
        print(f"[Move] Move event broadcast for node '{node_id}' to '{new_parent_id}'")

    @sio.on('refactor_knowledge')
    async def handle_refactor_knowledge(sid, data=None):
        """
        Phase 22: Force recalculate Knowledge Graph with fresh RRF scores.

        Clears cache and rebuilds the entire KG layout.
        Called when user clicks "Refactor Knowledge" button.
        """
        print("[Refactor] Recalculating Knowledge Graph...")

        try:
            # Import layout module
            from src.layout.knowledge_layout import build_knowledge_graph_from_qdrant

            # Get memory manager for Qdrant access
            memory = get_memory_manager()
            if not memory or not memory.qdrant:
                await sio.emit('knowledge_refactored', {
                    'success': False,
                    'error': 'Qdrant not connected'
                }, to=sid)
                return

            # Build fresh KG with auto-computed RRF
            kg_data = build_knowledge_graph_from_qdrant(
                qdrant_client=memory.qdrant,
                collection_name='vetka_elisya',
                min_cluster_size=2,
                similarity_threshold=0.7,
                rrf_scores=None  # Auto-compute fresh RRF
            )

            print(f"[Refactor] Knowledge Graph rebuilt: {len(kg_data.get('tags', {}))} tags, "
                  f"{len(kg_data.get('positions', {}))} positions")

            # Broadcast new layout to all clients
            await sio.emit('knowledge_refactored', {
                'success': True,
                'tags': len(kg_data.get('tags', {})),
                'positions': len(kg_data.get('positions', {})),
                'rrf_stats': kg_data.get('rrf_stats', {}),
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[Refactor] Error: {e}")
            await sio.emit('knowledge_refactored', {
                'success': False,
                'error': str(e)
            }, to=sid)
