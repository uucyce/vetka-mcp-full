from __future__ import annotations

from pathlib import Path


def test_mini_stats_runtime_trigger_markers_are_present() -> None:
    code = Path("client/src/components/mcc/MiniStats.tsx").read_text(encoding="utf-8")
    assert "MARKER_168.MYCO.RUNTIME.MINI_STATS_WORKFLOW_SELECTED_TRANSITION.V1" in code
    assert "MARKER_168.MYCO.RUNTIME.MINI_STATS_TASK_BOARD_TRANSITION.V1" in code
    assert "mcc-workflow-selected" in code
    assert "task-board-updated" in code
    assert "triggerRoleAsset" in code
    assert "if (!context?.taskId)" in code


def test_mini_chat_runtime_trigger_reset_is_present() -> None:
    code = Path("client/src/components/mcc/MiniChat.tsx").read_text(encoding="utf-8")
    assert "MARKER_168.MYCO.RUNTIME.MINI_CHAT_MODEL_SELECTED_TRANSITION.V1" in code
    assert "MARKER_168.MYCO.RUNTIME.MINI_CHAT_TRIGGER_RESET_ON_HELPER.V1" in code
    assert "mcc-model-updated" in code
    assert "compactTriggerRoleAvatar" in code
    assert "if (helperMode === 'off') return;" in code
