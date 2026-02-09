# CURSOR BRIEF: ActivityLog — Pipeline Activity Tab in DevPanel

## Goal
Add an "Activity" tab to DevPanel that shows real-time pipeline progress.
Backend already broadcasts `pipeline_activity` SocketIO events (MARKER_127.2).
Frontend `useSocket.ts` already dispatches `pipeline-activity` CustomEvent.
You just need to build the UI component that listens and renders.

## What Already Exists
- `DevPanel.tsx` has tabs (Board / Stats / Test / Balance)
- `useSocket.ts` dispatches `window.CustomEvent('pipeline-activity', { detail })`
- Event payload: `{ role, message, model, subtask_idx, total, task_id, preset, timestamp }`
- Style: Nolan monochrome (#111, #222, #e0e0e0), no color, glassmorphism

## Files to Create/Modify

### NEW: `client/src/components/panels/ActivityLog.tsx`
- Listen for `pipeline-activity` CustomEvent via `useEffect`
- Buffer: deque-style array, max 100 entries, newest on top
- Each entry: `[timestamp] role (model): message [idx/total]`
- Auto-scroll to bottom when new entries arrive (optional "follow" toggle)
- Clear button to reset log
- Empty state: "No pipeline activity yet"
- MARKER_127.2A

### MODIFY: `client/src/components/panels/DevPanel.tsx`
- Add 5th tab: "Activity" (after Balance)
- Import and render `<ActivityLog />` in Activity tab
- MARKER_127.2B

## Style Guide
- Background: `#111` for log area
- Text: `#888` for role/model, `#e0e0e0` for message
- Font: monospace, 12px
- Timestamp: `#555`, compact format (HH:MM:SS)
- Role badges: no color, just text like `@coder`, `@architect`
- Reuse StatusDot pattern from ModelDirectory if needed (grayscale pulse)

## Component Structure
```
ActivityLog.tsx
  LogEntry[] (max 100, ring buffer)
    timestamp | role (model) | message [idx/total]
  FollowTail toggle (optional)
  Clear button
```

## Event Payload Reference
```typescript
interface PipelineActivityEvent {
  role: string;        // "@coder", "@architect", "@scout", etc.
  message: string;     // "Writing code", "Planning subtasks"
  model: string;       // "qwen3-coder", "kimi-k2.5"
  subtask_idx: number; // 0-based
  total: number;       // total subtasks
  task_id?: string;    // "tb_xxx" from task board
  preset?: string;     // "dragon_silver"
  timestamp: number;   // unix timestamp
}
```

## DO NOT
- Add new socket events (already wired)
- Modify backend code (already done)
- Add colors/emoji (Nolan style)
- Add new dependencies
