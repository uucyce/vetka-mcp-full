# PHASE 170 — CUT Scene Graph Peer Pane Layout Plan

## Goal
Move Scene Graph from an embedded debug-shell card toward a concrete peer pane in CUT without demoting timeline or storyboard.

## Shell Layout
- Left stack: `Timeline Surface` -> `Worker Outputs` -> `Storyboard Strip`
- Right pane: `Scene Graph Surface`
- Right pane becomes sticky in peer-pane mode so graph navigation remains visible during editorial browsing.

## Mode Rules
- `embedded`: Scene Graph stays inline in the main flow for debugging and early validation.
- `peer_pane`: Scene Graph occupies the right-side peer column beside the left editorial stack.

## Promotion Signals
- explicit mode toggle remains visible
- copy states `layout slot: right peer pane beside timeline/storyboard stack`
- no hidden graph path
- `Selected Shot` remains the shared inspector on the far right

## Next Step
After this layout is stable, promote the same pane model into the product CUT NLE surface rather than keeping it isolated to the shell.
