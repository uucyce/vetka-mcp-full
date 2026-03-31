"""
MARKER_196.GW2.2: SSE (Server-Sent Events) stream for Agent Gateway.

Broadcasts real-time task status changes to external agents.
Uses asyncio.Queue for event distribution.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger("VETKA_SSE")

# Global event bus — shared across all connections
_event_queues: list[asyncio.Queue] = []
_event_lock = asyncio.Lock()

router = APIRouter()


async def _broadcast(event: Dict[str, Any]):
    """Broadcast an event to all connected SSE clients."""
    async with _event_lock:
        dead_queues = []
        for q in _event_queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead_queues.append(q)
        for q in dead_queues:
            _event_queues.remove(q)


def emit_task_event(task_id: str, action: str, task_data: Optional[Dict] = None):
    """Emit a task-related event (call from TaskBoard hooks).

    This is synchronous — it schedules the async broadcast.
    """
    event = {
        "event": action,
        "task_id": task_id,
        "timestamp": time.time(),
        "data": task_data or {},
    }
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_broadcast(event))
        else:
            asyncio.run(_broadcast(event))
    except Exception as e:
        logger.warning(f"[SSE] Failed to broadcast event: {e}")


@router.get("/stream")
async def sse_stream(
    request: Request,
    agent_id: Optional[str] = Query(None),
    task_id: Optional[str] = Query(None),
):
    """SSE endpoint for real-time task updates.

    Query params:
        agent_id: Filter events for a specific agent
        task_id: Filter events for a specific task
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)

    async with _event_lock:
        _event_queues.append(queue)

    async def event_generator():
        try:
            # Send initial connection event
            yield f"event: connected\ndata: {json.dumps({'message': 'SSE connected'})}\n\n"

            while True:
                if await request.is_disconnected():
                    break

                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    # Heartbeat
                    yield ": heartbeat\n\n"
                    continue

                # Apply filters
                if task_id and event.get("task_id") != task_id:
                    continue
                if agent_id and event.get("data", {}).get("assigned_to") != agent_id:
                    if event.get("data", {}).get("agent_id") != agent_id:
                        continue

                event_type = event.get("event", "task_update")
                data_str = json.dumps(event)
                yield f"event: {event_type}\ndata: {data_str}\n\n"

        except Exception as e:
            logger.warning(f"[SSE] Stream error: {e}")
        finally:
            async with _event_lock:
                if queue in _event_queues:
                    _event_queues.remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
