"""
VETKA workflow builders for LangGraph state graphs.

@status: active
@phase: 96
@depends: langgraph, src.orchestration.workflow_state
@used_by: src.orchestration.router
"""
from langgraph.graph import StateGraph, END
from src.orchestration.workflow_state import WorkflowState

def build_pm_plan_workflow():
    workflow = StateGraph(WorkflowState)
    workflow.add_node('placeholder', lambda x: x)
    workflow.add_edge('placeholder', END)
    workflow.set_entry_point('placeholder')
    return workflow.compile()

def build_dev_implement_workflow():
    return build_pm_plan_workflow()

def build_qa_test_workflow():
    return build_pm_plan_workflow()

def build_debug_workflow():
    return build_pm_plan_workflow()

def build_refactor_workflow():
    return build_pm_plan_workflow()

WORKFLOWS = {
    'pm_plan': build_pm_plan_workflow,
    'dev_implement': build_dev_implement_workflow,
    'qa_test': build_qa_test_workflow,
    'debug': build_debug_workflow,
    'refactor': build_refactor_workflow,
}

def get_workflow(workflow_type: str):
    builder = WORKFLOWS.get(workflow_type)
    if not builder:
        raise ValueError(f'Unknown workflow: {workflow_type}')
    return builder()

def list_workflows():
    return list(WORKFLOWS.keys())
