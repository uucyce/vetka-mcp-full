# Codex Brief — Phase 152 Wave 3: Task DAG + Toolbar UX

**Status:** READY FOR CODEX
**Agent:** Codex (single session, 3 tasks)
**Depends on:** Opus already completed: MCCDetailPanel contextual panels, Execute button adaptive, nodeCount prop wired to WorkflowToolbar.

---

## Summary: 3 Tasks

| # | Task | Files | Priority |
|---|------|-------|----------|
| **C1** | TaskDAGView + TaskDAGNode (NEW components) | 2 new files | P0 |
| **C2** | Dual DAG navigation toggle in MCC center column | 1 modify | P0 |
| **C3** | WorkflowToolbar cleanup: contextual buttons + inline inputs | 1 modify | P1 |

---

## C1: TaskDAGView + TaskDAGNode (152.10)

### Create: `client/src/components/mcc/TaskDAGView.tsx` (~250 lines)
### Create: `client/src/components/mcc/nodes/TaskDAGNode.tsx` (~120 lines)

**What:** A separate ReactFlow instance that renders task nodes from the analytics API.

### API (already working):
```
GET http://localhost:5001/api/analytics/dag/tasks?limit=50
```
Response:
```json
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
| done | solid, `data.color` | ✅ | — |
| failed | solid red `#a66` | ❌ | — |
| running | solid `data.color` | ● | `@keyframes pulse` animation |
| pending | dashed `#555` | — | muted text `#666` |
| queued | dashed `#888` | — | — |
| hold | dashed `#a98` | ⏸ | — |

**Dimensions:** 220px wide, 60-80px tall (auto). Monospace, Nolan palette.

**Mini-stats row** (only when `data.mini_stats` exists):
- `⏱ {duration_s}s` (or `Xm Ys` if >60s)
- `✓ {confidence * 100}%` — green `#8a8` if >=75%, orange `#a98` if <75%
- `🔁 {retries}` — only if retries > 0

### Layout:
```typescript
import dagre from 'dagre';

function applyDagreLayout(nodes, edges) {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: 'TB', ranksep: 80, nodesep: 40 });
  nodes.forEach(n => g.setNode(n.id, { width: 220, height: 70 }));
  edges.forEach(e => g.setEdge(e.source, e.target));
  dagre.layout(g);
  return nodes.map(n => {
    const pos = g.node(n.id);
    return { ...n, position: { x: pos.x - 110, y: pos.y - 35 } };
  });
}
```

### ReactFlow Setup:
```typescript
import {
  ReactFlow, Background, BackgroundVariant, MiniMap, Controls,
  useNodesState, useEdgesState,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

const nodeTypes = { taskNode: TaskDAGNode };

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
  <MiniMap nodeColor={(n) => n.data?.color || '#555'} style={{ background: '#111' }} />
  <Controls showInteractive={false} />
</ReactFlow>
```

### Data Fetching:
```typescript
useEffect(() => {
  fetchDAG();
  const handler = () => fetchDAG();
  window.addEventListener('task-board-updated', handler);
  return () => window.removeEventListener('task-board-updated', handler);
}, []);
```

### Selected node highlight:
```typescript
// In TaskDAGNode:
const isSelected = id === selectedTaskId; // passed via data
// boxShadow: isSelected ? '0 0 0 2px #4ecdc4' : 'none'
```

**Pass `selectedTaskId` through node data** so TaskDAGNode can highlight:
```typescript
const nodesWithSelection = nodes.map(n => ({
  ...n,
  data: { ...n.data, selectedTaskId },
}));
```

---

## C2: Dual DAG Navigation (152.11)

### Modify: `client/src/components/mcc/MyceliumCommandCenter.tsx`

**What:** Toggle between Task DAG and Workflow DAG in center column.

### New State (local useState):
```typescript
type DAGViewMode = 'tasks' | 'workflow';
const [dagViewMode, setDAGViewMode] = useState<DAGViewMode>('tasks');
const [taskDAGSelectedNode, setTaskDAGSelectedNode] = useState<string | null>(null);
```

### Import:
```typescript
import { TaskDAGView } from './TaskDAGView';
```

### Toggle Bar (insert AFTER WorkflowToolbar, BEFORE the DAG render area):
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

### WorkflowToolbar visibility:
```tsx
{/* Only show toolbar in workflow mode — Task DAG is read-only */}
{dagViewMode === 'workflow' && (
  <WorkflowToolbar ... />
)}
```

### Breadcrumb (workflow mode only):
```tsx
{dagViewMode === 'workflow' && selectedTaskId && (
  <div style={{
    padding: '3px 8px', fontSize: 9, fontFamily: 'monospace',
    borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
    display: 'flex', alignItems: 'center', gap: 8, color: '#888',
  }}>
    <button
      onClick={() => { setDAGViewMode('tasks'); selectTask(null); }}
      style={{
        background: 'none', border: 'none', color: '#4ecdc4',
        cursor: 'pointer', fontFamily: 'monospace', fontSize: 9, padding: 0,
      }}
    >
      ← Back to Tasks
    </button>
    <span style={{ color: '#555' }}>|</span>
    <span>Task: {tasks.find(t => t.id === selectedTaskId)?.title?.slice(0, 40) || selectedTaskId}</span>
  </div>
)}
```

### Center Column DAG (replace existing):
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
    <DAGView ... />   {/* existing props unchanged */}
  )}
</div>
```

### Transition Logic:
1. Default = "📋 Tasks" → `<TaskDAGView />`
2. Double-click task → `selectTask(id)` + `setDAGViewMode('workflow')`
3. "← Back to Tasks" → `setDAGViewMode('tasks')` + `selectTask(null)`
4. Click in MCCTaskList → sets selectedTaskId but does NOT change dagViewMode

---

## C3: WorkflowToolbar Cleanup (152.W3B1)

### Modify: `client/src/components/mcc/WorkflowToolbar.tsx`

**Opus already done:**
- Added `nodeCount?: number` prop to interface
- Wired `nodeCount={effectiveNodes.length}` from MCC
- `isDirty` was already wired

### You do:

**Fix 1: Validate — hide when 0 nodes**

Wrap the Validate button (~line 380):
```tsx
{/* MARKER_152.W3B1: Only show Validate when workflow has nodes */}
{(nodeCount ?? 0) > 0 && (
  <button style={btnStyle} onClick={handleValidate} title="Validate workflow">
    Validate ✓
  </button>
)}
```

**Fix 2: Generate — hide when dirty (unsaved changes)**

Wrap the Generate button (~line 384):
```tsx
{/* MARKER_152.W3B1: Hide Generate when editing to prevent accidental overwrite */}
{!isDirty && (
  <button ... onClick={handleGenerate}>
    ✦ Generate
  </button>
)}
```

**Fix 3: Save — replace prompt() with inline input**

Replace the `prompt()` call in `handleSave` (~line 115):
```typescript
// OLD:
const name = workflowName === 'Untitled Workflow'
  ? prompt('Workflow name:', 'My Workflow') || 'My Workflow'
  : workflowName;
```

With state-driven inline input:
```typescript
const [showNameInput, setShowNameInput] = useState(false);
const [nameValue, setNameValue] = useState('');

const handleSave = useCallback(async () => {
  if (workflowName === 'Untitled Workflow') {
    setNameValue('My Workflow');
    setShowNameInput(true);
    return;
  }
  doSave(workflowName);
}, [workflowName]);

const doSave = useCallback(async (name: string) => {
  setShowNameInput(false);
  setValidationMsg('saving...');
  onSetName(name);
  const wfId = await onSave(name);
  setValidationMsg(wfId ? `saved: ${wfId.slice(0, 8)}` : 'save failed');
}, [onSave, onSetName]);
```

JSX — show inline input next to Save button when `showNameInput`:
```tsx
<button style={btnStyle} onClick={handleSave}>
  Save
</button>
{showNameInput && (
  <div style={{ display: 'flex', gap: 3, alignItems: 'center' }}>
    <input
      autoFocus
      value={nameValue}
      onChange={e => setNameValue(e.target.value)}
      onKeyDown={e => {
        if (e.key === 'Enter' && nameValue.trim()) doSave(nameValue.trim());
        if (e.key === 'Escape') setShowNameInput(false);
      }}
      placeholder="workflow name..."
      style={{
        background: 'rgba(255,255,255,0.04)',
        border: `1px solid ${NOLAN_PALETTE.border}`,
        borderRadius: 2, color: '#e0e0e0',
        padding: '3px 6px', fontSize: 10,
        fontFamily: 'monospace', outline: 'none', width: 140,
      }}
    />
    <button
      onClick={() => nameValue.trim() && doSave(nameValue.trim())}
      style={{
        background: 'rgba(78,205,196,0.12)',
        border: '1px solid rgba(78,205,196,0.3)',
        borderRadius: 2, color: '#4ecdc4',
        padding: '3px 6px', fontSize: 9,
        fontFamily: 'monospace', cursor: 'pointer',
      }}
    >ok</button>
  </div>
)}
```

**Fix 4: Generate — replace prompt() with inline input**

Same pattern. Replace `prompt()` in `handleGenerate` (~line 140):
```typescript
const [showGenerateInput, setShowGenerateInput] = useState(false);
const [generateValue, setGenerateValue] = useState('');

// handleGenerate becomes:
const handleGenerate = useCallback(() => {
  setShowGenerateInput(true);
  setGenerateValue('');
}, []);

const doGenerate = useCallback(async (description: string) => {
  setShowGenerateInput(false);
  // ... existing generate logic using `description` instead of prompt() result
}, [activePreset, onGenerate]);
```

JSX:
```tsx
{showGenerateInput && (
  <div style={{ display: 'flex', gap: 3, alignItems: 'center' }}>
    <input
      autoFocus
      value={generateValue}
      onChange={e => setGenerateValue(e.target.value)}
      onKeyDown={e => {
        if (e.key === 'Enter' && generateValue.trim()) doGenerate(generateValue.trim());
        if (e.key === 'Escape') setShowGenerateInput(false);
      }}
      placeholder="describe workflow..."
      style={{
        background: 'rgba(255,255,255,0.04)',
        border: `1px solid ${NOLAN_PALETTE.border}`,
        borderRadius: 2, color: '#e0e0e0',
        padding: '3px 6px', fontSize: 10,
        fontFamily: 'monospace', outline: 'none', width: 200,
      }}
    />
    <button
      onClick={() => generateValue.trim() && doGenerate(generateValue.trim())}
      style={{
        background: 'rgba(78,205,196,0.12)',
        border: '1px solid rgba(78,205,196,0.3)',
        borderRadius: 2, color: '#4ecdc4',
        padding: '3px 6px', fontSize: 9,
        fontFamily: 'monospace', cursor: 'pointer',
      }}
    >ok</button>
  </div>
)}
```

---

## Files Summary

| Action | File | Est. Lines |
|--------|------|-----------|
| **CREATE** | `client/src/components/mcc/TaskDAGView.tsx` | ~250 |
| **CREATE** | `client/src/components/mcc/nodes/TaskDAGNode.tsx` | ~120 |
| **MODIFY** | `client/src/components/mcc/MyceliumCommandCenter.tsx` | +70, -10 |
| **MODIFY** | `client/src/components/mcc/WorkflowToolbar.tsx` | +80, -20 |

**Total: ~370 new + ~150 modified**

---

## DO NOT

1. ❌ Do NOT touch backend files (`src/`, `main.py`, `tests/`)
2. ❌ Do NOT modify `DAGView.tsx` (workflow DAG stays as-is)
3. ❌ Do NOT modify `MCCDetailPanel.tsx` (Opus already fixed)
4. ❌ Do NOT modify `MCCTaskList.tsx` (already cleaned)
5. ❌ Do NOT modify `panels/ArchitectChat.tsx` or `panels/PipelineStats.tsx`
6. ❌ Do NOT install new npm packages
7. ❌ Do NOT create `.ts` for JSX — always `.tsx`
8. ❌ Do NOT modify stores (`useMCCStore`, `useDevPanelStore`)
9. ❌ Do NOT add framer-motion

## DO

1. ✅ Use `@xyflow/react` v12 (import from `@xyflow/react`)
2. ✅ Use `dagre` for layout
3. ✅ Use `NOLAN_PALETTE` from `../../utils/dagLayout`
4. ✅ Use monospace font everywhere
5. ✅ Use MARKER_152.10 / MARKER_152.11 / MARKER_152.W3B1 in comments
6. ✅ Task DAG is READ-ONLY (no drag, no editing)
7. ✅ Run `npx tsc --noEmit` before committing (only NodeInspector.tsx error is pre-existing, ignore it)

---

## Test Plan

### C1+C2: Task DAG
1. Open MCC → "📋 Tasks" tab selected by default → Task DAG renders
2. Nodes show: title, preset, status color border, mini-stats badge
3. Edges connect dependent tasks
4. Single-click node → right panel shows task context
5. Double-click node → switches to "⚙ Workflow" mode, breadcrumb shows task title
6. "← Back to Tasks" → returns to Task DAG
7. "⚙ Workflow" tab → existing workflow DAG works exactly as before
8. WorkflowToolbar hidden in Tasks mode, visible in Workflow mode
9. No regressions: edit mode, context menu, node picker all work in Workflow mode

### C3: WorkflowToolbar
10. Edit mode → empty workflow → **Validate NOT visible**
11. Add a node → **Validate appears**
12. Click Save on "Untitled Workflow" → **inline input** (NOT browser prompt)
13. Type name + Enter → saves
14. Escape → closes input without saving
15. Click Generate → **inline description input** (NOT browser prompt)
16. Type + Enter → generates workflow
17. Make unsaved edits (dirty) → **Generate button hidden**
