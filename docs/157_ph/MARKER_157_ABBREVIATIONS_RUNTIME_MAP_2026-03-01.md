# MARKER_157_ABBREVIATIONS_RUNTIME_MAP_2026-03-01

## Goal
Canonical runtime map for glossary terms from:
- `docs/besedii_google_drive_docs/VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md`

Focus:
- VETKA message path (viewport + pinned files + context)
- MYCELIUM/MCC DAG path
- Memory stack participation (CAM/ARC/ELISION/ELISYA/MGC/ENGRAM/STM/HOPE/JEPA)

---

## 1) VETKA message -> context -> provider (live path)

### Context assembly is active and multi-source
- `build_pinned_context(...)` uses unified scoring with Qdrant + CAM + Engram + Viewport + HOPE + MGC  
  (`src/api/handlers/message_utils.py:708`, `:725-732`, `:631-659`)
- `build_viewport_summary(...)` injects camera/pinned/visible state  
  (`src/api/handlers/message_utils.py:1821`)
- `build_json_context(...)` injects dependency+semantic context and applies ELISION compression by default  
  (`src/api/handlers/message_utils.py:1236`, `:1242`, `:1422-1424`)
- Prompt merge point (json + pinned + spatial + history):
  (`src/api/handlers/chat_handler.py:110`, `:155-163`)
- Message handler wiring:
  (`src/api/handlers/user_message_handler.py:1012`, `:1019`, `:1028`, `:1054`)

### Provider call and context budget
- Non-stream: adaptive `max_tokens` resolver  
  (`src/elisya/provider_registry.py:1610-1614`)
- Stream: adaptive `max_tokens` resolver  
  (`src/elisya/provider_registry.py:1813-1817`)

Verdict:
- VETKA direct chat path is memory-aware and context-aware.
- ELISION is active at least on JSON-context branch.

---

## 2) Glossary term status (runtime reality)

### MCC / MYCELIUM / DAG / SCC
- `MCC`: active routes/services (`src/api/routes/mcc_routes.py`, `src/services/mcc_*`)
- `MYCELIUM`: active pipeline/auditor (`src/orchestration/agent_pipeline.py`, `src/services/mycelium_auditor.py`)
- `DAG`: active (executor/routes/aggregator) (`src/orchestration/dag_executor.py`, `src/api/routes/dag_routes.py`)
- `SCC`: active condensed graph path (`src/services/mcc_scc_graph.py`)

### JEPA
- Active integration points:
  - runtime adapter/server (`src/services/mcc_jepa_adapter.py`, `src/services/jepa_runtime.py`, `src/services/jepa_http_server.py`)
  - predictive overlay path (`src/services/mcc_predictive_overlay.py`)
  - semantic DAG hydration (`src/orchestration/semantic_dag_builder.py`, `src/knowledge_graph/jepa_integrator.py`)
- Mode can be runtime/fallback depending on env/backend availability.

### ARC
- Active solver/tools/routes and orchestrator pre-call gap detection:
  (`src/agents/arc_solver_agent.py`, `src/mcp/tools/arc_gap_tool.py`,
   `src/api/routes/knowledge_routes.py`,
   `src/orchestration/orchestrator_with_elisya.py:2398-2407`)

### HOPE
- Active in enhancer + LangGraph + weighted ranking + pipeline integrations:
  (`src/agents/hope_enhancer.py`, `src/orchestration/langgraph_nodes.py`,
   `src/api/handlers/message_utils.py:499`, `src/orchestration/context_fusion.py`)

### CAM
- Active at multiple levels:
  - scoring in message context (`src/api/handlers/message_utils.py:331`, `:363`, `:631`)
  - event emission in message flows (`src/api/handlers/user_message_handler.py` CAM event calls)
  - routes and metrics (`src/api/routes/cam_routes.py`, `src/monitoring/cam_metrics.py`)

### ELISION
- Active in:
  - message JSON context compression (`src/api/handlers/message_utils.py:1242`, `:1422-1424`)
  - orchestrator prompt compression for large prompts (`src/orchestration/orchestrator_with_elisya.py:1298-1307`)
  - standalone compressor core (`src/memory/elision.py`)

### ELISYA
- Active as middleware/state/orchestrator service:
  (`src/elisya/state.py`, `src/elisya/middleware.py`,
   `src/orchestration/orchestrator_with_elisya.py`)
- Not an agent (validated in `src/validators/vetka_validator.py`).

### STM
- Active global buffer + integrations:
  (`src/memory/stm_buffer.py`, `src/orchestration/langgraph_nodes.py`,
   `src/orchestration/cam_engine.py`, `src/voice/jarvis_llm.py`)

### ENGRAM
- Active RAM+Qdrant hybrid preference memory:
  (`src/memory/engram_user_memory.py`)
- Used in context ranking and prompt enrichment:
  (`src/api/handlers/message_utils.py:417`, `src/memory/jarvis_prompt_enricher.py`)

### MGC
- Active cache layer + integrations:
  (`src/memory/mgc_cache.py`, `src/memory/spiral_context_generator.py`)
- In message ranking path (sync-safe Gen0 read):
  (`src/api/handlers/message_utils.py:538-567`)

---

## 3) Important nuance (path-dependent behavior)

- Direct VETKA chat path includes CAM/MGC/Engram/HOPE/ELISION(JSON) in context assembly.
- ARC gap detection is guaranteed on orchestrator agent path, not universally on every direct message.
- JEPA is strongly present in MCC/semantic-DAG and predictive overlay paths; not every plain text chat request invokes JEPA runtime directly.

---

## 4) Operational takeaway for next JEPA cycle

Before adding new logic, keep this invariant:
1. Preserve existing context chain: `viewport + pinned + json(elision) + history`.
2. Preserve memory weighted ranking in `build_pinned_context`.
3. Add observability markers per request (`path`, `jepa_mode`, `elision_on`, `arc_on`, `cam_on`, `mgc_on`) rather than adding more branching logic first.

