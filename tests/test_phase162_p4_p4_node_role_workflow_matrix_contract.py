from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_p4_p4_markers_present():
    mcc = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    chat = _read("client/src/components/mcc/MiniChat.tsx")
    routes = _read("src/api/routes/chat_routes.py")
    guide = _read("docs/161_ph_MCC_TRM/MYCO_AGENT_INSTRUCTIONS_GUIDE_V1_2026-03-06.md")

    assert "MARKER_162.P4.P4.MYCO.TOP_HINT_NODE_ROLE_WORKFLOW_MATRIX.V1" in mcc
    assert "MARKER_162.P4.P4.MYCO.CHAT_REPLY_NODE_ROLE_WORKFLOW_MATRIX.V1" in chat
    assert "MARKER_162.P4.P4.MYCO.NODE_ROLE_WORKFLOW_NEXT_ACTIONS.V1" in routes
    assert "MARKER_162.P4.P4.MYCO.NODE_ROLE_WORKFLOW_GUIDE_MATRIX.V1" in guide


def test_minichat_quick_context_has_workflow_family_fields():
    chat = _read("client/src/components/mcc/MiniChat.tsx")
    assert "graph_kind: context?.graphKind" in chat
    assert "workflow_id: context?.workflowId" in chat
    assert "team_profile: context?.teamProfile" in chat
    assert "workflow_family: context?.workflowFamily" in chat


def test_backend_myco_reply_has_role_and_workflow_family_branching():
    routes = _read("src/api/routes/chat_routes.py")
    assert "workflow_family_hint" in routes
    assert "role == \"architect\"" in routes
    assert "role == \"coder\"" in routes
    assert "role in {\"verifier\", \"eval\"}" in routes
