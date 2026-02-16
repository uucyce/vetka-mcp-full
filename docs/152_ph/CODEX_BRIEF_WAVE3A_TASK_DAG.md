# Codex Brief — Wave 3A: Task DAG + Dual Navigation

**Status:** READY FOR CODEX
**Agent:** Codex Stream A (parallel with Wave 3B)
**Estimated:** 1 session
**Depends on:** Wave 1 backend (all done), Wave 2 frontend (all done)

---

## Goal

Add a **Task-level DAG** to MCC center column. Users toggle between **Task DAG** (project tasks as nodes) and **Workflow DAG** (per-task agent pipeline).

**This stream creates 2 new files + modifies 1 existing.**

---

## Task A1: TaskDAGView.tsx + TaskDAGNode.tsx (152.10)

### Create: `client/src/components/mcc/TaskDAGView.tsx` (~250 lines)
### Create: `client/src/components/mcc/nodes/TaskDAGNode.tsx` (~120 lines)

**TaskDAGView** — a separate ReactFlow instance rendering task nodes.

### API (already working, no backend changes needed):
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
    { "id": "e-tb_001-tb_003", "source": "tb_001", "target": "tb_003", "animated": false }
  ],
  "total": 3
}
```

**Note:** `mini_stats` may be absent for pending/queued tasks.

### Props:
```typescript
interface TaskDAGViewProps {
  onTaskSelect: (taskId: string) => void;
  onTaskDrillDown: (taskId: string) => void;
  selectedTaskId?: string | null;
}
```

### TaskDAGNode Design:
```
┌──────────────────────────────┐
│ ✅ Add bookmark toggle        │  ← status icon + title (40 char max)
│ dragon_silver · build         │  ← preset + phase_type
│ ⏱ 67s  ✓ 90%  🔁 1          │  ← mini_stats (only if present)
└──────────────────────────────┘
```

**Status styling:**
| Status | Border | Icon | Extra |
|--------|--------|------|-------|
| done | solid, color from `data.color` | ✅ | — |
| failed | solid red `#a66` | ❌ | — |
| running | solid, `data.color` | ● | `@keyframes pulse` border animation |
| pending | dashed `#555` | — | muted text `#666` |
| queued | dashed `#888` | — | — |
| hold | dashed yellow `#a98` | ⏸ | — |

**Node dimensions:** width 220px, height auto (60-80px).
**Font:** monospace, Nolan palette (#111 bg, #e0e0e0 text, #333 border).

**Mini-stats row** (only when `data.mini_stats` exists):
- `⏱ {duration_s}s` (or `Xm Ys` if > 60s)
- `✓ {verifier_confidence * 100}%` — green `#8a8` if ≥75%, orange `#a98` if <75%
- `🔁 {retries}` — only if retries > 0

### Layout:
- Use `dagre` (already installed)
- Direction: **TB** (top-to-bottom)
- `ranksep: 80`, `nodesep: 40`
- Write a simple dagre wrapper inline or import from `../../utils/dagLayout.ts`

### ReactFlow Setup:
```typescript
import {
  ReactFlow, Background, BackgroundVariant, MiniMap, Controls,
  useNodesState, useEdgesState,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

const nodeTypes = { taskNode: TaskDAGNode };

// In component:
<ReactFlow
  nodes={layoutNodes}
  edges={layoutEdges}
  nodeTypes={nodeTypes}
  onNodeClick={(_, node) => onTaskSelect(node.id)}
  onNodeDoubleClick={(_, node) => onTaskDrillDown(node.id)}
  fitView
  proOptions={{ hideAttribution: true }}
  style={{ background: '#0a0a0a' }}
>
  <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#222" />
  <MiniMap
    nodeColor={(n) => n.data?.color || '#555'}
    style={{ background: '#111' }}
  />
  <Controls showInteractive={false} />
</ReactFlow>
```

### Data Fetching:
```typescript
const API_BASE = 'http://localhost:5001/api';

// Fetch on mount + on 'task-board-updated' event
useEffect(() => {
  fetchDAG();
  const handler = () => fetchDAG();
  window.addEventListener('task-board-updated', handler);
  return () => window.removeEventListener('task-board-updated', handler);
}, []);

async function fetchDAG() {
  try {
    const res = await fetch(`${API_BASE}/analytics/dag/tasks?limit=50`);
    if (!res.ok) return;
    const data = await res.json();
    // Apply dagre layout to data.nodes, data.edges
    // Set nodes/edges state
  } catch {}
}
```

### Selected Node Highlight:
When `selectedTaskId` matches a node, add a brighter border or box-shadow:
```typescript
const isSelected = data.id === selectedTaskId;
// style: boxShadow: isSelected ? '0 0 0 2px #4ecdc4' : 'none'
```

---

## Task A2: Dual DAG Navigation (152.11)

### Modify: `client/src/components/mcc/MyceliumCommandCenter.tsx`

**What changes:** Add DAG mode toggle + conditional rendering in center column.

### State (local useState, NOT store):
```typescript
type DAGViewMode = 'tasks' | 'workflow';
const [dagViewMode, setDAGViewMode] = useState<DAGViewMode>('tasks');
const [taskDAGSelectedNode, setTaskDAGSelectedNode] = useState<string | null>(null);
```

### Import to add:
```typescript
import { TaskDAGView } from './TaskDAGView';
```

### Toggle Bar (between WorkflowToolbar and DAG area):
```tsx
{/* MARKER_152.11: DAG mode toggle */}
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

### Breadcrumb (only in workflow mode when task selected):
```tsx
{dagViewMode === 'workflow' && selectedTaskId && (
  <div style={{
    padding: '3px 8px', fontSize: 9, fontFamily: 'monospace',
    borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
    display: 'flex', alignItems: 'center', gap: 8,
    color: '#888',
  }}>
    <button
      onClick={() => { setDAGViewMode('tasks'); selectTask(null); }}
      style={{
        background: 'none', border: 'none', color: '#4ecdc4',
        cursor: 'pointer', fontFamily: 'monospace', fontSize: 9,
        padding: 0,
      }}
    >
      ← Back to Tasks
    </button>
    <span style={{ color: '#555' }}>|</span>
    <span>Task: {tasks.find(t => t.id === selectedTaskId)?.title?.slice(0, 40) || selectedTaskId}</span>
  </div>
)}
```

### Center Column DAG (replace existing DAG rendering):
```tsx
<div style={{ flex: 1, minHeight: 0 }}>
  {loading ? (
    <div style={{ color: '#555', textAlign: 'center', padding: 40 }}>Loading DAG...</div>
  ) : dagViewMode === 'tasks' ? (
    <TaskDAGView
      selectedTaskId={taskDAGSelectedNode}
      onTaskSelect={(id) => {
        setTaskDAGSelectedNode(id);
        selectTask(id);
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

### Transition Logic:
1. **Default** = "tasks" tab → `<TaskDAGView />`
2. **Double-click task node** → `selectTask(id)` + `setDAGViewMode('workflow')`
3. **"← Back to Tasks"** → `setDAGViewMode('tasks')` + `selectTask(null)`
4. **Click task in MCCTaskList** → sets selectedTaskId but does NOT change dagViewMode

### WorkflowToolbar Visibility:
- WorkflowToolbar should ONLY show when `dagViewMode === 'workflow'` (it's irrelevant for Task DAG which is read-only)
- Wrap the existing `<WorkflowToolbar>` render with: `{dagViewMode === 'workflow' && <WorkflowToolbar ... />}`

---

## Files

| Action | File | Lines |
|--------|------|-------|
| **CREATE** | `client/src/components/mcc/TaskDAGView.tsx` | ~250 |
| **CREATE** | `client/src/components/mcc/nodes/TaskDAGNode.tsx` | ~120 |
| **MODIFY** | `client/src/components/mcc/MyceliumCommandCenter.tsx` | +70, -10 |

---

## DO NOT

1. ❌ Do NOT touch backend files (`src/`, `main.py`, `tests/`)
2. ❌ Do NOT modify `DAGView.tsx` (workflow DAG stays as-is)
3. ❌ Do NOT modify `MCCTaskList.tsx`
4. ❌ Do NOT modify `MCCDetailPanel.tsx` (that's Wave 3B)
5. ❌ Do NOT modify `WorkflowToolbar.tsx` (that's Wave 3B)
6. ❌ Do NOT install new npm packages
7. ❌ Do NOT create `.ts` for JSX components — always `.tsx`
8. ❌ Do NOT modify stores (`useMCCStore`, `useDevPanelStore`)
9. ❌ Do NOT add framer-motion — CSS transitions only

## DO

1. ✅ Use `@xyflow/react` v12 (import from `@xyflow/react`)
2. ✅ Use `dagre` for layout
3. ✅ Use `NOLAN_PALETTE` from `../../utils/dagLayout`
4. ✅ Use MARKER_152.10 / MARKER_152.11 in comments
5. ✅ Task DAG is READ-ONLY (no drag, no editing, no context menu)
6. ✅ Run `npx tsc --noEmit` before committing

---

## Test Plan

1. Open MCC → "📋 Tasks" tab selected by default → Task DAG shows
2. Task nodes display: title, preset, status color, mini-stats
3. Edges render between dependent tasks
4. Single-click task node → right panel shows task context
5. Double-click task node → switches to "⚙ Workflow", breadcrumb appears
6. "← Back to Tasks" → returns to Task DAG
7. "⚙ Workflow" tab → existing workflow DAG works as before
8. WorkflowToolbar hidden in Tasks mode, visible in Workflow mode
9. No regressions: edit mode, context menu, node picker all work in Workflow mode
