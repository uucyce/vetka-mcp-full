# CODEX BRIEF — Phase 170 CUT Scene Graph First-Class Viewport Batch 5

## Scope
Strengthen reverse cross-highlighting so storyboard and timeline context drive explicit Scene Graph focus, and enrich `Selected Shot` with graph-linked inspector context.

## Tasks
1. Derive Scene Graph DAG selection from storyboard-selected shot via `scene_graph_view.crosslinks.by_source_path`.
2. Derive Scene Graph DAG selection from timeline selection via `scene_graph_view.crosslinks.by_clip_id`.
3. Expose graph-linked node counts and primary graph context in `Selected Shot`, then lock it with docs/tests.

## Guardrails
- Keep `Scene Graph Surface` explicit and first-class.
- Do not replace timeline or storyboard as the default CUT interaction path.
- Prefer additive client-side wiring; no schema churn unless strictly required.
