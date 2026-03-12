MARKER_171A.MYCO.FIRST_AID.ROADMAP.V1
LAYER: L4
DOMAIN: UI|SEARCH|SCANNER|ARTIFACT|VOICE|AGENTS
STATUS: PROJECT_BRIEF
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_171A_MYCO_FIRST_AID_ROADMAP_2026-03-11.md
LAST_VERIFIED: 2026-03-11

# Phase 171.A MYCO First Aid Roadmap

## Synopsis
Roadmap for turning MYCO into VETKA's deterministic first-aid layer.

Focus:
- normalize failures
- emit stable triggers
- keep advice practical
- escalate to `@doctor` only when needed

## Table of Contents
1. Goal
2. Implementation ladder
3. Debug markers
4. Trigger insertion points
5. Acceptance criteria
6. Prompt for another agent
7. Cross-links
8. Status matrix

## Treatment
The roadmap follows the MYCO scenario-authoring checklist:
1. inventory first
2. normalize reality
3. add deterministic bridges
4. write first-aid hints
5. verify with seeded failure fixtures

## Short Narrative
The product already contains most of the raw failures. The work now is not to invent more personality. It is to convert those failures into stable codes and helpful exits. Search can lead the way. Scanner, socket, artifact, media, voice, and file errors should then follow the same envelope.

## Full Spec
### Goal
Create `MYCO First Aid` as a deterministic emergency guidance contract for VETKA:
- accurate
- non-repetitive
- source-aware
- ready for future voice or LLM deepening

### Implementation Ladder
#### Phase 0. Canonical index
- Freeze the first-aid index from:
  - [PHASE_171A_MYCO_FIRST_AID_ERROR_INDEX_AND_SCENARIO_MATRIX_2026-03-11.md](./PHASE_171A_MYCO_FIRST_AID_ERROR_INDEX_AND_SCENARIO_MATRIX_2026-03-11.md)
- Output:
  - normalized codes
  - severity
  - retryability
  - user-visible flag
  - hint id
- Marker:
  - `MARKER_171A.MYCO.FIRST_AID.INDEX.V1`

#### Phase 1. Search becomes the reference implementation
- Extend Phase 171 web-search brief into a reusable envelope.
- Replace string-only `source_errors["web"]` with structured payload.
- Add:
  - `status`
  - `error_code`
  - `provider`
  - `retryable`
  - `results_count`
  - `results_truncated`
  - `provider_cap`
  - `requested_limit`
  - `hint_id`
  - `state_signature`
- Emit:
  - `vetka-myco-search-error`
- Markers:
  - `MARKER_171.SEARCH.ERROR_ENVELOPE.V2`
  - `MARKER_171.SEARCH.MYCO.ERROR_EVENT.V1`

#### Phase 2. Socket and product health bridge
- Normalize:
  - connect
  - disconnect
  - connect_error
  - search_error
  - stream_error
  - group_error
  - approval_error
  - key_error
- Emit one MYCO-facing event:
  - `vetka-myco-runtime-health`
- Payload:
  - `surface`
  - `code`
  - `severity`
  - `retryable`
  - `user_visible`
  - `state_signature`
- Markers:
  - `MARKER_171A.MYCO.RUNTIME_HEALTH.EVENT.V1`
  - `MARKER_171A.MYCO.SOCKET.FAILURE.NORMALIZE.V1`

#### Phase 3. Scanner and connector first aid
- Normalize:
  - missing oauth client
  - auth required
  - token expired
  - tree unavailable
  - scan failed
  - placeholder source
- Reuse or extend:
  - `vetka-myco-scanner-connector-state`
- Markers:
  - `MARKER_171A.MYCO.CONNECTOR.FIRST_AID.V1`
  - `MARKER_171A.MYCO.CONNECTOR.STATE_SIGNATURE.V1`

#### Phase 4. Artifact, file, and media first aid
- Normalize:
  - file not found
  - permission denied
  - artifact path missing
  - web save failed
  - media unsupported
  - media metadata unavailable
  - playback degraded
- Prefer route-owned, machine-readable details over UI-only strings.
- Markers:
  - `MARKER_171A.MYCO.ARTIFACT.FIRST_AID.V1`
  - `MARKER_171A.MYCO.MEDIA.FIRST_AID.V1`
  - `MARKER_171A.MYCO.FILE.FIRST_AID.V1`

#### Phase 5. Voice first aid
- Normalize:
  - no audio
  - timeout
  - STT empty
  - missing voice key or provider
- Important:
  - keep this only as deterministic first aid
  - no voice persona work in this slice
- Markers:
  - `MARKER_171A.MYCO.VOICE.FIRST_AID.V1`

#### Phase 6. Escalation policy
- Add a deterministic rule:
  - if two local remedies failed or the state is operator-side, suggest `@doctor`
- Do not escalate on the first obvious user-fixable issue.
- Marker:
  - `MARKER_171A.MYCO.DOCTOR.ESCALATION_POLICY.V1`

#### Phase 7. Browser and seeded verify
- Seed states for:
  - zero keys
  - Tavily missing
  - auth error
  - quota
  - rate limit
  - timeout
  - socket disconnect
  - missing oauth client
  - file permission denied
  - media metadata unavailable
- Verify:
  - correct hint
  - dedupe
  - silence on active typing
  - stale hint clears on recovery
- Marker:
  - `MARKER_171A.MYCO.FIRST_AID.VERIFY_MATRIX.V1`

### Debug Markers
- `MARKER_171A.MYCO.FIRST_AID.INDEX.V1`
- `MARKER_171.SEARCH.ERROR_ENVELOPE.V2`
- `MARKER_171.SEARCH.MYCO.ERROR_EVENT.V1`
- `MARKER_171A.MYCO.RUNTIME_HEALTH.EVENT.V1`
- `MARKER_171A.MYCO.SOCKET.FAILURE.NORMALIZE.V1`
- `MARKER_171A.MYCO.CONNECTOR.FIRST_AID.V1`
- `MARKER_171A.MYCO.ARTIFACT.FIRST_AID.V1`
- `MARKER_171A.MYCO.MEDIA.FIRST_AID.V1`
- `MARKER_171A.MYCO.FILE.FIRST_AID.V1`
- `MARKER_171A.MYCO.VOICE.FIRST_AID.V1`
- `MARKER_171A.MYCO.DOCTOR.ESCALATION_POLICY.V1`
- `MARKER_171A.MYCO.FIRST_AID.VERIFY_MATRIX.V1`

### Trigger Insertion Points
- Search:
  - `src/api/handlers/unified_search.py:182`
  - `src/mcp/tools/web_search_tool.py:55`
- Socket:
  - `client/src/hooks/useSocket.ts:815`
  - `client/src/hooks/useSocket.ts:1938`
  - `client/src/hooks/useSocket.ts:2073`
- Connectors:
  - `src/api/routes/connectors_routes.py:126`
  - `client/src/components/scanner/ScanPanel.tsx:508`
  - `client/src/components/scanner/ScanPanel.tsx:543`
- Artifacts/files/media:
  - `src/api/handlers/artifact_routes.py:156`
  - `src/api/routes/files_routes.py:169`
  - `client/src/components/artifact/viewers/VideoArtifactPlayer.tsx:615`
  - `client/src/utils/detachedMediaDebug.ts:130`
- Voice:
  - `src/api/handlers/voice_socket_handler.py:120`
  - `client/src/hooks/useSocket.ts:2517`
- Escalation:
  - `src/agents/agentic_tools.py:135`
  - `src/api/handlers/group_message_handler.py:597`

### Acceptance Criteria
1. MYCO never says vague lines like `something went wrong`.
2. User gets one concrete next move within one hint.
3. Operator-only failures are clearly labeled as operator-side.
4. Repeated failure state does not spam.
5. `@doctor` appears only after a useful local suggestion.
6. Search, connectors, socket, artifact/media, file, and voice all use the same envelope shape.

### Prompt For Another Agent
Use this exact handoff package:
- [PHASE_171A_MYCO_FIRST_AID_AGENT_HANDOFF_PROMPT_2026-03-11.md](./PHASE_171A_MYCO_FIRST_AID_AGENT_HANDOFF_PROMPT_2026-03-11.md)

## Cross-links
See also:
- [PHASE_171A_MYCO_FIRST_AID_RECON_REPORT_2026-03-11.md](./PHASE_171A_MYCO_FIRST_AID_RECON_REPORT_2026-03-11.md)
- [PHASE_171A_MYCO_FIRST_AID_ERROR_INDEX_AND_SCENARIO_MATRIX_2026-03-11.md](./PHASE_171A_MYCO_FIRST_AID_ERROR_INDEX_AND_SCENARIO_MATRIX_2026-03-11.md)
- [PHASE_171A_MYCO_FIRST_AID_SCENARIO_WRITER_LOG_2026-03-11.md](./PHASE_171A_MYCO_FIRST_AID_SCENARIO_WRITER_LOG_2026-03-11.md)
- [PHASE_171_MYCO_WEB_SEARCH_ERROR_TRIGGER_PROJECT_2026-03-11.md](./PHASE_171_MYCO_WEB_SEARCH_ERROR_TRIGGER_PROJECT_2026-03-11.md)

## Status Matrix
| Roadmap slice | Status |
|---|---|
| Canonical index | Ready |
| Search structured errors | Ready for narrow implementation |
| Socket health normalization | Ready for narrow implementation |
| Connector first aid | Ready for narrow implementation |
| Artifact/media/file first aid | Needs event normalization |
| Voice first aid | Needs event normalization |
| `@doctor` escalation policy | Ready for deterministic rules |
