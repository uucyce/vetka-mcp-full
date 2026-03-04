# CODEX Deep Recon — VETKA Internals for Modular OSS

Date: 2026-03-04
Scope: internal architecture reconnaissance with focus on ELISYA orchestration, MCP topology, bridge layer, and data→vector scanner pipeline.

## MARKER_160_RECON_1_ORCHESTRATION_REALITY

1. ELISYA is the orchestrator core in current runtime.
- `src/orchestration/orchestrator_with_elisya.py`
- `src/orchestration/` contains orchestration substrate (pipeline, DAG execution, context packing, CAM integration, triple-write manager).
- `src/elisya/` contains provider/model/key/middleware runtime used by orchestrator and services.

2. MYCELIUM is already an extracted execution lane inside repo.
- heavyweight pipeline runtime and task/workflow tools are separated in dedicated MCP server (`mycelium_mcp_server.py`).

## MARKER_160_RECON_2_MCP_TOPOLOGY

Observed MCP servers in codebase:
1. `src/mcp/vetka_mcp_bridge.py`
- fast/stateless + broad tool surface (file/search/git/memory/workflow/context tooling).

2. `src/mcp/mycelium_mcp_server.py`
- autonomous async pipeline/task/workflow/artifact lane.

3. `src/mcp/jarvis_mcp_server.py`
- voice/jarvis specific MCP lane with unified-search proxy.

Current config state:
- `.mcp.json` registers `vetka` + `mycelium`.
- `jarvis` server exists in code, but is not currently in `.mcp.json`.
- `opencode.json` currently wires only `vetka` MCP.

Implication:
- You already have the right modular pattern in practice: multi-server MCP topology with role-based specialization.

## MARKER_160_RECON_3_BRIDGE_LAYER

Bridge unification exists and is strategically important for modular OSS:
- `src/bridge/__init__.py`
- `src/bridge/shared_tools.py`

This layer already acts as shared implementation between:
- MCP bridge (`vetka_mcp_bridge.py`)
- OpenCode/IDE-oriented integration routes.

Modularity implication:
- `bridge` should become a first-class reusable package (`vetka-bridge-core`) with stable tool contracts.

## MARKER_160_RECON_4_DATA_TO_VECTOR_PIPELINE

Data/scanner ingestion is substantial and already close to module shape:
- watchers: `src/scanners/file_watcher.py`
- update/index paths: `src/scanners/qdrant_updater.py`
- extraction registry: `src/scanners/extractor_registry.py`
- artifact ingestion hooks: `src/api/routes/artifact_routes.py`

Observed behavior:
- watcher + updater + extractor chain supports heterogeneous artifacts and multimedia routes,
- indexing/vectorization path is connected to runtime retrieval (search + context assembly).

Modularity implication:
- scanner/extractor/indexing should be separated as its own “ingest engine” module with strict contracts to core runtime.

## MARKER_160_RECON_5_RECOMMENDED_CORE_REPOS

Given actual code topology, recommended first repo split order:

1. `vetka-contracts`
- shared DTO/events/schemas for chat/context/memory/workflow/artifact/MCP.

2. `vetka-mcp-core`
- common MCP framework pieces, base tool abstractions, approval/rate-limit/audit primitives.

3. `vetka-mcp-vetka-server`
- `vetka_mcp_bridge` + thin server wiring.

4. `vetka-mcp-mycelium-server`
- async pipeline/task/workflow server lane.

5. `vetka-mcp-jarvis-server`
- jarvis/voice lane.

6. `vetka-bridge-core`
- reusable shared tool execution layer for MCP + IDE/web integrations.

7. `vetka-ingest-engine`
- scanner/watcher/extractor/updater subsystem.

8. `vetka-memory-stack`
- CAM/STM/ENGRAM/MGC/ELISION subsystem.

9. `vetka-search-retrieval`
- file/hybrid/unified search.

10. `vetka-app-shell` (last)
- current integrated product app.

## MARKER_160_RECON_6_RELEASE_STRATEGY

Safe staged publication:
1. Freeze contracts first (`vetka-contracts`).
2. Publish MCP servers + bridge as separate repos while app still consumes in-tree copies.
3. Publish ingest + memory + search repos.
4. Flip app to consume versioned packages.
5. Only then split UI and advanced modes.

## MARKER_160_RECON_7_GOVERNANCE_FOR_MULTI_AGENT_DEV

For your parallel multi-agent environment, mandatory controls before repo split:
1. compat matrix (`app version` x `contracts` x `mcp servers`).
2. import boundary linting (forbidden cross-module imports).
3. contract tests in CI for each module and each MCP server.
4. changelog discipline per module with explicit breaking-change flag.

This minimizes desync risk while scaling OSS contributions.
