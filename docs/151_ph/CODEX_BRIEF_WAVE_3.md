# CODEX BRIEF — Wave 3: Panel = Zoom
## Phase 151 | Tasks 151.8, 151.9, 151.10
**Depends on: Wave 2 complete (unified header)**

---

## OVERVIEW

Every panel has 2 modes: **compact** (embedded in DAG view) and **expanded** (full tab).
Same component, same state, different layout. Click ↗ to expand, click ↙ to collapse.

**After Wave 3:** Architect chat in DAG panel = same chat as ARCHITECT tab. Stats preview in DAG = same data as STATS tab.

**Rules:**
- Same component instance — NOT a copy
- State through Zustand (useMCCStore or dedicated store)
- Expand = switch to that tab, Collapse = switch back to MCC tab
- No data duplication

---

## 151.8 — Architect Chat: Compact ↔ Expanded

### Problem
`ArchitectChat.tsx` (442 lines) is a separate component that only renders in the ARCHITECT tab. DAG has no chat. Two separate interfaces with no shared state.

### What to Build

Add `mode` prop to ArchitectChat:

```tsx
interface ArchitectChatProps {
  mode: 'compact' | 'expanded';
}
```

**Compact mode** (rendered in MCCDetailPanel, right column of DAG):
- Height: 300px max
- Shows last 5 messages only
- Minimal input (one-line, no model selector)
- Expand button ↗ at top-right corner

**Expanded mode** (rendered in ARCHITECT tab):
- Flex: 1 (full height)
- Full message history with scroll
- Model selector dropdown
- Subtask extraction panel
- Collapse button ↙ at top-right corner

### State Management
Chat messages and model selection must be in Zustand store (NOT local useState):

```tsx
// Add to useMCCStore or create useArchitectStore:
interface ArchitectState {
  messages: ChatMessage[];
  selectedModel: string;
  isGenerating: boolean;
  addMessage: (msg: ChatMessage) => void;
  setModel: (model: string) => void;
}
```

Currently ArchitectChat uses local useState for messages (line ~50). Move to store.

### Wiring

**MCCDetailPanel.tsx** — add compact chat at bottom of detail panel:
```tsx
{/* Below existing node/edge detail info */}
<ArchitectChat mode="compact" />
```

**DevPanel.tsx** — ARCHITECT tab renders expanded:
```tsx
case 'ARCHITECT':
  return <ArchitectChat mode="expanded" />;
```

**Expand action:** When user clicks ↗ in compact chat:
1. Switch active tab to ARCHITECT (via store or prop callback)
2. ArchitectChat now renders in expanded mode
3. Same messages, same state

**Collapse action:** When user clicks ↙ in expanded chat:
1. Switch active tab back to MCC
2. Chat continues in compact mode in DAG panel

---

## 151.9 — Stats: Compact ↔ Expanded

### Same Pattern as 151.8

Add `mode` prop to PipelineStats:

```tsx
interface PipelineStatsProps {
  mode: 'compact' | 'expanded';
  tasks: TaskData[];
}
```

**Compact mode** (rendered in MCCDetailPanel):
- Shows summary only: Total Runs | Success% | Confidence | Weak Link
- 4 stat boxes in 2x2 grid
- Height: ~120px
- Expand button ↗

**Expanded mode** (rendered in STATS tab):
- Full stats: per-preset bars, token breakdown, running tasks, etc.
- Everything that exists today
- Collapse button ↙

### Wiring
Same as 151.8 — compact in MCCDetailPanel, expanded in STATS tab.

---

## 151.10 — Balance: Mini-Preview in Header

### What to Build

This is lighter than 151.8/151.9. Not a panel in DAG — just a richer dropdown in header.

The `KeyDropdown` from 151.5 (Wave 2) already shows selected key. Enhance it:
- Show selected key provider name
- Show remaining balance ($X.XX)
- Dropdown lists all keys with balances
- Click key → select it
- "View all →" link at bottom → switches to BALANCE tab

Balance tab (BALANCE in DevPanel) stays as full expanded view.

No `mode` prop needed — KeyDropdown IS the compact view, BALANCE tab IS the expanded view.

---

## MCCDetailPanel Layout After Wave 3

```
┌─ MCCDetailPanel (right column, 240px) ─┐
│                                          │
│  [Selected Node/Edge Info]               │  ← Existing (node status, model, tokens)
│                                          │
│  ─────────── separator ──────────        │
│                                          │
│  [Stats Compact]              [↗]        │  ← 151.9 (2x2 summary grid)
│   Runs: 12  Success: 75%                 │
│   Conf: 0.82  Weak: Coder               │
│                                          │
│  ─────────── separator ──────────        │
│                                          │
│  [Architect Chat Compact]     [↗]        │  ← 151.8 (last 5 msgs + input)
│   > Add caching to API                   │
│   < Планирую 3 подзадачи...             │
│   [type message...          ] [Send]     │
│                                          │
└──────────────────────────────────────────┘
```

---

*Codex Brief Wave 3 | Phase 151 | Opus Commander*
