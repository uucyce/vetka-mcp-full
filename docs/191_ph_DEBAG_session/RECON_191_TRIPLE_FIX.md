# RECON: Phase 191 — Three Bugs

**Date:** 2026-03-18
**Phase:** 191 — DEBUG Session

---

## BUG 2: Schema Drift — Duplicate MCP Schemas

### Problem
Task board MCP schema is defined in **3 places** independently. They drift every time one is updated.

| Location | Actions in enum | Missing |
|----------|:-:|---------|
| `task_board_tools.py:29-76` (canonical) | 11 | — |
| `vetka_mcp_bridge.py:920-957` | 9 | `merge_request`, `promote_to_main` |
| `mycelium_mcp_server.py:220-253` | 6 (no enum!) | `claim`, `complete`, `active_agents`, `merge_request`, `promote_to_main` |

All three also missing `force_no_docs` field from phase 190 in non-canonical copies.

### Root Cause
Both bridge and mycelium import `handle_task_board()` (handler) but NOT `TASK_BOARD_SCHEMA`. Each maintains its own inline copy.

### Fix: Single Source of Truth

**`task_board_tools.py`** already exports `TASK_BOARD_SCHEMA` (line 29). Import it:

**`vetka_mcp_bridge.py:~920`:**
```python
from src.mcp.tools.task_board_tools import TASK_BOARD_SCHEMA
Tool(
    name="vetka_task_board",
    description="Task Board CRUD...",
    inputSchema=TASK_BOARD_SCHEMA,  # Single source
)
```

**`mycelium_mcp_server.py:~223`:**
```python
from src.mcp.tools.task_board_tools import TASK_BOARD_SCHEMA
Tool(
    name="mycelium_task_board",
    description="Task Board CRUD...",
    inputSchema=TASK_BOARD_SCHEMA,  # Single source
)
```

### Files to Change
1. `src/mcp/vetka_mcp_bridge.py` — replace inline schema with import (~lines 918-958)
2. `src/mcp/mycelium_mcp_server.py` — replace inline schema with import (~lines 220-253)

---

## BUG 3: Reflex Not Task-Aware

### Problem
`reflex_session()` returns generic top-10 recommendations across the entire system. It ignores the current task even though `task_board_summary` (with task titles and descriptions) is already loaded in session context.

### Data Flow (current, broken)
```
session_init()
  → loads task_board_summary (pending/in_progress tasks with titles)
  → calls reflex_session(context, agent_type)
    → recommend_for_session(session_data, phase_type, agent_type)
      → ReflexContext.from_session()
        → task_text = _infer_context_from_git()  ← GENERIC, ignores tasks
      → scorer.recommend(context, ALL_TOOLS, top_n=10)  ← GENERIC
```

### Key Insight
`_semantic_match()` (weight 0.22) already supports keyword matching via `tool.matches_keywords(context.task_text)` and `intent_tags` overlap. It just needs a real `task_text` from the actual task.

### Fix: Inject Task Context

**`session_tools.py:385-406`** — extract current task before calling reflex:
```python
current_task = None
tb = context.get("task_board_summary", {})
in_prog = tb.get("in_progress", [])
if in_prog:
    current_task = in_prog[0]
elif tb.get("top_pending"):
    current_task = tb["top_pending"][0]

reflex_recs = reflex_session(context, agent_type=agent_type, current_task=current_task)
```

**`reflex_integration.py:330`** — accept and forward `current_task`:
```python
def reflex_session(session_data, phase_type="research", agent_type="", current_task=None):
```

**`reflex_scorer.py:763`** — use task title+description as `task_text`:
```python
def recommend_for_session(self, session_data, ..., current_task=None):
    task_text = ""
    if current_task:
        task_text = (current_task.get("title", "") + " " + current_task.get("description", "")).strip()
    context = ReflexContext.from_session(session_data, task_text=task_text, ...)
```

### Files to Change
1. `src/mcp/tools/session_tools.py` (~line 395) — extract task, pass to reflex
2. `src/services/reflex_integration.py` (~line 330) — accept `current_task` param
3. `src/services/reflex_scorer.py` (~line 763) — use task as `task_text`

### Scoring Weights (for reference)
```
semantic: 0.22  cam: 0.12  feedback: 0.18  engram: 0.07
stm: 0.15  phase: 0.18  hope: 0.05  mgc: 0.03
```

---

## BUG 4: Task List Limit Ignores Filters

### Problem
Default limit raised to 40 in 189.13, but limit applies **unconditionally** — even when `project_id` filter is active. Logic should be: "if you're filtering, you know what you want — return everything."

### Current Code
**`task_board_tools.py:254-262`:**
```python
# MARKER_189.13
max_limit = min(int(arguments.get("limit") or 40), 100)
total = len(tasks)
page = tasks[:max_limit]  # ALWAYS applies limit
```

### Fix
```python
max_limit = min(int(arguments.get("limit") or 40), 100)
total = len(tasks)
if filter_project:
    page = tasks  # Filtered query → return all matches
else:
    page = tasks[:max_limit]  # Unfiltered → apply default limit
```

### Files to Change
1. `src/mcp/tools/task_board_tools.py` (~lines 254-257)

---

## Summary

| Bug | Severity | Effort | Files |
|-----|----------|--------|-------|
| Schema drift | HIGH | 15 min | 2 files |
| Reflex not task-aware | MEDIUM | 20 min | 3 files |
| Limit ignores filters | LOW | 5 min | 1 file |
