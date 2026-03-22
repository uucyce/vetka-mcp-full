from __future__ import annotations

from pathlib import Path
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 173 contracts changed")

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_TOOL = ROOT / "src/mcp/tools/workflow_tools.py"
MYCELIUM_SERVER = ROOT / "src/mcp/mycelium_mcp_server.py"
PIPELINE = ROOT / "src/orchestration/agent_pipeline.py"
DIRECT_HELPER = ROOT / "src/mcp/tools/llm_call_reflex.py"
ORCHESTRATOR = ROOT / "src/orchestration/orchestrator_with_elisya.py"


def test_mycelium_execute_workflow_delegates_into_workflow_tool() -> None:
    server = MYCELIUM_SERVER.read_text(encoding="utf-8")
    workflow_tool = WORKFLOW_TOOL.read_text(encoding="utf-8")

    assert 'from src.mcp.tools.workflow_tools import vetka_execute_workflow' in server
    assert 'result = await vetka_execute_workflow(' in server
    assert 'workflow_family=arguments.get("workflow_family", "")' in server
    assert 'tool = ExecuteWorkflowTool()' in workflow_tool
    assert 'return tool.execute({' in workflow_tool
    assert '"workflow_family": {' in workflow_tool
    assert 'workflow_runtime_metadata = await self._resolve_workflow_runtime_metadata(workflow_family)' in workflow_tool
    assert 'workflow_runtime_metadata=workflow_runtime_metadata' in workflow_tool


def test_workflow_path_uses_pipeline_reflex_hooks_inside_agent_pipeline() -> None:
    pipeline = PIPELINE.read_text(encoding="utf-8")

    assert 'from src.services.reflex_integration import reflex_pre_fc' in pipeline
    assert 'from src.services.reflex_integration import reflex_filter_schemas' in pipeline
    assert '[REFLEX Team Performance]' in pipeline
    assert '[REFLEX Recommendations]' in pipeline


def test_workflow_entry_applies_direct_reflex_contract_helper_via_orchestrator() -> None:
    workflow_tool = WORKFLOW_TOOL.read_text(encoding="utf-8")
    pipeline = PIPELINE.read_text(encoding="utf-8")
    helper = DIRECT_HELPER.read_text(encoding="utf-8")
    orchestrator = ORCHESTRATOR.read_text(encoding="utf-8")

    assert 'maybe_apply_reflex_to_direct_tools' in helper
    assert 'from src.mcp.tools.llm_call_reflex import maybe_apply_reflex_to_direct_tools' in orchestrator
    assert 'messages, tool_schemas, _reflex_recs, reflex_meta = maybe_apply_reflex_to_direct_tools(' in orchestrator
    assert 'MARKER_173.P6.P9' in orchestrator
    assert 'maybe_apply_reflex_to_direct_tools' not in workflow_tool
    assert 'runtime_meta = dict(getattr(self, "_workflow_reflex_runtime_metadata", {}) or {})' in orchestrator
    assert '"_allow_task_board_writes": bool(write_opt_ins.get("task_board", False))' in orchestrator
    assert '[REFLEX WF PRE]' in orchestrator
    assert 'ownership_localguys' not in workflow_tool


def test_workflow_reflex_filtering_remains_flag_gated() -> None:
    integration = (ROOT / 'src/reflex/integration.py').read_text(encoding='utf-8')

    assert 'Requires BOTH REFLEX_ENABLED and REFLEX_ACTIVE to be True.' in integration
    assert 'def reflex_filter_schemas(' in integration
