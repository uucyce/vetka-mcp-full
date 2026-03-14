MARKER_171A.MYCO.FIRST_AID.AGENT.HANDOFF.V1
LAYER: L4
DOMAIN: UI|SEARCH|SCANNER|ARTIFACT|VOICE|AGENTS
STATUS: PROJECT_BRIEF
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_171A_MYCO_FIRST_AID_AGENT_HANDOFF_PROMPT_2026-03-11.md
LAST_VERIFIED: 2026-03-11

# Phase 171.A MYCO First Aid Agent Handoff Prompt

## Synopsis
Implementation prompt for another agent.
Scope is narrow:
- normalize existing failures
- emit deterministic MYCO triggers
- do not redesign VETKA

## Prompt
You are implementing `MYCO First Aid` for VETKA.

Work in:
`/Users/danilagulin/Documents/VETKA_Project/vetka_live_03`

Primary references:
- [PHASE_171A_MYCO_FIRST_AID_RECON_REPORT_2026-03-11.md](./PHASE_171A_MYCO_FIRST_AID_RECON_REPORT_2026-03-11.md)
- [PHASE_171A_MYCO_FIRST_AID_ERROR_INDEX_AND_SCENARIO_MATRIX_2026-03-11.md](./PHASE_171A_MYCO_FIRST_AID_ERROR_INDEX_AND_SCENARIO_MATRIX_2026-03-11.md)
- [PHASE_171A_MYCO_FIRST_AID_ROADMAP_2026-03-11.md](./PHASE_171A_MYCO_FIRST_AID_ROADMAP_2026-03-11.md)
- [PHASE_171_MYCO_WEB_SEARCH_ERROR_TRIGGER_PROJECT_2026-03-11.md](./PHASE_171_MYCO_WEB_SEARCH_ERROR_TRIGGER_PROJECT_2026-03-11.md)

Protocol:
`RECON+markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY TEST`

### Objective
Turn existing raw user-facing failures into one deterministic MYCO first-aid contract.

### Hard constraints
1. No new widgets.
2. No persona expansion.
3. No LLM in the primary first-aid loop.
4. Prefer structured payloads over raw strings.
5. Keep fixes narrow and traceable.

### First narrow slice
1. Search structured error envelope
- files:
  - `src/api/handlers/unified_search.py`
  - `src/mcp/tools/web_search_tool.py`
  - `client/src/components/search/UnifiedSearchBar.tsx`
  - `client/src/components/myco/useMycoModeA.ts`
  - `client/src/components/myco/mycoModeARules.ts`
- markers:
  - `MARKER_171.SEARCH.ERROR_ENVELOPE.V2`
  - `MARKER_171.SEARCH.MYCO.ERROR_EVENT.V1`
- acceptance:
  - no string-only `source_errors["web"]` for new path
  - `vetka-myco-search-error` emitted with normalized payload

2. Runtime health bridge
- files:
  - `client/src/hooks/useSocket.ts`
  - optional MYCO hook and rules files
- markers:
  - `MARKER_171A.MYCO.RUNTIME_HEALTH.EVENT.V1`
  - `MARKER_171A.MYCO.SOCKET.FAILURE.NORMALIZE.V1`
- acceptance:
  - MYCO can distinguish disconnect vs connect_error vs stream_error

3. Connector first-aid normalization
- files:
  - `client/src/components/scanner/ScanPanel.tsx`
  - optional connectors route only if machine-readable detail is missing
- markers:
  - `MARKER_171A.MYCO.CONNECTOR.FIRST_AID.V1`
- acceptance:
  - missing oauth client
  - auth required
  - expired or token missing
  - tree unavailable
  - scan failed

### Expected output
1. Updated structured events
2. Narrow tests
3. Verify notes
4. No unrelated refactor

### Important policy
- If the failure is user-fixable, give local recovery first.
- If the failure is operator-side, say so clearly.
- Suggest `@doctor` only after one useful recovery step.

### Test expectations
- add regression tests for new payload shape
- prove dedupe and state-signature behavior where possible
- keep browser verify notes short and factual
