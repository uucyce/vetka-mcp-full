"""
Rate limiting for MCP API calls.

@status: active
@phase: 96
@depends: time, collections
@used_by: mcp_server
"""
import time
from collections import defaultdict
from typing import Dict, Tuple


class RateLimiter:
    """Simple in-memory rate limiter per client"""

    def __init__(self, max_calls: int = 60, window_seconds: int = 60):
        self.max_calls = max_calls
        self.window = window_seconds
        self.calls: Dict[str, list] = defaultdict(list)

    def is_allowed(self, client_id: str) -> Tuple[bool, int]:
        """Check if client can make a call.

        Returns:
            (allowed, retry_after_seconds)
        """
        now = time.time()
        # Clean old entries
        self.calls[client_id] = [t for t in self.calls[client_id] if now - t < self.window]

        if len(self.calls[client_id]) >= self.max_calls:
            oldest = min(self.calls[client_id])
            retry_after = int(self.window - (now - oldest)) + 1
            return False, retry_after

        self.calls[client_id].append(now)
        return True, 0

    def get_usage(self, client_id: str) -> Dict:
        """Get current usage stats for client"""
        now = time.time()
        self.calls[client_id] = [t for t in self.calls[client_id] if now - t < self.window]
        return {
            "calls_made": len(self.calls[client_id]),
            "calls_remaining": max(0, self.max_calls - len(self.calls[client_id])),
            "window_seconds": self.window,
            "max_calls": self.max_calls
        }

    def reset(self, client_id: str):
        """Reset rate limit for a client (for testing)"""
        self.calls[client_id] = []


# Global rate limiters
api_limiter = RateLimiter(max_calls=60, window_seconds=60)  # 60/min for API
write_limiter = RateLimiter(max_calls=10, window_seconds=60)  # 10/min for writes
