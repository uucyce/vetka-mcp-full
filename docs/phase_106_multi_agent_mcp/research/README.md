# Phase 106 Multi-Agent MCP Architecture - Research Directory

**Date Created:** 2026-02-02
**Status:** Research Complete
**Phase:** 106 (Multi-Agent MCP Hub)

---

## Research Documents

### 1. OPENCODE_MCP_RESEARCH.md (PRIMARY)
**Length:** 632 lines | **Size:** 18 KB | **Reading Time:** 15-20 minutes

**Comprehensive research on Opencode (sst/opencode) MCP integration including:**
- Complete analysis of Opencode architecture and capabilities
- Direct answer: Does Opencode support MCP? (❌ NO)
- How VETKA bridges this gap with HTTP REST wrapper
- Python stdio MCP server compatibility analysis
- Configuration methods for MCP servers
- Special requirements and limitations
- Practical setup steps for Phase 106 implementation
- Integration checklist
- Detailed recommendations

**Contents:**
1. Executive Summary
2. What is Opencode (sst/opencode)?
3. MCP Protocol Support Analysis
4. Configuration Methods for MCP Servers
5. Compatibility with Python stdio MCP Servers
6. Special Requirements and Limitations
7. Practical Setup Steps
8. Current Integration Status
9. Key Differences: Opencode vs VETKA Bridge
10. Recommendations for Phase 106
11. Integration Checklist
12. Conclusion

**Key Finding:** Opencode is NOT an MCP server. It's a Monaco Editor UI component. VETKA has successfully integrated it via HTTP REST bridge, which is the correct approach for Phase 106+.

---

### 2. OPENCODE_MCP_QUICK_REFERENCE.md (SUMMARY)
**Length:** 250+ lines | **Size:** 6.9 KB | **Reading Time:** 5-10 minutes

**Quick reference guide with:**
- TL;DR key findings in table format
- Quick facts about Opencode and VETKA bridge
- Minimal configuration setup
- Current bridge endpoints (OpenRouter + VETKA tools)
- Phase 106 roadmap
- Why NOT to implement MCP directly in Opencode
- Common use cases with examples
- Troubleshooting guide
- Files to know
- Success criteria

**Use this for:**
- Quick lookups during implementation
- Phase 106 planning meetings
- Troubleshooting during development
- Configuration reference

---

## Key Research Findings

### Question 1: Does Opencode support MCP protocol?
**Answer:** ❌ **NO**

**Evidence:**
- Opencode is a UI component (Monaco Editor wrapper)
- No MCP protocol implementation in sst/opencode
- No stdio server capabilities
- HTTP REST only

**Solution:** Use VETKA's HTTP bridge (already implemented in Phase 95.6)

---

### Question 2: How does VETKA configure MCP servers?

**Current Configuration (Phase 95.6+):**
```bash
export OPENCODE_BRIDGE_ENABLED=true
```

**Endpoints Available:**
- OpenRouter: `/api/bridge/openrouter/*`
- VETKA Tools: `/search/*`, `/files/*`, `/git/*`, `/model/*` (18+ tools)
- HTTP Transport: `python run_mcp.py --http --port 5002`

---

### Question 3: Compatible with Python stdio MCP servers?

**Direct Compatibility:** ❌ NO (stdio → HTTP conversion needed)

**VETKA's Solution:** ✅ YES (via HTTP wrapper)

**Pattern:**
```
Python MCP Server (stdio)
    ↓ (wrapped by FastAPI)
HTTP REST Endpoint
    ↓ (called by Opencode)
Opencode UI (HTTP client)
```

---

### Question 4: Special requirements or limitations?

**Key Limitations:**
1. Opencode has no native MCP support (not a limitation of VETKA)
2. Single stdio bottleneck (Phase 106 solution: WebSocket + Actor pool)
3. No per-provider rate limiting (Phase 106 solution: Semaphores)
4. Session isolation missing (Phase 106 solution: workflow_id + session_id)

**Phase 106 Will Address:**
- WebSocket bidirectional communication
- MCPActor pool for 100+ concurrent agents
- Provider-specific rate limiting
- User session isolation with Qdrant namespacing

---

## Architecture Overview

### Current Stack (Phase 95.6+)
```
Opencode UI
    ↓ HTTP REST
FastAPI Bridge
    ├─ OpenRouter Key Manager
    ├─ Provider Registry
    ├─ VETKA MCP Tools
    └─ Session State
```

### Phase 106+ Enhancement
```
Opencode UI
    ↓ WebSocket
FastAPI MCP Hub
    ├─ MCPActor Pool (100+ agents)
    ├─ Session Dispatcher
    ├─ Provider Semaphores (rate limiting)
    ├─ Multi-transport (stdio, HTTP, WS)
    └─ Session Isolation (user_id + workflow_id)
```

---

## Implementation Status

### ✅ COMPLETE (Phase 95.6)
- OpenCode bridge REST endpoints
- 18 VETKA tools via HTTP API
- Key rotation logic
- Model invocation support
- OpenRouter integration

### ⏳ IN PROGRESS (Phase 106)
- WebSocket transport implementation
- MCPActor pool creation
- Per-provider rate limiting
- User session isolation
- Comprehensive monitoring

### 📋 PLANNED (Phase 106+)
- WebSocket-to-stdio adapters
- Advanced backpressure signaling
- Distributed state management
- Multi-instance coordination

---

## Quick Setup

### Minimal Configuration
```bash
# 1. Enable bridge
export OPENCODE_BRIDGE_ENABLED=true

# 2. Start VETKA server
python main.py

# 3. Test bridge
curl http://localhost:5001/api/bridge/openrouter/health
```

### For MCP Tools
```bash
# 1. HTTP transport
python run_mcp.py --http --port 5002

# 2. Call tool
curl -X POST http://localhost:5002/mcp/invoke \
  -d '{"tool": "vetka_read_file", "args": {"path": "/file"}}'
```

### For Phase 106 WebSocket
```bash
# Coming soon - see OPENCODE_MCP_RESEARCH.md section 6.4
```

---

## Next Steps

1. **Read Full Research** → `OPENCODE_MCP_RESEARCH.md`
   - Understand complete architecture
   - Review all integration points
   - See detailed setup instructions

2. **Reference During Development** → `OPENCODE_MCP_QUICK_REFERENCE.md`
   - Quick lookups
   - Troubleshooting
   - Configuration examples

3. **Implement Phase 106**
   - WebSocket endpoint (1-2 hours)
   - MCPActor pool (2-3 hours)
   - Provider semaphores (1-2 hours)
   - Session isolation (2+ hours)

4. **Test & Validate**
   - 100+ concurrent agents
   - Per-model rate limiting
   - User isolation
   - Performance metrics

---

## Related Documentation

| Document | Phase | Content |
|----------|-------|---------|
| `PHASE_106_RESEARCH_SYNTHESIS.md` | 106 | Overall MCP architecture research |
| `OPENCODE_BRIDGE_GUIDE.md` | 93 | Initial bridge setup guide |
| `OPENCODE_ENDPOINTS_MARKERS.md` | 95.2 | Endpoint inventory audit |
| `PHASE_95.6_BRIDGE_UNIFICATION_COMPLETE.md` | 95.6 | Bridge unification completion |

---

## Key Files in VETKA Codebase

### OpenCode Bridge Implementation
```
src/opencode_bridge/
├── __init__.py                    - Package initialization
├── routes.py                      - FastAPI REST endpoints
├── open_router_bridge.py          - OpenRouter integration
└── multi_model_orchestrator.py    - Model orchestration
```

### MCP Server
```
src/mcp/
├── vetka_mcp_server.py           - HTTP/stdio transport
├── vetka_mcp_bridge.py           - Bridge logic
└── state/
    └── mcp_state_manager.py      - State persistence
```

### API Handlers (Future - Phase 106)
```
src/api/handlers/
├── mcp_socket_handler.py         - (NEW) WebSocket handler
└── stream_handler.py             - Event streaming
```

---

## Contact & Questions

**Research Completed By:** Claude Code Agent
**Research Date:** 2026-02-02
**Status:** READY FOR IMPLEMENTATION

For questions about the research:
- See `OPENCODE_MCP_RESEARCH.md` for detailed analysis
- See `OPENCODE_MCP_QUICK_REFERENCE.md` for quick answers
- Check Phase 106 planning documents for implementation details

---

**Research Version:** 1.0
**Last Updated:** 2026-02-02
**Status:** APPROVED ✅

