# Phase 55.1: MCP + ARC Integration - Unified Markers

**Date:** 2026-01-26
**Status:** READY FOR IMPLEMENTATION
**Auditors:** 5x Haiku Agents (parallel)
**Verified:** Spot-checked against actual code

---

## Executive Summary

| Category | Markers | Files | Integration Type |
|----------|---------|-------|------------------|
| MCP State Infrastructure | 16 | 4 | Qdrant + Cache |
| Workflow Hooks | 15 | 3 | Agent execution |
| ARC Gaps | 10 | 6 | Semantic paths |
| Chat Entry Points | 12 | 4 | Solo/Group/MCP |
| CAM + Cleanup | 14 | 4 | TTL + Maintenance |
| **TOTAL** | **67** | **21 unique files** | |

---

## PART 1: MCP STATE INFRASTRUCTURE (16 markers)

### MemoryService Integration

| ID | File | Lines | Method | Hook Point |
|----|------|-------|--------|------------|
| MCP-STATE-001 | memory_service.py | 67-74 | `triple_write()` | MCPStateManager.save_state() |
| MCP-STATE-002 | memory_service.py | 28-44 | `save_agent_output()` | MCPStateManager.log_agent() |
| MCP-STATE-003 | memory_service.py | 46-54 | `save_workflow_result()` | MCPStateManager.archive_workflow() |
| MCP-STATE-004 | memory_service.py | 100-126 | `save_performance_metrics()` | MCPStateManager.track_metrics() |

### ElisyaStateService Integration

| ID | File | Lines | Method | Hook Point |
|----|------|-------|--------|------------|
| MCP-STATE-005 | elisya_state_service.py | 54-84 | `get_or_create_state()` | MCPStateManager.create_state_context() |
| MCP-STATE-006 | elisya_state_service.py | 86-107 | `update_state()` | MCPStateManager.update_conversation() |
| MCP-STATE-007 | elisya_state_service.py | 32-33 | `elisya_states dict` | MCPStateManager.get_state_snapshot() |

### QdrantVetkaClient Integration

| ID | File | Lines | Method | Hook Point |
|----|------|-------|--------|------------|
| MCP-STATE-008 | qdrant_client.py | 120-215 | `triple_write()` | MCPStateManager.persist_atomic() |
| MCP-STATE-009 | qdrant_client.py | 61-66 | `COLLECTION_NAMES` | Collections: VetkaTree, VetkaLeaf, VetkaChangeLog, VetkaTrash |
| MCP-STATE-010 | qdrant_client.py | 218-253 | `_write_to_qdrant()` | MCPStateManager.save_vectors() |
| MCP-STATE-011 | qdrant_client.py | 465-492 | `_write_to_changelog()` | MCPStateManager.audit_trail() |
| MCP-STATE-012 | qdrant_client.py | 494-496 | `get_changelog()` | MCPStateManager.get_audit_history() |

### EngramUserMemory Integration

| ID | File | Lines | Method | Hook Point |
|----|------|-------|--------|------------|
| MCP-STATE-013 | engram_user_memory.py | 91 | `ram_cache dict` | MCPStateManager.get_hot_cache() |
| MCP-STATE-014 | engram_user_memory.py | 196-238 | `set_preference()` | MCPStateManager.set_user_state() |
| MCP-STATE-015 | engram_user_memory.py | 161-194 | `get_preference()` | MCPStateManager.get_user_state() |
| MCP-STATE-016 | engram_user_memory.py | 325-341 | `_qdrant_upsert()` | MCPStateManager.sync_to_qdrant() |

---

## PART 2: WORKFLOW HOOKS (15 markers)

### Agent Execution Hooks

| ID | File | Lines | Agent | State to Share |
|----|------|-------|-------|----------------|
| WORKFLOW-001 | orchestrator_with_elisya.py | 1483-1500 | PM | pm_result, elisya_state |
| WORKFLOW-002 | orchestrator_with_elisya.py | 1525-1533 | Architect | architect_result, elisya_state |
| WORKFLOW-003 | orchestrator_with_elisya.py | 1589-1599 | Dev (parallel) | dev_result, dev_state |
| WORKFLOW-004 | orchestrator_with_elisya.py | 1610-1620 | QA (parallel) | qa_result, qa_state |
| WORKFLOW-005 | orchestrator_with_elisya.py | 1698-1721 | EvalAgent | eval_result, eval_score |

### Workflow Coordination Hooks

| ID | File | Lines | Event | State to Share |
|----|------|-------|-------|----------------|
| WORKFLOW-006 | orchestrator_with_elisya.py | 1760-1810 | Approval Gate | approval_status, approval_decision |
| WORKFLOW-007 | orchestrator_with_elisya.py | 1860-1862 | Workflow Complete | result, elisya_state final |
| WORKFLOW-008 | orchestrator_with_elisya.py | 1229-1230 | State Reframing | reframed_state (agent-specific) |
| WORKFLOW-009 | elisya_state_service.py | 54-84 | State Creation | workflow_id, semantic_path |
| WORKFLOW-010 | elisya_state_service.py | 86-107 | State Update | updated ElisyaState |

### Group Chat Integration

| ID | File | Lines | Event | State to Share |
|----|------|-------|-------|----------------|
| WORKFLOW-011 | group_message_handler.py | 800-810 | Agent Call | workflow_id, agent_type, result |
| WORKFLOW-012 | group_message_handler.py | 143-153 | MCP @mention | notification payload |
| WORKFLOW-013 | group_message_handler.py | 284-390 | Hostess Routing | routing_decision |
| WORKFLOW-014 | orchestrator_with_elisya.py | 1433-1436 | Workflow Init | elisya_state, chain |
| WORKFLOW-015 | orchestrator_with_elisya.py | 1625-1652 | Parallel Sync | dev_state, qa_state merge |

---

## PART 3: ARC GAPS INTEGRATION (10 markers)

### Transformer & Path Generation

| ID | File | Lines | Method | ARC Integration |
|----|------|-------|--------|-----------------|
| ARC-001 | vetka_transformer_service.py | 127, 182 | `build_phase9_output()` | arc_suggestions → phase9_output |
| ARC-002 | elisya_state_service.py | 67, 102 | `path_generator.generate()` | semantic_path evolution tracking |
| ARC-003 | routing_service.py | 33-64 | `get_routing_for_task()` | task_type classification → ARC query |

### Qdrant Semantic Search

| ID | File | Lines | Method | ARC Integration |
|----|------|-------|--------|-----------------|
| ARC-004 | hybrid_search.py | 331-379 | `_semantic_search()` | search_by_vector() for ARC gap queries |
| ARC-005 | middleware.py | 105-112, 222-271 | `_fetch_qdrant_context()` | ARC gap injection point |

### Context Fusion

| ID | File | Lines | Method | ARC Integration |
|----|------|-------|--------|-----------------|
| ARC-006 | langgraph_state.py | 72, 172 | `VETKAState.semantic_path` | Path mutation tracking |
| ARC-007 | context_fusion.py | 83-141, 148-188 | `context_fusion()` | Multi-source gap analysis |
| ARC-008 | jarvis_prompt_enricher.py | 467-541, 519 | `enrich_prompt_with_viewport()` | ELISION compression point |

### MCP & API

| ID | File | Lines | Method | ARC Integration |
|----|------|-------|--------|-----------------|
| ARC-009 | vetka_mcp_bridge.py | 80-114 | MCP logging | Tool sequence monitoring |
| ARC-010 | semantic_routes.py | 79-134 | `semantic_tag_search()` | Concept-based file discovery |

---

## PART 4: CHAT ENTRY POINTS (12 markers)

### Solo Chat (5 entry points)

| ID | File | Lines | Marker | Session Hook |
|----|------|-------|--------|--------------|
| CHAT-001 | user_message_handler.py | 245-260 | MARKER_94.5_SOLO_ENTRY | MCP session init |
| CHAT-002 | user_message_handler.py | 269-423 | Ollama local | Context init before call |
| CHAT-003 | user_message_handler.py | 441-646 | Direct provider | Streaming session |
| CHAT-004 | user_message_handler.py | 662-984 | @mention model | Context + model selection |
| CHAT-005 | user_message_handler.py | 1537-1763 | Agent chain | Per-agent context |

### Group Chat (4 entry points)

| ID | File | Lines | Marker | Session Hook |
|----|------|-------|--------|--------------|
| CHAT-006 | group_message_handler.py | 529-615 | MARKER_94.5_GROUP_ENTRY | Group context init |
| CHAT-007 | group_message_handler.py | 700-895 | MARKER_94.6_ROLE_ROUTING | Role-based session |
| CHAT-008 | group_message_handler.py | 95-215 | MCP @mention | Notification buffer |

### MCP Chat (3 entry points)

| ID | File | Lines | Method | Session Hook |
|----|------|-------|--------|--------------|
| CHAT-009 | vetka_mcp_bridge.py | 592-1008 | `call_tool()` | HTTP client + logging |
| CHAT-010 | vetka_mcp_bridge.py | 824-835 | `vetka_call_model` | LLM tool state |
| CHAT-011 | vetka_mcp_bridge.py | 75-114 | MCP_LOG_ENABLED | Group chat buffering |
| CHAT-012 | chat_handler.py | 49-87 | `detect_provider()` | Provider state routing |

---

## PART 5: CAM + CLEANUP (14 markers)

### CAM Engine

| ID | File | Lines | Method | MCP Hook |
|----|------|-------|--------|----------|
| CAM-001 | cam_engine.py | 416-456 | `prune_low_entropy()` | cleanup_marked_nodes() |
| CAM-002 | cam_engine.py | 458-529 | `merge_similar_subtrees()` | Qdrant collection cleanup |

### Compression

| ID | File | Lines | Method | Integration |
|----|------|-------|--------|-------------|
| CAM-003 | compression.py | 94-101 | `COMPRESSION_SCHEDULE` | 768D→384D→256D→64D |
| CAM-004 | compression.py | 371-430 | `check_and_compress()` | TTL expiry cleanup |
| CAM-005 | compression.py | 342-368 | `get_quality_degradation_report()` | MARKER-77-09 metrics |

### Qdrant Cleanup

| ID | File | Lines | Method | Integration |
|----|------|-------|--------|-------------|
| QDR-001 | qdrant_updater.py | 45-50 | `__init__` collection | vetka_elisya |
| QDR-002 | qdrant_updater.py | 394-429 | `soft_delete()` | TTL marking |
| QDR-003 | qdrant_updater.py | 461-512 | `cleanup_deleted()` | 24h TTL cleanup |
| QDR-004 | qdrant_updater.py | 534-602 | `scan_directory()` | Stop flag (Phase 90.6) |

### Initialization

| ID | File | Lines | Method | Integration |
|----|------|-------|--------|-------------|
| INIT-001 | components_init.py | 230-245 | `initialize_all_components()` | Qdrant init order |
| INIT-002 | components_init.py | 216-228 | `on_qdrant_connected()` | Socket.IO + metrics |
| INIT-003 | components_init.py | 52-55 | Locks | Missing CAM lock |
| INIT-004 | components_init.py | 83-141 | `_shutdown_executor()` | atexit cleanup |

### CRITICAL GAPS

| ID | Issue | Impact |
|----|-------|--------|
| MISSING-001 | CAM → Qdrant cleanup not connected | Orphaned Qdrant points |
| MISSING-002 | No maintenance_cycle scheduler | No periodic cleanup |
| MISSING-003 | No TTL expiry for >180 days | Storage bloat |

---

## PART 6: IMPLEMENTATION PLAN

### New Files to Create

```
src/mcp/
├── state/
│   └── mcp_state_manager.py      # [NEW] ~280 lines
├── tools/
│   ├── session_tools.py          # [NEW] ~180 lines
│   ├── compound_tools.py         # [NEW] ~220 lines
│   ├── workflow_tools.py         # [NEW] ~200 lines
│   └── bridge_tools.py           # [NEW] ~150 lines
src/orchestration/services/
└── mcp_state_bridge.py           # [NEW] ~150 lines
```

### Files to Modify

| File | Changes | Lines Changed |
|------|---------|---------------|
| memory_service.py | Add MCP hooks | +30 |
| elisya_state_service.py | Add MCP sync after updates | +25 |
| orchestrator_with_elisya.py | Add MCP hooks after agents | +50 |
| user_message_handler.py | Session init at entry | +20 |
| group_message_handler.py | Session init at entry | +20 |
| vetka_mcp_bridge.py | Register new tools | +40 |
| components_init.py | Add maintenance scheduler | +30 |
| cam_engine.py | Connect to Qdrant cleanup | +15 |

---

## PARALLEL IMPLEMENTATION STEPS

### Phase A: Core Infrastructure (CAN RUN IN PARALLEL)

**Agent A1: MCPStateManager Core**
```
CREATE: src/mcp/state/mcp_state_manager.py
- Class MCPStateManager
- save_state(), get_state(), update_state(), delete_state()
- Qdrant collection: vetka_mcp_states
- LRU cache with TTL
- Integration: MCP-STATE-008, MCP-STATE-010
```

**Agent A2: MCPStateBridge**
```
CREATE: src/orchestration/services/mcp_state_bridge.py
- Class MCPStateBridge extends MemoryService
- save_agent_state(), get_agent_state()
- triple_write sync
- Integration: MCP-STATE-001, MCP-STATE-002, MCP-STATE-003
```

**Agent A3: ARC Gap Detector**
```
ADD TO: elisya_state_service.py
- Method get_arc_gaps(task, workflow_id)
- Query MCP memory for similar concepts
- Score threshold >0.8
- Integration: ARC-002, ARC-004, ARC-005
```

### Phase B: Tool Registration (DEPENDS ON A1)

**Agent B1: Session Tools**
```
CREATE: src/mcp/tools/session_tools.py
- vetka_session_init: Fat context + ELISION compression
- vetka_session_status: Current session info
- Integration: CHAT-001, CHAT-006, CHAT-009
```

**Agent B2: Compound Tools**
```
CREATE: src/mcp/tools/compound_tools.py
- vetka_research: search + read + summarize
- vetka_implement: plan + code + test
- vetka_review: analyze + suggest + validate
- Integration: ARC-001, ARC-007
```

**Agent B3: Workflow Tools**
```
CREATE: src/mcp/tools/workflow_tools.py
- vetka_execute_workflow: PM → Architect → Dev → QA
- Uses Phase 60.1 LangGraph
- Integration: WORKFLOW-001..007
```

### Phase C: Hook Integration (DEPENDS ON A2)

**Agent C1: Orchestrator Hooks**
```
MODIFY: orchestrator_with_elisya.py
- After PM (line 1500): await mcp.save_agent_state()
- After Architect (line 1533): await mcp.save_agent_state()
- After Dev/QA (line 1652): await mcp.merge_parallel_states()
- Workflow complete (line 1862): await mcp.publish_complete()
- Integration: WORKFLOW-001..007, WORKFLOW-014..015
```

**Agent C2: Chat Entry Hooks**
```
MODIFY: user_message_handler.py + group_message_handler.py
- Solo entry (line 245): mcp.init_session()
- Group entry (line 529): mcp.init_group_session()
- Integration: CHAT-001..008
```

**Agent C3: MCP Bridge Tools**
```
MODIFY: vetka_mcp_bridge.py
- Register session_tools
- Register compound_tools
- Register workflow_tools
- Integration: CHAT-009..011
```

### Phase D: Maintenance (DEPENDS ON A1, B1)

**Agent D1: CAM + Cleanup**
```
MODIFY: cam_engine.py + components_init.py
- Add maintenance_cycle() scheduler (24h)
- Connect prune_low_entropy() → Qdrant cleanup
- Add mcp_state.delete_expired_states()
- Integration: CAM-001..005, QDR-003, MISSING-001..003
```

---

## DEPENDENCY GRAPH

```
Phase A (Parallel - No Dependencies):
  A1: MCPStateManager ─────────┐
  A2: MCPStateBridge ──────────┼──→ Phase B
  A3: ARC Gap Detector ────────┘

Phase B (Parallel - Depends on A1):
  B1: Session Tools ───────────┐
  B2: Compound Tools ──────────┼──→ Phase C
  B3: Workflow Tools ──────────┘

Phase C (Parallel - Depends on A2, B*):
  C1: Orchestrator Hooks ──────┐
  C2: Chat Entry Hooks ────────┼──→ Phase D
  C3: MCP Bridge Tools ────────┘

Phase D (Sequential - Depends on A1, B1):
  D1: CAM + Cleanup Scheduler
```

---

## TESTING CHECKLIST

### Unit Tests
- [ ] MCPStateManager: save/get/update/delete states
- [ ] MCPStateBridge: triple_write sync
- [ ] ARC gaps: similarity >0.8 detection
- [ ] Session tools: fat context generation

### Integration Tests
- [ ] Solo chat → MCP session init → agent call → state save
- [ ] Group chat → orchestrator → parallel Dev+QA → state merge
- [ ] MCP tools → workflow execution → state persistence
- [ ] Maintenance cycle → cleanup expired states

### End-to-End Tests
- [ ] Full workflow: PM → Architect → Dev → QA with shared state
- [ ] ARC gaps detected and injected into transformer output
- [ ] 24h maintenance cycle runs without errors

---

## RISK ASSESSMENT

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Qdrant overload | Low | Medium | TTL=3600, cache-first |
| State conflicts | Low | High | Unique agent_id hash |
| Async/sync mix | Medium | Medium | All async, wrappers |
| ARC embed quality | Medium | Low | Use existing path_generator |

---

**Document Complete**
**Ready for Phase A-D Implementation**
