"""
VETKA Chat Handlers - FastAPI/ASGI Version

@file chat_handlers.py
@status ACTIVE
@phase Phase 39.7
@lastAudit 2026-01-05

Chat Socket.IO handlers for python-socketio AsyncServer.
Migrated from src/server/handlers/chat_handlers.py (Flask-SocketIO)

Changes from Flask version:
- @socketio.on('event') -> @sio.on('event') async def handler()
- emit() -> await sio.emit()
- request.sid -> sid parameter
- def -> async def
- broadcast=True -> omit 'to' parameter
"""

import json


def register_chat_handlers(sio, app=None):
    """Register chat-related Socket.IO handlers."""

    # Phase 53: Import ChatRegistry for per-session management
    from src.chat.chat_registry import ChatRegistry

    # Lazy imports for dependencies
    def get_chat_history_file(node_path):
        from main import get_chat_history_file as _get_chat_history_file
        return _get_chat_history_file(node_path)

    def get_chat_history_dir():
        from main import CHAT_HISTORY_DIR
        return CHAT_HISTORY_DIR

    @sio.on('chat_set_context')
    async def handle_set_context(sid, data):
        """
        Phase 53: Handle context switching to a different node.
        Returns message history for the new context.
        """
        node_path = data.get('node_path')
        if not node_path:
            return

        chat_manager = ChatRegistry.get_manager(sid)
        messages = chat_manager.set_context(node_path)

        # Convert messages to dict format for frontend
        messages_dict = [m.to_dict() for m in messages]

        # Send context sync response
        await sio.emit('chat_context_synced', {
            'node_path': node_path,
            'messages': messages_dict
        }, to=sid)

    @sio.on('clear_context')
    async def handle_clear_context(sid, data):
        """
        PHASE L: Handle context clear from frontend (click empty space)
        Clears any server-side state for this client
        """
        client_id = sid[:8]
        print(f"[CONTEXT] Cleared for client {client_id}")

        # Phase 53: Clear active context in chat manager
        chat_manager = ChatRegistry.get_manager(sid)
        chat_manager.active_node = None

        await sio.emit('context_cleared', {'status': 'ok', 'client_id': client_id}, to=sid)

    @sio.on('mark_messages_read')
    async def handle_mark_messages_read(sid, data):
        """
        Phase 17-Q: Mark messages as read for a node.
        Emits updated counts to all clients.
        """
        node_path = data.get('path', '')

        if not node_path:
            return

        chat_file = get_chat_history_file(node_path)

        if chat_file.exists():
            try:
                with open(chat_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)

                # Mark agent messages as read
                modified = False
                for msg in history:
                    if msg.get('agent') and msg.get('role') != 'user' and not msg.get('read', False):
                        msg['read'] = True
                        modified = True

                if modified:
                    with open(chat_file, 'w', encoding='utf-8') as f:
                        json.dump(history, f, indent=2, ensure_ascii=False)

                    print(f"[Chat] Marked messages as read for: {node_path}")

                    # Emit updated counts to all clients
                    # Get fresh counts
                    counts = {}
                    CHAT_HISTORY_DIR = get_chat_history_dir()
                    if CHAT_HISTORY_DIR.exists():
                        for cf in CHAT_HISTORY_DIR.glob('*.json'):
                            try:
                                with open(cf, 'r', encoding='utf-8') as f:
                                    hist = json.load(f)
                                if hist:
                                    np = None
                                    for m in hist:
                                        np = m.get('node_path') or m.get('path')
                                        if np:
                                            break
                                    if np:
                                        counts[np] = {
                                            'total': len(hist),
                                            'unread': sum(1 for m in hist if m.get('agent') and not m.get('read', False))
                                        }
                            except:
                                pass

                    # Broadcast to all clients (omit 'to' param)
                    await sio.emit('message_counts_updated', {'counts': counts})

            except Exception as e:
                print(f"[Chat] Error marking read: {e}")
