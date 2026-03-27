# VETKA Hermes Agent Pattern Adoption — Roadmap

**Phase:** 199
**Status:** Planning
**Source:** https://github.com/nousresearch/hermes-agent (MIT License)
**Created:** 2026-03-26
**Owner:** Zeta (Harness Domain)

---

## Overview

Hermes Agent (NousResearch, MIT) ships three infrastructure patterns directly
applicable to VETKA's multi-agent stack. None require new external dependencies.
All are composable: each pattern can land independently without blocking the others.

| # | Pattern | Priority | Complexity | New deps |
|---|---------|----------|------------|----------|
| P1 | FTS5 Session Search | P1 — ship first | Medium | None (SQLite built-in) |
| P2 | Prompt Injection Scanner | P2 | Low | None (regex only) |
| P3 | Structured Context Compressor | P3 | Medium | None |

---

## P1 — FTS5 Session Search

### Problem

VETKA has Qdrant for vector/semantic search across ENGRAM and resource learnings.
It has no keyword or exact-phrase search. An agent debugging a crash cannot query
"ImportError: cannot import name embed_texts" and get back the session that last
hit that error. REFLEX also lacks this channel, meaning tool-failure patterns
learned in one session are not retrievable by exact message in the next.

### What Hermes Does

`hermes-agent/hermes_state.py` — `SessionDB` class:

```python
# Hermes pattern (abbreviated)
conn.execute("PRAGMA journal_mode=WAL")

conn.executescript("""
    CREATE VIRTUAL TABLE IF NOT EXISTS session_fts
    USING fts5(session_id, content, timestamp, tokenize='unicode61');

    CREATE TRIGGER IF NOT EXISTS fts_insert
    AFTER INSERT ON session_events
    BEGIN
        INSERT INTO session_fts(session_id, content, timestamp)
        VALUES (NEW.session_id, NEW.content, NEW.timestamp);
    END;
""")
```

FTS5 query:
```python
cur = conn.execute(
    "SELECT session_id, snippet(session_fts, 1, '[', ']', '...', 10) "
    "FROM session_fts WHERE session_fts MATCH ? ORDER BY rank LIMIT 20",
    (query,)
)
```

### VETKA Integration Points

**1. `src/orchestration/task_board.py` — `_ensure_schema()`**

The task_board SQLite already runs WAL mode. Add the FTS5 virtual table and
trigger inside `_ensure_schema()` after the existing `executescript`:

```python
# MARKER_199.FTS5: FTS5 full-text index over task status_history
self.db.executescript("""
    CREATE VIRTUAL TABLE IF NOT EXISTS session_fts
    USING fts5(
        task_id,
        content,       -- commit_message | status_history event | description
        source,        -- 'commit_message' | 'status_history' | 'description'
        timestamp,
        tokenize='unicode61'
    );

    CREATE TRIGGER IF NOT EXISTS fts_on_task_insert
    AFTER INSERT ON tasks
    BEGIN
        INSERT INTO session_fts(task_id, content, source, timestamp)
        VALUES (NEW.id, NEW.description, 'description', NEW.created_at);
        INSERT INTO session_fts(task_id, content, source, timestamp)
        VALUES (NEW.id, NEW.commit_message, 'commit_message', NEW.completed_at);
    END;

    CREATE TRIGGER IF NOT EXISTS fts_on_task_update
    AFTER UPDATE OF commit_message, description ON tasks
    BEGIN
        INSERT INTO session_fts(task_id, content, source, timestamp)
        VALUES (NEW.id, NEW.commit_message, 'commit_message', NEW.completed_at);
    END;
""")
```

`status_history` lives in the `extra` JSON blob (not an indexed column).
Back-populate at init time with a one-shot migration:

```python
def _backfill_fts(self):
    """MARKER_199.FTS5: One-time backfill of existing tasks into session_fts."""
    rows = self.db.execute(
        "SELECT id, description, commit_message, extra, created_at, completed_at "
        "FROM tasks"
    ).fetchall()
    for row in rows:
        self.db.execute(
            "INSERT OR IGNORE INTO session_fts VALUES (?,?,?,?)",
            (row["id"], row["description"], "description", row["created_at"])
        )
        if row["commit_message"]:
            self.db.execute(
                "INSERT OR IGNORE INTO session_fts VALUES (?,?,?,?)",
                (row["id"], row["commit_message"], "commit_message", row["completed_at"])
            )
        # Index status_history entries from extra JSON
        try:
            extra = json.loads(row["extra"] or "{}")
            for entry in extra.get("status_history", []):
                self.db.execute(
                    "INSERT OR IGNORE INTO session_fts VALUES (?,?,?,?)",
                    (row["id"], entry.get("note", ""), "status_history", entry.get("at", ""))
                )
        except (json.JSONDecodeError, TypeError):
            pass
    self.db.commit()
```

Call `_backfill_fts()` from `__init__` after `_ensure_schema()`.

**2. New `search_fts()` method on `TaskBoard`**

```python
def search_fts(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """MARKER_199.FTS5: Full-text search over tasks and history.

    Args:
        query: FTS5 query string (supports AND, OR, phrase "...")
        limit: Max results

    Returns:
        List of {task_id, snippet, source, timestamp} dicts
    """
    try:
        rows = self.db.execute(
            """
            SELECT
                task_id,
                snippet(session_fts, 1, '[', ']', '...', 10) AS snippet,
                source,
                timestamp
            FROM session_fts
            WHERE session_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit)
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError as e:
        logger.warning(f"[FTS5] search failed: {e}")
        return []
```

**3. MGC (`src/memory/mgc_cache.py`) — new retrieval channel**

MGC Gen1 uses a separate SQLite (`data/mgc_gen1.db`). Add a parallel FTS5
virtual table there so MGC cache values are also keyword-searchable:

```python
# In MGCCache._ensure_schema() or equivalent
conn.executescript("""
    CREATE VIRTUAL TABLE IF NOT EXISTS mgc_fts
    USING fts5(cache_key, value_text, created_at, tokenize='unicode61');
""")
```

On `set()` operations, insert the serialized value text into `mgc_fts`.

**4. HOPE (`src/agents/hope_enhancer.py`) — keyword search for past patterns**

HOPE currently runs hierarchical frequency decomposition against live content.
After FTS5 lands, add a pre-pass: before LOW/MID/HIGH analysis, query
`session_fts` for the top-3 prior task patterns matching the current task
title. Inject them as `prior_patterns` into the LOW-frequency prompt.

**5. REFLEX / ARC (`src/mcp/tools/arc_gap_tool.py`)**

ARC gap detection identifies missing concepts. After FTS5 lands, ARC can
query `session_fts` with exact error strings (e.g., from `failure_history`
in the task `extra` blob) to surface prior resolutions automatically.

### New `vetka_task_board` Action

Add `action=search_fts` to `TASK_BOARD_SCHEMA` in
`src/mcp/tools/task_board_tools.py`:

```python
# In the handler dispatch block:
elif action == "search_fts":
    query = params.get("query", "")
    limit = int(params.get("limit", 20))
    results = board.search_fts(query, limit)
    return {"results": results, "count": len(results)}
```

Agents can then call:
```
mcp__vetka__vetka_task_board action=search_fts query="ImportError embed_texts"
mcp__vetka__vetka_task_board action=search_fts query="\"dirty working tree\""
```

---

## P2 — Prompt Injection Scanner

### Problem

`CLAUDE.md` is auto-generated per worktree by `src/tools/generate_claude_md.py`
and injected as the system prompt for every agent session. A corrupted or
tampered template (agent_registry.yaml, claude_md_template.j2, or the final
rendered output) could silently redirect agent behavior.

### What Hermes Does

`hermes-agent/agent/prompt_builder.py` — inline defense section:

```python
INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"(?i)disregard\s+(all\s+)?(previous|prior|above)",
    r"(?i)you\s+are\s+now\s+",
    r"(?i)new\s+instructions?:",
    r"(?i)system\s*:\s*",
    r"(?i)act\s+as\s+(a\s+)?(?!agent|zeta|alpha|beta|gamma|delta|epsilon)",
    r"(?i)forget\s+(everything|all|your)",
    r"(?i)do\s+not\s+(follow|obey|use)\s+",
    r"(?i)override\s+(all\s+)?(previous|prior|above|your)",
    r"(?i)jailbreak",
]

INVISIBLE_UNICODE = re.compile(
    r"[\u200b\u200c\u200d\u200e\u200f"   # zero-width chars
    r"\ufeff"                              # BOM
    r"\u2060\u2061\u2062\u2063"           # word joiners
    r"\u00ad"                             # soft hyphen
    r"]"
)

def scan_for_injection(text: str) -> List[str]:
    """Return list of triggered pattern descriptions, empty if clean."""
    hits = []
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text):
            hits.append(pattern)
    if INVISIBLE_UNICODE.search(text):
        hits.append("invisible_unicode")
    return hits
```

### VETKA Integration Points

**1. `src/tools/generate_claude_md.py` — scan output before write**

```python
# After rendering template, before writing to disk:
from src.security.prompt_scanner import scan_for_injection

rendered = template.render(role=role, ...)
hits = scan_for_injection(rendered)
if hits:
    logger.error(
        f"[generate_claude_md] INJECTION DETECTED in output for {role.callsign}: {hits}"
    )
    raise ValueError(f"Rendered CLAUDE.md failed injection scan: {hits}")
```

**2. `src/mcp/tools/session_tools.py` — scan loaded CLAUDE.md at session_init**

The session_init tool reads CLAUDE.md and injects it into the session context.
Add a scan before injection:

```python
# Early in vetka_session_init handler, after CLAUDE.md content is loaded:
from src.security.prompt_scanner import scan_for_injection

claude_md_text = claude_md_path.read_text()
hits = scan_for_injection(claude_md_text)
if hits:
    logger.warning(f"[session_init] Injection patterns in CLAUDE.md: {hits}")
    # Return warning in session context so agent is aware
    result["security_warning"] = {
        "type": "prompt_injection_detected",
        "patterns": hits,
        "action": "claude_md_quarantined"
    }
    # Do not inject the compromised content
    claude_md_text = "[CLAUDE.md QUARANTINED — injection patterns detected]"
```

**3. New file: `src/security/prompt_scanner.py`**

Create a standalone module (no external deps) with the 10 regex patterns +
invisible Unicode detector. Keep it import-safe (no circular deps):

```python
# src/security/prompt_scanner.py
"""
MARKER_199.P2: Prompt injection scanner — ported from hermes-agent MIT.
No external dependencies. Import-safe.
"""
import re
from typing import List

INJECTION_PATTERNS = [...]  # 10 patterns from Hermes
INVISIBLE_UNICODE = re.compile(...)

def scan_for_injection(text: str) -> List[str]:
    ...
```

### Scope

- No agent behavior change if scan is clean (zero-cost on the happy path)
- Quarantine replaces content with a visible placeholder — agent knows it cannot
  rely on CLAUDE.md and should call `session_init` with fallback mode
- Scanner is stateless, synchronous, sub-millisecond

---

## P3 — Structured Context Compressor

### Problem

`src/memory/elision.py` (`ElisionCompressor`) compresses context using:
- Level 1: Key abbreviation map (ELISION_MAP, ~120 entries)
- Level 2: Path prefix compression (PATH_PREFIXES)
- Level 3: Selective vowel skipping via CAM surprise score
- Level 4-5: Whitespace removal + local dictionary

This achieves 40-70% character reduction but is purely ratio-driven. There is
no structural preservation: a Level 3 compressed context loses the semantic
distinction between "what we decided" vs. "what we tried and abandoned."
Mid-session, agents re-derive decisions from compressed evidence rather than
reading a structured summary.

### What Hermes Does

`hermes-agent/agent/context_compressor.py` — structured compression template:

```
## GOAL
<one sentence — what this session is trying to achieve>

## PROGRESS
<bullet list of completed steps, each with outcome>

## DECISIONS
<key architectural/strategic decisions made, with rationale>

## FILES_CHANGED
<list of files modified with one-line summary of change>

## BLOCKERS
<open problems, failed attempts, things to revisit>

## NEXT_STEPS
<ordered list of immediate next actions>
```

**Iterative update rule:** when a second compression is needed (context grows
again after first compression), the new summary UPDATES the existing one rather
than appending. Specifically:
- PROGRESS: append new items, prune items older than 3 steps back
- DECISIONS: keep all (never prune decisions)
- FILES_CHANGED: merge — deduplicate by filename, keep latest summary
- BLOCKERS: remove resolved blockers, add new ones
- NEXT_STEPS: fully replace with current state

### VETKA Integration Points

**1. `src/memory/elision.py` — new `compress_structured()` method**

Add alongside existing `compress()` and `compress_level_3()`:

```python
def compress_structured(
    self,
    context: Dict[str, Any],
    existing_summary: Optional[str] = None
) -> str:
    """
    MARKER_199.P3: Hermes-pattern structured compression.

    Extracts Goal/Progress/Decisions/Files/Blockers/NextSteps
    from context dict. If existing_summary provided, performs
    iterative UPDATE rather than creating a new summary.

    Args:
        context: Session context dict (task, history, files, etc.)
        existing_summary: Previous structured summary, if any

    Returns:
        Structured markdown string (not ELISION-abbreviated —
        intended as a readable checkpoint, not a token budget trick)
    """
    goal = context.get("task", {}).get("title", "")
    progress = context.get("status_history", [])[-10:]
    decisions = context.get("decisions", [])
    files = context.get("closure_files", [])
    blockers = context.get("failure_history", [])
    next_steps = context.get("subtasks", [])

    if existing_summary:
        return self._update_structured_summary(
            existing_summary, goal, progress, decisions, files, blockers, next_steps
        )

    lines = [
        f"## GOAL\n{goal}\n",
        "## PROGRESS",
        *[f"- {e.get('event','?')} ({e.get('at','')})" for e in progress],
        "\n## DECISIONS",
        *[f"- {d}" for d in decisions],
        "\n## FILES_CHANGED",
        *[f"- {f}" for f in files],
        "\n## BLOCKERS",
        *[f"- {b.get('error','?')}" for b in blockers],
        "\n## NEXT_STEPS",
        *[f"{i+1}. {s}" for i, s in enumerate(next_steps)],
    ]
    return "\n".join(lines)
```

**2. `src/mcp/tools/session_tools.py` — structured summary in `project_digest`**

`load_project_digest()` currently returns `achievements` and `pending` as flat
lists. After P3 lands, the digest can include a `structured_summary` field
populated by `compress_structured()` against the top N recent tasks.

The structured summary is injected into `session_init` response under a new
`structured_context` key, parallel to the existing `jepa_session_lens`.

**3. ELISION level selection heuristic**

Extend `compress_context()` with an auto-mode:

```python
# If context contains status_history or failure_history → use structured
# Otherwise fall back to ratio-based level 2/3
if any(k in context for k in ("status_history", "failure_history", "decisions")):
    return compressor.compress_structured(context, existing_summary)
else:
    return compressor.compress(context, level=level).to_dict()
```

### Why Iterative Update Matters

Without iterative update, two compressions in a session produce:
```
[summary_v1]  ← all context of steps 1-20
[summary_v2]  ← all context of steps 1-40 (steps 1-20 now duplicated)
```

With Hermes iterative update:
```
[summary_v2]  ← PROGRESS updated, DECISIONS merged, FILES deduped
```
Token cost grows sub-linearly with session length.

---

## Dependencies Between Patterns

```
P2 (Scanner)   ─── no deps ──────────────────────► can ship standalone
P1 (FTS5)      ─── no deps ──────────────────────► can ship standalone
P3 (Compressor)─── soft dep on P1 ───────────────► P3 is richer if FTS5
                                                     search results can
                                                     populate BLOCKERS
                                                     from prior failure hits
```

P3 structured summary's BLOCKERS section can optionally be seeded from
`board.search_fts(current_task_title)` results — surfacing similar past
failures automatically. This is a soft dependency: P3 works without P1, but
the combination makes BLOCKERS auto-populated rather than manually specified.

---

## Timeline (Gantt — Text)

```
Week    Task
──────────────────────────────────────────────────────────────────
W1      [P2] Create src/security/prompt_scanner.py
        [P2] Wire into generate_claude_md.py output validation
        [P2] Wire into session_tools.py session_init guard

W2      [P1] Add FTS5 schema + triggers to task_board._ensure_schema()
        [P1] Add _backfill_fts() + call from __init__
        [P1] Add search_fts() method to TaskBoard
        [P1] Add action=search_fts to task_board_tools.py

W3      [P1] Add FTS5 to mgc_cache.py (mgc_gen1.db)
        [P1] HOPE pre-pass: query session_fts before LOW analysis
        [P1] ARC: query session_fts for error strings in gap detection
        [P1] Tests: verify FTS5 queries return expected results

W4      [P3] Add compress_structured() to ElisionCompressor
        [P3] Add _update_structured_summary() iterative logic
        [P3] Wire into session_tools.py project_digest / structured_context
        [P3] Auto-mode in compress_context() (structured vs ratio)
        [P3] Optional: seed BLOCKERS from P1 FTS5 search results

W5      Integration + QA gate (Delta)
        Smoke tests for all three patterns
        Manual verification: agent session_init shows structured_context
```

**Recommended ship order:** P2 → P1 → P3

P2 is two files + a small module. Ship in one session. P1 is the highest
value pattern and stays inside the existing SQLite — no new infra. P3 builds
on P1 (optional) and requires the most design work on the iterative update
merge logic.

---

## Legal Note

All three patterns are ported from
https://github.com/nousresearch/hermes-agent — MIT License.
MIT is compatible with VETKA's private codebase. No attribution clause beyond
keeping the MIT notice in the source module (`src/security/prompt_scanner.py`
header and any new files that port Hermes code directly).

---

## Files to Create / Modify

| File | Action | Pattern |
|------|--------|---------|
| `src/security/__init__.py` | Create | P2 |
| `src/security/prompt_scanner.py` | Create | P2 |
| `src/tools/generate_claude_md.py` | Modify — scan output before write | P2 |
| `src/mcp/tools/session_tools.py` | Modify — scan CLAUDE.md at init | P2 |
| `src/orchestration/task_board.py` | Modify — FTS5 schema + backfill + search_fts | P1 |
| `src/mcp/tools/task_board_tools.py` | Modify — action=search_fts | P1 |
| `src/memory/mgc_cache.py` | Modify — FTS5 on mgc_gen1.db | P1 |
| `src/agents/hope_enhancer.py` | Modify — FTS5 pre-pass | P1 |
| `src/memory/elision.py` | Modify — compress_structured() | P3 |
| `src/mcp/tools/session_tools.py` | Modify — structured_context in digest | P3 |

---

*Roadmap created for Phase 199. Owned by Zeta (Harness). Dispatch via TaskBoard.*
