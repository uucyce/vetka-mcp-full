# PHASE 170 — CUT Scene Graph NLE Pane Node Actions

## Goal
Add small explicit actions inside the NLE Scene Graph pane so graph context can trigger established CUT focus flows.

## First Actions
- `Focus Timeline From Graph`
  - reuses existing graph/shot -> timeline focus flow
- `Focus Selected Shot`
  - keeps the current selected shot active and visible in shared inspector context

## Guardrails
- No separate graph-only transport.
- No duplicate inspector actions.
- Actions should call existing focus logic, not invent parallel state paths.
