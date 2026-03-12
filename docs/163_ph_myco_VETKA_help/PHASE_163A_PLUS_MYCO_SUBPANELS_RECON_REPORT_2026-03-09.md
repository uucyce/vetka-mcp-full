MARKER_163A_PLUS.MYCO.SUBPANELS.RECON.V1
LAYER: L2
DOMAIN: UI|CHAT|TOOLS
STATUS: PARTIAL
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_163A_PLUS_MYCO_SUBPANELS_RECON_REPORT_2026-03-09.md
LAST_VERIFIED: 2026-03-09

# Phase 163.A+ MYCO Subpanels Recon Report

## Synopsis
This report re-checks MYCO-relevant subpanels against current VETKA code and live browser runtime. Scope is narrow: deterministic guidance surfaces inside the unified lane and adjacent subpanels, not persona expansion.

## Table of Contents
1. Recon method
2. Current reality by surface
3. Docs vs code vs runtime mismatches
4. Trigger map for MYCO
5. Status matrix
6. Cross-links

## Treatment
The recon compares three layers:
- docs already written in phase 163
- current frontend/backend code
- current browser runtime at `http://localhost:3001` with API at `http://localhost:5001`

The report also checks dependency truth for OAuth/search providers against official docs.

## Short Narrative
Phase 163.A documents assumed a simpler world: `vetka/web/file` lane, mostly static scanner semantics, and no separate `myco/` first-class lane. Current runtime is different. `myco/` is now the default lane, scanner-family subpanels are deeper, and connectors surfaces look more complete than they really are. MYCO must now distinguish between visible, runnable, partially runnable, and developer-preconfigured states.

## Full Spec
### Recon Method
- Existing MYCO docs reviewed: [PHASE_163A_MYCO_MODE_A_RECON_REPORT_2026-03-08.md](./PHASE_163A_MYCO_MODE_A_RECON_REPORT_2026-03-08.md), [PHASE_163A_SEARCH_LANE_MODE_REFACTOR_RECON_REPORT_2026-03-08.md](./PHASE_163A_SEARCH_LANE_MODE_REFACTOR_RECON_REPORT_2026-03-08.md), [MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md), [MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md](./MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md).
- Frontend code checked:
  - `client/src/components/search/UnifiedSearchBar.tsx:273`
  - `client/src/components/scanner/ScanPanel.tsx:364`
  - `client/src/components/chat/ChatPanel.tsx:129`
  - `client/src/components/chat/ChatPanel.tsx:3032`
  - `client/src/components/ModelDirectory.tsx:147`
- Backend code checked:
  - `src/api/routes/connectors_routes.py:126`
  - `src/api/routes/connectors_routes.py:484`
  - `src/api/routes/connectors_routes.py:523`
  - `src/services/connectors_state_service.py:23`
- Runtime checked in Chrome with Playwright CLI snapshots and live API responses.

### Dependency Reality Check Against Official Docs
- Google OAuth clients must be created in Google Cloud before web or desktop OAuth flows can run. Official docs:
  - [Google Identity OAuth 2.0 for Web Server Applications](https://developers.google.com/identity/protocols/oauth2/web-server)
  - [Google Cloud: Configure OAuth consent](https://support.google.com/cloud/answer/15549257)
- Dropbox OAuth also depends on a registered Dropbox app and app key. Official docs:
  - [Dropbox OAuth Guide](https://developers.dropbox.com/oauth-guide)
- GitHub OAuth requires a registered OAuth app. Official docs:
  - [GitHub Authorizing OAuth Apps](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps)

Inference from these sources:
- End users can sign in with Google, Dropbox, or GitHub only after VETKA itself has already been configured with provider app credentials.
- “One click with Gmail” is realistic only after developer-side provider setup. It is not a zero-config end-user path.

### Current Reality By Surface
#### Unified lane main
- Code: `myco/` and `vetka/` are now first-class contexts, with `myco` default state and `cloud/social` still marked unavailable in lane menu. Evidence: `client/src/components/search/UnifiedSearchBar.tsx:281`-`286`, `client/src/components/search/UnifiedSearchBar.tsx:307`.
- Runtime: top lane starts as `myco/` and shows deterministic MYCO guidance on main surface.
- Status: implemented and live.

#### Chat subpanel
- Code: Chat emits `vetka-myco-chat-input-state` and `vetka-myco-chat-surface-state`, which are usable deterministic triggers for silence and subpanel guidance. Evidence: `client/src/components/chat/ChatPanel.tsx:129`-`146`, `client/src/components/chat/ChatPanel.tsx:196`-`210`.
- Code: Chat still mounts its own `UnifiedSearchBar`, so the lower panel still contains an independent lane instance. Evidence: `client/src/components/chat/ChatPanel.tsx:3032`-`3079`.
- Runtime: chat surface opens and MYCO shows a relevant top-lane hint.
- Status: implemented, but still contract-sensitive because of dual lane instances.

#### Scanner local files
- Code: local scanner is real in browser and Tauri, with path input in browser, folder dialog in Tauri, scanned file list, pinning, and fly-to actions. Evidence: `client/src/components/scanner/ScanPanel.tsx:1233`-`1326`.
- Runtime: local source shows path input and empty-state copy, not a placeholder.
- Status: implemented.

#### Scanner cloud
- Code: cloud source loads provider statuses from `/api/connectors/status`. Evidence: `client/src/components/scanner/ScanPanel.tsx:364`-`389`.
- Backend: provider registry is real for `dropbox`, `gmail`, `google_drive`. Evidence: `src/services/connectors_state_service.py:23`-`87`.
- Runtime: cloud panel is real, not a stub. Live API returned `dropbox`, `gmail`, `google_drive`, with mixed statuses.
- Critical constraint: OAuth start requires provider client credentials to already exist in secure store or env. Evidence: `src/api/routes/connectors_routes.py:126`-`158`, `src/api/routes/connectors_routes.py:523`-`540`.
- Runtime proof: clicking `Google Drive -> Auth -> Continue` raises `Connector auth failed: OAuth client credentials missing for google_drive...`.
- Status: partially implemented. User connect flow depends on developer preconfiguration.

#### Scanner browser
- Code: browser is still in the `sources` array but the render path falls through to the generic coming-soon block. Evidence: `client/src/components/scanner/ScanPanel.tsx:1328`-`1455`.
- Runtime: browser scanner shows `Coming soon` and `Import bookmarks and history`.
- Status: planned/not implemented.

#### Scanner social
- Code: social uses the same connectors panel as cloud. Evidence: `client/src/components/scanner/ScanPanel.tsx:1328`-`1444`.
- Backend registry exists for `github`, `linkedin`, `telegram`, `x`. Evidence: `src/services/connectors_state_service.py:88`-`163`.
- Runtime: social panel is partially real. Connectors are listed, but all were pending at verify time.
- Status: partially implemented.

#### Model Directory / phonebook
- Code: model directory emits MYCO key inventory refresh and loads `/api/keys` only when key drawer is opened. Evidence: `client/src/components/ModelDirectory.tsx:147`-`161`, `client/src/components/ModelDirectory.tsx:449`-`468`.
- Runtime: model list is live and large. Drawer/key-specific runtime was not deeply re-verified in this recon pass.
- Status: implemented, with partial browser verification in this pass.

#### History
- Runtime: history button is present in chat toolbar.
- Browser verify in this pass did not deepen the history inner states because scanner/connectors produced higher-value mismatches first.
- Status: implemented in project, not re-verified deeply in 163.A+ pass.

#### Artifacts/media/file viewers
- This recon pass did not re-open the detached artifact/media windows because the focus was subpanels inside unified lane + scanner family. Existing 163.A artifact findings remain valid until re-run after current media refactor stabilizes.
- Status: covered by prior phase, not primary target of 163.A+.

### Docs vs Code vs Runtime Mismatches
1. `cloud/` and `social/` in unified lane are still visible search contexts, but not runnable search contexts.
- Docs: older phase-163 docs already warned they were disabled, but current lane now also includes `myco/`, so wording is stale.
- Code: `available: false` in lane menu. Evidence: `client/src/components/search/UnifiedSearchBar.tsx:285`-`286`.
- Runtime: scanner `cloud/social` feel active, which can confuse users because search-lane `cloud/social` are still non-executing.

2. Scanner cloud connect looks like normal end-user OAuth, but actually needs app credentials first.
- Docs: not explicit enough in older MYCO corpus.
- Code: hard dependency on stored/env client credentials. Evidence: `src/api/routes/connectors_routes.py:149`-`157`.
- Runtime: confirmed by real alert on Google Drive auth.

3. Gmail gets Drive-like `Browse` affordance.
- Code: UI checks `provider.provider_class === 'google'`, which matches both Gmail and Drive. Evidence: `client/src/components/scanner/ScanPanel.tsx:1353`, `1395`-`1403`.
- Backend: `/tree` route is generic for provider class `google`, but the implementation always queries Drive files. Evidence: `src/api/routes/connectors_routes.py:211`-`291`, `484`-`502`.
- Runtime: `Gmail -> Browse` triggered a provider request error with Google auth failure. Even if token is valid, this action is semantically wrong for Gmail.

4. Chat still hosts a second `UnifiedSearchBar`.
- Docs: earlier refactor doc treated this as a core risk.
- Code: still true. Evidence: `client/src/components/chat/ChatPanel.tsx:3032`-`3079`.
- Runtime: not yet proven to corrupt top-lane ownership in this pass, but the architectural duplication remains.

### Trigger Map For MYCO
Deterministic trigger sources already present:
- `vetka-myco-search-state`: lane context, mode, provider health, and error. Evidence: `client/src/components/search/UnifiedSearchBar.tsx:410`-`422`.
- `vetka-myco-chat-input-state`: silence when user is already typing. Evidence: `client/src/components/chat/ChatPanel.tsx:129`-`146`.
- `vetka-myco-chat-surface-state`: `chat` vs `scanner` vs `group` plus active group. Evidence: `client/src/components/chat/ChatPanel.tsx:196`-`210`.
- `vetka-myco-key-inventory-refresh`: key presence and provider inventory. Evidence: `client/src/components/ModelDirectory.tsx:147`-`161`.

Missing or weak trigger points worth marking in next narrow slice:
- connector modal opened/closed
- connector auth failed with normalized category
- connector tree loaded vs tree failed
- scanner source switched with explicit status payload
- connector status snapshot refresh after scan/disconnect
- icon-token payload for white simple inline control icons in MYCO text

### Copy Precision Requirement
- Scanner hints must name the actual action the user can take.
- Replace vague copy such as `return found items to VETKA` with explicit control-based copy such as:
  - `attach the file to chat context with the pin icon`
  - `open chat first, then pin the file`
  - `run scan, then pin the useful result`
- MYCO copy should prefer control names and concrete verbs over abstract flow language.

## Cross-links
See also:
- [PHASE_163A_PLUS_MYCO_SUBPANELS_SCENARIO_MATRIX_2026-03-09.md](./PHASE_163A_PLUS_MYCO_SUBPANELS_SCENARIO_MATRIX_2026-03-09.md)
- [PHASE_163A_PLUS_MYCO_RUNTIME_MISMATCH_REPORT_2026-03-09.md](./PHASE_163A_PLUS_MYCO_RUNTIME_MISMATCH_REPORT_2026-03-09.md)
- [PHASE_163A_PLUS_MYCO_NARROW_FIX_PLAN_2026-03-09.md](./PHASE_163A_PLUS_MYCO_NARROW_FIX_PLAN_2026-03-09.md)
- [PHASE_163A_PLUS_MYCO_BROWSER_VERIFY_NOTES_2026-03-09.md](./PHASE_163A_PLUS_MYCO_BROWSER_VERIFY_NOTES_2026-03-09.md)
- [PHASE_163A_PLUS_MYCO_AGENT_HANDOFF_PROMPT_2026-03-09.md](./PHASE_163A_PLUS_MYCO_AGENT_HANDOFF_PROMPT_2026-03-09.md)

## Status Matrix
| Surface | Docs | Code | Runtime | Status |
|---|---|---|---|---|
| Top unified lane `myco/` | stale wording | yes | yes | Implemented, docs stale |
| Chat subpanel | yes | yes | yes | Implemented |
| Scanner local | partial | yes | yes | Implemented |
| Scanner cloud | partial | yes | yes | Partial, preconfigured |
| Scanner browser | partial | placeholder | placeholder | Planned |
| Scanner social | partial | yes | yes | Partial |
| Model Directory | yes | yes | partial verify | Partial verify |
| History | yes | yes | shallow verify | Partial verify |
| Artifact/media subpanels | yes | yes | not re-run in this pass | Deferred verify |
