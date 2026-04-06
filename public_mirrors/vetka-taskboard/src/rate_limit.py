"""
Rate limiting middleware — per API key sliding window.

@license MIT
"""

import time
from collections import defaultdict
from typing import Dict, Optional

from fastapi import HTTPException, Request

# In-memory rate limit store: {api_key_prefix: [timestamps]}
_request_log: Dict[str, list] = defaultdict(list)

# Config
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 100  # requests per window


def check_rate_limit(request: Request, api_key: Optional[str] = None) -> None:
    """Check rate limit for the current request. Raises 429 if exceeded."""
    if not api_key:
        return

    key = api_key[:16]
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW

    _request_log[key] = [t for t in _request_log[key] if t > window_start]

    if len(_request_log[key]) >= RATE_LIMIT_MAX:
        retry_after = int(_request_log[key][0] + RATE_LIMIT_WINDOW - now) + 1
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {RATE_LIMIT_MAX} requests per {RATE_LIMIT_WINDOW}s.",
            headers={"Retry-After": str(retry_after)},
        )

    _request_log[key].append(now)
