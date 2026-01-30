"""
VETKA Integration Framework v5.4

Integration module providing action types, execution modes, and data structures
for workflow automation and external service integrations.

@status: active
@phase: 96
@depends: enum, typing, dataclasses
@used_by: src.integrations.action_registry, src.integrations.composio_provider
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

__version__ = "5.4"

class ActionCategory(str, Enum):
    DEVELOPMENT = "development"
    DEVOPS = "devops"
    COMMUNICATION = "communication"

class ComposioExecutionMode(str, Enum):
    MOCK = "mock"
    SYNC = "sync"
    ASYNC = "async"

@dataclass
class ActionResult:
    action_name: str
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    execution_time: float = 0.0

@dataclass
class Action:
    name: str
    tool: str
    description: str
    category: ActionCategory
    parameters: Dict[str, str]
    tags: List[str] = None

@dataclass
class ReasoningSession:
    task: str
    thoughts: List[Dict[str, Any]]
    confidence_score: float = 0.0

print("✅ Integration framework loaded")
