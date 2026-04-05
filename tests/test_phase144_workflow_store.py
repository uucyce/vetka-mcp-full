"""
MARKER_144.1_TESTS: Tests for Workflow Store + MARKER_144.10 Execution Bridge.

@phase 144
@status active
"""

import json
import pytest
import tempfile
from pathlib import Path

from src.services.workflow_store import (
    WorkflowStore,
    ValidationResult,
    ValidationError,
    VALID_NODE_TYPES,
    VALID_EDGE_TYPES,
)


@pytest.fixture
def store(tmp_path):
    """Create WorkflowStore with temp directory."""
    return WorkflowStore(project_root=tmp_path)


@pytest.fixture
def sample_workflow():
    """Create a valid sample workflow."""
    return {
        "name": "Test Workflow",
        "description": "A test workflow for unit tests",
        "nodes": [
            {"id": "n1", "type": "task", "label": "Root Task", "position": {"x": 0, "y": 0}, "data": {}},
            {"id": "n2", "type": "agent", "label": "@architect", "position": {"x": 100, "y": 100}, "data": {"role": "architect"}},
            {"id": "n3", "type": "subtask", "label": "Subtask 1", "position": {"x": 200, "y": 200}, "data": {}},
        ],
        "edges": [
            {"id": "e1", "source": "n1", "target": "n2", "type": "structural"},
            {"id": "e2", "source": "n2", "target": "n3", "type": "dataflow"},
        ],
    }


class TestWorkflowStoreSave:
    """Test save operations."""

    def test_save_creates_file(self, store, sample_workflow):
        wf_id = store.save(sample_workflow)
        assert wf_id is not None
        assert wf_id.startswith("wf_")
        path = store._workflow_path(wf_id)
        assert path.exists()

    def test_save_with_custom_id(self, store, sample_workflow):
        sample_workflow["id"] = "my_custom_id"
        wf_id = store.save(sample_workflow)
        assert wf_id == "my_custom_id"

    def test_save_generates_metadata(self, store, sample_workflow):
        wf_id = store.save(sample_workflow)
        loaded = store.load(wf_id)
        assert "metadata" in loaded
        assert "created_at" in loaded["metadata"]
        assert "updated_at" in loaded["metadata"]
        assert loaded["metadata"]["version"] == 1

    def test_save_increments_version(self, store, sample_workflow):
        sample_workflow["id"] = "versioned"
        store.save(sample_workflow)
        store.save(sample_workflow)
        loaded = store.load("versioned")
        assert loaded["metadata"]["version"] == 2


class TestWorkflowStoreLoad:
    """Test load operations."""

    def test_load_returns_none_for_missing(self, store):
        assert store.load("nonexistent") is None

    def test_load_returns_saved_data(self, store, sample_workflow):
        wf_id = store.save(sample_workflow)
        loaded = store.load(wf_id)
        assert loaded["name"] == "Test Workflow"
        assert len(loaded["nodes"]) == 3
        assert len(loaded["edges"]) == 2


class TestWorkflowStoreList:
    """Test list operations."""

    def test_list_empty(self, store):
        result = store.list_workflows()
        assert result == []

    def test_list_returns_summaries(self, store, sample_workflow):
        store.save(sample_workflow)
        result = store.list_workflows()
        assert len(result) == 1
        summary = result[0]
        assert summary["name"] == "Test Workflow"
        assert summary["node_count"] == 3
        assert summary["edge_count"] == 2
        # Summaries should NOT include full nodes/edges
        assert "nodes" not in summary or not isinstance(summary.get("nodes"), list)

    def test_list_sorted_by_updated(self, store):
        store.save({"id": "old", "name": "Old", "nodes": [], "edges": []})
        store.save({"id": "new", "name": "New", "nodes": [], "edges": []})
        result = store.list_workflows()
        assert len(result) == 2
        # Most recently updated first
        assert result[0]["id"] == "new"


class TestWorkflowStoreDelete:
    """Test delete operations."""

    def test_delete_existing(self, store, sample_workflow):
        wf_id = store.save(sample_workflow)
        assert store.delete(wf_id) is True
        assert store.load(wf_id) is None

    def test_delete_nonexistent(self, store):
        assert store.delete("nonexistent") is False


class TestWorkflowStoreValidation:
    """Test validation."""

    def test_valid_workflow(self, store, sample_workflow):
        result = store.validate(sample_workflow)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_empty_nodes_invalid(self, store):
        result = store.validate({"name": "Empty", "nodes": [], "edges": []})
        assert result.valid is False
        assert any("no nodes" in e.message for e in result.errors)

    def test_invalid_node_type(self, store):
        result = store.validate({
            "name": "Bad Type",
            "nodes": [{"id": "n1", "type": "banana", "label": "Bad"}],
            "edges": [],
        })
        assert result.valid is False
        assert any("banana" in e.message for e in result.errors)

    def test_edge_references_invalid_node(self, store):
        result = store.validate({
            "name": "Bad Edge",
            "nodes": [{"id": "n1", "type": "task", "label": "Task"}],
            "edges": [{"id": "e1", "source": "n1", "target": "ghost", "type": "structural"}],
        })
        assert result.valid is False
        assert any("ghost" in e.message for e in result.errors)

    def test_cycle_detected(self, store):
        result = store.validate({
            "name": "Cyclic",
            "nodes": [
                {"id": "a", "type": "task", "label": "A"},
                {"id": "b", "type": "task", "label": "B"},
                {"id": "c", "type": "task", "label": "C"},
            ],
            "edges": [
                {"id": "e1", "source": "a", "target": "b", "type": "structural"},
                {"id": "e2", "source": "b", "target": "c", "type": "structural"},
                {"id": "e3", "source": "c", "target": "a", "type": "structural"},
            ],
        })
        assert result.valid is False
        assert any("cycle" in e.message.lower() for e in result.errors)

    def test_feedback_edges_allowed(self, store):
        """Feedback edges are intentionally cyclic — should not trigger cycle error."""
        result = store.validate({
            "name": "Loop",
            "nodes": [
                {"id": "a", "type": "task", "label": "A"},
                {"id": "b", "type": "loop", "label": "B"},
            ],
            "edges": [
                {"id": "e1", "source": "a", "target": "b", "type": "structural"},
                {"id": "e2", "source": "b", "target": "a", "type": "feedback"},
            ],
        })
        assert result.valid is True

    def test_orphan_node_warning(self, store):
        result = store.validate({
            "name": "Orphan",
            "nodes": [
                {"id": "a", "type": "task", "label": "A"},
                {"id": "b", "type": "task", "label": "B"},
                {"id": "orphan", "type": "task", "label": "Orphan"},
            ],
            "edges": [
                {"id": "e1", "source": "a", "target": "b", "type": "structural"},
            ],
        })
        assert result.valid is True  # Orphans are warnings, not errors
        assert any("orphan" in w.message.lower() for w in result.warnings)

    def test_new_node_types_valid(self, store):
        """Phase 144 node types should pass validation."""
        result = store.validate({
            "name": "Phase 144",
            "nodes": [
                {"id": "n1", "type": "condition", "label": "If check"},
                {"id": "n2", "type": "parallel", "label": "Fork"},
                {"id": "n3", "type": "loop", "label": "Repeat"},
                {"id": "n4", "type": "transform", "label": "Map"},
                {"id": "n5", "type": "group", "label": "Group"},
            ],
            "edges": [
                {"id": "e1", "source": "n1", "target": "n2", "type": "conditional"},
                {"id": "e2", "source": "n2", "target": "n3", "type": "parallel_fork"},
                {"id": "e3", "source": "n3", "target": "n4", "type": "parallel_join"},
                {"id": "e4", "source": "n4", "target": "n5", "type": "structural"},
            ],
        })
        assert result.valid is True
        assert len(result.errors) == 0

    def test_duplicate_node_id_is_error(self, store):
        result = store.validate({
            "name": "Dup",
            "nodes": [
                {"id": "same", "type": "task", "label": "A"},
                {"id": "same", "type": "task", "label": "B"},
            ],
            "edges": [],
        })
        assert result.valid is False
        assert any("Duplicate node ID" in e.message for e in result.errors)

    def test_missing_name_is_warning(self, store):
        result = store.validate({
            "nodes": [{"id": "n1", "type": "task", "label": "X"}],
            "edges": [],
        })
        assert result.valid is True
        assert any("no name" in w.message for w in result.warnings)

    def test_missing_label_is_warning(self, store):
        result = store.validate({
            "name": "No Label",
            "nodes": [{"id": "n1", "type": "task"}],
            "edges": [],
        })
        assert result.valid is True
        assert any("missing label" in w.message.lower() for w in result.warnings)

    def test_edge_invalid_source(self, store):
        result = store.validate({
            "name": "Bad Source",
            "nodes": [{"id": "n1", "type": "task", "label": "X"}],
            "edges": [{"id": "e1", "source": "phantom", "target": "n1", "type": "structural"}],
        })
        assert result.valid is False
        assert any("source 'phantom' not found" in e.message for e in result.errors)

    def test_validation_result_to_dict(self):
        result = ValidationResult(
            valid=False,
            errors=[ValidationError("error", "Bad thing", node_id="n1")],
            warnings=[ValidationError("warning", "Meh thing")],
        )
        d = result.to_dict()
        assert d["valid"] is False
        assert len(d["errors"]) == 1
        assert d["errors"][0]["message"] == "Bad thing"
        assert d["errors"][0]["node_id"] == "n1"
        assert len(d["warnings"]) == 1


# ============================================================
# MARKER_144.10: workflow_to_tasks Tests
# ============================================================

@pytest.fixture
def diamond_workflow():
    """Diamond DAG: root → left, root → right, left → join, right → join."""
    return {
        "id": "wf_diamond",
        "name": "Diamond Pipeline",
        "nodes": [
            {"id": "root", "type": "task", "label": "Analyze", "data": {}},
            {"id": "left", "type": "agent", "label": "Research Left", "data": {"role": "researcher"}},
            {"id": "right", "type": "subtask", "label": "Build Right", "data": {"role": "coder"}},
            {"id": "join", "type": "agent", "label": "Verify", "data": {"role": "verifier"}},
        ],
        "edges": [
            {"id": "e1", "source": "root", "target": "left", "type": "structural"},
            {"id": "e2", "source": "root", "target": "right", "type": "structural"},
            {"id": "e3", "source": "left", "target": "join", "type": "structural"},
            {"id": "e4", "source": "right", "target": "join", "type": "structural"},
        ],
    }


class TestWorkflowToTasks:
    """Test the workflow node → TaskBoard task conversion (MARKER_144.10)."""

    def test_empty_workflow_returns_empty(self, store):
        tasks = store.workflow_to_tasks({"nodes": [], "edges": []})
        assert tasks == []

    def test_simple_linear_correct_count(self, store, sample_workflow):
        tasks = store.workflow_to_tasks(sample_workflow, "dragon_silver")
        assert len(tasks) == 3

    def test_root_node_priority_1(self, store, sample_workflow):
        tasks = store.workflow_to_tasks(sample_workflow, "dragon_silver")
        root = next(t for t in tasks if t["node_id"] == "n1")
        assert root["priority"] == 1

    def test_depth_1_priority_2(self, store, sample_workflow):
        tasks = store.workflow_to_tasks(sample_workflow, "dragon_silver")
        mid = next(t for t in tasks if t["node_id"] == "n2")
        assert mid["priority"] == 2

    def test_depth_2_priority_3(self, store):
        """Linear chain with structural edges: n1 → n2 → n3 → depth 0,1,2."""
        wf = {
            "name": "Linear",
            "nodes": [
                {"id": "n1", "type": "task", "label": "Step 1"},
                {"id": "n2", "type": "agent", "label": "Step 2"},
                {"id": "n3", "type": "subtask", "label": "Step 3"},
            ],
            "edges": [
                {"id": "e1", "source": "n1", "target": "n2", "type": "structural"},
                {"id": "e2", "source": "n2", "target": "n3", "type": "structural"},
            ],
        }
        tasks = store.workflow_to_tasks(wf, "dragon_silver")
        leaf = next(t for t in tasks if t["node_id"] == "n3")
        assert leaf["priority"] == 3

    def test_diamond_root_no_deps(self, store, diamond_workflow):
        tasks = store.workflow_to_tasks(diamond_workflow)
        root = next(t for t in tasks if t["node_id"] == "root")
        assert root["dependency_node_ids"] == []

    def test_diamond_children_depend_on_root(self, store, diamond_workflow):
        tasks = store.workflow_to_tasks(diamond_workflow)
        left = next(t for t in tasks if t["node_id"] == "left")
        right = next(t for t in tasks if t["node_id"] == "right")
        assert left["dependency_node_ids"] == ["root"]
        assert right["dependency_node_ids"] == ["root"]

    def test_diamond_join_depends_on_both(self, store, diamond_workflow):
        tasks = store.workflow_to_tasks(diamond_workflow)
        join = next(t for t in tasks if t["node_id"] == "join")
        assert set(join["dependency_node_ids"]) == {"left", "right"}

    def test_diamond_join_priority_3(self, store, diamond_workflow):
        tasks = store.workflow_to_tasks(diamond_workflow)
        join = next(t for t in tasks if t["node_id"] == "join")
        assert join["priority"] == 3  # depth=2

    def test_task_title_matches_label(self, store, sample_workflow):
        tasks = store.workflow_to_tasks(sample_workflow)
        titles = {t["title"] for t in tasks}
        assert titles == {"Root Task", "@architect", "Subtask 1"}

    def test_workflow_tag_present(self, store, diamond_workflow):
        tasks = store.workflow_to_tasks(diamond_workflow)
        for task in tasks:
            assert "wf:wf_diamond" in task["tags"]

    def test_preset_tag_dragon(self, store, sample_workflow):
        tasks = store.workflow_to_tasks(sample_workflow, "dragon_silver")
        for task in tasks:
            assert "dragon" in task["tags"]

    def test_preset_tag_titan(self, store, sample_workflow):
        tasks = store.workflow_to_tasks(sample_workflow, "titan_lite")
        for task in tasks:
            assert "titan" in task["tags"]

    def test_condition_node_research_phase(self, store):
        wf = {
            "name": "Cond",
            "nodes": [{"id": "c1", "type": "condition", "label": "Check", "data": {}}],
            "edges": [],
        }
        tasks = store.workflow_to_tasks(wf)
        assert tasks[0]["phase_type"] == "research"
        assert "research" in tasks[0]["tags"]

    def test_proposal_node_research_phase(self, store):
        wf = {
            "name": "Prop",
            "nodes": [{"id": "p1", "type": "proposal", "label": "Propose", "data": {}}],
            "edges": [],
        }
        tasks = store.workflow_to_tasks(wf)
        assert tasks[0]["phase_type"] == "research"

    def test_agent_role_tag(self, store):
        wf = {
            "name": "Agent",
            "nodes": [{"id": "a1", "type": "agent", "label": "R", "data": {"role": "researcher"}}],
            "edges": [],
        }
        tasks = store.workflow_to_tasks(wf)
        assert "researcher" in tasks[0]["tags"]

    def test_description_contains_metadata(self, store):
        wf = {
            "name": "Desc",
            "nodes": [{"id": "n1", "type": "agent", "label": "W", "data": {
                "description": "Custom desc", "role": "coder", "model": "qwen3-coder",
            }}],
            "edges": [],
        }
        tasks = store.workflow_to_tasks(wf)
        desc = tasks[0]["description"]
        assert "Custom desc" in desc
        assert "Role: coder" in desc
        assert "Model: qwen3-coder" in desc
        assert "[from workflow node n1" in desc

    def test_custom_priority_override(self, store):
        wf = {
            "name": "Pri",
            "nodes": [{"id": "n1", "type": "task", "label": "Urgent", "data": {"priority": 1}}],
            "edges": [],
        }
        tasks = store.workflow_to_tasks(wf)
        assert tasks[0]["priority"] == 1

    def test_complexity_from_data(self, store):
        wf = {
            "name": "Complex",
            "nodes": [{"id": "n1", "type": "task", "label": "Hard", "data": {"complexity": 4}}],
            "edges": [],
        }
        tasks = store.workflow_to_tasks(wf)
        assert tasks[0]["complexity"] == 4

    def test_preset_passed_through(self, store, sample_workflow):
        tasks = store.workflow_to_tasks(sample_workflow, "dragon_gold")
        for task in tasks:
            assert task["preset"] == "dragon_gold"

    def test_temporal_edges_create_deps(self, store):
        wf = {
            "name": "Temporal",
            "nodes": [
                {"id": "a", "type": "task", "label": "First"},
                {"id": "b", "type": "task", "label": "Second"},
            ],
            "edges": [{"id": "e1", "source": "a", "target": "b", "type": "temporal"}],
        }
        tasks = store.workflow_to_tasks(wf)
        second = next(t for t in tasks if t["node_id"] == "b")
        assert second["dependency_node_ids"] == ["a"]

    def test_feedback_edges_no_deps(self, store):
        """Feedback edges should NOT create task dependencies."""
        wf = {
            "name": "Feedback",
            "nodes": [
                {"id": "a", "type": "task", "label": "First"},
                {"id": "b", "type": "task", "label": "Second"},
            ],
            "edges": [
                {"id": "e1", "source": "a", "target": "b", "type": "structural"},
                {"id": "e2", "source": "b", "target": "a", "type": "feedback"},
            ],
        }
        tasks = store.workflow_to_tasks(wf)
        first = next(t for t in tasks if t["node_id"] == "a")
        assert first["dependency_node_ids"] == []

    def test_single_node_workflow(self, store):
        wf = {
            "name": "Solo",
            "nodes": [{"id": "only", "type": "task", "label": "Solo"}],
            "edges": [],
        }
        tasks = store.workflow_to_tasks(wf)
        assert len(tasks) == 1
        assert tasks[0]["priority"] == 1
        assert tasks[0]["dependency_node_ids"] == []

    def test_wide_fan_workflow(self, store):
        """10 children branching from one root."""
        wf = {
            "name": "Wide",
            "nodes": [{"id": "root", "type": "task", "label": "Root"}] + [
                {"id": f"c{i}", "type": "subtask", "label": f"Child {i}"} for i in range(10)
            ],
            "edges": [
                {"id": f"e{i}", "source": "root", "target": f"c{i}", "type": "structural"}
                for i in range(10)
            ],
        }
        tasks = store.workflow_to_tasks(wf)
        assert len(tasks) == 11
        root = next(t for t in tasks if t["node_id"] == "root")
        assert root["priority"] == 1
        children = [t for t in tasks if t["node_id"] != "root"]
        assert all(c["priority"] == 2 for c in children)
        assert all(c["dependency_node_ids"] == ["root"] for c in children)

    def test_deep_chain_priority_caps(self, store):
        """5-step chain: depth 0→P1, 1→P2, 2+→P3."""
        nodes = [{"id": f"n{i}", "type": "task", "label": f"Step {i}"} for i in range(5)]
        edges = [{"id": f"e{i}", "source": f"n{i}", "target": f"n{i+1}", "type": "structural"} for i in range(4)]
        tasks = store.workflow_to_tasks({"name": "Chain", "nodes": nodes, "edges": edges})
        priorities = {t["node_id"]: t["priority"] for t in tasks}
        assert priorities["n0"] == 1
        assert priorities["n1"] == 2
        assert priorities["n2"] == 3
        assert priorities["n3"] == 3
        assert priorities["n4"] == 3

    def test_all_node_types_produce_tasks(self, store):
        """All 9 valid node types should produce task dicts."""
        wf = {
            "id": "wf_all",
            "name": "All Types",
            "nodes": [
                {"id": f"n_{t}", "type": t, "label": f"Node {t}", "data": {}}
                for t in VALID_NODE_TYPES
            ],
            "edges": [],
        }
        tasks = store.workflow_to_tasks(wf, "dragon_bronze")
        assert len(tasks) == len(VALID_NODE_TYPES)
        for task in tasks:
            assert task["preset"] == "dragon_bronze"
            assert "dragon" in task["tags"]


# ============================================================
# MARKER_144.10: API Route Tests (execute endpoint)
# ============================================================


class TestWorkflowAPIExecute:
    """Test workflow template API routes including execute bridge."""

    @pytest.fixture
    def api_client(self, tmp_path, monkeypatch):
        """FastAPI test client with temp WorkflowStore."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        import src.api.routes.workflow_template_routes as mod

        test_store = WorkflowStore(project_root=tmp_path)
        monkeypatch.setattr(mod, "_store", test_store)

        app = FastAPI()
        app.include_router(mod.router)
        return TestClient(app)

    def _create_workflow(self, client, name="Test", nodes=None, edges=None):
        """Helper: create a workflow and return its id."""
        if nodes is None:
            nodes = [
                {"id": "n1", "type": "task", "label": "Plan", "position": {"x": 0, "y": 0}, "data": {}},
                {"id": "n2", "type": "agent", "label": "Build", "position": {"x": 100, "y": 0}, "data": {}},
            ]
        if edges is None:
            edges = [
                {"id": "e1", "source": "n1", "target": "n2", "type": "structural", "data": {}},
            ]
        resp = client.post("/api/workflows", json={"name": name, "nodes": nodes, "edges": edges})
        assert resp.status_code == 200
        return resp.json()["id"]

    def test_list_empty(self, api_client):
        resp = api_client.get("/api/workflows")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_create_and_get(self, api_client):
        wf_id = self._create_workflow(api_client, "My WF")
        resp = api_client.get(f"/api/workflows/{wf_id}")
        assert resp.status_code == 200
        assert resp.json()["workflow"]["name"] == "My WF"

    def test_get_nonexistent_404(self, api_client):
        assert api_client.get("/api/workflows/ghost").status_code == 404

    def test_update_workflow(self, api_client):
        wf_id = self._create_workflow(api_client, "V1")
        api_client.put(f"/api/workflows/{wf_id}", json={
            "name": "V2",
            "nodes": [{"id": "n1", "type": "task", "label": "X", "position": {"x": 0, "y": 0}, "data": {}}],
            "edges": [],
        })
        resp = api_client.get(f"/api/workflows/{wf_id}")
        assert resp.json()["workflow"]["name"] == "V2"

    def test_delete_workflow(self, api_client):
        wf_id = self._create_workflow(api_client)
        assert api_client.delete(f"/api/workflows/{wf_id}").status_code == 200
        assert api_client.get(f"/api/workflows/{wf_id}").status_code == 404

    def test_validate_valid(self, api_client):
        resp = api_client.post("/api/workflows/validate", json={
            "name": "OK",
            "nodes": [
                {"id": "n1", "type": "task", "label": "A", "position": {"x": 0, "y": 0}, "data": {}},
                {"id": "n2", "type": "task", "label": "B", "position": {"x": 100, "y": 0}, "data": {}},
            ],
            "edges": [{"id": "e1", "source": "n1", "target": "n2", "type": "structural", "data": {}}],
        })
        assert resp.json()["validation"]["valid"] is True

    def test_validate_invalid(self, api_client):
        resp = api_client.post("/api/workflows/validate", json={
            "name": "Bad",
            "nodes": [{"id": "n1", "type": "banana", "label": "X", "position": {"x": 0, "y": 0}, "data": {}}],
            "edges": [],
        })
        assert resp.json()["validation"]["valid"] is False

    # --- Execute endpoint tests ---

    def test_execute_dry_run(self, api_client):
        wf_id = self._create_workflow(api_client, "Exec Dry")
        resp = api_client.post(f"/api/workflows/{wf_id}/execute", json={
            "preset": "dragon_silver",
            "dry_run": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["dry_run"] is True
        assert data["count"] == 2
        assert len(data["planned_tasks"]) == 2
        titles = [t["title"] for t in data["planned_tasks"]]
        assert "Plan" in titles
        assert "Build" in titles

    def test_execute_dry_run_preserves_deps(self, api_client):
        """Dry run tasks should show correct dependency node IDs."""
        wf_id = self._create_workflow(api_client, "Dep Test")
        resp = api_client.post(f"/api/workflows/{wf_id}/execute", json={
            "preset": "dragon_silver", "dry_run": True,
        })
        tasks = resp.json()["planned_tasks"]
        root = next(t for t in tasks if t["title"] == "Plan")
        child = next(t for t in tasks if t["title"] == "Build")
        assert root["dependency_node_ids"] == []
        assert child["dependency_node_ids"] == ["n1"]

    def test_execute_nonexistent_404(self, api_client):
        resp = api_client.post("/api/workflows/ghost/execute", json={
            "preset": "dragon_silver", "dry_run": False,
        })
        assert resp.status_code == 404

    def test_execute_invalid_workflow_fails(self, api_client):
        """Workflow with validation errors should not execute."""
        wf_id = self._create_workflow(
            api_client, "Bad Exec",
            nodes=[{"id": "n1", "type": "banana", "label": "Bad", "position": {"x": 0, "y": 0}, "data": {}}],
            edges=[],
        )
        resp = api_client.post(f"/api/workflows/{wf_id}/execute", json={
            "preset": "dragon_silver", "dry_run": False,
        })
        data = resp.json()
        assert data["success"] is False
        assert "validation errors" in data["error"]

    def test_execute_empty_nodes_fails(self, api_client):
        """Workflow with no nodes should fail execution."""
        wf_id = self._create_workflow(api_client, "Empty", nodes=[], edges=[])
        resp = api_client.post(f"/api/workflows/{wf_id}/execute", json={
            "preset": "dragon_silver", "dry_run": False,
        })
        data = resp.json()
        assert data["success"] is False

    def test_execute_dry_run_diamond(self, api_client):
        """Diamond workflow dry run: 4 tasks, root at P1."""
        wf_id = self._create_workflow(
            api_client, "Diamond",
            nodes=[
                {"id": "root", "type": "task", "label": "Analyze", "position": {"x": 0, "y": 0}, "data": {}},
                {"id": "left", "type": "agent", "label": "Research", "position": {"x": -100, "y": 100}, "data": {}},
                {"id": "right", "type": "subtask", "label": "Build", "position": {"x": 100, "y": 100}, "data": {}},
                {"id": "join", "type": "agent", "label": "Verify", "position": {"x": 0, "y": 200}, "data": {}},
            ],
            edges=[
                {"id": "e1", "source": "root", "target": "left", "type": "structural", "data": {}},
                {"id": "e2", "source": "root", "target": "right", "type": "structural", "data": {}},
                {"id": "e3", "source": "left", "target": "join", "type": "structural", "data": {}},
                {"id": "e4", "source": "right", "target": "join", "type": "structural", "data": {}},
            ],
        )
        resp = api_client.post(f"/api/workflows/{wf_id}/execute", json={
            "preset": "dragon_gold", "dry_run": True,
        })
        data = resp.json()
        assert data["success"] is True
        assert data["count"] == 4
        tasks = data["planned_tasks"]
        root = next(t for t in tasks if t["title"] == "Analyze")
        assert root["priority"] == 1
        assert root["dependency_node_ids"] == []
        join = next(t for t in tasks if t["title"] == "Verify")
        assert set(join["dependency_node_ids"]) == {"left", "right"}
        # All should have dragon_gold preset
        assert all(t["preset"] == "dragon_gold" for t in tasks)


# ============================================================
# MARKER_144.7: Workflow Architect (Generation) Tests
# ============================================================

from src.services.workflow_architect import (
    _parse_workflow_json,
    _post_process_workflow,
    _quick_validate,
    _generate_fallback_workflow,
    _load_preset_architect_model,
)


class TestWorkflowArchitectHelpers:
    """Test helper functions in workflow_architect.py."""

    # --- JSON parsing ---

    def test_parse_direct_json(self):
        """Direct JSON string should parse."""
        raw = '{"name": "Test", "nodes": [], "edges": []}'
        result = _parse_workflow_json(raw)
        assert result is not None
        assert result["name"] == "Test"

    def test_parse_json_in_code_block(self):
        """JSON wrapped in markdown code block should parse."""
        raw = '```json\n{"name": "Test", "nodes": [], "edges": []}\n```'
        result = _parse_workflow_json(raw)
        assert result is not None
        assert result["name"] == "Test"

    def test_parse_json_with_prose(self):
        """JSON embedded in prose text should be extracted."""
        raw = 'Here is the workflow:\n{"name": "Test", "nodes": [], "edges": []}\nHope that helps!'
        result = _parse_workflow_json(raw)
        assert result is not None
        assert result["name"] == "Test"

    def test_parse_invalid_returns_none(self):
        """Completely invalid content should return None."""
        assert _parse_workflow_json("not json at all") is None

    def test_parse_empty_returns_none(self):
        """Empty string should return None."""
        assert _parse_workflow_json("") is None

    # --- Post-processing ---

    def test_post_process_assigns_id(self):
        """Workflow without ID gets one assigned."""
        wf = {"nodes": [{"id": "n1", "type": "task", "label": "A"}], "edges": []}
        result = _post_process_workflow(wf, "Test task")
        assert result["id"].startswith("wf_")

    def test_post_process_preserves_id(self):
        """Workflow with existing ID keeps it."""
        wf = {"id": "custom_id", "nodes": [], "edges": []}
        result = _post_process_workflow(wf, "Test")
        assert result["id"] == "custom_id"

    def test_post_process_assigns_name(self):
        """Name derived from description if missing."""
        wf = {"nodes": [], "edges": []}
        result = _post_process_workflow(wf, "Build a REST API")
        assert result["name"] == "Build a REST API"

    def test_post_process_fixes_missing_node_fields(self):
        """Nodes without label/position/data get defaults."""
        wf = {
            "nodes": [{"id": "n1", "type": "task"}],
            "edges": [],
        }
        result = _post_process_workflow(wf, "Test")
        node = result["nodes"][0]
        assert node["label"] == "Step 1"
        assert "x" in node["position"]
        assert "y" in node["position"]
        assert isinstance(node["data"], dict)

    def test_post_process_fixes_invalid_type(self):
        """Invalid node type gets replaced with 'task'."""
        wf = {
            "nodes": [{"id": "n1", "type": "banana", "label": "Bad"}],
            "edges": [],
        }
        result = _post_process_workflow(wf, "Test")
        assert result["nodes"][0]["type"] == "task"

    def test_post_process_drops_invalid_edges(self):
        """Edges referencing non-existent nodes get dropped."""
        wf = {
            "nodes": [{"id": "n1", "type": "task", "label": "A"}],
            "edges": [{"id": "e1", "source": "n1", "target": "n999"}],
        }
        result = _post_process_workflow(wf, "Test")
        assert len(result["edges"]) == 0

    def test_post_process_keeps_valid_edges(self):
        """Valid edges are preserved."""
        wf = {
            "nodes": [
                {"id": "n1", "type": "task", "label": "A"},
                {"id": "n2", "type": "task", "label": "B"},
            ],
            "edges": [{"id": "e1", "source": "n1", "target": "n2"}],
        }
        result = _post_process_workflow(wf, "Test")
        assert len(result["edges"]) == 1

    def test_post_process_metadata_generated_flag(self):
        """Metadata should have generated=True flag."""
        wf = {"nodes": [], "edges": []}
        result = _post_process_workflow(wf, "Test")
        assert result["metadata"]["generated"] is True
        assert result["metadata"]["generator"] == "workflow_architect_v1"

    # --- Quick validation ---

    def test_validate_empty_nodes_fails(self):
        """Workflow with no nodes is invalid."""
        result = _quick_validate({"nodes": [], "edges": []})
        assert result["valid"] is False
        assert "No nodes" in result["errors"][0]

    def test_validate_valid_workflow(self):
        """Simple valid workflow passes."""
        result = _quick_validate({
            "nodes": [
                {"id": "n1", "type": "task", "label": "A"},
                {"id": "n2", "type": "task", "label": "B"},
            ],
            "edges": [{"id": "e1", "source": "n1", "target": "n2"}],
        })
        assert result["valid"] is True
        assert result["node_count"] == 2
        assert result["edge_count"] == 1

    def test_validate_bad_edge_source(self):
        """Edge with invalid source node fails."""
        result = _quick_validate({
            "nodes": [{"id": "n1", "type": "task", "label": "A"}],
            "edges": [{"id": "e1", "source": "ghost", "target": "n1"}],
        })
        assert result["valid"] is False

    def test_validate_duplicate_node_ids(self):
        """Duplicate node IDs detected."""
        result = _quick_validate({
            "nodes": [
                {"id": "n1", "type": "task", "label": "A"},
                {"id": "n1", "type": "task", "label": "B"},
            ],
            "edges": [],
        })
        assert result["valid"] is False
        assert "Duplicate" in result["errors"][0]

    # --- Fallback workflow generation ---

    def test_fallback_low_complexity(self):
        """Low complexity generates 2 nodes (implement + verify)."""
        result = _generate_fallback_workflow("Fix a bug", "low")
        assert result["success"] is True
        wf = result["workflow"]
        assert len(wf["nodes"]) == 2
        assert len(wf["edges"]) == 1
        assert wf["nodes"][0]["type"] == "task"
        assert wf["nodes"][1]["type"] == "agent"

    def test_fallback_medium_complexity(self):
        """Medium complexity generates 3 nodes (research + implement + verify)."""
        result = _generate_fallback_workflow("Add a feature", "medium")
        assert result["success"] is True
        wf = result["workflow"]
        assert len(wf["nodes"]) == 3
        assert len(wf["edges"]) == 2

    def test_fallback_high_complexity(self):
        """High complexity generates 6 nodes with parallel branches."""
        result = _generate_fallback_workflow("Full redesign", "high")
        assert result["success"] is True
        wf = result["workflow"]
        assert len(wf["nodes"]) == 6
        assert len(wf["edges"]) == 6
        # Should have parallel branches (2 nodes at same depth)
        labels = [n["label"] for n in wf["nodes"]]
        assert "Implement Core" in labels
        assert "Implement UI" in labels

    def test_fallback_default_complexity(self):
        """No complexity hint defaults to medium."""
        result = _generate_fallback_workflow("Some task")
        assert result["success"] is True
        assert len(result["workflow"]["nodes"]) == 3  # medium default

    def test_fallback_workflow_has_id(self):
        """Fallback workflow gets a workflow ID."""
        result = _generate_fallback_workflow("Test")
        assert result["workflow"]["id"].startswith("wf_")

    def test_fallback_metadata(self):
        """Fallback workflow has generator metadata."""
        result = _generate_fallback_workflow("Test", "low")
        meta = result["workflow"]["metadata"]
        assert meta["generated"] is True
        assert meta["generator"] == "workflow_architect_fallback"
        assert meta["complexity_hint"] == "low"

    def test_fallback_validation_passes(self):
        """Generated fallback workflows should always pass validation."""
        for hint in ["low", "medium", "high"]:
            result = _generate_fallback_workflow(f"Task {hint}", hint)
            assert result["validation"]["valid"] is True

    # --- Preset model loading ---

    def test_preset_model_dragon_silver(self):
        """Dragon silver should resolve to kimi-k2.5."""
        model = _load_preset_architect_model("dragon_silver")
        assert "kimi" in model.lower() or "moonshotai" in model.lower()

    def test_preset_model_unknown_falls_back(self):
        """Unknown preset falls back to kimi-k2.5."""
        model = _load_preset_architect_model("nonexistent_preset")
        assert "kimi" in model.lower() or "moonshotai" in model.lower()


class TestWorkflowGenerateAPI:
    """Test the /api/workflows/generate endpoint."""

    @pytest.fixture
    def api_client(self, tmp_path, monkeypatch):
        """FastAPI test client with temp WorkflowStore."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        import src.api.routes.workflow_template_routes as mod

        test_store = WorkflowStore(project_root=tmp_path)
        monkeypatch.setattr(mod, "_store", test_store)

        app = FastAPI()
        app.include_router(mod.router)
        return TestClient(app)

    def test_generate_fallback_basic(self, api_client):
        """Generate endpoint returns a valid workflow (fallback mode)."""
        resp = api_client.post("/api/workflows/generate", json={
            "description": "Build a REST API with auth",
            "preset": "dragon_silver",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "workflow" in data
        wf = data["workflow"]
        assert len(wf["nodes"]) >= 2
        assert len(wf["edges"]) >= 1

    def test_generate_with_complexity_hint(self, api_client):
        """High complexity hint generates more nodes."""
        resp = api_client.post("/api/workflows/generate", json={
            "description": "Full system redesign with frontend, backend, database, and tests",
            "complexity_hint": "high",
            "preset": "dragon_silver",
        })
        data = resp.json()
        assert data["success"] is True
        assert len(data["workflow"]["nodes"]) >= 3

    def test_generate_low_complexity(self, api_client):
        """Low complexity generates a small workflow (2-4 nodes)."""
        resp = api_client.post("/api/workflows/generate", json={
            "description": "Fix a typo",
            "complexity_hint": "low",
            "preset": "dragon_silver",
        })
        data = resp.json()
        assert data["success"] is True
        # Low complexity: 2-4 nodes depending on LLM vs fallback
        assert 2 <= len(data["workflow"]["nodes"]) <= 4

    def test_generate_and_save(self, api_client):
        """Generate with save=true should persist the workflow."""
        resp = api_client.post("/api/workflows/generate", json={
            "description": "Create a feature",
            "save": True,
            "preset": "dragon_silver",
        })
        data = resp.json()
        assert data["success"] is True
        assert data.get("saved") is True
        assert "workflow_id" in data

        # Verify it's actually saved
        wf_id = data["workflow_id"]
        resp2 = api_client.get(f"/api/workflows/{wf_id}")
        assert resp2.status_code == 200
        assert resp2.json()["workflow"]["name"] is not None

    def test_generate_without_save(self, api_client):
        """Generate without save should not persist."""
        resp = api_client.post("/api/workflows/generate", json={
            "description": "Test no save",
            "save": False,
        })
        data = resp.json()
        assert data["success"] is True
        assert data.get("saved") is not True

        # Workflows list should still be empty
        resp2 = api_client.get("/api/workflows")
        assert resp2.json()["count"] == 0

    def test_generate_has_valid_structure(self, api_client):
        """Generated workflow should pass full WorkflowStore validation."""
        resp = api_client.post("/api/workflows/generate", json={
            "description": "Add user authentication",
            "complexity_hint": "medium",
        })
        data = resp.json()
        wf = data["workflow"]

        # Validate via the validate endpoint
        resp2 = api_client.post("/api/workflows/validate", json={
            "name": wf.get("name", "Test"),
            "nodes": [
                {"id": n["id"], "type": n["type"], "label": n["label"],
                 "position": n.get("position", {"x": 0, "y": 0}), "data": n.get("data", {})}
                for n in wf["nodes"]
            ],
            "edges": [
                {"id": e["id"], "source": e["source"], "target": e["target"],
                 "type": e.get("type", "structural"), "data": e.get("data", {})}
                for e in wf["edges"]
            ],
        })
        assert resp2.json()["validation"]["valid"] is True

    def test_generate_validation_in_response(self, api_client):
        """Response should include validation info."""
        resp = api_client.post("/api/workflows/generate", json={
            "description": "Test validation",
        })
        data = resp.json()
        assert "validation" in data
        assert data["validation"]["valid"] is True

    def test_generate_model_used(self, api_client):
        """Response should indicate which model was used."""
        resp = api_client.post("/api/workflows/generate", json={
            "description": "Test model",
        })
        data = resp.json()
        assert "model_used" in data


# ============================================================
# MARKER_144.8: n8n Converter Tests
# ============================================================

class TestN8NConverter:
    """Tests for n8n ↔ VETKA conversion."""

    def test_detect_n8n_format_valid(self):
        from src.services.converters.n8n_converter import detect_n8n_format
        n8n_data = {
            "nodes": [
                {"name": "Start", "type": "n8n-nodes-base.manualTrigger", "typeVersion": 1, "position": [250, 300]}
            ],
            "connections": {},
        }
        assert detect_n8n_format(n8n_data) is True

    def test_detect_n8n_format_invalid(self):
        from src.services.converters.n8n_converter import detect_n8n_format
        assert detect_n8n_format({"nodes": [{"id": "n1", "type": "task"}], "edges": []}) is False
        assert detect_n8n_format({"random": "data"}) is False
        assert detect_n8n_format("not a dict") is False

    def test_detect_n8n_empty_with_connections(self):
        from src.services.converters.n8n_converter import detect_n8n_format
        assert detect_n8n_format({"nodes": [], "connections": {}}) is True

    def test_n8n_to_vetka_basic(self):
        from src.services.converters.n8n_converter import n8n_to_vetka
        n8n = {
            "name": "My n8n Workflow",
            "nodes": [
                {"name": "Start", "type": "n8n-nodes-base.manualTrigger", "typeVersion": 1, "position": [250, 300]},
                {"name": "Code", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [450, 300], "parameters": {"jsCode": "return items;"}},
            ],
            "connections": {
                "Start": {"main": [[{"node": "Code", "type": "main", "index": 0}]]}
            },
        }
        result = n8n_to_vetka(n8n)
        assert result["name"] == "My n8n Workflow"
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1
        assert result["metadata"]["imported_from"] == "n8n"

    def test_n8n_to_vetka_node_types(self):
        from src.services.converters.n8n_converter import n8n_to_vetka
        n8n = {
            "name": "Type Test",
            "nodes": [
                {"name": "If", "type": "n8n-nodes-base.if", "typeVersion": 1, "position": [0, 0]},
                {"name": "HTTP", "type": "n8n-nodes-base.httpRequest", "typeVersion": 3, "position": [200, 0]},
                {"name": "Set", "type": "n8n-nodes-base.set", "typeVersion": 2, "position": [400, 0]},
            ],
            "connections": {},
        }
        result = n8n_to_vetka(n8n)
        types = {n["label"]: n["type"] for n in result["nodes"]}
        assert types["If"] == "condition"
        assert types["HTTP"] == "agent"
        assert types["Set"] == "transform"

    def test_n8n_to_vetka_preserves_params(self):
        from src.services.converters.n8n_converter import n8n_to_vetka
        n8n = {
            "name": "Params",
            "nodes": [
                {"name": "Code", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [0, 0],
                 "parameters": {"jsCode": "const x = 1; return items;", "mode": "runOnceForAllItems"}},
            ],
            "connections": {},
        }
        result = n8n_to_vetka(n8n)
        node_data = result["nodes"][0]["data"]
        assert "n8n_parameters" in node_data
        assert node_data["n8n_parameters"]["jsCode"] == "const x = 1; return items;"

    def test_n8n_to_vetka_conditional_edges(self):
        from src.services.converters.n8n_converter import n8n_to_vetka
        n8n = {
            "name": "Conditional",
            "nodes": [
                {"name": "If Check", "type": "n8n-nodes-base.if", "typeVersion": 1, "position": [0, 0]},
                {"name": "True Branch", "type": "n8n-nodes-base.code", "typeVersion": 1, "position": [200, -100]},
                {"name": "False Branch", "type": "n8n-nodes-base.code", "typeVersion": 1, "position": [200, 100]},
            ],
            "connections": {
                "If Check": {
                    "main": [
                        [{"node": "True Branch", "type": "main", "index": 0}],
                        [{"node": "False Branch", "type": "main", "index": 0}],
                    ]
                }
            },
        }
        result = n8n_to_vetka(n8n)
        edges = result["edges"]
        assert len(edges) == 2
        labels = {e.get("label") for e in edges}
        assert "true" in labels
        assert "false" in labels
        assert all(e["type"] == "conditional" for e in edges)

    def test_n8n_to_vetka_positions(self):
        from src.services.converters.n8n_converter import n8n_to_vetka
        n8n = {
            "name": "Pos Test",
            "nodes": [
                {"name": "A", "type": "n8n-nodes-base.code", "typeVersion": 1, "position": [100, 200]},
                {"name": "B", "type": "n8n-nodes-base.code", "typeVersion": 1, "position": {"x": 300, "y": 400}},
            ],
            "connections": {},
        }
        result = n8n_to_vetka(n8n)
        assert result["nodes"][0]["position"] == {"x": 100, "y": 200}
        assert result["nodes"][1]["position"] == {"x": 300, "y": 400}

    def test_vetka_to_n8n_basic(self):
        from src.services.converters.n8n_converter import vetka_to_n8n
        workflow = {
            "id": "wf_test",
            "name": "Test Workflow",
            "nodes": [
                {"id": "n1", "type": "task", "label": "Do Something", "position": {"x": 0, "y": 0}, "data": {"description": "desc"}},
                {"id": "n2", "type": "transform", "label": "Transform", "position": {"x": 200, "y": 0}, "data": {}},
            ],
            "edges": [
                {"id": "e1", "source": "n1", "target": "n2", "type": "structural"},
            ],
        }
        result = vetka_to_n8n(workflow)
        assert result["name"] == "Test Workflow"
        assert len(result["nodes"]) == 2
        assert "connections" in result
        assert result["meta"]["exported_from"] == "vetka"

    def test_vetka_to_n8n_node_types(self):
        from src.services.converters.n8n_converter import vetka_to_n8n
        workflow = {
            "name": "Types",
            "nodes": [
                {"id": "n1", "type": "condition", "label": "Check", "position": {"x": 0, "y": 0}, "data": {}},
                {"id": "n2", "type": "agent", "label": "API Call", "position": {"x": 200, "y": 0}, "data": {}},
            ],
            "edges": [],
        }
        result = vetka_to_n8n(workflow)
        types = {n["name"]: n["type"] for n in result["nodes"]}
        assert types["Check"] == "n8n-nodes-base.if"
        assert types["API Call"] == "n8n-nodes-base.httpRequest"

    def test_n8n_roundtrip(self):
        """Import n8n → export back → structure preserved."""
        from src.services.converters.n8n_converter import n8n_to_vetka, vetka_to_n8n
        original_n8n = {
            "name": "Roundtrip",
            "nodes": [
                {"name": "Start", "type": "n8n-nodes-base.manualTrigger", "typeVersion": 1, "position": [0, 0]},
                {"name": "Process", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [200, 0],
                 "parameters": {"jsCode": "return items;"}},
            ],
            "connections": {
                "Start": {"main": [[{"node": "Process", "type": "main", "index": 0}]]}
            },
        }
        vetka = n8n_to_vetka(original_n8n)
        exported = vetka_to_n8n(vetka)
        # Check structure preserved
        assert exported["name"] == "Roundtrip"
        assert len(exported["nodes"]) == 2
        # Original n8n type should be restored from data.n8n_type
        node_types = {n["name"]: n["type"] for n in exported["nodes"]}
        assert node_types["Start"] == "n8n-nodes-base.manualTrigger"
        assert node_types["Process"] == "n8n-nodes-base.code"


# ============================================================
# MARKER_144.9: ComfyUI Converter Tests
# ============================================================

class TestComfyUIConverter:
    """Tests for ComfyUI ↔ VETKA conversion."""

    def test_detect_graph_format(self):
        from src.services.converters.comfyui_converter import detect_comfyui_format
        graph = {
            "nodes": [{"id": 1, "type": "KSampler", "pos": [0, 0]}],
            "links": [[1, 1, 0, 2, 0, "MODEL"]],
        }
        assert detect_comfyui_format(graph) == "graph"

    def test_detect_api_format(self):
        from src.services.converters.comfyui_converter import detect_comfyui_format
        api = {
            "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "v1-5.safetensors"}},
            "2": {"class_type": "KSampler", "inputs": {"model": ["1", 0]}},
        }
        assert detect_comfyui_format(api) == "api"

    def test_detect_none_format(self):
        from src.services.converters.comfyui_converter import detect_comfyui_format
        assert detect_comfyui_format({"random": "data"}) == "none"
        assert detect_comfyui_format("string") == "none"

    def test_comfyui_graph_to_vetka(self):
        from src.services.converters.comfyui_converter import comfyui_to_vetka
        graph = {
            "nodes": [
                {"id": 1, "type": "CheckpointLoaderSimple", "pos": [100, 200], "title": "Load Model"},
                {"id": 2, "type": "KSampler", "pos": [300, 200], "title": "Sampler"},
                {"id": 3, "type": "SaveImage", "pos": [500, 200], "title": "Save"},
            ],
            "links": [
                [1, 1, 0, 2, 0, "MODEL"],
                [2, 2, 0, 3, 0, "IMAGE"],
            ],
            "extra": {"title": "My ComfyUI Workflow"},
        }
        result = comfyui_to_vetka(graph)
        assert len(result["nodes"]) == 3
        assert len(result["edges"]) == 2
        assert result["metadata"]["imported_from"] == "comfyui_graph"
        # Check type mapping
        types = {n["label"]: n["type"] for n in result["nodes"]}
        assert types["Load Model"] == "agent"
        assert types["Sampler"] == "task"
        assert types["Save"] == "proposal"

    def test_comfyui_api_to_vetka(self):
        from src.services.converters.comfyui_converter import comfyui_to_vetka
        api = {
            "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "v1-5.safetensors"}},
            "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "a cat", "clip": ["1", 1]}},
            "3": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["2", 0]}},
        }
        result = comfyui_to_vetka(api)
        assert len(result["nodes"]) == 3
        assert len(result["edges"]) == 3  # clip→2, model→3, positive→3
        assert result["metadata"]["imported_from"] == "comfyui_api"

    def test_comfyui_api_preserves_inputs(self):
        from src.services.converters.comfyui_converter import comfyui_to_vetka
        api = {
            "1": {"class_type": "KSampler", "inputs": {
                "seed": 42, "steps": 20, "cfg": 7.5,
                "sampler_name": "euler", "scheduler": "normal",
                "model": ["2", 0],
            }},
            "2": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd_xl.safetensors"}},
        }
        result = comfyui_to_vetka(api)
        # Non-link inputs should be preserved
        sampler = [n for n in result["nodes"] if n["label"] == "KSampler"][0]
        inputs = sampler["data"].get("comfyui_inputs", {})
        assert inputs.get("seed") == 42
        assert inputs.get("steps") == 20

    def test_vetka_to_comfyui_graph(self):
        from src.services.converters.comfyui_converter import vetka_to_comfyui
        workflow = {
            "name": "Test Export",
            "nodes": [
                {"id": "n1", "type": "agent", "label": "Load Model", "position": {"x": 0, "y": 0}, "data": {}},
                {"id": "n2", "type": "task", "label": "Sample", "position": {"x": 200, "y": 0}, "data": {}},
            ],
            "edges": [
                {"id": "e1", "source": "n1", "target": "n2", "type": "dataflow", "data": {"from_slot": 0, "to_slot": 0}},
            ],
        }
        result = vetka_to_comfyui(workflow, fmt="graph")
        assert len(result["nodes"]) == 2
        assert len(result["links"]) == 1
        assert result["extra"]["exported_from"] == "vetka"

    def test_vetka_to_comfyui_api(self):
        from src.services.converters.comfyui_converter import vetka_to_comfyui
        workflow = {
            "name": "API Export",
            "nodes": [
                {"id": "n1", "type": "agent", "label": "Load", "position": {"x": 0, "y": 0}, "data": {}},
                {"id": "n2", "type": "task", "label": "Process", "position": {"x": 200, "y": 0}, "data": {}},
            ],
            "edges": [
                {"id": "e1", "source": "n1", "target": "n2", "type": "dataflow",
                 "data": {"from_slot": 0, "input_name": "model"}},
            ],
        }
        result = vetka_to_comfyui(workflow, fmt="api")
        assert "1" in result
        assert "2" in result
        assert result["1"]["class_type"] == "VETKAAgent"
        # Edge should create input link
        assert result["2"]["inputs"].get("model") == ["1", 0]

    def test_comfyui_graph_roundtrip(self):
        from src.services.converters.comfyui_converter import comfyui_to_vetka, vetka_to_comfyui
        original = {
            "nodes": [
                {"id": 1, "type": "CheckpointLoaderSimple", "pos": [0, 0], "title": "Load",
                 "widgets_values": ["model.safetensors"]},
                {"id": 2, "type": "KSampler", "pos": [200, 0], "title": "Sample"},
            ],
            "links": [[1, 1, 0, 2, 0, "MODEL"]],
        }
        vetka = comfyui_to_vetka(original)
        exported = vetka_to_comfyui(vetka, fmt="graph")
        # Check structure preserved
        assert len(exported["nodes"]) == 2
        assert len(exported["links"]) == 1
        # Original class_type should be restored
        types = {n["title"]: n["type"] for n in exported["nodes"]}
        assert types["Load"] == "CheckpointLoaderSimple"
        assert types["Sample"] == "KSampler"

    def test_comfyui_positions(self):
        from src.services.converters.comfyui_converter import comfyui_to_vetka
        graph = {
            "nodes": [
                {"id": 1, "type": "KSampler", "pos": [150, 300]},
            ],
            "links": [],
        }
        result = comfyui_to_vetka(graph)
        assert result["nodes"][0]["position"] == {"x": 150, "y": 300}


# ============================================================
# MARKER_144.8/9: Import/Export API Endpoint Tests
# ============================================================

class TestImportExportAPI:
    """Tests for import/export API endpoints."""

    @pytest.fixture
    def api_client(self, store):
        from fastapi.testclient import TestClient
        from src.api.routes.workflow_template_routes import router, _store
        from fastapi import FastAPI
        import src.api.routes.workflow_template_routes as mod
        mod._store = store
        app = FastAPI()
        app.include_router(router)
        yield TestClient(app)
        mod._store = None

    def test_import_n8n(self, api_client):
        n8n_data = {
            "name": "Test n8n",
            "nodes": [
                {"name": "Start", "type": "n8n-nodes-base.manualTrigger", "typeVersion": 1, "position": [0, 0]},
                {"name": "Code", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [200, 0]},
            ],
            "connections": {
                "Start": {"main": [[{"node": "Code", "type": "main", "index": 0}]]}
            },
        }
        resp = api_client.post("/api/workflows/import", json={"data": n8n_data, "save": True})
        data = resp.json()
        assert data["success"] is True
        assert data["format_detected"] == "n8n"
        assert data["saved"] is True
        assert data["workflow_id"] is not None
        assert len(data["workflow"]["nodes"]) == 2

    def test_import_comfyui_graph(self, api_client):
        comfy_data = {
            "nodes": [
                {"id": 1, "type": "CheckpointLoaderSimple", "pos": [0, 0]},
                {"id": 2, "type": "KSampler", "pos": [200, 0]},
            ],
            "links": [[1, 1, 0, 2, 0, "MODEL"]],
        }
        resp = api_client.post("/api/workflows/import", json={"data": comfy_data, "save": True})
        data = resp.json()
        assert data["success"] is True
        assert data["format_detected"] == "comfyui"
        assert len(data["workflow"]["nodes"]) == 2

    def test_import_comfyui_api(self, api_client):
        comfy_api = {
            "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "model.safetensors"}},
            "2": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "seed": 42}},
        }
        resp = api_client.post("/api/workflows/import", json={"data": comfy_api, "format": "comfyui", "save": False})
        data = resp.json()
        assert data["success"] is True
        assert data["format_detected"] == "comfyui"
        assert data["saved"] is False

    def test_import_auto_detect(self, api_client):
        """Auto-detection should identify n8n format."""
        n8n_data = {
            "nodes": [{"name": "A", "type": "n8n-nodes-base.code", "typeVersion": 1, "position": [0, 0]}],
            "connections": {},
        }
        resp = api_client.post("/api/workflows/import", json={"data": n8n_data})
        assert resp.json()["format_detected"] == "n8n"

    def test_import_unknown_format(self, api_client):
        resp = api_client.post("/api/workflows/import", json={"data": {"random": "stuff"}})
        data = resp.json()
        assert data["success"] is False
        assert "Unknown" in data["error"]

    def test_export_n8n(self, api_client, store):
        """Export a saved workflow as n8n JSON."""
        workflow = {
            "name": "Export Test",
            "nodes": [
                {"id": "n1", "type": "task", "label": "Do Stuff", "position": {"x": 0, "y": 0}, "data": {}},
            ],
            "edges": [],
        }
        wf_id = store.save(workflow)
        resp = api_client.post(f"/api/workflows/{wf_id}/export", json={"format": "n8n"})
        data = resp.json()
        assert data["success"] is True
        assert data["format"] == "n8n"
        assert len(data["exported"]["nodes"]) == 1
        assert "connections" in data["exported"]

    def test_export_comfyui(self, api_client, store):
        """Export a saved workflow as ComfyUI JSON."""
        workflow = {
            "name": "ComfyUI Export",
            "nodes": [
                {"id": "n1", "type": "agent", "label": "Load", "position": {"x": 0, "y": 0}, "data": {}},
                {"id": "n2", "type": "task", "label": "Sample", "position": {"x": 200, "y": 0}, "data": {}},
            ],
            "edges": [
                {"id": "e1", "source": "n1", "target": "n2", "type": "dataflow"},
            ],
        }
        wf_id = store.save(workflow)
        resp = api_client.post(f"/api/workflows/{wf_id}/export", json={"format": "comfyui"})
        data = resp.json()
        assert data["success"] is True
        assert data["format"] == "comfyui"
        assert len(data["exported"]["nodes"]) == 2
        assert "links" in data["exported"]

    def test_export_nonexistent(self, api_client):
        resp = api_client.post("/api/workflows/wf_nonexistent/export", json={"format": "n8n"})
        assert resp.status_code == 404

    def test_import_and_export_roundtrip(self, api_client, store):
        """Import n8n → save → export n8n → structure matches."""
        original = {
            "name": "Roundtrip API",
            "nodes": [
                {"name": "Start", "type": "n8n-nodes-base.manualTrigger", "typeVersion": 1, "position": [0, 0]},
                {"name": "End", "type": "n8n-nodes-base.noOp", "typeVersion": 1, "position": [200, 0]},
            ],
            "connections": {
                "Start": {"main": [[{"node": "End", "type": "main", "index": 0}]]}
            },
        }
        # Import
        imp = api_client.post("/api/workflows/import", json={"data": original, "save": True})
        imp_data = imp.json()
        assert imp_data["success"]
        wf_id = imp_data["workflow_id"]

        # Export
        exp = api_client.post(f"/api/workflows/{wf_id}/export", json={"format": "n8n"})
        exp_data = exp.json()
        assert exp_data["success"]
        exported = exp_data["exported"]

        # Structure should match
        assert exported["name"] == "Roundtrip API"
        assert len(exported["nodes"]) == 2
        node_names = {n["name"] for n in exported["nodes"]}
        assert "Start" in node_names
        assert "End" in node_names


# ============================================================
# MARKER_144.12B: Architect Chat Fix Tests
# ============================================================

class TestArchitectChatFix:
    """Tests for the architect chat LLM connection fix."""

    def test_get_architect_model_v2_dragon_silver(self):
        from src.api.routes.architect_chat_routes import _get_architect_model_v2
        model, source = _get_architect_model_v2("dragon_silver")
        assert "kimi" in model.lower() or "moonshotai" in model.lower()
        assert source == "polza"

    def test_get_architect_model_v2_dragon_bronze(self):
        from src.api.routes.architect_chat_routes import _get_architect_model_v2
        model, source = _get_architect_model_v2("dragon_bronze")
        assert "qwen" in model.lower()
        assert source == "polza"

    def test_get_architect_model_v2_unknown_preset(self):
        from src.api.routes.architect_chat_routes import _get_architect_model_v2
        model, source = _get_architect_model_v2("nonexistent_preset")
        # Should fall back to kimi-k2.5 / polza
        assert model is not None
        assert source is not None

    def test_architect_chat_fallback(self):
        """Fallback response should work when LLM unavailable."""
        from src.api.routes.architect_chat_routes import _fallback_response, ArchitectChatRequest
        req = ArchitectChatRequest(message="help me plan a project")
        resp = _fallback_response(req)
        assert resp.success is True
        assert len(resp.response) > 0

    def test_architect_chat_api_endpoint(self):
        """The /api/architect/chat endpoint should exist and return a response."""
        from fastapi.testclient import TestClient
        from src.api.routes.architect_chat_routes import router
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        resp = client.post("/api/architect/chat", json={
            "message": "Hello architect",
            "context": {"preset": "dragon_silver"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["response"]) > 0
