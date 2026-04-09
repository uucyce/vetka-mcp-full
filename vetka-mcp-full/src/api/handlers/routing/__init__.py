"""
Routing Module - Extracted Routing Logic.

Contains extracted routing logic from user_message_handler.py:
- HostessRouter: Hostess agent decision processing and action execution

@status: active
@phase: 96
@depends: hostess_router
@used_by: di_container
"""

from .hostess_router import HostessRouter, create_hostess_router

__all__ = [
    'HostessRouter',
    'create_hostess_router'
]
