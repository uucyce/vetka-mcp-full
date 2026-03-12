# PHASE 155F — OpenHands Reinforcement Recon (2026-03-05)

Status: `RECON + markers`  
Protocol: `RECON+markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`

## 1) Scope

Track #2 from planning:
1. Decide OpenHands role in MCC (separate workflow family vs reinforcement patterns).
2. Produce implementation-ready direction with markers.

## 2) Evidence reviewed

1. `docs/155_ph/PHASE_155E_CLOSEOUT_REPORT_2026-03-03.md`
2. `docs/155_ph/PHASE_155E_P3_TEMPLATE_FAMILY_REGISTRY_REPORT_2026-03-03.md`
3. `src/services/architect_prefetch.py`
4. `data/templates/workflows/openhands_collab_stub.json`
5. `data/templates/workflows/pulse_scheduler_stub.json`

## 3) Current factual state

1. OpenHands already exists as stub template:
- `openhands_collab_stub.json`
- family metadata: `openhands_family`
- policy marked as `stub: true`

2. Registry/selection substrate exists, but selector in `WorkflowTemplateLibrary.select_workflow(...)` currently routes mainly to:
- `quick_fix`, `test_only`, `docs_update`, `refactor`, `research_first`, `bmad_default`.
- no first-class reinforcement scoring path for OpenHands patterns.

3. Existing docs already defer final decision:
- `MARKER_155E.WF.FAMILY.OPENHANDS_AS_REINFORCEMENT.V1` (explicitly deferred).

## 4) Decision (recon verdict)

Recommended direction: **OpenHands as reinforcement, not separate default family**.

Meaning in MCC terms:
1. Keep core families (`BMAD/G3/Ralph`) as primary runtime behaviors.
2. Use OpenHands patterns as policy modifiers for Architect planning and execution governance:
- terminal/sandbox discipline,
- approval/review loop hygiene,
- recovery behavior,
- diff-first handoff patterns.
3. Preserve existing OpenHands stub as optional explicit template, but not default router target.

## 5) Reinforcement map into existing families

1. BMAD reinforcement:
- add explicit approval checkpoints + structured patch review hints.

2. G3 reinforcement:
- strengthen critic/coder adversarial loop with bounded retry + clearer failure semantics.

3. Ralph-loop reinforcement:
- add safety rails for single-agent loop recovery and audit trail.

## 6) Marker pack for implementation

1. `MARKER_155F.OPENHANDS.REINFORCEMENT_POLICY.V1`
2. `MARKER_155F.OPENHANDS.REINFORCEMENT_IN_BMAD.V1`
3. `MARKER_155F.OPENHANDS.REINFORCEMENT_IN_G3.V1`
4. `MARKER_155F.OPENHANDS.REINFORCEMENT_IN_RALPH.V1`
5. `MARKER_155F.OPENHANDS.STUB_OPTIONAL_NOT_DEFAULT.V1`
6. `MARKER_155F.OPENHANDS.ARCHITECT_SELECTOR_RULES.V1`

## 7) Narrow implementation plan (next go)

P0:
1. Extend template metadata policy contract (`workflow_family.policy`) with reinforcement flags.
2. Do not create new mandatory family in selector.

P1:
1. Update `WorkflowTemplateLibrary.select_workflow(...)` to apply reinforcement policy overlays based on task type/complexity, without replacing base family selection.

P2:
1. Expose reinforcement decision in API payload (diagnostics field), so MCC UI can show why this policy was applied.

P3:
1. Add focused tests for selector behavior and policy overlay determinism.

## 8) Risks and controls

1. Risk: silent behavior drift if reinforcement changes template semantics too aggressively.
- Control: reinforcement must be additive/diagnostic first; base topology untouched unless explicitly versioned.

2. Risk: user confusion from too many family modes.
- Control: keep one default path; OpenHands remains optional advanced modifier.

## 9) Recon conclusion for Track #2

1. OpenHands should be integrated as reinforcement layer over existing families.
2. No need to promote OpenHands to independent default workflow family at this stage.
3. This aligns with previously deferred marker and preserves Grandma mode simplicity.

