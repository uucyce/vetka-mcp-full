# MYCO RAG Agent Roles V1

Marker: `MARKER_162.P3.P3.MYCO.RAG_AGENT_ROLES_SPLIT.V1`

## Architect
- Builds planning-ready DAG.
- Keeps acyclic + monotonic invariants.
- Reports decisions and fallback reasons.

## Builder
- Runs deterministic baseline first.
- Applies refinement only via verifier gate.
- Emits source truth (`baseline|refined`) with reason codes.

## Verifier
- Validates topology and quality.
- Rejects unsafe mutations and forces rollback.

## UI Agent
- Mirrors backend truth in UI.
- Avoids client-side topology distortion.

## QA Agent
- Maintains regression contract suites.
- Verifies route + UI + memory contracts for phase markers.
