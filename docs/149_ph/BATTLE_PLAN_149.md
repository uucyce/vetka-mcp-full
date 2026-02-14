# BATTLE PLAN — Phase 149: Frontend Offensive
## Commander: Opus | Date: 2026-02-14

---

## STRATEGIC DECISION

**Cursor (Claude) REMOVED from army.** Token burn too expensive.

New army composition:
| Regiment | Model | Cost | Role |
|----------|-------|------|------|
| **Opus** (you) | Claude Opus | $$$ | Architecture, briefs, final review ONLY |
| **Codex** | Claude Code (worktree) | $$ | Isolated modules, tests, bug fixes |
| **Dragon Silver** | Kimi+Grok+Qwen+GLM | ¢ | Frontend implementation via Playground |
| **Haiku Scouts** | Claude Haiku | ¢ | Recon, markers, file discovery |
| **Sonnet Verifiers** | Claude Sonnet | $ | Cross-check scout findings |

**Rule:** Opus writes PLANS, not CODE. Dragon writes CODE. Codex writes TESTS + BUG FIXES.

---

## PHASE 1: RECON (Haiku Scouts) — 5 min

Deploy 6 scouts to map frontend codebase for Dragon:

| Scout | Target | Mission |
|-------|--------|---------|
| H1 | `client/src/components/mcc/` | Map MCC header structure, find where to inject HeartbeatChip + PlaygroundBadge |
| H2 | `client/src/components/panels/DevPanel.tsx` | Map existing heartbeat toggle location, understand removal plan |
| H3 | `client/src/components/panels/TaskCard.tsx` | Map Run button, find injection point for sandbox dropdown |
| H4 | `client/src/hooks/useSocket.ts` | Map existing socket events, find where to add playground events |
| H5 | `client/src/components/mcc/MCCTaskList.tsx` | Find heartbeat logic to MOVE (not duplicate) to header |
| H6 | `src/api/routes/debug_routes.py` | Verify all 8 playground endpoints exist and response format |

Each scout: read files, leave MARKER_149.H{N} tags, report structure.

---

## PHASE 2: VERIFY (Sonnet) — 3 min

2 Sonnet verifiers cross-check:
| Verifier | Scope |
|----------|-------|
| V1 | Check H1-H3 markers: are injection points correct? Any missing imports? |
| V2 | Check H4-H6 markers: are socket events + API endpoints correctly mapped? |

Output: **RECON_REPORT_149.md** — unified findings.

---

## PHASE 3: DRAGON EXECUTION — 4 tasks in Playground sandbox

### DRAGON TASK D-149.1: HeartbeatChip Component (Dragon Silver)

**What:** Create `<HeartbeatChip />` component for MCC header
**Where:** `client/src/components/mcc/HeartbeatChip.tsx` (NEW file)
**Reads first:**
- `client/src/components/mcc/MCCTaskList.tsx` (existing heartbeat toggle — MOVE logic from here)
- `client/src/hooks/useSocket.ts` (socket event pattern)
- `client/src/components/panels/DevPanel.tsx` (Nolan styling reference)

**Requirements:**
- Shows `ON 47s` (green pulse) or `OFF` (gray) — NO emoji in production
- Click: toggle heartbeat on/off → `POST /api/debug/heartbeat/settings`
- Compact chip: `height: 24px`, monochrome Nolan style
- Fetch state: `GET /api/debug/heartbeat/settings` → `{ enabled, interval_seconds, last_tick }`
- Listen: `task-board-updated` CustomEvent for tick updates
- Export: `export const HeartbeatChip: React.FC = () => { ... }`
- Use Zustand store if state needed, NOT MobX, NOT Redux
- Styling: inline or CSS module, `#111` bg, `#e0e0e0` text, `#4ecdc4` active accent

**Acceptance:** Component renders, toggles heartbeat via API, shows live tick count.

---

### DRAGON TASK D-149.2: PlaygroundBadge Component (Dragon Silver)

**What:** Create `<PlaygroundBadge />` for MCC header
**Where:** `client/src/components/mcc/PlaygroundBadge.tsx` (NEW file)
**Reads first:**
- `client/src/components/mcc/HeartbeatChip.tsx` (D-149.1 output — same pattern)
- `client/src/hooks/useSocket.ts` (event pattern)

**Requirements:**
- Shows `PG:2` (active count) or `PG:0` (gray)
- Click: dropdown list of active playgrounds
- Each dropdown item: name, task, `[Review]` `[Destroy]` buttons
- Glow green border when any playground has review_ready status
- Data: `GET /api/debug/playground` → array of playground objects
- Compact chip: same 24px height, Nolan monochrome
- Use Zustand, NOT MobX

**Acceptance:** Component renders count, dropdown shows playground list.

---

### DRAGON TASK D-149.3: Sandbox Toggle in TaskCard (Dragon Silver)

**What:** Add sandbox dispatch option to TaskCard run button
**Where:** `client/src/components/panels/TaskCard.tsx` (MODIFY existing)
**Reads first:**
- `client/src/components/panels/TaskCard.tsx` (MUST read current code first!)
- Previous D-149.1 or D-149.2 for style reference

**Requirements:**
- Run button `>` becomes dropdown with 2 options:
  - `Direct` — current behavior (POST dispatch as-is)
  - `Sandbox` — creates playground first, then dispatches with playground_id
- Sandbox flow:
  1. `POST /api/debug/playground/create { task: taskTitle }`
  2. Get `playground_id` from response
  3. `POST /api/debug/task-board/dispatch { task_id, preset, playground_id }`
- Show lock icon on card when running in sandbox
- When done in sandbox: show `[Review]` button
- Keep existing dispatch logic intact, add sandbox as option

**Acceptance:** Can dispatch task in both Direct and Sandbox modes.

---

### DRAGON TASK D-149.4: Wire Header + Remove Old Toggle (Dragon Silver)

**What:** Wire HeartbeatChip + PlaygroundBadge into MCC header, remove old heartbeat from footer
**Where:**
- MODIFY: MCC header component (find via H1 scout markers)
- MODIFY: `client/src/components/mcc/MCCTaskList.tsx` (remove heartbeat toggle)
**Reads first:**
- MCC header file (from H1 scout report)
- `client/src/components/mcc/MCCTaskList.tsx`
- `client/src/components/mcc/HeartbeatChip.tsx` (D-149.1 output)
- `client/src/components/mcc/PlaygroundBadge.tsx` (D-149.2 output)

**Requirements:**
- Import and render HeartbeatChip + PlaygroundBadge in header, right of LIVE badge
- Layout: `LIVE | HeartbeatChip | PlaygroundBadge | SettingsGear`
- Remove heartbeat toggle from MCCTaskList footer
- DO NOT break existing header layout — add to right side only

**Acceptance:** Header shows both chips. Old footer toggle removed. No layout breaks.

---

## PHASE 4: CODEX TASKS (parallel with Dragon)

### CODEX TASK C-149.1: Fix BUG-1 Scanner Duplicates (CRITICAL)
**Priority:** P0 — blocks tree visualization quality
**Branch:** codex worktree (isolated)
**Brief:** Scanner shows 2-3x duplicate files in tree. Find root cause in scanner/indexer and fix.

### CODEX TASK C-149.2: Complete S1.2 Unified Search Web Provider
**Priority:** P1 — already 70% done
**Files:** `src/api/handlers/unified_search.py`
**Brief:** Wire Tavily web search as 'web' source in federated router. Score normalization.

### CODEX TASK C-149.3: E2E Tests for Playground Review Flow
**Priority:** P2 — after D-149.1-4 land
**Brief:** Write tests for: create playground → run pipeline → review diffs → promote → verify files in main.

---

## EXECUTION ORDER

```
TIME  OPUS              CODEX             DRAGON
 0m   Deploy Scouts     Start C-149.1     (waiting)
 5m   Verify (Sonnet)   Working...        (waiting)
 8m   RECON_REPORT      Working...        Start D-149.1 (HeartbeatChip)
      Write this plan   Working...        D-149.1 running in Playground
15m   Review D-149.1    C-149.1 done?     Start D-149.2 (PlaygroundBadge)
22m   Review D-149.2    Start C-149.2     Start D-149.3 (TaskCard sandbox)
30m   Review D-149.3    Working...        Start D-149.4 (Wire header)
38m   FINAL REVIEW      C-149.2 done?     ALL DONE
40m   Promote from PG   Start C-149.3     ---
45m   COMMIT & DONE     Tests passing     ---
```

---

## MYCELIUM CONTROL STRATEGY

**Problem:** Dragon produces code but we can't easily review before it hits main.

**Solution — Playground Sandwich:**
1. Create playground BEFORE each Dragon task → `mycelium_playground_create`
2. Run Dragon pipeline IN playground → `mycelium_pipeline` with `playground_id`
3. Review diffs AFTER → `mycelium_playground_diff`
4. Promote good code / Reject bad → `mycelium_playground_promote` / `reject`

**Monitoring during execution:**
- DevPanel Activity Log shows real-time progress
- `mycelium_tracker_status` for quick status check
- Cancel via `task_board cancel` if going off rails

**Quality gate:** Opus reviews EVERY Dragon output before promote. No auto-promote.

---

## SUCCESS CRITERIA

- [ ] HeartbeatChip in header, working toggle
- [ ] PlaygroundBadge in header, shows count
- [ ] TaskCard has sandbox dispatch option
- [ ] Old heartbeat toggle removed from footer
- [ ] BUG-1 scanner duplicates fixed
- [ ] Unified Search web provider wired
- [ ] All runs through Playground sandbox (dogfooding)

---

*Battle Plan by Opus Commander | Phase 149 | NO CURSOR — Dragon + Codex army*
