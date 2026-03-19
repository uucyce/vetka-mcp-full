# Roadmap: Phase 195 — Protocol Guard Layer

**Commander:** Opus
**Date:** 2026-03-19
**Agents:** 2 parallel + Opus review
**Est. total:** 2-3 hours
**Depends on:** Phase 193 (REFLEX Feedback Guard) — DONE
**Architecture:** [ARCHITECTURE_195_PROTOCOL_GUARD.md](ARCHITECTURE_195_PROTOCOL_GUARD.md)

---

## Problem Statement

Agents skip the Work Entry Protocol defined in CLAUDE.md:
- Edit files without reading them first (blind edits)
- Code without claiming a task (naked commits)
- Create tasks without a roadmap
- Skip task_board check before starting work

**Phase 193** solved tool-level danger blocking (e.g., "never use preview_start for CUT").
**Phase 195** solves workflow-level enforcement (e.g., "never edit without reading first").

---

## Execution Plan: 2 Agents + Opus

### Why 2?

Two independent modules with clear boundaries:

- **Agent A (Core):** SessionActionTracker + ProtocolGuard — pure logic, no MCP imports
- **Agent B (Integration):** Wire into fc_loop, session_init, task_board MCP, REFLEX bridge
- **Opus:** Tests, review, merge, live verification

```
Timeline:
  ┌─ Agent A: Core modules (W1) ─────────────────────────────────┐
  │  session_tracker.py + protocol_guard.py                       │
  │                                                                ├──→ Opus: Tests +
  │  ┌─ Agent B: Integration (W2, after A done) ────────────┐    │     Review + Merge
  │  │  fc_loop + session_init + task_board + REFLEX bridge   │    │
  │  └────────────────────────────────────────────────────────┘    │
  └────────────────────────────────────────────────────────────────┘
```

---

## Wave 1 — Core Modules (Agent A, parallel start)

### Task 195.1: SessionActionTracker — per-session state accumulator

**What to do:**
1. Create `src/services/session_tracker.py`
2. Implement `SessionActions` dataclass:
   ```python
   @dataclass
   class SessionActions:
       session_id: str
       created_at: float
       session_init_called: bool = False
       task_board_checked: bool = False
       task_claimed: bool = False
       claimed_task_id: Optional[str] = None
       claimed_task_has_recon_docs: bool = False
       roadmap_exists: bool = False
       files_read: Set[str] = field(default_factory=set)
       files_edited: Set[str] = field(default_factory=set)
       read_count: int = 0
       edit_count: int = 0
       search_count: int = 0
       task_board_calls: int = 0
   ```
3. Implement `SessionActionTracker` class:
   - `record_action(session_id, tool_name, args)` — classify tool and update state
   - `get_session(session_id)` → SessionActions (creates if missing)
   - `get_protocol_summary(session_id)` → dict for session_init injection
   - `_classify_tool(tool_name)` → "read"|"edit"|"search"|"task_board"|"session"|"other"
   - TTL: auto-expire sessions older than 1 hour
4. Implement `get_session_tracker()` singleton
5. Tool classification table:
   ```python
   _READ_TOOLS = {"Read", "vetka_read_file", "Grep", "Glob"}
   _EDIT_TOOLS = {"Edit", "Write", "vetka_edit_file", "NotebookEdit"}
   _SEARCH_TOOLS = {"Grep", "Glob", "vetka_search_files", "vetka_search_semantic", "WebSearch"}
   _TASK_BOARD_TOOLS = {"vetka_task_board"}
   _SESSION_TOOLS = {"vetka_session_init"}
   ```

**Files:** `src/services/session_tracker.py`
**Constraint:** Pure logic. No imports from MCP tools, fc_loop, or session_tools. Only stdlib + dataclasses.

---

### Task 195.2: ProtocolGuard — rule engine

**What to do:**
1. Create `src/services/protocol_guard.py`
2. Implement `ProtocolViolation` dataclass:
   ```python
   @dataclass
   class ProtocolViolation:
       rule_id: str          # "read_before_edit"
       severity: str         # "warn" | "block"
       message: str          # Human-readable
       suggestion: str       # What to do instead
   ```
3. Implement `ProtocolGuard` class with rules:
   ```python
   class ProtocolGuard:
       def __init__(self):
           self._rules = self._load_rules()

       def check(self, session: SessionActions, tool_name: str, args: dict) -> List[ProtocolViolation]:
           """Run all applicable rules. Return violations (may be empty)."""

       def _rule_read_before_edit(self, session, tool_name, args) -> Optional[ProtocolViolation]:
           """Edit/Write on file not in session.files_read → warn"""

       def _rule_task_before_code(self, session, tool_name, args) -> Optional[ProtocolViolation]:
           """Edit/Write without claimed task → warn"""

       def _rule_taskboard_before_work(self, session, tool_name, args) -> Optional[ProtocolViolation]:
           """Edit/Write without prior task_board list/get → warn"""

       def _rule_recon_before_code(self, session, tool_name, args) -> Optional[ProtocolViolation]:
           """Edit/Write with claimed task missing recon_docs → warn"""

       def _rule_session_init_first(self, session, tool_name, args) -> Optional[ProtocolViolation]:
           """Any tool without session_init → warn"""

       def _rule_roadmap_before_tasks(self, session, tool_name, args) -> Optional[ProtocolViolation]:
           """task_board action=add without roadmap → warn"""
   ```
4. Load severity overrides from `data/protocol_guard_config.json` (optional file)
5. Implement `get_protocol_guard()` singleton
6. Feature flag: `PROTOCOL_GUARD_ENABLED` env var (default: true)

**Files:** `src/services/protocol_guard.py`, `data/protocol_guard_config.json`
**Constraint:** Only imports `session_tracker.SessionActions`. No MCP, no fc_loop.

---

### Task 195.3: Config file + path exemptions

**What to do:**
1. Create `data/protocol_guard_config.json`:
   ```json
   {
     "rules": {
       "read_before_edit": {
         "severity": "warn",
         "exempt_paths": ["docs/**", "*.md", "*.json", "data/**"],
         "description": "Warn when editing a file that hasn't been read in this session"
       },
       "task_before_code": {
         "severity": "warn",
         "exempt_paths": ["docs/**", "*.md"],
         "description": "Warn when editing code without a claimed task"
       },
       "taskboard_before_work": {
         "severity": "warn",
         "exempt_paths": [],
         "description": "Warn when editing without checking task board"
       },
       "recon_before_code": {
         "severity": "warn",
         "exempt_paths": [],
         "description": "Warn when claimed task has no recon_docs"
       },
       "session_init_first": {
         "severity": "warn",
         "exempt_paths": [],
         "description": "Warn when tools used before session_init"
       },
       "roadmap_before_tasks": {
         "severity": "warn",
         "exempt_paths": [],
         "description": "Warn when adding tasks without a phase roadmap"
       }
     },
     "global_exempt_agents": [],
     "session_ttl_seconds": 3600
   }
   ```
2. Integrate loading into ProtocolGuard.__init__()

**Files:** `data/protocol_guard_config.json`, update `src/services/protocol_guard.py`
**Note:** This is part of 195.2 agent's work — listed separately for clarity.

---

## Wave 2 — Integration (Agent B, after W1 merged)

### Task 195.4: fc_loop integration — pre-call protocol check

**What to do:**
1. In `src/tools/fc_loop.py`, after existing REFLEX guard check (MARKER_193.4):
   ```python
   # MARKER_195.4: Protocol Guard pre-call check
   try:
       from src.services.protocol_guard import get_protocol_guard
       from src.services.session_tracker import get_session_tracker
       tracker = get_session_tracker()
       guard = get_protocol_guard()
       # Record action BEFORE check (so reads count for same-turn edits)
       tracker.record_action(session_id, func_name, func_args)
       violations = guard.check(tracker.get_session(session_id), func_name, func_args)
       for v in violations:
           if v.severity == "block":
               tool_result = {"error": f"PROTOCOL: {v.message}\n→ {v.suggestion}"}
               # Skip execution
           else:
               logger.warning("[PROTOCOL] %s: %s", v.rule_id, v.message)
   except Exception:
       pass  # Never break fc_loop
   ```
2. Extract `session_id` from pipeline context (already available via `self._session_id`)
3. **Order matters:** record reads BEFORE checking edits, so same-turn read+edit works

**Files:** `src/tools/fc_loop.py`
**Constraint:** try/except around ALL protocol code. Guard crash = allow tool.

---

### Task 195.5: session_init — protocol_status section

**What to do:**
1. In `src/mcp/tools/session_tools.py`, after building context:
   ```python
   # MARKER_195.5: Protocol status in session_init
   try:
       from src.services.session_tracker import get_session_tracker
       tracker = get_session_tracker()
       tracker.record_action(session_id, "vetka_session_init", {})
       summary = tracker.get_protocol_summary(session_id)
       context["protocol_status"] = summary
   except Exception:
       context["protocol_status"] = {"error": "tracker unavailable"}
   ```
2. The `protocol_status` section shows agents their compliance state
3. Include in compressed output (important for agent context)

**Files:** `src/mcp/tools/session_tools.py`
**Constraint:** Non-invasive. Add section to existing context dict.

---

### Task 195.6: MCP tool recording — task_board + edit hooks

**What to do:**
1. In task_board MCP handler, after successful execution:
   ```python
   # MARKER_195.6: Record task_board action for protocol tracking
   tracker = get_session_tracker()
   tracker.record_action(session_id, "vetka_task_board", {"action": action, "task_id": task_id})
   ```
2. In vetka_edit_file MCP handler:
   ```python
   tracker.record_action(session_id, "vetka_edit_file", {"file_path": file_path})
   ```
3. In vetka_read_file MCP handler:
   ```python
   tracker.record_action(session_id, "vetka_read_file", {"file_path": file_path})
   ```
4. Add recording to any other MCP tools that map to read/edit categories

**Files:** `src/mcp/tools/task_board_tools.py` (or wherever task_board handler lives), `src/mcp/tools/file_tools.py` (or equivalent)
**Constraint:** One-liner additions. No logic changes to existing handlers.

---

### Task 195.7: REFLEX bridge — violations as warnings

**What to do:**
1. In `src/services/reflex_integration.py`, in `reflex_session()`:
   ```python
   # MARKER_195.7: Protocol violations as REFLEX warnings
   try:
       from src.services.protocol_guard import get_protocol_guard
       from src.services.session_tracker import get_session_tracker
       tracker = get_session_tracker()
       guard = get_protocol_guard()
       session = tracker.get_session(session_id)
       # Check for pending violations (what would trigger if agent edits now)
       pending = guard.check(session, "Edit", {"file_path": "__preview__"})
       for v in pending:
           warnings.append({
               "tool_id": "protocol_guard",
               "reason": v.message,
               "severity": v.severity,
               "source": f"protocol:{v.rule_id}"
           })
   except Exception:
       pass
   ```
2. This makes protocol status visible alongside REFLEX tool recommendations

**Files:** `src/services/reflex_integration.py`

---

## Wave 3 — Tests + Verify (Opus)

### Task 195.8: Test suite

**What to do:**
1. Create `tests/test_phase195_protocol_guard.py`:

   **SessionActionTracker tests:**
   - `test_record_read_updates_files_read` — Read tool → file added to files_read
   - `test_record_edit_updates_files_edited` — Edit tool → file added to files_edited
   - `test_record_task_board_list_sets_checked` — task_board action=list → task_board_checked=True
   - `test_record_task_board_claim_sets_claimed` — task_board action=claim → task_claimed=True
   - `test_record_session_init_sets_flag` — session_init → session_init_called=True
   - `test_classify_tool_read` — Read, vetka_read_file, Grep → "read"
   - `test_classify_tool_edit` — Edit, Write, vetka_edit_file → "edit"
   - `test_session_ttl_expiry` — old sessions auto-expire
   - `test_get_protocol_summary` — returns correct checklist dict

   **ProtocolGuard tests:**
   - `test_read_before_edit_warns` — Edit without Read → violation
   - `test_read_before_edit_ok` — Read then Edit → no violation
   - `test_task_before_code_warns` — Edit without claim → violation
   - `test_task_before_code_ok` — Claim then Edit → no violation
   - `test_taskboard_before_work_warns` — Edit without task_board list → violation
   - `test_recon_before_code_warns` — claimed task without recon_docs → violation
   - `test_session_init_first_warns` — tool without session_init → violation
   - `test_roadmap_before_tasks_warns` — task_board add without roadmap → violation
   - `test_exempt_paths_skip_rule` — Edit on docs/*.md → no violation for read_before_edit
   - `test_config_severity_override` — config sets rule to "block" → violation.severity="block"
   - `test_guard_disabled_returns_empty` — PROTOCOL_GUARD_ENABLED=false → no violations

   **Integration tests:**
   - `test_full_protocol_happy_path` — session_init → list → claim → read → edit → zero violations
   - `test_violation_cascade` — edit without anything → 3 violations (session_init, taskboard, task)
   - `test_same_session_cross_file` — read A, edit B → read_before_edit on B only

**Files:** `tests/test_phase195_protocol_guard.py`

---

### Task 195.9: Integration verify + live test

**What to do:**
1. Run full test suite: `python -m pytest tests/ -v`
2. Manual test flow:
   - Call session_init → check `protocol_status` present
   - Edit a file without reading → check warning logged
   - Read file → edit same file → no warning
3. Verify fc_loop integration doesn't crash pipeline
4. Verify REFLEX bridge shows protocol warnings in recommendations
5. Clean up dead code if any

**Files:** Various
**This is Opus's task — post-merge verification.**

---

## Task Summary

| Wave | Task ID | Title | Agent | Depends On | Est. |
|------|---------|-------|-------|------------|------|
| W1 | 195.1 | SessionActionTracker module | Agent A | — | 30min |
| W1 | 195.2 | ProtocolGuard rule engine | Agent A | 195.1 | 30min |
| W1 | 195.3 | Config file + path exemptions | Agent A | 195.2 | 10min |
| W2 | 195.4 | fc_loop pre-call integration | Agent B | 195.1, 195.2 | 20min |
| W2 | 195.5 | session_init protocol_status | Agent B | 195.1 | 15min |
| W2 | 195.6 | MCP tool recording hooks | Agent B | 195.1 | 15min |
| W2 | 195.7 | REFLEX bridge | Agent B | 195.1, 195.2 | 10min |
| W3 | 195.8 | Test suite | Opus | 195.1-195.7 | 30min |
| W3 | 195.9 | Integration verify | Opus | 195.8 | 20min |

```
Parallel execution:
  Time 0    ├── A: 195.1+195.2+195.3 (core) ── 70min ──┐
            │                                             ├── B: 195.4-195.7 (integration) ── 60min ──┐
            │                                             │                                             │
            └─────────────────────────────────────────────┘                                             │
                                                                    ├── Opus: 195.8+195.9 ── 50min ────┘

  Total wall time: ~3 hours (vs ~5h sequential)
```

---

## Agent Instructions

### For Agent A (core modules):
```
Read these files FIRST:
1. docs/195_PROTOCOL_GUARD/ARCHITECTURE_195_PROTOCOL_GUARD.md
2. src/services/reflex_guard.py (reference: singleton pattern, guard pattern)
3. CLAUDE.md "WORK ENTRY PROTOCOL" section (the rules to enforce)

Your job: Create session_tracker.py (195.1) + protocol_guard.py (195.2) + config (195.3).
DO NOT touch: fc_loop.py, session_tools.py, reflex_integration.py, tests.
Pure logic modules only. No MCP imports.
```

### For Agent B (integration):
```
Read these files FIRST:
1. docs/195_PROTOCOL_GUARD/ARCHITECTURE_195_PROTOCOL_GUARD.md
2. src/services/session_tracker.py (Agent A's output)
3. src/services/protocol_guard.py (Agent A's output)
4. src/tools/fc_loop.py (understand tool execution + existing REFLEX guard)
5. src/mcp/tools/session_tools.py (understand session_init)
6. src/services/reflex_integration.py (understand REFLEX session flow)

Your job: Wire core modules into fc_loop (195.4), session_init (195.5),
MCP tools (195.6), REFLEX (195.7).
DO NOT touch: session_tracker.py, protocol_guard.py, tests.
All integrations MUST be try/except safe.
```

---

## Design Principles

1. **Warn first, block later** — All rules start as `warn`. Promote to `block` only after observing violation patterns.
2. **Never break the pipeline** — All integration points wrapped in try/except. Guard crash = allow tool.
3. **Session-scoped** — No persistent state. Each session starts clean. Historical patterns go through CORTEX.
4. **Config-driven** — Severities and exemptions in JSON, not code. Easy to tune without deploys.
5. **Composable with REFLEX** — Protocol Guard is a separate layer that feeds INTO existing REFLEX warning pipeline.
