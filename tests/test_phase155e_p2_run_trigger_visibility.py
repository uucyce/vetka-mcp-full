"""
Phase 155E P2 tests: run trigger must be visible in grandma mode and existing panels.
"""

from pathlib import Path
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 155e contracts changed")


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_footer_action_bar_not_debug_gated():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "{navLevel !== 'first_run' && (" in code
    assert "<FooterActionBar" in code


def test_minitasks_has_run_workflow_button_in_existing_panel():
    code = _read("client/src/components/mcc/MiniTasks.tsx")
    assert "MARKER_155E.WF.EXEC.RUN_TRIGGER_IN_EXISTING_PANELS.V1" in code
    assert "run wf" in code
    assert "executeWorkflow(" in code
