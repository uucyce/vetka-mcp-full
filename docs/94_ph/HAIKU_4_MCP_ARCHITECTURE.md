# Phase 94: MCP Architecture for External Tools

**Agent:** Haiku 4
**Date:** 2026-01-26
**Status:** COMPREHENSIVE - 18 tools, 3 transports, gaps identified

---

## 1. MCP OVERVIEW

**Path:** `src/mcp/vetka_mcp_bridge.py`
**Protocol:** Model Context Protocol (Anthropic standard)
**Purpose:** Expose VETKA tools to external clients (Claude Code, OpenCode)

---

## 2. TRANSPORT LAYER

### Supported Transports:
| Transport | Port | Client | Status |
|-----------|------|--------|--------|
| stdio | - | Claude Code CLI | WORKING |
| HTTP | 5002 | REST clients | WORKING |
| SSE | 5002 | Streaming | WORKING |

### Connection Flow:
```
Claude Code
    ↓
stdio transport
    ↓
┌─────────────────────────┐
│ vetka_mcp_bridge.py     │
│ - Tool registration     │
│ - Request routing       │
│ - Response formatting   │
└──────────┬──────────────┘
           ↓
┌─────────────────────────┐
│ VETKA Backend           │
│ - Qdrant search         │
│ - File operations       │
│ - Model calls           │
└─────────────────────────┘
```

---

## 3. REGISTERED TOOLS (18)

### Semantic Search (3):
| Tool | Purpose |
|------|---------|
| `vetka_search_semantic` | Vector search in Qdrant |
| `vetka_search_files` | Ripgrep-style text search |
| `vetka_list_files` | Directory listing |

### File Operations (3):
| Tool | Purpose |
|------|---------|
| `vetka_read_file` | Read file content |
| `vetka_edit_file` | Edit/create files (dry_run default) |
| `vetka_get_tree` | 3D tree structure |

### Git Operations (2):
| Tool | Purpose |
|------|---------|
| `vetka_git_status` | Modified/staged/untracked |
| `vetka_git_commit` | Create commit (dry_run default) |

### System (4):
| Tool | Purpose |
|------|---------|
| `vetka_health` | Server health check |
| `vetka_get_metrics` | Performance metrics |
| `vetka_get_knowledge_graph` | Entity relationships |
| `vetka_run_tests` | Run pytest |

### Model Interaction (2):
| Tool | Purpose |
|------|---------|
| `vetka_call_model` | Call any LLM via VETKA |
| `vetka_camera_focus` | 3D visualization control |

### Group Chat (2):
| Tool | Purpose |
|------|---------|
| `vetka_read_group_messages` | Read group history |
| `vetka_write_group_message` | Post to group |

---

## 4. ENTRY POINT COMPLEXITY

### Current Entry (Claude Code):
```json
{
  "mcpServers": {
    "vetka": {
      "command": "python",
      "args": ["-m", "src.mcp.vetka_mcp_bridge"],
      "cwd": "/path/to/vetka_live_03"
    }
  }
}
```

### What Claude Code Receives:
1. Tool list (18 tools)
2. Tool schemas (JSON Schema)
3. Tool descriptions
4. NO context about VETKA project
5. NO user preferences
6. NO session memory

---

## 5. IDENTIFIED GAPS

### Gap 1: No Session Context
```
Problem: New Claude Code session = blank slate
Missing: User story, project context, recent work
Solution: Add "session_init" tool that returns compressed context
```

### Gap 2: No MCP-to-MCP Bridging
```
Problem: Can't call external MCPs from VETKA
Missing: Bridge to other MCP servers
Solution: Add MCP client capability
```

### Gap 3: Static Tool Registration
```
Problem: Tools registered at startup only
Missing: Dynamic tool discovery
Solution: Tool registry with hot-reload
```

### Gap 4: No Tool Composition
```
Problem: Each tool is atomic
Missing: Compound tools (search → read → summarize)
Solution: Add programmatic tools (chains)
```

### Gap 5: Context Truncation
```
Problem: Large results get truncated
Missing: Streaming for large outputs
Solution: Add pagination or streaming results
```

---

## 6. PROPOSED TOOL CATEGORIES

### Atomic Tools (existing):
- `vetka_search_semantic`
- `vetka_read_file`
- `vetka_call_model`

### Programmatic Tools (NEW):
| Tool | Description |
|------|-------------|
| `vetka_session_init` | Return compressed context for new session |
| `vetka_team_recon` | PM → Haiku swarm for research |
| `vetka_parallel_execute` | Run N tasks in parallel |
| `vetka_sequential_chain` | Step-by-step execution |

### Workflow Tools (NEW):
| Tool | Description |
|------|-------------|
| `vetka_architect_plan` | Create implementation plan |
| `vetka_dev_implement` | Execute plan item |
| `vetka_qa_verify` | Test implementation |
| `vetka_merge_results` | Combine parallel outputs |

---

## 7. SESSION INIT PROPOSAL

### `vetka_session_init` Tool:
```json
{
  "name": "vetka_session_init",
  "description": "Initialize session with compressed VETKA context",
  "returns": {
    "project_summary": "VETKA 3D knowledge system...",
    "user_context": "User preferences and recent work...",
    "available_tools": ["search", "read", "model_call", ...],
    "recent_artifacts": ["file1.py", "file2.ts", ...],
    "suggested_actions": ["Continue Phase 94...", ...]
  }
}
```

### Context Compression:
1. Project README → 500 tokens max
2. User memory (Engram) → 200 tokens
3. Recent files (CAM) → 300 tokens
4. Tool descriptions → already in MCP schema

---

## 8. MCP vs NATIVE DECISION

### Use MCP When:
- External client (Claude Code, OpenCode)
- Standard protocol needed
- Tool discovery required

### Use Native VETKA When:
- Internal orchestration
- High-speed operations
- Complex state management

### Hybrid Approach:
```
Claude Code (external)
    ↓
MCP Bridge (standard protocol)
    ↓
VETKA Native (internal)
    ↓
Other MCPs (via MCP client)
```

---

## SUMMARY

MCP architecture is SOLID with 18 tools across 3 transports. Main gaps:
1. No session context for new clients
2. No tool composition (chains)
3. No MCP-to-MCP bridging

Proposed solution: Add 4 programmatic tools for session init and workflow orchestration.

**Priority:** HIGH - This enables effective Claude Code integration.
