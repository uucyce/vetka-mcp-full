# CURSOR BRIEF: Header Controls + Playground Frontend
## Phase 148 | Priority: HIGH | Estimated: 8-10h total

---

## CONTEXT

Backend for Playground is 100% ready (74 tests). Need frontend to unlock the full workflow:
**@dragon task → sandbox → review diffs → approve/reject → promote to main → tree refreshes**

Also: Heartbeat toggle is buried below MCCTaskList. It's the main autonomy control — belongs in the header.

---

## TASK 1: Header Controls Bar (3h)

### Current Header:
```
MCC  ◇ silver ▾  • LIVE    0 · 0ev  0t 0r 0d  stream  ◀ ▶
```

### Target Header:
```
MCC  ◇ silver ▾  • LIVE  │ ❤️ ON 47s │ 🔒 PG:2 │ ⚙ │  0·0ev  stream  ◀ ▶
```

### Components to add (in MCC header, right of LIVE badge):

**A) Heartbeat Chip** `<HeartbeatChip />`
- Shows: `❤️ ON 47s` (green pulse) or `❤️ OFF` (gray)
- Click: toggle heartbeat on/off via `POST /api/debug/heartbeat/settings`
- Right-click / long press: interval selector popup (1m / 5m / 15m / 1h / 1d)
- Data: `GET /api/debug/heartbeat/settings` → `{ enabled, interval_seconds, last_tick, total_ticks }`
- Listen: `task-board-updated` CustomEvent for tick notifications
- **Move existing logic from MCCTaskList.tsx footer** — remove from there after

**B) Playground Badge** `<PlaygroundBadge />`
- Shows: `🔒 PG:2` (2 active sandboxes) or `🔒 PG:0` (gray)
- Click: opens dropdown list of active playgrounds with actions
- Badge glows green when any playground has "review available" (changed files)
- Data: `GET /api/debug/playground` → list of playgrounds with status
- Each item in dropdown: name, task, status, [Review] [Destroy] buttons
- If no playgrounds: show "No active sandboxes"

**C) Settings Gear** `<HeaderSettings />`
- Click: opens popover/modal with:
  - Heartbeat interval (dropdown)
  - Playground base_dir (text input + folder icon)
  - Playground max_concurrent (number input, default 5)
  - Playground TTL hours (number input, default 4)
- Data: `GET /api/debug/playground/settings` + `PATCH /api/debug/playground/settings`
- Nolan dark style: `#111` bg, `#e0e0e0` text, minimal borders

### Style Guide:
- Nolan monochrome aesthetic (existing MCC style)
- Chips: small, compact, `height: 24px`
- Active state: subtle `#4ecdc4` accent (existing VETKA teal)
- Inactive: `#666` gray
- No bright colors, no emojis in production — use unicode symbols

---

## TASK 2: Sandbox Toggle in TaskCard (2h)

### Current:
TaskCard → ▶ Run button → dispatches directly to pipeline

### Target:
TaskCard → ▶ Run button → dropdown menu:
- `⚡ Direct` — current behavior (writes to main)
- `🔒 Sandbox` — creates playground → runs pipeline in it → shows "Review Available"
- `📂 Custom Location` — opens folder picker → sets playground base_dir → then like Sandbox

### Implementation:
1. Add `sandbox_mode` state to TaskCard
2. On dispatch with sandbox:
   ```
   POST /api/debug/playground/create  { task: "...", auto_write: true }
   → returns { playground_id, worktree_path }

   POST /api/debug/task-board/dispatch  { task_id, preset, playground_id }
   ```
3. TaskCard badge: `🔒` icon when running in sandbox
4. When pipeline completes in sandbox → TaskCard shows `[Review]` button

### Endpoint reference:
```
POST /api/debug/playground/create
  Body: { task?: string, auto_write?: bool }
  Returns: { playground_id, worktree_path, branch, config }

POST /api/debug/task-board/dispatch
  Body: { task_id?: string, preset?: string, playground_id?: string }
```

---

## TASK 3: Playground Review Tab in MCC (3h)

### Where:
New tab in MCC: `MCC | STATS | ARCHITECT | PLAYGROUND | BALANCE | MYC`

### Content:
Left panel: List of playgrounds with status badges
Right panel: Diff viewer for selected playground

### Playground List:
```
┌─────────────────────────────────────┐
│ 🔒 pg_abc123 — "Add toggleBookmark"│
│    Status: review_ready             │
│    Files: 3 changed                 │
│    Created: 2 min ago               │
│    [Review] [Reject] [Destroy]      │
├─────────────────────────────────────┤
│ 🔄 pg_def456 — "Fix CSS hover"     │
│    Status: active (pipeline running)│
│    [Cancel]                         │
├─────────────────────────────────────┤
│ ⚪ No more playgrounds              │
└─────────────────────────────────────┘
```

### Review Panel (when [Review] clicked):
```
GET /api/debug/playground/{pg_id}/review
Returns:
{
  playground_id, task, branch,
  changed_files: [
    { path: "src/store/useStore.ts", status: "modified", diff: "unified diff..." },
    { path: "src/components/Star.tsx", status: "new", diff: "full content..." }
  ],
  total_changes: 3
}
```

### Diff Viewer:
- Reuse existing `DiffViewer.tsx` from Phase 128.4
- Per-file: checkbox (☑ include / ☐ skip)
- File list with expand/collapse per file
- Header: file path + status (modified/new/deleted)

### Action Buttons:
```
[✅ Promote All] — POST /playground/{pg_id}/promote { strategy: "copy" }
[🚀 Promote Selected] — POST /playground/{pg_id}/promote { files: [...checked], strategy: "copy" }
[❌ Reject] — POST /playground/{pg_id}/reject { reason: "...", destroy: true }
```

### Promote Response:
```json
{
  "success": true,
  "promoted_files": ["src/store/useStore.ts", "src/components/Star.tsx"],
  "errors": [],
  "destroyed": true
}
```

### Post-Promote:
- Show success toast
- Emit `vetka-tree-refresh-needed` for 3D tree
- Playground disappears from list
- TaskCard updates status

---

## TASK 4: Settings Panel (1h)

Part of HeaderSettings (Task 1C). Additional settings beyond heartbeat:

### Playground Settings:
```
GET /api/debug/playground/settings
Returns: { base_dir, max_concurrent, ttl_hours, auto_destroy_on_promote }

PATCH /api/debug/playground/settings
Body: { base_dir?: string, max_concurrent?: number, ttl_hours?: number }
```

### UI:
- Base directory: text input with `/` button (folder picker)
- Max concurrent: number spinner (1-10, default 5)
- TTL hours: number spinner (1-24, default 4)
- Auto-destroy on promote: toggle (default: on)

---

## EXISTING COMPONENTS TO REUSE

| Component | Location | Use For |
|-----------|----------|---------|
| `DiffViewer.tsx` | `client/src/components/panels/` | Playground review diffs |
| `TaskCard.tsx` | `client/src/components/panels/` | Add sandbox toggle |
| `MCCTaskList.tsx` | `client/src/components/mcc/` | Remove heartbeat from footer |
| `DevPanel.tsx` | `client/src/components/panels/` | Reference for Nolan styling |
| `useSocket.ts` | `client/src/hooks/` | Listen for playground events |

---

## API ENDPOINTS REFERENCE (All backend ready)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /api/debug/playground` | GET | List all playgrounds |
| `POST /api/debug/playground/create` | POST | Create new sandbox |
| `GET /api/debug/playground/{pg_id}/review` | GET | Get diffs per file |
| `POST /api/debug/playground/{pg_id}/promote` | POST | Promote files to main |
| `POST /api/debug/playground/{pg_id}/reject` | POST | Reject + optional destroy |
| `DELETE /api/debug/playground/{pg_id}` | DELETE | Destroy playground |
| `GET /api/debug/playground/settings` | GET | Get config |
| `PATCH /api/debug/playground/settings` | PATCH | Update config |
| `GET /api/debug/heartbeat/settings` | GET | Heartbeat config |
| `POST /api/debug/heartbeat/settings` | POST | Update heartbeat |
| `POST /api/debug/heartbeat/tick` | POST | Manual tick |

---

## PRIORITY ORDER

1. **Task 1A: HeartbeatChip** — most impactful, moves key control to visible location
2. **Task 1B: PlaygroundBadge** — pairs with heartbeat for autonomy dashboard
3. **Task 2: Sandbox Toggle** — enables sandbox workflow
4. **Task 3: Review Tab** — enables promote workflow (the full value)
5. **Task 4: Settings** — polish

---

*Brief by Opus Commander | Phase 148 | All backend endpoints tested and ready*
