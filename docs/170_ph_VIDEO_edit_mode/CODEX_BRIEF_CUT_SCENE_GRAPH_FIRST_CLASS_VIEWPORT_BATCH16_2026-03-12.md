# CODEX BRIEF — Phase 170 CUT Scene Graph First-Class Viewport Batch 16

## Scope
Add a compact poster preview to the NLE Scene Graph compact card when media poster data is available.

## Tasks
1. Define poster-preview rules for the compact card.
2. Render poster when available, and a neutral fallback when not.
3. Lock the behavior with docs/tests.

## Guardrails
- Keep preview compact.
- Do not replace the DAG pane with media art.
- Reuse existing poster data from graph render hints.
