# Phase 152 — MCC Analytics + Dual DAG + Task UX
## 🎖️ COMMANDER'S BATTLE PLAN v2

**Status:** ACTIVE — Wave 1 in progress
**Previous:** Phase 151 COMPLETE (UX Overhaul)
**Goal:** Transform MCC from monitoring tool → full analytics + project management platform
**Grok Research:** ✅ COMPLETE (6 deliverables)
**Estimated:** ~10 dev sessions across 3 waves

---

## Problem Statement

Phase 151 delivered per-agent stats collection (backend) and basic visualization (frontend).

**User feedback (verbatim):**
> "Статистика должна отвечать: За какое время? Кто — каждая роль и команда в целом? Сколько токенов? Сколько кругов перепроверки/эффективность. Каждая задача в отдельности. Полноценные графики с несколькими параметрами."

> "Два DAG: главный DAG задач/проекта, на задачу определяется DAG воркфлоу-команда. Изначально часть превью — клик во весь экран."

---

## Architecture Decisions (updated with Grok findings)

### Stats Storage
**Decision:** JSON-based time-series bucketing (no SQLite/Prometheus)
**Sources:** `task_board.json` + `pipeline_history.json` + `feedback/reports/*.json`
**Engine:** `pipeline_analytics.py` ✅ CREATED (813 lines) — aggregates from all 3 sources

### Dual DAG
**Decision:** Two ReactFlow instances — Task DAG (primary) + Workflow DAG (drill-down)
**Grok recommendation:** Option D (Nested Expand, ComfyUI-style) as primary, Option C (split view) для >1920px
**UX:** Click task node → inline expand OR modal transition (framer-motion)

### Fullscreen Views
**Decision:** Modal overlay (like current artifact viewer), not new route
**Grok:** Monaco for code/diff, Recharts Gantt for timeline

### Task Provenance
**Decision:** `source_chat_id` + `source_group_id` fields in TaskBoard
**Wire:** group_message_handler → auto-populate on @dragon/@doctor create

### Cost Tracking
**Grok insight:** KeyDropdown already has `balance_usd` + `exhausted` flags
**Decision:** Integrate KeyDropdown balance API into cost dashboard section

---

## 🗺️ FULL BATTLE MAP

```
═══════════════════════════════════════════════════════════════════
                    PARALLEL EXECUTION TIMELINE
═══════════════════════════════════════════════════════════════════

Session 1:
  OPUS ──── [152.1 Analytics Engine ✅] ── [152.2 REST API] ──┐
  OPUS ──── [152.3 Provenance] ──── [152.4 Timeline Events] ──┤
                                                                │
  (Codex CANNOT start dashboard until 152.2 API exists)        │
                                                                ▼
Session 2-3:
  OPUS ──── [152.9 Task DAG Backend] ─────────── [152.12 Persistence]
  CODEX ─── [152.7 Task Editor] ── [152.8 Filtering] ─────────┐
  CODEX ─── [152.5 Stats Dashboard] ──── [152.6 Drill-Down] ──┤
                                                                │
  (Codex 152.7+152.8 can start PARALLEL to 152.5 — independent)│
  (Opus 152.9 can start PARALLEL to Codex Wave 2)              │
                                                                ▼
Session 4:
  CODEX ─── [152.10 Task DAG Frontend] ── [152.11 Dual DAG Nav]
  OPUS ──── [Review + Integration + Tests]

═══════════════════════════════════════════════════════════════════
```

---

## Wave 1 — Backend Analytics Engine (Opus)
**Duration:** 1 session (current)
**Agent:** Opus (me) — Python backend ONLY
**Files:** `src/orchestration/`, `src/api/routes/`

### 152.1 — Pipeline Analytics Aggregator ✅ DONE
**Agent:** Opus | **Complexity:** Moderate | **Status:** ✅ CREATED
- **File:** `src/orchestration/pipeline_analytics.py` (813 lines)
- Reads from 3 data sources: task_board.json + pipeline_history.json + feedback/reports
- `compute_time_series()` — hourly/daily/weekly buckets, Recharts-compatible
- `compute_agent_efficiency()` — per-role: calls, tokens, duration, success_rate, efficiency_score
- `detect_weak_links()` — auto-detect bottleneck roles (success<60%, retries>2, duration>2x median)
- `get_task_analytics()` — per-task drill-down (token distribution, timeline, cost)
- `compute_summary()` — full dashboard data (cards + charts + agents + weak links)
- `compute_team_comparison()` — preset vs preset (Bronze/Silver/Gold)
- `compute_cost_report()` — cost by preset, by role, over time
- `compute_trends()` — trend direction (up/down/stable) with change %
- MODEL_COST_PER_1K — pricing table for all Dragon/Titan models
- PRESET_COST_TIER — multiplier per team tier

### 152.2 — Analytics REST API
**Agent:** Opus | **Complexity:** Simple | **Depends on:** 152.1
- **File:** `src/api/routes/analytics_routes.py` (NEW)
- **Register in:** `src/api/routes/__init__.py` (add import + router)
- Endpoints:
  - `GET /api/analytics/summary` — dashboard top row + time-series + agents
  - `GET /api/analytics/task/{task_id}` — per-task drill-down
  - `GET /api/analytics/agents` — per-agent efficiency + weak links
  - `GET /api/analytics/trends?period=day&metric=success_rate` — trend data
  - `GET /api/analytics/cost` — cost breakdown
  - `GET /api/analytics/teams` — preset comparison

### 152.3 — Task Provenance Backend
**Agent:** Opus | **Complexity:** Simple | **Independent**
- **Modify:** `src/orchestration/task_board.py` — add `source_chat_id`, `source_group_id` to ADDABLE_FIELDS
- **Modify:** `src/api/handlers/group_message_handler.py` — pass chat_id when creating tasks via @dragon/@doctor
- **New endpoint:** `GET /api/analytics/tasks-by-chat/{chat_id}` — reverse lookup
- Source enrichment: "dragon_pipeline" | "heartbeat" | "manual" | "opus" | "codex" | "cursor"

### 152.4 — Pipeline Timeline Events
**Agent:** Opus | **Complexity:** Simple | **Depends on:** 152.1
- **Modify:** `src/orchestration/agent_pipeline.py` — extend `_track_agent_stat()`
- New field: `timeline_events: [{role, action, timestamp, duration_ms, tokens}]`
- Actions: `started`, `completed`, `failed`, `retried`, `escalated`
- Records absolute timestamps (not just durations) for Gantt chart
- ⚠️ Minimal changes to agent_pipeline.py — only add event collection, don't refactor

---

## Wave 2 — Frontend Dashboard + Task UX (Codex + Opus parallel)
**Duration:** 2 sessions
**Codex:** Frontend TypeScript ONLY
**Opus:** Backend for Wave 3 + review

### ▶ PARALLEL TRACK A: Codex — Task UX (independent, no backend deps)

#### 152.7 — Task Editor
**Agent:** Codex | **Complexity:** Moderate | **Independent — START FIRST**
- **File:** `client/src/components/panels/TaskEditor.tsx` (NEW)
- Click edit icon on TaskCard → inline edit mode
- Editable fields: title, description, priority, tags
- Source badge: 🐉 Dragon | 🤖 Opus | 📝 Codex | ⏱ Heartbeat | 👤 Manual
- Chat link: "From: Chat #{chat_id}" → clickable (opens VETKA chat if available)
- Save via existing `PATCH /api/debug/task-board/{id}` REST API
- Nolan style: dark, #111/#222/#e0e0e0, minimal accents

#### 152.8 — Task Filtering & Search
**Agent:** Codex | **Complexity:** Moderate | **Independent — PARALLEL with 152.7**
- **File:** `client/src/components/panels/TaskFilterBar.tsx` (NEW)
- **Modify:** `client/src/components/panels/DevPanel.tsx` — add filter bar above task list
- Filters: source (dropdown), status (multi-select), preset (dropdown), date range
- Search: keyword in title/description (client-side filter)
- Sort: by priority, date, duration, success rate
- "Show completed" toggle (currently all mixed together)
- Persist filter state in `useDevPanelStore`

### ▶ PARALLEL TRACK B: Codex — Stats Dashboard (needs 152.2 API)

#### 152.5 — Stats Dashboard Rewrite
**Agent:** Codex | **Complexity:** Complex | **Depends on:** 152.2 API
- **File:** `client/src/components/panels/StatsDashboard.tsx` (NEW — replaces PipelineStats expanded)
- **Top row:** Summary cards (runs, success%, adjusted%, cost $, avg duration, retries)
- **Middle:** Recharts `<LineChart>` — success rate trend over time
- **Middle:** Recharts `<AreaChart>` — token consumption (in/out stacked)
- **Bottom-left:** Per-agent cards enhanced: retry badge, avg duration, token budget bar
- **Bottom-right:** Team comparison — grouped `<BarChart>` (presets × success%)
- **Weak links:** Red glow on weak agents, ranked warning list
- Fetches: `GET /api/analytics/summary`
- Keep PipelineStats compact mode as-is (just summary cards)

#### 152.6 — Per-Task Drill-Down Modal
**Agent:** Codex | **Complexity:** Complex | **Depends on:** 152.2 API + 152.4 events
- **File:** `client/src/components/panels/TaskDrillDown.tsx` (NEW)
- Click task in TaskList → fullscreen modal overlay
- **Tab: Timeline** — Gantt chart (Recharts horizontal BarChart as Gantt)
- **Tab: Code** — existing code results viewer, made fullscreen
- **Tab: Diff** — existing DiffViewer, made fullscreen
- **Tab: Stats** — pie chart (token distribution by agent), retry count per role
- Fetches: `GET /api/analytics/task/{task_id}`
- Close: Esc / X button / click outside

### ▶ PARALLEL TRACK C: Opus — Wave 3 Backend (runs during Codex Wave 2)

#### 152.9 — Task DAG Backend
**Agent:** Opus | **Complexity:** Moderate | **Depends on:** 152.3 (provenance)
- **File:** `src/api/routes/analytics_routes.py` (extend with Task DAG endpoint)
- `GET /api/analytics/dag/tasks` — returns task nodes + dependency edges
- Nodes from TaskBoard: `{id, title, status, preset, source, mini_stats}`
- Edges from TaskBoard `dependencies` field
- Auto-layout hints: parallel tasks = same layer (Sugiyama/hierarchical)
- Status coloring data: pending=gray, running=pulse, done=green, failed=red, hold=yellow
- Per-node mini-stats: duration, success%, subtask count

---

## Wave 3 — Dual DAG Architecture (Codex)
**Duration:** 1-2 sessions
**Agent:** Codex (frontend) — Opus provides backend + reviews
**Prerequisite:** 152.9 Task DAG Backend must be done

#### 152.10 — Task DAG Frontend
**Agent:** Codex | **Complexity:** Complex | **Depends on:** 152.9
- **File:** `client/src/components/mcc/TaskDAGView.tsx` (NEW)
- Separate ReactFlow instance (NOT the existing DAGView)
- Nodes styled as task cards (different from workflow agent circles)
- Status coloring: gray/pulse/green/red/yellow
- Mini-stats badge on each node (duration, success%)
- Click task node → fires event for drill-down

#### 152.11 — Dual DAG Navigation
**Agent:** Codex | **Complexity:** Complex | **Depends on:** 152.10
- **Modify:** `client/src/components/mcc/MyceliumCommandCenter.tsx` — add DAG toggle
- Toggle: Task DAG / Workflow DAG / Split view
- Click task node → transitions to Workflow DAG for that task_id
- Breadcrumb: "Tasks > {task_title} > Workflow" with back button
- Split view (>1920px): Task DAG left (30%), Workflow DAG right (70%)
- Mini-map in corner
- Transition: framer-motion or CSS transition (NOT full page reload)

#### 152.12 — Mycelium Persistence
**Agent:** Opus | **Complexity:** Moderate | **Independent**
- `_active_pipelines` is in-memory only (dies on restart)
- Add JSON persistence for pipeline state: `data/mycelium_state.json`
- On startup: restore pending pipelines from state file
- `/health` enhanced: total_pipelines_ever, last_pipeline_at, uptime
- ⚠️ NOT SQLite — JSON is sufficient for current scale

---

## 🎯 AGENT ASSIGNMENT TABLE

| # | Task | Agent | Complexity | Dependencies | Parallel? |
|---|------|-------|------------|--------------|-----------|
| **152.1** | Analytics Aggregator | **Opus** ✅ DONE | Moderate | none | — |
| **152.2** | Analytics REST API | **Opus** | Simple | 152.1 | Sequential |
| **152.3** | Task Provenance | **Opus** | Simple | none | ‖ with 152.2 |
| **152.4** | Timeline Events | **Opus** | Simple | none | ‖ with 152.2+152.3 |
| **152.7** | Task Editor | **Codex** | Moderate | none | ‖ START ASAP |
| **152.8** | Task Filtering | **Codex** | Moderate | none | ‖ with 152.7 |
| **152.5** | Stats Dashboard | **Codex** | Complex | 152.2 | After API ready |
| **152.6** | Task Drill-Down | **Codex** | Complex | 152.2 + 152.4 | After 152.5 |
| **152.9** | Task DAG Backend | **Opus** | Moderate | 152.3 | ‖ with Codex W2 |
| **152.10** | Task DAG Frontend | **Codex** | Complex | 152.9 | After 152.9 |
| **152.11** | Dual DAG Nav | **Codex** | Complex | 152.10 | Sequential |
| **152.12** | Mycelium Persist | **Opus** | Moderate | none | ‖ anytime |

---

## 📋 EXECUTION ORDER (Optimized for parallelism)

### Session 1: Opus Backend Blitz (NOW)
```
Opus: 152.1 ✅ → 152.2 → 152.3 → 152.4 (all backend, sequential)
Codex: 152.7 + 152.8 (Task UX — NO backend deps, can start NOW)
```
**Why:** Codex starts immediately on Task Editor + Filtering (zero backend deps).
Opus completes all backend APIs. By end of session, ALL APIs exist for Codex dashboards.

### Session 2: Codex Dashboard + Opus DAG Backend
```
Opus: 152.9 Task DAG Backend + 152.12 Mycelium Persistence
Codex: 152.5 Stats Dashboard → 152.6 Drill-Down (uses new APIs)
```
**Why:** Opus builds Task DAG backend WHILE Codex builds dashboard.
Both work in parallel — no blocking.

### Session 3: Codex Dual DAG
```
Opus: Review + Tests + Integration fixes
Codex: 152.10 Task DAG Frontend → 152.11 Dual DAG Navigation
```
**Why:** All backend ready. Codex focuses purely on ReactFlow + navigation.

---

## 🔒 CODEX BRIEF RULES (CRITICAL — learned from Phase 151 incidents)

### DO:
1. **Use MARKER_152.XX convention** in ALL code comments
2. **Save as .tsx** for components with JSX (NEVER .ts + JSX)
3. **Read existing code BEFORE modifying** — understand imports, patterns, store structure
4. **Test with `npx tsc --noEmit`** on changed files before committing
5. **Create NEW files** for new components (TaskEditor.tsx, TaskFilterBar.tsx, StatsDashboard.tsx, etc.)
6. **Use existing stores** — `useDevPanelStore`, `useMCCStore` for state
7. **Follow Nolan style** — #111/#222/#e0e0e0, minimal color, Itten accents only

### DON'T:
1. ❌ **Do NOT touch** `src/orchestration/`, `src/api/routes/`, `src/api/handlers/`, `main.py`
2. ❌ **Do NOT create .ts duplicates** alongside .tsx files (caused esbuild failure in 151)
3. ❌ **Do NOT overwrite** `src/api/handlers/__init__.py` (caused Socket.IO total failure in 151)
4. ❌ **Do NOT modify shared files** without asking: useMCCStore, dagLayout, types/dag
5. ❌ **Do NOT delete existing code** from files (ADD functions, don't replace whole files)
6. ❌ **Do NOT install new npm packages** without approval
7. ❌ **Do NOT touch Recharts imports** if they already work — only ADD new chart components

---

## 🔍 GROK RESEARCH APPLIED

| Grok Recommendation | Applied To |
|---------------------|-----------|
| Recharts (existing) for all charts | 152.5 Stats Dashboard |
| Option D: Nested Expand (ComfyUI-style) | 152.11 Dual DAG (primary mode) |
| Option C: Split view for >1920px | 152.11 Dual DAG (secondary mode) |
| react-beautiful-dnd for drag-reorder | 152.7 Task Editor (priority drag) |
| Monaco for diff/code view | 152.6 Drill-Down (existing CodeViewer) |
| framer-motion for transitions | 152.11 Dual DAG Nav transitions |
| KeyDropdown balance_usd for cost | 152.5 Stats Dashboard cost section |
| Arborescence DAG/Polytree | 152.9 Task DAG Backend layout |
| LOD/Octree for scale | Deferred to Phase 153 (not needed at current scale) |
| Qdrant pipeline_history collection | Deferred to Phase 153 (JSON sufficient now) |
| ELISION for pipeline agents | Deferred to Phase 153 |

---

## Dependency Map (Visual)

```
Session 1 (NOW):
  OPUS:  [152.1 ✅] ──→ [152.2] ──→ [152.3] ──→ [152.4]
  CODEX: [152.7] ──────────────── [152.8] (PARALLEL — no deps!)

Session 2:
  OPUS:  [152.9] ──────────────── [152.12]
  CODEX: [152.5 ←needs 152.2] ── [152.6 ←needs 152.2+152.4]

Session 3:
  OPUS:  [Review + Tests + Fixes]
  CODEX: [152.10 ←needs 152.9] ── [152.11 ←needs 152.10]
```

---

## Deferred to Phase 153+
- Full Prometheus/Grafana stack (Grok suggestion — too heavy now)
- Kubernetes/Docker deployment of Mycelium
- Multi-worker pipeline scaling
- API key auth for Mycelium endpoints
- BMAD loop auto-improvement (needs stats history first — 152 builds foundation)
- File attachment to tasks (chat → task file binding, `target_files` field)
- ELISION compression for pipeline agents
- Session init UI for user (project digest in MCC panel)
- Chat search by ID (reverse lookup from task → chat) — partially done via 152.3
- Qdrant LTM (vectorize pipeline_history for "what worked" memory)
- LOD/Octree for large DAG scale (100s+ tasks)
- Git deploy node in BMAD template
- BMAD loop counter badge on feedback edge

---

## Success Criteria
1. ✅ Stats tab shows **time-series Recharts charts** (not just CSS bars)
2. ✅ Click any task → **fullscreen drill-down** with timeline + code + diff + stats
3. ✅ Tasks show **source badge** and are **filterable** by source/status/preset
4. ✅ Tasks are **editable** inline (title, description, priority, tags)
5. ✅ **Task DAG** visible as primary MCC view (roadmap of all tasks)
6. ✅ Click task → **drill into workflow DAG** (team execution per task)
7. ✅ Pipeline results **survive Mycelium restart**
8. ✅ **Cost estimation** visible in dashboard (tokens → $)
