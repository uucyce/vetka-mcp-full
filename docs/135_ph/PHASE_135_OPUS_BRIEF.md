# Phase 135: OPUS COMMANDER BRIEF — DAG-Centric MCC
## For: Cursor Agent | From: Opus Commander | Date: 2026-02-10

---

## STATUS: Your Architecture v2.0 is APPROVED with corrections below.

The DAG-as-UI idea is strong. Single spatial view instead of 7 tabs — exactly right for VETKA philosophy. Below are corrections, constraints, and the exact execution plan.

---

## SECTION 1: CRITICAL CORRECTIONS

### 1.1 DO NOT create new WebSocket endpoint

**WRONG in your plan:**
```python
@router.websocket("/ws/dag")  # ← DO NOT CREATE THIS
```

**WHY:** We already have `ws://localhost:8082` (Mycelium WS). It broadcasts `pipeline_activity`, `task_board_updated`, `pipeline_stats`, `pipeline_complete`, `pipeline_failed`. The frontend hook `useMyceliumSocket.ts` dispatches CustomEvents.

**CORRECT approach:**
- Reuse `useMyceliumSocket.ts` hook (already exists)
- Listen to existing CustomEvents: `pipeline-activity`, `task-board-updated`, `pipeline-stats`
- Add ONE new event type `dag_update` to the existing Mycelium WS broadcaster (backend)
- The DAG component listens via `window.addEventListener('dag-update', handler)`

### 1.2 DO NOT remove existing tabs yet

**WRONG:** "After Phase 135 is complete, these become obsolete: DevPanel tabs system"

**CORRECT:** Phase 135 ADDS DAG as a new view mode in MCC. Tabs stay as fallback. Users can toggle: `DAG View | Classic Tabs`. Migration happens in Phase 136 after DAG is proven stable.

**Implementation:**
```tsx
// In DevPanel.tsx or MyceliumStandalone.tsx
const [viewMode, setViewMode] = useState<'dag' | 'tabs'>('dag');

// Toggle button in header
<button onClick={() => setViewMode(v => v === 'dag' ? 'tabs' : 'dag')}>
  {viewMode === 'dag' ? '≡ Tabs' : '◇ DAG'}
</button>

{viewMode === 'dag' ? <MyceliumCommandCenter /> : <DevPanel standalone={true} />}
```

### 1.3 WebSocket URL — use port 8082 NOT 5001

**WRONG in your plan:**
```tsx
const ws = new WebSocket('ws://localhost:5001/ws/dag');  // ← WRONG PORT
```

**CORRECT:** All pipeline events go through Mycelium WS on port 8082. DO NOT create a parallel WebSocket.

### 1.4 Package name is `@xyflow/react` not `xyflow`

```bash
cd client
npm install @xyflow/react dagre @types/dagre
# Import:
import { ReactFlow, Background, Controls, MiniMap } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
```

### 1.5 dagre rankdir should be 'BT' directly

**WRONG in Grok's code:** `rankdir: 'TB'` then manually invert Y.

**CORRECT:** dagre supports `rankdir: 'BT'` (Bottom-to-Top) natively. No Y-inversion hack needed:
```ts
g.setGraph({ rankdir: 'BT', ranksep: 80, nodesep: 50 });
```

---

## SECTION 2: EXACT FILE PLAN

### 2.1 New Files to Create

```
client/src/
├── types/
│   └── dag.ts                          # MARKER_135.1A_TYPES
├── components/mcc/
│   ├── MyceliumCommandCenter.tsx        # MARKER_135.1A — Main container
│   ├── DAGView.tsx                      # MARKER_135.1B — xyflow wrapper
│   ├── DetailPanel.tsx                  # MARKER_135.3A — Right sidebar
│   ├── FilterBar.tsx                    # MARKER_135.5A — Filters
│   └── nodes/
│       ├── TaskNode.tsx                 # MARKER_135.1C
│       ├── AgentNode.tsx                # MARKER_135.1D
│       ├── SubtaskNode.tsx              # MARKER_135.1E
│       └── ProposalNode.tsx             # MARKER_135.1F
└── utils/
    └── dagLayout.ts                     # MARKER_135.1G — Sugiyama BT layout

src/
├── services/
│   └── dag_aggregator.py               # MARKER_135.2A
└── api/routes/
    └── dag_routes.py                    # MARKER_135.2B
```

### 2.2 Files to Modify

```
client/src/MyceliumStandalone.tsx        # Add DAG/Tabs toggle
client/src/hooks/useMyceliumSocket.ts    # Add 'dag_update' event type
src/mcp/mycelium_ws_server.py           # Add broadcast_dag_update() method
src/api/__init__.py                      # Register dag_routes
```

### 2.3 Test Files to Create (MANDATORY before implementation)

```
tests/
├── test_phase135_dag_aggregator.py      # MARKER_135.T1 — 25+ tests
├── test_phase135_dag_routes.py          # MARKER_135.T2 — 15+ tests
└── test_phase135_dag_websocket.py       # MARKER_135.T3 — 10+ tests
```

---

## SECTION 3: DATA CONTRACT

### 3.1 DAG Node (Backend → Frontend)

```python
# src/services/dag_aggregator.py

@dataclass
class DAGNode:
    id: str                    # Unique: "task_{uuid}" / "agent_{task_id}_{role}" / "sub_{idx}"
    type: str                  # "task" | "agent" | "subtask" | "proposal"
    label: str                 # Display text
    status: str                # "pending" | "running" | "done" | "failed"
    layer: int                 # 0=task, 1=agents, 2-3=subtasks, 4=proposals
    parent_id: Optional[str]   # For tree edges
    task_id: str               # Root task reference

    # Metadata (optional, for Detail Panel)
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_s: Optional[float]
    tokens: Optional[int]
    model: Optional[str]       # "kimi-k2.5", "qwen3-coder", etc.
    confidence: Optional[float]  # For proposals only (0-1)
    role: Optional[str]        # For agents: "scout", "architect", "researcher", "coder", "verifier"
```

### 3.2 DAG Edge

```python
@dataclass
class DAGEdge:
    id: str
    source: str                # parent node id
    target: str                # child node id
    type: str                  # "structural" | "dataflow" | "temporal"
    strength: float            # 0.0-1.0
```

### 3.3 API Response

```python
@dataclass
class DAGResponse:
    nodes: List[DAGNode]
    edges: List[DAGEdge]
    root_ids: List[str]        # Task node IDs at layer 0
    stats: Dict                # Aggregate: total_tasks, running, success_rate
```

### 3.4 REST Endpoints

```
GET  /api/dag                          → DAGResponse (full graph)
     ?status=running                   → filter by status
     ?time_range=1h                    → filter by time (1h|6h|24h|all)
     ?task_id=xxx                      → single task tree only

GET  /api/dag/node/{node_id}           → DAGNodeDetail (full metadata + code preview)

POST /api/dag/node/{node_id}/action    → Execute action
     body: { action: "retry" | "approve" | "reject" | "cancel" }
```

---

## SECTION 4: DAG AGGREGATOR — HOW IT BUILDS THE GRAPH

The aggregator reads from EXISTING data sources. No new storage needed.

```python
class DAGAggregator:
    """MARKER_135.2A: Build DAG from existing MCC data sources."""

    def __init__(self):
        self.task_board = TaskBoard()  # Existing
        self.project_root = Path(__file__).resolve().parent.parent.parent

    async def build_dag(self, filters: dict = None) -> DAGResponse:
        nodes = []
        edges = []

        # SOURCE 1: Task Board → Layer 0 (root tasks)
        tasks = self.task_board.list_tasks()
        # Apply filters (status, time_range)
        for task in filtered_tasks:
            nodes.append(DAGNode(
                id=f"task_{task['id']}",
                type="task",
                label=task["title"],
                status=task["status"],
                layer=0,
                task_id=task["id"],
                ...
            ))

        # SOURCE 2: Pipeline results in task["result"] → Layers 1-3
        for task in tasks:
            if task.get("result") and task["result"].get("subtasks"):
                # Add agent nodes (layer 1)
                for role in ["scout", "architect", "researcher", "coder", "verifier"]:
                    nodes.append(DAGNode(
                        id=f"agent_{task['id']}_{role}",
                        type="agent",
                        label=f"@{role}",
                        role=role,
                        layer=1,
                        parent_id=f"task_{task['id']}",
                        task_id=task["id"],
                        ...
                    ))
                    edges.append(DAGEdge(
                        source=f"task_{task['id']}",
                        target=f"agent_{task['id']}_{role}",
                        type="structural",
                        strength=0.8,
                    ))

                # Add subtask nodes (layer 2-3)
                for idx, sub in enumerate(task["result"]["subtasks"]):
                    nodes.append(DAGNode(
                        id=f"sub_{task['id']}_{idx}",
                        type="subtask",
                        label=sub.get("description", f"Subtask {idx}")[:40],
                        layer=2,
                        parent_id=f"agent_{task['id']}_coder",
                        task_id=task["id"],
                        ...
                    ))

        # SOURCE 3: Feedback reports → Could become proposal nodes (layer 4)
        # Future: Playground experiments

        return DAGResponse(nodes=nodes, edges=edges, root_ids=[...], stats={...})
```

**KEY POINT:** The aggregator reads from `task_board.json` (tasks), `task["result"]` (pipeline output), and `feedback/reports/` (quality data). NO new data storage.

---

## SECTION 5: REAL-TIME UPDATES

### How it works (using existing infrastructure):

```
Pipeline runs → mycelium_ws_server broadcasts → useMyceliumSocket receives
→ CustomEvent dispatched → DAGView updates nodes
```

### Backend addition (mycelium_ws_server.py):

```python
async def broadcast_dag_update(self, update_type: str, node_data: dict):
    """MARKER_135.4A: Emit DAG node update."""
    await self._broadcast({
        "type": "dag_update",
        "update_type": update_type,  # "node_added" | "node_status" | "node_removed"
        "node": node_data,
    })
```

### Frontend addition (useMyceliumSocket.ts):

```typescript
case 'dag_update':
  window.dispatchEvent(
    new CustomEvent('dag-update', { detail: data })
  );
  break;
```

### DAGView listener:

```tsx
useEffect(() => {
  const handler = (e: CustomEvent) => {
    const { update_type, node } = e.detail;
    if (update_type === 'node_status') {
      // Update single node status (triggers re-render of that node only)
      setDagData(prev => updateNodeInDAG(prev, node));
    } else if (update_type === 'node_added') {
      // Re-fetch full DAG (new subtask spawned = new layout needed)
      fetchDAG(filters).then(setDagData);
    }
  };
  window.addEventListener('dag-update', handler);
  return () => window.removeEventListener('dag-update', handler);
}, [filters]);
```

---

## SECTION 6: EXECUTION ORDER (RAILS)

### Wave 1: Foundation (do first, test before moving on)

| Step | Task | Files | Test |
|------|------|-------|------|
| 1.1 | Install deps | `npm install @xyflow/react dagre @types/dagre` | `npm list @xyflow/react` |
| 1.2 | Create types | `types/dag.ts` | TypeScript compiles |
| 1.3 | Create dagLayout.ts | `utils/dagLayout.ts` | Manual test with 10 nodes |
| 1.4 | Create 4 custom nodes | `nodes/Task,Agent,Subtask,Proposal.tsx` | Storybook or manual |
| 1.5 | Create DAGView.tsx | `components/mcc/DAGView.tsx` | **HARDCODED TEST DATA** — render 10-15 nodes |
| 1.6 | Create MyceliumCommandCenter.tsx | Main container | Renders DAGView |
| 1.7 | Wire into MyceliumStandalone.tsx | Add DAG/Tabs toggle | Toggle works |

**CHECKPOINT:** Open MCC window, see DAG with hardcoded nodes. Pan/zoom/select works. Screenshot to verify.

### Wave 2: Backend Integration

| Step | Task | Files | Test |
|------|------|-------|------|
| 2.1 | Write tests FIRST | `test_phase135_dag_aggregator.py` | `pytest tests/test_phase135_dag_aggregator.py -v` |
| 2.2 | Create dag_aggregator.py | `src/services/dag_aggregator.py` | Tests pass |
| 2.3 | Write route tests | `test_phase135_dag_routes.py` | `pytest tests/test_phase135_dag_routes.py -v` |
| 2.4 | Create dag_routes.py | `src/api/routes/dag_routes.py` | Tests pass |
| 2.5 | Register routes | `src/api/__init__.py` | `curl localhost:5001/api/dag` returns JSON |
| 2.6 | Connect frontend to API | Replace hardcoded data with fetch | Real data renders |

**CHECKPOINT:** DAG shows real tasks from task board. Dispatch a task, see it appear.

### Wave 3: Real-time + Detail Panel

| Step | Task | Files | Test |
|------|------|-------|------|
| 3.1 | Add dag_update broadcast | `mycelium_ws_server.py` | WS test |
| 3.2 | Add dag_update to hook | `useMyceliumSocket.ts` | Console log on event |
| 3.3 | DAG listens to updates | `DAGView.tsx` | Run pipeline, nodes update live |
| 3.4 | Create DetailPanel.tsx | Right sidebar | Click node → details show |
| 3.5 | Create FilterBar.tsx | Filters | Filter by status works |
| 3.6 | Node actions | approve/reject/retry | Action triggers API call |

**CHECKPOINT:** Full workflow: dispatch task → see agents appear → subtasks execute → verifier scores → all live in DAG. Detail panel shows info.

### Wave 4: Polish + Animations

| Step | Task | Test |
|------|------|------|
| 4.1 | Pulse animation for running nodes | Visual check |
| 4.2 | Confidence glow on proposals | Visual check |
| 4.3 | Edge animations (temporal) | Visual check |
| 4.4 | Keyboard navigation | Arrow keys + Enter |
| 4.5 | MiniMap node colors by status | Visual check |

---

## SECTION 7: TESTING STRATEGY (MANDATORY)

### 7.1 Backend Tests (write BEFORE implementation)

```python
# tests/test_phase135_dag_aggregator.py — MARKER_135.T1

class TestDAGAggregatorBuildDAG:
    """Test DAG construction from task board data."""

    def test_empty_board_returns_empty_dag(self):
    def test_single_task_returns_one_root_node(self):
    def test_task_status_maps_correctly(self):
    def test_completed_task_has_agent_nodes(self):
    def test_agent_nodes_on_layer_1(self):
    def test_subtask_nodes_on_layer_2(self):
    def test_edges_connect_task_to_agents(self):
    def test_edges_connect_agents_to_subtasks(self):
    def test_filter_by_status(self):
    def test_filter_by_time_range(self):
    def test_filter_by_task_id(self):
    def test_node_ids_are_unique(self):
    def test_proposal_nodes_have_confidence(self):
    def test_agent_nodes_have_role(self):
    def test_stats_calculation(self):
    def test_root_ids_match_task_nodes(self):
    def test_large_board_performance(self):  # 100 tasks < 200ms
    def test_missing_result_graceful(self):
    def test_absolute_paths_used(self):  # CWD fix from Phase 134

class TestDAGAggregatorEdges:
    def test_structural_edges(self):
    def test_dataflow_edges(self):
    def test_edge_strength_range(self):
    def test_no_self_loops(self):
    def test_no_duplicate_edges(self):

class TestDAGRoutes:
    def test_get_dag_returns_200(self):
    def test_get_dag_with_status_filter(self):
    def test_get_node_detail(self):
    def test_get_node_detail_404(self):
    def test_node_action_retry(self):
    def test_node_action_approve(self):
    def test_node_action_reject(self):
    def test_node_action_invalid(self):
```

### 7.2 Visual Testing (Cursor self-check)

After EACH wave, Cursor must:
1. Take a screenshot of MCC window (or describe what renders)
2. Verify node count matches expected
3. Verify layout direction (root at BOTTOM)
4. Verify colors match Nolan palette
5. Report any console errors

### 7.3 Integration Test

```python
# tests/test_phase135_dag_websocket.py — MARKER_135.T3

class TestDAGWebSocket:
    """Test real-time DAG updates through existing Mycelium WS."""

    async def test_dag_update_event_broadcast(self):
    async def test_node_status_change_emits_update(self):
    async def test_new_subtask_emits_node_added(self):
    async def test_pipeline_complete_updates_all_nodes(self):
    async def test_multiple_clients_receive_updates(self):
```

---

## SECTION 8: FEEDBACK LOOP FOR CURSOR

After each Wave, Cursor should write a status update to:
`docs/135_ph/CURSOR_STATUS.md`

Format:
```markdown
## Wave X Status — [timestamp]

### Done
- [x] Step X.Y: description

### Issues
- Issue: description → resolution

### Screenshot
[describe what MCC shows]

### Next
- [ ] Step X.Y: next action

### Tests
- pytest result: X passed, Y failed
- Visual check: pass/fail
```

This creates a feedback loop — I (Opus) read the status and adjust the plan if needed.

---

## SECTION 9: WHAT CURSOR MUST NOT DO

1. **DO NOT create new WebSocket server** — use existing port 8082
2. **DO NOT remove existing tabs** — add toggle, keep tabs as fallback
3. **DO NOT use react-router** — use pathname check in main.tsx (existing pattern)
4. **DO NOT install xyflow** — install `@xyflow/react` (correct 2026 package name)
5. **DO NOT create playground sandbox** — that's deferred. DAG is the priority
6. **DO NOT add new buttons to main window** — MCC is a separate Tauri window
7. **DO NOT skip tests** — write tests BEFORE implementation (TDD for backend)
8. **DO NOT use relative paths in Python** — always `Path(__file__).resolve().parent` (Phase 134 CWD fix)

---

## SECTION 10: GROK RESEARCH NEEDED

I'm requesting Grok research on:
1. `@xyflow/react` v12+ API changes (2026) — custom nodes, performance with 200+ nodes
2. `dagre` vs `elkjs` for BT layout — which handles 50+ nodes better
3. How to animate node status transitions in xyflow (CSS vs xyflow API)

Results will be added as `docs/135_ph/GROK_XYFLOW_RESEARCH.txt`

---

## SUMMARY

| What | Decision |
|------|----------|
| Architecture | DAG View (80%) + Detail Panel (20%) — APPROVED |
| Layout | Sugiyama BT via dagre — APPROVED |
| Library | @xyflow/react + dagre — APPROVED |
| WebSocket | Reuse port 8082, add dag_update event — CORRECTED |
| Tabs | Keep as toggle fallback — CORRECTED |
| Testing | TDD for backend, visual checks for frontend — MANDATORY |
| Execution | 4 waves, checkpoints after each — CONFIRMED |

**Cursor: start with Wave 1 (Foundation). Write tests for Wave 2 in parallel. Report status after each wave.**

---

*OPUS COMMANDER BRIEF v1.0*
*Phase 135 — DAG-Centric MCC*
*2026-02-10*
