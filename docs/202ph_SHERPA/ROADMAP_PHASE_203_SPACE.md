# ROADMAP: Phase 203 — VETKA SPACE + SHERPA PULSAR
# From Scout to Intelligence

**Date:** 2026-04-03
**Author:** Captain Burnell (Джойс) + Commander
**Captains:** Burnell (Claude Opus) + Polaris (Qwen 3.6+ Free)
**Fleet:** 9 agents (3 Qwen, 3 Mistral Vibe, 3 Claude Code)

---

## 0. Phase Summary

**Goal:** Evolve Sherpa from a dumb round-robin scout into an intelligent recon system with:
- Health-aware service routing (ServiceHealthMonitor)
- Ethical Arena participation (ArenaVoter)
- Response quality verification (ReconVerifier)
- WEATHER → SPACE domain rename

**Timeline:** 4 sprints, ~2-3 days each
**Scope:** ~400 new lines in sherpa.py + config updates + tests

---

## 1. Sprint Plan

### Sprint 1: Foundation (ReconVerifier + Config)
**Duration:** Day 1
**Why first:** Verifier is pure logic, no I/O, no Playwright — safest to build and test first. All other modules depend on the VerifyResult dataclass.

| # | Task | Role | Domain | Parallel? | Complexity |
|---|------|------|--------|-----------|------------|
| 1.1 | Implement `VerifyResult` dataclass + `ReconVerifier` class | **Theta** (Qwen) | SPACE | -- | Low |
| 1.2 | Implement `extract_terms()` + `is_in_code_block()` helpers | **Iota** (Qwen) | SPACE | with 1.1 | Low |
| 1.3 | Write unit tests for ReconVerifier (8 fixtures: good/bad/hallucinated/short/off-topic/repetitive/no-code/edge) | **Mistral-2** (QA) | QA | with 1.1, 1.2 | Medium |
| 1.4 | Update `sherpa.yaml` — add `pulsar:` section with verifier config | **Kappa** (Qwen) | SPACE | with 1.1 | Low |
| 1.5 | Update `SherpaConfig` to parse `pulsar:` section from yaml | **Kappa** (Qwen) | SPACE | after 1.4 | Low |

**Parallel execution:** Tasks 1.1, 1.2, 1.3, 1.4 can ALL run simultaneously. 1.5 waits for 1.4.
**Integration:** After all complete, Burnell integrates into sherpa.py and verifies.

---

### Sprint 2: Health Monitor (ServiceHealthMonitor)
**Duration:** Day 1-2
**Why second:** SHM reads existing JSONL (FeedbackCollector output) — needs to understand the data format. Depends on nothing from Sprint 1 except config.

| # | Task | Role | Domain | Parallel? | Complexity |
|---|------|------|--------|-----------|------------|
| 2.1 | Implement `ServiceHealthMonitor` class — health scoring algorithm | **Polaris** (Qwen Captain) | SPACE | -- | Medium |
| 2.2 | Implement rate-limit detection in DOM (signals list + page scan) | **Theta** (Qwen) | SPACE | with 2.1 | Medium |
| 2.3 | Implement fallback chain logic + recovery mode | **Iota** (Qwen) | SPACE | with 2.1 | Medium |
| 2.4 | Write unit tests for SHM (mock JSONL, test scoring, test fallback) | **Mistral-2** (QA) | QA | after 2.1 | Medium |
| 2.5 | Add `fallback_chain:` and `health:` to sherpa.yaml + config parser | **Kappa** (Qwen) | SPACE | with 2.1 | Low |
| 2.6 | Update `sherpa_loop` to use SHM instead of round-robin (lines 1603-1618) | **Burnell** (Opus) | Engine | after 2.1, 2.3 | Medium |

**Parallel execution:** Tasks 2.1, 2.2, 2.3, 2.5 can ALL run simultaneously. 2.4 needs 2.1 done. 2.6 needs 2.1+2.3.
**Integration:** Burnell wires SHM into sherpa_loop and runs integration test.

---

### Sprint 3: Arena Voter (ArenaVoter)
**Duration:** Day 2-3
**Why third:** Arena is a specific service — needs real Playwright testing. Lower priority than SHM+RV.

| # | Task | Role | Domain | Parallel? | Complexity |
|---|------|------|--------|-----------|------------|
| 3.1 | Implement `ArenaVoter` class — scoring algorithm (volume + relevance + code) | **Polaris** (Qwen Captain) | SPACE | -- | Medium |
| 3.2 | Implement Arena DOM detection — dual response extraction | **Theta** (Qwen) | SPACE | with 3.1 | Medium |
| 3.3 | Implement vote button click logic (find A/B/Tie buttons, click winner) | **Iota** (Qwen) | SPACE | with 3.1 | Medium |
| 3.4 | Write unit tests for scoring (mock responses, verify math) | **Mistral-1** (Vibe) | QA | after 3.1 | Low |
| 3.5 | Integration test: real Arena page, extract dual, score, vote | **Burnell** (Opus) | Engine | after 3.1-3.3 | High |
| 3.6 | Wire ArenaVoter into sherpa_loop (Arena-specific branch after extraction) | **Burnell** (Opus) | Engine | after 3.5 | Low |

**Parallel execution:** Tasks 3.1, 3.2, 3.3 can ALL run simultaneously. 3.5 needs all three.
**Integration:** Burnell runs `sherpa.py --once --service arena` with real Arena page.

---

### Sprint 4: Integration + SPACE Rename
**Duration:** Day 3
**Why last:** Everything is built, now wire together and rename.

| # | Task | Role | Domain | Parallel? | Complexity |
|---|------|------|--------|-----------|------------|
| 4.1 | Full PULSAR integration test: SHM + RV + AV in sherpa_loop | **Burnell** (Opus) | Engine | -- | High |
| 4.2 | Update ARCHITECTURE_SHERPA.md with v2.0 status | **Mistral-3** (Vibe) | SPACE | with 4.1 | Low |
| 4.3 | Rename WEATHER references → SPACE in docs + worktree names | **Mistral-1** (Vibe) | SPACE | with 4.1 | Low |
| 4.4 | Update agent_registry.yaml — WEATHER domain → SPACE domain | **Kappa** (Qwen) | SPACE | with 4.1 | Low |
| 4.5 | Run 10-task autonomous test, collect metrics | **Delta** (QA) | QA | after 4.1 | Medium |
| 4.6 | Write SHERPA_USER_GUIDE.md — how to run, configure, monitor | **Polaris** (Qwen Captain) | SPACE | after 4.5 | Medium |

**Parallel execution:** Tasks 4.2, 4.3, 4.4 can run with 4.1. 4.5 waits for 4.1. 4.6 waits for 4.5.

---

## 2. Role Assignment Summary

| Role | Agent | Model | Sprint Tasks | Total |
|------|-------|-------|-------------|-------|
| **Burnell** (Captain) | Claude Opus | Opus 4.6 | 2.6, 3.5, 3.6, 4.1 | 4 (complex integration) |
| **Polaris** (Captain) | Qwen 3.6+ | Free | 2.1, 3.1, 4.6 | 3 (algorithm design) |
| **Theta** | Qwen 3.6+ | Free | 1.1, 2.2, 3.2 | 3 (implementation) |
| **Iota** | Qwen 3.6+ | Free | 1.2, 2.3, 3.3 | 3 (implementation) |
| **Kappa** | Qwen 3.6+ | Free | 1.4, 1.5, 2.5, 4.4 | 4 (config + registry) |
| **Mistral-1** | Vibe CLI | Free | 3.4, 4.3 | 2 (tests + docs) |
| **Mistral-2** | Vibe CLI | Free | 1.3, 2.4 | 2 (QA tests) |
| **Mistral-3** | Vibe CLI | Free | 4.2 | 1 (docs update) |
| **Delta** | Claude Haiku | Haiku | 4.5 | 1 (integration QA) |

**Total tasks:** 22
**Max parallel at once:** 4 (Sprint 1: tasks 1.1, 1.2, 1.3, 1.4)

---

## 3. Dependency Graph

```
Sprint 1 (Foundation)
  1.1 VerifyResult+ReconVerifier ─┐
  1.2 extract_terms helpers ──────┤──→ Integration by Burnell
  1.3 RV unit tests ─────────────┤     (merge Sprint 1)
  1.4 yaml config ───→ 1.5 parser┘

Sprint 2 (Health Monitor)            ← Can start same day as Sprint 1
  2.1 SHM class ──────────┬──→ 2.4 SHM tests
  2.2 rate-limit detect ──┤
  2.3 fallback chain ─────┼──→ 2.6 Wire into sherpa_loop (Burnell)
  2.5 yaml + parser ──────┘

Sprint 3 (Arena Voter)              ← Starts after Sprint 1 done
  3.1 AV scoring ─────────┬──→ 3.4 AV tests
  3.2 Arena DOM detect ───┼──→ 3.5 Integration test (Burnell)
  3.3 Vote click logic ───┘        → 3.6 Wire into loop

Sprint 4 (Integration)              ← All sprints done
  4.1 Full PULSAR test (Burnell) ──→ 4.5 10-task autonomous (Delta)
  4.2 Update arch docs ────────────      → 4.6 User guide (Polaris)
  4.3 WEATHER→SPACE rename ────────
  4.4 agent_registry update ───────
```

**Key insight:** Sprints 1 and 2 can run in parallel (different modules, no code overlap). Sprint 3 needs Sprint 1's `extract_terms()` helper. Sprint 4 needs everything.

---

## 4. Critical Path

```
1.1 (Theta) → merge → 2.6 (Burnell) → 3.5 (Burnell) → 4.1 (Burnell) → 4.5 (Delta)
```

**Bottleneck:** Burnell (me) — I'm the integration point. All modules converge through my hands because I own sherpa.py and know the codebase intimately.

**Mitigation:** Polaris and Theta write standalone classes with clear interfaces. I integrate. They don't need to understand the full sherpa_loop — just implement the interface.

---

## 5. Task Spec Template (for dispatcher)

Each task created on TaskBoard should include:

```
title: "SPACE-203.{sprint}.{number}: {description}"
project_id: "cut"
domain: "engine" (for Burnell) / "weather" → "space" (for Polaris team)
phase_type: "build" | "test"
priority: 2 (P2 — high, part of active sprint)
description: Full spec with:
  - Input/Output contract
  - Class/function signatures
  - Algorithm pseudocode (from ARCHITECTURE_SHERPA_V2_SPACE.md)
  - File to edit: sherpa.py (line range)
  - Test requirements
architecture_docs:
  - "docs/202ph_SHERPA/ARCHITECTURE_SHERPA_V2_SPACE.md"
recon_docs:
  - "docs/202ph_SHERPA/ROADMAP_PHASE_203_SPACE.md"
allowed_paths:
  - "sherpa.py"
  - "config/sherpa.yaml"
  - "tests/test_sherpa_*.py"
completion_contract:
  - "Class implemented with all methods from interface"
  - "Unit tests pass (pytest -v)"
  - "No new dependencies added"
```

---

## 6. SPACE Domain — What Changes

| Before (WEATHER) | After (SPACE) | Notes |
|-------------------|---------------|-------|
| weather-core worktree | space-core (or keep as-is) | Rename optional — worktrees are infra |
| WEATHER domain in agent_registry | SPACE domain | Registry update needed |
| docs/201ph_WEATHERE/ | docs/201ph_WEATHERE/ (keep) | Historical — don't move |
| docs/202ph_SHERPA/ | docs/203ph_SPACE/ (new phase) | New docs go here |
| "WEATHER Agent 1" role | "SPACE Agent 1" role | Cosmetic |

**Non-breaking:** Existing code doesn't reference "WEATHER" as a string. The rename is purely organizational (docs, roles, task labels).

---

## 7. Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Arena UI changes (selectors break) | AV module useless | `pulsar.arena.enabled: false` — graceful disable |
| Qwen agents can't handle algorithm complexity | Delay Sprint 2-3 | Burnell takes over; Polaris reviews |
| Rate limit storms (all services down simultaneously) | Sherpa stuck | Recovery mode: 5min sleep, retry with highest-reliability service |
| Free model tiers disappear (Qwen, Mistral) | Fleet shrinks | Tasks designed to be completable by any agent — no role lock-in |
| Merge conflicts (9 agents, 1 file) | Integration hell | Each sprint has isolated class. Burnell merges one sprint at a time. |

---

## 8. Success Metrics (Phase 203 Complete)

- [ ] ReconVerifier catches >80% of garbage responses in unit tests
- [ ] ServiceHealthMonitor correctly routes away from failing services
- [ ] ArenaVoter casts a vote in >90% of Arena interactions
- [ ] Full PULSAR loop processes 10 tasks with <20% reject rate
- [ ] No regressions in existing Sherpa v1.0 functionality
- [ ] All tests pass (existing + new)
- [ ] SPACE domain docs created and linked in MEMORY.md

---

*"Find the signal in the noise" — Burnell*
*"Navigate by the fixed star" — Polaris*
*Together: PULSAR illuminates the SPACE.*
