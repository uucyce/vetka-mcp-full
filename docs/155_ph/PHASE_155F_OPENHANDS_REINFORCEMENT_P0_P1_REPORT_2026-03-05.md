# PHASE 155F — OpenHands Reinforcement P0/P1 Report (2026-03-05)

Status: `IMPL NARROW + VERIFY`

## Scope delivered

1. `P0`: reinforcement policy contract added to template selector layer.
2. `P1`: selector now returns base workflow + OpenHands reinforcement overlay, without introducing a new default family.

## Markers implemented

1. `MARKER_155F.OPENHANDS.REINFORCEMENT_POLICY.V1`
2. `MARKER_155F.OPENHANDS.ARCHITECT_SELECTOR_RULES.V1`
3. `MARKER_155F.OPENHANDS.STUB_OPTIONAL_NOT_DEFAULT.V1`

## Code changes

1. `src/services/architect_prefetch.py`
- added workflow family normalization on load (`workflow_family` + default strict policy).
- added `list_families()` contract output.
- expanded `select_workflow(..., task_description=...)` for description-level routing.
- added `select_workflow_with_policy(...)` returning:
  - `workflow_key`
  - `reinforcement`
  - `reinforcement_policy`
- added OpenHands reinforcement inference (approval/sandbox/recovery/diff signals).
- `ArchitectPrefetch.prepare(...)` now writes reinforcement metadata into context and summary.

2. `tests/test_phase155f_openhands_reinforcement_policy.py` (new)
- verifies base workflow remains intact while reinforcement flags are attached.
- verifies overlay can remain off when no OpenHands signals.
- verifies prefetch context exposes reinforcement metadata.

## Verification

Executed:
1. `pytest -q tests/test_phase155e_p3_template_family_registry.py tests/test_phase155f_openhands_reinforcement_policy.py`
2. `pytest -q tests/test_phase155b_p3_5_template_library.py -k "template_library_includes_new_core_templates or select_workflow_supports_ralph_and_g3"`

Results:
1. `6 passed` (phase155e_p3 + phase155f policy)
2. `2 passed, 1 deselected` (phase155b_p3_5 subset)

Note:
- existing test `test_workflow_architect_uses_template_first_without_llm` remains unstable in this branch snapshot due fallback path in `workflow_architect` and is outside this narrow reinforcement change.

## Outcome

OpenHands is now represented as policy reinforcement over existing families, not as a competing default workflow family.

