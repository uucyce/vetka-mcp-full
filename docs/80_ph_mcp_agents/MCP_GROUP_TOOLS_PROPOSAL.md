# MCP GROUP CHAT TOOLS PROPOSAL
## Claude Code Integration for Orchestra Group Management

**Phase:** 80.4 (MCP Agents in Group Chat)
**Status:** Analysis Complete - Ready for Implementation
**Date:** 2026-01-23

---

## OVERVIEW

Claude Code (MCP Agent) should be able to **orchestrate group chats** just like users do:
- Create new orchestration groups
- Add/remove agents and models to groups
- Send messages to groups
- Read group conversation history
- Manage group participants and roles

**Current State:** Only 4 MCP endpoints exist for group chat (all **read/write through REST**).
**Goal:** Expose 4 dedicated **MCP tools** that Claude Code can call directly.

---

## EXISTING ARCHITECTURE

### 1. API Endpoints (Already Exist)

#### Group Management Routes (`/api/groups`)
```
POST   /api/groups                                 Create new group
GET    /api/groups                                 List all groups
GET    /api/groups/{group_id}                      Get group details
POST   /api/groups/{group_id}/participants          Add agent to group
DELETE /api/groups/{group_id}/participants/{agent_id}  Remove agent from group
PATCH  /api/groups/{group_id}/participants/{agent_id}/model  Update model
PATCH  /api/groups/{group_id}/participants/{agent_id}/role   Update role
GET    /api/groups/{group_id}/messages             Get chat history
POST   /api/groups/{group_id}/messages             Send message to group
POST   /api/groups/{group_id}/tasks                Assign task
POST   /api/groups/{group_id}/models/add-direct    Add model directly (Phase 80.19)
```

#### MCP-Specific Routes (`/api/debug/mcp/groups`)
```
GET    /api/debug/mcp/groups                       List groups for MCP agents
GET    /api/debug/mcp/groups/{group_id}/messages   Read messages from group
POST   /api/debug/mcp/groups/{group_id}/send       Send message as MCP agent
```

### 2. Data Model (groups.json)

**Saved in:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/groups.json`

```json
{
  "groups": {
    "609c0d9a-b5bc-426b-b134-d693023bdac8": {
      "id": "609c0d9a-b5bc-426b-b134-d693023bdac8",
      "name": "80 фаза",
      "description": "Group chat with 5 agents",
      "admin_id": "@PM",
      "participants": {
        "@PM": {
          "agent_id": "@PM",
          "model_id": "anthropic/claude-opus-4.5",
          "role": "admin",
          "display_name": "PM (Gpt 5.2 Codex)",
          "permissions": ["read", "write"]
        },
        "@Dev": {
          "agent_id": "@Dev",
          "model_id": "mcp/claude_code",
          "role": "worker",
          "display_name": "Dev (Claude_code)",
          "permissions": ["read", "write"]
        }
      },
      "messages": [...],
      "shared_context": {},
      "project_id": null,
      "created_at": "2026-01-21T22:45:09.699112",
      "last_activity": "2026-01-21T22:45:09.700720"
    }
  }
}
```

### 3. Core Service (GroupChatManager)

**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/group_chat_manager.py`

**Key Methods:**
```python
class GroupChatManager:
    async def create_group(name: str, admin_agent: GroupParticipant,
                          description: str, project_id: Optional[str]) -> Group

    async def add_participant(group_id: str, participant: GroupParticipant) -> bool
    async def remove_participant(group_id: str, agent_id: str) -> bool

    async def send_message(group_id: str, sender_id: str, content: str,
                          message_type: str, metadata: Dict) -> Optional[GroupMessage]

    def get_messages(group_id: str, limit: int = 50) -> List[GroupMessage]
    def get_group(group_id: str) -> Optional[Group]
    def get_all_groups() -> List[Group]
```

### 4. MCP Tool Infrastructure

**Base Class:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/tools/base_tool.py`

**Tool Registry:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py` (function `list_tools()` at line 177)

**Existing Tools:**
- `vetka_search_semantic` - Search knowledge base
- `vetka_read_file` - Read file content
- `vetka_edit_file` - Edit/create files (dry_run supported)
- `vetka_git_commit` - Create commits
- `vetka_run_tests` - Run pytest
- `vetka_get_tree` - Get project structure
- `vetka_list_files` - List files
- `vetka_search_files` - Search files
- `vetka_get_metrics` - System metrics
- `vetka_get_knowledge_graph` - Knowledge graph data
- `vetka_health` - Health check

---

## PROPOSED MCP TOOLS

### 1. `vetka_create_group`

Create a new orchestration group with initial members.

**Endpoint:** `POST /api/groups`

**Tool Schema:**
```json
{
  "name": "vetka_create_group",
  "description": "Create a new orchestration group chat with AI agents. Admin agent is the group creator.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "name": {
        "type": "string",
        "description": "Group name (e.g., 'Backend Refactor Team', 'Phase 80 Work')",
        "minLength": 1,
        "maxLength": 100
      },
      "description": {
        "type": "string",
        "description": "Group description/purpose",
        "maxLength": 500,
        "default": ""
      },
      "admin_agent_id": {
        "type": "string",
        "description": "Agent ID of group admin (e.g., '@PM', '@claude_code')",
        "pattern": "^@[a-zA-Z0-9_-]+$"
      },
      "admin_model_id": {
        "type": "string",
        "description": "Model ID for admin (e.g., 'anthropic/claude-opus-4.5', 'mcp/claude_code')"
      },
      "initial_agents": {
        "type": "array",
        "description": "Optional: Initial agents to add to group",
        "items": {
          "type": "object",
          "properties": {
            "agent_id": {
              "type": "string",
              "description": "Agent ID (e.g., '@Dev', '@QA')",
              "pattern": "^@[a-zA-Z0-9_-]+$"
            },
            "model_id": {
              "type": "string",
              "description": "Model to use (e.g., 'mcp/browser_haiku', 'deepseek-r1')"
            },
            "role": {
              "type": "string",
              "enum": ["admin", "worker", "reviewer", "observer"],
              "description": "Agent role in group",
              "default": "worker"
            },
            "display_name": {
              "type": "string",
              "description": "Display name for UI (e.g., 'QA Lead')"
            }
          },
          "required": ["agent_id", "model_id", "display_name"]
        },
        "default": []
      },
      "project_id": {
        "type": "string",
        "description": "Optional: Link to VETKA project ID"
      }
    },
    "required": ["name", "admin_agent_id", "admin_model_id"]
  }
}
```

**Response:**
```json
{
  "success": true,
  "group": {
    "id": "609c0d9a-b5bc-426b-b134-d693023bdac8",
    "name": "Backend Refactor Team",
    "admin_id": "@PM",
    "participant_count": 3,
    "created_at": "2026-01-23T10:30:45.123456"
  }
}
```

---

### 2. `vetka_add_agent_to_group`

Add an agent to an existing group with specified role.

**Endpoint:** `POST /api/groups/{group_id}/participants` or `POST /api/groups/{group_id}/models/add-direct`

**Tool Schema:**
```json
{
  "name": "vetka_add_agent_to_group",
  "description": "Add an agent or model to an orchestration group. Can add multiple agents in one call.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "group_id": {
        "type": "string",
        "description": "Group UUID (from create_group response or list_groups)"
      },
      "agents": {
        "type": "array",
        "description": "Agents/models to add to group",
        "items": {
          "type": "object",
          "properties": {
            "agent_id": {
              "type": "string",
              "description": "Agent ID (e.g., '@Dev', '@Architect'). Will be auto-generated if omitted.",
              "pattern": "^@?[a-zA-Z0-9_-]+$"
            },
            "model_id": {
              "type": "string",
              "description": "Model to use (e.g., 'mcp/claude_code', 'deepseek/deepseek-r1:free')"
            },
            "role": {
              "type": "string",
              "enum": ["admin", "worker", "reviewer", "observer"],
              "description": "Agent role in group",
              "default": "worker"
            },
            "display_name": {
              "type": "string",
              "description": "Display name (optional, auto-generated from model if omitted)"
            }
          },
          "required": ["model_id"]
        },
        "minItems": 1
      }
    },
    "required": ["group_id", "agents"]
  }
}
```

**Response:**
```json
{
  "success": true,
  "added": [
    {
      "agent_id": "@Architect",
      "model_id": "openai/gpt-5.2-chat",
      "role": "worker",
      "display_name": "Architect"
    }
  ],
  "group_participant_count": 4
}
```

---

### 3. `vetka_send_to_group`

Send a message to group chat. **This endpoint already exists** - just wrapping it as MCP tool.

**Endpoint:** `POST /api/debug/mcp/groups/{group_id}/send`

**Tool Schema:**
```json
{
  "name": "vetka_send_to_group",
  "description": "Send a message to orchestration group chat. Mentions agents with @name syntax. Message may trigger agent responses.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "group_id": {
        "type": "string",
        "description": "Group UUID"
      },
      "content": {
        "type": "string",
        "description": "Message text. Use @AgentName to mention agents (e.g., 'Hey @Dev please review this code')",
        "minLength": 1
      },
      "sender_agent_id": {
        "type": "string",
        "description": "MCP agent sending (default: 'claude_code')",
        "default": "claude_code",
        "enum": ["claude_code", "browser_haiku", "vetka_internal"]
      },
      "message_type": {
        "type": "string",
        "enum": ["chat", "response", "system"],
        "description": "Message type",
        "default": "chat"
      }
    },
    "required": ["group_id", "content"]
  }
}
```

**Response:**
```json
{
  "success": true,
  "message_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "group_id": "609c0d9a-b5bc-426b-b134-d693023bdac8",
  "timestamp": "2026-01-23T10:35:20.456789",
  "agents_mentioned": ["@Dev", "@QA"],
  "agents_responding": ["@Dev"]
}
```

---

### 4. `vetka_read_group_messages`

Read messages from a group chat, optionally filtered by agent.

**Endpoint:** `GET /api/debug/mcp/groups/{group_id}/messages`

**Tool Schema:**
```json
{
  "name": "vetka_read_group_messages",
  "description": "Read messages from orchestration group chat. Useful for understanding conversation context and agent responses.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "group_id": {
        "type": "string",
        "description": "Group UUID"
      },
      "limit": {
        "type": "integer",
        "description": "Maximum messages to return (default: 20, max: 100)",
        "default": 20,
        "minimum": 1,
        "maximum": 100
      },
      "since_id": {
        "type": "string",
        "description": "Optional: Only return messages after this message ID (for polling)"
      },
      "sender_filter": {
        "type": "string",
        "description": "Optional: Filter by sender (e.g., '@Dev', 'user')"
      }
    },
    "required": ["group_id"]
  }
}
```

**Response:**
```json
{
  "group_id": "609c0d9a-b5bc-426b-b134-d693023bdac8",
  "group_name": "80 фаза",
  "participants": [
    {
      "agent_id": "@PM",
      "display_name": "PM",
      "role": "admin",
      "model_id": "anthropic/claude-opus-4.5"
    },
    {
      "agent_id": "@Dev",
      "display_name": "Dev",
      "role": "worker",
      "model_id": "mcp/claude_code"
    }
  ],
  "messages": [
    {
      "id": "msg-001",
      "sender_id": "@Dev",
      "content": "I've analyzed the code and found 3 issues",
      "message_type": "response",
      "created_at": "2026-01-23T10:30:15.123456",
      "mentions": ["@PM", "@QA"]
    },
    {
      "id": "msg-002",
      "sender_id": "user",
      "content": "Great! @Dev can you implement the fixes?",
      "message_type": "chat",
      "created_at": "2026-01-23T10:31:45.234567",
      "mentions": ["@Dev"]
    }
  ],
  "message_count": 2,
  "total_messages_in_group": 15
}
```

---

## IMPLEMENTATION CHECKLIST

### Phase 1: Create Tool Files
- [ ] `src/mcp/tools/group_tools.py` - Create new file with all 4 tools
  - [ ] `CreateGroupTool` class (extends `BaseMCPTool`)
  - [ ] `AddAgentToGroupTool` class
  - [ ] `SendToGroupTool` class
  - [ ] `ReadGroupMessagesTool` class

### Phase 2: Register Tools in MCP Bridge
- [ ] Update `src/mcp/vetka_mcp_bridge.py`
  - [ ] Add 4 new `Tool()` entries to `list_tools()` (around line 177)
  - [ ] Update tool count in docstring (currently "8 tools")
  - [ ] Add handlers in `call_tool()` function for execution

### Phase 3: Testing
- [ ] Test `vetka_create_group` via Claude Code
- [ ] Test `vetka_add_agent_to_group` with multiple agents
- [ ] Test `vetka_send_to_group` with @mentions
- [ ] Test `vetka_read_group_messages` with filters
- [ ] Verify messages are saved to `data/groups.json`
- [ ] Verify agents are triggered correctly on @mentions

### Phase 4: Documentation
- [ ] Update `.claude-mcp-config.md` with new tools
- [ ] Add examples to `HAIKU_A_QUICK_REFERENCE.md`
- [ ] Document @ mention syntax and agent naming conventions

---

## BENEFITS FOR CLAUDE CODE

**Before (Manual REST Calls):**
```python
# Claude Code had to construct HTTP requests manually
response = await client.post("/api/groups", json={
    "name": "My Group",
    "admin_agent_id": "@pm",
    "admin_model_id": "gpt-4",
    "initial_agents": [...]
})
```

**After (Native MCP Tools):**
```python
# Claude Code can use MCP tools naturally
result = call_tool("vetka_create_group", {
    "name": "My Group",
    "admin_agent_id": "@pm",
    "admin_model_id": "anthropic/claude-opus-4.5",
    "initial_agents": [
        {"agent_id": "@dev", "model_id": "mcp/claude_code", "display_name": "Dev"}
    ]
})
```

**Use Cases:**
1. **Orchestration:** "Create a group for Phase 80 refactoring with PM, Dev, QA, Architect"
2. **Workflow Automation:** "Iterate through files and send each to @code_review group"
3. **Team Coordination:** "Brief @dev and @qa on new requirements, wait for their responses"
4. **Status Reporting:** "Summarize conversation from last hour's @planning group"
5. **Cross-Project Work:** "Create group linking Claude Code with Browser Haiku for testing"

---

## COMPATIBILITY NOTES

- **Backwards Compatible:** Existing REST API endpoints remain unchanged
- **No Database Changes:** Uses existing `data/groups.json` persistence
- **No Service Changes:** Wraps existing `GroupChatManager` methods
- **SocketIO Compatible:** Messages trigger real-time updates in frontend
- **Agent Routing:** Respects Phase 80.28 smart reply decay for MCP agents

---

## SUMMARY

| Tool | Endpoint | Purpose | Status |
|------|----------|---------|--------|
| `vetka_create_group` | POST /api/groups | Create group with initial agents | PROPOSED |
| `vetka_add_agent_to_group` | POST /api/groups/{id}/participants | Add agents to existing group | PROPOSED |
| `vetka_send_to_group` | POST /api/debug/mcp/groups/{id}/send | Send message (with @mentions) | PROPOSED |
| `vetka_read_group_messages` | GET /api/debug/mcp/groups/{id}/messages | Read conversation history | PROPOSED |

**Total New Tools:** 4
**Implementation Effort:** ~200 lines of code
**Complexity:** Low (wraps existing service layer)
**Ready for:** Immediate implementation after review
