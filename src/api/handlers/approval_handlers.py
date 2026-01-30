"""
VETKA Approval Handlers - FastAPI/ASGI Version

@file approval_handlers.py
@status ACTIVE
@phase Phase 39.7
@lastAudit 2026-01-05

Approval Socket.IO handlers for python-socketio AsyncServer.
Migrated from src/server/handlers/approval_handlers.py (Flask-SocketIO)

Changes from Flask version:
- @socketio.on('event') -> @sio.on('event') async def handler()
- emit() -> await sio.emit()
- def -> async def
"""

import asyncio
from datetime import datetime, timedelta

# Global approval manager instance (lazy initialized)
_APPROVAL_MANAGER = None
_SIO_INSTANCE = None


def get_approval_manager(sio):
    """Get or create global approval manager"""
    global _APPROVAL_MANAGER, _SIO_INSTANCE
    if _APPROVAL_MANAGER is None:
        from src.tools.approval_manager import ApprovalManager
        _APPROVAL_MANAGER = ApprovalManager(socketio=sio)
        _SIO_INSTANCE = sio
        print("[PHASE 20] ApprovalManager initialized (async handlers module)")
    return _APPROVAL_MANAGER


def register_approval_handlers(sio, app=None):
    """Register approval-related Socket.IO handlers."""

    @sio.on('get_pending_approvals')
    async def handle_get_pending_approvals(sid, data=None):
        """
        Phase 20: Get all pending approval requests.
        Returns acknowledgement for callback support.
        """
        print("[PHASE 20] Received get_pending_approvals request")

        manager = get_approval_manager(sio)
        pending = manager.get_pending_requests()

        result = {
            'status': 'ok',
            'requests': [r.to_dict() for r in pending],
            'count': len(pending)
        }

        await sio.emit('pending_approvals', result, to=sid)
        return result

    @sio.on('cancel_approval')
    async def handle_cancel_approval(sid, data):
        """
        Phase 20: Cancel a pending approval request.
        Returns acknowledgement for callback support.
        """
        print(f"[PHASE 20] Received cancel_approval: {data}")

        request_id = data.get('id') if data else None
        if not request_id:
            return {'status': 'error', 'error': 'Missing request ID'}

        manager = get_approval_manager(sio)
        success = manager.cancel_request(request_id)

        result = {
            'id': request_id,
            'status': 'cancelled' if success else 'error',
            'success': success
        }

        await sio.emit('approval_cancelled', result, to=sid)
        return result

    @sio.on('test_approval')
    async def handle_test_approval(sid, data=None):
        """
        Phase 20: Test approval flow by creating a dummy request.
        For debugging purposes only.
        """
        print("[PHASE 20] Creating test approval request")

        manager = get_approval_manager(sio)

        # Create test request
        request_id = f"test_approval_{datetime.now().strftime('%H%M%S')}"

        from src.tools.approval_manager import ApprovalRequest

        request = ApprovalRequest(
            id=request_id,
            operation_type='test_operation',
            agent_id='test-agent',
            description='This is a test approval request. Click Approve or Reject.',
            diff_preview='+ console.log("Hello World");\n- console.log("Goodbye");',
            expires_at=datetime.now() + timedelta(seconds=120)
        )

        # Add to manager
        with manager._lock:
            manager._requests[request_id] = request
            manager._events[request_id] = asyncio.Event()

        # Emit to frontend
        await sio.emit('approval_needed', request.to_dict())

        print(f"[PHASE 20] Test approval created: {request_id}")

        return {
            'status': 'ok',
            'request_id': request_id,
            'message': 'Test approval request created'
        }

    @sio.on('approval_response')
    async def handle_approval_response(sid, data):
        """
        Phase 20: Handle approval response from frontend.

        Expected data:
        {
            'id': 'approval_xxx',
            'approved': True/False,
            'reason': 'optional rejection reason'
        }

        Returns acknowledgement for callback support.
        """
        print(f"[PHASE 20] Received approval_response: {data}")

        request_id = data.get('id')
        approved = data.get('approved', False)
        reason = data.get('reason', '')
        user = data.get('user', 'anonymous')

        if not request_id:
            await sio.emit('approval_error', {'error': 'Missing request ID'}, to=sid)
            return {'status': 'error', 'error': 'Missing request ID'}

        manager = get_approval_manager(sio)

        if approved:
            success = manager.approve(request_id, approved_by=user)
            result = {
                'id': request_id,
                'status': 'approved' if success else 'error',
                'success': success,
                'message': 'Operation approved' if success else 'Failed to approve (expired or processed)'
            }
            await sio.emit('approval_confirmed', result, to=sid)
            return result
        else:
            success = manager.reject(request_id, reason=reason, rejected_by=user)
            result = {
                'id': request_id,
                'status': 'rejected' if success else 'error',
                'success': success,
                'message': 'Operation rejected' if success else 'Failed to reject'
            }
            await sio.emit('approval_confirmed', result, to=sid)
            return result
