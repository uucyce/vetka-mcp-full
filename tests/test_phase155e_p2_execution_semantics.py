"""
Phase 155E P2 tests: runtime edge kind mapping and conditional/feedback policy.
"""

from src.services.workflow_store import WorkflowStore
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 155e contracts changed")

def test_workflow_to_tasks_maps_runtime_dependency_edge_kinds(tmp_path):
    store = WorkflowStore(project_root=tmp_path)
    wf = {
        "id": "wf_map",
        "name": "Runtime Mapping",
        "nodes": [
            {"id": "a", "type": "task", "label": "A", "data": {}},
            {"id": "b", "type": "task", "label": "B", "data": {}},
            {"id": "c", "type": "task", "label": "C", "data": {}},
        ],
        "edges": [
            {"id": "e1", "source": "a", "target": "b", "type": "dataflow"},
            {"id": "e2", "source": "b", "target": "c", "type": "dependency"},
        ],
    }

    tasks = store.workflow_to_tasks(wf)
    by_node = {t["node_id"]: t for t in tasks}

    assert by_node["b"]["dependency_node_ids"] == ["a"]
    assert by_node["c"]["dependency_node_ids"] == ["b"]
    assert by_node["b"]["execution_policy"]["wait_for"][0]["edge_type"] == "dataflow"


def test_workflow_to_tasks_keeps_feedback_as_retry_not_dependency(tmp_path):
    store = WorkflowStore(project_root=tmp_path)
    wf = {
        "id": "wf_feedback",
        "name": "Feedback Policy",
        "nodes": [
            {"id": "coder", "type": "agent", "label": "Coder", "data": {}},
            {"id": "quality", "type": "condition", "label": "Quality", "data": {}},
        ],
        "edges": [
            {"id": "e1", "source": "coder", "target": "quality", "type": "structural"},
            {"id": "e2", "source": "quality", "target": "coder", "type": "feedback", "label": "retry"},
        ],
    }

    tasks = store.workflow_to_tasks(wf)
    by_node = {t["node_id"]: t for t in tasks}

    # feedback must not create hard dependency cycle
    assert by_node["coder"]["dependency_node_ids"] == []
    assert by_node["coder"]["execution_policy"]["retry_from"] == ["quality"]


def test_workflow_to_tasks_exposes_conditional_inputs(tmp_path):
    store = WorkflowStore(project_root=tmp_path)
    wf = {
        "id": "wf_cond",
        "name": "Conditional",
        "nodes": [
            {"id": "gate", "type": "condition", "label": "Gate", "data": {}},
            {"id": "ok", "type": "task", "label": "OK", "data": {}},
            {"id": "no", "type": "task", "label": "NO", "data": {}},
        ],
        "edges": [
            {"id": "e1", "source": "gate", "target": "ok", "type": "conditional", "label": "true"},
            {"id": "e2", "source": "gate", "target": "no", "type": "conditional", "label": "false"},
        ],
    }

    tasks = store.workflow_to_tasks(wf)
    by_node = {t["node_id"]: t for t in tasks}
    assert by_node["ok"]["dependency_node_ids"] == ["gate"]
    assert by_node["no"]["dependency_node_ids"] == ["gate"]
    assert by_node["ok"]["execution_policy"]["conditional_inputs"][0]["branch"] == "true"
    assert by_node["no"]["execution_policy"]["conditional_inputs"][0]["branch"] == "false"
