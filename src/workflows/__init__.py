"""
VETKA Workflows Package.

Exports CommandRouter for command routing to agents.

@status: active
@phase: 96
@depends: router
@used_by: orchestration, main
"""

from .router import CommandRouter

__all__ = ["CommandRouter"]
