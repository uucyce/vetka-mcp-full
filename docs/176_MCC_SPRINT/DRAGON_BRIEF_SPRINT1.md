# Dragon Brief — Sprint 1A Backend (Phase 176)

> **Source:** `docs/176_MCC_SPRINT/PHASE_176_ROADMAP.md`
> **Agents:** Dragon Silver (GAP 2,4,5) + Dragon Bronze (GAP 1B,3B,6)
> **Sprint:** 1A (parallel with Codex Sprint 1B frontend)
> **Estimated:** 370 lines across 6 tasks
> **ALL TASKS ARE INDEPENDENT — can run in parallel**

---

## Task 1: Roadmap→Task Bridge Backend (MARKER_176.1B)

**Dragon Tier:** Bronze (simple endpoint)
**Lines:** ~70
**Files:** `src/api/routes/mcc_routes.py`, `src/orchestration/roadmap_generator.py`

### Problem
Roadmap nodes are directory-structure nodes, NOT tasks. No endpoint to create tasks FROM a roadmap node.

### Source Reference
- `src/api/routes/mcc_routes.py` — existing MCC routes
- `src/orchestration/roadmap_generator.py` — generates roadmap nodes
- `docs/175_MCC_APP/SCOUT_MCC_AUDIT_2026-03-11.md` — GAP_1 (line 18-24)

### Implementation

1. Add endpoint to `mcc_routes.py`:
```python
# MARKER_176.1B: Create tasks from roadmap node
@router.post("/api/mcc/roadmap/{node_id}/create-tasks")
async def create_tasks_from_roadmap_node(node_id: str):
    """Generate subtasks for a specific roadmap module node."""
    board = get_task_board()

    # Get roadmap data from project state
    project_state = _load_project_state()
    if not project_state or "roadmap" not in project_state:
        raise HTTPException(404, "No roadmap found. Generate roadmap first.")

    roadmap = project_state["roadmap"]
    # Find the target node
    target_node = None
    for node in roadmap.get("nodes", []):
        if node["id"] == node_id:
            target_node = node
            break

    if not target_node:
        raise HTTPException(404, f"Roadmap node {node_id} not found")

    # Generate subtasks from node metadata
    created_tasks = []
    module_name = target_node.get("label", target_node["id"])
    module_desc = target_node.get("description", "")
    files = target_node.get("files", [])

    # Create one task per logical unit (or one parent task)
    task_id = board.add_task(
        title=f"Implement: {module_name}",
        description=f"{module_desc}\n\nFiles: {', '.join(files[:10])}",
        priority=target_node.get("priority", 5),
        phase_type="build",
        preset="dragon_silver",
        tags=[f"roadmap:{node_id}"],
    )
    created_tasks.append(task_id)

    # If node has sub-modules, create subtasks
    for sub in target_node.get("children", [])[:5]:
        sub_id = board.add_task(
            title=f"Subtask: {sub.get('label', sub.get('id', 'unknown'))}",
            description=sub.get("description", ""),
            priority=target_node.get("priority", 5),
            phase_type="build",
            preset="dragon_silver",
            tags=[f"roadmap:{node_id}", f"parent:{task_id}"],
        )
        created_tasks.append(sub_id)

    return {"success": True, "tasks": created_tasks, "count": len(created_tasks)}
```

### Tests
```python
# MARKER_176.T1: test_roadmap_create_tasks
def test_roadmap_node_creates_tasks(client, board, tmp_path):
    """POST /api/mcc/roadmap/{node_id}/create-tasks creates board tasks."""
    # Seed project state with roadmap
    # POST to endpoint
    # Verify tasks created in board
    # Verify task tags include roadmap:node_id
```

---

## Task 2: Prefetch Wire into Dispatch (MARKER_176.2)

**Dragon Tier:** Silver (pipeline wiring, needs flow understanding)
**Lines:** ~80
**Files:** `src/orchestration/agent_pipeline.py`, `src/services/architect_prefetch.py`

### Problem
`ArchitectPrefetch.prepare()` exists (prefetch_files, prefetch_markers, select_workflow, select_team) but NEVER called before pipeline dispatch. Architect sees raw task description only.

### Source Reference
- `src/services/architect_prefetch.py` — `prepare()` method
- `src/orchestration/agent_pipeline.py` — pipeline dispatch flow
- `docs/175_MCC_APP/SCOUT_MCC_AUDIT_2026-03-11.md` — GAP_2 (line 26-32)

### Implementation

1. In `agent_pipeline.py`, before architect phase, call prefetch:
```python
# MARKER_176.2: Wire prefetch into dispatch chain
from src.services.architect_prefetch import ArchitectPrefetch, WorkflowTemplateLibrary

async def _run_pipeline(self, task_data: dict, ...):
    # ... existing setup ...

    # MARKER_176.2: Prefetch context BEFORE architect
    task_description = task_data.get("description", "")
    task_type = task_data.get("phase_type", "build")
    complexity = task_data.get("estimated_complexity", 5)
    workflow_family = task_data.get("workflow_family", "")

    prefetch_ctx = ArchitectPrefetch.prepare(
        task_description=task_description,
        task_type=task_type,
        complexity=complexity,
        workflow_family=workflow_family,
    )

    # Inject prefetch context into architect prompt
    architect_context = f"""
## Prefetch Context (MARKER_176.2)
- Workflow: {prefetch_ctx.workflow_name} ({prefetch_ctx.workflow_id})
- Relevant files: {', '.join(prefetch_ctx.prefetch_files[:10])}
- Related markers: {', '.join(prefetch_ctx.prefetch_markers[:5])}
{chr(10).join(prefetch_ctx.workflow_reinforcement)}
"""
    # Prepend to architect user message
    # ... inject into existing architect call ...
```

2. Ensure `prepare()` handles edge cases (no project config, empty description).

### Tests
```python
# MARKER_176.T2: test_prefetch_called_before_dispatch
def test_prefetch_injected_into_architect(monkeypatch, tmp_path):
    """Pipeline dispatch calls ArchitectPrefetch.prepare() before architect."""
    # Mock pipeline, verify prepare() called with correct args
    # Verify architect prompt contains prefetch context
```

---

## Task 3: Apply/Reject Backend Handlers (MARKER_176.3B)

**Dragon Tier:** Bronze (simple endpoint additions)
**Lines:** ~30
**Files:** `src/api/routes/mcc_routes.py`

### Problem
Apply/Reject buttons exist in UI but backend has no handlers to update task status.

### Source Reference
- `src/api/routes/mcc_routes.py` — existing task PATCH
- `src/orchestration/task_board.py` — `ADDABLE_FIELDS` includes `result_status`
- `docs/175_MCC_APP/SCOUT_MCC_AUDIT_2026-03-11.md` — GAP_3 (line 34-40)

### Implementation
```python
# MARKER_176.3B: Apply pipeline results
@router.post("/api/mcc/tasks/{task_id}/apply")
async def apply_task_result(task_id: str):
    """Mark task result as applied (accepted by user)."""
    board = get_task_board()
    success = board.update_task(task_id,
        result_status="applied",
        status="done",
    )
    if not success:
        raise HTTPException(404, f"Task {task_id} not found")
    task = board.get_task(task_id)
    return {"success": True, "task": task}

# MARKER_176.3B: Reject pipeline results with feedback
@router.post("/api/mcc/tasks/{task_id}/reject")
async def reject_task_result(task_id: str, body: dict = Body(...)):
    """Reject result and requeue task with user feedback."""
    board = get_task_board()
    feedback = body.get("feedback", "")
    success = board.update_task(task_id,
        result_status="rejected",
        status="pending",  # Requeue
        description=board.get_task(task_id).get("description", "") + f"\n\n[FEEDBACK]: {feedback}",
    )
    if not success:
        raise HTTPException(404, f"Task {task_id} not found")
    task = board.get_task(task_id)
    return {"success": True, "task": task}
```

### Tests
```python
# MARKER_176.T3 + T4
def test_apply_updates_task_status(client, board):
    """POST /api/mcc/tasks/{id}/apply sets result_status=applied, status=done."""

def test_reject_requeues_task(client, board):
    """POST /api/mcc/tasks/{id}/reject sets status=pending, appends feedback."""
```

---

## Task 4: TRM Integration into DAG Builder (MARKER_176.4)

**Dragon Tier:** Silver (needs TRM adapter understanding)
**Lines:** ~60
**Files:** `src/services/mcc_trm_adapter.py`, DAG builder module

### Problem
`mcc_trm_config.py` + `mcc_trm_adapter.py` coded (Phase 161) but output IGNORED. `resolve_trm_policy()` returns policy but it's NOT passed to `build_design_dag()`.

### Source Reference
- `src/services/mcc_trm_config.py` — TRM config definitions
- `src/services/mcc_trm_adapter.py` — `resolve_trm_policy()`, `adapt_candidates()`
- DAG builder (find via grep for `build_design_dag`)
- `docs/175_MCC_APP/SCOUT_MCC_AUDIT_2026-03-11.md` — GAP_4 (line 42-48)

### Implementation
1. Find DAG builder function (likely in `src/orchestration/` or `src/services/`).
2. After existing DAG construction, call TRM adapter:
```python
# MARKER_176.4: TRM refines DAG candidates
from src.services.mcc_trm_adapter import MCCTRMAdapter

def build_design_dag(task_data, ...):
    # ... existing DAG construction ...

    # MARKER_176.4: Apply TRM policy to refine DAG
    try:
        trm_adapter = MCCTRMAdapter()
        trm_policy = trm_adapter.resolve_trm_policy(task_data)
        if trm_policy:
            candidates = trm_adapter.adapt_candidates(dag_nodes, trm_policy)
            # Merge TRM-refined candidates into DAG
            for node in dag_nodes:
                trm_meta = candidates.get(node["id"], {})
                if trm_meta:
                    node["data"]["trm_source"] = True  # Badge in UI
                    node["data"]["trm_policy"] = trm_meta
    except Exception as e:
        logger.warning(f"TRM integration skipped: {e}")

    return dag_nodes, dag_edges
```

### Tests
```python
# MARKER_176.T5
def test_trm_policy_in_dag():
    """TRM output enriches DAG nodes with trm_source badge."""
    # Build DAG with TRM adapter active
    # Verify nodes have trm_source=True where TRM contributes
```

---

## Task 5: JEPA Semantic Clustering in Roadmap (MARKER_176.5)

**Dragon Tier:** Silver (needs JEPA adapter understanding)
**Lines:** ~100
**Files:** `src/services/mcc_jepa_adapter.py`, `src/orchestration/roadmap_generator.py`

### Problem
`mcc_jepa_adapter.py` (Phase 155) provides embeddings for similarity, but `roadmap_generator.py` is pure directory-structure heuristic. No semantic grouping (e.g., "auth" spans api + middleware + tests).

### Source Reference
- `src/services/mcc_jepa_adapter.py` — embedding functions
- `src/orchestration/roadmap_generator.py` — static scan → roadmap
- `docs/175_MCC_APP/SCOUT_MCC_AUDIT_2026-03-11.md` — GAP_5 (line 50-56)

### Implementation
1. After static directory scan in roadmap_generator, call JEPA:
```python
# MARKER_176.5: JEPA semantic clustering refines roadmap
from src.services.mcc_jepa_adapter import MCCJEPAAdapter

def generate_roadmap(project_path: str, ...):
    # ... existing static scan → raw_modules ...

    # MARKER_176.5: Semantic refinement via JEPA
    try:
        jepa = MCCJEPAAdapter()
        embeddings = jepa.embed_modules(raw_modules)
        clusters = jepa.cluster_by_similarity(embeddings, threshold=0.7)

        # Merge semantically related modules
        for cluster in clusters:
            if len(cluster) > 1:
                # Create merged node with combined files
                merged = _merge_roadmap_nodes(cluster)
                merged["data"]["jepa_clustered"] = True
                refined_modules.append(merged)
            else:
                refined_modules.append(cluster[0])
    except Exception as e:
        logger.warning(f"JEPA clustering skipped: {e}")
        refined_modules = raw_modules

    return refined_modules
```

### Tests
```python
# MARKER_176.T6
def test_jepa_clustering_in_roadmap():
    """JEPA embeddings group related modules in roadmap."""
    # Create project with auth spread across api/middleware/tests
    # Generate roadmap with JEPA
    # Verify: auth files grouped into single cluster node
```

---

## Task 6: Group Chat → MCC Task Board Sync (MARKER_176.6)

**Dragon Tier:** Bronze (30 lines, simple wiring)
**Lines:** ~30
**Files:** `src/orchestration/group_message_handler.py`

### Problem
`@dragon` commands in VETKA group chat create mycelium pipeline tasks but DON'T appear in MCC task board.

### Source Reference
- `src/orchestration/group_message_handler.py` — `_dispatch_system_command()`
- `src/orchestration/task_board.py` — `add_task()` with `source_chat_id`
- `docs/175_MCC_APP/SCOUT_MCC_AUDIT_2026-03-11.md` — GAP_6 (line 62-68)

### Implementation
In `_dispatch_system_command()`, after creating pipeline task, add to board:
```python
# MARKER_176.6: Sync group chat commands to MCC task board
from src.orchestration.task_board import get_task_board

async def _dispatch_system_command(self, message, command, args, group_id):
    # ... existing pipeline dispatch ...

    # MARKER_176.6: Also add to MCC task board
    board = get_task_board()
    board.add_task(
        title=f"@{command}: {args[:80]}",
        description=args,
        priority=5,
        phase_type=command if command in ("build", "fix", "research") else "build",
        preset="dragon_silver",
        tags=["from_group_chat", f"group:{group_id}"],
        source_chat_id=str(message.get("chat_id", "")),
        source_group_id=str(group_id),
    )
```

### Tests
```python
# MARKER_176.T7
def test_group_task_appears_in_mcc(board, monkeypatch):
    """@dragon command in group chat creates task in MCC board."""
    # Simulate group message with @dragon
    # Verify: task appears in board with source_group_id set
```

---

## Test File: tests/test_176_sprint1_backend.py

All 7 backend tests should go into a single test file:
- `MARKER_176.T1`: test_roadmap_create_tasks
- `MARKER_176.T2`: test_prefetch_called_before_dispatch
- `MARKER_176.T3`: test_apply_updates_task_status
- `MARKER_176.T4`: test_reject_requeues_task
- `MARKER_176.T5`: test_trm_policy_in_dag
- `MARKER_176.T6`: test_jepa_clustering_in_roadmap
- `MARKER_176.T7`: test_group_task_appears_in_mcc

Use fixtures from `tests/test_175b_workflow_selection.py` as template (board, client, _seed_task).

### Run
```bash
python -m pytest tests/test_176_sprint1_backend.py -v
python -m pytest tests/test_175b_workflow_selection.py -v  # regression
```

---

## Dragon Dispatch Commands

```bash
# Bronze tasks (simple, can use dragon_bronze)
@dragon MARKER_176.1B: Add POST /api/mcc/roadmap/{node_id}/create-tasks endpoint to mcc_routes.py. See docs/176_MCC_SPRINT/DRAGON_BRIEF_SPRINT1.md Task 1.
@dragon MARKER_176.3B: Add POST /api/mcc/tasks/{id}/apply and /reject endpoints to mcc_routes.py. See docs/176_MCC_SPRINT/DRAGON_BRIEF_SPRINT1.md Task 3.
@dragon MARKER_176.6: Add board.add_task() call in group_message_handler._dispatch_system_command(). See docs/176_MCC_SPRINT/DRAGON_BRIEF_SPRINT1.md Task 6.

# Silver tasks (medium complexity)
@dragon MARKER_176.2: Wire ArchitectPrefetch.prepare() into agent_pipeline.py dispatch chain. See docs/176_MCC_SPRINT/DRAGON_BRIEF_SPRINT1.md Task 2.
@dragon MARKER_176.4: Integrate mcc_trm_adapter.adapt_candidates() into DAG builder. See docs/176_MCC_SPRINT/DRAGON_BRIEF_SPRINT1.md Task 4.
@dragon MARKER_176.5: Add JEPA semantic clustering to roadmap_generator.py. See docs/176_MCC_SPRINT/DRAGON_BRIEF_SPRINT1.md Task 5.
```
