"""
Base classes for VETKA Agent Tools Framework.

Defines core abstractions: BaseTool, ToolDefinition, ToolCall, ToolResult,
PermissionLevel, and the global ToolRegistry.

@status: active
@phase: 96
@depends: abc, dataclasses, typing, enum
@used_by: src/tools/__init__, src/tools/code_tools, src/tools/executor
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import time

class PermissionLevel(Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    EXTERNAL = "external"
    ADMIN = "admin"

@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]
    permission_level: PermissionLevel
    needs_user_approval: bool = False
    rate_limit: str = "30/min"
    implementation: Optional[Callable] = None

@dataclass
class ToolCall:
    tool_name: str
    arguments: Dict[str, Any]
    agent_type: str
    timestamp: float = field(default_factory=time.time)
    call_id: str = ""

@dataclass
class ToolResult:
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time_ms: float = 0

class BaseTool(ABC):
    """Abstract base class for all tools"""
    
    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        pass
    
    def to_ollama_schema(self) -> Dict:
        """Convert to Ollama function calling format"""
        # Note: Ollama's format is similar to OpenAI's tool format (function + parameters)
        return {
            "type": "function",
            "function": {
                "name": self.definition.name,
                "description": self.definition.description,
                "parameters": self.definition.parameters
            }
        }

class ToolRegistry:
    """Registry of all available tools"""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool):
        self._tools[tool.definition.name] = tool
    
    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)
    
    def get_by_permission(self, max_level: PermissionLevel) -> List[BaseTool]:
        """Get tools up to permission level"""
        levels = list(PermissionLevel)
        max_idx = levels.index(max_level)
        return [t for t in self._tools.values() 
                if levels.index(t.definition.permission_level) <= max_idx]
    
    def all_schemas(self) -> List[Dict]:
        """Get all tool schemas for LLM"""
        return [t.to_ollama_schema() for t in self._tools.values()]

# Global registry
registry = ToolRegistry()
