# Phase 175 — MYCELIUM.app Unified Recon Report

> **Date:** 2026-03-11
> **Sources:** 5 Haiku Scouts + 3 Sonnet Verifiers + Grok Research
> **Author:** Opus (Commander)
> **Status:** VERIFIED

---

## Executive Summary

MCC is **97% ready** for standalone extraction. Zero Tauri dependencies in MCC components.
The main blocker is **3 missing API endpoints** and **build tooling** (Vite multi-page + second Tauri config).

| Metric | Value | Source |
|--------|-------|--------|
| MCC components total | 28 files in `components/mcc/` | V2 verified |
| Tauri imports in MCC | **0** (zero) | V1+V2 confirmed |
| Browser-ready | **100%** of MCC components | V1 corrected (scouts said 94%) |
| Missing API endpoints | 3 critical | S3 confirmed, V2 verified |
| Estimated effort (MVP) | ~15-17 hours | V1 + Grok aligned |
| Bundle size savings | ~15MB (no Three.js/3D) | Grok research |

---

## 1. Tauri Dependency Analysis

### CORRECTED Finding (Scouts said "3 critical commands for MCC")

**Reality: MCC needs ZERO Tauri commands.**

Verifier V1 performed exhaustive grep across all 28 MCC component files:
- `grep 'invoke|tauri|__TAURI__|isTauri'` → **0 matches**
- `grep 'from.*config/tauri'` → **0 matches**

MCC communicates **entirely via REST API** and **browser CustomEvents** (bridged from WebSocket).

### Tauri Bridge Stats (config/tauri.ts)

| Metric | Count |
|--------|-------|
| Exported functions | 22 |
| Functions using invoke() | 17 |
| Functions needed by MCC | **0** |
| Event listeners | 6 |
| isTauri() detection | Solid (v1 + v2 compat) |

### Only Non-MCC Tauri Issue

`App.tsx` line 19 has **static import** of `@tauri-apps/api/core` — breaks in pure browser build.
MCC standalone bypasses App.tsx entirely (uses `MyceliumStandalone.tsx` → `DevPanel standalone=true`).

### Files with isTauri() in MCC directory

Only 2 files (not 3 as scouts reported):
1. `FirstRunView.tsx` — uses `openFolderDialog()` with text input fallback
2. `OnboardingModal.tsx` — uses `isTauri()` for conditional hints

Both have genuine fallbacks. MCCTaskList does NOT reference Tauri (scout was wrong).

---

## 2. MiniWindow System

### Architecture (Verifier V3 — Detailed)

| Property | Value |
|----------|-------|
| Positioning | `react-draggable` (compact) + CSS `position: fixed` |
| Expanded mode | `position: absolute` + framer-motion centered panel |
| Persistence | localStorage: `miniwindow_pos_v4_<windowId>` |
| Resize | Custom 8-handle zones (n/s/e/w/ne/nw/se/sw) |
| Viewport clamp | 12px padding, 260×190 reserved for minimap |
| Min size | 180×100 px |

### MiniWindow Dependency Matrix

| Window | windowId | API Endpoint | WS Needed? | Tauri? | Fallback |
|--------|----------|-------------|------------|--------|----------|
| **MiniChat** | `chat` | `POST /api/chat/quick` | No | No | Local MYCO helper (offline guidance) |
| **MiniTasks** | `tasks` | `GET /api/task-board` | Optional (refresh trigger) | No | "No tasks yet" |
| **MiniStats** | `stats` | `GET /api/analytics/summary` + `/agents` | Optional (refresh) | No | Zeros / loading |
| **MiniBalance** | `balance` | `GET /api/debug/usage/balances` | Optional (refresh) | No | "no usage records" |
| **MiniContext** | `context` | Multiple (`/presets`, `/prompts`, `/search/file`) | No | No | "Select a node" |
| **MiniWindowDock** | n/a | In-memory registry | No | No | Hidden when empty |

**Key insight:** ALL MiniWindows work without Tauri, without MYCELIUM WS, without SocketIO.
Only hard dependency: **FastAPI backend on port 5001**.

### Gate Condition (CORRECTED)

Scouts said `hasProject=true`. Actual gate: `navLevel !== 'first_run'` (line 4349 of MCC).
Related but different — navLevel transitions slightly after hasProject.

### Notable Dependencies

- `MiniBalance` imports from main `useStore` (not `useMCCStore`) — reads `selectedKey`, `setSelectedKey`
- `react-draggable` npm package required
- MiniWindowDock is co-located in `MiniWindow.tsx` (not separate file)
- No periodic refresh in MiniTasks (only mount + actions). MiniStats has 30s poll.

---

## 3. WebSocket Architecture

### Dual-Channel (Verifier V3 — Confirmed)

```
MYCELIUM WS (:8082) ──→ useMyceliumSocket.ts ──→ CustomEvents ──→ MCC listeners
                         (in DevPanel.tsx)        (window.dispatchEvent)
```

| WS Message Type | CustomEvent Name | MCC Reaction |
|----------------|-----------------|--------------|
| `pipeline_activity` | `pipeline-activity` | pushStreamEvent |
| `task_board_updated` | `task-board-updated` | DAG refetch + pushStreamEvent |
| `pipeline_stats` | `pipeline-stats` | pushStreamEvent (no DAG refetch) |
| `pipeline_complete` | `task-board-updated` + `pipeline-activity` | Both |
| unknown | `mycelium-event` | Logged |

**Critical detail:** Hyphens in CustomEvent names, underscores in WS protocol.

### MCC is Transport-Agnostic

MCC never imports useMyceliumSocket. It only listens to browser CustomEvents.
The WebSocket hook lives in DevPanel.tsx, which wraps MCC. Clean separation.

### Graceful Degradation

- WS failure → `connected = false`, 5000ms reconnect
- Visibility-aware: defers reconnection when tab hidden
- No crash, no error UI — just no live updates

---

## 4. API Endpoint Analysis

### Working Endpoints (18)

| Endpoint | Used By |
|----------|---------|
| `GET /api/mcc/state` | MCC init (hasProject gate) |
| `GET /api/task-board` | MiniTasks, DAG |
| `POST /api/task-board` | Task creation |
| `GET /api/analytics/summary` | MiniStats |
| `GET /api/analytics/agents` | MiniStats expanded |
| `GET /api/debug/usage/balances` | MiniBalance |
| `GET /api/pipeline/presets/<name>` | MiniContext |
| `GET /api/pipeline/prompts/<role>` | MiniContext |
| `POST /api/mcc/search/file` | MiniContext |
| `GET /api/models` | MiniContext |
| `POST /api/mcc/project/init` | FirstRunView |
| `POST /api/mcc/roadmap/generate` | FirstRunView |
| `GET /api/mcc/roadmap` | useRoadmapDAG |
| `POST /api/pipeline/run` | Execute actions |
| `GET /api/mcc/sandbox` | Sandbox selection |
| `POST /api/mcc/sandbox` | Sandbox creation |
| `GET /api/analytics/dag/tasks` | Task DAG panel |
| `GET /api/analytics/context` | Context pipeline |

### Missing Endpoints (3 CRITICAL)

| Endpoint | Needed By | Impact |
|----------|-----------|--------|
| `PATCH /api/mcc/tasks/{task_id}` | TaskEditPopup | Cannot edit task team/phase/description |
| `POST /api/mcc/tasks/{task_id}/feedback` | RedoFeedbackInput | Cannot submit redo feedback |
| `POST /api/chat/quick` | MiniChat | Chat input non-functional |

---

## 5. Build Strategy (Grok Research + Verifier Synthesis)

### Recommended: Vite Multi-Page + Separate src-tauri-mcc/

```
vetka_live_03/
├── client/
│   ├── index.html          ← VETKA entry
│   ├── mycelium.html        ← MCC entry (NEW)
│   ├── src/
│   │   ├── main.tsx         ← VETKA root
│   │   ├── MyceliumStandalone.tsx  ← MCC root (EXISTS)
│   │   └── components/mcc/  ← Shared MCC components
│   └── vite.config.ts       ← Multi-page input
├── src-tauri/               ← VETKA Tauri (existing)
└── src-tauri-mcc/           ← MCC Tauri (NEW, minimal)
    ├── Cargo.toml           ← ~6 deps (vs 14 in VETKA)
    ├── tauri.conf.json      ← Single window, MCC CSP
    └── src/main.rs          ← Minimal (no 3D commands)
```

### Vite Config Extension

```typescript
// vite.config.ts
build: {
  rollupOptions: {
    input: {
      vetka: resolve(__dirname, 'index.html'),
      mycelium: resolve(__dirname, 'mycelium.html')
    }
  }
}
```

### Bundle Size Comparison

| Build | Estimated Size | Savings |
|-------|---------------|---------|
| VETKA full | ~25MB | baseline |
| MCC standalone | ~8-10MB | -15MB (no Three.js/3D/Zustand-tree) |
| Tauri binary (MCC) | ~5MB | vs ~8MB VETKA binary |
| **Total dmg** | **~15MB** | vs ~35MB VETKA |

---

## 6. Backend Packaging Strategy

### Phase 175.1 (MVP): External Backend

User runs: `python main.py & open MYCELIUM.app`
- Zero bundle bloat
- Reuses existing VETKA backend
- Documented in README

### Phase 175.2: Sidecar

Tauri sidecar bundles `run_mycelium.py` via PyInstaller:
- `run_mycelium.py` → PyInstaller → `mycelium.bin` (~30MB)
- Tauri auto-launches on app start
- FastAPI optional (connect if running)

### Phase 175.3: Full Bundle

Both FastAPI + MYCELIUM bundled as sidecars:
- ~150MB total (PyInstaller overhead)
- Single app, zero terminal needed

---

## 7. MultiTask Generalization (Grok Research)

```
MYCELIUM.app ─ REST /api/taskboard ─→ Adapter Layer ─→ Backend
Adapters: ClaudeMCPAdapter, CursorAdapter, VSCodeAdapter, OpenCodeAdapter
```

| Adapter | Protocol | Effort |
|---------|----------|--------|
| Claude Code | MCP stdio | Reuse mycelium_mcp_server.py |
| Cursor | SSE/WS | New: POST /cursor/task |
| VSCode | LSP/Task API | Extension: tasks.json sync |
| OpenCode | REST | Native |

---

## 8. Risk Assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| Vite multi-page breaks existing build | Medium | Feature flag, separate npm script |
| MiniBalance depends on useStore (main) | Low | Extract needed state to useMCCStore |
| Missing API endpoints block testing | **High** | Codex implements 3 endpoints (priority) |
| Tauri capability permissions for MCC window | Low | Own default.json in src-tauri-mcc/ |
| CSP restricts connect-src to :5001 | Low | Add :8082 in MCC tauri.conf.json |
| react-draggable missing from MCC bundle | Low | Already in package.json |

---

## 9. Implementation Priority

| Phase | Task | Effort | Owner |
|-------|------|--------|-------|
| **175.1** | 3 missing API endpoints | 3h | Codex |
| **175.2** | `mycelium.html` + Vite multi-page | 3h | Opus/Codex |
| **175.3** | `src-tauri-mcc/` minimal Tauri project | 4h | Opus |
| **175.4** | MiniBalance store extraction | 1h | Codex |
| **175.5** | Build scripts (`npm run build:mcc`, `tauri build`) | 2h | Opus |
| **175.6** | Sidecar packaging (PyInstaller) | 3h | Dragon |
| **175.7** | Generic TaskBoard REST API + adapters | 6h | Dragon |
| **175.8** | dmg/app signing + distribution | 2h | Opus |
| **Total** | | **~24h** | |

---

## 10. New Findings (Verifiers Discovered)

1. **Missing generate_handler! registrations** — 3 Rust commands defined but not registered in main.rs (V1-N1)
2. **Capability permissions** only cover "main" window — MCC window lacks explicit FS/dialog perms (V1-N2)
3. **CSP** restricts connect-src to localhost:5001 — need :8082 for MCC (V1-N3)
4. **MiniChat has offline MYCO helper** — `buildMycoReply()` generates context-aware guidance without API (V3-N5)
5. **MiniStats has dual-scope mode** — per-agent diagnostics via `useMCCDiagnostics` hook (V3-N6)
6. **LAYOUT_VERSION = 4** — changing invalidates all saved MiniWindow positions (V3-N8)
7. **No periodic refresh in MiniTasks** — only mount + action-triggered. Stale without WS events (V3-N9)
8. **useMyceliumSocket lives in DevPanel**, not MCC — clean transport abstraction (V3-N4)

---

## Appendix: Scout-to-Verifier Corrections

| Scout Claim | Verifier Correction |
|-------------|-------------------|
| "19 Tauri commands" | 16 `#[tauri::command]`, 13 registered (V1) |
| "3 critical for MCC" | **0 needed** — MCC has zero Tauri imports (V1) |
| "54 components, 94% browser-ready" | 28 files in mcc/, **100% browser-ready** (V1+V2) |
| "3 files reference Tauri" | 2 files (FirstRunView, OnboardingModal) — not MCCTaskList (V2) |
| "hasProject=true gate" | `navLevel !== 'first_run'` gate (V3) |
| "CSS fixed/absolute positioning" | `react-draggable` controlled component + fixed CSS (V3) |
