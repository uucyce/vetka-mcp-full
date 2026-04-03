# ARCHITECTURE: Role Memory System — Phase 203
**Author:** Eta (Harness Engineer 2) | **Date:** 2026-04-03
**Status:** DRAFT — pending Commander review
**Task:** tb_1775220482_23491_1 (ARCH_DOC)
**Recon:** docs/202ph_SHERPA/RECON_ROLE_MEMORY.md
**Baseline:** .claude/worktrees/magical-burnell/MEMORY.md

---

## 0. Problem Statement

Every VETKA agent session starts blank. The system has rich memory infrastructure
(ENGRAM, MGC, AURA, Qdrant, CORTEX) but none of it answers the question:

> "What did YOU, Eta, learn in your last 3 sessions? What did you leave unfinished?"

Q1-Q3 debrief data is collected at `task_complete` but never fed back to the same agent.
The feedback loop is broken at the **read side**. Burnell's manual `MEMORY.md` proved
the concept — now we automate it.

---

## 1. Design Principles

1. **Same pattern as Sherpa JSONL** — auto-collect → structured store → inject next session
2. **Non-blocking write** — memory write never delays task completion
3. **Token-budgeted inject** — ELISION keeps role_memory < 500 tokens
4. **Manual override friendly** — agent can hand-write narrative sections (Burnell-style)
5. **Zero new dependencies** — pathlib + json, no new packages
6. **Rollout by pilot** — Eta + Zeta first, then all roles

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  WRITE SIDE (at task_complete)                                  │
│                                                                  │
│  task_board action=complete                                      │
│    → srco/task_board.py _complete_task()                        │
│    → smart_debrief.process_smart_debrief(report)               │
│       → [existing] ENGRAM L1 write                             │
│       → [existing] CORTEX feedback                             │
│       → [NEW] role_memory_writer.append_entry(callsign, ...)   │
│                → memory/roles/{callsign}/MEMORY.md             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  STORE                                                           │
│                                                                  │
│  memory/roles/                                                   │
│    Eta/MEMORY.md       ← append-only, markdown                  │
│    Zeta/MEMORY.md                                               │
│    Alpha/MEMORY.md                                              │
│    ... (one per callsign)                                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  READ SIDE (at session_init)                                    │
│                                                                  │
│  vetka_session_init role=Eta                                     │
│    → session_tools.py _execute_async()                          │
│       → [existing] ENGRAM inject                               │
│       → [NEW] load_role_memory(callsign, last_n=3)             │
│                → result["role_memory"] = {...}                  │
│       → _apply_token_budget() — T2, kept unless over budget    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  CLAUDE.md (at generate_claude_md)                              │
│                                                                  │
│  generate_claude_md.py --all                                    │
│    → claude_md_template.j2                                      │
│       → [NEW] ## Role Memory section                           │
│                → "Your memory: memory/roles/{callsign}/..."    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Write Side: role_memory_writer.py

**File:** `src/memory/role_memory_writer.py` (new, ~60 lines)

```python
"""
Role Memory Writer — auto-populate per-role MEMORY.md from task debrief.
Called by smart_debrief.process_smart_debrief() after each task completion.

Pattern: same as Sherpa feedback_log.jsonl but for agent experiences.
"""
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ROLES_MEMORY_DIR = PROJECT_ROOT / "memory" / "roles"
MAX_ENTRIES_PER_ROLE = 50  # keep last 50 entries per role


def append_entry(
    callsign: str,
    task_id: str,
    task_title: str,
    q1: Optional[str],
    q2: Optional[str],
    q3: Optional[str],
    domain: str = "",
    hot_files: list[str] | None = None,
) -> bool:
    """Append one task completion to role MEMORY.md. Non-blocking, never raises."""
    try:
        role_dir = ROLES_MEMORY_DIR / callsign
        role_dir.mkdir(parents=True, exist_ok=True)
        memory_path = role_dir / "MEMORY.md"

        date_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        files_str = (
            "\n".join(f"  - {f}" for f in (hot_files or [])[:5])
            or "  (none)"
        )

        entry = f"""
## [{task_id}] {task_title}
**Date:** {date_str} | **Domain:** {domain or 'general'}

### What I Learned (Q1)
{q1.strip() if q1 else '(not recorded)'}

### What Worked (Q2)
{q2.strip() if q2 else '(not recorded)'}

### What I'd Do Next (Q3)
{q3.strip() if q3 else '(not recorded)'}

### Hot Files This Session
{files_str}

---
"""
        with open(memory_path, "a", encoding="utf-8") as f:
            # Write header if file is new
            if memory_path.stat().st_size == 0:
                f.write(f"# Role Memory — {callsign}\n")
                f.write("# Auto-generated by role_memory_writer.py\n")
                f.write("# Entries append at task_complete. Do not delete.\n\n")
            f.write(entry)

        logger.info("[RoleMemory] Appended entry for %s: %s", callsign, task_id)
        return True
    except Exception as e:
        logger.debug("[RoleMemory] Non-fatal write error: %s", e)
        return False


def load_recent(callsign: str, last_n: int = 3) -> list[dict]:
    """Load last N entries from role MEMORY.md. Returns [] on any error."""
    try:
        memory_path = ROLES_MEMORY_DIR / callsign / "MEMORY.md"
        if not memory_path.exists():
            return []

        text = memory_path.read_text(encoding="utf-8")
        # Parse entries by ## [ marker
        raw_entries = text.split("\n## [")
        entries = []
        for raw in raw_entries[1:]:  # skip header
            lines = raw.strip().split("\n")
            # Extract task_id and title from first line: task_id] Title
            header = lines[0] if lines else ""
            bracket_end = header.find("]")
            if bracket_end < 0:
                continue
            task_id = header[:bracket_end]
            title = header[bracket_end + 1:].strip()
            entries.append({"task_id": task_id, "title": title, "raw": raw[:800]})

        return entries[-last_n:]  # most recent
    except Exception as e:
        logger.debug("[RoleMemory] Non-fatal read error: %s", e)
        return []
```

**Integration in smart_debrief.py** (~3 lines, after existing ENGRAM write):
```python
# In process_smart_debrief(), after _route_to_memory() calls:
try:
    from src.memory.role_memory_writer import append_entry
    append_entry(
        callsign=report.agent_callsign or "unknown",
        task_id=report.task_id or "",
        task_title=report.task_title or "",
        q1="\n".join(report.lessons_learned) if report.lessons_learned else None,
        q2="\n".join(report.successes) if report.successes else None,
        q3="\n".join(report.recommendations) if report.recommendations else None,
        domain=report.domain or "",
    )
except Exception:
    pass  # always non-fatal
```

---

## 4. Read Side: session_tools.py injection

**Where:** After `my_focus` injection (~line 1347), before `_apply_token_budget`.

**Token tier:** T2 (same as `my_focus`, `engram_learnings`) — always injected unless
token budget forces drop. Add to `_SECTION_TIERS`: `"role_memory": 2`.

```python
# In session_tools.py _execute_async(), after my_focus injection:

# MARKER_203.ROLE_MEMORY: Inject per-role experiential memory
_callsign = role_context.get("callsign") if role_context else None
if _callsign:
    try:
        from src.memory.role_memory_writer import load_recent
        _recent = load_recent(_callsign, last_n=3)
        if _recent:
            context["role_memory"] = {
                "callsign": _callsign,
                "last_sessions": _recent,
                "file": f"memory/roles/{_callsign}/MEMORY.md",
                "count": len(_recent),
            }
    except Exception:
        pass  # never fatal
```

**Result shape in session_init response:**
```json
"role_memory": {
  "callsign": "Eta",
  "count": 3,
  "file": "memory/roles/Eta/MEMORY.md",
  "last_sessions": [
    {
      "task_id": "tb_1775217408_19779_1",
      "title": "RECON: Role Memory Architecture",
      "raw": "## [tb_1775217408_19779_1] RECON: Role Memory...\n### What I Learned..."
    },
    ...
  ]
}
```

---

## 5. CLAUDE.md Integration

**File:** `data/templates/claude_md_template.j2` — add section at end:

```jinja2
{%- if role.memory_path %}

## Role Memory
Your experiential memory across sessions: `{{ role.memory_path }}`
Read it at session start — your last tasks, patterns, unfinished threads.
Auto-populated from Q1-Q3 debrief. You can add narrative sections manually (Burnell-style).
{%- endif %}
```

**agent_registry.yaml** — add `memory_path` field per role:
```yaml
- callsign: "Eta"
  ...
  memory_path: "memory/roles/Eta/MEMORY.md"
```

`generate_claude_md.py` already reads all fields from AgentRole dataclass.
Add `memory_path: str = ""` to `AgentRole` dataclass in `agent_registry.py`.

---

## 6. ELISION Strategy

Role memory gets ELISION before injection:
- Max raw entries: last 3 tasks
- Max chars per entry: 800 (already capped in `load_recent`)
- Total budget: ~2400 chars / ~600 tokens → fits in T2
- If token budget forces cut: drop oldest entry first (LIFO)
- Future: apply ELISION L2 compression on raw text

```python
# Optional: compress raw entries
from src.memory.elision import elide_text
for entry in _recent:
    entry["raw"] = elide_text(entry["raw"], max_tokens=200)
```

---

## 7. Burnell Format: Manual Override

Each role MEMORY.md can have a **manual preamble** before the auto-entries:

```markdown
# Role Memory — Eta
# Auto-generated by role_memory_writer.py

## About This Role
Eta = Harness Engineer 2. I own the infra plumbing: task_board.py, session_tools.py,
smart_debrief.py, generate_claude_md.py. I am NOT an architect — I implement what
Commander + Zeta design.

## How To Wake Me Up
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/harness-eta
claude --dangerously-skip-permissions
# First message: vetka session init

## Unfinished Business (manual)
- SHERPA-V1.1 DOM fix (tb_1775163667) — still pending
- Per-role subdirectory tb_1774617580 — P4, nobody picked it up

---
[auto-entries appended below]

## [tb_1775217408_19779_1] RECON: Role Memory Architecture
...
```

Manual preamble is preserved — auto-entries append below the `---` marker.

---

## 8. Integration Points Summary

| File | Change | Lines |
|------|--------|-------|
| `src/memory/role_memory_writer.py` | NEW file | ~60 |
| `src/services/smart_debrief.py` | Add `append_entry()` call | ~5 |
| `src/mcp/tools/session_tools.py` | Add `role_memory` inject + tier T2 | ~12 |
| `data/templates/claude_md_template.j2` | Add `## Role Memory` section | ~6 |
| `data/templates/agent_registry.yaml` | Add `memory_path` per role | ~10 |
| `src/services/agent_registry.py` | Add `memory_path: str = ""` to AgentRole | ~1 |

**Total: ~94 lines across 6 files + 1 new file.**

---

## 9. Rollout Plan

### Phase 203.1 — Pilot (Eta + Zeta)
1. Create `src/memory/role_memory_writer.py`
2. Wire into `smart_debrief.process_smart_debrief()`
3. Wire into `session_tools.py` inject
4. Add `memory/roles/Eta/` and `memory/roles/Zeta/` manual preambles
5. **Test:** complete 2 tasks → verify entries appear → restart session → verify inject

### Phase 203.2 — CLAUDE.md Integration
6. Update `claude_md_template.j2` + `agent_registry.yaml` + `AgentRole` dataclass
7. Regenerate all CLAUDE.md files (`generate_claude_md.py --all`)
8. **Test:** session_init for each role shows role_memory field

### Phase 203.3 — Full Rollout
9. Add manual preambles for Alpha, Beta, Gamma, Delta, Epsilon, Commander
10. Each agent completes 1+ task → verify auto-population
11. **Test:** predecessor_ideas from ENGRAM surfaced alongside role_memory

### Phase 203.4 — Enrichment (optional)
12. ELISION L2 compression on raw entries
13. "Unfinished threads" extraction from Q3 ideas not yet tasked
14. Cross-role memory search: "what did Alpha learn about same domain?"

---

## 10. Rollout Order by Priority

| Order | Role | Why |
|-------|------|-----|
| 1 | **Eta** | Owns the code, pilot makes sense |
| 2 | **Zeta** | Harness co-owner, frequent sessions |
| 3 | **Alpha** | Most active CUT engine agent |
| 4 | **Delta** | QA gate — memory of test failures is critical |
| 5 | **Beta, Gamma** | CUT domain, moderate session frequency |
| 6 | **Epsilon** | Backup QA, occasional |
| 7 | **Commander** | Burnell already has manual MEMORY.md |

---

## 11. Open Questions for Commander

1. **Where does `memory/roles/` live?** In the repo (committed) or in `~/.vetka/`?
   - Repo = version-controlled, shared across worktrees ✓ (preferred)
   - `~/.vetka/` = local-only, not committed (simpler setup)

2. **Should role_memory be T1 or T2?** T1 = always present, can't be dropped.
   - If agent identity is critical → T1
   - If token budget matters → T2 (can be dropped for large contexts)
   - **Recommendation:** T2 with min_entries=1 guarantee (always at least last task)

3. **AURA extension for agent roles?** No — AURA schema is user-preference-fixed.
   role_memory_writer.py is the right abstraction. Keep concerns separate.

4. **Predecessor Idea tracker (tb_1774423047, closed as already_implemented)?**
   Needs re-audit — ENGRAM has `{callsign}::debrief::idea::*` keys but no surfacing
   at session_init. May need a 1-line addition to session_tools.py.

---

## 12. Files to NOT Touch

- `src/memory/aura_store.py` — AURA stays user-only
- `src/memory/engram_cache.py` — ENGRAM already writes callsign keys, don't change
- `srco/task_board.py` — smart_debrief is called from there, integration goes via smart_debrief only
- `e2e/` — out of Eta's scope
