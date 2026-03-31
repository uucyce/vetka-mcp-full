"""
MARKER_196.GW3.2: Rate limiting middleware for Agent Gateway.

Simple in-memory sliding window rate limiter.
Default: 100 requests per minute per API key.
Returns 429 Too Many Requests with Retry-After header.
"""

import time
import logging
from collections import defaultdict
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("VETKA_RATE_LIMIT")


class RateLimiter:
    """Sliding window rate limiter using in-memory dict."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> tuple[bool, int]:
        """Check if request is allowed. Returns (allowed, retry_after)."""
        now = time.time()
        cutoff = now - self.window_seconds

        # Clean old entries
        self._requests[key] = [ts for ts in self._requests[key] if ts > cutoff]

        if len(self._requests[key]) >= self.max_requests:
            oldest = min(self._requests[key])
            retry_after = int(oldest + self.window_seconds - now) + 1
            return False, max(1, retry_after)

        self._requests[key].append(now)
        return True, 0

    def cleanup(self):
        """Remove empty keys to prevent memory growth."""
        now = time.time()
        cutoff = now - self.window_seconds
        empty_keys = [
            k
            for k, v in self._requests.items()
            if not v or all(ts < cutoff for ts in v)
        ]
        for k in empty_keys:
            del self._requests[k]


# Global rate limiter instance
_rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces rate limits on /api/gateway/* endpoints."""

    def __init__(
        self,
        app,
        max_requests: int = 100,
        window_seconds: int = 60,
        skip_paths: list = None,
    ):
        super().__init__(app)
        self.limiter = RateLimiter(max_requests, window_seconds)
        self.skip_paths = skip_paths or ["/api/gateway/health", "/api/gateway/stream"]

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        if not path.startswith("/api/gateway"):
            return await call_next(request)

        if path in self.skip_paths:
            return await call_next(request)

        # Extract API key from Authorization header
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            key = auth_header[7:]  # Use full key as rate limit identifier
        else:
            # No auth — apply stricter limit or skip
            key = f"ip:{request.client.host}" if request.client else "unknown"

        allowed, retry_after = self.limiter.is_allowed(key)
        if not allowed:
            logger.warning(
                f"[RateLimit] Rate limit exceeded for {key[:20]}... on {path}"
            )
            return Response(
                status_code=429,
                content='{"error": "Too Many Requests", "retry_after": '
                + str(retry_after)
                + "}",
                media_type="application/json",
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.limiter.max_requests)
        response.headers["X-RateLimit-Window"] = str(self.limiter.window_seconds)
        return response
