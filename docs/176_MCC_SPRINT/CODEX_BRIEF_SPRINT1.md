# Codex Brief — Sprint 1B Frontend (Phase 176)

> **Source:** `docs/176_MCC_SPRINT/PHASE_176_ROADMAP.md`
> **Agent:** Codex
> **Sprint:** 1B (parallel with Dragon Sprint 1A backend)
> **Estimated:** 280 lines across 5 tasks
> **Markers:** MARKER_176.15, MARKER_176.7, MARKER_176.18, MARKER_176.1F, MARKER_176.3F

---

## Task 1: API_BASE Centralization (MARKER_176.15)

**Priority:** HIGH — blocks all other frontend error handling improvements
**Lines:** ~30
**Can start:** IMMEDIATELY (no dependencies)

### Problem
`const API_BASE = 'http://localhost:5001/api'` hardcoded in 10+ MCC components.

### Evidence
- `MiniStats.tsx:23` — hardcoded
- `MiniChat.tsx:21` — hardcoded
- `FirstRunView.tsx:15` — hardcoded
- `NodeStreamView.tsx` — hardcoded
- `MyceliumCommandCenter.tsx` — hardcoded
- `WorkflowToolbar.tsx:169,210,244` — THREE separate hardcoded URLs (GAP_20 included)
- `PipelineResultsViewer.tsx:13` — hardcoded with `/debug` suffix
- `TaskDAGView.tsx:27` — hardcoded
- `SandboxDropdown.tsx:18` — hardcoded
- `OnboardingModal.tsx:15` — hardcoded with `/mcc` suffix

### Implementation
1. Create `client/src/config/api.config.ts`:
```typescript
// MARKER_176.15: Centralized API configuration
export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';
export const MCC_API = `${API_BASE}/mcc`;
export const DEBUG_API = `${API_BASE}/debug`;
export const ANALYTICS_API = `${API_BASE}/analytics`;
```

2. Replace all hardcoded `API_BASE` constants in 10+ files with import from config.

### Verification
```bash
cd client && grep -r "localhost:5001" src/components/ --include="*.tsx" | wc -l
# Should be 0 after fix
cd client && npx tsc --noEmit
cd client && npx vite build
```

### Marker Convention
Add `// MARKER_176.15` comment at each updated import site.

---

## Task 2: Edge Labels on DAG (MARKER_176.7)

**Priority:** HIGH — users can't see input/output matrix connections
**Lines:** ~80
**Can start:** IMMEDIATELY (no dependencies)

### Problem
Edge types defined (structural, dataflow, temporal, conditional, parallel_fork, parallel_join, feedback) but dagre `g.setEdge(source, target)` uses empty label. No label component in ReactFlow.

### Source Reference
- `client/src/utils/dagLayout.ts` — edge type definitions, `NOLAN_PALETTE` colors
- `docs/175_MCC_APP/SCOUT_MCC_AUDIT_2026-03-11.md` — GAP_7 description (line 70-76)
- Phase 135-144 edge type enum

### Implementation
1. In `dagLayout.ts`, ensure `g.setEdge()` passes label data:
```typescript
// MARKER_176.7: Edge labels with type and input/output matrix
g.setEdge(source, target, {
  label: edge.data?.label || edge.type || '',
  labelStyle: { fill: NOLAN_PALETTE.textMuted, fontSize: 8 },
});
```

2. Create custom edge component or use ReactFlow's `EdgeLabelRenderer`:
```typescript
// MARKER_176.7: Custom edge label renderer
const EDGE_TYPE_LABELS: Record<string, { label: string; color: string }> = {
  structural: { label: 'struct', color: NOLAN_PALETTE.textMuted },
  dataflow: { label: 'data →', color: '#4a9eff' },
  temporal: { label: 'then', color: '#ff9f43' },
  conditional: { label: 'if', color: '#ffd93d' },
  parallel_fork: { label: 'fork', color: '#6c5ce7' },
  parallel_join: { label: 'join', color: '#6c5ce7' },
  feedback: { label: 'feedback', color: '#ff6b6b' },
};
```

3. Add edge data to ReactFlow edges in the conversion function.

### Verification
- Visual: Open DAG view, edges should show type labels (small, monospace, Nolan style)
- Build: `cd client && npx vite build`

### Marker Convention
All edge label code: `// MARKER_176.7`

---

## Task 3: FirstRunView Error Handling (MARKER_176.18)

**Priority:** HIGH — users get stuck on project creation with no feedback
**Lines:** ~50
**Can start:** IMMEDIATELY (no dependencies)

### Problem
`FirstRunView.tsx` — POST `/api/mcc/project/init` on error: silently fails, no error state, no retry button. User clicks "Create", nothing happens.

### Source Reference
- `client/src/components/mcc/FirstRunView.tsx` — lines 152-160
- `docs/176_MCC_SPRINT/PHASE_176_ROADMAP.md` — GAP_18

### Implementation
1. Add error state:
```typescript
// MARKER_176.18: Error handling for project creation
const [createError, setCreateError] = useState<string | null>(null);
```

2. Update fetch handler with proper error catching:
```typescript
try {
  const res = await fetch(`${API_BASE}/mcc/project/init`, { ... });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    setCreateError(errData.detail || `Server error: ${res.status}`);
    return;
  }
  // ... success path
} catch (err) {
  setCreateError('Network error — check if backend is running');
}
```

3. Render error state with retry button:
```typescript
{createError && (
  <div style={{ color: '#ff6b6b', fontSize: 10, marginTop: 8 }}>
    {createError}
    <button onClick={() => setCreateError(null)}>Retry</button>
  </div>
)}
```

### Verification
- Test: Stop backend, try project create → should show error
- Test: Start backend, create project → should work
- Build: passes

---

## Task 4: Roadmap→Task Bridge Frontend (MARKER_176.1F)

**Priority:** CRITICAL — core workflow gap
**Lines:** ~80
**Can start:** AFTER Dragon completes MARKER_176.1B (backend API)

### Problem
User clicks roadmap node → stores `navRoadmapNodeId` in useMCCStore → but MCCTaskList ignores it. No "Create Tasks" action visible.

### Source Reference
- `client/src/components/mcc/RoadmapTaskNode.tsx` — click handler
- `client/src/store/useMCCStore.ts` — `drillDown()`, `navRoadmapNodeId`
- `docs/175_MCC_APP/SCOUT_MCC_AUDIT_2026-03-11.md` — GAP_1 (line 18-24)

### Backend API (provided by MARKER_176.1B)
```
POST /api/mcc/roadmap/{node_id}/create-tasks
Response: { tasks: [...], count: N }
```

### Implementation
1. In `useMCCStore.ts` LEVEL_CONFIG for 'tasks' level, add action:
```typescript
// MARKER_176.1F: Create tasks from roadmap node
{
  label: '+ Create Tasks',
  icon: '📋',
  action: 'createTasksFromRoadmap',
}
```

2. In `FooterActionBar.tsx` or `MyceliumCommandCenter.tsx`, handle the action:
```typescript
// MARKER_176.1F: Call backend to generate subtasks from roadmap node
if (action === 'createTasksFromRoadmap') {
  const nodeId = useMCCStore.getState().navRoadmapNodeId;
  if (!nodeId) return;
  const res = await fetch(`${API_BASE}/mcc/roadmap/${nodeId}/create-tasks`, { method: 'POST' });
  const data = await res.json();
  if (data.tasks) {
    await useMCCStore.getState().fetchTasks(); // Refresh task list
    // Toast: "Created {data.count} tasks from roadmap node"
  }
}
```

3. Show created tasks filtered by `roadmapNodeId` in MCCTaskList.

### Verification
- User Scenario: Click roadmap node → drill to tasks → click "Create Tasks" → see generated tasks
- Build: passes

---

## Task 5: Apply/Reject Frontend Wiring (MARKER_176.3F)

**Priority:** CRITICAL — users can't approve pipeline results
**Lines:** ~40
**Can start:** AFTER Dragon completes MARKER_176.3B (backend API)

### Problem
RailsActionBar at 'results' level has Apply/Reject buttons. `onApply()` and `onReject()` callbacks in MyceliumCommandCenter.tsx are NOT wired.

### Source Reference
- `client/src/components/mcc/MyceliumCommandCenter.tsx` — ~line 4857
- `docs/175_MCC_APP/SCOUT_MCC_AUDIT_2026-03-11.md` — GAP_3 (line 34-40)

### Backend API (provided by MARKER_176.3B)
```
POST /api/mcc/tasks/{id}/apply   → { success: true, task: {...} }
POST /api/mcc/tasks/{id}/reject  → { success: true, task: {...} }  (body: { feedback: string })
```

### Implementation
1. Wire `onApply` in results level action handler:
```typescript
// MARKER_176.3F: Apply pipeline results
const handleApply = async (taskId: string) => {
  await fetch(`${API_BASE}/mcc/tasks/${taskId}/apply`, { method: 'POST' });
  useMCCStore.getState().fetchTasks();
  useMCCStore.getState().goBack(); // Return to tasks level
};
```

2. Wire `onReject` with feedback from RedoFeedbackInput:
```typescript
// MARKER_176.3F: Reject with feedback → requeue
const handleReject = async (taskId: string, feedback: string) => {
  await fetch(`${API_BASE}/mcc/tasks/${taskId}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ feedback }),
  });
  useMCCStore.getState().fetchTasks();
};
```

### Verification
- User Scenario: Pipeline finishes → results level → click Apply → task marked "applied"
- User Scenario: Click Reject → feedback form → submit → task requeued with "rework" status
- Build: passes

---

## Test Scenarios (Codex runs after completing all tasks)

### MARKER_176.T8: Build Check
```bash
cd client && npx tsc --noEmit
cd client && VITE_MODE=mcc npx vite build
cd client && npx vite build
```

### MARKER_176.T9: User Scenario — Roadmap to Tasks
1. Open MCC → FirstRunView → enter folder path → Create project
2. See roadmap DAG with module nodes
3. Click a roadmap node → drill to tasks level
4. Click "Create Tasks" → see generated tasks
5. Verify: tasks have titles matching the roadmap module

### MARKER_176.T10: User Scenario — Edit, Dispatch, Apply
1. Select a task → click Edit → TaskEditPopup opens
2. Change workflow to "Ralph Solo" → Save
3. Click "Launch" → pipeline starts (running level)
4. Wait for completion → results level
5. Click "Apply" → task status = "applied", return to tasks
6. Alternatively: Click "Reject" → enter feedback → task requeued

### MARKER_176.T11: Edge Labels
1. Open any workflow DAG
2. Verify: edges show type labels (data, temporal, conditional, etc.)
3. Labels are small, monospace, Nolan-dark palette

---

## Deliverables Checklist

- [ ] MARKER_176.15 — api.config.ts + 10 file updates
- [ ] MARKER_176.7 — Edge labels rendering
- [ ] MARKER_176.18 — FirstRunView error handling
- [ ] MARKER_176.1F — Roadmap→Task frontend bridge
- [ ] MARKER_176.3F — Apply/Reject frontend wiring
- [ ] MARKER_176.T8 — Build passes
- [ ] MARKER_176.T9 — User scenario: Roadmap to Tasks
- [ ] MARKER_176.T10 — User scenario: Edit, Dispatch, Apply
- [ ] MARKER_176.T11 — Edge labels visible

**Report results to:** `docs/176_MCC_SPRINT/STATUS_CODEX_SPRINT1.md`
