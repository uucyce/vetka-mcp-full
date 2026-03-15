# Roadmap: Phase 182-184 — Task Board as Git

**Status:** 📋 DRAFT (Ready for Opus Task Creation)
**Target:** 10-12 hours across 3 phases
**Workflow Order:** Agent → Tests → User Verify → Verifier Merge → Auto-Close

---

## Overview: 3-Phase Rollout

| Phase | Focus | Hours | Key Files | Marker Count |
|-------|-------|-------|-----------|--------------|
| **182** | Action Registry + Run ID + Timeline Persistence | 3-4h | action_registry.py, agent_pipeline.py, pipeline_history.py | 12 markers |
| **183** | Session ID + Qdrant Integration + User Verification UI | 4-5h | mycelium_heartbeat.py, reflex_integration.py, VerificationChecklist.tsx | 8 markers |
| **184** | Playground Integration + Merge History + E2E Tests | 2-3h | playground_manager.py, E2E tests, API docs | 5 markers |

---

## Phase 182: Action Registry + Run ID (3-4 hours)

**Goal:** Enable Verifier to merge all agent actions into a single git commit.

### Checklist (Do NOT create tasks yet — Opus will do this)

#### Backend: Action Registry Foundation
- [ ] **182.1 Create ActionRegistry class**
  - [ ] File: `src/orchestration/action_registry.py` (NEW)
  - [ ] MARKER_182.ACTIONREGISTRY: Class definition + methods
  - [ ] `log_action(run_id, session_id, agent, action, file, result, duration_ms, metadata)`
  - [ ] `flush()` → write to `/data/action_log.json`
  - [ ] `get_actions_for_run(run_id)` → list[ActionLogEntry]
  - [ ] `get_actions_for_session(session_id)` → list[ActionLogEntry]
  - [ ] Rotating storage: keep only 10k newest entries
  - [ ] Tests: `test_phase182_action_registry.py` (5-10 basic tests)

- [ ] **182.2 Generate Unique Run IDs**
  - [ ] File: `src/orchestration/agent_pipeline.py` (line ~2725)
  - [ ] MARKER_182.RUNID: Change from `run_id = task_id` to `run_id = f"run_{timestamp}_{task_id[-8:]}_{random}"`
  - [ ] Store `self.run_id` for access throughout pipeline
  - [ ] Store `self.session_id` (will be passed by Phase 183)
  - [ ] Pass both to result dict: `result = {"run_id": ..., "session_id": ..., ...}`
  - [ ] Tests: Verify run_id uniqueness across 100 calls

- [ ] **182.3 Wire ActionRegistry into Pipeline**
  - [ ] File: `src/orchestration/agent_pipeline.py`
  - [ ] MARKER_182.3: Import ActionRegistry
  - [ ] In `execute()` method: instantiate `self.action_registry = ActionRegistry()`
  - [ ] In Architect phase: `self.action_registry.log_action("read", doc_path, "success")`
  - [ ] In Scout phase: `self.action_registry.log_action("read", file_path, "success")`
  - [ ] In Coder phase: After each file write → `self.action_registry.log_action("edit", file_path, "success")`
  - [ ] In Verifier phase: `self.action_registry.log_action("read", code_output, "success")`
  - [ ] On error: `self.action_registry.log_action(..., "failed", metadata={"error": str(e)})`
  - [ ] Tests: Verify all phases log actions correctly

#### Backend: Timeline Persistence
- [ ] **182.4 Persist Timeline Events**
  - [ ] File: `src/api/routes/pipeline_history.py` (append_run method, line ~37)
  - [ ] MARKER_182.5: Add `timeline_events` field to history entry
  - [ ] Modify signature: `append_run(..., timeline_events=None)`
  - [ ] Store full `self._timeline_events` from pipeline
  - [ ] Each event: `{ts, role, event, detail, duration_s}`
  - [ ] Tests: `test_phase182_timeline_persistence.py`

- [ ] **182.5 New API Endpoint: Get Timeline**
  - [ ] File: `src/api/routes/pipeline_history.py` (NEW endpoint)
  - [ ] MARKER_182.TIMELINE_API: `GET /api/pipeline/history/{run_id}/timeline`
  - [ ] Return array of timeline events (from pipeline_history.json)
  - [ ] Include role filter: `?role=architect` or `?role=coder`
  - [ ] Test: Fetch timeline for known run_id

#### Backend: Verifier Merge Logic
- [ ] **182.6 Verifier.verify_and_merge() Method**
  - [ ] File: `src/orchestration/agent_pipeline.py` (NEW method in AgentPipeline class)
  - [ ] MARKER_182.VERIFIER_MERGE: Full method signature
  - [ ] Parameters: `async def verify_and_merge(self, run_id, session_id, task_id)`
  - [ ] Step 1: `ActionRegistry.get_actions_for_run(run_id)` → list of all actions
  - [ ] Step 2: Group by file → `{file: [action, action, ...]}`
  - [ ] Step 3: Prepare commit message → `f"phase182: task {task_id} completed [run:{run_id}]"`
  - [ ] Step 4: MARKER_182.GITPREP: Verify files are written to disk (already done by agent)
  - [ ] Step 5: MARKER_182.GITCOMMIT: Call git.commit() with scoped files (closure_files from TaskBoard)
  - [ ] Step 6: MARKER_182.CLOSURE: Call `board.complete_task(task_id, commit_hash=git_hash)`
  - [ ] Step 7: Flush ActionRegistry → `/data/action_log.json`
  - [ ] Error handling: If git.commit fails, return error (don't close task)
  - [ ] Tests: `test_phase182_verifier_merge.py` (mock git, verify action grouping)

- [ ] **182.7 Integration Point: Task Complete Flow**
  - [ ] File: `src/api/routes/task_routes.py` (complete_task endpoint, line ~240)
  - [ ] When user approves result → trigger `verifier.verify_and_merge()`
  - [ ] OR: Create separate endpoint `POST /tasks/{task_id}/verify-and-merge`
  - [ ] Called after `result_status="applied"` and `closure_proof.tests passed`
  - [ ] Tests: Full flow test task → result → apply → merge

#### Backend: REFLEX Enhancement
- [ ] **182.8 Enhance REFLEX IP-5 (Verifier)**
  - [ ] File: `src/services/reflex_integration.py` (reflex_verifier function, line ~210)
  - [ ] MARKER_182.REFLEX: Add parameters `run_id`, `session_id`, `actions_registry`
  - [ ] Get actions for run: `actions = actions_registry.get_actions_for_run(run_id)`
  - [ ] Map tools → actions: Which tool caused each action?
  - [ ] Calculate success rate per tool: `success_count / total_count`
  - [ ] Log feedback: For each tool, record {tool_id, run_id, task_id, success, confidence}
  - [ ] This feeds back into REFLEX recommendations for next subtask (IP-4)
  - [ ] Tests: Verify tool-action mapping and feedback logging

#### Frontend: Minimal (Phase 182 skips UI, Phase 183 adds it)
- [ ] **182.9 Documentation Updates**
  - [ ] Update CLAUDE.md: Add notes about Action Registry + Run ID
  - [ ] Update pipeline_prompts.json comments: Reference MARKER_182.* locations
  - [ ] Add docstrings to ActionRegistry class

### Summary Checklist: Phase 182
```
Backend Foundation:
  ☐ ActionRegistry class created + tested
  ☐ Run ID generation unique + tested
  ☐ ActionRegistry wired into all phases
  ☐ Timeline events persisted to disk
  ☐ GET /api/pipeline/history/{run_id}/timeline works
  ☐ Verifier.verify_and_merge() implemented
  ☐ REFLEX IP-5 enhanced for run tracking
  ☐ All MARKER_182.* locations documented

Tests:
  ☐ test_phase182_action_registry.py (10+ tests)
  ☐ test_phase182_timeline_persistence.py (5+ tests)
  ☐ test_phase182_verifier_merge.py (10+ tests)
  ☐ test_phase182_reflex_integration.py (5+ tests)

Integration:
  ☐ Agent pipeline generates run_id + logs actions
  ☐ Verifier can merge all actions into single commit
  ☐ Git commits clean (no partial commits)
  ☐ No worktree conflicts

Verification:
  ☐ Run E2E: agent → execution → actions logged → verifier merge
```

---

## Phase 183: Session ID + Qdrant + User Verification UI (4-5 hours)

**Goal:** Link all tasks in one heartbeat as a session. Enable user to verify tests before merge.

### Checklist

#### Backend: Session ID Assignment
- [ ] **183.1 HeartbeatEngine: Session ID Generation**
  - [ ] File: `src/orchestration/mycelium_heartbeat.py` (tick method, line ~45)
  - [ ] MARKER_182.1: Before dispatch loop, generate `session_id = f"sess_{timestamp}_{random}"`
  - [ ] Pass to all `board.add_task()` calls in this tick
  - [ ] Pass to `mycelium_pipeline()` dispatch as context

- [ ] **183.2 TaskBoard: Accept session_id**
  - [ ] File: `src/orchestration/task_board.py` (add_task method)
  - [ ] MARKER_182.2: Add parameter `session_id: Optional[str] = None`
  - [ ] Store in TaskCard: `task["session_id"] = session_id`
  - [ ] Log in status_history: `{ts, event, session_id, ...}`
  - [ ] Tests: Verify session_id stored correctly

- [ ] **183.3 STM Buffer: Metadata Population**
  - [ ] File: `src/memory/stm_buffer.py` (line ~62)
  - [ ] Add session_id to STMEntry metadata: `metadata["session_id"] = session_id`
  - [ ] Now Future coders can query: "What actions happened in session_xyz?"

#### Backend: Qdrant Integration
- [ ] **183.4 ActionRegistry: Write to Qdrant**
  - [ ] File: `src/orchestration/action_registry.py` (flush method)
  - [ ] Create Qdrant collection `actions` if not exists:
    ```python
    {
      "name": "actions",
      "vectors": {"size": 1536, "distance": "Cosine"},
      "payload_schema": {
        "session_id": {"type": "keyword"},
        "run_id": {"type": "keyword"},
        "task_id": {"type": "keyword"},
        "agent": {"type": "keyword"},
        "action": {"type": "keyword"},
        "file": {"type": "text"},
        "result": {"type": "keyword"},
        "timestamp": {"type": "datetime"}
      }
    }
    ```
  - [ ] On flush: For each action, embed file+action: `vector = embed(f"{action} on {file}")`
  - [ ] Insert into Qdrant with payload metadata
  - [ ] Tests: Verify embeddings created, metadata indexed

- [ ] **183.5 New API: Search Actions**
  - [ ] File: `src/api/routes/actions_routes.py` (NEW)
  - [ ] MARKER_183.A: `GET /api/actions/search`
  - [ ] Parameters:
    - `?session_id=...` → All actions in this session
    - `?run_id=...` → All actions in this run
    - `?agent=...` → Filter by agent (opus, cursor, dragon)
    - `?file=...` → Filter by file path
    - `?action=...` → Filter by action type (edit, read, create)
    - `?q=...` → Semantic query (uses Qdrant semantic search)
  - [ ] Return: `{results: [{run_id, session_id, agent, action, file, timestamp, ...}]}`
  - [ ] Tests: Search by session, by file, by agent

#### Frontend: User Verification Checklist
- [ ] **183.6 VerificationChecklist Component**
  - [ ] File: `client/src/components/mcc/VerificationChecklist.tsx` (NEW)
  - [ ] MARKER_182.UIVERIF: Component showing:
    - Tests: `closure_proof.tests[]` array with pass/fail icons
    - Verifier Confidence: Score + threshold comparison
    - Closure Files: List of files to be committed
    - User Actions: [APPROVE] [REQUEST CHANGES]
  - [ ] Show test output (collapsed) with click-to-expand
  - [ ] Color coding: Green (pass), Red (fail), Yellow (threshold close)
  - [ ] Tests: Unit tests for rendering + interaction

- [ ] **183.7 Override Flow (Optional but important)**
  - [ ] File: `client/src/components/mcc/VerificationChecklist.tsx`
  - [ ] MARKER_182.OVERRIDE: "Override + Reason" button
  - [ ] Hidden behind advanced toggle (by default hidden)
  - [ ] Pops form: Text field "Why are you overriding?"
  - [ ] Sends to backend: `POST /tasks/{task_id}/override-verification`
  - [ ] Stores reason in TaskCard: `closure_proof.manual_override_reason`
  - [ ] Tests: Verify override reason stored

- [ ] **183.8 TaskCard Integration**
  - [ ] File: `client/src/components/mcc/TaskCard.tsx`
  - [ ] After agent result arrives + verifier checked → Show VerificationChecklist
  - [ ] Only when `result_status="pending_user_approval"` (new status)
  - [ ] Position: Below result diff view
  - [ ] Tests: Verify checklist appears at right time

- [ ] **183.9 MCC DAGView: Timeline Visualization**
  - [ ] File: `client/src/components/mcc/DAGView.tsx`
  - [ ] When user clicks on task node → Show timeline mini-panel
  - [ ] Timeline shows: All events for this run (from `/api/pipeline/history/{run_id}/timeline`)
  - [ ] Events: Architect (start/end), Scout (start/end), Coder (start/end), Verifier (start/end)
  - [ ] Optionally: Show ActionRegistry entries for this run
  - [ ] Tests: Fetch timeline, render timeline events

#### Backend: API Enhancements
- [ ] **183.10 Task Status: New State "pending_user_approval"**
  - [ ] File: `src/orchestration/task_board.py`
  - [ ] Between "done" and "pending": "pending_user_approval"
  - [ ] Sequence: running → done (verifier checked) → pending_user_approval (waiting for user) → applied (user approved) → done (merged)
  - [ ] Update status constants and lifecycle docs

- [ ] **183.11 Endpoint: Submit Override**
  - [ ] File: `src/api/routes/task_routes.py` (NEW endpoint)
  - [ ] `POST /tasks/{task_id}/override-verification`
  - [ ] Body: `{reason: str}`
  - [ ] Updates TaskCard: `closure_proof.manual_override = true`, `closure_proof.manual_override_reason = reason`
  - [ ] Can then call verify_and_merge even if tests didn't pass
  - [ ] Tests: Verify override recorded

### Summary Checklist: Phase 183
```
Backend Foundation:
  ☐ HeartbeatEngine generates session_id
  ☐ TaskBoard accepts and stores session_id
  ☐ STM Buffer tracks session_id
  ☐ ActionRegistry writes to Qdrant
  ☐ Qdrant collection "actions" created with schema
  ☐ GET /api/actions/search working (all filters)
  ☐ New "pending_user_approval" status
  ☐ POST /tasks/{id}/override-verification endpoint

Frontend:
  ☐ VerificationChecklist component renders
  ☐ Shows closure_proof.tests[] with pass/fail
  ☐ Shows verifier_confidence score
  ☐ Shows closure_files list
  ☐ Override button (hidden, toggle-able)
  ☐ TaskCard shows checklist at right time
  ☐ DAGView shows timeline on node click

Tests:
  ☐ test_phase183_session_tracking.py
  ☐ test_phase183_qdrant_integration.py
  ☐ test_phase183_actions_api.py
  ☐ VerificationChecklist.test.tsx
  ☐ End-to-end: session → task → user verify → merge

Integration:
  ☐ All tasks in one heartbeat linked by session_id
  ☐ User sees verification checklist before merge
  ☐ Qdrant enables semantic search on actions
  ☐ Timeline visible in MCC UI
```

---

## Phase 184: Playground Integration + E2E Tests (2-3 hours)

**Goal:** Complete the workflow — playgrounds linked to tasks, merge history tracked, full E2E tests.

### Checklist

#### Backend: Playground Integration
- [ ] **184.1 Playground Creation: Link to TaskBoard**
  - [ ] File: `src/orchestration/playground_manager.py` (create method)
  - [ ] When playground created → Also create special TaskCard entry
  - [ ] Type: "playground" (not "build/fix/research")
  - [ ] Links: `parent_task_id` (the task this playground is for)
  - [ ] Stores: `playground_id`, `worktree_path`, `branch_name`
  - [ ] Tests: Verify playground task created

- [ ] **184.2 Merge History Tracking**
  - [ ] File: `src/orchestration/playground_manager.py` (merge method)
  - [ ] When merging playground → main: Log to ActionRegistry
  - [ ] Action: `"merge"`, file: `"playground→main"`, metadata: `{playground_id, strategy, files_affected}`
  - [ ] Also store in TaskCard: `playground_merge_history: [{strategy, files, timestamp, commit_hash}]`
  - [ ] Tests: Verify merge logged

- [ ] **184.3 API: List Playgrounds for Task**
  - [ ] File: `src/api/routes/playground_routes.py` (NEW endpoint)
  - [ ] `GET /api/playground?task_id={task_id}`
  - [ ] Returns: List of all playgrounds (active + completed) for this task
  - [ ] Fields: `{playground_id, status, created_at, last_used, files_created, merge_status}`
  - [ ] Tests: Fetch playgrounds for known task

#### Frontend: Playground UI
- [ ] **184.4 TaskCard: Show Linked Playgrounds**
  - [ ] File: `client/src/components/mcc/TaskCard.tsx`
  - [ ] Section: "Related Playgrounds"
  - [ ] Show: Active playground (if any) + history
  - [ ] Link: Click to view playground branch
  - [ ] Tests: Verify playgrounds displayed

#### Testing
- [ ] **184.5 E2E Test: Full Workflow**
  - [ ] File: `tests/e2e/test_phase182_184_workflow.py` (or Playwright)
  - [ ] Scenario:
    1. Create task via heartbeat
    2. Agent claims task (session_id assigned)
    3. Agent executes: creates playground, edits files
    4. ActionRegistry logs all edits
    5. Pipeline completes, result submitted
    6. User verifies checklist, approves
    7. Verifier merges: git commit created, ActionRegistry flushed
    8. Task auto-closed via commit hash
    9. Timeline queryable via API
    10. Qdrant search for actions works
  - [ ] Assertions: Every step leaves traces (tests pass, commits exist, data persisted)
  - [ ] Tests: Run workflow, verify all breadcrumbs

- [ ] **184.6 Unit Tests: Edge Cases**
  - [ ] Test: User rejects result → task goes back to pending
  - [ ] Test: Verifier merge fails (git error) → task stays pending
  - [ ] Test: Override with low test coverage → still merges
  - [ ] Test: Parallel tasks in same session → no conflicts
  - [ ] Test: ActionRegistry grows > 10k → oldest trimmed
  - [ ] Tests: All edge cases covered

- [ ] **184.7 Performance Tests**
  - [ ] Test: ActionRegistry with 1000 entries → query performance
  - [ ] Test: Qdrant search on 10k actions → latency
  - [ ] Test: git commit with 100 files → timing
  - [ ] Benchmark: Before/after Phase 182 commit times
  - [ ] Tests: Performance regressions detected

#### Documentation
- [ ] **184.8 Update Developer Docs**
  - [ ] File: `docs/182_ph_MCC_git/ARCHITECTURE_182_TASKBOARD_AS_GIT.md` (already done)
  - [ ] Add: `IMPLEMENTATION_NOTES.md` — lessons learned, gotchas
  - [ ] Add: `API_REFERENCE.md` — all new endpoints documented
  - [ ] Add: `WORKFLOW_DIAGRAM.md` — visual flow with markers

- [ ] **184.9 Update CLAUDE.md**
  - [ ] Reference Phase 182-184 in agent instructions
  - [ ] Note: ActionRegistry as source of truth for agent actions
  - [ ] Note: Verifier role responsible for git (agents don't touch git)
  - [ ] Note: session_id links related tasks

### Summary Checklist: Phase 184
```
Backend:
  ☐ Playgrounds linked to TaskBoard
  ☐ Merge history tracked in ActionRegistry
  ☐ GET /api/playground?task_id=... works
  ☐ TaskCard stores playground_merge_history

Frontend:
  ☐ TaskCard shows "Related Playgrounds" section
  ☐ Links to playground branches
  ☐ History of merges visible

Testing:
  ☐ Full E2E workflow test (create → execute → verify → merge → auto-close)
  ☐ Edge case tests (reject, fail, override, parallel)
  ☐ Performance tests (ActionRegistry, Qdrant, git)
  ☐ All tests passing

Documentation:
  ☐ IMPLEMENTATION_NOTES.md written
  ☐ API_REFERENCE.md complete
  ☐ CLAUDE.md updated with Phase 182-184 notes
  ☐ All MARKER_182.* locations documented + linked

Integration:
  ☐ Full workflow: Agent → Actions → Verifier → Git → Auto-close
  ☐ User verification working
  ☐ Timeline + Qdrant search working
  ☐ No breaking changes to existing systems
```

---

## Workflow Order (User-Facing)

This is the intended user experience after all 3 phases:

```
1. USER initiates heartbeat in chat
   "@dragon Build feature X, Add tests, Optimize"

   ↓ Backend: HeartbeatEngine.tick()
   └─ session_id = "sess_..."
   └─ 3 tasks created with same session_id
   └─ All tasks dispatched to agents

2. AGENTS execute (parallel or sequential)
   Agent 1: executes task A
   └─ ActionRegistry logs all reads, edits, creates
   └─ run_id = "run_..."
   └─ closure_tests defined
   └─ timeline_events recorded

3. PIPELINE completes
   Agent 1: "I finished task A"
   result: {run_id, timeline, closure_proof, stats}

   ↓ TaskBoard status: running → done
   └─ closure_proof.tests[] populated by run_closure_protocol()
   └─ verifier_confidence = 0.92

4. USER sees VerificationChecklist (NEW in Phase 183)
   ✓ Tests Passed (3/3)
   ✓ Verifier Confidence: 0.92 >= 0.75 ✓
   ✓ Files Declared: src/feature.py, src/test.py

   [APPROVE]  [REQUEST CHANGES]

5. USER: [APPROVE]
   result_status = "applied"

   ↓ Verifier.verify_and_merge() triggered
   └─ ActionRegistry.get_actions_for_run(run_id)
   └─ Group by file
   └─ git commit "phase182: task tb_xxx completed [run:run_xxx]"
   └─ board.complete_task(task_id, commit_hash)

6. TASK auto-closed (MARKER_136.AUTO_CLOSE_COMMIT)
   status = "done"
   MCC shows: "✓ Task completed, merged to main"

7. USER later queries (Phase 183 Qdrant)
   "Show all edits to src/feature.py in session_xxx"
   GET /api/actions/search?session_id=...&file=src/feature.py
   → Returns: 5 edits by agent 1, 2 edits by agent 2, timestamps + content

8. USER looks at timeline
   Click task node in DAGView
   → Timeline popup shows: Architect (2m), Scout (3m), Coder (8m), Verifier (1m)
   → Can drill down: "Show coder actions"
   → Lists: edit src/feature.py (6m), edit src/test.py (2m), ...
```

---

## Risk Mitigation

| Risk | Mitigation | Phase |
|------|-----------|-------|
| ActionRegistry grows unbounded | Trim to 10k oldest entries | 182 |
| Run ID collisions | Use timestamp (ms) + task_id + random | 182 |
| Git commit fails silently | Error handling: return error, don't close task | 182 |
| User forgets to verify | UI makes it mandatory (no "Apply" without checklist) | 183 |
| Qdrant down | ActionRegistry still works (JSON log); search degrades gracefully | 183 |
| Session ID not assigned | Default to None; tasks still work (just not grouped) | 183 |
| Playground merge conflicts | Closure files list prevents accidental overwrites | 184 |
| E2E test flakiness | Mock git/subprocess calls in unit tests, use Playwright for real E2E | 184 |

---

## Success Criteria

After Phase 184, the system should:

1. ✓ **No worktree index.lock errors** — Verifier controls git, agents don't touch it
2. ✓ **Traceable actions** — Every agent action logged with run_id + session_id
3. ✓ **User verification** — Checklist shows tests + confidence before merge
4. ✓ **Clean commits** — One commit per task, with all changes included
5. ✓ **Queryable history** — Search actions by session/run/file/agent via Qdrant
6. ✓ **Timeline visible** — User can see execution flow (architect → coder → verifier)
7. ✓ **Auto-close working** — Git commit hash triggers `complete_task()` automatically
8. ✓ **Playground tracked** — All playgrounds linked to parent task, merge history logged
9. ✓ **REFLEX feedback** — Tool recommendations improved based on action success rates
10. ✓ **Full E2E working** — Agent → Task → Verify → Merge → Auto-close, no manual intervention needed after user approval

---

## Appendix: Marker Reference

All markers from ARCHITECTURE doc, organized by phase:

**Phase 182:**
- MARKER_182.ACTIONREGISTRY: ActionRegistry class definition
- MARKER_182.RUNID: Run ID generation (timestamp + task + random)
- MARKER_182.3: Wire ActionRegistry into pipeline phases
- MARKER_182.4: Emit timeline events in pipeline
- MARKER_182.5: Persist timeline_events to disk
- MARKER_182.VERIFIER_MERGE: Verifier.verify_and_merge() method
- MARKER_182.GITPREP: Prepare git commit from ActionRegistry
- MARKER_182.GITCOMMIT: Execute git commit
- MARKER_182.CLOSURE: Call complete_task() after merge
- MARKER_182.REFLEX: Enhance REFLEX IP-5
- MARKER_182.TIMELINE_API: GET /api/pipeline/history/{run_id}/timeline endpoint

**Phase 183:**
- MARKER_182.1: HeartbeatEngine assigns session_id
- MARKER_182.2: TaskBoard.add_task() accepts session_id
- MARKER_182.UIVERIF: VerificationChecklist.tsx component
- MARKER_182.OVERRIDE: Manual override button + reason form
- MARKER_183.A: New ActionRegistry → Qdrant integration
- MARKER_183.B: GET /api/actions/search endpoint

**Phase 184:**
- Playground linking to TaskBoard
- Merge history tracking
- API: GET /api/playground?task_id=...
- E2E workflow test
- Performance tests

---

**Next:** Opus creates tasks from this checklist. Each task gets a marker prefix.
