from __future__ import annotations

from pathlib import Path


def test_expanded_stats_has_workflow_selector_contract() -> None:
    code = Path("client/src/components/mcc/MiniStats.tsx").read_text(encoding="utf-8")
    assert "MARKER_167.STATS_WORKFLOW.UI_EXPANDED_SELECTOR.V1" in code
    assert "MARKER_167.STATS_WORKFLOW.UI_BANK_TABS.V1" in code
    assert "MARKER_167.STATS_WORKFLOW.UI_SELECT_ACTION.V1" in code
    assert "MARKER_167.STATS_WORKFLOW.MYCO_HINTS.V1" in code
    assert "MARKER_167.STATS_WORKFLOW.MYCO_TOOL_PRIORITY.V1" in code
    assert "useWorkflowCatalog" in code
    assert "useWorkflowMycoHint" in code
    assert "/mcc/workflow-catalog" in code
    assert "/mcc/workflow/myco-hint" in code
    assert "/mcc/tasks/${encodeURIComponent(context.taskId)}/workflow-binding" in code
    assert "Select for task" in code
    assert "Refresh workflow banks" in code
    assert "MYCO Workflow Guidance" in code
