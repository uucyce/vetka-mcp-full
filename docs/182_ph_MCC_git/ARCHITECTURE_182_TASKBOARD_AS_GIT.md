# Phase 182-184: Task Board как "Новый Git" для Агентов

**Status:** 📋 ARCHITECTURE DRAFT (Ready for Phase 182 Implementation)
**Last Updated:** 2026-03-15
**Author:** Opus + Reconnaissance
**Related Issues:** MARKER_178_TASK_CLOSE_AUTO_COMMIT_ERROR, MARKER_182_MCC_RECON, MARKER_182_VERIFIER_RECON

---

## Executive Summary

Task Board эволюционирует из "задачной системы" в **полноценную VCS для агентов**. Вместо того чтобы агенты трогали Git напрямую (и получали index.lock, worktree конфликты), они пишут действия в **Action Registry**, а **Verifier** (не "оркестратор") батчирует и коммитит в Git.

**Ключевое**: Workflow `agent → test → user verify → verifier merge → auto-close` полностью построен на существующих компонентах (TaskBoard, Verifier, REFLEX, closure_protocol).

---

## Workflow: От Agent до Merge

```
┌────────────────────────────────────────────────────────────┐
│ 1. AGENT PICKUP                                             │
│ vetka_session_init → TaskBoard.list() → agent claims task  │
│ MARKER_182.1: session_id assigned + MCC shows "claimed_by" │
└────────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────┐
│ 2. AGENT EXECUTION                                         │
│ agent_pipeline.execute(task_id, run_id)                   │
│ MARKER_182.2: run_id = f"run_{ts}_{task_id[-8:]}"        │
│ MARKER_182.3: ActionRegistry logs every edit/create/read  │
│ MARKER_182.4: closure_tests defined + closure_files scope │
└────────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────┐
│ 3. AGENT RESULT SUBMISSION                                 │
│ result, result_summary, stats, closure_proof.tests[]      │
│ MARKER_182.5: Verifier checked (confidence score)         │
│ MARKER_182.6: Timeline events persisted                   │
└────────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────┐
│ 4. USER VERIFICATION (NEW UI in Phase 183)                │
│ VerificationChecklist shows:                               │
│  • All tests passed? (closure_proof.tests[])              │
│  • Verifier confidence >= threshold?                      │
│  • Required closure files declared?                       │
│ MARKER_182.7: User can override with reason (optional)    │
│ MARKER_182.8: If not all verified → task for user (p2/p3) │
└────────────────────────────────────────────────────────────┘
                         ↓
        ┌─────────────────┬──────────────────┐
        │ User approves   │ User rejects      │
        ↓                 ↓
┌──────────────────┐ ┌──────────────────┐
│ result_status =  │ │ result_status =  │
│ "applied"        │ │ "rejected"       │
│ → Verifier flow  │ │ → Back to pending│
│                  │ │ + user feedback  │
└──────────────────┘ └──────────────────┘
        │
        ↓
┌────────────────────────────────────────────────────────────┐
│ 5. VERIFIER MERGE (Existing Role, Enhanced for Phase 182) │
│ MARKER_182.9: Verifier reads ActionRegistry for run_id    │
│ MARKER_182.10: Collects all file writes + creates commit  │
│ MARKER_182.11: Batch write to disk + one git commit       │
│ MARKER_182.12: REFLEX logs tool success (IP-5)            │
│ MARKER_182.13: Auto-close via commit hash (auto_complete) │
└────────────────────────────────────────────────────────────┘
                         ↓
        ┌──────────────┬──────────────┐
        │ Success      │ Failure      │
        ↓              ↓
┌────────────────┐ ┌────────────────┐
│ status="done"  │ │ Doctor or P1   │
│ Auto-push (CI) │ │ local agent    │
└────────────────┘ │ retry          │
                   └────────────────┘

```

---

## Component Breakdown

### 1. Action Registry (NEW, Phase 182)

**Purpose:** Central log of all agent actions during execution.

**Location:** `MARKER_182.ACTIONREGISTRY: src/orchestration/action_registry.py` (create new file)

**Responsibilities:**
- Log every action: `log_action(run_id, session_id, agent, action, file, result, duration_ms)`
- Actions: `edit`, `read`, `create`, `delete`, `test_run`, `commit_prep`
- Store in rotating `/data/action_log.json` (max 10k entries, trim oldest)
- Optional: Write to Qdrant collection `actions` for semantic search (Phase 183)

**Data Structure:**
```python
ActionLogEntry = {
    "id": uuid,
    "run_id": str,                    # run_20260315_102345_8f9a
    "session_id": str,                # sess_20260315_102345_abc123
    "task_id": str,                   # tb_1234567890_1
    "agent": str,                     # opus, cursor, dragon, grok
    "action": str,                    # edit|read|create|delete|test|commit
    "file": str,                      # src/main.py
    "result": "success|failed",
    "duration_ms": int,
    "timestamp": ISO8601,
    "metadata": {                     # Optional
        "lines_changed": int,
        "error": str,  # if failed
        "output": str  # if test
    }
}
```

**Methods:**
```python
class ActionRegistry:
    def __init__(self, storage_path="/data/action_log.json"):
        self.log_file = storage_path
        self.buffer = []

    def log_action(self, run_id, session_id, agent, action, file,
                   result, duration_ms=0, metadata=None):
        """Log a single action"""
        entry = ActionLogEntry(...)
        self.buffer.append(entry)
        if len(self.buffer) >= 100:  # Batch writes
            self.flush()

    def flush(self):
        """Write buffered actions to disk"""
        # Read, append, trim to 10k, write back

    def get_actions_for_run(self, run_id):
        """Get all actions for a specific run"""

    def get_actions_for_session(self, session_id):
        """Get all actions for a specific session"""
```

### 2. Run ID Generation (Phase 182)

**Location:** `MARKER_182.RUNID: src/orchestration/agent_pipeline.py` (modify execute method)

**Current:** `run_id = task_id` (line 2725)
**Change to:**
```python
def execute(self, ...):
    import time, secrets
    timestamp = int(time.time() * 1000)  # ms
    random_suffix = secrets.token_hex(4)
    self.run_id = f"run_{timestamp}_{self.task_id[-8:]}_{random_suffix}"

    # Store for later access
    self._timeline_metadata = {
        "run_id": self.run_id,
        "session_id": self.session_id,  # MARKER_183
        "task_id": self.task_id,
        "timestamp": timestamp
    }
```

**Use in pipeline:**
- Pass to `ActionRegistry.log_action(run_id=self.run_id, ...)`
- Include in result: `{"run_id": self.run_id, ...}`
- Pass to `PipelineHistory.append_run(run_id=...)`

### 3. Session ID Assignment (Phase 183)

**Location:** `MARKER_183.SESSIONID: src/orchestration/mycelium_heartbeat.py`

**Current:** HeartbeatEngine creates N tasks with no session linking
**Change:** Before dispatch loop:
```python
async def tick(self):
    # Generate unique session for this tick
    import time, secrets
    timestamp = int(time.time() * 1000)
    session_id = f"sess_{timestamp}_{secrets.token_hex(4)}"

    for parsed_task in parsed_tasks:
        task = self.board.add_task(
            ...,
            session_id=session_id,  # NEW MARKER_183.A
            source_chat_id=...,
            source_group_id=...
        )

        # Dispatch with session context
        dispatch_result = mycelium_pipeline(...,
            context={"session_id": session_id})  # NEW MARKER_183.B
```

**Update:** `TaskBoard.add_task()` signature:
```python
def add_task(self, title, ..., session_id=None):
    # MARKER_183.C: Add to TaskCard
    task["session_id"] = session_id
    task["status_history"].append({
        "ts": now(),
        "session_id": session_id,  # Track when session assigned
        ...
    })
```

### 4. Test Tracking & Closure Proof (Existing, Enhance for Phase 182)

**Location:** MARKER_182.CLOSURE: `src/orchestration/task_board.py` (existing, no changes for Phase 182, UI in Phase 183)

**Current Status:**
- ✓ `require_closure_proof` field exists (line 528)
- ✓ `closure_tests` array exists (line 530)
- ✓ `closure_proof` object with results exists (line 532-566)
- ✓ `run_closure_protocol()` auto-runs tests (line 1019-1162)
- ✓ `_run_closure_tests()` executes pytest commands (line 338-366)

**For Phase 182:**
- No code changes (tests already tracked)
- Just ensure `closure_proof.tests[]` is populated by `run_closure_protocol()`

**For Phase 183 (UI):**
- NEW: `VerificationChecklist.tsx` component
- Show `closure_proof.tests[]` with pass/fail
- Show `verifier_confidence` score
- Allow manual override with reason (MARKER_182.OVERRIDE)

### 5. Verifier Role (Existing, Enhanced for Phase 182)

**Location:** MARKER_182.VERIFIER: `src/orchestration/agent_pipeline.py` lines 838-981

**Current Verifier:**
```python
def _verify_subtask(self, subtask_result, scout_report, subtask_context):
    """Verify code from coder"""
    # Calls Claude Sonnet 4 to check: HAS CODE? CORRECT? COMPLETE?
    # Returns: {passed: bool, confidence: 0.0-1.0, issues: [], suggestions: []}
    # MARKER_125.0B: Quality gate at 0.75 confidence
```

**For Phase 182: Verifier as Merge Agent**
- New responsibility: After task closure approved by user, Verifier reads ActionRegistry
- Collects all file writes from run_id
- Batches them into one commit

**New Method (add to AgentPipeline class):**
```python
# MARKER_182.VERIFIER_MERGE
async def verify_and_merge(self, run_id, session_id, task_id):
    """
    Verifier role: merge all actions from a run into Git
    Called after user approval of result + test pass
    """
    # 1. Fetch all actions for this run
    actions = ActionRegistry.get_actions_for_run(run_id)

    # 2. Group by file
    file_changes = defaultdict(list)  # {file: [action, action, ...]}
    for action in actions:
        if action["action"] in ["edit", "create"]:
            file_changes[action["file"]].append(action)

    # 3. Prepare commit (MARKER_182.GITPREP)
    commit_message = f"phase182: task {task_id} completed [run:{run_id}]"

    # 4. Write files to disk (MARKER_182.FILEWRITE)
    # (This is done by agent already, but verify)

    # 5. Git commit (MARKER_182.GITCOMMIT)
    git.commit(commit_message, files=list(file_changes.keys()))

    # 6. Update task closure (MARKER_182.CLOSURE)
    board.complete_task(
        task_id,
        commit_hash=git.last_hash(),
        closure_proof={...verified...}
    )

    # 7. REFLEX feedback (MARKER_182.REFLEX)
    reflex_verifier(
        run_id=run_id,
        task_id=task_id,
        passed=True,
        tools_used=self.tools_used,
        confidence=avg_verifier_confidence
    )
```

### 6. Timeline Events Persistence (Phase 182)

**Location:** MARKER_182.TIMELINE: `src/api/routes/pipeline_history.py` (modify append_run)

**Current:** Timeline events are in memory only (agent_pipeline.py:215)
**Change:**

```python
# In agent_pipeline.py, after execution:
def execute(self, ...):
    ...
    result = {
        "run_id": self.run_id,
        "timeline": self._timeline_events,  # Collect all events
        "subtasks": [...],
        ...
    }

    # MARKER_182.TIMELINE_SAVE
    # In pipeline_history.append_run():
    self.history.append({
        "run_id": run_id,
        "task_id": task_id,
        "timeline_events": result["timeline"],  # NEW FIELD
        "phases_completed": [...],
        "status": "success|failed",
        ...
    })
```

**Result:**
- Can later do: `GET /api/pipeline/history/{run_id}/timeline` → see all events
- MARKER_182.TIMELINE_API: New endpoint in pipeline_history_routes.py

### 7. User Verification Checklist (NEW UI, Phase 183)

**Location:** MARKER_182.UIVERIF: `client/src/components/mcc/VerificationChecklist.tsx` (create new)

**Shows:**
```
✓ Tests Passed (closure_proof.tests[])
  ✓ pytest tests/ -v ... PASSED
  ✓ npm test ... PASSED
  ✓ mypy src/ ... PASSED

✓ Verifier Confidence: 0.92 (threshold: 0.75) ✓
  Issues found: 0
  Suggestions: 2

✓ Closure Files Declared:
  • src/main.py
  • tests/test_main.py

⚠️ User Approval Required:
  [ ] I have reviewed the code
  [ ] Tests are meaningful
  [ ] Changes match the task description

[APPROVE] [REQUEST CHANGES] [OVERRIDE + REASON]
```

**Triggered:** After agent completes + Verifier verified + closure_tests pass

**Integration:** `TaskCard.tsx` → show VerificationChecklist when `result_status="pending"`

### 8. REFLEX Integration (Existing, Phase 182+)

**Location:** MARKER_182.REFLEX: `src/services/reflex_integration.py` (modify reflex_verifier)

**Current IP-5 (After Verifier):**
```python
def reflex_verifier(pipeline_outcome, task_id, agent_used_tools):
    """Log which tools were used + link to verifier pass/fail"""
    # Maps: tool_id → verifier_passed
    # Feeds back into: next subtask recommendations (IP-4)
```

**For Phase 182:**
- Add `run_id` tracking
- Link `ActionRegistry.get_actions_for_run(run_id)` → tools used
- Log: Which files touched, how many changes, success rate

```python
# MARKER_182.REFLEX_ENHANCED
def reflex_verifier(run_id, session_id, task_id, verifier_confidence,
                    tools_used, actions_registry):
    """Enhanced IP-5: Link tools → actions → verifier outcome"""

    # Get all actions for this run
    actions = actions_registry.get_actions_for_run(run_id)

    # Group by tool used
    tool_to_actions = defaultdict(list)
    for action in actions:
        # Parse action.metadata to find which tool caused it
        tool_to_actions[action.get("tool_id")].append(action)

    # Log feedback: tool → success/fail
    for tool_id, tool_actions in tool_to_actions.items():
        success_rate = sum(1 for a in tool_actions if a["result"]=="success") / len(tool_actions)

        reflex_feedback.record({
            "tool_id": tool_id,
            "run_id": run_id,
            "task_id": task_id,
            "success": success_rate >= 0.8,
            "useful": verifier_passed,  # Verifier confirmed usefulness
            "context": "task_merge",
            "confidence": verifier_confidence
        })
```

---

## Data Flow Diagrams

### Diagram 1: Single Task Execution with Action Registry

```
agent_pipeline.execute(task_id, run_id, session_id)
    ↓
[ARCHITECT PHASE]
    └─ ActionRegistry.log_action("read", "docs/...", "success")
    ↓
[SCOUT PHASE]
    └─ ActionRegistry.log_action("read", "src/...", "success")
    ↓
[CODER PHASE]
    for file in files_to_edit:
        write(file, new_code)
        └─ ActionRegistry.log_action("edit", file, "success")
    ↓
[VERIFIER PHASE]
    read(code_output)
    └─ ActionRegistry.log_action("read", "result.txt", "success")
    confidence = 0.92
    ↓
result = {
    "run_id": "run_20260315_102345_8f9a",
    "session_id": "sess_20260315_102345_abc123",
    "subtasks": [...],
    "closure_proof": {
        "tests": [
            {"command": "pytest", "passed": true},
            {"command": "npm test", "passed": true}
        ],
        "verifier_confidence": 0.92
    },
    "timeline_events": [
        {"ts": "...", "role": "architect", "event": "start"},
        {"ts": "...", "role": "coder", "event": "end", "files_modified": 3}
    ]
}
    ↓
TaskBoard.update_task(
    task_id,
    result=result,
    status="pending_user_approval"
)
    ↓
[UI: VerificationChecklist appears]
    ↓
User: [APPROVE]
    ↓
TaskBoard.apply_task_result(task_id)  # result_status="applied"
    ↓
Verifier.verify_and_merge(run_id, session_id, task_id)
    ├─ ActionRegistry.get_actions_for_run(run_id)  [3 edit actions]
    ├─ Verify closure_files declared
    ├─ git commit "phase182: task tb_xxx completed [run:run_xxx]"
    ├─ ActionRegistry.flush() → /data/action_log.json
    ├─ REFLEX: Log tool feedback + confidence
    └─ auto_complete_task(task_id, commit_hash)  [via git hook]
         ↓
         status="done"
```

### Diagram 2: Session with Multiple Tasks

```
HeartbeatEngine.tick()
    ├─ session_id = "sess_20260315_102345_abc123"
    ├─ Parse @dragon commands
    │   ├─ Task A (tb_1): "Build feature X"
    │   ├─ Task B (tb_2): "Add tests"
    │   └─ Task C (tb_3): "Optimize"
    ↓
TaskBoard.add_task(
    title="Build feature X",
    session_id="sess_20260315_102345_abc123",  # All tasks linked
    source_chat_id="chat_uuid"
)
    ↓
Dispatch 3 tasks via mycelium_pipeline
    ├─ Agent 1: Task A (run_1)
    ├─ Agent 2: Task B (run_2)
    └─ Agent 1: Task C (run_3, after A done)
    ↓
All actions logged with same session_id:
    ActionRegistry:
    ├─ run_1: Agent 1 edits src/feature.py, src/test_feature.py
    ├─ run_2: Agent 2 edits tests/test_*.py
    └─ run_3: Agent 1 optimizes src/feature.py
    ↓
User verification (separate for each task):
    ├─ Approve A
    ├─ Approve B
    └─ Approve C
    ↓
Verifier merge (sequential or parallel):
    ├─ Merge A → commit "phase182: task tb_1 completed [run:run_1]"
    ├─ Merge B → commit "phase182: task tb_2 completed [run:run_2]"
    └─ Merge C → commit "phase182: task tb_3 completed [run:run_3]"
    ↓
Query capability: "Get all actions in session_xxx"
    → Shows: 3 tasks, X total file edits, Y files affected, Z commit history
```

---

## Integration Points & Markers

| Marker | File | Line(s) | What | Phase |
|--------|------|---------|------|-------|
| **MARKER_182.ACTIONREGISTRY** | `src/orchestration/action_registry.py` | NEW | ActionRegistry class definition | 182 |
| **MARKER_182.RUNID** | `src/orchestration/agent_pipeline.py` | ~2725 | Change run_id generation (was: task_id) | 182 |
| **MARKER_182.1** | `src/orchestration/mycelium_heartbeat.py` | ~45 | Assign session_id when parsing tasks | 183 |
| **MARKER_182.2** | `src/api/routes/task_routes.py` | ~50 | Add session_id param to add_task() | 183 |
| **MARKER_182.3** | `src/orchestration/agent_pipeline.py` | ~215 | Pass run_id + session_id to ActionRegistry | 182 |
| **MARKER_182.4** | `src/orchestration/agent_pipeline.py` | ~2313 | Emit timeline events with run_id context | 182 |
| **MARKER_182.5** | `src/api/routes/pipeline_history.py` | ~37 | Persist timeline_events in append_run() | 182 |
| **MARKER_182.CLOSURE** | `src/orchestration/task_board.py` | 528-566 | (Existing) closure_proof tracking | N/A |
| **MARKER_182.VERIFIER** | `src/orchestration/agent_pipeline.py` | 838-981 | (Existing) Verifier role | N/A |
| **MARKER_182.VERIFIER_MERGE** | `src/orchestration/agent_pipeline.py` | NEW | Add verify_and_merge() method | 182 |
| **MARKER_182.GITPREP** | `src/orchestration/agent_pipeline.py` | NEW | Prepare git commit from ActionRegistry | 182 |
| **MARKER_182.GITCOMMIT** | `src/orchestration/agent_pipeline.py` | NEW | Execute git commit (Verifier role) | 182 |
| **MARKER_182.CLOSURE** | `src/orchestration/task_board.py` | ~1019 | Call complete_task() after merge | 182 |
| **MARKER_182.REFLEX** | `src/services/reflex_integration.py` | ~210 | Enhance IP-5 with run_id + action tracking | 182 |
| **MARKER_182.UIVERIF** | `client/src/components/mcc/VerificationChecklist.tsx` | NEW | User verification UI component | 183 |
| **MARKER_182.OVERRIDE** | `client/src/components/mcc/VerificationChecklist.tsx` | NEW | Manual override button + reason form | 183 |
| **MARKER_182.TIMELINE_API** | `src/api/routes/pipeline_history.py` | NEW | GET /api/pipeline/history/{run_id}/timeline | 182 |

---

## Backward Compatibility

- ✓ Existing `TaskBoard.add_task()` signature: `session_id` is optional (default: None)
- ✓ Existing `agent_pipeline.execute()` works with both old and new run_id format
- ✓ Existing closure_proof tests still work (Phase 182 just adds ActionRegistry logging)
- ✓ REFLEX: New parameters are optional, old calls still work

---

## Security & Data Integrity

1. **ActionRegistry**: Append-only log, immutable once written
2. **Run ID uniqueness**: Timestamp (ms) + task_id (last 8 chars) + random suffix = ~2^64 combinations
3. **Session ID uniqueness**: Timestamp (ms) + 4-byte random = ~2^32 combinations per second
4. **File access**: Closure_files list prevents agent from modifying arbitrary files
5. **Git authorship**: All commits attributed to Verifier role (system agent)

---

## Success Metrics

- ✓ No more index.lock hangs from worktree
- ✓ Each run has traceable action log (ActionRegistry)
- ✓ Each session links all related tasks
- ✓ Verifier controls git (no race conditions)
- ✓ User can see: tests passed, verifier confidence, files changed
- ✓ Timeline persisted: can replay execution flow

---

## References

- Phase 182 Memory: `/Users/danilagulin/.claude/projects/.../memory/phase182_taskboard_as_git.md`
- Verifier Recon: `MARKER_182_VERIFIER_RECON` (this doc)
- Task Board Recon: `MARKER_182_MCC_RECON` (memory file)
- Existing closure protocol: `src/orchestration/task_board.py:1019-1162`
- REFLEX Integration points: `src/services/reflex_integration.py` (IP-1 through IP-7)

---

**Next:** See `ROADMAP_182_184.md` for detailed implementation phases and checklist.
