from __future__ import annotations

from src.services.architect_prefetch import WorkflowTemplateLibrary


def test_patchchain_localguys_template_is_registered_with_playbook_family() -> None:
    WorkflowTemplateLibrary._loaded = False
    templates = WorkflowTemplateLibrary.load_all()

    assert "patchchain_localguys" in templates
    template = templates["patchchain_localguys"]
    family = template.get("metadata", {}).get("workflow_family", {})

    assert family.get("family") == "patchchain_localguys"
    assert family.get("version") == "v1"
    assert family.get("roles") == ["coder"]
    assert family.get("policy", {}).get("stub") is False


def test_patchchain_localguys_is_selectable_by_local_patch_task_type() -> None:
    WorkflowTemplateLibrary._loaded = False
    WorkflowTemplateLibrary.load_all()

    result = WorkflowTemplateLibrary.select_workflow(
        task_type="local_patch_chain",
        complexity=2,
        task_description="Apply a tiny local model patch with targeted verification",
    )

    assert result == "patchchain_localguys"


def test_ownership_localguys_template_is_selectable_by_task_ownership_type() -> None:
    WorkflowTemplateLibrary._loaded = False
    WorkflowTemplateLibrary.load_all()

    result = WorkflowTemplateLibrary.select_workflow(
        task_type="local_task_ownership",
        complexity=1,
        task_description="Claim a local MYCELIUM task without widening tool scope",
    )

    assert result == "ownership_localguys"
