"""
Safe Tool Executor with security checks.

Executes tools with permission checks, rate limiting, user approval flow,
audit logging, and error handling.

@status: active
@phase: 96
@depends: base_tool (registry, ToolCall, ToolResult, PermissionLevel, BaseTool)
@used_by: src/tools/__init__, src/agents/
"""
import asyncio
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

from .base_tool import (
    registry, ToolCall, ToolResult, PermissionLevel, BaseTool
)

logger = logging.getLogger(__name__)

@dataclass
class RateLimitConfig:
    calls_per_minute: int = 30
    calls_per_turn: int = 10

class SafeToolExecutor:
    """
    Executes tools with:
    - Permission checks
    - Rate limiting
    - User approval flow (if needed)
    - Audit logging
    - Error handling
    """
    
    def __init__(self, 
                 max_permission: PermissionLevel = PermissionLevel.WRITE,
                 rate_limit: RateLimitConfig = None,
                 approval_callback=None):
        self.max_permission = max_permission
        self.rate_limit = rate_limit or RateLimitConfig()
        self.approval_callback = approval_callback  # async def(tool_call) -> bool
        self._call_counts: Dict[str, List[float]] = {}
    
    def _check_rate_limit(self, tool_name: str) -> bool:
        """Check if tool call is within rate limits"""
        now = time.time()
        minute_ago = now - 60
        
        if tool_name not in self._call_counts:
            self._call_counts[tool_name] = []
        
        # Clean old entries
        self._call_counts[tool_name] = [
            t for t in self._call_counts[tool_name] if t > minute_ago
        ]
        
        # Check minute rate limit
        if len(self._call_counts[tool_name]) >= self.rate_limit.calls_per_minute:
            return False
        
        self._call_counts[tool_name].append(now)
        return True
    
    def _check_permission(self, tool: BaseTool) -> bool:
        """Check if tool permission is allowed"""
        levels = list(PermissionLevel)
        tool_idx = levels.index(tool.definition.permission_level)
        max_idx = levels.index(self.max_permission)
        return tool_idx <= max_idx
    
    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call with all safety checks"""
        start_time = time.time()
        
        # 1. Get tool
        tool = registry.get(tool_call.tool_name)
        if not tool:
            return ToolResult(
                success=False,
                result=None,
                error=f"Unknown tool: {tool_call.tool_name}"
            )
        
        # 2. Permission check
        if not self._check_permission(tool):
            return ToolResult(
                success=False,
                result=None,
                error=f"Permission denied: {tool.definition.permission_level.value} not allowed"
            )
        
        # 3. Rate limit check
        if not self._check_rate_limit(tool_call.tool_name):
            return ToolResult(
                success=False,
                result=None,
                error="Rate limit exceeded"
            )
        
        # 4. User approval (if needed)
        if tool.definition.needs_user_approval:
            if self.approval_callback:
                approved = await self.approval_callback(tool_call)
                if not approved:
                    return ToolResult(
                        success=False,
                        result=None,
                        error="User denied tool execution"
                    )
            else:
                logger.warning(f"Tool {tool_call.tool_name} needs approval but no callback set")
        
        # 5. Execute
        try:
            result = await tool.execute(**tool_call.arguments)
            result.execution_time_ms = (time.time() - start_time) * 1000
            return result
        except Exception as e:
            logger.exception(f"Tool execution failed: {tool_call.tool_name}")
            return ToolResult(
                success=False,
                result=None,
                error=f"Execution error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    async def execute_multiple(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """Execute multiple tool calls"""
        results = []
        # Check turn rate limit (RateLimitConfig.calls_per_turn)
        if len(tool_calls) > self.rate_limit.calls_per_turn:
            return [ToolResult(success=False, result=None, error=f"Too many tool calls in one turn. Max is {self.rate_limit.calls_per_turn}.")]

        for call in tool_calls:
            result = await self.execute(call)
            results.append(result)
            # The plan suggests stopping on the first error, but for *multiple* calls in a list, 
            # we should execute all if possible, or stop if the error is critical. 
            # Given the executor's logic is simpler here, I'll adhere to the plan's implicit 'stop on error' by breaking.
            if not result.success:
                logger.error(f"Execution stop due to error on tool call: {call.tool_name}")
                break
        return results

# Default executor
default_executor = SafeToolExecutor()
