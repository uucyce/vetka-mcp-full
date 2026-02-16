# Codex Brief — Wave 3B: MCC UX Polish

**Status:** READY FOR CODEX
**Agent:** Codex Stream B (parallel with Wave 3A)
**Estimated:** 1 session
**Depends on:** Wave 1-2 complete. **Independent from Wave 3A** (no file conflicts)

---

## Goal

Fix UX issues found in the MCC audit. Remove unnecessary always-visible buttons, make controls contextual and adaptive, replace browser `prompt()` dialogs with Nolan-styled inline inputs. Fix right column panel stacking.

**This stream modifies 2 existing files. Creates 0 new files.**

---

## UX Philosophy (from Grok Research)

> Every control answers WHO, WHERE, or WHEN. If it doesn't, it's noise — remove it.
> Panel = Zoom: compact in DAG right column, expanded as DevPanel tab. Same component, mode prop.
> "Grandma pressed 3 buttons and launched it." — no jargon, no hidden modes, no unnecessary clutter.
> "Batman Nolan, not Burton." — grayscale base, teal accent, zero unnecessary color.

---

## Task B1: WorkflowToolbar Contextual Buttons (MARKER_152.W3B1)

### Modify: `client/src/components/mcc/WorkflowToolbar.tsx`

**Current problems:**
1. **Validate** button always visible even on empty workflows (0 nodes)
2. **Generate** button visible even when editing a loaded workflow (risk of overwrite)
3. **Save** uses browser `prompt()` for name input — breaks Nolan aesthetic
4. **Generate** uses browser `prompt()` for description — same problem

**Fix 1: Validate — contextual visibility**

The `WorkflowToolbar` already receives `dagNodes` via its props (or we pass `nodeCount`).

Add a new prop:
```typescript
interface WorkflowToolbarProps {
  // ... existing props
  nodeCount?: number;  // NEW: number of DAG nodes
}
```

Then wrap Validate button:
```tsx
{/* MARKER_152.W3B1: Only show Validate when workflow has nodes */}
{(nodeCount ?? 0) > 0 && (
  <button onClick={handleValidate} style={...}>
    Validate ✓
  </button>
)}
```

**Fix 2: Generate — contextual visibility**

Hide Generate when workflow has unsaved changes (dirty state):
```tsx
{/* MARKER_152.W3B1: Hide Generate when editing unsaved workflow */}
{!isDirty && (
  <button onClick={() => setShowGenerateInput(true)} style={...}>
    + Generate
  </button>
)}
```

Add prop: `isDirty?: boolean`

**Fix 3: Save — replace prompt() with inline input**

Replace:
```typescript
// OLD:
const name = prompt('Workflow name:', workflowName || 'Untitled');
```

With inline state + input:
```typescript
const [showNameInput, setShowNameInput] = useState(false);
const [nameValue, setNameValue] = useState('');

// In Save handler:
const handleSave = () => {
  if (!workflowName || workflowName === 'Untitled Workflow') {
    setNameValue(workflowName || '');
    setShowNameInput(true);
    return;
  }
  doSave(workflowName);
};

const doSave = async (name: string) => {
  setShowNameInput(false);
  // ... existing save logic with the given name
};
```

In JSX, next to Save button:
```tsx
{showNameInput && (
  <div style={{
    display: 'flex', gap: 3, alignItems: 'center',
  }}>
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
        borderRadius: 2,
        color: '#e0e0e0',
        padding: '3px 6px',
        fontSize: 10,
        fontFamily: 'monospace',
        outline: 'none',
        width: 140,
      }}
    />
    <button
      onClick={() => nameValue.trim() && doSave(nameValue.trim())}
      style={{
        background: 'rgba(78,205,196,0.12)',
        border: `1px solid rgba(78,205,196,0.3)`,
        borderRadius: 2,
        color: '#4ecdc4',
        padding: '3px 6px',
        fontSize: 9,
        fontFamily: 'monospace',
        cursor: 'pointer',
      }}
    >
      ✓
    </button>
  </div>
)}
```

**Fix 4: Generate — replace prompt() with inline input**

Same pattern as Save. Replace `prompt()` with:
```typescript
const [showGenerateInput, setShowGenerateInput] = useState(false);
const [generateValue, setGenerateValue] = useState('');
```

In JSX, inline input appears when Generate clicked:
```tsx
{showGenerateInput && (
  <div style={{ display: 'flex', gap: 3, alignItems: 'center' }}>
    <input
      autoFocus
      value={generateValue}
      onChange={e => setGenerateValue(e.target.value)}
      onKeyDown={e => {
        if (e.key === 'Enter' && generateValue.trim()) {
          doGenerate(generateValue.trim());
          setShowGenerateInput(false);
        }
        if (e.key === 'Escape') setShowGenerateInput(false);
      }}
      placeholder="describe workflow..."
      style={{
        background: 'rgba(255,255,255,0.04)',
        border: `1px solid ${NOLAN_PALETTE.border}`,
        borderRadius: 2,
        color: '#e0e0e0',
        padding: '3px 6px',
        fontSize: 10,
        fontFamily: 'monospace',
        outline: 'none',
        width: 200,
      }}
    />
    <button onClick={() => { doGenerate(generateValue.trim()); setShowGenerateInput(false); }}
      style={{ /* same teal confirm style */ }}
    >
      ✓
    </button>
  </div>
)}
```

### Props Update from MCC:

In `MyceliumCommandCenter.tsx`, pass these new props to WorkflowToolbar:
```tsx
<WorkflowToolbar
  // ... existing props
  nodeCount={effectiveNodes.length}
  isDirty={dagEditor.isDirty}  // or track dirty state from dagEditor
/>
```

**Note for Codex:** Check how `isDirty` / dirty state is tracked. The toolbar already shows `*` next to workflow name when dirty — use the same source.

---

## Task B2: MCCDetailPanel Context Awareness (MARKER_152.W3B2)

### Modify: `client/src/components/mcc/MCCDetailPanel.tsx`

**Current problem:** ArchitectChat (compact) + PipelineStats (compact) are ALWAYS rendered at the bottom of the right column, consuming 230-350px even when irrelevant (e.g., viewing node stream or task results).

**Fix: Show bottom panels based on mode.**

Current rendering (always):
```tsx
{/* MARKER_151.9 */}
<PipelineStats tasks={tasks} mode="compact" />
{/* MARKER_151.8 */}
<ArchitectChat mode="compact" />
```

Change to contextual:
```tsx
{/* MARKER_152.W3B2: Contextual bottom panels */}
{/* Stats compact: show in overview, task_info, task_results, task_running */}
{mode !== 'dag_node' && (
  <div style={{ marginTop: 10, paddingTop: 10, borderTop: `1px solid ${NOLAN_PALETTE.borderDim}` }}>
    <PipelineStats tasks={tasks} mode="compact" />
  </div>
)}

{/* Architect chat compact: show only in overview and task_info (where user is thinking) */}
{(mode === 'overview' || mode === 'task_info') && (
  <div data-onboarding="architect-chat" style={{ marginTop: 10, paddingTop: 10, borderTop: `1px solid ${NOLAN_PALETTE.borderDim}`, minHeight: 230, maxHeight: 320 }}>
    <ArchitectChat mode="compact" />
  </div>
)}
```

**Visibility matrix:**

| Mode | PipelineStats compact | ArchitectChat compact | Rationale |
|------|----------------------|----------------------|-----------|
| `overview` | ✅ show | ✅ show | User exploring, chat relevant |
| `task_info` | ✅ show | ✅ show | User considering a task, chat relevant |
| `task_running` | ✅ show | ❌ hide | User monitoring progress, chat distracting |
| `task_results` | ✅ show | ❌ hide | User reviewing results, chat distracting |
| `dag_node` (info) | ❌ hide | ❌ hide | Full height for node details |
| `dag_node` (stream) | ❌ hide | ❌ hide | Full height for stream content |

**Note:** `dag_node` mode already returns early (line ~269) before reaching the bottom panels. So `mode !== 'dag_node'` only applies to the non-early-return section. Since the bottom panels are rendered in the main return (after the dag_node early-return), just wrap them with the mode checks shown above.

This recovers ~300px of vertical space when viewing node details, results, or running progress.

---

## Task B3: Execute Button Adaptive State (MARKER_152.W3B3)

### Modify: `client/src/components/mcc/MyceliumCommandCenter.tsx`

**Current:** Execute button always clickable. Shows error message after click if no workflow.

**Fix:** Disable when nothing to execute.

Find the Execute button in the header (search for "Execute" in MCC). Add disabled logic:

```tsx
const canExecute = effectiveNodes.length > 0 || tasks.some(t => t.status === 'pending');

<button
  onClick={handleExecute}
  disabled={!canExecute}
  title={canExecute ? 'Execute workflow' : 'Load or create a workflow first'}
  style={{
    // ... existing styles
    opacity: canExecute ? 1 : 0.3,
    cursor: canExecute ? 'pointer' : 'not-allowed',
  }}
>
  ▶ Execute
</button>
```

**Logic:** Execute is enabled when:
- Workflow has nodes (workflow execution), OR
- Tasks are pending in queue (dispatch execution)

---

## Files

| Action | File | Est. Lines Changed |
|--------|------|--------------------|
| **MODIFY** | `client/src/components/mcc/WorkflowToolbar.tsx` | +80, -20 |
| **MODIFY** | `client/src/components/mcc/MCCDetailPanel.tsx` | +10, -6 |
| **MODIFY** | `client/src/components/mcc/MyceliumCommandCenter.tsx` | +8, -2 |

**Total: ~90 lines added, ~28 removed**

---

## DO NOT

1. ❌ Do NOT touch backend files
2. ❌ Do NOT modify `TaskDAGView.tsx` or `TaskDAGNode.tsx` (that's Wave 3A)
3. ❌ Do NOT modify `DAGView.tsx`
4. ❌ Do NOT modify `panels/ArchitectChat.tsx` or `panels/PipelineStats.tsx` (they work fine)
5. ❌ Do NOT modify `StatsDashboard.tsx` or `TaskDrillDown.tsx`
6. ❌ Do NOT install new npm packages
7. ❌ Do NOT modify stores
8. ❌ Do NOT delete components — only modify visibility/behavior

## DO

1. ✅ Use `NOLAN_PALETTE` for all new styling
2. ✅ Monospace font for all inputs
3. ✅ Use MARKER_152.W3B1 / MARKER_152.W3B2 / MARKER_152.W3B3 in comments
4. ✅ Run `npx tsc --noEmit` before committing
5. ✅ Test that ArchitectChat compact still works when visible (overview mode)
6. ✅ Test that PipelineStats ↗ expand button still works

---

## Test Plan

### B1: WorkflowToolbar
1. Open MCC → Enter edit mode → New workflow (0 nodes) → **Validate button NOT visible**
2. Add a node to workflow → **Validate button appears**
3. Click Save on "Untitled" workflow → **inline input appears** (NOT browser prompt)
4. Type name + Enter → workflow saves with that name
5. Press Escape on inline input → input closes, no save
6. Click Generate → **inline description input appears** (NOT browser prompt)
7. Load an existing workflow → make changes → Generate button **hidden** (dirty)

### B2: MCCDetailPanel
1. No selection (overview mode) → **both** PipelineStats compact AND ArchitectChat compact visible
2. Click a task (task_info mode) → **both** visible
3. Select a running task → **PipelineStats visible**, ArchitectChat **hidden**
4. Select a done task (task_results) → **PipelineStats visible**, ArchitectChat **hidden**
5. Click a DAG node → right panel shows node info, **no bottom panels** (full height)
6. ArchitectChat ↗ button → opens DevPanel Architect tab (still works)
7. PipelineStats ↗ button → opens DevPanel Stats tab (still works)

### B3: Execute Button
1. No workflow loaded, no pending tasks → Execute **disabled** (grayed out, 30% opacity)
2. Load a workflow → Execute **enabled**
3. Add a pending task → Execute **enabled** (even without workflow)

---

## Parallel Safety

**Wave 3A** touches: `TaskDAGView.tsx` (NEW), `TaskDAGNode.tsx` (NEW), `MyceliumCommandCenter.tsx` (toggle + conditional DAG render)

**Wave 3B** touches: `WorkflowToolbar.tsx`, `MCCDetailPanel.tsx`, `MyceliumCommandCenter.tsx` (Execute button only)

**Potential conflict:** Both touch `MyceliumCommandCenter.tsx`. But:
- Wave 3A adds toggle bar + DAG conditional in the **center column area** (lines ~660-740)
- Wave 3B adds Execute disabled logic in the **header area** (lines ~510-540) + passes new props to WorkflowToolbar (line ~600)

**Resolution:** Wave 3A runs first, Wave 3B runs second on the updated file. OR Codex B only touches the header section and WorkflowToolbar props — no overlap with center column.

**Safest approach:** Run Wave 3A first, then Wave 3B. If running in parallel, Wave 3B should ONLY modify `WorkflowToolbar.tsx` and `MCCDetailPanel.tsx` in its session, and the MCC changes (B3 Execute + B1 WorkflowToolbar props) are deferred to a quick merge pass.
