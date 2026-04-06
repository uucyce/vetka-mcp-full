"""
SSE (Server-Sent Events) stream for real-time task updates.

@license MIT
"""

import asyncio
import json
from typing import AsyncGenerator, Optional

from fastapi import Request
from sse_starlette.sse import EventSourceResponse

from .taskboard import get_task_board


async def _event_generator(
    agent_id: Optional[str], task_id: Optional[str]
) -> AsyncGenerator:
    """Generate SSE events for task updates."""
    yield {
        "event": "connected",
        "data": json.dumps({"service": "taskboard-gateway", "version": "1.0.0"}),
    }

    board = get_task_board()
    last_count = -1

    while True:
        tasks = board.list_tasks()
        count = len(tasks)

        if count != last_count:
            yield {
                "event": "tasks_update",
                "data": json.dumps(
                    {
                        "count": count,
                        "tasks": [
                            {"id": t["id"], "title": t["title"], "status": t["status"]}
                            for t in tasks[:20]
                        ],
                    }
                ),
            }
            last_count = count

        await asyncio.sleep(5)


async def sse_stream(
    request: Request,
    agent_id: Optional[str] = None,
    task_id: Optional[str] = None,
):
    """SSE endpoint handler."""
    return EventSourceResponse(_event_generator(agent_id, task_id))
