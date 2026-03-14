# PHASE 170 — CUT Scene Graph Pane State Persistence

## Goal
Keep Scene Graph pane mode stable across `/cut` reloads and project re-entry so the promotion from embedded card to peer pane feels intentional rather than random.

## Rule
- Persist only the pane presentation mode: `embedded` or `peer_pane`.
- Do not persist transient graph selection, timeline selection, or temporary job state in this step.
- Invalid or missing stored values fall back to `embedded`.

## Storage
- Use localStorage key: `cut.scene_graph.pane_mode.v1`
- Read on CUT shell startup.
- Write when the user changes pane mode.

## UX Signals
- `Scene Graph Surface` states that pane mode restores on reload.
- Reloading `/cut` should restore the last explicit pane mode choice.
- Persistence is a shell preference, not project data.

## Non-Goals
- No server persistence.
- No per-project pane-mode memory.
- No persistence of graph focus or selection.
