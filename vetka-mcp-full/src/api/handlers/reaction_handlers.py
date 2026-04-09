"""
VETKA Reaction Handlers - FastAPI/ASGI Version

@file reaction_handlers.py
@status ACTIVE
@phase Phase 39.7
@lastAudit 2026-01-05

Reaction/Quick Action Socket.IO handlers for python-socketio AsyncServer.
Migrated from src/server/handlers/reaction_handlers.py (Flask-SocketIO)

Changes from Flask version:
- @socketio.on('event') -> @sio.on('event') async def handler()
- emit() -> await sio.emit()
- broadcast=True -> omit 'to' parameter
- def -> async def
"""

import time
from datetime import datetime


def register_reaction_handlers(sio, app=None):
    """Register reaction-related Socket.IO handlers."""

    # Lazy imports to avoid circular dependencies
    def get_reactions_store():
        from main import REACTIONS_STORE
        return REACTIONS_STORE

    def get_save_reactions():
        from main import save_reactions
        return save_reactions

    def get_save_to_experience_library():
        from main import save_to_experience_library
        return save_to_experience_library

    @sio.on('quick_action')
    async def handle_quick_action(sid, data):
        """
        Handle quick action clicks from UI.

        Actions: detailed_analysis, improve, run_tests, full_chain, accept, reject, refine
        """
        action = data.get('action')
        node_path = data.get('node_path', '')
        original_message = data.get('original_message', '')

        print(f"[QUICK_ACTION] Action: {action}, node: {node_path}")

        # Map actions to new messages
        action_messages = {
            'detailed_analysis': f"Provide detailed analysis for: {original_message}",
            'improve': f"Improve the solution for: {original_message}",
            'run_tests': f"Write tests for the solution: {original_message}",
            'full_chain': f"Analyze in detail with full team (PM -> Dev -> QA): {original_message}",
            'accept': f"Accept the proposed solution",
            'reject': f"Reject the solution and suggest an alternative",
            'refine': f"Refine the current solution"
        }

        new_message = action_messages.get(action, original_message)

        if new_message:
            # Emit a new user message to trigger the workflow
            await sio.emit('user_message', {
                'text': new_message,
                'node_id': data.get('node_id', 'root'),
                'node_path': node_path
            }, to=sid)

    @sio.on('message_reaction')
    async def handle_reaction(sid, data):
        """
        Handle user reactions with PERSISTENT storage (Phase H)
        Reactions: like, dislike, star, retry, comment
        """
        REACTIONS_STORE = get_reactions_store()
        save_reactions = get_save_reactions()
        save_to_experience_library = get_save_to_experience_library()

        message_id = data.get('message_id')
        reaction = data.get('reaction')
        active = data.get('active', True)
        node_path = data.get('node_path', '')
        agent = data.get('agent', '')

        print(f"[REACTION] {reaction} on {message_id}, active={active}")

        key = f"{message_id}_{reaction}"

        # Handle special actions
        if reaction == 'retry':
            await sio.emit('reaction_received', {
                'message_id': message_id,
                'reaction': reaction,
                'status': 'retry_triggered',
                'timestamp': time.time()
            }, to=sid)
            return

        if reaction == 'comment':
            await sio.emit('reaction_received', {
                'message_id': message_id,
                'reaction': reaction,
                'status': 'comment_requested',
                'timestamp': time.time()
            }, to=sid)
            return

        # Save/remove reaction
        if active:
            REACTIONS_STORE[key] = {
                'message_id': message_id,
                'reaction': reaction,
                'timestamp': datetime.now().isoformat(),
                'node_path': node_path,
                'agent': agent,
                'user': 'default'
            }

            # Save to experience library if liked
            if reaction == 'like':
                save_to_experience_library(message_id)
        else:
            REACTIONS_STORE.pop(key, None)

        # Persist to disk
        save_reactions(REACTIONS_STORE)

        # Broadcast to all clients
        await sio.emit('reaction_saved', {
            'message_id': message_id,
            'reaction': reaction,
            'active': active,
            'persisted': True
        })

        print(f"[REACTION] Saved, total reactions: {len(REACTIONS_STORE)}")
