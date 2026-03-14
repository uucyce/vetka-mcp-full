from src.api.routes.chat_routes import (
    _build_architect_quick_system_prompt,
    _build_role_aware_instruction_packet,
    _resolve_architect_guidance_scope,
)


def test_project_arch_scope_resolution():
    normalized = {
        "chat_scope": "project",
        "node_kind": "project",
        "graph_kind": "",
        "nav_level": "roadmap",
        "task_id": "",
        "task_drill_state": "collapsed",
        "workflow_inline": False,
    }
    assert _resolve_architect_guidance_scope(normalized) == "project_architect"


def test_task_arch_scope_resolution_from_task_context():
    normalized = {
        "chat_scope": "task",
        "node_kind": "task",
        "graph_kind": "project_task",
        "nav_level": "roadmap",
        "task_id": "tb_1",
        "task_drill_state": "expanded",
        "workflow_inline": True,
    }
    assert _resolve_architect_guidance_scope(normalized) == "task_architect"


def test_shared_instruction_core_packet_includes_next_actions_and_tools():
    packet = _build_role_aware_instruction_packet(
        "helper_myco",
        {
            "nav_level": "workflow",
            "node_kind": "agent",
            "role": "coder",
            "workflow_family": "dragons",
        },
    )
    assert packet["workflow_family_hint"] == "Dragons (faster/cheaper)"
    assert len(packet["next_actions"]) == 3
    assert "Context model/prompt" in packet["top_tools_hint"]


def test_architect_prompt_injects_scope_and_tools_hint():
    prompt = _build_architect_quick_system_prompt(
        {
            "chat_scope": "task",
            "nav_level": "workflow",
            "node_kind": "agent",
            "role": "architect",
            "task_id": "tb_777",
            "workflow_family": "g3",
        }
    )
    assert "task architect" in prompt
    assert "Current view: workflow" in prompt
    assert "tools: Context model/prompt | Tasks run/retry | Stats diagnostics | Balance key/model" in prompt


def test_window_focus_balance_has_priority_actions():
    packet = _build_role_aware_instruction_packet(
        "helper_myco",
        {
            "nav_level": "roadmap",
            "window_focus": "balance",
            "window_focus_state": "expanded",
            "node_kind": "task",
            "task_id": "tb_9",
        },
    )
    actions = packet["next_actions"]
    assert "balance window expanded" in actions[0]
    assert "active API key" in actions[1]
    assert "cost + in/out" in actions[2]
