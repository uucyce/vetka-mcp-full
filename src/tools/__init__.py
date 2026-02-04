"""
VETKA Agent Tools Framework.

Unified tools framework for agent operations including code manipulation,
git operations, sandboxed execution, and approval flows.

@status: active
@phase: 96
@depends: base_tool, executor, sandbox_executor, git_tool, approval_manager, code_tools, mcp_tools
@used_by: src/agents/, src/orchestration/, src/mcp/

Usage:
    from src.tools import registry, SafeToolExecutor, ToolCall

    # Get all tools for LLM
    tools = registry.all_schemas()

    # Phase 96: MCP Tools (for group chat)
    # vetka_search_semantic - Semantic search in knowledge base
    # vetka_camera_focus - Control 3D camera
    # get_tree_context - Get tree structure
"""

# ============================================================================
# BASE CLASSES AND REGISTRY
# ============================================================================

from .base_tool import (
    BaseTool,
    ToolDefinition,
    ToolCall,
    ToolResult,
    PermissionLevel,
    ToolRegistry,
)

# Import registry instance separately to avoid naming collision
from .base_tool import registry as _registry_instance

from .executor import SafeToolExecutor, default_executor

# ============================================================================
# PHASE 20: TOOL IMPLEMENTATIONS
# ============================================================================

from .sandbox_executor import (
    SandboxExecutor,
    SandboxLevel,
    ExecutionResult,
    default_sandbox_executor
)
from .git_tool import GitTool, GitResult, GitOperationType
from .approval_manager import (
    ApprovalManager,
    ApprovalRequest,
    ApprovalStatus,
    create_approval_callback
)

# ============================================================================
# TOOL REGISTRATION
# ============================================================================

# Import code_tools to register basic file operations
from . import code_tools

# Phase 96: Import MCP tools module to register group chat tools
# This executes registry.py which registers:
#   - vetka_search_semantic (SemanticSearchTool wrapper)
#   - vetka_camera_focus (SharedCameraFocusTool wrapper)
#   - get_tree_context (TreeStructureTool wrapper)
import importlib
_mcp_registry_module = importlib.import_module('src.tools.registry')

# Re-export the registry instance for public use
registry = _registry_instance

# Export MCP tool classes for direct access
from .registry import (
    VetkaSearchSemanticTool,
    VetkaCameraFocusTool,
    GetTreeContextTool,
)

__all__ = [
    # Base
    'BaseTool', 'ToolDefinition', 'ToolCall', 'ToolResult',
    'PermissionLevel', 'ToolRegistry', 'registry',
    'SafeToolExecutor', 'default_executor',

    # Phase 20: Sandbox
    'SandboxExecutor', 'SandboxLevel', 'ExecutionResult',
    'default_sandbox_executor',

    # Phase 20: Git
    'GitTool', 'GitResult', 'GitOperationType',

    # Phase 20: Approval
    'ApprovalManager', 'ApprovalRequest', 'ApprovalStatus',
    'create_approval_callback',

    # Phase 96: MCP Tools
    'VetkaSearchSemanticTool',
    'VetkaCameraFocusTool',
    'GetTreeContextTool',
]
