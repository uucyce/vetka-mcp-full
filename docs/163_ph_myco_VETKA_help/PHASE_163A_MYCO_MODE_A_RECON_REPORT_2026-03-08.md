MARKER_163A.MYCO.MODE_A.RECON.REPORT.V1
LAYER: L4
DOMAIN: UI|CHAT|VOICE|MEMORY|TOOLS
STATUS: PARTIAL
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_163A_MYCO_MODE_A_RECON_REPORT_2026-03-08.md
LAST_VERIFIED: 2026-03-08

# PHASE_163A_MYCO_MODE_A_RECON_REPORT_2026-03-08

## Synopsis
Strict recon for `MYCO Mode A`: deterministic, event-driven, rule-based UI guide for VETKA main surface. This report does not trust prior phase labels blindly. It separates what exists in the project, in MCC, in VETKA main UI, and in the VETKA voice path.

## Table of Contents
1. Recon scope
2. Verified implementation status
3. Runtime evidence
4. Gaps that block Mode A
5. Cross-links
6. Status matrix

## Treatment
This document is a go/no-go baseline for implementation. Every claim below is tied to code evidence. "Implemented" always means "implemented in the stated plane", not globally.

## Short Narrative
The project already contains most of the raw ingredients for a deterministic guide layer: stable UI state in `useStore`, real surface toggles in `App.tsx`, a broad socket event stream in `useSocket.ts`, and a mature MYCO contract in MCC. What is missing is the VETKA-main assembly: event normalization, active-surface derivation, next-action rules, a dedicated hint lane, and tests for stale/noisy hint behavior.

## Full Spec
### Recon scope
- Docs checked:
  - `docs/163_ph_myco_VETKA_help/MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1.md`
  - `docs/163_ph_myco_VETKA_help/MYCO_VETKA_CONTEXT_MEMORY_STACK_V1.md`
  - `docs/163_ph_myco_VETKA_help/MYCO_VETKA_GAP_AND_REMINDERS_V1.md`
  - `docs/163_ph_myco_VETKA_help/MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md`
  - `docs/163_ph_myco_VETKA_help/MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md`
  - `docs/163_ph_myco_VETKA_help/MYCO_VETKA_HELP_HINT_LIBRARY_V1.md`
  - `docs/163_ph_myco_VETKA_help/MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1.md`
  - `docs/163_ph_myco_VETKA_help/MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md`
- Code checked:
  - `client/src/App.tsx`
  - `client/src/store/useStore.ts`
  - `client/src/hooks/useSocket.ts`
  - `client/src/components/search/UnifiedSearchBar.tsx`
  - `client/src/components/chat/ChatPanel.tsx`
  - `client/src/components/artifact/ArtifactWindow.tsx`
  - `client/src/components/mcc/MiniChat.tsx`
  - `src/api/routes/chat_routes.py`
  - `src/api/handlers/jarvis_handler.py`
- Tests checked:
  - `tests/test_phase162_p1_myco_helper_contract.py`
  - `tests/test_phase162_p4_p2_myco_guidance_matrix_contract.py`
  - `tests/test_phase162_p4_p1_myco_proactive_chat_contract.py`
  - `tests/test_phase162_p4_p4_node_role_workflow_matrix_contract.py`

### Verified implementation status
| Capability | Implemented in project | Implemented in MCC | Implemented in VETKA main | Implemented in VETKA voice path | Evidence | Recon verdict |
|---|---|---|---|---|---|---|
| Persisted helper mode toggle | Yes | Yes | No | No | `client/src/store/useMCCStore.ts:83`; `tests/test_phase162_p1_myco_helper_contract.py:11` | MCC-only |
| Deterministic proactive reply on context change | Yes | Yes | No | No | `client/src/components/mcc/MiniChat.tsx:239`; `client/src/components/mcc/MiniChat.tsx:247` | MCC-only |
| Deterministic top hint lane | Yes | Yes | No | No | `client/src/components/mcc/MyceliumCommandCenter.tsx:2404`; `client/src/components/mcc/MyceliumCommandCenter.tsx:3667` | MCC-only |
| MYCO quick backend fastpath | Yes | Used by MCC | No native caller | Partial | `src/api/routes/chat_routes.py:409`; `src/api/routes/chat_routes.py:475` | Exists, but not Mode A runtime |
| Hidden retrieval/state-key enrichment | Yes | Used by MCC | No native caller | Yes | `src/api/routes/chat_routes.py:435`; `src/services/myco_memory_bridge.py:243` | Reusable secondary contour |
| Voice help intent layer | Yes | n/a | n/a | Yes | `src/api/handlers/jarvis_handler.py:1144`; `docs/163_ph_myco_VETKA_help/PHASE_163_2_IMPL_VERIFY_REPORT_2026-03-07.md:1` | Voice-only |
| Stable surface state store | Yes | Shared indirectly | Yes | n/a | `client/src/store/useStore.ts:101`; `client/src/store/useStore.ts:127`; `client/src/store/useStore.ts:209` | Strong Mode A input |
| Surface switching in main app | Yes | n/a | Yes | n/a | `client/src/App.tsx:252`; `client/src/App.tsx:253`; `client/src/App.tsx:254`; `client/src/App.tsx:268` | Strong Mode A input |
| Search context switching | Yes | n/a | Yes | n/a | `client/src/components/search/UnifiedSearchBar.tsx:224`; `client/src/components/search/UnifiedSearchBar.tsx:250`; `client/src/components/search/UnifiedSearchBar.tsx:270` | Implemented |
| Cloud/social search execution | No | n/a | No | n/a | `client/src/components/search/UnifiedSearchBar.tsx:254`; `client/src/components/search/UnifiedSearchBar.tsx:255` | Visible but disabled |
| Main-surface MYCO render slot | No | n/a | No | n/a | `client/src/App.tsx:1039`; `client/src/App.tsx:1050`; `client/src/App.tsx:1065`; no MYCO surface there | Missing |
| Main-surface deterministic event bus | Yes | n/a | Partial | n/a | `client/src/App.tsx:444`; `client/src/App.tsx:568`; `client/src/App.tsx:777`; `client/src/App.tsx:850`; `client/src/App.tsx:877`; `client/src/App.tsx:885` | Present but not normalized for MYCO |
| Main-surface hotkey capture | Yes | n/a | Yes | n/a | `client/src/App.tsx:858`; `client/src/App.tsx:874`; `client/src/App.tsx:881`; `client/src/App.tsx:889` | Implemented |
| Runtime tests for VETKA-main MYCO guide | No | MCC only | No | No | `tests/test_phase162_p4_p2_myco_guidance_matrix_contract.py:11`; no phase-163A tests found | Missing |

### Runtime evidence
#### What is actually present in VETKA main
- App-level surface state:
  - chat open/close: `client/src/App.tsx:253`
  - left panel mode: `client/src/App.tsx:254`
  - tree mode: `client/src/App.tsx:268`
  - selection: `client/src/App.tsx:280`; `client/src/App.tsx:282`
- App-level render surfaces:
  - chat panel: `client/src/App.tsx:1039`
  - artifact window: `client/src/App.tsx:1050`
  - dev panel: `client/src/App.tsx:1065`
  - unified search: `client/src/App.tsx:1084`
- App-level event emission:
  - refresh/scanner: `client/src/App.tsx:444`; `client/src/App.tsx:445`
  - web-save refresh/focus: `client/src/App.tsx:568`; `client/src/App.tsx:608`
  - chat drop: `client/src/App.tsx:777`
  - open artifact: `client/src/App.tsx:850`; `client/src/App.tsx:851`
  - save/undo: `client/src/App.tsx:877`; `client/src/App.tsx:885`

#### What is not present in VETKA main
- No `MYCO` component rendered in `App.tsx`.
- No main-surface deterministic reducer for hint state.
- No main-surface dedupe/silence guard for hint spam.
- No main-surface contract tests comparable to MCC phase-162 tests.

#### What is already proven in MCC and can be reused
- Context-key dedupe for proactive helper reply: `client/src/components/mcc/MiniChat.tsx:247`.
- Helper reply event emission: `client/src/components/mcc/MiniChat.tsx:250`.
- Deterministic payload fields sent to backend: `client/src/components/mcc/MiniChat.tsx:297`.
- Contract tests for hint matrices: `tests/test_phase162_p4_p2_myco_guidance_matrix_contract.py:11`.

### Gaps that block Mode A
1. No VETKA-main hint lane.
2. No shared `vetka-myco-*` event contract; existing MYCO events are MCC-prefixed.
3. No active-surface selector object that converts UI/store state into one deterministic focus snapshot.
4. No next-best-action rules for VETKA main surfaces.
5. No stale/noise suppression contract in VETKA main.
6. No e2e or component tests for surface-bound hint changes.

## Cross-links
See also:
- [PHASE_163A_MYCO_MODE_A_ARCHITECTURE_PROPOSAL_2026-03-08](./PHASE_163A_MYCO_MODE_A_ARCHITECTURE_PROPOSAL_2026-03-08.md)
- [PHASE_163A_MYCO_MODE_A_SCENARIO_MATRIX_2026-03-08](./PHASE_163A_MYCO_MODE_A_SCENARIO_MATRIX_2026-03-08.md)
- [PHASE_163A_MYCO_MODE_A_NARROW_MVP_CUT_2026-03-08](./PHASE_163A_MYCO_MODE_A_NARROW_MVP_CUT_2026-03-08.md)
- [PHASE_163A_MYCO_MODE_A_TEST_STRATEGY_2026-03-08](./PHASE_163A_MYCO_MODE_A_TEST_STRATEGY_2026-03-08.md)
- [PHASE_163A_MYCO_MODE_A_IMPLEMENTATION_PLAN_2026-03-08](./PHASE_163A_MYCO_MODE_A_IMPLEMENTATION_PLAN_2026-03-08.md)
- [MYCO_VETKA_GAP_AND_REMINDERS_V1](./MYCO_VETKA_GAP_AND_REMINDERS_V1.md)
- [MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md)

## Status matrix
| Plane | Status | Evidence |
|---|---|---|
| Project-wide MYCO capabilities | Partial | MCC + backend + voice pieces exist |
| MCC deterministic helper | Implemented | `client/src/components/mcc/MiniChat.tsx:239` |
| VETKA main deterministic helper | Not implemented | no MYCO render slot in `client/src/App.tsx` |
| VETKA voice helper | Partial | backend path exists, but not main-surface guide layer |
