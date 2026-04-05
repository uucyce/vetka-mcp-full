from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_guide_contains_capability_and_state_matrix_markers():
    guide = _read("docs/161_ph_MCC_TRM/MYCO_AGENT_INSTRUCTIONS_GUIDE_V1_2026-03-06.md")
    assert "MARKER_162.P4.P3.MYCO.MYCELIUM_CAPABILITY_MATRIX.V1" in guide
    assert "MARKER_162.P4.P3.MYCO.PROACTIVE_MESSAGE_STATE_MATRIX.V1" in guide
    assert "MARKER_162.P4.P3.MYCO.RAG_STATE_KEY_ENRICHMENT.V1" in guide


def test_minichat_sends_drill_state_fields_to_quick_chat_context():
    code = _read("client/src/components/mcc/MiniChat.tsx")
    assert "active_task_id: context?.activeTaskId" in code
    assert "task_drill_state: context?.taskDrillState" in code
    assert "roadmap_node_drill_state: context?.roadmapNodeDrillState" in code
    assert "workflow_inline_expanded: context?.workflowInlineExpanded" in code
    assert "roadmap_node_inline_expanded: context?.roadmapNodeInlineExpanded" in code


def test_chat_route_has_state_key_retrieval_enrichment_and_action_pack_marker():
    code = _read("src/api/routes/chat_routes.py")
    assert "MARKER_162.P4.P3.MYCO.RAG_STATE_KEY_ENRICHMENT.V1" in code
    assert "MARKER_162.P4.P3.MYCO.PROACTIVE_NEXT_ACTION_PACK.V1" in code
    assert "task_drill_state" in code
    assert "roadmap_node_drill_state" in code
    assert "next_actions" in code
