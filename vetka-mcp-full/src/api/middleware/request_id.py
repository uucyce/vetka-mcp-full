"""
@file request_id.py
@status ACTIVE
@phase Phase 43

Request ID middleware for request tracing.
Adds unique X-Request-ID header to all requests/responses.
"""

import uuid
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request for tracing."""

    async def dispatch(self, request: Request, call_next):
        # Generate or use existing request ID (short 8-char UUID)
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        start_time = time.time()

        # Store in request state for access in routes
        request.state.request_id = request_id
        request.state.start_time = start_time

        # Set request ID in logger context (if available)
        try:
            from src.utils.structured_logger import set_request_id
            set_request_id(request_id)
        except ImportError:
            pass

        # Process request
        response = await call_next(request)

        # Calculate process time
        process_time = time.time() - start_time

        # Add headers to response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.3f}s"

        # Log request (if logger available)
        try:
            from src.utils.structured_logger import logger
            logger.request(
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration=process_time,
                request_id=request_id
            )
        except ImportError:
            pass

        # Record metrics (if available)
        try:
            from src.monitoring.simple_metrics import count_request, time_request
            endpoint = request.url.path.split("/")[-1] or "root"
            count_request(endpoint)
            time_request(endpoint, process_time)
        except ImportError:
            pass

        return response
