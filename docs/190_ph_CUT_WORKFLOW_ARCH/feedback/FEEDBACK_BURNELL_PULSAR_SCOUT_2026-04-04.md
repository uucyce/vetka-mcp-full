# Captain Burnell — PULSAR Scout Session Debrief + Handoff
# Date: 2026-04-04 | Session: magical-burnell | Phase: 203

## Q1-Q3: What I built

### Scout service (`src/services/scout.py`, 533 lines)
- ScoutMarker dataclass: file, start_line, end_line, symbol, snippet, relevance
- Scout.analyze(task_dict) -> List[ScoutMarker]:
  1. Extract keywords from title+description (regex split, stop words filter, top 20)
  2. Resolve scope from allowed_paths + domain (DOMAIN_PATHS mapping from agent_registry)
  3. ripgrep subprocess (`rg -n -i --type py --type ts --max-count 50`)
  4. Expand to symbol boundaries: ast.parse for Python (class/function enclosure), simple +-3 lines for TS
  5. Score by term overlap, deduplicate overlapping ranges, return top 8
- Singleton: get_scout() / reset_scout()
- Never crashes: try/except around everything, returns [] on any failure

### TaskBoard hooks (`src/orchestration/task_board.py`)
- `scout_recon` added to VALID_STATUSES
- `scout_context`, `verify_retries`, `verification_notes` added to ADDABLE_FIELDS
- Lazy-load `_get_scout()`: one-time import attempt, permanent disable on failure (same pattern as Verifier V2)
- `_run_scout_hook()`: called after add_task and update_task
  - Triggers when task has allowed_paths or domain
  - Skips research-type tasks
  - Sets status pending -> scout_recon when markers found
  - Re-scouts on update when allowed_paths or description changes

### Commits
- `f66f8e5a0` on claude/magical-burnell (worktree)
- `fc9244bf3` on main (manual apply, verified by Delta before merge)

---

## Q4: What's broken / gaps I noticed

1. **No tests for Scout** — zero. Architecture doc specifies ~150 lines. Critical gap.
2. **TypeScript expansion is trivial** — just +-3 lines, no real symbol detection. Client-side is heavily TS.
3. **Title changes don't re-trigger Scout** — update_task only watches allowed_paths and description.
4. **No priority awareness** — P1 critical gets same 8-marker budget as P5 someday.
5. **No proactive backfill** — tasks created before Scout existed stay in `pending` forever.
6. **add_task doesn't accept `domain` param** — domain is injected by MCP tool layer, not task_board.py. Scout hook in add_task can't use domain directly unless MCP layer passes it through.
7. **Singleton init race** — _scout_load_attempted has no lock. Two concurrent add_task calls could both attempt import. GIL makes this safe in practice but not formally correct.

---

## Q5: What worked well

- **Lazy-load pattern** from Verifier V2 — zero overhead when Scout absent, auto-activates when deployed. Should be the standard for all TaskBoard middleware.
- **Sonnet subagents for recon** — 3 parallel agents covered task_board.py (2800 lines), agent_registry.yaml, Verifier V2 code, services pattern, and domain mapping in ~2 minutes total. I would have spent 15 minutes reading fragments.
- **Smoke test loop** — creating a real task with add_task, checking status=scout_recon, checking markers. Caught the `--type tsx` bug immediately.

---

## Q6: Provocative questions (debrief format)

**What's the dumbest thing in the codebase right now?**
VALID_STATUSES being edited by 3 agents on 3 branches simultaneously. It's a single line. Snapshot merge can't resolve this — it needs to be a structured registry, not a set literal.

**What would I do with 2 more hours?**
Write test_scout.py (8 test functions), add MCP tool `mycelium_scout action=analyze`, implement backfill loop for pending tasks without scout_context.

**What anti-pattern keeps recurring?**
Agents building the same thing independently because task descriptions overlap (S1/S2/S3 + my S1/S2 = 5 tasks for 2 deliverables). Task board needs duplicate detection at creation time.

---

## Q7: HANDOFF — Scout & Sherpa Development Vector

### Scout: what exists now
```
Task created (action=add)
  -> _run_scout_hook() [sync, <2s]
    -> extract keywords from title+description
    -> ripgrep search in allowed_paths + domain dirs
    -> ast.parse expand to Python symbols
    -> score by relevance, top 8 markers
    -> task.scout_context = [ScoutMarker, ...]
    -> task.status = "scout_recon"
  -> Sherpa picks up scout_recon tasks (async background loop)
```

### Scout: immediate priorities (next session)

**P1: Tests** — `tests/test_scout.py`
- test_extract_keywords: stop words, technical terms, dedup
- test_resolve_scope: allowed_paths, domain mapping, fallback
- test_ripgrep_search: mock subprocess, parse output format
- test_expand_python: ast.parse real Python file, class.method resolution
- test_expand_simple: non-Python fallback
- test_deduplicate: overlapping markers
- test_hook_add_task: integration, pending -> scout_recon
- test_hook_update_task: re-scout on description change

**P2: MCP tool** — `mycelium_scout`
- `action=analyze task_id=<id>` — explicit scout trigger
- `action=backfill` — scan pending tasks without scout_context
- `action=status` — how many tasks in each scout state
- Agents can call Scout directly instead of only via task lifecycle

**P3: Priority-aware budget**
```python
if priority <= 2:  # P1-P2 critical/high
    max_markers = 12
    max_keywords = 30
    search_timeout = 10
else:
    max_markers = 8
    max_keywords = 20
    search_timeout = 5
```

**P4: TypeScript symbol expansion**
- Regex-based: search backward from match for `function|class|interface|export const`
- Use indentation to find block boundaries
- Or: tree-sitter-languages pip package (adds ~20MB but real parsing)

### Sherpa: integration with Scout (next phase)

**Scout context injection into Sherpa prompt** (arch doc section 3.5):
```
## Pre-scouted Code Locations (VERIFIED — these files and lines EXIST)

### src/orchestration/task_board.py:922-1109 (TaskBoard.add_task)
```python
def add_task(self, title, description, ...):
    ...
```
```
This is the key value prop: Sherpa sends REAL code to external AI, not guesses. Hallucination rate drops from ~40% to ~5%.

**Where to implement**: `sherpa.py` (or equivalent) — when building prompt for scout_recon task, read `task.scout_context` and format as verified code blocks.

### Sherpa: PULSAR v2 components (Phase 203 roadmap)

| Component | Status | Owner | What it does |
|-----------|--------|-------|-------------|
| ServiceHealthMonitor | pending | Polaris | Replace round-robin with health-score routing |
| ArenaVoter | pending | Polaris | Ethical dual-response scoring + vote clicks |
| ReconVerifier (V1) | pending | Polaris | TaskVerifier class with 6 check functions |
| Verifier middleware (V2) | done_main | Zeta | Lazy-load gate in TaskBoard update_task |
| sherpa.yaml pulsar config | pending | Polaris | fallback_chain, health thresholds, arena config |

### Testing landscape

| Tool | What to test | Notes |
|------|-------------|-------|
| pytest | Unit tests for Scout, Verifier, SHM | Standard, mock subprocess for rg |
| Gemma 4 (local) | Keyword extraction quality scoring | Compare Scout keywords vs LLM-extracted terms |
| Different search tools | ast-grep, tree-sitter, ctags vs ripgrep | Benchmark: which finds better symbols? |
| Real task corpus | Run Scout on 50 existing tasks, measure hit rate | Tasks with known code locations as ground truth |
| Sherpa E2E | Scout -> Sherpa -> Verifier full chain | Requires all 3 components merged |

### Architecture decisions for next agent

1. **Scout is middleware, not a service** — it runs inside TaskBoard, not as a separate process. Keep it that way.
2. **Lazy-load is the pattern** — `_get_scout()` tries once, caches forever. Same as `_get_task_verifier()`.
3. **Never crash the board** — every Scout call is wrapped in try/except. If Scout breaks, tasks still create normally.
4. **scout_recon is optional** — agents can claim `pending` tasks directly. Scout enriches but doesn't gate.
5. **Singleton per process** — one Scout instance shared by all add_task/update_task calls. Stateless analyze().

---

*The telescope points. The tape records. The eyes see.*
*Scout finds the signal. Sherpa amplifies it. Verifier filters the noise.*
*Three instruments. One truth. The PULSAR chain.*

— Captain Burnell, 2026-04-04
