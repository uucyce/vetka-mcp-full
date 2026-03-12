# PHASE 170 — CUT Scene Graph NLE Pane Insertion

## Goal
Insert the first actual Scene Graph pane into the CUT NLE layout so promotion is visible inside the editor, not only through readiness badges.

## Layout
- Source Browser | Program Monitor | Scene Graph Surface | Inspector
- Timeline remains the bottom anchor.
- Scene Graph pane appears only when `sceneGraphSurfaceMode = nle_ready`.

## First Insertion Rules
- Start with a lightweight placeholder pane.
- Reuse the same promoted state already coming from shell.
- Do not yet duplicate the full DAG viewport inside NLE in this step.

## Visible Signals
- NLE pane header: `Scene Graph Surface`
- Body copy: `NLE pane insertion active`
- Copy explicitly says the next step is replacing the placeholder with the shared DAG viewport.
