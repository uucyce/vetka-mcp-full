"""
VETKA Agent Tools Framework.

Unified tools framework for agent operations including code manipulation,
git operations, sandboxed execution, and approval flows.

@status: active
@phase: 96
@depends: base_tool, executor, sandbox_executor, git_tool, approval_manager, code_tools
@used_by: src/agents/, src/orchestration/, src/mcp/

Usage:
    from src.tools import registry, SafeToolExecutor, ToolCall

    # Get all tools for LLM
    tools = registry.all_schemas()

    # Execute a tool
    executor = SafeToolExecutor()
    result = await executor.execute(ToolCall(
        tool_name="read_code_file",
        arguments={"path": "src/main.py"},
        agent_type="Dev"
    ))

    # Phase 20: Sandbox execution
    from src.tools import SandboxExecutor, SandboxLevel
    sandbox = SandboxExecutor()
    result = sandbox.execute("print('Hello')", level=SandboxLevel.STANDARD)

    # Phase 20: Git with approval
    from src.tools import GitTool
    git = GitTool()
    status = await git.status()

    # Phase 20: Approval manager
    from src.tools import ApprovalManager
    manager = ApprovalManager(socketio=socketio)
"""

from .base_tool import (
    BaseTool,
    ToolDefinition,
    ToolCall,
    ToolResult,
    PermissionLevel,
    ToolRegistry,
    registry
)
from .executor import SafeToolExecutor, default_executor

# Phase 20: New tools
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

# Import tools to register them
from . import code_tools

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
    'create_approval_callback'
]
