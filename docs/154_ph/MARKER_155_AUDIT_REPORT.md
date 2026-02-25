# MYCELIUM AUDIT REPORT — Phase 155 Recovery
**Date:** 2026-02-18
**Status:** Post-Phase 154 — Cleanup & Optimization Required

---

## EXECUTIVE SUMMARY

### ✅ What Works (PRESERVE)
1. **Backend Pipeline** — Fractal workflow (Scout→Researcher→Architect→Coder→Verifier)
2. **Memory Systems** — STM, ELISION, MGC (10,876 lines production code)
3. **Matryoshka UI** — 6-level navigation with max 3 buttons rule enforced
4. **FooterActionBar** — Unified 3-action interface per level

### ⚠️ Critical Issues (FIX)
1. **Playground Self-Recursion** — Needs external placement (~/.vetka/playgrounds/)
2. **Event Loop Blocking** — tree_routes.py:284-300 sync operations in async routes
3. **Slow Shutdown** — reload=True with 1.1M files = 10-12sec graceful timeout

### 🎯 New Requirements (IMPLEMENT)
1. **VETKA Chat Integration** — Task nodes link to VETKA chat IDs
2. **Agent Statistics Dashboard** — Per-agent metrics (time, tokens, quality)
3. **Architect Team Remarks** — Quality ratings per execution

---

## 1. PLAYGROUND REORGANIZATION (VARIANT C)

### MARKER_155.PLAYGROUND.EXTERNAL_PLACEMENT
**Location:** `src/orchestration/playground_manager.py`

**Current (BROKEN):**
```
data/playgrounds/vetka-playground/ → inside project → watchdog sees → recursion
```

**Target (FIXED):**
```
~/.vetka/playgrounds/vetka-playground/ → outside project → watchdog doesn't see
```

**Files to Modify:**
- `src/orchestration/playground_manager.py` — MARKER_155.PLAYGROUND.PATH (Line ~45)
- `src/orchestration/playground_manager.py` — MARKER_155.PLAYGROUND.SYMLINK (Line ~92)
- `src/orchestration/playground_manager.py` — MARKER_155.PLAYGROUND.GUARD (Line ~67)

---

## 2. EVENT LOOP BLOCKING FIX

### MARKER_155.PERF.ASYNC_TREE_ROUTES
**Location:** `src/api/routes/tree_routes.py` (lines 284-325)

**Problem:** qdrant.scroll() + os.path.exists() in async route blocks for 22 seconds

**Solution:** Async Qdrant client + batch file checks + pagination

**Files:**
- `src/api/routes/tree_routes.py` — MARKER_155.PERF.ASYNC_QDRANT
- `src/api/routes/tree_routes.py` — MARKER_155.PERF.ASYNC_FILE
- `src/memory/qdrant_client.py` — Add async methods

---

## 3. RELOAD PERFORMANCE

### MARKER_155.PERF.RELOAD_TOGGLE
**Location:** `main.py:1166` and `run.sh:19`

**Add:** `VETKA_RELOAD=false` environment variable support

---

## 4. VETKA CHAT INTEGRATION

### MARKER_155.INTEGRATION.VETKA_CHAT_LINK
**User Story:** Task nodes show linked VETKA chat, agents post results there

**Backend:**
- `src/api/routes/mcc_routes.py` — MARKER_155.INTEGRATION.CHAT_ENDPOINT

**Frontend:**
- `client/src/components/mcc/nodes/RoadmapTaskNode.tsx` — MARKER_155.INTEGRATION.CHAT_BADGE
- `client/src/store/useMCCStore.ts` — MARKER_155.INTEGRATION.CHAT_STORE

**Config:**
- `data/task_board.json` — Add vetka_chat_id field

---

## 5. AGENT STATISTICS DASHBOARD

### MARKER_155.STATS.AGENT_METRICS
**Per-agent metrics:** time, tokens, cost, quality score, architect remarks

**Files:**
- `src/models/agent_metrics.py` — NEW — MARKER_155.STATS.MODEL
- `data/agent_metrics.json` — NEW — MARKER_155.STATS.STORAGE
- `src/api/routes/analytics_routes.py` — MARKER_155.STATS.ENDPOINTS
- `client/src/components/mcc/MiniStats.tsx` — MARKER_155.STATS.UI

---

## 6. USER FLOW (5 Steps)

```
1. 🚀 LAUNCH — "What project?" (FirstRunView - DONE)
2. 📁 PLAYGROUND — "Where to work?" (External placement)
3. 🔑 KEYS — "What API key?" (Key selection)
4. 🗺️ DAG — "What's the plan?" (Roadmap with VETKA chat links)
5. 🔍 DRILL — "Execute task" (Workflow with live updates)
```

### MARKER_155.FLOW.STEP_INDICATORS
**New component:** StepIndicator.tsx showing progress 1→2→3→4→5

---

## 7. MARKER REGISTRY

### P0 — Critical
| MARKER | File | Line | Description |
|--------|------|------|-------------|
| MARKER_155.PLAYGROUND.PATH | playground_manager.py | 45 | External path ~/.vetka/ |
| MARKER_155.PLAYGROUND.GUARD | playground_manager.py | 67 | Prevent internal paths |
| MARKER_155.WATCHDOG.EXCLUDE | watchdog config | — | Exclude ~/.vetka/ pattern |
| MARKER_155.PERF.ASYNC_QDRANT | tree_routes.py | 284 | Async Qdrant scroll |
| MARKER_155.PERF.ASYNC_FILE | tree_routes.py | 314 | Batch file checks |

### P1 — Important
| MARKER | File | Description |
|--------|------|-------------|
| MARKER_155.PERF.RELOAD | main.py:1166 | Env toggle |
| MARKER_155.STATS.MODEL | agent_metrics.py | New model |
| MARKER_155.STATS.ENDPOINTS | analytics_routes.py | API endpoints |
| MARKER_155.STATS.UI | MiniStats.tsx | Dashboard |
| MARKER_155.INTEGRATION.CHAT | mcc_routes.py | Chat linking |

### P2 — Enhancement
| MARKER | File | Description |
|--------|------|-------------|
| MARKER_155.FLOW.STEPS | StepIndicator.tsx | 5-step UI |
| MARKER_155.CLEANUP | Multiple | Remove deprecated |

---

## 8. WHAT TO PRESERVE

✅ **Backend Pipeline** — agent_pipeline.py (fractal workflow)
✅ **Memory Systems** — STM, ELISION, MGC (production ready)
✅ **Matryoshka UI** — 6 levels, 3 buttons max
✅ **FooterActionBar** — Unified actions

## 9. WHAT TO REMOVE

⚠️ RailsActionBar.tsx — Replaced by FooterActionBar
⚠️ WorkflowToolbar.tsx — Commented out, fully remove
⚠️ Internal playground paths — Move to ~/.vetka/

## 10. WHAT TO CREATE

🆕 Agent metrics model
🆕 VETKA chat integration
🆕 Step indicator component
🆕 Async Qdrant methods

---

## APPENDIX: Current Architecture

### Working Backend (Preserve)
```
src/
├── orchestration/
│   ├── agent_pipeline.py        ✅ 2000+ lines, fractal workflow
│   ├── playground_manager.py    ⚠️  Needs external path fix
│   └── orchestrator_with_elisya.py ✅ Production
├── memory/
│   ├── stm_buffer.py           ✅ 338 lines
│   ├── elision.py              ✅ 781 lines, compression
│   ├── mgc_cache.py            ✅ 482 lines, 4-tier cache
│   └── engram_user_memory.py   ✅ User preferences
└── api/routes/
    ├── debug_routes.py         ✅ 1700+ lines
    ├── mcc_routes.py           ✅ 514 lines
    ├── tree_routes.py          ⚠️ Needs async fix
    └── analytics_routes.py     🆕 Needs agent metrics
```

### Working Frontend (Preserve)
```
client/src/components/mcc/
├── MyceliumCommandCenter.tsx   ✅ 1291 lines, main UI
├── DAGView.tsx                 ✅ 444 lines, ReactFlow
├── FooterActionBar.tsx         ✅ 3 actions per level
├── MatryoshkaTransition.tsx    ✅ Drill-down animation
├── FirstRunView.tsx            ✅ Onboarding
├── MiniChat.tsx                ✅ Top-left window
├── MiniTasks.tsx               ✅ Bottom-right window
├── MiniStats.tsx               ✅ Top-right window
└── nodes/
    ├── RoadmapTaskNode.tsx     ✅ Task nodes
    └── [8 other node types]    ✅ All working
```

### Deprecated (Remove)
```
client/src/components/mcc/
├── RailsActionBar.tsx          ⚠️ MARKER_154.3A deprecated
├── WorkflowToolbar.tsx         ⚠️ MARKER_154.3A commented out
└── CaptainBar.tsx              ✅ Keep (roadmap only)
```

---

## APPENDIX: Implementation Order

### Phase 1: Critical Fixes (P0)
- [ ] MARKER_155.PLAYGROUND.* — External playground placement
- [ ] MARKER_155.WATCHDOG.EXCLUDE — Watchdog isolation
- [ ] MARKER_155.PERF.ASYNC_* — Event loop unblocking

### Phase 2: Performance (P1a)
- [ ] MARKER_155.PERF.RELOAD — Dev experience

### Phase 3: Features (P1b)
- [ ] MARKER_155.STATS.* — Agent metrics
- [ ] MARKER_155.INTEGRATION.* — VETKA chat

### Phase 4: Polish (P2)
- [ ] MARKER_155.FLOW.STEPS — UI improvements
- [ ] MARKER_155.CLEANUP — Remove deprecated

---

**END OF AUDIT**

**Next Action:** Start implementing P0 MARKERs (Playground + Performance)

---

## UPDATE: VETKA Chat Integration Status

### ✅ CONFIRMED: Integration ALREADY EXISTS

**Backend (Production Ready):**
- `src/orchestration/task_board.py:308` — `source_chat_id` field (MARKER_152.3)
- `src/orchestration/agent_pipeline.py:1389` — Posts results to chat via API
- `src/orchestration/mycelium_heartbeat.py:95` — Tracks source_chat_id for tasks

**Frontend (Partial):**
- ✅ `client/src/components/panels/TaskEditor.tsx:99` — Shows "From: Chat #xxxx"
- ✅ `client/src/components/mcc/MCCTaskList.tsx:398` — Passes source_chat_id
- ⚠️ `client/src/components/mcc/nodes/RoadmapTaskNode.tsx` — **MISSING** chat link badge

### Required UI Enhancements (Not New Integration):

#### MARKER_155.UI.CHAT_LINK_BADGE
**File:** `client/src/components/mcc/nodes/RoadmapTaskNode.tsx`
**Add:** Chat icon (💬) badge next to team badge when source_chat_id exists
**Click:** Opens VETKA chat in new tab

```typescript
// Add to RoadmapTaskNode data interface:
sourceChatId?: string;
sourceChatUrl?: string;

// Add to render:
{data.sourceChatId && (
  <span 
    className="chat-badge"
    onClick={(e) => {
      e.stopPropagation();
      window.open(`/chat/${data.sourceChatId}`, '_blank');
    }}
    title="Open linked VETKA chat"
  >
    💬
  </span>
)}
```

#### MARKER_155.UI.CHAT_TASK_LIST
**File:** `client/src/components/mcc/MiniChat.tsx` (expanded view)
**Add:** Section showing "Linked Tasks" with status badges

#### MARKER_155.UI.ASK_ARCHITECT_CHAT
**File:** `client/src/components/mcc/FooterActionBar.tsx`
**Modify:** "Ask Architect" action should open linked chat or create new one

### Data Flow:
```
VETKA Chat → @dragon command → Mycelium Task
     ↑                                      ↓
   Results ←──── Agent Pipeline ←──── Task Execution
```

**No new backend needed** — just UI polish to expose existing functionality!

