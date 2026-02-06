# MYCELIUM Dragon Architecture
## Phase 117.2: Anti-Bug Conveyor + Autonomous Agent Teams

**Date:** 2026-02-07
**Status:** DESIGN APPROVED, ready for implementation
**Inspired by:** OpenClaw heartbeat architecture + VETKA existing infra

---

## 1. WHAT WE HAVE (Verified, Real)

Every component below EXISTS and is TESTED:

| Component | File | Phase | What It Does |
|-----------|------|-------|-------------|
| **Agent Pipeline** | `src/orchestration/agent_pipeline.py` | 104 | Fractal pipeline: task decomposition, parallel execution, yielding |
| **Mycelium Pipeline** | `agent_pipeline.py:1301` | 111.13 | `async mycelium_pipeline()` — entry point for multi-agent runs |
| **Mycelium Auditor** | `src/services/mycelium_auditor.py` | 105 | Audits pipeline results |
| **Dragon Presets** | `data/templates/model_presets.json` | 117.1 | 9 team configs: dragon, dragon_budget, dragon_quality, polza_*, quality |
| **Multi-Provider MCP** | `src/mcp/tools/llm_call_tool.py` | 117.1 | `_call_provider_sync()` routes to ANY provider (Polza/Poe/xAI/etc) |
| **Doctor Tool** | `src/mcp/tools/doctor_tool.py` | 106g | Health diagnostics: Ollama, MCP, API keys, QUICK/STANDARD/DEEP |
| **Artifact Workflow** | `src/mcp/tools/artifact_tools.py` | 108.4 | Edit → pending → approve/reject + SocketIO notify |
| **Staging** | `data/staging.json` | 108.4 | Artifact staging area (pending approval) |
| **Elision Compressor** | `src/memory/elision.py` | 92/104 | Token compression 40-60%: abbreviations + vowel skip + paths |
| **Elisya Context DAG** | `src/mcp/tools/context_dag_tool.py` | 109.1 | Assembles viewport/pins/chats/CAM/Engram → ~500 token digest |
| **Session Init** | `src/mcp/tools/session_tools.py` | 108 | Fat context: project_digest + prefs + viewport + Elision |
| **ARC Gap Detector** | `src/mcp/tools/arc_gap_tool.py` | 99.3 | Finds conceptual gaps using pattern extraction + semantic search |
| **SocketIO Streaming** | `llm_call_tool.py:82` | 90.4 | LIGHTNING_CHAT_ID = `5e2198c2...`, emits to group chat |
| **Git Safe** | `src/mcp/tools/git_tools.py` | 108.7 | `vetka_git_commit(dry_run=true)` + auto-digest update |
| **Run Tests** | MCP tool `vetka_run_tests` | — | pytest with timeout, stdout/stderr capture |

### Polza AI (335 models via 1 key)
- Claude Opus 4.6, Sonnet 4.5
- Grok-4, Grok-4.1-fast
- GPT-5, GPT-5.2-pro
- Gemini 3 Pro, Gemini 2.5 Flash
- DeepSeek V3.2, DeepSeek R1
- Qwen3-235B, Qwen3-Coder, Qwen3-Coder-Flash
- GLM-4.7, GLM-4.7-Flash
- Kimi K2.5
- Xiaomi MiMo V2 Flash

---

## 2. WHAT WE NEED TO BUILD (3 components)

### 2.1 Heartbeat Engine (`mycelium_heartbeat.py`) — NEW

Inspired by OpenClaw. Cron-triggered (every 30 min or on-demand).

```
[Heartbeat Tick]
    |
    v
[Doctor Check] ─── unhealthy? → alert to chat, STOP
    |
    v
[Task Queue] ── scan: pending artifacts, known bugs, failed tests
    |
    v
[Dragon Dispatch] ── pick top-priority task → spawn pipeline
    |
    v
[Eval Loop] ── run tests → pass? → approve artifact → git commit
    |               |
    |               └── fail? → retry with error context (max 3)
    |                       |
    |                       └── 3 fails? → escalate to human (chat msg)
    v
[Update Digest] ── write results to project_digest + stream to chat
```

**Task Queue sources:**
- `data/staging.json` — pending artifacts
- `data/bug_queue.json` — NEW: prioritized bug list (manual or auto-detected)
- Failed tests from `vetka_run_tests`
- Doctor alerts

### 2.2 Eval Agent Loop — EXTEND existing

Extend `agent_pipeline.py` with post-execution eval:

```python
# After Dragon fixes a bug:
1. vetka_run_tests(test_path="tests/", pattern=relevant_pattern)
2. If PASS → vetka_approve_artifact(artifact_id) → vetka_git_commit(dry_run=false)
3. If FAIL → inject error into Dragon context → retry (max 3)
4. If 3 FAILS → vetka_send_message("Bug X needs human review", chat_id=LIGHTNING)
```

### 2.3 Stream Fix — FIX existing

**Current bug:** SocketIO emit works for `llm_call_tool` requests/responses,
but Mycelium pipeline output doesn't stream to chat.

**Root cause:** `agent_pipeline.py` calls LLM tool internally but doesn't
emit intermediate results to SocketIO.

**Fix:** Add `_emit_to_chat()` calls at each pipeline phase boundary:
- After architect response → emit
- After researcher response → emit
- After coder response → emit
- After verifier response → emit

---

## 3. DRAGON TEAMS (Verified, Working)

### dragon (default) — Fast + Balanced
| Role | Model | Strength |
|------|-------|----------|
| Architect | `moonshotai/kimi-k2.5` | Multi-agent spawn, long context |
| Researcher | `x-ai/grok-4` | Deep research, web knowledge |
| Coder | `qwen/qwen3-coder` | Top coding benchmarks |
| Verifier | `z-ai/glm-4.7-flash` | Fast verification, 0.7s latency |

### dragon_budget — Ultra-cheap
| Role | Model | Strength |
|------|-------|----------|
| Architect | `qwen/qwen3-30b-a3b` | MoE 30B, fast |
| Researcher | `z-ai/glm-4.7-flash` | Cheapest flash |
| Coder | `qwen/qwen3-coder-flash` | Speed-optimized coder |
| Verifier | `xiaomi/mimo-v2-flash` | Xiaomi ultra-fast |

### dragon_quality — Best Asian
| Role | Model | Strength |
|------|-------|----------|
| Architect | `moonshotai/kimi-k2.5` | Best reasoning |
| Researcher | `deepseek/deepseek-r1-0528` | R1 deep reasoning |
| Coder | `qwen/qwen3-coder` | Best code gen |
| Verifier | `qwen/qwen3-235b-a22b` | 235B full analysis |

---

## 4. SAFE PROTOCOL

**Rule: Dragon NEVER writes to production directly.**

```
Dragon Agent
    |
    v
vetka_edit_artifact(content, dry_run=true)  ← preview only
    |
    v
Human reviews in UI (or eval agent auto-approves if tests pass)
    |
    v
vetka_approve_artifact(id) → vetka_git_commit(dry_run=false)
    |
    v
Auto-digest update (Phase 108.7)
```

**Rollback:** `vetka_reject_artifact(id, feedback)` → Dragon retries with feedback.

**File restrictions:** Dragon can only edit files listed in the task scope.
No `rm`, no git push, no config changes.

---

## 5. ANTI-BUG CONVEYOR: First Targets

| # | Bug | Priority | Dragon Team | Expected Effort |
|---|-----|----------|-------------|----------------|
| 1 | SocketIO streaming in Mycelium | P0 | dragon | 1 session |
| 2 | Chat favorites + CAM binding | P1 | dragon | 1-2 sessions |
| 3 | balance_percent not computed (BUG-2) | P1 | dragon_budget | 30 min |
| 4 | 402 not zeroing balance (BUG-4) | P1 | dragon_budget | 30 min |
| 5 | Per-key balance fetch (BUG-5) | P2 | dragon | 1 session |
| 6 | 103 print() → logger migration | P3 | dragon_budget | auto |
| 7 | 14 pre-existing test failures | P3 | dragon_budget | auto |

---

## 6. IMPLEMENTATION ORDER

```
Phase 117.2a: Fix SocketIO streaming (prerequisite for visibility)
Phase 117.2b: Create bug_queue.json + heartbeat script
Phase 117.2c: Eval loop (tests → approve/reject → retry)
Phase 117.2d: First Dragon auto-fix run (BUG-2, BUG-4 — simplest)
Phase 117.2e: Chat favorites + CAM integration
```

**You + Claude:** Build new features, architecture, spatial intelligence
**Dragon Team:** Fix bugs, migrate code, run tests, clean up

---

## 7. WHAT GROK GOT RIGHT vs WRONG

### Right (verified):
- Elisya + Elision sisters architecture
- Artifact workflow for safe writes
- Doctor tool for health checks
- Yielding cycle in agent_pipeline
- `LIGHTNING_CHAT_ID` streaming

### Wrong (hallucinated):
- `mycelium_engine.py` — doesn't exist (functionality in agent_pipeline.py)
- `mycelium_heartbeat.py` — doesn't exist yet (we need to create it)
- `mycelium_digest.json` — doesn't exist (use project_digest.json)
- `Qwen3-235B` Arena Elo 1425 — exact benchmarks fabricated
- `DeepSeek-V4-300B` — model doesn't exist (V3.2 is latest)
- `GLM-5-200B` — model doesn't exist (GLM-4.7 is latest)

---

*Phase 117.2 — MYCELIUM Dragon Anti-Bug Conveyor*
*"You build. Dragon fixes."*
