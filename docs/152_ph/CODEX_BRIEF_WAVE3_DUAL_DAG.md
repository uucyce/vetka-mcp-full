# Codex Brief — Phase 152 Wave 3: Task DAG + Dual DAG Navigation

**Status:** READY FOR CODEX
**Depends on:** Wave 1 backend ✅ (152.1–152.4, 152.9, 152.12–152.13) + Wave 2 frontend ✅ (152.5–152.8)
**Agent:** Codex ONLY — frontend TypeScript
**Estimated:** 1 session (2 tasks)

---

## Goal

Add a **Task-level DAG** view to MCC that shows all tasks as nodes with dependency edges.
Users can toggle between **Task DAG** (project roadmap) and **Workflow DAG** (per-task agent execution).

Currently MCC center column shows ONLY the workflow DAG (agent roles/subtasks).
After Wave 3: Task DAG is the **default view**, click a task node → drill into its workflow DAG.

---

## 152.10 — Task DAG Frontend

### Create: `client/src/components/mcc/TaskDAGView.tsx` (NEW — ~300 lines)

**What it does:** A separate ReactFlow instance that renders task nodes from `/api/analytics/dag/tasks`.

### API Response Shape (already working):
```json
GET http://localhost:5001/api/analytics/dag/tasks?limit=50

{
  "success": true,
  "nodes": [
    {
      "id": "tb_001",
      "type": "taskNode",
      "position": { "x": 0, "y": 0 },
      "data": {
        "label": "Add bookmark toggle",
        "status": "done",
        "preset": "dragon_silver",
        "phase_type": "build",
        "priority": 2,
        "color": "#22c55e",
        "mini_stats": {
          "duration_s": 66.8,
          "success": true,
          "llm_calls": 12,
          "tokens_total": 23000,
          "cost_estimate": 0.023,
          "subtasks_done": 3,
          "subtasks_total": 3,
          "retries": 1,
          "verifier_confidence": 0.9
        }
      }
    }
  ],
  "edges": [
    {
      "id": "e-tb_001-tb_003",
      "source": "tb_001",
      "target": "tb_003",
      "animated": false
    }
  ],
  "total": 3
}
```

**Note:** `mini_stats` may be absent for pending/queued tasks (no pipeline ran yet).

### Component Requirements:

```typescript
interface TaskDAGViewProps {
  onTaskSelect: (taskId: string) => void;      // Click node → select task
  onTaskDrillDown: (taskId: string) => void;    // Double-click → switch to workflow DAG
  selectedTaskId?: string | null;
  width?: number | string;
  height?: number | string;
}
```

### Task Node Design (custom ReactFlow node `TaskDAGNode`):

```
┌──────────────────────────────┐
│ 📌 Add bookmark toggle       │  ← title (truncated to 40 chars)
│ dragon_silver · build         │  ← preset + phase_type
│ ⏱ 67s  ✓ 90%  🔁 1          │  ← mini_stats: duration, confidence%, retries
└──────────────────────────────┘
```

**Styling rules:**
- Border color from `data.color` (status-based — green/red/blue/gray/yellow)
- Done nodes: solid border + ✅ icon
- Failed nodes: solid red border + ❌ icon
- Running nodes: pulsing border (CSS animation `@keyframes pulse`)
- Pending nodes: dashed border, muted text
- Hold nodes: yellow dashed border, ⏸ icon
- Width: 220px, height: auto (60–80px depending on mini_stats presence)
- Font: monospace, Nolan palette (#111 bg, #e0e0e0 text, #333 border)

**Mini-stats badge (bottom row) — ONLY shown when `data.mini_stats` exists:**
- `⏱ {duration_s}s` — duration
- `✓ {verifier_confidence * 100}%` — confidence (green if ≥75%, orange if <75%)
- `🔁 {retries}` — retries (only shown if retries > 0)

**Layout:**
- Use existing `dagre` library (already installed)
- Direction: TB (top-to-bottom) — task dependencies flow downward
- Node spacing: `ranksep: 80, nodesep: 40`
- Import layout function from `../../utils/dagLayout.ts` OR write a simple dagre wrapper inline

### Data Fetching:
```typescript
const API_BASE = 'http://localhost:5001/api';

async function fetchTaskDAG(): Promise<{ nodes: any[], edges: any[] }> {
  const res = await fetch(`${API_BASE}/analytics/dag/tasks?limit=50`);
  if (!res.ok) return { nodes: [], edges: [] };
  const data = await res.json();
  return { nodes: data.nodes || [], edges: data.edges || [] };
}
```

### ReactFlow Setup:
- `@xyflow/react` v12 (already installed — import from `@xyflow/react`)
- Register custom node type: `const nodeTypes = { taskNode: TaskDAGNode };`
- MiniMap with status coloring (same as existing DAGView)
- `fitView` on initial load
- `proOptions={{ hideAttribution: true }}`
- Background: `<Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#222" />`
- Selection: single-click → `onTaskSelect(nodeId)`, double-click → `onTaskDrillDown(nodeId)`

### File Structure:
```
client/src/components/mcc/TaskDAGView.tsx     ← main component + fetch
client/src/components/mcc/nodes/TaskDAGNode.tsx  ← custom ReactFlow node
```

---

## 152.11 — Dual DAG Navigation

### Modify: `client/src/components/mcc/MyceliumCommandCenter.tsx`

**What changes:** Add a DAG mode toggle and conditional rendering in the center column.

### State Additions to MCC (local useState, NOT store):
```typescript
type DAGViewMode = 'tasks' | 'workflow';
const [dagViewMode, setDAGViewMode] = useState<DAGViewMode>('tasks');
const [taskDAGSelectedNode, setTaskDAGSelectedNode] = useState<string | null>(null);
```

### New: DAG Mode Toggle (add between breadcrumb and DAG view)

```
┌─────────────────────────────────────────────────────┐
│ [📋 Tasks] [⚙ Workflow]              ← mode toggle │
│                                                      │
│ (when mode = 'tasks')                                │
│   → TaskDAGView (new component)                      │
│                                                      │
│ (when mode = 'workflow')                             │
│   → DAGView (existing, unchanged)                    │
│   → Breadcrumb: "← Back to Tasks | Task: {title}"   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Toggle bar — MINIMAL, Nolan style:**
```typescript
<div style={{
  display: 'flex', gap: 0,
  borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
  flexShrink: 0,
}}>
  <button
    onClick={() => setDAGViewMode('tasks')}
    style={{
      flex: 1, padding: '4px 8px', fontSize: 9, fontFamily: 'monospace',
      background: dagViewMode === 'tasks' ? 'rgba(255,255,255,0.05)' : 'transparent',
      border: 'none',
      borderBottom: dagViewMode === 'tasks' ? '2px solid #4ecdc4' : '2px solid transparent',
      color: dagViewMode === 'tasks' ? '#e0e0e0' : '#666',
      cursor: 'pointer',
    }}
  >
    📋 Tasks
  </button>
  <button
    onClick={() => setDAGViewMode('workflow')}
    style={{
      flex: 1, padding: '4px 8px', fontSize: 9, fontFamily: 'monospace',
      background: dagViewMode === 'workflow' ? 'rgba(255,255,255,0.05)' : 'transparent',
      border: 'none',
      borderBottom: dagViewMode === 'workflow' ? '2px solid #4ecdc4' : '2px solid transparent',
      color: dagViewMode === 'workflow' ? '#e0e0e0' : '#666',
      cursor: 'pointer',
    }}
  >
    ⚙ Workflow
  </button>
</div>
```

### Transition Logic:

1. **Default view = "tasks"** → shows `<TaskDAGView />`
2. **User double-clicks a task node** → `onTaskDrillDown(taskId)`:
   - `selectTask(taskId)` — sets selectedTaskId in store (triggers workflow DAG fetch)
   - `setDAGViewMode('workflow')` — switches to workflow view
3. **User clicks "← Back to Tasks"** → `setDAGViewMode('tasks')`, `selectTask(null)`
4. **User clicks task in MCCTaskList (left panel)** → sets selectedTaskId, BUT does NOT change dagViewMode (stays in current mode)

### Breadcrumb Update (when mode = 'workflow'):
Replace the existing breadcrumb content:
```
← Back to Tasks | Task: {selectedTaskTitle}
```
- "← Back to Tasks" is a clickable link that sets `dagViewMode('tasks')` and `selectTask(null)`

### Center Column JSX (replace existing DAG section, lines ~707-737):

```tsx
{/* DAG Mode Toggle — MARKER_152.11 */}
<div style={{ /* toggle bar styles */ }}>
  <button onClick={() => setDAGViewMode('tasks')}>📋 Tasks</button>
  <button onClick={() => setDAGViewMode('workflow')}>⚙ Workflow</button>
</div>

{/* Breadcrumb — only in workflow mode */}
{dagViewMode === 'workflow' && selectedTaskId && (
  <div style={{ /* breadcrumb styles */ }}>
    <button onClick={() => { setDAGViewMode('tasks'); selectTask(null); }}>
      ← Back to Tasks
    </button>
    <span>Task: {selectedTaskTitle}</span>
  </div>
)}

{/* DAG View — conditional */}
<div style={{ flex: 1, minHeight: 0 }}>
  {loading ? (
    <div>Loading DAG...</div>
  ) : dagViewMode === 'tasks' ? (
    <TaskDAGView
      selectedTaskId={taskDAGSelectedNode}
      onTaskSelect={(id) => {
        setTaskDAGSelectedNode(id);
        selectTask(id);  // also select in store for right panel context
      }}
      onTaskDrillDown={(id) => {
        selectTask(id);
        setDAGViewMode('workflow');
      }}
    />
  ) : (
    <DAGView
      dagNodes={effectiveNodes}
      dagEdges={effectiveEdges}
      selectedNode={selectedNode}
      onNodeSelect={setSelectedNode}
      onEdgeSelect={handleEdgeSelect}
      editMode={editMode}
      onConnect={dagEditor.handleConnect}
      onNodesDelete={(deletedNodes) => deletedNodes.forEach(n => dagEditor.removeNode(n.id))}
      onEdgesDelete={(deletedEdges) => deletedEdges.forEach(e => dagEditor.removeEdge(e.id))}
      onContextMenu={handleContextMenu}
      onPaneDoubleClick={handlePaneDoubleClick}
    />
  )}
</div>
```

### Import to Add (top of MyceliumCommandCenter.tsx):
```typescript
import { TaskDAGView } from './TaskDAGView';
```

---

## Files Summary

| Action | File | Lines Est. |
|--------|------|-----------|
| **CREATE** | `client/src/components/mcc/TaskDAGView.tsx` | ~250 |
| **CREATE** | `client/src/components/mcc/nodes/TaskDAGNode.tsx` | ~120 |
| **MODIFY** | `client/src/components/mcc/MyceliumCommandCenter.tsx` | +60, -10 |

**Total: ~430 lines new + 50 lines modified**

---

## DO NOT

1. ❌ Do NOT touch backend files (`src/`, `main.py`, `tests/`)
2. ❌ Do NOT modify `DAGView.tsx` — it stays as-is for workflow DAG
3. ❌ Do NOT modify `MCCTaskList.tsx` — it already has drill-down via TaskDrillDown modal
4. ❌ Do NOT modify `StatsDashboard.tsx` or `TaskDrillDown.tsx` (Wave 2 — done)
5. ❌ Do NOT install new npm packages — everything needed is already installed
6. ❌ Do NOT create `.ts` files for components with JSX — always `.tsx`
7. ❌ Do NOT modify `useMCCStore.ts` — use local `useState` in MCC for dagViewMode
8. ❌ Do NOT add framer-motion animations for now — simple CSS transitions only
9. ❌ Do NOT add split-view (>1920px) — deferred to Phase 153

## DO

1. ✅ Use `@xyflow/react` (already installed v12.10.0)
2. ✅ Use `dagre` (already installed) for task DAG layout
3. ✅ Use Nolan palette from `../../utils/dagLayout` — `NOLAN_PALETTE`
4. ✅ Use monospace font everywhere
5. ✅ Fetch from `http://localhost:5001/api/analytics/dag/tasks`
6. ✅ Use MARKER_152.10 / MARKER_152.11 in code comments
7. ✅ Keep it simple — Task DAG is a READ-ONLY view (no drag-and-drop, no editing)
8. ✅ Run `npx tsc --noEmit` before committing

---

## Test Plan (manual)

1. Open MCC → should show "📋 Tasks" tab selected by default → Task DAG visible
2. Task nodes display: title, preset, status color, mini-stats badge
3. Edges render between tasks with dependencies
4. Single-click a task node → right panel shows task context
5. Double-click a task node → switches to "⚙ Workflow" mode, breadcrumb shows
6. "← Back to Tasks" link → returns to Task DAG
7. "⚙ Workflow" tab click → shows existing workflow DAG (same as before Wave 3)
8. No regressions: existing workflow DAG, edit mode, context menu, node picker all work

---

## Architecture Diagram

```
                    MyceliumCommandCenter
                    ┌─────────────────┐
                    │     HEADER      │
                    │ MCC Team Sandbox│
                    │ HB Key Stats ▶  │
                    ├─────────────────┤
                    │  WorkflowToolbar│
                    ├─────┬─────┬─────┤
                    │LEFT │ CTR │RIGHT│
                    │     │     │     │
                    │ MCC │[Tab]│ MCC │
                    │Task │📋 ⚙│Detl │
                    │List │     │Panl │
                    │     │ DAG │     │
                    │     │View │     │
                    │     │     │     │
                    │     │Strm │     │
                    └─────┴─────┴─────┘

  [Tab] = DAG mode toggle:
    📋 Tasks   → <TaskDAGView />     (NEW)
    ⚙ Workflow → <DAGView />         (existing)
```
