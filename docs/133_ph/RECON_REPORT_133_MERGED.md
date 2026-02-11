# Phase 133 Recon Report — Stable Dragons
**Date:** 2026-02-10
**Commander:** Opus (Claude Code worktree)
**Status:** Phase 132 MERGED, recon complete, Cursor executing

---

## Merge Status
- **Branch merged:** `origin/claude/continue-vetka-project-lOrZX` → `claude/eloquent-ptolemy`
- **Merge type:** Fast-forward, 8 files changed, +490 lines
- **Key fixes from Phase 132:**
  - `MARKER_132.R1` — Coder LLM retry with exponential backoff (agent_pipeline.py)
  - `MARKER_132.R2` — Architect LLM retry with backoff (agent_pipeline.py)
  - `MARKER_132.H2` — Heartbeat debug logging (mycelium_heartbeat.py)
  - `MARKER_132.M1` — Universal client endpoints: progress, release (task_routes.py)
  - **CRITICAL FIX:** `mycelium_mcp_server.py:448` — `await heartbeat_tick()` (was missing await)

---

## 9-Scout Recon Findings (Haiku Phase)

### Scout 1: Heartbeat Engine
- **File:** `src/orchestration/mycelium_heartbeat.py`
- **Status:** Functional after await fix
- Parses: @dragon, @titan, @doctor, @help, @pipeline, /task, /fix, /build, /research
- Loop prevention (lines 165-170): skips pipeline's own messages
- Dedup (lines 384-406): title-based, 1-hour window
- **Gap:** No heartbeat daemon auto-restart on crash

### Scout 2: Pipeline System
- **File:** `src/orchestration/agent_pipeline.py` (2862+ lines)
- All 5 phases implemented: Scout → Architect → Researcher → Coder → Verifier
- Retry logic at lines 2068-2088 (MAX_CODER_RETRIES + tier upgrade)
- STM at lines 1403-1442, auto-reset at 2132-2142 (10 subtask window)
- Dual streaming: WS broadcaster (1020-1034) + SocketIO (1047-1072)
- **Gap:** No per-phase timeouts (Cursor C33B will fix)

### Scout 3: Approval Service
- **File:** `src/services/approval_service.py` (471 lines)
- FULLY connected (was flagged as TODO in Phase 131 — actually done)
- Dual mode: VETKA=manual, MYCELIUM=auto via L2 ScoutAuditor (score >= 0.7)
- Integrated in orchestrator_with_elisya.py
- **No action needed**

### Scout 4: MCP Architecture
- Dual MCP confirmed: VETKA (5001) + MYCELIUM (WS 8082)
- All tool handlers properly async
- heartbeat_tick await fix confirmed (line 448)

### Scout 5: TaskBoard
- **File:** `src/orchestration/task_board.py` (885 lines)
- JSON-backed: `data/task_board.json`
- States: pending → queued → claimed → running → done/failed/cancelled
- Priority 1-5, sorted (priority ASC, created_at ASC)
- Claim mechanism: MARKER_130.C16A (lines 301-335)
- **Gap:** max_concurrent stored but NOT enforced (Cursor C33C will fix)

### Scout 6: DevPanel Frontend
- Fully operational, 6 tabs, dual WebSocket (SocketIO + native WS)
- Real-time pipeline streaming works

### Scout 7: Multi-Client
- Session isolation works
- **Gaps:** No client_id tracking (Cursor C33D), no file locking, no optimistic locking

### Scout 8: Documentation
- Clear trail Phase 14→131, organized in docs/
- All reports should go to LOCAL DISK for Vetka scanning

### Scout 9: Git State
- Phase 132 merged, 3 commits ahead of Phase 131
- Clean working tree (only untracked docs/133_ph/)

---

## Cursor Tasks (Phase 133 — C33A-D)
Cursor working from `CURSOR_BRIEF_133_STABLE_DRAGONS.md`:

| Task | File | Status | Priority |
|------|------|--------|----------|
| C33A: Provider Resilience Decorator | llm_call_tool_async.py | IN PROGRESS (Cursor) | P1 |
| C33B: Per-Phase Timeouts | agent_pipeline.py | PENDING | P1 |
| C33C: Concurrent Semaphore | task_board.py | PENDING | P2 |
| C33D: client_id Tracking | task_routes.py + task_board.py | PENDING | P2 |

---

## Opus Tasks (This Session)
| Task | Status |
|------|--------|
| Merge Phase 132 | DONE |
| Verify heartbeat await fix | DONE |
| Write recon report | DONE (this file) |
| Sync docs to main repo | NEXT |
| Write Grok research prompt | NEXT |
| E2E Dragon test | PENDING |

---

## Architecture Summary (Post-Merge)

```
User/Chat → @dragon task
    ↓
Heartbeat (60s loop, mycelium_heartbeat.py)
    ↓ await heartbeat_tick() ← FIXED
TaskBoard (task_board.py, JSON queue)
    ↓ dispatch → AgentPipeline
Pipeline 5 phases:
    Scout → Architect → Researcher → Coder → Verifier
    ↓ (retry + tier upgrade on fail)
Approval (auto L2 for mycelium mode)
    ↓
Result → Chat + DevPanel WS
```

## Key Memory Notes
- **Reports → LOCAL DISK:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/`
- Vetka scans this directory (sometimes auto, sometimes manual import)
- Cursor works in MAIN repo, Opus in worktree
- Dragon team: Polza provider (Kimi, Grok Fast, Qwen, GLM)
