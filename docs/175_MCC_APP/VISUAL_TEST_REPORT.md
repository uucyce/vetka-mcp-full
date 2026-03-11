# Visual Test Report — MCC Standalone (Phase 175)

> **Tester:** Opus (Claude Code — Commander)
> **Date:** 2026-03-11
> **Surface:** Browser MCC via vetka-client (`localhost:3001/mycelium`)
> **Backend:** FastAPI on port 5001
> **Mycelium WS:** port 8082
> **Branch:** `codex/mcc-wave-d-runtime-closeout`

---

## Executive Summary

**RESULT: ✅ PASS (with known issues)**

MCC loads successfully at `/mycelium` route with ALL 5 MiniWindows rendering.
Zero console errors. MYCELIUM WS connected. DAG drill-down navigation works.
API endpoints return 404s for unimplemented routes (expected — Codex A scope).

---

## Test Matrix

### 1. MCC Load (Surface: Browser at /mycelium)

| Test | Result | Notes |
|------|--------|-------|
| MCC loads without crash | ✅ PASS | Title: "MYCELIUM", React root renders |
| Document title correct | ✅ PASS | `document.title === "MYCELIUM"` |
| Browser Agent Bridge init | ✅ PASS | `vetkaAPI.help()` available |
| MYCELIUM WS connects | ✅ PASS | `[MYCELIUM WS] Connected to ws://localhost:8082` |
| Server info received | ✅ PASS | `[MYCELIUM WS] Server info: [object Object]` |
| No console errors | ✅ PASS | Zero error-level messages |
| No Tauri invoke errors | ✅ PASS | Zero Tauri references (confirmed zero deps) |

### 2. MiniWindows Rendering (All 5)

| MiniWindow | Compact | Expanded | Data | Notes |
|------------|---------|----------|------|-------|
| 📋 Tasks | ✅ | ✅ | 9 tasks, 1 active | "start" button, HEARTBEAT off/1d |
| ‖ Stats | ✅ | ✅ | core_library, dragon_silver | WORKFLOW BANKS: Core 10, Saved 1 |
| 💳 Balance | ✅ | — | keys: 39, cost: $4.07 | polza ★, gemini providers |
| 👁 Context | ✅ | — | Task details displayed | search input, SEARCH button |
| 💬 Chat | ✅ | — | TASK ARCHITECT message | "Ask..." input, from_preset badge |

### 3. MiniWindow Interactions

| Test | Result | Notes |
|------|--------|-------|
| Expand (↗) button present | ✅ PASS | All 5 windows have ↗ buttons |
| Stats expand shows details | ✅ PASS | CURRENT TASK + WORKFLOW BANKS rendered |
| Collapse (↙) button present | ✅ PASS | Appears in expanded view |
| Minimize (-) button works | ⚠️ PARTIAL | Reduces size but doesn't fully collapse to compact |
| Close (×) button present | ✅ PASS | Present in expanded header |
| Positions persist on reload | ✅ PASS | MiniWindows return to same positions |

### 4. DAG View

| Test | Result | Notes |
|------|--------|-------|
| DAG nodes render | ✅ PASS | Project directory tree as ReactFlow nodes |
| Node labels visible | ✅ PASS | "app", "tests", "docs", "src", etc. |
| Status badges visible | ✅ PASS | "PENDING", "(root)" labels |
| "double-click to enter" hint | ✅ PASS | All nodes show interaction hint |
| Double-click drill-down | ✅ PASS | Clicking "app" zooms and updates context |
| Edges render correctly | ✅ PASS | Dashed arrows between parent→child nodes |

### 5. Cross-Window Context Updates (on DAG node click)

| MiniWindow | Before Click | After Click "app" | Verdict |
|------------|-------------|-------------------|---------|
| Stats | core_library, S1.3 task | WORKFLOW tab, "choose workflow" | ✅ Context-aware |
| Context | S1.3 task details | "app" kind:Task status:pending | ✅ Context-aware |
| Chat | "TASK ARCHITECT: S1." | "TASK ARCHITECT: API" | ✅ Context-aware |
| Tasks | unchanged | unchanged | ✅ Expected |
| Balance | unchanged | unchanged | ✅ Expected |

### 6. Header

| Test | Result | Notes |
|------|--------|-------|
| Project name visible | ✅ PASS | "fake_project_b9c3cf3d" |
| Helper (MYCO) icon | ✅ PASS | Interactive, tooltip visible |
| Context hint bar | ✅ PASS | "Context focused: inspect node/task details" |
| "+ project" button | ✅ PASS | New project creation |

---

## Failed Network Requests (Expected)

These 404s are **expected** — endpoints not yet implemented (Codex A scope):

| Endpoint | Status | Owner |
|----------|--------|-------|
| `GET /api/workflow/design-graph/latest` | 404 | Codex A or existing workflow routes |
| `GET /api/workflow/design-graph/{id}` | 404 | Same — design graph viewer |
| `GET /api/mcc/tasks/{id}/workflow-binding` | 404 | Codex A — task workflow binding |

All other API calls succeed:
- `GET /api/task-board` → 200 (tasks loaded)
- `GET /api/analytics/summary` → 200 (stats populated)
- `WS ws://localhost:8082` → connected (MYCELIUM real-time)

---

## Vite Dev Server Issue

**Problem:** `VITE_MODE=mcc` dev server does not serve `mycelium.html` as default.
`rollupOptions.input` only affects production build, not dev server.

**Fix applied (MARKER_175.3):** Added `mccDevRedirect()` Vite plugin in `vite.config.ts`:
```typescript
function mccDevRedirect(): Plugin {
  return {
    name: 'mcc-dev-redirect',
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        if (req.url === '/' || req.url === '/index.html') {
          req.url = '/mycelium.html';
        }
        next();
      });
    }
  };
}
```

**Status:** Plugin created but port conflict (3002-3004 occupied) prevents isolated test.
**Workaround:** Use vetka-client at `localhost:3001/mycelium` — this works because `main.tsx`
has pathname-based routing that renders `MyceliumStandalone` when path matches `/mycelium`.

**Production build:** ✅ Works correctly. `VITE_MODE=mcc npm run build:mcc` produces `dist-mcc/`
with `mycelium.html` entry point (1.3MB JS, 0 Three.js refs).

---

## Known Issues

| # | Severity | Issue | Owner |
|---|----------|-------|-------|
| 1 | LOW | MiniWindow minimize from expanded doesn't fully collapse to compact | Frontend polish |
| 2 | LOW | Duplicate console logs from React StrictMode | Expected behavior |
| 3 | MEDIUM | 3 API endpoints return 404 | Codex A |
| 4 | LOW | Port conflict when running both vetka-client and mycelium-client | Dev environment |
| 5 | LOW | Header tooltip shows "Tasks focused" even when Tasks not focused | Tooltip logic |

---

## Build Verification

| Build | Status | Size | Time |
|-------|--------|------|------|
| MCC production (`build:mcc`) | ✅ PASS | 118MB total (1.38MB JS + 110MB APNG) | 2.85s |
| VETKA production (`build`) | ✅ PASS | nominal | 5.58s |
| MCC JS gzip | ✅ | 413KB | — |
| Three.js references in MCC | ✅ ZERO | — | — |

### APNG Asset Sizes (Dragon optimization target)

| Asset | Size | Priority |
|-------|------|----------|
| architect_primary | 21MB | HIGH |
| researcher_primary | 15MB | HIGH |
| scout_scout1/2/3 | 13MB each | HIGH |
| verifier_primary | 12MB | MEDIUM |
| coder_coder1/2 | 11-12MB each | MEDIUM |
| myco_speaking_loop | 44KB | ✅ Already optimized |
| **Total APNG** | **~110MB** | **Target: <20MB** |

### Test Suite Regression Check

| Suite | Tests | Result |
|-------|-------|--------|
| REFLEX Live + Registry | 27 | ✅ All pass |
| REFLEX Scorer + Feedback + Filter | 102 | ✅ All pass |
| **Total** | **129** | **✅ 0 failures** |

---

## Recommendations for Next Phases

1. **Codex A** should implement the 3 missing API endpoints (design-graph, workflow-binding)
2. **Codex B** should verify StatsDashboard renders in the Stats MiniWindow expanded view
3. **Dragon** APNG optimization — current bundle is 1.3MB which is great, but avatar assets add size
4. **Opus Phase 2** — integration test after Codex A endpoints are live:
   - TaskEditPopup → PATCH task
   - RedoFeedbackInput → POST feedback
   - MiniChat → POST chat/quick

---

## Test Environment

```
macOS (ARM64)
Node.js (via nvm)
Vite 5.4.21
React (StrictMode enabled)
Backend: Python FastAPI + SocketIO on :5001
MYCELIUM WS: :8082
Browser: Chromium (via Claude Preview)
```

---

**Signed:** Opus Commander, Phase 175 Integration Lead
**Next milestone:** Phase 2 — Endpoint Integration Test (after Codex A completes)
