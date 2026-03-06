# CODEX Phase 161 — MCC TRM Master Plan

Protocol: `RECON+markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`
Status: `ROADMAP READY`
Date: 2026-03-04

## Objective
Build `Algorithmic Offload v2` for DAG quality: from arbitrary project/array inputs to stable, readable architecture DAG using current deterministic pipeline + TRM-assisted refinement.

## Non-Goals (Phase 161)
- No replacement of current SCC/design backbone in one shot.
- No mandatory JEPA dependence for DAG build success.
- No workflow-execution changes (teams/commands runtime out of scope here).

## Architecture Target

### Current (stable)
`scope/array -> runtime graph -> design graph -> verifier -> versions/compare -> UI`

### Phase 161 target
`scope/array -> runtime graph -> design graph (baseline) -> TRM refine candidates -> verifier gate -> compare/versioned output -> UI source badge`

TRM stage is optional and policy-gated.

## Workstreams

### W1. Contracts and config (P161.1)
Deliverables:
- `src/services/mcc_trm_config.py` (new)
- request schema extension in `mcc_routes.py`
- response metadata extension (`trm_meta`, `graph_source`)

Markers:
- `MARKER_161.TRM.CONFIG.CONTRACT.V1`
- `MARKER_161.TRM.API.BUILD_DESIGN_INPUT.V1`
- `MARKER_161.TRM.API.BUILD_FROM_ARRAY_INPUT.V1`

Acceptance:
- build endpoints accept TRM policy block without behavior change when disabled.
- defaults preserve existing outputs.

### W2. TRM adapter + feature bridge (P161.2)
Deliverables:
- `src/services/mcc_trm_adapter.py` (new)
- deterministic feature extraction from design/runtime graph
- adapter returns candidate edge/rank/root adjustments (not direct mutation)

Markers:
- `MARKER_161.TRM.ADAPTER.ENTRY.V1`
- `MARKER_161.TRM.ADAPTER.FEATURE_BRIDGE.V1`
- `MARKER_161.TRM.ADAPTER.CANDIDATES.V1`

Acceptance:
- adapter deterministic under fixed seed/config.
- failures degrade to no-op refine (baseline path).

### W3. Builder integration gate (P161.3)
Deliverables:
- integrate adapter in `build_design_dag` and `build_design_dag_from_arrays`
- verifier-aware arbitration policy (`apply if pass/warn and no invariant break`)

Markers:
- `MARKER_161.TRM.BUILDER.ENTRY.V1`
- `MARKER_161.TRM.BUILDER.REFINE_GATE.V1`
- `MARKER_161.TRM.BUILDER.EXIT_PAYLOAD.V1`

Acceptance:
- no cycles introduced by refinement.
- layer monotonicity preserved.
- payload includes refinement diagnostics and marker trail.

### W4. Compare harness and persistence (P161.4)
Deliverables:
- extend compare variants with TRM profiles (`baseline`, `trm_light`, `trm_balanced`)
- persist TRM config + quality deltas in version metadata

Markers:
- `MARKER_161.TRM.COMPARE.VARIANT_POLICY.V1`
- `MARKER_161.TRM.COMPARE.SCORECARD_EXT.V1`
- `MARKER_161.TRM.VERSION_META.V1`

Acceptance:
- auto-compare returns ranked variants including TRM ones.
- `dag-versions/list` summaries keep stable contract and include marker evidence.

### W5. UI observability (P161.5)
Deliverables:
- source badge shows refined origin (`trm_refined`)
- lightweight diagnostics chip in DAG window (profile, passes, accepted/rejected candidates)

Markers:
- `MARKER_161.TRM.UI.SOURCE_BADGE.V1`
- `MARKER_161.TRM.UI.RENDER_GUARD.V1`

Acceptance:
- user can distinguish baseline vs TRM-refined graph visually.
- UI does not rewrite backend topology.

### W6. Tests + golden corpus (P161.6)
Deliverables:
- `tests/mcc/test_mcc_trm_contract.py`
- `tests/mcc/test_mcc_trm_compare_profiles.py`
- `tests/mcc/test_mcc_trm_determinism.py`
- `tests/mcc/fixtures/trm_golden/*` (small synthetic + real-like fixtures)

Markers:
- `MARKER_161.TRM.TEST.CONTRACT.V1`
- `MARKER_161.TRM.TEST.COMPARE.V1`
- `MARKER_161.TRM.TEST.DETERMINISM.V1`

Acceptance:
- deterministic snapshot equality for fixed fixture+seed.
- verify no invariant regressions vs baseline.

### W7. Multi-project tab shell (P161.7)
Deliverables:
- backend project registry + active-project selection API
- UI tab row (`project tabs + create tab`) without extra panel clutter
- active-tab scope binding for DAG/build/compare flows
- strict UI style policy for tabs/popovers (monochrome + existing palette/font tokens only)
- modal close policy: keyboard `Esc` closes new-project modal (no visible Cancel button)

Markers:
- `MARKER_161.7.MULTIPROJECT.REGISTRY.RECON.V1`
- `MARKER_161.7.MULTIPROJECT.API.INIT_ACTIVE_PROJECT.V1`
- `MARKER_161.7.MULTIPROJECT.UI.ACTIVE_PROJECT_STATE.V1`
- `MARKER_161.7.MULTIPROJECT.UI.TAB_SCOPE_BIND.V1`

Acceptance:
- tab switch changes active project scope deterministically.
- legacy single-project flow remains functional.
- active tab is visually connected to workspace container (clear “which tab is active” affordance).
- no non-token colors/icons/fonts introduced in tab shell and related popovers.

### W8. Grandma in-interface creation flow (P161.8)
Deliverables:
- disable modal onboarding in active MCC flow
- `+ project` opens in-canvas `first_run` creation surface
- draft tab opens as empty workspace (no DAG) with default mini-window placeholders
- delayed setup overlay on top of draft tab (source -> workspace)
- simplified source step labels (`From Disk`, `From Git`, `Skip Source`) and reduced button count
- immediate folder picker attempt for local source path

Markers:
- `MARKER_161.8.MULTIPROJECT.UI.NO_MODAL_ONBOARDING.V1`
- `MARKER_161.8.MULTIPROJECT.UI.GRANDMA_FLOW_SOURCE_STEP.V1`
- `MARKER_161.8.MULTIPROJECT.UI.DRAFT_TAB_EMPTY_CANVAS.V1`
- `MARKER_161.8.MULTIPROJECT.UI.DRAFT_TAB_MINI_DEFAULTS.V1`
- `MARKER_161.8.MULTIPROJECT.UI.DRAFT_TAB_DELAYED_OVERLAY.V1`

Acceptance:
- project creation starts from main interface, not modal onboarding
- source step is understandable without technical wording
- no regression in tab scope binding and existing `tests/mcc`

## Milestone Sequence (strict)

1. M161-A (`RECON+REPORT`): docs + marker map + no behavior changes.
2. M161-B (`IMPL NARROW`): W1 + W2 skeleton behind feature flag.
3. M161-C (`IMPL NARROW`): W3 integration with hard verifier gate.
4. M161-D (`IMPL NARROW`): W4 compare/version persistence.
5. M161-E (`IMPL NARROW`): W5 UI badges/diagnostics.
6. M161-F (`VERIFY`): W6 tests + manual DAG quality audit.

## Runtime Safety Policy

1. Baseline-first: if TRM fails, return baseline DAG with explicit `trm_meta.status=degraded`.
2. Invariant-first: reject any TRM mutation that violates acyclic/layer checks.
3. Budget-first: refinement bounded by `max_refine_steps`, `max_candidate_edges`.
4. Source-truth: backend decides topology; frontend only renders.

## Initial TRM Policy Profiles

- `off`:
  - no TRM calls
- `light`:
  - low step count, edge-rerank only
- `balanced`:
  - rerank + limited candidate insertion
- `aggressive` (debug only):
  - higher step count, never default

## Implementation Order in Code

1. `src/services/mcc_trm_config.py` (new)
2. `src/services/mcc_trm_adapter.py` (new)
3. `src/services/mcc_architect_builder.py` (gate integration)
4. `src/services/mcc_dag_compare.py` (profile matrix + score extension)
5. `src/services/mcc_dag_versions.py` (metadata persistence)
6. `src/api/routes/mcc_routes.py` (request/response contract)
7. `client/src/hooks/useRoadmapDAG.ts` + `client/src/components/mcc/MyceliumCommandCenter.tsx` (source badge)
8. `tests/mcc/*` (contract + determinism + profile compare)

## Report Artifacts for this phase

- `PHASE_161_MCC_TRM_RECON_MARKERS_2026-03-04.md` (this phase recon)
- `CODEX_PHASE_161_MCC_TRM_MASTER_PLAN.md` (this file)
- future per-wave reports:
  - `PHASE_161_P1_REPORT_YYYY-MM-DD.md`
  - `PHASE_161_P2_REPORT_YYYY-MM-DD.md`
  - ...

## GO Gate for next step

Next executable step after this roadmap:
- implement **W1 only** (contracts + flags + no-op behavior), then run only `tests/mcc` contract tests.
