"""
Phase 155B-P3.5 tests: core workflow template library + template-first selection.
"""

import asyncio

from src.services.architect_prefetch import WorkflowTemplateLibrary
from src.services.workflow_architect import generate_workflow


def test_template_library_includes_new_core_templates():
    templates = WorkflowTemplateLibrary.load_all()
    assert "ralph_loop" in templates
    assert "g3_critic_coder" in templates


def test_select_workflow_supports_ralph_and_g3():
    WorkflowTemplateLibrary.load_all()
    assert WorkflowTemplateLibrary.select_workflow(task_type="ralph", complexity=2) == "ralph_loop"
    assert WorkflowTemplateLibrary.select_workflow(task_type="g3", complexity=4) == "g3_critic_coder"

    # Description-only routing should also work.
    assert (
        WorkflowTemplateLibrary.select_workflow(
            task_type="",
            complexity=3,
            task_description="Need a single agent ralph loop for quick patch",
        )
        == "ralph_loop"
    )
    assert (
        WorkflowTemplateLibrary.select_workflow(
            task_type="",
            complexity=5,
            task_description="Use critic + coder pair for G3 style implementation",
        )
        == "g3_critic_coder"
    )


def test_workflow_architect_uses_template_first_without_llm():
    result = asyncio.run(
        generate_workflow(
            description="G3 flow: critic and coder pair for refactor patch",
            preset="dragon_silver",
            complexity_hint="medium",
        )
    )
    assert result["success"] is True
    assert result["model_used"] == "template_library:g3_critic_coder"
    assert result["workflow"]["metadata"]["template_first"] is True
    assert len(result["workflow"]["nodes"]) >= 2
