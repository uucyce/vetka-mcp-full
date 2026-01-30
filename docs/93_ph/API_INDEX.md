# VETKA Phase 93 API Documentation Index

## Overview

This directory contains comprehensive documentation for VETKA's API architecture and endpoints.

### Files in This Directory

#### 1. **API_QUICK_START.md** (Start Here!)
- Quick reference for common endpoints
- Example curl requests
- Key concepts explained
- Configuration tips
- **Best for:** Getting started quickly, finding common patterns

#### 2. **API_ENDPOINTS_REFERENCE.md** (Complete Reference)
- All 66+ REST endpoints documented
- Socket.IO events
- OpenCode Bridge endpoints
- MCP tool endpoints
- Service dependencies
- Error handling
- Configuration hierarchy
- **Best for:** Complete understanding, API integration, debugging

#### 3. **API_INDEX.md** (This File)
- Documentation navigation
- Summary of each document
- Quick links to sections

---

## API Statistics

| Category | Count | Routers |
|----------|-------|---------|
| Chat Endpoints | 3 | `chat_routes.py` |
| Config Endpoints | 12 | `config_routes.py` |
| Tree/KG Endpoints | 5 | `tree_routes.py` |
| Search Endpoints | 7 | `semantic_routes.py` |
| Files Endpoints | 4 | `files_routes.py` |
| Group Endpoints | 6 | `group_routes.py` |
| Model Registry | 8 | `model_routes.py` |
| Watcher Endpoints | 5 | `watcher_routes.py` |
| Health Endpoints | 4 | `health_routes.py` |
| Metrics Endpoints | 2 | `metrics_routes.py` |
| Debug Endpoints | 7 | `debug_routes.py` |
| **REST Total** | **63** | **11 routers** |
| Socket.IO Events | 15+ | Various handlers |
| OpenCode Bridge | 4 | `opencode_bridge/routes.py` |
| MCP Tools | 20+ | `src/mcp/` |

---

## Router Source Files

All route definitions are in `src/api/routes/`:

```
src/api/routes/
├── __init__.py                  # Router aggregator (get_all_routers)
├── chat_routes.py               # /api/chat/* (THE BIG ONE)
├── config_routes.py             # /api/config/*, /api/keys/*, /api/models
├── tree_routes.py               # /api/tree/*, /api/tree/knowledge-graph
├── semantic_routes.py           # /api/search/*, /api/semantic-tags/*, /api/scanner/*
├── files_routes.py              # /api/files/*
├── group_routes.py              # /api/groups/* (Phase 56)
├── model_routes.py              # /api/models/* (Phase 56)
├── watcher_routes.py            # /api/watcher/*
├── health_routes.py             # /api/health/* (Phase 43)
├── debug_routes.py              # /api/debug/* (Phase 80)
├── metrics_routes.py            # /api/metrics/*
├── chat_history_routes.py       # /api/chats/* (Phase 50)
├── knowledge_routes.py          # /api/knowledge-graph/*
├── ocr_routes.py                # /api/ocr/*
├── file_ops_routes.py           # /api/file/*
├── triple_write_routes.py       # /api/triple-write/*
├── workflow_routes.py           # /api/workflow/*
├── embeddings_routes.py         # /api/embeddings/*
├── eval_routes.py               # /api/eval/*
├── approval_routes.py           # /api/approval/*
└── mcp_console_routes.py        # /api/mcp-console/*
```

---

## Key Sections by Use Case

### For Users/Frontend Developers

1. **Chat & Interaction**
   - See: API_QUICK_START.md → "Simple Chat" pattern
   - Reference: API_ENDPOINTS_REFERENCE.md → "CHAT ENDPOINTS"
   - File: `chat_routes.py`

2. **Search & Discovery**
   - See: API_QUICK_START.md → "Semantic Search" pattern
   - Reference: API_ENDPOINTS_REFERENCE.md → "SEMANTIC SEARCH ENDPOINTS"
   - File: `semantic_routes.py`

3. **File Management**
   - See: API_QUICK_START.md → "File Operations"
   - Reference: API_ENDPOINTS_REFERENCE.md → "FILES ENDPOINTS"
   - File: `files_routes.py`

4. **3D Visualization**
   - See: API_QUICK_START.md → "Get Tree Visualization"
   - Reference: API_ENDPOINTS_REFERENCE.md → "TREE/KNOWLEDGE GRAPH ENDPOINTS"
   - File: `tree_routes.py`

### For Backend/System Developers

1. **API Architecture**
   - See: API_ENDPOINTS_REFERENCE.md → "ARCHITECTURAL PATTERNS"
   - Service flow diagrams
   - Dependency map

2. **Configuration Management**
   - See: API_QUICK_START.md → "Configuration Files"
   - Reference: API_ENDPOINTS_REFERENCE.md → "CONFIGURATION ENDPOINTS"
   - File: `config_routes.py`

3. **Health & Monitoring**
   - See: API_ENDPOINTS_REFERENCE.md → "HEALTH ENDPOINTS"
   - File: `health_routes.py`

4. **Error Handling**
   - See: API_ENDPOINTS_REFERENCE.md → "ERROR HANDLING"
   - All endpoints follow consistent patterns

### For MCP/Claude Code Integration

1. **MCP Tools**
   - See: API_ENDPOINTS_REFERENCE.md → "MCP TOOL ENDPOINTS"
   - Usage examples
   - Integration flow

2. **Team Messaging**
   - See: API_ENDPOINTS_REFERENCE.md → "DEBUG ENDPOINTS" → `team-messages`
   - MCP agent communication

3. **Chat Routing**
   - See: API_QUICK_START.md → "Advanced Usage" → "Group Chat"
   - Reference: `group_routes.py`

### For External Tool Integration

1. **OpenCode Bridge**
   - See: API_ENDPOINTS_REFERENCE.md → "OPENCODE BRIDGE ENDPOINTS"
   - Reference: `src/opencode_bridge/routes.py`

2. **Socket.IO Events**
   - See: API_ENDPOINTS_REFERENCE.md → "SOCKET.IO EVENTS"
   - Real-time updates
   - File: `src/api/handlers/connection_handlers.py`

---

## Feature Flags & Environment Variables

See **API_QUICK_START.md** → "Configuration Files" for complete list.

Key variables:
- `ELISYA_ENABLED`: Enable orchestrator
- `PARALLEL_MODE`: Parallel agent execution
- `HOSTESS_AVAILABLE`: Enable intelligent routing
- `API_GATEWAY_AVAILABLE`: Use API Gateway v2
- `MODEL_ROUTER_V2_AVAILABLE`: Use model router
- `QDRANT_AUTO_RETRY_AVAILABLE`: Save to Qdrant
- `OPENCODE_BRIDGE_ENABLED`: Enable OpenRouter bridge
- `VETKA_SEMANTIC_WEIGHT`: Hybrid search semantic weight
- `VETKA_KEYWORD_WEIGHT`: Hybrid search keyword weight
- `VETKA_RRF_K`: RRF smoothing constant
- `VETKA_HYBRID_CACHE_TTL`: Search cache TTL

---

## Common Integration Points

### Frontend (React/Vue)
- **Base URL:** `http://localhost:8000/api/`
- **WebSocket:** `http://localhost:8000` (Socket.IO)
- **Key Endpoints:** `/api/chat`, `/api/search/hybrid`, `/api/tree/data`

### Claude Code (MCP)
- **MCP Tool Definitions:** `src/mcp/vetka_mcp_bridge.py`
- **Available Tools:** 20+ (file ops, search, chat, scanning)
- **Response Format:** JSON with success/error fields

### Ollama Local Models
- **Connection:** `http://localhost:11434`
- **Default Model:** `qwen2:7b`
- **Used by:** `/api/chat` (fallback), Hostess agent

### Qdrant Vector DB
- **Connection:** `http://localhost:6333`
- **Collection:** `vetka_elisya`
- **Used by:** Search, KG, tree, scanning

### Weaviate (Optional)
- **Connection:** `http://localhost:8080`
- **Used by:** Hybrid search (keyword), falls back to Qdrant

### OpenRouter (Optional)
- **API:** Via `OPENROUTER_API_KEY` or OpenCode Bridge
- **Models:** 500+ available
- **Rotation:** Automatic key rotation via bridge

---

## Request/Response Patterns

### Standard Success Response
```json
{
  "success": true,
  "data": {...},
  "timestamp": 1234567890
}
```

### Standard Error Response
```json
{
  "success": false,
  "error": "Error description",
  "status_code": 400,
  "timestamp": 1234567890
}
```

### Query Parameters
- **Filtering:** `limit`, `offset`, `filters`
- **Formatting:** `format`, `mode`, `collection`
- **Behavior:** `force_refresh`, `skip_cache`

### Request Body
- **Chat:** `message`, `model_override`, `conversation_id`
- **Search:** `query`, `limit`, `filters`
- **Config:** Any JSON object (API keys prevented)

---

## Performance Characteristics

| Endpoint | Typical Latency | Cached |
|----------|-----------------|--------|
| `/api/chat` | 1-5s | No |
| `/api/search/semantic` | 100-500ms | Yes (5min) |
| `/api/search/hybrid` | 200-1000ms | Yes (5min) |
| `/api/tree/data` | 500ms-2s | No |
| `/api/tree/knowledge-graph` | 1-5s | Yes (session) |
| `/api/files/read` | 10-100ms | No |
| `/api/health/deep` | 200-2000ms | No |

---

## Development & Debugging

### Quick Local Testing

```bash
# Chat endpoint
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "model_override": "qwen2:7b"}'

# Search endpoint
curl "http://localhost:8000/api/search/hybrid?q=test&limit=5"

# Tree endpoint
curl "http://localhost:8000/api/tree/data?mode=directory"

# Health check
curl "http://localhost:8000/api/health/deep"
```

### Debug Endpoints

- `/api/debug/inspect` - Full tree state
- `/api/debug/tree-state` - Quick status
- `/api/debug/recent-errors` - Error log
- `/api/debug/team-messages` - MCP agent messages

### Logging

- Console: Check terminal where VETKA started
- File: `data/logs/` (if configured)
- Level: Configurable via `LOG_LEVEL` env var

---

## Version History

| Phase | Date | Changes |
|-------|------|---------|
| Phase 93 | 2026-01-25 | Complete API reference documentation |
| Phase 80 | 2026-01-21 | Debug routes, MCP team messaging |
| Phase 68 | 2026-01-18 | Hybrid search with RRF fusion |
| Phase 56 | 2026-01-15 | Group chat, model registry |
| Phase 54 | 2026-01-08 | Watcher, file operations |
| Phase 43 | 2026-01-05 | Health endpoints |

---

## FAQ

### Q: Where should I start?
**A:** Read `API_QUICK_START.md` first, then refer to `API_ENDPOINTS_REFERENCE.md` as needed.

### Q: How do I add API keys?
**A:** Use `POST /api/keys/add` or `POST /api/keys/add-smart` for auto-detection.

### Q: Can I use VETKA without internet?
**A:** Yes! Local Ollama models work without internet. OpenRouter requires internet.

### Q: How do I enable parallel agent execution?
**A:** Set `PARALLEL_MODE=true` in environment variables.

### Q: What's the difference between semantic and hybrid search?
**A:** Semantic uses vector similarity (Qdrant), hybrid combines semantic + keyword (Weaviate) with RRF fusion.

### Q: Can I extend the API?
**A:** Yes! Add routes to `src/api/routes/` and register in `__init__.py`.

---

## Quick Reference Cards

### Chat Endpoint Flow
```
POST /api/chat
  → Hostess Decision (optional)
  → Orchestrator (optional)
  → Model Call
  → Memory Save
  → Eval Scoring
  ↓
Response with metrics
```

### Search Flow
```
GET /api/search/hybrid
  → Cache check
  → Semantic (Qdrant) + Keyword (Weaviate)
  → RRF Fusion
  → Cache result
  ↓
Merged results with source attribution
```

### Scanner Flow
```
POST /api/scanner/rescan
  → Reset stop flag
  → Cleanup old entries
  → Scan directory
  → Update Qdrant vectors
  → Emit progress events
  ↓
Statistics with file counts
```

---

## Related Documentation

- **VETKA Architecture:** `docs/phase-**/ARCHITECTURE.md`
- **Agent System:** `docs/phase-**/AGENTS_DOCUMENTATION.md`
- **Memory System:** `docs/phase-**/MEMORY_SYSTEM.md`
- **Orchestration:** `docs/phase-**/ORCHESTRATION_GUIDE.md`
- **MCP Integration:** `docs/phase-**/MCP_INTEGRATION.md`

---

## Support & Contributions

### Reporting Issues
1. Check `/api/debug/recent-errors` for error context
2. Include endpoint name and request body
3. Provide `/api/health/deep` output

### Contributing
1. Add endpoint to appropriate `*_routes.py` file
2. Update `__init__.py` router aggregator
3. Document in this reference (PR required)

### Questions
- Check this documentation first
- Search existing issues
- Ask in VETKA discussions

---

**Generated:** 2026-01-25
**VETKA Phase:** 93
**Documentation Status:** Complete
**Last Updated:** 2026-01-25

---

## Quick Links

| Document | Purpose | When to Use |
|----------|---------|------------|
| **API_QUICK_START.md** | Quick reference | Getting started |
| **API_ENDPOINTS_REFERENCE.md** | Complete documentation | Integration, debugging |
| **API_INDEX.md** | Navigation guide | Finding information |

---

Start with [API_QUICK_START.md](./API_QUICK_START.md)
