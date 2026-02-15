# Grok Research: DAG-Drives-Pipeline Architecture + Node Editor UX

## Context
VETKA — 3D knowledge graph app (Tauri + React + FastAPI). We have:
- **Mycelium Pipeline** (`agent_pipeline.py`, ~3300 lines): Scout → Architect → Researcher → Coder → Verifier → retry loop. Hard-coded in Python.
- **DAG Editor** (Phase 144): Visual node editor with addNode/removeNode/addEdge, undo/redo, save/load workflow templates. Uses @xyflow/react.
- **Workflow Templates** API: CRUD endpoints for saving/loading user-created workflows.
- **n8n Converter** (`n8n_converter.py`): Bidirectional n8n ↔ VETKA format conversion.
- **Node Types**: task, agent, subtask, proposal, condition, parallel, loop, transform, group
- **Edge Types**: structural, dataflow, temporal, conditional, parallel_fork, parallel_join, feedback

**THE PROBLEM:** DAG visualizes pipeline AFTER the fact. Pipeline → DAG. Should be inverted: **DAG defines pipeline, pipeline executes DAG**. Like n8n and ComfyUI — user creates workflow visually, system executes it.

## Research Questions

### Q1: DAG-Drives-Pipeline Architecture
Search: "visual workflow to execution engine", "n8n workflow execution internals", "ComfyUI execution engine architecture", "DAG executor from visual graph"

1. How does n8n convert its visual workflow JSON into an execution plan?
   - Does it topological-sort nodes? Run BFS/DFS?
   - How does it handle conditions (if/else branches)?
   - How does it handle parallel execution (split/merge)?
2. How does ComfyUI execute its node graph?
   - Does it use a scheduler? Lazy evaluation?
   - How does it handle node dependencies (input/output ports)?
3. What's the minimal architecture to go from "JSON graph" → "execute agents in order"?
   - We already have `agent_pipeline.py` with Scout/Architect/Coder/Verifier
   - Can we make it DAG-driven: read workflow template → for each node, call appropriate agent?
   - How to handle dynamic nodes (Architect creates subtasks at runtime)?

### Q2: Node Editor UX (n8n + ComfyUI patterns)
Search: "n8n node editor UX patterns", "ComfyUI node interface design", "visual programming best practices", "node-based workflow UI"

1. What makes n8n intuitive for new users?
   - Input/output port conventions
   - Node categories (triggers, actions, logic)
   - Connection validation (which ports can connect to which)
2. What makes ComfyUI powerful for experts?
   - Multi-type connections
   - Preview in nodes
   - Group boxes
3. What UI patterns should we adopt to attract n8n/ComfyUI users?
   - We use @xyflow/react (React Flow) — same lib as n8n
   - Node palette / sidebar with drag-to-canvas
   - Mini-map, grid snap, auto-layout
4. How do these systems handle "templates" vs "instances"?
   - n8n: workflow template → execution instance
   - ComfyUI: saved workflow → queued prompt

### Q3: Playground as Execution Environment
Search: "sandboxed code execution workflow", "git worktree as sandbox", "isolated execution environment CI/CD"

1. In n8n, each execution runs in its own context. How is isolation achieved?
2. Should our Playground (git worktree) be the execution environment FOR the DAG?
   - DAG node "Coder" runs inside Playground → reads worktree, writes worktree
   - DAG node "Verifier" verifies code in Playground
   - DAG node "Promote" = merge approved changes to main
3. Should we show Playground as a "canvas" containing the DAG workflow?
   - User sees: Playground → inside it, the workflow DAG runs
   - Multiple playgrounds = multiple parallel workflows

### Q4: BMAD Loop Wiring
Search: "Build Measure Adjust Deploy CI agent", "approval workflow agent pipeline", "auto-approve threshold code generation"

We have all pieces but disconnected:
- **Build** = Coder agent (works)
- **Measure** = Verifier (works) + eval_agent.py `evaluate_with_retry()` (NOT connected)
- **Adjust** = retry_coder with feedback (works, MARKER_149.RETRY_FIX)
- **Deploy** = playground promote() (works) + approval_service.py (NOT connected)

Questions:
1. How to wire eval_agent into pipeline? As a DAG node after Verifier?
2. approval_service has SocketIO modal — should it be a DAG "gate" node (blocks until approved)?
3. Auto-approve rules: what thresholds? (e.g., new files auto-approve, modifications need review)
4. Should BMAD be a fixed template (always these 4 stages) or a customizable DAG workflow?

## Key VETKA Files for Reference

| File | What it does |
|------|-------------|
| `src/orchestration/agent_pipeline.py` | Hard-coded pipeline: Scout→Architect→Coder→Verifier |
| `src/orchestration/playground_manager.py` | Git worktree sandbox: create/destroy/promote/review |
| `src/services/approval_service.py` | Approve/reject artifacts with SocketIO events |
| `src/agents/eval_agent.py` | evaluate() + evaluate_with_retry() scoring |
| `src/services/converters/n8n_converter.py` | Bidirectional n8n ↔ VETKA workflow format |
| `client/src/hooks/useDAGEditor.ts` | DAG visual editor: addNode/removeNode/save/load |
| `client/src/components/mcc/WorkflowToolbar.tsx` | Save/Load/Validate/Generate toolbar |
| `client/src/types/dag.ts` | WorkflowNode, WorkflowEdge, NodeType, EdgeType types |
| `src/api/routes/workflow_template_routes.py` | CRUD for workflow templates |
| `data/templates/pipeline_prompts.json` | Agent prompts per role |
| `data/templates/model_presets.json` | Dragon/Titan team configurations |
| `docs/150_ph/SPARSE_APPLY_DESIGN.md` | Sparse Apply design (unified diff) |

## Expected Output
1. Architecture design for "DAG executes pipeline" (with code snippets)
2. UX recommendations for node editor (n8n/ComfyUI patterns to adopt)
3. Playground-as-workspace design (DAG inside Playground)
4. BMAD wiring plan (connect existing pieces)
5. Priority: what to implement first for maximum impact
