# MARKER_170_MULTITASK_DIGEST_DOCTOR_RECON_AND_CLEANUP_2026-03-09

## Scope
- Recon: multitask + digest coupling in VETKA/MYCO.
- Recon: `@doctor` routing from chat to task execution.
- Cleanup: remove closed/test task noise from `data/task_board.json`.

## Findings: Multitask vs Digest

Source:
- `src/services/myco_memory_bridge.py`

Observed:
- `_multitask_stats()` reads `data/task_board.json` and computes:
  - `total`, `done`, `active`, `queued`, `phase`, `max_concurrent`, `auto_dispatch`.
- `_digest_snapshot()` reads `data/project_digest.json`.
- Both are merged into one orchestration payload in `build_myco_memory_payload()`:
  - `orchestration.multitask`
  - `orchestration.digest`

Implication:
- Multitask is effectively a live queue snapshot after digest, not a replacement for digest.
- This is the right layering for orchestration of adjacent/dependent coder branches.

## Findings: `@doctor` in chat

### Mention parsing
- `src/agents/agentic_tools.py`
  - `SYSTEM_COMMAND_AGENTS = {"dragon", "doctor", "mycelium", "pipeline", "help"}`
  - mention mode becomes `system_command`.

### Solo VETKA chat path
- `src/api/handlers/user_message_handler.py`
  - `parse_mentions()` in main user flow.
  - `_dispatch_solo_system_command(...)` launches `AgentPipeline` directly.

Important nuance:
- Solo `@doctor` path does **not** inherently create a TaskBoard task first.
- It executes pipeline directly unless upstream logic explicitly dispatches through TaskBoard.

### Group chat path
- `src/api/handlers/group_message_handler.py`
  - `_doctor_triage(...)` runs triage, then creates TaskBoard entry via `board.add_task(...)`.
  - Abstract tasks go `hold`, concrete/moderate tasks go pending quick-actions.

Implication:
- Group `@doctor` is task-board-native.
- Solo `@doctor` is pipeline-direct.

## Cleanup Performed

File changed:
- `data/task_board.json`

Backup created:
- `data/backups/task_board_before_closed_cleanup_20260309_061713.json`

Action:
- Removed all tasks with `status == done` (closed tasks).
- Kept non-closed tasks (`queued`/`failed`) for follow-up.

Counts:
- Before: `51` tasks (`43 done`, `6 queued`, `2 failed`)
- After: `8` tasks (`6 queued`, `2 failed`)

Remaining open/attention tasks:
1. `tb_1770577538_9` queued — Research: search/embedding model categories
2. `tb_1770809271_3` queued — S1.3 Unified Search Cmd+K wiring
3. `tb_1770809279_6` queued — S1.6 Tests heartbeat/search integration
4. `tb_1771092048_3` queued — D-149.3 Sandbox toggle in TaskCard dispatch
5. `tb_1771092050_4` queued — D-149.4 HeartbeatChip + PlaygroundBadge wiring
6. `tb_1771092080_6` queued — C-149.2 Tavily provider wiring
7. `tb_1771352905_9` failed — build new API endpoint
8. `tb_1772075324_9` failed — build new API endpoint

## What to improve next

1. Unify doctor intake behavior:
   - Route solo `@doctor` through TaskBoard triage path (same semantics as group).
2. Add archive lane for closed tasks:
   - move `done/cancelled` to `task_board_archive.json` instead of hard delete.
3. Normalize digest snapshot shape:
   - `_digest_snapshot()` currently stringifies nested dicts; expose structured fields (`phase.number`, `phase.status`, short headline).
4. Add board hygiene job:
   - daily cleanup rule for stale `done` and duplicate `failed` heartbeat artifacts.
