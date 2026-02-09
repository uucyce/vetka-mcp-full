# CURSOR BRIEF Wave 3: UI Polish & Phase 128 Closure

## Context
All major features done. This is final polish before Phase 129 (MCP Scaling).

## C7: Pipeline Completion Toast (Priority 1)
**Problem:** When pipeline finishes, user doesn't notice — must manually check Board tab.

### What Needs to Change
1. When `task-board-updated` event fires with `status=done`:
   - Show toast notification at bottom-right
   - Toast text: "Pipeline done: {task.title} — {stats.verifier_avg_confidence}% confidence"
   - Auto-dismiss after 5s
   - Click → switch to Board tab + expand that task's results
2. Simple CSS animation: slide up from bottom, fade out

### Files
- `client/src/components/panels/DevPanel.tsx` — add toast state + render
- OR create `client/src/components/ui/Toast.tsx` if you prefer (small, inline)

### Style
- Background: `#1a1a1a`, border-left: 3px solid `#2d5a3d` (success) / `#5a2d2d` (failure)
- Font: same monochrome `#ccc`
- No external deps

### Markers
- MARKER_128.7A: Toast component
- MARKER_128.7B: Toast trigger on task-board-updated

## C8: Apply All Button (Priority 2)
**Problem:** User must click "apply" on each subtask individually. Tedious for 4+ subtask results.

### What Needs to Change
1. Add "Apply All" button in results header (next to collapse all)
2. Sequential apply: calls POST `/api/debug/pipeline-results/apply` for each subtask that has code
3. Show progress: "Applying 2/4..."
4. Mark task as `applied` after all succeed

### Files
- `client/src/components/panels/TaskCard.tsx` — add Apply All button logic

### Markers
- MARKER_128.8A: Apply All button
- MARKER_128.8B: Sequential apply with progress

## C9: Keyboard Shortcuts for Board (Priority 3)
**Problem:** No keyboard navigation in Board tab.

### What Needs to Change
1. `j`/`k` — navigate tasks up/down (highlight)
2. `Enter` — expand results of highlighted task
3. `r` — run highlighted task
4. `a` — apply all results of highlighted task
5. Only active when Board tab is focused

### Files
- `client/src/components/panels/DevPanel.tsx` — add keydown listener

### Markers
- MARKER_128.9A: Keyboard navigation
- MARKER_128.9B: Keyboard actions (run, apply)

## Rules
- Same Nolan monochrome
- No external deps
- TypeScript strict mode
- Keep it small — this is final polish, not new features

## Estimated Effort
- C7: 30min (simple toast)
- C8: 45min (sequential apply)
- C9: 30min (keydown handler)
- Total: ~2 hours
