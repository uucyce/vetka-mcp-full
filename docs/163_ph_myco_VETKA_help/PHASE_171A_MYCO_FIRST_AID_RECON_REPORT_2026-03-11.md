MARKER_171A.MYCO.FIRST_AID.RECON.REPORT.V1
LAYER: L2
DOMAIN: UI|CHAT|TOOLS|SEARCH|SCANNER|ARTIFACT|VOICE|AGENTS
STATUS: PARTIAL
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_171A_MYCO_FIRST_AID_RECON_REPORT_2026-03-11.md
LAST_VERIFIED: 2026-03-11

# Phase 171.A MYCO First Aid Recon Report

## Synopsis
This report maps the current VETKA error landscape for deterministic MYCO first-aid guidance.

Scope:
- likely user-facing blockers;
- existing raw error signals in code;
- recovery paths that are already real;
- dead ends where MYCO should escalate to `@doctor` or operator guidance.

Important finding:
there is no single universal error index yet.
Current truth is fragmented across:
- backend route errors;
- socket events;
- string-based provider failures;
- panel-local UI states;
- prior browser verify notes.

## Table of Contents
1. Recon method
2. Current global reality
3. Existing error surfaces
4. Domain findings
5. Runtime truth vs docs
6. Primary gaps
7. Cross-links
8. Status matrix

## Treatment
This recon follows the MYCO scenario-authoring method:
- start from cold-start and real failure points;
- verify docs against code;
- prefer runtime-proven paths where already available;
- do not call a state "implemented" if only the copy exists.

## Short Narrative
MYCO is already good at orientation and next-step guidance. The next maturity step is first aid: when the user is stuck, MYCO must classify the block, offer one or two concrete exits, and escalate only when the problem is no longer user-fixable. VETKA already contains many raw error signals, but they are not yet normalized into one deterministic contract.

## Full Spec
### Recon Method
- Scenario-authoring baseline:
  - [MYCO_SCENARIO_AUTHOR_CHECKLIST_V1.md](./MYCO_SCENARIO_AUTHOR_CHECKLIST_V1.md)
  - [MYCO_CORE_SCENARIO_ARCHITECTURE_V1.md](./MYCO_CORE_SCENARIO_ARCHITECTURE_V1.md)
- Existing search-error project brief:
  - [PHASE_171_MYCO_WEB_SEARCH_ERROR_TRIGGER_PROJECT_2026-03-11.md](./PHASE_171_MYCO_WEB_SEARCH_ERROR_TRIGGER_PROJECT_2026-03-11.md)
- Existing subpanel/runtime truth:
  - [PHASE_163A_PLUS_MYCO_SUBPANELS_RECON_REPORT_2026-03-09.md](./PHASE_163A_PLUS_MYCO_SUBPANELS_RECON_REPORT_2026-03-09.md)
  - [PHASE_163A_PLUS_MYCO_BROWSER_VERIFY_NOTES_2026-03-09.md](./PHASE_163A_PLUS_MYCO_BROWSER_VERIFY_NOTES_2026-03-09.md)
- Code checked:
  - `src/api/handlers/unified_search.py:182`
  - `src/mcp/tools/web_search_tool.py:55`
  - `client/src/hooks/useSocket.ts:815`
  - `src/api/routes/connectors_routes.py:126`
  - `client/src/components/scanner/ScanPanel.tsx:508`
  - `src/api/handlers/artifact_routes.py:156`
  - `client/src/WebShellStandalone.tsx:425`
  - `src/api/routes/files_routes.py:169`
  - `src/agents/agentic_tools.py:112`
  - `src/api/handlers/group_message_handler.py:597`
- Fast tests run on 2026-03-11:
  - `tests/test_phase169_unified_search_capabilities.py`
  - `tests/test_phase171_unified_web_search.py`
  - `tests/test_phase125_1_doctor_triage.py`
  - `tests/test_phase117_6_dragon_e2e.py`
  - Result: `45 passed`

### Current Global Reality
#### No universal error index
There is no global, product-wide error envelope yet.

Current fragmentation:
- `web/` search still uses raw strings in `source_errors` (`src/api/handlers/unified_search.py:200`-`227`, `src/mcp/tools/web_search_tool.py:63`-`110`)
- socket-level product failures are emitted as separate raw events (`client/src/hooks/useSocket.ts:827`-`830`, `client/src/hooks/useSocket.ts:1938`-`1963`, `client/src/hooks/useSocket.ts:2073`-`2083`)
- scanner/connectors use route-local HTTP details and panel-local alerts (`src/api/routes/connectors_routes.py:149`-`157`, `client/src/components/scanner/ScanPanel.tsx:522`-`538`)
- artifact/media routes expose some hard failures and some degraded reasons, but not one MYCO-facing taxonomy (`src/api/handlers/artifact_routes.py:168`-`170`, `src/api/routes/artifact_routes.py:1290`-`1308`)

#### `@doctor` is real, not speculative
MYCO can escalate to `@doctor` without inventing a new toolchain.

Evidence:
- mention parsing recognizes `@doctor` as a system command: `src/agents/agentic_tools.py:135`-`167`
- solo message handler routes system commands into Mycelium path: `src/api/handlers/user_message_handler.py:1568`-`1585`
- group handler has real doctor triage, hold/dispatch, and quick actions: `src/api/handlers/group_message_handler.py:597`-`739`

Inference:
- `@doctor` is the correct deterministic escalation for multi-surface or unclear failures.
- It should not be the first suggestion for simple recoverable states like "missing key" or "query too short".

### Existing Error Surfaces
#### Search and provider failures
- query-too-short exists as a real backend error: `src/api/handlers/unified_search.py:251`-`259`
- web-provider failure is still string-based: `src/api/handlers/unified_search.py:200`-`227`
- Tavily raw failure cases already exist:
  - no key: `src/mcp/tools/web_search_tool.py:67`-`73`
  - missing SDK: `src/mcp/tools/web_search_tool.py:105`-`107`
  - generic provider exception: `src/mcp/tools/web_search_tool.py:108`-`110`
- search sockets also emit generic `search_error`: `src/api/handlers/search_handlers.py:46`-`55`, `src/api/handlers/search_handlers.py:210`-`215`

#### Connectivity and socket failures
- connect/disconnect are surfaced in client state but not normalized for MYCO: `client/src/hooks/useSocket.ts:815`-`830`
- group, approval, key, search, stream, and voice have separate raw error events:
  - `client/src/hooks/useSocket.ts:1938`-`1963`
  - `client/src/hooks/useSocket.ts:2073`-`2083`
  - `src/api/handlers/group_message_handler.py:1496`, `1508`, `1550`, `1650`
  - `src/api/handlers/key_handlers.py:52`-`55`, `114`-`116`, `162`-`169`

#### Connector and scanner failures
- OAuth client credentials can be missing on the VETKA side: `src/api/routes/connectors_routes.py:149`-`157`
- provider auth may be required even when the panel exists: `src/api/routes/connectors_routes.py:194`-`201`
- panel actions already have real fail points and alerts:
  - scan/disconnect fail: `client/src/components/scanner/ScanPanel.tsx:522`-`538`
  - tree preview fail: `client/src/components/scanner/ScanPanel.tsx:547`-`560`
- prior runtime recon already verified that cloud/social are mixed reality and not pure stubs:
  - [PHASE_163A_PLUS_MYCO_SUBPANELS_RECON_REPORT_2026-03-09.md](./PHASE_163A_PLUS_MYCO_SUBPANELS_RECON_REPORT_2026-03-09.md)

#### Artifact, file, and media failures
- webpage save fetch can fail on route or downstream extraction: `client/src/WebShellStandalone.tsx:425`-`454`, `src/api/handlers/artifact_routes.py:156`-`170`
- artifact panel save can fail generically: `client/src/components/artifact/ArtifactPanel.tsx:724`-`739`, `1008`-`1027`
- detached artifact routes can start without a path:
  - `client/src/ArtifactStandalone.tsx:61`
  - `client/src/ArtifactMediaStandalone.tsx:73`
- file open/save permission and not-found are real backend contracts:
  - permission denied: `src/api/routes/files_routes.py:169`-`172`, `216`-`219`
  - file not found: `src/api/routes/files_routes.py:199`-`200`, `241`-`245`
- media type and media degradation are partially modeled:
  - unsupported media type: `src/api/routes/artifact_routes.py:1290`-`1294`
  - waveform fallback proxy: `src/api/routes/artifact_routes.py:1305`-`1308`
  - playback failure triggers a quality fallback, not a human-readable explanation: `client/src/components/artifact/viewers/VideoArtifactPlayer.tsx:615`-`620`
  - detached media debug already distinguishes `video_missing` and `video_metadata_unavailable`: `client/src/utils/detachedMediaDebug.ts:130`-`140`

#### Voice and input failures
- realtime voice can emit `voice_error`; raw backend messages include "No audio data received" and generic exception text:
  - `src/api/handlers/voice_socket_handler.py:120`-`159`
- voice router also emits actionable text like `STT returned empty - check API keys`: `src/api/handlers/voice_router.py:259`
- client already has a visible timeout path for voice transcription: `client/src/hooks/useSocket.ts:2517`-`2525`

### Domain Findings
#### Finding 1: Search is closest to a reusable first-aid core
Search already has:
- capability checks: `tests/test_phase169_unified_search_capabilities.py`
- an active design brief for structured errors: [PHASE_171_MYCO_WEB_SEARCH_ERROR_TRIGGER_PROJECT_2026-03-11.md](./PHASE_171_MYCO_WEB_SEARCH_ERROR_TRIGGER_PROJECT_2026-03-11.md)
- real deterministic MYCO search categories in frontend state:
  - `client/src/components/myco/mycoModeATypes.ts:48`
  - `client/src/components/myco/useMycoModeA.ts:99`-`106`

Status:
- partially implemented
- best candidate for the first universal first-aid contract

#### Finding 2: Socket-level product failures exist, but MYCO does not own them yet
The product already knows about:
- disconnection
- connection error
- search error
- stream error
- key error
- group error

But the current MYCO slice is not yet the universal interpreter for these events.

Status:
- implemented raw telemetry
- planned MYCO normalization

#### Finding 3: Scanner/connectors need honest recovery copy, not "one-click" fiction
OAuth/connectors are real, but end-user success depends on preconfigured app credentials in VETKA.

This means MYCO must say:
- whether the user can fix it alone
- whether the project/operator must add OAuth client credentials first
- whether a retry makes sense

Status:
- partial
- runtime-proven by prior recon

#### Finding 4: Media and artifacts already have useful low-level signals, but not user-grade first aid
Current code differentiates:
- missing path
- unsupported media type
- waveform degraded fallback
- detached video metadata unavailable
- playback failure fallback to full quality

What is missing:
- one normalized MYCO-facing explanation layer
- concrete user advice per failure
- operator escalation when playback keeps failing

Status:
- partial

#### Finding 5: File permission and not-found are real and should be first-aid scenarios
These are not hypothetical.
They are explicit backend contracts and should produce simple MYCO help:
- permission denied
- file not found
- path is a directory

Status:
- implemented in backend
- not yet normalized for MYCO

### Runtime Truth vs Docs
Current documentation truth for browser/runtime still comes from a mix of:
- prior browser verify docs for scanner/subpanels
- current test-backed recon for search and `@doctor`
- code read for artifact/media/file/voice

This means:
- scanner/connectors truth is stronger than artifact/media truth in this pass
- web-search truth is strongest because it now has docs + code + tests
- media/codec-specific user guidance must stay conservative until explicit runtime events are normalized

### Primary Gaps
1. No product-wide normalized first-aid index
- highest priority gap

2. No event bridge for many user-visible failures
- raw console errors and alerts exist, but MYCO cannot react deterministically

3. Media failure states are too low-level
- enough for debugging
- not enough for user guidance

4. Search is ahead of the rest
- strong candidate to define the universal contract style for other domains

5. `@doctor` exists but is not yet systematically wired as the last-resort escalation policy in VETKA UI guidance

## Cross-links
See also:
- [PHASE_171A_MYCO_FIRST_AID_ERROR_INDEX_AND_SCENARIO_MATRIX_2026-03-11.md](./PHASE_171A_MYCO_FIRST_AID_ERROR_INDEX_AND_SCENARIO_MATRIX_2026-03-11.md)
- [PHASE_171A_MYCO_FIRST_AID_ROADMAP_2026-03-11.md](./PHASE_171A_MYCO_FIRST_AID_ROADMAP_2026-03-11.md)
- [PHASE_171A_MYCO_FIRST_AID_SCENARIO_WRITER_LOG_2026-03-11.md](./PHASE_171A_MYCO_FIRST_AID_SCENARIO_WRITER_LOG_2026-03-11.md)
- [PHASE_171A_MYCO_FIRST_AID_AGENT_HANDOFF_PROMPT_2026-03-11.md](./PHASE_171A_MYCO_FIRST_AID_AGENT_HANDOFF_PROMPT_2026-03-11.md)
- [PHASE_171_MYCO_WEB_SEARCH_ERROR_TRIGGER_PROJECT_2026-03-11.md](./PHASE_171_MYCO_WEB_SEARCH_ERROR_TRIGGER_PROJECT_2026-03-11.md)
- [PHASE_163A_PLUS_MYCO_SUBPANELS_RECON_REPORT_2026-03-09.md](./PHASE_163A_PLUS_MYCO_SUBPANELS_RECON_REPORT_2026-03-09.md)

## Status Matrix
| Scope | Docs | Code | Runtime/Test truth | Status |
|---|---|---|---|---|
| Universal error index | no | fragmented | no | Planned |
| Web first-aid taxonomy | yes | partial | tests yes | Partial |
| `@doctor` escalation | yes | yes | tests yes | Implemented |
| Socket/connectivity raw events | no | yes | code yes | Partial |
| Scanner connector recovery | yes | yes | prior runtime yes | Partial |
| Artifact/media recovery | weak | partial | code-only in this pass | Partial |
| File permission/not-found recovery | no | yes | code yes | Partial |
| Voice timeout/no-audio recovery | no | yes | code/test partial | Partial |
