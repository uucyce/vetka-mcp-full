# PHASE 155E — Wave E Recon + Markers (2026-03-03)

Status: `RECON + markers`  
Protocol: `RECON+markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`  
Continuation after: `PHASE_155A_WAVE_D_RUNTIME_VERIFY_REPORT_2026-03-03.md`

## 1) Scope of this phase (confirmed)
1. User edge editing in workflow runtime UX:
   - create/edit/delete links,
   - validation,
   - persistence.
2. Workflow family library and canonical runtime mapping:
   - BMAD,
   - G3,
   - Ralph-loop,
   - n8n import/export landing,
   - OpenHands-inspired family,
   - Pulse (multi-objective scheduling for cloud-edge-IoT).
3. Keep Grandma contract from Wave D-RUNTIME:
   - workflow user flow = runtime-only truth,
   - design/predict remain diagnostics only.

## 2) Current state (what already exists)

### 2.1 Editing substrate already in code
1. `useDAGEditor` already supports:
   - add/remove nodes,
   - add/remove edges,
   - undo/redo,
   - save/load/list/validate workflow templates (`/api/workflows/*`).
2. `DAGView` already has edit handlers (`onConnect`, `onEdgesDelete`), but only when `editMode=true`.
3. Context menu already supports edge delete (`DAGContextMenu`) and node operations.

### 2.2 API/storage substrate already in code
1. Workflow template CRUD/import/export/validate/execute exists at `/api/workflows` (`workflow_template_routes.py`).
2. Persistent template storage exists (`WorkflowStore`) in `data/workflows/*.json`.
3. Canonical converter stack exists (`workflow_canonical_converters.py`) for `md/xml/xlsx`.
4. n8n converter exists and preserves round-trip metadata (`n8n_converter.py`).

### 2.3 Template-family baseline on disk
Current `data/templates/workflows/` includes:
1. `bmad_default.json`
2. `g3_critic_coder.json`
3. `ralph_loop.json`
4. additional utility templates (`quick_fix`, `refactor`, etc.)

## 3) Real gaps (blocking full Wave E)

### 3.1 UX-level gaps
1. Workflow edge editing is not available in current grandma runtime flow:
   - in roadmap inline workflow, `editMode` is effectively disabled for connect operations,
   - user can inspect runtime but cannot directly author links there.
2. No dedicated lightweight edge editor for:
   - edge type change,
   - relation label,
   - conditional metadata,
   - feedback policy.

### 3.2 Validation/persistence gaps
1. No explicit runtime-guard rules for user-created edges in grandma workflow path:
   - direction constraints,
   - forbidden loops except `feedback`,
   - gate transition constraints (quality/approval/deploy).
2. Missing explicit persistence contract for edited inline runtime graph back to canonical template/runtime package.

### 3.3 Family/template governance gaps
1. No unified family registry (versioned contract) spanning BMAD/G3/Ralph/OpenHands/Pulse.
2. OpenHands-inspired and Pulse families are not yet represented as first-class templates in canonical library.
3. No shared selection policy layer that maps user intent -> family -> team/prompt/model policy in one deterministic path.

## 4) Marker set for Phase 155E

### 4.1 Edge Editing + Runtime Contract
1. `MARKER_155E.WE.USER_EDGE_EDITING_RUNTIME.V1`
2. `MARKER_155E.WE.EDGE_EDITOR_MINIPANEL.V1`
3. `MARKER_155E.WE.EDGE_VALIDATION_POLICY.V1`
4. `MARKER_155E.WE.EDGE_PERSIST_CANONICAL.V1`

### 4.2 Template Family Registry
1. `MARKER_155E.WE.TEMPLATE_FAMILY_REGISTRY.V1`
2. `MARKER_155E.WE.FAMILY_POLICY_BIND.V1`
3. `MARKER_155E.WE.G3_RALPH_BMAD_CONTRACT.V1`
4. `MARKER_155E.WE.OPENHANDS_FAMILY.V1`
5. `MARKER_155E.WE.PULSE_FAMILY.V1`

### 4.3 n8n Landing + Canonical Merge
1. `MARKER_155E.WE.N8N_RUNTIME_LANDING.V1`
2. `MARKER_155E.WE.N8N_TYPE_PRESERVE_ASSERT.V1`
3. `MARKER_155E.WE.RUNTIME_CANONICAL_ROUNDTRIP.V1`

## 5) Proposed narrow execution order

### P0 — Contract freeze (no UI breakage)
1. Freeze `workflow runtime-only truth` contract for user flow.
2. Define edit entry points allowed in grandma UX (context menu + mini editor only).
3. Confirm which nav level owns editable workflow canvas.

### P1 — Minimal user edge editing in workflow
1. Enable connect/delete for workflow inline context only under explicit edit action.
2. Add compact edge editor (type + relation + basic metadata).
3. Apply validation gates before persist.

### P2 — Persistence and canonical writeback
1. Persist edited edges to workflow template store.
2. Add canonical normalization before save.
3. Add drift-safe merge policy for imported/runtime-derived graphs.
4. Keep run/execute trigger inside existing mini-panels (no extra window growth).
5. Move heartbeat controls into `Tasks` mini-window context area.

### P3 — Template family registry
1. Introduce explicit family metadata schema (`family`, `version`, `roles`, `policy`).
2. Normalize BMAD/G3/Ralph into one registry contract.
3. Add OpenHands-inspired and Pulse template stubs with strict role/edge semantics.

### P4 — n8n landing hardening
1. Add type-preservation asserts on import/export.
2. Add deterministic runtime mapping profile (`n8n -> canonical -> runtime`).
3. Add quick verify harness for round-trip and edge semantics.

### P4.5 — Tasks panel UX correctness
1. Add scroll parity in mini mode so task count perception matches full mode.
2. Sync selection both ways: DAG task/node click -> active row in `MiniTasks`, and task row click -> active DAG focus.
3. Show contextual task actions (`start`/`stop`) for active task directly in `MiniTasks`.

## 6) Verify criteria for this phase
1. User can create/delete/update workflow edges in intended runtime workflow surface.
2. Invalid edge attempts are blocked with clear reason.
3. Saved workflow reloads with same edges/types (no silent mutation).
4. Family templates are selectable under one registry and map to deterministic role policy.
5. n8n round-trip keeps key node/edge semantics.

## 7) Deferred and non-goals (explicit)
1. No return to user-facing dual mode (`runtime vs design`) in workflow UX.
2. No expansion of main canvas action count beyond grandma constraints.
3. No broad visual redesign (functional/minimal only).

## 8) Handoff context for next session (memory-safe)
1. Branch with latest Wave D-RUNTIME closure: `codex/mcc-wave-d-runtime-closeout`.
2. Last closeout commit: `cf169d48`.
3. Runtime-only contract already implemented in MCC workflow focus.
4. Immediate next implementation start should be `P0/P1` from this document.

## 9) WAIT GO
`RECON+markers` complete for Phase 155E Wave E scope.
Ready for `IMPL NARROW` on `P0` / `P1` after explicit GO.
