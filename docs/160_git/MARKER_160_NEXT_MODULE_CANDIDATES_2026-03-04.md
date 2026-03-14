# MARKER_160 - Next Module Candidates (2026-03-04)

## Goal
Find additional VETKA areas that are strong candidates for separate public modules after current 8-core split.

## Recon Basis
- Directory weight by file count (`src/*`)
- Coupling proxy:
  - `incoming_refs`: how many imports from other modules point to target
  - `outgoing_refs`: how many imports target has to other modules
- Practical boundary check by file semantics and existing annotations (`@used_by`, `@depends`)

## Coupling Snapshot (unsplit areas)
- `api` files=90, incoming=29, outgoing=364 (too central right now)
- `agents` files=27, incoming=59, outgoing=25 (important, but tightly tied to orchestration/runtime)
- `voice` files=14, incoming=22, outgoing=7 (good candidate)
- `intake` files=6, incoming=3, outgoing=2 (excellent candidate)
- `knowledge_graph` files=6, incoming=14, outgoing=3 (good candidate)
- `opencode_bridge` files=4, incoming=1, outgoing=4 (excellent candidate)
- `chat` files=4, incoming=22, outgoing=1 (good candidate)

## Recommended Next Modules

### Tier A (split now)

1. `vetka-intake-core`
- Source prefix: `src/intake`
- Optional paired split: `src/ocr` as `vetka-ocr-core`
- Why now:
  - low coupling,
  - clear responsibility (URL/content ingestion + extraction pipeline entry),
  - useful standalone OSS surface.
- Main risk:
  - hidden runtime assumptions from API handlers; needs explicit boundary docs.

2. `vetka-opencode-bridge`
- Source prefix: `src/opencode_bridge`
- Why now:
  - small, clear adapter layer,
  - natural complement to existing `vetka-bridge-core` and `vetka-mcp-core`.
- Main risk:
  - dependency on provider/key services in monorepo; needs minimal interface stubs.

3. `vetka-voice-runtime`
- Source prefix: `src/voice`
- Why now:
  - coherent voice stack (TTS/STT/streaming/prosody),
  - strong differentiation for public audience.
- Main risk:
  - environment/dependency heaviness (models, external binaries, audio runtime).

### Tier B (split next wave)

4. `vetka-knowledge-graph-core`
- Source prefix: `src/knowledge_graph`
- Optional pair: `src/visualizer` (or separate `vetka-graph-visualizer`)
- Why:
  - compact and conceptually coherent KG core.
- Risk:
  - runtime ties to search/memory embedding layer and frontend tree renderer.

5. `vetka-chat-core` (backend chat state/history)
- Source prefix: `src/chat`
- Why:
  - natural backend counterpart to already split `vetka-chat-ui`.
- Risk:
  - uses services/group-chat/session tooling from broader runtime.

### Tier C (defer until contract hardening)

6. `vetka-agent-pack`
- Source prefix: `src/agents`
- Why defer:
  - heavy behavioral coupling with orchestration + elisya runtime + memory contracts.

7. `vetka-api-gateway`
- Source prefix: `src/api`
- Why defer:
  - highest outgoing coupling in project; this is currently integration shell, not stable module boundary.

## Suggested Split Order (minimal sync risk)
1. `src/intake`
2. `src/opencode_bridge`
3. `src/voice`
4. `src/knowledge_graph`
5. `src/chat`

## Naming Guidance
- Keep naming by role, not implementation details:
  - `*-core`, `*-runtime`, `*-bridge`, `*-engine`
- Avoid overloaded names with existing external projects.

## Execution Guardrails
- Preserve monorepo as source-of-truth.
- Publish only by subtree split from one branch.
- Do not duplicate manual edits in target repos.
- Add README/CHANGELOG/OPEN_SOURCE_CREDITS at split time (same pattern as current 8 modules).
