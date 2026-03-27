# ARCHITECTURE 198: Memory System Closure
**Author:** Zeta (Opus 4.6) + 8 Sonnet recon agents | **Date:** 2026-03-24
**Status:** P0 COMPLETE — P1/P2/P3 pending
**Source:** R1-R4 (code audit), R5-R8 (docs + tasks + ELYSIA/ELISYA + design history)

---

## 1. Executive Summary

The VETKA cognitive architecture was designed with 15+ memory subsystems.
Most are **built** but many are **not wired** or **partially working**.
The result: memory leaks into static .md files, caches stay cold,
signals are disconnected at the exact moments they're needed most.

**Core finding:** The system writes to memory but rarely reads at the right time.

---

## 2. Subsystem Status Matrix

### Fully Working (design → code → wired → producing value)
| Subsystem | File | Signal |
|-----------|------|--------|
| ELISION (L1-L5 + expand) | `src/memory/elision.py` | 12+ call sites, proven compression |
| REFLEX scorer (8-signal) | `src/services/reflex_scorer.py` | End-to-end: IP-1→IP-3→IP-5→decay→recs |
| CORTEX (feedback log) | `src/services/reflex_feedback.py` | 347+ entries, auto-compaction, scoring |
| AURA (user profile) | `src/memory/aura_store.py` | 15+ call sites, RAM+Qdrant, ELISION integrated |
| ARC (architecture suggest) | `src/agents/arc_solver_agent.py` | MCP tool, standalone |
| ELISYA (LLM routing) | `src/elisya/` | Multi-provider, active |
| Resource Learnings (L2) | `src/orchestration/resource_learnings.py` | Qdrant-backed, JSON fallback |

### Built but Partially Wired (critical gaps)
| Subsystem | File | What's Missing |
|-----------|------|----------------|
| ENGRAM (L1 cache) | `src/memory/engram_cache.py` | FIXED: auto-promotion at ≥3 matches (P0.4, commit 6210a00e) |
| MGC (3-gen cache) | `src/memory/mgc_cache.py` | Gen1 Qdrant = STUB (returns None). Cross-process = 0 |
| STM (short-term) | `src/memory/stm_buffer.py` | FIXED: disk persistence + load on init (P0.1, commit 7cfa37b4) |
| CAM (saliency) | `src/orchestration/cam_engine.py` | FIXED: Jaccard task delta (P0.2, commit 2a621f89) |
| HOPE (LOD) | `src/agents/hope_enhancer.py` | FIXED: task complexity + model tier (P0.3, commit 83c47869) |

### Built but Dead/Dormant
| Subsystem | File | Status |
|-----------|------|--------|
| ELYSIA (Weaviate tools) | `src/orchestration/elysia_tools.py` | DORMANT — future REFLEX Signal 9 path (P1.4, commit 04863798) |
| JEPA (predictive embedding) | `src/knowledge_graph/jepa_integrator.py` | Disabled by default, HTTP bridge to external service |
| PULSE (narrative navigator) | Schema only | No implementation |
| Spectral math (Laplacian/Fiedler/GFT) | Design docs only | Not coded |

---

## 3. Critical Wiring Gaps

### [FIXED] Gap 1: STM + CAM + HOPE signals dead or misrouted at session_init
```python
# reflex_scorer.py:303 — hardcoded zeros
stm_items=[]        # "STM empty at session start" — 0.15 weight = 0
cam_surprise=0.0     # "Not available at session start" — 0.12 weight = 0
```
**Impact:** 27% of REFLEX scoring signal is always zero.

**BUG: CAM confused with Camera/Viewport.**
`cam_surprise` should measure *information novelty* (delta between previous and current
task context in embedding space, or user favorite/flag markers). It is NOT the 3D viewport
camera position. `from_session()` correctly hardcodes 0.0, but the fix must NOT read
from viewport. CAM = Constructivist Agentic Memory (surprise detector for finding needles
in haystacks via automatic + manual favorite markers).

**BUG: HOPE LOD reads viewport zoom instead of task complexity.**
`hope_level` at line 274 reads `viewport.zoom` — this is VETKA 3D UI zoom, irrelevant
for coding agents. HOPE should derive LOD from task scope (single-file fix = HIGH detail,
cross-domain research = LOW overview) or model tier (Haiku = compressed/LOW, Opus = full/HIGH).

**Correct fixes:**
- **STM:** Load from previous session's last state (disk-persisted STM snapshot)
- **CAM surprise:** Compute cosine distance between previous task embedding and current task
- **HOPE level:** Derive from task `complexity` field + model tier, NOT viewport zoom

### [FIXED] Gap 2: ENGRAM L2→L1 auto-promotion not implemented
Design: "L2 learning matched ≥3 times → promoted to L1 (ENGRAM)."
Reality: `resource_learnings.py` stores to Qdrant L2 but never checks match_count, never calls `engram_cache.put()`.
**Impact:** Valuable patterns stay in cold Qdrant, never reach hot ENGRAM cache.

### Gap 3: MGC Gen1 is a complete stub
```python
# mgc_cache.py — Gen1 Qdrant path
def _get_from_qdrant(self, key):
    return None  # Always falls through to Gen2 JSON
```
**Impact:** No warm tier. Gen0 (RAM) evicts → straight to disk (Gen2). Cross-process sharing impossible.

### Gap 4: No memory triggers on MCP tool calls
The MCP bridge (`vetka_mcp_bridge.py:1060`) is a flat dispatch switch with only logging.
No pre/post hooks that enrich tool calls with memory or record outcomes.
**Impact:** Agent search/grep/claim gets no "here's what worked before" auto-suggestion.

### Gap 5: ELISION not applied to largest payloads
session_init response and task_board responses go uncompressed despite ELISION being built and available.
**(Partially fixed in Phase 197 via field stripping, but not via actual ELISION compression.)**

---

## 4. The Memory Flow Today vs Designed

### Today (broken flow)
```
task complete → debrief Q1-Q3 (OPTIONAL, often empty)
                    ↓
              smart_debrief → CORTEX (tool-level only)
                            → ENGRAM (text-matched, regex)
                            → MGC (hot-file markers, never read)
                    ↓
              experience_report → JSON file (read by next session_init)
                    ↓
              session_init → fat JSON blob (mostly unused by agent)
                    ↓
              CLAUDE.md → static .md (redundant with session_init)
                    ↓
              MEMORY.md → index of .md files (manual grep by agent)
```
**Problems:** Debrief is optional. CORTEX is tool-level not task-level. MGC writes are orphaned.
MEMORY.md requires agent to manually follow links. No reactive triggers mid-session.

### Designed (target flow)
```
task complete → CORTEX records tool outcomes (automatic)
             → debrief routes to ENGRAM/REFLEX (text-based, automatic)
             → Resource Learnings → Qdrant L2 (automatic)
             → L2 match_count ≥3 → ENGRAM L1 promotion (automatic)
                    ↓
next session_init → REFLEX scorer uses:
                    - CORTEX feedback (0.18)
                    - STM from previous session (0.15) ← BROKEN
                    - CAM saliency (0.12) ← BROKEN
                    - ENGRAM L1 patterns (0.07)
                    - HOPE LOD (0.05) ← PROXY ONLY
                    ↓
mid-session:  → agent calls search/grep → intercept enriches with similar past results
              → agent claims task → inject similar completed tasks
              → tool fails → REFLEX checks for known workaround
              → agent asks "how was this done?" → semantic memory trigger
```

---

## 5. Implementation Priorities

### P0: Wire What's Built (no new code, just connections)
| # | Task | Files | Impact | Status |
|---|------|-------|--------|--------|
| 1 | STM: Persist last session state to disk, load on next session_init | `stm_buffer.py`, `session_tools.py`, `reflex_scorer.py` | Unlocks 15% signal weight | DONE (tb_1774336656_1, commit 7cfa37b4) |
| 2 | CAM: Compute surprise from task embedding delta (NOT viewport) | `cam_engine.py`, `session_tools.py`, `reflex_scorer.py` | Unlocks 12% signal weight | DONE (tb_1774336661_1, commit 2a621f89) |
| 3 | HOPE: Derive LOD from task complexity + model tier (NOT viewport zoom) | `reflex_scorer.py` | Correct 5% signal, enable adaptive compression | DONE (tb_1774336667_1, commit 83c47869) |
| 4 | ENGRAM: Implement L2→L1 auto-promotion (≥3 matches) | `resource_learnings.py` | Patterns auto-surface | DONE (tb_1774336674_1, commit 6210a00e) |
| 5 | ELISION: Apply L2 to session_init response dict | `session_tools.py` | 40%+ compression on largest payload | DONE (tb_1774336681_1) |
| 6 | Debrief fix: worktree path, guard, callsign, direct routing | `smart_debrief.py`, `session_tools.py` | Debrief→memory pipeline unblocked | DONE (tb_1774338917_1, commit 9ec399c3) |

### P1: Fix Cross-Process Cache
| # | Task | Files | Impact |
|---|------|-------|--------|
| 5 | MGC Gen1: Replace Qdrant stub with Redis (or file-lock Gen2) | `mgc_cache.py` | Warm cache shared between MCP + web |
| 6 | MGC: Cache session_init result with TTL | `session_tools.py` | Skip rebuild on rapid re-calls |
| 7 | MGC: Absolute path for `data/mgc_cache.json` | `mgc_cache.py` | Consistent across processes/worktrees |
| 7 | Direct Qdrant L2 ingest: debrief → Gemma embed → Qdrant → MGC → ENGRAM L1 | `resource_learnings.py`, `smart_debrief.py` | No .md files in memory chain (tb_1774340094_1, PENDING) |

> **Design Decision:** NO watchdog. Direct pipeline at `action=complete` trigger.
> Flow: Gemma embedding → Qdrant L2 → MGC → ENGRAM L1. No .md files in the memory chain.

### P2: Add Memory Triggers (new infrastructure)
| # | Task | Files | Impact |
|---|------|-------|--------|
| 8 | MCP bridge pre/post hooks | `vetka_mcp_bridge.py` | Foundation for all triggers |
| 9 | Post-failure: REFLEX workaround lookup | `vetka_mcp_bridge.py` + `reflex_feedback.py` | Auto-suggest fix on tool error |
| 10 | Claim-time: Inject similar completed tasks | `task_board_tools.py` + `resource_learnings.py` | Agent sees predecessors' approach |
| 11 | Search enrichment: Similar past results | `vetka_mcp_bridge.py` + `elysia/` | "Here's what worked before" |

### P3: Adaptive Context (JEPA-style)
| # | Task | Files | Impact |
|---|------|-------|--------|
| 12 | Model-adaptive ELISION: Haiku→L3, Sonnet→L2, Opus→L1 | `elision.py` + call sites | Right detail for right model |
| 13 | HOPE: Replace viewport proxy with actual LOD analysis | `reflex_scorer.py` + `hope_enhancer.py` | Real hierarchical context |
| 14 | max_context_tokens enforcement via ELISION level auto-tuning | `session_tools.py` | Adaptive compression to fit budget |

### P4: Cleanup
| # | Task | Files | Impact |
|---|------|-------|--------|
| 15 | Delete orphaned ELYSIA (elysia_tools.py) | `src/orchestration/elysia_tools.py` | Dead code removal |
| 16 | Replace static MEMORY.md with dynamic memory query | Claude Code config | No more .md stacks |
| 17 | Global CLAUDE.md → minimal universal entry | `~/.claude/CLAUDE.md` | -175 tok/turn |

---

## 6. Key Reference Documents

| Doc | Purpose |
|-----|---------|
| `docs/besedii_google_drive_docs/VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md` | Original cognitive architecture design |
| `docs/198ph_ZETA_memory_update/ROADMAP_198_MEMORY_CLOSURE.md` | Phase 198 roadmap |
| `docs/190_ph_CUT_WORKFLOW_ARCH/feedback/EXPERIENCE_ZETA_HARNESS_2026-03-23.md` | Previous Zeta session insights |

---

## 7. REFLEX Signal Weights (code vs design)

| Signal | Design Weight | Code Weight | Status |
|--------|--------------|-------------|--------|
| Semantic | 0.30 | 0.22 | Working |
| Feedback/CORTEX | 0.15 | 0.18 | Working |
| Phase | — | 0.18 | Working (not in original design) |
| STM | 0.15 | 0.15 | DEAD (always []) |
| CAM | 0.15 | 0.12 | DEAD (always 0.0) |
| ENGRAM | — | 0.07 | Working (reads only) |
| HOPE | 0.10 | 0.05 | PROXY (viewport zoom, not real HOPE) |
| MGC | — | 0.03 | Working (but 0 hits in MCP context) |

**27% of scoring capacity (STM + CAM) is permanently zero in MCP agent sessions.**

---

*"The architecture was designed right. The wires just need connecting."*

---

## 8. Deep Recon Findings (R5-R8)

### Phase Documentation Timeline (R5)
| Phase | What | Key Decision | Status |
|-------|------|--------------|--------|
| 91 | ELISION audit | Algorithm was mock (`content[:target]`), expand_folder never implemented | L1-L5 now real |
| 99 | STM/MGC design | Gen0→Gen1(Qdrant)→Gen2(JSON), MemoryProxy circuit-breaker | Gen1 = stub |
| 157 | JEPA integration | 3-level LOD (L0 local/L1 cluster/L2 global), A/B test plan | Dormant, HTTP bridge disabled |
| 172 | REFLEX blueprint | 3 layers (Registry/Scorer/Cortex), 6 injection points | Working |
| 178 | "Turn it all on" | 7 waves to activate REFLEX, 5/8 signals were stubs | Waves 1+3 done, 2 partial |
| 186 | Cognitive stack | ENGRAM L1/L2 split, AURA rename, Grok weight calibration | L1 exists, L2→L1 not wired |
| 192 | Smart debrief routing | regex→subsystem matrix, `_route_to_memory()` designed | F4 wiring was the final task |
| 193 | REFLEX Guard | Feedback guard + self-healing loop (3 failures→ENGRAM danger) | Built, D1↔D3 not wired |
| 195 | 3 workstreams | Protocol Guard, CORTEX Freshness, Emotions | All built, interface gaps between D1/D2/D3 |

### Interface Gaps Between Phase 195 Subsystems (R5)
- **D1↔D3:** Protocol Guard violations don't feed Caution emotion
- **D2↔D3:** Tool freshness updates don't boost Curiosity emotion
- **`score()` vs `recommend()`:** Emotion modifier only in `recommend()`, single-tool scoring bypasses it
- **Verifier path:** `record_outcome()` doesn't update Trust emotion

### ELYSIA vs ELISYA (R6)
- **ELYSIA** = dead Weaviate wrapper (`src/orchestration/elysia_tools.py`), 0 callers → DELETE
- **ELISYA** = active core runtime (`src/elisya/`, 20+ files, 78 imports), LLM routing + context middleware
- Origin: Phase 44, 3am mishap, documented in `docs/73_ph/THE_LEGENDARY_ELISYA_MISHAP.md`

### Task Board Audit (R7)
- **1 pending task still relevant:** `tb_1773881085_3` (Memory health dashboard)
- **1 stuck done_worktree:** `tb_1773881085_2` (ENGRAM L1 injection) → advance to done_main
- **2 noise tasks to close:** `tb_1774332804_2`, `tb_1774324620_2`
- **0 Phase 198 implementation tasks exist yet** — need creation from roadmap

### Key Reference Documents (R8, expanded)
| Doc | Phase | Content |
|-----|-------|---------|
| `docs/besedii_google_drive_docs/VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md` | — | Canonical glossary (weights STALE) |
| `docs/186_memory/VETKA_COGNITIVE_STACK_ARCHITECTURE.md` | 186 | Two-axis model, processing chain |
| `docs/186_memory/GROK_RESEARCH_ANSWERS.md` | 186 | Grok parameter decisions (weights, ENGRAM key, decay) |
| `docs/unpluged_search/PH99_STM_MGC_Memory_Architecture.md` | 99 | Original STM/MGC/MemoryProxy design |
| `docs/172_vetka_tools/REFLEX_ARCHITECTURE_BLUEPRINT_2026-03-10.md` | 172 | REFLEX 3-layer + 6 injection points |
| `docs/192_task_SQLite/RECON_FEEDBACK_MEMORY_MATRIX.md` | 192 | Debrief→memory routing matrix |
| `docs/192_task_SQLite/HANDOFF_ZETA_F4_MEMORY_WIRING.md` | 192 | API for all 5 subsystem writes |
| `docs/195_CORTEX_FRESHNESS/ARCHITECTURE_195_TOOL_FRESHNESS.md` | 195 | Epoch-based decay + CAM boost |
| `docs/195_REFLEX_EMOTIONS/ARCHITECTURE_195_REFLEX_EMOTIONS.md` | 195 | Emotions modulator (D1/D2 wiring pending) |
| `docs/157_ph/MARKER_157_ADAPTIVE_CONTEXT_AND_JEPA_RECON_2026-03-01.md` | 157 | JEPA 3-level LOD plan |
| `docs/73_ph/THE_LEGENDARY_ELISYA_MISHAP.md` | 73 | ELYSIA/ELISYA origin story |

### Known Doc Conflicts
- Canonical glossary REFLEX weights (0.30/0.15/0.15) ≠ Grok-updated (0.22/0.18/0.18) ≠ code
- Glossary says ENGRAM "not yet implemented" — it exists but L2→L1 missing
- `user_preference_store.py` rename (Phase 186) never completed
