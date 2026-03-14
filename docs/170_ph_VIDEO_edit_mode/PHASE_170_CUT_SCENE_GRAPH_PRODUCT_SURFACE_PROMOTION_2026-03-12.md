# PHASE 170 — CUT Scene Graph Product Surface Promotion

## Goal
Promote `Scene Graph Surface` from debug-shell placement into a product CUT surface without demoting timeline or storyboard workflows.

## Promotion Rules
- Scene Graph remains explicit and user-visible.
- Timeline stays the default temporal surface.
- Storyboard stays the default shot-browsing surface.
- Scene Graph becomes a peer surface for structural and semantic editing, not a hidden inspector.

## Layout Path
1. Keep current debug-shell card while first-class graph behavior stabilizes.
2. Promote Scene Graph into a dedicated CUT pane or tabbed surface beside timeline/storyboard.
3. Preserve `Selected Shot` as the common right-side inspector shared by storyboard and graph focus.
4. Reuse MCC DAG grammar, but keep CUT nodes media-native with poster, duration, marker, and sync context.

## Required UX Couplings
- storyboard selection -> graph focus
- timeline selection -> graph focus
- graph selection -> storyboard focus
- graph selection -> timeline selection
- graph-linked summaries visible in `Selected Shot`

## Non-Goals
- No graph-only CUT mode.
- No replacement of timeline with a pure DAG workflow.
- No hidden graph implementation as the target state.
