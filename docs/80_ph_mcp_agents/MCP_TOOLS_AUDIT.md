# MCP TOOLS AUDIT REPORT
**Phase 65.2 + Phase 80.16+ Group Chat Integration**

Generated: 2026-01-23 | Status: PRODUCTION

---

## INVENTORY: ALL VETKA MCP TOOLS

### READ-ONLY TOOLS (8) ✅ WORKING
Status: All operational, REST API bridge to VETKA server on localhost:5001

| Tool | Status | Description | Use Case |
|------|--------|-------------|----------|
| `vetka_search_semantic` | ✅ | Vector search via Qdrant | Find code by semantic meaning |
| `vetka_read_file` | ✅ | Read file contents | Access project files |
| `vetka_get_tree` | ✅ | Project tree structure | Understand codebase layout |
| `vetka_health` | ✅ | Server health check | Verify VETKA running |
| `vetka_list_files` | ✅ | List files with filtering | Browse directories |
| `vetka_search_files` | ✅ | Ripgrep-based file search | Full-text search |
| `vetka_get_metrics` | ✅ | System metrics/analytics | Monitor performance |
| `vetka_get_knowledge_graph` | ✅ | Knowledge graph relationships | Understand dependencies |

### WRITE/ACTION TOOLS (6) ✅ WORKING
Status: All operational, direct Python tool execution or REST bridge

| Tool | Status | Description | Requires |
|------|--------|-------------|----------|
| `vetka_edit_file` | ✅ | Create/modify files | dry_run flag (default=true) |
| `vetka_git_commit` | ✅ | Create git commits | dry_run flag (default=true) |
| `vetka_run_tests` | ✅ | Execute pytest tests | dry_run flag (default=true) |
| `vetka_camera_focus` | ✅ | Control 3D camera | Requires VETKA UI session |
| `vetka_git_status` | ✅ | Check git status | None |
| `vetka_call_model` | ✅ | Call LLM models | Model ID (grok-4, gpt-4o, claude-opus-4-5, etc) |

**Total: 14 tools | All operational**

---

## GROUP CHAT MESSAGING SYSTEM
### Phase 80.13-80.28 MCP @Mention Routing + Group Orchestration

### ENDPOINT FOR GROUP CHAT MESSAGES

#### For MCP Agents (Claude Code, Browser Haiku)

**Read Messages:**
```
GET /api/debug/mcp/groups/{group_id}/messages
Query params:
  - limit: int (default 50) - Number of messages
  - since_id: str (optional) - Get messages after this ID

Response:
{
  "group_id": "uuid",
  "group_name": "Project Alpha",
  "participants": [
    {
      "agent_id": "@Dev",
      "display_name": "Developer",
      "role": "Dev",
      "model_id": "gpt-4o"
    }
  ],
  "messages": [...],
  "message_count": 42
}
```

**Send Message:**
```
POST /api/debug/mcp/groups/{group_id}/send
Content-Type: application/json

Body:
{
  "agent_id": "claude_code",        // "claude_code" or "browser_haiku"
  "content": "Your message here",   // Message text
  "message_type": "chat"             // chat, response, or system
}

Response:
{
  "message": {
    "id": "msg-uuid",
    "group_id": "group-uuid",
    "sender_id": "@Claude Code",
    "content": "Your message here",
    "timestamp": 1674432000,
    "message_type": "chat"
  }
}
```

#### For Regular REST API (Standard group endpoints)

**Send Message via REST:**
```
POST /api/groups/{group_id}/messages
Content-Type: application/json

Body:
{
  "sender_id": "@MyAgent",      // Agent ID
  "content": "Message text",    // Message text
  "message_type": "chat"         // chat, response, system
}
```

---

### HOW TO GET group_id

#### Option 1: List all groups
```
GET /api/groups

Response:
{
  "groups": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Project Alpha",
      "admin": "@PM",
      "participants_count": 5,
      "created_at": 1674432000
    }
  ]
}
```

#### Option 2: Create a new group
```
POST /api/groups
Content-Type: application/json

Body:
{
  "name": "New Team",
  "description": "Project collaboration",
  "admin_agent_id": "@claude_code",
  "admin_model_id": "mcp/claude_code",
  "admin_display_name": "Claude Code"
}

Response:
{
  "group": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "New Team",
    ...
  }
}
```

#### Option 3: Get from environment/config
Groups are stored in `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/groups.json`

```json
{
  "550e8400-e29b-41d4-a716-446655440000": {
    "name": "Project Alpha",
    "participants": {...}
  }
}
```

---

## MESSAGE FORMAT

### Standard Message Structure (stored in group_chat_manager)
```python
{
  "id": "msg-uuid",
  "group_id": "group-uuid",
  "sender_id": "@AgentName",           # Agent identifier (starts with @)
  "content": "Message text",           # The actual message
  "timestamp": 1674432000,             # Unix timestamp
  "message_type": "chat",              # chat, response, system, error
  "mentions": ["@Dev", "@Architect"],  # Extracted from content
  "metadata": {                        # Optional metadata
    "mcp_agent": "claude_code",       # For MCP agent messages
    "icon": "terminal",               # Display icon
    "role": "Executor"                # Agent role
  }
}
```

### Special Features

**@Mentions in Content:**
- Format: `@AgentName` or `@browser_haiku` or `@claude_code`
- Phase 80.13: @mentions trigger automatic agent responses
- MCP agents (browser_haiku, claude_code) get special handling via `notify_mcp_agents()`

**Smart Reply Decay (Phase 80.28):**
- Tracks `last_responder_id` and `last_responder_decay` on Group object
- User messages: +1 decay
- MCP agent messages: +1 decay
- Resets when any agent successfully responds

---

## SOCKET.IO REAL-TIME EVENTS

### Broadcasting to Group Room
All events emitted to room: `group_{group_id}`

```javascript
// Join a group room (client-side)
socket.emit('join_group', {group_id: 'uuid'});

// Send a message
socket.emit('group_message', {
  group_id: 'uuid',
  sender_id: 'user',
  content: 'Hello @Dev'
});

// Listen for messages
socket.on('group_message', (msg) => {
  console.log(msg.sender_id, msg.content);
});

// Listen for agent responses (streaming)
socket.on('group_stream_start', (data) => {
  console.log('Agent starting:', data.agent_id);
});
socket.on('group_stream_end', (data) => {
  console.log('Agent response:', data.full_message);
});

// Typing indicator
socket.on('group_typing', (data) => {
  console.log(data.agent_id, 'is typing...');
});
```

---

## KEY CONFIGURATIONS

### Environment Detection
- **Transport types:** stdio, HTTP, SSE
- **Default port (REST):** 5001 (VETKA API)
- **MCP Console port:** 5002 (logging)
- **HTTP MCP server port:** 5002 (when run with --http)
- **SSE MCP server port:** 5003 (when run with --sse)

### Model Support for vetka_call_model
Models tested and working:
- **Grok:** grok-4 (via x.ai/OpenRouter)
- **Claude:** claude-opus-4-5, claude-3-sonnet (via Anthropic)
- **GPT:** gpt-4o, gpt-4-turbo (via OpenAI)
- **Gemini:** gemini-2.0-flash (via Google)
- **DeepSeek:** deepseek-r1:free, deepseek-chat (via OpenRouter)
- **Local/Ollama:** llama3.1:8b, qwen2:7b

---

## FILE STRUCTURE

### MCP Implementation
```
/src/mcp/
  ├── vetka_mcp_bridge.py           # Phase 65.1 - Main bridge (8 tools read-only)
  ├── vetka_mcp_server.py           # Phase 65.2 - Multi-transport wrapper
  ├── stdio_server.py               # Stdio transport implementation
  ├── rate_limiter.py               # API rate limiting
  ├── memory_transfer.py            # Elisya context transfer
  └── tools/
      ├── base_tool.py              # Base class for all tools
      ├── read_file_tool.py         # File reading
      ├── edit_file_tool.py         # File editing with backups
      ├── git_tool.py               # Git operations
      ├── search_tool.py            # File/semantic search
      ├── tree_tool.py              # Tree structure
      ├── run_tests_tool.py         # Test execution
      ├── camera_tool.py            # 3D camera control
      ├── llm_call_tool.py          # LLM model calling
      ├── branch_tool.py            # Git branch ops
      ├── search_knowledge_tool.py   # Knowledge base search
      └── list_files_tool.py        # File listing
```

### Group Chat System
```
/src/api/
  ├── routes/
  │   ├── group_routes.py           # REST API for groups
  │   ├── debug_routes.py           # MCP endpoints for browser agents
  │   └── chat_history_routes.py    # Chat persistence
  ├── handlers/
  │   ├── group_message_handler.py  # Socket.IO handler (Phase 80.13+)
  │   ├── routing/
  │   │   └── hostess_router.py     # Intelligent group routing
  │   └── mention/
  │       └── mention_handler.py    # @mention parsing
  └── ...
```

### Data Storage
```
/data/
  ├── groups.json                   # Group definitions
  ├── chat_history.json             # Chat persistence
  ├── models_cache.json             # Available models
  └── watcher_state.json            # File watcher state
```

---

## TESTING GROUP CHAT

### Quick Test: Send message to group
```bash
# Get group_id first
curl http://localhost:5001/api/groups

# Send message as Claude Code MCP agent
curl -X POST http://localhost:5001/api/debug/mcp/groups/550e8400-e29b-41d4-a716-446655440000/send \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "claude_code",
    "content": "Testing message from Claude Code",
    "message_type": "chat"
  }'

# Read messages
curl http://localhost:5001/api/debug/mcp/groups/550e8400-e29b-41d4-a716-446655440000/messages
```

---

## KNOWN ISSUES / NOTES

### Phase 80.28: Smart Reply Chain
- MCP messages trigger automatic agent responses if they contain @mentions
- Use this to coordinate multi-agent workflows: Claude Code → @Dev → @QA

### Phase 80.13: Browser Agent Integration
- Browser extensions can listen to `mcp_mention` socket events
- Messages are also stored in `debug_routes.team_messages` buffer (max 100)

### Phase 80.16: MCP Message Broadcasting
- Messages sent via `/api/debug/mcp/groups/{group_id}/send` are:
  1. Stored in group message history
  2. Broadcasted via Socket.IO to all connected clients
  3. Can trigger @mentioned agents to respond

### Camera Focus Tool
- Requires active VETKA UI session
- Otherwise fails gracefully with "SocketIO not available" message

---

## SUMMARY

✅ **14 MCP tools** - All operational and tested
✅ **Group chat system** - Ready for multi-agent collaboration
✅ **@Mention routing** - Smart agent selection + MCP browser integration
✅ **Real-time sync** - Socket.IO for live updates
✅ **REST API** - Complete group management endpoints

**For sending messages to VETKA group chats from MCP agents:**
```
POST /api/debug/mcp/groups/{group_id}/send
{
  "agent_id": "claude_code",
  "content": "Message text",
  "message_type": "chat"
}
```

**To get group_id:**
```
GET /api/groups  # List all groups
```
