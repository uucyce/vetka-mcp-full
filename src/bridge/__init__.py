"""
VETKA Bridge - Shared tool implementations for MCP and OpenCode bridges.

This module provides a unified tool implementation layer that both
the MCP bridge (vetka_mcp_bridge.py) and OpenCode bridge (opencode/routes.py)
can use, ensuring consistent behavior and zero code duplication.

Architecture:
    src/bridge/
    ├── __init__.py          # This file - package exports
    ├── shared_tools.py      # Tool implementations (this phase)
    └── compatibility.py     # Response format adapters (future)

Phase 95.3 - Bridge Unification (Read Tools)
Phase 95.4 - Bridge Unification (Write/Execution Tools)
Phase 95.5 - Bridge Unification (Memory Tools)
Created: 2026-01-26

@status: active
@phase: 96
@depends: shared_tools
@used_by: vetka_mcp_bridge, opencode/routes
"""

from .shared_tools import (
    # Base classes
    VETKATool,
    ReadTool,
    WriteTool,
    ExecutionTool,

    # Read tools (UNIFY-002 through UNIFY-009)
    SemanticSearchTool,
    ReadFileTool,
    TreeStructureTool,
    HealthCheckTool,
    ListFilesTool,
    SearchFilesTool,
    MetricsTool,
    KnowledgeGraphTool,

    # Collaboration tools (UNIFY-010)
    GroupMessagesTool,

    # Write tools (UNIFY-011 through UNIFY-013)
    SharedEditFileTool,
    SharedGitCommitTool,
    SharedGitStatusTool,

    # Execution tools (UNIFY-014 through UNIFY-016)
    SharedRunTestsTool,
    SharedCameraFocusTool,
    SharedCallModelTool,

    # Memory tools (UNIFY-017 through UNIFY-019) - Phase 95.5
    MemoryTool,
    ConversationContextTool,
    UserPreferencesTool,
    MemorySummaryTool,

    # Result formatting helpers - Read
    format_semantic_results,
    format_tree_summary,
    format_health_status,
    format_file_list,
    format_metrics,
    format_knowledge_graph_summary,

    # Result formatting helpers - Write/Execution (Phase 95.4)
    format_group_messages,
    format_write_result,
    format_git_status,
    format_test_result,
    format_camera_result,
    format_llm_result,

    # Result formatting helpers - Memory (Phase 95.5)
    format_context_result,
    format_preferences_result,
    format_memory_summary,

    # Tool registry utilities
    TOOL_REGISTRY,
    get_tool,
    list_tools,
)

__all__ = [
    # Base classes
    "VETKATool",
    "ReadTool",
    "WriteTool",
    "ExecutionTool",

    # Read tools
    "SemanticSearchTool",
    "ReadFileTool",
    "TreeStructureTool",
    "HealthCheckTool",
    "ListFilesTool",
    "SearchFilesTool",
    "MetricsTool",
    "KnowledgeGraphTool",

    # Collaboration tools
    "GroupMessagesTool",

    # Write tools
    "SharedEditFileTool",
    "SharedGitCommitTool",
    "SharedGitStatusTool",

    # Execution tools
    "SharedRunTestsTool",
    "SharedCameraFocusTool",
    "SharedCallModelTool",

    # Memory tools (Phase 95.5)
    "MemoryTool",
    "ConversationContextTool",
    "UserPreferencesTool",
    "MemorySummaryTool",

    # Formatters - Read
    "format_semantic_results",
    "format_tree_summary",
    "format_health_status",
    "format_file_list",
    "format_metrics",
    "format_knowledge_graph_summary",

    # Formatters - Write/Execution
    "format_group_messages",
    "format_write_result",
    "format_git_status",
    "format_test_result",
    "format_camera_result",
    "format_llm_result",

    # Formatters - Memory (Phase 95.5)
    "format_context_result",
    "format_preferences_result",
    "format_memory_summary",

    # Registry utilities
    "TOOL_REGISTRY",
    "get_tool",
    "list_tools",
]
