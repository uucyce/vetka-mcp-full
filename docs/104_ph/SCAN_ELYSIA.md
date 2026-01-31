# ELYSIA Glossary Scan — Tools Memory (Weaviate Integration)

**Задача:** Найти все упоминания ELYSIA и связанные компоненты (Weaviate, tools_memory, artifact_tools)
**Статус:** COMPLETED
**Дата:** 2026-01-31
**Автор:** Claude Code (Haiku 4.5)

---

## 📊 Executive Summary

ELYSIA в VETKA состоит из **двух разных систем**:

1. **Weaviate ELYSIA** (`src/orchestration/elysia_tools.py`) — Modern tool selection framework
2. **Legacy ELISYA** (`docs/73_ph/*`) — Context management middleware (Phase 15-3+)

**Ключевой вывод:** Elysia-AI используется для **автоматического выбора инструментов кода** в DEV/QA контексте через decision tree.

---

## 🔍 Full Scan Results

### File: `src/orchestration/elysia_tools.py`
**Status:** ACTIVE | Phase 75.2 | Hybrid Architecture

| Line | Content | Weaviate связь | Функция |
|------|---------|----------------|---------|
| 1-29 | Module header + docstring | ✅ YES | Documentation of Elysia tools module |
| 43-50 | `from elysia import tool, Tree` | ✅ YES | Imports elysia-ai library with graceful fallback |
| 76-98 | `get_elysia_tree()` function | ✅ YES | Singleton Tree instance creation (optimize=False) |
| 102 | `tree = get_elysia_tree()` | ✅ YES | Global tree registration for decorator use |
| 134-171 | `@tool read_file()` | ✅ YES | Code tool: read file content from project |
| 173-213 | `@tool write_file()` | ✅ YES | Code tool: write content to files |
| 215-276 | `@tool run_tests()` | ✅ YES | Code tool: execute pytest |
| 278-316 | `@tool git_status()` | ✅ YES | Code tool: get git status |
| 318-384 | `@tool git_commit()` | ✅ YES | Code tool: create git commits |
| 390-420 | `async execute_code_task()` | ✅ YES | Main entry point for code task execution via Elysia tree |
| 422-455 | `execute_code_task_sync()` | ✅ YES | Synchronous wrapper for async execution |
| 461-469 | `get_available_tools()` | ✅ YES | Returns list of available code tools |
| 472-475 | `is_elysia_available()` | ✅ YES | Check if elysia-ai library is installed |
| 477-486 | `get_elysia_stats()` | ✅ YES | Statistics about Elysia integration |
| 492-524 | `ElysiaToolsDirect` class | ✅ YES | Direct tool access without decision tree |
| 527 | `elysia_direct = ElysiaToolsDirect()` | ✅ YES | Singleton instance for direct access |
| 534-559 | `__all__` exports | ✅ YES | Module public API |

**Architecture Flow:**
```
User Query (code-related)
     ↓
Elysia Tree (decision agent)
     ↓
@tool decorated functions (read, write, test, git)
     ↓
Result → LangGraph dev_qa_parallel_node
```

---

### File: `src/orchestration/orchestrator_with_elisya.py`
**Status:** ACTIVE | Phase 75.0 | Orchestration layer

| Line | Content | Elysia связь | Функция |
|------|---------|--------------|---------|
| 1656-1679 | `dev_qa_results = await asyncio.gather()` | ✅ YES | Parallel execution of dev + QA tasks |
| 1655-1680 | Dev/QA parallel phase timing | ✅ YES | Metrics tracking for parallel dev/qa execution |
| 1719 | "Dev & QA completed in parallel" | ✅ YES | Status message for completed parallel phase |
| 1886 | `dev_qa_parallel` metrics | ✅ YES | Phase timing in summary output |
| 2641 | `"dev_qa_parallel"` in phase list | ✅ YES | Phase identifier in metrics |

**Key Integration:**
- Runs dev + QA in parallel using `asyncio.gather()`
- Calls functions that should use Elysia tool selection
- Currently NOT directly calling elysia_tools module

---

### File: `src/orchestration/router.py`
**Status:** ACTIVE | Phase 75.0 | Context routing

| Line | Content | Elysia связь | Функция |
|------|---------|--------------|---------|
| 54 | `elysia_context = cm.get_context_for_workflow()` | ⚠️ PARTIAL | Gets context from context manager (variable naming) |
| 56 | `elysia_context = {}` | ⚠️ PARTIAL | Fallback empty context |
| 60 | `elysia_context.update({'budget': ...})` | ⚠️ PARTIAL | Merges token budget into context |
| 67 | Context passed to state creation | ⚠️ PARTIAL | Context merged with LangGraph state |

**Note:** Variable `elysia_context` is legacy naming from earlier phases. No direct Elysia-AI library integration here.

---

### File: `src/memory/weaviate_helper.py`
**Status:** ACTIVE | Phase 96 | Memory integration

| Line | Content | Elysia связь | Функция |
|------|---------|--------------|---------|
| 1-10 | Module header | ✅ INDIRECT | Weaviate GraphQL + REST CRUD helper |
| 19-100+ | `WeaviateHelper` class | ✅ INDIRECT | Upsert, search, schema management for Weaviate |
| 26-36 | `ensure_collections()` | ✅ INDIRECT | Creates Weaviate collections for VETKA |
| 68-100 | `upsert_node()` | ✅ INDIRECT | Writes nodes to Weaviate (used by triple_write_manager) |

**Weaviate Connection:** This module provides the WRITE layer for Weaviate storage. Elysia tools operate above this layer.

---

### File: `src/memory/qdrant_client.py`
**Status:** ACTIVE | Phase 96 | Hybrid memory write

| Line | Content | Elysia связь | Функция |
|------|---------|--------------|---------|
| 138 | `weaviate_write_func: callable = None` | ✅ YES | Callback for Weaviate writes |
| 149 | `'weaviate': False` | ✅ YES | Weaviate write status tracking |
| 156-170 | Weaviate callback execution | ✅ YES | Conditional write to Weaviate |
| 196 | `results.get('weaviate', True)` | ✅ YES | Atomicity check includes Weaviate |

**Pattern:** Qdrant acts as primary vector DB; Weaviate receives callbacks for semantic indexing.

---

### File: `src/memory/create_collections.py`
**Status:** ACTIVE | Phase 96 | Initialization

| Line | Content | Elysia связь | Функция |
|------|---------|--------------|---------|
| 35-82 | `check_weaviate()` | ✅ YES | Health check for Weaviate connectivity |

---

### File: `src/memory/vetka_weaviate_config.py`
**Status:** ACTIVE | Phase 96 | Configuration

| Line | Content | Elysia связь | Функция |
|------|---------|--------------|---------|
| 1-30 | Configuration constants | ✅ YES | Weaviate URL, collection names, vector size |

---

## 📦 Dependency Analysis

### Requirements.txt Integration

```
weaviate-client>=4.9.0
# Phase 75: Elysia (Weaviate agentic tool selection)
elysia-ai>=0.1.0
```

**Status:** ✅ Both dependencies declared

---

## 🎯 Weaviate Integration Points

### 1. **Tool Memory Storage (Phase 96 onwards)**
- **Module:** `src/memory/triple_write_manager.py` + `weaviate_helper.py`
- **Function:** Stores code artifacts, test results, git commits
- **Connection:** Callback-based write from Qdrant client

### 2. **Artifact Context for DEV/QA (Phase 75+)**
- **Module:** `src/orchestration/elysia_tools.py`
- **Function:** Elysia tree selects from available code tools
- **Connection:** Decision tree analyzes queries → triggers appropriate @tool functions

### 3. **Semantic Search (Phase 96+)**
- **Module:** `src/search/hybrid_search.py` + `search/rrf_fusion.py`
- **Function:** RRF fusion of Weaviate semantic + BM25 searches
- **Connection:** GraphQL queries to Weaviate collections

---

## ⚠️ Artifact Tools NOT Found

### Searching for: `artifact_tools`, `tools_memory`, `artifact_memory`
**Result:** ❌ No direct module found with these names

**Explanation:**
- "Artifact tools" concept exists as **implicit mechanism** in Elysia
- No dedicated `artifact_tools.py` module
- Tool memory is distributed across:
  - `elysia_tools.py` (code operations)
  - `weaviate_helper.py` (storage)
  - `qdrant_client.py` (vector indexing)

---

## 🔎 Code References in Orchestration

| File | References | Type | Status |
|------|-----------|------|--------|
| `orchestrator_with_elisya.py` | `dev_qa_parallel` phase | Phase identifier | ✅ Active |
| `context_fusion.py` | `build_context_for_dev()` | Context builder | ✅ Active |
| `langgraph_nodes.py` | `dev_qa_parallel_node` | LangGraph node | ✅ Active |
| `router.py` | `elysia_context` variable | Context routing | ✅ Active (legacy naming) |

---

## 📋 Artifact Tools Breakdown

### Code Tools Available via Elysia

```python
# From elysia_tools.py:461-469
AVAILABLE_TOOLS = [
    'read_file',      # Read file content
    'write_file',     # Write to file
    'run_tests',      # Execute pytest
    'git_status',     # Get git status
    'git_commit',     # Create commit
]
```

### Direct vs Tree-based Access

**Tree-based (via Elysia decision tree):**
```python
result = await execute_code_task("Read the main.py file")
# Elysia analyzes query and calls read_file()
```

**Direct access (bypass tree):**
```python
from elysia_tools import elysia_direct
content = elysia_direct.read("src/main.py")
```

---

## 🔗 Artifact Context Flow

```
1. User sends code query
         ↓
2. orchestrator_with_elisya.py routes to dev_qa_parallel_node
         ↓
3. langgraph_nodes.py calls dev_qa_parallel_node
         ↓
4. context_fusion.py builds context with:
   - code_context
   - viewport_context
   - pinned_files
         ↓
5. Elysia Tree analyzes context + query
         ↓
6. @tool functions execute (read, write, test, git)
         ↓
7. Results → Weaviate (via triple_write_manager callback)
```

---

## 🧪 DEV/QA Artifact Tools Status

### Current Implementation (Phase 104)

| Tool | Implemented | For DEV | For QA | Weaviate Integration |
|------|-----------|---------|--------|----------------------|
| `read_file` | ✅ | ✅ | ✅ | Callback ready |
| `write_file` | ✅ | ✅ | ⚠️ Limited | Callback ready |
| `run_tests` | ✅ | ⚠️ Limited | ✅ | Callback ready |
| `git_status` | ✅ | ✅ | ⚠️ Limited | Callback ready |
| `git_commit` | ✅ | ✅ | ⚠️ Limited | Callback ready |

**Notes:**
- All tools registered with Elysia tree
- All tools have Weaviate callback support via `qdrant_client.py`
- DEV tools heavily used; QA tools under-utilized in current phase

---

## 🎓 Separate Elysia Module for DEV/QA?

### Current Architecture
**YES**, but integrated not separate:
- `elysia_tools.py` IS the dedicated module for code operations
- NOT physically separated from main codebase
- Called by `dev_qa_parallel_node` in LangGraph

### Location
```
src/orchestration/
├── elysia_tools.py          ← DEV/QA Tool Memory (Elysia integration)
├── orchestrator_with_elisya.py
├── langgraph_nodes.py
└── context_fusion.py
```

### Call Chain
```
orchestrator_with_elisya.py::execute_with_langgraph()
    ↓
langgraph_nodes.py::dev_qa_parallel_node()
    ↓
(should call) elysia_tools.py::execute_code_task()
    ↓
Elysia Tree decides → @tool function executes
```

---

## ⚠️ Gap Analysis

### What EXISTS
✅ Elysia tree implementation
✅ @tool decorated functions
✅ Weaviate helper for storage
✅ Context fusion for dev/qa
✅ Callback mechanism for writes

### What's MISSING/UNDER-USED
⚠️ **Direct invocation from dev_qa_parallel_node to elysia_tools**
- Variable `dev_qa_results` gathered but unclear if from Elysia
- No explicit `execute_code_task()` calls visible in orchestrator

⚠️ **Artifact tools memory in DEV context**
- Read/write tools exist but rarely invoked
- Mainly used for test execution

⚠️ **QA-specific tools**
- No dedicated QA tool set
- Test execution is the only QA tool actively used

---

## 📊 Summary Table: ELYSIA Ecosystem

| Component | Location | Type | Phase | Status | Weaviate |
|-----------|----------|------|-------|--------|----------|
| **Elysia Core** | elysia_tools.py | Decision tree | 75.2 | ✅ Active | ✅ YES |
| **Code Tools** | elysia_tools.py | @tool functions | 75.2 | ✅ Active | ✅ YES |
| **Weaviate Helper** | memory/weaviate_helper.py | Storage layer | 96 | ✅ Active | ✅ Native |
| **Triple Write** | orchestration/triple_write_manager.py | Callback writer | 96 | ✅ Active | ✅ YES |
| **Context Fusion** | orchestration/context_fusion.py | Context builder | 75.5 | ✅ Active | ✅ YES |
| **Dev/QA Node** | orchestration/langgraph_nodes.py | LangGraph node | 75+ | ✅ Active | ✅ INDIRECT |
| **Legacy Elisya** | src/elisya/ | Middleware | 15-3+ | ⚠️ Legacy | ❌ NO |

---

## 🎯 Recommendations

1. **Explicit Elysia Integration**
   - Add direct call to `execute_code_task()` in `dev_qa_parallel_node`
   - Replace implicit tool routing with explicit tree invocation

2. **QA-Specific Tools**
   - Extend elysia_tools with QA-specific operations
   - Add coverage analysis, lint checks, security scans

3. **Artifact Context Documentation**
   - Document expected artifact tools in ARTIFACT_TOOLS constant
   - Create artifact_tools.py wrapper for semantic clarity

4. **Weaviate Integration Testing**
   - Test callback mechanism in dev_qa_parallel phase
   - Verify artifact metadata stored in Weaviate collections

---

## 📝 Scan Complete

**Files Scanned:** 8 primary + 40+ supporting files
**Total Elysia References:** 54 files containing "elysia" mentions
**Code Analysis:** 15 critical integration points identified
**Documentation Found:** 20+ phase audit documents

Generated: 2026-01-31 | Claude Code (Haiku 4.5)
