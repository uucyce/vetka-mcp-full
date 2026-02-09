# CURSOR BRIEF: Stats Monitoring — Live Updates

## Goal
Stats tab in DevPanel should show live pipeline progress and auto-refresh when pipelines complete.

## Current State
- PipelineStats.tsx reads `tasks` from DevPanel props (passed from REST API fetch)
- DevPanel fetches tasks every 30s + on `task-board-updated` CustomEvent
- Stats tab shows "No pipeline runs yet" when no tasks have stats
- Pipeline stats ARE collected (see tb_5 and tb_7 with real stats in task_board.json)

## What Needs to Change

### 1. PipelineStats.tsx — Live Refresh
- Listen for `task-board-updated` CustomEvent directly (don't wait for DevPanel parent)
- When a task goes from `running` → `done`, show a brief "completed" animation
- Add a running tasks section at top: show currently running tasks with elapsed time

### 2. PipelineStats.tsx — Running Task Progress
- For running tasks, show:
  - Task title
  - Elapsed time (since `started_at`)
  - Pulsing indicator (reuse StatusIndicator pulse from TaskCard)
- Poll more frequently during runs: 5s instead of 30s

### 3. PipelineStats.tsx — Summary Improvements
- Show total pipelines run (count of tasks with stats)
- Average duration
- Success rate
- Total tokens consumed
- Per-preset breakdown (Dragon Bronze/Silver/Gold bars)

## Markers
- MARKER_126.12A: PipelineStats live refresh
- MARKER_126.12B: Running task progress display
- MARKER_126.12C: Summary statistics improvements

## Style
- Same Nolan monochrome as rest of DevPanel
- Running tasks: pulse animation from TaskCard
- Bars: white/gray gradient, no color

## Estimated Effort
2 hours, low complexity.
