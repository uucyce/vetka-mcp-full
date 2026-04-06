# RECON: Role Memory Architecture
**Author:** Eta (claude-sonnet-4-6) | **Date:** 2026-04-03 | **Task:** tb_1775217408_19779_1
**Baseline:** `.claude/worktrees/magical-burnell/MEMORY.md` (Captain Burnell, Phase 202)

---

## 1. Baseline: Burnell's MEMORY.md

Captain Burnell created a MEMORY.md for his worktree — experiential memory, not instructions.
Structure:
```
# Role Memory
## Session N: Title (date, duration)
### What I Saw — raw observations
### What I Learned — patterns extracted
### What Surprised Me — unexpected discoveries
### Unfinished Business — threads to pick up
### People — who I worked with, their traits
### Emotional Snapshots — the human moments
## How To Wake Me Up — launch instructions
```

This is the **proof of concept**. Manual, human-authored, rich narrative.
The gap: no other agent role has this. Each session starts blank.

---

## 2. Current Memory Infrastructure (what exists)

### 2.1 ENGRAM L1 (engram_cache.py)
- O(1) deterministic dict-based cache, max 200 entries
- Key format: `agent_type::filename::action_type::phase_type`
- smart_debrief.py DOES write to ENGRAM with callsign prefix:
  - `{callsign}::debrief::learning::{domain}` — pattern/principle mentions
  - `{callsign}::debrief::ux_insight::{domain}` — UX mentions
- Auto-promoted from Qdrant L2 at match_count >= 3
- **Partial role memory via key prefix** — but limited to regex-triggered entries

### 2.2 smart_debrief.py — Where Q1-Q3 Goes Today
```
Q1 (bugs/lessons_learned):
  → if bug pattern → [DEBRIEF-BUG] task (P3, source=smart_debrief)
  → if pattern/principle → ENGRAM L1 (callsign::debrief::learning)
  → if tool mention → CORTEX reflex_feedback
  → if file mention → MGC hot file marker

Q2 (what worked / successes):
  → report.successes field → only CORTEX fallback if no pattern matches
  → NOT explicitly routed to role memory (gap!)

Q3 (ideas / recommendations):
  → [DEBRIEF-IDEA] task (P4, source=smart_debrief)
  → NO routing to role memory
```

**Critical gap:** Q1-Q3 data reaches task board and ENGRAM (partially) but NEVER
comes back to the same agent in future sessions. The loop is broken at the read side.

### 2.3 Feedback Bridge (tb_1774591903_1 — done_main, MARKER_200.FEEDBACK_BRIDGE)
- Scans `~/.claude/projects/.../memory/feedback_*.md` at session_init
- Converts to ENGRAM L1 danger entries (key: `feedback::{name}`)
- Per-role ENGRAM filtering via `_matches_role()` already implemented
- **What this covers:** user-authored feedback files → ENGRAM (read side works)
- **What it doesn't cover:** auto-generated role experience (write side missing)

### 2.4 Per-Role Claude Code Memory (proposed, not built)
- `memory/roles/{callsign}/` structure PROPOSED in ENGRAM design
- `generate_claude_md.py` does NOT yet point CLAUDE.md to role-specific dir
- IDEA task `tb_1774617580_57121_2` still pending (P4)

### 2.5 AURA
- User preference learning only — zoom_levels, formality, model tier
- NOT designed for agent experiences
- Schema is attribute-fixed: "debrief_ux_insight" doesn't fit → routed to ENGRAM instead

### 2.6 Sherpa Feedback JSONL (data/reflex/feedback_log.jsonl)
- Auto-collecting per-service: success/fail/chars/time per call
- Already sorted and rated by Qwen for service selection
- **Pattern to replicate:** auto-collect → score → inject next session
- For agents: auto-collect Q1-Q3 → role MEMORY.md → session_init injects

### 2.7 Predecessor Idea Tracker (tb_1774423047_1)
- Closed as `already_implemented` — but actual status unclear
- Design: extract `{callsign}::debrief::idea::*` from ENGRAM, check if implemented
- Would surface "Delta proposed test pyramid 3 sessions ago, still not done"

---

## 3. The Gap: Broken Feedback Loop

```
TODAY:
task_complete(q1, q2, q3)
  → smart_debrief → ENGRAM L1 (partial write)
  → task board → [DEBRIEF-BUG] / [DEBRIEF-IDEA] tasks
  → session_init → injects ENGRAM top entries (NOT filtered per session)
  ✗ NO: "here's what YOU, Eta, learned in your last 5 tasks"
  ✗ NO: per-role narrative memory file
  ✗ NO: "your unfinished business from last session"

NEEDED:
task_complete(q1, q2, q3)
  → smart_debrief → ENGRAM L1 (as today)
  → NEW: role_memory_writer.append(callsign, task_id, q1, q2, q3)
    → appends to memory/roles/{callsign}/MEMORY.md
  → session_init reads memory/roles/{callsign}/MEMORY.md
    → injects last 3-5 sessions as role_memory[] block
  ✓ Agent sees: "last session you were working on Sherpa DOM, learned X, left Y unfinished"
```

---

## 4. Minimal Pipeline Design

### 4.1 Write Side: role_memory_writer.py (new file)
```python
# src/memory/role_memory_writer.py

def append_session_entry(callsign: str, task_id: str, task_title: str,
                          q1: str, q2: str, q3: str, domain: str):
    """Append one task completion to role MEMORY.md."""
    path = PROJECT_ROOT / "memory" / "roles" / callsign / "MEMORY.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    entry = f"""
## [{task_id}] {task_title} ({datetime.now().strftime('%Y-%m-%d')})
**Domain:** {domain}

### What I Learned (Q1)
{q1 or '(none)'}

### What Worked (Q2)
{q2 or '(none)'}

### What I'd Do Next (Q3)
{q3 or '(none)'}

---
"""
    with open(path, "a") as f:
        f.write(entry)
```

**Integration point:** `smart_debrief.process_smart_debrief(report)` — add call after
existing ENGRAM write. Zero-risk: isolated write, non-blocking.

### 4.2 Read Side: session_init injection
```python
# In session_tools.py SessionInitTool._execute_async():

role_memory = load_role_memory(callsign, last_n=3)  # last 3 task completions
result["role_memory"] = role_memory  # inject into session_init response
```

Format in session_init response:
```json
"role_memory": {
  "last_sessions": [
    {"task_id": "tb_xxx", "date": "2026-04-02", "learned": "...", "worked": "...", "next": "..."},
    ...
  ],
  "unfinished": ["thread1", "thread2"],
  "file_path": "memory/roles/Eta/MEMORY.md"
}
```

### 4.3 CLAUDE.md Integration
`generate_claude_md.py` adds to each role's CLAUDE.md:
```markdown
## Role Memory
Your experiential memory: `memory/roles/Eta/MEMORY.md`
Read it at session start. Your last sessions, patterns, unfinished work.
```

---

## 5. Existing Tasks Found (search_fts results)

| Task ID | Title | Status |
|---------|-------|--------|
| `tb_1774591903_1` | REFLEX Feedback Bridge — ENGRAM L1 + per-role partitioning | **done_main** |
| `tb_1774617580_57121_2` | [DEBRIEF-IDEA] Per-role memory subdirectories via role_memory_path | pending P4 |
| `tb_1774423047_1` | Predecessor Idea Tracker — surface unimplemented ideas same role | done (already_impl?) |
| `tb_1774251392_1` | Inject ENGRAM/MGC L2 memory into session_init | pending |
| `tb_1774424683_1` | Cross-role ENGRAM search | pending |
| `tb_1774244568_5` | Full audit worktree CLAUDE.md generation — role identity + memory | pending |

**Key finding:** Foundation exists (Feedback Bridge done), per-role subdirectories proposed
but never built, and the write-side (auto-populate MEMORY.md from Q1-Q3) is missing entirely.

---

## 6. Sherpa JSONL → Agent Memory Parallel

Sherpa feedback JSONL is the exact pattern to replicate:

```
Sherpa pattern:
  service_call(url, prompt) → feedback_log.jsonl → Qwen scores → picks best service

Agent memory pattern (to build):
  task_complete(q1, q2, q3) → memory/roles/{callsign}/MEMORY.md → session_init injects
```

Both are: **auto-collect → structured store → inject into next decision**.
The JSONL is already proven. The agent memory is the same architecture, different data.

---

## 7. Guard/Reflex Integration

Auto-trigger memory save at session end:
- **Option A:** Hook into `action=complete` in task_board.py — already has q1/q2/q3 fields
- **Option B:** Post-hook in MCP bridge (vetka_mcp_bridge.py) on session end signal
- **Recommended:** Option A — task_board.py already has the debrief data. Add
  `_trigger_role_memory_write(task)` call inside `_complete_task()` after smart_debrief.

REFLEX can surface "memory file updated" as a signal — low priority, no blocking needed.

---

## 8. Recommendations

### P0 — Build (Phase 203)
1. `src/memory/role_memory_writer.py` — write side (~50 lines)
2. Wire into `smart_debrief.process_smart_debrief()` — 3 lines
3. Wire read into `session_tools.py` session_init — inject `role_memory` field

### P1 — Enhance
4. `generate_claude_md.py` — add Role Memory section pointing to `memory/roles/{callsign}/MEMORY.md`
5. Per-role subdirectories in Claude Code memory: `memory/roles/{callsign}/` (tb_1774617580)

### P2 — Optional
6. Manual MEMORY.md override: agent can write narrative sections (Burnell-style) that persist
7. ELISION compression for role_memory injection (last 3 sessions → ~500 tokens)

---

## 9. Conclusion

**What exists:** ENGRAM L1 with callsign-prefix keys (partial write from debrief),
Feedback Bridge (user feedback → ENGRAM), task board debrief pipeline.

**What's missing:** The write-side for auto-populating role MEMORY.md from Q1-Q3 (~50 lines),
and the read-side injection in session_init (~20 lines). Total effort: ~70 lines + 1 new file.

**Burnell's MEMORY.md is the proof of concept.** Manual, rich, narrative.
The automated version doesn't need to be as human — it needs to be consistent and injected.

**Next steps:** Create ARCH_DOC task + ROADMAP task (see follow-up tasks created below).
