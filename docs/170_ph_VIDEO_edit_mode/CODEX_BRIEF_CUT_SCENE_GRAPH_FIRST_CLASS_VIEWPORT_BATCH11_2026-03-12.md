# CODEX BRIEF — Phase 170 CUT Scene Graph First-Class Viewport Batch 11

## Scope
Insert the first actual Scene Graph pane into the CUT NLE layout using the existing shell-to-NLE promotion state.

## Tasks
1. Define the first NLE pane insertion contract for Scene Graph.
2. Insert a lightweight Scene Graph pane placeholder into the NLE layout when promotion state is `nle_ready`.
3. Lock the visible insertion behavior with docs/tests.

## Guardrails
- Keep timeline and preview primary.
- Use the promoted state already carried from shell.
- Do not fork a second graph workflow.
