# ROADMAP 198: Memory System Closure
**Author:** Zeta (Opus 4.6) | **Date:** 2026-03-24
**Status:** P0 COMPLETE, P1-P3 in progress
**Domain:** Zeta (harness) + cross-cutting

---

## Problem Statement

Memory is leaking. The system was designed with JEPA-style adaptive compression,
ELISION expand/contract, MGC multi-generational caching, ENGRAM user context,
CORTEX-REFLEX feedback loops. But in practice:

- **CLAUDE.md = static .md files** loaded on every turn (~3K tok overhead)
- **MEMORY.md = index of .md files** that Claude reads manually (no compression, no triggers)
- **MGC = 0 hits** because MCP bridge runs in separate process, never writes to cache
- **ELISION compression was a no-op** (fixed in Phase 197, but not wired everywhere)
- **session_init** returns fat JSON instead of adaptive context based on model needs
- No memory triggers — agent asks "how was this done before?" and greps manually

The system was designed right (VETKA_MEMORY_DAG) but the wiring is incomplete.

---

## Vision (from user)

1. **No static .md as memory** — Claude can write .md, but data must be dynamic, cached, compressed
2. **Adaptive context** — model gets context based on WHO it is and WHAT it needs (not one-size-fits-all)
3. **ELISION expand** — `_l expand = _list` pattern for LOD (Level of Detail), already designed
4. **Memory triggers** — auto-activate on "how was this?", "what did I do?", glob, grep, vetka_search
5. **CORTEX-REFLEX → memory** — successful/failed patterns from task board feed into memory automatically
6. **MGC everywhere** — cache all computed context, share between processes
7. **Universal init** — one entry point for Claude Code, Codex, Gemini, Cursor, MCC

---

## Recon Tasks (Phase 198.0)

| # | Agent | What | Status |
|---|-------|------|--------|
| R1 | Sonnet | Audit MEMORY_DAG design doc → what was designed vs what's built | DISPATCHED |
| R2 | Sonnet | Audit ELISION/MGC code → where wired, where not, expand/contract | DISPATCHED |
| R3 | Sonnet | Audit CORTEX-REFLEX → memory pipeline → what data flows where | DISPATCHED |
| R4 | Sonnet | Audit memory triggers → what intercepts exist, what's missing | DISPATCHED |

## Implementation Plan (Phase 198.1+, after recon)

| # | Task | Priority | Task ID | Status |
|---|------|----------|---------|--------|
| P0.1 | STM: Persist last session state to disk, load on init | P0 | tb_1774336656_1 | DONE (commit 7cfa37b4) |
| P0.2 | CAM: Jaccard task delta surprise (NOT viewport) | P0 | tb_1774336661_1 | DONE (commit 2a621f89) |
| P0.3 | HOPE: LOD from task complexity + model tier | P0 | tb_1774336667_1 | DONE (commit 83c47869) |
| P0.4 | ENGRAM: L2→L1 auto-promotion at ≥3 matches | P0 | tb_1774336674_1 | DONE (commit 6210a00e) |
| P0.5 | ELISION: Apply L2 to session_init response dict | P0 | tb_1774336681_1 | DONE |
| P0.6 | Debrief fix: worktree path, guard, callsign, direct routing | P0 | tb_1774338917_1 | DONE (commit 9ec399c3) |
| P1.1 | D1↔D3: Protocol Guard → Caution emotion | P1 | tb_1774336686_1 | DONE |
| P1.2 | D2↔D3: Tool Freshness → Curiosity emotion | P1 | tb_1774336689_1 | DONE |
| P1.3 | MGC Gen1: Replace Qdrant stub (shared cache, cross-process) | P1 | tb_1774336711_1 | PENDING |
| P1.4 | ELYSIA → DORMANT (Signal 9 future path) | P1 | tb_1774337745_1 | DONE (commit 04863798) |
| P1.5 | score() emotions bypass fix | P1 | tb_1774337733_1 | PENDING |
| P1.6 | Verifier→Trust wiring | P1 | tb_1774337737_1 | PENDING |
| P1.7 | Direct Qdrant L2 ingest: debrief → Gemma embed → Qdrant → MGC → ENGRAM L1 | P1 | tb_1774340094_1 | PENDING |
| P2.1 | MCP bridge pre/post hooks | P2 | tb_1774336713_1 | PENDING |
| P2.2 | Claim-time: inject similar completed tasks | P2 | tb_1774336714_1 | PENDING |
| P2.3 | ELYSIA evaluation | P2 | tb_1774336723_1 | PENDING |
| P2.4 | Post-failure workaround lookup | P2 | tb_1774337724_1 | PENDING |
| P3.1 | Model-adaptive ELISION: Haiku→L3, Sonnet→L2, Opus→L1 | P3 | tb_1774336719_1 | PENDING |
| P3.2 | REFLEX Signal 9 (ELYSIA path) | P3 | tb_1774337717_1 | PENDING |

---

## Design Decision

**No watchdog.** Direct pipeline at `action=complete` trigger.

```
action=complete
    → debrief Q1-Q3
    → Gemma embedding
    → Qdrant L2 ingest
    → MGC warm cache
    → ENGRAM L1 (if match_count ≥ 3)
```

No `.md` files in the memory chain. No background polling. No separate watchdog process.
Trigger is synchronous with task closure.

---

## Key Reference

- **Entry point:** `docs/besedii_google_drive_docs/VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md`
- **ELISION code:** `src/memory/elision.py` (if exists) or search for elision/compress
- **MGC code:** search for `mgc` / `MultiGenerationalCache`
- **CORTEX-REFLEX:** `src/services/reflex_feedback.py`, `src/services/reflex_integration.py`
- **ENGRAM:** search for `engram` in `src/`
- **Session init:** `src/mcp/tools/session_tools.py`
- **Handoff (P0 complete):** `docs/198ph_ZETA_memory_update/HANDOFF_ZETA_198_MEMORY_CLOSURE_2026-03-24.md`

---

*"Memory that isn't triggered by context is just a filing cabinet nobody opens."*
