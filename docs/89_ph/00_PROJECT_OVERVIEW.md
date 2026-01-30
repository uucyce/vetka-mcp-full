# VETKA PROJECT OVERVIEW v1.0
**Reconnaissance Report: 2026-01-22**

---

## DEPENDENCY MAP

### Backend Stack (Python)
**Location:** `/src/` | **Entry:** `/src/main.py`

**Core Framework:**
- FastAPI / Flask 3.0 + flask-socketio 5.3
- LangGraph 0.2.45 | LangChain 0.3 | CrewAI 0.201
- Qdrant (vector DB) 1.11.1 | Weaviate 4.9.3

**LLM Providers:**
- Anthropic SDK 0.66 (Claude)
- OpenAI 1.99.9
- Ollama 0.5.3
- LiteLLM 1.76.2 (multi-provider router)

**Key Services:**
- File Processing: pdf2image, PyPDF2, Pillow
- Data Validation: Pydantic v1
- Testing: pytest

### Frontend Stack (Node.js)
**Location:** `/app/frontend/` | **Entry:** `/app/frontend/static/js/tree_view.js`

**Core:**
- 3D-force-graph 1.70.0 (Three.js-based)
- D3 7.9.0 (layout/forces)
- HTTP Server 14.1.1 (local dev)

### MCP Servers
**Location:** `/src/mcp/` | **Main Server:** `/src/mcp/vetka_mcp_server.py`

**Components:**
- `vetka_mcp_bridge.py` - Bridge between client/server
- `vetka_mcp_server.py` - Main MCP endpoint (31KB)
- `stdio_server.py` - Stdio transport
- `mcp_server.py` - Core server logic
- `/tools/` - 15+ tool implementations

**MCP Tools Exposed:**
- Memory operations, file scanning, graph building
- Agent triggering, approval workflows
- Qdrant integration

### External Services
- **Qdrant Cloud:** Vector embeddings/search (Elisya integration)
- **LLM APIs:** Claude, GPT, Grok, Deepseek, QwQ
- **Whisper:** Audio transcription (centralized via MCP)

---

## ARCHITECTURE VECTORS

### Backend Entry Points
```
MAIN SERVER:     /src/main.py
├─ Initialization:  /src/initialization/components_init.py
├─ Routes:          /src/api/routes/ (11 files)
├─ Handlers:        /src/api/handlers/ (multiple)
└─ Services:        /src/services/

ORCHESTRATION:   /src/orchestration/ (34 files)
├─ LangGraph:       langgraph_builder.py
├─ Agent Chain:     agent_orchestrator.py
├─ CAM Engine:      cam_engine.py
├─ Context Fusion:  context_fusion.py
└─ Tools:           elysia_tools.py

FILE SCANNING:   /src/scanners/
├─ Watcher:        file_watcher.py
├─ Qdrant Updater:  qdrant_updater.py (Phase 87 fix)
└─ Packages:       known_packages.py

GROUP CHAT:      /src/api/handlers/group_message_handler.py
└─ @mention:      Multi-strategy matching (Phase 88 fix)

MCP INTEGRATION: /src/mcp/
├─ Bridge:         vetka_mcp_bridge.py
└─ Server:         vetka_mcp_server.py
```

### Frontend Entry Points
```
MAIN UI:         /app/frontend/
├─ Tree Viewer:   static/js/tree_view.js
├─ Components:    static/components/ (React/TSX)
├─ Styles:        static/css/
└─ WebGL:         Three.js + Force-Graph

CHAT PANEL:      static/components/ChatPanel.tsx
├─ Group Chat:    GroupChatPanel.tsx
└─ Message Handler: MessageHandler.tsx

SCANNER PANEL:   static/components/ScannerPanel.tsx
├─ File Count:    filesCount fix (Phase 85)
└─ Controls:      Stop/pause (Phase 83-84)
```

### Qdrant Integration
```
Entry:           /src/knowledge_graph/qdrant_client.py
Updater:         /src/scanners/qdrant_updater.py
├─ Watchdog Sync: Fixed Phase 87 race conditions
├─ Deduplication: Phase 84 implementation
└─ Indexing:      File metadata + embeddings

API Routes:      /src/api/routes/qdrant_routes.py
```

### Watchdog System
```
Watcher:         /src/scanners/file_watcher.py
Events:          Phase 87 integration with Qdrant
Routes:          /src/api/routes/watcher_routes.py
├─ Start scan
├─ Pause scanner
├─ Stop scanner (Phase 83)
└─ Clear all (Phase 84)
```

### Agent Infrastructure
```
Agents:          /src/agents/ (29 subdirs)
├─ MCP Agents:   MCP server registration
├─ Orchestrator: agent_orchestrator.py
└─ Tools:        /src/mcp/tools/

Group Chat:      /src/services/group_chat_manager.py
├─ Participants:  Model assignments
├─ Mentions:      Phase 88 multi-strategy matching
└─ Response Chain: Agent routing + aggregation
```

---

## STATUS CHECKLIST

### ✅ COMPLETED PHASES (77-88)

| Phase | Feature | Status | Key File |
|-------|---------|--------|----------|
| 77-78 | Memory sync protocol | ✅ Done | `/docs/77_78_ph/PHASE_77_MEMORY_SYNC_PROTOCOL_FINAL.md` |
| 79 | Sugiyama layout | ✅ Done | `/docs/79_ph_sugiyama/` |
| 80 | MCP agents + routing | ✅ Done | Phase 80.1-40 commits |
| 81 | MCP fixes | ✅ Done | `/docs/81_ph_mcp_fixes/` |
| 82 | UI fixes (chat/scanner) | ✅ Done | `/docs/82_ph_ui_fixes/` (22 commits) |
| 83 | Scanner stop mechanism | ✅ Done | `qdrant_updater.py` stop logic |
| 84 | Clear All + dedup | ✅ Done | Deduplication in scanner |
| 85 | Add Folder scan fix | ✅ Done | `ScannerPanel.tsx` filesCount |
| 86 | MCP @mention trigger | ✅ Done | `debug_routes.py:1162-1240` |
| 87 | Watchdog→Qdrant sync | ✅ Done | `file_watcher.py` + `main.py` |
| 88 | Agent chain response | ✅ Done | 3-tier mention matching (Phase 88 fix) |

### 🔄 IN PROGRESS / PENDING

| Phase | Issue | Priority | File |
|-------|-------|----------|------|
| 80.11 | Pinned files NOT saving | 🔴 CRITICAL | `group_chat_manager.py` |
| 80.12 | Team settings menu missing | 🔴 CRITICAL | Group creation UI |
| 80.13+ | Deepseek fallback (no tools) | 🔴 CRITICAL | LLM routing |

### 📊 METRICS
- **Total Python Files:** 267 | **TypeScript/React:** 176
- **MCP Tools:** 15+ implementations
- **Backend Modules:** 37 directories
- **Git Commits (recent):** Phase 80.38-80.40 (Grok key rotation)

---

## CRITICAL PATHS FOR AGENTS

### Initialization Sequence
```
1. main.py startup
   ↓
2. components_init.py → Load services
   ↓
3. Qdrant connection + watchdog start
   ↓
4. MCP server startup (vetka_mcp_server.py)
   ↓
5. Flask + SocketIO listeners active
```

### Message Flow (Group Chat)
```
Message received → group_message_handler.py
    ↓
Parse @mentions (regex: r'@(\w+)')
    ↓
Multi-strategy matching (Phase 88):
  1. Exact display_name match
  2. agent_id match
  3. Prefix match (before parentheses)
    ↓
Add matched agents to response queue
    ↓
LangGraph orchestrator processes chain
    ↓
Agent responses aggregated + returned
```

### File Sync Flow (Watchdog)
```
File system event → file_watcher.py
    ↓
Create/update/delete detected
    ↓
qdrant_updater.py processes
    ↓
Deduplication check (Phase 84)
    ↓
Qdrant index updated + broadcast to frontend
    ↓
WebSocket: UI updates in real-time
```

---

## RECENT FIX SUMMARIES

**Phase 87:** Fixed watchdog→Qdrant race conditions. Watcher now properly syncs with Qdrant on startup (`main.py` integration).

**Phase 88:** Fixed agent chain responses. Multi-strategy @mention matching now handles display names with model info in parentheses. Enables natural mention syntax: "@Researcher" matches "Researcher (Claude Opus 4.5)".

**Phase 80.38-40:** Grok API key detection + rotation. OpenRouter fallback when xai key missing.

---

## KNOWN BLOCKERS

1. **Pinned Files:** Not persisting in `groups.json`. Need `pinned_files` field in schema.
2. **Team Settings:** Group settings UI broken after creation. Needs adapter for existing menu.
3. **Model Support:** Deepseek/QwQ lack tool support → need fallback routing in `litellm` config.

---

## DEPLOYMENT INFO

**Backend:** `Flask 3.0` @ localhost:5001
**Frontend:** Static files @ `/app/frontend/` (HTTP server @ 3000)
**Vector DB:** Qdrant (local or cloud)
**Config:** `/app/.env` + `/src/config/`

---

*Generated by Claude Reconnaissance Agent | Phase 89*
*Code coverage: 267 Python modules | 15+ MCP tools | 176 Frontend components*
