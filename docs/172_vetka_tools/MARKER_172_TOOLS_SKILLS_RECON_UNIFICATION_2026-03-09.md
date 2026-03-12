# MARKER 172 — Tools/Skills Recon + Unification Plan (2026-03-09)

## Goal
Собрать полную картину по инструментам и навыкам (Codex tools, Codex skills, VETKA tools, MYCELIUM tools, MCC API), разложить по контекстам использования и дать план унификации для `auto-memory-tool-context` (через ELISYA + Weaviate/CAM).

## Source of Truth
Inventory exported from code/runtime metadata:
- `docs/172_vetka_tools/TOOLS_SKILLS_CATALOG_2026-03-09.json`
- `docs/172_vetka_tools/TOOLS_SKILLS_CATALOG_2026-03-09.csv`

Primary scanned sources:
- `src/mcp/vetka_mcp_bridge.py`
- `src/mcp/mycelium_mcp_server.py`
- `src/mcp/tools/*.py`
- `src/api/routes/mcc_routes.py`
- `src/api/routes/task_routes.py`
- `/Users/danilagulin/.codex/skills/*/SKILL.md`
- `CLAUDE.md`, `docs/skills/vetka-mcp/SKILL.md`

## Inventory Counts
- Codex tools (agent runtime): `16`
- Installed Codex skills (`~/.codex/skills`): `33`
- VETKA bridge tools (`vetka_*` in bridge): `32`
- MYCELIUM MCP tools (`mycelium_*`): `24`
- MCP package tool implementations: `33`
- MCC API routes: `34`
- Task API routes: `13`

## Context Categories (Execution-Oriented)

### 1) Local Build/Debug Execution (Codex local tools)
Use when editing/testing/committing in workspace.
- `exec_command`, `write_stdin`, `apply_patch`, `parallel`, `update_plan`, `view_image`

### 2) Live External Fact Retrieval (Codex web tools)
Use only when facts can change (news/docs/prices/specs).
- `search_query`, `open`, `click`, `find`, `image_query`, `finance`, `sports`, `weather`, `time`, `screenshot`

### 3) Operator Skills (Codex skill layer)
Reusable workflows; trigger by task intent (deploy, Notion, security, docs, media, etc.).
- total installed: `33` skills
- examples by family:
  - Deploy: `cloudflare-deploy`, `netlify-deploy`, `render-deploy`, `vercel-deploy`
  - GitHub flow: `gh-address-comments`, `gh-fix-ci`, `yeet`
  - Research/docs: `openai-docs`, `notion-*`, `doc`, `pdf`, `spreadsheet`
  - Media: `imagegen`, `speech`, `transcribe`, `sora`, `slides`
  - AppSec: `security-*`
  - Meta: `skill-creator`, `skill-installer`

### 4) VETKA Fast Context/Code Tools (`vetka_*`)
Synchronous/stateless-ish operations for direct code+context work.
- read/search/tree/files/git/camera/session/context_dag/artifacts/workflow wrappers
- key session bootstrap tool: `vetka_session_init`

### 5) MYCELIUM Orchestration Tools (`mycelium_*`)
Async orchestration and pipeline control.
- pipeline, task board, dispatch/import, heartbeat, workflow, artifacts, tracker, playground, health/devpanel

### 6) MCC Orchestration Surface (`/api/mcc/*` + `/api/tasks/*`)
Product-level control plane used by UI and orchestration.
- project/session/sandbox management
- DAG versions and compare
- predictive graph and roadmap generation
- hidden MYCO memory reindex/context endpoints
- task board lifecycle endpoints

## Findings (Important)
1. Tool namespace fragmentation is real.
- Similar capabilities exist in multiple layers (`vetka_task_*` legacy wrappers vs `mycelium_task_*`, plus `/api/tasks/*`).

2. Discovery is static, memory is dynamic.
- Tool schemas are static; contextual choice of the right tool is weakly automated.
- `vetka_session_init` already injects digest + memory context, but not explicit tool-recommendation ranking.

3. Memory signals already exist but are not unified for tool routing.
- ELISION, CAM, hidden MYCO retrieval, Weaviate/Qdrant exist.
- No single “tool-context broker” that ranks tools per current task + runtime state.

4. MCC and MCP are both control planes.
- Need one recommendation layer above both, not another parallel list.

## Proposed Unification: Auto-Memory-Tool-Context

### A. Add a Tool Capability Index (TCI)
Create one index containing every tool/skill/endpoint with normalized metadata:
- `id`, `namespace`, `kind` (`tool|skill|endpoint`)
- `intent_tags` (search, debug, taskboard, deploy, docs, etc.)
- `io_cost` (latency/token), `risk_level`, `requires_approval`
- `runtime_requirements` (backend, ws, mcp, external API)
- `deprecation_aliases` (`vetka_task_* -> mycelium_task_*`)

Storage:
- canonical JSON in repo (`docs/172_vetka_tools/...`)
- optional indexed copy in Weaviate for semantic retrieval by intent.

### B. Add ELISYA Tool-Recommendation Broker
New service (`src/services/tool_context_broker.py`) returning top-N recommended instruments.
Inputs:
- user query/task
- active phase/digest
- session context (`vetka_session_init` payload)
- CAM signals (focus, activation/surprise)
- availability/health (MCP server, backend routes)
Outputs:
- ranked list of tools/skills/endpoints with `why` and confidence

### C. CAM + Weaviate fusion for ranking
Ranking formula (draft):
- `score = semantic_match * 0.50 + cam_focus_boost * 0.20 + runtime_health * 0.15 + recency_success * 0.15`

Where:
- `semantic_match`: query->TCI vector/BM25 match (Weaviate/Qdrant)
- `cam_focus_boost`: current file/area/task context relevance
- `runtime_health`: live availability (health endpoints/session)
- `recency_success`: last successful uses in similar contexts

### D. Wire points (minimal invasive)
1. `vetka_session_init`
- append `recommended_tools` and `recommended_skills` block.

2. pre-tool phase in chat handlers
- before tool execution, ask broker for shortlist.
- pass shortlist as “preferred tools” hint to model/tool executor.

3. MCC surface
- expose `GET /api/mcc/tool-context/recommend` for UI + debugging.

## Immediate Cleanup/Standardization
1. Define canonical namespaces:
- execution: `mycelium_*`
- fast local context/code ops: `vetka_*`
- product API orchestration: `/api/mcc/*`, `/api/tasks/*`

2. Keep compatibility aliases but mark deprecated hard:
- ensure deprecated wrappers always return forward-hint.

3. Introduce one capability taxonomy file:
- `intent_taxonomy`: `build`, `fix`, `research`, `review`, `ops`, `deploy`, `doc`, `media`, `security`, `orchestration`

## Suggested Implementation Phases
- `172.P1`: build TCI schema + initial catalog generator from current sources.
- `172.P2`: implement ELISYA Tool-Context Broker (without UI).
- `172.P3`: inject broker into `vetka_session_init` + chat pre-tool path.
- `172.P4`: add MCC endpoint + simple recommendation panel.
- `172.P5`: collect telemetry and tune ranking weights.

## Risks
- Over-recommendation noise if confidence threshold is too low.
- Tool alias drift if legacy wrappers not synchronized with registry.
- Runtime health checks can add latency if not cached.

## Practical Next Move
Start with `172.P1` now (low risk, high leverage):
- freeze canonical catalog format
- auto-generate from code each run
- add CI check for broken/deleted tool references.
