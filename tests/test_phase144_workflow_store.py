"""
MARKER_144.1_TESTS: Tests for Workflow Store.

@phase 144
@status active
"""

import json
import pytest
import tempfile
from pathlib import Path

from src.services.workflow_store import WorkflowStore, ValidationResult


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
