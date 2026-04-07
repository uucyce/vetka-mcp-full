# ROADMAP: Gemma Fleet Full Integration
**Version:** 1.0 | **Date:** 2026-04-07 | **Author:** Agent Zeta (Harness Captain)
**Status:** DRAFT — pending review by User + Grok

---

## Executive Summary

Gemma Fleet (Omicron/Pi/Rho/Sigma) infrastructure is 90% built but **not integrated end-to-end**. Benchmarks prove Gemma4 warm cache = 0.38s, strict prompt = 9.5x speedup. LiteRT classifier = 7ms. The pieces exist — they need wiring.

**Goal:** Gemma agents autonomously claim tasks, execute via tool calls, and complete through TaskBoard — same pipeline as Claude agents.

---

## Current State (What Exists)

### Infrastructure — DONE
| Component | Status | Location |
|-----------|--------|----------|
| 4 Gemma worktrees (gemma-engine/scout/sherpa/qa) | Created | `.claude/worktrees/gemma-*` |
| 4 Gemma branches (claude/gemma-*) | Created | git branches |
| 19 CLAUDE.md with XML tool protocol | Generated | Each worktree |
| agent_registry.yaml with 4 Gemma roles | On main | `data/templates/agent_registry.yaml` |
| spawn_synapse.sh free_code case | On main | `scripts/spawn_synapse.sh` |
| free-code binary (Claude Code fork) | Available | `~/Documents/VETKA_Project/free-code/cli-dev` |
| Ollama with gemma4:e2b/e4b/26b | Running | localhost:11434 |
| LiteLLM proxy | Running | localhost:4000 |
| litellm_gemma_bridge.py | Running | localhost:4001 |
| LiteRT (ai_edge_litert 2.1.3) | Installed | pip package |

### Benchmarks — DONE (Captain Polaris, 2026-04-05)
| Tier | Model | Warm Cache | Use Case |
|------|-------|-----------|----------|
| Drone | gemma4:e2b | **0.38s** | Code classification, intent detection |
| Plane | gemma4:e4b | **0.37s** | Task enrichment (26s), code gen (60s) |
| Vision | gemma4:e4b | 37.8s | Screenshot analysis, UI detection |
| Classifier | LiteRT MobileNetV2 | **7.16ms** | Router, 34x faster than Ollama |

### Sherpa/Scout/Verifier — DONE (Phase 202-203)
| Component | Lines | Status |
|-----------|-------|--------|
| Sherpa v1.1 (async recon) | 1709 | Active, running |
| Scout v1.0 (code analyzer) | 532 | Active, hook in TaskBoard |
| Verifier (quality gate) | ~100 | Active, middleware |
| PULSAR (SHM+RV+AV) | ~400 | Blueprinted, not coded |

### Prompt Engineering — DONE
- Grok system prompt for XML tool calls (in CLAUDE.md template)
- Strict JSON prompt: 9.5x speedup (6.9s → 0.73s)
- Gemma follows instructions well with explicit formatting rules

---

## Critical Gaps (What's Broken)

### GAP-1: MCP Not Connected (P0 — BLOCKING)
**Problem:** Gemma worktrees have no `.mcp.json` → free-code can't call MCP tools (session_init, task_board, read_file, etc.)
**Impact:** Agent starts but can't interact with VETKA infrastructure
**Fix:** Generate/copy MCP config into each Gemma worktree during spawn

### GAP-2: Bridge Latency (P0 — BLOCKING)
**Problem:** litellm_gemma_bridge.py (Priority C, deprecated) buffers entire response before forwarding → "Cultivating..." hangs 2+ minutes
**Impact:** Agent appears frozen; laptop overheats from sustained GPU load
**Fix:** Switch to Priority B — system prompt forces XML output, thin parser (15 lines) in bridge or direct LiteLLM without bridge
**Evidence:** Polaris benchmarks show 0.38s warm cache WITHOUT bridge

### GAP-3: No Task Board Gemma Logic (P1)
**Problem:** TaskBoard has no domain="gemma" filtering, no model tier routing, no XML tool call validation
**Impact:** Gemma agents can't auto-claim tasks from their domain
**Fix:** Add Gemma domain filter + model tier awareness to list/claim

### GAP-4: No Pre-flight Validation (P1)
**Problem:** spawn_synapse.sh doesn't check if Ollama/LiteLLM are running before launching agent
**Impact:** Agent spawns into broken environment, fails silently
**Fix:** Health checks for :4000, :4001, :11434 before exec

### GAP-5: Lost Docs Not On Main (P2)
**Problem:** ROADMAP_GEMMA_BRIDGE_INTEGRATION.md and LITELLM_BRIDGE_TEST.md never reached main
**Fix:** Cherry-pick from harness-eta

### GAP-6: Benchmark Tests Not Integrated (P2)
**Problem:** polaris-iota has 3 test suites (model_tier, drone_tier, vision_tier) but never run in fleet
**Fix:** Cherry-pick tests to main, run via Sigma (QA agent)

---

## Architecture: Gemma Fleet Pipeline

### Agent Roles & Models

```
Pi (Scout / gemma4:e2b / fastest)
  → Auto-recon on new tasks
  → Warm cache 0.38s → instant code location analysis
  → Feeds scout_context to Sherpa and agents

Omicron (Engine / gemma4:e4b / balanced)
  → Claims build/fix tasks
  → Task enrichment (26s), code generation (60s)
  → Primary workhorse for CUT development

Rho (Sherpa-Eyes / gemma4:26b / deepest)
  → Vision analysis, screenshot parsing
  → Deep security audit, architect-level review
  → On-demand only (17GB, constrain on 24GB Mac)

Sigma (QA / gemma4:e4b / verifier)
  → Runs tests, verifies implementations
  → Cross-checks Omicron's output
  → Files fix tasks if regressions found
```

### Task Lifecycle with Gemma

```
1. Task created (Commander or auto)
   Status: pending

2. Pi (Scout/e2b) auto-analyzes (0.38s warm)
   → ripgrep + ast.parse → scout_context
   → Status: scout_recon

3. Sherpa enriches (optional, 2min via external AI)
   → Uses scout_context for grounded research
   → Status: recon_done

4. Omicron (Engine/e4b) claims and builds (26-60s)
   → Reads scout_context + recon_docs
   → Implements, commits
   → Status: done_worktree

5. Sigma (QA/e4b) verifies
   → Runs tests, checks allowed_paths
   → Status: verified OR needs_fix

6. Commander/Zeta merges to main
   → Status: done_main
```

### Progressive Enhancement (80% Early Exit)

```
Level 1: Pi/e2b (0.38s) — classify, scout, quick answer
  ↓ if complex
Level 2: Omicron/e4b (26s) — enrich, build, review
  ↓ if critical/vision
Level 3: Rho/26b (74s) — deep analysis, architect review
```

Most tasks resolve at Level 1-2. Only security audits and vision tasks escalate to Level 3.

### Subtask Decomposition (Big Gemma → Small Gemma)

For tasks exceeding e2b's context or capability:
1. Omicron (e4b) receives complex task
2. Decomposes into 3-5 atomic subtasks (MARKER_201.DECOMPOSER)
3. Each subtask → TaskBoard as child task
4. Pi (e2b) scouts each subtask (0.38s × 5 = 1.9s total)
5. Omicron or Pi executes atomic subtasks
6. Sigma verifies each, then verifies parent

**Context budget:** E2B has 128K tokens — sufficient for single-file tasks. E4B has 128K — sufficient for multi-file refactors. Decomposition keeps each subtask within 1-2 files.

### Memory Strategy (M4 24GB)

```
Always Resident (9.7 GB):
  gemma4:e2b    7.2 GB   ← Pi (Scout), always warm
  phi4-mini     2.5 GB   ← fast classifier backup

On-Demand (9.6 GB):
  gemma4:e4b    9.6 GB   ← Omicron/Sigma, load for task, auto-unload 5min idle

Rare (17 GB):
  gemma4:26b   17.0 GB   ← Rho, load only for vision/deep tasks, unload immediately

LiteRT (negligible):
  MobileNetV2   ~5 MB    ← classification router, 7ms, always available
```

---

## Sprint Plan

### Sprint 1: Fix Blocking Gaps (Day 1)
**Owner:** Zeta

| # | Task | Priority | Estimate |
|---|------|----------|----------|
| 1.1 | Fix MCP config: generate `.mcp.json` for Gemma worktrees in spawn_synapse.sh | P0 | 30min |
| 1.2 | Remove bridge from spawn chain: connect free-code → LiteLLM :4000 directly | P0 | 30min |
| 1.3 | Upgrade system prompt: full Grok prompt with few-shot XML examples in CLAUDE.md template | P0 | 20min |
| 1.4 | Add thin XML parser to LiteLLM config (15 lines, replaces 250-line bridge) | P0 | 30min |
| 1.5 | Pre-flight health checks in spawn_synapse.sh | P1 | 15min |
| 1.6 | E2E test: spawn Omicron → session_init → read_file → complete | P0 | 30min |

**Exit criteria:** Omicron spawns, calls session_init via MCP, reads a file, responds in <30s (not 2 minutes)

### Sprint 2: Fleet Activation (Day 1-2)
**Owner:** Zeta + Eta

| # | Task | Priority | Estimate |
|---|------|----------|----------|
| 2.1 | Spawn all 4 Gemma agents, verify each can session_init | P1 | 1h |
| 2.2 | Add TaskBoard domain="gemma" filter + model tier routing | P1 | 30min |
| 2.3 | Cherry-pick lost docs from harness-eta to main (ROADMAP, LITELLM_BRIDGE_TEST) | P2 | 10min |
| 2.4 | Cherry-pick Polaris benchmark tests to main | P2 | 15min |
| 2.5 | Configure model router: task_type → model mapping in registry | P2 | 30min |

**Exit criteria:** All 4 agents online, auto-claiming tasks from gemma domain

### Sprint 3: Pipeline Integration (Day 2-3)
**Owner:** Zeta (harness) + Epsilon (tests) + Delta (QA)

| # | Task | Priority | Estimate |
|---|------|----------|----------|
| 3.1 | Wire Pi (Scout/e2b) as auto-recon on task creation | P1 | 1h |
| 3.2 | Wire Omicron (Engine/e4b) to claim recon_done tasks | P1 | 30min |
| 3.3 | Wire Sigma (QA/e4b) to verify done_worktree tasks | P1 | 30min |
| 3.4 | Add subtask decomposition: Omicron decomposes complex tasks for Pi | P2 | 1h |
| 3.5 | Warm cache strategy: keep e2b always loaded, e4b on-demand | P2 | 30min |

**Exit criteria:** Full pipeline: task → Pi scouts → Omicron builds → Sigma verifies

### Sprint 4: PULSAR + Testing (Day 3-4)
**Owner:** Epsilon (test creation) + Delta (verification)

| # | Task | Priority | Estimate |
|---|------|----------|----------|
| 4.1 | Epsilon: write E2E tests for Gemma spawn + tool call chain | P1 | 2h |
| 4.2 | Epsilon: write E2E tests for Pi→Omicron→Sigma pipeline | P1 | 2h |
| 4.3 | Delta: independent verification of all E2E tests | P1 | 2h |
| 4.4 | Run Polaris benchmark suites against live fleet | P2 | 1h |
| 4.5 | Code PULSAR modules (SHM + RV + AV, ~400 lines) | P2 | 4h |

**Exit criteria:** E2E tests pass, Delta verifies, benchmarks match Polaris results

### Sprint 5: Production Readiness (Day 4-5)
**Owner:** Zeta + Commander

| # | Task | Priority | Estimate |
|---|------|----------|----------|
| 5.1 | LiteRT router integration: classify task → route to correct model tier | P2 | 2h |
| 5.2 | Tmux history-limit per role tier (from Grok recommendation) | P3 | 30min |
| 5.3 | Update USER_GUIDE_MULTI_AGENT.md v8.0 with Gemma fleet operations | P2 | 1h |
| 5.4 | Clear stale tmux scrollback on respawn | P3 | 15min |
| 5.5 | Final merge to main, tag release | P1 | 30min |

**Exit criteria:** Gemma fleet operational in production, documented, tested

---

## Key Decisions Needed

1. **Bridge or direct?** — Evidence says direct (LiteLLM :4000) + system prompt. Bridge (Priority C) adds 2min latency. Polaris proved 0.38s without bridge.

2. **free-code or opencode?** — free-code works with `--bare` flag. Opencode needs custom provider setup. Recommend: keep free-code for Gemma, opencode for Polaris/Qwen fleet.

3. **26B model usage** — 17GB on 24GB Mac is tight. Options: (a) on-demand only, (b) use Q4 quantization (10GB), (c) skip 26B, use e4b for vision. Recommend: (a) on-demand, auto-unload after task.

4. **PULSAR priority** — SHM+RV are P1 (improve Sherpa quality). AV is P2 (Arena voting is nice-to-have). Code all 3 in Sprint 4?

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Gemma XML output unstable in stream | Tool calls not parsed | Strict system prompt + few-shot examples (proven 9.5x) |
| 24GB RAM pressure with e4b + e2b resident | OOM, swap, overheating | Memory strategy: e2b always, e4b on-demand, monitor with `ollama ps` |
| free-code binary outdated / breaks | Spawn fails | Pin version, test on update, fallback to opencode |
| MCP config divergence across worktrees | Tools unavailable | Generate MCP config dynamically in spawn_synapse.sh |
| Merge regression (lesson learned 2026-04-07) | Lost docs, broken scripts | Always read docs first, never --ours blindly, E2E tests mandatory |

---

## Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Omicron spawn → first response | <30s | ~120s (bridge) |
| Pi warm cache response | <1s | 0.38s (proven) |
| E2E pipeline (task → verified) | <5min | Not tested |
| Gemma agents completing real tasks | >0 | 0 |
| E2E test suite | passing | Not written |
| Delta independent verification | pass | Not done |

---

## References

- `docs/210_sherpa_gemma4/BENCHMARK_RESULTS_LIVE.md` — Polaris race results
- `docs/210_sherpa_gemma4/GEMMA_BRIDGE_SESSION4_UPDATE_2026-04-06.md` — Bridge status
- `docs/202ph_SHERPA/ARCHITECTURE_SHERPA_V2_SPACE.md` — PULSAR spec
- `docs/202ph_SHERPA/ARCHITECTURE_SCOUT_VERIFIER_CHAIN.md` — Scout/Verifier design
- `docs/177_MCC_local/LITERT_BENCHMARK_RESULTS.md` — LiteRT benchmarks
- `data/templates/agent_registry.yaml` — Gemma role definitions
- `.claude/worktrees/polaris-iota/tests/benchmark/` — Benchmark test suites
