# PHASE 171 Multitask / MCC Project-Lane Recon (2026-03-13)
Date: 2026-03-13  
Owner: Codex

## Context
- `TaskBoard.add_task` still limits `phase_type` to `build|fix|research` even though tests are a distinct flow, so any QA or test-focused ticket continues to ride the `build` bucket (`src/orchestration/task_board.py:412-470`). That folds test work into analytics that already mix builds, which obscures remaining test-specific metrics.
- MCC, MYCELIUM, and desktop agents now consume the shared `TaskBoard` via `/api/mcc/tasks`/`/api/tasks`. Adding `phase_type=test` there would give every UI and agent a clearer hook to differentiate automated vs. delivery work.
- P6-level work already benefits from stronger proofs (`architecture_docs`, `closure_tests`) that track closure provenance. Those fields exist on the task payload, so the agents just need the discipline to pre-populate them when the story is opened.

## What to improve next
1. **Add `phase_type='test'` to TaskBoard validation**  
   - `add_task` and any schema that filters `phase_type` need to accept `test` in addition to `build|fix|research`, so MCC branches and filters can carve test streams without pretending they are builds.  
   - Ensure downstream corners (`/api/tasks`, MCC schema, quick replies) propagate that new value to dashboards/filters.
2. **Bind P6 work to closure proof metadata immediately**  
   - When adding or templating a P6 task, fill `architecture_docs` with the relevant phase docs, and inject the expected `closure_tests` array so the agent knows right away what suite must pass before the closure handshake runs (`src/orchestration/task_board.py:508-549`).  
   - The new `/api/tasks/{id}/history` endpoint should reflect those expectations so reviewers can see whether the architecture docs/tests were attached prior to completion.
3. **Document how MCC project lanes land on TaskBoard metadata**  
   - Each lane is already captured via `project_lane/project_id` in the TaskBoard payload and mirrored in the MCC + myco view funnels. Capture that mapping in the playbook so new tabs create the appropriate `project_lane` and reuse the same `architecture_docs`/`recon_docs`.

## Git mirror thought exercise – `project_lane -> branch/worktree`
1. **Pros**
   - Explicit per-lane isolation mirrors the DAG branches: each project lane can push to a dedicated branch/worktree, making review + rollback deterministic.
   - Digest and closure proofs can tie directly to a commit hash per lane, so MCC/MYCELIUM can show “this branch delivered the lane” in the task history.
2. **Cons**
   - More branches require stricter coordination; the protocol you just added already assumes a single commit per task, so multi-branch pushes would need extra merge/CI rules.  
   - Switching lanes via git worktrees still exposes shared files, so stray cross-lane edits can slip in unless the worktree setup enforces targeted `closure_files`.

## Next steps
1. Expand `TaskBoard` phase validation + MCC schema to include `test` and propagate it through the REST contracts.
2. Update the P6 workflow templates to attach architecture docs and closure tests before dispatching tasks.
3. Capture the `project_lane -> branch` guidance in the MCC onboarding doc referenced above so every new tab enforces the same git discipline.
