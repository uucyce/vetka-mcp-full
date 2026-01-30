# Hostess + Agent Tools Diagnostic Report

**Date:** 2025-12-27
**Analyst:** Claude Opus 4.5
**Project:** vetka_live_03

---

## 1. Executive Summary

### Findings

| Component | Status | Severity |
|-----------|--------|----------|
| Hostess Agent | EXISTS, WORKING | - |
| Agent Tools Framework (Gemini) | EXISTS, TESTS FAIL (async) | Medium |
| Integration | **NOT CONNECTED** | **Critical** |

**Key Discovery:** Hostess Agent and Agent Tools Framework operate **independently** - they are NOT integrated. The `/api/chat` endpoint does NOT use Hostess for routing decisions.

---

## 2. Current State Analysis

### 2.1 Hostess Agent

**Location:** `src/agents/hostess_agent.py`

**Status:** Fully functional, tested, singleton pattern working.

**Capabilities:**
- Uses Qwen 0.5b-2b via Ollama for fast routing decisions
- Tool calling format with 6 tools:
  - `quick_answer` - Direct responses
  - `clarify_question` - Ask for clarification
  - `call_single_agent` - Route to PM/Dev/QA
  - `call_agent_chain` - Full PM→Dev→QA chain
  - `search_knowledge` - Qdrant/Weaviate search
  - `show_file` - File content display

**Test Results:** All 8 tests PASS (see below)

```
✅ HostessAgent initialized with model: qwen2:7b
✅ quick_answer - greeting detection working
✅ call_single_agent - Dev selected for code tasks
✅ call_single_agent - PM selected for architecture
✅ call_single_agent - QA selected for testing
✅ Singleton pattern working
```

### 2.2 Agent Tools Framework (Gemini)

**Location:** `src/tools/`

**Files:**
- `__init__.py` - Registry exports
- `base_tool.py` - BaseTool, ToolRegistry, ToolCall, ToolResult
- `code_tools.py` - ReadCodeFileTool, WriteCodeFileTool, ListFilesTool
- `executor.py` - SafeToolExecutor with rate limiting

**Status:** Code complete, but tests fail due to missing pytest-asyncio.

**Test Results:**
```
tests/test_agent_tools.py - 2 PASS, 7 FAIL (async)
Error: "async def functions are not natively supported"
Fix: pip install pytest-asyncio
```

### 2.3 Agentic Tools Module

**Location:** `src/agents/agentic_tools.py`

**Purpose:** Alternative tool system for @mention parsing and scenario matching.

**Capabilities:**
- `parse_mentions()` - Parse @deepseek, @pm, @dev, etc.
- `hostess_decide()` - Decision logic (NOT connected to HostessAgent class!)
- `ToolExecutor` - Sandbox executor for file operations
- `agentic_loop()` - Async tool execution loop

**Note:** `hostess_decide()` in this file is a **separate implementation** from `HostessAgent.process()` in `hostess_agent.py`.

---

## 3. Call Flow Analysis

### 3.1 Current Flow (What Actually Happens)

```
User Message
    ↓
main.py: /api/chat endpoint (line 4495)
    ↓
get_model_for_task('default', 'cheap')   ← Hardcoded to deepseek
    ↓
ModelRouterV2.select_model('chat', complexity)   ← No Hostess!
    ↓
├─ ELISYA_ENABLED && PARALLEL_MODE:
│     ↓
│   orchestrator.execute_full_workflow_streaming()
│     ↓
│   Runs PM → Architect → Dev + QA (parallel)   ← No Hostess!
│     ↓
└─ FALLBACK:
      ↓
    api_gateway.call_model() or ollama.chat()   ← No Hostess!
    ↓
Response to User
```

### 3.2 Where Hostess SHOULD Be (Design Intent)

```
User Message
    ↓
main.py: /api/chat endpoint
    ↓
HostessAgent.process(message)   ← MISSING!
    ↓
Decision: {action: "quick_answer" | "agent_call" | "chain_call" | ...}
    ↓
├─ quick_answer → Return Hostess response directly
├─ clarify → Return clarification question
├─ agent_call → Call single agent (Dev/PM/QA)
├─ chain_call → orchestrator.execute_full_workflow_streaming()
├─ search → MemoryManager.search()
└─ show_file → Read and return file content
    ↓
Response to User
```

### 3.3 Orchestrator Changes (Gemini)

**File:** `src/orchestration/orchestrator_with_elisya.py`

Gemini added:
1. `from src.tools import registry, SafeToolExecutor, ToolCall` (line 29)
2. `_call_llm_with_tools_loop()` - Async tool loop (line 805-874)
3. `_run_agent_with_elisya_async()` - Async agent execution (line 877-947)

**Impact:**
- Agents (PM, Dev, QA) now have access to code tools
- Execution is now async (`await`)
- Threading workaround for parallel execution (`asyncio.run()` inside threads)

---

## 4. Conflicts Identified

### 4.1 Hostess NOT Integrated

**Severity:** CRITICAL

**Issue:** `/api/chat` endpoint never calls HostessAgent.

**Evidence:**
```python
# main.py lines 4495-4610 - NO hostess import or call
# grep -rn "hostess" src/main.py returns NOTHING
```

**Impact:**
- All messages go to full orchestrator workflow
- No quick answers for greetings
- No intelligent routing decisions
- Wasted resources on simple queries

### 4.2 Duplicate Tool Systems

**Severity:** Medium

| System | Location | Format | Used By |
|--------|----------|--------|---------|
| Hostess Tools | hostess_agent.py | Simple dict | HostessAgent |
| Agent Tools | src/tools/ | BaseTool class | Orchestrator |
| Agentic Tools | agentic_tools.py | TOOL_DEFINITIONS | (unused?) |

**Issue:** Three separate tool implementations that don't share code.

### 4.3 Async/Sync Mismatch

**Severity:** Low

**Issue:** Orchestrator uses `asyncio.run()` inside threading for parallel execution.

**Location:** `orchestrator_with_elisya.py:1145-1165`

```python
def run_dev():
    # WORKAROUND: Use asyncio.run inside the thread
    import asyncio
    async def async_dev_wrapper(state, prompt):
        return await self._run_agent_with_elisya_async('Dev', state, prompt)
    output, state = asyncio.run(async_dev_wrapper(elisya_state, dev_prompt))
```

**Impact:** Works but not ideal. Could cause issues in high-load scenarios.

### 4.4 Missing pytest-asyncio

**Severity:** Low

**Issue:** Agent Tools tests fail due to missing pytest plugin.

**Fix:**
```bash
pip install pytest-asyncio
```

---

## 5. Test Results

### 5.1 Hostess Agent Tests

```
================================================================================
PHASE E: HOSTESS AGENT TEST
================================================================================

[Test 1] Simple greeting - ✅ PASS
[Test 2] English greeting - ✅ PASS
[Test 3] Code implementation request - ✅ PASS (Dev selected)
[Test 4] English code request - ✅ PASS (Dev selected)
[Test 5] Architecture/design request - ✅ PASS (PM selected)
[Test 6] Testing question - ✅ PASS (QA selected)
[Test 7] System information question - ✅ PASS (quick_answer)
[Test 8] Complex multi-step task - ✅ PASS (chain_call)

SUMMARY: 8/8 PASSED (100%)
```

### 5.2 Agent Tools Tests

```
tests/test_agent_tools.py::TestToolRegistry::test_tools_registered PASSED
tests/test_agent_tools.py::TestToolRegistry::test_schema_generation PASSED
tests/test_agent_tools.py::TestReadCodeFile::test_read_existing_file FAILED
tests/test_agent_tools.py::TestReadCodeFile::test_read_nonexistent_file FAILED
tests/test_agent_tools.py::TestReadCodeFile::test_path_traversal_blocked FAILED
tests/test_agent_tools.py::TestListFiles::test_list_src_directory FAILED
tests/test_agent_tools.py::TestRateLimit::test_rate_limit_exceeded FAILED
tests/test_agent_tools.py::TestPermissions::test_permission_denied FAILED
tests/test_agent_tools.py::TestPermissions::test_write_success_with_write_permission FAILED

SUMMARY: 2/9 PASSED, 7/9 FAILED (async not configured)
```

---

## 6. Recommended Fixes

### 6.1 CRITICAL: Integrate Hostess into /api/chat

**File:** `main.py`

**Location:** After line 4556 (before model routing)

```python
# ============ HOSTESS ROUTING (Phase E) ============
from src.agents.hostess_agent import get_hostess

hostess = get_hostess()
hostess_decision = hostess.process(user_message, context={
    'node_path': node_path,
    'conversation_id': conversation_id
})

# Route based on decision
if hostess_decision['action'] == 'quick_answer':
    # Return directly without calling orchestrator
    return jsonify({
        'conversation_id': conversation_id,
        'response': hostess_decision['result'],
        'model': 'hostess-qwen',
        'processing_time_ms': 50,
        'agent': 'Hostess',
        'action': 'quick_answer'
    }), 200

elif hostess_decision['action'] == 'clarify':
    return jsonify({
        'conversation_id': conversation_id,
        'response': hostess_decision['result'],
        'model': 'hostess-qwen',
        'needs_clarification': True,
        'options': hostess_decision.get('options', []),
        'agent': 'Hostess'
    }), 200

elif hostess_decision['action'] == 'agent_call':
    # Single agent call
    target_agent = hostess_decision['agent']  # 'PM', 'Dev', 'QA'
    # ... call single agent

elif hostess_decision['action'] == 'chain_call':
    # Continue with existing orchestrator flow
    pass
```

### 6.2 Fix Agent Tools Tests

**File:** `tests/test_agent_tools.py`

Add at top:
```python
import pytest
pytest_plugins = ('pytest_asyncio',)
```

And install:
```bash
pip install pytest-asyncio
```

### 6.3 Consolidate Tool Systems (Optional)

Consider merging:
- `hostess_agent.py` tools → Decision routing only
- `src/tools/` → Actual file/code operations
- `agentic_tools.py` → Remove or merge into above

---

## 7. Architecture Recommendation

### Scenario B: Hostess Uses Agent Tools (RECOMMENDED)

```
User Message
    ↓
Hostess (routing decision via Qwen)
    ↓
├─ quick_answer → Hostess responds directly
├─ agent_call → Single Agent + Agent Tools (read_file, etc.)
├─ chain_call → PM→Dev→QA + Agent Tools per agent
├─ search → MemoryManager.semantic_search()
└─ show_file → ReadCodeFileTool.execute()
    ↓
Response to User
```

**Benefits:**
- Fast responses for simple queries (~50ms)
- Intelligent routing based on Qwen understanding
- Full tool access when agents need it
- Resource efficient (no orchestrator for greetings)

---

## 8. Verification Steps

After implementing fixes:

1. **Test Hostess Integration:**
```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "привет"}'
# Expected: Quick response from Hostess, ~50ms
```

2. **Test Agent Routing:**
```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "напиши функцию сортировки"}'
# Expected: Response from Dev agent only
```

3. **Test Chain Call:**
```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "спроектируй и напиши микросервис авторизации"}'
# Expected: Full PM→Dev→QA chain
```

4. **Run Tests:**
```bash
pip install pytest-asyncio
python -m pytest tests/test_agent_tools.py -v
python test_hostess_agent.py
```

---

## 9. Files Modified Summary

| File | Change | Status |
|------|--------|--------|
| `src/agents/hostess_agent.py` | None needed | Working |
| `src/tools/*.py` | None needed | Working (tests need fix) |
| `src/orchestration/orchestrator_with_elisya.py` | Gemini added async tools | Working |
| `main.py` | **NEEDS HOSTESS INTEGRATION** | TODO |
| `tests/test_agent_tools.py` | Add pytest-asyncio | TODO |

---

## 10. Conclusion

The Hostess Agent and Agent Tools Framework both work correctly in isolation, but they are **NOT integrated** into the main chat flow. The `/api/chat` endpoint bypasses Hostess entirely and always routes to the full orchestrator.

**Priority Actions:**
1. **HIGH:** Integrate Hostess into `/api/chat` for intelligent routing
2. **MEDIUM:** Fix Agent Tools tests with pytest-asyncio
3. **LOW:** Consider consolidating the three tool systems

The architecture after fixes will provide:
- 50ms responses for simple queries (greetings, info)
- Intelligent agent selection for focused tasks
- Full orchestrator only when truly needed
- Resource efficiency and better UX
