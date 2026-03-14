# Grok Research Round 2 — Memory Architecture Analysis

**Source:** 3 documents from Grok (VETKA AI Agent), ~20K chars total
**Date:** 2026-02-17
**Topic:** Persistence concerns in Phase 154, VETKA memory integration, QIM, OpenClaw

---

## Opus Audit Results

Opus провёл полный аудит кодовой базы для проверки утверждений Грока.

### Memory System (production, main branch):

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| STM Buffer | `src/memory/stm_buffer.py` | ~200 | Production, in pipeline |
| ELISION Compression | `src/memory/elision.py` | ~300 | 23-43% token savings |
| MGC Cache (4-tier) | `src/memory/mgc_cache.py` | ~400 | Gen 0 RAM → Gen 1 Qdrant → Gen 2 JSON → Gen 3 Archive |
| Engram User Memory | `src/memory/engram_user_memory.py` | ~300 | Qdrant + RAM hot cache |
| Qdrant Client | `src/memory/qdrant_client.py` | ~800 | Full CRUD + batch |
| Qdrant Batch Manager | `src/memory/qdrant_batch_manager.py` | ~400 | Async queue |
| Surprise Detector (CAM) | `src/memory/surprise_detector.py` | ~600 | Novelty scoring |
| Compression | `src/memory/compression.py` | ~500 | DEP graph pruning |
| DEP Compression | `src/memory/dep_compression.py` | ~300 | Dependency-aware |
| Diff tracking | `src/memory/diff.py` | ~400 | Change tracking |
| Snapshot | `src/memory/snapshot.py` | ~400 | State snapshots |
| Replay Buffer | `src/memory/replay_buffer.py` | ~400 | Experience replay |
| User Memory Updater | `src/memory/user_memory_updater.py` | ~600 | Auto-update prefs |
| **Total** | | **~10,876** | **Production** |

### Model Routing (production, main branch):

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| ModelRouter v2 | `src/elisya/model_router_v2.py` | ~200 | Task-type routing |
| LLM Model Registry | `src/elisya/llm_model_registry.py` | ~300 | 20+ model profiles, Artificial Analysis API |
| Provider Registry | `src/elisya/provider_registry.py` | ~2000 | 7 providers, FC support, key rotation |
| Capability Matrix | `src/elisya/capability_matrix.py` | 65 | Stream/FC mode detection |

### Pipeline Integration (verified):

- `agent_pipeline.py` lines 106, 121: STM + ELISION imports
- Lines 1702-1854: `_add_result_to_stm()`, `_get_stm_memory_stats()`
- Lines 3167, 3285: Qdrant semantic search with `include_prefs: False`
- `orchestrator_with_elisya.py` line 69: ModelRouter import + RoutingService

---

## Grok's Proposals — Verdict

### Accepted (3 items, integrated into Phase 154 Roadmap):

1. **Qdrant Fallback для Persistence (154.17B)**
   - Grok: "If config corrupt → restore from VETKA memory"
   - Implementation: `project_config.json` corrupt → query Qdrant `project_state` → rebuild
   - Fallback chain: JSON → Qdrant → directory scan

2. **Memory-Aware Drill-Down (154.1C)**
   - Grok: "syncWithVETKAMemory() on level change"
   - Implementation: `useMatryoshkaStore.drillDown()` triggers async Qdrant query
   - Context: related files, past attempts, feedback — enriched node metadata

3. **Architect Chat Engram Integration (154.12B)**
   - Grok: "Architect remembers via RAG on user_interactions"
   - Implementation: MiniChat expand → load Engram history (communication_style, topics)
   - Full Architect intelligence → Phase 156, but UI hook now

### Rejected (7 items):

| Proposal | Reason |
|----------|--------|
| `agent_memory_hook.py` (~100 lines) | STM/ELISION/MGC already wired directly in pipeline. Abstraction layer adds indirection without value now |
| `model_catalog.json` | Duplicate of `llm_model_registry.py` which already has 20+ models with API fetch |
| `compression_pipeline.py` + QIM | `compression.py` (17K) + `dep_compression.py` (10K) already exist. QIM is Phase 137 research, not implemented |
| `engram_integration.py` | = `engram_user_memory.py` (production, hybrid RAM/Qdrant) |
| OpenClaw synergy | Simple vector DB chatbot. Our 4-tier MGC + graph is superior. Nothing to adopt |
| MCP duality (MCP1 routing + MCP2 compression) | Terminology confusion. Our MCP = Model Context Protocol server (FastAPI+SocketIO), not "Memory Compression Pipeline" |
| `model_router.py` pseudocode | = `model_router_v2.py` already production with same routing logic |

### Deferred to Future Phases:

| Idea | Phase | Why |
|------|-------|-----|
| Agent-scoped memory (Project/Task/Role) | Phase 156 | Good architecture, but needs Project Architect first |
| QIM (70-80% compression) | Phase 155+ | Research Phase 137. Current ELISION (23-43%) sufficient |
| Multi-Model Council (parallel voting) | Phase 157+ | Research Phase 131. ModelRouter v2 sufficient for now |

---

## Key Insight

Grok's concern about "losing VETKA memory" is unfounded. The memory system is:
- **10,876 lines** of production code
- **4-tier generational cache** (MGC: RAM → Qdrant → JSON → Archive)
- **Already integrated** in agent_pipeline.py (STM + ELISION + Qdrant search)
- **Engram** for user preferences (hot RAM + cold Qdrant)

Phase 154 is a **UI simplification** phase. Memory architecture is untouched.
`project_config.json` is a lightweight bootstrap for cold start — not a replacement for Qdrant.
