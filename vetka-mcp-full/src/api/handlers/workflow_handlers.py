"""
VETKA Workflow Handlers - FastAPI/ASGI Version

@file workflow_handlers.py
@status ACTIVE
@phase Phase 39.7
@lastAudit 2026-01-05

Workflow Socket.IO handlers for python-socketio AsyncServer.
Migrated from src/server/handlers/workflow_handlers.py (Flask-SocketIO)

Changes from Flask version:
- @socketio.on('event') -> @sio.on('event') async def handler()
- emit() -> await sio.emit()
- join_room() -> await sio.enter_room()
- request.sid -> sid parameter
- def -> async def
"""

import time
import uuid


def register_workflow_handlers(sio, app=None):
    """Register workflow-related Socket.IO handlers."""

    # Import dependencies from main module (lazy)
    def get_executor():
        from main import executor
        return executor

    def get_run_workflow_async():
        from main import run_workflow_async
        return run_workflow_async

    def get_memory_manager():
        from main import get_memory_manager as _get_memory_manager
        return _get_memory_manager()

    def get_orchestrator():
        from main import get_orchestrator as _get_orchestrator
        return _get_orchestrator()

    def get_metrics():
        from main import METRICS_AVAILABLE, metrics_engine
        return METRICS_AVAILABLE, metrics_engine

    @sio.on('cancel_workflow')
    async def handle_cancel(sid, data):
        """Cancel running workflow"""
        workflow_id = data.get('workflow_id', 'unknown')
        print(f"  Workflow cancelled: {workflow_id}")
        await sio.emit('workflow_cancelled', {
            'workflow_id': workflow_id,
            'timestamp': time.time()
        }, room=workflow_id)

    @sio.on('start_workflow')
    async def handle_workflow(sid, data):
        """
        Start agent workflow with real-time streaming.

        Phase 15-3: Extracts user_data (node_id, node_path) to enable rich context
        for agents analyzing specific files.
        """
        feature = data.get('feature', '')
        workflow_id = data.get('workflow_id', str(uuid.uuid4())[:8])

        # Phase 15-3: Extract user_data for rich context
        user_data = {
            'node_id': data.get('node_id'),
            'node_path': data.get('node_path'),
            'file_path': data.get('file_path'),
        }
        # Only include user_data if at least one field is present
        if not any(user_data.values()):
            user_data = None

        if not feature.strip():
            await sio.emit('workflow_error', {
                'workflow_id': workflow_id,
                'error': 'Feature description is empty',
                'timestamp': time.time()
            }, to=sid)
            return

        executor = get_executor()
        queue_size = executor._work_queue.qsize()
        if queue_size > 10:
            print(f"  Server busy: {queue_size} workflows in queue")
            await sio.emit('workflow_error', {
                'workflow_id': workflow_id,
                'error': f'Server busy: {queue_size} workflows queued',
                'timestamp': time.time()
            }, to=sid)
            return

        print(f"\n{'='*70}")
        print(f"  WORKFLOW QUEUED: {workflow_id}")
        print(f"  Feature: {feature[:100]}...")
        if user_data:
            print(f"  Node: {user_data.get('node_path', 'unknown')} (ID: {user_data.get('node_id', 'unknown')})")
        print(f"  Queue size: {queue_size + 1}/10")
        print(f"{'='*70}")

        # Join room for workflow updates
        await sio.enter_room(sid, workflow_id)

        await sio.emit('workflow_started', {
            'workflow_id': workflow_id,
            'feature': feature,
            'timestamp': time.time()
        }, room=workflow_id)

        # Phase 15-3: Pass user_data for rich context building
        run_workflow_async = get_run_workflow_async()
        executor.submit(run_workflow_async, feature, workflow_id, user_data)

        print(f"  Workflow submitted to executor: {workflow_id}")

    @sio.on('get_status')
    async def handle_status(sid, data=None):
        """Get current system status (ENHANCED)"""
        try:
            memory = get_memory_manager()
            orchestrator = get_orchestrator()
            stats = orchestrator.get_agent_statistics()

            # Get metrics from engine if available
            metrics_data = {}
            METRICS_AVAILABLE, metrics_engine = get_metrics()
            if METRICS_AVAILABLE and metrics_engine:
                try:
                    agent_stats = metrics_engine.get_agent_stats()
                    metrics_data = {
                        'avg_latency': agent_stats.get('avg_latency', 0),
                        'active_workflows': agent_stats.get('active_workflows', 0)
                    }
                except:
                    pass

            executor = get_executor()
            await sio.emit('status_update', {
                'weaviate_connected': memory.health_check().get('weaviate', False),
                'total_workflows': stats.get('total_workflows', 0),
                'successful_workflows': stats.get('successful', 0),
                'failed_workflows': stats.get('failed', 0),
                'executor_queue': executor._work_queue.qsize(),
                'metrics': metrics_data,
                'timestamp': time.time()
            }, to=sid)
        except Exception as e:
            print(f"  Status handler error: {e}")
            await sio.emit('status_update', {'error': str(e)}, to=sid)
