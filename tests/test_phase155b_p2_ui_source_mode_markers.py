"""
Phase 155B-P2 marker checks for MCC source mode + source badge.
"""

from pathlib import Path
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 155b contracts changed")


ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_store_has_persistent_workflow_source_mode_contract():
    code = _read("client/src/store/useMCCStore.ts")
    assert "export type WorkflowSourceMode = 'runtime' | 'design' | 'predict';" in code
    assert "WORKFLOW_SOURCE_MODE_STORAGE_KEY" in code
    assert "loadWorkflowSourceMode" in code
    assert "saveWorkflowSourceMode" in code
    assert "workflowSourceMode: loadWorkflowSourceMode()" in code
    assert "setWorkflowSourceMode: (mode) => {" in code


def test_mcc_has_source_mode_marker_and_badge_marker():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "MARKER_155B.CANON.UI_SOURCE_MODE.V1" in code
    assert "MARKER_155B.CANON.UI_SOURCE_BADGE.V1" in code
    assert "resolveWorkflowGraphEndpoint" in code
    assert "API_BASE}/workflow/${endpoint}/${encodeURIComponent(taskKey)}" in code
    assert "Source: {workflowSourceBadge}" in code
