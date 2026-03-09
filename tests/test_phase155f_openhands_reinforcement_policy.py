"""
Phase 155F tests: OpenHands reinforcement policy overlays existing family selection.
"""

from src.services.architect_prefetch import ArchitectPrefetch, WorkflowTemplateLibrary


def test_select_workflow_with_policy_keeps_base_family_and_adds_reinforcement_flags():
    WorkflowTemplateLibrary.load_all()

    selection = WorkflowTemplateLibrary.select_workflow_with_policy(
        task_type="g3",
        complexity=6,
        task_description="Need approval review loop and diff-based patch in sandbox",
    )

    assert selection["workflow_key"] == "g3_critic_coder"
    assert "reinforcement_policy" in selection
    assert selection["reinforcement_policy"]["mode"] == "reinforcement"
    assert selection["reinforcement_policy"]["enabled"] is True

    flags = selection["reinforcement"]
    assert "approval_loop" in flags
    assert "diff_first_handoff" in flags
    assert "sandbox_terminal_discipline" in flags


def test_select_workflow_with_policy_no_openhands_signal_keeps_overlay_off():
    WorkflowTemplateLibrary.load_all()

    selection = WorkflowTemplateLibrary.select_workflow_with_policy(
        task_type="docs",
        complexity=2,
        task_description="Update readme wording only",
    )

    assert selection["workflow_key"] == "docs_update"
    assert selection["reinforcement"] == []
    assert selection["reinforcement_policy"]["enabled"] is False


def test_prepare_exposes_reinforcement_metadata_in_context_summary():
    WorkflowTemplateLibrary.load_all()

    ctx = ArchitectPrefetch.prepare(
        task_description="Run approval review in sandbox and provide unified diff",
        task_type="build",
        complexity=7,
        config=None,
    )

    assert isinstance(ctx.workflow_reinforcement, list)
    assert isinstance(ctx.workflow_reinforcement_policy, dict)
    assert "OpenHands reinforcement:" in ctx.summary
    assert ctx.workflow_reinforcement_policy.get("mode") == "reinforcement"
