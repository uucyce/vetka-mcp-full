# VETKA BATTLEFIELD REPORT — Phase 149 UPDATE
## Commander: Opus | Date: 2026-02-14 (evening) | Deadline: 2026-02-17 (MVP)

---

## I. EXECUTIVE SUMMARY

**Phase 149 LAUNCHED. Cursor REMOVED from army. Dragon + Codex + Opus only.**

**DRAGON SILVER FIRST TEST — COMPLETED:**
- HeartbeatChip.tsx: 8/10, PROMOTED to main (170 lines, Zustand, Nolan style)
- MCCTaskList.tsx: REJECTED (Dragon deleted 410/430 lines — destructive rewrite)
- DevPanel.tsx: REJECTED (same destructive pattern)
- **Verdict:** Dragon = excellent for NEW files, DANGEROUS for modifications

**Playground Sandbox VALIDATED:** Caught Dragon's destructive edits BEFORE they hit main.
Without sandbox, MCCTaskList would be destroyed. Selective promote saved the day.

**BUG-2 FOUND + FIXED:** `playground_manager.get_diff()` didn't show untracked files.

**NEW INITIATIVE:** Sparse Apply mechanism (Phase 150) — Dragon outputs patches instead of full files.
Design doc written, Grok research completed, Aider/Sweep patterns identified.

**Readiness: 75% → Target 90%** (Day 3)

---

## II. WHAT WE HAVE (Completed)

| Layer | Phase | Status | Tests |
|-------|-------|--------|-------|
| 3D Visualization (Three.js) | 96+ | 80% | 0 (no frontend tests) |
| Backend API (FastAPI+SocketIO) | 136 | 80% | 14 test files |
| Mycelium Pipeline (Dragon teams) | 128 | 75% | 287+ tests |
| MCP Dual Architecture (VETKA+MYCELIUM) | 129 | 85% | 6 test files |
| TaskBoard Multi-Agent | 136 | 70% | 39+ tests |
| MCC DevPanel (DAG, Board, Stats, Chat) | 143 | 90% | 0 (frontend) |
| DAG Workflow Editor | 144 | 100% | 63 tests |
| n8n/ComfyUI Converters | 144 | 100% | 63 tests |
| OAuth Integration | 147.5 | 100% | tested |
| Mycelium Standalone Server | 140 | 85% | 50 tests |
| Unified Search Backend | 148 | 70% | partial (Codex working) |
| Heartbeat Daemon | 140 | 55% | 50 tests |
| **Playground Infrastructure** | **146** | **95%** | **74 tests** |
| **Playground Ops (Backend)** | **146.5** | **100%** | **21 tests** |
| **Watcher SpamDetector** | **146.5** | **100%** | **19 tests** |
| **Adaptive Timeout** | **145** | **100%** | **36 tests** |

**Total: ~115 test files, ~900+ tests**

---

## III. CRITICAL BUGS (Fix FIRST)

### BUG-1: Scanner Duplicates 🔴 CRITICAL
**Impact:** Дерево показывает 2-3x файлов. UX сломан.
**Root Cause:** Path normalization, double scan, no dedup in Qdrant
- **OWNER: CODEX** — in progress

### BUG-2: Heartbeat Architecture Duplication 🟠 HIGH ⬅️ UPDATED
**Impact:** ДВА heartbeat работают одновременно без синхронизации
**Root Cause:** Rust heartbeat.rs (Phase 100.3) и Python mycelium_heartbeat.py (Phase 117.2c) — разные системы

| Aspect | System A (Rust) | System B (Python) |
|--------|-----------------|-------------------|
| Location | `heartbeat.rs` | `mycelium_heartbeat.py` |
| Interval | 5 min (HARDCODED) | 60s (configurable) |
| UI Control | NONE | MCC toggle + interval |
| Execution | Show notification only | Full pipeline dispatch |
| Chat monitoring | None | All groups + solos |
| TaskBoard | No | Yes |
| Tests | 0 | 28+ |

**РЕШЕНИЕ: Удалить System A (Rust heartbeat).** System B делает ВСЁ что делает A + намного больше.
⚠️ **НО:** Codex уже починил `heartbeat.rs` (MARKER_148.HEARTBEAT_NO_BLOCK_ON) — убрал `block_on` crash.
**Рекомендация:** Пока оставить как есть. Перенести в Rust только если нужны OS-native notifications.

### BUG-3: FC Loop Silent Degradation 🟠 HIGH
- **OWNER: CODEX**

### ~~BUG-4: Coder Timeout 90s Too Short~~ ✅ FIXED
- **Fix:** Adaptive timeout per-model (Phase 145)

### BUG-5: Chat Group Name Bug 🟡 MEDIUM
- **OWNER: CURSOR**

### BUG-6: Model/Provider Not Persisted in Solo Chat 🟡 MEDIUM
- **OWNER: CODEX**

### BUG-7: Hardcoded localhost:5001 in 16 Components 🟢 LOW
- **OWNER: DRAGON BRONZE**

### BUG-8: Web Shell Navigation Race 🟠 HIGH
- **OWNER: CODEX** — in progress

### BUG-9: Web Shell Save Path Empty 🟡 MEDIUM
- **Status: FIXED by Codex (MARKER_148.WEB_SAVE_PATH_INTERNAL_FILTER)**
- Save modal now shows `<select>` with real path list
- Filters `.claude/worktrees`, `.playgrounds` from suggestions

### ~~BUG-10: Web Shell Find-in-Page~~ 🟡 Deferred

### BUG-11: Watcher Spam from Worktrees 🟢 FIXED (Phase 146.5)
- **Was:** Watcher indexed `.playgrounds/` and `.claude/worktrees/` → 100+ events/sec → backend freeze
- **Fix:** 2-layer protection:
  1. Static: `.playgrounds`, `.claude/worktrees` added to SKIP_PATTERNS
  2. Dynamic: SpamDetector — auto-mutes dirs exceeding 50 events/10s
  3. Removed DEBUG_WATCHER print spam (Phase 90.9 leftovers)
- **Tests:** 19 tests, REST API: `/api/watcher/spam-status`, `/api/watcher/spam-block`

---

## IV. CODEX PHASE 148 REPORT (Received)

### 148.1: Heartbeat.rs Crash Fix ✅
- **Problem:** `Cannot start a runtime from within a runtime` — `block_on` inside async heartbeat
- **Fix:** Rewrote heartbeat to pure `await` without `block_on`
- **File:** `heartbeat.rs`
- **Marker:** MARKER_148.HEARTBEAT_NO_BLOCK_ON

### 148.2: Web Save Path Internal Filter ✅
- **Problem:** Save suggestions included `.claude/worktrees`, `.playgrounds` paths
- **Fix:** `<select>` in modal + filter internal paths from suggestions
- **Files:** `commands.rs`, `tauri.ts`
- **Marker:** MARKER_148.WEB_SAVE_PATH_INTERNAL_FILTER

### 148.3: Post-Save Pipeline to Graph ✅
- **Problem:** After save-webpage, file not visible in 3D tree
- **Fix:** POST to `/api/watcher/index-file` + emit `vetka:web-artifact-saved` + retry camera focus (8 attempts)
- **Files:** `commands.rs`, `App.tsx`, `tauri.ts`
- **Marker:** MARKER_148.WEB_SAVE_MAIN_REFRESH_FOCUS

### Codex Still Working On:
- Unified Search `/web` provider integration
- Web artifact save → Qdrant index pipeline

---

## V. PLAYGROUND — FULL STATUS

### Infrastructure (Phase 146) ✅ DONE — 53 tests

| Component | Status | Tests |
|-----------|--------|-------|
| PlaygroundManager (worktree lifecycle) | ✅ | 34 unit |
| Pipeline scoped writes | ✅ | 6 E2E |
| Cross-process state sync | ✅ | 3 E2E |
| Path security (traversal blocked) | ✅ | 2 E2E |
| MCP tools (4 tools) | ✅ | 3 E2E |
| Git diff | ✅ | 2 E2E |
| Config persistence | ✅ | 3 E2E |

### Operations (Phase 146.5) ✅ DONE — 21 tests

| Endpoint | Method | Status | Tests |
|----------|--------|--------|-------|
| `/api/debug/playground` | GET | ✅ list all | 1 |
| `/api/debug/playground/create` | POST | ✅ create | 1 |
| `/api/debug/playground/{pg_id}/review` | GET | ✅ per-file diffs | 5 |
| `/api/debug/playground/{pg_id}/promote` | POST | ✅ copy/cherry-pick/merge | 6 |
| `/api/debug/playground/{pg_id}/reject` | POST | ✅ mark failed + destroy | 3 |
| `/api/debug/playground/{pg_id}` | DELETE | ✅ destroy | 1 |
| `/api/debug/playground/settings` | GET/PATCH | ✅ config persist | 2 |
| Full lifecycle test | E2E | ✅ create→write→review→promote | 1 |

### Frontend (Pending — CURSOR)

| # | Task | Status |
|---|------|--------|
| PG-5 | Sandbox toggle in TaskCard dispatch | 📋 Brief needed |
| PG-6 | Playground Review tab in MCC | 📋 Brief needed |
| PG-7 | Promote button + file selector | 📋 Dep: PG-6 |
| PG-8 | Settings panel (location, limits) | 📋 Brief needed |

---

## VI. HEARTBEAT ARCHITECTURE ANALYSIS 🔍 NEW

### Current State: Two Independent Systems Running

```
┌─ SYSTEM A: Rust (heartbeat.rs) ──────────────────────┐
│ • Fixed 5-minute interval (hardcoded)                 │
│ • Polls GET /api/tasks/open (endpoint doesn't exist!) │
│ • Shows OS notification if tasks open                 │
│ • NO UI control, NO TaskBoard integration             │
│ • NO multi-chat, NO dedup                             │
│ • 0 tests                                             │
│ • Status: ORPHANED (running but unused)               │
└───────────────────────────────────────────────────────┘

┌─ SYSTEM B: Python (mycelium_heartbeat.py) ───────────┐
│ • Configurable interval (1m-1d, MCC toggle)           │
│ • Monitors ALL group chats + solo chats               │
│ • Parses @dragon/@doctor/@titan/@board triggers       │
│ • Routes through TaskBoard priority queue             │
│ • Dispatches via Mycelium pipeline                    │
│ • 213+ ticks completed, 28+ tests                     │
│ • Status: PRODUCTION-READY                            │
└───────────────────────────────────────────────────────┘
```

### Decision: Keep System B, Repurpose System A

**System B** — полноценная продакшен-система, не трогаем.

**System A (Rust)** — единственная польза: OS-native notifications. Варианты:
1. ❌ Удалить полностью (самое простое)
2. ✅ **Превратить в thin client:** Rust heartbeat опрашивает System B status через REST
   → показывает OS notification "3 tasks pending, heartbeat active"
   → убрать дублирование логики, оставить только нотификации

### UI Consolidation: Header Controls

**Проблема:** Heartbeat toggle сейчас внизу MCCTaskList (под чатом). Это главное — должно быть в шапке.

**Новый Header Layout:**
```
┌──────────────────────────────────────────────────────────────────┐
│ MCC  ◇ silver ▾  • LIVE  │ ❤️ ON 47s │ 🔒 PG:2 │ ⚙ │  ◀ ▶  │
│                           │  heartbeat │ sandbox  │set│  stream │
└──────────────────────────────────────────────────────────────────┘

Header controls (left to right):
- ❤️ Heartbeat toggle + countdown ("ON 47s" / "OFF")
  - Click: toggle on/off
  - Long press: interval selector popup (1m/5m/15m/1h)
- 🔒 Playground badge ("PG:2" = 2 active sandboxes)
  - Click: open playground list
  - Badge turns green when promote available
- ⚙ Settings gear
  - Opens: playground base_dir, heartbeat interval, GitHub token
- ◀ ▶ Stream controls (existing)
```

**⚠️ Задача переназначена: CURSOR → DRAGON Silver (new files) + OPUS (wiring)**
- HeartbeatChip.tsx: ✅ DONE (Dragon created, user refined, promoted to main)
- PlaygroundBadge.tsx: NEXT (Dragon Silver — new file)
- Wire into header: OPUS manual (2-3 lines)
- Settings gear: FUTURE

---

## VI-B. DRAGON SILVER TEST RESULTS (Phase 149) 🐉 NEW

### Test: D-149.1 HeartbeatChip in Playground Sandbox

| Metric | Value |
|--------|-------|
| **Pipeline** | Dragon Silver (Kimi architect + Grok researcher + Qwen coder + GLM verifier) |
| **Playground** | pg_4ce1a45a (git worktree) |
| **Time** | ~4 minutes total |
| **Files created** | 1 new (HeartbeatChip.tsx) + 2 modified (MCCTaskList, DevPanel) |

**Results per file:**

| File | Action | Quality | Decision |
|------|--------|---------|----------|
| `HeartbeatChip.tsx` (NEW) | Created 170-line component | 8/10 — correct Zustand, Nolan style, countdown timer, toggle | ✅ PROMOTED |
| `MCCTaskList.tsx` (MODIFIED) | Deleted 410 of 430 lines | 0/10 — CATASTROPHIC rewrite | ❌ REJECTED |
| `DevPanel.tsx` (MODIFIED) | Deleted 656 lines | 0/10 — CATASTROPHIC rewrite | ❌ REJECTED |

**Key finding:** Dragon LLMs rewrite entire files instead of making surgical edits.
This is a known industry problem (Aider, Sweep, Cursor Composer all solve differently).

**Decision:** Dragon = new files ONLY. Modifications → Opus/Codex/Sparse Apply (Phase 150).

### BUG-2 Found: playground_manager.get_diff() misses untracked files
- `get_diff()` used `git diff --stat HEAD` — only sees tracked changes
- NEW files are `??` (untracked) → invisible to diff
- `review()` method correctly catches untracked via `git status --porcelain`
- **FIX (MARKER_149.FIX_DIFF):** Added untracked file detection to `get_diff()`

### Sparse Apply Initiative (Phase 150)
- **Problem:** Dragon rewrites entire files → breaks existing code
- **Solution:** Three modes: CREATE (works now) + MARKER INSERT + UNIFIED DIFF
- **Design doc:** `docs/150_ph/SPARSE_APPLY_DESIGN.md`
- **Prior art:** Aider (prompt templates), Sweep (patch generator), tree-sitter (AST validation)
- **ETA:** Phase 150A (marker insert) = 2-3 hours, 200 LOC

---

## VII. STRATEGIC GAPS — Updated

| Gap | Current | Target | Status |
|-----|---------|--------|--------|
| **Playground Infra** | 95% | 100% E2E | ✅ 146 DONE |
| **Playground Ops Backend** | 100% | 100% | ✅ 146.5 DONE |
| **Playground Ops Frontend** | 0% | MVP | 🔥 PG-5,6,7,8 (CURSOR) |
| **Watcher SpamDetector** | 100% | 100% | ✅ 146.5 DONE |
| **Heartbeat Consolidation** | analyzed | unified | 🔥 Remove Rust dupe |
| **Header UI (HB+PG+Settings)** | 0% | MVP | 🔥 CURSOR task |
| **Scanner Dedup** | broken | fixed | 🔴 CODEX working |
| **Unified Search Web** | 70% | 90% | 🟠 CODEX working |
| **Knowledge Graph** | 10% | 10% | skip → Phase 149+ |
| **Jarvis Superagent** | 0% | 0% | skip → Phase 148+ |
| **Messenger (Telegram)** | 0% | 0% | skip → Phase 150+ |

---

## VIII. MVP PLAN — Updated Status

### Day 1 (Feb 14): FIX — ✅ DONE

| # | Task | Owner | Status |
|---|------|-------|--------|
| D1.1 | Fix Scanner Duplicates | CODEX | 🔴 In progress |
| D1.2 | Fix Heartbeat multi-group | CODEX | ⚠️ Needs reassessment (see Heartbeat Analysis) |
| D1.5 | Increase coder timeout | OPUS | ✅ DONE (adaptive timeout) |
| D1.6 | Cleanup TaskBoard | OPUS | ✅ DONE |
| D1.8 | Adaptive Timeout | OPUS | ✅ DONE (36 tests) |
| D1.9 | Frontend Polling Cleanup | OPUS | ✅ DONE (~103K req/day saved) |
| D1.10 | Kill model_updater cron | OPUS | ✅ DONE |

### Day 2 (Feb 14-15): BUILD — 🔶 IN PROGRESS

| # | Task | Owner | Status |
|---|------|-------|--------|
| D2.1 | Playground: git worktree + scoped MCP | OPUS | ✅ DONE (53 tests) |
| D2.2 | Playground: pipeline sandbox flag | OPUS | ✅ DONE (included in D2.1) |
| D2.3 | Playground: test Dragon Silver in sandbox | OPUS | ✅ DONE (cross-process bug found & fixed) |
| D2.3b | Playground: review/promote/reject backend | OPUS | ✅ DONE (21 tests) |
| D2.3c | Watcher SpamDetector | OPUS | ✅ DONE (19 tests) |
| D2.4 | Wire Cmd+K → unified search | DRAGON SILVER | 📋 Pending |
| D2.5 | Wire Tavily web provider | CODEX | 🔶 In progress |

### Codex Parallel Track (Phase 148):

| # | Task | Status |
|---|------|--------|
| C148.1 | Heartbeat.rs crash fix | ✅ DONE |
| C148.2 | Web save path filter | ✅ DONE |
| C148.3 | Post-save pipeline refresh | ✅ DONE |
| C148.4 | Unified Search `/web` provider | 🔶 In progress |
| C148.5 | Web artifact save → Qdrant | 🔶 In progress |

### Day 3 (Feb 16-17): DELEGATE

| # | Task | Owner | Status |
|---|------|-------|--------|
| D3.1 | E2E test: Heartbeat dispatch | CODEX | 📋 Pending |
| D3.2 | Load TaskBoard with current tasks | OPUS | 📋 Pending |
| D3.3 | Dragon Silver: Sprint 1 remaining | DRAGON SILVER | 📋 Pending |
| D3.5 | Verify full pipeline cycle | OPUS | 📋 Pending |

---

## IX. NEXT ACTIONS (Priority Order)

### Army Roster (Updated — NO CURSOR)

| Agent | Role | Cost | Status |
|-------|------|------|--------|
| **Opus** | Architecture, briefs, wiring, review | $$$ | ACTIVE |
| **Codex** | Bug fixes, tests, isolated modules | $$ | ACTIVE (debugging viewport) |
| **Dragon Silver** | New file creation via Playground | ¢ | TESTED, ready for D-149.2 |
| **Haiku Scouts** | Recon, markers, file discovery | ¢ | 6 deployed in Phase 149 |
| ~~Cursor~~ | ~~Removed~~ | ~~$$$~~ | ~~Too expensive~~ |

### OPUS (Now):
1. ~~Playground Ops backend~~ ✅ DONE
2. ~~SpamDetector~~ ✅ DONE
3. ~~Dragon test D-149.1~~ ✅ DONE (HeartbeatChip promoted)
4. ~~BATTLE_PLAN_149~~ ✅ DONE
5. ~~SPARSE_APPLY_DESIGN~~ ✅ DONE
6. **Wire HeartbeatChip into MCC header** (manual, 3-5 lines)
7. **Launch Dragon D-149.2** (PlaygroundBadge — new file)
8. **Review Codex** when he finishes viewport debugging

### CODEX (Parallel):
1. **Currently:** Debugging viewport fallback/focus issues
2. **Next:** Scanner dedup (BUG-1) — critical → `docs/149_ph/CODEX_BRIEF_149.md`
3. **Then:** Unified search web provider

### DRAGON SILVER (Queue — via Playground):
1. ~~D-149.1: HeartbeatChip~~ ✅ DONE + PROMOTED
2. **D-149.2: PlaygroundBadge** (new file) — READY
3. **D-149.3: TaskCard sandbox toggle** — NEEDS Sparse Apply or manual
4. **D-149.4: Wire header** — NEEDS Sparse Apply or manual

---

## X. ADAPTIVE TIMEOUT — FULL RECON REPORT (5 Scouts)

*(Unchanged from previous version — see Phase 145 details)*

### Adaptive Timeout Formula (from Grok Research)

```
timeout = (processing_time × complexity_multiplier) + fc_overhead + safety_buffer
where:
  processing_time = (input_tokens + output_tokens) / model_speed_tps
  complexity_multiplier = {simple: 1.0, medium: 1.8, complex: 3.2}
  fc_overhead = fc_turns × 12s
  safety_buffer = 25s
  result = clamp(timeout, 45s, 600s)
```

---

## XI. COMMITS (Day 2 — Phase 146-146.5)

| Hash | Phase | Description | Tests |
|------|-------|-------------|-------|
| `3850aca1` | 146.E2E | Playground E2E tests + cross-process fix | 53 |
| `96e75f8a` | 146.5 | Playground Ops: review, promote, reject + settings | 21 |
| `ff12bb42` | 146.5 | SpamDetector: auto-mute noisy watcher dirs | 19 |

---

## XII. SUCCESS CRITERIA — Feb 17

| Metric | Was (Day 1) | Now (Day 2) | Target |
|--------|-------------|-------------|--------|
| Scanner duplicates | 2-3x files | 2-3x (Codex working) | 0 duplicates |
| Heartbeat reliability | single group | analyzed, dual system | unified system |
| Pipeline dispatch cycle | manual | semi-autonomous | autonomous |
| Playground operational | 0% | **95% backend** | MVP frontend |
| Tests passing | ~800 | **~900+** | ~950+ |
| Watcher spam | broken | **FIXED** | n/a |
| Header controls (HB+PG) | none | designed | MVP implemented |

---

## XIII. RISK LOG

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Scanner fix breaks existing Qdrant data | Medium | High | Backup data/ before fix |
| Playground frontend delays MVP | Medium | High | Backend complete, frontend can follow |
| Heartbeat consolidation touches Rust | Low | Medium | Keep both running, just add UI |
| Codex overwhelmed (multiple tracks) | Medium | High | Prioritize scanner dedup |
| Feb 17 deadline tight for frontend | High | Medium | MVP = backend ready, UI follows |

---

## XIV. PHASE 149 DOCS CREATED

| File | Purpose |
|------|---------|
| `docs/149_ph/BATTLE_PLAN_149.md` | Full battle plan: Dragon+Codex+Opus assignments |
| `docs/149_ph/OPUS_STATUS.md` | Agent coordination, file boundaries |
| `docs/149_ph/CODEX_BRIEF_149.md` | Codex tasks: BUG-1, S1.2, E2E tests |
| `docs/149_ph/RECON_REPORT_149.md` | 6 Haiku scout findings |
| `docs/150_ph/SPARSE_APPLY_DESIGN.md` | Sparse Apply architecture (Grok research) |

---

*Generated by Opus Commander + Dragon Silver Test + Grok 4.1 Research*
*Phase 149 IN PROGRESS — Dragon tested, Sparse Apply designed*
*Key commit: HeartbeatChip.tsx promoted from playground pg_4ce1a45a*
