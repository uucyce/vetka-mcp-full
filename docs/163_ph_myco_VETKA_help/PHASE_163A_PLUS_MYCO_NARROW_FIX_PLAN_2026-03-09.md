MARKER_163A_PLUS.MYCO.NARROW_FIX_PLAN.V1
LAYER: L4
DOMAIN: UI|TOOLS
STATUS: IMPLEMENTED
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_163A_PLUS_MYCO_NARROW_FIX_PLAN_2026-03-09.md
LAST_VERIFIED: 2026-03-09

# Phase 163.A+ MYCO Narrow Fix Plan

## Synopsis
Narrow slices only. No new widgets. No persona expansion. Goal is truthful deterministic guidance for subpanels.

## Table of Contents
1. Fix slices
2. Debug markers
3. Trigger insertion points
4. Go/no-go criteria
5. Cross-links
6. Status matrix

## Treatment
Each slice is scoped so another agent can implement it without changing product architecture.

## Short Narrative
Fix the lie before polishing the advice. The first value is not richer text. It is stricter state truth.

## Full Spec
### Slice 1: Gmail Browse guard
- Goal: remove or disable `Browse` for Gmail.
- File: `client/src/components/scanner/ScanPanel.tsx`
- Current cause: `provider.provider_class === 'google'` is too broad.
- Narrow change: replace `isGoogleDrive` with exact `provider.id === 'google_drive'` for tree affordance and selection badge.
- Marker to add: `MARKER_163A_PLUS.SCANNER.GMAIL_BROWSE_GUARD.V1`
- Go criterion: Gmail card no longer shows `Browse`; Google Drive still does.

### Slice 2: Connector auth state normalization for MYCO
- Goal: emit deterministic status payloads instead of forcing MYCO to parse raw strings.
- Files:
  - `client/src/components/scanner/ScanPanel.tsx`
  - `client/src/components/myco/useMycoModeA.ts`
  - `client/src/components/myco/mycoModeARules.ts`
- Narrow change: dispatch `vetka-myco-scanner-connector-state` on source switch, modal open, auth error, tree error, and successful scan.
- Payload categories:
  - `missing_oauth_client`
  - `provider_token_missing`
  - `provider_connected`
  - `provider_expired`
  - `tree_preview_unavailable`
  - `browser_placeholder`
- Marker to add: `MARKER_163A_PLUS.MYCO.SCANNER_CONNECTOR_STATE.V1`
- Go criterion: MYCO emits connector-specific hints without brittle string matching.

### Slice 3: Browser scanner placeholder honesty
- Goal: make browser-source hint explicit and useful.
- Files:
  - `client/src/components/myco/mycoModeARules.ts`
  - optional `client/src/components/scanner/ScanPanel.tsx` marker only
- Narrow change: MYCO should say browser import is not live and route user to `web/` search or connectors.
- Marker to add: `MARKER_163A_PLUS.MYCO.BROWSER_PLACEHOLDER_HINT.V1`
- Go criterion: selecting browser source never yields generic scanner help.

### Slice 4: Top lane ownership debug marker
- Goal: prove whether chat/scanner lower lane ever overrides main contract.
- Files:
  - `client/src/components/search/UnifiedSearchBar.tsx`
  - `client/src/components/chat/ChatPanel.tsx`
- Narrow change: add debug-only marker log/event when a lane changes context while parent surface is `chat` and top lane is `myco/vetka`.
- Marker to add: `MARKER_163A_PLUS.LANE_OWNERSHIP_AUDIT.V1`
- Go criterion: clear telemetry showing whether duplicate lane instances still fight.

### Slice 5: MYCO icon-text binding
- Goal: make MYCO hints visually point to the same controls the user sees.
- Files:
  - `client/src/components/myco/MycoGuideLane.tsx`
  - `client/src/components/myco/mycoModeARules.ts`
  - optional shared icon helper under `client/src/components/myco/`
- Narrow change:
  - add a tiny deterministic icon-token system for white simple icons inside hint text
  - bind scanner/chat/history/model-directory/pin/folder controls to stable inline icons
  - keep icon style grayscale/white, matching current UI language
- Required wording correction:
  - replace vague `return found items to VETKA` style text with explicit action text like `attach the file to chat context with the pin icon`
- Marker to add: `MARKER_163A_PLUS.MYCO.ICON_TEXT_BIND.V1`
- Go criterion:
  - hints mention concrete controls
  - icon tokens visually match the button family in UI
  - scanner hint explicitly says `pin` where that is the true action

### Trigger Insertion Points
- `client/src/components/scanner/ScanPanel.tsx:364` after connector status load
- `client/src/components/scanner/ScanPanel.tsx:471` on tree open success/fail
- `client/src/components/scanner/ScanPanel.tsx:509` on auth modal submit result
- `client/src/components/chat/ChatPanel.tsx:186` when tab changes to `scanner`
- `client/src/components/search/UnifiedSearchBar.tsx:410` when lane search state is emitted

### Go/No-go Criteria
- GO if fixes stay inside scanner + MYCO deterministic layer.
- NO-GO if implementation requires redesigning full connector architecture or replacing unified lane.

## Cross-links
See also:
- [PHASE_163A_PLUS_MYCO_RUNTIME_MISMATCH_REPORT_2026-03-09.md](./PHASE_163A_PLUS_MYCO_RUNTIME_MISMATCH_REPORT_2026-03-09.md)
- [PHASE_163A_PLUS_MYCO_AGENT_HANDOFF_PROMPT_2026-03-09.md](./PHASE_163A_PLUS_MYCO_AGENT_HANDOFF_PROMPT_2026-03-09.md)

## Status Matrix
| Slice | Status |
|---|---|
| Gmail Browse guard | Implemented and browser-verified |
| Connector state normalization | Implemented and browser-verified |
| Browser placeholder honesty | Implemented and browser-verified |
| Lane ownership audit marker | Implemented |
| MYCO icon-text binding | Implemented and browser-verified |
