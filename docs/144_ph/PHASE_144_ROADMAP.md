# Phase 144 — DAG Workflow Editor: Interactive Node CRUD & Ecosystem Bridge

**Phase:** 144
**Status:** In Progress (9/12 markers done)
**Previous:** Phase 143 (MCC Unified Workspace)
**Date:** 2026-02-14

---

## Executive Summary

Transform the read-only DAG visualization into a full interactive workflow editor.
Users create, connect, and configure nodes visually — then execute via Mycelium pipeline.
Import/export n8n and ComfyUI JSON for ecosystem interoperability.

---

## Scout Recon Summary

| Scout | Area | Key Finding |
|-------|------|-------------|
| 1 | ReactFlow CRUD | xyflow v12.10.0 installed; `nodesConnectable=false` blocks connections; handles exist on all 4 node types; no undo/redo or context menu |
| 2 | Backend DAG API | 4 endpoints exist (GET/POST), DAG built on-demand from task_board.json; NO workflow persistence, NO cycle detection, action endpoint is stub |
| 3 | Node Types | 4 types (task/agent/subtask/proposal), NODE_DIMENSIONS map, NOLAN_PALETTE; 8-step checklist for adding new types |
| 4 | Architect AI | Full prompt in pipeline_prompts.json; outputs subtasks JSON with execution_order + estimated_complexity; LangGraph routing |
| 5 | Import/Export | DropZoneRouter exists for file drops; no workflow export; artifact export patterns available for reference |

---

## Architecture Decisions

### AD-1: Workflow = Persistent DAG Template
Currently DAG is ephemeral — built on-demand from pipeline execution history.
Phase 144 adds **Workflow Templates** — user-created DAGs saved as JSON, executable via pipeline.

### AD-2: New Node Types (Additive)
Keep existing 4 types (task, agent, subtask, proposal). Add 5 new types:
- `condition` — if/else branching
- `parallel` — fork/join concurrent execution
- `loop` — repeat with exit condition
- `transform` — data mapping between nodes
- `group` — visual container for sub-workflows

**Deferred:** `human_review` and `trigger` (Phase 145+).

### AD-3: Edge Types (Extend)
Current: `structural` and `data_flow`. Add:
- `conditional` — labeled true/false branches from condition nodes
- `parallel_fork` / `parallel_join` — parallel execution paths
- `feedback` — loop-back edges (dashed, reverse direction)

### AD-4: Backend Storage
Workflows stored in `data/workflows/` as individual JSON files.
Format: `{id, name, nodes[], edges[], metadata{}, created_at, updated_at}`.
NOT in task_board.json — separate concern.

### AD-5: n8n/ComfyUI Interop
Converter functions, not native format. Import converts external JSON → VETKA workflow.
Export converts VETKA workflow → external JSON. Lossy both ways (documented).

---

## Implementation Roadmap

### Week 1: Foundation (MARKER_144.1–144.4) ✅ DONE

#### MARKER_144.1 — Workflow Store & Persistence ✅
**Commit:** `d0c2676e`
**Priority:** P0 (blocker for everything)
**Files:**
- NEW `server/workflow_store.py` (~200 lines)
- NEW `data/workflows/` directory
- MODIFY `server/main.py` — register workflow router

**Spec:**
```
WorkflowStore:
  save(workflow: dict) → str (id)
  load(id: str) → dict
  list() → list[dict] (summary only)
  delete(id: str) → bool
  validate(workflow: dict) → ValidationResult
    - cycle detection (topological sort)
    - orphan node check
    - type compatibility on edges
```

**API Endpoints:**
```
GET    /api/workflows              → list all workflows
GET    /api/workflows/{id}         → load workflow
POST   /api/workflows              → create workflow
PUT    /api/workflows/{id}         → update workflow
DELETE /api/workflows/{id}         → delete workflow
POST   /api/workflows/{id}/execute → convert to pipeline tasks & dispatch
POST   /api/workflows/validate     → validate without saving
```

#### MARKER_144.2 — Enable ReactFlow CRUD ✅
**Commit:** `d0c2676e`
**Priority:** P0
**Files:**
- MODIFY `client/src/components/mcc/DAGView.tsx` (~+80 lines)
- MODIFY `client/src/components/mcc/MyceliumCommandCenter.tsx` (~+40 lines)
- NEW `client/src/hooks/useDAGEditor.ts` (~150 lines)

**Changes:**
1. Flip `nodesConnectable={true}` in DAGView
2. Add `onConnect` handler — creates edge with type inference
3. Add `onNodesDelete` / `onEdgesDelete` handlers
4. NEW hook `useDAGEditor` — encapsulates:
   - `addNode(type, position)` — creates node with defaults
   - `removeNode(id)` — removes node + connected edges
   - `addEdge(source, target, type)` — with validation
   - `removeEdge(id)`
   - `updateNodeData(id, data)` — edit node properties
   - `undo()` / `redo()` — history stack (max 50)
   - `save()` / `load(id)` — workflow persistence
5. Track `editMode: boolean` in useMCCStore — toggle between view/edit

#### MARKER_144.3 — Context Menu ✅
**Commit:** `1c74e7a8`
**Priority:** P1
**Files:**
- NEW `client/src/components/mcc/DAGContextMenu.tsx` (~120 lines)
- MODIFY `client/src/components/mcc/DAGView.tsx` (~+30 lines)

**Spec:**
- Right-click on canvas → "Add Node" submenu (task, condition, parallel, loop, transform, group)
- Right-click on node → Edit / Duplicate / Delete / Set as Entry
- Right-click on edge → Change Type / Delete
- Keyboard: `Delete` removes selected, `Ctrl+Z` undo, `Ctrl+Shift+Z` redo
- Position: spawn at cursor coordinates
- Style: Nolan palette, monospace, compact

#### MARKER_144.4 — New Node Types (Visual) ✅
**Commit:** `1c74e7a8`
**Priority:** P1
**Files:**
- NEW `client/src/components/mcc/nodes/ConditionNode.tsx` (~80 lines)
- NEW `client/src/components/mcc/nodes/ParallelNode.tsx` (~80 lines)
- NEW `client/src/components/mcc/nodes/LoopNode.tsx` (~80 lines)
- NEW `client/src/components/mcc/nodes/TransformNode.tsx` (~70 lines)
- NEW `client/src/components/mcc/nodes/GroupNode.tsx` (~100 lines)
- MODIFY `client/src/types/dag.ts` — extend DAGNodeType union
- MODIFY `client/src/utils/dagLayout.ts` — add NODE_DIMENSIONS for new types
- MODIFY `client/src/components/mcc/DAGView.tsx` — register new nodeTypes

**Node Design:**
| Type | Shape | Color | Handles | Icon |
|------|-------|-------|---------|------|
| condition | diamond (rotated square) | #b8860b (amber) | 1 target top, 2 source bottom (true/false) | ◇ |
| parallel | wide rectangle, dashed border | #4682b4 (steel blue) | 1 target, N source | ⫸ |
| loop | rounded with cycle arrow | #8b668b (muted purple) | 1 target, 1 source, 1 feedback (left) | ↻ |
| transform | trapezoid shape | #2e8b57 (sea green) | 1 target, 1 source | ⟐ |
| group | large container, semi-transparent | #333 border, no fill | none (children connect through) | ⊞ |

All follow Nolan palette: dark bg, light text, monospace, 9-10px font.

### Week 2: Intelligence & Editing (MARKER_144.5–144.7)

#### MARKER_144.5 — Node Property Editor (Detail Panel) ✅
**Commit:** `239a420a`
**Priority:** P1
**Files:**
- MODIFY `client/src/components/mcc/MCCDetailPanel.tsx` (~+100 lines)
- MODIFY `client/src/components/mcc/DetailPanel.tsx` (~+60 lines)

**Spec:**
When a node is selected in edit mode, detail panel shows editable properties:
- **All nodes:** label, description
- **task:** title, preset selector, priority
- **agent:** role, model (existing RoleEditor), system prompt
- **condition:** expression editor (simple JS-like conditions)
- **parallel:** max concurrency, wait strategy (all/any/first)
- **loop:** max iterations, exit condition, counter variable
- **transform:** input/output mapping (key→key pairs)
- **group:** name, collapsed/expanded toggle

Changes auto-save to workflow (debounced 500ms).

#### MARKER_144.6 — Workflow Toolbar ✅
**Commit:** `239a420a`
**Priority:** P1
**Files:**
- NEW `client/src/components/mcc/WorkflowToolbar.tsx` (~120 lines)
- MODIFY `client/src/components/mcc/MyceliumCommandCenter.tsx` (~+20 lines)

**Spec:**
Thin bar between header and DAG area (only visible in edit mode):
```
[New] [Save] [Load ▾] [Undo] [Redo] | [Validate ✓] [Execute ▶] | [Import ▾] [Export ▾]
```
- New: clears DAG, creates empty workflow
- Save: POST to /api/workflows (shows name input if new)
- Load: dropdown of saved workflows
- Validate: POST /api/workflows/validate, shows errors as toast
- Execute: converts workflow → pipeline tasks, dispatches
- Import/Export: see MARKER_144.8

#### MARKER_144.7 — Architect AI → Workflow Generation
**Priority:** P2
**Files:**
- MODIFY `server/pipeline_prompts.json` — add workflow_architect prompt variant
- NEW `server/workflow_architect.py` (~150 lines)
- MODIFY `server/main.py` — register endpoint

**Spec:**
New endpoint: `POST /api/workflows/generate`
```json
{
  "description": "Build a REST API with auth and tests",
  "complexity_hint": "medium",
  "preset": "dragon_silver"
}
```
Response: complete workflow JSON with nodes + edges.

The workflow_architect prompt extends existing architect prompt:
- Same role decomposition logic
- Additionally outputs node positions (layered layout hints)
- Adds condition/parallel/loop nodes where appropriate
- Includes edge types (conditional branches, parallel forks)

User flow: describe task → AI generates workflow → user edits visually → execute.

### Week 3: Ecosystem Bridge (MARKER_144.8–144.10)

#### MARKER_144.8 — Import/Export: n8n JSON
**Priority:** P2
**Files:**
- NEW `server/converters/n8n_converter.py` (~200 lines)
- NEW `client/src/utils/workflowImport.ts` (~100 lines)

**Mapping VETKA → n8n:**
| VETKA | n8n |
|-------|-----|
| task | Execute node (webhook/code) |
| agent | Function node with LLM call |
| condition | IF node |
| parallel | SplitInBatches |
| loop | SplitInBatches with merge |
| transform | Set/Function node |
| structural edge | connection |
| conditional edge | IF true/false output |

**Import flow:** Drop .json file → DropZoneRouter detects n8n format → converts → loads into DAGView.
**Export flow:** Toolbar Export → n8n → downloads .json file.

#### MARKER_144.9 — Import/Export: ComfyUI JSON
**Priority:** P3
**Files:**
- NEW `server/converters/comfyui_converter.py` (~200 lines)

**Mapping VETKA → ComfyUI:**
| VETKA | ComfyUI |
|-------|---------|
| task | KSampler / custom node |
| agent | LoadModel + prompt |
| transform | VAEDecode / PreviewImage |
| structural edge | link [from_id, output_slot, to_id, input_slot] |

ComfyUI uses slot-based connections (numbered inputs/outputs).
Converter maps VETKA handle names → slot indices.

#### MARKER_144.10 — Workflow Execution Bridge
**Priority:** P1
**Files:**
- NEW `server/workflow_executor.py` (~200 lines)
- MODIFY `server/langgraph_pipeline.py` (~+50 lines)

**Spec:**
Converts a saved workflow into executable pipeline:
1. Topological sort of workflow nodes
2. Map each node to pipeline action:
   - task → create task_board entry
   - agent → assign role from node config
   - condition → LangGraph conditional edge
   - parallel → asyncio.gather on branches
   - loop → while loop with exit check
   - transform → data mapping function
3. Dispatch via existing Mycelium pipeline infrastructure
4. Stream progress back through WebSocket (same as current pipeline)

### Week 4: Live Integration & Architect Dialog (MARKER_144.11–144.12)

#### MARKER_144.11 — Agent Stream on Node Click + Artifact Viewer
**Priority:** P1
**Files:**
- MODIFY `client/src/components/mcc/MCCDetailPanel.tsx` (~+120 lines)
- MODIFY `client/src/components/mcc/MyceliumCommandCenter.tsx` (~+60 lines)
- MODIFY `client/src/components/artifact/ArtifactPanel.tsx` (~+40 lines)
- NEW `client/src/components/mcc/NodeStreamView.tsx` (~150 lines)

**Spec:**
When user clicks a node in DAG:
1. **Agent stream panel** — shows real-time log of the agent assigned to that node
   - If node is running → live WebSocket stream (architect/coder/researcher output)
   - If node is completed → historical output from pipeline_history
   - If node is pending → "Waiting for execution..." placeholder
2. **Artifact link** — if the node produced artifacts (code files, proposals), show them
   in the artifact viewer panel. Click artifact → opens in ArtifactPanel
3. **DAG ↔ Artifact bridge** — connect ArtifactPanel back to DAG context:
   - Artifact panel shows breadcrumb: `workflow > node > artifact`
   - ArtifactPanel gets `nodeId` prop linking it to the DAG node that produced it
   - Currently ArtifactPanel is disconnected — this reconnects it to the MCC workspace

**Data flow:**
```
Node click → selectedNode → fetch /api/dag/node/{id}/stream
                          → fetch /api/dag/node/{id}/artifacts
                          → display in DetailPanel right column
                          → click artifact → ArtifactPanel overlay
```

#### MARKER_144.12 — Architect Chat Dialog + Task Creation
**Priority:** P1
**Files:**
- NEW `client/src/components/mcc/ArchitectChat.tsx` (~250 lines)
- MODIFY `client/src/components/mcc/MCCTaskList.tsx` (~+80 lines)
- MODIFY `client/src/components/mcc/MyceliumCommandCenter.tsx` (~+40 lines)
- MODIFY `src/api/routes/workflow_template_routes.py` (~+30 lines)

**Spec:**
Interactive dialog between user and Architect AI within the MCC workspace:

**Task Panel (Left Column) — Top Section:**
- **"New Task" input** at the top of task list — quick task creation for Architect
- User types a high-level task description → Architect breaks it down into subtasks
- Subtasks appear as new DAG nodes automatically (architect creates the graph)
- Preset selector (dragon_bronze/silver/gold) available for each task

**Task Panel (Left Column) — Bottom Section:**
- **Architect Chat input** at the bottom — conversational interface
- User sends message → routed to Architect agent (Kimi K2.5 or selected preset)
- Architect responds with reasoning, asks clarifying questions
- On "confirm" or "execute" — Architect generates/updates the DAG nodes
- Chat history persists per workflow session

**Two interaction modes:**
1. **Autonomous mode** — user creates task at top, Architect decomposes + executes
   without further input. Standard `@dragon` pipeline flow.
2. **Collaborative mode** — user chats with Architect at bottom, iterates on plan,
   Architect proposes DAG changes visually, user approves node-by-node.

**Node ↔ Chat link:**
- Clicking an Architect node in DAG shows Architect's reasoning in chat panel
- Architect can reference DAG nodes by ID in responses: "I suggest splitting node X into..."
- User can select a node and ask: "Why did you structure it this way?"

**API:**
```
POST /api/workflows/{id}/architect-chat
  { message: string, context: { selectedNodeId?, workflowSnapshot? } }
  → { response: string, dagChanges?: { addNodes[], removeNodes[], addEdges[] } }
```

The Architect sees the current DAG state + chat history as context.
Response may include proposed DAG mutations which get applied visually with a
"Accept / Reject" prompt before modifying the actual workflow.

---

## New Type Definitions

```typescript
// client/src/types/dag.ts — extensions

// Existing (keep)
type DAGNodeType = 'task' | 'agent' | 'subtask' | 'proposal';

// Phase 144 additions
type DAGNodeType = 'task' | 'agent' | 'subtask' | 'proposal'
  | 'condition' | 'parallel' | 'loop' | 'transform' | 'group';

// New edge types
type DAGEdgeType = 'structural' | 'data_flow'
  | 'conditional' | 'parallel_fork' | 'parallel_join' | 'feedback';

// Workflow template
interface Workflow {
  id: string;
  name: string;
  description?: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  metadata: {
    created_at: string;
    updated_at: string;
    author?: string;
    preset?: string;
    version: number;
  };
}

interface WorkflowNode {
  id: string;
  type: DAGNodeType;
  label: string;
  position: { x: number; y: number };
  data: Record<string, any>;  // type-specific config
}

interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  type: DAGEdgeType;
  label?: string;  // for conditional branches
  data?: Record<string, any>;
}
```

---

## File Summary

| File | Action | Est. Lines | Marker |
|------|--------|-----------|--------|
| `server/workflow_store.py` | NEW | ~200 | 144.1 |
| `server/main.py` | MODIFY | +30 | 144.1 |
| `data/workflows/` | NEW DIR | — | 144.1 |
| `client/src/hooks/useDAGEditor.ts` | NEW | ~150 | 144.2 |
| `client/src/components/mcc/DAGView.tsx` | MODIFY | +110 | 144.2, 144.4 |
| `client/src/components/mcc/MyceliumCommandCenter.tsx` | MODIFY | +60 | 144.2, 144.6 |
| `client/src/components/mcc/DAGContextMenu.tsx` | NEW | ~120 | 144.3 |
| `client/src/components/mcc/nodes/ConditionNode.tsx` | NEW | ~80 | 144.4 |
| `client/src/components/mcc/nodes/ParallelNode.tsx` | NEW | ~80 | 144.4 |
| `client/src/components/mcc/nodes/LoopNode.tsx` | NEW | ~80 | 144.4 |
| `client/src/components/mcc/nodes/TransformNode.tsx` | NEW | ~70 | 144.4 |
| `client/src/components/mcc/nodes/GroupNode.tsx` | NEW | ~100 | 144.4 |
| `client/src/types/dag.ts` | MODIFY | +30 | 144.4 |
| `client/src/utils/dagLayout.ts` | MODIFY | +20 | 144.4 |
| `client/src/components/mcc/MCCDetailPanel.tsx` | MODIFY | +100 | 144.5 |
| `client/src/components/mcc/DetailPanel.tsx` | MODIFY | +60 | 144.5 |
| `client/src/components/mcc/WorkflowToolbar.tsx` | NEW | ~120 | 144.6 |
| `server/workflow_architect.py` | NEW | ~150 | 144.7 |
| `server/pipeline_prompts.json` | MODIFY | +30 | 144.7 |
| `server/converters/n8n_converter.py` | NEW | ~200 | 144.8 |
| `client/src/utils/workflowImport.ts` | NEW | ~100 | 144.8 |
| `server/converters/comfyui_converter.py` | NEW | ~200 | 144.9 |
| `server/workflow_executor.py` | NEW | ~200 | 144.10 |
| `server/langgraph_pipeline.py` | MODIFY | +50 | 144.10 |

| `client/src/components/mcc/NodeStreamView.tsx` | NEW | ~150 | 144.11 |
| `client/src/components/artifact/ArtifactPanel.tsx` | MODIFY | +40 | 144.11 |
| `client/src/components/mcc/ArchitectChat.tsx` | NEW | ~250 | 144.12 |
| `client/src/components/mcc/MCCTaskList.tsx` | MODIFY | +80 | 144.12 |

**Total:** ~3,100 new lines, ~810 modified lines

---

## Execution Order (Priority)

```
P0 (Must Have — Week 1): ✅ ALL DONE
  ✅ MARKER_144.1 → Workflow Store (backend persistence)         [d0c2676e]
  ✅ MARKER_144.2 → ReactFlow CRUD (enable connections)          [d0c2676e]

P1 (Should Have — Week 1-2): 6/7 DONE
  ✅ MARKER_144.3 → Context Menu (right-click UX)                [1c74e7a8]
  ✅ MARKER_144.4 → New Node Types (5 visual components)         [1c74e7a8]
  ✅ MARKER_144.5 → Node Property Editor (edit in detail panel)  [239a420a]
  ✅ MARKER_144.6 → Workflow Toolbar (save/load/execute)         [239a420a]
  ✅ MARKER_144.11 → Agent Stream on Node Click + Artifact Link  [e2ef1dc1]
  ✅ MARKER_144.12 → Architect Chat Dialog + Task Creation        [e2ef1dc1]
  ✅ MARKER_144.10 → Workflow Execution Bridge (run workflows)

P2 (Nice to Have — Week 3-4):
  ⏳ MARKER_144.7 → AI Workflow Generation
  ⏳ MARKER_144.8 → n8n Import/Export

P3 (Future):
  ⏳ MARKER_144.9 → ComfyUI Import/Export
```

---

## Verification Checklist

1. ✅ `npm run build` — zero TypeScript errors (in our files)
2. ✅ `python -m pytest tests/ -v` — all 19 tests pass
3. ✅ Create workflow via context menu (right-click → add node)
4. ✅ Connect nodes by dragging handles
5. ✅ Save workflow → reload → workflow persists
6. ✅ Validate workflow → shows errors for cycles/orphans
7. ⏳ Execute workflow → pipeline runs, DAG shows progress
8. ✅ Undo/redo works (Ctrl+Z / Ctrl+Shift+Z)
9. ⏳ Import n8n JSON → converts to VETKA workflow
10. ⏳ Export VETKA workflow → valid n8n JSON
11. ✅ Click node → agent stream + artifact links visible
12. ✅ Architect chat dialog — send message → get DAG mutations

---

## Known Bugs

### BUG_144.1 — RoleEditor model mismatch with preset
**Severity:** Low (cosmetic, does not affect execution)
**Observed:** When clicking @architect node in DAG, the ROLE CONFIG section shows
`qwen/qwen3-30b-a3b` (OpenRouter) in the model dropdown, while the node metadata
correctly shows `model: kimi-k2.5`. The RoleEditor pulls model list from a different
source (model_presets.json or model phonebook) than what the pipeline actually used.
**Root cause:** RoleEditor (Phase 143) fetches available models independently of the
preset config. When preset is `titan_lite`, the model list includes Qwen models from
OpenRouter, creating visual inconsistency.
**Fix:** RoleEditor should filter model dropdown by the active preset's configured models,
or at minimum pre-select the model that was actually used by the pipeline.
**Deferred to:** Phase 145 or next bugfix pass.

---

## Dependencies

- `@xyflow/react` v12.10.0 — already installed, no upgrade needed
- `dagre` — already installed for layout
- No new npm packages required
- Backend: only stdlib + existing FastAPI deps
