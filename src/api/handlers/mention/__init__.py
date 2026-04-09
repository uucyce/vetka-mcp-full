"""
VETKA Mention Handler Module.

Public API for @mention parsing and handling.

@status: active
@phase: 96
@depends: mention_handler
@used_by: di_container
"""

from .mention_handler import MentionHandler, IMentionParser

__all__ = [
    'MentionHandler',
    'IMentionParser',
]
