from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_markers_present_for_workflow_priority_over_unfold() -> None:
    chat = _read("client/src/components/mcc/MiniChat.tsx")
    mcc = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "MARKER_164.P5.P3.MYCO.WORKFLOW_NODE_PRIORITY_OVER_UNFOLD.V1" in chat
    assert "MARKER_164.P5.P3.MYCO.TOP_HINT_WORKFLOW_NODE_PRIORITY_OVER_UNFOLD.V1" in mcc


def test_chat_treats_workflow_node_context_as_workflow_open() -> None:
    chat = _read("client/src/components/mcc/MiniChat.tsx")
    assert "const workflowNodeContext = graphKind.startsWith('workflow_')" in chat
    assert "if (taskDrillExpanded || workflowNodeContext)" in chat


def test_mcc_prioritizes_workflow_branch_before_module_unfold() -> None:
    mcc = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    workflow_idx = mcc.find("MARKER_164.P5.P3.MYCO.TOP_HINT_WORKFLOW_NODE_PRIORITY_OVER_UNFOLD.V1")
    unfold_idx = mcc.find("MARKER_162.P4.P2.MYCO.TOP_HINT_NODE_UNFOLD_ACTIONS.V1")
    assert workflow_idx != -1 and unfold_idx != -1
    assert workflow_idx < unfold_idx
