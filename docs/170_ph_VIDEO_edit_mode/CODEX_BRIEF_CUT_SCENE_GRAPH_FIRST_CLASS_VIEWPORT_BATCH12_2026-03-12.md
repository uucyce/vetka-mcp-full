# CODEX BRIEF — Phase 170 CUT Scene Graph First-Class Viewport Batch 12

## Scope
Replace the first NLE Scene Graph placeholder with the shared DAG viewport bridge already used by the shell.

## Tasks
1. Define the shared DAG pane contract for NLE.
2. Mount the shared DAG viewport inside the NLE Scene Graph pane when promotion state is ready.
3. Lock the behavior with docs/tests.

## Guardrails
- Reuse the existing adapter and DAG bridge.
- Do not fork separate graph logic for NLE.
- Keep timeline and preview primary.
