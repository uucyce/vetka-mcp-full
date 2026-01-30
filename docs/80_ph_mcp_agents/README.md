# MCP Agents Quick Start

## What are MCP Agents?

MCP (Model Context Protocol) agents are **external AI assistants** that participate in VETKA group chats:

| Agent | Icon | Role | Interface |
|-------|------|------|-----------|
| Claude Code | Terminal | Executor | MCP in terminal |
| Browser Haiku | Eye | Tester | Chrome Console |

Unlike regular AI models (Architect, Dev, QA), MCP agents are **not called** - they **read and write when online**.

## For Claude Code

```bash
# Check available groups
python3 -c "
import requests
r = requests.get('http://localhost:3000/api/debug/mcp/groups')
print(r.json())
"

# Read group messages
python3 -c "
import requests
group_id = 'YOUR_GROUP_ID'
r = requests.get(f'http://localhost:3000/api/debug/mcp/groups/{group_id}/messages')
for m in r.json().get('messages', []):
    print(f\"[{m['sender_id']}]: {m['content'][:80]}...\")
"

# Write to group
python3 -c "
import requests
group_id = 'YOUR_GROUP_ID'
r = requests.post(
    f'http://localhost:3000/api/debug/mcp/groups/{group_id}/send',
    json={'agent_id': 'claude_code', 'content': 'Hello from Claude Code!'}
)
print(r.json())
"
```

## For Browser Haiku

Open Chrome Console on `localhost:3000` and use:

```javascript
// Check everything
vetkaAPI.quickStatus()

// Read team messages
vetkaAPI.getTeamMessages()

// Send message
vetkaAPI.sendTeamMessage('browser_haiku', 'user', 'Testing from Browser Haiku')
```

## Key Behaviors

### Phase 80.6: Agent Isolation
- When MCP agent sends message → other agents DON'T auto-respond
- This prevents Architect from "hijacking" the conversation
- Use @mentions for explicit agent-to-agent calls

### @Mentions
- `@Architect` → calls Architect specifically
- `@Dev` → calls Dev agent
- Works from any sender (user or agent)

### Reply to MCP Agent
**Known issue**: UI reply goes to Architect instead of MCP agent.
Workaround: MCP agents check `/api/debug/mcp/pending/{agent_id}` for messages.

## Files

- `PHASE_80_MCP_AGENTS.md` - Full documentation
- This README - Quick start guide
