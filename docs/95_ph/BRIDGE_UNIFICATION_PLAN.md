# Bridge Unification Plan
## Phase 95.2 - Gap Analysis & Implementation Plan

**Document ID:** BRIDGE_UNIFY_001
**Status:** DISCOVERY PHASE
**Created:** 2026-01-26
**Author:** Claude Code Analyzer

---

## Executive Summary

**Gap Analysis Results:**
- **MCP Tools Available:** 18 tools
- **OpenCode Endpoints:** 4 endpoints
- **Gap:** 14 tools missing in OpenCode (78% coverage gap)
- **Type Distribution:** 8 read-only + 4 write + 3 collaboration + 3 memory

**Severity:** HIGH - OpenCode bridge severely lacks functionality compared to MCP

---

## Full Gap Matrix

### MCP Bridge Tools (vetka_mcp_bridge.py)

| # | Tool Name | Lines | Category | Implementation | OpenCode |
|---|-----------|-------|----------|-----------------|----------|
| 1 | vetka_search_semantic | 181-202 | READ | REST call | ❌ MISSING |
| 2 | vetka_read_file | 203-216 | READ | REST call | ❌ MISSING |
| 3 | vetka_get_tree | 217-232 | READ | REST call | ❌ MISSING |
| 4 | vetka_health | 233-241 | READ | REST call | ❌ MISSING |
| 5 | vetka_list_files | 242-264 | READ | REST call | ❌ MISSING |
| 6 | vetka_search_files | 265-290 | READ | REST call | ❌ MISSING |
| 7 | vetka_get_metrics | 291-305 | READ | REST call | ❌ MISSING |
| 8 | vetka_get_knowledge_graph | 306-321 | READ | REST call | ❌ MISSING |
| 9 | vetka_edit_file | 325-359 | WRITE | Internal tool | ❌ MISSING |
| 10 | vetka_git_commit | 360-384 | WRITE | Internal tool | ❌ MISSING |
| 11 | vetka_run_tests | 385-414 | WRITE | Internal tool | ❌ MISSING |
| 12 | vetka_camera_focus | 415-441 | WRITE | Internal tool | ❌ MISSING |
| 13 | vetka_git_status | 442-450 | READ | Internal tool | ❌ MISSING |
| 14 | vetka_call_model | 451-495 | EXEC | Internal tool | ❌ MISSING |
| 15 | vetka_read_group_messages | 496-514 | READ | REST call | ❌ MISSING |
| 16 | vetka_get_conversation_context | 518-542 | MEMORY | REST/Internal | ❌ MISSING |
| 17 | vetka_get_user_preferences | 543-563 | MEMORY | Internal tool | ❌ MISSING |
| 18 | vetka_get_memory_summary | 564-584 | MEMORY | Internal tool | ❌ MISSING |

### OpenCode Endpoints (opencode_bridge/routes.py)

| # | Endpoint | Method | Lines | Functionality |
|---|----------|--------|-------|-----------------|
| 1 | /openrouter/keys | GET | 17-33 | Retrieve OpenRouter keys |
| 2 | /openrouter/invoke | POST | 36-61 | Invoke OpenRouter model |
| 3 | /openrouter/stats | GET | 64-86 | Get bridge statistics |
| 4 | /openrouter/health | GET | 89-96 | Health check |

---

## Gap Analysis by Category

### READ-ONLY TOOLS (8 missing)
```
vetka_search_semantic        [181-202] → REST /api/search/semantic
vetka_read_file              [203-216] → REST /api/files/read
vetka_get_tree               [217-232] → REST /api/tree/data
vetka_health                 [233-241] → REST /api/health
vetka_list_files             [242-264] → REST /api/tree/data (filtered)
vetka_search_files           [265-290] → REST /api/search/semantic
vetka_get_metrics            [291-305] → REST /api/metrics/*
vetka_get_knowledge_graph    [306-321] → REST /api/tree/knowledge-graph
```

**Impact:** Cannot browse code, search, or retrieve project metadata via OpenCode

### WRITE/EXECUTION TOOLS (4 missing)
```
vetka_edit_file              [325-359] → Internal EditFileTool
vetka_git_commit             [360-384] → Internal GitCommitTool
vetka_run_tests              [385-414] → Internal RunTestsTool
vetka_camera_focus           [415-441] → Internal CameraControlTool
```

**Impact:** OpenCode cannot modify files or execute git operations

### EXECUTION TOOLS (1 missing)
```
vetka_call_model             [451-495] → Internal LLMCallTool
```

**Impact:** Cannot invoke LLM models from OpenCode

### COLLABORATION TOOLS (1 missing)
```
vetka_read_group_messages    [496-514] → REST /api/groups/{id}/messages
```

**Impact:** No group chat awareness in OpenCode

### MEMORY TOOLS (3 missing)
```
vetka_get_conversation_context    [518-542] → REST/Internal
vetka_get_user_preferences        [543-563] → Internal EngramUserMemory
vetka_get_memory_summary          [564-584] → Internal MemoryCompression
```

**Impact:** No context awareness or memory integration in OpenCode

### GIT STATUS TOOL (1 missing - READ)
```
vetka_git_status             [442-450] → Internal GitStatusTool
```

**Impact:** Cannot check git state from OpenCode

---

## Unification Architecture Options

### Option A: Add All MCP Tools to OpenCode Routes (SIMPLE ASYNC)
**Approach:** Duplicate MCP tool logic into OpenCode routes.py

**Pros:**
- Simple implementation
- Single file modification
- Direct REST calls for most tools
- Internal tools can be imported directly
- 2-3 hours estimate

**Cons:**
- Code duplication (18 duplicate handlers)
- Maintenance nightmare (bugs must be fixed in 2 places)
- Hard to keep in sync
- Violates DRY principle

**Code Debt:** HIGH

---

### Option B: Create Shared Tool Handlers Module (ROBUST DRY)
**Approach:** Extract tool logic into `src/bridge/shared_tools.py`, both bridges import from it

**Structure:**
```
src/bridge/
├── shared_tools.py          # Tool implementations (shared)
├── mcp/
│   └── vetka_mcp_bridge.py  # MCP wrapper (imports from shared)
└── opencode/
    └── routes.py            # FastAPI routes (imports from shared)
```

**Pros:**
- Zero duplication
- Single source of truth
- Easier maintenance
- Clear separation of concerns
- 4-5 hours estimate

**Cons:**
- Refactoring required
- Slight latency from imports
- More initial setup time

**Code Debt:** LOW - Future-proof

---

### Option C: OpenCode Calls MCP Bridge (INTEGRATION LAYER)
**Approach:** OpenCode routes act as HTTP clients to MCP via local service

**Pros:**
- Zero duplication
- No refactoring needed
- Automatic consistency
- 1-2 hours estimate

**Cons:**
- Performance overhead (HTTP round-trip)
- MCP server must run alongside VETKA
- Adds network dependency
- Single point of failure

**Code Debt:** MEDIUM

---

### Recommendation: **Option B (Shared Tool Handlers)**

**Justification:**
1. **Scalability:** Best long-term maintenance
2. **Performance:** No HTTP overhead vs Option C
3. **Consistency:** Single source of truth
4. **Extensibility:** Easy to add new tools
5. **Testing:** Can test handlers once, reuse in both bridges

**Timeline:** Phase 95.3 → Phase 95.5 (3-4 weeks)

---

## Implementation Markers

### Phase 95.3: Refactoring Foundation

#### [UNIFY-001] Create shared_tools.py base module
- **Action:** CREATE new file
- **Target:** `/src/bridge/shared_tools.py`
- **Purpose:** Container for all shared tool logic
- **Est. Size:** ~100 lines (base classes)
- **Priority:** CRITICAL

**Pseudo-code:**
```python
# src/bridge/shared_tools.py

from abc import ABC, abstractmethod
from typing import Any, Dict
import httpx

class VETKATool(ABC):
    """Base class for all VETKA tools"""

    def __init__(self, client: httpx.AsyncClient = None):
        self.client = client or httpx.AsyncClient(base_url="http://localhost:5001")

    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pass

class ReadTool(VETKATool):
    """Base for read-only tools"""
    pass

class WriteTool(VETKATool):
    """Base for write tools"""
    pass

class ExecutionTool(VETKATool):
    """Base for execution tools"""
    pass
```

---

#### [UNIFY-002] Extract vetka_search_semantic handler
- **Action:** EXTRACT from MCP
- **Source:** `vetka_mcp_bridge.py:611-619`
- **Target:** `src/bridge/shared_tools.py`
- **New Class:** `SemanticSearchTool`
- **Est. Lines:** ~30
- **Priority:** HIGH

**Source to Extract:**
```python
if name == "vetka_search_semantic":
    query = arguments.get("query", "")
    limit = arguments.get("limit", 10)
    response = await http_client.get(
        "/api/search/semantic",
        params={"q": query, "limit": limit}
    )
```

---

#### [UNIFY-003] Extract vetka_read_file handler
- **Action:** EXTRACT from MCP
- **Source:** `vetka_mcp_bridge.py:621-628`
- **Target:** `src/bridge/shared_tools.py`
- **New Class:** `ReadFileTool`
- **Est. Lines:** ~20
- **Priority:** HIGH

---

#### [UNIFY-004] Extract vetka_get_tree handler
- **Action:** EXTRACT from MCP
- **Source:** `vetka_mcp_bridge.py:630-664`
- **Target:** `src/bridge/shared_tools.py`
- **New Class:** `TreeStructureTool`
- **Est. Lines:** ~50
- **Priority:** HIGH

---

#### [UNIFY-005] Extract vetka_health handler
- **Action:** EXTRACT from MCP
- **Source:** `vetka_mcp_bridge.py:666-668`
- **Target:** `src/bridge/shared_tools.py`
- **New Class:** `HealthCheckTool`
- **Est. Lines:** ~15
- **Priority:** MEDIUM

---

#### [UNIFY-006] Extract vetka_list_files handler
- **Action:** EXTRACT from MCP
- **Source:** `vetka_mcp_bridge.py:670-701`
- **Target:** `src/bridge/shared_tools.py`
- **New Class:** `ListFilesTool`
- **Est. Lines:** ~40
- **Priority:** MEDIUM

---

#### [UNIFY-007] Extract vetka_search_files handler
- **Action:** EXTRACT from MCP
- **Source:** `vetka_mcp_bridge.py:703-714`
- **Target:** `src/bridge/shared_tools.py`
- **New Class:** `SearchFilesTool`
- **Est. Lines:** ~25
- **Priority:** MEDIUM

---

#### [UNIFY-008] Extract vetka_get_metrics handler
- **Action:** EXTRACT from MCP
- **Source:** `vetka_mcp_bridge.py:716-737`
- **Target:** `src/bridge/shared_tools.py`
- **New Class:** `MetricsTool`
- **Est. Lines:** ~30
- **Priority:** LOW

---

#### [UNIFY-009] Extract vetka_get_knowledge_graph handler
- **Action:** EXTRACT from MCP
- **Source:** `vetka_mcp_bridge.py:739-765`
- **Target:** `src/bridge/shared_tools.py`
- **New Class:** `KnowledgeGraphTool`
- **Est. Lines:** ~35
- **Priority:** LOW

---

#### [UNIFY-010] Extract vetka_read_group_messages handler
- **Action:** EXTRACT from MCP
- **Source:** `vetka_mcp_bridge.py:837-845`
- **Target:** `src/bridge/shared_tools.py`
- **New Class:** `GroupMessagesTool`
- **Est. Lines:** ~15
- **Priority:** MEDIUM

---

### Phase 95.4: Write Tools Extraction

#### [UNIFY-011] Extract vetka_edit_file handler
- **Action:** EXTRACT from MCP
- **Source:** `vetka_mcp_bridge.py:771-782`
- **Target:** `src/bridge/shared_tools.py`
- **New Class:** `EditFileTool`
- **Logic:** Import from `src/mcp/tools/edit_file_tool.py`
- **Est. Lines:** ~20
- **Priority:** HIGH

---

#### [UNIFY-012] Extract vetka_git_commit handler
- **Action:** EXTRACT from MCP
- **Source:** `vetka_mcp_bridge.py:784-795`
- **Target:** `src/bridge/shared_tools.py`
- **New Class:** `GitCommitTool`
- **Logic:** Import from `src/mcp/tools/git_tool.py`
- **Est. Lines:** ~20
- **Priority:** HIGH

---

#### [UNIFY-013] Extract vetka_git_status handler
- **Action:** EXTRACT from MCP
- **Source:** `vetka_mcp_bridge.py:797-802`
- **Target:** `src/bridge/shared_tools.py`
- **New Class:** `GitStatusTool`
- **Logic:** Import from `src/mcp/tools/git_tool.py`
- **Est. Lines:** ~15
- **Priority:** HIGH

---

#### [UNIFY-014] Extract vetka_run_tests handler
- **Action:** EXTRACT from MCP
- **Source:** `vetka_mcp_bridge.py:804-815`
- **Target:** `src/bridge/shared_tools.py`
- **New Class:** `RunTestsTool`
- **Logic:** Import from `src/mcp/tools/run_tests_tool.py`
- **Est. Lines:** ~20
- **Priority:** MEDIUM

---

#### [UNIFY-015] Extract vetka_camera_focus handler
- **Action:** EXTRACT from MCP
- **Source:** `vetka_mcp_bridge.py:817-822`
- **Target:** `src/bridge/shared_tools.py`
- **New Class:** `CameraFocusTool`
- **Logic:** Import from `src/mcp/tools/camera_tool.py`
- **Est. Lines:** ~15
- **Priority:** LOW

---

#### [UNIFY-016] Extract vetka_call_model handler
- **Action:** EXTRACT from MCP
- **Source:** `vetka_mcp_bridge.py:824-835`
- **Target:** `src/bridge/shared_tools.py`
- **New Class:** `CallModelTool`
- **Logic:** Import from `src/mcp/tools/llm_call_tool.py`
- **Est. Lines:** ~20
- **Priority:** MEDIUM

---

### Phase 95.5: Memory Tools Extraction

#### [UNIFY-017] Extract vetka_get_conversation_context handler
- **Action:** EXTRACT from MCP
- **Source:** `vetka_mcp_bridge.py:851-899`
- **Target:** `src/bridge/shared_tools.py`
- **New Class:** `ConversationContextTool`
- **Logic:** REST + ELISION compression
- **Est. Lines:** ~60
- **Priority:** MEDIUM

---

#### [UNIFY-018] Extract vetka_get_user_preferences handler
- **Action:** EXTRACT from MCP
- **Source:** `vetka_mcp_bridge.py:901-930`
- **Target:** `src/bridge/shared_tools.py`
- **New Class:** `UserPreferencesTool`
- **Logic:** Import from `src/memory/engram_user_memory.py`
- **Est. Lines:** ~40
- **Priority:** MEDIUM

---

#### [UNIFY-019] Extract vetka_get_memory_summary handler
- **Action:** EXTRACT from MCP
- **Source:** `vetka_mcp_bridge.py:932-964`
- **Target:** `src/bridge/shared_tools.py`
- **New Class:** `MemorySummaryTool`
- **Logic:** Import from `src/memory/compression.py`
- **Est. Lines:** ~45
- **Priority:** LOW

---

### Phase 95.6: Bridge Integration

#### [UNIFY-020] Refactor MCP bridge to use shared_tools
- **Action:** UPDATE
- **Target:** `vetka_mcp_bridge.py`
- **Change:** Replace tool implementations with imports from shared_tools
- **Lines Changed:** ~150 (simplification)
- **Priority:** HIGH

**Pattern:**
```python
# OLD:
elif name == "vetka_search_semantic":
    query = arguments.get("query", "")
    response = await http_client.get("/api/search/semantic", ...)
    # ... process response ...

# NEW:
from src.bridge.shared_tools import SemanticSearchTool
elif name == "vetka_search_semantic":
    tool = SemanticSearchTool(http_client)
    result = await tool.execute(arguments)
    return format_result(name, result)
```

---

#### [UNIFY-021] Add all 18 tools to OpenCode routes
- **Action:** UPDATE
- **Target:** `opencode_bridge/routes.py`
- **Change:** Add 18 new endpoints using shared_tools
- **Est. New Lines:** ~200 (compact with shared_tools)
- **Priority:** HIGH

**New Endpoints:**
```python
@router.get("/search/semantic")
async def search_semantic(q: str, limit: int = 10):
    tool = SemanticSearchTool()
    return await tool.execute({"query": q, "limit": limit})

@router.post("/files/read")
async def read_file(file_path: str):
    tool = ReadFileTool()
    return await tool.execute({"file_path": file_path})

# ... 16 more endpoints
```

---

#### [UNIFY-022] Create OpenCode bridge compatibility layer
- **Action:** CREATE
- **Target:** `src/opencode_bridge/compatibility.py`
- **Purpose:** Format results for OpenCode vs MCP
- **Est. Lines:** ~50
- **Priority:** MEDIUM

---

#### [UNIFY-023] Update MCP bridge documentation
- **Action:** UPDATE
- **Target:** `vetka_mcp_bridge.py` (docstring)
- **Change:** Document shared_tools architecture
- **Priority:** LOW

---

#### [UNIFY-024] Update OpenCode bridge documentation
- **Action:** UPDATE
- **Target:** `opencode_bridge/routes.py` (docstring + new comments)
- **Change:** Document all 18 new endpoints
- **Priority:** MEDIUM

---

## Priority Implementation Order

### BATCH 1: Critical Read Tools (2-3 hours)
1. [UNIFY-001] Create shared_tools.py
2. [UNIFY-002] Extract vetka_search_semantic
3. [UNIFY-003] Extract vetka_read_file
4. [UNIFY-004] Extract vetka_get_tree
5. [UNIFY-005] Extract vetka_health

**Result:** OpenCode can browse code and search

---

### BATCH 2: Critical Write Tools (2-3 hours)
6. [UNIFY-011] Extract vetka_edit_file
7. [UNIFY-012] Extract vetka_git_commit
8. [UNIFY-013] Extract vetka_git_status

**Result:** OpenCode can modify files and commit

---

### BATCH 3: Bridge Integration (1-2 hours)
9. [UNIFY-020] Refactor MCP bridge
10. [UNIFY-021] Add all tools to OpenCode routes
11. [UNIFY-022] Create compatibility layer

**Result:** Unified architecture, 18 tools available in OpenCode

---

### BATCH 4: Medium Priority Tools (1-2 hours)
12. [UNIFY-006] Extract vetka_list_files
13. [UNIFY-007] Extract vetka_search_files
14. [UNIFY-010] Extract vetka_read_group_messages
15. [UNIFY-016] Extract vetka_call_model

**Result:** Full metadata + execution capability

---

### BATCH 5: Memory & Low Priority (1-2 hours)
16. [UNIFY-017] Extract vetka_get_conversation_context
17. [UNIFY-018] Extract vetka_get_user_preferences
18. [UNIFY-019] Extract vetka_get_memory_summary
19. [UNIFY-008] Extract vetka_get_metrics
20. [UNIFY-009] Extract vetka_get_knowledge_graph
21. [UNIFY-014] Extract vetka_run_tests
22. [UNIFY-015] Extract vetka_camera_focus

**Result:** Full feature parity

---

## Markers Summary Table

| Marker | Phase | Action | Source Location | Target | Type | Priority | Est. Lines | Status |
|--------|-------|--------|-----------------|--------|------|----------|-----------|--------|
| UNIFY-001 | 95.3 | CREATE | N/A | `src/bridge/shared_tools.py` | BASE | CRITICAL | 100 | PENDING |
| UNIFY-002 | 95.3 | EXTRACT | `mcp:611-619` | `shared_tools.py` | CLASS | HIGH | 30 | PENDING |
| UNIFY-003 | 95.3 | EXTRACT | `mcp:621-628` | `shared_tools.py` | CLASS | HIGH | 20 | PENDING |
| UNIFY-004 | 95.3 | EXTRACT | `mcp:630-664` | `shared_tools.py` | CLASS | HIGH | 50 | PENDING |
| UNIFY-005 | 95.3 | EXTRACT | `mcp:666-668` | `shared_tools.py` | CLASS | MEDIUM | 15 | PENDING |
| UNIFY-006 | 95.4 | EXTRACT | `mcp:670-701` | `shared_tools.py` | CLASS | MEDIUM | 40 | PENDING |
| UNIFY-007 | 95.4 | EXTRACT | `mcp:703-714` | `shared_tools.py` | CLASS | MEDIUM | 25 | PENDING |
| UNIFY-008 | 95.4 | EXTRACT | `mcp:716-737` | `shared_tools.py` | CLASS | LOW | 30 | PENDING |
| UNIFY-009 | 95.4 | EXTRACT | `mcp:739-765` | `shared_tools.py` | CLASS | LOW | 35 | PENDING |
| UNIFY-010 | 95.4 | EXTRACT | `mcp:837-845` | `shared_tools.py` | CLASS | MEDIUM | 15 | PENDING |
| UNIFY-011 | 95.4 | EXTRACT | `mcp:771-782` | `shared_tools.py` | CLASS | HIGH | 20 | PENDING |
| UNIFY-012 | 95.4 | EXTRACT | `mcp:784-795` | `shared_tools.py` | CLASS | HIGH | 20 | PENDING |
| UNIFY-013 | 95.4 | EXTRACT | `mcp:797-802` | `shared_tools.py` | CLASS | HIGH | 15 | PENDING |
| UNIFY-014 | 95.4 | EXTRACT | `mcp:804-815` | `shared_tools.py` | CLASS | MEDIUM | 20 | PENDING |
| UNIFY-015 | 95.4 | EXTRACT | `mcp:817-822` | `shared_tools.py` | CLASS | LOW | 15 | PENDING |
| UNIFY-016 | 95.5 | EXTRACT | `mcp:824-835` | `shared_tools.py` | CLASS | MEDIUM | 20 | PENDING |
| UNIFY-017 | 95.5 | EXTRACT | `mcp:851-899` | `shared_tools.py` | CLASS | MEDIUM | 60 | PENDING |
| UNIFY-018 | 95.5 | EXTRACT | `mcp:901-930` | `shared_tools.py` | CLASS | MEDIUM | 40 | PENDING |
| UNIFY-019 | 95.5 | EXTRACT | `mcp:932-964` | `shared_tools.py` | CLASS | LOW | 45 | PENDING |
| UNIFY-020 | 95.6 | UPDATE | `mcp:entire` | `vetka_mcp_bridge.py` | REFACTOR | HIGH | -150 | PENDING |
| UNIFY-021 | 95.6 | UPDATE | `shared_tools:all` | `opencode_bridge/routes.py` | EXTEND | HIGH | +200 | PENDING |
| UNIFY-022 | 95.6 | CREATE | N/A | `opencode_bridge/compatibility.py` | LAYER | MEDIUM | 50 | PENDING |
| UNIFY-023 | 95.6 | UPDATE | N/A | `vetka_mcp_bridge.py` (docs) | DOCS | LOW | 20 | PENDING |
| UNIFY-024 | 95.6 | UPDATE | N/A | `opencode_bridge/routes.py` (docs) | DOCS | MEDIUM | 30 | PENDING |

---

## Architecture Diagram

```
UNIFIED BRIDGE ARCHITECTURE (Post-Phase 95.6)

┌─────────────────────────────────────────────────────────────────┐
│                    VETKA UNIFIED BRIDGE                         │
└─────────────────────────────────────────────────────────────────┘

                        ┌──────────────────────┐
                        │  shared_tools.py     │
                        │  (18 Tool Classes)   │
                        │  - ReadTools (8)     │
                        │  - WriteTools (4)    │
                        │  - ExecTools (3)     │
                        │  - MemoryTools (3)   │
                        └──────────────────────┘
                                 ▲
                    ┌────────────┴────────────┐
                    │                        │
                    ▼                        ▼
        ┌──────────────────────┐  ┌──────────────────────┐
        │  MCP Bridge          │  │  OpenCode Bridge     │
        │  (vetka_mcp_bridge)  │  │  (opencode/routes)   │
        │  - Tool dispatch     │  │  - HTTP routes       │
        │  - Result formatting │  │  - Async handlers    │
        │  - Error logging     │  │  - Compatibility     │
        └──────────────────────┘  └──────────────────────┘
                    │                        │
                    ▼                        ▼
        ┌──────────────────────┐  ┌──────────────────────┐
        │  Claude Desktop      │  │  VS Code / IDE       │
        │  Claude Code         │  │  (OpenCode Bridge)   │
        └──────────────────────┘  └──────────────────────┘
```

---

## Testing Strategy

### Phase 95.3-95.4: Unit Testing
```bash
# Test each tool extraction
pytest tests/bridge/test_shared_tools.py -k "test_semantic_search" -v
pytest tests/bridge/test_shared_tools.py -k "test_read_file" -v
# etc.
```

### Phase 95.6: Integration Testing
```bash
# Test MCP bridge with new shared_tools
pytest tests/mcp/test_integration.py -v

# Test OpenCode bridge with new endpoints
pytest tests/opencode/test_endpoints.py -v

# Test both produce same results
pytest tests/bridge/test_unified.py -v
```

### Regression Testing
- MCP bridge must still pass all existing tests
- OpenCode bridge must return compatible responses
- No breaking changes to existing endpoints

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Refactoring breaks MCP bridge | LOW | CRITICAL | Comprehensive testing before refactor |
| Performance regression in shared_tools | LOW | MEDIUM | Benchmark before/after |
| OpenCode routes not compatible | MEDIUM | MEDIUM | Test response format compatibility |
| Missing error handling in extraction | MEDIUM | MEDIUM | Thorough code review of each extraction |
| Async/await issues in OpenCode | MEDIUM | HIGH | Test with real OpenCode client |

---

## Success Criteria

- [ ] All 18 MCP tools available in OpenCode via HTTP endpoints
- [ ] Identical functionality in both bridges (verified by integration tests)
- [ ] No code duplication between bridges
- [ ] Response format compatibility verified
- [ ] Performance comparable or better than current MCP bridge
- [ ] Documentation updated for both bridges
- [ ] Zero regressions in existing functionality

---

## Next Steps

1. **Phase 95.3:** Execute BATCH 1 ([UNIFY-001] through [UNIFY-005])
2. **Review & Test:** Verify shared_tools.py architecture
3. **Phase 95.4:** Execute BATCH 2 ([UNIFY-006] through [UNIFY-013])
4. **Phase 95.6:** Execute BATCH 3 ([UNIFY-020] through [UNIFY-022])
5. **Integration Testing:** Run full test suite
6. **Documentation:** Update user guides and API docs
7. **Deployment:** Roll out unified bridge to production

---

## Appendix: Tool Implementation Reference

### REST-based Tools (Ready for simple extraction)
- `vetka_search_semantic` → `/api/search/semantic`
- `vetka_read_file` → `/api/files/read`
- `vetka_get_tree` → `/api/tree/data`
- `vetka_health` → `/api/health`
- `vetka_get_metrics` → `/api/metrics/*`
- `vetka_get_knowledge_graph` → `/api/tree/knowledge-graph`
- `vetka_read_group_messages` → `/api/groups/{id}/messages`

### Internal Tool-based (Requires import pattern)
- `vetka_edit_file` → Import `src.mcp.tools.edit_file_tool`
- `vetka_git_commit` → Import `src.mcp.tools.git_tool`
- `vetka_git_status` → Import `src.mcp.tools.git_tool`
- `vetka_run_tests` → Import `src.mcp.tools.run_tests_tool`
- `vetka_camera_focus` → Import `src.mcp.tools.camera_tool`
- `vetka_call_model` → Import `src.mcp.tools.llm_call_tool`

### Memory/Compression-based (Complex extraction)
- `vetka_get_conversation_context` → REST + `src.memory.elision`
- `vetka_get_user_preferences` → Import `src.memory.engram_user_memory`
- `vetka_get_memory_summary` → Import `src.memory.compression`

---

**Document End**
**Version:** 1.0
**Status:** READY FOR PHASE 95.3 IMPLEMENTATION
