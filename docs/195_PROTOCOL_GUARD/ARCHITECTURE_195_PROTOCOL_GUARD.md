# Architecture: Phase 195 — Protocol Guard Layer

**Author:** Opus
**Date:** 2026-03-19
**Phase:** 195.0
**Depends on:** Phase 193 (REFLEX Feedback Guard)

---

## Problem Statement

CLAUDE.md defines a **Work Entry Protocol** that agents must follow:
1. `session_init` FIRST
2. Check roadmap → check task board → claim task → THEN code
3. Read files before editing them
4. Never commit without a task

**The protocol is enforced by text instructions only.** Agents routinely skip steps:

| Violation | Frequency | Impact |
|-----------|-----------|--------|
| Edit without prior Read | Common | Blind edits, broken code |
| Code without task_board check | Common | Naked commits, orphan work |
| Task creation without roadmap | Occasional | Fragmented planning |
| Edit without recon_docs in task | Common | No context for reviewer |

**Root cause:** No infrastructure enforcement. The protocol lives in CLAUDE.md markdown — agents can (and do) ignore it.

**Phase 193 (REFLEX Guard)** solved tool-level danger rules. Phase 195 solves **workflow-level** protocol enforcement.

---

## What Exists (Phase 193) vs What's Missing (Phase 195)

```
Phase 193 — REFLEX Guard (DONE):
  "Is this TOOL dangerous in this CONTEXT?"
  → tool_pattern + context_pattern → block/warn/demote
  → Sources: ENGRAM L1, CORTEX failures, static rules
  → Scope: single tool call

Phase 195 — Protocol Guard (NEW):
  "Has this AGENT followed the PROTOCOL before this action?"
  → session-level action history → protocol compliance check
  → Sources: SessionActionTracker (new), task_board state
  → Scope: session workflow sequence
```

Key difference: REFLEX Guard checks **what** tool is called. Protocol Guard checks **what happened before** the tool is called.

---

## Architecture

### Layer Diagram

```
                          ┌──────────────────────┐
                          │   CLAUDE.md Protocol  │  ← text instructions (advisory)
                          └──────────┬───────────┘
                                     │ codifies
                          ┌──────────▼───────────┐
                          │   ProtocolGuard       │  ← NEW: enforcement layer
                          │   (protocol_guard.py) │
                          └──────────┬───────────┘
                                     │ queries
                          ┌──────────▼───────────┐
                          │  SessionActionTracker │  ← NEW: per-session state
                          │  (session_tracker.py) │
                          └──────────┬───────────┘
                                     │ fed by
                    ┌────────────────┼────────────────┐
                    │                │                  │
             ┌──────▼──────┐  ┌─────▼──────┐  ┌──────▼──────┐
             │  fc_loop.py  │  │  MCP tools  │  │ task_board  │
             │ (tool calls) │  │ (session_   │  │ (claim/     │
             │              │  │  init, etc.) │  │  complete)  │
             └─────────────┘  └────────────┘  └─────────────┘
```

### Components

#### 1. SessionActionTracker (`src/services/session_tracker.py`) — NEW

Lightweight per-session counter that tracks what the agent has done.

```python
@dataclass
class SessionActions:
    session_id: str
    created_at: float
    # Protocol checkpoints
    session_init_called: bool = False
    task_board_checked: bool = False        # action=list or action=get
    task_claimed: bool = False               # action=claim
    claimed_task_id: Optional[str] = None
    claimed_task_has_recon_docs: bool = False
    roadmap_exists: bool = False             # docs/{phase}_*/ROADMAP_*.md found
    # File tracking
    files_read: Set[str] = field(default_factory=set)     # paths Read/Grep/search
    files_edited: Set[str] = field(default_factory=set)    # paths Edit/Write
    # Counters
    read_count: int = 0
    edit_count: int = 0
    search_count: int = 0
    task_board_calls: int = 0


class SessionActionTracker:
    """Per-session action accumulator. Singleton per session_id."""

    def record_action(self, session_id: str, tool_name: str, args: dict) -> None:
        """Record a tool call. Categorize into read/edit/search/task_board."""

    def get_session(self, session_id: str) -> SessionActions:
        """Get current session state."""

    def check_protocol(self, session_id: str, tool_name: str, args: dict) -> ProtocolResult:
        """Check if calling this tool right now violates the protocol."""
```

**Classification of tools:**

| Category | Tools | Tracked Field |
|----------|-------|---------------|
| **read** | `Read`, `vetka_read_file`, `Grep`, `Glob`, `vetka_search_files`, `vetka_search_semantic` | `files_read`, `read_count` |
| **edit** | `Edit`, `Write`, `vetka_edit_file`, `NotebookEdit` | `files_edited`, `edit_count` |
| **search** | `Grep`, `Glob`, `vetka_search_files`, `vetka_search_semantic`, `WebSearch` | `search_count` |
| **task_board** | `vetka_task_board` (all actions) | `task_board_calls`, per-action flags |
| **session** | `vetka_session_init` | `session_init_called` |

#### 2. ProtocolGuard (`src/services/protocol_guard.py`) — NEW

Stateless rule engine that evaluates protocol compliance given a SessionActions snapshot.

```python
@dataclass
class ProtocolViolation:
    rule_id: str            # "read_before_edit", "task_before_code", etc.
    severity: str           # "warn" | "block"
    message: str            # Human-readable violation description
    suggestion: str         # What the agent should do instead


class ProtocolGuard:
    """Evaluates Work Entry Protocol compliance."""

    def check(self, session: SessionActions, tool_name: str, args: dict) -> List[ProtocolViolation]:
        """Check all protocol rules before allowing tool execution."""
```

**Protocol Rules:**

| Rule ID | Trigger | Condition | Severity | Message |
|---------|---------|-----------|----------|---------|
| `read_before_edit` | Edit/Write called | `file_path not in session.files_read` | **warn** | "You haven't read {file} yet. Read it first to understand context." |
| `task_before_code` | Edit/Write called | `not session.task_claimed` | **warn** | "No task claimed. Claim a task before editing code." |
| `taskboard_before_work` | Edit/Write called | `not session.task_board_checked` | **warn** | "You haven't checked the task board. Run task_board action=list first." |
| `recon_before_code` | Edit/Write called | `session.task_claimed and not session.claimed_task_has_recon_docs` | **warn** | "Your claimed task has no recon_docs. Consider adding context." |
| `session_init_first` | Any MCP tool | `not session.session_init_called` | **warn** | "Call session_init first to load project context." |
| `roadmap_before_tasks` | task_board action=add | `not session.roadmap_exists` | **warn** | "No roadmap found for current phase. Create one first." |

**All rules start as `warn` (never `block`).** We observe violation frequency first, then promote to `block` based on data.

#### 3. Integration Points

**IP-1: fc_loop.py — Pre-call hook (Mycelium pipeline)**

```python
# In fc_loop.py, before tool execution:
try:
    from src.services.protocol_guard import get_protocol_guard
    from src.services.session_tracker import get_session_tracker

    tracker = get_session_tracker()
    guard = get_protocol_guard()

    # Record the action
    tracker.record_action(session_id, tool_name, tool_args)

    # Check protocol
    violations = guard.check(tracker.get_session(session_id), tool_name, tool_args)
    for v in violations:
        if v.severity == "block":
            return {"error": f"PROTOCOL VIOLATION: {v.message}\n{v.suggestion}"}
        else:
            logger.warning("[PROTOCOL] %s: %s", v.rule_id, v.message)
            # Inject warning into tool result preamble
except Exception:
    pass  # Never break the pipeline
```

**IP-2: MCP tool handlers — Record actions (external agents)**

For Claude Code and Cursor (which call MCP tools directly, not via fc_loop):

```python
# In each MCP tool handler (session_tools, task_board_tools, etc.):
# After successful execution, record to tracker
tracker = get_session_tracker()
tracker.record_action(session_id, tool_name, args)
```

**IP-3: session_init — Protocol status in context**

```python
# In session_init response, add protocol_status section:
context["protocol_status"] = {
    "session_init": True,
    "task_board_checked": session.task_board_checked,
    "task_claimed": session.task_claimed,
    "files_read": len(session.files_read),
    "files_edited": len(session.files_edited),
    "violations_this_session": violation_count,
    "protocol_checklist": [
        {"step": "session_init", "done": True},
        {"step": "task_board_check", "done": session.task_board_checked},
        {"step": "claim_task", "done": session.task_claimed},
        {"step": "read_before_edit", "done": True},  # dynamic per-file
    ]
}
```

**IP-4: Reflex Guard bridge — Protocol violations as REFLEX warnings**

```python
# In reflex_integration.py, add protocol violations to session warnings:
violations = guard.check_all_pending(session)
for v in violations:
    context["reflex_warnings"].append({
        "tool_id": "protocol_guard",
        "reason": v.message,
        "severity": v.severity,
        "source": f"protocol:{v.rule_id}"
    })
```

---

## Scope: What This Is NOT

1. **NOT a replacement for CLAUDE.md** — Protocol Guard enforces the same rules, not different ones
2. **NOT a hard blocker (initially)** — All rules start as `warn`, not `block`
3. **NOT tracking Claude Code's native tools** — Only MCP tools and fc_loop tools are tracked. Claude Code's Read/Edit/Grep are invisible to the MCP server. For Claude Code agents, Protocol Guard works through **session_init advisories** rather than real-time blocking.
4. **NOT persistent across sessions** — SessionActionTracker resets per session. Historical patterns go to CORTEX/ENGRAM via existing feedback loops.

### Claude Code vs Mycelium: Different Enforcement Modes

| Agent Type | Tool Execution | Tracking | Enforcement |
|------------|---------------|----------|-------------|
| **Mycelium (Dragon)** | fc_loop | Real-time (IP-1) | Pre-call warn/block |
| **Claude Code (Opus)** | Native CLI tools | MCP calls only (IP-2) | Advisory in session_init (IP-3) |
| **Cursor** | MCP tools | MCP calls only (IP-2) | Advisory in session_init (IP-3) |

For Claude Code, the key enforcement mechanism is **session_init displaying the protocol checklist**. The agent sees "task_board_checked: false" and self-corrects. This is "soft enforcement" — effective because the LLM reads session_init output.

---

## Data Flow

```
1. Agent starts session
   └─ session_init → tracker.record("session_init")
                   → response includes protocol_status (checklist)

2. Agent calls task_board action=list
   └─ tracker.record("task_board", {action: "list"})
   └─ session.task_board_checked = True

3. Agent claims task
   └─ tracker.record("task_board", {action: "claim", task_id: "tb_xxx"})
   └─ session.task_claimed = True
   └─ Check task.recon_docs → session.claimed_task_has_recon_docs

4. Agent reads a file
   └─ tracker.record("Read", {file_path: "/src/foo.py"})
   └─ session.files_read.add("/src/foo.py")

5. Agent edits a file
   └─ tracker.record("Edit", {file_path: "/src/foo.py"})
   └─ guard.check() → file in files_read? task claimed? → OK or WARN
   └─ session.files_edited.add("/src/foo.py")

6. Agent edits ANOTHER file (not read)
   └─ tracker.record("Edit", {file_path: "/src/bar.py"})
   └─ guard.check() → "/src/bar.py" NOT in files_read → WARN: read_before_edit
```

---

## File Plan

| File | Type | Purpose |
|------|------|---------|
| `src/services/session_tracker.py` | NEW | SessionActionTracker + SessionActions |
| `src/services/protocol_guard.py` | NEW | ProtocolGuard + ProtocolViolation + rules |
| `src/tools/fc_loop.py` | MODIFY | IP-1: pre-call protocol check |
| `src/mcp/tools/session_tools.py` | MODIFY | IP-2: record session_init, IP-3: protocol_status |
| `src/mcp/tools/task_board_tools.py` | MODIFY | IP-2: record task_board actions |
| `src/services/reflex_integration.py` | MODIFY | IP-4: bridge violations to REFLEX warnings |
| `tests/test_phase195_protocol_guard.py` | NEW | Full test suite |
| `data/protocol_guard_config.json` | NEW | Rule severity overrides (warn→block) |

---

## Metrics (Success Criteria)

After deployment, measure via CORTEX feedback:

1. **Blind edit rate** — % of edits where file was not previously read. Target: <10% (from ~40%)
2. **Naked code rate** — % of edit sessions without a claimed task. Target: <5%
3. **Protocol compliance score** — % of sessions with zero violations. Target: >70%

These metrics feed back into ENGRAM for long-term tracking.

---

## Open Questions

1. **Severity escalation:** When should a rule go from `warn` to `block`? Proposal: after 10+ violations in 7 days.
2. **Exclude paths:** Should some paths be exempt (e.g., docs/, tests/)? Proposal: yes, `read_before_edit` only for `src/**/*.py` and `client/src/**/*.{ts,tsx}`.
3. **Multi-file reads:** If agent reads `src/foo.py`, does that "count" for editing `src/foo.py:50-60`? Yes — path match only, not line ranges.
4. **Session TTL:** How long does session state persist? Proposal: 1 hour, matching session_init TTL.
