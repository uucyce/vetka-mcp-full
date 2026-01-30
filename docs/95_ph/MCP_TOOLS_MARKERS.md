# VETKA MCP Bridge Tools Audit
## Phase 95.2 - Tools Inventory and REST Endpoint Mapping

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py`
**Last Updated:** 2026-01-26
**Total Tools:** 18

---

## Summary

- **Total tools:** 18
- **Categories:**
  - Read-Only Tools (8)
  - Write Tools (3)
  - Development Tools (1)
  - Memory Tools (3)
  - Model Interaction (1)
  - Group Communication (1)
  - System Tools (1)
- **Tool Definitions Location:** Lines 177-585 (@server.list_tools() decorator)
- **Tool Handlers Location:** Lines 592-1008 (@server.call_tool() decorator)
- **REST Base URL:** http://localhost:5001
- **VETKA Phase:** Phase 65.1+

---

## Tools Inventory

### READ-ONLY TOOLS

#### [MCP-TOOL-001] vetka_search_semantic
- **Location:** src/mcp/vetka_mcp_bridge.py:181-202
- **MCP Decorator Line:** 177 (@server.list_tools)
- **Handler Line:** 611-619
- **Status:** ACTIVE
- **Description:** "Semantic search in VETKA knowledge base using Qdrant vector search. Search for concepts, ideas, or topics across all indexed documents."
- **Parameters:**
  - `query` (string, required): Semantic search query (e.g., 'authentication logic', 'API error handling')
  - `limit` (integer, optional, default: 10, max: 50): Max results to return
- **REST Endpoint:** `GET /api/search/semantic`
- **Query Parameters:** `q={query}`, `limit={limit}`
- **Response Format:** JSON with results array containing content, score, metadata
- **Formatter:** format_result() → Lines 1015-1031 (special formatting)

#### [MCP-TOOL-002] vetka_read_file
- **Location:** src/mcp/vetka_mcp_bridge.py:203-216
- **MCP Decorator Line:** 177 (@server.list_tools)
- **Handler Line:** 621-628
- **Status:** ACTIVE
- **Description:** "Read file content from VETKA project. Returns full file content with line numbers."
- **Parameters:**
  - `file_path` (string, required): Path to file relative to project root (e.g., 'src/main.py')
- **REST Endpoint:** `POST /api/files/read`
- **Request Payload:** `{"file_path": "..."}`
- **Response Format:** JSON with content, line numbers, metadata
- **Formatter:** format_result() → Lines 1057-1062 (plain content return)

#### [MCP-TOOL-003] vetka_get_tree
- **Location:** src/mcp/vetka_mcp_bridge.py:217-232
- **MCP Decorator Line:** 177 (@server.list_tools)
- **Handler Line:** 630-664
- **Status:** ACTIVE
- **Description:** "Get VETKA 3D tree structure showing files and folders hierarchy. Useful for understanding project structure and navigating codebase."
- **Parameters:**
  - `format` (string, optional, enum: ["tree", "summary"], default: "summary"): Output format
- **REST Endpoint:** `GET /api/tree/data`
- **Response Format:** JSON with tree structure (nodes, edges, hierarchy)
- **Special Logic:**
  - If format="summary": Returns summary (node counts, file count, folder count)
  - If format="tree": Returns full JSON structure
- **Formatter:** format_result() with inline formatting (Lines 636-664)

#### [MCP-TOOL-004] vetka_health
- **Location:** src/mcp/vetka_mcp_bridge.py:233-241
- **MCP Decorator Line:** 177 (@server.list_tools)
- **Handler Line:** 666-668
- **Status:** ACTIVE
- **Description:** "Check VETKA server health and component status. Shows which components (Qdrant, metrics, model router, etc.) are available and healthy."
- **Parameters:** None (object with no properties)
- **REST Endpoint:** `GET /api/health`
- **Response Format:** JSON with status, version, phase, components dict
- **Formatter:** format_result() → Lines 1064-1082 (health status formatted output)

#### [MCP-TOOL-005] vetka_list_files
- **Location:** src/mcp/vetka_mcp_bridge.py:242-264
- **MCP Decorator Line:** 177 (@server.list_tools)
- **Handler Line:** 670-701
- **Status:** ACTIVE
- **Description:** "List files in a directory or matching a pattern. Returns file paths with metadata."
- **Parameters:**
  - `path` (string, optional, default: "."): Directory path to list
  - `pattern` (string, optional): Glob pattern to filter files (e.g., '*.py', 'src/**/*.ts')
  - `recursive` (boolean, optional, default: False): Recursively list subdirectories
- **REST Endpoint:** `GET /api/tree/data` (reuses tree endpoint)
- **Implementation Note:** TODO comment indicates proper file listing endpoint needed
- **Local Processing:** Filters tree nodes by type="file" and applies pattern matching
- **Formatter:** format_result() with inline formatting (Lines 690-701)

#### [MCP-TOOL-006] vetka_search_files
- **Location:** src/mcp/vetka_mcp_bridge.py:265-290
- **MCP Decorator Line:** 177 (@server.list_tools)
- **Handler Line:** 703-714
- **Status:** ACTIVE (Limited - uses semantic search)
- **Description:** "Search for files by name or content pattern using ripgrep-style search. Fast full-text search across the codebase."
- **Parameters:**
  - `query` (string, required): Search query (file name or content pattern)
  - `search_type` (string, optional, enum: ["filename", "content", "both"], default: "both"): Search in filenames, file content, or both
  - `limit` (integer, optional, default: 20): Max results
- **REST Endpoint:** `GET /api/search/semantic` (reuses semantic search)
- **Implementation Note:** TODO comment indicates dedicated file search endpoint needed
- **Formatter:** format_result() (reuses semantic formatter)

#### [MCP-TOOL-007] vetka_get_metrics
- **Location:** src/mcp/vetka_mcp_bridge.py:291-305
- **MCP Decorator Line:** 177 (@server.list_tools)
- **Handler Line:** 716-737
- **Status:** ACTIVE
- **Description:** "Get VETKA metrics and analytics. Shows system performance, query stats, and usage data."
- **Parameters:**
  - `metric_type` (string, optional, enum: ["dashboard", "agents", "all"], default: "dashboard"): Type of metrics to retrieve
- **REST Endpoints:**
  - `GET /api/metrics/dashboard` (if metric_type="dashboard")
  - `GET /api/metrics/agents` (if metric_type="agents")
  - Both (if metric_type="all") with combined result
- **Formatter:** format_result() with JSON output (Lines 734-737)

#### [MCP-TOOL-008] vetka_get_knowledge_graph
- **Location:** src/mcp/vetka_mcp_bridge.py:306-321
- **MCP Decorator Line:** 177 (@server.list_tools)
- **Handler Line:** 739-765
- **Status:** ACTIVE
- **Description:** "Get VETKA knowledge graph structure showing relationships between code entities, concepts, and documents. Useful for understanding architecture and dependencies."
- **Parameters:**
  - `format` (string, optional, enum: ["json", "summary"], default: "summary"): Output format
- **REST Endpoint:** `GET /api/tree/knowledge-graph`
- **Response Format:** JSON with nodes and edges arrays
- **Special Logic:**
  - If format="summary": Returns summary (node count, edge count)
  - If format="json": Returns full graph structure
- **Formatter:** format_result() with inline formatting (Lines 748-765)

---

### WRITE TOOLS

#### [MCP-TOOL-009] vetka_edit_file
- **Location:** src/mcp/vetka_mcp_bridge.py:325-359
- **MCP Decorator Line:** 177 (@server.list_tools)
- **Handler Line:** 771-782
- **Status:** ACTIVE
- **Description:** "Edit or create a file. Creates backup before changes. Default: dry_run=true (preview only). Set dry_run=false to apply changes."
- **Parameters:**
  - `path` (string, required): File path relative to project root (e.g., 'src/main.py')
  - `content` (string, required): New file content
  - `mode` (string, optional, enum: ["write", "append"], default: "write"): Write mode
  - `create_dirs` (boolean, optional, default: False): Create parent directories if they don't exist
  - `dry_run` (boolean, optional, default: True): Preview only (no actual write)
- **Internal Tool:** `EditFileTool` from `src.mcp.tools.edit_file_tool`
- **Implementation:** Lines 771-782
  - Validates arguments via `tool.validate_arguments()`
  - Executes via `tool.execute()`
  - Returns formatted result via `format_write_result()`
- **Formatter:** format_write_result() → Lines 1088-1143

#### [MCP-TOOL-010] vetka_git_commit
- **Location:** src/mcp/vetka_mcp_bridge.py:360-384
- **MCP Decorator Line:** 177 (@server.list_tools)
- **Handler Line:** 784-795
- **Status:** ACTIVE
- **Description:** "Create a git commit. Default: dry_run=true (preview only). Set dry_run=false to actually commit."
- **Parameters:**
  - `message` (string, required, min 5 chars): Commit message
  - `files` (array of strings, optional): Files to stage (empty = all changed files)
  - `dry_run` (boolean, optional, default: True): Preview only. Set to false to commit.
- **Internal Tool:** `GitCommitTool` from `src.mcp.tools.git_tool`
- **Implementation:** Lines 784-795
  - Validates arguments via `tool.validate_arguments()`
  - Executes via `tool.execute()`
  - Returns formatted result via `format_write_result()`
- **Formatter:** format_write_result() with commit-specific formatting (Lines 1113-1119)

#### [MCP-TOOL-011] vetka_run_tests
- **Location:** src/mcp/vetka_mcp_bridge.py:385-414
- **MCP Decorator Line:** 177 (@server.list_tools)
- **Handler Line:** 804-815
- **Status:** ACTIVE
- **Description:** "Run pytest tests with output capture. Returns stdout/stderr/exit code."
- **Parameters:**
  - `test_path` (string, optional, default: "tests/"): Path to test file or directory
  - `pattern` (string, optional): Test name pattern (-k flag)
  - `verbose` (boolean, optional, default: True): Verbose output
  - `timeout` (integer, optional, default: 60, min: 1, max: 300): Timeout in seconds
- **Internal Tool:** `RunTestsTool` from `src.mcp.tools.run_tests_tool`
- **Implementation:** Lines 804-815
  - Validates arguments via `tool.validate_arguments()`
  - Executes via `tool.execute()`
  - Returns formatted result via `format_test_result()`
- **Formatter:** format_test_result() → Lines 1189-1221

---

### DEVELOPMENT TOOLS

#### [MCP-TOOL-012] vetka_camera_focus
- **Location:** src/mcp/vetka_mcp_bridge.py:415-441
- **MCP Decorator Line:** 177 (@server.list_tools)
- **Handler Line:** 817-822
- **Status:** ACTIVE (Requires UI Session)
- **Description:** "Move 3D camera to focus on a specific file, branch, or overview. Use to show user something important in the visualization. Requires active VETKA UI session."
- **Parameters:**
  - `target` (string, required): File path (e.g., 'src/main.py'), branch name, or 'overview' for full tree
  - `zoom` (string, optional, enum: ["close", "medium", "far"], default: "medium"): Zoom level
  - `highlight` (boolean, optional, default: True): Highlight target with glow effect
- **Internal Tool:** `CameraControlTool` from `src.mcp.tools.camera_tool`
- **Implementation:** Lines 817-822
  - Executes via `tool.execute()`
  - Returns formatted result via `format_camera_result()`
- **Formatter:** format_camera_result() → Lines 1224-1248
- **Dependencies:** Requires active SocketIO connection to VETKA UI

#### [MCP-TOOL-013] vetka_git_status
- **Location:** src/mcp/vetka_mcp_bridge.py:442-450
- **MCP Decorator Line:** 177 (@server.list_tools)
- **Handler Line:** 797-802
- **Status:** ACTIVE (Read-Only)
- **Description:** "Get git status showing modified, staged, and untracked files. Also shows current branch and last commit."
- **Parameters:** None (object with no properties)
- **Internal Tool:** `GitStatusTool` from `src.mcp.tools.git_tool`
- **Implementation:** Lines 797-802
  - Executes via `tool.execute()`
  - Returns formatted result via `format_git_status()`
- **Formatter:** format_git_status() → Lines 1146-1186

---

### MODEL INTERACTION

#### [MCP-TOOL-014] vetka_call_model
- **Location:** src/mcp/vetka_mcp_bridge.py:451-495
- **MCP Decorator Line:** 177 (@server.list_tools)
- **Handler Line:** 824-835
- **Status:** ACTIVE
- **Description:** "Call any LLM model through VETKA infrastructure (Grok, GPT, Claude, Gemini, Ollama). Supports function calling for compatible models."
- **Parameters:**
  - `model` (string, required): Model: grok-4, gpt-4o, claude-opus-4-5, gemini-2.0-flash, llama3.1:8b, etc.
  - `messages` (array of objects, required): Chat messages [{role, content}]
    - Each message: {role: "user|assistant|system", content: string}
  - `temperature` (number, optional, default: 0.7, range: 0.0-2.0): Temperature for sampling
  - `max_tokens` (integer, optional, default: 4096, min: 1): Max tokens to generate
  - `tools` (array of objects, optional): Optional function calling tools (OpenAI format)
- **Internal Tool:** `LLMCallTool` from `src.mcp.tools.llm_call_tool`
- **Implementation:** Lines 824-835
  - Validates arguments via `tool.validate_arguments()`
  - Executes via `tool.execute()`
  - Returns formatted result via `format_llm_result()`
- **Formatter:** format_llm_result() → Lines 1251-1288

---

### GROUP COMMUNICATION

#### [MCP-TOOL-015] vetka_read_group_messages
- **Location:** src/mcp/vetka_mcp_bridge.py:496-514
- **MCP Decorator Line:** 177 (@server.list_tools)
- **Handler Line:** 837-845
- **Status:** ACTIVE
- **Description:** "Read messages from VETKA group chat. Use to see what other agents wrote."
- **Parameters:**
  - `group_id` (string, optional, default: "609c0d9a-b5bc-426b-b134-d693023bdac8"): Group ID (default: MCP log group)
  - `limit` (integer, optional, default: 10): Max messages to return
- **REST Endpoint:** `GET /api/groups/{group_id}/messages`
- **Query Parameters:** `limit={limit}`
- **Response Format:** JSON with messages array
- **Formatter:** format_result() → Lines 1033-1055 (group messages formatter)

---

### MEMORY TOOLS (Phase 93.6)

#### [MCP-TOOL-016] vetka_get_conversation_context
- **Location:** src/mcp/vetka_mcp_bridge.py:518-542
- **MCP Decorator Line:** 177 (@server.list_tools)
- **Handler Line:** 851-899
- **Status:** ACTIVE
- **Description:** "Get ELISION-compressed conversation context. Use before responding to get relevant conversation history with 40-60% token savings. Returns compressed context suitable for prompt injection."
- **Parameters:**
  - `group_id` (string, optional): Group ID to get context from
  - `max_messages` (integer, optional, default: 20): Max messages to include in context
  - `compress` (boolean, optional, default: True): Apply ELISION compression
- **REST Endpoints:**
  - `GET /api/groups/{group_id}/messages` (if group_id provided)
  - `GET /api/chat/history` (if group_id not provided)
- **Query Parameters:** `limit={max_messages}`
- **Internal Processing:**
  - If compress=True: Uses `compress_context()` from `src.memory.elision`
  - Returns compressed format with token savings estimate (40-60%)
  - If compress=False: Returns raw messages
- **Formatter:** format_context_result() → Lines 1295-1323
- **Handler:** Lines 851-899 (dedicated implementation with compression logic)

#### [MCP-TOOL-017] vetka_get_user_preferences
- **Location:** src/mcp/vetka_mcp_bridge.py:543-563
- **MCP Decorator Line:** 177 (@server.list_tools)
- **Handler Line:** 901-930
- **Status:** ACTIVE
- **Description:** "Get user preferences from Engram memory. Returns hot preferences (frequently accessed) from RAM cache plus cold preferences from Qdrant. Use to personalize responses based on user's communication style, favorite topics, etc."
- **Parameters:**
  - `user_id` (string, optional, default: "danila"): User ID
  - `category` (string, optional, enum: ["communication_style", "viewport_patterns", "code_preferences", "topics", "all"]): Preference category to fetch
- **Internal Implementation:** Direct Python integration (no REST endpoint)
  - Uses `EngramUserMemory` from `src.memory.engram_user_memory`
  - Uses `get_qdrant_client()` from `src.memory.qdrant_client`
  - Hybrid retrieval: RAM cache (hot) + Qdrant (cold)
- **Formatter:** format_preferences_result() → Lines 1326-1350
- **Handler:** Lines 901-930 (dedicated implementation)

#### [MCP-TOOL-018] vetka_get_memory_summary
- **Location:** src/mcp/vetka_mcp_bridge.py:564-584
- **MCP Decorator Line:** 177 (@server.list_tools)
- **Handler Line:** 932-964
- **Status:** ACTIVE
- **Description:** "Get CAM (Context-Aware Memory) and Elisium compression summary. Returns: active memory nodes, compression stats, age distribution, quality scores. Use to understand what context is available and its quality level."
- **Parameters:**
  - `include_stats` (boolean, optional, default: True): Include compression statistics
  - `include_nodes` (boolean, optional, default: False): Include list of active memory nodes
- **Internal Implementation:** Direct Python integration (no REST endpoint)
  - Uses `MemoryCompression` from `src.memory.compression`
  - Returns compression schedule (4 levels: 0-6 days, 7-29 days, 30-89 days, 90+)
  - Dimensions: 768D → 384D → 256D → 64D with quality degradation
- **Formatter:** format_memory_summary() → Lines 1353-1381
- **Handler:** Lines 932-964 (dedicated implementation)

---

## REST Endpoint Mapping Summary

| Endpoint | HTTP Method | Purpose | Tools | Status |
|----------|-------------|---------|-------|--------|
| `/api/search/semantic` | GET | Semantic vector search | MCP-TOOL-001, MCP-TOOL-006 | ACTIVE |
| `/api/files/read` | POST | Read file content | MCP-TOOL-002 | ACTIVE |
| `/api/tree/data` | GET | Get tree structure | MCP-TOOL-003, MCP-TOOL-005 | ACTIVE |
| `/api/health` | GET | Health check | MCP-TOOL-004 | ACTIVE |
| `/api/metrics/dashboard` | GET | Dashboard metrics | MCP-TOOL-007 | ACTIVE |
| `/api/metrics/agents` | GET | Agent metrics | MCP-TOOL-007 | ACTIVE |
| `/api/tree/knowledge-graph` | GET | Knowledge graph | MCP-TOOL-008 | ACTIVE |
| `/api/groups/{group_id}/messages` | GET | Group messages | MCP-TOOL-015, MCP-TOOL-016 | ACTIVE |
| `/api/chat/history` | GET | Chat history | MCP-TOOL-016 | ACTIVE |
| `/api/debug/mcp/groups/{group_id}/send` | POST | Log to group chat | MCP Bridge Internal | ACTIVE |

---

## Tool Categories Analysis

### By Execution Model

**REST API Clients (10 tools):**
- MCP-TOOL-001: vetka_search_semantic
- MCP-TOOL-002: vetka_read_file
- MCP-TOOL-003: vetka_get_tree
- MCP-TOOL-004: vetka_health
- MCP-TOOL-005: vetka_list_files
- MCP-TOOL-006: vetka_search_files
- MCP-TOOL-007: vetka_get_metrics
- MCP-TOOL-008: vetka_get_knowledge_graph
- MCP-TOOL-015: vetka_read_group_messages
- MCP-TOOL-016: vetka_get_conversation_context (hybrid: REST + local compression)

**Internal Tool Classes (5 tools):**
- MCP-TOOL-009: vetka_edit_file → EditFileTool
- MCP-TOOL-010: vetka_git_commit → GitCommitTool
- MCP-TOOL-011: vetka_run_tests → RunTestsTool
- MCP-TOOL-012: vetka_camera_focus → CameraControlTool
- MCP-TOOL-013: vetka_git_status → GitStatusTool
- MCP-TOOL-014: vetka_call_model → LLMCallTool

**Direct Python Integration (3 tools):**
- MCP-TOOL-017: vetka_get_user_preferences → EngramUserMemory + Qdrant
- MCP-TOOL-018: vetka_get_memory_summary → MemoryCompression
- Note: MCP-TOOL-016 also uses direct Python (ELISION compression)

### By Safety Level

**Read-Only (8 tools):** MCP-TOOL-001 through MCP-TOOL-008, MCP-TOOL-015
- No state modifications
- Can execute without restrictions

**Safe-Write (1 tool):** MCP-TOOL-013 (vetka_git_status)
- Reads git state only
- No modifications

**Controlled-Write (3 tools):** MCP-TOOL-009, MCP-TOOL-010, MCP-TOOL-011
- Support dry_run mode (default: True)
- Require explicit opt-in for actual modification
- Create backups before writes

**Unrestricted-Write (2 tools):** MCP-TOOL-012 (camera), MCP-TOOL-014 (LLM call)
- Immediate execution
- Camera requires UI availability
- LLM call requires model API keys

**Memory-Read (3 tools):** MCP-TOOL-016, MCP-TOOL-017, MCP-TOOL-018
- Read user/context data only
- No modifications
- Internal system access only

---

## Logging and Monitoring

### MCP Request Logging

**Group Chat Logging:** Lines 83-114
- **Function:** `log_to_group_chat()` → Sends to VETKA group chat
- **Group ID:** `5e2198c2-8b1a-45df-807f-5c73c5496aa8` (Claude Architect group)
- **Enable Flag:** `MCP_LOG_ENABLED = True` (Line 81)
- **Endpoint:** `POST /api/debug/mcp/groups/{group_id}/send`

**Request Tracking:** Lines 100-105
- Function: `log_mcp_request(tool_name, arguments, request_id)`
- Logs tool name, arguments (truncated to 200 chars), and request ID

**Response Tracking:** Lines 108-113
- Function: `log_mcp_response(tool_name, result, request_id, duration_ms, error)`
- Logs success/error with duration in milliseconds
- Formats response with status emoji (✅/❌)

**Request ID Generation:** Line 599
- Format: `req-{uuid.hex[:8]}` (e.g., "req-a1b2c3d4")
- Used for correlating requests and responses

---

## Error Handling

### Connection Errors (Lines 993-1000)
```
httpx.ConnectError → "Cannot connect to VETKA server at localhost:5001"
```

### Validation Errors (Lines 777-779, 790-792, etc.)
```
tool.validate_arguments() → Returns error message if validation fails
```

### HTTP Status Errors (Lines 984-991)
```
Non-200 status codes → Returns "Error: HTTP {status_code}\n{response.text}"
```

### General Exceptions (Lines 1001-1008)
```
Any exception → "Error executing {tool_name}: {str(e)}"
```

---

## Tool Dependencies

### Import Dependencies by Tool

**MCP-TOOL-009 (vetka_edit_file):**
```python
from src.mcp.tools.edit_file_tool import EditFileTool
```

**MCP-TOOL-010 (vetka_git_commit):**
```python
from src.mcp.tools.git_tool import GitCommitTool
```

**MCP-TOOL-013 (vetka_git_status):**
```python
from src.mcp.tools.git_tool import GitStatusTool
```

**MCP-TOOL-011 (vetka_run_tests):**
```python
from src.mcp.tools.run_tests_tool import RunTestsTool
```

**MCP-TOOL-012 (vetka_camera_focus):**
```python
from src.mcp.tools.camera_tool import CameraControlTool
```

**MCP-TOOL-014 (vetka_call_model):**
```python
from src.mcp.tools.llm_call_tool import LLMCallTool
```

**MCP-TOOL-016 (vetka_get_conversation_context):**
```python
from src.memory.elision import compress_context
```

**MCP-TOOL-017 (vetka_get_user_preferences):**
```python
from src.memory.engram_user_memory import EngramUserMemory
from src.memory.qdrant_client import get_qdrant_client
```

**MCP-TOOL-018 (vetka_get_memory_summary):**
```python
from src.memory.compression import MemoryCompression
```

---

## Markers Summary Table

| MCP Marker | Tool Name | Tool Def Lines | Handler Lines | REST Endpoint | Internal Tool | Status |
|----------|-----------|-----------------|---------------|---------------|---------------|--------|
| MCP-TOOL-001 | vetka_search_semantic | 181-202 | 611-619 | GET /api/search/semantic | ❌ | ACTIVE |
| MCP-TOOL-002 | vetka_read_file | 203-216 | 621-628 | POST /api/files/read | ❌ | ACTIVE |
| MCP-TOOL-003 | vetka_get_tree | 217-232 | 630-664 | GET /api/tree/data | ❌ | ACTIVE |
| MCP-TOOL-004 | vetka_health | 233-241 | 666-668 | GET /api/health | ❌ | ACTIVE |
| MCP-TOOL-005 | vetka_list_files | 242-264 | 670-701 | GET /api/tree/data | ❌ | ACTIVE |
| MCP-TOOL-006 | vetka_search_files | 265-290 | 703-714 | GET /api/search/semantic | ❌ | ACTIVE |
| MCP-TOOL-007 | vetka_get_metrics | 291-305 | 716-737 | GET /api/metrics/* | ❌ | ACTIVE |
| MCP-TOOL-008 | vetka_get_knowledge_graph | 306-321 | 739-765 | GET /api/tree/knowledge-graph | ❌ | ACTIVE |
| MCP-TOOL-009 | vetka_edit_file | 325-359 | 771-782 | ❌ | EditFileTool | ACTIVE |
| MCP-TOOL-010 | vetka_git_commit | 360-384 | 784-795 | ❌ | GitCommitTool | ACTIVE |
| MCP-TOOL-011 | vetka_run_tests | 385-414 | 804-815 | ❌ | RunTestsTool | ACTIVE |
| MCP-TOOL-012 | vetka_camera_focus | 415-441 | 817-822 | ❌ | CameraControlTool | ACTIVE |
| MCP-TOOL-013 | vetka_git_status | 442-450 | 797-802 | ❌ | GitStatusTool | ACTIVE |
| MCP-TOOL-014 | vetka_call_model | 451-495 | 824-835 | ❌ | LLMCallTool | ACTIVE |
| MCP-TOOL-015 | vetka_read_group_messages | 496-514 | 837-845 | GET /api/groups/{id}/messages | ❌ | ACTIVE |
| MCP-TOOL-016 | vetka_get_conversation_context | 518-542 | 851-899 | GET /api/groups/{id}/messages + /api/chat/history | ❌ | ACTIVE |
| MCP-TOOL-017 | vetka_get_user_preferences | 543-563 | 901-930 | ❌ | EngramUserMemory + Qdrant | ACTIVE |
| MCP-TOOL-018 | vetka_get_memory_summary | 564-584 | 932-964 | ❌ | MemoryCompression | ACTIVE |

---

## OpenCode Bridge Compatibility Status

All tools in vetka_mcp_bridge.py are designed to work with Claude Code via MCP stdio protocol.

### To Use These Tools in Claude Code:

```bash
# Register VETKA MCP in Claude Code
claude mcp add vetka -- python /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py
```

### Missing OpenCode Bridge Features

**Not in OpenCode Bridge (from system):**
- vetka_search_semantic ✅ Exists in MCP Bridge only
- vetka_read_file ✅ Exists in MCP Bridge only
- vetka_get_tree ✅ Exists in MCP Bridge only
- vetka_health ✅ Exists in MCP Bridge only
- vetka_list_files ✅ Exists in MCP Bridge only
- vetka_search_files ✅ Exists in MCP Bridge only
- vetka_get_metrics ✅ Exists in MCP Bridge only
- vetka_get_knowledge_graph ✅ Exists in MCP Bridge only
- vetka_edit_file ✅ Exists in MCP Bridge only
- vetka_git_commit ✅ Exists in MCP Bridge only
- vetka_run_tests ✅ Exists in MCP Bridge only
- vetka_camera_focus ✅ Exists in MCP Bridge only
- vetka_git_status ✅ Exists in MCP Bridge only
- vetka_call_model ✅ Exists in MCP Bridge only
- vetka_read_group_messages ✅ Exists in MCP Bridge only
- vetka_get_conversation_context ✅ Exists in MCP Bridge only
- vetka_get_user_preferences ✅ Exists in MCP Bridge only
- vetka_get_memory_summary ✅ Exists in MCP Bridge only

**All 18 tools are MCP-first design** - OpenCode bridge requires separate implementation if needed.

---

## Performance Characteristics

### Timeout Configuration
- **HTTP Client Timeout:** 30 seconds (Line 44: VETKA_TIMEOUT = 30.0)
- **Test Tool Timeout:** Maximum 300 seconds, default 60 seconds

### Request ID Tracking
- **Format:** `req-{8-char uuid hex}`
- **Scope:** Correlates single request through logging pipeline

### Response Duration Logging
- **Captured:** `time.time() - start_time` converted to milliseconds
- **Logged to Group Chat:** Duration always included in response log

---

## Configuration and Constants

### Connection Settings (Lines 42-44)
```python
VETKA_BASE_URL = "http://localhost:5001"
VETKA_TIMEOUT = 30.0
```

### Group Chat Logging (Lines 80-81)
```python
MCP_LOG_GROUP_ID = "5e2198c2-8b1a-45df-807f-5c73c5496aa8"  # Claude Architect group
MCP_LOG_ENABLED = True
```

### Lifecycle Management (Lines 57-72)
- **Initialization:** `init_client()` - Creates httpx.AsyncClient
- **Cleanup:** `cleanup_client()` - Closes httpx.AsyncClient
- **Main Entry:** Lines 1388-1407 with try/finally for cleanup

---

## Phase Information

- **File Phase:** Phase 65.1 (Line 7)
- **Last Audit:** 2026-01-18 (Line 8)
- **Memory Tools Phase:** Phase 93.6 (Line 516)
- **Write Tools Phase:** Phase 65.2 (Line 323)
- **Status:** PRODUCTION (Line 6)

---

## Notes for Future Development

### TODO Items Found

1. **Line 672:** Implement proper file listing endpoint in VETKA
   - Currently reuses tree endpoint with client-side filtering
   - Affected: MCP-TOOL-005, MCP-TOOL-006

2. **Line 710:** Add dedicated file search endpoint
   - Currently reuses semantic search
   - Should support ripgrep-style filtering

### Archived Features

Lines 117-170: Old console logging implementation archived
- Previous logging to standalone console on port 5002
- Replaced by group chat logging (Lines 83-114)

---

## Audit Summary

- **Total Tools Audited:** 18
- **Tools by Type:**
  - REST API Clients: 10
  - Internal Tool Wrappers: 6
  - Direct Python Integration: 2
- **Active Tools:** 18/18
- **Critical Dependencies:** 9 (internal tool imports + memory system)
- **REST Endpoints Used:** 9 unique endpoints
- **Error Handling:** Full coverage with ConnectError, validation, HTTP status, and general exceptions
- **Logging:** Full request/response tracking to VETKA group chat
- **Safety:** Dry-run mode for write operations, compression for memory tools

---

Generated: 2026-01-26 by Phase 95.2 Audit
Source: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py`
