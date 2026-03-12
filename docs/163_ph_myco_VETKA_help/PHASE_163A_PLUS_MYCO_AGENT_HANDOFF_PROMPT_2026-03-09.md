MARKER_163A_PLUS.MYCO.AGENT_HANDOFF_PROMPT.V1
LAYER: L4
DOMAIN: UI|TOOLS
STATUS: READY
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_163A_PLUS_MYCO_AGENT_HANDOFF_PROMPT_2026-03-09.md
LAST_VERIFIED: 2026-03-09

# Phase 163.A+ MYCO Agent Handoff Prompt

## Synopsis
Prompt pack for another agent to implement only the narrow MYCO/scanner fixes from 163.A+ recon.

## Table of Contents
1. Prompt
2. Scope guardrails
3. Acceptance checks
4. Cross-links
5. Status matrix

## Treatment
This handoff is implementation-oriented. It is grounded in the runtime mismatches confirmed on 2026-03-09.

## Full Spec
### Prompt
You are implementing a narrow deterministic MYCO/scanner correctness slice in `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03`.

Scope only:
- `client/src/components/scanner/ScanPanel.tsx`
- `client/src/components/myco/useMycoModeA.ts`
- `client/src/components/myco/mycoModeARules.ts`
- optional debug markers in `client/src/components/search/UnifiedSearchBar.tsx` and `client/src/components/chat/ChatPanel.tsx`

Do not create new widgets.
Do not redesign connectors.
Do not touch voice or MCC.

Implement these slices:
1. Remove or disable `Browse` for Gmail. `Browse` must remain only for `google_drive`.
2. Emit deterministic scanner connector state events for MYCO:
   - source selected
   - auth modal opened
   - missing oauth client credentials
   - provider expired
   - provider connected
   - tree preview unavailable
   - browser placeholder selected
3. Update MYCO rules so scanner hints distinguish:
   - real local scan
   - real cloud/social connectors
   - browser placeholder
   - developer-preconfig needed before OAuth can begin
4. Add a debug marker proving whether lower chat/scanner lane changes ever override top-lane `myco/vetka` ownership.
5. Add simple white inline icon tokens to MYCO hints for real controls:
   - pin
   - history
   - model directory
   - folder/file
   - scanner/connect

Copy requirement:
- replace vague phrasing like `return found items to VETKA`
- prefer explicit control-based phrasing like `attach the file to chat context with the pin icon`
- if a control is not actually present in the panel, do not mention it

Use markers:
- `MARKER_163A_PLUS.SCANNER.GMAIL_BROWSE_GUARD.V1`
- `MARKER_163A_PLUS.MYCO.SCANNER_CONNECTOR_STATE.V1`
- `MARKER_163A_PLUS.MYCO.BROWSER_PLACEHOLDER_HINT.V1`
- `MARKER_163A_PLUS.LANE_OWNERSHIP_AUDIT.V1`
- `MARKER_163A_PLUS.MYCO.ICON_TEXT_BIND.V1`

Required acceptance:
- Gmail no longer shows `Browse`.
- Browser scanner gets a truthful MYCO hint, not generic scanner text.
- Google Drive auth failure due to missing client credentials yields MYCO remediation hint.
- Scanner hint text uses explicit `pin` wording where pin is the true next action.
- Inline icons are white/simple and visually match the related UI control family.
- No unrelated UI changes.

Primary evidence docs:
- `docs/163_ph_myco_VETKA_help/PHASE_163A_PLUS_MYCO_SUBPANELS_RECON_REPORT_2026-03-09.md`
- `docs/163_ph_myco_VETKA_help/PHASE_163A_PLUS_MYCO_RUNTIME_MISMATCH_REPORT_2026-03-09.md`
- `docs/163_ph_myco_VETKA_help/PHASE_163A_PLUS_MYCO_NARROW_FIX_PLAN_2026-03-09.md`

### Scope Guardrails
- Keep implementation narrow.
- Prefer exact provider-id checks over broad provider-class checks when the UI action is subtype-specific.
- Emit structured categories for MYCO rather than parsing backend error strings in multiple places.

### Acceptance Checks
- browser verify on `localhost:3001`
- scanner cloud -> Gmail card
- scanner browser source
- scanner cloud -> Google Drive Auth without creds

## Cross-links
See also:
- [PHASE_163A_PLUS_MYCO_NARROW_FIX_PLAN_2026-03-09.md](./PHASE_163A_PLUS_MYCO_NARROW_FIX_PLAN_2026-03-09.md)
- [PHASE_163A_PLUS_MYCO_RUNTIME_MISMATCH_REPORT_2026-03-09.md](./PHASE_163A_PLUS_MYCO_RUNTIME_MISMATCH_REPORT_2026-03-09.md)

## Status Matrix
| Item | Status |
|---|---|
| Prompt ready for handoff | Ready |
