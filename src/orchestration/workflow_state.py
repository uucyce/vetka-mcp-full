"""
Workflow state definitions and token budgets for VETKA orchestration.

@status: active
@phase: 96
@depends: typing
@used_by: src.orchestration.workflows, src.orchestration.router
"""
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime

class WorkflowState(TypedDict):
    task: str
    task_type: str
    workflow_id: str
    path: str
    context: Dict[str, Any]
    current_agent: Optional[str]
    agent_outputs: List[Dict]
    results: Dict[str, Any]
    memory_updates: List[Dict]
    step_number: int
    status: str
    error: Optional[str]
    messages: List[Dict]

class AgentOutput(TypedDict):
    agent: str
    action: str
    output: str
    reasoning: str
    timestamp: str
    metadata: Dict[str, Any]

TOKEN_BUDGETS = {
    'pm_plan': 2000,
    'dev_implement': 4000,
    'qa_test': 3000,
    'debug': 5000,
    'refactor': 3500,
}
