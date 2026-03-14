from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_markers_present_for_workflow_guidance_depth_matrix() -> None:
    chat = _read("client/src/components/mcc/MiniChat.tsx")
    mcc = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")

    assert "MARKER_164.P5.P4.MYCO.WORKFLOW_ROLE_STATUS_DEPTH_MATRIX.V1" in chat
    assert "MARKER_164.P5.P4.MYCO.TOP_HINT_ROLE_STATUS_DEPTH_MATRIX.V1" in mcc
    assert "MARKER_164.P5.P4.MYCO.WORKFLOW_OPEN_NO_GENERIC_ROADMAP_FALLBACK.V1" in chat


def test_top_hint_has_role_specific_workflow_guidance() -> None:
    mcc = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")

    for token in (
        "architect: refine subtasks/team preset",
        "scout: inspect impacted files/deps",
        "researcher: inspect docs/constraints",
        "coder: open Context model/prompt",
        "verifier: inspect acceptance criteria",
        "eval: inspect score/quality signals",
        "quality gate: decide retry vs approval",
        "approval gate: approve deploy or send back",
        "deploy: verify approval/release target",
        "measure: inspect telemetry/test output",
    ):
        assert token in mcc


def test_top_hint_uses_role_guidance_in_both_workflow_paths() -> None:
    mcc = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert mcc.count("buildTopHintWorkflowRoleGuidance({") >= 2
    assert "const statusHintTail = buildTopHintWorkflowStatusAction(activeTaskStatus);" in mcc
