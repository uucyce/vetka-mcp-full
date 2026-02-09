# CURSOR BRIEF Phase 129: Watcher Health + Chat Performance

## Context
Watcher was causing server freeze during pipeline execution — 50+ TripleWrite calls
from data/ files that weren't in skip list. Opus fixed skip patterns (MARKER_129.0A).
Now Cursor handles UI tasks for Phase 129.

## C10: Watcher Status Panel in DevPanel (Priority 1)

### Problem
No visibility into watcher state. User can't see if watcher is flooding server.

### What Needs to Change
1. New "Watcher" tab in DevPanel (6th tab after Board / Stats / Test / Activity / Chat?)
2. Show:
   - **Files indexed today**: count from changelog (GET /api/debug/watcher-stats)
   - **Skip patterns**: list of what's being skipped
   - **Last 10 events**: recently processed files with timestamps
   - **Event rate**: events/minute over last 5 min
3. Compact: just a stats box + scrollable event list

### Files
- `client/src/components/panels/WatcherStats.tsx` (new component)
- `client/src/components/panels/DevPanel.tsx` (add tab)

### Backend Endpoint (Opus will create)
```
GET /api/debug/watcher-stats
Response: {
  "indexed_today": 1247,
  "skip_patterns_count": 22,
  "events_last_5min": 3,
  "recent_events": [
    {"path": "src/foo.py", "type": "modified", "time": "23:15:20"}
  ]
}
```

### Markers
- MARKER_129.1A: WatcherStats component
- MARKER_129.1B: DevPanel watcher tab

### Style
- Same Nolan monochrome
- No bars/charts — just numbers + list

## C11: Chat History Lazy Loading (Priority 1)

### Problem
Chat history takes very long to load. User said "Я не могу посмотреть историю чата".

### What Needs to Change
1. Check how chat history loads — is it loading ALL messages at once?
2. Implement pagination: load 20 chats initially, load more on scroll
3. Show loading skeleton while fetching
4. Cache loaded chats in Zustand store

### Files
- Check `client/src/components/chat/` for chat list component
- Check API endpoint that returns chat history
- Modify to support `?offset=0&limit=20` pagination

### Markers
- MARKER_129.2A: Chat list pagination
- MARKER_129.2B: Loading skeleton
- MARKER_129.2C: Scroll-to-load-more

## C12: DevPanel Performance Guard (Priority 2)

### Problem
DevPanel re-renders on every SocketIO event (pipeline_activity, task_board_updated, etc.)
During pipeline execution this causes constant re-renders → browser lag.

### What Needs to Change
1. Add `React.memo()` to all DevPanel child components
2. Throttle SocketIO event processing: max 2 updates per second
3. Use `useRef` for event buffer, flush to state every 500ms

### Files
- `client/src/components/panels/DevPanel.tsx`
- `client/src/components/panels/ActivityLog.tsx` (already a hot spot)
- `client/src/components/panels/TaskCard.tsx`

### Markers
- MARKER_129.3A: React.memo guards
- MARKER_129.3B: Event throttling (500ms flush)

## Rules
- Nolan monochrome
- No external deps
- TypeScript strict mode
- Performance-first: fewer re-renders = less browser lag

## Estimated Effort
- C10: 1 hour (stats panel + new endpoint)
- C11: 1.5 hours (pagination + skeleton)
- C12: 45 min (memo + throttle)
- Total: ~3 hours
