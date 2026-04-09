"""
Socket.IO handlers for LangGraph workflow streaming.

Phase 60.2: Real-time workflow events on the /workflow namespace.

@status: active
@phase: 96
@depends: socketio
@used_by: main.py socket registration
"""

from socketio import AsyncServer
import logging

logger = logging.getLogger(__name__)


def register_workflow_socket_handlers(sio: AsyncServer, app=None):
    """
    Register all workflow-related Socket.IO handlers.

    Args:
        sio: python-socketio AsyncServer instance
        app: FastAPI app for accessing app.state (optional)
    """
    namespace = '/workflow'

    @sio.on('connect', namespace=namespace)
    async def handle_connect(sid, environ):
        """Client connected to workflow namespace"""
        logger.info(f"[Workflow Socket] Client connected: {sid}")
        await sio.emit('connection_status', {'status': 'connected'}, to=sid, namespace=namespace)

    @sio.on('disconnect', namespace=namespace)
    async def handle_disconnect(sid):
        """Client disconnected"""
        logger.info(f"[Workflow Socket] Client disconnected: {sid}")

    @sio.on('join_workflow', namespace=namespace)
    async def handle_join_workflow(sid, data):
        """
        Client wants to receive events for specific workflow.
        Room = workflow_id for targeted event delivery.

        Args:
            sid: Socket ID
            data: Dict with 'workflow_id' key
        """
        workflow_id = data.get('workflow_id') if isinstance(data, dict) else None
        if workflow_id:
            await sio.enter_room(sid, workflow_id, namespace=namespace)
            await sio.emit('joined_workflow', {
                'workflow_id': workflow_id,
                'status': 'subscribed'
            }, to=sid, namespace=namespace)
            logger.info(f"[Workflow Socket] Client {sid} joined workflow: {workflow_id}")
        else:
            await sio.emit('error', {'message': 'workflow_id is required'}, to=sid, namespace=namespace)

    @sio.on('leave_workflow', namespace=namespace)
    async def handle_leave_workflow(sid, data):
        """
        Client wants to stop receiving events for workflow.

        Args:
            sid: Socket ID
            data: Dict with 'workflow_id' key
        """
        workflow_id = data.get('workflow_id') if isinstance(data, dict) else None
        if workflow_id:
            await sio.leave_room(sid, workflow_id, namespace=namespace)
            await sio.emit('left_workflow', {
                'workflow_id': workflow_id,
                'status': 'unsubscribed'
            }, to=sid, namespace=namespace)
            logger.info(f"[Workflow Socket] Client {sid} left workflow: {workflow_id}")

    @sio.on('get_workflow_status', namespace=namespace)
    async def handle_get_status(sid, data):
        """
        Client requests current workflow status.

        Args:
            sid: Socket ID
            data: Dict with 'workflow_id' key
        """
        workflow_id = data.get('workflow_id') if isinstance(data, dict) else None
        # TODO: Get from orchestrator or state store
        await sio.emit('workflow_status', {
            'workflow_id': workflow_id,
            'status': 'unknown',
            'message': 'Status check - workflow state not persisted yet'
        }, to=sid, namespace=namespace)

    @sio.on('ping_workflow', namespace=namespace)
    async def handle_ping(sid, data):
        """
        Simple ping/pong for connection testing.

        Args:
            sid: Socket ID
            data: Any data to echo back
        """
        await sio.emit('pong_workflow', {
            'received': data,
            'status': 'alive'
        }, to=sid, namespace=namespace)

    logger.info("[Workflow Socket] Handlers registered on /workflow namespace")
