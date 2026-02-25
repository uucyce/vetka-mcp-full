# CODEX G2.1 Spec: Single-Canvas Drill + Vector Edges

Date: 2026-02-22
Status: Draft for approval
Protocol: RECON -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY

## 1. Position (What we agree on)

1. MCC must feel like one room, not scene switching.
2. Drill is contextual zoom/focus on the same canvas, not opening another UI world.
3. Core UX principle: obvious interdependency.
4. Primary UI contract remains: max 3 primary actions.

Slogan for UI spec:
- OCHYEVIDNAYA VZAIMOZAVISIMOST (Obvious Interdependency)

## 2. Clarification on edge routing

Current issue is mixed:
1. Layout reuse across incompatible graph sets causes visual corruption.
2. Edge style currently uses orthogonal/step routing in places.

Target behavior:
1. Default edge geometry = direct vectors (input -> output), not horse-step routes.
2. Workflow level uses explicit ports/handles (n8n/ComfyUI mental model).
3. Architecture level keeps directional dependencies but still vector-style readability.

Implementation direction:
1. Set connection rendering to smooth/direct style for primary graph edges.
2. Keep handles visible and directional (source/output, target/input).
3. Preserve editability only where intended (workflow nodes), while architecture dependencies remain code-derived.

## 3. Two-level logic without “new room” effect

Question: should team workflow be separate window?

Decision:
1. No separate primary window for team workflow.
2. Use one canvas + context overlays/miniwindows.
3. Optional detachable view is secondary (not default path), to avoid user disorientation.

Reason:
1. Separate scene creates memory/context reset effect.
2. Single canvas preserves spatial memory and task intent continuity.

## 4. Canonical model update (G2.1)

1. Project DAG (LOD1):
- Rooted project architecture graph (MAIN/root -> dirs/files/components).
- Task overlays attached to architecture nodes.

2. Team Workflow DAG (LOD2):
- Workflow template/team graph assigned to task(s), not trapped inside one task view.
- Workflow templates are provided out-of-the-box by default (no blank start).
- Both user and architect can refine/tune workflow wiring through UI ports.
- Task references a workflow assignment + runtime instance.

3. Assignment relation:
- task --executes--> workflow_template
- task_run --instantiates--> workflow_instance

4. Cross-cut remains first-class:
- task has primary_node_id + affected_nodes[]

## 5. UI/Interaction contract

1. One canvas always visible.
2. Drill transitions:
- select node -> focus
- double-click/enter -> increase detail in place
- back -> restore previous focus/camera in same space
3. No route/screen replacement for roadmap/tasks/workflow.
4. Miniwindows are contextual lenses, not navigation destinations.

## 6. Technical change set (next narrow implementation)

Marker block: MARKER_155A.G21

1. MARKER_155A.G21.SINGLE_CANVAS_STATE
- File: client/src/store/useMCCStore.ts
- Replace semantic nav switching with focus/depth context model while keeping backward compatibility.

2. MARKER_155A.G21.LAYOUT_RESET_POLICY
- File: client/src/components/mcc/DAGView.tsx
- Reset cached positions when graph identity/domain changes (architecture vs task overlay vs workflow instance).

3. MARKER_155A.G21.VECTOR_EDGE_STYLE
- File: client/src/components/mcc/DAGView.tsx
- Default to vector-like edge type and directional markers.
- Keep workflow editable handles for input/output.

4. MARKER_155A.G21.DRILL_IN_PLACE
- File: client/src/components/mcc/MyceliumCommandCenter.tsx
- Drill updates focus/depth/camera only; no perceived scene replacement.

5. MARKER_155A.G21.PLAYGROUND_ENTRY
- File: client/src/components/mcc/MyceliumCommandCenter.tsx
- Expose explicit playground entry even when project already exists.

## 7. Acceptance criteria

1. User never feels a new window/room when drilling.
2. Architecture appears as rooted project DAG, not phase train.
3. Edges read as directional vectors input->output at all LODs.
4. Workflow node ports are explicit and user-editable in workflow detail level.
5. Primary action count remains <= 3.

## 8. Risks

1. Full migration from navLevel to depth/focus model can regress hotkeys.
2. Edge style switch can affect readability for dense graphs if not tuned.
3. Architecture dependency extraction quality depends on backend input matrix quality.

## 9. Verify plan

1. Open MCC on existing project -> single canvas visible.
2. Drill architecture node -> no route-like scene switch.
3. Drill task -> workflow detail appears in same spatial context.
4. Back restores prior camera/focus deterministically.
5. Confirm vector edge readability and port behavior on editable workflow nodes.
