# RECON: WEATHER Browser — Transform VETKA Tauri into Universal AI Service Interface

**Task:** `tb_1774980431_74494_1`
**Date:** 2026-03-31
**Phase:** 201
**Author:** Opus (Commander)

---

## 1. Executive Summary

**Verdict: Feasible with moderate-to-high effort.** The existing Tauri browser infrastructure covers ~40% of what WEATHER needs. The remaining 60% requires new window management, profile persistence, embedded terminal, and TaskBoard mirroring.

**Recommendation:** Build WEATHER as a **separate Tauri app** (not modifying the existing VETKA app), sharing React components via a monorepo package. This avoids destabilizing the existing 3D knowledge graph app.

---

## 2. Existing Infrastructure Audit

### 2.1 Tauri Browser (client/src-tauri/) ✅ EXISTING

| Component | Status | File | Reusability |
|-----------|--------|------|-------------|
| Tauri 2.x setup | ✅ Ready | `Cargo.toml`, `tauri.conf.json` | Base template |
| Multi-window support | ✅ Ready | `main.rs:17-44` | Can create new windows dynamically |
| External webview | ✅ Ready | `commands.rs:736-764` | `open_external_webview` — opens raw URLs |
| Research browser shell | ✅ Ready | `commands.rs:666-732` | `open_research_browser` with Nolan bar |
| Direct web window | ✅ Ready | `commands.rs:769-1238` | Single-instance webview with save functionality |
| Window management | ✅ Ready | `commands.rs:308-622` | Fullscreen, sizing, reuse patterns |
| Backend health check | ✅ Ready | `commands.rs:202-225` | Can check VETKA API |
| Native FS access | ✅ Ready | `file_system.rs` | Read/write files |
| Notification plugin | ✅ Ready | `main.rs:53` | `tauri_plugin_notification` |
| Shell plugin | ✅ Ready | `main.rs:50` | `tauri_plugin_shell` — can launch terminal |
| Dialog plugin | ✅ Ready | `main.rs:52` | File/folder pickers |
| Deep link plugin | ✅ Ready | `main.rs:54` | OAuth callbacks |

**Key Finding:** The `open_research_browser` and `open_direct_web_window` commands already implement a Nolan-style browser shell with address bar, navigation, and save functionality. This is the closest existing piece to WEATHER.

### 2.2 React UI Components ✅ EXISTING (Reusable)

| Component | Status | Location | Reusability for WEATHER |
|-----------|--------|----------|------------------------|
| MCC TaskBoard UI | ✅ Ready | `client/src/components/mcc/` | TaskDAGView, MCCTaskList, MiniTasks |
| Chat UI | ✅ Ready | `client/src/components/chat/` | ChatPanel, ChatSidebar, MessageBubble |
| MiniChat | ✅ Ready | `client/src/components/mcc/MiniChat.tsx` | Compact chat for sidebar |
| DevPanel | ✅ Ready | `client/src/components/devpanel/` | ArtifactViewer |
| API hooks | ✅ Ready | `client/src/utils/chatApi.ts` | Backend communication |

**Key Finding:** All UI components are in the same React app. WEATHER can reuse them by routing to existing pages or extracting them into a shared package.

### 2.3 Backend API ✅ EXISTING

| Endpoint | Status | Purpose |
|----------|--------|---------|
| `/api/taskboard/*` | ✅ Ready | Task CRUD, claim, complete |
| `/api/gateway/*` | ✅ Ready | Agent registration, auth, task ops |
| `/api/chat` | ✅ Ready | Universal chat endpoint |
| SSE `/api/gateway/stream` | ✅ Ready | Real-time task updates |
| WebSocket (SocketIO) | ✅ Ready | Live progress streaming |

---

## 3. Gap Analysis

### 3.1 Browser Foundation 🔴 HIGH EFFORT

| Gap | Solution | Effort |
|-----|----------|--------|
| Separate standalone app | Create `client-weather/` as new Tauri app in same repo | Medium |
| Gmail profile persistence | Use Tauri's `data_dir` per-profile; WebKit on macOS supports separate data directories | Medium |
| Save/restore cookies + localStorage | Tauri's WebKitView persists cookies automatically per data_dir. localStorage persists with it. For explicit save/restore: use `evaluate_script` to export localStorage | Low |
| Multiple profiles simultaneously | Each profile = separate Tauri window with its own `data_dir`. macOS WebKit supports this. Limit: ~4-6 concurrent before RAM issues | Medium |

**Alternative Approach (Recommended):** Instead of building a separate Tauri app, use **Playwright with persistent context** (userDataDir). This gives us:
- Profile persistence out of the box
- Multiple contexts (profiles) per browser instance
- Full DOM automation for code extraction
- No need to build a separate desktop app

The existing `browser_manager.py` (just created in Phase 196.BP1) already implements this pattern.

### 3.2 TaskBoard Integration 🟢 LOW EFFORT

| Gap | Solution | Effort |
|-----|----------|--------|
| Mirror MCC TaskBoard UI | Reuse existing MCC components via shared routes | Low |
| Filter by project | Add `project_id` query param to existing API calls | Low |
| Real-time sync | Use existing SSE endpoint `/api/gateway/stream` | Low |
| Click task → open editor | Tauri `tauri_plugin_shell` can open VSCode/opencode | Low |

### 3.3 Terminal + Chat 🟡 MEDIUM EFFORT

| Gap | Solution | Effort |
|-----|----------|--------|
| Embedded terminal | `tauri_plugin_shell` can spawn processes, but embedding a terminal UI requires xterm.js in React | Medium |
| Launch CLI agents | Shell plugin can run `opencode`, `claude code` commands | Low |
| Chat with local model | Reuse existing ChatPanel component + `/api/chat` endpoint | Low |
| Local model as mediator | Ollama/Qwen already available; needs prompt orchestration layer | Medium |

### 3.4 Universal Agent Interface 🟡 MEDIUM EFFORT

| Gap | Solution | Effort |
|-----|----------|--------|
| Find message input on any AI service | DOM selectors per service (maintain a selector registry) | Medium |
| Inject context | `page.fill()` + `page.keyboard.type()` via Playwright | Low |
| Extract code from response | Already implemented in `browser_agent_proxy.py` (DOM parsing + regex) | Done |
| No per-service adapters | Universal approach: find textarea → type → wait → extract | Medium |

### 3.5 Profile Management 🟡 MEDIUM EFFORT

| Gap | Solution | Effort |
|-----|----------|--------|
| Gmail login → save profile | Playwright persistent context (userDataDir) | Low |
| Multiple profiles per service | Multiple userDataDir paths | Low |
| Session persistence | Automatic with persistent context | Done |
| Auto-login on start | Persistent context preserves sessions | Done |

---

## 4. Recommended Architecture

### Option A: Playwright-Based (Recommended) ✅

```
┌──────────────┐    ┌───────────────┐    ┌──────────────────┐
│  TaskBoard   │───▶│  WEATHER      │───▶│  Playwright      │
│  (existing)  │    │  Orchestrator │    │  Chromium × N    │
│              │◀───│  (Python)     │◀───│  (persistent     │
└──────────────┘    │               │    │   contexts)      │
                    │  + React UI   │    └────────┬─────────┘
                    │  (optional)   │             │
                    └───────────────┘      ┌──────┼──────┐
                                          │      │      │
                                       Gemini  Kimi  Grok
```

**Why this is better:**
- No new desktop app to build/maintain
- Playwright persistent contexts solve profile management natively
- Code extraction is already implemented
- Browser manager already exists (Phase 196.BP1)
- Can add a lightweight React UI later if needed

### Option B: Tauri-Based (Alternative)

Build a separate `client-weather/` Tauri app with:
- Tabbed browser interface (like Chrome)
- Embedded TaskBoard sidebar (React components)
- Embedded terminal (xterm.js)
- Profile manager (data_dir per profile)

**Why this is harder:**
- 2-3x more code to write
- Need to build tab management, profile switching, terminal UI
- Duplicates browser functionality that Playwright already provides
- Maintenance burden of two desktop apps

---

## 5. Implementation Sub-Tasks

### Phase 201.1: Profile Manager (Low Effort)
- [ ] Add profile configuration to `browser_manager.py`
- [ ] Implement userDataDir-based persistent contexts
- [ ] Add profile list/save/load API
- **Files:** `src/services/browser_manager.py`

### Phase 201.2: Universal Prompt Injection (Medium Effort)
- [ ] Create selector registry for AI service input fields
- [ ] Implement universal `send_prompt(page, prompt)` function
- [ ] Add wait-for-response detection
- **Files:** `src/services/adapters/base_adapter.py` (new)

### Phase 201.3: TaskBoard UI Sidebar (Low Effort)
- [ ] Create lightweight TaskBoard view for WEATHER
- [ ] Wire to existing `/api/taskboard/*` endpoints
- [ ] Add SSE real-time updates
- **Files:** New React component or extend existing MCC

### Phase 201.4: Code Extraction Pipeline (Done)
- ✅ Already implemented in `browser_agent_proxy.py`
- ✅ DOM parsing + regex extraction
- ✅ Git commit integration

### Phase 201.5: Terminal Integration (Medium Effort)
- [ ] Add `tauri_plugin_shell` commands for launching CLI agents
- [ ] Create terminal UI component (xterm.js)
- [ ] Wire to local model (Ollama/Qwen)
- **Files:** `client/src-tauri/src/commands.rs`, new React component

### Phase 201.6: Local Model Mediator (Medium Effort)
- [ ] Create mediator service that bridges TaskBoard → AI service
- [ ] Implement context packing (task + files + docs → prompt)
- [ ] Add response routing (AI service → code extraction → git)
- **Files:** `src/services/weather_mediator.py` (new)

---

## 6. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| AI service UI changes break selectors | High | Medium | Selector registry with fallback patterns; regular audits |
| Captcha blocks automation | Medium | High | User notification + pause/rotate strategy (already designed) |
| Rate limiting on free tiers | High | Medium | Account rotation + rate limiting (already designed) |
| Playwright detection by AI services | Medium | Medium | Use stealth plugins; rotate user agents |
| Session expiry | Medium | Low | Auto-restore + re-login prompts |

---

## 7. Decision: Playwright-First, Tauri-Later

**Start with Playwright-based WEATHER** (Option A). The infrastructure is 60% complete:
- ✅ `browser_manager.py` — browser lifecycle
- ✅ `browser_agent_proxy.py` — orchestrator
- ✅ Code extraction — DOM parsing + regex
- ✅ TaskBoard Gateway API — task operations
- ✅ Git auto-commit — Phase 196.CORE_GAP_1

**Remaining 40%:**
- 🔴 Service adapters (selectors per AI service)
- 🔴 Profile management (userDataDir configuration)
- 🟡 Universal prompt injection
- 🟡 Local model mediator
- 🟡 Optional: Tauri UI wrapper (can be added later)

**Timeline estimate:** 2-3 days for core functionality, 1-2 weeks for full polish with UI.
