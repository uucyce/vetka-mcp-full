# PHASE 170 — CUT Scene Graph NLE Pane Inspector Coupling

## Goal
Expose graph-selection summaries inside the NLE Scene Graph pane so users can read graph-linked clip context without leaving NLE mode.

## Rules
- Reuse selected-shot graph summaries already computed in the shell bridge.
- Show graph-linked node count, active graph node, inspector linkage, and graph buckets in the NLE pane.
- Do not create a second full inspector or duplicate selected-shot logic.

## Visible Signals
- `clip-linked graph nodes:`
- `active graph node:`
- `pane inspector link:`
- `graph buckets:`
