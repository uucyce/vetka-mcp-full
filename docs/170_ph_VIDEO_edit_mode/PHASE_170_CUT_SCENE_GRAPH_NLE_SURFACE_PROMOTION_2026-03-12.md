# PHASE 170 — CUT Scene Graph NLE Surface Promotion

## Goal
Carry the Scene Graph peer-pane state from the shell into the main CUT NLE surface so promotion does not stop at the legacy debug layer.

## First Promotion Hook
- Shell peer-pane mode maps to NLE-facing state: `sceneGraphSurfaceMode = nle_ready`
- NLE does not yet render the graph pane itself in this step.
- NLE does expose visible readiness signals so future pane insertion is not a blind rewrite.

## Visible Signals
- Transport bar shows `Graph Ready` when shell state has promoted the graph toward NLE.
- NLE `Program Monitor` header shows `Scene Graph peer pane ready`.
- This state is additive and does not replace timeline or preview.

## Next Step
Insert the actual Scene Graph pane into the NLE layout using the same readiness state, rather than inventing a second graph workflow.
