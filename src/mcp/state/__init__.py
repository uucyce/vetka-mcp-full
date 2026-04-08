"""MCP State Management Module.

Provides persistent state management for MCP sessions and agent workflows.
Uses Qdrant for persistence with an LRU cache for fast access.

Features:
- Agent state persistence with TTL expiration
- LRU cache (100 entries) for hot data
- Qdrant vector store for cold storage
- Workflow state tracking across multiple agents

@status: active
@phase: 96
@depends: mcp_state_manager
@used_by: src/mcp/tools/session_tools.py, src/mcp/tools/workflow_tools.py, src/orchestration/services/mcp_state_bridge.py
"""
from .mcp_state_manager import MCPStateManager, get_mcp_state_manager

__all__ = ["MCPStateManager", "get_mcp_state_manager"]
