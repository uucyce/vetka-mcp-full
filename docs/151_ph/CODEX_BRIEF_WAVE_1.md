# CODEX BRIEF — Wave 1: Critical UX Fixes
## Phase 151 | Tasks 151.1, 151.3, 151.4
**Priority: P0-P3 | "Make it work for humans"**
**Note: 151.2 (edges) already done by Opus — skip it.**

---

## OVERVIEW

3 tasks for Codex (151.2 done by Opus). Can be done in any order or parallel.
Goal: remove all showstoppers that prevent a normal human from using the DAG editor.

**After Wave 1:** User opens MCC → sees editable DAG → double-click → add node → drag handle → connection → clean straight edges → heartbeat via left-click dropdown.

**Rules:**
- Nolan palette only (grayscale + teal accent #4ecdc4)
- Monospace font everywhere
- No new npm dependencies unless strictly necessary
- No right-click for basic operations
- All inline styles (project convention — no CSS modules)

---

## 151.1 — HeartbeatChip → HeartbeatDropdown

### Problem
HeartbeatChip uses right-click for interval settings. Right-click in browser shows "Reload, Inspect Element" — user never discovers the settings. Interval is raw seconds (86399 = 24h) — inhuman.

### What to Build
Replace `HeartbeatChip.tsx` with a left-click dropdown that has:
1. **Start / Pause toggle** at top
2. **Preset intervals** with radio selection (human labels)
3. **Custom interval** input (in minutes)
4. **Status footer** — next tick time, total dispatched, last tick result

### Wireframe
```
⏱ [Every 30min ▾]  ← Left-click opens dropdown
┌──────────────────────────────┐
│  ● Start  /  ⏸ Pause         │  ← Toggle (green dot when active)
├──────────────────────────────┤
│  ○ 10 min                    │
│  ● 30 min                    │  ← Radio buttons, selected = ●
│  ○ 1 hour                    │
│  ○ 4 hours                   │
│  ○ 12 hours                  │
│  ○ 1 day                     │
│  ○ 1 week                    │
│  Custom: [___] min    [Set]  │  ← Number input + apply
├──────────────────────────────┤
│  Next: 12:34 (14m remaining) │  ← Countdown
│  Dispatched: 5 │ Last: OK    │  ← Stats
└──────────────────────────────┘
```

### Chip Display (closed state)
```
When OFF:   ⏱ Heartbeat off
When ON:    ⏱ 14m (with teal pulse animation)
```

### Technical Spec

**File:** `client/src/components/mcc/HeartbeatChip.tsx` (165 lines → rewrite in-place)

**Current code to replace (entire component):**
- Remove `onContextMenu` handler (line 68-71)
- Remove `showIntervalInput` state and popup (lines 87-153)
- Keep: `useMCCStore` import, `fmtInterval` helper, countdown timer logic, pulse animation

**New structure:**
```tsx
export function HeartbeatChip() {
  const { heartbeat, updateHeartbeat } = useMCCStore();
  const [open, setOpen] = useState(false);
  const [customMinutes, setCustomMinutes] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Existing countdown timer effect (keep as-is from lines 18-30)

  // Close on click outside
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  // Preset intervals (seconds)
  const PRESETS = [
    { label: '10 min', value: 600 },
    { label: '30 min', value: 1800 },
    { label: '1 hour', value: 3600 },
    { label: '4 hours', value: 14400 },
    { label: '12 hours', value: 43200 },
    { label: '1 day', value: 86400 },
    { label: '1 week', value: 604800 },
  ];

  const selectPreset = async (seconds: number) => {
    await updateHeartbeat({ interval: seconds });
  };

  const toggleHeartbeat = async () => {
    await updateHeartbeat({ enabled: !heartbeat?.enabled });
  };

  const applyCustom = async () => {
    const mins = parseInt(customMinutes);
    if (mins > 0) {
      await updateHeartbeat({ interval: mins * 60 });
      setCustomMinutes('');
    }
  };

  // ... render
}
```

**Chip onClick:** `() => setOpen(!open)` — toggle dropdown (NOT toggle heartbeat)
**Remove:** `onContextMenu` entirely — no right-click behavior

**Display format:**
- OFF: `⏱ Heartbeat off`
- ON: `⏱ 14m` (countdown, using existing `fmtInterval`)
- When dropdown is open: chip gets subtle border highlight

**Dropdown styling:**
- position: absolute, top: 100%, left: 0 (below chip)
- background: #1a1a1a, border: 1px solid #333, borderRadius: 6
- z-index: 1000
- width: 200px
- Font: monospace 10px
- Radio circles: ○ (unselected) / ● (selected) — use `•` character or 6px circle div

**Status footer:**
- Next tick: `last_tick + interval` formatted as HH:MM + `(Xm remaining)`
- Dispatched: `heartbeat.tasks_dispatched`
- Last tick result: show "OK" or nothing (we don't have failure tracking for ticks)

**Important:** Heartbeat toggle (start/stop) must NOT prevent manual task dispatch. These are independent systems. The `updateHeartbeat({ enabled: true/false })` only controls the heartbeat timer.

### Test
- Left-click chip → dropdown opens
- Select "1 hour" → interval updates to 3600 (verify via API: `GET /api/debug/heartbeat/settings`)
- Click Start → heartbeat enabled, teal pulse animation, countdown shows
- Click outside dropdown → closes
- Manual task dispatch still works while heartbeat is active

---

## 151.2 — Edge Routing Fix

### Problem
Edges use `smoothstep` which creates curved U-turns and roundabouts. Layout is too cramped (ranksep=80, nodesep=50). User says: "Not like ComfyUI/n8n where everything is simple."

### What to Change

**File 1: `client/src/utils/dagLayout.ts`**

**Change 1 — dagre config (line 110-116):**
```typescript
// BEFORE:
g.setGraph({
  rankdir: 'BT',
  ranksep: 80,
  nodesep: 50,
  marginx: 20,
  marginy: 20,
});

// AFTER (MARKER_151.2A):
g.setGraph({
  rankdir: 'BT',     // Keep: VETKA tree metaphor (root at bottom)
  ranksep: 120,       // Was 80 — more vertical breathing room
  nodesep: 80,        // Was 50 — more horizontal space
  edgesep: 20,        // New — minimum edge separation
  marginx: 30,
  marginy: 30,
});
```

**Change 2 — edge type (line 178):**
```typescript
// BEFORE:
type: 'smoothstep',

// AFTER (MARKER_151.2B):
type: 'step',         // Orthogonal routing — clean right-angle connections
```

**File 2: `client/src/components/mcc/DAGView.tsx`**

**Change 3 — connectionLineType (add to ReactFlow props, line 294-ish):**
```tsx
// ADD these props to <ReactFlow>:
connectionLineType="step"        // Preview while dragging uses same style
defaultEdgeOptions={{ type: 'step' }}  // New edges created by user are also step
```

### Verification
- Open MCC → see DAG → edges should be orthogonal (right-angle corners), not curved
- No U-turns, no roundabouts
- Edges between layers flow cleanly bottom → top
- More space between nodes (not cramped)

### Rollback Safety
If `step` edges look worse than expected, can fall back to `smoothstep` with just the spacing changes (ranksep/nodesep improvements are independent).

---

## 151.3 — editMode ON + Node Picker

### Problem
1. editMode is OFF by default → user can't create nodes, can't connect, can't right-click for menu
2. Node creation only via right-click context menu → user sees browser "Reload" instead
3. User expects ComfyUI-style: double-click canvas → search popup

### What to Change

**Part A: editMode default = true**

**File: `client/src/store/useMCCStore.ts`**
```typescript
// BEFORE (line 77):
editMode: boolean;  // initialized as false in create()

// Find the initial state in create() and change:
editMode: true,  // MARKER_151.3A: Edit mode ON by default
```

This alone enables: context menu on right-click, connections via handle drag, delete via keyboard.

**Part B: Node Picker on double-click**

**File: `client/src/components/mcc/DAGView.tsx`**

Add `onDoubleClick` handler to ReactFlow:
```tsx
// New state in DAGView parent (MyceliumCommandCenter.tsx):
const [nodePickerPos, setNodePickerPos] = useState<{x: number, y: number} | null>(null);

// In DAGView, add new prop:
onPaneDoubleClick?: (position: { x: number; y: number }) => void;

// In ReactFlow component, handle pane double-click:
onDoubleClick={(event) => {
  if (!editMode) return;
  // Get canvas position from mouse coordinates
  const bounds = event.currentTarget.getBoundingClientRect();
  onPaneDoubleClick?.({
    x: event.clientX - bounds.left,
    y: event.clientY - bounds.top,
  });
}}
```

**New file: `client/src/components/mcc/NodePicker.tsx`** (~120 lines)

Search popup that appears at double-click position:

```tsx
interface NodePickerProps {
  position: { x: number; y: number };
  onSelect: (type: DAGNodeType) => void;
  onClose: () => void;
}

const NODE_OPTIONS = [
  { type: 'agent',     icon: '●', label: 'Agent',     desc: 'AI agent node (scout, coder, verifier...)' },
  { type: 'task',      icon: '■', label: 'Task',      desc: 'Root task node' },
  { type: 'condition', icon: '◇', label: 'Condition', desc: 'If/else branch (diamond)' },
  { type: 'parallel',  icon: '═', label: 'Parallel',  desc: 'Parallel execution fork' },
  { type: 'loop',      icon: '↻', label: 'Loop',      desc: 'Retry/iteration loop' },
  { type: 'transform', icon: '▷', label: 'Transform', desc: 'Data transformation' },
  { type: 'group',     icon: '▢', label: 'Group',     desc: 'Container for sub-workflow' },
];

export function NodePicker({ position, onSelect, onClose }: NodePickerProps) {
  const [search, setSearch] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-focus search on mount
  useEffect(() => { inputRef.current?.focus(); }, []);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  // Close on click outside
  // ... (same pattern as HeartbeatDropdown)

  // Filter by search
  const filtered = NODE_OPTIONS.filter(opt =>
    opt.label.toLowerCase().includes(search.toLowerCase()) ||
    opt.desc.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div style={{
      position: 'fixed',
      left: position.x,
      top: position.y,
      background: '#1a1a1a',
      border: '1px solid #333',
      borderRadius: 6,
      padding: 4,
      zIndex: 1000,
      width: 220,
      fontFamily: 'monospace',
      fontSize: 11,
    }}>
      <input
        ref={inputRef}
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder="search nodes..."
        style={{
          width: '100%',
          background: 'rgba(255,255,255,0.05)',
          border: '1px solid #333',
          borderRadius: 3,
          color: '#ccc',
          padding: '4px 8px',
          fontSize: 11,
          fontFamily: 'monospace',
          marginBottom: 4,
          boxSizing: 'border-box',
        }}
      />
      {filtered.map(opt => (
        <div
          key={opt.type}
          onClick={() => { onSelect(opt.type as DAGNodeType); onClose(); }}
          style={{
            padding: '5px 8px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            borderRadius: 3,
            color: '#ccc',
          }}
          onMouseEnter={e => (e.currentTarget.style.background = '#222')}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
        >
          <span style={{ color: '#666', width: 14, textAlign: 'center' }}>{opt.icon}</span>
          <span>{opt.label}</span>
          <span style={{ color: '#555', fontSize: 9, marginLeft: 'auto' }}>{opt.desc}</span>
        </div>
      ))}
      {filtered.length === 0 && (
        <div style={{ padding: '8px', color: '#555', textAlign: 'center' }}>no matches</div>
      )}
    </div>
  );
}
```

**Wiring in `MyceliumCommandCenter.tsx`:**
```tsx
// Add state:
const [nodePickerPos, setNodePickerPos] = useState<{x: number, y: number} | null>(null);

// Pass to DAGView:
<DAGView
  // ...existing props
  onPaneDoubleClick={(pos) => setNodePickerPos(pos)}
/>

// Render NodePicker:
{nodePickerPos && (
  <NodePicker
    position={nodePickerPos}
    onSelect={(type) => {
      dagEditor.addNode(type, nodePickerPos, type);
      setNodePickerPos(null);
    }}
    onClose={() => setNodePickerPos(null)}
  />
)}
```

### Keep existing context menu
Right-click context menu (`DAGContextMenu.tsx`) stays as a fallback for power users. Don't remove it. editMode=true means it now actually works.

### Test
- Open MCC → DAG is immediately editable (no need to click "edit" first)
- Double-click on empty canvas → NodePicker appears at cursor position
- Type "co" → filters to "Condition" and "Coder"-like matches
- Click "Agent" → agent node appears on canvas
- Press Escape → picker closes
- Right-click still works (context menu with same 7 types)

---

## 151.4 — Connection Handles Always Visible

### Problem
Connection handles (source/target ports on nodes) are only visible on hover. User doesn't know they can drag to connect. No visual feedback during drag (valid vs invalid connection).

### What to Change

**File: `client/src/components/mcc/DAGView.tsx`**

**Change 1 — Add global handle styles (append to existing `<style>` block, line 329-386):**
```css
/* MARKER_151.4A: Always-visible connection handles */
.react-flow__handle {
  width: 8px !important;
  height: 8px !important;
  background: #333 !important;
  border: 1px solid #555 !important;
  border-radius: 50% !important;
  opacity: 1 !important;          /* Always visible, not hover-only */
  transition: all 0.15s ease;
}

.react-flow__handle:hover {
  background: #4ecdc4 !important;  /* Teal on hover */
  border-color: #4ecdc4 !important;
  transform: scale(1.3);
}

/* Drag preview — connecting state */
.react-flow__handle.connecting {
  background: #4ecdc4 !important;
  box-shadow: 0 0 6px rgba(78, 205, 196, 0.6);
}

/* Connection line while dragging */
.react-flow__connection-line {
  stroke: #4ecdc4 !important;
  stroke-width: 2 !important;
}
```

**Change 2 — Valid/invalid connection feedback:**

Add `isValidConnection` prop to `<ReactFlow>`:
```tsx
isValidConnection={(connection) => {
  // Prevent self-connections
  if (connection.source === connection.target) return false;
  // Prevent duplicate edges
  const exists = edges.some(
    e => e.source === connection.source && e.target === connection.target
  );
  return !exists;
}}
```

The valid/invalid state is shown by xyflow automatically via CSS classes (`.react-flow__handle.valid` / `.react-flow__handle.invalid`). Add styles:
```css
.react-flow__handle.valid {
  background: #4ecdc4 !important;  /* Green/teal = can connect */
}

.react-flow__handle.invalid {
  background: #ff4444 !important;  /* Red = can't connect */
}
```

### Node Handle Placement

The individual node components (TaskNode, AgentNode, etc.) should already have `<Handle>` components with `type="source"` and `type="target"`. Verify that each node type has both:
- `<Handle type="target" position={Position.Bottom} />` (input from below)
- `<Handle type="source" position={Position.Top} />` (output going up)

This follows our BT (bottom-to-top) layout: data flows upward.

### Test
- All node handles visible as small circles (even without hovering)
- Hover over handle → turns teal, slightly larger
- Drag from handle → teal connection preview line follows cursor
- Drop on valid target → connection created
- Drop on self or duplicate → no connection (red indicator briefly)

---

## SUMMARY — All 4 Tasks

| Task | File(s) | Effort | Risk |
|------|---------|--------|------|
| 151.1 HeartbeatDropdown | `HeartbeatChip.tsx` (rewrite) | S | Low — self-contained |
| 151.2 Edge Routing | `dagLayout.ts`, `DAGView.tsx` | S | Low — config change |
| 151.3 editMode + NodePicker | `useMCCStore.ts`, `DAGView.tsx`, new `NodePicker.tsx`, `MCC.tsx` | M | Medium — wiring |
| 151.4 Handles Visible | `DAGView.tsx` (CSS + isValidConnection) | S | Low — CSS only |

**Order:** Any order works. Recommended: 151.2 → 151.4 → 151.1 → 151.3 (quick wins first, then bigger NodePicker).

**No backend changes needed.** All Wave 1 is pure frontend.

---

*Cursor Brief by Opus Commander | Phase 151 Wave 1 | 2026-02-15*
