# MCC Drill-Down Revision (Markers)
Date: 2026-02-27
Scope: roadmap inline workflow unfold (single-canvas)
Status: RECON ONLY (no implementation in this step)

## Target Contract (what we want)
1. Double-click on task node toggles expand/collapse of subgraph.
2. Subgraph unfolds from the task node (local origin), keeps hierarchy readable.
3. Base architecture stays visible and stable (no global “teleport” effect).
4. Inline workflow is visually smaller than architecture nodes (fractal scale).
5. No random single edge as primary signal; full subgraph appears as first-class reveal.
6. No separate window for workflow in this mode.

## Fact Check vs Contract

### MARKER_REV_A1_LAYOUT_COUPLING (critical)
- Location: `client/src/components/mcc/DAGView.tsx:192-443`
- Fact: architecture nodes + task overlays + `wf_*` nodes are laid out in one shared pass.
- Effect: workflow cluster is forced by architecture layout constraints, causing overlap/strip/"kasha".
- Why this breaks target: reveal is not local to task node; it competes with global graph constraints.

### MARKER_REV_A2_OVERPACKED_WORKFLOW_BOX (critical)
- Location: `client/src/components/mcc/DAGView.tsx:345-364`
- Fact: template workflow is normalized into fixed `targetW=180`, `targetH=110`.
- Effect: for 8-14 workflow nodes, cluster density is too high; labels collide.
- Why this breaks target: subgraph is technically present, but not readable as DAG.

### MARKER_REV_A3_FALLBACK_GRID_TOO_DENSE (high)
- Location: `client/src/components/mcc/DAGView.tsx:414-429`
- Fact: fallback layout uses `xGap=36`, `yGap=20`.
- Effect: rows overlap visually with current node component widths (40-70+) and labels.
- Why this breaks target: compactness exceeds readability budget.

### MARKER_REV_A4_NODE_SIZE_CONTROL_MISMATCH (high)
- Location A: `client/src/components/mcc/MyceliumCommandCenter.tsx:648-652`
- Location B: node renderers (`AgentNode`, `SubtaskNode`, etc.)
- Fact: width/height set on DAG node object are not the true visual source of size for ReactFlow custom components.
- Fact: real rendered size is driven by component CSS (`minWidth`, `padding`, font, handles).
- Effect: reducing `node.width/height` in MCC does not reliably shrink rendered cards.
- Why this breaks target: attempted “x10 smaller workflow” did not affect what user sees.

### MARKER_REV_A5_BRIDGE_OK_BUT_NOT_SEMANTIC_UNFOLD (medium)
- Location: `client/src/components/mcc/MyceliumCommandCenter.tsx:670-685`
- Fact: there is exactly one bridge edge from `task_overlay_*` to entry workflow node.
- Effect: link exists, but unfold still appears as detached cluster, not progressive reveal chain.
- Why this breaks target: structural relation is present, interaction semantics are still abrupt.

### MARKER_REV_A6_CLICK_MODEL_CONFLICT (medium)
- Location: `client/src/components/mcc/DAGView.tsx:675-706`
- Fact: single-click has 220ms delayed timer; double-click cancels it.
- Effect: first-click highlight/dim and second-click unfold can still feel like mixed interaction in rapid usage.
- Why this breaks target: user perceives “random line first, then something else”.

### MARKER_REV_A7_INCREMENTAL_POSITION_STICKINESS (medium)
- Location: `client/src/components/mcc/DAGView.tsx:205-217`
- Fact: in architecture mode, when inline workflow exists, `keepIncremental=true` keeps previous positions.
- Effect: stale positions can persist and amplify crowding artifacts between toggles.
- Why this breaks target: expanded/collapsed cycles do not reset to a clean local arrangement.

### MARKER_REV_A8_NO_TRUE_UNFOLD_ANIMATION (medium)
- Location: `client/src/components/mcc/DAGView.tsx:865-887`
- Fact: current animation is mainly CSS transition on transform/opacity after layout jump.
- Effect: looks like abrupt “cut” + slight motion, not matryoshka unfolding from parent node.
- Why this breaks target: motion does not communicate hierarchy expansion.

## What is already correct
1. Explicit drill state exists (`collapsed/expanded`) and is toggled by task double-click.
2. Inline workflow is rendered in same canvas (no forced separate window).
3. Bridge edge from task to workflow entry exists.
4. Pane click reset works more reliably than before.

## Minimal P0 Fix Direction (narrow, safe)

### MARKER_FIX_P0_1
Separate workflow placement from architecture pass:
- Keep architecture node positions frozen for current frame.
- Place workflow nodes in a local coordinate system centered on selected task.
- Do not re-run architecture-wide displacement because of workflow.

### MARKER_FIX_P0_2
Increase workflow local envelope and spacing:
- Template path: replace `180x110` with adaptive envelope based on node count.
- Fallback path: raise gaps from `(36,20)` to readable compact values.

### MARKER_FIX_P0_3
Single source of visual mini-size:
- Drive workflow compactness in node components by one `data.miniScale` contract.
- Stop relying on DAG node `width/height` as primary visual knob.

### MARKER_FIX_P0_4
Interaction contract split:
- Single click = highlight only.
- Double click = toggle unfold only.
- Ensure no intermediate dim edge artifact on double-click path.

### MARKER_FIX_P0_5
Optional (after P0): staged unfold animation
- Spawn workflow nodes at task center with low opacity.
- Animate to final local positions (200-350ms ease-out).

## GO/NO-GO gate for next implementation step
GO when all pass:
1. Workflow cluster remains readable for 10+ nodes (no card overlap).
2. Architecture nodes do not become globally transparent during unfold.
3. Double-click does not trigger camera zoom jump.
4. Bridge from task to workflow entry remains visible.
5. Expand/collapse cycle is deterministic for 5 consecutive toggles.

NO-GO if any fail:
- Any overlap that hides labels in expanded workflow.
- Any global re-layout that makes user lose task context.
