# DAG Panel Optimization Research
## MARKER_137.RESEARCH — MCC DAG Panel Redesign

**Phase:** 137 (Cursor assignment)
**Date:** 2026-02-13
**Author:** Opus Commander (synthesis of Haiku audit + Sonnet research)
**Target:** `/client/src/components/mcc/` — full DAG panel overhaul

---

## 1. Executive Summary

The MCC DAG panel has ~80% of its visual infrastructure built but suffers from three critical gaps:
1. **Non-functional controls** — 13 filter buttons at top, most do nothing
2. **No connection intelligence** — clicking a node doesn't highlight its edges or connected nodes
3. **Disconnected live stream** — agent output streams in a separate panel instead of inside the DAG

This document proposes a phased redesign that eliminates button noise, embeds functionality into the graph itself, and adds league/preset management directly in the DAG panel.

---

## 2. Current State Audit

### 2.1 Component Inventory

| Component | File | Status | Issues |
|-----------|------|--------|--------|
| DAGView | `DAGView.tsx` | Working | Nodes not draggable (reported), no edge highlighting |
| FilterBar | `FilterBar.tsx` | Broken | 13 buttons, STATUS/TIME work partially, TYPE filter never applied |
| DetailPanel | `DetailPanel.tsx` | Working | RoleEditor added, but preset list too long/scrollable |
| TaskNode | `nodes/TaskNode.tsx` | Working | No click feedback beyond selection |
| AgentNode | `nodes/AgentNode.tsx` | Working | Shows role badge, model info |
| SubtaskNode | `nodes/SubtaskNode.tsx` | Working | Token count display |
| ProposalNode | `nodes/ProposalNode.tsx` | Working | Confidence bar |

### 2.2 What Works
- Sugiyama BT layout (root at bottom, proposals at top)
- Custom node types with Nolan grayscale palette
- Node click → DetailPanel shows node metadata
- RoleEditor for agent nodes (model per preset + prompt editing)
- Incremental layout with position preservation
- CSS fade-in animations for new nodes
- Animated edges for temporal connections

### 2.3 What's Broken

#### Critical
1. **TYPE filter buttons don't work** — `FilterBar` dispatches `type` filter but `fetchDAGNodes()` in MyceliumCommandCenter never adds `type` to API query params
2. **No edge highlighting on node select** — `getConnectedEdges` from xyflow is not imported or used; clicking a node doesn't dim unrelated edges
3. **Node dragging broken** — user reports nodes stopped being draggable (needs investigation — `nodesDraggable={true}` is set)

#### UX Problems
4. **13 filter buttons** — STATUS(4) + TIME(3) + TYPE(4) + search + global reset = visual noise
5. **Preset list is a vertical scroll** — should be a top-level league selector (tabs/chips)
6. **No live agent stream in DAG** — stream is in separate chat/DevPanel, creating cognitive split
7. **No edge click handler** — can't inspect connections
8. **getNodeColor function defined but passed as `() => '#666'`** to MiniMap — dead code

### 2.4 Dead Code / Redundancy
- `getNodeColor` callback (line 130-138 in DAGView.tsx) — defined but overridden by `() => '#666'`
- `MiniMap nodeColor` always returns `#666` regardless of status
- FilterBar TYPE section — wired but params never sent to API
- `edgeStrength` calculations exist but edge thickness barely visible on dark bg

---

## 3. Industry Best Practices Research

### 3.1 Analyzed Systems

| System | Key UX Pattern | Applicable to VETKA |
|--------|---------------|---------------------|
| **Apache Airflow** | Grid view + Gantt + Graph as tabs; status color-coded squares | Status indicators via node border/glow |
| **Prefect 2** | Radar view with concentric rings; minimal chrome | Minimal buttons, graph-first interaction |
| **Dagster** | Asset lineage graph with sidebar detail; filter as search | Search-first filtering, sidebar for detail |
| **n8n** | Canvas-first workflow builder; inline node editing | Inline editing directly on nodes |
| **LangGraph Studio** | Thread-based execution view; step highlighting | Live execution highlighting per-node |

### 3.2 Key Patterns Extracted

#### Pattern 1: Graph-First Interaction (n8n, Dagster)
- **Principle:** The graph IS the interface. No separate button bars for actions that can be done on the graph itself.
- **Application:** Remove FilterBar entirely. Replace with:
  - Right-click context menu on nodes
  - Click node → highlight connections + show detail
  - Double-click node → inline edit
  - Cmd+F → search nodes (keyboard shortcut, no persistent search bar)

#### Pattern 2: Progressive Disclosure (Prefect, Dagster)
- **Principle:** Show minimal info by default, expand on interaction.
- **Application:**
  - Nodes show only: icon + label + status dot
  - Hover → tooltip with model, tokens, duration
  - Click → DetailPanel with full editing
  - No permanent filter buttons

#### Pattern 3: Edge Intelligence (All systems)
- **Principle:** Edges carry meaning. On node select, dim everything except the selected node's connections.
- **Application:**
  - Click node → connected edges brighten to `#fff`, others fade to `opacity: 0.1`
  - Connected nodes get subtle border highlight
  - Click edge → show data flow info (tokens passed, etc.)

#### Pattern 4: Execution Embedding (LangGraph Studio)
- **Principle:** Show execution state directly on nodes, not in a separate log panel.
- **Application:**
  - Running node gets animated border pulse + inline progress text
  - Completed node shows checkmark + duration badge
  - Failed node shows X + error summary on hover
  - Stream output appears as a floating tooltip near the active node

#### Pattern 5: Preset/Template as First-Class (n8n)
- **Principle:** Templates are not buried in settings — they're a top-level concept.
- **Application:**
  - League selector as horizontal tabs at very top of DAG panel
  - Each league shows its team composition as visual preview
  - Edit league → opens inline editor, not a modal
  - "New League" button creates a copy of current

---

## 4. Proposed Architecture

### 4.1 Layout Redesign

```
+----------------------------------------------------------+
| [Dragon Bronze] [Dragon Silver] [Dragon Gold] [+ New]    |  <- League Tabs
+----------------------------------------------------------+
|                                                          |
|                    DAG CANVAS                            |
|                                                          |
|           ┌─────────┐                                   |
|           │Proposal │  ← Layer 4 (top)                  |
|           └────┬────┘                                   |
|                │                                        |
|           ┌────┴────┐                                   |
|           │Verifier │  ← Layer 3                        |
|           └────┬────┘                                   |
|       ┌────────┼────────┐                               |
|  ┌────┴───┐┌───┴───┐┌───┴───┐                          |
|  │Cache   ││Redis  ││Update │  ← Layer 2 (subtasks)    |
|  │Service ││Client ││APIs   │                          |
|  └────┬───┘└───┬───┘└───┬───┘                          |
|       └────────┼────────┘                               |
|       ┌────────┼────────┐                               |
|  ┌────┴───┐┌───┴────┐┌──┴─────┐                        |
|  │@scout  ││@arch   ││@research│ ← Layer 1 (agents)    |
|  └────┬───┘└───┬────┘└──┬─────┘                        |
|       └────────┼────────┘                               |
|           ┌────┴────┐                                   |
|           │  TASK   │  ← Layer 0 (root, bottom)         |
|           └─────────┘                                   |
|                                                          |
+----------------------------------------------------------+
|              [Detail Panel — right sidebar]              |
+----------------------------------------------------------+
```

### 4.2 Component Changes

#### REMOVE
- `FilterBar.tsx` — delete entirely (13 buttons → 0)
- Status filter buttons
- Time filter buttons
- Type filter buttons
- Reset button

#### ADD
- `LeagueSelector.tsx` — horizontal tab bar at top of DAG panel
  - Shows all presets as clickable chips/tabs
  - Active preset highlighted
  - "+ New" button for creating custom presets
  - Each tab shows: name + icon (dragon/titan/custom)

- `NodeContextMenu.tsx` — right-click menu on nodes
  - Agent nodes: "Change Model", "Edit Prompt", "View Logs"
  - Task nodes: "Re-run", "View Input", "View Output"
  - Subtask nodes: "View Code", "View Tokens"
  - Proposal nodes: "Approve", "Reject", "View Diff"

- `EdgeHighlightManager` — logic in DAGView for connection highlighting
  - On node select: dim all edges to 0.1 opacity, brighten connected to 1.0
  - Brighten connected nodes with border glow
  - On deselect (pane click): restore all

- `InlineStreamOverlay.tsx` — floating text near running nodes
  - Shows last 3 lines of agent output
  - Auto-scrolls as new lines arrive
  - Fades out when agent completes

#### MODIFY
- `DAGView.tsx`:
  - Add edge highlighting on node select
  - Fix MiniMap to use actual `getNodeColor` function
  - Add edge click handler
  - Verify nodesDraggable works (investigate regression)
  - Add right-click handler for context menu

- `DetailPanel.tsx`:
  - Remove preset list scrolling
  - Show only the ACTIVE preset's config
  - League switching happens via LeagueSelector, not DetailPanel
  - Focus on: model editing + prompt editing + node metadata

- `MyceliumCommandCenter.tsx`:
  - Replace FilterBar with LeagueSelector
  - Pass activePreset to DAGView and DetailPanel
  - Connect to live pipeline stream (WebSocket events)
  - Route stream events to InlineStreamOverlay

### 4.3 Data Flow

```
LeagueSelector (top)
    │
    ├── activePreset → DAGView (node rendering, edge colors per preset theme)
    ├── activePreset → DetailPanel (show only this preset's model config)
    └── activePreset → Pipeline API (use this preset for next @dragon run)

DAGView (canvas)
    │
    ├── onNodeSelect → DetailPanel (show node info + role editor)
    ├── onNodeSelect → EdgeHighlightManager (highlight connections)
    ├── onNodeRightClick → NodeContextMenu (show actions)
    ├── onEdgeClick → DetailPanel (show edge info: type, strength, data flow)
    └── pipelineEvents → InlineStreamOverlay (floating text near active node)
```

---

## 5. Implementation Roadmap

### Phase 1: Clean & Fix (1-2 hours) — Cursor
**Priority: Critical bugs + noise removal**

1. **Remove FilterBar** — delete component, remove from MyceliumCommandCenter
2. **Fix node dragging** — investigate why `nodesDraggable={true}` stopped working
3. **Fix MiniMap colors** — replace `() => '#666'` with actual `getNodeColor`
4. **Fix TYPE filter** — remove dead code path since FilterBar is deleted

**Result:** Clean canvas with no broken controls.

### Phase 2: Edge Intelligence (2-3 hours) — Cursor
**Priority: Connection highlighting — user's top request**

1. **Import `getConnectedEdges`** from xyflow
2. **On node select:**
   - Find all connected edges via `getConnectedEdges(node, edges)`
   - Set selected edges: `opacity: 1.0, strokeWidth: 3, stroke: '#fff'`
   - Set unselected edges: `opacity: 0.08`
   - Set connected nodes: `border: 1px solid #fff`
   - Set unselected nodes: `opacity: 0.4`
3. **On pane click (deselect):** restore all to default
4. **Add edge click handler:** show edge info in DetailPanel (type, strength, source→target)

**Result:** VETKA-style connection highlighting in DAG.

### Phase 3: League Selector (2-3 hours) — Cursor
**Priority: Preset management at top level**

1. **Create `LeagueSelector.tsx`:**
   - Fetch presets from `/api/pipeline/presets`
   - Render as horizontal chips: `[Dragon Bronze] [Dragon Silver] [Dragon Gold] [Titans Alpha] ...`
   - Active preset has bright border, others dim
   - Click to switch active preset
   - "+ New" button at end
2. **Replace FilterBar** in MyceliumCommandCenter with LeagueSelector
3. **Wire activePreset** to DetailPanel — RoleEditor shows only active preset's models
4. **Wire activePreset** to pipeline dispatch — next `@dragon` uses selected preset

**Result:** Top-level league switching, no scrolling through presets.

### Phase 4: Inline Stream (3-4 hours) — Cursor + Opus
**Priority: Live agent output in DAG**

1. **Listen to Mycelium WebSocket events** in DAGView:
   - `pipeline:subtask_start` → mark node as running
   - `pipeline:subtask_stream` → append text to overlay
   - `pipeline:subtask_done` → mark node as done, hide overlay
2. **Create `InlineStreamOverlay.tsx`:**
   - Absolute-positioned div near the running node
   - Shows last 3-5 lines of agent output in monospace
   - Auto-fades after completion (2s delay)
   - Draggable to reposition if blocking view
3. **Connect DAG nodes to pipeline events** via taskId matching

**Result:** See what agents are doing directly on the DAG, no panel switching.

### Phase 5: Preset CRUD (2-3 hours) — Cursor
**Priority: Create/edit/save custom presets from DAG panel**

1. **"+ New" in LeagueSelector** → clone current preset with editable name
2. **Edit mode:** inline rename, add/remove roles, change provider
3. **Save via POST** `/api/pipeline/presets/create`
4. **Delete** with confirmation (only custom presets, not base Dragon/Titan)
5. **Export/Import** as JSON (drag-and-drop or copy-paste)

**Backend changes needed:**
- Add `POST /api/pipeline/presets/create` endpoint
- Add `DELETE /api/pipeline/presets/{name}` endpoint
- Add `POST /api/pipeline/presets/{name}/clone` endpoint

**Result:** Full preset management without leaving DAG panel.

### Phase 6: Context Menu (1-2 hours) — Cursor
**Priority: Right-click actions on nodes**

1. **Create `NodeContextMenu.tsx`** — floating menu on right-click
2. **Agent nodes:** Change Model, Edit Prompt, View Logs, Re-assign
3. **Task nodes:** Re-run, View Input/Output, Cancel
4. **Subtask nodes:** View Code, Copy Output, View Tokens
5. **Proposal nodes:** Approve, Reject, View Diff, Edit

**Result:** Power-user actions without cluttering the UI.

---

## 6. Technical Specifications

### 6.1 Edge Highlighting Algorithm

```typescript
// In DAGView.tsx — onNodeClick handler
function handleNodeSelect(nodeId: string) {
  const connectedEdgeIds = new Set(
    edges
      .filter(e => e.source === nodeId || e.target === nodeId)
      .map(e => e.id)
  );

  const connectedNodeIds = new Set(
    edges
      .filter(e => e.source === nodeId || e.target === nodeId)
      .flatMap(e => [e.source, e.target])
  );

  // Update edges
  setEdges(eds => eds.map(e => ({
    ...e,
    style: {
      ...e.style,
      opacity: connectedEdgeIds.has(e.id) ? 1.0 : 0.08,
      strokeWidth: connectedEdgeIds.has(e.id) ? 3 : 1,
      stroke: connectedEdgeIds.has(e.id) ? '#fff' : e.style?.stroke,
    },
  })));

  // Update nodes
  setNodes(nds => nds.map(n => ({
    ...n,
    style: {
      ...n.style,
      opacity: n.id === nodeId || connectedNodeIds.has(n.id) ? 1.0 : 0.3,
    },
  })));
}
```

### 6.2 LeagueSelector Spec

```typescript
interface LeagueSelectorProps {
  presets: PresetInfo[];       // from /api/pipeline/presets
  activePreset: string;        // current selection
  onPresetChange: (name: string) => void;
  onCreateNew: () => void;
}

// Visual: horizontal row of chips
// Active chip: bg=#222, border=#fff, text=#fff
// Inactive chip: bg=#0a0a0a, border=#333, text=#888
// "+ New" chip: bg=#0a0a0a, border=dashed #555, text=#555
```

### 6.3 InlineStreamOverlay Spec

```typescript
interface InlineStreamOverlayProps {
  nodeId: string;              // which node to attach to
  lines: string[];             // last N lines of output
  visible: boolean;
  position: { x: number; y: number }; // computed from node position
}

// Visual: floating dark box, max 200px wide, 3-5 lines
// Font: monospace 10px, color: #888
// Border: 1px solid #333
// Positioned: 10px to the right of the node
// Auto-hide: 2s after stream stops
```

### 6.4 API Endpoints (New)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/pipeline/presets/create` | Create new preset |
| DELETE | `/api/pipeline/presets/{name}` | Delete custom preset |
| POST | `/api/pipeline/presets/{name}/clone` | Clone preset with new name |
| GET | `/api/pipeline/presets/{name}/validate` | Validate preset has all required roles |

---

## 7. Design Principles (Nolan Rules)

1. **Graph is the UI** — every action starts from a node or edge, not a button
2. **Zero-button ideal** — aim for 0 persistent filter buttons; use keyboard shortcuts + right-click
3. **Grayscale hierarchy** — white = active/selected, gray = normal, dark = dimmed/disabled
4. **Progressive disclosure** — label → hover tooltip → click detail → right-click actions
5. **Spatial consistency** — match VETKA 3D tree metaphor (root at bottom, results at top)
6. **Live-in-place** — agent output appears ON the graph, not in a separate panel

---

## 8. Risk Assessment

| Risk | Mitigation |
|------|------------|
| xyflow performance with 50+ nodes | Use virtualization (xyflow supports it natively) |
| WebSocket events overwhelming overlay | Throttle to 5 updates/sec, keep only last 3 lines |
| Custom presets breaking pipeline | Validate all 5 roles present before saving |
| Edge highlighting flicker on rapid clicks | Debounce node select by 100ms |
| MiniMap becoming cluttered | Keep MiniMap simple, don't add highlighting there |

---

## 9. Success Metrics

- [ ] FilterBar removed — 0 persistent filter buttons
- [ ] Edge highlighting works — click node, connections glow white
- [ ] League selector at top — switch presets in 1 click
- [ ] Node dragging works — can reposition any node
- [ ] Live stream visible on running nodes
- [ ] Custom preset creation from DAG panel
- [ ] MiniMap shows actual status colors
- [ ] Right-click context menu on all node types

---

## 10. Assignment

| Phase | Assigned To | Estimated Time | Dependencies |
|-------|------------|----------------|--------------|
| Phase 1: Clean & Fix | Cursor | 1-2h | None |
| Phase 2: Edge Intelligence | Cursor | 2-3h | Phase 1 |
| Phase 3: League Selector | Cursor | 2-3h | Phase 1 |
| Phase 4: Inline Stream | Cursor + Opus | 3-4h | Phase 2, WebSocket hookup |
| Phase 5: Preset CRUD | Cursor | 2-3h | Phase 3, Backend endpoints |
| Phase 6: Context Menu | Cursor | 1-2h | Phase 2 |

**Total estimated:** 12-18 hours of Cursor work + 1-2h Opus architecture review.

---

## Appendix A: Files to Modify

```
client/src/components/mcc/
├── DAGView.tsx          — Edge highlighting, fix MiniMap, edge click, right-click
├── DetailPanel.tsx      — Simplify to active-preset-only, remove scroll
├── FilterBar.tsx        — DELETE ENTIRELY
├── MyceliumCommandCenter.tsx — Replace FilterBar with LeagueSelector
├── nodes/
│   ├── TaskNode.tsx     — Add hover tooltip, right-click support
│   ├── AgentNode.tsx    — Add stream overlay anchor point
│   ├── SubtaskNode.tsx  — Add hover tooltip
│   └── ProposalNode.tsx — Add approve/reject quick actions
└── [NEW] LeagueSelector.tsx
└── [NEW] NodeContextMenu.tsx
└── [NEW] InlineStreamOverlay.tsx

client/src/utils/
└── dagLayout.ts         — No changes needed (Nolan palette stays)

client/src/types/
└── dag.ts               — Add PresetInfo type, StreamEvent type

server (Python):
└── src/api/routes/pipeline_config_routes.py — Add create/delete/clone endpoints
```

## Appendix B: Keyboard Shortcuts (Proposed)

| Shortcut | Action |
|----------|--------|
| `Cmd+F` | Search nodes by label |
| `1-9` | Switch to preset by number |
| `Escape` | Deselect all, reset highlighting |
| `Delete` | Remove selected node (with confirmation) |
| `Space` | Fit view (zoom to show all nodes) |
| `R` | Re-run selected task |
| `E` | Edit selected node (open detail) |

---

*Document generated by Opus Commander. Synthesized from Haiku audit (9 components analyzed) + Sonnet research (5 DAG systems compared).*
