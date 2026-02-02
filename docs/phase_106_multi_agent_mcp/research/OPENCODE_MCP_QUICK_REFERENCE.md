# Opencode MCP Integration - Quick Reference
## Phase 106 Multi-Agent MCP Research Summary

**Research Date:** 2026-02-02
**Status:** Complete

---

## TL;DR: Key Findings

| Question | Answer | Details |
|----------|--------|---------|
| **Does Opencode support MCP?** | ❌ NO | It's a UI component, not an MCP server |
| **How does VETKA solve this?** | HTTP Bridge | REST API wrapper around MCP tools |
| **Python stdio MCP support?** | ⏸️ Indirect | Via HTTP wrapper (not direct stdio) |
| **Configuration needed?** | ✅ Minimal | Just set `OPENCODE_BRIDGE_ENABLED=true` |
| **Current status?** | ✅ Working | Phase 95.6 bridge unification complete |

---

## Quick Facts

### Opencode (sst/opencode)
```
Type:       UI Component (Monaco Editor wrapper)
Language:   TypeScript/JavaScript
Support:    HTTP REST only, NO native MCP
Repository: https://github.com/sst/opencode
```

### VETKA's Bridge Solution
```
Type:       FastAPI HTTP Server
Location:   src/opencode_bridge/
Status:     Active (Phase 95.6+)
Endpoints:  18+ VETKA tools via REST API
```

---

## Configuration (TL;DR)

### Minimal Setup
```bash
# 1. Set environment variable
export OPENCODE_BRIDGE_ENABLED=true

# 2. Start VETKA server
python main.py

# 3. Test bridge
curl http://localhost:5001/api/bridge/openrouter/health
```

### For MCP Tools
```bash
# HTTP transport (Phase 106+)
python run_mcp.py --http --port 5002

# Test tool execution
curl -X POST http://localhost:5002/mcp/invoke \
  -H "Content-Type: application/json" \
  -d '{"tool": "vetka_read_file", "args": {"path": "/file"}}'
```

---

## Current Bridge Endpoints

### OpenRouter Model Calls
```
GET  /api/bridge/openrouter/health     ← Server alive?
GET  /api/bridge/openrouter/keys       ← Available keys
POST /api/bridge/openrouter/invoke     ← Call model
GET  /api/bridge/openrouter/stats      ← Key rotation stats
```

### VETKA Tools (Phase 95.6+)
```
GET  /search/semantic                  ← Search knowledge base
POST /files/read                        ← Read file content
POST /files/edit                        ← Edit/create file
GET  /tree/structure                    ← Project tree
POST /git/commit                        ← Git commit
POST /model/call                        ← Call any LLM
... and 12+ more tools
```

---

## Phase 106 Roadmap

### What's Coming

1. **WebSocket Transport** (Priority: HIGH)
   - Real-time bidirectional communication
   - Better for long-running tasks
   - Endpoint: `/api/mcp/ws`

2. **MCPActor Pool** (Priority: HIGH)
   - Support 100+ concurrent agents
   - Per-session isolation
   - Mailbox pattern execution

3. **Provider Semaphores** (Priority: MEDIUM)
   - Per-model rate limiting
   - Grok: 10, Haiku: 50, Claude: 20
   - Backpressure signaling

4. **User Session Isolation** (Priority: MEDIUM)
   - Multi-user support
   - Separate Qdrant namespaces
   - Audit trails per user

---

## Why NOT Implement MCP in Opencode

### Problem with Direct MCP
```
Opencode MCP Server (Not Feasible)
├─ Opencode is UI-only component ❌
├─ No server logic capabilities ❌
├─ Would duplicate MCP implementation ❌
└─ Session management complexity ❌
```

### VETKA's Better Approach
```
Opencode UI ──HTTP──▶ FastAPI Bridge
                        │
                        ├─▶ MCP Tools (Python)
                        ├─▶ Key Manager
                        ├─▶ Provider Registry
                        └─▶ Session Manager
```

**Advantages:**
✅ Clean separation of concerns
✅ Leverages existing VETKA infrastructure
✅ Easier session/user management
✅ Better for concurrent agents

---

## Common Use Cases

### Use Case 1: Opencode Calls VETKA Tool
```bash
# Opencode UI makes HTTP request
curl -X POST http://localhost:5001/api/files/read \
  -d '{"file_path": "/path/to/file"}'

# Response
{
  "success": true,
  "result": "file content..."
}
```

### Use Case 2: Model Invocation with Key Rotation
```bash
# Opencode requests model response
curl -X POST http://localhost:5001/api/bridge/openrouter/invoke \
  -d '{
    "model_id": "deepseek/deepseek-chat",
    "messages": [{"role": "user", "content": "help"}]
  }'

# Bridge handles:
# 1. Select available key (automatic rotation)
# 2. Call OpenRouter
# 3. Return response
# 4. Track usage
```

### Use Case 3: Multi-Agent Workflow (Phase 106+)
```bash
# Client 1: PM Agent
# Connects via WebSocket: /api/mcp/ws?session_id=pm_agent_1

# Client 2: Dev Agent
# Connects via WebSocket: /api/mcp/ws?session_id=dev_agent_1

# Each has:
# ✅ Isolated state (MCPActor)
# ✅ Mailbox message queue
# ✅ Rate-limited execution
# ✅ User isolation
```

---

## Troubleshooting

### Bridge Not Responding?
```bash
# 1. Check environment variable
echo $OPENCODE_BRIDGE_ENABLED  # Should be "true"

# 2. Check VETKA server
curl http://localhost:5001/api/health

# 3. Check bridge specifically
curl http://localhost:5001/api/bridge/openrouter/health
```

### All Keys Rate-Limited?
```bash
# Check key status
curl http://localhost:5001/api/bridge/openrouter/stats

# Add new keys to data/config.json
# They auto-rotate every 24h after rate limit
```

### Tool Execution Timeout?
```bash
# Phase 106 will solve this with actor pools
# Current: Sequential execution limits to 1 client

# Workaround: Use multiple VETKA instances on different ports
python main.py --port 5002
python main.py --port 5003
```

---

## Files to Know

### Core Bridge Files
```
src/opencode_bridge/
├── __init__.py                    ← Package init
├── routes.py                      ← FastAPI endpoints
├── open_router_bridge.py          ← OpenRouter integration
└── multi_model_orchestrator.py    ← Model chaining
```

### MCP Server Files (Phase 106)
```
src/mcp/
├── vetka_mcp_server.py           ← HTTP transport
├── mcp_actor.py                  ← (NEW) Actor pool
└── client_pool.py                ← (NEW) Connection pooling
```

### Documentation
```
docs/phase_106_multi_agent_mcp/research/
├── OPENCODE_MCP_RESEARCH.md           ← Full research (this)
├── OPENCODE_MCP_QUICK_REFERENCE.md    ← Quick ref (you are here)
└── (other phase docs)
```

---

## Success Criteria

### Phase 95.6 (Current - COMPLETE ✅)
- [x] OpenCode bridge implemented
- [x] 18 VETKA tools accessible via REST
- [x] Key rotation working
- [x] Multi-model support

### Phase 106 (In Progress)
- [ ] WebSocket transport (100+ agents)
- [ ] MCPActor pool with mailbox pattern
- [ ] Per-provider rate limiting
- [ ] User session isolation
- [ ] Metrics and monitoring

---

## Next Steps

1. **Review full research** → `OPENCODE_MCP_RESEARCH.md`
2. **Implement WebSocket** → Phase 106a (1-2 hours)
3. **Create MCPActor** → Phase 106b (2-3 hours)
4. **Add provider semaphores** → Phase 106d (1-2 hours)
5. **Test concurrent agents** → Phase 106e (2+ hours)

---

**Document Version:** 1.0
**Last Updated:** 2026-02-02
**For More Details:** See OPENCODE_MCP_RESEARCH.md

