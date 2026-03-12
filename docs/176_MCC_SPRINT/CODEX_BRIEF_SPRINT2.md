# Codex Brief — Sprint 2B Frontend (Phase 176)

> **Source:** `docs/176_MCC_SPRINT/PHASE_176_ROADMAP.md`
> **Agent:** Codex
> **Sprint:** 2B (parallel with Dragon Gold Sprint 2A)
> **Prerequisite:** Sprint 1 complete (edge labels, API config, apply/reject wired)
> **Estimated:** 480 lines across 4 tasks
> **Markers:** MARKER_176.9, MARKER_176.10, MARKER_176.16, MARKER_176.19

---

## Task 1: MYCO Proactive Guidance System (MARKER_176.9)

**Priority:** HIGH — new users get no contextual help
**Lines:** ~100
**Files:** NEW `client/src/components/mcc/MycoHints.tsx`, `client/src/store/useMCCStore.ts`

### Problem
MYCO only responds to explicit `/myco` trigger. Doesn't suggest help unprompted at each navigation level.

### Source Reference
- `client/src/components/mcc/MyceliumCommandCenter.tsx` — MYCO trigger check
- `client/src/store/useMCCStore.ts` — `navLevel`, LEVEL_CONFIG
- `docs/175_MCC_APP/SCOUT_MCC_AUDIT_2026-03-11.md` — GAP_9 (line 86-92)

### Implementation
1. Create `MycoHints.tsx` — level-specific hint component:
```typescript
// MARKER_176.9: MYCO Proactive Hints
const LEVEL_HINTS: Record<NavLevel, { text: string; action?: string }> = {
  first_run: { text: "Welcome! Point me to a codebase folder, Git URL, or describe your project.", action: "create" },
  roadmap: { text: "Click any module to drill into its tasks. Or add a new task manually.", action: "drill" },
  tasks: { text: "Select a task to edit, choose a workflow, and launch it.", action: "launch" },
  workflow: { text: "This is your execution plan. Run it or edit individual nodes.", action: "run" },
  running: { text: "Pipeline is executing. Watch agent progress in real-time.", action: "wait" },
  results: { text: "Review results. Apply to accept, or reject with feedback to retry.", action: "review" },
};
```

2. Add `mycoHintDismissed: Record<NavLevel, boolean>` to useMCCStore for dismissal tracking.

3. Render as a small floating hint bar (bottom-left, above MiniWindows):
   - Shows on first visit to each level
   - Dismisses on click or after 10 seconds
   - Style: Nolan-dark, small monospace, 30% opacity → 100% on hover

### Verification
- Navigate to each level → see contextual hint
- Dismiss hint → doesn't reappear on same level
- MARKER_176.T14: User scenario test

---

## Task 2: TaskDAGView Component (MARKER_176.10)

**Priority:** HIGH — users can't see task dependency graph
**Lines:** ~310
**Files:** NEW `client/src/components/mcc/TaskDAGView.tsx`

### Problem
Backend `/api/analytics/dag/tasks` endpoint exists. Frontend component MISSING.
Users can only see individual workflow DAGs, not the cross-task dependency graph.

### Source Reference
- `src/api/routes/analytics_routes.py` — `/api/analytics/dag/tasks` endpoint
- `client/src/utils/dagLayout.ts` — existing DAG layout utilities
- `client/src/components/mcc/DAGView.tsx` — existing workflow DAG (pattern to follow)
- `docs/175_MCC_APP/SCOUT_MCC_AUDIT_2026-03-11.md` — GAP_10 (line 94-100)

### Implementation
1. Create `TaskDAGView.tsx` following DAGView.tsx pattern:
```typescript
// MARKER_176.10: Task Dependency DAG View
import ReactFlow, { Node, Edge } from 'reactflow';
import { NOLAN_PALETTE, layoutDAG } from '../../utils/dagLayout';

export function TaskDAGView({ projectId }: { projectId?: string }) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  useEffect(() => {
    // Fetch task dependency data
    fetch(`${API_BASE}/analytics/dag/tasks`)
      .then(res => res.json())
      .then(data => {
        const { nodes: dagNodes, edges: dagEdges } = layoutDAG(data.nodes, data.edges);
        setNodes(dagNodes);
        setEdges(dagEdges);
      });
  }, [projectId]);

  return (
    <div style={{ width: '100%', height: '100%', background: NOLAN_PALETTE.bg }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        nodeTypes={taskNodeTypes}  // Reuse RoadmapTaskNode
      />
    </div>
  );
}
```

2. Task nodes show: title, status badge (pending/running/done), workflow family icon.

3. Edges show: dependency type (blocks, follows, related), using edge labels from MARKER_176.7.

4. Add toggle in useMCCStore: `dagMode: 'workflow' | 'tasks'` to switch between DAGView and TaskDAGView.

5. Wire into Matryoshka navigation — accessible from roadmap level action bar.

### Verification
- Fetch from `/api/analytics/dag/tasks` → renders task graph
- Nodes clickable → drill to task detail
- Edge labels visible with dependency types
- Toggle between workflow DAG and task DAG
- MARKER_176.T15: User scenario test

---

## Task 3: MiniStats Real Data (MARKER_176.16)

**Priority:** MEDIUM — users see fake data on error
**Lines:** ~40
**Files:** `client/src/components/mcc/MiniStats.tsx`

### Problem
MiniStats falls back to placeholder data on fetch error. Shows `success_rate: 87.5, avg_duration_s: 142` even when no pipelines have run.

### Source Reference
- `client/src/components/mcc/MiniStats.tsx` — lines 155-210
- `docs/176_MCC_SPRINT/PHASE_176_ROADMAP.md` — GAP_16

### Implementation
```typescript
// MARKER_176.16: Real data or "No data" state (no fake fallbacks)
const [hasData, setHasData] = useState(false);
const [fetchError, setFetchError] = useState<string | null>(null);

// In fetch handler:
if (!res.ok) {
  setFetchError(`API error: ${res.status}`);
  setHasData(false);
  return;
}
const data = await res.json();
if (data.total_pipelines === 0) {
  setHasData(false); // No pipelines yet — show empty state
} else {
  setHasData(true);
  setStats(data);
}

// In render:
if (fetchError) return <div style={errorStyle}>⚠ {fetchError}</div>;
if (!hasData) return <div style={emptyStyle}>No pipeline data yet. Launch a task to see stats.</div>;
```

### Verification
- No pipelines: shows "No pipeline data yet"
- Backend down: shows error, not fake data
- Real data: shows actual stats
- MARKER_176.T17

---

## Task 4: MiniChat API Contract Fix (MARKER_176.19)

**Priority:** MEDIUM — chat fails silently on API mismatch
**Lines:** ~30
**Files:** `client/src/components/mcc/MiniChat.tsx`

### Problem
MiniChat POST to `/api/chat/quick` expects `.response` or `.message` field but no defensive typing. If API returns different format, chat shows "(no response)" forever.

### Source Reference
- `client/src/components/mcc/MiniChat.tsx` — lines 438, 475-477
- `docs/176_MCC_SPRINT/PHASE_176_ROADMAP.md` — GAP_19

### Implementation
```typescript
// MARKER_176.19: Typed API response with defensive fallback
interface ChatQuickResponse {
  response?: string;
  message?: string;
  error?: string;
}

// In fetch handler:
const data: ChatQuickResponse = await res.json();
const reply = data.response || data.message || data.error || '(empty response from server)';
if (data.error) {
  // Show as error-styled message
  addMessage({ role: 'system', content: `Error: ${data.error}` });
} else {
  addMessage({ role: 'assistant', content: reply });
}
```

### Verification
- Send message → receive typed response
- API returns error → shows error-styled message
- API returns unexpected format → shows "(empty response from server)"

---

## Test Scenarios

### MARKER_176.T14: MYCO Proactive Hints
1. Open MCC → navigate to roadmap level
2. Verify: hint appears "Click any module to drill into its tasks"
3. Click hint → dismisses
4. Navigate to tasks level → new hint appears
5. Navigate back to roadmap → no hint (already dismissed)

### MARKER_176.T15: TaskDAGView
1. Open MCC → have tasks with dependencies
2. Toggle to TaskDAGView
3. Verify: task nodes with status badges
4. Verify: dependency edges with labels
5. Click a task node → drill to task detail

### MARKER_176.T17: MiniStats States
1. No pipeline data → "No pipeline data yet" message
2. Backend offline → error indicator
3. After running pipeline → real stats shown

---

## Deliverables Checklist

- [ ] MARKER_176.9 — MycoHints.tsx + useMCCStore hint state
- [ ] MARKER_176.10 — TaskDAGView.tsx + DAG toggle
- [ ] MARKER_176.16 — MiniStats real data / empty state
- [ ] MARKER_176.19 — MiniChat typed response
- [ ] MARKER_176.T14 — MYCO proactive test
- [ ] MARKER_176.T15 — TaskDAGView test
- [ ] MARKER_176.T17 — MiniStats states test

**Report results to:** `docs/176_MCC_SPRINT/STATUS_CODEX_SPRINT2.md`
