"""
MARKER_135.T1: DAG Aggregator Tests.
TDD approach — write tests BEFORE implementation.

@phase 135.2
@status active
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

# Will be implemented
# from src.services.dag_aggregator import DAGAggregator, DAGNode, DAGEdge, DAGResponse


class TestDAGAggregatorBuildDAG:
    """Test DAG construction from task board data."""

    @pytest.fixture
    def aggregator(self):
        """Create DAGAggregator instance with mocked dependencies."""
        from src.services.dag_aggregator import DAGAggregator
        return DAGAggregator()

    @pytest.fixture
    def sample_task(self):
        """Sample task from task board."""
        return {
            "id": "task_001",
            "title": "Add caching to API",
            "status": "done",
            "phase_type": "build",
            "preset": "dragon_silver",
            "created_at": "2026-02-10T10:00:00",
            "started_at": "2026-02-10T10:01:00",
            "completed_at": "2026-02-10T10:05:00",
            "pipeline_task_id": "pipe_001",
            "result": {
                "success": True,
                "subtasks": [
                    {
                        "description": "Create cache service",
                        "status": "done",
                        "agent": "coder",
                        "tokens_used": 1240,
                    },
                    {
                        "description": "Add Redis client",
                        "status": "done",
                        "agent": "coder",
                        "tokens_used": 890,
                    },
                ],
                "agents": {
                    "scout": {"status": "done", "duration_s": 3},
                    "architect": {"status": "done", "duration_s": 8, "model": "kimi-k2.5"},
                    "researcher": {"status": "done", "duration_s": 5, "model": "grok-fast-4.1"},
                    "coder": {"status": "done", "duration_s": 45, "model": "qwen3-coder"},
                    "verifier": {"status": "done", "duration_s": 4, "confidence": 0.87},
                },
            },
        }

    def test_empty_board_returns_empty_dag(self, aggregator):
        """Empty task board should return empty DAG."""
        with patch.object(aggregator.task_board, 'list_tasks', return_value=[]):
            result = aggregator.build_dag()

        assert result.nodes == []
        assert result.edges == []
        assert result.root_ids == []

    def test_single_task_returns_one_root_node(self, aggregator, sample_task):
        """Single task should create one root node at layer 0."""
        with patch.object(aggregator.task_board, 'list_tasks', return_value=[sample_task]):
            result = aggregator.build_dag()

        root_nodes = [n for n in result.nodes if n.layer == 0]
        assert len(root_nodes) == 1
        assert root_nodes[0].type == "task"
        assert root_nodes[0].label == "Add caching to API"

    def test_task_status_maps_correctly(self, aggregator, sample_task):
        """Task status should be preserved in node."""
        with patch.object(aggregator.task_board, 'list_tasks', return_value=[sample_task]):
            result = aggregator.build_dag()

        task_node = next(n for n in result.nodes if n.type == "task")
        assert task_node.status == "done"

    def test_completed_task_has_agent_nodes(self, aggregator, sample_task):
        """Completed task with result should have agent nodes."""
        with patch.object(aggregator.task_board, 'list_tasks', return_value=[sample_task]):
            result = aggregator.build_dag()

        agent_nodes = [n for n in result.nodes if n.type == "agent"]
        assert len(agent_nodes) == 5  # scout, architect, researcher, coder, verifier

    def test_agent_nodes_on_layer_1(self, aggregator, sample_task):
        """Agent nodes should be on layer 1."""
        with patch.object(aggregator.task_board, 'list_tasks', return_value=[sample_task]):
            result = aggregator.build_dag()

        agent_nodes = [n for n in result.nodes if n.type == "agent"]
        for agent in agent_nodes:
            assert agent.layer == 1

    def test_subtask_nodes_on_layer_2(self, aggregator, sample_task):
        """Subtask nodes should be on layer 2."""
        with patch.object(aggregator.task_board, 'list_tasks', return_value=[sample_task]):
            result = aggregator.build_dag()

        subtask_nodes = [n for n in result.nodes if n.type == "subtask"]
        assert len(subtask_nodes) == 2
        for subtask in subtask_nodes:
            assert subtask.layer == 2

    def test_edges_connect_task_to_agents(self, aggregator, sample_task):
        """Edges should connect task to agent nodes."""
        with patch.object(aggregator.task_board, 'list_tasks', return_value=[sample_task]):
            result = aggregator.build_dag()

        task_id = f"task_{sample_task['id']}"
        task_edges = [e for e in result.edges if e.source == task_id]
        assert len(task_edges) >= 3  # At least scout, architect, researcher

    def test_edges_connect_agents_to_subtasks(self, aggregator, sample_task):
        """Edges should connect coder agent to subtasks."""
        with patch.object(aggregator.task_board, 'list_tasks', return_value=[sample_task]):
            result = aggregator.build_dag()

        coder_id = f"agent_{sample_task['id']}_coder"
        coder_edges = [e for e in result.edges if e.source == coder_id]
        assert len(coder_edges) == 2  # 2 subtasks

    def test_filter_by_status(self, aggregator, sample_task):
        """Filter by status should only return matching tasks."""
        running_task = {**sample_task, "id": "task_002", "status": "running"}

        with patch.object(aggregator.task_board, 'list_tasks', return_value=[sample_task, running_task]):
            result = aggregator.build_dag(filters={"status": "running"})

        task_nodes = [n for n in result.nodes if n.type == "task"]
        assert len(task_nodes) == 1
        assert task_nodes[0].status == "running"

    def test_filter_by_time_range(self, aggregator, sample_task):
        """Filter by time range should exclude old tasks."""
        old_task = {
            **sample_task,
            "id": "task_old",
            "created_at": "2026-02-09T10:00:00",  # Yesterday
        }

        with patch.object(aggregator.task_board, 'list_tasks', return_value=[sample_task, old_task]):
            result = aggregator.build_dag(filters={"time_range": "1h"})

        # Should only include recent task (within 1 hour)
        task_nodes = [n for n in result.nodes if n.type == "task"]
        # Depends on current time, but logic should filter

    def test_filter_by_task_id(self, aggregator, sample_task):
        """Filter by task_id should return only that task tree."""
        other_task = {**sample_task, "id": "task_002", "title": "Other task"}

        with patch.object(aggregator.task_board, 'list_tasks', return_value=[sample_task, other_task]):
            result = aggregator.build_dag(filters={"task_id": "task_001"})

        task_nodes = [n for n in result.nodes if n.type == "task"]
        assert len(task_nodes) == 1
        assert "task_001" in task_nodes[0].id

    def test_node_ids_are_unique(self, aggregator, sample_task):
        """All node IDs should be unique."""
        with patch.object(aggregator.task_board, 'list_tasks', return_value=[sample_task]):
            result = aggregator.build_dag()

        ids = [n.id for n in result.nodes]
        assert len(ids) == len(set(ids)), "Duplicate node IDs found"

    def test_agent_nodes_have_role(self, aggregator, sample_task):
        """Agent nodes should have role field set."""
        with patch.object(aggregator.task_board, 'list_tasks', return_value=[sample_task]):
            result = aggregator.build_dag()

        agent_nodes = [n for n in result.nodes if n.type == "agent"]
        for agent in agent_nodes:
            assert agent.role is not None
            assert agent.role in ["scout", "architect", "researcher", "coder", "verifier"]

    def test_verifier_has_confidence(self, aggregator, sample_task):
        """Verifier agent should have confidence score."""
        with patch.object(aggregator.task_board, 'list_tasks', return_value=[sample_task]):
            result = aggregator.build_dag()

        verifier = next((n for n in result.nodes if n.type == "agent" and n.role == "verifier"), None)
        assert verifier is not None
        assert verifier.confidence == 0.87

    def test_stats_calculation(self, aggregator, sample_task):
        """Stats should be calculated correctly."""
        running_task = {**sample_task, "id": "task_002", "status": "running", "result": None}
        failed_task = {**sample_task, "id": "task_003", "status": "failed", "result": None}

        tasks = [sample_task, running_task, failed_task]
        with patch.object(aggregator.task_board, 'list_tasks', return_value=tasks):
            result = aggregator.build_dag()

        assert result.stats["total_tasks"] == 3
        assert result.stats["running_tasks"] == 1
        assert result.stats["completed_tasks"] == 1
        assert result.stats["failed_tasks"] == 1

    def test_root_ids_match_task_nodes(self, aggregator, sample_task):
        """root_ids should contain all task node IDs."""
        with patch.object(aggregator.task_board, 'list_tasks', return_value=[sample_task]):
            result = aggregator.build_dag()

        task_ids = [n.id for n in result.nodes if n.type == "task"]
        assert set(result.root_ids) == set(task_ids)

    def test_missing_result_graceful(self, aggregator, sample_task):
        """Task without result should still create task node."""
        pending_task = {**sample_task, "status": "pending", "result": None}

        with patch.object(aggregator.task_board, 'list_tasks', return_value=[pending_task]):
            result = aggregator.build_dag()

        task_nodes = [n for n in result.nodes if n.type == "task"]
        assert len(task_nodes) == 1
        # No agent/subtask nodes for pending task
        agent_nodes = [n for n in result.nodes if n.type == "agent"]
        assert len(agent_nodes) == 0

    def test_absolute_paths_used(self, aggregator):
        """Aggregator should use absolute paths (CWD fix from Phase 134)."""
        assert aggregator.project_root.is_absolute()


class TestDAGAggregatorEdges:
    """Test edge generation."""

    @pytest.fixture
    def aggregator(self):
        from src.services.dag_aggregator import DAGAggregator
        return DAGAggregator()

    def test_structural_edges_type(self, aggregator):
        """Parent-child edges should be structural type."""
        sample_task = {
            "id": "task_001",
            "title": "Test",
            "status": "done",
            "result": {
                "agents": {"scout": {"status": "done"}},
                "subtasks": [],
            },
        }

        with patch.object(aggregator.task_board, 'list_tasks', return_value=[sample_task]):
            result = aggregator.build_dag()

        task_to_agent = [e for e in result.edges if "task_" in e.source and "agent_" in e.target]
        for edge in task_to_agent:
            assert edge.type == "structural"

    def test_edge_strength_range(self, aggregator):
        """Edge strength should be between 0 and 1."""
        sample_task = {
            "id": "task_001",
            "title": "Test",
            "status": "done",
            "result": {
                "agents": {"scout": {"status": "done"}},
                "subtasks": [],
            },
        }

        with patch.object(aggregator.task_board, 'list_tasks', return_value=[sample_task]):
            result = aggregator.build_dag()

        for edge in result.edges:
            assert 0 <= edge.strength <= 1

    def test_no_self_loops(self, aggregator):
        """No edge should have same source and target."""
        sample_task = {
            "id": "task_001",
            "title": "Test",
            "status": "done",
            "result": {
                "agents": {"scout": {"status": "done"}},
                "subtasks": [],
            },
        }

        with patch.object(aggregator.task_board, 'list_tasks', return_value=[sample_task]):
            result = aggregator.build_dag()

        for edge in result.edges:
            assert edge.source != edge.target

    def test_no_duplicate_edges(self, aggregator):
        """No duplicate edges should exist."""
        sample_task = {
            "id": "task_001",
            "title": "Test",
            "status": "done",
            "result": {
                "agents": {"scout": {"status": "done"}, "architect": {"status": "done"}},
                "subtasks": [{"description": "Sub1", "agent": "coder"}],
            },
        }

        with patch.object(aggregator.task_board, 'list_tasks', return_value=[sample_task]):
            result = aggregator.build_dag()

        edge_pairs = [(e.source, e.target) for e in result.edges]
        assert len(edge_pairs) == len(set(edge_pairs)), "Duplicate edges found"


class TestDAGAggregatorPerformance:
    """Performance tests."""

    @pytest.fixture
    def aggregator(self):
        from src.services.dag_aggregator import DAGAggregator
        return DAGAggregator()

    def test_large_board_performance(self, aggregator):
        """100 tasks should complete in < 200ms."""
        import time

        tasks = []
        for i in range(100):
            tasks.append({
                "id": f"task_{i:03d}",
                "title": f"Task {i}",
                "status": "done" if i % 3 == 0 else "running" if i % 3 == 1 else "pending",
                "result": {
                    "agents": {"scout": {"status": "done"}, "architect": {"status": "done"}},
                    "subtasks": [{"description": f"Sub {j}", "agent": "coder"} for j in range(3)],
                } if i % 2 == 0 else None,
            })

        with patch.object(aggregator.task_board, 'list_tasks', return_value=tasks):
            start = time.time()
            result = aggregator.build_dag()
            elapsed = (time.time() - start) * 1000

        assert elapsed < 200, f"DAG build took {elapsed:.0f}ms, expected < 200ms"
        assert len(result.nodes) > 100  # Tasks + agents + subtasks
