# Dragon Gold Brief — Sprint 2A: DAG Execution Engine (Phase 176)

> **Source:** `docs/176_MCC_SPRINT/PHASE_176_ROADMAP.md`
> **Agent:** Dragon Gold (Kimi K2.5 + Grok Fast 4.1 + Qwen3-coder + Qwen3-235b)
> **Sprint:** 2A (parallel with Codex Sprint 2B)
> **Prerequisite:** Sprint 1A complete (MARKER_176.2 Prefetch Wire, MARKER_176.4 TRM Integration)
> **Estimated:** 200 lines — MAJOR FEATURE
> **Marker:** MARKER_176.8

---

## Problem Statement

Users can create/edit workflow DAGs visually (Phase 144 editor), but execution still uses hard-coded sequential pipeline: Scout → Architect → Coder → Verifier. Custom workflows are visual-only, can't execute.

### Current Flow (BROKEN)
```
User creates custom workflow (DAGView editor)
  → Template saved to data/templates/workflows/{key}.json
  → Pipeline IGNORES template, runs fixed sequence
  → Custom workflow is decoration-only
```

### Target Flow (MARKER_176.8)
```
User creates custom workflow
  → Template saved with node topology + edge dependencies
  → Pipeline reads template topology
  → Dispatches agents per DAG order:
    - Sequential: A → B → C (follows edges)
    - Parallel fork: A → [B, C] (no edge between B,C)
    - Join: [B, C] → D (D waits for both)
    - Conditional: if(condition) → branch
  → Each node = agent call with role from template
```

---

## Source References

| File | Content | Lines |
|------|---------|-------|
| `src/orchestration/agent_pipeline.py` | Main pipeline execution | ~600 |
| `data/templates/workflows/*.json` | 10 workflow templates | ~50 each |
| `src/services/architect_prefetch.py` | WorkflowTemplateLibrary | ~300 |
| `client/src/utils/dagLayout.ts` | Edge type definitions | ~200 |
| `docs/175_MCC_APP/SCOUT_MCC_AUDIT_2026-03-11.md` | GAP_8 (line 78-84) |

### Template Structure (existing)
```json
{
  "key": "g3_critic_coder",
  "name": "G3 Critic + Coder",
  "family": "multi_agent",
  "nodes": [
    { "id": "architect", "role": "architect", "type": "agent" },
    { "id": "coder", "role": "coder", "type": "agent" },
    { "id": "critic", "role": "verifier", "type": "agent" },
    { "id": "loop_check", "type": "condition", "condition": "critic.pass" }
  ],
  "edges": [
    { "source": "architect", "target": "coder", "type": "structural" },
    { "source": "coder", "target": "critic", "type": "dataflow" },
    { "source": "critic", "target": "loop_check", "type": "conditional" },
    { "source": "loop_check", "target": "coder", "type": "feedback", "condition": "!pass" }
  ]
}
```

---

## Implementation Plan

### Part 1: Workflow Executor Module (~120 lines)

Create `src/orchestration/workflow_executor.py`:

```python
# MARKER_176.8: DAG-Driven Workflow Executor
"""
Executes workflow templates as DAGs instead of fixed sequential pipelines.
Parses template topology → dispatches agents per node order.

Node types: agent, condition, parallel, loop, transform
Edge types: structural, dataflow, temporal, conditional, parallel_fork, parallel_join, feedback
"""

import asyncio
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from src.services.architect_prefetch import WorkflowTemplateLibrary


class WorkflowExecutor:
    """Execute a workflow template as a directed acyclic graph."""

    def __init__(self, template_key: str, task_data: dict, pipeline_context: dict):
        self.template = WorkflowTemplateLibrary.get_template(template_key)
        if not self.template:
            raise ValueError(f"Template {template_key} not found")
        self.task_data = task_data
        self.context = pipeline_context
        self.node_results: Dict[str, Any] = {}
        self.completed_nodes: Set[str] = set()

    def _build_adjacency(self) -> Dict[str, List[str]]:
        """Build adjacency list from template edges."""
        adj = defaultdict(list)
        for edge in self.template.get("edges", []):
            adj[edge["source"]].append(edge["target"])
        return dict(adj)

    def _get_roots(self) -> List[str]:
        """Find root nodes (no incoming edges)."""
        targets = {e["target"] for e in self.template.get("edges", [])}
        all_nodes = {n["id"] for n in self.template.get("nodes", [])}
        return list(all_nodes - targets)

    def _get_ready_nodes(self) -> List[str]:
        """Find nodes whose all dependencies are satisfied."""
        ready = []
        for node in self.template.get("nodes", []):
            nid = node["id"]
            if nid in self.completed_nodes:
                continue
            # Check all incoming edges satisfied
            deps = [e["source"] for e in self.template.get("edges", [])
                    if e["target"] == nid]
            if all(d in self.completed_nodes for d in deps):
                ready.append(nid)
        return ready

    def _get_node(self, node_id: str) -> Optional[dict]:
        for n in self.template.get("nodes", []):
            if n["id"] == node_id:
                return n
        return None

    async def execute(self, agent_dispatch_fn) -> dict:
        """
        Execute the workflow DAG.

        agent_dispatch_fn(role: str, context: dict) -> result
        Called for each agent node with the appropriate role.
        """
        max_iterations = 50  # Safety limit for loops
        iteration = 0

        while iteration < max_iterations:
            ready = self._get_ready_nodes()
            if not ready:
                break  # All done or deadlock

            # Group parallel nodes (can execute concurrently)
            tasks = []
            for nid in ready:
                node = self._get_node(nid)
                if not node:
                    self.completed_nodes.add(nid)
                    continue

                node_type = node.get("type", "agent")

                if node_type == "agent":
                    tasks.append(self._execute_agent_node(nid, node, agent_dispatch_fn))
                elif node_type == "condition":
                    tasks.append(self._execute_condition_node(nid, node))
                elif node_type == "transform":
                    tasks.append(self._execute_transform_node(nid, node))
                else:
                    # Unknown type — mark complete
                    self.completed_nodes.add(nid)

            # Execute ready nodes in parallel
            if tasks:
                await asyncio.gather(*tasks)

            iteration += 1

        return {
            "completed": list(self.completed_nodes),
            "results": self.node_results,
            "iterations": iteration,
        }

    async def _execute_agent_node(self, nid, node, dispatch_fn):
        """Dispatch an agent node with accumulated context."""
        role = node.get("role", "coder")
        # Gather input from parent nodes
        parent_results = {}
        for edge in self.template.get("edges", []):
            if edge["target"] == nid and edge["source"] in self.node_results:
                parent_results[edge["source"]] = self.node_results[edge["source"]]

        context = {
            **self.context,
            "parent_results": parent_results,
            "node_config": node,
        }
        result = await dispatch_fn(role, context)
        self.node_results[nid] = result
        self.completed_nodes.add(nid)

    async def _execute_condition_node(self, nid, node):
        """Evaluate condition based on parent results."""
        condition = node.get("condition", "true")
        # Simple evaluation: check if parent passed
        parent_id = condition.split(".")[0] if "." in condition else None
        if parent_id and parent_id in self.node_results:
            parent_result = self.node_results[parent_id]
            passed = parent_result.get("passed", True)
        else:
            passed = True

        self.node_results[nid] = {"passed": passed, "condition": condition}
        self.completed_nodes.add(nid)

        # If condition failed, remove downstream feedback edges
        if not passed:
            # Only keep feedback edges (for retry loops)
            pass  # Let _get_ready_nodes handle it naturally

    async def _execute_transform_node(self, nid, node):
        """Transform/merge results from parent nodes."""
        parent_results = {}
        for edge in self.template.get("edges", []):
            if edge["target"] == nid and edge["source"] in self.node_results:
                parent_results[edge["source"]] = self.node_results[edge["source"]]
        self.node_results[nid] = {"merged": parent_results}
        self.completed_nodes.add(nid)
```

### Part 2: Integration with Pipeline (~80 lines)

In `agent_pipeline.py`, add workflow execution path:

```python
# MARKER_176.8: DAG execution path
from src.orchestration.workflow_executor import WorkflowExecutor

async def _run_pipeline(self, task_data, ...):
    workflow_id = task_data.get("workflow_family", "")
    template = WorkflowTemplateLibrary.get_template(workflow_id)

    if template and len(template.get("nodes", [])) > 0:
        # MARKER_176.8: Use DAG executor for custom workflows
        executor = WorkflowExecutor(workflow_id, task_data, pipeline_context)

        async def agent_dispatch(role, ctx):
            """Dispatch a single agent node."""
            if role == "architect":
                return await self._run_architect(ctx)
            elif role == "researcher":
                return await self._run_researcher(ctx)
            elif role == "coder":
                return await self._run_coder(ctx)
            elif role == "verifier":
                return await self._run_verifier(ctx)
            else:
                return await self._run_coder(ctx)  # Default to coder

        result = await executor.execute(agent_dispatch)
        return result
    else:
        # Fallback: existing sequential pipeline
        return await self._run_sequential_pipeline(task_data, ...)
```

---

## Tests (tests/test_176_dag_execution.py)

```python
# MARKER_176.T12: test_dag_execution_follows_topology
async def test_sequential_execution():
    """Nodes execute in edge-defined order: A→B→C."""
    executor = WorkflowExecutor("bmad_default", task_data, context)
    order = []
    async def mock_dispatch(role, ctx):
        order.append(role)
        return {"passed": True}
    await executor.execute(mock_dispatch)
    assert order == ["scout", "architect", "coder", "verifier"]

# MARKER_176.T13: test_dag_parallel_fork_join
async def test_parallel_fork_join():
    """Parallel nodes execute concurrently."""
    # Template with A → [B, C] → D
    executor = WorkflowExecutor("parallel_test", task_data, context)
    # ... verify B and C dispatched before D
    # ... verify D only starts after both B and C complete

# Additional tests:
# - Condition node routes correctly (pass vs fail)
# - Feedback loop retries (max iterations)
# - Unknown template falls back to sequential
# - Empty template falls back to sequential
```

---

## Verification

```bash
python -m pytest tests/test_176_dag_execution.py -v
python -m pytest tests/test_175b_workflow_selection.py -v  # regression
python -m pytest tests/test_176_sprint1_backend.py -v  # regression
```

### Manual Test
1. Create task with `workflow_family: "g3_critic_coder"`
2. Launch → verify: Architect runs first, then Coder, then Critic (verifier)
3. If Critic fails → Coder retries (feedback loop)
4. Compare execution order with template topology

---

## Deliverables

- [ ] `src/orchestration/workflow_executor.py` (~120 lines) — NEW
- [ ] `src/orchestration/agent_pipeline.py` — DAG execution path (~80 lines addition)
- [ ] `tests/test_176_dag_execution.py` — 5+ tests
- [ ] All code tagged with `MARKER_176.8`

**Report results to:** `docs/176_MCC_SPRINT/STATUS_DRAGON_GOLD_SPRINT2.md`
