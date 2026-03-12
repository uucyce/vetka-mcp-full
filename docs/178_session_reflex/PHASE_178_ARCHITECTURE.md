# Phase 178 - Session Protocol + REFLEX Activation

**Date:** 2026-03-13
**Author:** Opus (Claude Code)
**Status:** ARCHITECTURE + ROADMAP
**Depends on:** Phase 177 (Capability Broker - partial), Phase 172 (REFLEX - built not wired)

---

## Problem Statement

Three interconnected problems discovered by Haiku recon (5 scouts, MARKER_177.S1-S5):

### 1. Session Init is incomplete
`vetka_session_init` returns context but NOT:
- Capability manifest (which transports are alive)
- Active tasks summary (agent doesn't know what to do)
- Actionable next_steps (REFLEX recommendations)
- Recent commits (what just happened)

### 2. REFLEX is built but dead
All REFLEX infrastructure exists (6 services, REST API, tool catalog) but:
- `REFLEX_ENABLED=false` in production
- 5 of 8 scoring signals are stubs (CAM, ENGRAM, STM, HOPE, MGC)
- `feedback_log.jsonl` doesn't exist (no learning)
- Eval triggers in pipeline return 0 (disabled)
- No `next_steps` block in session_init response

### 3. Two disconnected worlds
| Agent Type | Instructions Source | REFLEX Access | Dynamic? |
|-----------|-------------------|---------------|----------|
| Claude Code/Cursor | CLAUDE.md (static file) | Never reached | No |
| Dragon pipeline | pipeline_prompts.json | Not mentioned | No |
| External API models | session_init response | Could work | Partially |

CLAUDE.md is static. REFLEX is dynamic. They don't talk to each other.

### 4. done_task chain breaks
`complete_task()` -> tracker -> digest chain was broken:
- Phase 177 fixed it in code (MARKER_177.6)
- MCP servers may cache old modules (needs process restart)
- `_seq` race detection added but API route not wired

### 5. Git staging pulls dirty files
`git add -A` catches unrelated files from other branches/phases.
Phase 177 Wave 1 fixed this (safe porcelain staging), but needs verification.

---

## What Already Exists (Audit)

### REFLEX Infrastructure (Phase 172 - built)
| Component | File | Status |
|-----------|------|--------|
| Registry | `src/services/reflex_registry.py` | Works - loads catalog |
| Scorer | `src/services/reflex_scorer.py` | Works - but 5/8 signals stub |
| Feedback | `src/services/reflex_feedback.py` | Built - never called |
| Decay | `src/services/reflex_decay.py` | Built - never triggered |
| Integration | `src/services/reflex_integration.py` | Built - REFLEX_ENABLED=false |
| Preferences | `src/services/reflex_preferences.py` | Built - empty |
| Tool Catalog | `data/reflex/tool_catalog.json` | 45+ tools cataloged |
| REST API | `src/api/routes/reflex_routes.py` | Endpoints exist |

### Capability Broker (Phase 177 - partial)
| Component | File | Status |
|-----------|------|--------|
| CapabilityBroker | `src/mcp/tools/capability_broker.py` | New - transport manifest |
| Session enrichment | `src/mcp/tools/session_tools.py` | Enriched with tasks/commits |
| Task complete chain | `src/orchestration/task_board.py` | Fixed - MARKER_177.6 |
| Git safe staging | `src/mcp/tools/git_tool.py` | Fixed - porcelain only |
| vetka_task_board | `src/mcp/vetka_mcp_bridge.py` | Still deprecated stub |

### Memory Systems (exist but disconnected from REFLEX)
| System | Purpose | Connected to REFLEX? |
|--------|---------|---------------------|
| ENGRAM (Qdrant) | Long-term user prefs | No - `include_prefs: False` since Phase 135 |
| STM | Short-term pipeline memory | No - `stm_items` always [] |
| CAM | Context-aware memory nodes | No - `cam_surprise` never passed |
| HOPE | Viewport zoom/LOD | No - hardcoded "MID" |
| MGC | Cache stats | No - `mgc_stats` always {} |

---

## Target Architecture

### Session Init Flow (after Phase 178)

```
Agent connects
    |
    v
vetka_session_init()
    |
    +-- 1. Load project digest (existing)
    +-- 2. Load user preferences from ENGRAM (fix async)
    +-- 3. Load recent_commits (3 last) [Phase 177 - done]
    +-- 4. Load active_tasks from TaskBoard [Phase 177 - done]
    +-- 5. Build capability_manifest via CapabilityBroker [Phase 177 - done]
    +-- 6. Call REFLEX scorer with loaded context [NEW]
    +-- 7. Generate next_steps[] from REFLEX + tasks [NEW]
    +-- 8. ELISION compress ALL of above [fix ordering]
    |
    v
Response includes:
{
  "digest": {...},
  "recent_commits": [...],
  "active_tasks": [...],
  "capabilities": {...},
  "reflex_recommendations": [...],
  "next_steps": [
    "5 pending tasks -> start with mycelium_task_board action=list",
    "Last commit was 2h ago on session_tools.py -> review changes",
    "REFLEX suggests vetka_search_semantic for current fix phase"
  ]
}
```

### REFLEX Activation Chain

```
                        REFLEX Scorer
                       /      |       \
              Signal 1    Signal 2    Signal 3...8
              semantic    feedback    cam/engram/stm/hope/mgc
                 |            |           |
            tool_catalog  feedback_log  memory_systems
                 |            |           |
              registry    JSONL file    ENGRAM/CAM/STM
```

Current: Only Signal 1 (semantic) + Signal 6 (phase_match) work.
Target: All 8 signals active, feedback loop recording, eval triggers firing.

### Done Task Chain (fixed)

```
complete_task(task_id)
    |
    +-- 1. Update task_board.json status=done
    +-- 2. Call task_tracker.track_done(marker, description)
    +-- 3. Call _update_digest_with_task(task_id, commit_hash)
    +-- 4. Increment digest._seq (race detection)
    |
    v
vetka_git_commit(message, files)
    |
    +-- 1. Safe porcelain staging (only specified files)
    +-- 2. git commit
    +-- 3. Update digest with commit hash
    +-- 4. Increment digest._seq
```

---

## Roadmap

### Wave 0: Recon + Docs (THIS DOCUMENT)
- [x] Haiku recon: 5 scouts, all markers placed
- [x] Architecture doc created
- [x] Roadmap with checklist

### Wave 1: REFLEX Activation (quick wins, ~1 session)
**Goal:** Turn on REFLEX and make it visible in session_init.

- [ ] 178.1.1 Set `REFLEX_ENABLED=true` in `.env` and `config.py`
- [ ] 178.1.2 Create `data/reflex/feedback_log.jsonl` (empty file, auto-create on first write)
- [ ] 178.1.3 Fix REFLEX call ordering in session_init: move AFTER tasks/commits/capability load
- [ ] 178.1.4 Add `next_steps[]` block to session_init response:
  - Based on active_tasks count + phase
  - Based on REFLEX top-3 tool recommendations
  - Based on recent_commits (staleness detection)
- [ ] 178.1.5 Wire REFLEX into session_init: call `reflex_scorer.recommend_for_session()`
- [ ] 178.1.6 Tests: 10 tests in `test_phase178_wave1.py`

**Exit criteria:** `vetka_session_init` returns `next_steps` + `reflex_recommendations`.

### Wave 2: Signal Wiring (~1 session)
**Goal:** Connect 5 stub signals to real memory systems.

- [ ] 178.2.1 ENGRAM signal: call `get_engram_user_memory()` in `reflex_pre_fc()` (fix async wrapper)
- [ ] 178.2.2 STM signal: query STM buffer in `ReflexContext.from_subtask()`
- [ ] 178.2.3 CAM signal: pass `cam_surprise` from CAM node activations
- [ ] 178.2.4 HOPE signal: read real viewport zoom from session state (not hardcoded "MID")
- [ ] 178.2.5 MGC signal: read cache stats from MGC service
- [ ] 178.2.6 Re-enable `include_prefs: True` in architect call (wrap Qdrant in async)
- [ ] 178.2.7 Tests: 12 tests in `test_phase178_wave2.py`

**Exit criteria:** All 8 REFLEX signals return real values. Scorer uses full context.

### Wave 3: Eval Triggers + Feedback Loop (~1 session)
**Goal:** REFLEX learns from pipeline outcomes.

- [ ] 178.3.1 Enable IP-1 eval trigger: `reflex_pre_fc()` in fc_loop.py (score > 0)
- [ ] 178.3.2 Enable IP-3 eval trigger: `reflex_post_fc()` records outcome
- [ ] 178.3.3 Enable IP-5 eval trigger: verifier feedback closes loop
- [ ] 178.3.4 Auto-create feedback_log.jsonl on first write
- [ ] 178.3.5 Add `match_rate` metric: recommended vs actually used
- [ ] 178.3.6 Tests: 8 tests in `test_phase178_wave3.py`

**Exit criteria:** After pipeline run, `feedback_log.jsonl` has entries. Match rate tracked.

### Wave 4: Universal REFLEX Injection — ALL surfaces (~1.5 session)
**Goal:** REFLEX visible EVERYWHERE a model picks a tool. Recommended vs chosen — tracked on ALL platforms.

#### 4A: Dragon Pipeline (agent_pipeline.py)
- [x] 178.4.1 IP-1,3,5,7 already fire (Waves 1-3)
- [ ] 178.4.2 Inject REFLEX summary into system prompts at runtime
- [ ] 178.4.3 Architect sees: "Team performance: coder success 78%, verifier caught 3 issues"
- [ ] 178.4.4 Coder sees: "REFLEX recommends: vetka_edit_file (0.92), vetka_search_semantic (0.85)"

#### 4B: MCC Workflow (orchestrator_with_elisya.py — PM→Architect→Dev→QA)
- [ ] 178.4.5 Find injection points in workflow orchestrator
- [ ] 178.4.6 Add reflex_pre_fc/post_fc to workflow agent calls
- [ ] 178.4.7 Track recommended vs chosen in workflow context

#### 4C: Chat Agent Calls (vetka_call_model / mycelium_call_model)
- [ ] 178.4.8 Add REFLEX pre/post hooks to vetka_call_model MCP tool
- [ ] 178.4.9 Add REFLEX pre/post hooks to mycelium_call_model MCP tool
- [ ] 178.4.10 Every LLM call through VETKA ecosystem logs: recommended tools, chosen tools, match_rate

#### 4D: Session Init for External Agents (Claude Code, Cursor, API)
- [ ] 178.4.11 session_init already returns reflex_recommendations + next_steps (Wave 1)
- [ ] 178.4.12 Add `reflex_report` to session_init: last 10 match_rates, feedback_summary
- [ ] 178.4.13 External agents see full REFLEX picture on connect

#### 4E: Tests
- [ ] 178.4.14 Tests: ~12 tests in `test_phase178_wave4.py`

**Exit criteria:** Every model call in VETKA ecosystem (pipeline, workflow, chat, MCP) has REFLEX visibility. Recommended vs chosen tracked everywhere.

### Wave 5: CLAUDE.md Dynamic Bridge (~0.5 session)
**Goal:** Bridge static CLAUDE.md with dynamic session_init.

- [ ] 178.5.1 Add to CLAUDE.md: "After session_init, follow `next_steps` if present"
- [ ] 178.5.2 session_init `next_steps` references CLAUDE.md task lifecycle protocol
- [ ] 178.5.3 Document: CLAUDE.md = "what tools exist", session_init = "what to do now"
- [ ] 178.5.4 Verify: Claude Code agent reads session_init and acts on next_steps

**Exit criteria:** Claude Code agent follows dynamic guidance from session_init.

### Wave 6: Unified Facade + vetka_task_board Resurrection (~1 session)
**Goal:** One tool name, automatic transport routing.

- [ ] 178.6.1 Un-deprecate `vetka_task_board` — make it live fallback (Phase 177 code exists)
- [ ] 178.6.2 Verify MCP server loads new code (kill old Python process)
- [ ] 178.6.3 Add transport selection logging ("using: rest_api fallback")
- [ ] 178.6.4 End-to-end test: MYCELIUM down -> vetka_task_board -> REST -> file
- [ ] 178.6.5 Tests: 5 tests in `test_phase178_wave6.py`

**Exit criteria:** Agent can always reach TaskBoard regardless of which MCP is alive.

### Wave 7: Verify Full Chain (~0.5 session)
**Goal:** Smoke test everything.

- [ ] 178.7.1 Create task via MCP
- [ ] 178.7.2 Claim + start task
- [ ] 178.7.3 Complete task -> verify tracker updated
- [ ] 178.7.4 Commit -> verify digest updated + _seq incremented
- [ ] 178.7.5 Call session_init -> verify next_steps include the completed task context
- [ ] 178.7.6 Verify no dirty files in commit (safe staging)

**Exit criteria:** Full protocol works end-to-end. Real test, not mock.

---

## Test Summary

| Wave | Tests | Focus |
|------|-------|-------|
| W1 | ~10 | REFLEX activation + next_steps |
| W2 | ~12 | Signal wiring to memory systems |
| W3 | ~8 | Eval triggers + feedback loop |
| W4 | ~6 | Pipeline injection |
| W5 | ~3 | CLAUDE.md bridge verification |
| W6 | ~5 | Unified facade + transport fallback |
| W7 | ~6 | End-to-end smoke test |
| **Total** | **~50** | |

---

## Execution Order

```
W1 (REFLEX on) -> W2 (signals) -> W3 (eval triggers) -> W4 (pipeline inject)
                                                              |
W5 (CLAUDE.md bridge) -----> can start after W1               |
W6 (unified facade) -------> can start after W1               |
W7 (smoke test) -----------> after ALL waves                  v
```

W1 is the foundation. W5 and W6 can run in parallel with W2-W4.
W7 is the final validation.

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| REFLEX slows session_init | Timeout 200ms, fallback to no-REFLEX response |
| Qdrant blocks async loop (Phase 135 bug) | Wrap in `asyncio.to_thread()` |
| Feedback log grows unbounded | Compaction after 1000 entries (172.P3.4 spec exists) |
| Dragon agents ignore REFLEX | Inject into system prompt, not optional context |
| MCP server caches old code | Document: must kill Python process, not just restart |

---

## Relation to Previous Phases

| Phase | What it did | Status | Carried into 178 |
|-------|------------|--------|------------------|
| 172 | Built REFLEX infrastructure | Complete (code exists) | W1-W3 activate it |
| 173 | Planned REFLEX Active (filtering) | Roadmap only | Deferred to 179 |
| 177 | Capability Broker + session enrichment | Partial (committed) | W6 completes it |

Phase 178 = "turn everything on and connect it."
Phase 179 = "optimize" (active filtering, A/B, model-specific tuning from 173 roadmap).

---

*MARKER_178.ARCHITECTURE - Phase 178: Session Protocol + REFLEX Activation*
