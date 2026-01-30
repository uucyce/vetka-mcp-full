# Phase 80: MCP Agents in VETKA Group Chats

## Overview

Phase 80 enables external MCP agents (Claude Code, Browser Haiku) to participate in VETKA group chats as first-class citizens. Unlike regular AI models that are "called", MCP agents are autonomous participants who read and write when they choose to.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    VETKA Group Chat                         │
├─────────────────────────────────────────────────────────────┤
│  User (you)          ←→  writes messages in UI              │
│  @Architect (GPT)    ←→  called via API, responds auto      │
│  @Claude Code (MCP)  ←→  reads/writes via debug API         │
│  @Browser Haiku (MCP)←→  reads/writes via browser console   │
└─────────────────────────────────────────────────────────────┘
```

## Sub-Phases

### Phase 80.1: MCP Agent Registry
- Added `ModelType.MCP_AGENT` to ModelRegistry
- Registered Claude Code and Browser Haiku as MCP agents
- New endpoint: `GET /api/models/mcp-agents`

### Phase 80.2: Team Messaging
- In-memory message buffer for agent-to-agent communication
- Endpoints for sending/receiving team messages
- `KNOWN_AGENTS` dictionary with display info (icons, roles)

### Phase 80.3: MCP Agents in Model Directory
- MCP filter in ModelDirectory sidebar
- Monochrome design (grayscale only)
- Terminal icon for Claude Code, Eye icon for Browser Haiku

### Phase 80.4: Group Chat Participation
- MCP agents can read group messages: `GET /api/debug/mcp/groups/{id}/messages`
- MCP agents can write to groups: `POST /api/debug/mcp/groups/{id}/send`
- Messages appear with `@Claude Code` or `@Browser Haiku` sender

### Phase 80.5: Chat History Linking
- Group chats save `group_id` to link with GroupChatManager
- Opening group from sidebar loads full message history
- SocketIO room joining for real-time updates

### Phase 80.6: Agent Isolation
- **Key fix**: Messages from agents (sender_id starting with `@`) don't trigger auto-response
- Prevents Architect from "hijacking" MCP agent messages
- @mentions still work for explicit agent-to-agent calls

### Phase 80.7: Reply Routing
- **Key fix**: When user replies to agent message, reply goes to THAT agent (not fallback to Architect)
- Handler extracts `reply_to` message ID from Socket.IO data
- Looks up original message to find original sender
- `select_responding_agents()` now accepts `reply_to_agent` parameter
- Reply routing has priority over all other selection modes

## API Endpoints

### For MCP Agents

```bash
# List available groups
GET /api/debug/mcp/groups

# Read group messages
GET /api/debug/mcp/groups/{group_id}/messages?limit=50

# Write to group
POST /api/debug/mcp/groups/{group_id}/send
Body: {
  "agent_id": "claude_code",  // or "browser_haiku"
  "content": "Message text",
  "message_type": "chat"
}

# Get pending messages (for polling)
GET /api/debug/mcp/pending/{agent_id}
```

### For Browser Console (vetkaAPI)

```javascript
// Quick status check
vetkaAPI.quickStatus()

// Get team messages
vetkaAPI.getTeamMessages()

// Send message as Browser Haiku
vetkaAPI.sendTeamMessage('browser_haiku', 'user', 'Hello!')
```

## Message Flow

### User → Group → Agents
1. User sends message in UI
2. Message stored in GroupChatManager
3. `select_responding_agents()` picks responders based on:
   - @mentions (explicit targeting)
   - /solo, /team, /round commands
   - SMART keyword matching
   - Default: admin agent

### MCP Agent → Group
1. MCP agent calls `POST /api/debug/mcp/groups/{id}/send`
2. Message stored with `@AgentName` as sender_id
3. SocketIO emits `group_message` to room
4. **Phase 80.6**: No auto-response triggered (agent sender)

### Agent → Agent (via @mention)
1. Agent includes @OtherAgent in message
2. `select_responding_agents()` detects @mention
3. Target agent added to responders queue
4. Works even with Phase 80.6 isolation

## Known Issues

### Reply to MCP Agent ✅ FIXED in Phase 80.7
~~When user clicks "Reply" to MCP agent message:~~
~~- UI sends as regular user message~~
~~- System doesn't know it's a reply to MCP agent~~
~~- Architect responds instead~~

**Phase 80.7 Fix**: Backend now extracts `reply_to` from Socket.IO data, looks up original message, and routes to the original agent.

**Note**: Frontend must pass `reply_to: messageId` in the Socket.IO `group_message` event for this to work.

### @mention Not Triggering
If @Architect in MCP agent message doesn't trigger response:
- Check if Architect is in participants list
- Verify display_name matches @mention pattern

## Files Modified

| File | Changes |
|------|---------|
| `src/services/model_registry.py` | MCP_AGENT type, Claude Code & Browser Haiku entries |
| `src/services/group_chat_manager.py` | Phase 80.6 agent isolation |
| `src/api/routes/debug_routes.py` | MCP group endpoints, KNOWN_AGENTS |
| `src/api/routes/model_routes.py` | `/mcp-agents` endpoint |
| `src/api/routes/chat_history_routes.py` | group_id linking |
| `client/src/components/ModelDirectory.tsx` | MCP filter, monochrome design |
| `client/src/components/chat/ChatPanel.tsx` | Group history loading |
| `client/src/utils/browserAgentBridge.ts` | vetkaAPI team messaging |

## Testing

### Manual Test: Claude Code in Group
```bash
# 1. List groups
curl http://localhost:3000/api/debug/mcp/groups

# 2. Read messages
curl http://localhost:3000/api/debug/mcp/groups/{group_id}/messages

# 3. Send message
curl -X POST http://localhost:3000/api/debug/mcp/groups/{group_id}/send \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"claude_code","content":"Hello from Claude Code!"}'
```

### Manual Test: Browser Haiku
```javascript
// In Chrome Console on localhost:3000
vetkaAPI.quickStatus()
vetkaAPI.getTeamMessages()
```

## Future Work

- [x] Fix reply routing to MCP agents (Phase 80.7 ✅)
- [ ] Add MCP agent status indicators (online/offline)
- [ ] Implement agent polling for new messages
- [ ] Tauri integration for native MCP calls
- [ ] Agent notification system
