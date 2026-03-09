from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_p4_p2_markers_present_in_mcc_and_chat():
    mcc = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    chat = _read("client/src/components/mcc/MiniChat.tsx")
    assert "MARKER_162.P4.P2.MYCO.TOP_HINT_POST_DRILL_PRIORITY.V1" in mcc
    assert "MARKER_162.P4.P2.MYCO.TOP_HINT_WORKFLOW_ACTIONS.V1" in mcc
    assert "MARKER_162.P4.P2.MYCO.TOP_HINT_NODE_UNFOLD_ACTIONS.V1" in mcc
    assert "MARKER_162.P4.P2.MYCO.CHAT_REPLY_STATE_MATRIX.V1" in chat


def test_top_hint_has_post_drill_branch_before_pre_drill_prompt():
    mcc = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    post_idx = mcc.find("MARKER_162.P4.P2.MYCO.TOP_HINT_POST_DRILL_PRIORITY.V1")
    pre_idx = mcc.find("Press Enter to drill into")
    assert post_idx != -1 and pre_idx != -1
    assert post_idx < pre_idx


def test_mini_context_payload_contains_drill_state_fields():
    ctx = _read("client/src/components/mcc/MiniContext.tsx")
    assert "taskDrillState?: 'collapsed' | 'expanded'" in ctx
    assert "roadmapNodeDrillState?: 'collapsed' | 'expanded'" in ctx
    assert "workflowInlineExpanded?: boolean" in ctx
    assert "roadmapNodeInlineExpanded?: boolean" in ctx


def test_mcc_maps_drill_state_into_mini_context_payload():
    mcc = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "taskDrillState," in mcc
    assert "roadmapNodeDrillState," in mcc
    assert "workflowInlineExpanded:" in mcc
    assert "roadmapNodeInlineExpanded:" in mcc


def test_chat_reply_matrix_has_post_drill_wording():
    chat = _read("client/src/components/mcc/MiniChat.tsx")
    assert "workflow is already open for the active task" in chat
    assert "module unfold is active" in chat
