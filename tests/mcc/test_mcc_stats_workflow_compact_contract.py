from __future__ import annotations

import pytest
from pathlib import Path

pytestmark = pytest.mark.stale(reason="MCC stats workflow — compact view contract changed")


def test_compact_stats_exposes_workflow_action_and_team_stats_contract() -> None:
    code = Path("client/src/components/mcc/MiniStats.tsx").read_text(encoding="utf-8")
    assert "MARKER_167.STATS_WORKFLOW.UI_COMPACT_CONTEXT.V1" in code
    assert "MARKER_167.STATS_WORKFLOW.UI_COMPACT_TEAM_STATS.V1" in code
    assert "MARKER_167.STATS_WORKFLOW.BADGES.V1" in code
    assert "useTaskWorkflowBinding" in code
    assert "/mcc/tasks/${encodeURIComponent(taskId)}/workflow-binding" in code
    assert "WORKFLOW" in code
    assert "windowId: 'stats', expanded: true" in code
    assert "team:" in code
    assert "choose workflow for task" in code
    assert "bind:" in code
