"""
Audit logging middleware.

@license MIT
"""

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from .taskboard import get_task_board

logger = logging.getLogger("taskboard.audit")


class AuditMiddleware(BaseHTTPMiddleware):
    """Log all gateway API requests to the audit table."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if request.url.path.startswith("/api/gateway"):
            try:
                board = get_task_board()
                auth_header = request.headers.get("authorization", "")
                agent_id = ""
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:]
                    agent = board.get_agent_by_key(token)
                    if agent:
                        agent_id = agent.get("id", "")

                ip = request.headers.get("x-forwarded-for", "")
                if ip:
                    ip = ip.split(",")[0].strip()
                elif request.client:
                    ip = request.client.host

                board.log_audit(
                    action=f"{request.method} {request.url.path}",
                    agent_id=agent_id,
                    ip_address=ip,
                    response_status=response.status_code,
                )
            except Exception as e:
                logger.warning(f"Audit log failed: {e}")

        return response
