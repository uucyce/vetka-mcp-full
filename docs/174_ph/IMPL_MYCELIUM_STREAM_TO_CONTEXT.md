# Phase 174.B — MYCELIUM Stream in MCC Context Window

## Problem

Pipeline events (MYCELIUM stream) are currently only visible in:
- DevPanel (deprecated, "мусорное" окно)
- StreamPanel (tiny 72px log at bottom of MCC)

Users need to see **rich pipeline activity** — including REFLEX tool selection insights — directly in the **context window** when clicking on a running/completed DAG node.

## What Already Exists (Ready to Use)

### Backend — Fully Ready (Phase 174.A DONE)

`_emit_progress()` in `agent_pipeline.py` now sends structured `metadata` through all channels:

```python
# agent_pipeline.py line ~1319
await self._emit_progress("@reflex", "Recommends: read_file, edit_file",
    metadata={
        "type": "reflex",          # Message rendering type
        "event": "recommendation", # recommendation | outcome | verifier | filter
        "tools": [{"id": "read_file", "score": 0.92}, ...],
        "phase": "fix",
        "tier": "silver",
        "subtask": "step_1",
    })
```

**4 REFLEX event types** are emitted with metadata:
| Event | When | Key Fields |
|-------|------|------------|
| `recommendation` | IP-1: Before FC loop | `tools[{id, score}]`, `tier`, `phase` |
| `filter` | IP-7: Schema filtering | `original_count`, `filtered_count`, `tier` |
| `outcome` | IP-3: After FC call | `tools_used[]`, `feedback_count` |
| `verifier` | IP-5: After verify | `passed`, `tools[]`, `feedback_count` |

All `pipeline_activity` WebSocket broadcasts now include `metadata` field when present.

### Frontend Components — Ready

| Component | File | Status | What It Does |
|-----------|------|--------|-------------|
| `ReflexInsight.tsx` | `client/src/components/chat/ReflexInsight.tsx` | **NEW (174.A)** | Renders REFLEX metadata as compact colored pills |
| `NodeStreamView.tsx` | `client/src/components/mcc/NodeStreamView.tsx` | **EXISTS (144)** | 3-tab view (stream/output/artifacts) filtered by node.taskId |
| `StreamPanel.tsx` | `client/src/components/mcc/StreamPanel.tsx` | **EXISTS (143)** | Tiny collapsible event log, filters by selectedTaskId |
| `MiniContext.tsx` | `client/src/components/mcc/MiniContext.tsx` | **EXISTS (155A)** | Context shell with MiniWindow — renders NodeStreamView inside |
| `MiniWindow.tsx` | `client/src/components/mcc/MiniWindow.tsx` | **EXISTS (154)** | compact/expanded floating window framework |

### Data Flow — Current (Gap Marked)

```
Backend                    WebSocket                Frontend
────────                   ──────────               ────────
_emit_progress()
  ↓ (includes metadata)
ws_broadcaster.broadcast({ ───────→  useMyceliumSocket.ts
  type: "pipeline_activity",          ↓
  role, message, task_id,            Dispatches CustomEvent
  metadata: {...},                   'pipeline-activity'
})                                    ↓
                                     MyceliumCommandCenter.tsx
                                     line 2282: handlePipelineActivity(e)
                                       ↓
                                     pushStreamEvent({        ←── 🔴 GAP: metadata LOST
                                       role: detail.role,
                                       message: detail.message,
                                       taskId: detail.task_id,
                                     })
                                       ↓
                                     useMCCStore.streamEvents[]
                                       ↓
                             ┌─────────┴──────────┐
                             ↓                    ↓
                        StreamPanel          NodeStreamView
                        (tiny log)           (3-tab detail)
                                              ↓
                                         StreamTabContent
                                         (plain text only)  ←── 🔴 No ReflexInsight
```

---

## Implementation Plan

### Fix 1: Extend `StreamEvent` interface (5 min)

**File:** `client/src/store/useMCCStore.ts` line 19

```typescript
// BEFORE
export interface StreamEvent {
  id: string;
  ts: number;
  role: string;
  message: string;
  taskId?: string;
}

// AFTER
export interface StreamEvent {
  id: string;
  ts: number;
  role: string;
  message: string;
  taskId?: string;
  // MARKER_174.B: Structured metadata for rich rendering
  metadata?: {
    type?: string;
    event?: string;
    tools?: Array<{ id: string; score?: number }>;
    tools_used?: string[];
    feedback_count?: number;
    passed?: boolean;
    original_count?: number;
    filtered_count?: number;
    phase?: string;
    tier?: string;
    subtask?: string;
    [key: string]: any;
  };
}
```

### Fix 2: Pass metadata in `handlePipelineActivity` (2 min)

**File:** `client/src/components/mcc/MyceliumCommandCenter.tsx` line 2282

```typescript
// BEFORE (line 2287)
pushStreamEvent({ role: String(role), message: String(message), taskId });

// AFTER
pushStreamEvent({
  role: String(role),
  message: String(message),
  taskId,
  metadata: detail.metadata || undefined,
});
```

### Fix 3: Preserve metadata in `pushStreamEvent` (2 min)

**File:** `client/src/store/useMCCStore.ts` line 531

```typescript
// BEFORE
pushStreamEvent: (event) => {
  const next: StreamEvent = {
    id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    ts: Date.now(),
    role: event.role || 'pipeline',
    message: event.message || '',
    taskId: event.taskId,
  };

// AFTER
pushStreamEvent: (event) => {
  const next: StreamEvent = {
    id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    ts: Date.now(),
    role: event.role || 'pipeline',
    message: event.message || '',
    taskId: event.taskId,
    metadata: event.metadata,  // MARKER_174.B: Preserve structured metadata
  };
```

### Fix 4: Render ReflexInsight in NodeStreamView (15 min)

**File:** `client/src/components/mcc/NodeStreamView.tsx`

This is the KEY change. The `StreamTabContent` component currently renders events as plain text. Add REFLEX-aware rendering:

```typescript
// At the top of the file, add import:
import { ReflexInsight } from '../chat/ReflexInsight';
import type { ChatMessage } from '../../types/chat';

// In StreamTabContent, REPLACE the plain text event renderer:
// BEFORE (approximately line 185):
{events.map(event => (
  <div key={event.id} style={{ ... }}>
    <span>{time}</span>
    <span>{event.role}</span>
    <span>{event.message}</span>
  </div>
))}

// AFTER:
{events.map(event => {
  // MARKER_174.B: Rich rendering for REFLEX events
  if (event.metadata?.type === 'reflex') {
    // Convert StreamEvent to ChatMessage shape for ReflexInsight
    const reflexMsg: ChatMessage = {
      id: event.id,
      role: 'system',
      content: event.message,
      type: 'reflex',
      timestamp: new Date(event.ts).toISOString(),
      metadata: { reflex: event.metadata as any },
    };
    return <ReflexInsight key={event.id} message={reflexMsg} />;
  }

  // Default: plain text rendering (existing code)
  return (
    <div key={event.id} style={{ ... }}>
      <span>{time}</span>
      <span>{event.role}</span>
      <span>{event.message}</span>
    </div>
  );
})}
```

### Fix 5: Render ReflexInsight in StreamPanel (10 min)

**File:** `client/src/components/mcc/StreamPanel.tsx`

Same pattern — add REFLEX-aware rendering to the bottom stream panel:

```typescript
// At top:
import { ReflexInsight } from '../chat/ReflexInsight';
import type { ChatMessage } from '../../types/chat';

// In render (line ~53):
{filteredEvents.map(event => {
  // MARKER_174.B: Compact REFLEX pills in stream
  if (event.metadata?.type === 'reflex') {
    const reflexMsg: ChatMessage = {
      id: event.id,
      role: 'system',
      content: event.message,
      type: 'reflex',
      timestamp: new Date(event.ts).toISOString(),
      metadata: { reflex: event.metadata as any },
    };
    return <ReflexInsight key={event.id} message={reflexMsg} />;
  }

  // Default plain text (existing code)
  return (
    <div key={event.id} style={{ display: 'flex', gap: 6 }}>
      ...existing code...
    </div>
  );
})}
```

---

## Architecture After Implementation

```
Backend                    WebSocket                Frontend
────────                   ──────────               ────────
_emit_progress(metadata)
  ↓
ws_broadcaster.broadcast({ ───────→  useMyceliumSocket.ts
  type: "pipeline_activity",          ↓
  metadata: {                        'pipeline-activity' CustomEvent
    type: "reflex",                   ↓
    event: "recommendation",         handlePipelineActivity(e)
    tools: [...],                      ↓
  }                                  pushStreamEvent({
})                                     ...
                                       metadata: detail.metadata ←── ✅ FIXED
                                     })
                                       ↓
                                     useMCCStore.streamEvents[]
                                       ↓
                             ┌─────────┼──────────┐
                             ↓         ↓          ↓
                        StreamPanel  NodeStreamView  MiniContext
                             ↓         ↓               ↓
                        ReflexInsight  ReflexInsight   NodeStreamView
                        (pills)        (pills)        (wraps NodeStreamView)
```

## Component Reuse Map

| Component | Location | Reuse |
|-----------|----------|-------|
| `ReflexInsight` | `client/src/components/chat/ReflexInsight.tsx` | Import & render for reflex events |
| `ChatMessage` type | `client/src/types/chat.ts` | Use to construct `reflexMsg` adapter |
| `NodeStreamView` | `client/src/components/mcc/NodeStreamView.tsx` | Already used in MiniContext, just enhance |
| `StreamPanel` | `client/src/components/mcc/StreamPanel.tsx` | Enhance inline rendering |
| `useMCCStore` | `client/src/store/useMCCStore.ts` | Extend StreamEvent interface |
| `MyceliumCommandCenter` | `client/src/components/mcc/MyceliumCommandCenter.tsx` | Fix metadata passthrough |

## Files to Modify (Summary)

| # | File | Change | Lines |
|---|------|--------|-------|
| 1 | `client/src/store/useMCCStore.ts` | Extend `StreamEvent` + preserve metadata | ~15 |
| 2 | `client/src/components/mcc/MyceliumCommandCenter.tsx` | Pass `detail.metadata` | ~1 |
| 3 | `client/src/components/mcc/NodeStreamView.tsx` | Import ReflexInsight, conditional render | ~20 |
| 4 | `client/src/components/mcc/StreamPanel.tsx` | Import ReflexInsight, conditional render | ~15 |
| **Total** | | | **~51 lines** |

## NO New Files Needed

Everything reuses existing components:
- `ReflexInsight.tsx` — already exists (Phase 174.A)
- `ChatMessage` type — already has `reflex` metadata (Phase 174.A)
- `NodeStreamView` — already has 3-tab layout (Phase 144)
- `StreamPanel` — already filters by taskId (Phase 143)

## Verification

```bash
# 1. Start backend + frontend
python main.py  # port 5001
cd client && npm run dev  # port 3001

# 2. Open MCC, create a task, run @dragon
# 3. Click on running node in DAG
# 4. Verify:
#    - NodeStreamView "stream" tab shows REFLEX pills (not just plain text)
#    - StreamPanel at bottom shows REFLEX pills
#    - Clicking recommendation pill expands to show all tools
#    - Filter events show reduction percentage
#    - Verifier events show pass/fail with color

# 5. TypeScript check:
cd client && npx tsc --noEmit
```

## Visual Mockup

When a user clicks on a running pipeline node in the DAG:

```
┌── NodeStreamView (MiniContext expanded) ──────────────┐
│ [roadmap_task] Deploy auth system                      │
│ status: running │ role: coder │ model: qwen3-coder     │
│                                                        │
│ [stream] (12) │ [output] │ [artifacts] (0)             │
│ ──────────────────────────────────────────────────────  │
│                                                        │
│ 14:23:05  @coder  Executing: implement login...        │
│                                                        │
│ ┌─ 🎯 REFLEX ─ read_file 0.92 │ edit_file 0.88 ─ Silver ┐  │
│ └───────────────────────────────────── step_1 ──────────┘  │
│                                                        │
│ ┌─ 🔧 FILTER ─ 12 → 3 ─ -75% ─────── Bronze ──────┐  │
│ └────────────────────────────────────── step_1 ──────┘  │
│                                                        │
│ 14:23:11  @coder  Done: step_1                         │
│                                                        │
│ ┌─ 📊 USED ─ read_file │ edit_file ─── 2 feedback ──┐  │
│ └────────────────────────────────────── step_1 ──────┘  │
│                                                        │
│ ┌─ ✅ PASS ─ read_file │ edit_file ─── 2 feedback ──┐  │
│ └────────────────────────────────────── step_1 ──────┘  │
│                                                        │
│ 14:23:15  @coder  Executing: add tests...              │
└────────────────────────────────────────────────────────┘
```

## Dependencies

- Phase 174.A (DONE): `ReflexInsight.tsx`, `ChatMessage.reflex` type, `_emit_progress(metadata)` backend
- Phase 154 (DONE): MiniContext, MiniWindow, NodeStreamView architecture
- Phase 143 (DONE): StreamPanel with taskId filtering

## Notes for Sandbox Team

1. **DO NOT create new WebSocket channels** — metadata flows through existing `pipeline_activity` events
2. **DO NOT modify backend** — all backend work is complete (Phase 174.A)
3. **ReflexInsight is a React component**, import from `../chat/ReflexInsight` (relative path depends on file location)
4. **ChatMessage adapter pattern**: Convert `StreamEvent` to `ChatMessage` shape for ReflexInsight props — see Fix 4 code example
5. **Metadata is optional** — old events without metadata render as plain text (backward compatible)
6. **StreamEvent.metadata is a "bag"** — any key-value data from backend, not just REFLEX. Future events may have different `type` values.
