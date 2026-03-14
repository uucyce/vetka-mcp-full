from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_TOOL = ROOT / "src/mcp/tools/workflow_tools.py"
MYCELIUM_SERVER = ROOT / "src/mcp/mycelium_mcp_server.py"
PIPELINE = ROOT / "src/orchestration/agent_pipeline.py"
DIRECT_HELPER = ROOT / "src/mcp/tools/llm_call_reflex.py"


def test_mycelium_execute_workflow_delegates_into_workflow_tool() -> None:
    server = MYCELIUM_SERVER.read_text(encoding="utf-8")
    workflow_tool = WORKFLOW_TOOL.read_text(encoding="utf-8")

    assert 'from src.mcp.tools.workflow_tools import vetka_execute_workflow' in server
    assert 'result = await vetka_execute_workflow(' in server
    assert 'tool = ExecuteWorkflowTool()' in workflow_tool
    assert 'return tool.execute({' in workflow_tool


def test_workflow_path_uses_pipeline_reflex_hooks_inside_agent_pipeline() -> None:
    pipeline = PIPELINE.read_text(encoding="utf-8")

    assert 'from src.services.reflex_integration import reflex_pre_fc' in pipeline
    assert 'from src.services.reflex_integration import reflex_filter_schemas' in pipeline
    assert '[REFLEX Team Performance]' in pipeline
    assert '[REFLEX Recommendations]' in pipeline


def test_workflow_entry_does_not_apply_direct_reflex_contract_helper() -> None:
    workflow_tool = WORKFLOW_TOOL.read_text(encoding="utf-8")
    pipeline = PIPELINE.read_text(encoding="utf-8")
    helper = DIRECT_HELPER.read_text(encoding="utf-8")

    assert 'maybe_apply_reflex_to_direct_tools' in helper
    assert 'maybe_apply_reflex_to_direct_tools' not in workflow_tool
    assert 'maybe_apply_reflex_to_direct_tools' not in pipeline
    assert 'ownership_localguys' not in workflow_tool


def test_workflow_reflex_filtering_remains_flag_gated_not_universally_enforced() -> None:
    integration = (ROOT / 'src/reflex/integration.py').read_text(encoding='utf-8')

    assert 'Requires BOTH REFLEX_ENABLED and REFLEX_ACTIVE to be True.' in integration
    assert 'def reflex_filter_schemas(' in integration
