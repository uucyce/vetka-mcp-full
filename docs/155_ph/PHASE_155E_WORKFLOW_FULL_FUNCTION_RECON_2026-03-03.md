# PHASE 155E — Workflow Full Function Recon (2026-03-03)

Status: `RECON + markers`  
Protocol: `RECON+markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`

## 1) Goal of this recon

Close ambiguity around workflow surface in MCC:
1. node/edge type contract;
2. add/edit/reconnect/delete behavior;
3. what affects execution vs what is visual-only;
4. where workflow execution is launched in grandma UX;
5. what to take from ComfyUI/n8n at pattern level without architecture/license mistakes.

## 2) Current reality map (code-grounded)

### 2.1 Core type contracts (frontend)
Source: `client/src/types/dag.ts`
1. `DAGNodeType` supports: `task|agent|subtask|proposal|condition|parallel|loop|transform|group|roadmap_task`.
2. `EdgeType` supports: `structural|dataflow|temporal|conditional|parallel_fork|parallel_join|feedback|dependency|predicted`.
3. `AgentRole` supports: `scout|architect|researcher|coder|verifier` (no `eval`).
4. `DAGEdge.relationKind` is restricted to: `contains|depends_on|affects|executes|passes|produces|predicted`.

### 2.2 Template library reality
Sources:
- `data/templates/workflows/bmad_default.json`
- `data/templates/workflows/g3_critic_coder.json`
- `data/templates/workflows/ralph_loop.json`

Observed:
1. BMAD uses node type `gate` (`approval_gate`) which is not in `DAGNodeType` and not in `WorkflowStore.VALID_NODE_TYPES`.
2. BMAD/G3 use semantic role `eval` (Eval Agent), but `AgentRole` excludes `eval`.
3. Template edge labels/semantics are richer than current `relationKind` enum (`retries`, `passes_to`, `deploys`, `feeds`, etc. appear in UI build paths).

### 2.3 Add/edit edge mechanics in UI
Sources:
- `client/src/components/mcc/MyceliumCommandCenter.tsx`
- `client/src/components/mcc/DAGView.tsx`
- `client/src/hooks/useDAGEditor.ts`

Observed:
1. Inline roadmap workflow edit is gated by:
   - `navLevel=roadmap`
   - `taskDrillState=expanded`
   - `editMode=true`
   - `selectedTaskId` present.
2. `onConnect/onReconnect/onEdgesDelete` now wired for inline runtime mode.
3. Validation blocks:
   - missing source/target,
   - self-loop,
   - cross-workflow edge,
   - duplicate,
   - direct structural cycle.
4. Source-of-truth split still exists globally:
   - inline runtime drill graph uses `inlineWorkflowNodes/inlineWorkflowEdges`,
   - classic editor uses `dagEditor` state.

### 2.4 What execution actually uses
Sources:
- `client/src/store/useMCCStore.ts` (`executeWorkflow`)
- `src/api/routes/workflow_template_routes.py` (`POST /api/workflows/{id}/execute`)
- `src/services/workflow_store.py` (`workflow_to_tasks`)

Observed:
1. Execute path runs stored workflow template by `workflow_id`.
2. Execution conversion uses only `structural` and `temporal` edges for dependency chain.
3. `dataflow/conditional/parallel_fork/parallel_join/feedback` currently do not define full execution semantics in task dispatch.
4. So part of current graph semantics is visual/diagnostic, not runtime-enforced orchestration.

### 2.5 Node settings path
Source: `client/src/components/mcc/MiniContext.tsx`

Observed:
1. Agent model edit persists to preset-level role mapping (`/api/pipeline/presets/update-role`), not per-node model override.
2. Role prompt edit persists to global role prompts (`/api/pipeline/prompts/update`), also preset/role-level.
3. For `eval` node UI maps model/prompt editing to `verifier` role (`effectiveRole = verifier`).

### 2.6 Where workflow launch is triggered
Sources:
- `client/src/components/mcc/MyceliumCommandCenter.tsx` (`handleExecute`)
- `client/src/hooks/useKeyboardShortcuts.ts`
- `client/src/components/mcc/FooterActionBar.tsx`

Observed:
1. Launch is implemented via `handleExecute` -> save workflow -> `/api/workflows/{id}/execute`.
2. Keyboard path exists (`workflow` level: `Enter` executes).
3. FooterActionBar contains visible execute action, but in current MCC render it is mounted only under `debugMode` block.
4. Therefore discoverability in grandma UX is currently weak/inconsistent.

## 3) Functional gaps (critical)

1. **Type contract drift**:
   - `gate` and `eval` are used in real templates/visualization but absent in strict TS/Python enums.
2. **Execution semantics drift**:
   - many edge kinds are rendered but not interpreted by executor.
3. **Edit semantics drift**:
   - inline runtime edit and template editor are still two separate state domains.
4. **Launch UX drift**:
   - execute action is not clearly exposed in non-debug grandma flow.
5. **Policy drift**:
   - no role-aware edge policy (allowed/disallowed transitions by template family).
6. **Task panel drift**:
   - mini mode currently creates a truncated/non-scroll impression of task count.
   - selection is not always synchronized: click on task node should activate same task in task list.

## 4) External pattern evaluation (ComfyUI / n8n)

### 4.1 Useful to adopt (pattern-level)
1. ComfyUI-like UX patterns:
   - explicit handles/ports,
   - edge hover actions,
   - fast context menu on node/edge,
   - reroute/reconnect ergonomics.
2. n8n-like execution governance:
   - deterministic node parameter schema,
   - retry/error policy blocks,
   - trigger nodes,
   - run log + step diagnostics.

### 4.2 What to avoid
1. Do not transplant foreign engines wholesale.
2. Do not treat UI graph features as execution truth until runtime contract is encoded server-side.
3. Do not copy code directly across license boundaries; use pattern-level reimplementation.

## 5) Marker set for full workflow hardening

### P0 — Contract unification
1. `MARKER_155E.WF.CONTRACT.NODE_TYPE_MATRIX.V1`
2. `MARKER_155E.WF.CONTRACT.ROLE_MATRIX.V1`
3. `MARKER_155E.WF.CONTRACT.EDGE_RELATION_MATRIX.V1`

### P1 — Editing semantics
1. `MARKER_155E.WF.EDIT.UNIFIED_SOURCE_OF_TRUTH.V1`
2. `MARKER_155E.WF.EDIT.ROLE_AWARE_EDGE_POLICY.V1`
3. `MARKER_155E.WF.EDIT.EDGE_MINIPANEL.V1`

### P2 — Execution semantics
1. `MARKER_155E.WF.EXEC.EDGE_KIND_RUNTIME_MAPPING.V1`
2. `MARKER_155E.WF.EXEC.CONDITIONAL_AND_FEEDBACK_POLICY.V1`
3. `MARKER_155E.WF.EXEC.RUN_TRIGGER_GRANDMA_VISIBLE.V1`
4. `MARKER_155E.WF.EXEC.RUN_TRIGGER_IN_EXISTING_PANELS.V1`
5. `MARKER_155E.WF.EXEC.HEARTBEAT_TASK_PANEL_CONTROL.V1`

### P2.5 — Tasks Panel Truthfulness + Linkage
1. `MARKER_155E.WF.TASKS_PANEL.MINI_SCROLL_PARITY.V1`
2. `MARKER_155E.WF.TASKS_PANEL.SELECTION_SYNC_WITH_DAG.V1`
3. `MARKER_155E.WF.TASKS_PANEL.CONTEXT_ACTIONS.START_STOP.V1`

### P3 — Family governance
1. `MARKER_155E.WF.FAMILY.REGISTRY.V1`
2. `MARKER_155E.WF.FAMILY.BMAD_G3_RALPH_BIND.V1`
3. `MARKER_155E.WF.FAMILY.OPENHANDS_PULSE_STUBS.V1`

## 6) Narrow implementation order (recommended)

1. **Step A (must first):** freeze unified type matrix (`gate/eval/relation kinds`) across TS + Python validators.
2. **Step B:** merge inline runtime edit state with persisted workflow package writeback.
3. **Step C:** add edge minipanel (edge type/relation/condition/retry flags) and role-aware validation.
4. **Step D:** make execute trigger explicit in grandma mode (context window + chat header action), keep keyboard as secondary.
5. **Step E:** runtime mapping for non-structural edges (conditional/feedback/parallel) in execution bridge.

## 7) Direct answers to user questions

1. **Types and dependencies**: currently partially formalized, but contract drift exists (`gate/eval/relation kinds`).
2. **Adding nodes**: available via context menu + NodePicker in edit mode; node menu currently excludes some declared types (`subtask`, `proposal`).
3. **Node settings**: currently role/preset-level (model/prompt), not full per-node execution config object.
4. **Where to run workflow**: implemented in `handleExecute`, but explicit visible entry should be restored in grandma UI (not only debug or keyboard).
5. **Heartbeat**: best place is existing `Tasks` panel (no new window), with clear controls near task actions.

## 8) Immediate next implementation target

`P0/P1-A`: contract freeze for node/role/edge matrices + unified inline source-of-truth writeback.

## 9) WAIT GO

Recon complete. Ready for narrow implementation after explicit `GO`.
