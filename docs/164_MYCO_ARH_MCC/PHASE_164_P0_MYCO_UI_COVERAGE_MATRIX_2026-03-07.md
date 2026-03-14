# PHASE 164 — P0 MYCO UI Coverage Matrix (2026-03-07)

Status: `IMPL NARROW` (doc-contract only)  
Markers:
- `MARKER_164.P0.MYCO_UI_COVERAGE_MATRIX.V1`
- `MARKER_164.P0.MYCO_UI_ACTION_CATALOG.V1`

## Coverage Legend
1. `YES` — behavior and guidance already represented in current MYCO rules/messages.
2. `PARTIAL` — represented, but not enough depth or missing role split.
3. `NO` — not represented in existing MYCO guide/runtime prompts.

## Matrix

| Surface group | Element | MYCO short guidance | Architect detail guidance | Coverage |
|---|---|---|---|---|
| Top bar | project tabs | YES | PARTIAL | PARTIAL |
| Top bar | `+ project` | PARTIAL | PARTIAL | PARTIAL |
| Top bar | MYCO avatar handoff | YES | YES | YES |
| Top bar | hint capsule | YES | PARTIAL | PARTIAL |
| DAG | node select | YES | YES | YES |
| DAG | drill into workflow/module | YES | PARTIAL | PARTIAL |
| DAG | task overlay interpretation | PARTIAL | PARTIAL | PARTIAL |
| DAG menu | add node | PARTIAL | NO | PARTIAL |
| DAG menu | create task here | PARTIAL | PARTIAL | PARTIAL |
| DAG menu | approve suggested anchor | PARTIAL | PARTIAL | PARTIAL |
| DAG menu | delete edge | NO | NO | NO |
| Tasks | select active task | YES | PARTIAL | PARTIAL |
| Tasks | start task | YES | PARTIAL | PARTIAL |
| Tasks | stop task | PARTIAL | PARTIAL | PARTIAL |
| Tasks | heartbeat controls | PARTIAL | PARTIAL | PARTIAL |
| Chat | architect mode separation | YES | YES | YES |
| Chat | helper mode separation | YES | YES | YES |
| Chat | proactive state updates | PARTIAL | PARTIAL | PARTIAL |
| Context | agent model change | YES | PARTIAL | PARTIAL |
| Context | prompt preview semantics | PARTIAL | PARTIAL | PARTIAL |
| Context | file/directory interpretation | PARTIAL | PARTIAL | PARTIAL |
| Stats | scope metrics explanation | PARTIAL | PARTIAL | PARTIAL |
| Balance | key/provider implications | PARTIAL | PARTIAL | PARTIAL |
| Dock | restore flow guidance | PARTIAL | PARTIAL | PARTIAL |

## Gaps Requiring P1/P2
1. No full role-aware split for:
- Project Architect instruction layer
- Task Architect instruction layer
2. No exhaustive guidance for context menu edge actions.
3. No deep procedural guide for heartbeat orchestration and retry loops.
4. No complete workflow-family guidance map in UI terms:
- Dragons
- Titans
- G3
- Ralph loop
- custom workflow

## Exit Criteria for P0
1. Full surface map documented.
2. Action catalog documented for all key controls.
3. Coverage matrix identifies exactly where P1/P2 implementation must bind.

Result: `P0 exit criteria met` (doc baseline ready for `P1` implementation).
