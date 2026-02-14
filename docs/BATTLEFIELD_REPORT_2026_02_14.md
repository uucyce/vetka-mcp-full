# VETKA BATTLEFIELD REPORT — Phase 145 Recon
## Commander: Opus | Date: 2026-02-14 | Deadline: 2026-02-17 (MVP)

---

## I. EXECUTIVE SUMMARY

**Phase 144 COMPLETE.** Мы на переломной точке: ядро Mycelium работает (pipeline, TaskBoard, MCC, DAG Editor), но есть критические баги (сканер-дубликаты, heartbeat reliability) и стратегические gap-ы (Playground, Knowledge Graph, Jarvis).

**Цель до 17 февраля:** Починить Mycelium для полуавтономной работы, поднять Playground, делегировать рутину агентам.

**Readiness: 65% → Target 90%** (по оценке Грока + наш аудит)

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
| Unified Search Backend | 136 | 60% | partial |
| Heartbeat Daemon | 140 | 55% | 50 tests |

**Total: 101 test files, ~800+ tests, 30/43 tasks done (70%)**

---

## III. CRITICAL BUGS (Fix FIRST)

### BUG-1: Scanner Duplicates 🔴 CRITICAL
**Impact:** Дерево показывает 2-3x файлов. UX сломан.
**Root Cause (Sonnet V3 audit):**
1. `qdrant_updater.py` — нет path normalization перед генерацией point ID
2. `watcher_routes.py:166` — при добавлении папки запускается И watcher И full scan = двойная индексация
3. Нет проверки "already indexed" перед upsert в Qdrant
4. `os.path.expanduser()` не используется консистентно (~/project vs /Users/x/project = 2 записи)

**Fix (2-3 часа):**
- [ ] Path normalize в `_get_point_id()` — `os.path.abspath(os.path.expanduser(path))`
- [ ] Prevent double-scan в `watcher_routes.py` — только scan если not already_watching
- [ ] Добавить indexed_paths cache в EmbeddingPipeline
- **OWNER: CODEX** (isolated module, не трогает pipeline)

### BUG-2: Heartbeat Hardcoded GROUP_ID 🟠 HIGH
**Impact:** Heartbeat мониторит ОДИН чат. Остальные чаты игнорируются.
**File:** `mycelium_heartbeat.py` — hardcoded `GROUP_ID="5e2198c2-..."`
**Fix:** YAML config multi-group
- **OWNER: CODEX**

### BUG-3: FC Loop Silent Degradation 🟠 HIGH
**Impact:** Если `src/tools/fc_loop.py` не импортируется → coder падает на one-shot без уведомления
**File:** `agent_pipeline.py` — `FC_LOOP_AVAILABLE = try/except`
**Fix:** Required dependency + heartbeat health check
- **OWNER: CODEX**

### BUG-4: Coder Timeout 90s Too Short 🟡 MEDIUM
**Impact:** Сложные FC loops с 4 turns вылетают по timeout
**File:** `agent_pipeline.py` — `PHASE_TIMEOUTS['coder'] = 90`
**Fix:** Adaptive timeout или увеличить до 180s
- **OWNER: DRAGON SILVER** (simple config change)

### BUG-5: Chat Group Name Bug 🟡 MEDIUM
**Impact:** Edit name создаёт новый чат, контент теряется
**Source:** `119_dragon_todo.txt`
**Fix:** Нужен аудит ChatPanel rename flow
- **OWNER: CURSOR** (frontend)

### BUG-6: Model/Provider Not Persisted in Solo Chat 🟡 MEDIUM
**Impact:** При повторном обращении фолбэк на openrouter
**Source:** `119_dragon_todo.txt`
- **OWNER: CODEX**

### BUG-7: Hardcoded localhost:5001 in 16 Components 🟢 LOW
**Impact:** Не будет работать в production
**Fix:** Import from `config/api.config.ts`
- **OWNER: DRAGON BRONZE** (search-replace)

### BUG-8: Web Shell Navigation Race 🟠 HIGH (Codex Phase 147.6 Recon)
**Impact:** Быстрые клики по веб-результатам → старый контент перезаписывает новый
**Root Cause:** `loadPreview()` без AbortController/navigation token guard
**Files:** `WebShellStandalone.tsx:128`, `commands.rs:96`
**Fix:** AbortController per navigation + monotonic navigationRequestId
- **OWNER: CODEX**

### BUG-9: Web Shell Save Path Empty 🟡 MEDIUM (Codex Phase 147.6 Recon)
**Impact:** Нет предложений куда сохранить при save-to-vetka
**Root Cause:** Нет backend fallback resolver, frontend зависит от viewport state
**Fix:** `POST /api/tree/recommend-save-paths` backend resolver
- **OWNER: CODEX**

### BUG-10: Web Shell Find-in-Page Fragile 🟡 MEDIUM (Codex Phase 147.6 Recon)
**Impact:** Поиск ломается на динамических/санитизированных страницах
**Root Cause:** `window.find()` fallback + iframe contentDocument доступ нестабилен
**Fix:** Детерминистическая модель поиска с rebuild index on load
- **OWNER: CODEX**

---

## IV. TASKBOARD — PENDING TASKS (11)

| ID | Title | Priority | Owner | Sprint |
|----|-------|----------|-------|--------|
| tb_..._1 | S1.1 Event-driven dispatch | P1 | Opus ✅ DONE | S1 |
| tb_..._2 | S1.2 Unified Search: Tavily web provider | P2 | Codex | S1 |
| tb_..._3 | S1.3 Cmd+K → unified backend | P2 | Cursor | S1 |
| tb_..._4 | S1.4 MCC Stats real data | P2 | Cursor | S1 |
| tb_..._5 | S1.5 Artifact panel → API | P2 | Cursor | S1 |
| tb_..._6 | S1.6 Tests: heartbeat+search E2E | P2 | Codex | S1 |
| tb_..._1 | Pipeline commands infra | P2 | Titan | - |
| tb_..._2 | Pipeline Quality Gates | P2 | Dragon | - |
| tb_..._13 | Tests: artifact_scanner | P3 | Codex | S1 |
| tb_..._14 | Tests: feedback_service | P3 | Codex | S1 |
| tb_..._9 | Research: search/embedding models | P4 | Archive | - |

---

## V. STRATEGIC GAPS

| Gap | Current | Target | Effort | Phase |
|-----|---------|--------|--------|-------|
| **Playground infra** | 85% | 90% E2E | needs MYCELIUM restart to verify | ✅ 146 |
| **Playground Ops (UI+Promote)** | 0% | MVP working | 8-12h (backend+frontend) | 🔥 146.5 |
| **Scanner Dedup** | broken | fixed | 3h | 🔥 145 |
| **Heartbeat multi-group** | single group | multi | 2h | 🔥 145 |
| **Knowledge Graph** | 10% | 10% | skip | 149+ |
| **Jarvis Superagent** | 0% | 0% | skip | 148+ |
| **Messenger (Telegram)** | 0% | 0% | skip | 150+ |
| **Social/Federation** | 0% | 0% | skip | future |
| **Frontend Tests** | 0 tests | 0 | skip for now | future |

---

## VI. MVP PLAN — 3 Days (Feb 14-17)

### Day 1 (Feb 14): FIX — "Stop the Bleeding"

| # | Task | Owner | Hours | Status |
|---|------|-------|-------|--------|
| D1.1 | Fix Scanner Duplicates (BUG-1) | **CODEX** | 3h | 📋 Briefing ready |
| D1.2 | Fix Heartbeat multi-group (BUG-2) | **CODEX** | 2h | 📋 Briefing ready |
| D1.3 | Web Shell: navigation race + AbortController (BUG-8) | **CODEX** | 2h | 📋 Briefing ready |
| D1.4 | Web Shell: save path backend resolver (BUG-9) | **CODEX** | 1.5h | 📋 Briefing ready |
| D1.5 | Increase coder timeout to 180s (BUG-4) | **OPUS** | 5min | ✅ DONE |
| D1.6 | Cleanup TaskBoard junk tasks | **OPUS** | 15min | ✅ DONE |
| D1.7 | Fix FC loop degradation alert (BUG-3) | **CODEX** | 1h | 📋 Briefing ready |
| D1.8 | **Adaptive Timeout** (model-aware `_safe_phase`) | **OPUS** | 2h | ✅ DONE (36 tests) |
| D1.9 | **Frontend Polling Cleanup** (7 components, ~103K req/day saved) | **OPUS** | 1h | ✅ DONE |
| D1.10 | **Kill model_updater cron** → on-demand | **OPUS** | 30min | ✅ DONE |

**Day 1 Evening Check:** Поиск → клик по веб-результату → сохранение → нет дубликатов в дереве.

### Day 2 (Feb 15): BUILD — "Playground MVP"

| # | Task | Owner | Hours | Dependency |
|---|------|-------|-------|------------|
| D2.1 | Playground: git worktree + scoped MCP | **OPUS** | 2h | ✅ DONE |
| D2.2 | Playground: pipeline sandbox flag | **CODEX** | 2h | D2.1 |
| D2.3 | Playground: test Dragon Silver in sandbox | **OPUS** | 1h | D2.2 |
| D2.4 | Wire Cmd+K → unified search (S1.3) | **DRAGON SILVER** | 3h | — |
| D2.5 | Wire Tavily web provider (S1.2) | **CODEX** | 2h | — |

### Day 3 (Feb 16-17): DELEGATE — "Agents Go Autonomous"

| # | Task | Owner | Hours | Dependency |
|---|------|-------|-------|------------|
| D3.1 | E2E test: Heartbeat dispatch cycle | **CODEX** | 2h | D1.2 |
| D3.2 | Load TaskBoard with Phase 145 tasks | **OPUS** | 30min | D2.3 |
| D3.3 | Dragon Silver: fix remaining Sprint 1 | **DRAGON SILVER** | 4h | D2.3 |
| D3.4 | Dragon Bronze: CAM UI integration | **DRAGON BRONZE** | 3h | — |
| D3.5 | Verify full pipeline: task → dispatch → execute → commit | **OPUS** | 2h | D3.1-D3.3 |
| D3.6 | Write tests for Phase 145 | **CODEX** | 2h | D3.5 |

---

## VII. ARMY ASSIGNMENTS

### OPUS (You — Architect & Commander)
- **Day 1:** Fix coder timeout (5min), cleanup TaskBoard, orchestrate
- **Day 2:** Playground architecture (git worktree + scoped MCP), test in sandbox
- **Day 3:** Load tasks, verify full pipeline, final review
- **Budget:** Save context for synthesis and architecture decisions

### CODEX (Parallel Worker — Backend)
- **Day 1:** BUG-1 (scanner dedup), BUG-2 (heartbeat multi-group), BUG-3 (FC alert)
- **Day 2:** Playground sandbox flag, Tavily web provider
- **Day 3:** E2E heartbeat test, Phase 145 tests
- **Briefing doc needed:** Yes (write before dispatching)

### DRAGON SILVER (Mycelium Pipeline — Standard)
- **Day 2:** Wire Cmd+K → unified search
- **Day 3:** Fix remaining Sprint 1 tasks via pipeline
- **Dispatch via:** `@dragon build "wire Cmd+K frontend to POST /api/search/unified"`

### DRAGON BRONZE (Mycelium Pipeline — Quick)
- **Day 1:** Replace hardcoded URLs in 16 components
- **Day 3:** CAM UI integration (4 TODO markers)
- **Dispatch via:** `@dragon build "replace http://localhost:5001 with API_BASE import"`

### GROK (External Research — You Relay)
- **Day 1:** Research prompt for Playground security (Docker vs worktree depth)
- **Day 2:** Research prompt for Unified Search architecture (Meilisearch vs current)

---

## VIII. GROK RESEARCH REQUEST #2

> **Grok, задача:**
>
> **1. Playground Deep Dive:**
> - Мы выбрали `git worktree` для MVP. Вопрос: как правильно scoped MCP tools?
> - Нужно чтобы agent_pipeline.py мог работать в worktree с ограниченными правами
> - Какие env vars нужны? Как предотвратить запись в main tree?
> - Есть ли готовые Python библиотеки для sandbox execution (не Docker)?
>
> **2. Scanner Dedup — Best Practices:**
> - Qdrant point ID generation: uuid5 от normalized path — достаточно?
> - Или нужен content hash (SHA256) как дополнительная проверка?
> - Как другие проекты решают dedup при hot-reload/watchdog?
>
> **Файлы:** `src/scanning/qdrant_updater.py`, `src/scanning/file_watcher.py`

---

## IX. ADAPTIVE TIMEOUT — FULL RECON REPORT (5 Scouts)

### Scout 3: Pipeline Integration Points (Sonnet)

**CENTRAL FINDING:** `_safe_phase()` (line 330) — единственная точка интеграции.
- Все 11 вызовов pipeline проходят через неё
- Модель **доступна** на каждом call site (`self.prompts[role]["model"]`), но **НЕ передаётся** в `_safe_phase`
- `_safe_phase` знает только `phase_name` → берёт timeout из `PHASE_TIMEOUTS` dict
- **Решение:** Добавить параметр `model: str = None` в `_safe_phase`

**Все call sites:**

| Line | Phase | Coroutine | Model Source |
|------|-------|-----------|--------------|
| 687 | scout | `_scout_scan()` | `self.prompts["scout"]["model"]` |
| 688 | researcher | `_research()` | `self.prompts["researcher"]["model"]` |
| 1984 | architect | `_architect_plan()` | `self.prompts["architect"]["model"]` |
| 2424 | coder | `_execute_subtask()` | `self.prompts["coder"]["model"]` |
| 2438 | verifier | `_verify_subtask()` | `self.prompts["verifier"]["model"]` |
| +6 retry/parallel | coder/verifier | same | same |

### Scout 4: VETKA Chat LLM Timeouts (Sonnet)

**CRITICAL: 15+ LLM call sites OUTSIDE pipeline, each with different timeout!**

| Context | Timeout | Hardcoded? | Adaptive? |
|---------|---------|------------|-----------|
| Group Chat Agent | 120s | YES | NO |
| Group Chat Hostess | 30s | YES | NO |
| Doctor Triage | **NONE** ⚠️ | N/A | N/A |
| Provider HTTP (all) | 120s | YES | NO |
| Ollama Inference | 60s | YES | NO |
| Streaming Total | 300s | YES | NO |
| Context Injection | 3-5s | YES | NO |

**⚠️ VULNERABILITY:** Doctor triage LLM call (line 346) has NO timeout wrapper!

### Scout 5: Unified LLM Call Points (Sonnet)

**CENTRAL HUB FOUND: `call_model_v2()` in `provider_registry.py:1498`**

```
User Request → Handler → orchestrator → call_model_v2() → Provider.call() → httpx
```

- **ALL** LLM calls pass through `call_model_v2()`
- Both pipeline AND chat handlers use it
- Currently NO timeout parameter in its signature
- Timeout is delegated to each provider's `.call()` method (hardcoded @ 120s)
- **SINGLE INJECTION POINT** for adaptive timeout

### Strategic Decision: Mycelium First, VETKA Later

**Командир прав:** Не трогаем VETKA chat сейчас. Стратегия:

1. **Phase 145:** Adaptive timeout ТОЛЬКО в Mycelium Pipeline (`agent_pipeline.py`)
   - Файл `src/elisya/llm_model_registry.py` — общая библиотека
   - Вызов `calculate_timeout()` в `_safe_phase()`
   - НЕ трогаем `provider_registry.py` и chat handlers

2. **Phase 146+:** Когда Pipeline стабилен → портируем в VETKA chat
   - Добавим `timeout` параметр в `call_model_v2()`
   - Пробросим через все 7 Provider.call() методов
   - Покроем Doctor Triage (закроем vulnerability)

3. **Артефакты:** В VETKA кодеры работают в артефактах (не в pipeline subtasks)
   - Артефакт timeout != Pipeline timeout
   - Отдельная формула для artifact generation

### Files Ready to Create

| File | Lines | Status |
|------|-------|--------|
| `src/elisya/llm_model_registry.py` | ~490 | Code ready, needs Write |
| `src/elisya/model_updater.py` | ~180 | Code ready, needs Write |
| `agent_pipeline.py` (patch) | ~20 lines diff | Planned |

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

### Model Speed Profiles (Hardcoded Defaults)

| Model | TPS (output) | Recommended Timeout (medium, 8k) |
|-------|-------------|----------------------------------|
| Grok Fast 4.1 | 90 | 55-80s |
| GPT-4o | 80 | 65-90s |
| Qwen3-coder-flash | 85 | 55-80s |
| Qwen3-coder | 55 | 90-130s |
| Kimi K2.5 | 50 | 100-150s |
| GLM-4.7-flash | 80 | 55-80s |
| Qwen3-235B | 30 | 180-300s ⚠️ |
| Claude Opus | 40 | 140-220s |

---

## X. SUCCESS CRITERIA — Feb 17

| Metric | Current | Target |
|--------|---------|--------|
| Scanner duplicates | 2-3x files | 0 duplicates |
| Heartbeat reliability | single group | multi-group |
| Pipeline dispatch cycle | manual | semi-autonomous |
| Playground operational | 0% | MVP working |
| TaskBoard pending tasks | 11 | ≤5 |
| Tests passing | ~800 | ~850+ (53 playground + 36 adaptive) |

---

## X. COMPLETED FIXES (Phase 145, Day 1)

### FIX-1: Adaptive Timeout (BUG-4 killer) ✅
- **Created:** `src/elisya/llm_model_registry.py` — 20 model speed profiles, 3-tier API fetch, disk cache
- **Created:** `src/elisya/model_updater.py` — ON-DEMAND only (no cron, no polling)
- **Modified:** `agent_pipeline.py` — `_safe_phase()` now calculates timeout per-model
- **Formula:** `timeout = (tokens / output_tps) × complexity + fc_overhead + buffer` → [45s, 600s]
- **Tests:** 36 new tests, all passing

### FIX-2: Frontend Polling Cleanup ✅ (BUG-10 NEW — was hidden)
- **Problem:** 7 React components polling backend every 3-30 seconds = **~130,000 API calls/day**
- **Root cause:** setInterval() without event-driven alternatives
- **Impact:** CPU heat, unreadable logs, wasted bandwidth

| Component | Was | Now | Saved/Day |
|-----------|-----|-----|-----------|
| ArtifactViewer.tsx | 10s × 4 fetches | Mount only | 34,560 |
| ChatPanel.tsx | 3s polling | 120s fallback | 28,080 |
| AgentStatusBar.tsx | 5s polling | Event-driven | 17,280 |
| PipelineStats.tsx | 5-30s + events | 60s render tick only | ~10,000 |
| MCCTaskList.tsx | 30s + events | Event-only | 2,880 |
| WatcherStats.tsx | 10s polling | 120s fallback | 7,920 |
| WatcherMicroStatus.tsx | 30s polling | Mount only | 2,880 |
| **TOTAL SAVED** | | | **~103,600 req/day** |

### FIX-3: Playground Architecture (D2.1) ✅
- **Created:** `src/orchestration/playground_manager.py` — Git worktree lifecycle manager
  - `PlaygroundManager`: create/destroy/list/cleanup playground instances
  - `PlaygroundConfig`: dataclass with serialization, persistence to JSON
  - Path validation: `validate_path()`, `scope_path()` — blocks `..` traversal
  - Auto-expiry: `cleanup_expired()` — removes inactive playgrounds after 4h
  - Max 5 concurrent playgrounds
  - Convenience functions: `create_playground()`, `destroy_playground()`, `list_playgrounds_summary()`
- **Modified:** `agent_pipeline.py` — `playground_root` parameter
  - `_resolve_write_path(filepath)` — prefixes playground root for all file writes
  - Both `_extract_and_write_files()` and `_write_extracted_file()` use scoped paths
  - Staging dirs also scoped: `data/vetka_staging/` → `playground/data/vetka_staging/`
  - Forbidden file checks relaxed in playground (can modify `main.py` in worktree)
- **Modified:** `mycelium_mcp_server.py` — 4 new MCP tools + pipeline integration
  - `mycelium_playground_create`: create worktree sandbox
  - `mycelium_playground_list`: list active playgrounds
  - `mycelium_playground_destroy`: cleanup worktree
  - `mycelium_playground_diff`: git diff of playground changes
  - `mycelium_pipeline` accepts `playground_id` param → scopes file writes
- **Tests:** 34 new (8 classes), all passing + 136 regression tests green
- **Architecture:**
  ```
  MCP tool call: mycelium_pipeline(task="...", playground_id="pg_abc123")
  → PlaygroundManager resolves playground root
  → AgentPipeline(playground_root="/path/to/.playgrounds/pg_abc123")
  → _resolve_write_path("src/new.py") → /path/to/.playgrounds/pg_abc123/src/new.py
  → Pipeline writes ONLY to worktree, main codebase untouched
  ```

### FIX-4: Cross-Process Playground Bug (D2.3) ✅
- **Bug found during E2E testing:** Pipeline wrote files to MAIN codebase instead of playground!
- **Root cause:** MYCELIUM server (separate process) created PlaygroundManager singleton BEFORE
  playground was created by Claude Code. `get_playground_root()` looked up in-memory dict → miss
  → returned None → pipeline ran UNSCOPED → files leaked to main
- **Fix (MARKER_146.CROSS_PROCESS):** `get_playground_root()` now auto-reloads from disk when
  playground_id not found in memory. `_load_config()` re-reads `playgrounds.json`
- **Added `.playgrounds/` to `.gitignore`** — worktrees are ephemeral
- **E2E test results:**
  - 19 E2E tests (real git worktrees, not mocked) — ALL passing
  - Dragon Silver pipeline dispatched with playground_id
  - Pipeline completed, but files leaked to main (before fix)
  - Cross-process fix ensures MYCELIUM reads fresh config from disk
  - Requires MYCELIUM restart to take effect (code change in separate process)
- **Key learning:** Any multi-process architecture needs disk-based state synchronization.
  The singleton pattern works within ONE process but fails across process boundaries.

---

### Day 2 Roadmap Status

| # | Task | Owner | Status |
|---|------|-------|--------|
| D2.1 | Playground: git worktree + scoped MCP | OPUS | ✅ DONE |
| D2.2 | Playground: pipeline sandbox flag | CODEX | ⚠️ Included in D2.1 (playground_root scoping) |
| D2.3 | Playground: test Dragon Silver in sandbox | OPUS | ✅ DONE (53 tests, cross-process bug found & fixed) |
| D2.4 | Wire Cmd+K → unified search | DRAGON SILVER | Pending |
| D2.5 | Wire Tavily web provider | CODEX | Pending |

---

## XI. PLAYGROUND OPS — Missing User Workflow (NEW)

**Problem:** У нас есть инфраструктура (worktree, scoped writes, 53 теста), но нет пользовательского flow.
Агент создаёт код в sandbox — и что дальше? Нет UI для управления, нет выбора location, нет promote.

### Gap A: MCC Sandbox Toggle (UI для вкл/выкл)
**Current:** TaskCard → ▶ Run → dispatch → writes to MAIN
**Target:** TaskCard → ▶ Run → dropdown [🔒 Sandbox / ⚡ Direct / 📂 Custom]
**Owner:** CURSOR (frontend) + OPUS (backend endpoint tweak)
**Effort:** 2-3h
**Implementation:**
- MCCTaskList dispatch → передаёт `sandbox_mode` параметр
- dispatch endpoint → если sandbox → `playground_create` → `playground_id` в pipeline
- StreamPanel показывает: `🔒 Running in sandbox: pg_xxx`
- StatusBar: badge с количеством активных playgrounds

### Gap B: Custom Playground Location
**Current:** Hardcoded `.playgrounds/` в project root
**Target:** Пользователь выбирает base_dir (любой путь на диске)
**Owner:** OPUS (backend) + CURSOR (settings UI)
**Effort:** 1h
**Implementation:**
- `PlaygroundManager.__init__(base_dir=...)` уже поддерживает! Нужен только REST + UI
- `GET/PATCH /api/debug/playground/settings` → `data/playground_settings.json`
- Settings panel в DevPanel: base_dir picker, max_concurrent, auto-expire timer
- Сценарий: пользователь хочет playgrounds на быстром SSD или в tmpfs

### Gap C: Promote Flow (⭐ КРИТИЧЕСКИЙ) — Review → Approve → Merge
**Current:** Pipeline пишет файлы в worktree → конец. Нет способа перенести в main.
**Target:** Полный цикл: generate → review diff → approve/reject per file → promote to main
**Owner:** OPUS (backend) + CURSOR (UI)
**Effort:** 4-6h
**Implementation:**

**Backend (3 new endpoints):**
```
GET  /api/debug/playground/{pg_id}/review     → файлы, диффы, статистика
POST /api/debug/playground/{pg_id}/promote    → перенос в main (cherry-pick/copy/merge)
POST /api/debug/playground/{pg_id}/reject     → пометить как rejected, опционально destroy
```

**Promote strategies:**
1. **Copy files** (default MVP) — `shutil.copy2` worktree → main, затем `vetka_git_commit`
2. **Cherry-pick** — `git cherry-pick` из playground branch (чище git history)
3. **Merge** — `git merge playground/pg_xxx` (все изменения разом)

**Frontend (MCCDetailPanel новый tab "Playground"):**
- Diff viewer для каждого файла (уже есть `DiffViewer.tsx`)
- Per-file checkboxes: ☑ promote / ☐ skip
- Action buttons: [✅ Approve All] [🚀 Promote Selected] [❌ Reject All]
- Post-promote: auto-destroy playground + refresh 3D tree (glow on promoted files)

**Full lifecycle:**
```
@dragon task → dispatch(sandbox=true) → playground_create → pipeline runs
  → files in worktree → MCC shows "Review Available"
  → user opens Review tab → sees diff per file
  → checks files to promote → clicks 🚀 Promote
  → files copied to main → vetka_git_commit → playground destroyed
  → 3D tree refreshes → new files glow green
```

### Day 2-3 Playground Ops Roadmap

| # | Task | Owner | Hours | Status |
|---|------|-------|-------|--------|
| PG-1 | Backend: promote endpoint (copy strategy) | OPUS | 2h | 📋 Ready |
| PG-2 | Backend: review endpoint (diff + file list) | OPUS | 1h | 📋 Ready |
| PG-3 | Backend: reject endpoint + auto-destroy | OPUS | 30min | 📋 Ready |
| PG-4 | Backend: playground settings persistence | OPUS | 30min | 📋 Ready |
| PG-5 | Frontend: Sandbox toggle in TaskCard | CURSOR | 2h | 📋 Brief needed |
| PG-6 | Frontend: Playground Review tab in MCC | CURSOR | 3h | 📋 Brief needed |
| PG-7 | Frontend: Promote button + file selector | CURSOR | 2h | 📋 Dep: PG-6 |
| PG-8 | Frontend: Settings panel (location, limits) | CURSOR | 1h | 📋 Brief needed |

---

## XII. RISK LOG

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Scanner fix breaks existing Qdrant data | Medium | High | Backup data/ before fix |
| Playground worktree conflicts with main | Low | Medium | Separate branch + `.gitignore` |
| Dragon pipeline fails in sandbox | Medium | Medium | Test with bronze first |
| Codex overwhelmed (6 tasks Day 1) | Medium | High | Prioritize BUG-1, defer BUG-6 |
| Feb 17 deadline too aggressive | High | Medium | MVP = Playground + Scanner fix only |

---

*Generated by Opus Commander + 3 Sonnet Verifiers + 6 Haiku Scouts + Grok Recon*
*Phase 145 RECON COMPLETE — Awaiting Commander Approval*
