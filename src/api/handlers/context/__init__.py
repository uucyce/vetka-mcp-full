"""
VETKA Context Building Module.

Exports context building utilities for LLM prompts.

@status: active
@phase: 96
@depends: context_builders
@used_by: di_container
"""

from .context_builders import ContextBuilder, get_context_builder

__all__ = ['ContextBuilder', 'get_context_builder']
