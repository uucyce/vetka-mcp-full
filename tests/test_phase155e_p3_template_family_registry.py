"""
Phase 155E P3 tests: workflow template family registry governance.
"""

from src.services.architect_prefetch import WorkflowTemplateLibrary


def test_family_registry_has_required_families_and_contract_keys():
    WorkflowTemplateLibrary.load_all()
    families = WorkflowTemplateLibrary.list_families()
    by_name = {item["family"]: item for item in families}

    assert "core_library" in by_name
    assert "openhands_family" in by_name
    assert "pulse_family" in by_name

    for family_payload in by_name.values():
        assert "version" in family_payload
        assert isinstance(family_payload.get("roles", []), list)
        assert isinstance(family_payload.get("templates", []), list)
        policy = family_payload.get("policy", {})
        assert isinstance(policy, dict)
        assert "edge_semantics" in policy
        assert "role_contract" in policy


def test_core_templates_have_normalized_family_contract():
    templates = WorkflowTemplateLibrary.load_all()
    for key in ("bmad_default", "g3_critic_coder", "ralph_loop"):
        tpl = templates[key]
        family = tpl.get("metadata", {}).get("workflow_family", {})
        assert family.get("family") == "core_library"
        assert family.get("version") == "v1"
        assert isinstance(family.get("roles"), list) and family.get("roles")
        policy = family.get("policy", {})
        assert policy.get("edge_semantics") == "strict"
        assert policy.get("role_contract") == "strict"


def test_openhands_and_pulse_stubs_are_selectable_and_bound():
    templates = WorkflowTemplateLibrary.load_all()
    assert "openhands_collab_stub" in templates
    assert "pulse_scheduler_stub" in templates

    assert WorkflowTemplateLibrary.select_workflow(task_type="openhands", complexity=6) == "openhands_collab_stub"
    assert WorkflowTemplateLibrary.select_workflow(task_type="pulse", complexity=7) == "pulse_scheduler_stub"
