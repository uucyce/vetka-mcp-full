MARKER_163A_PLUS.MYCO.SUBPANELS.SCENARIO_MATRIX.V1
LAYER: L3
DOMAIN: UI|CHAT|TOOLS
STATUS: PARTIAL
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_163A_PLUS_MYCO_SUBPANELS_SCENARIO_MATRIX_2026-03-09.md
LAST_VERIFIED: 2026-03-09

# Phase 163.A+ MYCO Subpanels Scenario Matrix

## Synopsis
Deterministic hint matrix for subpanels that materially affect next actions in the current VETKA runtime.

## Table of Contents
1. Matrix
2. Silence rules
3. Transition rules
4. Cross-links
5. Status matrix

## Treatment
This matrix is written for MYCO Mode A. It does not assume LLM help in the primary loop.

## Short Narrative
MYCO should explain only what is true in the panel the user is actually in. If a panel is only partially wired, MYCO must expose that cleanly and route to the next useful action instead of pretending the panel is complete.

## Full Spec
| Panel | Visible state | Real actions | Fake or partial actions | Deterministic hints | Silence conditions | Transition cue |
|---|---|---|---|---|---|---|
| Main lane `myco/` | empty lane, top guidance ticker | ask MYCO, switch to `vetka/web/file`, open chat | `cloud/social` lane search | explain current surface and best next action | user typing in chat or search | change hint when surface or lane mode changes |
| First run `zero keys` | no configured providers, empty productive route | open chat, open phonebook, open API Keys drawer | pretending scanner/connectors are the first step | `first add one LLM key`, `then add Tavily for web/`, `then connect external sources only if needed` | if keys already exist | once key inventory changes, remove cold-start hint |
| Chat | message list, input, history/models buttons | send text, open history, open models, voice input | none confirmed in this pass | `write task`, `open history`, `choose model if route matters` | non-empty input | if history/models open, switch to subpanel-specific hint |
| Scanner local | path input or folder picker, recent files list | add folder, scan, click file, pin file | browser drag directory path is limited in browser runtime | `add folder`, `scan`, `pin file into chat context with the pin button` | active manual typing in top lane if current copy would duplicate | after files appear, hint shifts from connect/add to review/pin |
| Scanner cloud idle | provider cards with statuses | auth, scan, disconnect, browse for some providers | OAuth may fail before app credentials exist | `connect account`, `review token state`, `scan`, `then pin useful result into chat context` | while OAuth modal is open and user already filling fields | when provider becomes connected, shift to `scan` |
| Scanner cloud auth modal | OAuth/API key/link modal | paste client creds, continue OAuth, cancel | looks user-ready even when app creds are missing | `this account needs provider app credentials first`, `continue only after client ID and secret exist`, `cancel and ask admin if needed` | do not repeat if modal already displays fields | on auth error, switch to remediation hint |
| Scanner cloud connected Gmail | connected badge, token saved, scan/disconnect, browse button | scan, disconnect | browse is semantically wrong for Gmail | `scan mailbox snapshot`, `disconnect if wrong account`; suppress browse suggestion | if user already pressed scan | if Gmail browse clicked, switch to mismatch warning |
| Scanner cloud pending Google Drive | pending badge, auth button | auth flow | one-click connect is false until client creds exist | `connect Drive after OAuth app is configured`, `then browse folders`, `then scan selection` | none | after auth success, shift to browse/scan |
| Scanner browser | coming soon block | none | entire source | `browser import is not live yet`, `use web/ search or cloud connectors instead` | none | if user cycles away, remove warning |
| Scanner social | connector cards for GitHub/LinkedIn/Telegram/X | auth for each provider | all providers were pending at verify time | `GitHub first` for fastest working path, `Telegram uses bot token not OAuth`, `LinkedIn may require app review`, `X depends on plan limits` | during open auth modal | after provider connected, shift to scan or disconnect |
| Model Directory list | models, filters, favorites | select model, filter, refresh, star | key drawer not opened in this pass | `pick route/model only when it changes answer path`, `favorite frequent models`, `open keys if no providers work` | when user is scrolling long list with no focus change | if key drawer opens, switch to key onboarding hints |
| History | history icon and panel path exists | open prior chats, restore context | deep state not re-verified in this pass | `reopen prior thread`, `resume context`, `rename or copy chat id if needed` | while user is composing in current chat | if specific chat selected, switch to that chat context |

### Silence Rules
- Stay silent when the user is actively typing in chat. Evidence: `client/src/components/chat/ChatPanel.tsx:129`-`146`.
- Do not repeat onboarding for missing keys if key inventory already reports configured providers. Evidence: `client/src/components/ModelDirectory.tsx:147`-`161` and existing Mode A rules.
- Inside scanner connectors modal, suppress generic scanner hints and use only connector-specific remediation.

### Icon Writing Rule
- MYCO hint text should reference real UI controls with simple white inline icons, not only words.
- Example style:
  - `Attach to chat context with the white pin icon`
  - `Open Model Directory with the white phone icon`
  - `Open History with the white clock icon`
  - `Start scan with the white Scan button`
- The icon token must visually match the actual control family used in the panel.
- MYCO should not invent decorative emoji or colorful symbols for deterministic panel guidance.

### Transition Rules
- `scanner local -> recent files appear`: move from setup hint to review/pin/fly-to hint.
- `cloud/social -> auth modal open`: move from source-level hint to auth-preconditions hint.
- `auth error -> classified error`: move to remediation hint, not generic retry.
- `browser source selected`: immediately disclose placeholder status and point to working alternatives.

## Cross-links
See also:
- [PHASE_163A_PLUS_MYCO_SUBPANELS_RECON_REPORT_2026-03-09.md](./PHASE_163A_PLUS_MYCO_SUBPANELS_RECON_REPORT_2026-03-09.md)
- [PHASE_163A_PLUS_MYCO_RUNTIME_MISMATCH_REPORT_2026-03-09.md](./PHASE_163A_PLUS_MYCO_RUNTIME_MISMATCH_REPORT_2026-03-09.md)
- [PHASE_163A_PLUS_MYCO_NARROW_FIX_PLAN_2026-03-09.md](./PHASE_163A_PLUS_MYCO_NARROW_FIX_PLAN_2026-03-09.md)

## Status Matrix
| Item | Status |
|---|---|
| Core matrix for chat/scanner/cloud/social/browser | Implemented in docs |
| Runtime-backed hints | Partial |
| Connector error classification in MYCO | Implemented |
| Social provider-specific hints | Implemented |
