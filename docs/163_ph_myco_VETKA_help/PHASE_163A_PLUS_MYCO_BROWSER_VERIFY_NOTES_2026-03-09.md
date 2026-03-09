MARKER_163A_PLUS.MYCO.BROWSER_VERIFY_NOTES.V1
LAYER: L4
DOMAIN: UI|TOOLS
STATUS: IMPLEMENTED
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_163A_PLUS_MYCO_BROWSER_VERIFY_NOTES_2026-03-09.md
LAST_VERIFIED: 2026-03-09

# Phase 163.A+ MYCO Browser Verify Notes

## Synopsis
Live browser notes from Playwright CLI verification on 2026-03-09.

## Table of Contents
1. Environment
2. Verified flows
3. Console/runtime notes
4. Missing fixtures
5. Cross-links
6. Status matrix

## Treatment
Headed Chrome via Playwright CLI. The browser used `http://localhost:3001`. `http://127.0.0.1:3001` refused in this environment, while `localhost` succeeded.

## Short Narrative
The runtime was good enough to validate subpanel truth. It was not stable enough to claim every surface clean. The biggest value came from checking what the UI promised versus what actually happened after click.

## Full Spec
### Environment
- Frontend: `http://localhost:3001`
- Backend: `http://localhost:5001`
- Playwright CLI snapshots used for interaction
- Console on boot:
  - Socket.IO websocket closed before established
  - mycelium websocket closed before established
  - favicon 404

### Verified Flows
- Main app boots into `myco/` lane with top-lane MYCO guidance.
- Simulated `zero keys` inventory via `vetka-myco-key-inventory-refresh` updates first-run hints without mutating real stored keys.
- Main surface under `zero keys` switches to `First run · keys missing`.
- Chat under `zero keys` switches to `Chat surface · setup first`.
- Model Directory under `zero keys` switches to `Model phonebook · no keys yet`.
- Simulated `LLM key exists, Tavily missing` via MYCO event bridge switches main lane to `web/ needs Tavily key`.
- Simulated `web/` remediation flows via MYCO search-state bridge:
  - `401 invalid key` -> `web/ key auth error`
  - `402 billing quota exceeded` -> `web/ quota or billing issue`
  - `429 rate limit` -> `web/ rate limited`
- Open chat from main surface.
- Chat shows MYCO top-lane hint and chat toolbar.
- Switch chat to scanner.
- Scanner local source is real and shows path input in browser runtime.
- Scanner cloud source is real and loads live connector cards.
- Top unified lane renders MYCO inline icon hints as real white icons, not raw token text.
- `Google Drive -> Auth -> Continue` fails with missing OAuth client credentials alert.
- Scanner browser source is a placeholder.
- Scanner social source is real enough to show providers and auth affordances.
- Scanner social source now yields provider-specific MYCO hints:
  - `GitHub first`
  - `Telegram setup`
  - `LinkedIn review`
- `Gmail` no longer shows false `Browse` affordance after guard narrowing.
- Model Directory opens and renders live model inventory.

### Console/Runtime Notes
- `localhost` works where `127.0.0.1` refused for Playwright page navigation.
- Current runtime started with a favicon 404 and websocket warnings; those were not primary blockers for subpanel recon.
- Top-lane MYCO ticker now resolves icon tokens such as `pin`, `scanner`, `folder`, and `web` into inline white icons inside the unified lane.
- First-run onboarding was browser-verified through the existing MYCO event bridge:
  - `window.dispatchEvent(new CustomEvent('vetka-myco-key-inventory-refresh', { detail: { totalKeys: 0, providers: [] } }))`
  - this changed MYCO state without touching real `/api/keys` storage.
- Web remediation was browser-verified through the existing MYCO search-state bridge:
  - `window.dispatchEvent(new CustomEvent('vetka-myco-search-state', { detail: { scope: 'main', context: 'web', ... } }))`
  - this exercised deterministic error classification without mutating provider storage.
- Cloud connector statuses at verify time:
  - `dropbox`: connected + expired + token missing
  - `gmail`: connected + token saved
  - `google_drive`: pending
- Social connector statuses at verify time:
  - `github`, `linkedin`, `telegram`, `x`: all pending
- Social modal checks at verify time:
  - `Telegram` opens manual token flow, not OAuth
  - `LinkedIn` opens OAuth flow and MYCO warns about app review or approval

### Missing Fixtures
- No seeded success fixture for Google Drive OAuth completion.
- No seeded success fixture for GitHub/Telegram social auth.
- No deep history panel traversal in this pass.
- No detached artifact/media window verify in this pass.

## Cross-links
See also:
- [PHASE_163A_PLUS_MYCO_SUBPANELS_RECON_REPORT_2026-03-09.md](./PHASE_163A_PLUS_MYCO_SUBPANELS_RECON_REPORT_2026-03-09.md)
- [PHASE_163A_PLUS_MYCO_RUNTIME_MISMATCH_REPORT_2026-03-09.md](./PHASE_163A_PLUS_MYCO_RUNTIME_MISMATCH_REPORT_2026-03-09.md)

## Status Matrix
| Flow | Result |
|---|---|
| Main `myco/` lane | Pass |
| First-run zero-keys fixture on main surface | Pass |
| First-run zero-keys fixture in chat | Pass |
| First-run zero-keys fixture in Model Directory | Pass |
| `LLM key exists, Tavily missing` | Pass |
| `web/` auth remediation | Pass |
| `web/` billing remediation | Pass |
| `web/` rate-limit remediation | Pass |
| Chat open | Pass |
| Scanner local | Pass |
| Scanner cloud status cards | Pass |
| MYCO icon-text binding in top lane | Pass |
| Google Drive auth start | Pass, honest failure path |
| Browser scanner | Placeholder confirmed |
| Social scanner cards | Pass, partial |
| Social scanner provider-specific hints | Pass |
| Gmail Browse guard | Pass |
| Model Directory open | Pass |
