MARKER_163A_PLUS.MYCO.RUNTIME_MISMATCH.REPORT.V1
LAYER: L4
DOMAIN: UI|TOOLS|CHAT
STATUS: PARTIAL
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_163A_PLUS_MYCO_RUNTIME_MISMATCH_REPORT_2026-03-09.md
LAST_VERIFIED: 2026-03-09

# Phase 163.A+ MYCO Runtime Mismatch Report

## Synopsis
This file lists concrete mismatches between intended MYCO guidance surfaces and the product that actually runs today.

## Table of Contents
1. Findings
2. Severity scale
3. Recommendations
4. Cross-links
5. Status matrix

## Treatment
Severity uses product-debug meaning:
- P1: user-facing contract break or misleading action
- P2: partial contract mismatch with workaround
- P3: stale docs or technical debt without immediate user harm

## Short Narrative
The largest problem is not that subpanels are missing. It is that some panels look more real than they are. MYCO must therefore become status-aware, especially in connectors and mixed search/scanner surfaces.

## Full Spec
### Findings
1. P1: Cloud OAuth is not end-user self-sufficient.
- Symptom: `Google Drive -> Auth -> Continue` fails with missing OAuth client credentials.
- Code cause: backend requires `*_CLIENT_ID/*_CLIENT_SECRET` or secure-store credentials before OAuth can start. Evidence: `src/api/routes/connectors_routes.py:126`-`158`, `523`-`540`.
- Runtime evidence: Playwright alert on 2026-03-09.
- Recommendation: MYCO must say `developer/admin must configure provider app first` and not promise one-click account connect.

2. P1: Gmail exposes Drive-style `Browse` action.
- Symptom: Gmail card shows `Browse`, but tree preview is logically a Drive file-tree operation.
- Code cause: `isGoogleDrive = provider.id === 'google_drive' || provider.provider_class === 'google'`. Evidence: `client/src/components/scanner/ScanPanel.tsx:1353`, `1395`-`1403`.
- Backend cause: `/tree` always calls `_google_drive_tree`, regardless of whether provider is Gmail or Drive. Evidence: `src/api/routes/connectors_routes.py:211`-`291`, `484`-`502`.
- Runtime evidence: `Gmail -> Browse` produced provider request failure.
- Recommendation: narrow UI fix should scope `Browse` to `provider.id === 'google_drive'` only.

3. P2: Search-lane `cloud/social` and scanner `cloud/social` use the same names but very different execution contracts.
- Code: unified lane marks `cloud/social` unavailable. Evidence: `client/src/components/search/UnifiedSearchBar.tsx:285`-`286`.
- Runtime: scanner `cloud/social` show real connector cards.
- Impact: users can read the surface as one product mode when it is actually two different systems.
- Recommendation: MYCO should explicitly say `scanner connectors`, not `cloud search`, in scanner context.

4. P2: Browser scanner is a visible source but still a placeholder.
- Code: browser falls through to coming-soon render. Evidence: `client/src/components/scanner/ScanPanel.tsx:1446`-`1453`.
- Runtime: `Browser History -> Coming soon`.
- Recommendation: MYCO should redirect users to `web/` search or documented future roadmap, not to browser import steps.

5. P3: Chat still mounts a separate `UnifiedSearchBar`.
- Code evidence: `client/src/components/chat/ChatPanel.tsx:3032`-`3079`.
- Impact: lane ownership bugs remain possible even if not reproduced in this pass.
- Recommendation: keep in fix-plan as guardrail audit, not immediate rewrite.

6. P3: Existing phase-163 docs understate the current `myco/`-first lane reality.
- Code evidence: `client/src/components/search/UnifiedSearchBar.tsx:281`-`283`, `307`.
- Runtime evidence: app starts in `myco/` lane.
- Recommendation: update docs and MYCO hint library wording.

### Recommendations
- Convert scanner connector hints from generic `connect source` copy into status-classified copy: `pending`, `expired`, `connected`, `review required`, `missing app credentials`.
- Hide or demote fake affordances before adding more persona text.
- Keep the top lane as source-of-truth and let lower subpanels feed it normalized state instead of parallel guidance.

## Cross-links
See also:
- [PHASE_163A_PLUS_MYCO_SUBPANELS_RECON_REPORT_2026-03-09.md](./PHASE_163A_PLUS_MYCO_SUBPANELS_RECON_REPORT_2026-03-09.md)
- [PHASE_163A_PLUS_MYCO_SUBPANELS_SCENARIO_MATRIX_2026-03-09.md](./PHASE_163A_PLUS_MYCO_SUBPANELS_SCENARIO_MATRIX_2026-03-09.md)
- [PHASE_163A_PLUS_MYCO_NARROW_FIX_PLAN_2026-03-09.md](./PHASE_163A_PLUS_MYCO_NARROW_FIX_PLAN_2026-03-09.md)

## Status Matrix
| Finding | Severity | Status |
|---|---|---|
| OAuth client preconfig hidden behind normal UI | P1 | Open |
| Gmail Browse miswired | P1 | Open |
| Search/scanner `cloud/social` naming collision | P2 | Open |
| Browser scanner placeholder | P2 | Open |
| Dual lane instances | P3 | Open |
| Docs stale on `myco/` default lane | P3 | Open |
