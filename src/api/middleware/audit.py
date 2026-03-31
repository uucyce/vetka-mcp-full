"""
MARKER_196.GW2.3: Audit log middleware for Agent Gateway.

Logs all gateway API requests to the audit_log table for security
and compliance tracking.
"""

import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("VETKA_AUDIT")


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Middleware that logs all /api/gateway/* requests to audit_log table."""

    def __init__(self, app, skip_paths: list = None):
        super().__init__(app)
        self.skip_paths = skip_paths or ["/api/gateway/health"]
        self.max_body_length = 1024

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        if not path.startswith("/api/gateway"):
            return await call_next(request)

        if path in self.skip_paths:
            return await call_next(request)

        agent_id = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token_preview = auth_header[7:15] + "..."
            agent_id = f"key:{token_preview}"

        body_preview = ""
        if request.method in ("POST", "PATCH", "PUT"):
            body_bytes = await request.body()
            if body_bytes:
                try:
                    body_str = body_bytes.decode("utf-8", errors="replace")
                    body_preview = body_str[: self.max_body_length]
                except Exception:
                    body_preview = "<unreadable>"

        response = await call_next(request)

        try:
            from src.orchestration.task_board import get_task_board

            board = get_task_board()
            board.log_audit(
                agent_id=agent_id,
                action=f"{request.method.lower()}_{path.split('/')[-1] or 'root'}",
                task_id=self._extract_task_id(path),
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                request_body=body_preview if body_preview else None,
                response_status=response.status_code,
            )
        except Exception as e:
            logger.warning(f"[AuditLog] Failed to log request: {e}")

        return response

    def _extract_task_id(self, path: str):
        parts = path.split("/")
        if len(parts) >= 5 and parts[3] == "tasks":
            return parts[4]
        return None
