# CODEX Unified DAG Master Plan (Phase 155+)

**Date:** 2026-02-21  
**Status:** ACTIVE CANONICAL PLAN  
**Protocol:** RECON+markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY

## 0.1 Implementation References (Current)
- `docs/155_ph/MCC_DRILLDOWN_MECHANICS_SYNTHESIS_2026-02-27.md`
- `docs/155_ph/MCC_DRILLDOWN_IMPLEMENTATION_ROADMAP_2026-02-27.md`
- `docs/155_ph/MCC_DRILLDOWN_REVISION_MARKERS_2026-02-27.md`

## 1) Objective
Build MCC as a single-canvas, drill/zoom DAG system:
- LOD0: Playground context (workspace selected/created by user).
- LOD1: Project architecture tree (files/folders + project tasks overlaid).
- LOD2: Task workflow team graph inside selected branch (agents, messages, artifacts, live stream).

Hard UX rule:
- One main window.
- Max 3 primary actions in context.
- Progressive disclosure only.

## 2) Canonical Model
Introduce one graph contract for all levels.

### 2.1 Node Kinds
- `project_root`
- `project_dir`
- `project_file`
- `project_task`
- `workflow_agent`
- `workflow_artifact`
- `workflow_message`

### 2.2 Edge Kinds
- `contains` (dir/file tree)
- `depends_on` (project dependencies)
- `affects` (task -> file/dir; allows cross-cutting tasks)
- `executes` (task -> workflow graph)
- `passes` (agent -> agent message/data flow)
- `produces` (agent -> artifact)

### 2.3 Required IDs
- `project_node_id`
- `task_id`
- `workflow_id`
- `agent_node_id`
- `source_message_id`

### 2.4 Cross-Cutting Task Rule
Every `project_task` has:
- `primary_node_id`
- `affected_nodes[]` (1..N)
- `integration_task_of[]` optional (for architect merge/verify tasks)

## 3) LOD/Drill Behavior

### 3.0 Mandatory Drill Contract (Locked)
- Workflow unfolds **from selected task node anchor** in the same canvas.
- Reveal is matryoshka-style: expand/collapse is local, deterministic, and reversible.
- Expanded workflow must **push aside conflicting nearby branches/files** locally (collision area only), not by global random re-layout.
- Workflow cards are micro-layer scale: approximately **10x smaller** than architecture cards.
- Workflow DAG must remain structurally clear (hierarchy/branches readable, no strip/no cluster mash).
- No route/screen switch and no detached workflow scene.
- Pane click only clears selection/highlight; it must not destroy unfolded structure state unless explicit collapse is requested.
- Canonical DAG direction is fixed: **bottom -> top**.
- For workflow: task/root context at lower level, team/steps above, result/artifact/new code outcome at upper level.
- Same matryoshka rule for project tree: folder/node expand reveals next directory depth in-place; each deeper level is rendered as micro-layer (~10x smaller than parent level).

### 3.0.1 Non-negotiable UX checks
- Double-click on task toggles workflow expand/collapse for this exact task.
- Expanded workflow stays visually linked to its parent task node.
- Architecture context remains visible; no global fade blackout and no camera teleport.
- If local top space is insufficient, deterministic local fallback is allowed (top -> down), still anchored to the same task node.
- Folder drill is hierarchical and directional: parent stays as anchor, children appear above in DAG flow, then next drill repeats the same pattern.

### LOD0 (Playground)
- No drill UI yet.
- User configures source (new/copy/continue) and key setup.
- Exit condition: project initialized and graph bootstrap available.

### LOD1 (Architecture Tree)
- Render tree as primary structure.
- Files/folders are dim gray.
- Branches with active tasks are accent white.
- Optional tiny workflow previews allowed only if perf budget is stable.
- Default view is topology-only (no global dependency spaghetti).

### LOD2 (Task Workflow)
- Trigger: click/enter/double-click on `project_task`, or zoom threshold + focused task.
- Show team workflow graph on the same canvas (no route/screen switch).
- Active agent nodes visibly animated/highlighted.
- Node click opens contextual data (model, stream, stats, code/artifacts).

### Focus Lens (cross-LOD invariant)
- Selecting node/file enables dependency overlay only for focus set.
- Focus set persists across zoom in/out until cleared by user.
- Shift adds/removes nodes from focus set.
- Multi-focus can be escalated into `Create Task` payload for Project Architect chat.

## 4) Action Policy (Max 3 Primary Buttons)
`actions = f(lod, selection, runtime_state)`

### LOD0
- `Continue`
- `Back`
- `Help`

### LOD1
- `Create Task`
- `Ask Architect`
- `Launch`

### LOD2
- `Run` or `Resume`
- `Pause` or `Stop`
- `Back`

Non-primary actions go to gear/secondary menu, never replacing 3-slot primary rule.

## 5) Phased Implementation

## P0: Gate + Onboarding
**Markers**
- `MARKER_155A.P0.FLOW_GATE`
- `MARKER_155A.P0.ONBOARDING_REBIND`
- `MARKER_155A.P0.STEP_VISIBILITY`

**Scope**
- Enforce first-start gate: user cannot land in drill levels before setup completion.
- Rebind onboarding hints to current UI targets.
- Show step UI only when contextually valid (no premature Drill).

**Acceptance**
- Fresh user always starts at setup flow.
- Onboarding appears once, targets real elements, can be dismissed/reset.
- No forced jump to step 5 on initial launch.

## P1: Unified Graph Contract
**Markers**
- `MARKER_155A.P1.GRAPH_SCHEMA`
- `MARKER_155A.P1.CROSSCUT_TASKS`
- `MARKER_155A.P1.ADAPTERS`

**Scope**
- Add/normalize API payloads for unified node/edge kinds.
- Implement adapters from existing roadmap/task/workflow sources.
- Add cross-cutting task links (`affected_nodes[]`).

**Acceptance**
- One payload can render LOD1 and LOD2 without route switch.
- Complex tasks can target multiple tree branches.

## P2: LOD Render Engine
**Markers**
- `MARKER_155A.P2.LOD_THRESHOLDS`
- `MARKER_155A.P2.FRACTAL_RENDER`
- `MARKER_155A.P2.FAN_LAYOUT_BRIDGE`

**Scope**
- Add LOD thresholds and focus rules.
- Bridge existing fan-layout/Sugiyama mechanics into unified DAG rendering.
- Keep perf budget under control for large trees.
- Enforce topology-default + focus-only dependencies policy.
- Preserve manual node pin positions during soft refresh.

**Acceptance**
- Smooth drill/zoom within one canvas.
- LOD transitions do not re-mount a different screen/component tree.

## P2.1: Layout Preference Learning
**Markers**
- `MARKER_155A.P2_1.LAYOUT_PREFERENCE_LEARNING`
- `MARKER_155A.P2_1.PIN_FEEDBACK_LOOP`
- `MARKER_155A.P2_1.BIAS_PROFILE`
- `MARKER_155.MEMORY.SHARED_DAG_POLICY.V1`

**Scope**
- Learn user layout intent from manual pin/drag actions in architecture view.
- Convert stable manual adjustments into per-scope layout bias profile.
- Feed learned profile back into auto-layout (without hardcoded coordinates).

**Learning loop**
- Input signal: user drag/pin deltas (`before -> after`) by context key.
- Aggregation: accumulate directional bias (vertical separation, sibling spacing, branch compactness).
- Stabilization: apply only when confidence threshold and repetition count are met.
- Application: profile influences next auto-layout pass for same project scope.
- Persistence split:
  - local UI stores keep exact coordinates/pins,
  - ENGRAM keeps cross-surface layout intent profile (`dag_layout_profiles`) for MCC+VETKA reuse.

**Non-goals**
- No forced override of explicit user pin.
- No global cross-project bias leakage.
- No timer-based retraining; only trigger/event driven updates.

**Acceptance**
- Repeated user refinements in same scope produce visibly closer auto-layout on next rebuild.
- User pin remains authoritative and is never silently undone.
- Learned bias improves readability metrics (fewer crossings, higher layer separation) on verifier pass.
- MCC and VETKA share one logical preference memory (ENGRAM profile), but do not share one raw coordinate blob.

## P3: Node-Centric Mini Windows
**Markers**
- `MARKER_155A.P3.NODE_CONTEXT_WINDOW`
- `MARKER_155A.P3.MODEL_EDIT_BIND`
- `MARKER_155A.P3.STATS_CONTEXT`

**Scope**
- Reintroduce node context panel behavior as mini-window pattern.
- Support model view/replace on selected agent node.
- Bind stats to current selection (global/module/task/agent).
- Expose stream/messages/artifacts/code from selected nodes.

**Acceptance**
- Clicking agent/task node reveals contextual model+stats+stream data.
- Stats are no longer detached from DAG context.

## P4: Orchestration + Merge
**Markers**
- `MARKER_155A.P4.ARCHITECT_MERGE`
- `MARKER_155A.P4.CONFLICT_POLICY`
- `MARKER_155A.P4.INTEGRATION_VERIFY`

**Scope**
- Architect creates integration tasks that unify outputs of multiple task-teams.
- Add conflict policy for overlapping code spaces.
- Add verify task generation for final integration pass.

**Acceptance**
- Multi-branch tasks converge through explicit architect-controlled merge/verify tasks.
- TaskBoard can represent dependencies between team outputs and integration checkpoints.

## P5: JEPA Integration (Design-time Predictor)
**Markers**
- `MARKER_155A.P5.JEPA_PROVIDER`
- `MARKER_155A.P5.PREDICTOR_CALIBRATION`
- `MARKER_155A.P5.OVERLAY_GUARDRAILS`

**Scope**
- Replace heuristic predictor channel with real JEPA/V-JEPA provider.
- Keep JEPA output overlay-only (never auto-mutates base topology).
- Add confidence calibration and explainability evidence bundle for each predicted edge.

**Acceptance**
- JEPA edges are visible only in focus lens or explicit "show predicted" mode.
- Overlay quality is verifier-gated and does not degrade base readability.

## P5.1: DAG Variant Auto-Compare Harness
**Markers**
- `MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.V1`
- `MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.SCORECARD.V1`
- `MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.AUTORUN.V1`
- `MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.PERSIST.V1`
- `MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.API.V1`

**Scope**
- Add one API call to run multiple DAG builder variants in one shot.
- Produce deterministic scorecards from verifier/spectral outputs and rank variants.
- Optionally persist each result as DAG version and set best as primary.
- Support both repository scope (`source_kind=scope`) and generic arrays (`source_kind=array`).

**Current status (2026-02-25)**
- Backend implemented:
  - `src/services/mcc_dag_compare.py`
  - `POST /api/mcc/dag-versions/auto-compare`
- UI compare matrix is pending (debug-stage DAG tabs are available in roadmap level).

**Acceptance**
- Single request returns ranked variants with explicit score breakdown and best candidate.
- Persisted variants are visible in DAG version tabs and can be promoted to primary.
- Same harness works for repo path and array payload without manual code edits.

## P6: OpenHands Accelerator Track (Execution UX + Runtime)
**Markers**
- `MARKER_155A.P6.OPENHANDS_TERMINAL`
- `MARKER_155A.P6.OPENHANDS_SANDBOX`
- `MARKER_155A.P6.OPENHANDS_APPROVAL`
- `MARKER_155A.P6.OPENHANDS_DIFF_REVIEW`
- `MARKER_155A.P6.OPENHANDS_LOCAL_LLM`
- `MARKER_155A.P6.OPENHANDS_RECOVERY_LOOP`

**Goal**
- Reuse proven OpenHands patterns to accelerate Mycelium MVP without changing core MCC one-canvas UX.
- Scope is selective adoption (80/20), not direct architecture copy.

**Adoption Rules**
- Keep FastAPI + current backend stack. No Flask paths.
- Any imported behavior must fit MCC action policy (max 3 primary actions).
- Execution/runtime additions must remain trigger-driven (no periodic UI polling loops).

### P6.1 Terminal Streaming (High ROI)
**What**
- Add unified execution terminal pane behavior (real-time tool output, timestamps, copy support).
- Connect to existing structured events (`dag_node_update`, pipeline events).

**Why**
- Closes execution observability gap in Matryoshka flow.

**Acceptance**
- User can inspect live tool output for focused task/workflow without leaving MCC canvas.

### P6.2 Sandbox Runtime Overlay (Docker-compatible)
**What**
- Extend playground runtime with optional containerized execution path.
- Keep current git-worktree mode as default fallback.

**Why**
- Reliable run/test/install isolation for agent actions.

**Acceptance**
- Same task can run in worktree mode or container mode with identical task contract.

### P6.3 Human-in-the-Loop Tool Approval
**What**
- Gate dangerous tool calls through explicit approve/edit/reject controls in execution stage.
- Reuse existing approval/stream paths, no parallel approval systems.

**Why**
- Safer autonomous execution and better operator control.

**Acceptance**
- Proposed tool call can be paused, edited, approved, or rejected from MCC.

### P6.4 Diff Review Pane (Result Stage)
**What**
- Add side-by-side patch/diff review before promote/apply.
- Bind to PatchApplier artifacts and task result payloads.

**Why**
- Improves final acceptance quality and reduces bad promote events.

**Acceptance**
- User can review old/new content and approve promote from one contextual surface.

### P6.5 Local LLM Preset Alignment
**What**
- Add OpenHands-style local model fallback profile tuning in existing registry/presets.
- Prioritize available local models for architect/scout tasks in MVP mode.

**Why**
- Reduces cost and keeps offline-first behavior strong.

**Acceptance**
- Preset switch can force local-first execution for architect/scout pipeline stages.

### P6.6 Error-Recovery Loops
**What**
- Add bounded retry with feedback in execution loop for patch/apply/verify failures.
- Keep retries transparent in stream and verifier telemetry.

**Why**
- Increases robustness for long autonomous runs.

**Acceptance**
- Failed step emits correction attempt(s) with explicit retry count and final outcome.

## 6) Verification Plan
- V1: First-run walkthrough (new user) reaches LOD1 only after setup.
- V2: Existing project starts at valid context, no ghost step transitions.
- V3: Cross-cutting task appears in multiple branches and drills into one workflow context.
- V4: Node click shows model, stream, stats, and artifacts tied to that node.
- V5: Action bar never exceeds 3 primary actions.
- V6: Topology default remains clean with no dependency noise unless focus selected.
- V7: Manual layout adjustments persist on soft refresh.
- V8: Focus overlay persists across zoom transitions.
- V9: Shift multi-select can dispatch architect task payload.
- V10: Strict JEPA runtime mode fails closed (`503`) when true runtime backend is unavailable.
- V11: OpenHands terminal stream is readable and synchronized with focused workflow node.
- V12: Approval gate blocks tool execution until explicit user action.

## 7) Non-Goals (Current Window)
- Full replacement of all legacy docs/components in one patch.
- Deep backend schema migrations without adapter compatibility layer.
- Large UI redesign outside MCC unified DAG scope.

## 8) Document Governance
- This file is the canonical execution plan for Phase 155+ Unified DAG.
- `docs/154_ph/MCC_ARCHITECTURE_DIAGRAM.md` remains conceptual UX map.
- `docs/154_ph/MARKER_155_MCC_ARCHITECTURE_REDUX.md` remains architectural rationale/history.
