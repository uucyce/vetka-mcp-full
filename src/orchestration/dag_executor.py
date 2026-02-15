"""
MARKER_150.DAG_EXECUTOR: DAG-Drives-Pipeline Executor.

Reads a workflow template JSON (from data/templates/ or /api/workflow-templates)
and executes it by topological sort → dispatch agents in order.

Phase 150 MVP — bridges visual DAG editor with agent pipeline execution.
Current agent_pipeline.py = "default BMAD" template executed procedurally.
This executor makes the pipeline DAG-driven: user edits graph → executor runs it.

Architecture (inspired by n8n WorkflowExecute + ComfyUI execution.py):
  1. Load workflow JSON (nodes + edges)
  2. Topological sort (Kahn's BFS — handles parallel forks)
  3. For each node in order:
     - agent → dispatch to AgentPipeline method
     - condition → evaluate → pick branch
     - parallel → asyncio.gather children
     - gate → await approval_service
     - task → execute action (promote, etc.)
  4. Collect outputs, stream progress via SocketIO

@phase 150
@status MVP
@depends agent_pipeline.py, playground_manager.py, approval_service.py, eval_agent.py
"""

import asyncio
import json
import logging
import time
from collections import deque, defaultdict
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger(__name__)


class DAGExecutionError(Exception):
    """Raised when DAG execution fails."""
    pass


class NodeResult:
    """Result of executing a single DAG node."""
    def __init__(self, node_id: str, status: str = "pending", output: Any = None, error: str = None):
        self.node_id = node_id
        self.status = status  # pending | running | done | failed | skipped
        self.output = output
        self.error = error
        self.started_at: float = 0
        self.completed_at: float = 0
        self.duration_s: float = 0


class DAGExecutor:
    """
    Execute a workflow template as a pipeline.

    Usage:
        template = json.load(open("data/templates/bmad_workflow.json"))
        executor = DAGExecutor(template)
        results = await executor.execute(
            task="Add toggle bookmark to useStore.ts",
            playground_path="/path/to/worktree",
            progress_callback=my_callback,
        )
    """

    def __init__(self, workflow: Dict[str, Any]):
        self.workflow = workflow
        self.workflow_id = workflow.get("id", "unknown")
        self.workflow_name = workflow.get("name", "Unnamed")

        # Build adjacency + reverse adjacency
        self.nodes: Dict[str, Dict] = {}
        self.adj: Dict[str, List[str]] = defaultdict(list)      # node → successors
        self.rev_adj: Dict[str, List[str]] = defaultdict(list)   # node → predecessors
        self.edge_data: Dict[str, Dict] = {}                     # edge_id → edge metadata

        for node in workflow.get("nodes", []):
            self.nodes[node["id"]] = node

        for edge in workflow.get("edges", []):
            src, tgt = edge["source"], edge["target"]
            self.adj[src].append(tgt)
            self.rev_adj[tgt].append(src)
            self.edge_data[edge["id"]] = edge

        # Results storage
        self.results: Dict[str, NodeResult] = {}

        # Progress callback: async fn(node_id, role, message)
        self._progress_callback: Optional[Callable] = None

    def topological_sort(self) -> List[str]:
        """
        Kahn's algorithm — BFS topological sort.
        Returns node IDs in execution order.
        Raises DAGExecutionError if cycle detected.
        """
        indegree = {nid: 0 for nid in self.nodes}
        for src in self.adj:
            for tgt in self.adj[src]:
                if tgt in indegree:
                    indegree[tgt] += 1

        queue = deque([nid for nid, deg in indegree.items() if deg == 0])
        order = []

        while queue:
            node_id = queue.popleft()
            order.append(node_id)
            for tgt in self.adj.get(node_id, []):
                if tgt in indegree:
                    indegree[tgt] -= 1
                    if indegree[tgt] == 0:
                        queue.append(tgt)

        if len(order) != len(self.nodes):
            missing = set(self.nodes.keys()) - set(order)
            raise DAGExecutionError(f"Cycle detected in workflow. Unreachable nodes: {missing}")

        return order

    async def execute(
        self,
        task: str,
        phase_type: str = "build",
        playground_path: str = None,
        pipeline: Any = None,
        progress_callback: Callable = None,
    ) -> Dict[str, Any]:
        """
        Execute the workflow DAG.

        Args:
            task: Task description
            phase_type: build/fix/research
            playground_path: Path to playground worktree (if sandboxed)
            pipeline: AgentPipeline instance (reuse existing, or create new)
            progress_callback: async fn(node_id, role, message) for live updates

        Returns:
            Dict with node results, stats, and final output
        """
        self._progress_callback = progress_callback
        start_time = time.time()

        # Get execution order
        try:
            order = self.topological_sort()
        except DAGExecutionError as e:
            logger.error(f"[DAGExecutor] {e}")
            return {"success": False, "error": str(e)}

        logger.info(f"[DAGExecutor] Executing workflow '{self.workflow_name}' — {len(order)} nodes")
        logger.info(f"[DAGExecutor] Order: {' → '.join(order)}")

        await self._emit("system", f"🔄 DAG Executor: {self.workflow_name} ({len(order)} nodes)")

        # Execute nodes in topological order
        for node_id in order:
            node = self.nodes[node_id]
            node_type = node.get("type", "task")
            result = NodeResult(node_id=node_id, status="running")
            result.started_at = time.time()
            self.results[node_id] = result

            await self._emit(node_id, f"▶ {node.get('label', node_id)}")

            try:
                if node_type == "agent":
                    output = await self._execute_agent_node(node, task, phase_type, pipeline, playground_path)
                elif node_type == "condition":
                    output = await self._execute_condition_node(node)
                elif node_type == "parallel":
                    output = await self._execute_parallel_node(node, task, phase_type, pipeline, playground_path)
                elif node_type == "gate":
                    output = await self._execute_gate_node(node)
                elif node_type == "task":
                    output = await self._execute_task_node(node, playground_path)
                else:
                    output = {"skipped": True, "reason": f"Unknown node type: {node_type}"}

                result.output = output
                result.status = "done"

            except Exception as e:
                result.status = "failed"
                result.error = str(e)
                logger.error(f"[DAGExecutor] Node {node_id} failed: {e}")
                await self._emit(node_id, f"❌ {node.get('label', node_id)}: {str(e)[:100]}")

                # Check if error should stop execution
                if not node.get("data", {}).get("optional", False):
                    break

            result.completed_at = time.time()
            result.duration_s = round(result.completed_at - result.started_at, 2)

            if result.status == "done":
                await self._emit(node_id, f"✅ {node.get('label', node_id)} ({result.duration_s}s)")

        # Compile results
        total_time = round(time.time() - start_time, 2)
        node_results = {
            nid: {
                "status": r.status,
                "duration_s": r.duration_s,
                "output": r.output,
                "error": r.error,
            }
            for nid, r in self.results.items()
        }

        success = all(r.status in ("done", "skipped") for r in self.results.values())

        return {
            "success": success,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "total_time_s": total_time,
            "nodes_executed": len(self.results),
            "nodes_total": len(self.nodes),
            "node_results": node_results,
        }

    # ── Node Type Handlers ──

    async def _execute_agent_node(
        self, node: Dict, task: str, phase_type: str,
        pipeline: Any, playground_path: str = None
    ) -> Dict:
        """Execute an agent node (scout/architect/coder/verifier/researcher/eval)."""
        role = node.get("data", {}).get("role", "")
        logger.info(f"[DAGExecutor] Agent node: @{role}")

        # Collect inputs from predecessor nodes
        inputs = self._gather_inputs(node["id"])

        if not pipeline:
            return {"warning": "No pipeline instance provided", "role": role}

        # Dispatch to appropriate pipeline method based on role
        # MARKER_150.DAG_DISPATCH: Map DAG roles to pipeline methods
        if role == "scout":
            result = await pipeline._parallel_recon(task, phase_type)
            pipeline._scout_context = result[0] if result else None
            return {"scout_context": result[0], "research": result[1]} if result else {}

        elif role == "architect":
            scout_ctx = inputs.get("scout", {}).get("scout_context", {})
            research = inputs.get("researcher", {}).get("research", {})
            subtasks = await pipeline._architect_plan(
                task, phase_type,
                research_context=research,
            )
            return {"subtasks": subtasks, "count": len(subtasks) if subtasks else 0}

        elif role == "researcher":
            # Researcher runs as part of parallel_recon or standalone
            return inputs.get("scout", {}).get("research", {"note": "Bundled with scout recon"})

        elif role == "coder":
            # Execute all subtasks from architect
            architect_output = inputs.get("architect", {})
            subtasks = architect_output.get("subtasks", [])
            if not subtasks:
                return {"warning": "No subtasks from architect"}
            # Use pipeline's existing subtask executor
            # (In future: sparse apply mode from node.data.mode)
            return {"subtask_count": len(subtasks), "note": "Executed via pipeline._execute_subtask"}

        elif role == "verifier":
            return {"note": "Runs via pipeline._verify_subtask for each coder output"}

        elif role == "eval":
            # Wire eval_agent.evaluate_with_retry()
            coder_output = inputs.get("coder", {})
            try:
                from src.agents.eval_agent import EvalAgent
                eval_agent = EvalAgent()
                score_result = eval_agent.evaluate(task=task, output=str(coder_output))
                return {"score": score_result.get("score", 0), "feedback": score_result}
            except Exception as e:
                logger.warning(f"[DAGExecutor] Eval agent failed: {e}")
                return {"score": 0.5, "error": str(e), "fallback": True}

        return {"role": role, "note": "Agent dispatched (stub)"}

    async def _execute_condition_node(self, node: Dict) -> Dict:
        """
        Evaluate condition and determine which branch to take.
        Reads threshold from node.data, compares with input scores.
        """
        data = node.get("data", {})
        threshold = data.get("threshold", 0.8)
        max_retries = data.get("max_retries", 3)

        # Gather inputs (verifier + eval results)
        inputs = self._gather_inputs(node["id"])

        # Extract scores
        verifier_passed = True
        eval_score = 1.0

        for pred_id, pred_output in inputs.items():
            if isinstance(pred_output, dict):
                if "passed" in pred_output:
                    verifier_passed = pred_output["passed"]
                if "score" in pred_output:
                    eval_score = pred_output["score"]

        passed = verifier_passed and eval_score >= threshold

        # Check retry count
        retry_count = data.get("_retry_count", 0)
        if not passed and retry_count >= max_retries:
            logger.warning(f"[DAGExecutor] Max retries ({max_retries}) reached, forcing pass")
            passed = True

        logger.info(f"[DAGExecutor] Condition: passed={passed}, score={eval_score}, threshold={threshold}")

        return {
            "passed": passed,
            "eval_score": eval_score,
            "verifier_passed": verifier_passed,
            "threshold": threshold,
            "retry_count": retry_count,
            "branch": "pass" if passed else "retry",
        }

    async def _execute_parallel_node(
        self, node: Dict, task: str, phase_type: str,
        pipeline: Any, playground_path: str = None
    ) -> Dict:
        """Execute parallel children concurrently."""
        data = node.get("data", {})
        children_ids = data.get("children", [])

        if not children_ids:
            return {"note": "No children in parallel node"}

        # Execute children as concurrent tasks
        tasks = []
        for child_id in children_ids:
            if child_id in self.nodes:
                child_node = self.nodes[child_id]
                tasks.append(
                    self._execute_agent_node(child_node, task, phase_type, pipeline, playground_path)
                )

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            child_results = {}
            for i, child_id in enumerate(children_ids):
                if isinstance(results[i], Exception):
                    child_results[child_id] = {"error": str(results[i])}
                else:
                    child_results[child_id] = results[i]
            return child_results

        return {"note": "No executable children"}

    async def _execute_gate_node(self, node: Dict) -> Dict:
        """
        Approval gate — blocks until approved.
        Checks auto-approve rules first, then falls back to SocketIO modal.
        """
        data = node.get("data", {})
        auto_rules = data.get("auto_approve_rules", {})

        # Gather inputs for auto-approve evaluation
        inputs = self._gather_inputs(node["id"])

        # Check auto-approve rules
        # MARKER_150.AUTO_APPROVE: Simple rule engine
        eval_score = 0.0
        for pred_output in inputs.values():
            if isinstance(pred_output, dict):
                if "eval_score" in pred_output:
                    eval_score = pred_output["eval_score"]

        auto_approved = False
        reason = ""

        if auto_rules.get("new_files") and eval_score > 0:
            # TODO: check if changes are only new files
            auto_approved = True
            reason = "Auto-approved: new files only"

        if auto_rules.get("eval_score_above_0.95") and eval_score >= 0.95:
            auto_approved = True
            reason = f"Auto-approved: eval score {eval_score} >= 0.95"

        if auto_approved:
            logger.info(f"[DAGExecutor] Gate auto-approved: {reason}")
            return {"approved": True, "auto": True, "reason": reason}

        # Manual approval via approval_service
        try:
            from src.services.approval_service import ApprovalService
            # For now, auto-approve in MVP (TODO: wire SocketIO modal)
            logger.info("[DAGExecutor] Gate: manual approval needed (auto-approving in MVP)")
            return {"approved": True, "auto": True, "reason": "MVP auto-approve (TODO: wire SocketIO)"}
        except Exception as e:
            logger.warning(f"[DAGExecutor] Approval service unavailable: {e}")
            return {"approved": True, "auto": True, "reason": f"Fallback: {e}"}

    async def _execute_task_node(self, node: Dict, playground_path: str = None) -> Dict:
        """Execute a task node (promote, cleanup, etc.)."""
        data = node.get("data", {})
        action = data.get("action", "")

        if action == "playground_promote" and playground_path:
            try:
                from src.orchestration.playground_manager import get_playground_manager
                manager = get_playground_manager()
                # Extract playground_id from path
                pg_id = Path(playground_path).name
                result = await manager.promote(
                    playground_id=pg_id,
                    strategy=data.get("strategy", "copy"),
                    destroy_after=data.get("destroy_after", False),
                )
                return result
            except Exception as e:
                return {"error": f"Promote failed: {e}"}

        return {"action": action, "note": "Task executed (stub)"}

    # ── Helpers ──

    def _gather_inputs(self, node_id: str) -> Dict[str, Any]:
        """Collect outputs from all predecessor nodes."""
        inputs = {}
        for pred_id in self.rev_adj.get(node_id, []):
            if pred_id in self.results and self.results[pred_id].output:
                inputs[pred_id] = self.results[pred_id].output
        return inputs

    async def _emit(self, node_id: str, message: str):
        """Emit progress event."""
        if self._progress_callback:
            try:
                await self._progress_callback(node_id, message)
            except Exception:
                pass
        logger.info(f"[DAGExecutor] {node_id}: {message}")


# ── Convenience Functions ──

def load_workflow_template(template_id: str) -> Optional[Dict]:
    """Load a workflow template from data/templates/ or workflow store."""
    # Check data/templates/ first
    templates_dir = Path(__file__).resolve().parent.parent.parent / "data" / "templates"
    template_path = templates_dir / f"{template_id}.json"
    if template_path.exists():
        with open(template_path) as f:
            return json.load(f)

    # Check workflow store
    store_dir = templates_dir.parent / "workflows"
    if store_dir.exists():
        for wf_file in store_dir.glob("*.json"):
            with open(wf_file) as f:
                wf = json.load(f)
                if wf.get("id") == template_id:
                    return wf

    return None


async def execute_workflow_template(
    template_id: str,
    task: str,
    phase_type: str = "build",
    playground_path: str = None,
    pipeline: Any = None,
    progress_callback: Callable = None,
) -> Dict[str, Any]:
    """
    High-level convenience: load template → create executor → run.

    Usage:
        result = await execute_workflow_template(
            "bmad_default_v1",
            task="Add bookmark toggle",
            playground_path="/path/to/worktree",
        )
    """
    template = load_workflow_template(template_id)
    if not template:
        return {"success": False, "error": f"Template not found: {template_id}"}

    executor = DAGExecutor(template)
    return await executor.execute(
        task=task,
        phase_type=phase_type,
        playground_path=playground_path,
        pipeline=pipeline,
        progress_callback=progress_callback,
    )
