"""
@file qdrant_utils.py
@status ACTIVE
@phase Phase 38.1
@lastAudit 2026-01-05

Qdrant utility functions.
Extracted from main.py by marker HELPER_GET_QDRANT_HOST_PHASE38.1
"""

import os
import socket


def get_qdrant_host() -> str:
    """
    Auto-detect Qdrant host based on environment.

    Checks in order:
    1. QDRANT_HOST environment variable
    2. localhost (127.0.0.1)
    3. Docker host.docker.internal (for Mac Docker)

    Returns:
        Qdrant host string (IP or hostname)
    """
    # Try environment variable first
    env_host = os.getenv('QDRANT_HOST')
    if env_host:
        return env_host

    # Try localhost
    try:
        socket.gethostbyname('127.0.0.1')
        return '127.0.0.1'
    except socket.error:
        pass

    # Fallback for Mac Docker
    try:
        socket.gethostbyname('host.docker.internal')
        return 'host.docker.internal'
    except socket.error:
        return '127.0.0.1'


def get_qdrant_port() -> int:
    """
    Get Qdrant port from environment or use default.

    Returns:
        Qdrant port number
    """
    return int(os.getenv('QDRANT_PORT', '6333'))


def get_qdrant_url() -> str:
    """
    Get full Qdrant URL.

    Returns:
        Full URL string like 'http://127.0.0.1:6333'
    """
    host = get_qdrant_host()
    port = get_qdrant_port()
    return f"http://{host}:{port}"
