# CODEX MODULAR OPEN-SOURCE BLUEPRINT — VETKA

Date: 2026-03-04
Scope: decomposition plan for modular OSS release (no code split yet)
Inputs:
- `docs/157_ph/MARKER_157_ABBREVIATIONS_RUNTIME_MAP_2026-03-01.md`
- `src/` topology
- `client/src/` topology
- `src/api/routes/` topology

## MARKER_159_MODULAR_1_GOAL
Target: publish VETKA as modular directories with safe contributor boundaries, while preserving current integrated runtime.

Constraints:
- keep current product working during extraction;
- expose stable contracts first (events, API DTOs, memory context envelope);
- avoid hard coupling of experimental modes to core runtime.

## MARKER_159_MODULAR_2_PROPOSED_MODULES

1. `vetka-core-runtime`
- Responsibility: app lifecycle, config, runtime wiring, health, sessions, feature flags.
- Candidate paths:
  - `src/config/`, `src/initialization/`, `src/api/middleware/`, `src/api/routes/health_routes.py`, `src/api/routes/config_routes.py`, `src/api/routes/session_routes.py`

2. `vetka-chat-runtime` (solo + team chat)
- Responsibility: chat flows, history, groups, transport, prompt assembly entry.
- Candidate paths:
  - backend: `src/api/handlers/chat_*`, `src/api/handlers/user_message_handler.py`, `src/api/routes/chat_routes.py`, `src/api/routes/chat_history_routes.py`, `src/api/routes/group_routes.py`
  - frontend: `client/src/components/chat/`

3. `vetka-memory-stack`
- Responsibility: STM/ENGRAM/MGC/CAM/ELISION memory orchestration and context compression.
- Candidate paths:
  - `src/memory/`, `src/api/routes/cam_routes.py`, memory use-sites in `src/api/handlers/message_utils.py`
- Notes:
  - this is core moat; should be a first-class module, not utility folder.

4. `vetka-search-retrieval`
- Responsibility: unified search, hybrid retrieval, semantic reranking, embeddings adapters.
- Candidate paths:
  - `src/search/`, `src/api/handlers/unified_search.py`, `src/api/routes/unified_search_routes.py`, `src/api/routes/embeddings_routes.py`, frontend `client/src/components/search/`

5. `vetka-graph-mcc-mycelium`
- Responsibility: DAG orchestration, SCC graph, MCC runtime, MYCELIUM pipeline/agent execution.
- Candidate paths:
  - `src/orchestration/dag_*`, `src/services/mcc_*`, `src/orchestration/agent_pipeline.py`, `src/api/routes/mcc_routes.py`, `src/api/routes/dag_routes.py`, frontend `client/src/components/mcc/`

6. `vetka-artifacts-files`
- Responsibility: artifact panel, file ops, approvals, scanner/watcher integration surface.
- Candidate paths:
  - `src/api/routes/artifact_routes.py`, `src/api/routes/file_ops_routes.py`, `src/api/routes/files_routes.py`, `src/services/artifact_scanner.py`, `src/scanners/`, frontend `client/src/components/artifact/`

7. `vetka-pulse-intake`
- Responsibility: data ingestion, watchers, triple-write, extraction registry and content normalization.
- Candidate paths:
  - `src/scanners/`, `src/services/workflow_*` (only ingest-related), `src/api/routes/watcher_routes.py`, `src/api/routes/triple_write_routes.py`, `src/api/routes/pipeline_*`

8. `vetka-agent-registry-and-keys`
- Responsibility: provider registry, model routing, phonebook-like agent/model/key selection.
- Candidate paths:
  - `src/elisya/provider_registry.py`, `src/api/routes/model_routes.py`, `src/api/routes/connectors_routes.py`, frontend model/agent selectors in chat/MCC panels.

9. `vetka-voice-jarvis`
- Responsibility: voice runtime, TTS/STT orchestration, Jarvis path.
- Candidate paths:
  - `src/voice/`, `src/jarvis/`, `src/api/routes/voice_storage_routes.py`, frontend `client/src/components/voice/`, `client/src/components/jarvis/`

10. `vetka-knowledge-mode` (experimental)
- Responsibility: knowledge mode UI + semantic overlays + knowledge routes.
- Candidate paths:
  - `src/api/routes/knowledge_routes.py`, `src/api/routes/semantic_routes.py`, parts of `src/knowledge_graph/`, frontend canvas/knowledge mode controls.

11. `vetka-media-edit-mode` (experimental)
- Responsibility: media-edit pipeline, Premiere/integration adapters, multimedia extraction path.
- Candidate paths:
  - multimedia-related in `src/scanners/`, `src/services/` and docs/contracts for media jobs.
- Rule:
  - isolate from `core-runtime` behind feature flags and connector interfaces.

12. `vetka-ui-shell`
- Responsibility: desktop/web shell, layout, top-level panel orchestration.
- Candidate paths:
  - `client/src/components/panels/`, `client/src/App.tsx`, shared hooks/store/types.

## MARKER_159_MODULAR_3_MINIMAL_FUNCTIONAL_BUNDLES

Bundle A (MVP OSS, smallest useful):
- `core-runtime` + `ui-shell` + `chat-runtime` + `memory-stack` + `search-retrieval` + `artifacts-files`
- Outcome: solo chat with pinned files, long/short memory participation, unified search.

Bundle B (Collaborative orchestrator):
- Bundle A + `graph-mcc-mycelium` + `agent-registry-and-keys`
- Outcome: team-agent workflows, DAG execution, model/key routing.

Bundle C (Voice extension):
- Bundle A + `voice-jarvis`
- Outcome: voice-enabled assistant over same memory/search/chat substrate.

Bundle D (R&D lane):
- Bundle B + `knowledge-mode` + `media-edit-mode` + `pulse-intake`
- Outcome: advanced/experimental capability lane separated from stable OSS core.

## MARKER_159_MODULAR_4_BOUNDARY_CONTRACTS_REQUIRED
Before physical split, freeze these contracts:

1. `ContextEnvelope` (chat input to provider)
- includes: viewport summary, pinned context, json context (with elision marker), history tail.

2. `MemorySignals`
- canonical booleans/weights: `cam_on`, `mgc_on`, `engram_on`, `elision_on`, `arc_on`, `hope_on`, `jepa_mode`.

3. `AgentRegistryContract`
- provider/model/agent/key metadata schema used by chat + MCC + phonebook.

4. `WorkflowDAGContract`
- node/edge/task/result schema shared by MCC UI and backend executors.

5. `ArtifactContract`
- pin/download/edit/approval payloads + event names.

## MARKER_159_MODULAR_5_REPO_LAYOUT_PROPOSAL
Monorepo (recommended first step):

- `apps/vetka-desktop` (current integrated app)
- `modules/vetka-core-runtime`
- `modules/vetka-chat-runtime`
- `modules/vetka-memory-stack`
- `modules/vetka-search-retrieval`
- `modules/vetka-graph-mcc-mycelium`
- `modules/vetka-artifacts-files`
- `modules/vetka-pulse-intake`
- `modules/vetka-agent-registry-and-keys`
- `modules/vetka-voice-jarvis`
- `modules/vetka-knowledge-mode` (experimental)
- `modules/vetka-media-edit-mode` (experimental)
- `packages/vetka-contracts` (shared DTO/events/contracts)
- `packages/vetka-ui-kit` (shared UI primitives)

## MARKER_159_MODULAR_6_EXTRACTION_SEQUENCE

Phase S1 (contract hardening, no moves):
- define `packages/vetka-contracts` and migrate shared types first.

Phase S2 (safe backend split):
- extract `memory-stack`, `search-retrieval`, `agent-registry-and-keys` as internal modules.

Phase S3 (chat + artifact split):
- extract `chat-runtime` and `artifacts-files` with end-to-end tests.

Phase S4 (orchestrator lane):
- extract `graph-mcc-mycelium` and `pulse-intake`.

Phase S5 (experimental lanes):
- isolate `knowledge-mode` and `media-edit-mode` behind feature flags.

## MARKER_159_MODULAR_7_OPEN_SOURCE_RELEASE_PLAN

Release R1 (stable core OSS):
- Bundle A + selective docs and examples.

Release R2 (pro orchestration OSS):
- add Bundle B.

Release R3 (extensions):
- publish Bundle C, then D as experimental repositories or opt-in packages.

## MARKER_159_MODULAR_8_RISKS

1. Hidden cross-imports between `api/handlers`, `memory`, `orchestration`.
2. UI coupling via global stores/events in `client/src/store` and panel-level hooks.
3. Route-level ownership drift (`src/api/routes/*`) without module ownership map.
4. Experimental mode leakage into stable core via shared utility functions.

Mitigation:
- mandatory module owners,
- contract tests per module boundary,
- import-lint rules (forbidden cross-layer imports),
- release train with feature flags.

## MARKER_159_MODULAR_9_DECISION
Recommended first public modular baseline:
- publish Bundle A as OSS core,
- keep MCC/MYCELIUM/Knowledge/Media as opt-in modules until contracts mature.

This gives community value fast without exposing unstable orchestration internals too early.

## MARKER_160_MODULAR_10_MCP_CORE_SPLIT
Observed practical modularity already exists in MCP topology:
- `src/mcp/vetka_mcp_bridge.py` (general VETKA tool lane)
- `src/mcp/mycelium_mcp_server.py` (heavy async pipeline lane)
- `src/mcp/jarvis_mcp_server.py` (voice/jarvis lane)

Recommendation:
- treat MCP as a dedicated module family, not as a subfolder of core runtime:
  - `vetka-mcp-core`
  - `vetka-mcp-vetka-server`
  - `vetka-mcp-mycelium-server`
  - `vetka-mcp-jarvis-server`

## MARKER_160_MODULAR_11_BRIDGE_AND_INGEST_AS_CORES
Two additional cores should be explicit in repo plan:

1. `vetka-bridge-core`
- from `src/bridge/` shared tool abstraction layer used by multiple integration fronts.

2. `vetka-ingest-engine`
- from scanner/watcher/extractor/updater chain:
  - `src/scanners/file_watcher.py`
  - `src/scanners/qdrant_updater.py`
  - `src/scanners/extractor_registry.py`
  - ingest hooks in `src/api/routes/artifact_routes.py`

These are strategic for OSS because contributors can improve adapters/extractors/ingest performance independently of chat UI.
