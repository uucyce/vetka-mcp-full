# MARKER_171.P1 — Multitask + Digest + VETKA MCP (Report)

Date: 2026-03-09
Owner: Codex

## Scope
- Harden MYCO digest snapshot for structured payloads.
- Split multitask status signal so `failed` is not mixed into `queued`.
- Surface failed counter in MYCO quick reply.
- Validate with focused tests.

## Recon Summary
- `src/services/myco_memory_bridge.py`:
  - `_digest_snapshot` previously stringified dict-like fields (`summary/phase/status`) into noisy blobs.
  - `_multitask_stats` previously grouped all non-`done`/`active` into `queued`, mixing `failed/cancelled`.
- `src/api/routes/chat_routes.py`:
  - MYCO quick reply consumed multitask stats but did not expose explicit failed signal.
- `data/task_board.json` current state (after cleanup baseline):
  - total tasks: `8`
  - statuses: `queued=6`, `failed=2`, `done=0`

## Implemented Changes

### 1) Digest normalization
File: `src/services/myco_memory_bridge.py`
Marker: `MARKER_171.P1.MYCO.DIGEST_NORMALIZE.V1`

- Normalized dict payloads for `summary`, `phase`, `status`.
- Added structured fields to digest snapshot:
  - `phase_number`
  - `phase_subphase`
  - `phase_name`
  - `phase_status`
- Preserved compact fallback behavior for string payloads.

### 2) Multitask status split
File: `src/services/myco_memory_bridge.py`
Marker: `MARKER_171.P1.MYCO.MULTITASK_STATUS_SPLIT.V1`

- Added `failed` counter in multitask snapshot.
- Counted `claimed` as `active`.
- Routed `failed/cancelled` into `failed` bucket (not `queued`).

### 3) MYCO quick reply signal
File: `src/api/routes/chat_routes.py`

- Parsed `multitask.failed`.
- Added explicit line in quick-help reply:
  - `multitask errors: failed N`
- Extended full summary line:
  - `active ... queued ... done ... failed ...`

## Tests
Added: `tests/test_phase171_multitask_digest_contract.py`

Covered contracts:
1. `_multitask_stats` splits `failed` from `queued` and counts `claimed` as active.
2. `_digest_snapshot` normalizes dict payload fields and emits structured phase keys.
3. `_build_myco_quick_reply` includes failed counter line.

Run results:
- `pytest -q tests/test_phase171_multitask_digest_contract.py` -> `3 passed`
- `pytest -q tests/test_phase162_p3_p2_orchestration_memory_contract.py tests/test_phase162_p3_p4_retrieval_quality_contract.py` -> `8 passed`

## Notes for orchestration
- This improves MCC/VETKA orchestration readability: queued backlog and failed/error pressure are now separated.
- Digest payload is now machine-friendly for agents that consume phase metadata.
