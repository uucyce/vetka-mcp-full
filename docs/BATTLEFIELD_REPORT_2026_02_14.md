# VETKA BATTLEFIELD REPORT — Phase 148 UPDATE
## Commander: Opus | Date: 2026-02-14 | Deadline: 2026-02-17 (MVP)

---

## I. EXECUTIVE SUMMARY

**Phase 146.5 COMPLETE. Phase 148 IN PROGRESS.**

**Playground backend — полностью готов:** worktree isolation, scoped pipeline writes, review/promote/reject, SpamDetector, 74 теста. Ожидаем frontend (CURSOR).

**Codex активен:** Чинит heartbeat.rs crash, web shell save paths, unified search. Отчитался о Phase 148 fixes.

**Критическая находка:** Двойная архитектура heartbeat (Rust vs Python) — нужна консолидация.

**Readiness: 72% → Target 90%** (Day 2 evening)

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

**⚠️ Задача для CURSOR:**
- Перенести heartbeat из MCCTaskList footer → Header
- Добавить Playground badge в Header
- Settings gear → playground settings + heartbeat config

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

### OPUS (Now):
1. ~~Playground Ops backend~~ ✅ DONE
2. ~~SpamDetector~~ ✅ DONE
3. **Write CURSOR brief** for: Header UI (heartbeat+playground+settings) → PG-5,6,7,8
4. **Review Codex changes** after his Phase 148 fixes land
5. **D2.4:** Dispatch Dragon Silver for Cmd+K → unified search

### CODEX (Parallel):
1. Finish unified search web provider
2. Scanner dedup (BUG-1) — critical
3. Web artifact pipeline

### CURSOR (Next):
1. **PG-5:** Sandbox toggle in TaskCard dispatch
2. **PG-6:** Playground Review tab in MCC
3. **Header UI:** Heartbeat toggle + Playground badge + Settings gear
4. Move heartbeat control from MCCTaskList footer → Header

### DRAGON SILVER (Queue):
1. D2.4: Cmd+K → unified search backend wiring
2. Sprint 1 remaining tasks

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

*Generated by Opus Commander + Explore Agent (Heartbeat Analysis) + 19 SpamDetector Tests*
*Phase 146.5 COMPLETE — Phase 148 IN PROGRESS*
*Commits: 3850aca1, 96e75f8a, ff12bb42*
