"""
Tests for Phase 150.3: DAG Executor wired to real pipeline methods.

Tests:
- Feedback edge exclusion from topological sort
- Skip logic for retry nodes and parallel children
- Coder node executes real subtasks
- Verifier node runs real verification
- Condition node internal retry loop
- Parallel node propagates inputs to children
- Full DAG execution flow (mocked pipeline)

@phase 150.3
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field
from typing import Optional, Dict, List

from src.orchestration.dag_executor import (
    DAGExecutor,
    DAGExecutionError,
    NodeResult,
    load_workflow_template,
)


# ── Fixtures ──

@dataclass
class MockSubtask:
    """Lightweight Subtask mock matching agent_pipeline.Subtask fields."""
    description: str
    needs_research: bool = False
    context: Optional[Dict] = None
    result: Optional[str] = None
    status: str = "pending"
    retry_count: int = 0
    verifier_feedback: Optional[Dict] = None
    escalated: bool = False


def _load_bmad_template():
    """Load the real BMAD workflow template."""
    return load_workflow_template("bmad_workflow")


def _make_mock_pipeline(subtasks=None):
    """Create a mock AgentPipeline with controllable methods."""
    pipeline = MagicMock()
    pipeline._scout_context = None
    pipeline.playground_root = None

    # Scout + Researcher (parallel recon)
    pipeline._parallel_recon = AsyncMock(return_value=(
        {"relevant_files": ["src/store.ts"], "marker_map": []},
        {"web_sources": [], "api_patterns": []}
    ))

    # Architect
    if subtasks is None:
        subtasks = [
            MockSubtask(description="Add toggleBookmark function to useStore.ts"),
            MockSubtask(description="Add bookmark icon to ChatItem component"),
        ]
    pipeline._architect_plan = AsyncMock(return_value=subtasks)

    # Coder (execute_subtask)
    async def mock_execute_subtask(subtask, phase_type):
        code = f"// Code for: {subtask.description}\nfunction impl() {{ return true; }}"
        return code
    pipeline._execute_subtask = AsyncMock(side_effect=mock_execute_subtask)

    # Verifier
    pipeline._verify_subtask = AsyncMock(return_value={
        "passed": True, "confidence": 0.85, "issues": [], "severity": "minor"
    })

    # Retry coder
    async def mock_retry_coder(subtask, verifier_result, phase_type, previous_result=""):
        subtask.retry_count += 1
        return f"// FIXED: {subtask.description}\nfunction fixedImpl() {{ return true; }}"
    pipeline._retry_coder = AsyncMock(side_effect=mock_retry_coder)

    # LLM tracking
    pipeline._llm_calls = 0
    pipeline._tokens_in = 0
    pipeline._tokens_out = 0

    return pipeline, subtasks


# ── Test: Feedback Edges ──

class TestFeedbackEdges:
    """Test that feedback edges are excluded from topological sort."""

    def test_feedback_edge_excluded_from_adjacency(self):
        """Feedback edges should not appear in adj/rev_adj."""
        template = _load_bmad_template()
        executor = DAGExecutor(template)

        assert len(executor.feedback_edges) == 1
        fe = executor.feedback_edges[0]
        assert fe["source"] == "retry_coder"
        assert fe["target"] == "measure"

        # retry_coder → measure should NOT be in adj
        assert "measure" not in executor.adj.get("retry_coder", [])
        # measure should NOT have retry_coder in rev_adj
        assert "retry_coder" not in executor.rev_adj.get("measure", [])

    def test_topo_sort_succeeds_with_feedback_edges(self):
        """Topological sort should succeed (no cycle) when feedback edges excluded."""
        template = _load_bmad_template()
        executor = DAGExecutor(template)
        order = executor.topological_sort()

        assert len(order) == 11  # All nodes in order
        # scout before architect before coder
        assert order.index("scout") < order.index("architect")
        assert order.index("architect") < order.index("coder")
        assert order.index("coder") < order.index("measure")

    def test_cycle_detection_without_feedback_exclusion(self):
        """If we DON'T exclude feedback edges, cycle should be detected."""
        template = _load_bmad_template()
        # Manually add feedback edge back as structural
        template_copy = json.loads(json.dumps(template))
        for edge in template_copy["edges"]:
            if edge["type"] == "feedback":
                edge["type"] = "structural"  # Make it structural → will create cycle

        executor = DAGExecutor(template_copy)
        with pytest.raises(DAGExecutionError, match="Cycle detected"):
            executor.topological_sort()


# ── Test: Skip Logic ──

class TestSkipLogic:
    """Test that retry nodes and parallel children are skipped in main loop."""

    def test_skip_set_includes_retry_and_parallel_children(self):
        """retry_coder, verifier, eval_agent should be in skip set."""
        template = _load_bmad_template()
        executor = DAGExecutor(template)

        # Build skip set same way as execute() method
        skip = set()
        for fe in executor.feedback_edges:
            skip.add(fe["source"])
        for nid, node in executor.nodes.items():
            if node.get("type") == "parallel":
                for cid in node.get("data", {}).get("children", []):
                    skip.add(cid)

        assert "retry_coder" in skip
        assert "verifier" in skip
        assert "eval_agent" in skip
        assert "coder" not in skip  # Regular coder should NOT be skipped
        assert "measure" not in skip  # Parallel parent should NOT be skipped

    def test_main_loop_executes_8_nodes(self):
        """Main loop should execute 8 of 11 nodes."""
        template = _load_bmad_template()
        executor = DAGExecutor(template)
        order = executor.topological_sort()

        skip = set()
        for fe in executor.feedback_edges:
            skip.add(fe["source"])
        for nid, node in executor.nodes.items():
            if node.get("type") == "parallel":
                for cid in node.get("data", {}).get("children", []):
                    skip.add(cid)

        executed = [n for n in order if n not in skip]
        assert len(executed) == 8
        assert executed == [
            "scout", "architect", "researcher", "coder",
            "measure", "adjust", "approval_gate", "deploy"
        ]


# ── Test: Coder Node ──

class TestCoderNode:
    """Test coder node executes real subtasks."""

    @pytest.mark.asyncio
    async def test_coder_executes_all_subtasks(self):
        """Coder node should call pipeline._execute_subtask for each subtask."""
        template = _load_bmad_template()
        executor = DAGExecutor(template)
        pipeline, subtasks = _make_mock_pipeline()

        coder_node = executor.nodes["coder"]
        inputs = {
            "architect": {"subtasks": subtasks, "count": 2}
        }
        result = await executor._execute_coder(coder_node, inputs, "build", pipeline)

        assert result["subtask_count"] == 2
        assert result["done_count"] == 2
        assert result["failed_count"] == 0
        assert pipeline._execute_subtask.call_count == 2
        # Check subtask results are stored
        assert subtasks[0].result is not None
        assert subtasks[0].status == "done"

    @pytest.mark.asyncio
    async def test_coder_handles_subtask_failure(self):
        """Coder should mark failed subtasks and continue."""
        template = _load_bmad_template()
        executor = DAGExecutor(template)
        pipeline, subtasks = _make_mock_pipeline()

        # Make second subtask fail
        call_count = 0
        async def fail_on_second(subtask, phase_type):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise ValueError("Model returned empty response")
            return f"// Code for: {subtask.description}"
        pipeline._execute_subtask = AsyncMock(side_effect=fail_on_second)

        coder_node = executor.nodes["coder"]
        inputs = {"architect": {"subtasks": subtasks, "count": 2}}
        result = await executor._execute_coder(coder_node, inputs, "build", pipeline)

        assert result["done_count"] == 1
        assert result["failed_count"] == 1
        assert subtasks[0].status == "done"
        assert subtasks[1].status == "failed"

    @pytest.mark.asyncio
    async def test_coder_returns_warning_when_no_subtasks(self):
        """Coder should return warning if no subtasks from architect."""
        template = _load_bmad_template()
        executor = DAGExecutor(template)
        pipeline, _ = _make_mock_pipeline()

        coder_node = executor.nodes["coder"]
        inputs = {"architect": {"subtasks": [], "count": 0}}
        result = await executor._execute_coder(coder_node, inputs, "build", pipeline)

        assert "warning" in result
        assert pipeline._execute_subtask.call_count == 0


# ── Test: Verifier Node ──

class TestVerifierNode:
    """Test verifier node runs real verification."""

    @pytest.mark.asyncio
    async def test_verifier_checks_all_subtasks(self):
        """Verifier should call pipeline._verify_subtask for each subtask with result."""
        template = _load_bmad_template()
        executor = DAGExecutor(template)
        pipeline, subtasks = _make_mock_pipeline()

        # Set coder results
        subtasks[0].result = "function toggleBookmark() { ... }"
        subtasks[1].result = "function BookmarkIcon() { ... }"

        verifier_node = executor.nodes["verifier"]
        inputs = {
            "coder": {
                "subtasks": subtasks,
                "results": [{"result": s.result, "status": "done"} for s in subtasks]
            }
        }
        result = await executor._execute_verifier(verifier_node, inputs, "build", pipeline)

        assert result["passed"] is True
        assert result["total_checked"] == 2
        assert len(result["verifications"]) == 2
        assert pipeline._verify_subtask.call_count == 2

    @pytest.mark.asyncio
    async def test_verifier_fails_on_empty_result(self):
        """Subtasks with no coder output should fail verification."""
        template = _load_bmad_template()
        executor = DAGExecutor(template)
        pipeline, subtasks = _make_mock_pipeline()

        subtasks[0].result = "function impl() { ... }"
        subtasks[1].result = ""  # Empty result

        verifier_node = executor.nodes["verifier"]
        inputs = {"coder": {"subtasks": subtasks, "results": []}}
        result = await executor._execute_verifier(verifier_node, inputs, "build", pipeline)

        assert result["passed"] is False
        # Only first subtask should be verified (second has no result)
        assert pipeline._verify_subtask.call_count == 1

    @pytest.mark.asyncio
    async def test_verifier_aggregates_confidence(self):
        """Average confidence should be computed from all subtask verifications."""
        template = _load_bmad_template()
        executor = DAGExecutor(template)
        pipeline, subtasks = _make_mock_pipeline()

        subtasks[0].result = "code A"
        subtasks[1].result = "code B"

        # Different confidences
        call_count = 0
        async def varying_confidence(subtask, result, phase):
            nonlocal call_count
            call_count += 1
            conf = 0.9 if call_count == 1 else 0.7
            return {"passed": True, "confidence": conf, "issues": [], "severity": "minor"}
        pipeline._verify_subtask = AsyncMock(side_effect=varying_confidence)

        verifier_node = executor.nodes["verifier"]
        inputs = {"coder": {"subtasks": subtasks, "results": []}}
        result = await executor._execute_verifier(verifier_node, inputs, "build", pipeline)

        assert result["confidence"] == 0.8  # (0.9 + 0.7) / 2


# ── Test: Condition Node (Retry Loop) ──

class TestConditionNode:
    """Test condition node with internal retry loop."""

    @pytest.mark.asyncio
    async def test_condition_passes_on_good_scores(self):
        """Condition should pass when verifier_passed=True and score >= threshold."""
        template = _load_bmad_template()
        executor = DAGExecutor(template)
        pipeline, subtasks = _make_mock_pipeline()

        # Set up predecessor results (verifier + eval are direct predecessors of adjust)
        executor.results["verifier"] = NodeResult(
            "verifier", "done",
            {"passed": True, "confidence": 0.9, "verifications": [], "subtasks": subtasks}
        )
        executor.results["eval_agent"] = NodeResult(
            "eval_agent", "done",
            {"score": 0.85, "feedback": {}}
        )

        adjust_node = executor.nodes["adjust"]
        result = await executor._execute_condition_node(
            adjust_node, "Add bookmark", "build", pipeline
        )

        assert result["passed"] is True
        assert result["branch"] == "pass"
        assert result["retry_count"] == 0

    @pytest.mark.asyncio
    async def test_condition_retries_on_failure(self):
        """Condition should retry when verifier fails, then pass on retry."""
        template = _load_bmad_template()
        executor = DAGExecutor(template)
        pipeline, subtasks = _make_mock_pipeline()

        # Give subtasks results
        subtasks[0].result = "// bad code"
        subtasks[1].result = "// also bad"

        # Verifier says subtask 0 failed
        # Note: adjust's predecessors are "verifier" and "eval_agent" (direct edges)
        failed_verifications = [
            {"index": 0, "passed": False, "confidence": 0.4, "issues": ["No real code"], "severity": "minor"},
            {"index": 1, "passed": True, "confidence": 0.8, "issues": [], "severity": "minor"},
        ]

        executor.results["verifier"] = NodeResult(
            "verifier", "done",
            {
                "passed": False, "confidence": 0.6,
                "verifications": failed_verifications,
                "subtasks": subtasks, "total_checked": 2
            }
        )
        executor.results["eval_agent"] = NodeResult(
            "eval_agent", "done",
            {"score": 0.5, "feedback": {}}
        )

        # After retry, verifier passes everything
        pipeline._verify_subtask = AsyncMock(return_value={
            "passed": True, "confidence": 0.85, "issues": [], "severity": "minor"
        })

        adjust_node = executor.nodes["adjust"]
        result = await executor._execute_condition_node(
            adjust_node, "Add bookmark", "build", pipeline
        )

        assert result["passed"] is True
        assert result["retry_count"] >= 1
        # retry_coder should have been called (only for subtask 0 which failed)
        assert pipeline._retry_coder.call_count >= 1

    @pytest.mark.asyncio
    async def test_condition_forces_pass_after_max_retries(self):
        """Condition should force pass after max_retries."""
        template = _load_bmad_template()
        executor = DAGExecutor(template)
        pipeline, subtasks = _make_mock_pipeline()

        subtasks[0].result = "// bad code"

        # Always fail verification
        pipeline._verify_subtask = AsyncMock(return_value={
            "passed": False, "confidence": 0.3, "issues": ["Still bad"], "severity": "major"
        })

        failed_verifications = [
            {"index": 0, "passed": False, "confidence": 0.3, "issues": ["Bad"], "severity": "major"},
        ]

        # Note: adjust's predecessors are "verifier" and "eval_agent" (direct edges)
        executor.results["verifier"] = NodeResult(
            "verifier", "done",
            {
                "passed": False, "confidence": 0.3,
                "verifications": failed_verifications,
                "subtasks": [subtasks[0]], "total_checked": 1
            }
        )
        executor.results["eval_agent"] = NodeResult(
            "eval_agent", "done",
            {"score": 0.2, "feedback": {}}
        )

        adjust_node = executor.nodes["adjust"]
        # Set max_retries to 2 for faster test
        adjust_node["data"]["max_retries"] = 2

        result = await executor._execute_condition_node(
            adjust_node, "Add bookmark", "build", pipeline
        )

        # Should force pass after max retries
        assert result["passed"] is True
        assert result["retry_count"] == 2
        assert pipeline._retry_coder.call_count == 2


# ── Test: Parallel Node ──

class TestParallelNode:
    """Test parallel node propagates inputs to children."""

    @pytest.mark.asyncio
    async def test_parallel_runs_children_concurrently(self):
        """Parallel node should run verifier + eval concurrently."""
        template = _load_bmad_template()
        executor = DAGExecutor(template)
        pipeline, subtasks = _make_mock_pipeline()

        # Set up coder result (predecessor of measure)
        subtasks[0].result = "function impl() { ... }"
        subtasks[1].result = "function impl2() { ... }"
        executor.results["coder"] = NodeResult(
            "coder", "done",
            {
                "subtask_count": 2, "subtasks": subtasks,
                "results": [
                    {"result": s.result, "status": "done"} for s in subtasks
                ],
                "done_count": 2, "failed_count": 0,
            }
        )

        measure_node = executor.nodes["measure"]
        result = await executor._execute_parallel_node(
            measure_node, "Add bookmark", "build", pipeline
        )

        # Should have results from both children
        assert "verifier" in result or "eval_agent" in result

    @pytest.mark.asyncio
    async def test_parallel_stores_child_results(self):
        """Parallel node should store child results in self.results."""
        template = _load_bmad_template()
        executor = DAGExecutor(template)
        pipeline, subtasks = _make_mock_pipeline()

        subtasks[0].result = "code"
        executor.results["coder"] = NodeResult(
            "coder", "done",
            {"subtask_count": 1, "subtasks": subtasks, "results": [{"result": "code", "status": "done"}],
             "done_count": 1, "failed_count": 0}
        )

        measure_node = executor.nodes["measure"]
        await executor._execute_parallel_node(
            measure_node, "task", "build", pipeline
        )

        # Child results should be stored
        assert "verifier" in executor.results or "eval_agent" in executor.results


# ── Test: Full DAG Execution ──

class TestFullDAGExecution:
    """Test end-to-end DAG execution with mocked pipeline."""

    @pytest.mark.asyncio
    async def test_full_bmad_execution(self):
        """Full BMAD DAG should execute: scout→arch→coder→measure→adjust→gate→deploy."""
        template = _load_bmad_template()
        executor = DAGExecutor(template)
        pipeline, subtasks = _make_mock_pipeline()

        progress_log = []
        async def log_progress(node_id, message):
            progress_log.append((node_id, message))

        result = await executor.execute(
            task="Add toggleBookmark to useStore.ts",
            phase_type="build",
            pipeline=pipeline,
            progress_callback=log_progress,
        )

        assert result["success"] is True
        assert result["nodes_executed"] == 11  # All nodes have results
        # Pipeline methods should have been called
        assert pipeline._parallel_recon.call_count == 1
        assert pipeline._architect_plan.call_count == 1
        assert pipeline._execute_subtask.call_count == 2  # 2 subtasks
        assert pipeline._verify_subtask.call_count >= 2  # At least once per subtask

    @pytest.mark.asyncio
    async def test_dag_without_pipeline(self):
        """DAG should handle missing pipeline gracefully."""
        template = _load_bmad_template()
        executor = DAGExecutor(template)

        result = await executor.execute(
            task="Test task", phase_type="build", pipeline=None
        )

        # Should not crash, but nodes will have warnings
        assert "node_results" in result

    @pytest.mark.asyncio
    async def test_role_to_node_mapping(self):
        """_role_to_node should map roles to node IDs."""
        template = _load_bmad_template()
        executor = DAGExecutor(template)

        assert executor._role_to_node["scout"] == "scout"
        assert executor._role_to_node["architect"] == "architect"
        assert executor._role_to_node["coder"] in ("coder", "retry_coder")
        assert executor._role_to_node["verifier"] == "verifier"
        assert executor._role_to_node["eval"] == "eval_agent"


# ── Test: Template Loading ──

class TestTemplateLoading:
    """Test workflow template loading."""

    def test_load_bmad_template(self):
        """Should load bmad_workflow.json from data/templates/."""
        template = load_workflow_template("bmad_workflow")
        assert template is not None
        assert template["id"] == "bmad_default_v1"
        assert len(template["nodes"]) == 11
        assert len(template["edges"]) == 13

    def test_load_nonexistent_template(self):
        """Should return None for missing template."""
        result = load_workflow_template("nonexistent_template_xyz")
        assert result is None
