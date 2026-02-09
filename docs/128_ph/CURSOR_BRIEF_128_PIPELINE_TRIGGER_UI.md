# CURSOR BRIEF: Pipeline Trigger from DevPanel

## Problem
Currently pipeline can only be triggered from group chat (@dragon/@doctor).
DevPanel has Board tab with tasks but no way to dispatch from there.
User has to switch to chat, type @dragon, wait for intake prompt, reply 1d...

## Goal
Add "Run" button to pending TaskCard → dispatches pipeline directly.
Quick dispatch without chat interaction.

## What Needs to Change

### 1. TaskCard: Run Button
For tasks with status `pending`:
- Show ▶ Run button (next to existing buttons)
- On click: POST to `/api/debug/task-board/dispatch` with `task_id`
- Show loading state while pipeline runs
- Auto-refresh when done (via existing `task-board-updated` event)

### 2. Quick-Add with Dispatch
Current quick-add input adds task to board.
Add a "Run Now" option:
- Input task → click "Add & Run" → adds to board + dispatches immediately
- Regular "Add" still available (just queues)

### 3. Preset Selector
Small dropdown next to Run button:
- Dragon Bronze (fast, cheap)
- Dragon Silver (balanced) — default
- Dragon Gold (best quality)
- POST includes `preset` param

### 4. Backend: Dispatch supports preset override
`POST /api/debug/task-board/dispatch` already works.
Just need to pass `preset` in body if user selected non-default.

## Markers
- MARKER_128.5A: Run button on TaskCard
- MARKER_128.5B: Quick-add with dispatch
- MARKER_128.5C: Preset selector dropdown

## Style
- Run button: `▶` icon, muted blue-gray `#2d3d5a` (Nolan)
- Loading: pulsing animation (reuse from running status)
- Preset dropdown: tiny, inline, same monochrome

## File Hints
- `client/src/components/panels/TaskCard.tsx` — run button
- `client/src/components/panels/DevPanel.tsx` — quick-add enhancement

## Estimated Effort
2 hours, low-medium complexity.
