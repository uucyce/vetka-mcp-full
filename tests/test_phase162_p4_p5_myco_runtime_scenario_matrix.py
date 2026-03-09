from src.api.routes.chat_routes import _build_myco_quick_reply


def _reply(context: dict, message: str = "help") -> str:
    payload = {
        "user_id": "danila",
        "user_name": "Danila",
        "active_project_id": "proj_1",
        "recent_tasks_by_project": {
            "proj_1": [{"title": "Write tests for task_tracker.py"}],
        },
        "fastpath": {"mode": "local"},
        "hidden_index": {"source_count": 3},
        "orchestration": {
            "multitask": {"active": 1, "queued": 2, "done": 5, "max_concurrent": 3, "auto_dispatch": True, "phase": "runtime"},
            "digest": {"phase": "runtime", "summary": "ok"},
        },
    }
    return _build_myco_quick_reply(message, payload, context, retrieval={"items": []})


def test_node_unfold_roadmap_prefers_unfold_actions_not_generic_roadmap_fallback():
    text = _reply(
        {
            "nav_level": "roadmap",
            "roadmap_node_drill_state": "expanded",
            "node_kind": "directory",
            "label": "pulse/src",
        }
    )
    assert "double-click deeper" in text
    assert "select task node in this module" in text
    assert "create task here from Tasks panel" in text
    assert "select node or task | drill into workflow | ask for dependency map" not in text


def test_workflow_expanded_architect_dragons_has_role_and_family_actions():
    text = _reply(
        {
            "nav_level": "roadmap",
            "task_drill_state": "expanded",
            "workflow_inline_expanded": True,
            "node_kind": "agent",
            "role": "architect",
            "team_profile": "dragon_silver",
            "workflow_id": "wf_task_123",
            "label": "Architect",
        }
    )
    assert "define/adjust subtasks" in text
    assert "Dragons (faster/cheaper)" in text
    assert "run/start from Tasks" in text


def test_workflow_expanded_coder_titans_has_coder_specific_actions():
    text = _reply(
        {
            "nav_level": "roadmap",
            "task_drill_state": "expanded",
            "workflow_inline_expanded": True,
            "node_kind": "agent",
            "role": "coder",
            "team_profile": "titan_core",
            "workflow_id": "wf_task_777",
            "label": "Coder",
        }
    )
    assert "open Context and verify coder model/prompt" in text
    assert "run/retry coder from Tasks" in text
    assert "Titans (smarter/costlier)" in text


def test_workflow_expanded_verifier_actions_present():
    text = _reply(
        {
            "nav_level": "roadmap",
            "task_drill_state": "expanded",
            "workflow_inline_expanded": True,
            "node_kind": "agent",
            "role": "verifier",
            "team_profile": "dragon_silver",
            "label": "Verifier",
        }
    )
    assert "check quality criteria" in text
    assert "run verify/eval stage" in text
    assert "send retry to coder" in text


def test_task_context_mentions_family_and_drill_next_step():
    text = _reply(
        {
            "nav_level": "roadmap",
            "node_kind": "task",
            "graph_kind": "project_task",
            "team_profile": "dragon_bronze",
            "label": "S1.6 Tests",
        }
    )
    assert "task scope detected (Dragons (faster/cheaper))" in text
    assert "press Enter to open workflow" in text
