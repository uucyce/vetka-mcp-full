# RECON: Debrief Feedback → Memory Subsystems Matrix
**Task:** `tb_1774236111_10`
**Date:** 2026-03-23
**Author:** Opus (Zeta)
**Status:** RECON COMPLETE

---

## Full Data Flow

```
Agent completes task
  → action=complete response includes debrief_requested=true (MARKER_195.21)
  → Agent answers Q1/Q2/Q3
  → Agent calls submit_experience_report(lessons_learned=[...], recommendations=[...])
  → ExperienceReportStore.submit()
    → saves JSON to data/experience_reports/<session>.json
    → calls process_smart_debrief(report)
      → _create_auto_tasks(): Q1 bugs → [DEBRIEF-BUG], Q3 ideas → [DEBRIEF-IDEA]
      → _route_to_memory(): regex triggers → subsystem API calls
```

---

## Trigger → Subsystem → API Matrix

| Trigger | Regex | Subsystem | API Call | Params | Storage | TTL |
|---------|-------|-----------|----------|--------|---------|-----|
| Tool mention (negative) | `/vetka_\w+\|Read\|Edit\|Grep\|Bash\|Write/` + `_BUG_PATTERNS` | **REFLEX/CORTEX** | `get_reflex_feedback().record()` | `tool_id=<match>`, `success=False`, `useful=False`, `agent_role="debrief"`, `extra.text[:200]` | `data/reflex/feedback_log.jsonl` | Exponential decay (0.1/day) |
| Tool mention (positive) | Same tool regex, NO bug pattern | **REFLEX/CORTEX** | `get_reflex_feedback().record()` | `tool_id=<match>`, `success=True`, `useful=True`, `agent_role="debrief"` | Same JSONL | Same decay |
| User/UX mention + UI keyword | `/user\|пользовател\|юзер/i` + `/UI\|UX\|viewport\|panel\|layout/i` | **AURA** | `get_aura_store().set_preference()` | `category="viewport_patterns"`, `key="debrief_ux_insight"`, `value[:500]`, `confidence=0.3` | RAM (Gen0) + Qdrant (Gen1) | Category decay (0.01-0.05/week) |
| User mention (no UI) | `/user\|пользовател\|юзер/i` only | **AURA** | Same | `category="communication_style"`, same params | Same | Same |
| File path mention | `/[\w./]+\.(py\|ts\|tsx\|js\|yaml\|json\|md\|css\|html)/` | **MGC** | `get_mgc_cache().set_sync()` | `key="debrief_hot:<path>"`, `value={source, text[:200], agent}`, `size_bytes=0` | RAM Gen0 (LRU, max ~1000) | Evict on LRU, promote at access_count≥3 |
| Principle/rule | `/always\|never\|принцип\|principle\|rule\|правил/i` | **ENGRAM** | `get_engram_cache().put()` | `key="<agent>::debrief::learning::<domain>"`, `value[:300]`, `category="architecture"`, `match_count=0` | `data/engram_cache.json` (max 200) | **Permanent** (TTL=0) |
| Pattern/learning | `/паттерн\|pattern\|эффективн\|стандарт\|recommend/i` (no principle) | **ENGRAM** | Same | Same key, `category="pattern"` | Same | **60 days** |
| No triggers matched | Fallback | **CORTEX** | `get_reflex_feedback().record()` | `tool_id="__general_debrief__"`, `success=True`, `useful=True` | Same JSONL | Same decay |

---

## Cross-Subsystem Interactions

### One debrief answer → multiple subsystems

Example: `"vetka_read_file in task_board.py — пользователь should always use Read pattern"`

Triggers ALL FOUR:
1. **REFLEX** → `record(tool_id="vetka_read_file")` + `record(tool_id="Read")`
2. **AURA** → `set_preference(category="communication_style", value=...)`
3. **MGC** → `set_sync(key="debrief_hot:task_board.py")`
4. **ENGRAM** → `put(category="architecture", key="...::debrief::learning::...")`  (because "always")

**Race conditions?** NO — all calls are synchronous, sequential in `_route_to_memory()`. Each in its own try/except. One crash doesn't affect others.

### Feedback loop: CORTEX → REFLEX → next session

```
Session N:
  Agent says "vetka_edit_file сломан"
  → CORTEX records: tool=vetka_edit_file, success=False, useful=False

Session N+1:
  REFLEX scorer reads CORTEX feedback_log.jsonl
  → Signal 3 (feedback score): vetka_edit_file gets lower score
  → Signal weight: 0.18
  → REFLEX recommends alternative tools higher
  → session_init reflex_recommendations shows vetka_edit_file lower

EFFECT: Negative debrief feedback → tool drops in REFLEX rankings → agents see alternatives first
```

### ENGRAM → REFLEX Guard

```
Session N:
  Agent says "never use vetka_edit_file for large files"
  → ENGRAM stores: category="architecture" (permanent)

Session N+1:
  REFLEX Guard checks ENGRAM L1 danger/architecture entries
  → If agent tries vetka_edit_file on large file → Guard warning
  → reflex_guard.py:258-259 checks ENGRAM for guard warnings

EFFECT: Permanent learning from debrief → hard guard in future sessions
```

### AURA → session_init context

```
Session N:
  Agent says "пользователь предпочитает русский в ответах"
  → AURA stores: category=communication_style, confidence=0.3

Session N+1:
  session_init → user_preferences → communication_style
  → prefers_russian may be influenced (if confidence accumulates)
  → LLM call context enriched with preference

EFFECT: UX insight from debrief → context enrichment for future agents
```

### MGC → file heat → REFLEX scorer

```
Session N:
  Agent mentions "task_board.py:847 has a bug"
  → MGC: set_sync(key="debrief_hot:task_board.py")

Session N+1:
  REFLEX scorer signal 8 (MGC cache heat): weight 0.03
  → Tools related to task_board.py get small boost
  → Minimal effect (0.03 weight) but contributes to signal mix

EFFECT: File mention → MGC heat → marginal REFLEX signal
```

---

## ELISION: Compression Needed?

**Answer: NO.**

- Debrief texts are already truncated: REFLEX=200, ENGRAM=300, AURA=500 chars
- ELISION is for LLM prompt injection (compressing large context for token efficiency)
- Debrief routing is regex-based, no LLM calls, no token budget
- ELISION would add complexity with zero benefit here

**Exception:** If debrief answers were used in session_init context (AURA spiral context), ELISION would apply there — but that's AURA's responsibility, not debrief routing.

---

## Current Implementation Status

| Subsystem | API exists? | Called from debrief? | F4 wired? |
|-----------|------------|---------------------|-----------|
| REFLEX/CORTEX | `record()` ✓ | Regex detects ✓ | **NO — logs only** |
| AURA | `set_preference()` ✓ | Regex detects ✓ | **NO — logs only** |
| MGC | `set_sync()` ✓ | Regex detects ✓ | **NO — logs only** |
| ENGRAM | `put()` ✓ | Regex detects ✓ | **NO — logs only** |
| CORTEX fallback | `record()` ✓ | Fallback logic ✓ | **NO — logs only** |

**All 5 subsystem APIs exist and are battle-tested by other callers.** The ONLY missing piece is F4: replacing log-only `_route_to_memory()` with the wired version from `HANDOFF_ZETA_F4_MEMORY_WIRING.md`.

---

## Dependency Chain

```
tb_1774235503_9  ✅ Smart debrief fires on all complete paths (DONE)
       ↓
tb_1774161488_20 ⏳ F4: Wire _route_to_memory() to real APIs (PENDING)
       ↓
AUTOMATIC: debrief answers flow to CORTEX/ENGRAM/AURA/MGC
       ↓
AUTOMATIC: REFLEX scorer reads CORTEX → affects next session recommendations
AUTOMATIC: REFLEX Guard reads ENGRAM → blocks dangerous patterns
AUTOMATIC: session_init reads AURA → enriches agent context
```

**One task remains:** `tb_1774161488_20` (F4 memory wiring). Handoff is complete with ready code + 13 tests. After that, the full loop is live.

---

*"The memory is the pipeline. The pipeline is the memory."*
