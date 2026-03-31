"""
API key authentication middleware for Agent Gateway.

External agents authenticate via Bearer token in Authorization header.
The token is SHA256-hashed and looked up in the agents table.

@license MIT
"""

import hashlib
from typing import Optional

from fastapi import Header, HTTPException, Request

from .taskboard import get_task_board


async def verify_agent_authorization(
    authorization: Optional[str] = Header(None),
) -> dict:
    """FastAPI dependency: verify agent API key from Authorization header.

    Usage in routes:
        agent = await verify_agent_authorization(authorization)

    Raises:
        HTTPException(401) if no key or invalid key
        HTTPException(403) if agent is suspended/retired
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required. Use: Bearer <api_key>",
        )

    # Extract Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization format. Use: Bearer <api_key>",
        )

    api_key = parts[1]
    board = get_task_board()
    agent = board.get_agent_by_key(api_key)

    if not agent:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if agent.get("status") != "active":
        raise HTTPException(
            status_code=403,
            detail=f"Agent is {agent.get('status', 'unknown')}",
        )

    return agent


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
