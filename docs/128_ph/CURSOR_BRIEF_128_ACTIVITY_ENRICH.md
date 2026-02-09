# CURSOR BRIEF: Activity Log Enrichment

## Context
Phase 127.2 added ActivityLog.tsx with ring buffer of pipeline events.
Events show: role + message + timestamp.

## Problem
Activity log shows raw text. No structure, no visual hierarchy.
Can't tell: is this a tool call? A verifier verdict? A progress update?

## Goal
Enrich activity log entries with:
- Role icons (Scout 🔍, Coder 💻, Verifier ✓, Architect 📐)
- Tool call highlighting (when coder reads/searches files)
- Verifier verdict badge (passed ✓ / failed ✕ + confidence %)
- Subtask progress bar (2/5 done)

## What Needs to Change

### 1. Parse Activity Message
`pipeline_activity` event already has:
```json
{
  "role": "@coder",
  "message": "📖 vetka_read_file: client/src/store/useStore.ts",
  "progress": {"current": 2, "total": 5, "percentage": 40}
}
```

Parse `message` for known patterns:
- `📖` → tool call (file icon + path)
- `✅`/`❌` → verifier result
- `📁` → file created
- `🔄` → retry/recovery

### 2. Visual Formatting
- Tool calls: show file path as clickable link (opens in viewport?)
- Verifier: show confidence bar (0.0 — 1.0)
- Progress: show mini progress bar per subtask
- Errors: red-tinted background

### 3. Collapsible Per-Task Grouping
Group activity entries by `task_id`:
- Header: "Task: Add toggleBookmark (Dragon Silver)"
- Expand to see all events for that task
- Collapse completed tasks, expand running

## Markers
- MARKER_128.6A: Activity message parser
- MARKER_128.6B: Rich formatting (icons, badges, bars)
- MARKER_128.6C: Per-task grouping

## Style
- Same Nolan monochrome
- Tool calls: `#252525` bg, file path in `#888`
- Verifier passed: subtle green bar
- Verifier failed: subtle red bar
- Progress: thin white bar on dark bg

## File Hints
- `client/src/components/panels/ActivityLog.tsx` — enrich rendering

## Estimated Effort
2-3 hours, medium complexity.
