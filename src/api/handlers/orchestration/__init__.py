"""
Orchestration Module for Agent Chain Execution.

Contains refactored orchestration components extracted from user_message_handler.py.
Components:
- AgentOrchestrator: Executes agent chains with context passing
- ResponseManager: Manages response emission and summaries

@status: active
@phase: 96
@depends: agent_orchestrator, response_manager
@used_by: di_container
"""

from .agent_orchestrator import AgentOrchestrator
from .response_manager import ResponseManager

__all__ = ['AgentOrchestrator', 'ResponseManager']
