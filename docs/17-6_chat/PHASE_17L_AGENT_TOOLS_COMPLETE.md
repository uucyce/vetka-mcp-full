# Phase 17-L: Agent Tools with Function Calling

**Status:** ✅ COMPLETE
**Date:** 2025-12-27
**Commit:** `2e7cd31`
**Tests:** 30/30 passing

---

## Overview

Phase 17-L implements **real function calling** for VETKA agents (PM, Dev, QA, Architect). Previously, agents could only generate text responses. Now they can:

- Read/write files
- Execute code
- Search the codebase
- Run tests
- Create artifacts for UI visibility

---

## Files Changed

| File | Changes |
|------|---------|
| `src/agents/tools.py` | NEW - 10 tool implementations with agent permissions |
| `src/agents/role_prompts.py` | Updated PM, Dev, QA prompts with tool instructions |
| `src/orchestration/orchestrator_with_elisya.py` | Uses agent-specific tools via `get_tools_for_agent()` |
| `tests/test_agent_tools.py` | Extended with Phase 17-L tests (30 total) |

---

## New Tools (10 total)

### Read-Only Tools
| Tool | Description | Agents |
|------|-------------|--------|
| `read_code_file` | Read file contents | All |
| `list_files` | List files in directory | All |
| `search_codebase` | Grep search for patterns | PM, Dev, QA, Architect |
| `search_weaviate` | Semantic search in knowledge base | PM, Architect, Hostess |
| `get_file_info` | File metadata (size, lines, modified) | All |

### Write Tools
| Tool | Description | Agents |
|------|-------------|--------|
| `write_code_file` | Create/update files | Dev only |
| `execute_code` | Run shell commands | Dev, QA |
| `validate_syntax` | Check Python/JSON/JS syntax | Dev, QA |
| `run_tests` | Execute pytest | QA only |
| `create_artifact` | Create UI-visible artifacts | Dev, Architect |

---

## Agent Permissions

```python
AGENT_TOOL_PERMISSIONS = {
    "PM": [
        "read_code_file", "list_files", "search_codebase",
        "search_weaviate", "get_file_info"
    ],
    "Dev": [
        "read_code_file", "write_code_file", "list_files",
        "execute_code", "search_codebase", "create_artifact",
        "validate_syntax", "get_file_info"
    ],
    "QA": [
        "read_code_file", "execute_code", "run_tests",
        "validate_syntax", "search_codebase", "get_file_info"
    ],
    "Architect": [
        "read_code_file", "list_files", "search_codebase",
        "search_weaviate", "get_file_info", "create_artifact"
    ],
    "Hostess": [
        "search_weaviate", "list_files", "get_file_info"
    ]
}
```

---

## Security Features

1. **Path Traversal Protection**
   - All paths validated to be within PROJECT_ROOT
   - `../` patterns blocked

2. **Dangerous Command Blocking**
   ```python
   BLOCKED_PATTERNS = [
       'rm -rf /', 'rm -rf ~', 'sudo', 'chmod 777',
       '> /dev', 'mkfs', 'dd if=', 'curl | sh'
   ]
   ```

3. **Output Size Limits**
   - Files: 50KB max
   - Command output: 10KB max
   - Search results: 50 matches max

4. **Permission-Based Access**
   - PM cannot write files
   - QA cannot modify code
   - Each agent gets only its allowed tools

---

## Integration Points

### Orchestrator (`orchestrator_with_elisya.py`)

```python
# Line 822-824
tool_schemas = get_tools_for_agent(agent_type)
print(f"🔧 {agent_type} has access to {len(tool_schemas)} tools")
```

The orchestrator's `_call_llm_with_tools_loop` method now uses agent-specific tools instead of all tools.

### Role Prompts (`role_prompts.py`)

Each agent prompt now includes:
- List of available tools
- When to use tools
- Example workflow with tools

Example for Dev:
```
## WORKFLOW WITH TOOLS
1. FIRST: read_code_file() to see existing code
2. THEN: Write your changes
3. ALWAYS: validate_syntax() before write_code_file()
4. FINALLY: create_artifact() for user visibility
```

---

## Test Results

```
tests/test_agent_tools.py::TestAgentPermissions::test_pm_tools_read_only PASSED
tests/test_agent_tools.py::TestAgentPermissions::test_dev_tools_include_write PASSED
tests/test_agent_tools.py::TestAgentPermissions::test_qa_tools_include_tests PASSED
tests/test_agent_tools.py::TestValidateSyntaxTool::test_valid_python PASSED
tests/test_agent_tools.py::TestValidateSyntaxTool::test_invalid_python PASSED
tests/test_agent_tools.py::TestSearchCodebaseTool::test_search_finds_pattern PASSED
tests/test_agent_tools.py::TestExecuteCodeTool::test_blocked_command PASSED
tests/test_agent_tools.py::TestExecuteCodeTool::test_sudo_blocked PASSED
tests/test_agent_tools.py::TestCreateArtifactTool::test_create_code_artifact PASSED
tests/test_agent_tools.py::TestAllToolsRegistered::test_new_tools_in_registry PASSED
...
============================== 30 passed in 0.08s ==============================
```

---

## Usage Example

```python
from src.agents.tools import get_tools_for_agent, AgentToolExecutor

# Get tools for Dev agent
dev_tools = get_tools_for_agent("Dev")
# Returns: 8 Ollama-compatible tool schemas

# Execute a tool manually
executor = AgentToolExecutor()
result = executor.execute("validate_syntax", {
    "code": "def hello(): pass",
    "language": "python"
})
# Returns: {"success": True, "result": {"valid": True, "message": "Python syntax OK"}}
```

---

## Next Steps

1. **Phase 17-M:** UI integration for artifacts display
2. **Phase 17-N:** Tool call logging and analytics
3. **Phase 17-O:** Weaviate search integration (currently placeholder)

---

## Commit Details

```
commit 2e7cd31
Author: Claude Opus 4.5
Date:   2025-12-27

Phase 17-L: Agent Tools with Function Calling

- src/agents/tools.py: 10 tools for agents
- Agent-specific tool permissions (PM read-only, Dev write, QA test)
- Security: path traversal, dangerous command blocking
- 30 unit tests all passing
```
