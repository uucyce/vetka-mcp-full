# PHASE 168 — W9.B MYCO MCC Probe Contract

Date: 2026-03-09
Status: recon + contract frozen
Protocol stage: RECON+markers -> REPORT -> WAIT GO

Related docs:
- `docs/168_ph_videoplayer/PHASE_168_MYCO_MOTION_ASSET_PIPELINE_RECON_2026-03-09.md`
- `docs/168_ph_videoplayer/MYCO_MOTION_DEV_UI_TOOL_V1.md`
- `docs/164_MYCO_ARH_MCC/PHASE_164_P0_UI_SURFACE_FULL_MAP_2026-03-07.md`
- `docs/164_MYCO_ARH_MCC/PHASE_164_P4_WINDOW_TRIGGER_MATRIX_RECON_2026-03-08.md`

## 1. Goal

Define a dedicated MCC-side probe for MYCO motion assets.

This probe is separate from the existing player-lab probe:

- player-lab probe validates geometry/fit for raw media assets,
- MCC probe validates readability, dominance, trigger transitions, and layout stability inside real MCC UI surfaces.

## 2. Why Existing Probe Is Not Enough

The existing player probe already proves:
- aspect fit,
- shell sizing,
- letterbox,
- chrome ratio.

It does **not** prove:
- compact panel readability,
- visual competition with DAG and text,
- trigger-state switching quality,
- multi-role coexistence (`coder`, `scout`),
- surface-specific motion noise.

## 3. Target Runtime Surfaces

Current MCC seams confirmed in code:

1. top MYCO avatar
- `client/src/components/mcc/MyceliumCommandCenter.tsx`
- current states: `idle`, `ready`, `speaking`

2. top MYCO hint bubble
- `client/src/components/mcc/MyceliumCommandCenter.tsx`

3. MiniChat compact helper avatar/header
- `client/src/components/mcc/MiniChat.tsx`

4. MiniChat expanded helper avatar/header
- `client/src/components/mcc/MiniChat.tsx`

5. MiniStats compact workflow panel
- `client/src/components/mcc/MiniStats.tsx`

6. MiniStats expanded workflow panel
- `client/src/components/mcc/MiniStats.tsx`

Deferred surfaces:
- role picker / workflow roster view
- future task workflow bank card media

## 4. Surface Probe Questions

Each surface must answer:

1. Fit
- does the asset fit the slot without clipping?

2. Readability
- does nearby text remain readable?

3. Dominance
- does the asset overpower the panel?

4. Jitter
- does switching trigger state move or resize layout?

5. Identity
- is the role visually distinguishable in its intended slot?

6. Parallel separation
- if two coders or multiple scouts are present, are they still separable?

## 5. Trigger Matrix For Probe

The probe must cover these trigger classes:

1. `idle`
- no active reply, no fresh event

2. `ready`
- focused / armed / contextual but not actively speaking

3. `speaking`
- MYCO reply or active assist pulse

4. `window_focus_*`
- `chat`
- `context`
- `stats`
- `tasks`
- `balance`

5. `workflow_selected`
- user explicitly selected workflow in `Stats`

6. `model_selected`
- architect or task role model changed

7. `task_started`
- active task moved to running

8. `task_completed`
- active task moved to done

9. `task_failed`
- active task moved to failed

10. `parallel_role_active`
- second coder or second scout activated in the same runtime slice

## 6. Role Rules

Singleton roles:
- `architect`
- `researcher`
- `verifier`

Parallel-allowed roles:
- `coder` (up to 2)
- `scout` (up to 3 source variants, but runtime should still cap visible concurrency explicitly)

Probe contract implication:
- singleton surfaces only need single-asset validation
- coder/scout surfaces must include a dual/parallel scenario

## 7. Machine-Readable Contract

Machine-readable source of truth:
- `docs/contracts/myco_mcc_motion_probe_contract_v1.json`

This contract is intended to drive:
- future screenshot plans,
- trigger-state scenario generation,
- MCC probe test fixtures.

## 8. Expected Probe Outputs

For every probe run, produce:

1. screenshot artifacts
- one image per surface/state pair

2. JSON metrics
- slot width/height
- visible media bounds
- clip ratio
- text overlap ratio
- motion dominance score
- layout delta between states

3. summary matrix
- pass / warn / fail per surface/state

4. stable markers
- for later CI or local review automation

## 9. Proposed Markers

- `MARKER_168.MYCO.MOTION.MCC_PROBE.CONTRACT.V1`
- `MARKER_168.MYCO.MOTION.MCC_PROBE.SURFACES.V1`
- `MARKER_168.MYCO.MOTION.MCC_PROBE.TRIGGERS.V1`
- `MARKER_168.MYCO.MOTION.MCC_PROBE.PARALLEL_ROLES.V1`
- `MARKER_168.MYCO.MOTION.MCC_PROBE.ARTIFACTS.V1`

## 10. Acceptance Gate Before Runtime Wiring

Do not wire motion assets into live MCC role triggers until:

1. asset pack exists and is reproducible,
2. MCC probe contract exists,
3. surface list is frozen,
4. trigger matrix is frozen,
5. at least one automated contract test protects the matrix,
6. future probe implementation can generate reproducible artifacts.
