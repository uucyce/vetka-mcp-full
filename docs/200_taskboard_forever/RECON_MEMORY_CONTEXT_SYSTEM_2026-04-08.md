# RECON: Memory & Context System Audit — Compression, Retrieval, Format

**Date:** 2026-04-08  
**Task ID:** `tb_1775676757_9601_1`  
**Domain:** harness (memory + context)  
**Phase:** 210  
**Audit Scope:** Hardcodes, ELISION, STM, Qdrant, Memory Format

---

## Executive Summary

The VETKA memory system has **three interconnected problems**:

1. **Compression & Budget (ELISION)** — Hardcoded values + misunderstood compression
2. **Retrieval System (STM + Qdrant RAG)** — STM cold, no dynamic filtering
3. **Memory Format** — Unstructured text, no Q1-Q6 template

**Root cause:** System components work independently, not as a pipeline. Result: agents get whole memories dumped into context instead of relevant fragments.

---

## Part 1: Hardcodes & Compression (ELISION Misconception)

### Issue 1.1: Hardcoded 800-char Cap

**Location:** `src/memory/role_memory_writer.py:181`

```python
"raw": ("## [" + raw)[:800],  # cap at 800 chars for token budget
```

**Problems:**
- Magic number 800 — no relation to actual token budget
- Unrelated to adaptive budget system (haiku 2000 vs opus 4000)
- Same cap for all agents regardless of model tier
- Comment claims "token budget" but this is character truncation

**Current behavior:**
- Load recent N memories
- Each entry capped at 800 chars
- Injected as-is into context

**Better approach:**
```python
# Calculate dynamic cap based on remaining budget
max_chars = remaining_tokens * 4  # rough char-to-token ratio
"raw": ("## [" + raw)[:max_chars]
```

### Issue 1.2: Misunderstanding ELISION

**What it is:** SAM-based **compression** (frequent words → short symbols with legend)  
**What it's NOT:** Section dropper

**Evidence:** Session init output shows ELISION legend:
```json
"legend": {
  "task_board_summary": "tbs",
  "engram_learnings": "el",
  "protocol_status": "ps"
}
```

This is **NOT** dropping sections — it's **abbreviating** them.

**The real token budget enforcement:** `_apply_token_budget()` in `session_tools.py:90`

This function:
1. Estimates tokens for each section (line 85: `len(json.dumps) // 4`)
2. Progressively drops T4 → T3 → T2 sections if over budget
3. NEVER drops T1 (core identity)

**Misconception:** ELISION was thought to be section-dropper. It's NOT. Section drops happen in `_apply_token_budget()` with tier-based logic.

### Issue 1.3: Adaptive Budget System Partially Works

**Mechanism:** `session_tools.py:409-425`

```python
# Get model tier from agent registry
role_tier = agent_registry.get(role).model_tier  # e.g., "haiku"
max_tokens = {
    "haiku": 2000,
    "sonnet": 4000,  
    "opus": 8000
}[role_tier]
```

**Why it sometimes fails:**
- Requires `role=<callsign>` passed to `session_init`
- If missing → defaults to 4000 (middle value)
- Delta reported 93% usage with role=Delta → means she got 2000, not 8000

**Real issue:** Not all agents pass `role` parameter correctly

---

## Part 2: Memory Retrieval System (STM + Qdrant)

### Issue 2.1: STM is Cold (0 items)

**From session_init output:**
```json
"stm": {
  "items": 0,
  "status": "cold"
}
```

**What STM should be:** Short-term memory buffer for current session items

**Why it's cold:**
- No mechanism to populate it at session start
- No TTL-based eviction (would empty on session close)
- Currently unused in context injection pipeline

### Issue 2.2: role_memory → Qdrant Pipeline Unclear

**Write side exists:**
- `role_memory_writer.append_entry()` writes to `memory/roles/{callsign}/MEMORY.md`
- Called by `smart_debrief.process_smart_debrief()` after task complete

**Read side exists:**
- `load_recent()` in `role_memory_writer.py:154` loads last N entries
- Injected as `role_memory` field in session context (session_tools.py:1720)

**MISSING:** Pipeline ENGRAM L1 → Qdrant L2

Currently:
1. ✅ role_memory written to disk (MEMORY.md)
2. ❌ Not indexed in Qdrant for semantic search
3. ✅ Manually loaded via `load_recent()` (crude "last N")
4. ❌ No relevance filtering — dumps whole memories

**The gap:** Should be
```
role_memory → ENGRAM L1 (cache) → Qdrant L2 (semantic index)
                                         ↓
                              At session_init:
                              Query Qdrant for relevant entries only
                              (not "last 3 blind")
```

### Issue 2.3: Hardcoded last_n=3 in session_tools.py

**Location:** `src/mcp/tools/session_tools.py:1720`

```python
_role_entries = load_recent(_resolved_role, last_n=3)
```

**Problem:**
- Always loads last 3 entries regardless of context
- Doesn't account for token budget
- Doesn't account for relevance

**Should be:**
```python
# Dynamic N based on remaining budget
remaining = max_tokens - current_usage
max_entries = max(1, remaining // 200)  # ~200 tokens per entry

# Then Qdrant-filter by relevance if pipeline exists
_role_entries = query_qdrant_for_role(
    _resolved_role,
    query=task_context,  # filter by what agent is working on
    limit=max_entries
)
```

---

## Part 3: Memory Format (Q1-Q6 Template)

### Current Format: Unstructured Markdown

**Example from role_memory_writer.py:180-181**

```python
task_id = header[:bracket_end].strip()
title = header[bracket_end + 1:].strip()
entries.append({
    "task_id": task_id,
    "title": title,
    "raw": ("## [" + raw)[:800],  # raw markdown blob
})
```

**Problems:**
- Free-form markdown text (good for humans, bad for indexing)
- No structured fields for Q1/Q2/Q3/Q4/Q5/Q6
- Qdrant vectorization sees it as generic text, not agent experience

### Proposed Format: Karpathy-style Program.md

**New standard for memory entries:**

```markdown
## [tb_1775672689_6783_1] Implement Pre-commit Hook Guardrail

Role: Wu | Project: harness | Date: 2026-04-08 | Duration: 2h 15m

### Q1 (What broke?)
None — existing pre-commit hook infrastructure was solid.

### Q2 (What unexpectedly worked?)
Pre-commit hook pattern from digest update provided perfect foundation.
Role extraction from branch name (sed regex) was simple and reliable.

### Q3 (What idea came to mind?)
Could add --no-verify audit logging to catch emergency bypasses.
Also potential for task_board metrics dashboard showing compliance rate by agent.

### Q4 (What's left for next session?)
Phase 2 (MCP guard) and Phase 3 (soft guard + metrics) ready for Eta.
Eta already has task created (tb_1775672696_6783_1).

### Q5 (Hot files for next session)
- .git/hooks/pre-commit
- src/orchestration/task_board.py
- scripts/check_task_board_compliance.py

### Q6 (What's happening in the project?)
WAKE-LITE-2 cycle: building task board guardrail system to enforce agent discipline.
One agent tried to bypass it with raw git — guardrail caught it. System working.
```

**Advantages:**
- **Structured fields** → Qdrant vectorizes Q1, Q2, Q3, Q4, Q5 separately
- **Q4 handoff** → Next session knows what's pending
- **Q5 hot files** → Easier to pre-load context
- **Q6 summary** → Project-level digest (like Karpathy's program.md)
- **Metadata** → Role, project, date, duration for filtering

**For Qdrant:**
```json
{
  "task_id": "tb_1775672689_6783_1",
  "role": "Wu",
  "project": "harness",
  "date": "2026-04-08",
  "q1_bugs": "None — existing pre-commit hook infrastructure was solid.",
  "q2_worked": "Pre-commit hook pattern from digest update provided perfect foundation...",
  "q3_idea": "Could add --no-verify audit logging...",
  "q4_handoff": "Phase 2 (MCP guard) and Phase 3 (soft guard + metrics) ready for Eta...",
  "q5_hot_files": ["git/hooks/pre-commit", "src/orchestration/task_board.py"],
  "q6_context": "WAKE-LITE-2 cycle: building task board guardrail system...",
  "vector_q2": [...embeddings...],  # separate vectors for each field
  "vector_q3": [...]
}
```

---

## Part 4: System Integration Issues

### Current State (Broken Pipeline)

```
task_complete
    ↓
smart_debrief.process()  ← Q1/Q2/Q3 collected
    ↓
role_memory_writer.append_entry()  ← written to disk (MEMORY.md)
    ↓
memory/roles/Wu/MEMORY.md  ← stored
    ↓
[DEAD END — no Qdrant indexing]
    ↓
next session: session_init
    ↓
load_recent(Wu, last_n=3)  ← crude "last 3 blind"
    ↓
role_memory field in context  ← dumped in as-is (800 char cap)
    ↓
agent receives unfiltered memories
```

### Desired State (Complete Pipeline)

```
task_complete
    ↓
smart_debrief.process()  ← Q1-Q6 collected with structured format
    ↓
role_memory_writer.append_entry()  ← formatted entry
    ↓
memory/roles/Wu/MEMORY.md  ← stored
    ↓
ENGRAM L1 watch  ← promotes to L1 if hit_count >= 3
    ↓
Qdrant L2 index  ← vectorizes and indexes Q1-Q6 separately
    ↓
next session: session_init
    ↓
query_qdrant_for_role(
    role=Wu,
    query=<current task context>,
    limit=<dynamic based on budget>
)  ← semantic filtering
    ↓
role_memory field in context  ← only relevant entries
    ↓
agent receives filtered, contextual memories
```

---

## Part 5: Issues Inventory

| # | System | Problem | File | Line | Severity |
|---|--------|---------|------|------|----------|
| 1 | Hardcodes | 800-char magic number | role_memory_writer.py | 181 | Medium |
| 2 | Hardcodes | last_n=3 hardcoded | session_tools.py | 1720 | Medium |
| 3 | Budget | Adaptive budget not always used | session_tools.py | 409 | Low |
| 4 | ELISION | Misconception about what it does | — | — | Low |
| 5 | STM | Cold/unused (0 items) | session_init | — | High |
| 6 | Qdrant | role_memory not indexed | (missing) | — | High |
| 7 | Format | Unstructured markdown | role_memory_writer.py | 180-181 | High |
| 8 | Filtering | "last N blind" vs relevance | load_recent() | 184 | High |

---

## Part 6: Implementation Strategy

### Phase 1: Fix Hardcodes & Adaptive Budget
- Replace 800-char hardcode with dynamic calculation
- Replace last_n=3 with token-budget-aware limit
- Ensure all agents pass `role=` to session_init
- **Time:** 2h | **Files:** 2 | **Risk:** Low

### Phase 2: Implement STM + Qdrant Pipeline
- Activate STM (populate at session_init, expire at session_close)
- Wire role_memory → Qdrant indexing (after append_entry)
- Implement `query_qdrant_for_role()` function
- Replace `load_recent()` with semantic filtering
- **Time:** 4h | **Files:** 4-5 | **Risk:** Medium

### Phase 3: Memory Format Migration
- Define Q1-Q6 template + validation
- Update role_memory_writer to output structured format
- Update Qdrant schema for per-field vectors
- Migrate existing MEMORY.md entries (script)
- Update CLAUDE.md generation to reference Q4/Q5/Q6
- **Time:** 3h | **Files:** 3-4 | **Risk:** Medium

### Phase 4: Testing & Metrics
- Unit tests for load_recent → query_qdrant migration
- Integration tests for memory injection in session_init
- Metrics: memory retrieval latency, relevance score, agent feedback
- **Time:** 2h | **Files:** 2 | **Risk:** Low

---

## Part 7: Questions Needing Clarification

**Q1:** Should last_n default be adaptive (compute from budget) or explicit parameter?  
**Q2:** Who owns Qdrant indexing — role_memory_writer or separate ingest service?  
**Q3:** Should Q4/Q5/Q6 be injected into CLAUDE.md or separate "next steps" section?  
**Q4:** What's the TTL for role memories in Qdrant (30 days? 90 days)?  
**Q5:** Should STM (short-term) be per-session or per-agent-per-day?  

---

## Part 8: Success Metrics

After implementation, measure:

1. **Compression efficiency:**
   - Avg role_memory tokens before/after (target: 50% reduction)
   - % of entries actually used in decisions vs dumped

2. **Retrieval quality:**
   - Qdrant relevance score distribution (target: mean > 0.7)
   - Agent feedback on "remembered correctly" (survey)

3. **System health:**
   - Qdrant query latency (target: <100ms)
   - Memory ingestion lag (target: <5s after task_complete)
   - STM cache hit rate (target: >60%)

4. **Agent adoption:**
   - % agents with role_memory in CLAUDE.md (target: 100%)
   - % sessions using Qdrant filtering vs blind last_n (target: 100%)

---

## Conclusion

The VETKA memory system has solid infrastructure (ENGRAM, Qdrant, role_memory_writer) but **three broken connection points:**

1. **Hardcoded values** instead of adaptive calculations
2. **STM unused** and **Qdrant not wired** to role_memory
3. **No structured format** for efficient indexing & retrieval

Fixing these would transform memory from "dump everything" to "retrieve only relevant entries." Estimated 11 hours total implementation.

**Next action:** Break into three separate IMPL tasks (Phases 1-3).

---

## Appendix: ELISION Explanation

**ELISION = Selective Abbreviation + Expansion Legend**

Example:
```json
{
  "task_board_summary": "tbs",
  "engram_learnings": "el",
  "protocol_status": "ps",
  
  "context": {
    "tbs": {...large task board data...},
    "el": {...large engram learnings...},
    "ps": {...protocol status...}
  },
  
  "legend": {
    "tbs": "task_board_summary",
    "el": "engram_learnings",
    "ps": "protocol_status"
  }
}
```

When LLM sees abbreviations, it can expand using legend: `tbs → task_board_summary`

This saves ~40-60% tokens because long keys are replaced with 2-3 char abbreviations.

**Does NOT drop sections.** Section dropping is handled separately by `_apply_token_budget()` with tier logic.
