# MYCO Test Matrix V1

Status: `P0 CONTRACT`
Date: `2026-03-06`

Marker: `MARKER_162.MYCO.NODE_HELP_MAP.V1`

## Contract tests
1. Store mode enum exists: `off|passive|active`.
2. Context payload includes required fields (`nav_level`, `lod`, `node.kind`, `event.type`).
3. Chat injection uses `role=helper_myco`.
4. OFF mode: zero helper emissions.
5. PASSIVE mode: only explicit trigger emits.
6. ACTIVE mode: click/select emits concise hint.
7. Rate-limit: no spam burst on camera drag.
8. Rules fallback works without API key / LLM.

## UI tests
1. Toggle helper ON/OFF updates badge state.
2. Clicking task node yields MYCO explanation in chat.
3. Clicking agent node yields role/model hint.
4. Switching roadmap->workflow changes explanation context.

## Regression tests
1. Architect chat flow unaffected when helper off.
2. Existing chat model chooser (`Chat -> Context`) still works.
3. Mini-window routing events unaffected.
