# RECON_MULTITASK_PROTOCOL — MCP VETKA (2026-03-11)
Date: 2026-03-11
Owner: Codex

## Scope
- Survey the MCP multitask stack (`TaskBoard`, `AgentPipeline`, SDK bridges) in the current worktree.
- Trace how agents (Codex / Claude / Cursor) claim, complete, and observe tasks today.
- Pinpoint gaps that lead to the reported behavior (old tasks reopening, no clear protocol, digest drift).
- Annotate the codebase with markers/entry points for future automation (history, auto-commit, digest refresh).

## 1. Current multitask stack
### 1.1 Task board storage and status flow
- `data/task_board.json` is the canonical queue. `src/orchestration/task_board.py` owns the schema, valid statuses (`pending`, `queued`, `claimed`, `running`, `done`, `failed`, `cancelled`, `hold`), priority tiers, and the `settings` object (`max_concurrent`, `auto_dispatch`, `default_preset`).
- `_notify_board_update()` fires after every save and emits `task-board-updated`. The front-end listens in `client/src/hooks/useToast.ts` and `client/src/components/mcc/MiniStats.tsx` to keep Codex/Claude dashboards synced without agent-specific IDs.
- `_get_dispatch_semaphore` with `MARKER_133.C33C` enforces concurrent limits. `cleanup_stale()` plus `/api/tasks/cleanup` keep stuck `running`/`claimed` entries moving, but the only signal agents see is the quick reply snapshot described in section 1.3.

### 1.2 Claim/dispatch/complete pipeline
- Task intake is exposed via REST (`src/api/routes/task_routes.py`): `/claimable`, `/take`, `/tasks/{id}/claim`, `/complete`, `/cancel`. `claim_task()` updates `assigned_to/agent_type/assigned_at`; `complete_task()` (and the auto-close hook) only sets `status="done"` without gating on tests. `TaskBoard.auto_complete_by_commit()` runs on every commit but still accepts pending/queued/claimed/running tasks, so the same task can be reopened if the agent forgets to commit.
- Dispatch (`TaskBoard.dispatch_task`) picks the highest-priority `pending`/`queued` task, registers the pipeline via `TaskBoard.register_pipeline`, runs `AgentPipeline.execute`, and writes back `result_summary`/`stats`. The `AgentPipeline` reports `pipeline_stats` and calls `board.record_pipeline_stats()` plus `src/services.task_tracker.on_task_completed()` for digest history (see sections 1.3/1.4). That is the only automated handshake between work (pipeline) and bookkeeping today.

### 1.3 Observability and digest surfaces
- `src/services/myco_memory_bridge.py` reads `_multitask_stats()` (aggregating counts from `data/task_board.json`) and `project_digest.json`, exposes them as `orchestration.multitask`/`digest`, and wires this payload to MYCO quick replies via `src/api/routes/chat_routes.py`. The quick reply shows `multitask: active/queued/done/failed` plus digest phase/status so agents have a lightweight snapshot, but it does not include task history, tests, or the agent who closed a task.
- The digest itself is maintained by `scripts/update_project_digest.py` (phase/headline/achievements derived from git messages, plus Qdrant/MCP status) and patched after successful commits via `src/tools/git_tool.py::_update_digest_after_commit`. `TaskTracker` (`src/services/task_tracker.py`) also appends pipeline completions to `task_tracker.json` and rewrites the digest `key_achievements`; `mycelium_mcp_server` exposes this tracker through `mycelium_track_done / mycelium_tracker_status` for non-pipeline work (Cursor, Claude).

### 1.4 API + UI integration points
- `/api/tasks` routes plus `debug_routes` expose CRUD, concurrency info, and `TaskBoard.cleanup_stale()` so agents can inspect and manipulate the queue without a locked-in ID.
- `mycelium_mcp_server.py` (lines 788‑829) registers the tracker handlers and the pipeline hook (`mycelium_track_done`). The MCP server guests (Claude, Cursor) can signal `on_task_completed` through these tools without direct board access.
- The TaskBoard also serves as the source for workflow templates (`src/api/routes/workflow_template_routes.py`), `src/services/workflow_store.py` conversions, and MCC UI components (`client/src/components/mcc/MyceliumCommandCenter.tsx`), making it the shared bus between agents/projects.

## 2. Issues that trigger the current confusion
1. **No deterministic “task closed” protocol for agents.**
   - `TaskBoard.complete_task()` simply flips `status` to `done` (and optionally records commit info) without verifying `pipeline_stats.success` or `verifier` passes. An agent can mark the task done, but the board, tracker, and digest do not lock in who closed it or why — so Claude sees the same `queued`/`failed` counts and reopens the task. (Bug: there is no guard clause ensuring the completion stems from a pipeline with success=true.)
2. **History/lineage is invisible.**
   - The board retains only the current `status`, `assigned_to`, and a truncated `result_summary` (`TaskBoard.update_task()`), but nothing tracks “opened by”, “closed by”, or “why reopened”. `task_tracker` records completions, but the data is siloed in `task_tracker.json` and not surfaced in the quick reply or API (no `/api/tracker` is exposed to multi-agent consumers yet). Without that story, Codex sees Claude “open an old task” and cannot tell whether it was requeued because of a failure, cleanup, or a mistake. (Gap: we need a shared history field that can be read via `/api/tasks/{id}/history`.)
3. **Project/direction separation is muddy.**
   - Tasks carry `tags`, `module`, `phase_type`, and `preset`, but there is no `project_id` or “lane” field. `_recent_tasks_by_project()` in `myco_memory_bridge` fakes per-project views by matching `load_session_for_project`, but the board itself lets every agent grab any `pending` task, so Codex and Claude step on each other’s projects because there is no enforced routing or ownership metadata. (We observe reopened tasks because the wrong project lane snatches an old ticket.)
4. **Closing a task does not trigger tests → commit → digest cascade automatically.**
   - Agents have to run tests manually, commit, and push to update `project_digest` via the pre-commit hook or `GitTool`. `TaskBoard.auto_complete_by_commit` tries to close tasks mentioned in commit messages, but there is no guarantee that the finished pipeline ran tests or that the task was the subject of the commit. Digest writes from `scripts/update_project_digest.py` rely on human-run scripts (Qdrant/MCP checks call `requests`). The missing automation is the “protocol” the user asked for: close a task only when `AgentPipeline` returns success + tests pass, then push a commit that updates the digest and auto-closes the board entry.

## 3. Proposed fixes / protocol glue
1. **Make task closure a verifiable handshake.**
   - Extend `TaskBoard.complete_task()` (via `MARKER_130.C16A`) to require a `closure_proof` structure (`verifier_confidence`, `tests`, `commit_hash`, `activating_agent`). Agents would not be allowed to call `/complete` manually; the pipeline would call a new helper that checks `pipeline_stats['success']`/`verifier_avg_confidence >= 0.7` before closing. Once closed, trigger `task_tracker`/`scripts/update_project_digest.py` (the same path `src/tools/git_tool.py::_update_digest_after_commit` already touches). This ensures the digest, tracker, and TaskBoard move together and the next agent sees a clean pipeline snapshot.
2. **Surface a per-task history/agent log.**
   - Use `TaskBoard.update_task()` to append entries to a `status_history` list (`created`, `claimed`, `run`, `failed`, `cancelled`, `done`). Each entry can record `agent_name`, `agent_type`, timestamp, source (Codex, Claude, Cursor), and a short reason. Expose the history via a new `/api/tasks/{id}/history` endpoint (hook into the same router used for `/results`) so Codex can fetch “who reopened this task?” before touching it. This satisfies the “visible history” requirement without hard wiring IDs.
3. **Segment tasks by project/direction.**
   - Add `project_id`, `project_lane`, or `workflow_family` metadata when tasks are created (`TaskBoard.add_task` and `workflow_template_routes` already tag tasks with `workflow_family`). Then extend `_recent_tasks_by_project()` and the quick reply to respect those lanes, ensuring Claude only sees tasks in the project it opened. The existing `_recent_tasks_by_project` already iterates over `list_projects()`; reusing `project_id` plus the stored `active_project_id` would make the board lane-aware.
4. **Auto-run commit + digest update when closing tasks.**
   - After a pipeline declares success, invoke `GitTool` (or reuse `scripts/update_project_digest.py`) to: run a targeted test suite, stage the changes, commit with `[Task tb_x]` in the message, and push if allowed. The commit hooks already call `auto_sync_from_git`; keep using them but ensure the `GitTool` returns `commit_hash`. Pass that hash into `TaskBoard.complete_task()` and into `task_tracker`. If tests fail, the pipeline should leave the task `failed` and emit `result_summary` explaining the failure. This matches the “task closed by agent with successful tests → commit → digest update” flow requested.

## 4. Key markers / integration knobs
- `MARKER_130.C16A` (`src/orchestration/task_board.py`): extend agent metadata (new `status_history`, `closed_by`, `closure_proof`).
- `MARKER_133.C33C` (same file): concurrency semaphore already limits max pipelines; hook a `state_bump` there to log multi-task transitions.
- `MARKER_126.0A` / `MARKER_133.TRACKER` (`agent_pipeline.py` / `task_tracker.py`): there is already a hook for pipeline stats and tracker updates. Use it to capture the “successful tests + commit” handshake.
- `MARKER_162.P3.P2.MYCO.ORCHESTRATION_SNAPSHOT.V1` (`myco_memory_bridge.py`): add fields like `history_age`, `last_closed_by`, `project_lane` so quick replies show the new protocol data.
- `MARKER_171.P1.MYCO.MULTITASK_STATUS_SPLIT.V1`: the heartbeat already emits `failed` counts; extend `_multitask_stats` to expose `status_history` summary for watchers.

## 5. Dependencies to monitor
- Storage: `data/task_board.json`, `data/project_digest.json`, `data/task_tracker.json`, `data/pipeline_tasks.json`.
- Core logic: `src/orchestration/task_board.py`, `src/orchestration/agent_pipeline.py`, `src/orchestration/taskboard_adapters.py`, `src/orchestration/playground_manager.py` (for special workflows).
- Observability: `src/services/task_tracker.py`, `src/services/myco_memory_bridge.py`, `src/api/routes/chat_routes.py`, `src/api/routes/task_routes.py`, `src/mcp/mycelium_mcp_server.py`, `src/tools/git_tool.py`, `scripts/update_project_digest.py`.
- Front-end sinks: `client/src/components/mcc/MyceliumCommandCenter.tsx`, `client/src/hooks/useToast.ts`, `client/src/hooks/useMCCDiagnostics.ts`, `client/src/components/mcc/MiniStats.tsx`.
- Tests/contracts: `tests/test_phase121_task_board.py`, `tests/test_phase130_agent_coordination.py`, `tests/test_phase171_multitask_digest_contract.py`, `tests/test_task_tracker.py`.

## 6. Bugs / unexpected behaviors
- **Bug:** The only code path that auto-closes tasks (`TaskBoard.auto_complete_by_commit`) accepts `pending` and `queued` tasks, so a tug-of-war between Codex and Claude can keep flipping the same entry without any history; there is no check that the task was actually his current focus or that the preceding pipeline succeeded (see `TaskBoard.auto_complete_by_commit()` lines 626‑657).
- **Gap:** `TaskBoard.complete_task()` can be called manually via `/api/tasks/{id}/complete` even when no commit/tests happened, so the board prematurely marks tasks done. We need to gate this route, ideally by forcing agents to route through the pipeline (section 3.1). Otherwise “locking in tests” never occurs.

